"""Allure report configuration helpers for the framework."""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from utils.core.environment import EnvironmentStore, get_environment_store


@dataclass(frozen=True)
class AllureConfig:
    """Runtime configuration for Allure reporting.

    Attributes:
        enabled: Whether Allure result generation is enabled.
        results_dir: Directory where Allure raw results are written.
        report_dir: Directory where generated HTML report is written.
        clean_results: Whether results directory is cleaned before a run.
    """

    enabled: bool
    results_dir: Path
    report_dir: Path
    clean_results: bool


class AllureSettingsFactory:
    """Build AllureConfig from shared environment store."""

    def __init__(self, env_store: EnvironmentStore):
        """Initialize factory.

        Args:
            env_store: Shared environment store singleton.
        """
        self._env = env_store

    def build(self) -> AllureConfig:
        """Build immutable allure configuration.

        Returns:
            AllureConfig: Parsed and validated allure configuration.
        """
        runtime_root = self._env.get_runtime_root()
        allure_root = self._env.resolve_path(
            self._env.get_optional("ALLURE_ROOT_DIR", default="allure"),
            runtime_root,
        )

        results_dir = self._env.resolve_path(
            self._env.get_optional(
                "ALLURE_RESULTS_SUBDIR",
                default="results",
            ),
            allure_root,
        )
        report_dir = self._env.resolve_path(
            self._env.get_optional(
                "ALLURE_REPORT_SUBDIR",
                default="report",
            ),
            allure_root,
        )

        return AllureConfig(
            enabled=self._env.get_bool_optional(
                "ALLURE_ENABLED",
                default=True,
            ),
            results_dir=results_dir,
            report_dir=report_dir,
            clean_results=self._env.get_bool_optional(
                "ALLURE_CLEAN_RESULTS",
                default=False,
            ),
        )


class AllureConfigurator:
    """Encapsulate allure preparation and command helpers."""

    def __init__(self, config: AllureConfig):
        """Initialize configurator.

        Args:
            config: Immutable allure configuration.
        """
        self._config = config
        self._is_configured = False

    @property
    def config(self) -> AllureConfig:
        """Get immutable allure configuration.

        Returns:
            AllureConfig: Runtime allure configuration.
        """
        return self._config

    def configure(self) -> AllureConfig:
        """Prepare allure directories and return effective config.

        Returns:
            AllureConfig: Effective allure configuration.
        """
        if self._is_configured:
            return self._config

        if not self._config.enabled:
            self._is_configured = True
            return self._config

        if self._config.clean_results and self._config.results_dir.exists():
            shutil.rmtree(self._config.results_dir)

        self._config.results_dir.mkdir(parents=True, exist_ok=True)
        self._config.report_dir.mkdir(parents=True, exist_ok=True)
        self._is_configured = True
        return self._config

    def write_environment_properties(
        self,
        metadata: Mapping[str, str],
    ) -> Path | None:
        """Write environment.properties for allure report context.

        Args:
            metadata: Key-value pairs in properties format.

        Returns:
            Path | None: Output file path, or None when disabled.
        """
        resolved = self.configure()
        if not resolved.enabled:
            return None

        output = resolved.results_dir / "environment.properties"
        lines = [f"{key}={value}" for key, value in metadata.items()]
        output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return output


ALLURE_CONFIGURATOR = AllureConfigurator(
    AllureSettingsFactory(get_environment_store()).build()
)


def load_allure_config_from_environment() -> AllureConfig:
    """Load immutable allure configuration.

    Returns:
        AllureConfig: Parsed and validated allure configuration.
    """
    return ALLURE_CONFIGURATOR.config


async def configure_allure(config: AllureConfig | None = None) -> AllureConfig:
    """Asynchronously prepare allure directories and return config.

    Args:
        config: Optional externally provided allure configuration.

    Returns:
        AllureConfig: Effective allure configuration.
    """
    configurator = (
        ALLURE_CONFIGURATOR if config is None else AllureConfigurator(config)
    )
    return await asyncio.to_thread(configurator.configure)


async def write_environment_properties(
    metadata: Mapping[str, str],
    config: AllureConfig | None = None,
) -> Path | None:
    """Asynchronously write environment.properties for report context.

    Args:
        metadata: Key-value pairs in properties format.
        config: Optional externally provided allure configuration.

    Returns:
        Path | None: Output file path, or None when disabled.
    """
    configurator = (
        ALLURE_CONFIGURATOR if config is None else AllureConfigurator(config)
    )
    return await asyncio.to_thread(
        configurator.write_environment_properties,
        metadata,
    )
