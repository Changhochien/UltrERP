"""Legacy product-category review helpers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.shared import coerce_mapping as _coerce_mapping
from domains.legacy_import.staging import _open_raw_connection, _quoted_identifier

_APPROVED_CATEGORY_VALUES = frozenset(
    {
        "V-Belts",
        "Timing Belts",
        "Ribbed Belts",
        "Variable-Speed Belts",
        "Flat / Specialty Belts",
        "Vehicle Belts",
        "Belt Supplies",
        "Non-Merchandise",
        "Other Power Transmission",
    }
)


@dataclass(slots=True, frozen=True)
class ProductCategoryReviewExportResult:
    batch_id: str
    schema_name: str
    output_path: Path
    exported_row_count: int


@dataclass(slots=True, frozen=True)
class ProductCategoryReviewImportResult:
    batch_id: str
    schema_name: str
    input_path: Path
    applied_decision_count: int


def _build_review_rows(
    batch_id: str,
    candidates: tuple[dict[str, object], ...],
) -> list[dict[str, str]]:
    review_rows: list[dict[str, str]] = []
    for candidate in candidates:
        review_rows.append(
            {
                "batch_id": batch_id,
                "legacy_code": str(candidate["legacy_code"]),
                "name": str(candidate.get("name") or ""),
                "legacy_category": str(candidate.get("legacy_category") or ""),
                "stock_kind": str(candidate.get("stock_kind") or ""),
                "current_category": str(candidate.get("current_category") or ""),
                "category_source": str(candidate.get("category_source") or ""),
                "category_rule_id": str(candidate.get("category_rule_id") or ""),
                "category_confidence": str(candidate.get("category_confidence") or ""),
                "review_reason": str(candidate.get("review_reason") or ""),
                "review_status": "",
                "approved_category": "",
                "review_notes": "",
            }
        )
    return review_rows


def _collect_review_decisions(
    rows: list[dict[str, str]],
    expected_batch_id: str,
) -> dict[str, dict[str, str]]:
    decisions: dict[str, dict[str, str]] = {}
    for row in rows:
        row_batch_id = str(row.get("batch_id") or "").strip()
        if row_batch_id != expected_batch_id:
            raise ValueError(
                "Review row batch_id does not match requested batch: "
                f"{row_batch_id or '<empty>'} != {expected_batch_id}"
            )

        review_status = str(row.get("review_status") or "").strip().lower()
        if not review_status:
            continue
        if review_status not in {"approved", "keep_current"}:
            raise ValueError(f"Unsupported review_status: {review_status}")

        legacy_code = str(row.get("legacy_code") or "").strip()
        if not legacy_code:
            raise ValueError("Review row missing legacy_code")
        if legacy_code in decisions:
            raise ValueError(f"Multiple review decisions provided for legacy_code: {legacy_code}")

        current_category = str(row.get("current_category") or "").strip()
        approved_category = str(row.get("approved_category") or "").strip() or current_category
        if review_status == "keep_current" and approved_category != current_category:
            raise ValueError("keep_current cannot change category")
        if not approved_category:
            raise ValueError(f"Approved review row for {legacy_code} is missing approved_category")
        if approved_category not in _APPROVED_CATEGORY_VALUES:
            raise ValueError(f"Unsupported approved_category: {approved_category}")

        decisions[legacy_code] = {
            "approved_category": approved_category,
            "review_notes": str(row.get("review_notes") or "").strip(),
        }
    return decisions


async def _fetch_review_candidate_codes(
    connection,
    schema_name: str,
    tenant_id,
    batch_id: str,
) -> set[str]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT legacy_code
		FROM {quoted_schema}.product_category_review_candidates
		WHERE tenant_id = $1 AND batch_id = $2
		""",
        tenant_id,
        batch_id,
    )
    return {
        str(_coerce_mapping(row).get("legacy_code") or "").strip()
        for row in rows
        if str(_coerce_mapping(row).get("legacy_code") or "").strip()
    }


async def _refresh_review_batch(*, batch_id: str, tenant_id, schema_name: str) -> None:
    from domains.legacy_import.normalization import run_normalization

    await run_normalization(
        batch_id=batch_id,
        tenant_id=tenant_id,
        schema_name=schema_name,
    )


async def export_product_category_review(
    *,
    batch_id: str,
    output_path: Path,
    tenant_id=DEFAULT_TENANT_ID,
    schema_name: str = "raw_legacy",
) -> ProductCategoryReviewExportResult:
    quoted_schema = _quoted_identifier(schema_name)
    connection = await _open_raw_connection()
    try:
        candidate_rows = await connection.fetch(
            f"""
			SELECT
				legacy_code,
				name,
				legacy_category,
				stock_kind,
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
    finally:
        await connection.close()

    rows = _build_review_rows(batch_id, tuple(_coerce_mapping(row) for row in candidate_rows))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "batch_id",
                "legacy_code",
                "name",
                "legacy_category",
                "stock_kind",
                "current_category",
                "category_source",
                "category_rule_id",
                "category_confidence",
                "review_reason",
                "review_status",
                "approved_category",
                "review_notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    return ProductCategoryReviewExportResult(
        batch_id=batch_id,
        schema_name=schema_name,
        output_path=output_path,
        exported_row_count=len(rows),
    )


async def import_product_category_review(
    *,
    batch_id: str,
    input_path: Path,
    approved_by: str,
    tenant_id=DEFAULT_TENANT_ID,
    schema_name: str = "raw_legacy",
) -> ProductCategoryReviewImportResult:
    quoted_schema = _quoted_identifier(schema_name)
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    decisions = _collect_review_decisions(rows, batch_id)
    connection = await _open_raw_connection()
    try:
        async with connection.transaction():
            known_codes = await _fetch_review_candidate_codes(
                connection,
                schema_name,
                tenant_id,
                batch_id,
            )
            approved_at = datetime.now(UTC)
            for legacy_code, decision in decisions.items():
                if legacy_code not in known_codes:
                    raise ValueError(f"Unknown review candidate: {legacy_code}")
                await connection.execute(
                    f"""
					INSERT INTO {quoted_schema}.product_category_override (
						tenant_id,
						legacy_code,
						category,
						review_notes,
						approval_source,
						approved_by,
						approved_at,
						first_seen_batch_id,
						last_seen_batch_id
					)
					VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
					ON CONFLICT (tenant_id, legacy_code) DO UPDATE SET
						category = EXCLUDED.category,
						review_notes = EXCLUDED.review_notes,
						approval_source = EXCLUDED.approval_source,
						approved_by = EXCLUDED.approved_by,
						approved_at = EXCLUDED.approved_at,
						last_seen_batch_id = EXCLUDED.last_seen_batch_id,
						updated_at = NOW()
					""",
                    tenant_id,
                    legacy_code,
                    decision["approved_category"],
                    decision["review_notes"] or None,
                    "review-import",
                    approved_by,
                    approved_at,
                    batch_id,
                    batch_id,
                )
    finally:
        await connection.close()

    if decisions:
        await _refresh_review_batch(
            batch_id=batch_id,
            tenant_id=tenant_id,
            schema_name=schema_name,
        )

    return ProductCategoryReviewImportResult(
        batch_id=batch_id,
        schema_name=schema_name,
        input_path=input_path,
        applied_decision_count=len(decisions),
    )