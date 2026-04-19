from __future__ import annotations

import importlib.util
from contextlib import nullcontext
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "15d9e4c2b7a1_normalize_sales_reservation_reason_code_enum.py"
)


class _FakeContext:
    def autocommit_block(self):
        return nullcontext()


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("sales_reservation_reason_code_enum_migration", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_renames_lowercase_sales_reservation_label(monkeypatch) -> None:
    module = _load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module, "_enum_labels", lambda _name: {"sales_reservation"})
    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(module.op, "get_context", lambda: _FakeContext())

    module.upgrade()

    assert executed == [
        "ALTER TYPE reason_code_enum RENAME VALUE 'sales_reservation' TO 'SALES_RESERVATION'"
    ]


def test_upgrade_adds_uppercase_sales_reservation_label_when_missing(monkeypatch) -> None:
    module = _load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module, "_enum_labels", lambda _name: {"RECEIVED", "DAMAGED"})
    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(module.op, "get_context", lambda: _FakeContext())

    module.upgrade()

    assert executed == [
        "ALTER TYPE reason_code_enum ADD VALUE IF NOT EXISTS 'SALES_RESERVATION'"
    ]