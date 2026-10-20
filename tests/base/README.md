# tests.base — shared test infrastructure

Shared async test stack and reusable WCAG smoke orchestration.

## Modules

- `conftest.py` — canonical async fixture stack and pytest hooks
- `wcag/` — dedicated WCAG package for orchestration and criterion modules

## Purpose

This package centralises framework concerns so that concrete suites stay
focused on target-page flows:

- Playwright lifecycle (session/browser/context/page)
- logging configuration and per-test correlation IDs
- Allure setup and metadata writing
- criteria-driven WCAG extraction and LLM evaluation

The WCAG stack uses a registry-driven orchestration flow:

- typed criterion registry in deterministic order
- criterion-specific execution via declarative configs
- deferred failure aggregation, so all criteria run before the test finally fails
- criterion-specific enrichment modules where needed (2.4.9)

## Async fixture stack

Implemented in `tests/base/conftest.py`:

- `pytest_configure` / `pytest_sessionstart` — hooks for the logging and Allure lifecycle
- `playwright_runtime`, `browser`, `browser_type_launch_args` — session-scoped
- `context` — per test
- `page` — per test
- `test_logger` — per test, correlation-bound logger
- `wcag_criteria` — criteria configuration loader

## Pytest hook behaviour

- `pytest_configure` — sets the Allure output directory from the runtime reporting config.
- `pytest_sessionstart` — prepares Allure directories and writes environment metadata.

## WCAG smoke base behaviour

`tests/base/wcag/base.py` provides:

- consistent Allure naming helpers
- criterion extraction from `src/utils/wcag/criteria.json`
- evaluator creation (`WCAGEvaluator` + `Connector`)
- default criterion sequence (`2.4.4`, `3.1.1`, `3.1.2`)
- optional `2.4.9` specialist runner with target-page enrichment
- per-element Allure evidence and structured failure summaries
- deferred assertion aggregation, so one failing criterion does not stop the others

## Allure layer separation

- `tests/base/conftest.py` — session setup and metadata writing via pytest hooks.
- `tests/base/wcag/reporting.py` — per-element WCAG result evidence.

These layers are deliberately separate and do not duplicate behaviour.

## Recommended pattern (async)

```python
import pytest

from tests.base.wcag import create_wcag_evaluator, run_configured_wcag_criteria
from web.your_app.login import LoginPage  # your own page object

pytestmark = pytest.mark.asyncio


async def test_example(page, context, test_logger, wcag_criteria) -> None:
    login_page = LoginPage(page)
    evaluator = create_wcag_evaluator()
    await login_page.navigate()
    await run_configured_wcag_criteria(
        login_page,
        evaluator,
        wcag_criteria,
        test_logger,
        context,
    )
```

For a full flow with login and the criterion 2.4.9 override, build your own
suite on this pattern (e.g. `tests/<your_app>/test_<page>_smoke.py`).
