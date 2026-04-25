from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date
from pathlib import Path

from domains.legacy_import.canonical import CanonicalImportResult
from domains.legacy_import.mapping import (
    ProductMappingBatchResult,
    ProductMappingReviewExportResult,
)
from domains.legacy_import.normalization import NormalizationBatchResult
from domains.legacy_import.staging import (
    StageBatchResult,
    StageSourceDescriptor,
    StageTableResult,
)
from domains.legacy_import.validation import (
    ImportReplayMetadata,
    MigrationBatchValidationResult,
    MigrationValidationReport,
    ProductMappingValidationSummary,
)
from scripts.legacy_refresh_common import RefreshBatchMode
from scripts.refresh_sales_monthly import SalesMonthlyHistoryRefreshResult
from scripts import run_legacy_refresh as refresh

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _stage_result(batch_id: str) -> StageBatchResult:
    return StageBatchResult(
        batch_id=batch_id,
        schema_name="raw_legacy",
        source_descriptor=StageSourceDescriptor.live(
            database="cao50001",
            schema_name="public",
        ),
        tables=(
            StageTableResult(
                table_name="tbsslipx",
                row_count=10,
                column_count=5,
                source_file="public.tbsslipx",
            ),
        ),
    )


def _normalize_result(batch_id: str) -> NormalizationBatchResult:
    return NormalizationBatchResult(
        batch_id=batch_id,
        schema_name="raw_legacy",
        party_count=2,
        product_count=3,
        warehouse_count=1,
        inventory_count=4,
    )


def _mapping_result(batch_id: str, *, unknown_count: int) -> ProductMappingBatchResult:
    return ProductMappingBatchResult(
        batch_id=batch_id,
        schema_name="raw_legacy",
        mapping_count=5,
        candidate_count=2,
        exact_match_count=3,
        unknown_count=unknown_count,
        orphan_code_count=unknown_count,
        orphan_row_count=unknown_count * 2,
    )


def _canonical_result(batch_id: str, *, attempt_number: int = 3) -> CanonicalImportResult:
    return CanonicalImportResult(
        batch_id=batch_id,
        schema_name="raw_legacy",
        attempt_number=attempt_number,
        customer_count=2,
        product_count=3,
        warehouse_count=1,
        inventory_count=4,
        order_count=5,
        order_line_count=6,
        invoice_count=7,
        invoice_line_count=8,
        holding_count=0,
        lineage_count=9,
        supplier_count=1,
        supplier_invoice_count=2,
        supplier_invoice_line_count=3,
    )


def _validation_result(
    batch_id: str,
    artifacts_dir: Path,
    *,
    status: str = "passed",
    blocking_issue_count: int = 0,
    attempt_number: int = 3,
) -> MigrationBatchValidationResult:
    json_path = artifacts_dir / f"{batch_id}-validation.json"
    markdown_path = artifacts_dir / f"{batch_id}-validation.md"
    json_path.write_text("{}", encoding="utf-8")
    markdown_path.write_text("# validation\n", encoding="utf-8")
    report = MigrationValidationReport(
        batch_id=batch_id,
        tenant_id=str(TENANT_ID),
        schema_name="raw_legacy",
        attempt_number=attempt_number,
        status=status,
        blocking_issue_count=blocking_issue_count,
        stage_reconciliation=(),
        mapping_summary=ProductMappingValidationSummary(
            mapping_count=5,
            candidate_count=2,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        ),
        failed_stages=(),
        issues=(),
        replay=ImportReplayMetadata(
            scope_key="scope-001",
            scope_cutoff_date=None,
            disposition="new",
        ),
        epic13_handoff={
            "scope_key": "scope-001",
            "lineage_count": 9,
            "holding_count": 0,
            "boundary": "epic-13",
        },
    )
    return MigrationBatchValidationResult(
        report=report,
        json_path=json_path,
        markdown_path=markdown_path,
    )


def _sales_monthly_result(
    *,
    batch_mode: str = "full",
    affected_domains: tuple[str, ...] = (),
    skipped_reason: str | None = None,
) -> SalesMonthlyHistoryRefreshResult:
    return SalesMonthlyHistoryRefreshResult(
        batch_mode=batch_mode,
        affected_domains=affected_domains,
        start_month=None if skipped_reason else date(2024, 1, 1),
        end_month=None if skipped_reason else date(2026, 3, 1),
        refreshed_month_count=0 if skipped_reason else 27,
        total_upserted_row_count=0 if skipped_reason else 42,
        total_deleted_row_count=0,
        skipped_line_count=0,
        cleared_row_count=0,
        skipped_reason=skipped_reason,
    )


