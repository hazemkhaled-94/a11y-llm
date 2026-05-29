"""Tests for robust LLM response parsing in WCAGEvaluator."""

from __future__ import annotations

from llm.wcag_evaluator import WCAGEvaluator


def test_parse_content_accepts_plain_json() -> None:
    """Parses direct JSON object strings without wrappers."""
    payload = '{"results": []}'
    parsed = WCAGEvaluator._parse_content(payload)
    assert isinstance(parsed, dict)
    assert parsed["results"] == []


def test_parse_content_accepts_fenced_json_without_tag() -> None:
    """Parses JSON wrapped in generic markdown code fences."""
    payload = '```\n{"results": []}\n```'
    parsed = WCAGEvaluator._parse_content(payload)
    assert isinstance(parsed, dict)
    assert parsed["results"] == []


def test_parse_content_accepts_text_before_code_block() -> None:
    """Parses JSON when explanatory text appears before fenced payload."""
    payload = (
        "Here is your evaluation output.\n"
        "```json\n"
        '{"results": [{"element_id": "1", "status": "PASS", '
        '"reason": "ok", "confidence_score": 0.9}]}\n'
        "```"
    )
    parsed = WCAGEvaluator._parse_content(payload)
    assert isinstance(parsed, dict)
    assert parsed["results"][0]["element_id"] == "1"


def test_parse_content_accepts_text_wrapped_json_without_fences() -> None:
    """Parses embedded JSON surrounded by plain commentary text."""
    payload = (
        "Some commentary before JSON. "
        '{"results": [{"element_id": "x", "status": "FAIL", '
        '"reason": "bad", "confidence_score": 0.1}]} '
        "Trailing commentary."
    )
    parsed = WCAGEvaluator._parse_content(payload)
    assert isinstance(parsed, dict)
    assert parsed["results"][0]["status"] == "FAIL"
