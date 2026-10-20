# web — namespace package

Page-object layer for the target application.

## Structure

- `base/` — reusable page-object base class
- Add app-specific page objects in your own subpackage (e.g. `<your_app>/` with a login flow or search input)

## Packaging note

`web` is an implicit namespace package (no `web/__init__.py`).
This works because `src` is listed as a `pythonpath` in the pytest config.

## Shared behaviour (BasePage)

`web.base.base_page.BasePage` provides:

- `navigate()` — navigation with timeout handling and logging
- `wait_for_page_load()` — waits for `domcontentloaded`
- `extract_elements_by_locator()` — element extraction by selector
- `extract_element_data()` — per-element JS evaluator helper
- `run_axe_audit()` — placeholder hook (currently returns `{}`)

## Subpackage documentation

- [src/web/base/README.md](base/README.md)
