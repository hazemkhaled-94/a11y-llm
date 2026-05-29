"""Shared pytest fixtures for logging, reporting, and Playwright setup."""

from __future__ import annotations

import asyncio
import os
import platform
from collections.abc import AsyncGenerator, Generator
from dataclasses import dataclass
from typing import Any

import pytest
import pytest_asyncio
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from tests.base.wcag.repository import load_wcag_criteria
from utils.logging import (
    Logger,
    clear_correlation_id,
    configure_logging,
    get_logger,
    set_correlation_id,
)
from utils.reporting import (
    configure_allure,
    load_allure_config_from_environment,
    write_environment_properties,
)


@dataclass(frozen=True)
class PlaywrightRuntimeSettings:
    """Resolved Playwright runtime settings shared across fixtures."""

    headless: bool
    slow_mo_ms: int
    launch_timeout_ms: int
    action_timeout_ms: int
    navigation_timeout_ms: int
    ignore_https_errors: bool


_PW_SETTINGS_ATTR = "_a11y_playwright_runtime_settings"


def pytest_configure(config: pytest.Config) -> None:
    """Ensure pytest writes Allure results when Allure is enabled.

    This keeps `poetry run pytest ...` behavior consistent without requiring
    manual `--alluredir` arguments.
    """
    configure_logging()

    setattr(
        config,
        _PW_SETTINGS_ATTR,
        PlaywrightRuntimeSettings(
            headless=_get_env_bool("PW_HEADLESS", default=False),
            slow_mo_ms=_get_env_int("PW_SLOW_MO_MS", default=150),
            launch_timeout_ms=_get_env_int(
                "PW_LAUNCH_TIMEOUT_MS",
                default=30_000,
                min_value=1,
            ),
            action_timeout_ms=_get_env_int(
                "PW_ACTION_TIMEOUT_MS",
                default=10_000,
                min_value=1,
            ),
            navigation_timeout_ms=_get_env_int(
                "PW_NAVIGATION_TIMEOUT_MS",
                default=20_000,
                min_value=1,
            ),
            ignore_https_errors=_get_env_bool(
                "PW_IGNORE_HTTPS_ERRORS",
                default=True,
            ),
        ),
    )

    allure_cfg = load_allure_config_from_environment()
    if not allure_cfg.enabled:
        return

    current_allure_dir = getattr(config.option, "allure_report_dir", None)
    if current_allure_dir:
        return

    config.option.allure_report_dir = str(allure_cfg.results_dir)


def pytest_sessionstart(session: pytest.Session) -> None:
    """Prepare Allure lifecycle metadata using native pytest hooks."""
    del session
    asyncio.run(configure_allure())
    asyncio.run(
        write_environment_properties(
            {
                "framework": "a11y-llm",
                "python_version": platform.python_version(),
                "platform": platform.platform(),
            }
        )
    )


def _get_env_bool(name: str, *, default: bool) -> bool:
    """Read a boolean environment variable with tolerant parsing."""
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    return default


def _get_env_int(name: str, *, default: int, min_value: int = 0) -> int:
    """Read an integer environment variable with safe fallback."""
    value = os.getenv(name)
    if value is None:
        return default

    try:
        parsed = int(value)
    except ValueError:
        return default

    return parsed if parsed >= min_value else default


def _get_playwright_runtime_settings(
    pytestconfig: pytest.Config,
) -> PlaywrightRuntimeSettings:
    """Get resolved Playwright settings cached in pytest config."""
    resolved = getattr(pytestconfig, _PW_SETTINGS_ATTR, None)
    if isinstance(resolved, PlaywrightRuntimeSettings):
        return resolved

    return PlaywrightRuntimeSettings(
        headless=_get_env_bool("PW_HEADLESS", default=False),
        slow_mo_ms=_get_env_int("PW_SLOW_MO_MS", default=150),
        launch_timeout_ms=_get_env_int(
            "PW_LAUNCH_TIMEOUT_MS",
            default=30_000,
            min_value=1,
        ),
        action_timeout_ms=_get_env_int(
            "PW_ACTION_TIMEOUT_MS",
            default=10_000,
            min_value=1,
        ),
        navigation_timeout_ms=_get_env_int(
            "PW_NAVIGATION_TIMEOUT_MS",
            default=20_000,
            min_value=1,
        ),
        ignore_https_errors=_get_env_bool(
            "PW_IGNORE_HTTPS_ERRORS",
            default=True,
        ),
    )


