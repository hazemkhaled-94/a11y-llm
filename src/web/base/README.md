# web.base package

Shared page-object foundation for all target sites.

## Module

- `base_page.py`

## Class: `BasePage`

Core attributes:

- `PAGE_URL` default `""` (must be overridden by concrete page object)
- `NAVIGATION_TIMEOUT_MS` default `20_000`
- `PAGE_LOAD_TIMEOUT_MS` default `15_000`

### Key methods

- `navigate()`
  - requires `PAGE_URL` to be set
  - calls `page.goto(..., wait_until="domcontentloaded")`
  - raises `TimeoutError` on Playwright navigation timeout

- `wait_for_page_load()`
  - waits for `domcontentloaded` with configured timeout

- `extract_elements_by_locator(selector)`
  - returns all elements matching CSS/XPath selector

- `extract_element_data(locator, js_extractor)`
  - executes provided JS extractor function string on locator element via `locator.evaluate`

- `run_axe_audit(context_name=None)`
  - currently stubbed and returns `{}`
  - used by tests for Allure attachment pipeline compatibility

## Logging

Each page object instance initializes `self.logger` using `utils.logging.get_logger`.
