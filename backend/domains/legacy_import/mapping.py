"""Legacy product-code mapping helpers."""

from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Mapping

from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.normalization import deterministic_legacy_uuid
from domains.legacy_import.shared import coerce_mapping as _coerce_mapping
from domains.legacy_import.staging import _open_raw_connection, _quoted_identifier

CORRECTED_ORPHAN_CODE_BASELINE = 190
CORRECTED_ORPHAN_ROW_BASELINE = 523
UNKNOWN_PRODUCT_CODE = "UNKNOWN"
AUTO_APPROVED_RESOLUTION_TYPES = frozenset({"exact_match", "normalized_exact_match"})

_NORMALIZED_TOKEN_RE = re.compile(r"[^A-Z0-9]+")
_LEADING_NOTE_PREFIX_RE = re.compile(r"^N[13]\s+(.+)$", re.IGNORECASE)
_TRAILING_DIGIT_SUFFIX_RE = re.compile(r"^(.*\D)\d$")


@dataclass(slots=True, frozen=True)
class ProductMappingRecord:
    legacy_code: str
    target_code: str
    resolution_type: str
    confidence: Decimal
    affected_row_count: int
    notes: str | None = None


@dataclass(slots=True, frozen=True)
class ProductMappingCandidate:
    legacy_code: str
    candidate_code: str
    confidence: Decimal
    heuristic: str
    candidate_rank: int


@dataclass(slots=True, frozen=True)
class ProductMappingSeedResult:
    mappings: tuple[ProductMappingRecord, ...]
    candidates: tuple[ProductMappingCandidate, ...]
    exact_match_count: int
    unknown_count: int
    orphan_code_count: int
    orphan_row_count: int


@dataclass(slots=True, frozen=True)
class ProductMappingBatchResult:
    batch_id: str
    schema_name: str
    mapping_count: int
    candidate_count: int
    exact_match_count: int
    unknown_count: int
    orphan_code_count: int
    orphan_row_count: int


@dataclass(slots=True, frozen=True)
class ProductMappingReviewExportResult:
    batch_id: str
    schema_name: str
    output_path: Path
    exported_row_count: int


@dataclass(slots=True, frozen=True)
class ProductMappingReviewImportResult:
    batch_id: str
    schema_name: str
    input_path: Path
    applied_decision_count: int


def _normalize_code_token(value: str) -> str:
    return _NORMALIZED_TOKEN_RE.sub("", value.strip().upper())


def _collect_product_counts(
    rows: list[Mapping[str, object]] | tuple[Mapping[str, object], ...],
) -> Counter[str]:
    product_counts: Counter[str] = Counter()
    for row in rows:
        product_code = str(row.get("product_code") or "").strip()
        if not product_code:
            continue

        row_count = int(row.get("row_count") or 1)
        if row_count < 1:
            raise ValueError("Sales-detail row_count must be positive")

        product_counts[product_code] += row_count
    return product_counts


def _derive_candidate_matches(
    legacy_code: str,
    known_product_codes: set[str],
) -> list[tuple[str, Decimal, str]]:
    known_upper_map = {code.upper(): code for code in known_product_codes}
    proposals: list[tuple[str, Decimal, str]] = []
    seen: set[str] = set()
    legacy_upper = legacy_code.upper()
    legacy_token = _normalize_code_token(legacy_code)

    if "-" in legacy_upper:
        base_code = legacy_upper.rsplit("-", 1)[0]
        candidate_code = known_upper_map.get(base_code)
        if candidate_code:
            proposals.append((candidate_code, Decimal("0.85"), "strip-trailing-hyphen-segment"))
            seen.add(candidate_code)

    for candidate_code in sorted(known_product_codes):
        if candidate_code in seen:
            continue

        candidate_token = _normalize_code_token(candidate_code)
        if not legacy_token or not candidate_token or legacy_token == candidate_token:
            continue

        if legacy_token in candidate_token or candidate_token in legacy_token:
            proposals.append((candidate_code, Decimal("0.60"), "normalized-substring"))
            seen.add(candidate_code)

    return proposals[:5]


def _find_unique_normalized_exact_match(
    legacy_code: str,
    normalized_known_codes: Mapping[str, tuple[str, ...]],
) -> str | None:
    legacy_token = _normalize_code_token(legacy_code)
    if not legacy_token:
        return None

    matches = normalized_known_codes.get(legacy_token, ())
    if len(matches) != 1:
        return None

    return matches[0]


