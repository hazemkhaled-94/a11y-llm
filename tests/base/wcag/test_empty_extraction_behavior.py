"""Tests for empty WCAG extraction handling and orchestration outcomes."""

from __future__ import annotations

from typing import Any
from typing import cast

import pytest
from playwright.async_api import BrowserContext

from llm.wcag_evaluator import WCAGEvaluator
from tests.base.wcag import base as wcag_base
from tests.base.wcag.types import CriterionDefinition
from utils.logging import Logger
from web.base.base_page import BasePage


@pytest.mark.parametrize("empty_behavior", ["skip", "pass", "fail"])
def test_handle_empty_extraction_marks_criterion_skipped(
    empty_behavior: str,
) -> None:
    """No extracted elements should produce a skipped criterion outcome."""
    with pytest.raises(pytest.skip.Exception):
        wcag_base._handle_empty_extraction(
            criterion_key="2.4.4",
            empty_behavior=cast(Any, empty_behavior),
        )


@pytest.mark.asyncio
async def test_run_configured_wcag_criteria_continues_after_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skipped criteria should not fail the overall WCAG run."""

    async def _skip_runner(
        page: BasePage,
        evaluator: WCAGEvaluator,
        wcag_criteria: dict[str, Any],
        logger: Logger,
        browser_context: BrowserContext,
    ) -> None:
        del page, evaluator, wcag_criteria, logger, browser_context
        pytest.skip("No elements were extracted for criterion 2.4.4")

    monkeypatch.setattr(
        wcag_base,
        "criterion_steps",
        lambda include_criterion_2_4_9=False: [
            CriterionDefinition(key="2.4.4", runner=_skip_runner)
        ],
    )

    await wcag_base.run_configured_wcag_criteria(
        page=cast(Any, None),
        evaluator=cast(Any, None),
        wcag_criteria={},
        logger=cast(Any, None),
        browser_context=cast(Any, None),
    )
