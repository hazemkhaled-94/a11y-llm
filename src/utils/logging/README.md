# utils.logging package

Centralized logging system for framework runtime and tests.

## Module

- `config.py`

## What it provides

- Global logging configuration (`configure_logging`)
- Logger retrieval (`get_logger`)
- Correlation ID lifecycle helpers
- Safe text formatter and JSON formatter
- Configurable stdout/file/both sink routing

## Required environment variables

- `LOG_LEVEL`
- `LOG_FORMAT` (`text` or `json`)
- `LOG_SINK` (`stdout`, `file`, `both`)
- `LOG_SERVICE_NAME`

Additional required values when `LOG_SINK` includes file output (`file` or `both`):

- `PROJECT_ROOT_DIR` (optional at runtime, but used when path resolving; falls back to cwd)
- `LOG_ROOT_DIR`
- `LOG_FILE`
- `LOG_ROTATE_MAX_BYTES`
- `LOG_ROTATE_BACKUP_COUNT`

## Runtime configuration model

`LoggingSettings` includes:

- `level`
- `log_format`
- `log_sink`
- `service_name`
- optional file-rotation settings (`logs_dir`, `log_file_name`, `rotate_max_bytes`, `rotate_backup_count`)

Settings are created by `LoggingSettingsFactory` from `EnvironmentStore`.

## Handler behavior

### Stdout handler

- `logging.StreamHandler(sys.stdout)`
- Tagged internally with framework-specific handler kind

### File handler

- `ConcurrentRotatingFileHandler` from `concurrent-log-handler`
- Created lazily, only when sink requires file output
- Logs directory is created automatically

## Output formats

### `text`

- Formatter: `SafeTextFormatter`
- Message CR/LF sanitized (`\r` and `\n` escaped) to reduce multiline injection issues
- Line template:
  - `%(asctime)s | %(levelname)s | %(name)s | %(correlation_id)s | %(message)s`

### `json`

- Formatter: `JsonFormatter`
- One JSON object per line with fields:
  - `timestamp`
  - `level`
  - `logger`
  - `message`
  - `correlation_id`
  - `module`
  - `function`
  - `line`
  - `service`
  - optional `exception`

## Correlation IDs

Global context variable: `_CORRELATION_ID`

API:

- `set_correlation_id(correlation_id=None) -> Token[str]`
- `get_correlation_id() -> str`
- `clear_correlation_id(token)`

A custom LogRecord factory injects `record.correlation_id` into every record.

## Threading behavior

- Logging configurator singleton is lock-protected.
- Initial configure and lazy singleton creation are thread-safe.

## Typical usage

```python
from utils.logging import configure_logging
from utils.logging import clear_correlation_id
from utils.logging import get_logger
from utils.logging import set_correlation_id

configure_logging()
logger = get_logger(__name__)

token = set_correlation_id("smoke-case-123")
try:
    logger.info("Starting audit")
finally:
    clear_correlation_id(token)
```

## Test integration

Test lifecycle integration lives in:

- `tests/base/conftest.py`

`test_logger` uses per-test `nodeid` values as correlation IDs and clears tokens in teardown.
