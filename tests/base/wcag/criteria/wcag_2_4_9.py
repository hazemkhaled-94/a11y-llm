"""WCAG 2.4.9 runner with destination-page enrichment in one module."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse
import json

import allure
from playwright.async_api import BrowserContext
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from llm.models import ExtractedElement
from llm.models import WCAGEvaluationRequest
from llm.wcag_evaluator import WCAGEvaluator
from tests.base.wcag.reporting import assert_llm_outcome_or_raise
from tests.base.wcag.reporting import WCAGCriterionAllureReporter
from utils.logging import Logger
from web.base.base_page import BasePage


def _resolve_link_text(element_html: dict[str, Any]) -> str:
    """Resolve best-available accessible text from extracted fields."""
    for key in (
        "aria_labelledby",
        "aria_label",
        "visible_text",
        "nested_media_text",
        "title_attr",
    ):
        candidate = element_html.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def _resolve_http_destination_url(
    base_url: str,
    href: str | None,
) -> str | None:
    """Resolve a navigable absolute HTTP(S) URL from href."""
    if href is None:
        return None

    normalized_href = href.strip()
    if not normalized_href or normalized_href.startswith("#"):
        return None

    parsed_href = urlparse(normalized_href)
    if parsed_href.scheme and parsed_href.scheme not in {"http", "https"}:
        return None

    resolved_url = urljoin(base_url, normalized_href)
    parsed_resolved = urlparse(resolved_url)
    if parsed_resolved.scheme not in {"http", "https"}:
        return None

    return resolved_url


def _build_destination_summary(snapshot: dict[str, Any]) -> str:
    """Create compact destination summary consumed by the LLM prompt."""
    sections: list[str] = []

    title = snapshot.get("title")
    if isinstance(title, str) and title.strip():
        sections.append(f"Title: {title.strip()}")

    meta_description = snapshot.get("meta_description")
    if isinstance(meta_description, str) and meta_description.strip():
        sections.append(f"Meta description: {meta_description.strip()}")

    headings = snapshot.get("headings")
    if isinstance(headings, list):
        cleaned_headings = [
            heading.strip()
            for heading in headings
            if isinstance(heading, str) and heading.strip()
        ]
        if cleaned_headings:
            sections.append("Headings: " + " | ".join(cleaned_headings[:5]))

    intro_text = snapshot.get("intro_text")
    if isinstance(intro_text, str) and intro_text.strip():
        sections.append(f"Intro text: {intro_text.strip()}")

    body_text_sample = snapshot.get("body_text_sample")
    if isinstance(body_text_sample, str) and body_text_sample.strip():
        sections.append(f"Body sample: {body_text_sample.strip()}")

    return "\n".join(sections)


async def _extract_destination_page_snapshot(
    browser_context: BrowserContext,
    logger: Logger,
    destination_url: str,
) -> dict[str, Any]:
    """Open one destination URL and extract summary metadata."""
    destination_page = await browser_context.new_page()
    extractor_script = r"""
        () => {
            const toCleanText = (value) =>
                (value || "").replace(/\s+/g, " ").trim();
            const headings = Array.from(
                document.querySelectorAll("h1, h2")
            )
                .map((node) => toCleanText(node.textContent))
                .filter(Boolean)
                .slice(0, 5);
            const introParagraphs = Array.from(
                document.querySelectorAll("main p, article p, p")
            )
                .map((node) => toCleanText(node.textContent))
                .filter((text) => text.length >= 40)
                .slice(0, 3);
            const introText = introParagraphs.join(" ").slice(0, 800);
            const bodyTextSample = toCleanText(
                document.body?.textContent || document.body?.innerText
            )
                .slice(0, 600);
            const metaDescription = toCleanText(
                document
                    .querySelector('meta[name="description"]')
                    ?.getAttribute("content")
            );

            return {
                title: toCleanText(document.title),
                meta_description: metaDescription || null,
                headings,
                intro_text: introText || null,
                body_text_sample: bodyTextSample || null,
            };
        }
    """

    try:
        response = await destination_page.goto(
            destination_url,
            wait_until="domcontentloaded",
            timeout=20_000,
        )
        await destination_page.wait_for_load_state(
            "domcontentloaded",
            timeout=20_000,
        )
        snapshot = await destination_page.evaluate(extractor_script)
        summary = _build_destination_summary(snapshot)

        return {
            "status": "LOADED",
            "requested_url": destination_url,
            "final_url": destination_page.url,
            "http_status": response.status if response else None,
            "snapshot": snapshot,
            "summary": summary,
        }
    except PlaywrightTimeoutError as exc:
        logger.warning(
            "Timed out while opening destination URL: %s",
            destination_url,
        )
        return {
            "status": "NAVIGATION_TIMEOUT",
            "requested_url": destination_url,
            "error": str(exc),
        }
    except PlaywrightError as exc:
        logger.warning(
            "Playwright failed while opening destination URL: %s",
            destination_url,
        )
        return {
            "status": "NAVIGATION_ERROR",
            "requested_url": destination_url,
            "error": str(exc),
        }
    finally:
        await destination_page.close()


async def run_criterion_2_4_9(
    page: BasePage,
    evaluator: WCAGEvaluator,
    wcag_criteria: dict[str, Any],
    logger: Logger,
    browser_context: BrowserContext,
    system_prompt: str,
) -> None:
    """Execute WCAG 2.4.9 with destination-page enrichment."""
    criterion_key = "2.4.9"
    wcag_rule = wcag_criteria.get(criterion_key)
    if not isinstance(wcag_rule, dict):
        raise AssertionError(
            f"Criterion '{criterion_key}' is missing in criteria.json."
        )

    rule_name = wcag_rule.get("name") or "Unnamed Criterion"

    with allure.step(f"Evaluate WCAG {criterion_key}: {rule_name}"):
        # Local import avoids import-cycle at module import time.
        from tests.base.wcag.base import get_elements_for_wcag_criterion

        source_elements = await get_elements_for_wcag_criterion(
            page,
            criterion_key,
            wcag_criteria,
            logger,
        )
        source_page_url = page.page.url

        destination_cache: dict[str, dict[str, Any]] = {}
        enriched_elements: list[ExtractedElement] = []
        skipped_links: list[dict[str, Any]] = []

        for source_element in source_elements:
            source_html = source_element.element_html
            source_href = source_html.get("href")
            href_text = (
                source_href.strip() if isinstance(source_href, str) else None
            )
            resolved_url = _resolve_http_destination_url(
                source_page_url,
                href_text,
            )

            if not resolved_url:
                skipped_links.append(
                    {
                        "element_id": source_element.element_id,
                        "href": source_href,
                        "reason": "Unsupported or non-navigable href",
                    }
                )
                continue

            if resolved_url not in destination_cache:
                destination_cache[resolved_url] = (
                    await _extract_destination_page_snapshot(
                        browser_context,
                        logger,
                        resolved_url,
                    )
                )

            destination_data = destination_cache[resolved_url]
            if destination_data.get("status") != "LOADED":
                skipped_links.append(
                    {
                        "element_id": source_element.element_id,
                        "href": source_href,
                        "resolved_url": resolved_url,
                        "reason": destination_data.get("status"),
                        "error": destination_data.get("error"),
                    }
                )
                continue

            snapshot = destination_data.get("snapshot", {})
            summary = destination_data.get("summary")

            link_text = _resolve_link_text(source_html)
            enriched_elements.append(
                ExtractedElement(
                    element_id=source_element.element_id,
                    element_html={
                        "href": source_href,
                        "visible_text": (
                            source_html.get("visible_text")
                            or link_text
                            or source_href
                        ),
                        "source_link_text": link_text or None,
                        "source_href": source_href,
                        "resolved_destination_url": resolved_url,
                        "destination_title": snapshot.get("title"),
                        "destination_meta_description": snapshot.get(
                            "meta_description"
                        ),
                        "destination_headings": snapshot.get("headings"),
                        "destination_intro_text": snapshot.get("intro_text"),
                        "destination_summary": summary,
                    },
                    parent_context=None,
                )
            )

        if skipped_links:
            allure.attach(
                json.dumps(skipped_links, indent=2),
                name="wcag-2.4.9-skipped-links",
                attachment_type=allure.attachment_type.JSON,
            )

        if not enriched_elements:
            if skipped_links:
                raise AssertionError(
                    "WCAG 2.4.9 could not evaluate any links because all "
                    "candidate links were skipped during destination "
                    "enrichment."
                )

            message = (
                "No elements were extracted for criterion "
                f"{criterion_key}. Policy=skip."
            )
            allure.attach(
                message,
                name=f"wcag-{criterion_key}-empty-extraction",
                attachment_type=allure.attachment_type.TEXT,
            )
            return

        request = WCAGEvaluationRequest(
            wcag_rule_id=criterion_key,
            rule_name=str(wcag_rule.get("name") or criterion_key),
            wcag_description=str(wcag_rule.get("description") or ""),
            elements=enriched_elements,
        )

        llm_result = await evaluator.evaluate(
            request=request,
            system_prompt=system_prompt,
            user_prompt=str(wcag_rule["prompt"]),
            chunk_size=5,
        )

        reporter = WCAGCriterionAllureReporter(enriched_elements)
        failures = reporter.report_results(request, llm_result)

        assert_llm_outcome_or_raise(
            criterion_key,
            llm_result,
            failures,
            wcag_rule_id=criterion_key,
        )


__all__ = [
    "run_criterion_2_4_9",
]
