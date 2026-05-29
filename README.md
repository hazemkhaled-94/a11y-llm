# a11y-llm

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

- Python `>=3.12,<3.14` (bounded by `litellm`'s supported range)
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

## Environment variables

Only the LLM connection variables are **required** — the framework fails fast on
startup if any is missing:

- `AUDITOR_LLM_API_KEY`
- `AUDITOR_LLM_MODEL`
- `AUDITOR_LLM_URL`

Everything else (logging, Allure, and Playwright settings) is optional and ships
with working defaults in `.env.example`. Copy that file and adjust only what you
need; the full variable reference is in
`documentation/TECHNICAL_DOCUMENTATION.md`.

## Quality checks

Run lint:

```bash
poetry run ruff check src tests
```

Check formatting (apply with `ruff format` instead of `--check`):

```bash
poetry run ruff format --check src tests
```

Run static typing:

```bash
poetry run mypy src tests
```

Validate WCAG config JSON:

```bash
python -m json.tool src/utils/wcag/criteria.json > /dev/null
```

Optionally install the git hooks so these run automatically before each commit:

```bash
poetry run pre-commit install
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
- The Mars smoke flow needs the required LLM variables and the Chromium browser. The unit tests under `tests/base/wcag/` and `tests/llm/` run with no external setup (no browser, network, or LLM):

  ```bash
  poetry run pytest tests/base/wcag/test_repository.py tests/base/wcag/test_empty_extraction_behavior.py tests/llm/test_wcag_evaluator_parse.py -vv
  ```

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

## Reliability and known limitations

Reliability behavior (by design):

- Connector calls and response validation are each retried up to 3 times;
  malformed model output is rejected rather than trusted.
- If the model returns fewer results than the elements in a batch, the evaluator
  fills the missing element IDs with `MANUAL_REVIEW` placeholders and marks the
  batch status `ERROR`. This makes incomplete model coverage fail the criterion
  instead of passing silently.

Known limitations:

- `web.base.BasePage.run_axe_audit` is a placeholder that returns `{}`. The
  Allure attachment pipeline is already wired so a real Axe-core integration can
  drop in without changing callers.

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

## License

Released under the MIT License. See [LICENSE](LICENSE).
