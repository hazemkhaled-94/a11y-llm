"""Shared pytest fixtures for all tests packages.

This bridge ensures tests outside tests/base also use the async Playwright
and session fixtures defined in tests.base.conftest.
"""

from tests.base.conftest import *  # noqa: F401,F403
