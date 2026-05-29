# utils package

Shared infrastructure utilities used across test execution and runtime services.

## Package layout

- `core`: environment loading and typed environment access helpers
- `logging`: structured logging, sink/format control, and correlation IDs
- `reporting`: Allure directory setup and command helper APIs
- `wcag/criteria.json`: criterion configuration used by smoke execution

## Important implementation note

The Allure helper package in current code is `utils.reporting` (not `utils.allure`).

## What this package owns

- Process-wide environment snapshot via `EnvironmentStore`
- Process-wide logger configuration via `LoggingConfigurator`
- Process-wide Allure configuration via `AllureConfigurator`
- Shared type-export marker via `py.typed`

## Documentation map

- `src/utils/core/README.md`
- `src/utils/logging/README.md`
- `src/utils/reporting/README.md`

## WCAG configuration reference

`src/utils/wcag/criteria.json` currently defines:

- `2.4.4` Link Purpose (In Context)
- `2.4.9` Link Purpose (Link Only)
- `3.1.1` Language of Page
- `3.1.2` Language of Parts

Fields per criterion:

- metadata (`name`, `description`, `url`, `level`)
- extraction config (`selectors`, `js_extractor`)
- LLM instruction prompt (`prompt`)
