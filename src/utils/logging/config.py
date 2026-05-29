"""Centralized logging setup for the framework."""

from __future__ import annotations

import importlib
import json
import logging
import sys
import threading
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from utils.core.environment import EnvironmentStore, get_environment_store

_ALLOWED_LOG_FORMATS = {"text", "json"}
_ALLOWED_LOG_SINKS = {"stdout", "file", "both"}
_CORRELATION_ID = ContextVar("correlation_id", default="-")
_CONCURRENT_HANDLER_CLASS: type[logging.Handler] | None = None
_HANDLER_KIND_ATTR = "_a11y_handler_kind"
_HANDLER_KIND_STDOUT = "stdout"
_HANDLER_KIND_FILE = "file"


def _get_concurrent_handler_class() -> type[logging.Handler]:
    """Resolve ConcurrentRotatingFileHandler class lazily.

    Returns:
        type[logging.Handler]: Concurrent rotating file handler class.

    Raises:
        RuntimeError: If concurrent-log-handler is not installed.
    """
    global _CONCURRENT_HANDLER_CLASS
    if _CONCURRENT_HANDLER_CLASS is not None:
        return _CONCURRENT_HANDLER_CLASS

    try:
        module = importlib.import_module("concurrent_log_handler")
    except ImportError as exc:
        raise RuntimeError(
            "Package 'concurrent-log-handler' is required for logging."
        ) from exc

    _CONCURRENT_HANDLER_CLASS = getattr(
        module,
        "ConcurrentRotatingFileHandler",
    )
    assert _CONCURRENT_HANDLER_CLASS is not None
    return _CONCURRENT_HANDLER_CLASS


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON payloads."""

    def __init__(self, service_name: str):
        """Initialize formatter.

        Args:
            service_name: Service identifier included in log payloads.
        """
        super().__init__()
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format one log record.

        Args:
            record: Log record passed by logging framework.

        Returns:
            str: Serialized JSON log line.
        """
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "service": self._service_name,
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


class SafeTextFormatter(logging.Formatter):
    """Format log records as text and sanitize line breaks."""

    def format(self, record: logging.LogRecord) -> str:
        """Format one log record with newline-safe message.

        Args:
            record: Log record passed by logging framework.

        Returns:
            str: Sanitized formatted log line.
        """
        copied = logging.makeLogRecord(record.__dict__.copy())
        message = copied.getMessage()
        copied.msg = message.replace("\r", "\\r").replace("\n", "\\n")
        copied.args = ()
        return super().format(copied)


class CorrelationIdRecordFactory:
    """Install a global LogRecord factory that injects correlation ID."""

    _installed = False
    _lock = threading.Lock()

    @classmethod
    def install(cls) -> None:
        """Install record factory once per process."""
        with cls._lock:
            if cls._installed:
                return

            previous_factory = logging.getLogRecordFactory()

            def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
                record = previous_factory(*args, **kwargs)
                record.correlation_id = get_correlation_id()
                return record

            logging.setLogRecordFactory(factory)
            cls._installed = True


@dataclass(frozen=True)
class LoggingSettings:
    """Runtime settings for logging configuration."""

    level: str
    log_format: str
    log_sink: str
    service_name: str
    logs_dir: Path | None
    log_file_name: str | None
    rotate_max_bytes: int | None
    rotate_backup_count: int | None

    @property
    def log_file_path(self) -> Path | None:
        """Get active log file path.

        Returns:
            Path | None: Absolute path to active log file.
        """
        if self.logs_dir is None or self.log_file_name is None:
            return None
        return self.logs_dir / self.log_file_name


class LoggingSettingsFactory:
    """Build logging settings from shared environment store."""

    def __init__(self, env_store: EnvironmentStore):
        """Initialize factory.

        Args:
            env_store: Shared environment store singleton.
        """
        self._env = env_store

    def build(self) -> LoggingSettings:
        """Build validated logging settings.

        Returns:
            LoggingSettings: Immutable logging settings.
        """
        level = self._env.get_optional("LOG_LEVEL", default="INFO").upper()
        log_format = self._env.get_optional(
            "LOG_FORMAT",
            default="json",
        ).lower()
        if log_format not in _ALLOWED_LOG_FORMATS:
            raise ValueError("LOG_FORMAT must be either 'text' or 'json'.")

        log_sink = self._env.get_optional(
            "LOG_SINK",
            default="stdout",
        ).lower()
        if log_sink not in _ALLOWED_LOG_SINKS:
            raise ValueError("LOG_SINK must be one of: stdout, file, both.")

        logs_dir: Path | None = None
        log_file_name: str | None = None
        rotate_max_bytes: int | None = None
        rotate_backup_count: int | None = None

        if log_sink in {"file", "both"}:
            runtime_root = self._env.get_runtime_root()
            logs_root = self._env.get_optional(
                "LOG_ROOT_DIR",
                default="logs",
            )
            logs_dir = self._env.resolve_path(logs_root, runtime_root)

            rotate_max_bytes = self._env.get_int_optional(
                "LOG_ROTATE_MAX_BYTES",
                default=5_242_880,
                min_value=1,
            )
            rotate_backup_count = self._env.get_int_optional(
                "LOG_ROTATE_BACKUP_COUNT",
                default=5,
                min_value=0,
            )
            log_file_name = self._env.get_optional(
                "LOG_FILE",
                default="a11y-auditor.log",
            )

        return LoggingSettings(
            level=level,
            log_format=log_format,
            log_sink=log_sink,
            service_name=self._env.get_optional(
                "LOG_SERVICE_NAME",
                default="a11y-auditor",
            ),
            logs_dir=logs_dir,
            log_file_name=log_file_name,
            rotate_max_bytes=rotate_max_bytes,
            rotate_backup_count=rotate_backup_count,
        )


