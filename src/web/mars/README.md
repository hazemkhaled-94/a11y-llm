# web.mars package

Page object for the Deque University Mars demo target.

## Modules

- `mars_demo_page.py`

## Class: `MarsDemoPage`

Inherits from `web.base.base_page.BasePage`.

Current constants:

- `PAGE_URL = "https://dequeuniversity.com/demo/mars/"`
- `READY_SELECTOR = "body"`
- `READY_TIMEOUT_MS = 10_000`

### Method: `open()`

Flow:

1. Calls inherited `navigate()`.
2. Waits for first `body` locator to be visible.
3. Raises `TimeoutError` if readiness timeout is exceeded.
4. Returns `MarsDemoPage` for fluent chaining.

## Test usage

Used by:

- `tests/base/test_mars_smoke.py`
