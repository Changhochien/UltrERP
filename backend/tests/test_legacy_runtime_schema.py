from __future__ import annotations

import logging

import pytest
from alembic.util.exc import CommandError

from scripts import legacy_runtime_schema


def test_ensure_legacy_refresh_schema_current_runs_upgrade(monkeypatch) -> None:
    calls: list[tuple[object, str]] = []

    def fake_upgrade(config, revision: str) -> None:
        calls.append((config, revision))

    monkeypatch.setattr(legacy_runtime_schema.command, "upgrade", fake_upgrade)

    legacy_runtime_schema.ensure_legacy_refresh_schema_current()

    assert len(calls) == 1
    assert calls[0][1] == "head"


def test_ensure_legacy_refresh_schema_current_ignores_missing_revision(
    monkeypatch,
    caplog,
) -> None:
    def fake_upgrade(_config, _revision: str) -> None:
        raise CommandError("Can't locate revision identified by '7b9d2c4e6f1a'")

    monkeypatch.setattr(legacy_runtime_schema.command, "upgrade", fake_upgrade)

    with caplog.at_level(logging.WARNING):
        legacy_runtime_schema.ensure_legacy_refresh_schema_current()

    assert "orphaned revision" in caplog.text


def test_ensure_legacy_refresh_schema_current_raises_other_command_errors(
    monkeypatch,
) -> None:
    def fake_upgrade(_config, _revision: str) -> None:
        raise CommandError("database is locked")

    monkeypatch.setattr(legacy_runtime_schema.command, "upgrade", fake_upgrade)

    with pytest.raises(CommandError, match="database is locked"):
        legacy_runtime_schema.ensure_legacy_refresh_schema_current()