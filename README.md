# a11y-llm — LLM-assisted accessibility audits

Automated framework for WCAG testing of web applications.  
It combines browser automation, configurable WCAG rules, and AI-assisted evaluation into an auditable test process with structured evidence.

---

## Who is this documentation for?

Pick your starting point based on your role — no document is longer than it needs to be:

| I am ... | Start here |
|---|---|
| **Manager / project owner** — I want to understand what this is about, what value it brings, and what the current status is | [Management Overview →](documentation/MANAGEMENT.md) |
| **User** — I want to set up the tests and run them against my target application | [User Guide →](documentation/USER_GUIDE.md) |
| **Developer** — I want to understand or extend the code, or add new pages/criteria | [Developer Guide →](documentation/DEVELOPER_GUIDE.md) |

---

## What does this project do?

The framework automatically checks a target web application for compliance with the
[WCAG guidelines](https://www.w3.org/WAI/WCAG22/quickref/) (Web Content
Accessibility Guidelines). It opens pages in the browser, extracts the DOM
elements relevant to each criterion, evaluates them with an AI model, and
produces structured test evidence as an Allure report and log files.

**Currently checked WCAG criteria:**

| Criterion | Name | Level |
|---|---|---|
| 2.4.4 | Link Purpose (In Context) | A |
| 2.4.9 | Link Purpose (Link Only) | AAA |
| 3.1.1 | Language of Page | A |
| 3.1.2 | Language of Parts | AA |

---

## Quick start (for experienced users)

> The complete step-by-step guide is in the
> [User Guide](documentation/USER_GUIDE.md).

**Prerequisites:** Python 3.12–3.13, Poetry, Allure CLI

```bash
# 1. Install dependencies
poetry install
poetry run playwright install chromium

# 2. Configure the environment
cp .env.example .env
# Fill in .env — at minimum:
#   AUDITOR_LLM_API_KEY, AUDITOR_LLM_MODEL, AUDITOR_LLM_URL

# 3. Run the unit tests (no browser or LLM required)
poetry run pytest tests/base/wcag/ tests/llm/ -vv -rs

# 4. Run your own app-specific smoke test (example path, see the Developer Guide)
poetry run pytest tests/<your_app>/test_<page>_smoke.py -vv -rs

# 5. View the Allure report
allure serve allure/results
```

---

## Project status

Pre-production — technical foundation complete, four WCAG criteria active.

Next steps: scaling to further criteria, CI/CD integration, and completing the
classic axe audit integration.

Details in the [Developer Guide](documentation/DEVELOPER_GUIDE.md) and the
[Management Overview](documentation/MANAGEMENT.md).

---

## Documentation overview

| Document | Audience | Language |
|---|---|---|
| [documentation/MANAGEMENT.md](documentation/MANAGEMENT.md) | Management, project owners | English |
| [documentation/USER_GUIDE.md](documentation/USER_GUIDE.md) | Users, QA, DevOps | English |
| [documentation/DEVELOPER_GUIDE.md](documentation/DEVELOPER_GUIDE.md) | Developers | English |
