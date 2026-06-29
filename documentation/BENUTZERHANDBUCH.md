# Benutzerhandbuch — a11y-llm

**Zielgruppe:** Anwender, QA-Ingenieure, DevOps

Dieses Handbuch führt Sie Schritt für Schritt von der Installation bis zum
fertigen Allure-Report. Sie brauchen keine tiefen Programmierkenntnisse —
folgen Sie einfach den Abschnitten in der angegebenen Reihenfolge.

---

## Inhaltsverzeichnis

1. [Voraussetzungen](#1-voraussetzungen)
2. [Installation](#2-installation)
3. [Konfiguration](#3-konfiguration)
4. [Tests ausführen](#4-tests-ausführen)
5. [Allure-Report anzeigen](#5-allure-report-anzeigen)
6. [Nur Unit-Tests ausführen (ohne Browser und LLM)](#6-nur-unit-tests-ausführen)
7. [Qualitätsprüfungen](#7-qualitätsprüfungen)
8. [Häufige Probleme](#8-häufige-probleme)

---

## 1. Voraussetzungen

Stellen Sie sicher, dass folgende Software installiert ist, bevor Sie
beginnen:

| Software | Version | Zweck |
| --- | --- | --- |
| Python | 3.12 oder 3.13 | Laufzeitumgebung |
| [Poetry](https://python-poetry.org/docs/#installation) | aktuell | Abhängigkeitsverwaltung |
| [Allure CLI](https://allurereport.org/docs/install/) | aktuell | Report-Anzeige |

Außerdem benötigen Sie:

- **LLM-Zugangsdaten:** API-Key, Modellname und Endpunkt-URL für das
  KI-Modell (wird vom Projektverantwortlichen bereitgestellt).
- **P20-Zugangsdaten:** Benutzername und Passwort für die P20-Testumgebung.

---

## 2. Installation

Führen Sie folgende Befehle im Projektverzeichnis aus:

```bash
# Schritt 1: Python-Abhängigkeiten installieren
poetry install

# Schritt 2: Chromium-Browser für Playwright installieren
poetry run playwright install chromium
```

> **Tipp:** Alle Befehle in diesem Handbuch müssen im Wurzelverzeichnis des
> Projekts ausgeführt werden (dort wo `pyproject.toml` liegt).

---

## 3. Konfiguration

Das Framework liest seine Einstellungen aus einer `.env`-Datei im
Projektwurzelverzeichnis.

### 3.1 .env-Datei erstellen

```bash
cp .env.example .env
```

### 3.2 .env-Datei befüllen

Öffnen Sie `.env` in einem Texteditor und setzen Sie mindestens diese Werte:

```bash
# LLM-Zugangsdaten (Pflichtfelder — ohne diese startet das Framework nicht)
AUDITOR_LLM_API_KEY=ihr-api-schluessel
AUDITOR_LLM_MODEL=ihr-modellname
AUDITOR_LLM_URL=https://ihr-llm-endpunkt/v1

# P20-Zugangsdaten (Pflichtfelder für den P20-Smoke-Test)
P20_USERNAME=ihr-benutzername
P20_PASSWORD=ihr-passwort
```

Alle anderen Variablen haben sinnvolle Standardwerte und müssen nicht
geändert werden. Die vollständige Variablenreferenz finden Sie in
[Abschnitt 3.3](#33-vollständige-variablenreferenz).

> **Sicherheitshinweis:** Die `.env`-Datei enthält Zugangsdaten und ist
> git-ignoriert — sie wird nie ins Repository eingecheckt. Teilen Sie den
> Inhalt nicht per E-Mail oder Chat.

### 3.3 Vollständige Variablenreferenz

<details>
<summary>Alle verfügbaren Umgebungsvariablen anzeigen</summary>

| Variable | Standard | Pflicht | Beschreibung |
| --- | --- | --- | --- |
| `AUDITOR_LLM_API_KEY` | — | **Ja** | API-Schlüssel für den LLM-Endpunkt |
| `AUDITOR_LLM_MODEL` | — | **Ja** | Modellname/-bezeichner |
| `AUDITOR_LLM_URL` | — | **Ja** | Basis-URL des LLM-Providers |
| `P20_USERNAME` | — | Für P20-Test | P20-Benutzername |
| `P20_PASSWORD` | — | Für P20-Test | P20-Passwort |
| `PROJECT_ROOT_DIR` | `.` | Nein | Wurzelverzeichnis für Log- und Allure-Pfade |
| `LOG_LEVEL` | `INFO` | Nein | Logging-Stufe (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_FORMAT` | `json` | Nein | Ausgabeformat: `json` oder `text` |
| `LOG_SINK` | `stdout` | Nein | Ausgabeort: `stdout`, `file` oder `both` |
| `LOG_ROOT_DIR` | `logs` | Nein | Log-Verzeichnis (bei `file`/`both`) |
| `LOG_FILE` | `a11y-llm.log` | Nein | Log-Dateiname |
| `ALLURE_ENABLED` | `true` | Nein | Allure-Ergebnisse schreiben |
| `ALLURE_ROOT_DIR` | `allure` | Nein | Allure-Wurzelverzeichnis |
| `ALLURE_RESULTS_SUBDIR` | `results` | Nein | Unterverzeichnis für Rohdaten |
| `ALLURE_CLEAN_RESULTS` | `false` | Nein | Rohdaten vor jedem Lauf löschen |
| `PW_HEADLESS` | `true` | Nein | Browser ohne sichtbares Fenster starten |
| `PW_SLOW_MO_MS` | `0` | Nein | Verzögerung zwischen Aktionen in ms |
| `PW_LAUNCH_TIMEOUT_MS` | `30000` | Nein | Browser-Start-Timeout in ms |
| `PW_ACTION_TIMEOUT_MS` | `10000` | Nein | Aktions-Timeout in ms |
| `PW_NAVIGATION_TIMEOUT_MS` | `20000` | Nein | Navigations-Timeout in ms |
| `PW_IGNORE_HTTPS_ERRORS` | `true` | Nein | TLS-Fehler ignorieren (für Testumgebungen) |

</details>

---

## 4. Tests ausführen

### 4.1 P20-Smoke-Test (Haupttest)

Führt den vollständigen Barrierefreiheits-Smoke-Test gegen die
P20-Testumgebung aus. Erfordert Browser, LLM und P20-Zugangsdaten.

```bash
poetry run pytest tests/p20/test_searchinput_smoke.py -vv -rs
```

**Was passiert dabei:**

1. Der Browser öffnet die P20-Login-Seite.
2. Anmeldung mit den konfigurierten Zugangsdaten.
3. Nach dem Login werden alle vier WCAG-Kriterien (2.4.4, 2.4.9, 3.1.1, 3.1.2) geprüft.
4. Ergebnisse werden in `allure/results/` geschrieben.
5. Der Test endet mit BESTANDEN oder NICHT BESTANDEN plus einer
   strukturierten Zusammenfassung aller Befunde.

**Typische Ausgabe bei einem Fehlschlag:**

```
FAILED tests/p20/test_searchinput_smoke.py::test_p20_search_input_page_a11y
  Criterion 2.4.4 — 3 elements failed:
    element-id-1: FAIL — Linktext "hier klicken" gibt keinen Hinweis auf das Ziel
    ...
```

### 4.2 Alle Tests ausführen

Führt sowohl den P20-Smoke-Test als auch alle Unit-Tests aus:

```bash
poetry run pytest -vv -rs
```

### 4.3 Nur bestimmte Tests ausführen

```bash
# Nur den P20-Test
poetry run pytest tests/p20/ -vv -rs

# Nur Unit-Tests (kein Browser, kein LLM, keine Zugangsdaten nötig)
poetry run pytest tests/base/wcag/test_repository.py tests/base/wcag/test_empty_extraction_behavior.py tests/llm/test_wcag_evaluator_parse.py -vv
```

---

## 5. Allure-Report anzeigen

Der Report wird automatisch in `allure/results/` geschrieben, wenn
`ALLURE_ENABLED=true` gesetzt ist (Standardwert).

### 5.1 Live-Report im Browser öffnen

```bash
allure serve allure/results
```

Öffnet automatisch den Browser mit dem interaktiven Report.

### 5.2 Statischen Report generieren

```bash
allure generate allure/results -o allure/report --clean
```

Der statische Report liegt danach in `allure/report/` und kann ohne
Allure CLI betrachtet oder weitergegeben werden.

> **Wichtig:** Führen Sie Allure-Befehle immer aus dem Projektwurzelverzeichnis
> aus, damit der Pfad `allure/results` korrekt aufgelöst wird.

### 5.3 Was zeigt der Report?

- **Übersichtsseite:** Testlauf-Zusammenfassung mit Bestanden/Fehlgeschlagen.
- **Test-Detail:** Ablauf des Tests Schritt für Schritt.
- **Element-Evidenz:** Für jedes geprüfte Element: Selektor, extrahierter
  Inhalt, KI-Bewertung, Status.
- **Screenshot:** Vollseiten-Screenshot der P20-Seite zum Zeitpunkt der Prüfung.

---

## 6. Nur Unit-Tests ausführen

Unit-Tests benötigen keinen Browser, keine LLM-Zugangsdaten und keine
P20-Verbindung. Sie eignen sich für schnelle Überprüfungen und CI-Pipelines
ohne Netzwerkzugriff:

```bash
poetry run pytest \
  tests/base/wcag/test_repository.py \
  tests/base/wcag/test_empty_extraction_behavior.py \
  tests/llm/test_wcag_evaluator_parse.py \
  -vv
```

Diese Tests prüfen:

- Laden der WCAG-Kriterien-Konfiguration.
- Verhalten bei leerer DOM-Extraktion.
- Parsen und Validierung von LLM-Antworten.

---

## 7. Qualitätsprüfungen

Vor dem Einchecken von Codeänderungen sollten diese Prüfungen durchlaufen:

```bash
# Code-Stil und Lint
poetry run ruff check src tests

# Formatierung prüfen (mit 'ruff format src tests' anwenden)
poetry run ruff format --check src tests

# Statische Typprüfung
poetry run mypy src tests

# WCAG-Konfigurationsdatei validieren
python -m json.tool src/utils/wcag/criteria.json > /dev/null
```

**Git-Hooks (optional, empfohlen):**

Die Prüfungen können als automatische Git-Hooks eingerichtet werden, sodass
sie vor jedem Commit ausgeführt werden:

```bash
poetry run pre-commit install
```

---

## 8. Häufige Probleme

### Problem: "LLM API key is missing"

**Ursache:** Die Datei `.env` wurde nicht erstellt oder `AUDITOR_LLM_API_KEY`
ist leer.

**Lösung:**
```bash
cp .env.example .env
# .env mit echten Werten befüllen
```

---

### Problem: P20-Test wird übersprungen (SKIPPED)

**Ursache:** `P20_USERNAME` oder `P20_PASSWORD` sind nicht in `.env` gesetzt.

**Lösung:** Beide Variablen in `.env` setzen:
```bash
P20_USERNAME=mein-benutzername
P20_PASSWORD=mein-passwort
```

---

### Problem: "Executable doesn't exist" (Playwright)

**Ursache:** Chromium wurde noch nicht installiert.

**Lösung:**
```bash
poetry run playwright install chromium
```

---

### Problem: Allure-Report ist leer oder nicht aktuell

**Ursache:** `ALLURE_ENABLED` ist auf `false` gesetzt oder der Report wurde
vor dem Test generiert.

**Lösung:** Sicherstellen, dass `ALLURE_ENABLED=true` in `.env` steht und
den Report erst **nach** dem Testlauf generieren.

---

### Problem: Browser-Timeout beim Seitenaufruf

**Ursache:** Die P20-Testumgebung ist nicht erreichbar oder braucht länger als
erwartet.

**Lösung:** Timeout-Werte in `.env` erhöhen:
```bash
PW_NAVIGATION_TIMEOUT_MS=60000
PW_ACTION_TIMEOUT_MS=30000
```

---

### Logs lesen

Wenn ein Problem unklar ist, helfen die Logs weiter. Format auf
`text` setzen für bessere Lesbarkeit:

```bash
LOG_FORMAT=text LOG_SINK=both poetry run pytest tests/p20/ -vv -rs
```

Logs erscheinen dann auf der Konsole und in `logs/a11y-llm.log`.