class LoggingConfigurator:
    """Encapsulate process-wide logging configuration behavior."""

    def __init__(self, settings: LoggingSettings):
        """Initialize configurator.

        Args:
            settings: Immutable logging settings.
        """
        self._settings = settings
        self._configure_lock = threading.Lock()
        self._is_configured = False

    def configure(
        self,
        *,
        level: str | None = None,
        log_format: str | None = None,
        log_sink: str | None = None,
    ) -> None:
        """Configure root logger.

        Args:
            level: Optional runtime level override.
            log_format: Optional runtime format override.
            log_sink: Optional runtime sink override.
        """
        if (
            self._is_configured
            and level is None
            and log_format is None
            and log_sink is None
        ):
            return

        with self._configure_lock:
            if (
                self._is_configured
                and level is None
                and log_format is None
                and log_sink is None
            ):
                return

            root = logging.getLogger()

            effective_format = self._resolve_format(log_format)
            effective_sink = self._resolve_sink(log_sink)
            CorrelationIdRecordFactory.install()
            formatter = self._build_formatter(effective_format)

            existing_stdout_handler = self._get_stdout_handler(root)
            existing_handler = self._get_project_file_handler(root)

            if effective_sink in {"stdout", "both"}:
                if existing_stdout_handler is None:
                    stdout_handler = self._build_stdout_handler()
                    stdout_handler.setFormatter(formatter)
                    root.addHandler(stdout_handler)
                else:
                    existing_stdout_handler.setFormatter(formatter)
            elif existing_stdout_handler is not None:
                root.removeHandler(existing_stdout_handler)

            if effective_sink in {"file", "both"}:
                if existing_handler is None:
                    handler = self._build_rotating_file_handler(
                        effective_format
                    )
                    root.addHandler(handler)
                else:
                    existing_handler.setFormatter(formatter)
            else:
                if existing_handler is not None:
                    root.removeHandler(existing_handler)

            if level is not None:
                root.setLevel(self._resolve_level(level))
            elif not self._is_configured:
                root.setLevel(self._resolve_level(None))

            self._is_configured = True

    def get_logger(self, name: str) -> logging.Logger:
        """Get logger after ensuring configuration is applied.

        Args:
            name: Logger namespace, usually `__name__`.

        Returns:
            logging.Logger: Configured logger instance.
        """
        self.configure()
        return logging.getLogger(name)

    def _resolve_level(self, level: str | None) -> int:
        """Resolve effective logging level constant.

        Args:
            level: Optional runtime override.

        Returns:
            int: Logging level constant.
        """
        candidate = (level or self._settings.level).upper()
        return getattr(logging, candidate, logging.INFO)

    def _resolve_format(self, log_format: str | None) -> str:
        """Resolve effective output format.

        Args:
            log_format: Optional runtime override.

        Returns:
            str: Valid format (`text` or `json`).
        """
        candidate = (log_format or self._settings.log_format).lower()
        if candidate not in _ALLOWED_LOG_FORMATS:
            raise ValueError("LOG_FORMAT must be either 'text' or 'json'.")
        return candidate

    def _resolve_sink(self, log_sink: str | None) -> str:
        """Resolve effective output sink.

        Args:
            log_sink: Optional runtime override.

        Returns:
            str: Valid sink (`stdout`, `file`, or `both`).
        """
        candidate = (log_sink or self._settings.log_sink).lower()
        if candidate not in _ALLOWED_LOG_SINKS:
            raise ValueError("LOG_SINK must be one of: stdout, file, both.")
        return candidate

    def _get_stdout_handler(
        self,
        root: logging.Logger,
    ) -> logging.Handler | None:
        """Find stdout handler managed by this configurator.

        Args:
            root: Root logger object.

        Returns:
            logging.Handler | None: Matching stdout handler.
        """
        for handler in root.handlers:
            if (
                getattr(handler, _HANDLER_KIND_ATTR, None)
                == _HANDLER_KIND_STDOUT
            ):
                return handler
        return None

    def _get_project_file_handler(
        self,
        root: logging.Logger,
    ) -> logging.Handler | None:
        """Find project file handler if it already exists.

        Args:
            root: Root logger object.

        Returns:
            logging.Handler | None: Matching project file handler.
        """
        log_file_path = self._settings.log_file_path
        if log_file_path is None:
            return None

        target = self._normalize_path(log_file_path)
        for handler in root.handlers:
            if self._is_project_file_handler(handler, target):
                return handler
        return None

    def _is_project_file_handler(
        self,
        handler: logging.Handler,
        target: Path,
    ) -> bool:
        """Check if handler writes to the configured project log file.

        Args:
            handler: Candidate logging handler.
            target: Normalized project log file path.

        Returns:
            bool: True when handler matches configured file path.
        """
        handler_class = cast(Any, _get_concurrent_handler_class())
        if not isinstance(handler, handler_class):
            return False

        if getattr(handler, _HANDLER_KIND_ATTR, None) != _HANDLER_KIND_FILE:
            return False

        base_name = getattr(handler, "baseFilename", None)
        if not base_name:
            return False

        return self._normalize_path(base_name) == target

    def _normalize_path(self, path_value: str | Path) -> Path:
        """Normalize path for robust cross-handler comparison.

        Args:
            path_value: Path-like value to normalize.

        Returns:
            Path: Normalized absolute path.
        """
        return Path(path_value).expanduser().resolve()

    def _build_formatter(self, log_format: str) -> logging.Formatter:
        """Build formatter for selected output format.

        Args:
            log_format: Selected format.

        Returns:
            logging.Formatter: Formatter instance.
        """
        if log_format == "json":
            return JsonFormatter(self._settings.service_name)

        return SafeTextFormatter(
            (
                "%(asctime)s | %(levelname)s | %(name)s | "
                "%(correlation_id)s | %(message)s"
            ),
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )

    def _build_stdout_handler(self) -> logging.Handler:
        """Create stdout stream handler.

        Returns:
            logging.Handler: Configured stdout handler.
        """
        handler = logging.StreamHandler(stream=sys.stdout)
        setattr(handler, _HANDLER_KIND_ATTR, _HANDLER_KIND_STDOUT)
        return handler

    def _build_rotating_file_handler(
        self,
        log_format: str,
    ) -> logging.Handler:
        """Create rotating file handler for the project.

        Args:
            log_format: Selected output format.

        Returns:
            logging.Handler: Configured file handler.
        """
        if self._settings.logs_dir is None:
            raise RuntimeError("LOG_ROOT_DIR is required for file logging.")
        if self._settings.log_file_path is None:
            raise RuntimeError("LOG_FILE is required for file logging.")
        if self._settings.rotate_max_bytes is None:
            raise RuntimeError(
                "LOG_ROTATE_MAX_BYTES is required for file logging."
            )
        if self._settings.rotate_backup_count is None:
            raise RuntimeError(
                "LOG_ROTATE_BACKUP_COUNT is required for file logging."
            )

        self._settings.logs_dir.mkdir(parents=True, exist_ok=True)
        handler_class = cast(Any, _get_concurrent_handler_class())
        handler = handler_class(
            filename=str(self._settings.log_file_path),
            maxBytes=self._settings.rotate_max_bytes,
            backupCount=self._settings.rotate_backup_count,
            encoding="utf-8",
        )
        setattr(handler, _HANDLER_KIND_ATTR, _HANDLER_KIND_FILE)
        handler.setFormatter(self._build_formatter(log_format))
        return handler