def _find_unique_deterministic_exact_match(
    legacy_code: str,
    known_product_codes: set[str],
    omitted_oh_exact_matches: Mapping[str, str] | None = None,
    dash_three_exact_matches: Mapping[str, str] | None = None,
) -> tuple[str, str] | None:
    known_upper_map = {code.upper(): code for code in known_product_codes}
    stripped_legacy_code = legacy_code.strip()

    prefix_match = _LEADING_NOTE_PREFIX_RE.match(stripped_legacy_code)
    if prefix_match is not None:
        candidate_code = prefix_match.group(1).strip()
        resolved_code = known_upper_map.get(candidate_code.upper())
        if resolved_code is not None:
            return resolved_code, "strip-leading-note-prefix"

    trailing_digit_match = _TRAILING_DIGIT_SUFFIX_RE.match(stripped_legacy_code)
    if trailing_digit_match is not None:
        candidate_code = trailing_digit_match.group(1).strip()
        resolved_code = known_upper_map.get(candidate_code.upper())
        if resolved_code is not None:
            return resolved_code, "strip-trailing-digit"

    if "-" in stripped_legacy_code:
        base_code, suffix = stripped_legacy_code.rsplit("-", 1)
        resolved_code = known_upper_map.get(base_code.strip().upper())
        if resolved_code is not None and (
            "-" in base_code or "." in base_code or suffix.isalpha()
        ):
            return resolved_code, "strip-trailing-hyphen-segment-exact"

    if omitted_oh_exact_matches is not None:
        resolved_code = omitted_oh_exact_matches.get(stripped_legacy_code.upper())
        if resolved_code is not None:
            return resolved_code, "append-oh-descriptor"

    if dash_three_exact_matches is not None:
        resolved_code = dash_three_exact_matches.get(stripped_legacy_code.upper())
        if resolved_code is not None:
            return resolved_code, "append-dash-three-suffix"

    return None


def _build_sole_family_suffix_matches(
    known_upper_map: Mapping[str, str],
    suffix: str,
) -> dict[str, str]:
    matches: dict[str, str] = {}
    for known_code_upper, known_code in known_upper_map.items():
        if not known_code_upper.endswith(suffix):
            continue

        base_code_upper = known_code_upper[: -len(suffix)].rstrip()
        family_matches = [
            candidate_upper
            for candidate_upper in known_upper_map
            if candidate_upper.startswith(base_code_upper)
        ]
        if len(family_matches) == 1:
            matches[base_code_upper] = known_code

    return matches


