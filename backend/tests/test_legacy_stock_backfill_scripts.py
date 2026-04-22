from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.dialects import postgresql

from common.models.stock_adjustment import ReasonCode
from scripts import _legacy_stock_adjustments as stock_backfill


def test_build_sales_adjustments_aggregates_by_product_warehouse_and_day() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000182")
    product_id = uuid.UUID("00000000-0000-0000-0000-000000000111")
    warehouse_a_id = uuid.UUID("00000000-0000-0000-0000-000000000211")
    warehouse_b_id = uuid.UUID("00000000-0000-0000-0000-000000000212")

    adjustments = stock_backfill.build_sales_adjustments(
        rows=[
            {
                "product_code": "LEG-P001",
                "warehouse_code": "WH-A",
                "invoice_date": "2024-08-27",
                "signed_qty": Decimal("2"),
            },
            {
                "product_code": "LEG-P001",
                "warehouse_code": "WH-A",
                "invoice_date": "2024-08-27",
                "signed_qty": Decimal("3"),
            },
            {
                "product_code": "LEG-P001",
                "warehouse_code": "WH-A",
                "invoice_date": "2024-08-27",
                "signed_qty": Decimal("-1"),
            },
            {
                "product_code": "LEG-P001",
                "warehouse_code": "WH-B",
                "invoice_date": "2024-08-27",
                "signed_qty": Decimal("4"),
            },
        ],
        tenant_id=tenant_id,
        product_by_code={"P001": product_id},
        warehouse_by_code={"WH-A": warehouse_a_id, "WH-B": warehouse_b_id},
        product_mappings={"LEG-P001": "P001"},
    )

    assert len(adjustments) == 2

    warehouse_a_adjustment = next(
        adjustment for adjustment in adjustments if adjustment.warehouse_id == warehouse_a_id
    )
    warehouse_b_adjustment = next(
        adjustment for adjustment in adjustments if adjustment.warehouse_id == warehouse_b_id
    )

    assert warehouse_a_adjustment.quantity_change == -4
    assert warehouse_a_adjustment.reason_code == ReasonCode.SALES_RESERVATION.value
    assert warehouse_a_adjustment.created_at == datetime(2024, 8, 27, tzinfo=UTC)
    assert "3 lines" in warehouse_a_adjustment.notes
    assert warehouse_a_adjustment.id == stock_backfill.tenant_scoped_uuid(
        tenant_id,
        "legacy-sales-adjustment",
        str(product_id),
        str(warehouse_a_id),
        date(2024, 8, 27).isoformat(),
    )

    assert warehouse_b_adjustment.quantity_change == -4
    assert warehouse_b_adjustment.created_at == datetime(2024, 8, 27, tzinfo=UTC)


def test_build_sales_adjustments_raises_for_unknown_warehouse() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000183")
    product_id = uuid.UUID("00000000-0000-0000-0000-000000000112")

    try:
        stock_backfill.build_sales_adjustments(
            rows=[
                {
                    "product_code": "LEG-P001",
                    "warehouse_code": "WH-MISSING",
                    "invoice_date": "2024-08-27",
                    "signed_qty": Decimal("2"),
                }
            ],
            tenant_id=tenant_id,
            product_by_code={"P001": product_id},
            warehouse_by_code={},
            product_mappings={"LEG-P001": "P001"},
        )
    except ValueError as exc:
        assert "WH-MISSING" in str(exc)
    else:
        raise AssertionError("Expected missing warehouse code to raise ValueError")


def test_build_sales_adjustments_coerces_fractional_totals_for_integer_schema() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000186")
    product_id = uuid.UUID("00000000-0000-0000-0000-000000000117")
    warehouse_id = uuid.UUID("00000000-0000-0000-0000-000000000217")

    adjustments = stock_backfill.build_sales_adjustments(
        rows=[
            {
                "product_code": "LEG-P001",
                "warehouse_code": "WH-A",
                "invoice_date": "2024-08-27",
                "signed_qty": Decimal("7.5"),
            }
        ],
        tenant_id=tenant_id,
        product_by_code={"P001": product_id},
        warehouse_by_code={"WH-A": warehouse_id},
        product_mappings={"LEG-P001": "P001"},
    )

    assert len(adjustments) == 1
    assert adjustments[0].quantity_change == -7
    assert "coerced from 7.5 to 7" in adjustments[0].notes


