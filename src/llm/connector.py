"""Generic LLM connector for executing network requests."""

from typing import Any, Optional, Protocol, Sequence, cast

import litellm
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
)  # type: ignore

from utils.logging.config import get_logger

from .config import LLMConfig, LLMConfigLoader

logger = get_logger(__name__)


class CompletionMessage(Protocol):
    """Protocol describing a completion message payload."""

    content: Any


class CompletionChoice(Protocol):
    """Protocol describing a completion choice payload."""

    message: CompletionMessage


class CompletionResponse(Protocol):
    """Protocol describing the subset of completion response fields used."""

    choices: Sequence[CompletionChoice]


class CompletionClient(Protocol):
    """Protocol for clients that can generate chat completions."""

    async def generate_completion(
        self,
        messages: list[dict[str, str]],
        response_format: Optional[dict[str, Any]] = None,
    ) -> CompletionResponse:
        """Generate one completion response."""
        ...


class Connector:
    """Facade for executing generic LLM completions."""

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        """Initializes the generic LLM connector."""
        if config:
            self.config = config
        else:
            self.config = LLMConfigLoader().load_from_environment()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def generate_completion(
        self,
        messages: list[dict[str, str]],
        response_format: Optional[dict[str, Any]] = None,
    ) -> CompletionResponse:
        """Send messages to the LLM and return a standardized envelope.

        Args:
            messages: List of message dictionaries.
            response_format: Optional format config (e.g., JSON Schema).

        Returns:
            CompletionResponse: The provider response projected to protocol.
        """
        response = await litellm.acompletion(
            model=self.config.model_name,
            messages=messages,
            api_base=self.config.model_url,
            api_key=self.config.api_key,
            response_format=response_format,
            max_tokens=4096,
            timeout=900,
            temperature=0.2,
            seed=200994,
            extra_body={"options": {"num_ctx": 131072}},
        )

        return cast(CompletionResponse, response)
