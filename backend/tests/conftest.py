"""Root conftest — sets environment variables before any app imports."""

from __future__ import annotations

import os

from common.model_registry import register_all_models

# JWT_SECRET must be set before Settings is first accessed.
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long")
os.environ.setdefault("PYTEST_RUNNING", "1")

register_all_models()
