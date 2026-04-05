"""Validation and replay-safety reporting for legacy import batches."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Mapping

from common.config import PROJECT_ROOT, settings
from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.normalization import normalize_legacy_date
from domains.legacy_import.staging import _open_raw_connection, _quoted_identifier

_ARTIFACT_TOKEN_RE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(slots=True, frozen=True)
class StageReconciliationRow:
    table_name: str
    source_file: str
    expected_row_count: int | None
    loaded_row_count: int
    status: str
    error_message: str | None = None

    @property
    def matches_expected(self) -> bool:
        return self.expected_row_count is None or self.expected_row_count == self.loaded_row_count


@dataclass(slots=True, frozen=True)
class ProductMappingValidationSummary:
    mapping_count: int
    candidate_count: int
    unknown_count: int
    orphan_code_count: int
    orphan_row_count: int


@dataclass(slots=True, frozen=True)
class ValidationStageFailure:
    stage_name: str
    row_count: int
    error_message: str | None


@dataclass(slots=True, frozen=True)
class MigrationValidationIssue:
    code: str
    severity: int
    message: str
    details: dict[str, object]

    @property
    def blocking(self) -> bool:
        return self.severity == 1


@dataclass(slots=True, frozen=True)
class ImportReplayMetadata:
    scope_key: str
    scope_cutoff_date: str | None
    disposition: str
    previous_batch_id: str | None = None
    previous_attempt_number: int | None = None
    previous_status: str | None = None


@dataclass(slots=True, frozen=True)
class MigrationValidationReport:
    batch_id: str
    tenant_id: str
    schema_name: str
    attempt_number: int
    status: str
    blocking_issue_count: int
    stage_reconciliation: tuple[StageReconciliationRow, ...]
    mapping_summary: ProductMappingValidationSummary
    failed_stages: tuple[ValidationStageFailure, ...]
    issues: tuple[MigrationValidationIssue, ...]
    replay: ImportReplayMetadata
    epic13_handoff: dict[str, object]
    counts: dict[str, int] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "batch_id": self.batch_id,
            "tenant_id": self.tenant_id,
            "schema_name": self.schema_name,
            "attempt_number": self.attempt_number,
            "status": self.status,
            "blocking_issue_count": self.blocking_issue_count,
            "counts": dict(self.counts or {}),
            "stage_reconciliation": [asdict(row) for row in self.stage_reconciliation],
            "mapping_summary": asdict(self.mapping_summary),
            "failed_stages": [asdict(stage) for stage in self.failed_stages],
            "issues": [
                {
                    "code": issue.code,
                    "severity": issue.severity,
                    "message": issue.message,
                    "details": issue.details,
                }
                for issue in self.issues
            ],
            "replay": asdict(self.replay),
            "epic13_handoff": self.epic13_handoff,
        }


@dataclass(slots=True, frozen=True)
class MigrationBatchValidationResult:
    report: MigrationValidationReport
    json_path: Path
    markdown_path: Path


def _coerce_row(row: Mapping[str, object] | object | None) -> dict[str, object]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    return dict(row)


def _as_int(value: object | None) -> int:
    if value in (None, ""):
        return 0
    return int(value)


def _as_text(value: object | None) -> str:
    return str(value or "").strip()


def _derive_scope_key(
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    cutoff_date: str | None,
    stage_rows: tuple[StageReconciliationRow, ...],
    mapping_summary: ProductMappingValidationSummary,
    failed_stages: tuple[ValidationStageFailure, ...],
    counts: Mapping[str, int],
) -> str:
    payload = {
        "tenant_id": str(tenant_id),
        "schema_name": schema_name,
        "cutoff_date": cutoff_date,
        "stage_tables": [
            {
                "table_name": row.table_name,
                "expected_row_count": row.expected_row_count,
                "loaded_row_count": row.loaded_row_count,
            }
            for row in stage_rows
        ],
        "mapping_summary": asdict(mapping_summary),
        "failed_stages": [asdict(stage) for stage in failed_stages],
        "counts": dict(sorted(counts.items())),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return digest[:16]


def build_validation_report(
    *,
    batch_id: str,
    tenant_id: uuid.UUID,
    schema_name: str,
    attempt_number: int,
    stage_rows: tuple[StageReconciliationRow, ...],
    mapping_summary: ProductMappingValidationSummary,
    failed_stages: tuple[ValidationStageFailure, ...],
    counts: Mapping[str, int],
    cutoff_date: str | None,
    previous_scope_run: Mapping[str, object] | None,
) -> MigrationValidationReport:
    issues: list[MigrationValidationIssue] = []
    for row in stage_rows:
        if not row.matches_expected:
            issues.append(
                MigrationValidationIssue(
                    code="stage-row-count-mismatch",
                    severity=1,
                    message=(
                        f"Stage reconciliation mismatch for {row.table_name}: "
                        f"expected {row.expected_row_count}, loaded {row.loaded_row_count}."
                    ),
                    details={
                        "table_name": row.table_name,
                        "expected_row_count": row.expected_row_count,
                        "loaded_row_count": row.loaded_row_count,
                    },
                )
            )
        if row.status == "failed":
            issues.append(
                MigrationValidationIssue(
                    code="stage-load-failed",
                    severity=1,
                    message=f"Stage table {row.table_name} failed to load.",
                    details={
                        "table_name": row.table_name,
                        "error_message": row.error_message,
                    },
                )
            )

    for stage in failed_stages:
        issues.append(
            MigrationValidationIssue(
                code="import-stage-failed",
                severity=1,
                message=f"Import stage {stage.stage_name} failed.",
                details={
                    "stage_name": stage.stage_name,
                    "row_count": stage.row_count,
                    "error_message": stage.error_message,
                },
            )
        )

    if mapping_summary.unknown_count > 0:
        issues.append(
            MigrationValidationIssue(
                code="unresolved-product-mappings",
                severity=2,
                message=(
                    f"{mapping_summary.unknown_count} product codes remain routed to UNKNOWN "
                    f"across {mapping_summary.orphan_row_count} sales-detail rows."
                ),
                details={
                    "unknown_count": mapping_summary.unknown_count,
                    "orphan_code_count": mapping_summary.orphan_code_count,
                    "orphan_row_count": mapping_summary.orphan_row_count,
                    "candidate_count": mapping_summary.candidate_count,
                },
            )
        )

    issues.sort(key=lambda issue: (issue.severity, issue.code, issue.message))
    blocking_issue_count = sum(1 for issue in issues if issue.blocking)
    status = "blocked" if blocking_issue_count else ("warning" if issues else "clean")
    scope_key = _derive_scope_key(
        tenant_id=tenant_id,
        schema_name=schema_name,
        cutoff_date=cutoff_date,
        stage_rows=stage_rows,
        mapping_summary=mapping_summary,
        failed_stages=failed_stages,
        counts=counts,
    )
    previous_scope_payload = _coerce_row(previous_scope_run)
    if previous_scope_payload:
        previous_status = _as_text(previous_scope_payload.get("status")) or None
        replay = ImportReplayMetadata(
            scope_key=scope_key,
            scope_cutoff_date=cutoff_date,
            disposition=(
                "replayed-scope"
                if previous_status in {None, "completed"}
                else "replayed-after-failure"
            ),
            previous_batch_id=_as_text(previous_scope_payload.get("batch_id")) or None,
            previous_attempt_number=(
                _as_int(previous_scope_payload.get("attempt_number"))
                if previous_scope_payload.get("attempt_number") is not None
                else None
            ),
            previous_status=previous_status,
        )
    else:
        replay = ImportReplayMetadata(
            scope_key=scope_key,
            scope_cutoff_date=cutoff_date,
            disposition="new-scope",
        )

    epic13_handoff = {
        "scope_key": scope_key,
        "scope_cutoff_date": cutoff_date,
        "lineage_count": _as_int(counts.get("lineage_count")),
        "holding_count": _as_int(counts.get("holding_count")),
        "comparison_inputs": [
            "stage_reconciliation",
            "mapping_summary",
            "failed_stages",
            "counts",
        ],
        "boundary": (
            "Story 15.5 emits batch-scoped import evidence only. "
            "Epic 13 owns longer-horizon shadow-mode reconciliation."
        ),
    }

    return MigrationValidationReport(
        batch_id=batch_id,
        tenant_id=str(tenant_id),
        schema_name=schema_name,
        attempt_number=attempt_number,
        status=status,
        blocking_issue_count=blocking_issue_count,
        stage_reconciliation=stage_rows,
        mapping_summary=mapping_summary,
        failed_stages=failed_stages,
        issues=tuple(issues),
        replay=replay,
        epic13_handoff=epic13_handoff,
        counts=dict(counts),
    )


def render_validation_markdown(report: MigrationValidationReport) -> str:
    lines = [
        f"# Legacy Import Validation Report - {report.batch_id}",
        "",
        f"Status: {report.status}",
        f"Attempt: {report.attempt_number}",
        f"Replay disposition: {report.replay.disposition}",
        f"Scope key: {report.replay.scope_key}",
        f"Scope cutoff date: {report.replay.scope_cutoff_date or 'n/a'}",
        f"Previous scope status: {report.replay.previous_status or 'n/a'}",
        "",
        "## Row Count Reconciliation",
        "",
    ]
    for row in report.stage_reconciliation:
        lines.append(
            "- "
            f"{row.table_name}: expected={row.expected_row_count}, "
            f"loaded={row.loaded_row_count}, status={row.status}"
        )
    lines.extend(["", "## Mapping Summary", ""])
    lines.append(
        "- "
        f"mappings={report.mapping_summary.mapping_count}, "
        f"candidates={report.mapping_summary.candidate_count}, "
        f"unknown={report.mapping_summary.unknown_count}, "
        f"orphan_codes={report.mapping_summary.orphan_code_count}, "
        f"orphan_rows={report.mapping_summary.orphan_row_count}"
    )
    lines.extend(["", "## Discrepancies", ""])
    if not report.issues:
        lines.append("- No discrepancies detected.")
    for issue in report.issues:
        lines.append(f"- Severity {issue.severity}: {issue.message}")
    lines.extend(["", "## Epic 13 Handoff", ""])
    lines.append(f"- Scope key: {report.epic13_handoff['scope_key']}")
    lines.append(f"- Lineage count: {report.epic13_handoff['lineage_count']}")
    lines.append(f"- Holding count: {report.epic13_handoff['holding_count']}")
    lines.append(f"- Boundary: {report.epic13_handoff['boundary']}")
    return "\n".join(lines) + "\n"


def _artifact_paths_for_report(
    report: MigrationValidationReport,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    resolved_output_dir = (
        output_dir or PROJECT_ROOT / "_bmad-output" / "validation" / "legacy-import"
    )
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    base_name = (
        f"{_artifact_token(report.schema_name)}-"
        f"{_artifact_token(report.tenant_id)}-"
        f"{_artifact_token(report.batch_id)}-"
        f"attempt-{report.attempt_number}-validation"
    )
    json_path = resolved_output_dir / f"{base_name}.json"
    markdown_path = resolved_output_dir / f"{base_name}.md"
    return json_path, markdown_path


def _write_report_files(
    report: MigrationValidationReport,
    *,
    json_path: Path,
    markdown_path: Path,
) -> None:
    json_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_validation_markdown(report), encoding="utf-8")


def write_validation_report(
    report: MigrationValidationReport,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    json_path, markdown_path = _artifact_paths_for_report(report, output_dir=output_dir)
    _write_report_files(report, json_path=json_path, markdown_path=markdown_path)
    return json_path, markdown_path


def _artifact_token(value: str) -> str:
    cleaned = _ARTIFACT_TOKEN_RE.sub("-", value.strip()).strip("-._")
    return cleaned or "unknown"


async def _fetch_latest_stage_run(
    connection,
    tenant_id: uuid.UUID,
    batch_id: str,
    *,
    canonical_started_at: datetime | None,
) -> dict[str, object]:
    row = await connection.fetchrow(
        """
		SELECT id, attempt_number, status, completed_at
		FROM legacy_import_runs
		WHERE tenant_id = $1
			AND batch_id = $2
			AND status = 'completed'
			AND ($3::timestamptz IS NULL OR completed_at <= $3)
		ORDER BY attempt_number DESC, completed_at DESC NULLS LAST, started_at DESC
		LIMIT 1
		""",
        tenant_id,
        batch_id,
        canonical_started_at,
    )
    return _coerce_row(row)


async def _fetch_stage_table_runs(
    connection, run_id: uuid.UUID
) -> tuple[StageReconciliationRow, ...]:
    rows = await connection.fetch(
        """
		SELECT table_name, source_file, expected_row_count, loaded_row_count, status, error_message
		FROM legacy_import_table_runs
		WHERE run_id = $1
		ORDER BY table_name
		""",
        run_id,
    )
    return tuple(
        StageReconciliationRow(
            table_name=_as_text(payload.get("table_name")),
            source_file=_as_text(payload.get("source_file")),
            expected_row_count=(
                _as_int(payload.get("expected_row_count"))
                if payload.get("expected_row_count") is not None
                else None
            ),
            loaded_row_count=_as_int(payload.get("loaded_row_count")),
            status=_as_text(payload.get("status")) or "unknown",
            error_message=_as_text(payload.get("error_message")) or None,
        )
        for payload in (_coerce_row(row) for row in rows)
    )


async def _fetch_latest_canonical_run(
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
    batch_id: str,
    *,
    attempt_number: int | None,
) -> dict[str, object]:
    quoted_schema = _quoted_identifier(schema_name)
    row = await connection.fetchrow(
        f"""
		SELECT id, attempt_number, status, summary, started_at, error_message
		FROM {quoted_schema}.canonical_import_runs
		WHERE tenant_id = $1
			AND batch_id = $2
			AND status IN ('completed', 'failed')
			AND ($3::INTEGER IS NULL OR attempt_number = $3)
		ORDER BY attempt_number DESC, started_at DESC
		LIMIT 1
		""",
        tenant_id,
        batch_id,
        attempt_number,
    )
    return _coerce_row(row)


async def _fetch_canonical_step_runs(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
) -> tuple[ValidationStageFailure, ...]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT step_name, row_count, status, error_message
		FROM {quoted_schema}.canonical_import_step_runs
		WHERE run_id = $1
		ORDER BY step_name
		""",
        run_id,
    )
    failures: list[ValidationStageFailure] = []
    for payload in (_coerce_row(row) for row in rows):
        if _as_text(payload.get("status")) == "failed":
            failures.append(
                ValidationStageFailure(
                    stage_name=_as_text(payload.get("step_name")),
                    row_count=_as_int(payload.get("row_count")),
                    error_message=_as_text(payload.get("error_message")) or None,
                )
            )
    return tuple(failures)


