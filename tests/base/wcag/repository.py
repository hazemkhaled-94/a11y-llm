"""WCAG criteria loading helpers for smoke tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from utils.logging import Logger


def _resolve_project_root(project_root: Path | str | None) -> Path:
    """Resolve project root from explicit input or supported env vars."""
    if project_root is not None:
        return Path(project_root).expanduser().resolve()

    env_root = (
        os.getenv("PROJECT_ROOT") or os.getenv("PROJECT_ROOT_DIR") or ""
    ).strip()
    if env_root:
        return Path(env_root).expanduser().resolve()

    raise RuntimeError(
        "Project root is not configured. Pass project_root from "
        "pytest request.config.rootpath or set PROJECT_ROOT."
    )


def criteria_config_path(
    project_root: Path | str | None = None,
) -> Path:
    """Return absolute path to the WCAG criteria JSON file.

    Resolution order:
    1) Explicit ``project_root`` argument.
    2) ``PROJECT_ROOT`` environment variable.
    3) ``PROJECT_ROOT_DIR`` environment variable.

    Returns:
        Path: Absolute path to criteria.json.
    """
    root = _resolve_project_root(project_root)

    candidates = [
        root / "src" / "utils" / "wcag" / "criteria.json",
        root / "utils" / "wcag" / "criteria.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


def load_wcag_criteria(
    logger: Logger,
    *,
    project_root: Path | str | None = None,
) -> dict[str, Any]:
    """Load and parse WCAG criteria JSON configuration.

    Args:
        logger: Logger instance used for diagnostics.
        project_root: Optional project root path.

    Returns:
        dict[str, Any]: Parsed criteria mapping.
    """
    logger.info("Loading WCAG criteria JSON configuration.")
    config_path = criteria_config_path(project_root)
    if not config_path.exists():
        raise FileNotFoundError(
            f"WCAG criteria configuration was not found: {config_path}"
        )

    with open(config_path, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)
