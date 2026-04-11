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
    assert report_payload["epic13_handoff"]["scope_key"] == result.report.replay.scope_key
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
    assert result.json_path.exists()
    assert result.markdown_path.exists()


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
