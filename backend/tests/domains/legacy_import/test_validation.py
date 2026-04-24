from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from domains.legacy_import import validation


class FakeValidationConnection:
    def __init__(self, rows_by_key: dict[str, object]) -> None:
        self.rows_by_key = rows_by_key
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.fetchrow_calls: list[tuple[str, tuple[object, ...]]] = []
        self.closed = False

    async def fetchrow(self, query: str, *args: object):
        self.fetchrow_calls.append((query, args))
        if "FROM legacy_import_runs" in query:
            return self.rows_by_key.get("stage_run")
        if 'FROM "raw_legacy".canonical_import_runs' in query:
            if "summary->>'scope_key'" in query:
                return self.rows_by_key.get("previous_scope_run")
            return self.rows_by_key.get("canonical_run")
        if 'FROM "raw_legacy".canonical_record_lineage AS lineage' in query:
            return self.rows_by_key.get("snapshot_coverage")
        return None

    async def fetch(self, query: str, *args: object):
        if "FROM legacy_import_table_runs" in query:
            return self.rows_by_key.get("stage_tables", [])
        if 'FROM "raw_legacy".canonical_import_step_runs' in query:
            return self.rows_by_key.get("canonical_steps", [])
        if 'FROM "raw_legacy".source_row_resolution' in query:
            return self.rows_by_key.get("resolution_status_counts", [])
        if "FROM customers" in query and "GROUP BY customer_type" in query:
            return self.rows_by_key.get("customer_type_counts", [])
        if "SELECT col_3 AS invoice_date_raw" in query:
            cutoff_rows = self.rows_by_key.get("cutoff_rows")
            if cutoff_rows is not None:
                return cutoff_rows
            cutoff_date = self.rows_by_key.get("cutoff_date")
            if cutoff_date is None:
                return []
            return [{"invoice_date_raw": cutoff_date.isoformat()}]
        return []

    async def fetchval(self, query: str, *args: object):
        if "COUNT(*) FILTER (WHERE resolution_type = 'unknown')" in query:
            return None
        if "MAX(invoice_date)" in query:
            return self.rows_by_key.get("cutoff_date")
        return None

    async def execute(self, query: str, *args: object) -> str:
        self.execute_calls.append((query, args))
        return "OK"

    async def close(self) -> None:
        self.closed = True


class CutoffQueryConnection:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.queries: list[str] = []

    async def fetch(self, query: str, *args: object):
        self.queries.append(query)
        return self.rows


def test_coerce_row_parses_json_object_strings() -> None:
    assert validation._coerce_row('{"lineage_count": 3, "holding_count": 0}') == {
        "lineage_count": 3,
        "holding_count": 0,
    }


