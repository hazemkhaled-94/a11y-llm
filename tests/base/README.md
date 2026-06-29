# tests.base — Gemeinsame Test-Infrastruktur

Geteilter async Test-Stack und wiederverwendbare WCAG-Smoke-Orchestrierung.

## Module

- `conftest.py` — kanonischer async Fixture-Stack und pytest-Hooks
- `wcag/` — dediziertes WCAG-Package für Orchestrierung und Kriterium-Module

## Zweck

Dieses Package zentralisiert Framework-Belange, sodass konkrete Suites auf
Zielseiten-Flows fokussiert bleiben:

- Playwright-Lebenszyklus (Session/Browser/Kontext/Page)
- Logging-Konfiguration und per-Test-Korrelations-IDs
- Allure-Setup und Metadaten-Schreiben
- Kriteriengetriebene WCAG-Extraktion und LLM-Bewertung

Der WCAG-Stack nutzt einen registry-getriebenen Orchestrierungsfluss:

- typisierte Kriterium-Registry in deterministischer Reihenfolge
- kriterienspezifische Ausführung über deklarative Configs
- verzögerte Fehleraggregation, sodass alle Kriterien laufen bevor final fehlgeschlagen wird
- kriterienspezifische Anreicherungsmodule wo nötig (2.4.9)

## Async Fixture-Stack

Implementiert in `tests/base/conftest.py`:

- `pytest_configure` / `pytest_sessionstart` — Hooks für Logging- und Allure-Lebenszyklus
- `playwright_runtime`, `browser`, `browser_type_launch_args` — session-scoped
- `context` — per Test
- `page` — per Test
- `test_logger` — per Test, korrelationsgebundener Logger
- `wcag_criteria` — Kriterien-Konfigurationsloader

## Pytest-Hook-Verhalten

- `pytest_configure` — setzt Allure-Ausgabeverzeichnis aus Laufzeit-Reporting-Config.
- `pytest_sessionstart` — bereitet Allure-Verzeichnisse vor und schreibt Umgebungsmetadaten.

## WCAG-Smoke-Basisverhalten

`tests/base/wcag/base.py` stellt bereit:

- einheitliche Allure-Namens-Helfer
- Kriterium-Extraktion aus `src/utils/wcag/criteria.json`
- Evaluator-Erstellung (`WCAGEvaluator` + `Connector`)
- Standard-Kriterium-Sequenz (`2.4.4`, `3.1.1`, `3.1.2`)
- optionaler `2.4.9`-Spezialist-Runner mit Zielseiten-Anreicherung
- per-Element Allure-Evidenz und strukturierte Fehlerzusammenfassungen
- verzögerte Assertion-Aggregation, sodass ein fehlgeschlagenes Kriterium die anderen nicht stoppt

## Allure-Schichttrennung

- `tests/base/conftest.py` — Session-Setup und Metadaten-Schreiben via pytest-Hooks.
- `tests/base/wcag/reporting.py` — per-Element WCAG-Ergebnis-Evidenz.

Diese Schichten sind bewusst getrennt und duplizieren kein Verhalten.

## Empfohlenes Muster (async)

```python
import pytest

from tests.base.wcag import create_wcag_evaluator, run_configured_wcag_criteria
from web.p20.login import LoginPage

pytestmark = pytest.mark.asyncio


async def test_beispiel(page, context, test_logger, wcag_criteria) -> None:
    seite = LoginPage(page)
    evaluator = create_wcag_evaluator()
    await seite.navigate()
    await run_configured_wcag_criteria(
        seite,
        evaluator,
        wcag_criteria,
        test_logger,
        context,
    )
```

Für den vollständigen P20-Flow mit Login und Kriterium-2.4.9-Override
siehe `tests/p20/test_searchinput_smoke.py`.
