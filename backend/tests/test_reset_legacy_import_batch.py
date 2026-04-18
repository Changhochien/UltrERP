from __future__ import annotations

from scripts import reset_legacy_import_batch as reset_batch


def test_build_reset_plan_orders_lineaged_tables_before_control_rows() -> None:
    plan = reset_batch.build_reset_plan(
        lineage_counts={
            "orders": 3,
            "order_lines": 7,
            "stock_adjustment": 4,
            "warehouse": 1,
        },
        resolution_state_count=2,
        resolution_event_count=5,
        holding_count=2,
        lineage_count=9,
        step_run_count=5,
        run_count=1,
        extra_counts={"sales_backfill": 6, "correction_rows": 0},
        include_sales_backfill=True,
        include_correction_rows=False,
    )

    assert [item.label for item in plan] == [
        "order_lines",
        "stock_adjustment",
        "sales_backfill",
        "orders",
        "warehouse",
        "source_row_resolution_events",
        "source_row_resolution",
        "unsupported_history_holding",
        "canonical_record_lineage",
        "canonical_import_step_runs",
        "canonical_import_runs",
    ]
    assert plan[0].batch_scoped is True
    assert plan[2].batch_scoped is False


def test_build_reset_plan_omits_optional_extra_slices_when_disabled() -> None:
    plan = reset_batch.build_reset_plan(
        lineage_counts={"inventory_stock": 5},
        resolution_state_count=0,
        resolution_event_count=0,
        holding_count=0,
        lineage_count=5,
        step_run_count=1,
        run_count=1,
        extra_counts={"sales_backfill": 4, "correction_rows": 3},
        include_sales_backfill=False,
        include_correction_rows=False,
    )

    assert [item.label for item in plan] == [
        "inventory_stock",
        "canonical_record_lineage",
        "canonical_import_step_runs",
        "canonical_import_runs",
    ]