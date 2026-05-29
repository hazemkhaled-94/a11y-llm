"""WCAG smoke-test data contracts and type aliases."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from playwright.async_api import BrowserContext

from llm.wcag_evaluator import WCAGEvaluator
from utils.logging import Logger
from web.base.base_page import BasePage

EmptyBehavior = Literal["skip", "pass", "fail"]


@dataclass(frozen=True)
class ElementEvaluationFailure:
    """Represents one failed element-level WCAG evaluation.

    Attributes:
        element_id: Stable element identifier from extraction.
        status: Evaluator status for the element.
        label: Human-readable label shown in reports.
        reason: Evaluator reasoning for the status.
        html_properties: Extracted element payload attached for diagnosis.
    """

    element_id: str
    status: str
    label: str
    reason: str
    html_properties: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the failure to a JSON-friendly dictionary.

        Returns:
            dict[str, Any]: Serializable representation for attachments.
        """
        return {
            "element_id": self.element_id,
            "status": self.status,
            "label": self.label,
            "reason": self.reason,
            "html_properties": self.html_properties,
        }


@dataclass(frozen=True)
class CriterionExecutionConfig:
    """Configuration options for executing one WCAG criterion.

    Attributes:
        criterion_key: WCAG key from criteria.json.
        empty_behavior: Policy when extraction yields no elements.
        accepted_statuses: Evaluator statuses considered passing.
    """

    criterion_key: str
    empty_behavior: EmptyBehavior
    accepted_statuses: tuple[str, ...] = ("PASS",)


@dataclass(frozen=True)
class CriterionFailure:
    """Structured criterion failure captured for delayed assertion."""

    criterion_key: str
    message: str


CriterionRunner = Callable[
    [BasePage, WCAGEvaluator, dict[str, Any], Logger, BrowserContext],
    Awaitable[None],
]


@dataclass(frozen=True)
class CriterionDefinition:
    """Typed registry entry for one WCAG criterion runner."""

    key: str
    runner: CriterionRunner
