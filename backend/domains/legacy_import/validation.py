"""Validation and replay-safety reporting for legacy import batches.

Story 15.27: Incremental validation supports scoped batches that verify only the
affected domains and entities. It emits artifacts that distinguish freshness
success from promotion eligibility, records `summary_valid`, `batch_mode`,
and `affected_domains` for operator observability, and advances watermarks
only after durable scoped success (AC1, AC3, AC4, AC5).
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Mapping, TypedDict

from common.config import PROJECT_ROOT, settings
from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.normalization import normalize_legacy_date
from domains.legacy_import.staging import (
    _open_raw_connection,
    _quoted_identifier,
    is_ephemeral_live_source_table,
)

_ARTIFACT_TOKEN_RE = re.compile(r"[^A-Za-z0-9._-]+")
_MISSING_RELATION_ERROR_RE = re.compile(
    r"\brelation\b.*\bdoes not exist\b",
    re.IGNORECASE | re.DOTALL,
)


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
class ProductCategoryReviewCandidate:
    legacy_code: str
    name: str
    current_category: str
    category_source: str
    category_rule_id: str
    category_confidence: str
    review_reason: str


@dataclass(slots=True, frozen=True)
class ProductCategoryReviewSummary:
    candidate_count: int
    fallback_count: int
    low_confidence_count: int
    excluded_count: int
    candidates: tuple[ProductCategoryReviewCandidate, ...]


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


def _is_ephemeral_stage_table_disappearance(row: StageReconciliationRow) -> bool:
    return bool(
        row.error_message
        and is_ephemeral_live_source_table(row.table_name)
        and _MISSING_RELATION_ERROR_RE.search(row.error_message)
    )


@dataclass(slots=True, frozen=True)
class ImportReplayMetadata:
    scope_key: str
    scope_cutoff_date: str | None
    disposition: str
    previous_batch_id: str | None = None
    previous_attempt_number: int | None = None
    previous_status: str | None = None


@dataclass(slots=True, frozen=True)
class LegacyHeaderSnapshotCoverage:
    order_count: int
    order_snapshot_count: int
    invoice_count: int
    invoice_snapshot_count: int
    supplier_invoice_count: int
    supplier_invoice_snapshot_count: int

    @property
    def imported_document_count(self) -> int:
        return self.order_count + self.invoice_count + self.supplier_invoice_count

    @property
    def snapshot_count(self) -> int:
        return (
            self.order_snapshot_count
            + self.invoice_snapshot_count
            + self.supplier_invoice_snapshot_count
        )

    @property
    def missing_snapshot_count(self) -> int:
        return max(0, self.imported_document_count - self.snapshot_count)

    def to_counts(self) -> dict[str, int]:
        return {
            "legacy_header_snapshot_document_count": self.imported_document_count,
            "legacy_header_snapshot_count": self.snapshot_count,
            "legacy_header_snapshot_missing_count": self.missing_snapshot_count,
            "order_snapshot_count": self.order_snapshot_count,
            "invoice_snapshot_count": self.invoice_snapshot_count,
            "supplier_invoice_snapshot_count": self.supplier_invoice_snapshot_count,
        }


# Story 15.27: Incremental validation scope dataclasses.
class IncrementalValidationScope(TypedDict, total=False):
    """Scope parameters for incremental validation (AC1)."""

    affected_domains: Sequence[str]
    """Domains that were touched by the incremental canonical import."""

    entity_scope: dict[str, dict[str, object]]
    """Per-domain closure keys identifying affected entities."""

    scoped_document_count: int | None
    """Count of documents processed in the scoped import."""

    last_successful_batch_ids: dict[str, str]
    """Prior successful batch IDs per domain for carryforward validation."""


@dataclass(slots=True, frozen=True)
class ValidationArtifactMetadata:
    """AC5: Observability metadata emitted with every validation report."""

    batch_mode: str
    """'full', 'incremental', or 'rebaseline'."""

    affected_domains: tuple[str, ...]
    """Domains validated by this report."""

    summary_valid: bool
    """True when validation produced a clean or warning status."""

    watermark_advanced: bool
    """True when watermarks were advanced after this batch."""

    root_failed_step: str | None
    """Step name that caused validation failure, if any."""

    root_error_message: str | None
    """Error message from the root failure, if any."""

    requires_rebaseline: bool
    """True when a full rebaseline is required instead of incremental."""

    rebaseline_reason: str | None
    """Human-readable reason when requires_rebaseline is True."""

    freshness_success: bool
    """True when scoped import + validation succeeded (AC5)."""

    promotion_eligible: bool
    """True when batch passes the shared promotion policy (AC5)."""

    incremental_scope: IncrementalValidationScope | None
    """Full scope metadata for incremental batches; None for full batches."""


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
    snapshot_coverage: LegacyHeaderSnapshotCoverage | None = None
    category_review_summary: ProductCategoryReviewSummary | None = None
    # Story 15.27: Incremental validation observability fields (AC3-5).
    artifact_metadata: ValidationArtifactMetadata | None = None

    def to_dict(self) -> dict[str, object]:
        result = {
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
            "snapshot_coverage": (
                asdict(self.snapshot_coverage) if self.snapshot_coverage is not None else None
            ),
            "category_review_summary": (
                asdict(self.category_review_summary)
                if self.category_review_summary is not None
                else None
            ),
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
        # Story 15.27: Include artifact metadata for operator observability (AC5).
        if self.artifact_metadata is not None:
            result["artifact_metadata"] = asdict(self.artifact_metadata)
        return result


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
    if isinstance(row, (str, bytes, bytearray)):
        raw = row.decode("utf-8") if isinstance(row, (bytes, bytearray)) else row
        if raw.strip() == "":
            return {}
        payload = json.loads(raw)
        return payload if isinstance(payload, dict) else {}
    return dict(row)


def _as_int(value: object | None) -> int:
    if value in (None, ""):
        return 0
    return int(value)


def _as_text(value: object | None) -> str:
    return str(value or "").strip()


async def _fetch_customer_type_counts(
    connection,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    rows = await connection.fetch(
        """
        SELECT customer_type, COUNT(*) AS customer_count
        FROM customers
        WHERE tenant_id = $1
        GROUP BY customer_type
        """,
        tenant_id,
    )
    counts = {
        "customer_type_dealer_count": 0,
        "customer_type_end_user_count": 0,
        "customer_type_unknown_count": 0,
    }
    for row in rows:
        payload = _coerce_row(row)
        customer_type = _as_text(payload.get("customer_type")) or "unknown"
        if customer_type not in {"dealer", "end_user", "unknown"}:
            continue
        counts[f"customer_type_{customer_type}_count"] = _as_int(
            payload.get("customer_count")
        )
    return counts


def _derive_scope_key(
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
    cutoff_date: str | None,
    stage_rows: tuple[StageReconciliationRow, ...],
    mapping_summary: ProductMappingValidationSummary,
    failed_stages: tuple[ValidationStageFailure, ...],
    counts: Mapping[str, int],
    category_review_summary: ProductCategoryReviewSummary | None,
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
        "category_review_summary": (
            {
                "candidate_count": category_review_summary.candidate_count,
                "fallback_count": category_review_summary.fallback_count,
                "low_confidence_count": category_review_summary.low_confidence_count,
                "excluded_count": category_review_summary.excluded_count,
                "candidates": [
                    {
                        "legacy_code": candidate.legacy_code,
                        "current_category": candidate.current_category,
                        "review_reason": candidate.review_reason,
                    }
                    for candidate in category_review_summary.candidates
                ],
            }
            if category_review_summary is not None
            else None
        ),
        "failed_stages": [asdict(stage) for stage in failed_stages],
        "counts": dict(sorted(counts.items())),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return digest[:16]


def _build_artifact_metadata(
    *,
    batch_mode: str,
    affected_domains: tuple[str, ...],
    status: str,
    blocking_issue_count: int,
    failed_stages: tuple[ValidationStageFailure, ...],
    incremental_scope: IncrementalValidationScope | None,
    promotion_eligible: bool = False,
) -> ValidationArtifactMetadata:
    """Build incremental validation artifact metadata (AC3-5).

    Distinguishes freshness success (scoped import + validation passed)
    from promotion eligibility (passes shared promotion policy).
    """
    summary_valid = status in ("clean", "warning")
    freshness_success = summary_valid and blocking_issue_count == 0

    # Determine root failure for operator observability (AC4).
    root_failed_step: str | None = None
    root_error_message: str | None = None
    if failed_stages:
        root_failed_step = failed_stages[0].stage_name
        root_error_message = failed_stages[0].error_message

    # Determine rebaseline requirement (AC4).
    requires_rebaseline = status == "blocked" or blocking_issue_count > 0
    if requires_rebaseline:
        if root_failed_step:
            rebaseline_reason = f"Validation blocked by failed stage: {root_failed_step}"
        elif blocking_issue_count > 0:
            rebaseline_reason = f"{blocking_issue_count} blocking issue(s) must be resolved"
        else:
            rebaseline_reason = "Unknown blocking condition requires rebaseline"
    else:
        rebaseline_reason = None

    return ValidationArtifactMetadata(
        batch_mode=batch_mode,
        affected_domains=affected_domains,
        summary_valid=summary_valid,
        watermark_advanced=False,  # Set by caller after durable success (AC3).
        root_failed_step=root_failed_step,
        root_error_message=root_error_message,
        requires_rebaseline=requires_rebaseline,
        rebaseline_reason=rebaseline_reason,
        freshness_success=freshness_success,
        promotion_eligible=promotion_eligible and freshness_success,
        incremental_scope=incremental_scope,
    )


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
    snapshot_coverage: LegacyHeaderSnapshotCoverage | None = None,
    category_review_summary: ProductCategoryReviewSummary | None = None,
    # Story 15.27: Incremental scope parameters (AC1, AC5).
    batch_mode: str | None = None,
    affected_domains: Sequence[str] | None = None,
    entity_scope: dict[str, dict[str, object]] | None = None,
    scoped_document_count: int | None = None,
    last_successful_batch_ids: dict[str, str] | None = None,
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
            ephemeral_disappearance = _is_ephemeral_stage_table_disappearance(row)
            issues.append(
                MigrationValidationIssue(
                    code="stage-load-failed",
                    severity=2 if ephemeral_disappearance else 1,
                    message=(
                        f"Ephemeral live-source table {row.table_name} disappeared during staging; "
                        "the table is treated as a transient report scratch table."
                        if ephemeral_disappearance
                        else f"Stage table {row.table_name} failed to load."
                    ),
                    details={
                        "table_name": row.table_name,
                        "error_message": row.error_message,
                        "transient_source_table": ephemeral_disappearance,
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

    if snapshot_coverage is not None and snapshot_coverage.missing_snapshot_count > 0:
        issues.append(
            MigrationValidationIssue(
                code="legacy-header-snapshot-missing",
                severity=1,
                message=(
                    "Legacy header snapshots are missing for "
                    f"{snapshot_coverage.missing_snapshot_count} of "
                    f"{snapshot_coverage.imported_document_count} imported documents."
                ),
                details={
                    "order_count": snapshot_coverage.order_count,
                    "order_snapshot_count": snapshot_coverage.order_snapshot_count,
                    "invoice_count": snapshot_coverage.invoice_count,
                    "invoice_snapshot_count": snapshot_coverage.invoice_snapshot_count,
                    "supplier_invoice_count": snapshot_coverage.supplier_invoice_count,
                    "supplier_invoice_snapshot_count": (
                        snapshot_coverage.supplier_invoice_snapshot_count
                    ),
                    "missing_snapshot_count": snapshot_coverage.missing_snapshot_count,
                },
            )
        )

    if category_review_summary is not None and category_review_summary.candidate_count > 0:
        issues.append(
            MigrationValidationIssue(
                code="provisional-category-assignments",
                severity=2,
                message=(
                    f"{category_review_summary.candidate_count} products still carry provisional "
                    "family categories pending review."
                ),
                details={
                    "candidate_count": category_review_summary.candidate_count,
                    "fallback_count": category_review_summary.fallback_count,
                    "low_confidence_count": category_review_summary.low_confidence_count,
                    "excluded_count": category_review_summary.excluded_count,
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
        category_review_summary=category_review_summary,
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
        "resolution_status_counts": {
            key: _as_int(value)
            for key, value in counts.items()
            if key.startswith("resolution_") and key.endswith("_count")
        },
        "comparison_inputs": [
            "stage_reconciliation",
            "mapping_summary",
            "failed_stages",
            "counts",
            "snapshot_coverage",
            "resolution_status_counts",
        ],
        "boundary": (
            "Story 15.5 emits batch-scoped import evidence only. "
            "Epic 13 owns longer-horizon shadow-mode reconciliation."
        ),
        "legacy_header_snapshot_count": _as_int(counts.get("legacy_header_snapshot_count")),
        "legacy_header_snapshot_missing_count": _as_int(
            counts.get("legacy_header_snapshot_missing_count")
        ),
    }

    # Story 15.27: Build incremental validation artifact metadata (AC1, AC5).
    resolved_batch_mode = batch_mode or "full"
    resolved_affected_domains = tuple(affected_domains) if affected_domains else ()
    incremental_scope: IncrementalValidationScope | None = None
    if resolved_batch_mode == "incremental" and resolved_affected_domains:
        incremental_scope = IncrementalValidationScope(
            affected_domains=list(resolved_affected_domains),
            entity_scope=dict(entity_scope) if entity_scope else {},
            scoped_document_count=scoped_document_count,
            last_successful_batch_ids=(
                dict(last_successful_batch_ids) if last_successful_batch_ids else {}
            ),
        )

    artifact_metadata = _build_artifact_metadata(
        batch_mode=resolved_batch_mode,
        affected_domains=resolved_affected_domains,
        status=status,
        blocking_issue_count=blocking_issue_count,
        failed_stages=failed_stages,
        incremental_scope=incremental_scope,
    )

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
        snapshot_coverage=snapshot_coverage,
        category_review_summary=category_review_summary,
        artifact_metadata=artifact_metadata,
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
    ]
    # Story 15.27: Include incremental validation metadata section (AC3-5).
    if report.artifact_metadata is not None:
        meta = report.artifact_metadata
        lines.append("## Incremental Validation Metadata")
        lines.append("")
        lines.append(f"- Batch mode: {meta.batch_mode}")
        if meta.affected_domains:
            lines.append(f"- Affected domains: {', '.join(meta.affected_domains)}")
        lines.append(f"- Summary valid: {meta.summary_valid}")
        lines.append(f"- Freshness success: {meta.freshness_success}")
        lines.append(f"- Promotion eligible: {meta.promotion_eligible}")
        lines.append(f"- Watermark advanced: {meta.watermark_advanced}")
        lines.append(f"- Requires rebaseline: {meta.requires_rebaseline}")
        if meta.root_failed_step:
            lines.append(f"- Root failed step: {meta.root_failed_step}")
        if meta.root_error_message:
            lines.append(f"- Root error message: {meta.root_error_message}")
        if meta.rebaseline_reason:
            lines.append(f"- Rebaseline reason: {meta.rebaseline_reason}")
        lines.append("")
    lines.append("## Row Count Reconciliation")
    lines.append("")
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
    lines.extend(["", "## Snapshot Coverage", ""])
    if report.snapshot_coverage is None:
        lines.append("- Snapshot coverage was not collected.")
    else:
        lines.append(
            "- "
            f"orders={report.snapshot_coverage.order_snapshot_count}/"
            f"{report.snapshot_coverage.order_count}, "
            f"invoices={report.snapshot_coverage.invoice_snapshot_count}/"
            f"{report.snapshot_coverage.invoice_count}, "
            f"supplier_invoices={report.snapshot_coverage.supplier_invoice_snapshot_count}/"
            f"{report.snapshot_coverage.supplier_invoice_count}, "
            f"missing={report.snapshot_coverage.missing_snapshot_count}"
        )
    lines.extend(["", "## Category Review", ""])
    if report.category_review_summary is None or not report.category_review_summary.candidate_count:
        lines.append("- No provisional category assignments detected.")
    else:
        lines.append(
            "- "
            f"candidates={report.category_review_summary.candidate_count}, "
            f"fallback={report.category_review_summary.fallback_count}, "
            f"low_confidence={report.category_review_summary.low_confidence_count}, "
            f"excluded={report.category_review_summary.excluded_count}"
        )
        for candidate in report.category_review_summary.candidates:
            lines.append(
                "- "
                f"{candidate.legacy_code}: {candidate.current_category} "
                f"({candidate.review_reason}, source={candidate.category_source}, "
                f"rule={candidate.category_rule_id}, confidence={candidate.category_confidence})"
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
    resolution_status_counts = report.epic13_handoff.get("resolution_status_counts") or {}
    if resolution_status_counts:
        lines.append(
            "- Resolution states: "
            + ", ".join(
                f"{key.removeprefix('resolution_').removesuffix('_count')}={value}"
                for key, value in sorted(resolution_status_counts.items())
            )
        )
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


async def _fetch_product_category_review_summary(
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
    batch_id: str,
) -> ProductCategoryReviewSummary:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT
			legacy_code,
			name,
			current_category,
			category_source,
			category_rule_id,
			category_confidence,
			review_reason
		FROM {quoted_schema}.product_category_review_candidates
		WHERE tenant_id = $1 AND batch_id = $2
		ORDER BY review_reason, legacy_code
		""",
        tenant_id,
        batch_id,
    )
    candidates = tuple(
        ProductCategoryReviewCandidate(
            legacy_code=_as_text(payload.get("legacy_code")),
            name=_as_text(payload.get("name")),
            current_category=_as_text(payload.get("current_category")),
            category_source=_as_text(payload.get("category_source")),
            category_rule_id=_as_text(payload.get("category_rule_id")),
            category_confidence=_as_text(payload.get("category_confidence")),
            review_reason=_as_text(payload.get("review_reason")),
        )
        for payload in (_coerce_row(row) for row in rows)
    )
    def _count_by_reason(reason: str) -> int:
        return sum(1 for c in candidates if c.review_reason == reason)

    return ProductCategoryReviewSummary(
        candidate_count=len(candidates),
        fallback_count=_count_by_reason("fallback_assignment"),
        low_confidence_count=_count_by_reason("low_confidence"),
        excluded_count=_count_by_reason("excluded_path"),
        candidates=candidates,
    )