def test_stock_adjustment_upsert_uses_primary_key_conflict_update() -> None:
    payload = stock_backfill.StockAdjustmentPayload(
        id=uuid.UUID("00000000-0000-0000-0000-000000000190"),
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        product_id=uuid.UUID("00000000-0000-0000-0000-000000000111"),
        warehouse_id=uuid.UUID("00000000-0000-0000-0000-000000000211"),
        quantity_change=-5,
        reason_code=ReasonCode.SALES_RESERVATION.value,
        actor_id="backfill-script",
        notes="Legacy sales backfill (2 lines)",
        created_at=datetime(2024, 8, 27, tzinfo=UTC),
    )

    statement = stock_backfill.build_stock_adjustment_upsert(payload)
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (id) DO UPDATE" in compiled
    assert "quantity_change = excluded.quantity_change" in compiled
    assert "reason_code = excluded.reason_code" in compiled


def test_collapse_stock_adjustments_keeps_last_duplicate_payload() -> None:
    shared_id = uuid.UUID("00000000-0000-0000-0000-000000000191")
    first = stock_backfill.StockAdjustmentPayload(
        id=shared_id,
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        product_id=uuid.UUID("00000000-0000-0000-0000-000000000111"),
        warehouse_id=uuid.UUID("00000000-0000-0000-0000-000000000211"),
        quantity_change=3,
        reason_code=ReasonCode.SUPPLIER_DELIVERY.value,
        actor_id="legacy_import",
        notes="first",
        created_at=datetime(2024, 8, 27, tzinfo=UTC),
    )
    second = stock_backfill.StockAdjustmentPayload(
        id=shared_id,
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        product_id=uuid.UUID("00000000-0000-0000-0000-000000000111"),
        warehouse_id=uuid.UUID("00000000-0000-0000-0000-000000000211"),
        quantity_change=5,
        reason_code=ReasonCode.SUPPLIER_DELIVERY.value,
        actor_id="legacy_import",
        notes="second",
        created_at=datetime(2024, 8, 28, tzinfo=UTC),
    )

    collapsed = stock_backfill.collapse_stock_adjustments([first, second])

    assert len(collapsed) == 1
    assert collapsed[0].quantity_change == 5
    assert collapsed[0].notes == "second"


def test_build_purchase_receipt_adjustments_matches_canonical_contract() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000184")
    product_id = uuid.UUID("00000000-0000-0000-0000-000000000113")
    warehouse_id = uuid.UUID("00000000-0000-0000-0000-000000000213")

    adjustments = stock_backfill.build_purchase_receipt_adjustments(
        rows=[
            {
                "doc_number": "1130827001",
                "line_number": 1,
                "receipt_date": "2024-08-27",
                "invoice_date": "2024-08-28",
                "product_code": "LEG-P001",
                "warehouse_code": "WH-A",
                "qty": Decimal("3"),
            }
        ],
        tenant_id=tenant_id,
        product_by_code={"P001": product_id},
        warehouse_by_code={"WH-A": warehouse_id},
        product_mappings={"LEG-P001": "P001"},
    )

    assert len(adjustments) == 1
    assert adjustments[0].id == stock_backfill.tenant_scoped_uuid(
        tenant_id,
        "legacy-receiving-adjustment",
        "1130827001:1",
    )
    assert adjustments[0].quantity_change == 3
    assert adjustments[0].reason_code == ReasonCode.SUPPLIER_DELIVERY.value
    assert adjustments[0].actor_id == "legacy_import"
    assert adjustments[0].notes == "Legacy import: invoice 1130827001"
    assert adjustments[0].created_at == datetime(2024, 8, 27, tzinfo=UTC)


def test_build_purchase_receipt_adjustments_falls_back_to_header_invoice_date() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000185")
    product_id = uuid.UUID("00000000-0000-0000-0000-000000000114")
    warehouse_id = uuid.UUID("00000000-0000-0000-0000-000000000214")

    adjustments = stock_backfill.build_purchase_receipt_adjustments(
        rows=[
            {
                "doc_number": "1130827002",
                "line_number": 2,
                "receipt_date": "1900-01-01",
                "invoice_date": "2024-08-29",
                "product_code": "LEG-P001",
                "warehouse_code": "WH-A",
                "qty": Decimal("5"),
            }
        ],
        tenant_id=tenant_id,
        product_by_code={"P001": product_id},
        warehouse_by_code={"WH-A": warehouse_id},
        product_mappings={"LEG-P001": "P001"},
    )

    assert len(adjustments) == 1
    assert adjustments[0].created_at == datetime(2024, 8, 29, tzinfo=UTC)


def test_build_purchase_receipt_adjustments_falls_back_to_unknown_product() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000187")
    unknown_product_id = uuid.UUID("00000000-0000-0000-0000-000000000118")
    warehouse_id = uuid.UUID("00000000-0000-0000-0000-000000000218")

    adjustments = stock_backfill.build_purchase_receipt_adjustments(
        rows=[
            {
                "doc_number": "1130827003",
                "line_number": 3,
                "receipt_date": "2024-08-30",
                "invoice_date": "2024-08-30",
                "product_code": "LM047-5",
                "warehouse_code": "WH-A",
                "qty": Decimal("1"),
            }
        ],
        tenant_id=tenant_id,
        product_by_code={"UNKNOWN": unknown_product_id},
        warehouse_by_code={"WH-A": warehouse_id},
        product_mappings={},
    )

    assert len(adjustments) == 1
    assert adjustments[0].product_id == unknown_product_id
    assert "UNKNOWN product LM047-5" in adjustments[0].notes


