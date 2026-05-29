"""Unit tests for WCAG criteria repository path handling."""

from __future__ import annotations

from pathlib import Path

from tests.base.wcag.repository import criteria_config_path


class _NoopLogger:
    """Minimal logger stub used by repository tests."""

    def info(self, *_args: object, **_kwargs: object) -> None:
        """Accept info calls without producing output."""
        return None


def test_criteria_config_path_uses_explicit_root() -> None:
    """Criteria path should resolve from explicitly passed project root."""
    project_root = Path(__file__).resolve().parents[3]
    resolved = criteria_config_path(project_root)

    assert resolved.is_absolute()
    assert resolved.name == "criteria.json"
    assert resolved.exists()
    assert "src/utils/wcag/criteria.json" in resolved.as_posix()


def test_criteria_config_path_uses_environment(monkeypatch) -> None:
    """Criteria path should resolve from PROJECT_ROOT environment variable."""
    project_root = Path(__file__).resolve().parents[3]
    monkeypatch.setenv("PROJECT_ROOT", str(project_root))
    resolved = criteria_config_path()

    assert resolved.exists()
    assert resolved.name == "criteria.json"
