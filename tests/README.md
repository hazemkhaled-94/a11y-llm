# tests — Test-Suite

End-to-End-Barrierefreiheits-Smoke-Tests für P20.

## Struktur

- `conftest.py` — Bridge-Fixture-Datei; re-exportiert Fixtures aus `tests.base.conftest`
- `base/` — geteilte Test-Infrastruktur, async Fixture-Stack, WCAG-Smoke-Orchestrierung
- `p20/` — P20-spezifische Smoke-Tests

## Fixture-Architektur

Die kanonische Fixture-Einrichtung ist in `tests/base/conftest.py` implementiert:

- pytest-Hooks für Logging- und Allure-Session-Setup
- Session-scoped Playwright-Runtime, Browser und Launch-Arg-Fixtures
- Per-Test Kontext- und Page-Fixtures
- Per-Test Logger und WCAG-Kriterien-Fixtures

`tests/conftest.py` importiert alle Base-Fixtures, sodass jede Suite denselben Runtime-Stack erhält.

## Kollektionsregel

Es gibt kein Klassen-Vererbungs-Gate im aktiven Fixture-Stack.
Die aktuelle Suite ist funktionsbasiert und asynchron.

## Test-Einstiegspunkte

- `tests/p20/test_searchinput_smoke.py` — P20-Smoke-Test (Browser + LLM erforderlich)

## Unit-Tests (kein Browser, kein LLM)

- `tests/base/wcag/test_repository.py`
- `tests/base/wcag/test_empty_extraction_behavior.py`
- `tests/llm/test_wcag_evaluator_parse.py`

## WCAG-Architektur-Überblick

`tests/base/wcag/` ist das dedizierte WCAG-Package.

`tests/base/wcag/base.py` ist die Orchestrierungsschicht.

Kriterienspezifisches Verhalten ist unter `tests/base/wcag/criteria/` implementiert.

Spezialisiertes Verhalten wird an fokussierte Hilfsmodule delegiert:

- `tests/base/wcag/types.py` — unveränderliche Datenverträge und Kriterium-Config-Typisierung
- `tests/base/wcag/reporting.py` — element-level Allure-Rendering und Fehlersammlung
- `tests/base/wcag/criteria/wcag_2_4_9.py` — kohäsiver 2.4.9-Extraktions-, Anreicherungs- und Bewertungsfluss