def test_run_legacy_refresh_orders_steps_and_marks_review_required(
    monkeypatch,
    tmp_path: Path,
) -> None:
    batch_id = "legacy-shadow-001"
    events: list[str] = []
    summary_root = tmp_path / "operations"
    validation_dir = tmp_path / "validation"
    validation_dir.mkdir()
    review_export_path = (
        summary_root
        / "product-review"
        / "raw_legacy-00000000-0000-0000-0000-000000000001-legacy-shadow-001-product-review.csv"
    )

    async def fake_live_stage_import(**kwargs):
        events.append("live-stage")
        assert kwargs["tenant_id"] == TENANT_ID
        return _stage_result(batch_id)

    async def fake_run_normalization(**kwargs):
        events.append("normalize")
        return _normalize_result(batch_id)

    async def fake_run_product_mapping_seed(**kwargs):
        events.append("map-products")
        return _mapping_result(batch_id, unknown_count=2)

    async def fake_export_product_mapping_review(**kwargs):
        events.append("export-product-review")
        assert kwargs["output_path"] == review_export_path
        kwargs["output_path"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["output_path"].write_text("legacy_code,target_code\n", encoding="utf-8")
        return ProductMappingReviewExportResult(
            batch_id=batch_id,
            schema_name="raw_legacy",
            output_path=kwargs["output_path"],
            exported_row_count=2,
        )

    async def fake_run_canonical_import(**kwargs):
        events.append("canonical-import")
        return _canonical_result(batch_id)

    async def fake_validate_import_batch(**kwargs):
        events.append("validate-import")
        return _validation_result(batch_id, validation_dir)

    async def fake_refresh_closed_sales_monthly_history(**kwargs):
        events.append("refresh_sales_monthly")
        assert kwargs["tenant_id"] == TENANT_ID
        return _sales_monthly_result()

    async def fake_backfill_purchase_receipts(
        *,
        lookback_days: int,
        dry_run: bool,
        tenant_id,
        entity_scope=None,
        affected_domains=None,
    ):
        events.append("backfill_purchase_receipts")
        assert lookback_days == 10000
        assert dry_run is False
        assert tenant_id == TENANT_ID
        assert entity_scope is None
        assert affected_domains is None

    async def fake_backfill_sales_reservations(
        *,
        lookback_days: int,
        dry_run: bool,
        tenant_id,
        entity_scope=None,
        affected_domains=None,
    ):
        events.append("backfill_sales_reservations")
        assert lookback_days == 10000
        assert dry_run is False
        assert tenant_id == TENANT_ID
        assert entity_scope is None
        assert affected_domains is None

    async def fake_verify_reconciliation(*, tenant_id):
        events.append("verify_reconciliation")
        assert tenant_id == TENANT_ID
        return 0

    monkeypatch.setattr(refresh, "run_live_stage_import", fake_live_stage_import)
    monkeypatch.setattr(refresh, "run_normalization", fake_run_normalization)
    monkeypatch.setattr(refresh, "run_product_mapping_seed", fake_run_product_mapping_seed)
    monkeypatch.setattr(
        refresh,
        "export_product_mapping_review",
        fake_export_product_mapping_review,
    )
    monkeypatch.setattr(refresh, "run_canonical_import", fake_run_canonical_import)
    monkeypatch.setattr(refresh, "validate_import_batch", fake_validate_import_batch)
    monkeypatch.setattr(
        refresh,
        "refresh_closed_sales_monthly_history",
        fake_refresh_closed_sales_monthly_history,
    )
    monkeypatch.setattr(refresh, "backfill_purchase_receipts", fake_backfill_purchase_receipts)
    monkeypatch.setattr(refresh, "backfill_sales_reservations", fake_backfill_sales_reservations)
    monkeypatch.setattr(refresh, "verify_reconciliation", fake_verify_reconciliation)

    execution = asyncio.run(
        refresh.run_legacy_refresh(
            batch_id=batch_id,
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=summary_root,
        )
    )

    assert execution.exit_code == 0
    assert events == [
        "live-stage",
        "normalize",
        "map-products",
        "export-product-review",
        "canonical-import",
        "validate-import",
        "refresh_sales_monthly",
        "backfill_purchase_receipts",
        "backfill_sales_reservations",
        "verify_reconciliation",
    ]
    assert execution.summary_path.exists()

    summary = json.loads(execution.summary_path.read_text(encoding="utf-8"))
    assert [step["name"] for step in summary["steps"]] == [
        "live-stage",
        "normalize",
        "map-products",
        "export-product-review",
        "import-product-review",
        "canonical-import",
        "validate-import",
        "refresh_sales_monthly",
        "sales_monthly_health_check",
        "backfill_purchase_receipts",
        "backfill_sales_reservations",
        "verify_reconciliation",
    ]
    assert summary["steps"][4]["status"] == "skipped"
    assert summary["analyst_review_required"] is True
    assert summary["analyst_review_imported"] is False
    assert summary["promotion_readiness"] is False
    assert summary["promotion_gate_status"]["analyst_review"]["status"] == "review-required"
    assert summary["promotion_gate_status"]["validation"]["status"] == "passed"
    assert summary["promotion_policy"]["classification"] == "exception-required"
    assert summary["promotion_policy"]["reason_codes"] == ["analyst-review"]
    assert summary["analyst_review_export_path"] == str(review_export_path)
    assert summary["canonical_attempt_number"] == 3
    assert summary["validation_json_path"].endswith(f"{batch_id}-validation.json")


def test_run_legacy_refresh_stops_after_blocked_validation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    batch_id = "legacy-shadow-002"
    events: list[str] = []
    validation_dir = tmp_path / "validation"
    validation_dir.mkdir()

    async def fake_live_stage_import(**kwargs):
        events.append("live-stage")
        return _stage_result(batch_id)

    async def fake_run_normalization(**kwargs):
        events.append("normalize")
        return _normalize_result(batch_id)

    async def fake_run_product_mapping_seed(**kwargs):
        events.append("map-products")
        return _mapping_result(batch_id, unknown_count=0)

    async def fake_run_canonical_import(**kwargs):
        events.append("canonical-import")
        return _canonical_result(batch_id)

    async def fake_validate_import_batch(**kwargs):
        events.append("validate-import")
        return _validation_result(
            batch_id,
            validation_dir,
            status="blocked",
            blocking_issue_count=2,
        )

    async def fail_sales_monthly(**kwargs):
        raise AssertionError("sales monthly refresh should not run after blocked validation")

    async def fail_backfill(**kwargs):
        raise AssertionError("backfill should not run after blocked validation")

    monkeypatch.setattr(refresh, "run_live_stage_import", fake_live_stage_import)
    monkeypatch.setattr(refresh, "run_normalization", fake_run_normalization)
    monkeypatch.setattr(refresh, "run_product_mapping_seed", fake_run_product_mapping_seed)
    monkeypatch.setattr(refresh, "run_canonical_import", fake_run_canonical_import)
    monkeypatch.setattr(refresh, "validate_import_batch", fake_validate_import_batch)
    monkeypatch.setattr(refresh, "refresh_closed_sales_monthly_history", fail_sales_monthly)
    monkeypatch.setattr(refresh, "backfill_purchase_receipts", fail_backfill)
    monkeypatch.setattr(refresh, "backfill_sales_reservations", fail_backfill)

    execution = asyncio.run(
        refresh.run_legacy_refresh(
            batch_id=batch_id,
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=tmp_path / "operations",
        )
    )

    summary = json.loads(execution.summary_path.read_text(encoding="utf-8"))

    assert execution.exit_code == 1
    assert events == [
        "live-stage",
        "normalize",
        "map-products",
        "canonical-import",
        "validate-import",
    ]
    assert summary["final_disposition"] == "validation-blocked"
    assert summary["promotion_readiness"] is False
    assert summary["failed_step"] is None
    assert summary["last_completed_step"] == "validate-import"
    assert summary["promotion_gate_status"]["validation"]["status"] == "blocked"
    assert summary["promotion_policy"]["classification"] == "blocked"
    assert summary["promotion_policy"]["reason_codes"] == ["validation"]
    assert summary["steps"][7]["status"] == "skipped"
    assert summary["steps"][8]["status"] == "skipped"
    assert summary["steps"][9]["status"] == "skipped"
    assert summary["steps"][10]["status"] == "skipped"


def test_run_legacy_refresh_blocks_on_reconciliation_threshold(
    monkeypatch,
    tmp_path: Path,
) -> None:
    batch_id = "legacy-shadow-003"
    events: list[str] = []
    validation_dir = tmp_path / "validation"
    validation_dir.mkdir()

    async def fake_live_stage_import(**kwargs):
        events.append("live-stage")
        return _stage_result(batch_id)

    async def fake_run_normalization(**kwargs):
        events.append("normalize")
        return _normalize_result(batch_id)

    async def fake_run_product_mapping_seed(**kwargs):
        events.append("map-products")
        return _mapping_result(batch_id, unknown_count=0)

    async def fake_run_canonical_import(**kwargs):
        events.append("canonical-import")
        return _canonical_result(batch_id)

    async def fake_validate_import_batch(**kwargs):
        events.append("validate-import")
        return _validation_result(batch_id, validation_dir)

    async def fake_refresh_closed_sales_monthly_history(**kwargs):
        events.append("refresh_sales_monthly")
        return _sales_monthly_result()

    async def fake_backfill_purchase_receipts(**kwargs):
        events.append("backfill_purchase_receipts")

    async def fake_backfill_sales_reservations(**kwargs):
        events.append("backfill_sales_reservations")

    async def fake_verify_reconciliation(**kwargs):
        events.append("verify_reconciliation")
        return 2

    monkeypatch.setattr(refresh, "run_live_stage_import", fake_live_stage_import)
    monkeypatch.setattr(refresh, "run_normalization", fake_run_normalization)
    monkeypatch.setattr(refresh, "run_product_mapping_seed", fake_run_product_mapping_seed)
    monkeypatch.setattr(refresh, "run_canonical_import", fake_run_canonical_import)
    monkeypatch.setattr(refresh, "validate_import_batch", fake_validate_import_batch)
    monkeypatch.setattr(
        refresh,
        "refresh_closed_sales_monthly_history",
        fake_refresh_closed_sales_monthly_history,
    )
    monkeypatch.setattr(refresh, "backfill_purchase_receipts", fake_backfill_purchase_receipts)
    monkeypatch.setattr(refresh, "backfill_sales_reservations", fake_backfill_sales_reservations)
    monkeypatch.setattr(refresh, "verify_reconciliation", fake_verify_reconciliation)

    execution = asyncio.run(
        refresh.run_legacy_refresh(
            batch_id=batch_id,
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=tmp_path / "operations",
        )
    )

    summary = json.loads(execution.summary_path.read_text(encoding="utf-8"))

    assert execution.exit_code == 1
    assert events[-4:] == [
        "refresh_sales_monthly",
        "backfill_purchase_receipts",
        "backfill_sales_reservations",
        "verify_reconciliation",
    ]
    assert summary["final_disposition"] == "reconciliation-blocked"
    assert summary["reconciliation_gap_count"] == 2
    assert summary["promotion_gate_status"]["reconciliation"]["status"] == "blocked"
    assert summary["failed_step"] is None
    assert summary["last_completed_step"] == "verify_reconciliation"


def test_run_legacy_refresh_records_partial_failure_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    batch_id = "legacy-shadow-004"
    events: list[str] = []

    async def fake_live_stage_import(**kwargs):
        events.append("live-stage")
        return _stage_result(batch_id)

    async def fake_run_normalization(**kwargs):
        events.append("normalize")
        raise RuntimeError("normalize exploded")

    monkeypatch.setattr(refresh, "run_live_stage_import", fake_live_stage_import)
    monkeypatch.setattr(refresh, "run_normalization", fake_run_normalization)

    execution = asyncio.run(
        refresh.run_legacy_refresh(
            batch_id=batch_id,
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=tmp_path / "operations",
        )
    )

    summary = json.loads(execution.summary_path.read_text(encoding="utf-8"))

    assert execution.exit_code == 1
    assert events == ["live-stage", "normalize"]
    assert summary["final_disposition"] == "failed"
    assert summary["failed_step"] == "normalize"
    assert summary["last_completed_step"] == "live-stage"
    assert summary["promotion_readiness"] is False
    assert summary["steps"][1]["status"] == "failed"
    assert summary["steps"][1]["error"] == "normalize exploded"
    assert summary["steps"][2]["status"] == "skipped"


def test_run_legacy_refresh_same_batch_rerun_writes_new_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    batch_id = "legacy-shadow-005"
    validation_dir = tmp_path / "validation"
    validation_dir.mkdir()

    async def fake_live_stage_import(**kwargs):
        return _stage_result(batch_id)

    async def fake_run_normalization(**kwargs):
        return _normalize_result(batch_id)

    async def fake_run_product_mapping_seed(**kwargs):
        return _mapping_result(batch_id, unknown_count=0)

    async def fake_run_canonical_import(**kwargs):
        return _canonical_result(batch_id)

    async def fake_validate_import_batch(**kwargs):
        return _validation_result(batch_id, validation_dir)

    async def fake_refresh_closed_sales_monthly_history(**kwargs):
        return _sales_monthly_result()

    async def fake_backfill_purchase_receipts(**kwargs):
        return None

    async def fake_backfill_sales_reservations(**kwargs):
        return None

    async def fake_verify_reconciliation(**kwargs):
        return 0

    monkeypatch.setattr(refresh, "run_live_stage_import", fake_live_stage_import)
    monkeypatch.setattr(refresh, "run_normalization", fake_run_normalization)
    monkeypatch.setattr(refresh, "run_product_mapping_seed", fake_run_product_mapping_seed)
    monkeypatch.setattr(refresh, "run_canonical_import", fake_run_canonical_import)
    monkeypatch.setattr(refresh, "validate_import_batch", fake_validate_import_batch)
    monkeypatch.setattr(
        refresh,
        "refresh_closed_sales_monthly_history",
        fake_refresh_closed_sales_monthly_history,
    )
    monkeypatch.setattr(refresh, "backfill_purchase_receipts", fake_backfill_purchase_receipts)
    monkeypatch.setattr(refresh, "backfill_sales_reservations", fake_backfill_sales_reservations)
    monkeypatch.setattr(refresh, "verify_reconciliation", fake_verify_reconciliation)

    summary_root = tmp_path / "operations"

    first_execution = asyncio.run(
        refresh.run_legacy_refresh(
            batch_id=batch_id,
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=summary_root,
        )
    )
    second_execution = asyncio.run(
        refresh.run_legacy_refresh(
            batch_id=batch_id,
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=summary_root,
        )
    )

    first_summary = json.loads(first_execution.summary_path.read_text(encoding="utf-8"))
    second_summary = json.loads(second_execution.summary_path.read_text(encoding="utf-8"))

    assert first_execution.exit_code == 0
    assert second_execution.exit_code == 0
    assert first_execution.summary_path != second_execution.summary_path
    assert first_execution.summary_path.exists()
    assert second_execution.summary_path.exists()
    assert first_summary["batch_id"] == batch_id
    assert second_summary["batch_id"] == batch_id
    assert first_summary["orchestrator_run_id"] != second_summary["orchestrator_run_id"]


def test_run_legacy_refresh_marks_the_actual_failed_backfill_step(
    monkeypatch,
    tmp_path: Path,
) -> None:
    batch_id = "legacy-shadow-006"
    validation_dir = tmp_path / "validation"
    validation_dir.mkdir()

    async def fake_live_stage_import(**kwargs):
        return _stage_result(batch_id)

    async def fake_run_normalization(**kwargs):
        return _normalize_result(batch_id)

    async def fake_run_product_mapping_seed(**kwargs):
        return _mapping_result(batch_id, unknown_count=0)

    async def fake_run_canonical_import(**kwargs):
        return _canonical_result(batch_id)

    async def fake_validate_import_batch(**kwargs):
        return _validation_result(batch_id, validation_dir)

    async def fake_refresh_closed_sales_monthly_history(**kwargs):
        return _sales_monthly_result()

    async def fake_backfill_purchase_receipts(**kwargs):
        return None

    async def fake_backfill_sales_reservations(**kwargs):
        raise RuntimeError("sales backfill exploded")

    monkeypatch.setattr(refresh, "run_live_stage_import", fake_live_stage_import)
    monkeypatch.setattr(refresh, "run_normalization", fake_run_normalization)
    monkeypatch.setattr(refresh, "run_product_mapping_seed", fake_run_product_mapping_seed)
    monkeypatch.setattr(refresh, "run_canonical_import", fake_run_canonical_import)
    monkeypatch.setattr(refresh, "validate_import_batch", fake_validate_import_batch)
    monkeypatch.setattr(
        refresh,
        "refresh_closed_sales_monthly_history",
        fake_refresh_closed_sales_monthly_history,
    )
    monkeypatch.setattr(refresh, "backfill_purchase_receipts", fake_backfill_purchase_receipts)
    monkeypatch.setattr(refresh, "backfill_sales_reservations", fake_backfill_sales_reservations)

    execution = asyncio.run(
        refresh.run_legacy_refresh(
            batch_id=batch_id,
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=tmp_path / "operations",
        )
    )

    summary = json.loads(execution.summary_path.read_text(encoding="utf-8"))

    assert execution.exit_code == 1
    assert summary["failed_step"] == "backfill_sales_reservations"
    assert summary["steps"][8]["status"] == "completed"  # sales_monthly_health_check
    assert summary["steps"][10]["status"] == "failed"  # backfill_sales_reservations
    assert summary["steps"][10]["error"] == "sales backfill exploded"


def test_run_legacy_refresh_uses_rolling_sales_monthly_upkeep_for_incremental_scope(
    monkeypatch,
    tmp_path: Path,
) -> None:
    batch_id = "legacy-incremental-001"
    validation_dir = tmp_path / "validation"
    validation_dir.mkdir()

    async def fake_live_stage_import(**kwargs):
        return _stage_result(batch_id)

    async def fake_run_normalization(**kwargs):
        return _normalize_result(batch_id)

    async def fake_run_product_mapping_seed(**kwargs):
        return _mapping_result(batch_id, unknown_count=0)

    async def fake_run_canonical_import(**kwargs):
        return _canonical_result(batch_id)

    async def fake_validate_import_batch(**kwargs):
        return _validation_result(batch_id, validation_dir)

    async def fake_refresh_closed_sales_monthly_history(**kwargs):
        assert kwargs["batch_mode"] == RefreshBatchMode.INCREMENTAL
        assert kwargs["affected_domains"] == ("products",)
        assert kwargs["rolling_closed_months"] == (
            refresh.INCREMENTAL_SALES_MONTHLY_ROLLING_CLOSED_MONTHS
        )
        return _sales_monthly_result(
            batch_mode="incremental",
            affected_domains=("products",),
        )

    async def fake_backfill_purchase_receipts(**kwargs):
        return None

    async def fake_backfill_sales_reservations(**kwargs):
        return None

    async def fake_verify_reconciliation(**kwargs):
        return 0

    monkeypatch.setattr(refresh, "run_live_stage_import", fake_live_stage_import)
    monkeypatch.setattr(refresh, "run_normalization", fake_run_normalization)
    monkeypatch.setattr(refresh, "run_product_mapping_seed", fake_run_product_mapping_seed)
    monkeypatch.setattr(refresh, "run_canonical_import", fake_run_canonical_import)
    monkeypatch.setattr(refresh, "validate_import_batch", fake_validate_import_batch)
    monkeypatch.setattr(
        refresh,
        "refresh_closed_sales_monthly_history",
        fake_refresh_closed_sales_monthly_history,
    )
    monkeypatch.setattr(refresh, "backfill_purchase_receipts", fake_backfill_purchase_receipts)
    monkeypatch.setattr(refresh, "backfill_sales_reservations", fake_backfill_sales_reservations)
    monkeypatch.setattr(refresh, "verify_reconciliation", fake_verify_reconciliation)

    execution = asyncio.run(
        refresh.run_legacy_refresh(
            batch_id=batch_id,
            tenant_id=TENANT_ID,
            schema_name="raw_legacy",
            source_schema="public",
            lookback_days=10000,
            reconciliation_threshold=0,
            summary_root=tmp_path / "operations",
            batch_mode=RefreshBatchMode.INCREMENTAL,
            affected_domains=("products",),
        )
    )

    summary = json.loads(execution.summary_path.read_text(encoding="utf-8"))
    sales_step = next(
        step for step in summary["steps"] if step["name"] == "refresh_sales_monthly"
    )

    assert execution.exit_code == 0
    assert sales_step["status"] == "completed"
    assert sales_step["details"]["affected_domains"] == ["products"]
    assert sales_step["details"]["rolling_closed_months"] == 3