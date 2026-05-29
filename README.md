# a11y-auditor

Accessibility smoke-auditing framework that combines:

- Async Playwright page automation
- WCAG rule-driven DOM extraction
- LLM-based criterion evaluation
- Allure evidence reporting
- Structured process logging with correlation IDs

This README is aligned with the current implementation in `src/` and `tests/`.

## What is currently implemented

The repository ships an end-to-end async smoke scenario against a public demo
target:

- `tests/base/test_mars_smoke.py`: accessibility smoke flow for the Deque
  University Mars demo

It runs on the shared WCAG pipeline in `tests/base/wcag/base.py`, which is the
reusable core for auditing any target page (see "Extending the project").

## WCAG criteria currently configured

Configured in `src/utils/wcag/criteria.json`:

- `2.4.4` Link Purpose (In Context), level A
- `2.4.9` Link Purpose (Link Only), level AAA
- `3.1.1` Language of Page, level A
- `3.1.2` Language of Parts, level AA

Criteria executed by the shipped Mars smoke flow: `2.4.4`, `3.1.1`, `3.1.2`.

Criterion `2.4.9` (Link Purpose, Link Only) is implemented as an opt-in
specialist path and is enabled per flow via `include_criterion_2_4_9=True`.

## High-level architecture

1. A page object opens the target page.
2. Criterion selectors and JS extractors are loaded from `src/utils/wcag/criteria.json`.
3. Extracted elements are converted to typed models (`llm.models.ExtractedElement`).
4. `llm.wcag_evaluator.WCAGEvaluator` sends chunked requests to the LLM connector.
5. Model output is validated against strict Pydantic schemas.
6. Results are attached to Allure with per-element evidence.
7. Non-accepted statuses fail the smoke test with structured failure summaries.

## Repository structure

- `src/llm`: LLM configuration, connector, schemas, evaluation orchestration
- `src/utils`: infrastructure helpers (environment, logging, reporting)
- `src/web`: page objects and browser interaction layer (namespace package)
- `tests/base`: shared fixtures, lifecycle managers, WCAG smoke base
- `documentation`: management and technical project documentation

Detailed package documentation:

- `src/llm/README.md`
- `src/utils/README.md`
- `src/utils/core/README.md`
- `src/utils/logging/README.md`
- `src/utils/reporting/README.md`
- `src/web/README.md`
- `src/web/base/README.md`
- `src/web/mars/README.md`
- `tests/README.md`
- `tests/base/README.md`

Project-level documentation:

- `documentation/ARCHITECTURE.md` (architecture and diagrams)
- `documentation/TECHNICAL_DOCUMENTATION.md` (technical reference)
- `documentation/MANAGEMENT_DOKUMENTATION.md` (management overview, German)

## Runtime and tool requirements

- Python `>=3.12,<4.0`
- Poetry
- Playwright browser binaries (Chromium)
- Allure CLI (for local report generation/serving)

## Installation and local setup

1. Install dependencies:

   ```bash
   poetry install
   ```

2. Create your environment file:

   ```bash
   cp .env.example .env
   ```

3. Fill `.env` with real values, especially:

   - `AUDITOR_LLM_API_KEY`
   - `AUDITOR_LLM_MODEL`
   - `AUDITOR_LLM_URL`

4. Install Chromium for Playwright:

   ```bash
   poetry run playwright install chromium
   ```

## Environment variables used by implementation

### LLM

- `AUDITOR_LLM_API_KEY`
- `AUDITOR_LLM_MODEL`
- `AUDITOR_LLM_URL`

### Logging

- `PROJECT_ROOT_DIR`
- `LOG_LEVEL`
- `LOG_FORMAT` (`text` or `json`)
- `LOG_SINK` (`stdout`, `file`, `both`)
- `LOG_ROOT_DIR`
- `LOG_FILE`
- `LOG_ROTATE_MAX_BYTES`
- `LOG_ROTATE_BACKUP_COUNT`
- `LOG_SERVICE_NAME`

### Allure

- `ALLURE_ENABLED`
- `ALLURE_ROOT_DIR`
- `ALLURE_RESULTS_SUBDIR`
- `ALLURE_REPORT_SUBDIR`
- `ALLURE_CLEAN_RESULTS`

### Playwright fixtures

- `PW_HEADLESS`
- `PW_SLOW_MO_MS`
- `PW_LAUNCH_TIMEOUT_MS`
- `PW_ACTION_TIMEOUT_MS`
- `PW_NAVIGATION_TIMEOUT_MS`
- `PW_IGNORE_HTTPS_ERRORS`

## Quality checks

Run lint:

```bash
poetry run ruff check src tests
```

Run static typing:

```bash
poetry run mypy src tests
```

Validate WCAG config JSON:

```bash
python -m json.tool src/utils/wcag/criteria.json > /dev/null
```

## Test execution

Run all tests:

```bash
poetry run pytest -vv -rs
```

Run the Mars smoke flow only:

```bash
poetry run pytest tests/base/test_mars_smoke.py -vv -rs
```

Notes:

- Tests are async (`pytest.mark.asyncio`).
- Session-scoped Playwright/browser fixtures are defined in `tests/base/conftest.py`.
- `tests/conftest.py` re-exports base fixtures so all suites use one fixture stack.

## Allure reporting

Results are written to `allure/results` when `ALLURE_ENABLED=true`.

Serve report from repository root:

```bash
allure serve allure/results
```

Generate static report:

```bash
allure generate allure/results -o allure/report --clean
```

Important operational detail:

- Run Allure commands from repository root so `allure/results` resolves correctly.

## Known implementation constraints

- `web.base.BasePage.run_axe_audit` currently returns `{}` (placeholder stub).
- `WCAGEvaluator` attempts to recover partial model output by adding `MANUAL_REVIEW` placeholders, but marks batch status as `ERROR` in those cases.

## Extending the project

### Add a new WCAG criterion

1. Add criterion definition to `src/utils/wcag/criteria.json`:
   - selector list
   - `js_extractor`
   - criterion prompt
2. Add runner logic in `tests/base/wcag/base.py` (or in a dedicated module under `tests/base/wcag/criteria/` for criterion-specific behavior).
3. Add the criterion runner to `criterion_steps()` ordering in `tests/base/wcag/base.py`.
4. Execute smoke tests and verify Allure evidence.

### Add a new target page

1. Add page object under `src/web/...` extending `BasePage`.
2. Create an async function-based smoke test under `tests/<target>/`.
3. Reuse `run_configured_wcag_criteria(...)` from `tests/base/wcag/base.py`.
4. Add target-specific setup/auth flow if needed.

## Documentation scope notes

- `documentation/` holds the architecture, technical, and management references; start at `documentation/README.md`.
- Package-level READMEs under `src/` and `tests/` are the authoritative implementation-level API/flow documentation.
