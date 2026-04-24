"""Helpers for keeping routine legacy-refresh entrypoints on the current schema."""

from __future__ import annotations

import logging

from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError

from common.config import PROJECT_ROOT


_LOGGER = logging.getLogger(__name__)


def build_alembic_config() -> Config:
    return Config(str(PROJECT_ROOT / "migrations" / "alembic.ini"))


def _is_missing_revision_error(exc: CommandError) -> bool:
    return "Can't locate revision identified by" in str(exc)


def ensure_legacy_refresh_schema_current() -> None:
    try:
        command.upgrade(build_alembic_config(), "head")
    except CommandError as exc:
        if not _is_missing_revision_error(exc):
            raise
        _LOGGER.warning(
            "Skipping legacy refresh Alembic preflight because the database is pinned "
            "to an orphaned revision outside the current repo history: %s. "
            "Refresh-owned support tables are created at runtime, so the routine can "
            "continue, but the application Alembic state still needs operator repair.",
            exc,
        )