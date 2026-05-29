"""WCAG smoke-test orchestration helpers for functional pytest tests."""

from __future__ import annotations

import json
from typing import Any

import pytest
from playwright.async_api import BrowserContext, Page
from tqdm import tqdm  # type: ignore

import allure
from llm.connector import Connector
from llm.models import ExtractedElement, WCAGEvaluationRequest
from llm.wcag_evaluator import WCAGEvaluator
from tests.base.wcag.criteria.wcag_2_4_9 import (
    run_criterion_2_4_9 as run_2_4_9,
)
from tests.base.wcag.reporting import (
    WCAGCriterionAllureReporter,
    assert_llm_outcome_or_raise,
)
from tests.base.wcag.types import (
    CriterionDefinition,
    CriterionExecutionConfig,
    CriterionFailure,
    EmptyBehavior,
)
from utils.logging import Logger
from web.base.base_page import BasePage

WCAG_SYSTEM_PROMPT = (
    "You are an expert accessibility auditor. "
    "Evaluate EACH provided DOM element individually."
)
ALLURE_PARENT_SUITE = "Accessibility Audits"
ALLURE_SUITE = "Smoke Tests"
ALLURE_TITLE_TEMPLATE = "A11Y Smoke | {target}"
ALLURE_STORY_TEMPLATE = "Accessibility smoke for {target}"


def create_wcag_evaluator() -> WCAGEvaluator:
    """Create the default WCAG evaluator instance."""
    return WCAGEvaluator(Connector())


def apply_unified_allure_naming(target: str) -> None:
    """Apply consistent naming style for Allure test entries."""
    allure.dynamic.parent_suite(ALLURE_PARENT_SUITE)
    allure.dynamic.suite(ALLURE_SUITE)
    allure.dynamic.sub_suite(target)
    allure.dynamic.story(ALLURE_STORY_TEMPLATE.format(target=target))
    allure.dynamic.title(ALLURE_TITLE_TEMPLATE.format(target=target))


async def get_elements_for_wcag_criterion(
    page: BasePage,
    criterion_key: str,
    wcag_criteria: dict[str, Any],
    logger: Logger,
) -> list[ExtractedElement]:
    """Extract criterion-targeted elements from a page."""
    target_selectors = wcag_criteria[criterion_key].get(
        "selectors",
        [],
    )
    if not target_selectors:
        raise AssertionError(
            f"No 'selectors' defined for criterion '{criterion_key}'."
        )

    combined_selector = ", ".join(target_selectors)
    logger.info("Running extraction for %s", criterion_key)
    locators = await page.extract_elements_by_locator(combined_selector)

    js_extractor = wcag_criteria[criterion_key].get("js_extractor", "")
    if not js_extractor:
        raise AssertionError(
            f"No 'js_extractor' defined for criterion '{criterion_key}'."
        )

    extracted_elements: list[ExtractedElement] = []
    extraction_progress = tqdm(
        locators,
        desc=f"Extracting {criterion_key} elements",
        unit="el",
        leave=False,
        disable=None,
    )
    for index, locator in enumerate(extraction_progress):
        raw_html = await page.extract_element_data(locator, js_extractor)
        if (
            criterion_key == "3.1.2"
            and isinstance(raw_html, dict)
            and not raw_html.get("has_text", False)
        ):
            continue

        extracted_elements.append(
            ExtractedElement(
                element_id=str(index),
                element_html=raw_html,
                parent_context=None,
            )
        )

    logger.info(
        "Successfully extracted %s evaluated elements for %s.",
        len(extracted_elements),
        criterion_key,
    )
    return extracted_elements


def _get_criterion_or_raise(
    wcag_criteria: dict[str, Any],
    criterion_key: str,
) -> dict[str, Any]:
    """Resolve criterion configuration and fail fast when missing."""
    rule = wcag_criteria.get(criterion_key)
    if not isinstance(rule, dict):
        raise AssertionError(
            f"Criterion '{criterion_key}' is missing in criteria.json."
        )
    return rule