async def _fetch_cutoff_date(connection, schema_name: str, batch_id: str) -> str | None:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT col_3 AS invoice_date_raw
		FROM {quoted_schema}.tbsslipx
		WHERE _batch_id = $1
		UNION ALL
        SELECT CASE
            WHEN COALESCE(col_62, '') NOT IN ('', '1900-01-01') THEN col_62
            ELSE col_3
        END AS invoice_date_raw
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
    if report.snapshot_coverage is not None:
        merged["legacy_header_snapshot_coverage"] = asdict(report.snapshot_coverage)
    if report.category_review_summary is not None:
        merged["category_review_summary"] = asdict(report.category_review_summary)
    # Story 15.27: Include incremental validation metadata in summary (AC3-5).
    if report.artifact_metadata is not None:
        merged["artifact_metadata"] = asdict(report.artifact_metadata)
    return merged


async def _fetch_legacy_header_snapshot_coverage(
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
    batch_id: str,
) -> LegacyHeaderSnapshotCoverage:
    quoted_schema = _quoted_identifier(schema_name)
    row = await connection.fetchrow(
        f"""
        SELECT
            COUNT(*) FILTER (WHERE lineage.canonical_table = 'orders')::INTEGER AS order_count,
            COUNT(*) FILTER (
                WHERE lineage.canonical_table = 'orders'
                    AND orders_record.legacy_header_snapshot IS NOT NULL
            )::INTEGER AS order_snapshot_count,
            COUNT(*) FILTER (WHERE lineage.canonical_table = 'invoices')::INTEGER AS invoice_count,
            COUNT(*) FILTER (
                WHERE lineage.canonical_table = 'invoices'
                    AND invoices_record.legacy_header_snapshot IS NOT NULL
            )::INTEGER AS invoice_snapshot_count,
            COUNT(*) FILTER (
                WHERE lineage.canonical_table = 'supplier_invoices'
            )::INTEGER AS supplier_invoice_count,
            COUNT(*) FILTER (
                WHERE lineage.canonical_table = 'supplier_invoices'
                    AND supplier_invoices_record.legacy_header_snapshot IS NOT NULL
            )::INTEGER AS supplier_invoice_snapshot_count
        FROM {quoted_schema}.canonical_record_lineage AS lineage
        LEFT JOIN orders AS orders_record
            ON lineage.canonical_table = 'orders'
            AND orders_record.id = lineage.canonical_id
            AND orders_record.tenant_id = lineage.tenant_id
        LEFT JOIN invoices AS invoices_record
            ON lineage.canonical_table = 'invoices'
            AND invoices_record.id = lineage.canonical_id
            AND invoices_record.tenant_id = lineage.tenant_id
        LEFT JOIN supplier_invoices AS supplier_invoices_record
            ON lineage.canonical_table = 'supplier_invoices'
            AND supplier_invoices_record.id = lineage.canonical_id
            AND supplier_invoices_record.tenant_id = lineage.tenant_id
        WHERE lineage.tenant_id = $1
            AND lineage.batch_id = $2
            AND lineage.canonical_table IN ('orders', 'invoices', 'supplier_invoices')
        """,
        tenant_id,
        batch_id,
    )
    payload = _coerce_row(row)
    return LegacyHeaderSnapshotCoverage(
        order_count=_as_int(payload.get("order_count")),
        order_snapshot_count=_as_int(payload.get("order_snapshot_count")),
        invoice_count=_as_int(payload.get("invoice_count")),
        invoice_snapshot_count=_as_int(payload.get("invoice_snapshot_count")),
        supplier_invoice_count=_as_int(payload.get("supplier_invoice_count")),
        supplier_invoice_snapshot_count=_as_int(
            payload.get("supplier_invoice_snapshot_count")
        ),
    )


