from __future__ import annotations

import importlib.util
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "f3b4c5d6e7f8_add_source_row_resolution_tables.py"
)


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("source_row_resolution_migration", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_creates_source_resolution_tables_and_backfill_guards(monkeypatch) -> None:
    module = _load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(module, "_table_exists", lambda _schema, _table: True)

    module.upgrade()

    assert any(
        "ADD PRIMARY KEY (" in statement
        and "source_row_number" in statement
        and "canonical_record_lineage" in statement
        for statement in executed
    )
    assert any("CREATE TABLE IF NOT EXISTS raw_legacy.source_row_resolution (" in statement for statement in executed)
    assert any(
        "CREATE TABLE IF NOT EXISTS raw_legacy.source_row_resolution_events (" in statement
        for statement in executed
    )
    assert any(
        "Resolved to multiple canonical targets; consult canonical_record_lineage." in statement
        and "COUNT(*) = 1 THEN MIN(lineage.canonical_table)" in statement
        for statement in executed
    )
    assert any(
        "present in both unsupported_history_holding and canonical_record_lineage" in statement
        for statement in executed
    )
    assert any(
        "INSERT INTO raw_legacy.source_row_resolution (" in statement
        and "FROM raw_legacy.unsupported_history_holding AS holding" in statement
        for statement in executed
    )
    assert any(
        "INSERT INTO raw_legacy.source_row_resolution (" in statement
        and "WITH lineage_state AS (" in statement
        for statement in executed
    )
    assert any(
        "INSERT INTO raw_legacy.source_row_resolution_events (" in statement
        and "source-resolution-backfill" in statement
        and "'holding'" in statement
        for statement in executed
    )
    assert any(
        "INSERT INTO raw_legacy.source_row_resolution_events (" in statement
        and "source-resolution-backfill" in statement
        and "'resolved'" in statement
        for statement in executed
    )


def test_downgrade_drops_source_resolution_tables_and_restores_old_pk(monkeypatch) -> None:
    module = _load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(module, "_table_exists", lambda _schema, _table: True)

    module.downgrade()

    assert executed[0].strip() == "DROP TABLE IF EXISTS raw_legacy.source_row_resolution_events;"
    assert executed[1].strip() == "DROP TABLE IF EXISTS raw_legacy.source_row_resolution;"
    assert "Downgrade cannot restore the previous canonical_record_lineage PK" in executed[2]
    assert "ADD PRIMARY KEY (" in executed[3]
    assert "source_identifier" in executed[3]
    assert "source_row_number" not in executed[3]


def test_upgrade_skips_lineage_backfill_when_runtime_tables_are_absent(monkeypatch) -> None:
    module = _load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(module, "_table_exists", lambda _schema, _table: False)

    module.upgrade()

    assert any("CREATE TABLE IF NOT EXISTS raw_legacy.source_row_resolution (" in statement for statement in executed)
    assert any(
        "CREATE TABLE IF NOT EXISTS raw_legacy.source_row_resolution_events (" in statement
        for statement in executed
    )
    assert not any(
        "canonical_record_lineage" in statement and "ADD PRIMARY KEY (" in statement
        for statement in executed
    )
    assert not any("WITH lineage_state AS (" in statement for statement in executed)
    assert not any(
        "FROM raw_legacy.unsupported_history_holding AS holding" in statement
        for statement in executed
    )