def _handle_empty_extraction(
    criterion_key: str,
    empty_behavior: EmptyBehavior,
) -> None:
    """Resolve an empty extraction according to the criterion's policy.

    Args:
        criterion_key: WCAG criterion key, used for the evidence attachment.
        empty_behavior: Policy applied when no elements were extracted:
            ``"skip"`` marks the criterion skipped (inconclusive), ``"pass"``
            treats the absence of elements as compliant, and ``"fail"`` treats
            it as a violation.

    Raises:
        AssertionError: If ``empty_behavior`` is ``"fail"``.
        Skipped: If ``empty_behavior`` is ``"skip"``.
    """
    message = (
        "No elements were extracted for criterion "
        f"{criterion_key}. Policy={empty_behavior}."
    )
    allure.attach(
        message,
        name=f"wcag-{criterion_key}-empty-extraction",
        attachment_type=allure.attachment_type.TEXT,
    )

    if empty_behavior == "fail":
        raise AssertionError(message)
    if empty_behavior == "pass":
        return
    pytest.skip(message)


async def _execute_standard_criterion(
    page: BasePage,
    evaluator: WCAGEvaluator,
    wcag_criteria: dict[str, Any],
    logger: Logger,
    config: CriterionExecutionConfig,
) -> None:
    """Execute one standard criterion with extraction/evaluation pipeline."""
    wcag_rule = _get_criterion_or_raise(wcag_criteria, config.criterion_key)
    rule_name = wcag_rule.get("name") or "Unnamed Criterion"

    with allure.step(f"Evaluate WCAG {config.criterion_key}: {rule_name}"):
        html_elements = await get_elements_for_wcag_criterion(
            page,
            config.criterion_key,
            wcag_criteria,
            logger,
        )

        if not html_elements:
            _handle_empty_extraction(
                config.criterion_key,
                config.empty_behavior,
            )
            return

        request = WCAGEvaluationRequest(
            wcag_rule_id=config.criterion_key,
            rule_name=str(wcag_rule.get("name") or config.criterion_key),
            wcag_description=str(wcag_rule.get("description") or ""),
            elements=html_elements,
        )

        llm_result = await evaluator.evaluate(
            request=request,
            system_prompt=WCAG_SYSTEM_PROMPT,
            user_prompt=str(wcag_rule["prompt"]),
        )

        reporter = WCAGCriterionAllureReporter(html_elements)
        failures = reporter.report_results(
            request,
            llm_result,
            accepted_statuses=config.accepted_statuses,
        )

        assert_llm_outcome_or_raise(
            config.criterion_key,
            llm_result,
            failures,
            wcag_rule_id=request.wcag_rule_id,
        )


async def run_criterion_2_4_4(
    page: BasePage,
    evaluator: WCAGEvaluator,
    wcag_criteria: dict[str, Any],
    logger: Logger,
    browser_context: BrowserContext,
) -> None:
    """Run WCAG 2.4.4 with criterion-specific extraction policy."""
    del browser_context
    await _execute_standard_criterion(
        page,
        evaluator,
        wcag_criteria,
        logger,
        CriterionExecutionConfig(
            criterion_key="2.4.4",
            empty_behavior="skip",
        ),
    )


async def run_criterion_2_4_9(
    page: BasePage,
    evaluator: WCAGEvaluator,
    wcag_criteria: dict[str, Any],
    logger: Logger,
    browser_context: BrowserContext,
) -> None:
    """Run WCAG 2.4.9 using destination-page enrichment."""
    await run_2_4_9(
        page,
        evaluator,
        wcag_criteria,
        logger,
        browser_context,
        WCAG_SYSTEM_PROMPT,
    )


async def run_criterion_3_1_1(
    page: BasePage,
    evaluator: WCAGEvaluator,
    wcag_criteria: dict[str, Any],
    logger: Logger,
    browser_context: BrowserContext,
) -> None:
    """Run WCAG 3.1.1 and require page language target presence."""
    del browser_context
    await _execute_standard_criterion(
        page,
        evaluator,
        wcag_criteria,
        logger,
        CriterionExecutionConfig(
            criterion_key="3.1.1",
            empty_behavior="fail",
        ),
    )


async def run_criterion_3_1_2(
    page: BasePage,
    evaluator: WCAGEvaluator,
    wcag_criteria: dict[str, Any],
    logger: Logger,
    browser_context: BrowserContext,
) -> None:
    """Run WCAG 3.1.2 with criterion-specific policy."""
    del browser_context
    await _execute_standard_criterion(
        page,
        evaluator,
        wcag_criteria,
        logger,
        CriterionExecutionConfig(
            criterion_key="3.1.2",
            empty_behavior="pass",
        ),
    )


