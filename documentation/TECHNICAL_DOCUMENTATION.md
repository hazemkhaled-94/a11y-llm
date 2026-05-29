# Technical Documentation

A complete technical reference for `a11y-auditor`, aligned with the current
implementation in [`src/`](../src) and [`tests/`](../tests). For diagrams see
[ARCHITECTURE.md](ARCHITECTURE.md); for the management view see
[MANAGEMENT_DOKUMENTATION.md](MANAGEMENT_DOKUMENTATION.md).

## 1. Overview

`a11y-auditor` is an asynchronous accessibility smoke-testing framework. It
drives a target web page with Playwright, extracts the DOM evidence relevant to
each WCAG criterion, evaluates that evidence with an LLM (through LiteLLM),
validates the model output against strict Pydantic schemas, and attaches
auditable evidence to Allure. A criterion fails the smoke test when the model
returns a non-accepted status for any element.

The framework currently ships two end-to-end smoke flows and four WCAG
criteria. The LLM evaluation path is production-near; the classic Axe-core path
is a documented placeholder (see [§11](#11-known-constraints)).

## 2. Repository layout

```text
src/
  llm/            LLM config, connector, Pydantic schemas, evaluator
  utils/
    core/         EnvironmentStore (typed environment access)
    logging/      Structured logging with correlation IDs
    reporting/    Allure configuration lifecycle
    wcag/         criteria.json (selectors + JS extractors + prompts)
  web/
    base/         BasePage (navigation + DOM extraction)
    mars/         Deque "Mars" demo page object
tests/
  conftest.py     Re-exports base fixtures for all suites
  base/
    conftest.py   Session Playwright/browser, logging, Allure fixtures
    wcag/         Orchestrator, reporter, repository, types, unit tests
      criteria/   Criterion-specific runners (2.4.9 enrichment)
  llm/            Evaluator parsing unit tests
documentation/    This documentation set
```

## 3. Runtime requirements

- Python `>=3.12,<3.14` (bounded by `litellm`'s supported range)
- [Poetry](https://python-poetry.org/) for dependency management
- Playwright browser binaries (Chromium): `poetry run playwright install chromium`
- Allure CLI (for local report generation/serving)

### Dependencies

Runtime: `pytest`, `pytest-xdist`, `pytest-asyncio`, `allure-pytest`,
`litellm`, `concurrent-log-handler`, `tenacity`, `pydantic`,
`pydantic-settings`, `pytest-playwright-axe`.

Development: `ruff`, `mypy`, `black`, `isort`, `flake8`, `pre-commit`,
`pip-audit`.

## 4. Configuration

All runtime behavior is controlled by environment variables, read once into a
process-wide [`EnvironmentStore`](../src/utils/core/environment.py)
(`pydantic-settings`, `.env`-aware). Copy `.env.example` to `.env` and fill in
real values. `.env` is git-ignored; `.env.example` is the committed template.

| Variable | Default | Purpose |
| --- | --- | --- |
| `PROJECT_ROOT_DIR` | cwd | Root used to resolve log/allure paths. |
| `AUDITOR_LLM_API_KEY` | — (required) | API key for the LLM endpoint. |
| `AUDITOR_LLM_MODEL` | — (required) | Model name/identifier. |
| `AUDITOR_LLM_URL` | — (required) | Base URL of the LLM provider. |
| `LOG_LEVEL` | `INFO` | Logging level. |
| `LOG_FORMAT` | `json` | `text` or `json`. |
| `LOG_SINK` | `stdout` | `stdout`, `file`, or `both`. |
| `LOG_ROOT_DIR` | `logs` | Log directory (file sinks). |
| `LOG_FILE` | `a11y-auditor.log` | Log file name (file sinks). |
| `LOG_ROTATE_MAX_BYTES` | `5242880` | Rotation size threshold. |
| `LOG_ROTATE_BACKUP_COUNT` | `5` | Rotated files retained. |
| `LOG_SERVICE_NAME` | `a11y-auditor` | `service` field in JSON logs. |
| `ALLURE_ENABLED` | `true` | Enable Allure result emission. |
| `ALLURE_ROOT_DIR` | `allure` | Allure root directory. |
| `ALLURE_RESULTS_SUBDIR` | `results` | Raw results subdirectory. |
| `ALLURE_REPORT_SUBDIR` | `report` | Generated report subdirectory. |
| `ALLURE_CLEAN_RESULTS` | `false` | Clear results before a run. |
| `PW_HEADLESS` | `false` | Run Chromium headless. |
| `PW_SLOW_MO_MS` | `150` | Slow-motion delay per action. |
| `PW_LAUNCH_TIMEOUT_MS` | `30000` | Browser launch timeout. |
| `PW_ACTION_TIMEOUT_MS` | `10000` | Default action timeout. |
| `PW_NAVIGATION_TIMEOUT_MS` | `20000` | Default navigation timeout. |
| `PW_IGNORE_HTTPS_ERRORS` | `true` | Ignore TLS errors (test targets). |

The LLM variables are mandatory and fail fast via
`EnvironmentStore.get_required` when missing or blank. The logging, Allure, and
Playwright variables are optional and fall back to the defaults above; the
`PW_*` defaults shown are the fixture defaults in
[`tests/base/conftest.py`](../tests/base/conftest.py), while the committed
`.env.example` ships headless-friendly values for CI.

## 5. Component reference

### 5.1 Environment store — `src/utils/core/environment.py`

A single `EnvironmentStore` (subclass of `pydantic_settings.BaseSettings`)
loaded once at import time and exposed via `get_environment_store()`. It offers
typed, validated accessors: `get_required`, `get_optional`, `get_bool_*`,
`get_int_*`, plus path helpers (`resolve_path`, `get_runtime_root`). Unknown
variables are ignored (`extra="ignore"`), and any variable not declared as a
field falls back to `os.getenv`.

### 5.2 Logging — `src/utils/logging/config.py`

Process-wide logging configured idempotently through a `LoggingConfigurator`
singleton. Highlights:

- Two formats: single-line `JsonFormatter` (timestamp, level, logger, message,
  correlation ID, module, function, line, service) and a `SafeTextFormatter`
  that escapes `\r`/`\n` to reduce log-injection risk.
- Three sinks: `stdout`, rotating `file` (via `concurrent-log-handler`), or
  `both`. Handlers are tagged so reconfiguration is safe and never duplicates.
- Correlation IDs via a `contextvars` variable and a custom `LogRecord`
  factory, with `set_correlation_id` / `get_correlation_id` /
  `clear_correlation_id`. Tests bind the pytest `nodeid` as the correlation ID.

Public API: `configure_logging`, `get_logger`, `set_correlation_id`,
`get_correlation_id`, `clear_correlation_id`.

### 5.3 Reporting — `src/utils/reporting/config.py`

`AllureConfig` (immutable) plus an `AllureConfigurator` that prepares the
results/report directories. Public API: `load_allure_config_from_environment`,
`configure_allure` (async), `write_environment_properties` (async). Report
rendering is performed with the Allure CLI from the repository root; the package
only prepares directories and environment metadata.

### 5.4 LLM layer — `src/llm/`

- **`config.py`** — `LLMConfig` (frozen dataclass) and `LLMConfigLoader`, which
  reads `AUDITOR_LLM_*` from the environment store.
- **`connector.py`** — `Connector` wraps `litellm.acompletion`. It is retried
  with `tenacity` (3 attempts, exponential backoff 2–10 s) and sends fixed
  generation settings: `max_tokens=4096`, `timeout=900`, `temperature=0.2`,
  `seed=200994`, `num_ctx=131072`. The `CompletionClient` `Protocol` keeps the
  evaluator transport-agnostic.
- **`models.py`** — strict Pydantic contracts: `ExtractedElement`,
  `WCAGEvaluationRequest`, `ElementEvaluationResult`
  (`PASS`/`FAIL`/`NEEDS_CONTEXT`/`MANUAL_REVIEW`), and `WCAGEvaluationResult`
  (`SUCCESS`/`ERROR` + results).
- **`wcag_evaluator.py`** — `WCAGEvaluator` orchestrates evaluation:
  1. Splits elements into chunks (`chunk_size`, default 15).
  2. Builds prompt messages with JSON-schema reinforcement.
  3. Calls the connector and validates the response (up to 3 validation
     retries).
  4. Normalizes varied model output shapes (object, array, single result,
     fenced/embedded JSON, typed-text chunks).
  5. Reconciles coverage: missing element IDs are filled with `MANUAL_REVIEW`
     placeholders and the batch status is downgraded to `ERROR`, so partial
     model responses cannot silently drop coverage.

### 5.5 Web layer — `src/web/`

- **`base/base_page.py`** — `BasePage`: `navigate`, `wait_for_page_load`,
  `extract_elements_by_locator`, `extract_element_data` (runs a JS extractor on
  a locator), and `run_axe_audit` (placeholder returning `{}`).
- **`mars/mars_demo_page.py`** — `MarsDemoPage` for the Deque "Mars" demo.

Additional target page objects (for example, authenticated flows) live in their
own subpackage under `src/web/` and reuse `BasePage`; see "Adding a new
criterion" and the root README's "Add a new target page".

### 5.6 WCAG domain — `tests/base/wcag/`

- **`repository.py`** — resolves and loads `criteria.json` (explicit root →
  `PROJECT_ROOT` → `PROJECT_ROOT_DIR`).
- **`types.py`** — `EmptyBehavior`, `CriterionExecutionConfig`,
  `CriterionFailure`, `CriterionDefinition`, `ElementEvaluationFailure`.
- **`reporting.py`** — `WCAGCriterionAllureReporter` attaches per-element
  evidence and returns failing elements; `assert_llm_outcome_or_raise` is the
  shared pass/fail gate used by every criterion runner.
- **`base.py`** — the orchestrator: extraction, evaluation, reporting, the
  typed criterion registry (`criterion_steps`), and
  `run_configured_wcag_criteria`, which runs each criterion, collects skips and
  failures, and fails once with an aggregated summary.
- **`criteria/wcag_2_4_9.py`** — the 2.4.9 specialist: resolves link
  destinations, opens each unique destination once (cached), enriches each
  element with destination metadata, and evaluates with `chunk_size=5`.

## 6. WCAG criteria configuration

Criteria are declared as data in
[`src/utils/wcag/criteria.json`](../src/utils/wcag/criteria.json). Each entry
has: `name`, `description`, `url`, `level`, `selectors` (list), `js_extractor`
(a JS function string returning a data object per element), and `prompt`.

| Criterion | Name | Level | Empty-extraction policy |
| --- | --- | --- | --- |
| 2.4.4 | Link Purpose (In Context) | A | skip |
| 2.4.9 | Link Purpose (Link Only) | AAA | bespoke (specialist path) |
| 3.1.1 | Language of Page | A | fail |
| 3.1.2 | Language of Parts | AA | pass |

For 2.4.9 the specialist runner handles emptiness itself: no candidate links at
all is treated as a pass with an evidence note, whereas links that all fail
destination enrichment raise a failure.

The shipped Mars smoke flow (`tests/base/test_mars_smoke.py`) runs 2.4.4,
3.1.1, and 3.1.2. Criterion 2.4.9 is opt-in on any flow via
`include_criterion_2_4_9=True`.

### Adding a new criterion

1. Add the criterion to `criteria.json` (selectors, `js_extractor`, `prompt`).
2. For standard handling, add a runner that delegates to
   `_execute_standard_criterion` with a `CriterionExecutionConfig`; for special
   handling (like destination enrichment), add a module under `criteria/`.
3. Register the runner in `criterion_steps()` in the desired order.
4. Run the smoke tests and verify the Allure evidence.

## 7. Execution model

- Tests are asynchronous (`asyncio_mode = "auto"`). Playwright runtime,
  browser, context, and page fixtures are session-scoped and defined in
  `tests/base/conftest.py`; `tests/conftest.py` re-exports them so all suites
  share one fixture stack.
- `pytest_configure` initializes logging and resolves the Playwright/Allure
  configuration; `pytest_sessionstart` prepares Allure directories and writes
  `environment.properties`.
- Each test receives a `test_logger` bound to a per-test correlation ID and a
  `wcag_criteria` mapping loaded from `criteria.json`.

## 8. Error resilience

- **Transport retries** — connector calls retry 3× with exponential backoff.
- **Validation retries** — the evaluator re-requests up to 3× when model output
  fails JSON parsing or schema validation, then raises a clear `ValueError`.
- **Coverage reconciliation** — missing element results become `MANUAL_REVIEW`
  placeholders and force batch status `ERROR`.
- **Aggregated failure** — `run_configured_wcag_criteria` never aborts on the
  first failing criterion; it records each skip/failure and fails once with a
  per-criterion summary, with all evidence attached to Allure.
- **Bounded teardown** — browser/context/page teardown is wrapped with
  `asyncio.wait_for` timeouts to avoid hanging sessions.

## 9. Security and data handling

The security-relevant surface is small: secrets, the content sent to the LLM,
and log hygiene.

- **Secrets** — the LLM API key (and any target credentials) are read only from
  the environment. `.env` is git-ignored; only `.env.example` (placeholders) is
  committed. No secret is written to logs or Allure attachments.
- **Data sent to the LLM** — the framework sends extracted DOM evidence (and,
  for 2.4.9, short destination-page text summaries) to the configured LLM
  endpoint. Extractors deliberately collect only criterion-relevant fields
  (data minimization). Do not point the framework at pages containing sensitive
  personal data without reviewing the LLM provider's data-handling terms.
- **Log hygiene** — the text formatter escapes newline characters to reduce
  log-injection risk; JSON logs are structured and carry a correlation ID for
  traceability.

For production or enterprise adoption, the natural next steps are a managed
secret store with rotation, a defined retention/cleanup policy for logs and
Allure artifacts, and a documented review of the LLM endpoint's data residency.

## 10. Quality gates

```bash
poetry run ruff check src tests          # lint
poetry run mypy src tests                # static typing (strict, typed)
python -m json.tool src/utils/wcag/criteria.json > /dev/null   # validate config
poetry run pytest -vv -rs                # full suite (needs browser + LLM)
```

Offline unit tests (no browser/LLM/credentials required) cover repository path
resolution, evaluator response parsing, and empty-extraction orchestration:

```bash
poetry run pytest \
  tests/base/wcag/test_repository.py \
  tests/llm/test_wcag_evaluator_parse.py \
  tests/base/wcag/test_empty_extraction_behavior.py -vv
```

## 11. Known constraints

- `BasePage.run_axe_audit` returns `{}` (placeholder); the Allure attachment
  pipeline is already wired so a real Axe-core integration can drop in.
- WCAG coverage is intentionally limited to four criteria.

## 12. Roadmap

- **Short term** — integrate real Axe-core results; expand the prioritized
  WCAG criteria set.
- **Mid term** — resolve `NEEDS_CONTEXT` via parent/sibling traversal;
  deterministic baseline suites with a mocked LLM for CI; quality metrics.
- **Long term** — multi-page crawling; versioned, reviewable rule packages;
  formal CI/CD integration with quality gates.
