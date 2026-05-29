"""Allure evidence reporting for WCAG criterion evaluation."""

from __future__ import annotations

import json
from typing import Any

import pytest

import allure
from llm.models import (
    ExtractedElement,
    WCAGEvaluationRequest,
    WCAGEvaluationResult,
)
from tests.base.wcag.types import ElementEvaluationFailure


class WCAGCriterionAllureReporter:
    """Render element-level WCAG evaluator results in Allure.

    Args:
        extracted_elements: Elements submitted for evaluation.
    """

    def __init__(self, extracted_elements: list[ExtractedElement]) -> None:
        """Index extracted elements by ID for stable result lookup.

        Args:
            extracted_elements: Elements submitted to the evaluator.
        """
        self._elements_by_id = {
            element.element_id: element for element in extracted_elements
        }

    def report_results(
        self,
        request: WCAGEvaluationRequest,
        llm_result: WCAGEvaluationResult,
        accepted_statuses: tuple[str, ...] = ("PASS",),
    ) -> list[ElementEvaluationFailure]:
        """Attach all element results and collect failing elements.

        Args:
            request: Evaluation request metadata.
            llm_result: Raw evaluator response with element results.
            accepted_statuses: Status values that should pass.

        Returns:
            list[ElementEvaluationFailure]: Failing element records.

        Raises:
            Failed: If evaluator returns no element-level results.
        """
        del request

        if not llm_result.results:
            pytest.fail(
                "AI WCAG evaluation returned no element-level results."
            )

        failures: list[ElementEvaluationFailure] = []
        accepted = set(accepted_statuses)

        for result in llm_result.results:
            original_element = self._elements_by_id.get(result.element_id)
            label = self._resolve_display_label(
                original_element,
                result.element_id,
            )

            failure = self._report_single_element(
                element_id=result.element_id,
                label=label,
                status=result.status,
                reason=result.reason,
                accepted_statuses=accepted,
                html_properties=(
                    original_element.element_html if original_element else None
                ),
            )
            if failure:
                failures.append(failure)

        return failures

    def _report_single_element(
        self,
        element_id: str,
        label: str,
        status: str,
        reason: str,
        accepted_statuses: set[str],
        html_properties: dict[str, Any] | None,
    ) -> ElementEvaluationFailure | None:
        """Attach one element result and return failure data when needed.

        Args:
            element_id: Stable element identifier.
            label: Human-readable label for reporting.
            status: Evaluator status for the element.
            reason: Evaluator reasoning details.
            accepted_statuses: Set of passing status values.
            html_properties: Source HTML properties extracted for the element.

        Returns:
            ElementEvaluationFailure | None: Failure record when status is not
            accepted, otherwise None.
        """
        try:
            with allure.step(f"Element: {label}"):
                self._attach_element_details(
                    label=label,
                    html_properties=html_properties,
                    reason=reason,
                    status=status,
                )
                if status not in accepted_statuses:
                    raise AssertionError(
                        f"Element status is {status}. Reason: {reason}"
                    )
        except AssertionError:
            return ElementEvaluationFailure(
                element_id=element_id,
                status=status,
                label=label,
                reason=reason,
                html_properties=html_properties,
            )

        return None

    @staticmethod
    def _resolve_display_label(
        element: ExtractedElement | None,
        element_id: str,
    ) -> str:
        """Resolve a stable, human-readable element label.

        Args:
            element: Optional extracted element payload.
            element_id: Fallback identifier when labels are unavailable.

        Returns:
            str: Preferred display label.
        """
        if not element:
            return f"Unknown Element ({element_id})"

        properties = element.element_html
        return (
            properties.get("visible_text")
            or properties.get("href")
            or element_id
        )

    @staticmethod
    def _attach_element_details(
        label: str,
        html_properties: dict[str, Any] | None,
        reason: str,
        status: str,
    ) -> None:
        """Attach evaluator status, reasoning, and HTML payload to Allure.

        Args:
            label: Human-readable element label.
            html_properties: Extracted element payload.
            reason: Evaluator reasoning text.
            status: Evaluator status value.
        """
        base_name = f"Element: {label}"
        allure.attach(
            status,
            name=f"{base_name} | LLM Status",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            reason,
            name=f"{base_name} | LLM Reasoning",
            attachment_type=allure.attachment_type.TEXT,
        )
        if html_properties is None:
            allure.attach(
                "No matching extracted HTML properties found.",
                name=f"{base_name} | Extracted HTML Properties",
                attachment_type=allure.attachment_type.TEXT,
            )
            return

        allure.attach(
            json.dumps(html_properties, indent=2),
            name=f"{base_name} | Extracted HTML Properties",
            attachment_type=allure.attachment_type.JSON,
        )


def assert_llm_outcome_or_raise(
    criterion_key: str,
    llm_result: WCAGEvaluationResult,
    failures: list[ElementEvaluationFailure],
    wcag_rule_id: str,
) -> None:
    """Attach evaluator payloads and raise when quality gates fail.

    Args:
        criterion_key: WCAG criterion key used for attachment naming.
        llm_result: Aggregated evaluator response for the criterion.
        failures: Element-level failures collected during reporting.
        wcag_rule_id: WCAG rule identifier used in failure messages.

    Raises:
        AssertionError: If the evaluator status is not ``SUCCESS`` or any
            element failed its accepted-status gate.
    """
    allure.attach(
        llm_result.model_dump_json(indent=2),
        name=f"llm-{criterion_key}-raw-response",
        attachment_type=allure.attachment_type.JSON,
    )

    if llm_result.status != "SUCCESS":
        raise AssertionError(
            f"WCAG {wcag_rule_id} LLM evaluation status is "
            f"{llm_result.status}."
        )

    if not failures:
        return

    allure.attach(
        json.dumps([failure.to_dict() for failure in failures], indent=2),
        name=f"FAILED Elements Summary: ({len(failures)} items)",
        attachment_type=allure.attachment_type.JSON,
    )
    raise AssertionError(
        f"WCAG {wcag_rule_id} failed for "
        f"{len(failures)}/{len(llm_result.results)} elements. "
        "See the 'FAILED Elements Summary' attachment above for details."
    )