def seed_product_code_mappings(
    rows: list[Mapping[str, object]] | tuple[Mapping[str, object], ...],
    known_product_codes: set[str] | list[str] | tuple[str, ...],
) -> ProductMappingSeedResult:
    known_codes = {code.strip() for code in known_product_codes if str(code).strip()}
    known_upper_map = {code.upper(): code for code in known_codes}
    normalized_known_codes: dict[str, list[str]] = {}
    for code in sorted(known_codes):
        token = _normalize_code_token(code)
        if not token:
            continue
        normalized_known_codes.setdefault(token, []).append(code)

    omitted_oh_exact_matches = _build_sole_family_suffix_matches(known_upper_map, " OH")
    dash_three_exact_matches = _build_sole_family_suffix_matches(known_upper_map, "-3")

    product_counts = _collect_product_counts(rows)

    mappings: list[ProductMappingRecord] = []
    candidates: list[ProductMappingCandidate] = []
    exact_match_count = 0
    unknown_count = 0
    orphan_code_count = 0
    orphan_row_count = 0

    for legacy_code, affected_row_count in sorted(product_counts.items()):
        if legacy_code in known_codes:
            mappings.append(
                ProductMappingRecord(
                    legacy_code=legacy_code,
                    target_code=legacy_code,
                    resolution_type="exact_match",
                    confidence=Decimal("1.00"),
                    affected_row_count=affected_row_count,
                    notes="Seeded from tbsslipdtx.col_7 exact product-code match.",
                )
            )
            exact_match_count += 1
            continue

        deterministic_exact_match = _find_unique_deterministic_exact_match(
            legacy_code,
            known_codes,
            omitted_oh_exact_matches,
            dash_three_exact_matches,
        )
        if deterministic_exact_match is not None:
            target_code, heuristic = deterministic_exact_match
            mappings.append(
                ProductMappingRecord(
                    legacy_code=legacy_code,
                    target_code=target_code,
                    resolution_type="normalized_exact_match",
                    confidence=Decimal("0.95"),
                    affected_row_count=affected_row_count,
                    notes=(
                        "Seeded from tbsslipdtx.col_7 deterministic exact product-code "
                        f"cleanup ({heuristic})."
                    ),
                )
            )
            continue

        normalized_exact_match = _find_unique_normalized_exact_match(
            legacy_code,
            {
                token: tuple(codes)
                for token, codes in normalized_known_codes.items()
            },
        )
        if normalized_exact_match:
            mappings.append(
                ProductMappingRecord(
                    legacy_code=legacy_code,
                    target_code=normalized_exact_match,
                    resolution_type="normalized_exact_match",
                    confidence=Decimal("0.95"),
                    affected_row_count=affected_row_count,
                    notes=(
                        "Seeded from tbsslipdtx.col_7 unique normalized product-code "
                        "match."
                    ),
                )
            )
            continue

        orphan_code_count += 1
        orphan_row_count += affected_row_count

        for candidate_rank, (candidate_code, confidence, heuristic) in enumerate(
            _derive_candidate_matches(legacy_code, known_codes),
            start=1,
        ):
            candidates.append(
                ProductMappingCandidate(
                    legacy_code=legacy_code,
                    candidate_code=candidate_code,
                    confidence=confidence,
                    heuristic=heuristic,
                    candidate_rank=candidate_rank,
                )
            )

        mappings.append(
            ProductMappingRecord(
                legacy_code=legacy_code,
                target_code=UNKNOWN_PRODUCT_CODE,
                resolution_type="unknown",
                confidence=Decimal("0.00"),
                affected_row_count=affected_row_count,
                notes=(
                    "Seeded from tbsslipdtx.col_7 orphan analysis; retained on UNKNOWN "
                    "until an analyst approves a mapping."
                ),
            )
        )
        unknown_count += 1

    return ProductMappingSeedResult(
        mappings=tuple(mappings),
        candidates=tuple(candidates),
        exact_match_count=exact_match_count,
        unknown_count=unknown_count,
        orphan_code_count=orphan_code_count,
        orphan_row_count=orphan_row_count,
    )


async def _fetch_normalized_product_codes(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id,
) -> set[str]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT legacy_code
		FROM {quoted_schema}.normalized_products
		WHERE batch_id = $1 AND tenant_id = $2
		ORDER BY legacy_code
		""",
        batch_id,
        tenant_id,
    )
    return {
        str(_coerce_mapping(row)["legacy_code"]).strip()
        for row in rows
        if str(_coerce_mapping(row)["legacy_code"]).strip()
    }


async def _fetch_sales_detail_product_context(
    connection,
    schema_name: str,
    batch_id: str,
    legacy_code: str,
) -> dict[str, object]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
                SELECT
                        NULLIF(TRIM(col_8), '') AS name,
                        NULLIF(TRIM(col_18), '') AS unit,
                        _source_row_number AS source_row_number
                FROM {quoted_schema}.tbsslipdtx
                WHERE _batch_id = $1
                    AND TRIM(col_7) = $2
                ORDER BY
                        CASE WHEN NULLIF(TRIM(col_8), '') IS NULL THEN 1 ELSE 0 END,
                        CASE WHEN NULLIF(TRIM(col_18), '') IS NULL THEN 1 ELSE 0 END,
                        _source_row_number
                LIMIT 1
                """,
        batch_id,
        legacy_code,
    )
    if not rows:
        return {
            "name": legacy_code,
            "unit": "unknown",
            "source_row_number": 0,
        }

    row = _coerce_mapping(rows[0])
    return {
        "name": str(row.get("name") or "").strip() or legacy_code,
        "unit": str(row.get("unit") or "").strip() or "unknown",
        "source_row_number": int(row.get("source_row_number") or 0),
    }


