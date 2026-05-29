"""Utilities for configuring and calling the LLM."""

from dataclasses import dataclass

from utils.core.environment import get_environment_store


@dataclass(frozen=True)
class LLMConfig:
    """Configuration required to connect to the model.

    Attributes:
        api_key: API key used to authenticate with the model endpoint.
        model_name: Name or identifier of the model.
        model_url: Base URL of the model provider endpoint.
    """

    api_key: str
    model_name: str
    model_url: str


class LLMConfigLoader:
    """Loads `LLMConfig` from environment variables."""

    def load_from_environment(self) -> LLMConfig:
        """Loads configuration from environment variables.

        Returns:
            LLMConfig: Validated configuration for the model.

        Raises:
            EnvironmentError: If a required variable is missing or empty.
        """
        env = get_environment_store()

        return LLMConfig(
            api_key=env.get_required("AUDITOR_LLM_API_KEY"),
            model_name=env.get_required("AUDITOR_LLM_MODEL"),
            model_url=env.get_required("AUDITOR_LLM_URL"),
        )