def criterion_steps(
    *,
    include_criterion_2_4_9: bool = False,
) -> list[CriterionDefinition]:
    """Return typed criterion registry in deterministic execution order."""
    steps: list[CriterionDefinition] = [
        CriterionDefinition(key="2.4.4", runner=run_criterion_2_4_4),
    ]
    if include_criterion_2_4_9:
        steps.append(
            CriterionDefinition(
                key="2.4.9",
                runner=run_criterion_2_4_9,
            )
        )
    steps.extend(
        [
            CriterionDefinition(key="3.1.1", runner=run_criterion_3_1_1),
            CriterionDefinition(key="3.1.2", runner=run_criterion_3_1_2),
        ]
    )
    return steps


async def run_configured_wcag_criteria(
    page: BasePage,
    evaluator: WCAGEvaluator,
    wcag_criteria: dict[str, Any],
    logger: Logger,
    browser_context: BrowserContext,
    *,
    include_criterion_2_4_9: bool = False,
) -> None:
    """Run configured criteria and fail once with aggregated findings."""
    criterion_failures: list[CriterionFailure] = []
    criterion_skips: list[CriterionFailure] = []

    for criterion in criterion_steps(
        include_criterion_2_4_9=include_criterion_2_4_9,
    ):
        try:
            await criterion.runner(
                page,
                evaluator,
                wcag_criteria,
                logger,
                browser_context,
            )
        except pytest.skip.Exception as exc:
            message = str(exc)
            allure.attach(
                message,
                name=f"wcag-{criterion.key}-skipped",
                attachment_type=allure.attachment_type.TEXT,
            )
            criterion_skips.append(
                CriterionFailure(
                    criterion_key=criterion.key,
                    message=message,
                )
            )
        except AssertionError as exc:
            message = str(exc)
            allure.attach(
                message,
                name=f"wcag-{criterion.key}-failure",
                attachment_type=allure.attachment_type.TEXT,
            )
            criterion_failures.append(
                CriterionFailure(
                    criterion_key=criterion.key,
                    message=message,
                )
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            message = f"Unexpected criterion error: {exc}"
            allure.attach(
                message,
                name=f"wcag-{criterion.key}-unexpected-error",
                attachment_type=allure.attachment_type.TEXT,
            )
            criterion_failures.append(
                CriterionFailure(
                    criterion_key=criterion.key,
                    message=message,
                )
            )

    if criterion_skips:
        skipped_summary_payload = [
            {
                "criterion_key": skipped.criterion_key,
                "message": skipped.message,
            }
            for skipped in criterion_skips
        ]
        allure.attach(
            json.dumps(skipped_summary_payload, indent=2),
            name="wcag-skipped-summary",
            attachment_type=allure.attachment_type.JSON,
        )

    if criterion_failures:
        summary_payload = [
            {
                "criterion_key": failure.criterion_key,
                "message": failure.message,
            }
            for failure in criterion_failures
        ]
        allure.attach(
            json.dumps(summary_payload, indent=2),
            name="wcag-failure-summary",
            attachment_type=allure.attachment_type.JSON,
        )
        summary_lines = [
            f"- {failure.criterion_key}: {failure.message}"
            for failure in criterion_failures
        ]
        pytest.fail(
            "WCAG run completed with criterion failures:\n"
            + "\n".join(summary_lines)
        )


async def run_and_attach_axe_audit(
    page: BasePage,
    context_name: str,
) -> None:
    """Run Axe audit and attach JSON results to Allure."""
    axe_results = await page.run_axe_audit(context_name)
    allure.attach(
        json.dumps(axe_results, indent=2),
        name="axe-core-results",
        attachment_type=allure.attachment_type.JSON,
    )


async def attach_full_page_screenshot(
    page: Page,
    name: str,
) -> None:
    """Capture and attach a full-page screenshot to Allure."""
    screenshot = await page.screenshot(full_page=True)
    allure.attach(
        screenshot,
        name=name,
        attachment_type=allure.attachment_type.PNG,
    )


__all__ = [
    "attach_full_page_screenshot",
    "apply_unified_allure_naming",
    "create_wcag_evaluator",
    "criterion_steps",
    "get_elements_for_wcag_criterion",
    "run_configured_wcag_criteria",
    "run_criterion_2_4_4",
    "run_criterion_2_4_9",
    "run_criterion_3_1_1",
    "run_criterion_3_1_2",
    "run_and_attach_axe_audit",
]
