from __future__ import annotations

import importlib.util
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "16a4c9e7b2d3_add_order_discount_columns.py"
)


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("order_discount_columns_migration", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_adds_and_backfills_missing_order_discount_columns(monkeypatch) -> None:
    module = _load_migration_module()
    added_columns: list[tuple[str, str]] = []
    executed: list[str] = []
    altered_columns: list[tuple[str, str, dict[str, object]]] = []

    monkeypatch.setattr(module, "_column_exists", lambda _table, _column: False)
    monkeypatch.setattr(
        module.op,
        "add_column",
        lambda table_name, column: added_columns.append((table_name, column.name)),
    )
    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(
        module.op,
        "alter_column",
        lambda table_name, column_name, **kwargs: altered_columns.append(
            (table_name, column_name, kwargs)
        ),
    )

    module.upgrade()

    assert added_columns == [
        ("orders", "discount_amount"),
        ("orders", "discount_percent"),
    ]
    assert executed == [
        "UPDATE orders SET discount_amount = COALESCE(discount_amount, 0.00);",
        "UPDATE orders SET discount_percent = COALESCE(discount_percent, 0.0000);",
    ]
    assert [column_name for _, column_name, _ in altered_columns] == [
        "discount_amount",
        "discount_percent",
    ]


def test_upgrade_backfills_existing_nullable_order_discount_columns(monkeypatch) -> None:
    module = _load_migration_module()
    added_columns: list[tuple[str, str]] = []
    executed: list[str] = []
    altered_columns: list[tuple[str, str, dict[str, object]]] = []

    monkeypatch.setattr(module, "_column_exists", lambda _table, _column: True)
    monkeypatch.setattr(
        module.op,
        "add_column",
        lambda table_name, column: added_columns.append((table_name, column.name)),
    )
    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(
        module.op,
        "alter_column",
        lambda table_name, column_name, **kwargs: altered_columns.append(
            (table_name, column_name, kwargs)
        ),
    )

    module.upgrade()

    assert added_columns == []
    assert executed == [
        "UPDATE orders SET discount_amount = COALESCE(discount_amount, 0.00);",
        "UPDATE orders SET discount_percent = COALESCE(discount_percent, 0.0000);",
    ]
    assert [column_name for _, column_name, _ in altered_columns] == [
        "discount_amount",
        "discount_percent",
    ]


def test_downgrade_drops_order_discount_columns_when_present(monkeypatch) -> None:
    module = _load_migration_module()
    dropped_columns: list[tuple[str, str]] = []

    monkeypatch.setattr(module, "_column_exists", lambda _table, _column: True)
    monkeypatch.setattr(
        module.op,
        "drop_column",
        lambda table_name, column_name: dropped_columns.append((table_name, column_name)),
    )

    module.downgrade()

    assert dropped_columns == [
        ("orders", "discount_percent"),
        ("orders", "discount_amount"),
    ]