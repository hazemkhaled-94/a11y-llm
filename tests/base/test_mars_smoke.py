"""Smoke test that exercises accessibility checks on the Mars demo page."""

from __future__ import annotations

from typing import Any

import allure
import pytest
from playwright.async_api import BrowserContext, Page

from tests.base.wcag import (
    apply_unified_allure_naming,
    create_wcag_evaluator,
    run_and_attach_axe_audit,
    run_configured_wcag_criteria,
)
from utils.logging import Logger
from web.mars import MarsDemoPage

pytestmark = pytest.mark.asyncio


@allure.feature("Framework Smoke")
@allure.story("Mars demo page accessibility")
async def test_mars_demo_page_a11y(
    page: Page,
    context: BrowserContext,
    test_logger: Logger,
    wcag_criteria: dict[str, Any],
) -> None:
    """Open the Mars demo page and verify accessibility signals."""
    apply_unified_allure_naming("Mars Demo")
    mars_page = MarsDemoPage(page)
    wcag_evaluator = create_wcag_evaluator()

    with allure.step("Open Mars demo page"):
        await mars_page.open()

    with allure.step("Validate Mars demo page URL"):
        assert "/demo/mars/" in page.url.lower()

    with allure.step("Axe-core audit"):
        await run_and_attach_axe_audit(mars_page, "Mars Demo")

    with allure.step("LLM Audit for WCAG compliance"):
        await run_configured_wcag_criteria(
            mars_page,
            wcag_evaluator,
            wcag_criteria,
            test_logger,
            context,
        )
