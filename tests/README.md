# tests package

Test suite for end-to-end accessibility smoke checks.

## Structure

- `conftest.py`
  - bridge fixture file
  - re-exports fixtures from `tests.base.conftest`
- `base/`
  - shared test model, async fixture stack, WCAG smoke orchestration, managers
  - dedicated `wcag/` package with criterion-specific modules

## Fixture architecture

The canonical fixture setup is implemented in `tests/base/conftest.py`:

- pytest hooks for logging and Allure session setup
- session browser launch args configuration
- per-test context fixture
- per-test page fixture (provided by pytest-playwright-asyncio)
- per-test logger and WCAG criteria fixtures

`tests/conftest.py` imports all base fixtures so every suite gets the same runtime stack.

## Collection rule

There is no class-inheritance collection gate in the active fixture stack.
The current suite is function-based and async.

## Main test entry points

- `tests/base/test_mars_smoke.py`

## WCAG architecture overview

`tests/base/wcag/` is the dedicated WCAG package.

`tests/base/wcag/base.py` is the orchestration layer.

Criterion-specific behavior is implemented under `tests/base/wcag/criteria/`.

Specialized behavior is delegated to focused helper modules:

- `tests/base/wcag/types.py`
  - immutable data contracts and criterion config typing
- `tests/base/wcag/reporting.py`
  - element-level Allure rendering and failure collection
- `tests/base/wcag/criteria/wcag_2_4_9.py`
  - cohesive 2.4.9 extraction, destination enrichment, and evaluation flow
