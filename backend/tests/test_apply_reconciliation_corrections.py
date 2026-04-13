from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from scripts import apply_reconciliation_corrections as apply_script


def test_select_approved_candidates_rejects_review_only_rows() -> None:
    rows = [
        {
            "disposition": "review_only",
            "approval_action": "apply",
            "product_code": "0000",
            "product_id": str(uuid.uuid4()),
        }
    ]

    with pytest.raises(ValueError, match="cannot be auto-applied"):
        apply_script.select_approved_candidates(rows)


def test_build_approved_corrections_uses_deterministic_id_and_apply_actor() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    product_id = uuid.UUID("00000000-0000-0000-0000-000000000111")
    warehouse_id = uuid.UUID("00000000-0000-0000-0000-000000000211")
    as_of_day = "2025-06-10"
    correction_id = apply_script.tenant_scoped_uuid(
        tenant_id,
        "inventory-reconciliation-correction",
        str(product_id),
        str(warehouse_id),
        as_of_day,
    )

    payloads = apply_script.build_approved_corrections(
        [
            {
                "disposition": "actionable",
                "approval_action": "apply",
                "product_id": str(product_id),
                "warehouse_id": str(warehouse_id),
                "gap": "12",
                "expected_adjustment_sum": "15",
                "actual_stock": "3",
                "proposed_quantity_change": "-12",
                "correction_id": str(correction_id),
                "reason_breakdown": "SUPPLIER_DELIVERY=20, SALES_RESERVATION=-5",
                "as_of_day": as_of_day,
            }
        ],
        tenant_id=tenant_id,
        approved_by="ops-user",
    )

    assert len(payloads) == 1
    payload = payloads[0]
    assert payload.id == correction_id
    assert payload.actor_id == "reconciliation-apply"
    assert payload.quantity_change == -12
    assert "Approved inventory reconciliation correction by ops-user" in payload.notes


def test_load_correction_candidates_requires_approval_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "invalid.csv"
    csv_path.write_text("product_id,warehouse_id\n1,2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns"):
        apply_script.load_correction_candidates(csv_path)