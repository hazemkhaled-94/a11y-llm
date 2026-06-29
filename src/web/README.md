# web — Namespace-Package

Page-Object-Schicht für die P20-Zielanwendung.

## Struktur

- `base/` — wiederverwendbare Page-Object-Basisklasse
- `p20/` — Page Objects für P20 (Login-Flow, Sucheingabe)

## Packaging-Hinweis

`web` ist ein implizites Namespace-Package (kein `web/__init__.py`).
Möglich, weil `src` in pytest-Config als `pythonpath` eingetragen ist.

## Gemeinsames Verhalten (BasePage)

`web.base.base_page.BasePage` stellt bereit:

- `navigate()` — Navigation mit Timeout-Behandlung und Logging
- `wait_for_page_load()` — wartet auf `domcontentloaded`
- `extract_elements_by_locator()` — Element-Extraktion per Selektor
- `extract_element_data()` — JS-Evaluator-Helfer pro Element
- `run_axe_audit()` — Platzhalter-Hook (gibt derzeit `{}` zurück)

## Unterpackage-Dokumentation

- [src/web/base/README.md](base/README.md)
- [src/web/p20/README.md](p20/README.md)