async def _fetch_resolution_status_counts(
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
    batch_id: str,
) -> dict[str, int]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
        SELECT status, COUNT(*)::INTEGER AS row_count
        FROM {quoted_schema}.source_row_resolution
        WHERE tenant_id = $1
            AND batch_id = $2
        GROUP BY status
        ORDER BY status
        """,
        tenant_id,
        batch_id,
    )
    counts: dict[str, int] = {}
    for row in rows:
        payload = _coerce_row(row)
        status = _as_text(payload.get("status"))
        if not status:
            continue
        counts[f"resolution_{status}_count"] = _as_int(payload.get("row_count"))
    return counts


async def validate_import_batch(
    *,
    batch_id: str,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str | None = None,
    attempt_number: int | None = None,
    output_dir: Path | None = None,
    # Story 15.27: Incremental scope parameters for scoped validation (AC1).
    batch_mode: str | None = None,
    affected_domains: Sequence[str] | None = None,
    entity_scope: dict[str, dict[str, object]] | None = None,
    scoped_document_count: int | None = None,
    last_successful_batch_ids: dict[str, str] | None = None,
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
        snapshot_coverage = await _fetch_legacy_header_snapshot_coverage(
            connection,
            resolved_schema,
            tenant_id,
            batch_id,
        )
        resolution_status_counts = await _fetch_resolution_status_counts(
            connection,
            resolved_schema,
            tenant_id,
            batch_id,
        )
        customer_type_counts = await _fetch_customer_type_counts(connection, tenant_id)
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
        category_review_summary = await _fetch_product_category_review_summary(
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
            category_review_summary=category_review_summary,
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
            counts={
                **counts,
                **snapshot_coverage.to_counts(),
                **resolution_status_counts,
                **customer_type_counts,
                "category_review_candidate_count": category_review_summary.candidate_count,
                "category_review_fallback_count": category_review_summary.fallback_count,
                "category_review_low_confidence_count": (
                    category_review_summary.low_confidence_count
                ),
                "category_review_excluded_count": category_review_summary.excluded_count,
            },
            cutoff_date=cutoff_date,
            previous_scope_run=previous_scope_run,
            snapshot_coverage=snapshot_coverage,
            category_review_summary=category_review_summary,
            # Story 15.27: Pass incremental scope parameters (AC1, AC5).
            batch_mode=batch_mode,
            affected_domains=affected_domains,
            entity_scope=entity_scope,
            scoped_document_count=scoped_document_count,
            last_successful_batch_ids=last_successful_batch_ids,
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
