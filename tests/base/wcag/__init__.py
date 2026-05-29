"""WCAG smoke-test package.

This package contains reusable WCAG smoke-test orchestration and criterion
implementations.
"""

from .base import (
    apply_unified_allure_naming,
    attach_full_page_screenshot,
    create_wcag_evaluator,
    criterion_steps,
    get_elements_for_wcag_criterion,
    run_and_attach_axe_audit,
    run_configured_wcag_criteria,
    run_criterion_2_4_4,
    run_criterion_2_4_9,
    run_criterion_3_1_1,
    run_criterion_3_1_2,
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
