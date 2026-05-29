"""Service for evaluating WCAG rules using the LLM."""

import json
import math
from typing import Any, Iterator, Literal

from pydantic import ValidationError

from .connector import CompletionClient
from .models import (
    ElementEvaluationResult,
    WCAGEvaluationRequest,
    WCAGEvaluationResult,
)
from utils.logging.config import get_logger

logger = get_logger(__name__)


def build_wcag_prompt_messages(
    request: WCAGEvaluationRequest,
    system_prompt: str,
    user_prompt: str,
    output_schema: dict[str, Any],
) -> list[dict[str, str]]:
    """Build the final prompt payload for a WCAG model call."""
    reinforced_system_prompt = (
        f"{system_prompt}\n\n"
        "You MUST output a valid JSON object "
        "matching this exact JSON Schema. "
        "The root key MUST be 'results'. "
        "Do not include markdown formatting.\n"
        f"{json.dumps(output_schema, indent=2)}"
    )

    elements_json_str = request.model_dump_json(
        include={"elements"},
        exclude_none=True,
        indent=2,
    )
    user_content = f"{user_prompt}{elements_json_str}"

    return [
        {"role": "system", "content": reinforced_system_prompt},
        {"role": "user", "content": user_content},
    ]


class WCAGEvaluator:
    """Orchestrates chunked WCAG evaluations through an LLM client."""

    _VALIDATION_RETRY_ATTEMPTS = 3

    def __init__(
        self,
        connector: CompletionClient
    ) -> None:
        """Initialize the evaluator.

        Args:
            connector: Connector-compatible client for model calls.
            response_parser: Optional response parser strategy.
        """
        self.connector = connector

    async def evaluate(
        self,
        request: WCAGEvaluationRequest,
        system_prompt: str,
        user_prompt: str,
        chunk_size: int = 15,
    ) -> WCAGEvaluationResult:
        """Evaluate a request and aggregate results across chunks.

        Args:
            request: Full WCAG evaluation request.
            system_prompt: System prompt sent to the model.
            user_prompt: User prompt prefix sent to the model.
            chunk_size: Maximum number of elements per model call.

        Returns:
            WCAGEvaluationResult: Aggregated result for all input elements.

        Raises:
            ValueError: If chunk_size is less than 1.
        """
        if chunk_size < 1:
            raise ValueError("chunk_size must be at least 1.")

        all_results = []
        total_elements = len(request.elements)
        total_chunks = math.ceil(total_elements / chunk_size)
        status: Literal["SUCCESS", "ERROR"] = "SUCCESS"
        logger.info(
            f"Starting evaluation of {total_elements} "
            f"elements across {total_chunks} batches."
        )

        for current_chunk_index, chunk_request in enumerate(
            self._chunk_requests(request, chunk_size),
            start=1,
        ):
            logger.info(
                f"Processing Batch {current_chunk_index}/{total_chunks} "
                f"({len(chunk_request.elements)} elements)..."
            )
            chunk_response = await self._evaluate_single_batch(
                request=chunk_request,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            chunk_response = self._reconcile_batch_results(
                request=chunk_request,
                response=chunk_response,
                batch_index=current_chunk_index,
            )
            if chunk_response.status != "SUCCESS":
                status = "ERROR"
            all_results.extend(chunk_response.results)
            logger.info(
                f"Successfully aggregated {len(all_results)} "
                "total evaluation results."
            )
        return WCAGEvaluationResult(results=all_results, status=status)

    def _reconcile_batch_results(
        self,
        request: WCAGEvaluationRequest,
        response: WCAGEvaluationResult,
        batch_index: int,
    ) -> WCAGEvaluationResult:
        """Reconcile model batch output with expected input elements.

        This method is intentionally non-blocking. If a model returns fewer
        results than requested, it fills missing element IDs with
        ``MANUAL_REVIEW`` placeholder results so the test can continue.

        Args:
            request: The batch request sent to the model.
            response: Parsed model response for this batch.
            batch_index: One-based index of the current batch.

        Returns:
            WCAGEvaluationResult: Reconciled batch response.
        """
        expected_ids = [element.element_id for element in request.elements]

        seen_ids: set[str] = set()
        duplicate_ids: set[str] = set()
        for result in response.results:
            if result.element_id in seen_ids:
                duplicate_ids.add(result.element_id)
            seen_ids.add(result.element_id)

        missing_ids = [eid for eid in expected_ids if eid not in seen_ids]
        extra_ids = [
            result.element_id
            for result in response.results
            if result.element_id not in expected_ids
        ]

        if not missing_ids and not extra_ids and not duplicate_ids:
            return response

        logger.warning(
            "Batch %s coverage mismatch: expected=%s, received=%s, "
            "missing=%s, extra=%s, duplicates=%s",
            batch_index,
            len(expected_ids),
            len(response.results),
            len(missing_ids),
            len(extra_ids),
            len(duplicate_ids),
        )

        reconciled_results = list(response.results)
        for missing_id in missing_ids:
            reconciled_results.append(
                ElementEvaluationResult(
                    element_id=missing_id,
                    status="MANUAL_REVIEW",
                    reason=(
                        "Model did not return an evaluation result for this "
                        f"element in batch {batch_index}."
                    ),
                    confidence_score=0.0,
                )
            )

        return WCAGEvaluationResult(
            status="ERROR",
            results=reconciled_results,
        )

    def _chunk_requests(
        self,
        request: WCAGEvaluationRequest,
        chunk_size: int,
    ) -> Iterator[WCAGEvaluationRequest]:
        """Yield chunked requests from the full evaluation request.

        Args:
            request: Full evaluation request.
            chunk_size: Maximum number of elements per chunk.

        Yields:
            WCAGEvaluationRequest: Chunked request for a model invocation.
        """
        for i in range(0, len(request.elements), chunk_size):
            yield WCAGEvaluationRequest(
                wcag_rule_id=request.wcag_rule_id,
                wcag_description=request.wcag_description,
                rule_name=request.rule_name,
                elements=request.elements[i: i + chunk_size],
            )

    async def _evaluate_single_batch(
        self,
        request: WCAGEvaluationRequest,
        system_prompt: str,
        user_prompt: str,
    ) -> WCAGEvaluationResult:
        """Evaluate a single chunk through the model client.

        Args:
            request: Chunk request.
            system_prompt: System prompt.
            user_prompt: User prompt prefix.

        Returns:
            WCAGEvaluationResult: Validated result for the given chunk.

        Raises:
            ValueError: If the response envelope or payload is invalid.
        """
        output_schema = WCAGEvaluationResult.model_json_schema()
        messages = build_wcag_prompt_messages(
            request=request,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
        )

        retry_attempts = self._VALIDATION_RETRY_ATTEMPTS
        last_error: Exception | None = None
        last_content: Any = None

        for attempt in range(1, retry_attempts + 1):
            raw_response = await self.connector.generate_completion(
                messages=messages,
                response_format={
                    "type": "json_object",
                    "json_schema": {
                        "name": "wcag_evaluation",
                        "schema": output_schema,
                    }
                },
            )

            try:
                if not raw_response.choices:
                    raise ValueError("LLM returned no choices.")

                content = raw_response.choices[0].message.content
                last_content = content
                if content is None:
                    raise ValueError(
                        "LLM returned an empty message content."
                    )

                payload = self._normalize_response_payload(content)
                return WCAGEvaluationResult.model_validate(payload)
            except (ValueError, ValidationError) as exc:
                last_error = exc
                if attempt < retry_attempts:
                    logger.warning(
                        "LLM validation failed for chunk "
                        "(attempt %s/%s). Retrying.",
                        attempt,
                        retry_attempts,
                    )
                    continue

                logger.error(
                    "LLM validation failed for chunk after %s attempts. "
                    "Raw output: %s",
                    retry_attempts,
                    last_content,
                )

        raise ValueError(
            "LLM returned malformed or non-compliant JSON."
        ) from last_error

    @staticmethod
    def _normalize_response_payload(content: Any) -> dict[str, Any]:
        """Normalize model content into WCAGEvaluationResult payload shape.

        Args:
            content: Raw LLM response content.

        Returns:
            dict[str, Any]: JSON payload compatible with WCAGEvaluationResult.

        Raises:
            ValueError: If content cannot be parsed to a JSON payload.
        """
        parsed = WCAGEvaluator._parse_content(content)

        if isinstance(parsed, list):
            return {
                "status": "SUCCESS",
                "results": parsed,
            }

        if not isinstance(parsed, dict):
            raise ValueError("LLM payload must be a JSON object or array.")

        if (
            "results" not in parsed
            and {"element_id", "status", "reason"}.issubset(parsed)
        ):
            return {
                "status": "SUCCESS",
                "results": [parsed],
            }

        return parsed

    @staticmethod
    def _parse_content(content: Any) -> dict[str, Any] | list[Any]:
        """Parse raw LLM content into JSON object/list.

        Args:
            content: Raw model output content.

        Returns:
            dict[str, Any] | list[Any]: Parsed JSON structure.

        Raises:
            ValueError: If content cannot be parsed as JSON.
        """
        if isinstance(content, dict):
            return content

        if isinstance(content, str):
            text = content.strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return WCAGEvaluator._decode_first_json_fragment(text)

        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        text_parts.append(text_value)
            if text_parts:
                return WCAGEvaluator._parse_content("".join(text_parts))

            return content

        raise ValueError(f"Unsupported model response type: {type(content)!r}")

    @staticmethod
    def _decode_first_json_fragment(
        text: str,
    ) -> dict[str, Any] | list[Any]:
        """Decode the first valid JSON object/array found within text.

        This supports model responses that contain conversational prefixes,
        fenced blocks, or trailing explanations around otherwise valid JSON.
        """
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char not in "[{":
                continue

            try:
                parsed, _ = decoder.raw_decode(text, index)
            except json.JSONDecodeError:
                continue

            if isinstance(parsed, (dict, list)):
                return parsed

        raise ValueError("LLM response is not valid JSON.")
