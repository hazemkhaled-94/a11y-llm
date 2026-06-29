# a11y-llm — Barrierefreiheits-Audit für P20

Automatisiertes Framework zur WCAG-Prüfung der P20-Anwendung.  
Es kombiniert Browser-Automatisierung, konfigurierbare WCAG-Regeln und KI-gestützte Bewertung zu einem revisionsfähigen Testprozess mit strukturierten Nachweisen.

---

## Für wen ist diese Dokumentation?

Wählen Sie Ihren Einstieg je nach Rolle — kein Dokument ist länger als nötig:

| Ich bin ... | Mein Einstieg |
|---|---|
| **Manager / Projektverantwortliche** — ich möchte verstehen, worum es geht, welchen Nutzen es bringt und was der aktuelle Status ist | [Managementübersicht →](documentation/MANAGEMENT.md) |
| **Anwender** — ich möchte die Tests einrichten und gegen P20 ausführen | [Benutzerhandbuch →](documentation/BENUTZERHANDBUCH.md) |
| **Entwickler** — ich möchte den Code verstehen, erweitern oder neue Seiten/Kriterien ergänzen | [Entwicklerhandbuch →](documentation/ENTWICKLERHANDBUCH.md) |

---

## Was macht dieses Projekt?

Das Framework prüft die P20-Anwendung automatisiert auf die Einhaltung der
[WCAG-Richtlinien](https://www.w3.org/WAI/WCAG22/quickref/) (Web Content
Accessibility Guidelines). Es öffnet Seiten im Browser, extrahiert die für
jedes Kriterium relevanten DOM-Elemente, bewertet sie mit einem KI-Modell und
erzeugt strukturierte Testnachweise als Allure-Report und Log-Dateien.

**Aktuell geprüfte WCAG-Kriterien:**

| Kriterium | Bezeichnung | Stufe |
|---|---|---|
| 2.4.4 | Linkzweck (im Kontext) | A |
| 2.4.9 | Linkzweck (nur Link) | AAA |
| 3.1.1 | Sprache der Seite | A |
| 3.1.2 | Sprache von Teilen | AA |

---

## Schnellstart (für Erfahrene)

> Die vollständige Schritt-für-Schritt-Anleitung steht im
> [Benutzerhandbuch](documentation/BENUTZERHANDBUCH.md).

**Voraussetzungen:** Python 3.12–3.13, Poetry, Allure CLI

```bash
# 1. Abhängigkeiten installieren
poetry install
poetry run playwright install chromium

# 2. Umgebung konfigurieren
cp .env.example .env
# .env befüllen — mindestens:
#   AUDITOR_LLM_API_KEY, AUDITOR_LLM_MODEL, AUDITOR_LLM_URL
#   P20_USERNAME, P20_PASSWORD

# 3. P20-Smoke-Test ausführen
poetry run pytest tests/p20/test_searchinput_smoke.py -vv -rs

# 4. Allure-Report anzeigen
allure serve allure/results
```

---

## Projektstatus

Pre-production — technisches Fundament vollständig, vier WCAG-Kriterien aktiv.

Nächste Schritte: fachliche Skalierung auf weitere Kriterien, CI/CD-Integration,
Fertigstellung der klassischen Axe-Audit-Integration.

Details im [Entwicklerhandbuch](documentation/ENTWICKLERHANDBUCH.md) und in
der [Managementübersicht](documentation/MANAGEMENT.md).

---

## Dokumentationsübersicht

| Dokument | Zielgruppe | Sprache |
|---|---|---|
| [documentation/MANAGEMENT.md](documentation/MANAGEMENT.md) | Management, Projektverantwortliche | Deutsch |
| [documentation/BENUTZERHANDBUCH.md](documentation/BENUTZERHANDBUCH.md) | Anwender, QA, DevOps | Deutsch |
| [documentation/ENTWICKLERHANDBUCH.md](documentation/ENTWICKLERHANDBUCH.md) | Entwickler | Deutsch |
