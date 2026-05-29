# tests.base.wcag package

Dedicated WCAG smoke-test package for orchestration, shared helpers, and
criterion-specific modules.

## Modules

- `base.py`: orchestration entrypoint and criterion execution pipeline
- `types.py`: shared contracts (criterion registry, failure models)
- `repository.py`: criteria JSON loading and path resolution
- `reporting.py`: element-level Allure evidence reporting
- `criteria/wcag_2_4_9.py`: consolidated 2.4.9 enrichment + execution flow

## Criterion package

The `criteria` subpackage holds implementation details that are unique to one
WCAG criterion. WCAG 2.4.9 is intentionally kept in one cohesive module to
reduce indirection during debugging and maintenance.

Standard criteria execution (2.4.4, 3.1.1, 3.1.2) is consolidated in
`base.py` to reduce deep call chains and simplify maintenance.

## Allure responsibilities

Two Allure components exist by design:

- `tests/base/conftest.py`
  - session lifecycle setup for Allure directories and environment metadata
- `tests/base/wcag/reporting.py`
  - criterion-level and element-level evidence attachments during WCAG
    evaluation

They operate at different layers and do not overlap in responsibility.
