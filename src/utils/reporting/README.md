# utils.reporting package

Allure reporting configuration and command helper package.

## Module

- `config.py`

## Public API exports

From `utils.reporting.__init__`:

- `AllureConfig`
- `load_allure_config_from_environment()`
- `configure_allure(config=None)`
- `write_environment_properties(metadata, config=None)`

The async API functions (`configure_allure`, `write_environment_properties`)
delegate their synchronous filesystem work through `asyncio.to_thread`.

## Configuration model

`AllureConfig` fields:

- `enabled: bool`
- `results_dir: Path`
- `report_dir: Path`
- `clean_results: bool`

## Required environment variables

- `ALLURE_ENABLED`
- `ALLURE_ROOT_DIR`
- `ALLURE_RESULTS_SUBDIR`
- `ALLURE_REPORT_SUBDIR`
- `ALLURE_CLEAN_RESULTS`
- `PROJECT_ROOT_DIR` (optional root override, defaults to cwd)

## Path resolution behavior

1. Runtime root is resolved from `PROJECT_ROOT_DIR` or current working directory.
2. `ALLURE_ROOT_DIR` is resolved against runtime root.
3. Results/report subdirectories are resolved against `ALLURE_ROOT_DIR`.

Example with default `.env.example` values:

- `ALLURE_ROOT_DIR=allure`
- `ALLURE_RESULTS_SUBDIR=results`
- `ALLURE_REPORT_SUBDIR=report`

Resolved folders become:

- `<runtime_root>/allure/results`
- `<runtime_root>/allure/report`

## Configure behavior

`AllureConfigurator.configure()`:

- No-op when already configured
- No-op when `enabled=false`
- Optionally removes existing results directory when `clean_results=true`
- Ensures both results/report directories exist

## Report generation (Allure CLI)

This package prepares the results/report directories; report rendering is done
with the Allure CLI, run from the repository root:

- Generate a static report:
  - `allure generate <results_dir> -o <report_dir> --clean`
- Open a generated report:
  - `allure open <report_dir>`

## Pytest integration points

- `tests/base/conftest.py` reads this config during `pytest_configure` and sets `config.option.allure_report_dir` when enabled.
- `tests/base/conftest.py::pytest_sessionstart` calls `configure_allure()` and writes `environment.properties` metadata.

## Operational note

To serve report from raw results, run from repository root:

```bash
allure serve allure/results
```
