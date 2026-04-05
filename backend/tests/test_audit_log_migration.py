from __future__ import annotations

import importlib.util
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "qq777ss77t09_fix_audit_log_immutability.py"
)


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("audit_log_immutability_fix", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_replaces_silent_rules_with_trigger(monkeypatch) -> None:
    module = _load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed[0] == "DROP RULE IF EXISTS audit_log_no_delete ON audit_log;"
    assert executed[1] == "DROP RULE IF EXISTS audit_log_no_update ON audit_log;"
    assert executed[2] == "DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log;"
    assert "CREATE OR REPLACE FUNCTION audit_log_reject_mutation()" in executed[3]
    assert "RAISE EXCEPTION 'audit_log is append-only; % is not allowed'" in executed[3]
    assert "CREATE TRIGGER audit_log_immutable" in executed[4]
    assert "BEFORE UPDATE OR DELETE ON audit_log" in executed[4]


def test_downgrade_restores_previous_rules(monkeypatch) -> None:
    module = _load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == [
        "DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log;",
        "DROP FUNCTION IF EXISTS audit_log_reject_mutation();",
        "CREATE RULE audit_log_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING;",
        "CREATE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING;",
    ]
