# utils.core package

Core infrastructure utilities for environment management.

## Module

- `environment.py`

## Main types and functions

- `EnvironmentStore`: pydantic-settings backed reader over environment values
- `get_environment_store()`: process singleton accessor

## Behavior details

### Environment loading

On `EnvironmentStore` initialization:

- values are resolved by `pydantic-settings` from environment variables and
  optional `.env`
- known fields are typed and validated via Pydantic

This means later external environment changes are not automatically reflected
unless a new store instance is created.

### Required value accessors

- `get_required(name)`: returns non-empty string or raises `EnvironmentError`
- `get_bool_required(name)`: supports `1/0`, `true/false`, `yes/no`, `on/off`
- `get_int_required(name, min_value=None)`: parses integer and enforces optional lower bound

### Path resolution

- `resolve_path(value, root)`: supports absolute paths and root-relative values
- `get_runtime_root()`: resolves to:
  - `PROJECT_ROOT_DIR` when defined
  - current working directory otherwise

## Consumers in this repository

- `src/llm/config.py`
- `src/utils/logging/config.py`
- `src/utils/reporting/config.py`

## Error semantics

- Missing required variable: `EnvironmentError`
- Invalid boolean or integer literal: `ValueError`
- Integer below minimum: `ValueError`