async def _ensure_reviewed_synthetic_normalized_product(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id,
    legacy_code: str,
    name: str,
    unit: str,
    source_row_number: int,
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        f"""
		INSERT INTO {quoted_schema}.normalized_products (
			batch_id,
			tenant_id,
			deterministic_id,
			legacy_code,
			name,
			category,
			supplier_legacy_code,
			supplier_deterministic_id,
			origin,
			unit,
			status,
			created_date,
			last_sale_date,
			avg_cost,
			source_table,
			source_row_number
		)
		VALUES (
			$1,
			$2,
			$3,
			$4,
			$5,
			$6,
			$7,
			$8,
			$9,
			$10,
			$11,
			$12,
			$13,
			$14,
			$15,
			$16
		)
		ON CONFLICT DO NOTHING
		""",
        batch_id,
        tenant_id,
        deterministic_legacy_uuid("product", legacy_code),
        legacy_code,
        name,
        None,
        None,
        None,
        None,
        unit,
        "synthetic-review",
        None,
        None,
        None,
        "product_code_mapping_review",
        source_row_number,
    )


async def _ensure_unknown_normalized_product(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id,
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        f"""
		INSERT INTO {quoted_schema}.normalized_products (
			batch_id,
			tenant_id,
			deterministic_id,
			legacy_code,
			name,
			category,
			supplier_legacy_code,
			supplier_deterministic_id,
			origin,
			unit,
			status,
			created_date,
			last_sale_date,
			avg_cost,
			source_table,
			source_row_number
		)
		VALUES (
			$1,
			$2,
			$3,
			$4,
			$5,
			$6,
			$7,
			$8,
			$9,
			$10,
			$11,
			$12,
			$13,
			$14,
			$15,
			$16
		)
		ON CONFLICT DO NOTHING
		""",
        batch_id,
        tenant_id,
        deterministic_legacy_uuid("product", UNKNOWN_PRODUCT_CODE),
        UNKNOWN_PRODUCT_CODE,
        "Unknown Product",
        None,
        None,
        None,
        None,
        "unknown",
        "placeholder",
        None,
        None,
        None,
        "product_code_mapping",
        0,
    )


async def _fetch_sales_detail_product_rows(connection, schema_name: str, batch_id: str):
    quoted_schema = _quoted_identifier(schema_name)
    return await connection.fetch(
        f"""
		SELECT
			col_7 AS product_code,
			MIN(col_6) AS warehouse_code,
			COUNT(*)::INTEGER AS row_count
		FROM {quoted_schema}.tbsslipdtx
		WHERE _batch_id = $1
		GROUP BY col_7
		ORDER BY col_7
		""",
        batch_id,
    )