@pytest.mark.asyncio
async def test_validate_import_batch_blocks_on_severity1_and_keeps_severity2_visible(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000001550")
    connection = FakeValidationConnection(
        {
            "stage_run": {"id": uuid.uuid4(), "attempt_number": 1, "status": "completed"},
            "stage_tables": [
                {
                    "table_name": "tbscust",
                    "source_file": "tbscust.csv",
                    "expected_row_count": 10,
                    "loaded_row_count": 10,
                    "status": "completed",
                    "error_message": None,
                },
                {
                    "table_name": "tbsslipdtx",
                    "source_file": "tbsslipdtx.csv",
                    "expected_row_count": 5,
                    "loaded_row_count": 4,
                    "status": "completed",
                    "error_message": None,
                },
            ],
            "canonical_run": {
                "id": uuid.uuid4(),
                "attempt_number": 2,
                "status": "failed",
                "summary": {
                    "customer_count": 1,
                    "product_count": 2,
                    "warehouse_count": 1,
                    "inventory_count": 1,
                    "order_count": 1,
                    "order_line_count": 1,
                    "invoice_count": 1,
                    "invoice_line_count": 1,
                    "holding_count": 0,
                    "lineage_count": 6,
                },
            },
            "canonical_steps": [
                {
                    "step_name": "customers",
                    "row_count": 1,
                    "status": "completed",
                    "error_message": None,
                },
                {
                    "step_name": "sales_history",
                    "row_count": 1,
                    "status": "failed",
                    "error_message": "missing customer mapping",
                },
            ],
            "previous_scope_run": {
                "id": uuid.uuid4(),
                "batch_id": "batch-154",
                "attempt_number": 1,
                "status": "completed",
            },
            "snapshot_coverage": {
                "order_count": 1,
                "order_snapshot_count": 1,
                "invoice_count": 1,
                "invoice_snapshot_count": 1,
                "supplier_invoice_count": 0,
                "supplier_invoice_snapshot_count": 0,
            },
            "resolution_status_counts": [
                {"status": "holding", "row_count": 2},
                {"status": "resolved", "row_count": 6},
            ],
            "cutoff_date": date(2024, 8, 31),
        }
    )

    async def fake_open_raw_connection() -> FakeValidationConnection:
        return connection

    async def fake_fetch_mapping_summary(*args, **kwargs):
        return validation.ProductMappingValidationSummary(
            mapping_count=3,
            candidate_count=1,
            unknown_count=1,
            orphan_code_count=1,
            orphan_row_count=2,
        )

    monkeypatch.setattr(validation, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(validation, "_fetch_product_mapping_summary", fake_fetch_mapping_summary)

    result = await validation.validate_import_batch(
        batch_id="batch-155",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        output_dir=tmp_path,
    )

    assert result.report.status == "blocked"
    assert result.report.replay.disposition == "replayed-scope"
    assert result.report.replay.previous_batch_id == "batch-154"
    assert result.report.replay.previous_status == "completed"
    assert [issue.severity for issue in result.report.issues] == [1, 1, 2]
    assert result.json_path.exists()
    assert result.markdown_path.exists()

    report_payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert report_payload["status"] == "blocked"
    assert report_payload["replay"]["scope_cutoff_date"] == "2024-08-31"
    assert report_payload["counts"]["resolution_holding_count"] == 2
    assert report_payload["epic13_handoff"]["scope_key"] == result.report.replay.scope_key
    assert report_payload["epic13_handoff"]["resolution_status_counts"] == {
        "resolution_holding_count": 2,
        "resolution_resolved_count": 6,
    }
    assert report_payload["issues"][2]["code"] == "unresolved-product-mappings"
    assert "Severity 1" in result.markdown_path.read_text(encoding="utf-8")

    update_call = next(
        args
        for query, args in connection.execute_calls
        if 'UPDATE "raw_legacy".canonical_import_runs' in query
    )
    stored_summary = json.loads(update_call[1])
    assert stored_summary["validation_status"] == "blocked"
    assert stored_summary["replay"]["previous_batch_id"] == "batch-154"
    assert stored_summary["replay"]["previous_status"] == "completed"
    assert connection.closed is True


@pytest.mark.asyncio
async def test_validate_import_batch_marks_clean_replayed_scope_success(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000001551")
    connection = FakeValidationConnection(
        {
            "stage_run": {"id": uuid.uuid4(), "attempt_number": 2, "status": "completed"},
            "stage_tables": [
                {
                    "table_name": "tbscust",
                    "source_file": "tbscust.csv",
                    "expected_row_count": 10,
                    "loaded_row_count": 10,
                    "status": "completed",
                    "error_message": None,
                },
            ],
            "canonical_run": {
                "id": uuid.uuid4(),
                "attempt_number": 3,
                "status": "completed",
                "summary": {
                    "customer_count": 1,
                    "product_count": 1,
                    "warehouse_count": 1,
                    "inventory_count": 1,
                    "order_count": 0,
                    "order_line_count": 0,
                    "invoice_count": 0,
                    "invoice_line_count": 0,
                    "holding_count": 0,
                    "lineage_count": 3,
                },
            },
            "customer_type_counts": [
                {"customer_type": "dealer", "customer_count": 2},
                {"customer_type": "unknown", "customer_count": 1},
            ],
            "canonical_steps": [
                {
                    "step_name": "customers",
                    "row_count": 1,
                    "status": "completed",
                    "error_message": None,
                },
            ],
            "previous_scope_run": {
                "id": uuid.uuid4(),
                "batch_id": "batch-155-prev",
                "attempt_number": 1,
                "status": "completed",
            },
            "snapshot_coverage": {
                "order_count": 0,
                "order_snapshot_count": 0,
                "invoice_count": 0,
                "invoice_snapshot_count": 0,
                "supplier_invoice_count": 0,
                "supplier_invoice_snapshot_count": 0,
            },
            "resolution_status_counts": [
                {"status": "resolved", "row_count": 3},
            ],
            "cutoff_date": date(2024, 8, 31),
        }
    )

    async def fake_open_raw_connection() -> FakeValidationConnection:
        return connection

    async def fake_fetch_mapping_summary(*args, **kwargs):
        return validation.ProductMappingValidationSummary(
            mapping_count=1,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        )

    monkeypatch.setattr(validation, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(validation, "_fetch_product_mapping_summary", fake_fetch_mapping_summary)

    result = await validation.validate_import_batch(
        batch_id="batch-155-rerun",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        output_dir=tmp_path,
    )

    assert result.report.status == "clean"
    assert result.report.replay.disposition == "replayed-scope"
    assert result.report.blocking_issue_count == 0
    assert result.report.epic13_handoff["lineage_count"] == 3
    assert result.report.epic13_handoff["resolution_status_counts"] == {
        "resolution_resolved_count": 3,
    }
    assert result.report.counts["customer_type_dealer_count"] == 2
    assert result.report.counts["customer_type_unknown_count"] == 1
    assert result.report.counts["resolution_resolved_count"] == 3
    assert result.json_path.exists()
    assert result.markdown_path.exists()

    report_payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert report_payload["counts"]["customer_type_dealer_count"] == 2


@pytest.mark.asyncio
async def test_validate_import_batch_blocks_failed_canonical_run_without_failed_steps(
    monkeypatch,
    tmp_path: Path,
) -> None:
    connection = FakeValidationConnection(
        {
            "stage_run": {"id": uuid.uuid4(), "attempt_number": 2, "status": "completed"},
            "stage_tables": [
                {
                    "table_name": "tbscust",
                    "source_file": "tbscust.csv",
                    "expected_row_count": 1,
                    "loaded_row_count": 1,
                    "status": "completed",
                    "error_message": None,
                }
            ],
            "canonical_run": {
                "id": uuid.uuid4(),
                "attempt_number": 2,
                "status": "failed",
                "error_message": "preflight setup failed",
                "summary": {"customer_count": 1, "lineage_count": 1, "holding_count": 0},
            },
            "canonical_steps": [],
            "snapshot_coverage": {
                "order_count": 0,
                "order_snapshot_count": 0,
                "invoice_count": 0,
                "invoice_snapshot_count": 0,
                "supplier_invoice_count": 0,
                "supplier_invoice_snapshot_count": 0,
            },
            "cutoff_date": date(2024, 8, 31),
        }
    )

    async def fake_open_raw_connection() -> FakeValidationConnection:
        return connection

    async def fake_fetch_mapping_summary(*args, **kwargs):
        return validation.ProductMappingValidationSummary(
            mapping_count=1,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        )

    monkeypatch.setattr(validation, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(validation, "_fetch_product_mapping_summary", fake_fetch_mapping_summary)

    result = await validation.validate_import_batch(
        batch_id="batch-155-failed",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000001555"),
        schema_name="raw_legacy",
        output_dir=tmp_path,
    )

    assert result.report.status == "blocked"
    assert result.report.failed_stages[0].stage_name == "canonical_run"
    assert result.report.issues[0].code == "import-stage-failed"
    assert "preflight setup failed" in (result.report.issues[0].details["error_message"] or "")


@pytest.mark.asyncio
async def test_validate_import_batch_marks_replay_after_failed_scope(
    monkeypatch,
    tmp_path: Path,
) -> None:
    connection = FakeValidationConnection(
        {
            "stage_run": {"id": uuid.uuid4(), "attempt_number": 3, "status": "completed"},
            "stage_tables": [
                {
                    "table_name": "tbscust",
                    "source_file": "tbscust.csv",
                    "expected_row_count": 1,
                    "loaded_row_count": 1,
                    "status": "completed",
                    "error_message": None,
                }
            ],
            "canonical_run": {
                "id": uuid.uuid4(),
                "attempt_number": 3,
                "status": "completed",
                "summary": {"customer_count": 1, "lineage_count": 1, "holding_count": 0},
            },
            "canonical_steps": [],
            "previous_scope_run": {
                "id": uuid.uuid4(),
                "batch_id": "batch-155-prev-failed",
                "attempt_number": 2,
                "status": "failed",
            },
            "snapshot_coverage": {
                "order_count": 0,
                "order_snapshot_count": 0,
                "invoice_count": 0,
                "invoice_snapshot_count": 0,
                "supplier_invoice_count": 0,
                "supplier_invoice_snapshot_count": 0,
            },
            "cutoff_date": date(2024, 8, 31),
        }
    )

    async def fake_open_raw_connection() -> FakeValidationConnection:
        return connection

    async def fake_fetch_mapping_summary(*args, **kwargs):
        return validation.ProductMappingValidationSummary(
            mapping_count=1,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        )

    monkeypatch.setattr(validation, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(validation, "_fetch_product_mapping_summary", fake_fetch_mapping_summary)

    result = await validation.validate_import_batch(
        batch_id="batch-155-rerun",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000001556"),
        schema_name="raw_legacy",
        output_dir=tmp_path,
    )

    assert result.report.replay.disposition == "replayed-after-failure"
    assert result.report.replay.previous_status == "failed"


@pytest.mark.asyncio
async def test_validate_import_batch_removes_temp_artifacts_when_summary_persist_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    connection = FakeValidationConnection(
        {
            "stage_run": {"id": uuid.uuid4(), "attempt_number": 1, "status": "completed"},
            "stage_tables": [
                {
                    "table_name": "tbscust",
                    "source_file": "tbscust.csv",
                    "expected_row_count": 1,
                    "loaded_row_count": 1,
                    "status": "completed",
                    "error_message": None,
                }
            ],
            "canonical_run": {
                "id": uuid.uuid4(),
                "attempt_number": 1,
                "status": "completed",
                "summary": {"customer_count": 1, "lineage_count": 1, "holding_count": 0},
            },
            "canonical_steps": [],
            "snapshot_coverage": {
                "order_count": 0,
                "order_snapshot_count": 0,
                "invoice_count": 0,
                "invoice_snapshot_count": 0,
                "supplier_invoice_count": 0,
                "supplier_invoice_snapshot_count": 0,
            },
            "cutoff_date": date(2024, 8, 31),
        }
    )

    async def fake_open_raw_connection() -> FakeValidationConnection:
        return connection

    async def fake_fetch_mapping_summary(*args, **kwargs):
        return validation.ProductMappingValidationSummary(
            mapping_count=1,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        )

    async def fake_persist_validation_summary(*args, **kwargs):
        raise RuntimeError("persist failed")

    monkeypatch.setattr(validation, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(validation, "_fetch_product_mapping_summary", fake_fetch_mapping_summary)
    monkeypatch.setattr(validation, "_persist_validation_summary", fake_persist_validation_summary)

    with pytest.raises(RuntimeError, match="persist failed"):
        await validation.validate_import_batch(
            batch_id="batch-155-cleanup",
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000001557"),
            schema_name="raw_legacy",
            output_dir=tmp_path,
        )

    assert list(tmp_path.iterdir()) == []


def test_build_validation_report_scope_key_changes_when_mapping_state_changes() -> None:
    report_clean = validation.build_validation_report(
        batch_id="batch-155",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000001552"),
        schema_name="raw_legacy",
        attempt_number=1,
        stage_rows=(
            validation.StageReconciliationRow(
                table_name="tbscust",
                source_file="tbscust.csv",
                expected_row_count=10,
                loaded_row_count=10,
                status="completed",
            ),
        ),
        mapping_summary=validation.ProductMappingValidationSummary(
            mapping_count=1,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        ),
        failed_stages=(),
        counts={"customer_count": 1, "lineage_count": 1},
        cutoff_date="2024-08-31",
        previous_scope_run=None,
    )
    report_with_unknowns = validation.build_validation_report(
        batch_id="batch-155",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000001552"),
        schema_name="raw_legacy",
        attempt_number=1,
        stage_rows=report_clean.stage_reconciliation,
        mapping_summary=validation.ProductMappingValidationSummary(
            mapping_count=1,
            candidate_count=1,
            unknown_count=1,
            orphan_code_count=1,
            orphan_row_count=2,
        ),
        failed_stages=(),
        counts={"customer_count": 1, "lineage_count": 1},
        cutoff_date="2024-08-31",
        previous_scope_run=None,
    )

    assert report_clean.replay.scope_key != report_with_unknowns.replay.scope_key


@pytest.mark.asyncio
async def test_validate_import_batch_flags_missing_legacy_header_snapshots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    connection = FakeValidationConnection(
        {
            "stage_run": {"id": uuid.uuid4(), "attempt_number": 1, "status": "completed"},
            "stage_tables": [
                {
                    "table_name": "tbsslipx",
                    "source_file": "tbsslipx.csv",
                    "expected_row_count": 2,
                    "loaded_row_count": 2,
                    "status": "completed",
                    "error_message": None,
                }
            ],
            "canonical_run": {
                "id": uuid.uuid4(),
                "attempt_number": 1,
                "status": "completed",
                "summary": {
                    "order_count": 1,
                    "invoice_count": 1,
                    "supplier_invoice_count": 1,
                    "lineage_count": 3,
                    "holding_count": 0,
                },
            },
            "canonical_steps": [],
            "snapshot_coverage": {
                "order_count": 1,
                "order_snapshot_count": 1,
                "invoice_count": 1,
                "invoice_snapshot_count": 0,
                "supplier_invoice_count": 1,
                "supplier_invoice_snapshot_count": 1,
            },
            "cutoff_date": date(2024, 8, 31),
        }
    )

    async def fake_open_raw_connection() -> FakeValidationConnection:
        return connection

    async def fake_fetch_mapping_summary(*args, **kwargs):
        return validation.ProductMappingValidationSummary(
            mapping_count=0,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        )

    monkeypatch.setattr(validation, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(validation, "_fetch_product_mapping_summary", fake_fetch_mapping_summary)

    result = await validation.validate_import_batch(
        batch_id="batch-155-snapshots",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000001558"),
        schema_name="raw_legacy",
        output_dir=tmp_path,
    )

    assert result.report.status == "blocked"
    assert result.report.snapshot_coverage is not None
    assert result.report.snapshot_coverage.missing_snapshot_count == 1
    assert result.report.issues[0].code == "legacy-header-snapshot-missing"

    report_payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert report_payload["snapshot_coverage"]["invoice_snapshot_count"] == 0
    assert report_payload["counts"]["legacy_header_snapshot_missing_count"] == 1
    assert "## Snapshot Coverage" in result.markdown_path.read_text(encoding="utf-8")

    update_call = next(
        args
        for query, args in connection.execute_calls
        if 'UPDATE "raw_legacy".canonical_import_runs' in query
    )
    stored_summary = json.loads(update_call[1])
    assert stored_summary["legacy_header_snapshot_missing_count"] == 1
    assert stored_summary["legacy_header_snapshot_coverage"]["invoice_snapshot_count"] == 0


def test_write_validation_report_scopes_artifact_names_by_schema_and_tenant(
    tmp_path: Path,
) -> None:
    report = validation.MigrationValidationReport(
        batch_id="batch/155",
        tenant_id="00000000-0000-0000-0000-000000001553",
        schema_name="raw_legacy",
        attempt_number=2,
        status="clean",
        blocking_issue_count=0,
        stage_reconciliation=(),
        mapping_summary=validation.ProductMappingValidationSummary(
            mapping_count=0,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        ),
        failed_stages=(),
        issues=(),
        replay=validation.ImportReplayMetadata(
            scope_key="scope-155",
            scope_cutoff_date="2024-08-31",
            disposition="new-scope",
        ),
        epic13_handoff={
            "scope_key": "scope-155",
            "lineage_count": 0,
            "holding_count": 0,
            "boundary": "test",
        },
        counts={"lineage_count": 0, "holding_count": 0},
    )

    json_path, markdown_path = validation.write_validation_report(report, output_dir=tmp_path)

    assert json_path.name.startswith(
        "raw_legacy-00000000-0000-0000-0000-000000001553-batch-155-attempt-2-validation"
    )
    assert markdown_path.name.endswith(".md")


@pytest.mark.asyncio
async def test_validate_import_batch_includes_provisional_category_review_artifacts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000001559")
    connection = FakeValidationConnection(
        {
            "stage_run": {"id": uuid.uuid4(), "attempt_number": 1, "status": "completed"},
            "stage_tables": [
                {
                    "table_name": "tbsstock",
                    "source_file": "tbsstock.csv",
                    "expected_row_count": 2,
                    "loaded_row_count": 2,
                    "status": "completed",
                    "error_message": None,
                }
            ],
            "canonical_run": {
                "id": uuid.uuid4(),
                "attempt_number": 2,
                "status": "completed",
                "summary": {
                    "customer_count": 1,
                    "product_count": 2,
                    "warehouse_count": 1,
                    "inventory_count": 1,
                    "holding_count": 0,
                    "lineage_count": 4,
                },
            },
            "canonical_steps": [],
            "snapshot_coverage": {
                "order_count": 0,
                "order_snapshot_count": 0,
                "invoice_count": 0,
                "invoice_snapshot_count": 0,
                "supplier_invoice_count": 0,
                "supplier_invoice_snapshot_count": 0,
            },
            "cutoff_date": date(2024, 8, 31),
        }
    )

    async def fake_open_raw_connection() -> FakeValidationConnection:
        return connection

    async def fake_fetch_mapping_summary(*args, **kwargs):
        return validation.ProductMappingValidationSummary(
            mapping_count=1,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        )

    async def fake_fetch_product_category_review_summary(*args, **kwargs):
        return validation.ProductCategoryReviewSummary(
            candidate_count=1,
            fallback_count=1,
            low_confidence_count=0,
            excluded_count=0,
            candidates=(
                validation.ProductCategoryReviewCandidate(
                    legacy_code="MISC001",
                    name="Unclassified Belt Item",
                    current_category="Other Power Transmission",
                    category_source="fallback_rule",
                    category_rule_id="fallback-other-power-transmission",
                    category_confidence="0.40",
                    review_reason="fallback_assignment",
                ),
            ),
        )

    monkeypatch.setattr(validation, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(validation, "_fetch_product_mapping_summary", fake_fetch_mapping_summary)
    monkeypatch.setattr(
        validation,
        "_fetch_product_category_review_summary",
        fake_fetch_product_category_review_summary,
    )

    result = await validation.validate_import_batch(
        batch_id="batch-155-category-review",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        output_dir=tmp_path,
    )

    assert result.report.status == "warning"
    assert result.report.category_review_summary is not None
    assert result.report.category_review_summary.candidate_count == 1
    assert any(issue.code == "provisional-category-assignments" for issue in result.report.issues)

    report_payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert report_payload["category_review_summary"]["candidate_count"] == 1
    assert report_payload["category_review_summary"]["candidates"][0]["legacy_code"] == "MISC001"
    assert report_payload["counts"]["category_review_candidate_count"] == 1
    assert "## Category Review" in result.markdown_path.read_text(encoding="utf-8")
    assert "fallback_assignment" in result.markdown_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_fetch_cutoff_date_normalizes_legacy_numeric_dates() -> None:
    connection = FakeValidationConnection(
        {
            "cutoff_rows": [
                {"invoice_date_raw": "88032642"},
                {"invoice_date_raw": "1130826001"},
                {"invoice_date_raw": "1900-01-01"},
            ]
        }
    )

    result = await validation._fetch_cutoff_date(connection, "raw_legacy", "batch-155")

    assert result == "2024-08-26"


@pytest.mark.asyncio
async def test_fetch_cutoff_date_uses_purchase_invoice_date_fallback_query() -> None:
    connection = CutoffQueryConnection(
        [
            {"invoice_date_raw": "2024-09-25"},
            {"invoice_date_raw": "2024-09-26"},
        ]
    )

    result = await validation._fetch_cutoff_date(connection, "raw_legacy", "batch-155")

    assert connection.queries
    assert "col_62" in connection.queries[0]
    assert "1900-01-01" in connection.queries[0]
    assert result == "2024-09-26"


@pytest.mark.asyncio
async def test_validate_import_batch_binds_stage_lookup_to_canonical_started_at(
    monkeypatch,
    tmp_path: Path,
) -> None:
    started_at = datetime(2024, 9, 1, 10, 0, tzinfo=UTC)
    connection = FakeValidationConnection(
        {
            "stage_run": {"id": uuid.uuid4(), "attempt_number": 2, "status": "completed"},
            "stage_tables": [
                {
                    "table_name": "tbscust",
                    "source_file": "tbscust.csv",
                    "expected_row_count": 1,
                    "loaded_row_count": 1,
                    "status": "completed",
                    "error_message": None,
                }
            ],
            "canonical_run": {
                "id": uuid.uuid4(),
                "attempt_number": 3,
                "status": "completed",
                "started_at": started_at,
                "summary": {"customer_count": 1, "lineage_count": 1, "holding_count": 0},
            },
            "canonical_steps": [],
            "snapshot_coverage": {
                "order_count": 0,
                "order_snapshot_count": 0,
                "invoice_count": 0,
                "invoice_snapshot_count": 0,
                "supplier_invoice_count": 0,
                "supplier_invoice_snapshot_count": 0,
            },
            "cutoff_date": date(2024, 8, 31),
        }
    )

    async def fake_open_raw_connection() -> FakeValidationConnection:
        return connection

    async def fake_fetch_mapping_summary(*args, **kwargs):
        return validation.ProductMappingValidationSummary(
            mapping_count=1,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        )

    monkeypatch.setattr(validation, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(validation, "_fetch_product_mapping_summary", fake_fetch_mapping_summary)

    await validation.validate_import_batch(
        batch_id="batch-155",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000001554"),
        schema_name="raw_legacy",
        output_dir=tmp_path,
    )

    stage_lookup = next(
        args for query, args in connection.fetchrow_calls if "FROM legacy_import_runs" in query
    )
    assert stage_lookup[2] == started_at


# =============================================================================
# Story 15.27: Incremental Validation and Derived Refresh Scope Tests
# =============================================================================


def test_build_artifact_metadata_clean_status() -> None:
    """AC5: Clean validation produces correct artifact metadata."""
    metadata = validation._build_artifact_metadata(
        batch_mode="incremental",
        affected_domains=("sales", "invoices"),
        status="clean",
        blocking_issue_count=0,
        failed_stages=(),
        incremental_scope=None,
    )
    assert metadata.batch_mode == "incremental"
    assert metadata.affected_domains == ("sales", "invoices")
    assert metadata.summary_valid is True
    assert metadata.freshness_success is True
    assert metadata.promotion_eligible is False  # Not eligible without promotion policy
    assert metadata.watermark_advanced is False  # Set by caller
    assert metadata.requires_rebaseline is False
    assert metadata.root_failed_step is None
    assert metadata.rebaseline_reason is None


def test_build_artifact_metadata_blocked_status() -> None:
    """AC4: Blocked validation records root failure info."""
    failed_stages = (
        validation.ValidationStageFailure(
            stage_name="canonical-import",
            row_count=0,
            error_message="Missing required mapping for product XYZ",
        ),
    )
    metadata = validation._build_artifact_metadata(
        batch_mode="incremental",
        affected_domains=("sales",),
        status="blocked",
        blocking_issue_count=1,
        failed_stages=failed_stages,
        incremental_scope=None,
    )
    assert metadata.summary_valid is False
    assert metadata.freshness_success is False
    assert metadata.requires_rebaseline is True
    assert metadata.root_failed_step == "canonical-import"
    assert metadata.root_error_message == "Missing required mapping for product XYZ"
    assert "canonical-import" in metadata.rebaseline_reason


def test_build_artifact_metadata_warning_status() -> None:
    """AC5: Warning status is still valid but freshness is not fully successful."""
    metadata = validation._build_artifact_metadata(
        batch_mode="full",
        affected_domains=("products",),
        status="warning",
        blocking_issue_count=0,
        failed_stages=(),
        incremental_scope=None,
        promotion_eligible=True,
    )
    assert metadata.summary_valid is True
    assert metadata.freshness_success is True  # No blocking issues
    assert metadata.promotion_eligible is True


def test_build_validation_report_incremental_scope() -> None:
    """AC1: Validation report includes incremental scope metadata."""
    report = validation.build_validation_report(
        batch_id="batch-155-inc",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000001560"),
        schema_name="raw_legacy",
        attempt_number=1,
        stage_rows=(
            validation.StageReconciliationRow(
                table_name="tbscust",
                source_file="tbscust.csv",
                expected_row_count=10,
                loaded_row_count=10,
                status="completed",
            ),
        ),
        mapping_summary=validation.ProductMappingValidationSummary(
            mapping_count=1,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        ),
        failed_stages=(),
        counts={"customer_count": 1, "lineage_count": 1},
        cutoff_date="2024-08-31",
        previous_scope_run=None,
        # Story 15.27: Incremental scope parameters (AC1).
        batch_mode="incremental",
        affected_domains=["sales", "invoices"],
        entity_scope={"sales": {"closure_keys": ["SO-001", "SO-002"]}},
        scoped_document_count=42,
        last_successful_batch_ids={"sales": "batch-154"},
    )
    assert report.artifact_metadata is not None
    assert report.artifact_metadata.batch_mode == "incremental"
    assert report.artifact_metadata.affected_domains == ("sales", "invoices")
    assert report.artifact_metadata.incremental_scope is not None
    assert report.artifact_metadata.incremental_scope["scoped_document_count"] == 42
    assert report.artifact_metadata.incremental_scope["affected_domains"] == ["sales", "invoices"]
    assert report.artifact_metadata.freshness_success is True


def test_build_validation_report_full_batch_no_incremental_scope() -> None:
    """AC1: Full batch validation does not include incremental scope."""
    report = validation.build_validation_report(
        batch_id="batch-155-full",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000001561"),
        schema_name="raw_legacy",
        attempt_number=1,
        stage_rows=(
            validation.StageReconciliationRow(
                table_name="tbscust",
                source_file="tbscust.csv",
                expected_row_count=10,
                loaded_row_count=10,
                status="completed",
            ),
        ),
        mapping_summary=validation.ProductMappingValidationSummary(
            mapping_count=1,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        ),
        failed_stages=(),
        counts={"customer_count": 1, "lineage_count": 1},
        cutoff_date="2024-08-31",
        previous_scope_run=None,
        # Story 15.27: Full batch (no incremental scope).
        batch_mode="full",
        affected_domains=None,
    )
    assert report.artifact_metadata is not None
    assert report.artifact_metadata.batch_mode == "full"
    assert report.artifact_metadata.affected_domains == ()
    assert report.artifact_metadata.incremental_scope is None


@pytest.mark.asyncio
async def test_validate_import_batch_passes_incremental_scope(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """AC1: validate_import_batch passes incremental scope to build_validation_report."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000001562")
    connection = FakeValidationConnection(
        {
            "stage_run": {"id": uuid.uuid4(), "attempt_number": 1, "status": "completed"},
            "stage_tables": [
                {
                    "table_name": "tbscust",
                    "source_file": "tbscust.csv",
                    "expected_row_count": 10,
                    "loaded_row_count": 10,
                    "status": "completed",
                    "error_message": None,
                },
            ],
            "canonical_run": {
                "id": uuid.uuid4(),
                "attempt_number": 1,
                "status": "completed",
                "summary": {"customer_count": 1, "lineage_count": 1, "holding_count": 0},
            },
            "canonical_steps": [],
            "snapshot_coverage": {
                "order_count": 0,
                "order_snapshot_count": 0,
                "invoice_count": 0,
                "invoice_snapshot_count": 0,
                "supplier_invoice_count": 0,
                "supplier_invoice_snapshot_count": 0,
            },
            "cutoff_date": date(2024, 8, 31),
        }
    )

    async def fake_open_raw_connection() -> FakeValidationConnection:
        return connection

    async def fake_fetch_mapping_summary(*args, **kwargs):
        return validation.ProductMappingValidationSummary(
            mapping_count=1,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        )

    monkeypatch.setattr(validation, "_open_raw_connection", fake_open_raw_connection)
    monkeypatch.setattr(validation, "_fetch_product_mapping_summary", fake_fetch_mapping_summary)

    result = await validation.validate_import_batch(
        batch_id="batch-155-inc",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
        output_dir=tmp_path,
        # Story 15.27: Incremental scope parameters (AC1).
        batch_mode="incremental",
        affected_domains=["sales", "invoices"],
        entity_scope={"sales": {"closure_keys": ["SO-001"]}},
        scoped_document_count=10,
        last_successful_batch_ids={"sales": "batch-154"},
    )

    assert result.report.artifact_metadata is not None
    assert result.report.artifact_metadata.batch_mode == "incremental"
    assert result.report.artifact_metadata.affected_domains == ("sales", "invoices")
    assert result.report.artifact_metadata.freshness_success is True


def test_render_validation_markdown_includes_artifact_metadata(tmp_path: Path) -> None:
    """AC5: Markdown report includes incremental validation metadata section."""
    report = validation.MigrationValidationReport(
        batch_id="batch-155-inc",
        tenant_id="00000000-0000-0000-0000-000000001563",
        schema_name="raw_legacy",
        attempt_number=1,
        status="clean",
        blocking_issue_count=0,
        stage_reconciliation=(),
        mapping_summary=validation.ProductMappingValidationSummary(
            mapping_count=0,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        ),
        failed_stages=(),
        issues=(),
        replay=validation.ImportReplayMetadata(
            scope_key="scope-155",
            scope_cutoff_date="2024-08-31",
            disposition="new-scope",
        ),
        epic13_handoff={"scope_key": "scope-155", "lineage_count": 0, "holding_count": 0, "boundary": "test"},
        counts={"lineage_count": 0, "holding_count": 0},
        # Story 15.27: Include artifact metadata (AC5).
        artifact_metadata=validation.ValidationArtifactMetadata(
            batch_mode="incremental",
            affected_domains=("sales",),
            summary_valid=True,
            watermark_advanced=True,
            root_failed_step=None,
            root_error_message=None,
            requires_rebaseline=False,
            rebaseline_reason=None,
            freshness_success=True,
            promotion_eligible=True,
            incremental_scope=validation.IncrementalValidationScope(
                affected_domains=["sales"],
                entity_scope={},
                scoped_document_count=5,
                last_successful_batch_ids={},
            ),
        ),
    )

    markdown = validation.render_validation_markdown(report)
    assert "## Incremental Validation Metadata" in markdown
    assert "Batch mode: incremental" in markdown
    assert "Affected domains: sales" in markdown
    assert "Summary valid: True" in markdown
    assert "Freshness success: True" in markdown
    assert "Promotion eligible: True" in markdown
    assert "Watermark advanced: True" in markdown
    assert "Requires rebaseline: False" in markdown


def test_report_to_dict_includes_artifact_metadata() -> None:
    """AC5: JSON report includes artifact_metadata field."""
    report = validation.MigrationValidationReport(
        batch_id="batch-155-inc",
        tenant_id="00000000-0000-0000-0000-000000001564",
        schema_name="raw_legacy",
        attempt_number=1,
        status="blocked",
        blocking_issue_count=1,
        stage_reconciliation=(),
        mapping_summary=validation.ProductMappingValidationSummary(
            mapping_count=0,
            candidate_count=0,
            unknown_count=0,
            orphan_code_count=0,
            orphan_row_count=0,
        ),
        failed_stages=(
            validation.ValidationStageFailure(
                stage_name="canonical-import",
                row_count=0,
                error_message="Test error",
            ),
        ),
        issues=(
            validation.MigrationValidationIssue(
                code="test-block",
                severity=1,
                message="Test blocking issue",
                details={},
            ),
        ),
        replay=validation.ImportReplayMetadata(
            scope_key="scope-155",
            scope_cutoff_date="2024-08-31",
            disposition="new-scope",
        ),
        epic13_handoff={"scope_key": "scope-155", "lineage_count": 0, "holding_count": 0, "boundary": "test"},
        counts={"lineage_count": 0, "holding_count": 0},
        # Story 15.27: Include artifact metadata (AC5).
        artifact_metadata=validation.ValidationArtifactMetadata(
            batch_mode="incremental",
            affected_domains=("sales",),
            summary_valid=False,
            watermark_advanced=False,
            root_failed_step="canonical-import",
            root_error_message="Test error",
            requires_rebaseline=True,
            rebaseline_reason="Test blocking issue",
            freshness_success=False,
            promotion_eligible=False,
            incremental_scope=None,
        ),
    )

    report_dict = report.to_dict()
    assert "artifact_metadata" in report_dict
    assert report_dict["artifact_metadata"]["batch_mode"] == "incremental"
    assert report_dict["artifact_metadata"]["summary_valid"] is False
    assert report_dict["artifact_metadata"]["watermark_advanced"] is False
    assert report_dict["artifact_metadata"]["requires_rebaseline"] is True
    assert report_dict["artifact_metadata"]["root_failed_step"] == "canonical-import"