@pytest.fixture(scope="session")
def browser_type_launch_args(
    pytestconfig: pytest.Config,
) -> dict[str, Any]:
    """Configure Playwright browser launch args from environment."""
    settings = _get_playwright_runtime_settings(pytestconfig)
    logger = get_logger("conftest")

    logger.info(
        "Launching Chromium with headless=%s slow_mo_ms=%s "
        "launch_timeout_ms=%s",
        settings.headless,
        settings.slow_mo_ms,
        settings.launch_timeout_ms,
    )
    return {
        "headless": settings.headless,
        "slow_mo": settings.slow_mo_ms,
        "timeout": settings.launch_timeout_ms,
    }


@pytest_asyncio.fixture(loop_scope="session")
async def playwright_runtime() -> AsyncGenerator[Playwright, None]:
    """Provide one async Playwright runtime for the test session."""
    async with async_playwright() as playwright:
        yield playwright


@pytest_asyncio.fixture(loop_scope="session")
async def browser(
    playwright_runtime: Playwright,
    pytestconfig: pytest.Config,
    browser_type_launch_args: dict[str, Any],
) -> AsyncGenerator[Browser, None]:
    """Launch one async browser instance for the test session."""
    logger = get_logger("conftest")
    browser_names = pytestconfig.getoption("--browser", default=[])
    browser_name = (
        str(browser_names[0])
        if isinstance(browser_names, list) and browser_names
        else "chromium"
    )

    browser_type = getattr(playwright_runtime, browser_name, None)
    if browser_type is None:
        raise pytest.UsageError(
            f"Unsupported browser '{browser_name}'. "
            "Expected one of chromium, firefox, webkit."
        )

    browser_instance = await browser_type.launch(**browser_type_launch_args)
    logger.info("Launched async Playwright browser=%s", browser_name)
    try:
        yield browser_instance
    finally:
        await asyncio.wait_for(browser_instance.close(), timeout=10)


@pytest_asyncio.fixture(loop_scope="session")
async def context(
    browser: Browser,
    pytestconfig: pytest.Config,
) -> AsyncGenerator[BrowserContext, None]:
    """Create one configured async Playwright context per test."""
    settings = _get_playwright_runtime_settings(pytestconfig)
    logger = get_logger("conftest")

    browser_context = await asyncio.wait_for(
        browser.new_context(ignore_https_errors=settings.ignore_https_errors),
        timeout=10,
    )
    browser_context.set_default_timeout(settings.action_timeout_ms)
    browser_context.set_default_navigation_timeout(
        settings.navigation_timeout_ms
    )
    logger.info(
        "Created browser context with action_timeout_ms=%s "
        "navigation_timeout_ms=%s ignore_https_errors=%s",
        settings.action_timeout_ms,
        settings.navigation_timeout_ms,
        settings.ignore_https_errors,
    )
    try:
        yield browser_context
    finally:
        await asyncio.wait_for(browser_context.close(), timeout=10)


@pytest_asyncio.fixture(loop_scope="session")
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Create one async page per test and close it after execution."""
    browser_page = await asyncio.wait_for(context.new_page(), timeout=10)
    try:
        yield browser_page
    finally:
        await asyncio.wait_for(browser_page.close(), timeout=10)


@pytest.fixture
def test_logger(
    request: pytest.FixtureRequest,
) -> Generator[Logger, None, None]:
    """Provide a per-test logger with correlation scope bound locally."""
    test_id = request.node.nodeid
    logger_name = (
        request.node.cls.__name__
        if request.node.cls is not None
        else request.node.name
    )
    logger = get_logger(logger_name)
    token = set_correlation_id(test_id)
    logger.info("Starting test: %s", test_id)
    try:
        yield logger
    finally:
        clear_correlation_id(token)


@pytest.fixture
def wcag_criteria(
    test_logger: Logger,
    request: pytest.FixtureRequest,
) -> dict[str, Any]:
    """Load WCAG criteria configuration for one test."""
    return load_wcag_criteria(
        test_logger,
        project_root=request.config.rootpath,
    )