LOGGING_CONFIGURATOR = LoggingConfigurator(
    LoggingSettingsFactory(get_environment_store()).build()
)


def set_correlation_id(correlation_id: str | None = None) -> Token[str]:
    """Set active correlation ID and return reset token.

    Args:
        correlation_id: Optional explicit ID.

    Returns:
        Token[str]: Token that can restore previous context.
    """
    resolved = correlation_id or str(uuid4())
    return _CORRELATION_ID.set(resolved)


def get_correlation_id() -> str:
    """Get active correlation ID for current context.

    Returns:
        str: Current correlation ID or `-` if not set.
    """
    return _CORRELATION_ID.get()


def clear_correlation_id(token: Token[str]) -> None:
    """Reset active correlation ID using provided token.

    Args:
        token: Token returned from set_correlation_id.
    """
    _CORRELATION_ID.reset(token)


def configure_logging(
    *,
    level: str | None = None,
    log_format: str | None = None,
    log_sink: str | None = None,
) -> None:
    """Configure process-wide logging.

    Args:
        level: Optional runtime level override.
        log_format: Optional runtime format override.
        log_sink: Optional runtime sink override.
    """
    LOGGING_CONFIGURATOR.configure(
        level=level,
        log_format=log_format,
        log_sink=log_sink,
    )


def get_logger(name: str) -> logging.Logger:
    """Return logger after ensuring global configuration.

    Args:
        name: Logger namespace, usually `__name__`.

    Returns:
        logging.Logger: Configured logger instance.
    """
    return LOGGING_CONFIGURATOR.get_logger(name)
