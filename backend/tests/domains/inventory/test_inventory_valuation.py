from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from domains.inventory import services as inventory_services


class FakeRowsResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class FakeAsyncSession:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    async def execute(self, _statement: object) -> FakeRowsResult:
        return FakeRowsResult(self._rows)


def _valuation_row(
    *,
    product_code: str,
    product_name: str,
    warehouse_id: uuid.UUID,
    warehouse_name: str,
    quantity: int,
    standard_cost: Decimal | None = None,
    latest_purchase_unit_cost: Decimal | None = None,
) -> object:
    return SimpleNamespace(
        product_id=uuid.uuid4(),
        product_code=product_code,
        product_name=product_name,
        category="Hardware",
        warehouse_id=warehouse_id,
        warehouse_name=warehouse_name,
        quantity=quantity,
        standard_cost=standard_cost,
        latest_purchase_unit_cost=latest_purchase_unit_cost,
    )


@pytest.mark.asyncio
async def test_get_inventory_valuation_prefers_standard_cost_and_builds_warehouse_totals() -> None:
    main_warehouse_id = uuid.uuid4()
    overflow_warehouse_id = uuid.uuid4()
    session = FakeAsyncSession(
        [
            _valuation_row(
                product_code="VAL-001",
                product_name="Rotor",
                warehouse_id=main_warehouse_id,
                warehouse_name="Main Warehouse",
                quantity=4,
                standard_cost=Decimal("3.1250"),
                latest_purchase_unit_cost=Decimal("9.9900"),
            ),
            _valuation_row(
                product_code="VAL-002",
                product_name="Bracket",
                warehouse_id=overflow_warehouse_id,
                warehouse_name="Overflow",
                quantity=2,
                standard_cost=Decimal("2.5000"),
            ),
        ]
    )

    report = await inventory_services.get_inventory_valuation(session, uuid.uuid4())

    assert report["total_rows"] == 2
    assert report["grand_total_quantity"] == 6
    assert report["grand_total_value"] == Decimal("17.5000")

    first_item = report["items"][0]
    assert first_item["cost_source"] == "standard_cost"
    assert first_item["unit_cost"] == Decimal("3.1250")
    assert first_item["extended_value"] == Decimal("12.5000")

    warehouse_totals = {item["warehouse_id"]: item for item in report["warehouse_totals"]}
    assert warehouse_totals[main_warehouse_id]["total_quantity"] == 4
    assert warehouse_totals[main_warehouse_id]["total_value"] == Decimal("12.5000")
    assert warehouse_totals[overflow_warehouse_id]["total_quantity"] == 2
    assert warehouse_totals[overflow_warehouse_id]["total_value"] == Decimal("5.0000")


@pytest.mark.asyncio
async def test_get_inventory_valuation_uses_latest_purchase_fallback_and_keeps_missing_rows_visible() -> None:
    warehouse_id = uuid.uuid4()
    session = FakeAsyncSession(
        [
            _valuation_row(
                product_code="VAL-101",
                product_name="Bearing",
                warehouse_id=warehouse_id,
                warehouse_name="Main Warehouse",
                quantity=5,
                latest_purchase_unit_cost=Decimal("4.5000"),
            ),
            _valuation_row(
                product_code="VAL-102",
                product_name="Coupler",
                warehouse_id=warehouse_id,
                warehouse_name="Main Warehouse",
                quantity=7,
            ),
        ]
    )

    report = await inventory_services.get_inventory_valuation(session, uuid.uuid4(), warehouse_id=warehouse_id)

    assert report["total_rows"] == 2
    assert report["grand_total_quantity"] == 12
    assert report["grand_total_value"] == Decimal("22.5000")

    latest_purchase_row = report["items"][0]
    assert latest_purchase_row["cost_source"] == "latest_purchase"
    assert latest_purchase_row["unit_cost"] == Decimal("4.5000")
    assert latest_purchase_row["extended_value"] == Decimal("22.5000")

    missing_row = report["items"][1]
    assert missing_row["cost_source"] == "missing"
    assert missing_row["unit_cost"] is None
    assert missing_row["extended_value"] == Decimal("0.0000")

    assert report["warehouse_totals"][0]["row_count"] == 2
    assert report["warehouse_totals"][0]["total_value"] == Decimal("22.5000")