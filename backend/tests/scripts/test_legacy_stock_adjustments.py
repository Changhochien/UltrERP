from __future__ import annotations

import uuid
from datetime import date

from common.models.stock_adjustment import ReasonCode
from scripts._legacy_stock_adjustments import (
    ReconciliationRow,
    build_reconciliation_rows,
    build_snapshot_baseline_adjustments,
    tenant_scoped_uuid,
)

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
PRODUCT_ID = uuid.UUID("00000000-0000-0000-0000-000000000111")
WAREHOUSE_ID = uuid.UUID("00000000-0000-0000-0000-000000000211")


def test_build_snapshot_baseline_adjustments_closes_snapshot_gap() -> None:
    baseline_day = date(2026, 4, 30)
    row = ReconciliationRow(
        product_id=PRODUCT_ID,
        warehouse_id=WAREHOUSE_ID,
        expected_adjustment_sum=7,
        actual_stock=10,
        gap=-3,
        reason_breakdown={"SALES_RESERVATION": -5, "SUPPLIER_DELIVERY": 12},
    )

    payloads = build_snapshot_baseline_adjustments(
        [row],
        tenant_id=TENANT_ID,
        as_of_day=baseline_day,
    )

    assert len(payloads) == 1
    payload = payloads[0]
    assert payload.id == tenant_scoped_uuid(
        TENANT_ID,
        "legacy-snapshot-baseline",
        str(PRODUCT_ID),
        str(WAREHOUSE_ID),
    )
    assert payload.quantity_change == 3
    assert payload.reason_code == ReasonCode.LEGACY_SNAPSHOT_BASELINE.value
    assert payload.actor_id == "legacy-snapshot-baseline"
    assert "current_stock=10" in payload.notes


def test_build_snapshot_baseline_adjustments_updates_existing_baseline_to_zero() -> None:
    row = ReconciliationRow(
        product_id=PRODUCT_ID,
        warehouse_id=WAREHOUSE_ID,
        expected_adjustment_sum=10,
        actual_stock=7,
        gap=3,
        reason_breakdown={
            "SALES_RESERVATION": -5,
            "SUPPLIER_DELIVERY": 12,
            ReasonCode.LEGACY_SNAPSHOT_BASELINE.value: 3,
        },
    )

    payloads = build_snapshot_baseline_adjustments(
        [row],
        tenant_id=TENANT_ID,
        as_of_day=date(2026, 4, 30),
    )

    assert len(payloads) == 1
    assert payloads[0].quantity_change == 0


def test_snapshot_baseline_makes_reconciliation_match_inventory() -> None:
    movement_rows = [
        {
            "product_id": PRODUCT_ID,
            "warehouse_id": WAREHOUSE_ID,
            "reason_code": "SUPPLIER_DELIVERY",
            "quantity_total": 12,
        },
        {
            "product_id": PRODUCT_ID,
            "warehouse_id": WAREHOUSE_ID,
            "reason_code": "SALES_RESERVATION",
            "quantity_total": -5,
        },
    ]
    inventory_rows = [
        {"product_id": PRODUCT_ID, "warehouse_id": WAREHOUSE_ID, "current_stock": 10}
    ]
    rows = build_reconciliation_rows(
        adjustment_rows=movement_rows,
        inventory_rows=inventory_rows,
    )
    baseline = build_snapshot_baseline_adjustments(
        rows,
        tenant_id=TENANT_ID,
        as_of_day=date(2026, 4, 30),
    )[0]
    reconciled_rows = build_reconciliation_rows(
        adjustment_rows=[
            *movement_rows,
            {
                "product_id": baseline.product_id,
                "warehouse_id": baseline.warehouse_id,
                "reason_code": baseline.reason_code,
                "quantity_total": baseline.quantity_change,
            },
        ],
        inventory_rows=inventory_rows,
    )

    assert reconciled_rows[0].expected_adjustment_sum == 10
    assert reconciled_rows[0].gap == 0