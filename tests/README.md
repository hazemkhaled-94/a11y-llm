# tests — test suite

End-to-end accessibility smoke tests for the target application.

## Structure

- `conftest.py` — bridge fixture file; re-exports fixtures from `tests.base.conftest`
- `base/` — shared test infrastructure, async fixture stack, WCAG smoke orchestration
- Add app-specific smoke tests in your own folder (e.g. `<your_app>/`)

## Fixture architecture

The canonical fixture setup is implemented in `tests/base/conftest.py`:

- pytest hooks for logging and Allure session setup
- session-scoped Playwright runtime, browser, and launch-arg fixtures
- per-test context and page fixtures
- per-test logger and WCAG criteria fixtures

`tests/conftest.py` imports all base fixtures, so every suite gets the same runtime stack.

## Collection rule

There is no class-inheritance gate in the active fixture stack.
The current suite is function-based and asynchronous.

## Test entry points

- `tests/<your_app>/test_<page>_smoke.py` — example path for your own app-specific smoke test (browser + LLM required)

## Unit tests (no browser, no LLM)

- `tests/base/wcag/test_repository.py`
- `tests/base/wcag/test_empty_extraction_behavior.py`
- `tests/llm/test_wcag_evaluator_parse.py`

## WCAG architecture overview

`tests/base/wcag/` is the dedicated WCAG package.

`tests/base/wcag/base.py` is the orchestration layer.

Criterion-specific behaviour is implemented under `tests/base/wcag/criteria/`.

Specialised behaviour is delegated to focused helper modules:

- `tests/base/wcag/types.py` — immutable data contracts and criterion config typing
- `tests/base/wcag/reporting.py` — element-level Allure rendering and failure collection
- `tests/base/wcag/criteria/wcag_2_4_9.py` — cohesive 2.4.9 extraction, enrichment, and evaluation flow
