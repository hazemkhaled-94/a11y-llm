"""Pydantic schemas for LLM requests and responses."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ExtractedElement(BaseModel):
    """Represents a single DOM node and its extracted properties."""

    element_id: str = Field(
        ..., description="Unique identifier for the element."
    )
    element_html: Dict[str, Any] = Field(
        description="The raw outerHTML of the element, kept brief."
    )
    parent_context: Optional[str] = Field(
        None,
        description="Text from surrounding elements "
        "(e.g., parent <p> or preceding <h1>) "
        "if fallback evaluation is triggered.",
    )


class WCAGEvaluationRequest(BaseModel):
    """Structured input required to perform an evaluation."""

    wcag_rule_id: str = Field(
        ..., description="The WCAG criteria ID (e.g., '1.1.1')."
    )
    rule_name: str = Field(..., description="Human-readable name of the rule.")
    wcag_description: str = Field(
        ..., description="The actual text of the WCAG rule."
    )
    elements: List[ExtractedElement] = Field(
        ...,
        description="The batch of elements to be evaluated "
        "in this specific request.",
    )


class ElementEvaluationResult(BaseModel):
    """The strict, universal evaluation schema for ANY extracted element."""

    element_id: str = Field(
        ..., description="The exact element_id provided in the input data."
    )
    status: Literal["PASS", "FAIL", "NEEDS_CONTEXT", "MANUAL_REVIEW"] = Field(
        ...,
        description=(
            "PASS: Fully compliant. "
            "FAIL: Confirmed violation. "
            "NEEDS_CONTEXT: Requires traversal of parent/sibling elements. "
            "MANUAL_REVIEW: The LLM cannot confidently "
            "determine compliance automatically."
        ),
    )
    reason: str = Field(
        ...,
        description="A concise, 1-2 sentence explanation mapping "
        "the decision to the specific WCAG rule.",
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="The LLM's confidence in its own evaluation (0.0 to 1.0).",
    )


class WCAGEvaluationResult(BaseModel):
    """The root JSON object expected from the LLM."""

    status: Literal["SUCCESS", "ERROR"] = Field(
        ...,
        description=(
            "Indicates whether the processed elements "
            "conform to the WCAG rule or not."
        ),
    )
    results: List[ElementEvaluationResult] = Field(
        ...,
        description="A list containing the evaluation result "
        "for every requested element.",
    )
