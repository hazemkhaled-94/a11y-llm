# User Guide — a11y-llm

**Audience:** Users, QA engineers, DevOps

This guide takes you step by step from installation to a finished Allure
report. You don't need in-depth programming knowledge — just follow the
sections in the order given.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [Running tests](#4-running-tests)
5. [Viewing the Allure report](#5-viewing-the-allure-report)
6. [Running unit tests only (no browser or LLM)](#6-running-unit-tests-only)
7. [Quality checks](#7-quality-checks)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Prerequisites

Make sure the following software is installed before you start:

| Software | Version | Purpose |
| --- | --- | --- |
| Python | 3.12 or 3.13 | Runtime environment |
| [Poetry](https://python-poetry.org/docs/#installation) | latest | Dependency management |
| [Allure CLI](https://allurereport.org/docs/install/) | latest | Viewing reports |

You will also need:

- **LLM credentials:** API key, model name, and endpoint URL for the AI
  model (from your LLM provider or project administrator).
- **Access to the application under test:** a reachable instance of the
  target application (for example a test environment) and, if your smoke
  suite logs in, test credentials for it.

---

## 2. Installation

Run the following commands in the project directory:

```bash
# Step 1: Install Python dependencies
poetry install

# Step 2: Install the Chromium browser for Playwright
poetry run playwright install chromium
```

> **Tip:** All commands in this guide must be run from the project root
> directory (where `pyproject.toml` is located).

---

## 3. Configuration

The framework reads its settings from a `.env` file in the project root
directory.

### 3.1 Create the .env file

```bash
cp .env.example .env
```

### 3.2 Fill in the .env file

Open `.env` in a text editor and set at least these values:

```bash
# LLM credentials (required — the framework will not start without them)
AUDITOR_LLM_API_KEY=your-api-key
AUDITOR_LLM_MODEL=your-model-name
AUDITOR_LLM_URL=https://your-llm-endpoint/v1
```

All other variables have sensible defaults and do not need to be changed.
You can find the full variable reference in
[section 3.3](#33-complete-variable-reference).

**App-specific credentials (optional):** If your own smoke suite logs in to
the application under test, it can read credentials from environment
variables such as `APP_USERNAME` and `APP_PASSWORD`. These are example names:
the framework does not read them and they are not part of `.env.example`.
Note that the framework loads values from `.env` only for the variables
declared in `src/utils/core/environment.py`. For any other variable, either
declare it there or export it in your shell before running pytest.

> **Security note:** The `.env` file contains credentials and is
> git-ignored — it is never committed to the repository. Do not share its
> contents by email or chat.

### 3.3 Complete variable reference

<details>
<summary>Show all available environment variables</summary>

| Variable | Default | Required | Description |
| --- | --- | --- | --- |
| `AUDITOR_LLM_API_KEY` | — | **Yes** | API key for the LLM endpoint |
| `AUDITOR_LLM_MODEL` | — | **Yes** | Model name/identifier |
| `AUDITOR_LLM_URL` | — | **Yes** | Base URL of the LLM provider |
| `APP_USERNAME` | — | Only if your suite reads it | Example: username for the application under test, read by your own smoke suite (not by the framework) |
| `APP_PASSWORD` | — | Only if your suite reads it | Example: password for the application under test, read by your own smoke suite (not by the framework) |
| `PROJECT_ROOT_DIR` | `.` | No | Root directory for log and Allure paths |
| `LOG_LEVEL` | `INFO` | No | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_FORMAT` | `json` | No | Output format: `json` or `text` |
| `LOG_SINK` | `stdout` | No | Output destination: `stdout`, `file`, or `both` |
| `LOG_ROOT_DIR` | `logs` | No | Log directory (for `file`/`both`) |
| `LOG_FILE` | `a11y-llm.log` | No | Log file name |
| `ALLURE_ENABLED` | `true` | No | Write Allure results |
| `ALLURE_ROOT_DIR` | `allure` | No | Allure root directory |
| `ALLURE_RESULTS_SUBDIR` | `results` | No | Subdirectory for raw results |
| `ALLURE_CLEAN_RESULTS` | `false` | No | Delete raw results before each run |
| `PW_HEADLESS` | `true` | No | Launch the browser without a visible window |
| `PW_SLOW_MO_MS` | `0` | No | Delay between actions in ms |
| `PW_LAUNCH_TIMEOUT_MS` | `30000` | No | Browser launch timeout in ms |
| `PW_ACTION_TIMEOUT_MS` | `10000` | No | Action timeout in ms |
| `PW_NAVIGATION_TIMEOUT_MS` | `20000` | No | Navigation timeout in ms |
| `PW_IGNORE_HTTPS_ERRORS` | `true` | No | Ignore TLS errors (for test environments) |

</details>

---

## 4. Running tests

### 4.1 Your app-specific smoke test (main test)

The repository does not ship a smoke suite for any particular application.
You add your own suite for the application under test; see the
[Developer Guide](DEVELOPER_GUIDE.md) for how to write one. The path
`tests/<your_app>/test_<page>_smoke.py` below is an example path for a suite
you add yourself.

The smoke test runs the full accessibility check against the application
under test. It requires a browser, the LLM, and any credentials your suite
needs.

```bash
poetry run pytest tests/<your_app>/test_<page>_smoke.py -vv -rs
```

**What happens:**

1. The browser opens the page of the application under test (for example its
   login page).
2. If your suite logs in, it signs in with the configured credentials.
3. The configured WCAG criteria are checked: 2.4.4, 3.1.1, and 3.1.2 by
   default, plus 2.4.9 if your suite passes `include_criterion_2_4_9=True`.
4. Results are written to `allure/results/`.
5. The test ends with PASSED or FAILED, plus a structured summary of all
   findings.

**Typical output for a failure:**

```
FAILED tests/<your_app>/test_<page>_smoke.py::test_<page>_a11y
  Failed: WCAG run completed with criterion failures:
  - 2.4.4: WCAG 2.4.4 failed for 3/12 elements. See the 'FAILED Elements Summary' attachment above for details.
  ...
```

### 4.2 Running all tests

Runs every test under `tests/`: the bundled unit tests plus any app-specific
smoke suites you have added:

```bash
poetry run pytest -vv -rs
```

### 4.3 Running specific tests only

```bash
# Only your app-specific suite
poetry run pytest tests/<your_app>/ -vv -rs

# Only unit tests (no browser, no LLM, no credentials needed)
poetry run pytest tests/base/wcag/test_repository.py tests/base/wcag/test_empty_extraction_behavior.py tests/llm/test_wcag_evaluator_parse.py -vv
```

---

## 5. Viewing the Allure report

The report data is written automatically to `allure/results/` when
`ALLURE_ENABLED=true` is set (the default).

### 5.1 Open a live report in the browser

```bash
allure serve allure/results
```

Automatically opens the browser with the interactive report.

### 5.2 Generate a static report

```bash
allure generate allure/results -o allure/report --clean
```

The static report is then located in `allure/report/` and can be viewed or
shared without the Allure CLI.

> **Important:** Always run Allure commands from the project root directory
> so that the path `allure/results` resolves correctly.

### 5.3 What does the report show?

- **Overview page:** Test run summary with passed/failed counts.
- **Test detail:** The test flow, step by step.
- **Element evidence:** For each checked element: selector, extracted
  content, AI evaluation, status.
- **Screenshot:** Full-page screenshot of the page under test at the time of
  the check (if your suite attaches one, for example with
  `attach_full_page_screenshot`).

---

## 6. Running unit tests only

Unit tests do not need a browser, LLM credentials, or a connection to the
application under test. They are suitable for quick checks and for CI
pipelines without network access:

```bash
poetry run pytest \
  tests/base/wcag/test_repository.py \
  tests/base/wcag/test_empty_extraction_behavior.py \
  tests/llm/test_wcag_evaluator_parse.py \
  -vv
```

These tests check:

- Loading of the WCAG criteria configuration.
- Behavior when DOM extraction returns no elements.
- Parsing and validation of LLM responses.

---

## 7. Quality checks

These checks should pass before you commit code changes:

```bash
# Code style and lint
poetry run ruff check src tests

# Check formatting (apply with 'ruff format src tests')
poetry run ruff format --check src tests

# Static type checking
poetry run mypy src tests

# Validate the WCAG configuration file
python -m json.tool src/utils/wcag/criteria.json > /dev/null
```

**Git hooks (optional, recommended):**

The checks can be set up as automatic Git hooks so that they run before
every commit:

```bash
poetry run pre-commit install
```

---

## 8. Troubleshooting

### Problem: "LLM API key is missing"

**Cause:** The `.env` file was not created or `AUDITOR_LLM_API_KEY` is
empty.

**Solution:**
```bash
cp .env.example .env
# Fill in .env with real values
```

---

### Problem: Smoke test skipped because credentials are missing (SKIPPED)

**Cause:** This depends on your own smoke suite. If your suite skips when
its credentials are not set, the variables it reads (for example
`APP_USERNAME` or `APP_PASSWORD`) are missing.

**Solution:** Make the variables your suite expects available when pytest
runs (see the note on app-specific credentials in
[section 3.2](#32-fill-in-the-env-file)), for example:
```bash
export APP_USERNAME=your-username
export APP_PASSWORD=your-password
```

---

### Problem: "Executable doesn't exist" (Playwright)

**Cause:** Chromium has not been installed yet.

**Solution:**
```bash
poetry run playwright install chromium
```

---

### Problem: Allure report is empty or out of date

**Cause:** `ALLURE_ENABLED` is set to `false`, or the report was generated
before the test run.

**Solution:** Make sure `ALLURE_ENABLED=true` is set in `.env`, and generate
the report only **after** the test run.

---

### Problem: Browser timeout when loading a page

**Cause:** The application under test is unreachable or takes longer than
expected to respond.

**Solution:** Increase the timeout values in `.env`:
```bash
PW_NAVIGATION_TIMEOUT_MS=60000
PW_ACTION_TIMEOUT_MS=30000
```

---

### Reading logs

If a problem is unclear, the logs can help. Set the format to `text` for
better readability:

```bash
LOG_FORMAT=text LOG_SINK=both poetry run pytest tests/<your_app>/ -vv -rs
```

The logs then appear on the console and in `logs/a11y-llm.log`.
