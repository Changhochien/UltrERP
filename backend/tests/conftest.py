"""Root conftest — sets environment variables before any app imports."""

from __future__ import annotations

import os

# JWT_SECRET must be set before Settings is first accessed.
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long")