async def _fetch_product_mapping_summary(
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
    batch_id: str,
) -> ProductMappingValidationSummary:
    quoted_schema = _quoted_identifier(schema_name)
    row = await connection.fetchrow(
        f"""
		SELECT
			COUNT(*)::INTEGER AS mapping_count,
			COUNT(*) FILTER (WHERE resolution_type = 'unknown')::INTEGER AS unknown_count,
            COALESCE(
                SUM(affected_row_count) FILTER (WHERE resolution_type = 'unknown'),
                0
            )::INTEGER AS orphan_row_count,
			COUNT(*) FILTER (WHERE resolution_type = 'unknown')::INTEGER AS orphan_code_count
		FROM {quoted_schema}.product_code_mapping
		WHERE tenant_id = $1 AND last_seen_batch_id = $2
		""",
        tenant_id,
        batch_id,
    )
    row_payload = _coerce_row(row)
    candidate_count = _as_int(
        await connection.fetchval(
            f"""
			SELECT COUNT(*)::INTEGER
			FROM {quoted_schema}.product_code_mapping_candidates
			WHERE tenant_id = $1 AND batch_id = $2
			""",
            tenant_id,
            batch_id,
        )
    )
    return ProductMappingValidationSummary(
        mapping_count=_as_int(row_payload.get("mapping_count")),
        candidate_count=candidate_count,
        unknown_count=_as_int(row_payload.get("unknown_count")),
        orphan_code_count=_as_int(row_payload.get("orphan_code_count")),
        orphan_row_count=_as_int(row_payload.get("orphan_row_count")),
    )