async def _fetch_existing_product_mappings(connection, schema_name: str, tenant_id):
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT
			legacy_code,
			target_code,
			resolution_type,
			confidence,
			affected_row_count,
			first_seen_batch_id,
			last_seen_batch_id,
			review_notes,
			approval_source,
			approved_by,
			approved_at
		FROM {quoted_schema}.product_code_mapping
		WHERE tenant_id = $1
		""",
        tenant_id,
    )
    return {str(_coerce_mapping(row)["legacy_code"]): _coerce_mapping(row) for row in rows}


async def _replace_mapping_candidates(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id,
    candidates: tuple[ProductMappingCandidate, ...],
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        (
            f"DELETE FROM {quoted_schema}.product_code_mapping_candidates "
            "WHERE tenant_id = $1 AND batch_id = $2"
        ),
        tenant_id,
        batch_id,
    )
    for candidate in candidates:
        await connection.execute(
            f"""
			INSERT INTO {quoted_schema}.product_code_mapping_candidates (
				tenant_id,
				batch_id,
				legacy_code,
				candidate_code,
				confidence,
				heuristic,
				candidate_rank
			)
			VALUES ($1, $2, $3, $4, $5, $6, $7)
			ON CONFLICT (tenant_id, batch_id, legacy_code, candidate_code) DO UPDATE SET
				confidence = EXCLUDED.confidence,
				heuristic = EXCLUDED.heuristic,
				candidate_rank = EXCLUDED.candidate_rank
			""",
            tenant_id,
            batch_id,
            candidate.legacy_code,
            candidate.candidate_code,
            candidate.confidence,
            candidate.heuristic,
            candidate.candidate_rank,
        )


async def _upsert_product_code_mappings(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id,
    mappings: tuple[ProductMappingRecord, ...],
    existing_mappings: dict[str, dict[str, object]],
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    for mapping in mappings:
        existing = existing_mappings.get(mapping.legacy_code)
        approval_source = existing.get("approval_source") if existing else None
        approved_by = existing.get("approved_by") if existing else None
        approved_at = existing.get("approved_at") if existing else None
        first_seen_batch_id = (
            str(existing.get("first_seen_batch_id") or batch_id) if existing else batch_id
        )

        if approval_source == "review-import":
            target_code = str(existing.get("target_code") or mapping.target_code)
            resolution_type = str(existing.get("resolution_type") or mapping.resolution_type)
            confidence = Decimal(str(existing.get("confidence") or mapping.confidence))
            review_notes = str(existing.get("review_notes") or mapping.notes or "") or None
        else:
            target_code = mapping.target_code
            resolution_type = mapping.resolution_type
            confidence = mapping.confidence
            review_notes = mapping.notes
            if resolution_type in AUTO_APPROVED_RESOLUTION_TYPES:
                approval_source = (
                    "seed-exact-match"
                    if resolution_type == "exact_match"
                    else "seed-normalized-exact-match"
                )
                approved_at = approved_at or datetime.now(UTC)

        await connection.execute(
            f"""
			INSERT INTO {quoted_schema}.product_code_mapping (
				tenant_id,
				legacy_code,
				target_code,
				resolution_type,
				confidence,
				affected_row_count,
				source_field,
				first_seen_batch_id,
				last_seen_batch_id,
				review_notes,
				approval_source,
				approved_by,
				approved_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
			ON CONFLICT (tenant_id, legacy_code) DO UPDATE SET
				target_code = EXCLUDED.target_code,
				resolution_type = EXCLUDED.resolution_type,
				confidence = EXCLUDED.confidence,
				affected_row_count = EXCLUDED.affected_row_count,
				source_field = EXCLUDED.source_field,
				last_seen_batch_id = EXCLUDED.last_seen_batch_id,
				review_notes = EXCLUDED.review_notes,
				approval_source = EXCLUDED.approval_source,
				approved_by = EXCLUDED.approved_by,
				approved_at = EXCLUDED.approved_at,
				updated_at = NOW()
			""",
            tenant_id,
            mapping.legacy_code,
            target_code,
            resolution_type,
            confidence,
            mapping.affected_row_count,
            "tbsslipdtx.col_7",
            first_seen_batch_id,
            batch_id,
            review_notes,
            approval_source,
            approved_by,
            approved_at,
        )


def _effective_unresolved_mapping_counts(
    seed_result: ProductMappingSeedResult,
    existing_mappings: dict[str, dict[str, object]],
) -> tuple[int, int, int]:
    unknown_count = 0
    orphan_code_count = 0
    orphan_row_count = 0
    for mapping in seed_result.mappings:
        existing = existing_mappings.get(mapping.legacy_code)
        resolution_type = mapping.resolution_type
        if existing and existing.get("approval_source") == "review-import":
            resolution_type = str(existing.get("resolution_type") or resolution_type)

        if resolution_type == "unknown":
            unknown_count += 1
            orphan_code_count += 1
            orphan_row_count += mapping.affected_row_count

    return unknown_count, orphan_code_count, orphan_row_count


async def run_product_mapping_seed(
    *,
    batch_id: str,
    tenant_id=DEFAULT_TENANT_ID,
    schema_name: str = "raw_legacy",
) -> ProductMappingBatchResult:
    connection = await _open_raw_connection()
    try:
        async with connection.transaction():
            known_codes = await _fetch_normalized_product_codes(
                connection,
                schema_name,
                batch_id,
                tenant_id,
            )
            if not known_codes:
                raise ValueError(f"No normalized product rows found for batch {batch_id}")

            await _ensure_unknown_normalized_product(
                connection,
                schema_name,
                batch_id,
                tenant_id,
            )
            known_codes.add(UNKNOWN_PRODUCT_CODE)

            sales_rows = await _fetch_sales_detail_product_rows(
                connection,
                schema_name,
                batch_id,
            )
            if not sales_rows:
                raise ValueError(f"No staged tbsslipdtx rows found for batch {batch_id}")

            seed_result = seed_product_code_mappings(
                tuple(_coerce_mapping(row) for row in sales_rows),
                known_codes,
            )
            existing_mappings = await _fetch_existing_product_mappings(
                connection,
                schema_name,
                tenant_id,
            )
            await _replace_mapping_candidates(
                connection,
                schema_name,
                batch_id,
                tenant_id,
                seed_result.candidates,
            )
            await _upsert_product_code_mappings(
                connection,
                schema_name,
                batch_id,
                tenant_id,
                seed_result.mappings,
                existing_mappings,
            )
    finally:
        await connection.close()

    unknown_count, orphan_code_count, orphan_row_count = (
        _effective_unresolved_mapping_counts(seed_result, existing_mappings)
    )

    return ProductMappingBatchResult(
        batch_id=batch_id,
        schema_name=schema_name,
        mapping_count=len(seed_result.mappings),
        candidate_count=len(seed_result.candidates),
        exact_match_count=seed_result.exact_match_count,
        unknown_count=unknown_count,
        orphan_code_count=orphan_code_count,
        orphan_row_count=orphan_row_count,
    )


def _build_review_rows(
    batch_id: str,
    mappings: tuple[dict[str, object], ...],
    candidates: tuple[dict[str, object], ...],
) -> list[dict[str, str]]:
    candidates_by_code: dict[str, list[dict[str, object]]] = {}
    for candidate in candidates:
        candidates_by_code.setdefault(str(candidate["legacy_code"]), []).append(candidate)

    review_rows: list[dict[str, str]] = []
    for mapping in mappings:
        legacy_code = str(mapping["legacy_code"])
        mapped_candidates = sorted(
            candidates_by_code.get(legacy_code, []),
            key=lambda item: int(item["candidate_rank"]),
        )
        candidate_rows = mapped_candidates or [None]
        for candidate in candidate_rows:
            review_rows.append(
                {
                    "batch_id": batch_id,
                    "legacy_code": legacy_code,
                    "affected_row_count": str(mapping["affected_row_count"]),
                    "current_target_code": str(mapping["target_code"]),
                    "current_resolution_type": str(mapping["resolution_type"]),
                    "current_confidence": str(mapping["confidence"]),
                    "candidate_rank": str(candidate["candidate_rank"]) if candidate else "",
                    "candidate_code": str(candidate["candidate_code"]) if candidate else "",
                    "candidate_confidence": str(candidate["confidence"]) if candidate else "",
                    "candidate_heuristic": str(candidate["heuristic"]) if candidate else "",
                    "review_status": "",
                    "approved_target_code": "",
                    "review_notes": str(mapping.get("review_notes") or ""),
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
        if review_status not in {"approved", "keep_unknown"}:
            raise ValueError(f"Unsupported review_status: {review_status}")

        legacy_code = str(row.get("legacy_code") or "").strip()
        if not legacy_code:
            raise ValueError("Review row missing legacy_code")
        if legacy_code in decisions:
            raise ValueError(f"Multiple review decisions provided for legacy_code: {legacy_code}")

        decisions[legacy_code] = {
            "review_status": review_status,
            "approved_target_code": str(
                row.get("approved_target_code") or row.get("candidate_code") or ""
            ).strip(),
            "review_notes": str(row.get("review_notes") or "").strip(),
            "candidate_confidence": str(row.get("candidate_confidence") or "0").strip() or "0",
            "affected_row_count": str(row.get("affected_row_count") or "0").strip() or "0",
        }
    return decisions


async def export_product_mapping_review(
    *,
    batch_id: str,
    output_path: Path,
    tenant_id=DEFAULT_TENANT_ID,
    schema_name: str = "raw_legacy",
) -> ProductMappingReviewExportResult:
    quoted_schema = _quoted_identifier(schema_name)
    connection = await _open_raw_connection()
    try:
        mapping_rows = await connection.fetch(
            f"""
			SELECT
				legacy_code,
				target_code,
				resolution_type,
				confidence,
				affected_row_count,
				review_notes
			FROM {quoted_schema}.product_code_mapping
            WHERE tenant_id = $1 AND last_seen_batch_id = $2
              AND resolution_type NOT IN ('exact_match', 'normalized_exact_match')
			ORDER BY legacy_code
			""",
            tenant_id,
            batch_id,
        )
        candidate_rows = await connection.fetch(
            f"""
			SELECT legacy_code, candidate_code, confidence, heuristic, candidate_rank
			FROM {quoted_schema}.product_code_mapping_candidates
			WHERE tenant_id = $1 AND batch_id = $2
			ORDER BY legacy_code, candidate_rank
			""",
            tenant_id,
            batch_id,
        )
    finally:
        await connection.close()

    rows = _build_review_rows(
        batch_id,
        tuple(_coerce_mapping(row) for row in mapping_rows),
        tuple(_coerce_mapping(row) for row in candidate_rows),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "batch_id",
                "legacy_code",
                "affected_row_count",
                "current_target_code",
                "current_resolution_type",
                "current_confidence",
                "candidate_rank",
                "candidate_code",
                "candidate_confidence",
                "candidate_heuristic",
                "review_status",
                "approved_target_code",
                "review_notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    return ProductMappingReviewExportResult(
        batch_id=batch_id,
        schema_name=schema_name,
        output_path=output_path,
        exported_row_count=len(rows),
    )


async def import_product_mapping_review(
    *,
    batch_id: str,
    input_path: Path,
    approved_by: str,
    tenant_id=DEFAULT_TENANT_ID,
    schema_name: str = "raw_legacy",
) -> ProductMappingReviewImportResult:
    quoted_schema = _quoted_identifier(schema_name)
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    decisions = _collect_review_decisions(rows, batch_id)

    connection = await _open_raw_connection()
    try:
        async with connection.transaction():
            await _ensure_unknown_normalized_product(
                connection,
                schema_name,
                batch_id,
                tenant_id,
            )
            known_codes = await _fetch_normalized_product_codes(
                connection,
                schema_name,
                batch_id,
                tenant_id,
            )
            approved_at = datetime.now(UTC)
            for legacy_code, decision in decisions.items():
                review_status = decision["review_status"]
                if review_status == "approved":
                    target_code = decision["approved_target_code"]
                    if not target_code:
                        raise ValueError(
                            f"Approved review row for {legacy_code} is missing approved_target_code"
                        )
                    if target_code not in known_codes:
                        if target_code != legacy_code:
                            raise ValueError(
                                "Approved target_code is not available in normalized "
                                f"products: {target_code}"
                            )

                        product_context = await _fetch_sales_detail_product_context(
                            connection,
                            schema_name,
                            batch_id,
                            legacy_code,
                        )
                        await _ensure_reviewed_synthetic_normalized_product(
                            connection,
                            schema_name,
                            batch_id,
                            tenant_id,
                            legacy_code=target_code,
                            name=str(product_context["name"]),
                            unit=str(product_context["unit"]),
                            source_row_number=int(product_context["source_row_number"]),
                        )
                        known_codes.add(target_code)
                    resolution_type = "analyst_review"
                    confidence = Decimal(decision["candidate_confidence"])
                else:
                    target_code = UNKNOWN_PRODUCT_CODE
                    resolution_type = "unknown"
                    confidence = Decimal("0.00")

                await connection.execute(
                    f"""
					INSERT INTO {quoted_schema}.product_code_mapping (
						tenant_id,
						legacy_code,
						target_code,
						resolution_type,
						confidence,
						affected_row_count,
						source_field,
						first_seen_batch_id,
						last_seen_batch_id,
						review_notes,
						approval_source,
						approved_by,
						approved_at
					)
					VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
					ON CONFLICT (tenant_id, legacy_code) DO UPDATE SET
						target_code = EXCLUDED.target_code,
						resolution_type = EXCLUDED.resolution_type,
						confidence = EXCLUDED.confidence,
						affected_row_count = EXCLUDED.affected_row_count,
						last_seen_batch_id = EXCLUDED.last_seen_batch_id,
						review_notes = EXCLUDED.review_notes,
						approval_source = EXCLUDED.approval_source,
						approved_by = EXCLUDED.approved_by,
						approved_at = EXCLUDED.approved_at,
						updated_at = NOW()
					""",
                    tenant_id,
                    legacy_code,
                    target_code,
                    resolution_type,
                    confidence,
                    int(decision["affected_row_count"]),
                    "tbsslipdtx.col_7",
                    batch_id,
                    batch_id,
                    decision["review_notes"] or None,
                    "review-import",
                    approved_by,
                    approved_at,
                )
    finally:
        await connection.close()

    return ProductMappingReviewImportResult(
        batch_id=batch_id,
        schema_name=schema_name,
        input_path=input_path,
        applied_decision_count=len(decisions),
    )
