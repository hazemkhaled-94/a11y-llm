# web namespace package

Page object layer for target web applications used in accessibility smoke tests.

## Structure

- `base`: reusable page object base class
- `mars`: page object for the Deque University Mars demo

## Packaging note

`web` is an implicit namespace package (no `web/__init__.py`).
This works because `src` is added to `PYTHONPATH` in pytest config (`pythonpath = ["src"]`).

## Base behavior shared by all targets

`web.base.base_page.BasePage` provides:

- `navigate()` with timeout handling and logging
- `wait_for_page_load()` (`domcontentloaded`)
- element extraction by selector
- element JS evaluation helper
- `run_axe_audit()` placeholder hook (currently returns empty dict)

## Subpackage docs

- `src/web/base/README.md`
- `src/web/mars/README.md`