async def _fetch_cutoff_date(connection, schema_name: str, batch_id: str) -> str | None:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT col_3 AS invoice_date_raw
		FROM {quoted_schema}.tbsslipx
		WHERE _batch_id = $1
		UNION ALL
		SELECT col_3 AS invoice_date_raw
		FROM {quoted_schema}.tbsslipj
		WHERE _batch_id = $1
		""",
        batch_id,
    )
    cutoff: date | None = None
    for payload in (_coerce_row(row) for row in rows):
        raw_value = payload.get("invoice_date_raw")
        if raw_value in (None, ""):
            continue
        try:
            candidate = normalize_legacy_date(raw_value)
        except ValueError as exc:
            raise ValueError(
                f"Unsupported legacy invoice date in batch {batch_id}: {raw_value}"
            ) from exc
        if candidate is not None and (cutoff is None or candidate > cutoff):
            cutoff = candidate
    return cutoff.isoformat() if cutoff else None


async def _fetch_previous_scope_run(
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
    scope_key: str,
    current_run_id: uuid.UUID,
) -> dict[str, object]:
    quoted_schema = _quoted_identifier(schema_name)
    row = await connection.fetchrow(
        f"""
		SELECT id, batch_id, attempt_number, status
		FROM {quoted_schema}.canonical_import_runs
		WHERE tenant_id = $1
			AND id <> $2
			AND summary->>'scope_key' = $3
		ORDER BY completed_at DESC, started_at DESC
		LIMIT 1
		""",
        tenant_id,
        current_run_id,
        scope_key,
    )
    return _coerce_row(row)


async def _persist_validation_summary(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    merged_summary: Mapping[str, object],
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        f"UPDATE {quoted_schema}.canonical_import_runs SET summary = $2::jsonb WHERE id = $1",
        run_id,
        json.dumps(merged_summary),
    )


def _merge_summary_payload(
    *,
    existing_summary: Mapping[str, object],
    report: MigrationValidationReport,
    json_path: Path,
    markdown_path: Path,
) -> dict[str, object]:
    merged = dict(existing_summary)
    merged.update(dict(report.counts or {}))
    merged["scope_key"] = report.replay.scope_key
    merged["scope_cutoff_date"] = report.replay.scope_cutoff_date
    merged["validation_status"] = report.status
    merged["validation_blocking_issue_count"] = report.blocking_issue_count
    merged["validation_artifacts"] = {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }
    merged["replay"] = asdict(report.replay)
    merged["epic13_handoff"] = report.epic13_handoff
    return merged


async def validate_import_batch(
    *,
    batch_id: str,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str | None = None,
    attempt_number: int | None = None,
    output_dir: Path | None = None,
) -> MigrationBatchValidationResult:
    resolved_schema = schema_name or settings.legacy_import_schema
    connection = await _open_raw_connection()
    try:
        canonical_run = await _fetch_latest_canonical_run(
            connection,
            resolved_schema,
            tenant_id,
            batch_id,
            attempt_number=attempt_number,
        )
        if not canonical_run:
            attempt_suffix = f" attempt {attempt_number}" if attempt_number is not None else ""
            raise ValueError(f"No canonical import run found for batch {batch_id}{attempt_suffix}")

        stage_run = await _fetch_latest_stage_run(
            connection,
            tenant_id,
            batch_id,
            canonical_started_at=canonical_run.get("started_at"),
        )
        if not stage_run:
            raise ValueError(f"No completed staging run found for batch {batch_id}")
        stage_rows = await _fetch_stage_table_runs(connection, uuid.UUID(str(stage_run["id"])))

        canonical_run_id = uuid.UUID(str(canonical_run["id"]))
        counts = {
            key: _as_int(value)
            for key, value in _coerce_row(canonical_run.get("summary")).items()
            if key.endswith("_count")
        }
        failed_stages = await _fetch_canonical_step_runs(
            connection, resolved_schema, canonical_run_id
        )
        canonical_status = _as_text(canonical_run.get("status")) or "unknown"
        if canonical_status != "completed" and not failed_stages:
            failed_stages = (
                ValidationStageFailure(
                    stage_name="canonical_run",
                    row_count=0,
                    error_message=_as_text(canonical_run.get("error_message")) or None,
                ),
            )
        mapping_summary = await _fetch_product_mapping_summary(
            connection,
            resolved_schema,
            tenant_id,
            batch_id,
        )
        cutoff_date = await _fetch_cutoff_date(connection, resolved_schema, batch_id)
        scope_key = _derive_scope_key(
            tenant_id=tenant_id,
            schema_name=resolved_schema,
            cutoff_date=cutoff_date,
            stage_rows=stage_rows,
            mapping_summary=mapping_summary,
            failed_stages=failed_stages,
            counts=counts,
        )
        previous_scope_run = await _fetch_previous_scope_run(
            connection,
            resolved_schema,
            tenant_id,
            scope_key,
            canonical_run_id,
        )
        report = build_validation_report(
            batch_id=batch_id,
            tenant_id=tenant_id,
            schema_name=resolved_schema,
            attempt_number=_as_int(canonical_run.get("attempt_number")) or 1,
            stage_rows=stage_rows,
            mapping_summary=mapping_summary,
            failed_stages=failed_stages,
            counts=counts,
            cutoff_date=cutoff_date,
            previous_scope_run=previous_scope_run,
        )
        json_path, markdown_path = _artifact_paths_for_report(report, output_dir=output_dir)
        temp_json_path = json_path.with_suffix(f"{json_path.suffix}.tmp")
        temp_markdown_path = markdown_path.with_suffix(f"{markdown_path.suffix}.tmp")
        _write_report_files(
            report,
            json_path=temp_json_path,
            markdown_path=temp_markdown_path,
        )
        merged_summary = _merge_summary_payload(
            existing_summary=_coerce_row(canonical_run.get("summary")),
            report=report,
            json_path=json_path,
            markdown_path=markdown_path,
        )
        try:
            await _persist_validation_summary(
                connection, resolved_schema, canonical_run_id, merged_summary
            )
        except Exception:
            temp_json_path.unlink(missing_ok=True)
            temp_markdown_path.unlink(missing_ok=True)
            raise
        temp_json_path.replace(json_path)
        temp_markdown_path.replace(markdown_path)
        return MigrationBatchValidationResult(
            report=report,
            json_path=json_path,
            markdown_path=markdown_path,
        )
    finally:
        await connection.close()
