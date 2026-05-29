# tests.base package

Shared async test infrastructure and reusable WCAG smoke orchestration.

## Modules

- `conftest.py`: canonical async fixture stack and pytest hooks
- `wcag/`: dedicated WCAG package for orchestration and criterion modules

## Purpose

This package centralizes framework concerns so concrete suites stay focused on target page flows:

- Playwright lifecycle (session/browser/context/page)
- logging configuration and per-test correlation IDs
- Allure setup and metadata writing
- criterion-driven WCAG extraction and LLM evaluation

The WCAG stack uses a context-driven orchestration flow:

- one shared audit context object per test
- criterion-specific execution through declarative configs
- delayed failure aggregation so all criteria run before final fail
- criterion-specific enrichment modules where needed (2.4.9)

Criterion-specific behavior (for example WCAG 2.4.9) lives in
`tests/base/wcag/criteria/`.

## Async fixture stack

Implemented in `tests/base/conftest.py`:

- `pytest_configure` / `pytest_sessionstart` hooks for logging and Allure lifecycle setup
- `browser_type_launch_args` (session)
- `context` (per test)
- `page` (provided by pytest-playwright-asyncio)
- `test_logger` (per test correlation-scoped logger)
- `wcag_criteria` (criteria configuration loader)

## Pytest hook behavior

- `pytest_configure`: automatically sets Allure output dir from runtime reporting config when Allure is enabled.
- `pytest_sessionstart`: prepares Allure directories and writes environment metadata.

## WCAG smoke base behavior

`tests/base/wcag/base.py` provides:

- unified Allure naming helpers
- criterion extraction from `src/utils/wcag/criteria.json`
- evaluator creation (`WCAGEvaluator` + `Connector`)
- default criterion sequence (`2.4.4`, `3.1.1`, `3.1.2`)
- optional `2.4.9` specialized runner with destination-page enrichment
- per-element Allure evidence and structured failure summaries
- delayed assertion aggregation so one failing criterion does not stop remaining criteria

Execution internals are intentionally concentrated in `base.py` to reduce deep call chains.

## Allure layer separation

- `tests/base/conftest.py` handles session setup and metadata writing via pytest hooks.
- `tests/base/wcag/reporting.py` handles per-element WCAG result evidence.

These layers are intentionally separate and do not duplicate behavior.

## Recommended pattern (async)

```python
import pytest

from tests.base.wcag import create_wcag_evaluator
from tests.base.wcag import run_configured_wcag_criteria
from web.mars import MarsDemoPage

pytestmark = pytest.mark.asyncio


async def test_example(page, context, test_logger, wcag_criteria) -> None:
    page_obj = MarsDemoPage(page)
    evaluator = create_wcag_evaluator()
    await page_obj.open()
    await run_configured_wcag_criteria(
        page_obj,
        evaluator,
        wcag_criteria,
        test_logger,
        context,
    )
```
