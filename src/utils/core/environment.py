"""Shared environment store loaded once for the process."""
# pyright: reportMissingImports=false

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter
from pydantic import ValidationError
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class EnvironmentStore(BaseSettings):
    """Read environment variables via pydantic-settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core runtime roots
    PROJECT_ROOT_DIR: str | None = None

    # LLM
    AUDITOR_LLM_API_KEY: str | None = None
    AUDITOR_LLM_MODEL: str | None = None
    AUDITOR_LLM_URL: str | None = None

    # Logging
    LOG_LEVEL: str | None = None
    LOG_FORMAT: str | None = None
    LOG_SINK: str | None = None
    LOG_ROOT_DIR: str | None = None
    LOG_FILE: str | None = None
    LOG_ROTATE_MAX_BYTES: str | None = None
    LOG_ROTATE_BACKUP_COUNT: str | None = None
    LOG_SERVICE_NAME: str | None = None

    # Allure
    ALLURE_ENABLED: str | None = None
    ALLURE_ROOT_DIR: str | None = None
    ALLURE_RESULTS_SUBDIR: str | None = None
    ALLURE_REPORT_SUBDIR: str | None = None
    ALLURE_CLEAN_RESULTS: str | None = None

    _BOOL_ADAPTER = TypeAdapter(bool)
    _INT_ADAPTER = TypeAdapter(int)

    def __init__(self) -> None:
        """Load settings once from environment and optional `.env` file."""
        super().__init__()

    def _lookup_raw(self, name: str) -> str | None:
        """Resolve one variable from settings fields or process env."""
        model_fields = type(self).model_fields
        if name in model_fields:
            value: Any = getattr(self, name)
            if value is None:
                return None
            if isinstance(value, str):
                return value
            return str(value)

        fallback = os.getenv(name)
        if fallback is None:
            return None
        return fallback

    def get_required(self, name: str) -> str:
        """Get required non-empty environment variable.

        Args:
            name: Environment variable name.

        Returns:
            str: Non-empty value.

        Raises:
            EnvironmentError: If missing or empty.
        """
        value = self._lookup_raw(name)
        if value is None or value.strip() == "":
            raise EnvironmentError(
                f"Required environment variable missing: {name}"
            )
        return value

    def get_optional(self, name: str, *, default: str) -> str:
        """Get environment variable or fallback default value.

        Args:
            name: Environment variable name.
            default: Default value used when missing or blank.

        Returns:
            str: Environment value or provided default.
        """
        value = self._lookup_raw(name)
        if value is None or value.strip() == "":
            return default
        return value

    def get_bool_required(self, name: str) -> bool:
        """Parse required environment variable as boolean.

        Args:
            name: Environment variable name.

        Returns:
            bool: Parsed boolean value.

        Raises:
            ValueError: If value is not a supported boolean literal.
        """
        value = self.get_required(name)
        try:
            return self._BOOL_ADAPTER.validate_python(value)
        except ValidationError as exc:
            raise ValueError(
                f"Environment variable {name} must be true/false like value."
            ) from exc

    def get_bool_optional(self, name: str, *, default: bool) -> bool:
        """Parse optional environment variable as boolean.

        Args:
            name: Environment variable name.
            default: Default value when missing/blank/invalid.

        Returns:
            bool: Parsed boolean value or default.
        """
        value = self._lookup_raw(name)
        if value is None or value.strip() == "":
            return default

        try:
            return self._BOOL_ADAPTER.validate_python(value)
        except ValidationError:
            return default

    def get_int_required(
        self,
        name: str,
        *,
        min_value: int | None = None,
    ) -> int:
        """Parse required environment variable as integer.

        Args:
            name: Environment variable name.
            min_value: Optional minimum inclusive value.

        Returns:
            int: Parsed integer value.

        Raises:
            ValueError: If value is not integer or below minimum.
        """
        raw_value = self.get_required(name)
        try:
            parsed = self._INT_ADAPTER.validate_python(raw_value)
        except ValidationError as exc:
            raise ValueError(
                f"Environment variable {name} must be an integer."
            ) from exc

        if min_value is not None and parsed < min_value:
            raise ValueError(
                f"Environment variable {name} must be >= {min_value}."
            )

        return parsed

    def get_int_optional(
        self,
        name: str,
        *,
        default: int,
        min_value: int | None = None,
    ) -> int:
        """Parse optional environment variable as integer.

        Args:
            name: Environment variable name.
            default: Default value when missing/invalid.
            min_value: Optional minimum inclusive value.

        Returns:
            int: Parsed integer or default fallback.
        """
        raw_value = self._lookup_raw(name)
        if raw_value is None or raw_value.strip() == "":
            return default

        try:
            parsed = self._INT_ADAPTER.validate_python(raw_value)
        except ValidationError:
            return default

        if min_value is not None and parsed < min_value:
            return default

        return parsed

    def resolve_path(self, value: str, root: Path) -> Path:
        """Resolve absolute or root-relative path.

        Args:
            value: Path string from environment.
            root: Base root for relative paths.

        Returns:
            Path: Absolute normalized path.
        """
        candidate = Path(value).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        return (root / candidate).resolve()

    def get_runtime_root(self) -> Path:
        """Resolve runtime root from env or working directory.

        Returns:
            Path: Absolute runtime root path.
        """
        cwd = Path(os.getcwd()).resolve()
        root_value = (self.PROJECT_ROOT_DIR or "").strip()
        if root_value == "":
            return cwd
        return self.resolve_path(root_value, cwd)


ENVIRONMENT_STORE = EnvironmentStore()


def get_environment_store() -> EnvironmentStore:
    """Get process-wide environment store singleton.

    Returns:
        EnvironmentStore: Shared environment store.
    """
    return ENVIRONMENT_STORE