def test_build_reconciliation_rows_uses_adjustment_sum_minus_current_stock() -> None:
    product_id = uuid.UUID("00000000-0000-0000-0000-000000000115")
    warehouse_id = uuid.UUID("00000000-0000-0000-0000-000000000215")

    rows = stock_backfill.build_reconciliation_rows(
        adjustment_rows=[
            {
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "reason_code": ReasonCode.SUPPLIER_DELIVERY.value,
                "quantity_total": 10,
            },
            {
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "reason_code": ReasonCode.SALES_RESERVATION.value,
                "quantity_total": -7,
            },
        ],
        inventory_rows=[
            {
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "current_stock": 1,
            }
        ],
    )

    assert len(rows) == 1
    assert rows[0].expected_adjustment_sum == 3
    assert rows[0].actual_stock == 1
    assert rows[0].gap == 2
    assert rows[0].reason_breakdown == {
        ReasonCode.SUPPLIER_DELIVERY.value: 10,
        ReasonCode.SALES_RESERVATION.value: -7,
    }


def test_build_reconciliation_rows_can_ignore_existing_corrections() -> None:
    product_id = uuid.UUID("00000000-0000-0000-0000-000000000117")
    warehouse_id = uuid.UUID("00000000-0000-0000-0000-000000000217")

    rows = stock_backfill.build_reconciliation_rows(
        adjustment_rows=[
            {
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "reason_code": ReasonCode.SUPPLIER_DELIVERY.value,
                "quantity_total": 10,
            },
            {
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "reason_code": ReasonCode.SALES_RESERVATION.value,
                "quantity_total": -7,
            },
            {
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "reason_code": ReasonCode.CORRECTION.value,
                "quantity_total": 5,
            },
        ],
        inventory_rows=[
            {
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "current_stock": 8,
            }
        ],
        ignored_reason_codes={ReasonCode.CORRECTION.value},
    )

    assert len(rows) == 1
    assert rows[0].expected_adjustment_sum == 3
    assert rows[0].actual_stock == 8
    assert rows[0].gap == -5
    assert rows[0].reason_breakdown == {
        ReasonCode.SUPPLIER_DELIVERY.value: 10,
        ReasonCode.SALES_RESERVATION.value: -7,
    }


def test_build_correction_adjustments_inverts_gap_with_deterministic_id() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    row = stock_backfill.ReconciliationRow(
        product_id=uuid.UUID("00000000-0000-0000-0000-000000000111"),
        warehouse_id=uuid.UUID("00000000-0000-0000-0000-000000000211"),
        expected_adjustment_sum=15,
        actual_stock=3,
        gap=12,
        reason_breakdown={
            ReasonCode.SUPPLIER_DELIVERY.value: 20,
            ReasonCode.SALES_RESERVATION.value: -5,
        },
    )

    corrections = stock_backfill.build_correction_adjustments(
        [row],
        tenant_id=tenant_id,
        as_of_day=date(2026, 4, 12),
        min_abs_gap=10,
    )

    assert len(corrections) == 1
    correction = corrections[0]
    assert correction.quantity_change == -12
    assert correction.reason_code == ReasonCode.CORRECTION.value
    assert correction.actor_id == "reconciliation-plan"
    assert correction.id == stock_backfill.tenant_scoped_uuid(
        tenant_id,
        "inventory-reconciliation-correction",
        str(row.product_id),
        str(row.warehouse_id),
        "2026-04-12",
    )
    assert "gap=12" in correction.notes


def test_format_reconciliation_table_includes_reason_breakdown() -> None:
    row = stock_backfill.ReconciliationRow(
        product_id=uuid.UUID("00000000-0000-0000-0000-000000000116"),
        warehouse_id=uuid.UUID("00000000-0000-0000-0000-000000000216"),
        expected_adjustment_sum=5,
        actual_stock=2,
        gap=3,
        reason_breakdown={
            ReasonCode.SUPPLIER_DELIVERY.value: 8,
            ReasonCode.SALES_RESERVATION.value: -3,
        },
    )

    table = stock_backfill.format_reconciliation_table([row])

    assert "expected_adjustment_sum" in table
    assert "SUPPLIER_DELIVERY=8" in table
    assert "SALES_RESERVATION=-3" in table
