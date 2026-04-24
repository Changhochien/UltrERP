"""Canonical historical import helpers for legacy ERP batches."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
import zlib
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, AsyncIterable, AsyncIterator, Mapping, Sequence, cast

from common.config import settings
from common.models.stock_adjustment import ReasonCode
from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import import source_resolution
from domains.legacy_import.mapping import UNKNOWN_PRODUCT_CODE
from domains.legacy_import.normalization import deterministic_legacy_uuid, normalize_legacy_date
from domains.legacy_import.shared import (
    DOMAIN_PARTIES,
    DOMAIN_PRODUCTS,
    DOMAIN_PURCHASE_INVOICES,
    DOMAIN_SALES,
    DOMAIN_WAREHOUSES,
    execute_many,
)
from domains.legacy_import.shared import (
    resolve_row_identity as _resolve_row_identity,
)
from domains.legacy_import.staging import _open_raw_connection, _quoted_identifier

_DIGITS_ONLY_RE = re.compile(r"\D+")
_LOGGER = logging.getLogger(__name__)

# Legacy source table code for receiving audit slip detail (tbsslipdtj = TBS-SLIP-DTJ)
LEGACY_RECEIVING_SOURCE = "tbsslipdtj"

# =============================================================================
# Domain name constants (documented in shared.py)
# =============================================================================
# These constants must match IncrementalDomainContract.name values in
# incremental_state.py. They are imported from shared.py for consistency:
#   DOMAIN_CUSTOMERS = "customers"
#   DOMAIN_PRODUCTS = "products"
#   DOMAIN_SALES = "sales"
#   DOMAIN_PURCHASE_INVOICES = "purchase-invoices"
#   (see domains/legacy_import/shared.py for the full set)
#
# Note: The canonical import uses canonical_table names ("customers", "suppliers",
# "products", etc.) for lineage and "sales_history" / "purchase_history" for
# step selection. The incremental domains use different names ("sales",
# "purchase-invoices"). The entity_scope manifest uses the incremental domain
# names ("sales", "purchase-invoices", "parties", "products").
# =============================================================================

# Module-level fallback counters — used as a mutable accumulator passed through
# the date-resolution call chain. Reset via .clear() at the start of each
# run_canonical_import call to avoid cross-batch leakage.
_receiving_date_fallback_counts: dict[str, int] = {}


@dataclass(slots=True, frozen=True)
class CanonicalImportResult:
    batch_id: str
    schema_name: str
    attempt_number: int
    customer_count: int
    product_count: int
    warehouse_count: int
    inventory_count: int
    order_count: int
    order_line_count: int
    invoice_count: int
    invoice_line_count: int
    holding_count: int
    lineage_count: int
    receiving_date_fallback_count: int = 0
    supplier_count: int = 0
    supplier_invoice_count: int = 0
    supplier_invoice_line_count: int = 0
    # Story 15.26: Scoped incremental metadata
    selected_domains: tuple[str, ...] = ()
    scoped_document_count: int = 0
    skipped_domains: tuple[str, ...] = ()
    review_required_issues: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class PendingLineageResolution:
    canonical_table: str
    canonical_id: uuid.UUID
    source_table: str
    source_identifier: str
    source_row_number: int
    domain_name: str | None = None
    resolution_notes: str | None = None


def _coerce_row(row: Mapping[str, object] | object) -> dict[str, object]:
    if isinstance(row, Mapping):
        return {str(key): value for key, value in row.items()}
    if hasattr(row, "items"):
        mapping_row = cast(Mapping[str, object], row)
        return {str(key): value for key, value in mapping_row.items()}
    raise TypeError(f"Unsupported row payload: {type(row)!r}")


def _as_text(value: object | None) -> str:
    return str(value or "").strip()


def _as_int(value: object | None, default: int = 0) -> int:
    text = _as_text(value)
    if not text:
        return default
    return int(text)


def _as_decimal(value: object | None, default: str | None = "0") -> Decimal | None:
    text = _as_text(value)
    if not text:
        return Decimal(default) if default is not None else None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal value: {text}") from exc


def _as_integral_quantity(value: object | None, *, field_name: str) -> int:
    quantity = _as_decimal(value, "0")
    if quantity is None:
        return 0
    if quantity != quantity.to_integral_value():
        raise ValueError(f"{field_name} must be integral, got {quantity}")
    return int(quantity)


def _coerce_quantity_for_integer_schema(
    value: object | None,
    *,
    field_name: str,
) -> tuple[int, str | None]:
    quantity = _as_decimal(value, "0")
    if quantity is None:
        return 0, None
    if quantity == quantity.to_integral_value():
        return int(quantity), None

    coerced = int(quantity)
    return coerced, f"{field_name} coerced from {quantity.normalize()} to {coerced}"


def _as_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _as_legacy_date(value: object | None) -> date | None:
    text = _as_text(value)
    if not text:
        return None
    return normalize_legacy_date(text)


def _try_as_legacy_date(value: object | None) -> date | None:
    text = _as_text(value)
    if text in {"", "0", "1900-01-01"}:
        return None

    looks_supported = (
        (len(text) == 10 and text.isdigit())
        or (len(text) == 8 and text.isdigit())
        or (len(text) == 10 and text[4] == "-" and text[7] == "-")
    )
    if not looks_supported:
        return None

    try:
        return normalize_legacy_date(text)
    except ValueError:
        return None


def _as_timestamp(day: date | None) -> datetime:
    resolved_day = day or date.today()
    return datetime.combine(resolved_day, time.min, tzinfo=UTC)


def _normalized_business_number(tax_id: object | None, legacy_code: object | None) -> str:
    tax_digits = _DIGITS_ONLY_RE.sub("", _as_text(tax_id))
    if len(tax_digits) == 8:
        return tax_digits

    legacy_digits = _DIGITS_ONLY_RE.sub("", _as_text(legacy_code))
    if legacy_digits:
        return legacy_digits[-8:].zfill(8)

    legacy_text = _as_text(legacy_code) or "legacy-party"
    checksum = zlib.crc32(legacy_text.encode("utf-8")) % 100_000_000
    return f"{checksum:08d}"


def _currency_code(value: object | None) -> str:
    raw = _as_text(value).upper()
    if raw in {"", "0001", "NTD", "TWD"}:
        return "TWD"
    return raw[:3]


def _compact_snapshot(snapshot: dict[str, object | None]) -> dict[str, object]:
    return {key: value for key, value in snapshot.items() if value not in (None, "")}


def _build_sales_header_snapshot(header: dict[str, object]) -> dict[str, object]:
    return _compact_snapshot(
        {
            "source_table": "tbsslipx",
            "legacy_doc_number": _as_text(header.get("doc_number")),
            "invoice_date_raw": _as_text(header.get("invoice_date")),
            "customer_code": _as_text(header.get("customer_code")),
            "customer_name": _as_text(header.get("customer_name")),
            "address": _as_text(header.get("address")),
            "currency_code": _as_text(header.get("currency_code")),
            "exchange_rate": _as_text(header.get("exchange_rate")),
            "tax_type": _as_text(header.get("tax_type")),
            "tax_rate": _as_text(header.get("tax_rate")),
            "period_code": _as_text(header.get("period_code")),
            "source_status": _as_text(header.get("source_status")),
            "remark": _as_text(header.get("remark")),
            "created_by": _as_text(header.get("created_by")),
        }
    )


def _map_legacy_status_to_canonical(source_status: str) -> str:
    """Map legacy source_status (col_80) to canonical invoice status.

    Common legacy status values and their mappings:
    - '1', 'N', 'ACTIVE', 'ISSUED', 'OPEN': 'issued' (new invoice, awaiting payment)
    - 'A', 'PAID', 'CLEARED', 'CLOSED', 'DONE': 'paid' (fully paid / cleared)
    - '2', '3', 'VOID', 'VOIDED', 'CANCELLED', 'CANCEL': 'voided' (voided/cancelled)
    - '' (empty): default to 'issued'

    The legacy system stores payment state in col_80 of tbsslipx.
    """
    raw = source_status.strip().upper()
    if raw in {"", "1", "N", "ACTIVE", "ISSUED", "OPEN"}:
        return "issued"
    if raw in {"A", "PAID", "CLEARED", "CLOSED", "DONE", "2"}:
        return "paid"
    if raw in {"3", "VOID", "VOIDED", "CANCELLED", "CANCEL"}:
        return "voided"
    # Unknown status — treat as issued (open/pending) for safety
    return "issued"


def _map_legacy_order_status(source_status: str) -> str:
    """Map imported historical sales documents to canonical order status.

    The sales-history import only creates orders for documents that already became
    invoices in the legacy system, so non-void documents should land as fulfilled
    rather than remaining on the active-order dashboard.
    """
    return (
        "cancelled"
        if _map_legacy_status_to_canonical(source_status) == "voided"
        else "fulfilled"
    )


def _map_purchase_invoice_status(must_pay_amount: object | None) -> str:
    """Map purchase invoice status from the legacy remaining-payable amount."""
    return "open" if _as_money(_as_decimal(must_pay_amount, "0.00")) > 0 else "paid"


def _resolve_purchase_invoice_total(
    subtotal_amount: object | None,
    tax_amount: object | None,
    must_pay_amount: object | None,
    line_total_amount: object | None = None,
) -> Decimal:
    gross_total = _as_money(_as_decimal(subtotal_amount, "0.00") + _as_decimal(tax_amount, "0.00"))
    if gross_total != 0:
        return gross_total
    line_total = _as_money(_as_decimal(line_total_amount, "0.00"))
    if line_total != 0:
        return line_total
    return _as_money(_as_decimal(must_pay_amount, "0.00"))


def _build_purchase_header_snapshot(header: dict[str, object]) -> dict[str, object]:
    raw_invoice_number = _as_text(header.get("raw_invoice_number"))
    raw_invoice_date = _as_text(header.get("raw_invoice_date"))
    return _compact_snapshot(
        {
            "source_table": "tbsslipj",
            "legacy_doc_number": _as_text(header.get("doc_number")),
            "supplier_code": _as_text(header.get("supplier_code")),
            "supplier_name": _as_text(header.get("supplier_name")),
            "address": _as_text(header.get("address")),
            "currency_code": _as_text(header.get("currency_code")),
            "period_code": _as_text(header.get("period_code")),
            "tax_rate": _as_text(header.get("tax_rate")),
            "must_pay_amount": _as_text(header.get("must_pay_amount")),
            "raw_invoice_number": raw_invoice_number,
            "resolved_invoice_number": _as_text(header.get("invoice_number")),
            "invoice_number_source": (
                "legacy_invoice_number" if raw_invoice_number else "doc_number"
            ),
            "raw_invoice_date": raw_invoice_date,
            "resolved_invoice_date": _as_text(header.get("invoice_date")),
            "invoice_date_source": "legacy_invoice_date" if raw_invoice_date else "slip_date",
            "slip_date": _as_text(header.get("slip_date")),
            "notes": _as_text(header.get("notes")),
        }
    )


def _build_party_master_snapshot(row: dict[str, object]) -> dict[str, object]:
    return _compact_snapshot(
        {
            "legacy_code": _as_text(row.get("legacy_code")),
            "role": _as_text(row.get("role")),
            "company_name": _as_text(row.get("company_name")),
            "short_name": _as_text(row.get("short_name")),
            "tax_id": _as_text(row.get("tax_id")),
            "full_address": _as_text(row.get("full_address")),
            "address": _as_text(row.get("address")),
            "phone": _as_text(row.get("phone")),
            "email": _as_text(row.get("email")),
            "contact_person": _as_text(row.get("contact_person")),
            "source_table": _as_text(row.get("source_table")),
            "source_row_number": _as_int(row.get("source_row_number")),
        }
    )


def _build_product_master_snapshot(row: dict[str, object]) -> dict[str, object]:
    return _compact_snapshot(
        {
            "legacy_code": _as_text(row.get("legacy_code")),
            "name": _as_text(row.get("name")),
            "category": _as_text(row.get("category")),
            "legacy_category": _as_text(row.get("legacy_category")),
            "stock_kind": _as_text(row.get("stock_kind")),
            "category_source": _as_text(row.get("category_source")),
            "category_rule_id": _as_text(row.get("category_rule_id")),
            "category_confidence": _as_text(row.get("category_confidence")),
            "description": _as_text(row.get("description")),
            "unit": _as_text(row.get("unit")),
            "status": _as_text(row.get("status")),
            "source_table": _as_text(row.get("source_table")),
            "source_row_number": _as_int(row.get("source_row_number")),
        }
    )


def _tax_policy_code(tax_amount: Decimal) -> tuple[str, int, Decimal]:
    if tax_amount > Decimal("0"):
        return ("standard", 1, Decimal("0.05"))
    return ("exempt", 3, Decimal("0.00"))


def _tenant_scoped_uuid(tenant_id: uuid.UUID, kind: str, *parts: str) -> uuid.UUID:
    return deterministic_legacy_uuid(kind, str(tenant_id), *parts)


async def _load_category_cache(
    connection,
    tenant_id: uuid.UUID,
) -> dict[str, tuple[uuid.UUID, str]]:
    rows = await connection.fetch(
        """
		SELECT id, name
		FROM category
		WHERE tenant_id = $1
		""",
        tenant_id,
    )
    cache: dict[str, tuple[uuid.UUID, str]] = {}
    for row in rows:
        category_id = cast(uuid.UUID, row["id"])
        category_name = _as_text(row["name"])
        if not category_name:
            continue
        cache[category_name.casefold()] = (category_id, category_name)
    return cache


async def _ensure_product_category(
    connection,
    tenant_id: uuid.UUID,
    category_name: str | None,
    *,
    category_cache: dict[str, tuple[uuid.UUID, str]],
) -> tuple[uuid.UUID | None, str | None]:
    normalized_name = _as_text(category_name)
    if not normalized_name:
        return None, None

    cache_key = normalized_name.casefold()
    cached = category_cache.get(cache_key)
    if cached is not None:
        return cached

    category_row = await connection.fetchrow(
        """
		INSERT INTO category (
			id,
			tenant_id,
			name,
			is_active,
			created_at,
			updated_at
		)
		VALUES ($1::uuid, $2::uuid, $3::varchar, TRUE, NOW(), NOW())
		ON CONFLICT (tenant_id, name) DO UPDATE SET
			is_active = TRUE,
			updated_at = NOW()
		RETURNING id, name
		""",
        _tenant_scoped_uuid(tenant_id, "category", cache_key),
        tenant_id,
        normalized_name,
    )
    resolved_category_id = cast(uuid.UUID, category_row["id"])
    resolved_category_name = _as_text(category_row["name"])

    await connection.execute(
        """
		INSERT INTO category_translation (
			id,
			category_id,
			locale,
			name
		)
		VALUES ($1::uuid, $2::uuid, 'en', $3::varchar)
		ON CONFLICT (category_id, locale) DO UPDATE SET
			name = EXCLUDED.name
		""",
        _tenant_scoped_uuid(tenant_id, "category-translation", str(resolved_category_id), "en"),
        resolved_category_id,
        resolved_category_name,
    )

    category_cache[cache_key] = (resolved_category_id, resolved_category_name)
    return resolved_category_id, resolved_category_name


def _step_row_count(step_name: str, counts: Mapping[str, int]) -> int:
    if step_name == "sales_history":
        return counts.get("order_line_count", 0) + counts.get("invoice_line_count", 0)
    if step_name == "purchase_history":
        return counts.get("supplier_invoice_count", 0) + counts.get(
            "supplier_invoice_line_count", 0
        )
    if step_name == "receiving_audit":
        return counts.get("receiving_audit_count", 0)
    if step_name == "unsupported_history":
        return counts.get("holding_count", 0)

    step_to_count_key = {
        "customers": "customer_count",
        "suppliers": "supplier_count",
        "products": "product_count",
        "warehouses": "warehouse_count",
        "inventory": "inventory_count",
    }
    return counts.get(step_to_count_key.get(step_name, ""), 0)


async def _ensure_canonical_support_tables(connection, schema_name: str) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.canonical_import_runs (
			id UUID PRIMARY KEY,
			tenant_id UUID NOT NULL,
			batch_id TEXT NOT NULL,
			source_schema TEXT NOT NULL,
			attempt_number INTEGER NOT NULL,
			status TEXT NOT NULL,
			summary JSONB,
			error_message TEXT,
			started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			completed_at TIMESTAMPTZ,
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			UNIQUE (tenant_id, batch_id, attempt_number)
		)
		"""
    )
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.canonical_import_step_runs (
			run_id UUID NOT NULL REFERENCES {quoted_schema}.canonical_import_runs(id),
			step_name TEXT NOT NULL,
			row_count INTEGER NOT NULL DEFAULT 0,
			status TEXT NOT NULL,
			error_message TEXT,
			started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			completed_at TIMESTAMPTZ,
			PRIMARY KEY (run_id, step_name)
		)
		"""
    )
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.canonical_record_lineage (
			tenant_id UUID NOT NULL,
			batch_id TEXT NOT NULL,
			canonical_table TEXT NOT NULL,
			canonical_id UUID NOT NULL,
			source_table TEXT NOT NULL,
			source_identifier TEXT NOT NULL,
			source_row_number INTEGER NOT NULL,
			import_run_id UUID NOT NULL,
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			PRIMARY KEY (
				batch_id,
				tenant_id,
				canonical_table,
				source_table,
                source_identifier,
                source_row_number
			)
		)
		"""
    )
    # Unique index for source-identifier-only matching.
    # This allows holding-path lineage entries (__holding__) and drain-path entries
    # (supplier_payments, etc.) to share the same source identity. The ON CONFLICT
    # clause in the holding/drain queries uses this index to UPDATE existing entries
    # instead of creating duplicates when the same source row is processed through
    # both holding and drain paths.
    await connection.execute(
        f"""
		CREATE UNIQUE INDEX IF NOT EXISTS {quoted_schema}.
			canonical_record_lineage_source_identity
			ON {quoted_schema}.canonical_record_lineage (
				batch_id,
				tenant_id,
				source_table,
				source_identifier,
				source_row_number
			);
		"""
    )
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.unsupported_history_holding (
			id UUID PRIMARY KEY,
			tenant_id UUID NOT NULL,
			batch_id TEXT NOT NULL,
			domain_name TEXT NOT NULL,
			source_table TEXT NOT NULL,
			source_identifier TEXT NOT NULL,
			source_row_number INTEGER NOT NULL,
			payload JSONB NOT NULL,
			notes TEXT,
			import_run_id UUID NOT NULL,
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			UNIQUE (tenant_id, batch_id, source_table, source_identifier, source_row_number)
        )
        """
    )
    await source_resolution.ensure_source_resolution_tables(connection, schema_name)

    # Held rows stay in manual quarantine until a later import resolves them.
    # Current holding/resolved state lives in source_row_resolution, and the
    # payload/notes remain in unsupported_history_holding for operator review.


async def _next_attempt_number(
    connection, schema_name: str, batch_id: str, tenant_id: uuid.UUID
) -> int:
    quoted_schema = _quoted_identifier(schema_name)
    value = await connection.fetchval(
        f"""
		SELECT COALESCE(MAX(attempt_number), 0)
		FROM {quoted_schema}.canonical_import_runs
		WHERE tenant_id = $1 AND batch_id = $2
		""",
        tenant_id,
        batch_id,
    )
    return int(value or 0) + 1


async def _upsert_run_row(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    attempt_number: int,
    status: str,
    summary: dict[str, int] | None,
    error_message: str | None,
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        f"""
		INSERT INTO {quoted_schema}.canonical_import_runs (
			id,
			tenant_id,
			batch_id,
			source_schema,
			attempt_number,
			status,
			summary,
			error_message,
			started_at,
			completed_at
		)
        VALUES (
            $1,
            $2,
            $3,
            $4,
            $5,
            $6,
            $7::jsonb,
            $8,
            NOW(),
            CASE
                WHEN $6 = 'completed' OR $6 = 'failed' THEN NOW()
                ELSE NULL
            END
        )
		ON CONFLICT (tenant_id, batch_id, attempt_number) DO UPDATE SET
			status = EXCLUDED.status,
			summary = EXCLUDED.summary,
			error_message = EXCLUDED.error_message,
			completed_at = EXCLUDED.completed_at
		""",
        run_id,
        tenant_id,
        batch_id,
        schema_name,
        attempt_number,
        status,
        json.dumps(summary or {}),
        error_message,
    )


async def _upsert_step_row(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    step_name: str,
    row_count: int,
    status: str,
    error_message: str | None = None,
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        f"""
		INSERT INTO {quoted_schema}.canonical_import_step_runs (
			run_id,
			step_name,
			row_count,
			status,
			error_message,
			started_at,
			completed_at
		)
        VALUES (
            $1,
            $2,
            $3,
            $4,
            $5,
            NOW(),
            CASE
                WHEN $4 = 'completed' OR $4 = 'failed' THEN NOW()
                ELSE NULL
            END
        )
		ON CONFLICT (run_id, step_name) DO UPDATE SET
			row_count = EXCLUDED.row_count,
			status = EXCLUDED.status,
			error_message = EXCLUDED.error_message,
			completed_at = EXCLUDED.completed_at
		""",
        run_id,
        step_name,
        row_count,
        status,
        error_message,
    )


def _lineage_record_query(schema_name: str) -> str:
    quoted_schema = _quoted_identifier(schema_name)
    return f"""
		INSERT INTO {quoted_schema}.canonical_record_lineage (
			tenant_id,
			batch_id,
			canonical_table,
			canonical_id,
			source_table,
			source_identifier,
			source_row_number,
			import_run_id
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (
            batch_id,
            tenant_id,
            canonical_table,
            source_table,
            source_identifier,
            source_row_number
        )
		DO UPDATE SET
			canonical_id = EXCLUDED.canonical_id,
			import_run_id = EXCLUDED.import_run_id
		"""


def _lineage_record_args(
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    row: PendingLineageResolution,
) -> tuple[object, ...]:
    return (
        tenant_id,
        batch_id,
        row.canonical_table,
        row.canonical_id,
        row.source_table,
        row.source_identifier,
        row.source_row_number,
        run_id,
    )


# Sentinel canonical_table value for holding-path rows.
# When the drain path later upserts a lineage record for the same source
# identifiers, the ON CONFLICT clause matches on source identifiers only
# (not canonical_table) so the holding entry is updated to the real table.
HOLDING_LINEAGE_TABLE = "__holding__"


def _lineage_record_query_for_holding(schema_name: str) -> str:
    """Lineage upsert query that matches on source identifiers only.

    The ON CONFLICT target is (batch_id, tenant_id, source_table,
    source_identifier, source_row_number) WITHOUT canonical_table, so that
    a drain-path upsert for the same source identifiers will UPDATE the
    existing holding entry rather than creating a duplicate.
    """
    quoted_schema = _quoted_identifier(schema_name)
    return f"""
		INSERT INTO {quoted_schema}.canonical_record_lineage (
			tenant_id,
			batch_id,
			canonical_table,
			canonical_id,
			source_table,
			source_identifier,
			source_row_number,
			import_run_id
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (
            batch_id,
            tenant_id,
            source_table,
            source_identifier,
            source_row_number
        )
		DO UPDATE SET
			canonical_table = EXCLUDED.canonical_table,
			canonical_id = EXCLUDED.canonical_id,
			import_run_id = EXCLUDED.import_run_id
		"""


async def _upsert_lineage_record_for_holding(
    connection,
    *,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    canonical_id: uuid.UUID,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
) -> None:
    """Insert or update a lineage record for a holding-path row.

    Uses source-identifier-only conflict matching so that drain-path upserts
    (which use the same source identifiers but different canonical_table)
    will UPDATE this entry rather than creating a duplicate.
    """
    await connection.execute(
        _lineage_record_query_for_holding(schema_name),
        tenant_id,
        batch_id,
        HOLDING_LINEAGE_TABLE,
        canonical_id,
        source_table,
        source_identifier,
        source_row_number,
        run_id,
    )


async def _flush_lineage_resolutions(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    rows: list[PendingLineageResolution],
) -> None:
    if not rows:
        return

    await execute_many(
        connection,
        _lineage_record_query(schema_name),
        [_lineage_record_args(run_id, tenant_id, batch_id, row) for row in rows],
    )
    await source_resolution.resolve_source_rows(
        connection,
        schema_name=schema_name,
        run_id=run_id,
        tenant_id=tenant_id,
        batch_id=batch_id,
        rows=[
            source_resolution.ResolvedSourceRow(
                domain_name=row.domain_name or row.canonical_table,
                source_table=row.source_table,
                source_identifier=row.source_identifier,
                source_row_number=row.source_row_number,
                canonical_table=row.canonical_table,
                canonical_id=row.canonical_id,
                notes=row.resolution_notes,
            )
            for row in rows
        ],
    )


async def _upsert_lineage_record(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    canonical_table: str,
    canonical_id: uuid.UUID,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
) -> None:
    """Upsert canonical lineage for one canonical destination mapping."""
    await connection.execute(
        _lineage_record_query(schema_name),
        tenant_id,
        batch_id,
        canonical_table,
        canonical_id,
        source_table,
        source_identifier,
        source_row_number,
        run_id,
    )


async def _upsert_lineage(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    canonical_table: str,
    canonical_id: uuid.UUID,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
    domain_name: str | None = None,
    resolution_notes: str | None = None,
) -> None:
    """Upsert canonical lineage and mark the source row as resolved."""
    await _upsert_lineage_record(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        canonical_table,
        canonical_id,
        source_table,
        source_identifier,
        source_row_number,
    )
    await source_resolution.resolve_source_row(
        connection,
        schema_name=schema_name,
        run_id=run_id,
        tenant_id=tenant_id,
        batch_id=batch_id,
        domain_name=domain_name or canonical_table,
        source_table=source_table,
        source_identifier=source_identifier,
        source_row_number=source_row_number,
        canonical_table=canonical_table,
        canonical_id=canonical_id,
        notes=resolution_notes,
    )


async def _table_exists(connection, schema_name: str, table_name: str) -> bool:
    quoted_schema = _quoted_identifier(schema_name)
    value = await connection.fetchval(f"SELECT to_regclass('{quoted_schema}.{table_name}')")
    return bool(value)


async def _iter_query_rows(
    connection,
    query: str,
    *args: object,
) -> AsyncIterator[dict[str, object]]:
    # Prefer server-side cursor when available — streams rows without loading
    # all into memory. Falls back to fetch() for non-transactional connections.
    cursor = getattr(connection, "cursor", None)
    if callable(cursor):
        async with connection.transaction():
            cursor_iter = cast(Any, cursor)(query, *args)
            async for row in cursor_iter:
                yield _coerce_row(row)
        return

    rows = await connection.fetch(query, *args)
    for row in rows:
        yield _coerce_row(row)


async def _iter_normalized_parties(
    connection, schema_name: str, batch_id: str, tenant_id: uuid.UUID
) -> AsyncIterator[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    async for row in _iter_query_rows(
        connection,
        f"""
		SELECT
			deterministic_id,
			legacy_code,
			role,
			company_name,
			short_name,
			tax_id,
			full_address,
			address,
			phone,
			email,
			contact_person,
            customer_type,
			source_table,
			source_row_number
		FROM {quoted_schema}.normalized_parties
		WHERE batch_id = $1 AND tenant_id = $2
		ORDER BY role, legacy_code
		""",
        batch_id,
        tenant_id,
    ):
        yield row


async def _iter_normalized_products(
    connection, schema_name: str, batch_id: str, tenant_id: uuid.UUID
) -> AsyncIterator[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    async for row in _iter_query_rows(
        connection,
        f"""
		SELECT
			deterministic_id,
			legacy_code,
			name,
			category,
			legacy_category,
			stock_kind,
			category_source,
            category_rule_id,
            category_confidence,
			unit,
			status,
			source_table,
			source_row_number
		FROM {quoted_schema}.normalized_products
		WHERE batch_id = $1 AND tenant_id = $2
		ORDER BY legacy_code
		""",
        batch_id,
        tenant_id,
    ):
        yield row


async def _iter_normalized_warehouses(
    connection, schema_name: str, batch_id: str, tenant_id: uuid.UUID
) -> AsyncIterator[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    async for row in _iter_query_rows(
        connection,
        f"""
		SELECT
			deterministic_id,
			code,
			name,
			location,
			address,
			source_table,
			source_row_number
		FROM {quoted_schema}.normalized_warehouses
		WHERE batch_id = $1 AND tenant_id = $2
		ORDER BY code
		""",
        batch_id,
        tenant_id,
    ):
        yield row


async def _iter_normalized_inventory(
    connection, schema_name: str, batch_id: str, tenant_id: uuid.UUID
) -> AsyncIterator[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    async for row in _iter_query_rows(
        connection,
        f"""
		SELECT
			product_deterministic_id,
			warehouse_deterministic_id,
			product_legacy_code,
			warehouse_code,
			quantity_on_hand,
			reorder_point,
			source_table,
			source_row_number
		FROM {quoted_schema}.normalized_inventory_prep
		WHERE batch_id = $1 AND tenant_id = $2
		ORDER BY product_legacy_code, warehouse_code
		""",
        batch_id,
        tenant_id,
    ):
        yield row


async def _iter_product_mappings(
    connection, schema_name: str, tenant_id: uuid.UUID,
) -> AsyncIterator[tuple[str, str]]:
    """Yield (legacy_code, target_code) pairs — streaming, memory-efficient."""
    quoted_schema = _quoted_identifier(schema_name)
    async for row in _iter_query_rows(
        connection,
        f"""
		SELECT legacy_code, target_code
		FROM {quoted_schema}.product_code_mapping
		WHERE tenant_id = $1
		ORDER BY legacy_code
		""",
        tenant_id,
    ):
        legacy = _as_text(row.get("legacy_code"))
        target = _as_text(row.get("target_code"))
        if legacy:
            yield legacy, target


async def _fetch_product_mappings(
    connection, schema_name: str, tenant_id: uuid.UUID
) -> dict[str, str]:
    """Build product code mapping dict by streaming rows (memory-efficient)."""
    result: dict[str, str] = {}
    async for legacy, target in _iter_product_mappings(connection, schema_name, tenant_id):
        result[legacy] = target
    return result


async def _fetch_sales_headers(
    connection, schema_name: str, batch_id: str
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT
			col_2 AS doc_number,
			col_3 AS invoice_date,
			col_7 AS customer_code,
			col_8 AS customer_name,
			col_9 AS address,
			col_10 AS currency_code,
			col_12 AS exchange_rate,
			col_17 AS subtotal,
			col_18 AS tax_type,
			col_19 AS tax_amount,
			col_24 AS total_amount,
			col_30 AS remark,
            col_31 AS period_code,
			col_32 AS created_by,
            col_80 AS source_status,
			col_85 AS tax_rate,
			_source_row_number AS source_row_number
		FROM {quoted_schema}.tbsslipx
		WHERE _batch_id = $1
		ORDER BY col_2
		""",
        batch_id,
    )
    return [_coerce_row(row) for row in rows]


async def _fetch_sales_lines(
    connection, schema_name: str, batch_id: str
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT
			dtx.col_2 AS doc_number,
			dtx.col_3 AS line_number,
			dtx.col_7 AS product_code,
			dtx.col_8 AS product_name,
			dtx.col_18 AS unit,
			dtx.col_19 AS list_unit_price,
			dtx.col_21 AS unit_price,
			dtx.col_22 AS line_tax_amount,
			dtx.col_23 AS qty,
			dtx.col_29 AS extended_amount,
			dtx.col_44 AS original_list_price,
			dtx.col_45 AS original_discount_ratio,
			dtx._source_row_number AS source_row_number,
			COALESCE(SUM(inv.quantity_on_hand), 0) AS available_stock_snapshot
		FROM {quoted_schema}.tbsslipdtx dtx
		LEFT JOIN {quoted_schema}.normalized_inventory_prep inv
			ON inv.product_legacy_code = dtx.col_7
			AND inv.batch_id = dtx._batch_id
		WHERE dtx._batch_id = $1
		GROUP BY dtx.col_2, dtx.col_3, dtx.col_7, dtx.col_8, dtx.col_18,
			dtx.col_19, dtx.col_21, dtx.col_22, dtx.col_23, dtx.col_29,
			dtx.col_44, dtx.col_45, dtx._source_row_number
		ORDER BY dtx.col_2, dtx.col_3
		""",
        batch_id,
    )
    return [_coerce_row(row) for row in rows]


async def _fetch_purchase_headers(
    connection, schema_name: str, batch_id: str
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT
			col_2 AS doc_number,
            col_3 AS slip_date,
            col_30 AS period_code,
            col_42 AS raw_invoice_number,
            col_62 AS raw_invoice_date,
            col_78 AS tax_rate,
            CASE
                WHEN COALESCE(col_42, '') <> '' THEN col_42
                ELSE col_2
            END AS invoice_number,
            CASE
                WHEN COALESCE(col_62, '') NOT IN ('', '1900-01-01') THEN col_62
                ELSE col_3
            END AS invoice_date,
			col_7 AS supplier_code,
			col_8 AS supplier_name,
			col_9 AS address,
            col_10 AS currency_code,
			col_17 AS subtotal,
			col_19 AS tax_amount,
            col_29 AS notes,
            col_48 AS must_pay_amount,
            CASE
                WHEN (COALESCE(col_17::numeric, 0) + COALESCE(col_19::numeric, 0)) <> 0
                    THEN (COALESCE(col_17::numeric, 0) + COALESCE(col_19::numeric, 0))
                ELSE col_49::numeric
            END AS total_amount,
			_source_row_number AS source_row_number
		FROM {quoted_schema}.tbsslipj
        WHERE _batch_id = $1 AND COALESCE(col_1, '') = '4'
		ORDER BY col_2
		""",
        batch_id,
    )
    return [_coerce_row(row) for row in rows]


async def _fetch_purchase_lines(
    connection, schema_name: str, batch_id: str
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT
			col_2 AS doc_number,
			col_3 AS line_number,
            col_4 AS receipt_date,
			col_6 AS product_code,
			col_7 AS product_name,
			col_16 AS warehouse_code,
			col_18 AS unit,
			col_19 AS foldprice,
			col_20 AS discount_multiplier,
			col_21 AS unit_price,
			col_22 AS qty,
			col_25 AS taxable,
			col_26 AS line_total,
			(col_21::numeric * col_22::numeric) AS extended_amount,
			_source_row_number AS source_row_number
		FROM {quoted_schema}.tbsslipdtj
		WHERE _batch_id = $1 AND COALESCE(col_1, '') = '4'
		ORDER BY col_2, col_3
		""",
        batch_id,
    )
    return [_coerce_row(row) for row in rows]


def _derive_legacy_receiving_batch_fallback_day(
    headers: list[dict[str, object]],
    lines: list[dict[str, object]],
) -> date | None:
    candidates = []
    for header in headers:
        day = _try_as_legacy_date(header.get("invoice_date"))
        if day is not None:
            candidates.append(day)
    for line in lines:
        day = _try_as_legacy_date(line.get("receipt_date"))
        if day is not None:
            candidates.append(day)
    return max(candidates) if candidates else None


def _resolve_legacy_receiving_created_at(
    line: dict[str, object],
    header: dict[str, object] | None,
    batch_fallback_day: date | None,
) -> datetime:
    source_identifier = (
        f"{_as_text(line.get('doc_number'))}:{_as_int(line.get('line_number'), 1)}"
    )

    line_day = _try_as_legacy_date(line.get("receipt_date"))
    if line_day is not None:
        return _as_timestamp(line_day)

    if header is not None:
        header_day = _try_as_legacy_date(header.get("invoice_date"))
        if header_day is not None:
            _LOGGER.warning(
                "Legacy receiving line %s has sentinel/missing receipt_date; "
                "falling back to header invoice_date",
                source_identifier,
            )
            _receiving_date_fallback_counts["receiving_date_fallback_receipt_to_invoice"] += 1
            return _as_timestamp(header_day)

    if batch_fallback_day is not None:
        _LOGGER.warning(
            "Legacy receiving line %s has no usable row/header date; "
            "falling back to batch-scoped legacy date %s",
            source_identifier,
            batch_fallback_day.isoformat(),
        )
        _receiving_date_fallback_counts["receiving_date_fallback_to_batch"] += 1
        return _as_timestamp(batch_fallback_day)

    _LOGGER.warning(
        "Legacy receiving line %s has sentinel/missing receipt_date and no "
        "header fallback; using import-day timestamp",
        source_identifier,
    )
    _receiving_date_fallback_counts["receiving_date_fallback_to_import_day"] += 1
    return _as_timestamp(None)


# =============================================================================
# AC5: Master lookup from prior successful batch lineage
# =============================================================================

async def _resolve_master_uuid_from_prior_batch(
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
    canonical_table: str,
    source_table: str,
    source_identifier: str,
    last_successful_batch_id: str | None,
) -> uuid.UUID | None:
    """Look up canonical UUID from a prior successful batch's lineage.

    AC5: When a master entity (party, product) is not found in the current
    normalized staging during a scoped rerun, this function looks up its
    canonical UUID from the last successful batch's lineage. This prevents
    creating duplicate master records when a scoped run only processes a
    subset of the data.

    Args:
        connection: Database connection
        schema_name: Legacy schema name
        tenant_id: Tenant UUID
        canonical_table: Canonical table name (e.g., "customers", "product")
        source_table: Source table name (e.g., "tbscust", "tbsstock")
        source_identifier: Source identifier (e.g., legacy_code)
        last_successful_batch_id: Batch ID of the last successful import, or None

    Returns:
        The canonical UUID from the prior batch's lineage, or None if not found.
    """
    if last_successful_batch_id is None:
        return None

    quoted_schema = _quoted_identifier(schema_name)
    row = await connection.fetchrow(
        f"""
        SELECT canonical_id
        FROM {quoted_schema}.canonical_record_lineage
        WHERE batch_id = $1
          AND tenant_id = $2
          AND canonical_table = $3
          AND source_table = $4
          AND source_identifier = $5
          AND canonical_table != '__holding__'
        LIMIT 1
        """,
        last_successful_batch_id,
        tenant_id,
        canonical_table,
        source_table,
        source_identifier,
    )
    if row is None:
        return None
    return cast(uuid.UUID, row["canonical_id"])


async def _build_prior_master_lookup(
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
    last_successful_batch_ids: Mapping[str, str] | None,
    canonical_table: str,
    source_table: str,
    legacy_codes: Sequence[str],
) -> dict[str, uuid.UUID]:
    """Build a lookup of legacy_code -> canonical_uuid from prior batch lineage.

    For each legacy code not found in current staging, attempt to resolve
    the canonical UUID from the last successful batch's lineage.

    Args:
        connection: Database connection
        schema_name: Legacy schema name
        tenant_id: Tenant UUID
        last_successful_batch_ids: Mapping of domain -> batch_id
        canonical_table: Canonical table name
        source_table: Source table name
        legacy_codes: Sequence of legacy codes to look up

    Returns:
        Dict mapping legacy_code -> canonical_uuid for codes found in prior lineage.
    """
    result: dict[str, uuid.UUID] = {}
    if not legacy_codes or last_successful_batch_ids is None:
        return result

    # Map canonical_table names to the domain names used in last_successful_batch_ids.
    # The last_successful_batch_ids mapping uses incremental domain names:
    # "customers", "suppliers", "products", "sales", "purchase-invoices".
    # The canonical_table names in lineage are: "customers", "supplier", "product".
    # For parties (customers + suppliers), we check "customers" domain.
    domain_map = {
        "customers": "customers",   # lineage: customers, domain: customers
        "supplier": "suppliers",   # lineage: supplier, domain: suppliers
        "product": "products",     # lineage: product, domain: products
    }
    domain_name = domain_map.get(canonical_table)
    if domain_name is None:
        return result

    last_batch_id = last_successful_batch_ids.get(domain_name)
    if last_batch_id is None:
        return result

    for legacy_code in legacy_codes:
        prior_uuid = await _resolve_master_uuid_from_prior_batch(
            connection,
            schema_name,
            tenant_id,
            canonical_table,
            source_table,
            legacy_code,
            last_batch_id,
        )
        if prior_uuid is not None:
            result[legacy_code] = prior_uuid

    return result


def _build_entity_scope_closure_keys(
    entity_scope: Mapping[str, object] | None,
) -> dict[str, frozenset[str]]:
    """Extract per-domain closure_key sets from the entity_scope manifest.

    The entity_scope is a dict of domain_name -> {closure_keys: [...], ...}.
    Returns a dict of domain_name -> frozenset of closure keys for efficient
    membership tests. If entity_scope is None, returns empty dict.
    """
    if entity_scope is None:
        return {}

    domain_value_fields: dict[str, tuple[str, ...]] = {
        DOMAIN_SALES: ("document_number",),
        DOMAIN_PURCHASE_INVOICES: ("document_number",),
        DOMAIN_PRODUCTS: ("product-code", "product_code"),
        DOMAIN_PARTIES: ("party-code", "party_code"),
        DOMAIN_WAREHOUSES: ("warehouse-code", "warehouse_code"),
    }

    result: dict[str, frozenset[str]] = {}
    for domain, spec in entity_scope.items():
        if not isinstance(spec, Mapping):
            continue
        keys = spec.get("closure_keys")
        if not isinstance(keys, (list, tuple, frozenset)):
            continue

        extracted: set[str] = set()
        for key_entry in keys:
            if isinstance(key_entry, Mapping):
                for field_name in domain_value_fields.get(domain, ()):
                    value = key_entry.get(field_name)
                    if value is None:
                        continue
                    text = str(value).strip()
                    if text:
                        extracted.add(text)
                        break
                continue

            text = str(key_entry).strip()
            if text:
                extracted.add(text)

        if extracted:
            result[domain] = frozenset(extracted)
    return result


def _domain_in_selected(
    domain: str,
    selected_domains: tuple[str, ...] | Sequence[str] | None,
) -> bool:
    """Check if a domain is in the selected set (or all if None)."""
    if not selected_domains:
        return True
    return domain in selected_domains


def _is_sales_domain_selected(selected_domains: tuple[str, ...] | None) -> bool:
    """Check if sales domain is selected (or all if None)."""
    return _domain_in_selected(DOMAIN_SALES, selected_domains)


def _is_purchase_domain_selected(selected_domains: tuple[str, ...] | None) -> bool:
    """Check if purchase-invoices domain is selected (or all if None)."""
    return _domain_in_selected(DOMAIN_PURCHASE_INVOICES, selected_domains)


def _filter_sales_headers_by_scope(
    headers: list[dict[str, object]],
    entity_scope_closure_keys: dict[str, frozenset[str]],
) -> list[dict[str, object]]:
    """Filter sales headers to only those in entity_scope.

    For sales documents, the closure_key is the doc_number. If entity_scope
    is empty (full batch), return all headers.
    """
    sales_keys = entity_scope_closure_keys.get(DOMAIN_SALES)
    if not sales_keys:
        return headers

    return [
        h for h in headers
        if _as_text(h.get("doc_number")) in sales_keys
    ]


def _filter_purchase_headers_by_scope(
    headers: list[dict[str, object]],
    entity_scope_closure_keys: dict[str, frozenset[str]],
) -> list[dict[str, object]]:
    """Filter purchase headers to only those in entity_scope.

    For purchase invoices, the closure_key is the doc_number. If entity_scope
    is empty (full batch), return all headers.
    """
    purchase_keys = entity_scope_closure_keys.get(DOMAIN_PURCHASE_INVOICES)
    if not purchase_keys:
        return headers

    return [
        h for h in headers
        if _as_text(h.get("doc_number")) in purchase_keys
    ]


def _filter_sales_lines_by_scope(
    lines: list[dict[str, object]],
    scoped_header_doc_numbers: frozenset[str],
) -> list[dict[str, object]]:
    """Filter sales lines to only those belonging to scoped headers.

    Full document families are rebuilt: if a header is in scope, ALL its lines
    are included (deterministic lineage preservation).
    """
    if not scoped_header_doc_numbers:
        return lines
    return [
        line for line in lines
        if _as_text(line.get("doc_number")) in scoped_header_doc_numbers
    ]


def _filter_purchase_lines_by_scope(
    lines: list[dict[str, object]],
    scoped_header_doc_numbers: frozenset[str],
) -> list[dict[str, object]]:
    """Filter purchase lines to only those belonging to scoped headers.

    Full document families are rebuilt: if a header is in scope, ALL its lines
    are included (deterministic lineage preservation).
    """
    if not scoped_header_doc_numbers:
        return lines
    return [
        line for line in lines
        if _as_text(line.get("doc_number")) in scoped_header_doc_numbers
    ]


async def _import_customers(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    party_rows: AsyncIterable[dict[str, object]],
) -> tuple[int, int, dict[str, uuid.UUID], dict[str, str]]:
    count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    customer_by_code: dict[str, uuid.UUID] = {}
    business_number_by_code: dict[str, str] = {}
    async for row in party_rows:
        if _as_text(row.get("role")) != "customer":
            continue
        legacy_code = _as_text(row.get("legacy_code"))
        customer_id = _tenant_scoped_uuid(tenant_id, "party", "customer", legacy_code)
        business_number = _normalized_business_number(row.get("tax_id"), legacy_code)
        company_name = _as_text(row.get("company_name")) or legacy_code
        contact_name = (
            _as_text(row.get("contact_person"))
            or _as_text(row.get("company_name"))
            or legacy_code
        )
        contact_phone = _as_text(row.get("phone")) or "N/A"
        contact_email = _as_text(row.get("email")) or "N/A"
        billing_address = _as_text(row.get("address")) or _as_text(row.get("full_address")) or "N/A"
        legacy_master_snapshot = _build_party_master_snapshot(row)
        # Truncate phone to column limit
        if contact_phone and len(contact_phone) > 30:
            contact_phone = contact_phone[:30]
        await connection.execute(
            """
			INSERT INTO customers (
				id,
				tenant_id,
				company_name,
				normalized_business_number,
				billing_address,
				contact_name,
				contact_phone,
				contact_email,
				credit_limit,
				status,
                customer_type,
                legacy_master_snapshot,
				version,
				created_at,
				updated_at
			)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::json, 1, NOW(), NOW())
			ON CONFLICT (tenant_id, normalized_business_number) DO UPDATE SET
				company_name = EXCLUDED.company_name,
				billing_address = EXCLUDED.billing_address,
				contact_name = EXCLUDED.contact_name,
				contact_phone = EXCLUDED.contact_phone,
				contact_email = EXCLUDED.contact_email,
				status = EXCLUDED.status,
                customer_type = CASE
                    WHEN EXCLUDED.customer_type = 'unknown' THEN customers.customer_type
                    ELSE EXCLUDED.customer_type
                END,
                legacy_master_snapshot = EXCLUDED.legacy_master_snapshot,
				updated_at = NOW()
			""",
            customer_id,
            tenant_id,
            company_name,
            business_number,
            billing_address,
            contact_name,
            contact_phone,
            contact_email,
            Decimal("0.00"),
            "active",
            _as_text(row.get("customer_type")) or "unknown",
            json.dumps(legacy_master_snapshot),
        )
        # Resolve actual customer_id: ON CONFLICT may have reused an existing row
        # Always look up by BN to get the actual persisted id
        actual_row = await connection.fetchrow(
            "SELECT id FROM customers WHERE tenant_id = $1 AND normalized_business_number = $2",
            tenant_id,
            business_number,
        )
        if actual_row is None:
            raise ValueError(
                f"No customer found for BN {business_number} after INSERT — "
                "check ON CONFLICT constraint or tenant_id mismatch"
            )
        actual_customer_id = actual_row["id"]
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="customers",
                canonical_id=actual_customer_id,
                source_table=_as_text(row.get("source_table")) or "tbscust",
                source_identifier=legacy_code,
                source_row_number=_as_int(row.get("source_row_number")),
            )
        )
        customer_by_code[legacy_code] = actual_customer_id
        business_number_by_code[legacy_code] = business_number
        count += 1
        lineage_count += 1
    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return count, lineage_count, customer_by_code, business_number_by_code


async def _import_suppliers(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    party_rows: AsyncIterable[dict[str, object]],
) -> tuple[int, int, dict[str, uuid.UUID]]:
    count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    supplier_by_code: dict[str, uuid.UUID] = {}
    async for row in party_rows:
        if _as_text(row.get("role")) != "supplier":
            continue
        legacy_code = _as_text(row.get("legacy_code"))
        supplier_id = _tenant_scoped_uuid(tenant_id, "party", "supplier", legacy_code)
        legacy_master_snapshot = _build_party_master_snapshot(row)
        await connection.execute(
            """
			INSERT INTO supplier (
				id,
				tenant_id,
				name,
				contact_email,
				phone,
				address,
                legacy_master_snapshot,
				default_lead_time_days,
				is_active,
				created_at
			)
            VALUES ($1, $2, $3, $4, $5, $6, $7::json, NULL, TRUE, NOW())
			ON CONFLICT (id) DO UPDATE SET
				name = EXCLUDED.name,
				contact_email = EXCLUDED.contact_email,
				phone = EXCLUDED.phone,
				address = EXCLUDED.address,
                legacy_master_snapshot = EXCLUDED.legacy_master_snapshot,
				default_lead_time_days = EXCLUDED.default_lead_time_days,
				is_active = EXCLUDED.is_active
			""",
            supplier_id,
            tenant_id,
            _as_text(row.get("company_name")) or legacy_code,
            _as_text(row.get("email")) or None,
            _as_text(row.get("phone")) or None,
            _as_text(row.get("address")) or _as_text(row.get("full_address")) or None,
            json.dumps(legacy_master_snapshot),
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="supplier",
                canonical_id=supplier_id,
                source_table=_as_text(row.get("source_table")) or "tbscust",
                source_identifier=legacy_code,
                source_row_number=_as_int(row.get("source_row_number")),
            )
        )
        supplier_by_code[legacy_code] = supplier_id
        count += 1
        lineage_count += 1
    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return count, lineage_count, supplier_by_code


async def _import_products(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    product_rows: AsyncIterable[dict[str, object]],
) -> tuple[int, int, dict[str, uuid.UUID], dict[str, dict[str, str | None]]]:
    count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    product_by_code: dict[str, uuid.UUID] = {}
    product_snapshot_by_code: dict[str, dict[str, str | None]] = {}
    unknown_product_present = False
    category_cache = await _load_category_cache(connection, tenant_id)

    async def _upsert_product_row(row: dict[str, object]) -> None:
        nonlocal count, lineage_count, unknown_product_present
        legacy_code = _as_text(row.get("legacy_code"))
        if legacy_code == UNKNOWN_PRODUCT_CODE:
            unknown_product_present = True
        product_id = _tenant_scoped_uuid(tenant_id, "product", legacy_code)
        legacy_master_snapshot = _build_product_master_snapshot(row)
        product_name = _as_text(row.get("name")) or legacy_code
        product_category_id, product_category = await _ensure_product_category(
            connection,
            tenant_id,
            _as_text(row.get("category")) or None,
            category_cache=category_cache,
        )
        status = (
            "inactive"
            if legacy_code == UNKNOWN_PRODUCT_CODE
            else (
                "active"
                if _as_text(row.get("status")) in {"A", "ACTIVE", "placeholder", "PLACEHOLDER"}
                else "inactive"
            )
        )
        await connection.execute(
            """
			INSERT INTO product (
				id,
				tenant_id,
				code,
				name,
				category,
                category_id,
				description,
				unit,
				status,
                legacy_master_snapshot,
				search_vector,
				created_at,
				updated_at
			)
			VALUES (
                $1::uuid, $2::uuid, $3::varchar, $4::varchar, $5::varchar, $6::uuid, $7::text,
                $8::varchar, $9::varchar, $10::json,
                to_tsvector(
                    'simple',
                    coalesce($3::text, '')
                    || ' '
                    || coalesce($4::text, '')
                    || ' '
                    || coalesce($5::text, '')
                ),
				NOW(), NOW()
			)
			ON CONFLICT (id) DO UPDATE SET
				code = EXCLUDED.code,
				name = EXCLUDED.name,
				category = EXCLUDED.category,
                category_id = EXCLUDED.category_id,
				description = EXCLUDED.description,
				unit = EXCLUDED.unit,
				status = EXCLUDED.status,
                legacy_master_snapshot = EXCLUDED.legacy_master_snapshot,
				search_vector = EXCLUDED.search_vector,
				updated_at = NOW()
			""",
            product_id,
            tenant_id,
            legacy_code,
            product_name,
            product_category,
            product_category_id,
            _as_text(row.get("description")) if row.get("description") else None,
            _as_text(row.get("unit")) or "pcs",
            status,
            json.dumps(legacy_master_snapshot),
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="product",
                canonical_id=product_id,
                source_table=_as_text(row.get("source_table")) or "tbsstock",
                source_identifier=legacy_code,
                source_row_number=_as_int(row.get("source_row_number")),
            )
        )
        product_by_code[legacy_code] = product_id
        product_snapshot_by_code[legacy_code] = {
            "name": product_name,
            "category": product_category,
        }
        count += 1
        lineage_count += 1

    async for row in product_rows:
        await _upsert_product_row(row)

    if not unknown_product_present:
        await _upsert_product_row(
            {
                "legacy_code": UNKNOWN_PRODUCT_CODE,
                "name": "Unknown Product",
                "category": None,
                "unit": "unknown",
                "status": "placeholder",
                "source_table": "product_code_mapping",
                "source_row_number": 0,
            }
        )

    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return count, lineage_count, product_by_code, product_snapshot_by_code


def _resolve_order_line_product_snapshots(
    line: dict[str, object],
    *,
    legacy_product_code: str,
    mapped_product_code: str,
    product_snapshot_by_code: dict[str, dict[str, str | None]],
) -> tuple[str, str | None]:
    product_snapshot = product_snapshot_by_code.get(mapped_product_code, {})
    fallback_name = _as_text(line.get("product_name")) or legacy_product_code or mapped_product_code
    fallback_category = (
        _as_text(line.get("product_category_snapshot"))
        or _as_text(line.get("product_category"))
        or _as_text(line.get("legacy_category"))
        or None
    )
    master_name = product_snapshot.get("name")
    master_category = product_snapshot.get("category")

    if mapped_product_code == UNKNOWN_PRODUCT_CODE:
        return (
            fallback_name or master_name or mapped_product_code,
            fallback_category or master_category,
        )

    return (
        master_name or fallback_name or mapped_product_code,
        master_category or fallback_category,
    )


async def _import_warehouses(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    warehouse_rows: AsyncIterable[dict[str, object]],
) -> tuple[int, int, dict[str, uuid.UUID]]:
    count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    warehouse_by_code: dict[str, uuid.UUID] = {}
    async for row in warehouse_rows:
        code = _as_text(row.get("code"))
        warehouse_id = _tenant_scoped_uuid(tenant_id, "warehouse", code)
        await connection.execute(
            """
			INSERT INTO warehouse (
				id,
				tenant_id,
				name,
				code,
				location,
				address,
				contact_email,
				is_active,
				created_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, NOW())
			ON CONFLICT (id) DO UPDATE SET
				name = EXCLUDED.name,
				code = EXCLUDED.code,
				location = EXCLUDED.location,
				address = EXCLUDED.address,
				contact_email = EXCLUDED.contact_email,
				is_active = EXCLUDED.is_active
			""",
            warehouse_id,
            tenant_id,
            _as_text(row.get("name")) or code,
            code,
            _as_text(row.get("location")) or None,
            _as_text(row.get("address")) or None,
            None,
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="warehouse",
                canonical_id=warehouse_id,
                source_table=_as_text(row.get("source_table")) or "normalized_warehouses",
                source_identifier=code,
                source_row_number=_as_int(row.get("source_row_number")),
            )
        )
        warehouse_by_code[code] = warehouse_id
        count += 1
        lineage_count += 1
    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return count, lineage_count, warehouse_by_code


async def _import_inventory(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    inventory_rows: AsyncIterable[dict[str, object]],
    product_by_code: dict[str, uuid.UUID],
    warehouse_by_code: dict[str, uuid.UUID],
) -> tuple[int, int]:
    count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    async for row in inventory_rows:
        product_code = _as_text(row.get("product_legacy_code"))
        warehouse_code = _as_text(row.get("warehouse_code"))
        product_id = product_by_code.get(product_code)
        warehouse_id = warehouse_by_code.get(warehouse_code)
        if product_id is None or warehouse_id is None:
            raise ValueError(
                "Inventory dependency missing for "
                f"product={product_code} warehouse={warehouse_code}"
            )
        inventory_id = _tenant_scoped_uuid(
            tenant_id,
            "inventory-stock",
            product_code,
            warehouse_code,
        )
        await connection.execute(
            """
			INSERT INTO inventory_stock (
				id,
				tenant_id,
				product_id,
				warehouse_id,
				quantity,
				reorder_point,
				updated_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, NOW())
			ON CONFLICT (id) DO UPDATE SET
				quantity = EXCLUDED.quantity,
				reorder_point = EXCLUDED.reorder_point,
				updated_at = NOW()
			""",
            inventory_id,
            tenant_id,
            product_id,
            warehouse_id,
            int(_as_decimal(row.get("quantity_on_hand"))),
            _as_int(row.get("reorder_point")),
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="inventory_stock",
                canonical_id=inventory_id,
                source_table=_as_text(row.get("source_table")) or "tbsstkhouse",
                source_identifier=f"{product_code}:{warehouse_code}",
                source_row_number=_as_int(row.get("source_row_number")),
            )
        )
        count += 1
        lineage_count += 1
    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return count, lineage_count


async def _import_legacy_receiving_audit(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    headers: list[dict[str, object]],
    lines: list[dict[str, object]],
    product_by_code: dict[str, uuid.UUID],
    warehouse_by_code: dict[str, uuid.UUID],
    product_mappings: dict[str, str],
) -> tuple[int, int, int, int]:
    count = 0
    lineage_count = 0
    holding_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    headers_by_doc = {
        _as_text(header.get("doc_number")): header
        for header in headers
        if _as_text(header.get("doc_number"))
    }
    batch_fallback_day = _derive_legacy_receiving_batch_fallback_day(headers, lines)

    for line in lines:
        doc_number = _as_text(line.get("doc_number"))
        line_number = _as_int(line.get("line_number"), 1)
        source_row_number = _as_int(line.get("source_row_number"))

        # Blank doc_number would produce colliding deterministic UUIDs across all blank
        # rows (same source_identifier = ":{line_number}"). Route to holding instead.
        # Use line_number as the row identity when source_row_number is absent or zero
        # to avoid UUID collisions in the holding table.
        row_identity = _resolve_row_identity(source_row_number, line_number)
        if not doc_number:
            ok = await _try_upsert_holding_and_lineage(
                connection,
                schema_name,
                run_id,
                tenant_id,
                batch_id,
                "receiving_audit",
                LEGACY_RECEIVING_SOURCE,
                f":{line_number}",
                source_row_number,
                row_identity,
                line,
                f"Blank doc_number held (row_id={row_identity}); UUID collision prevented.",
            )
            if ok:
                holding_count += 1
            continue

        source_identifier = f"{doc_number}:{line_number}"

        legacy_product_code = _as_text(line.get("product_code"))
        mapped_product_code = product_mappings.get(legacy_product_code) or legacy_product_code
        if mapped_product_code not in product_by_code:
            mapped_product_code = UNKNOWN_PRODUCT_CODE
        product_id = product_by_code.get(mapped_product_code)
        if product_id is None:
            raise ValueError(
                "Receiving audit line "
                f"{source_identifier} cannot resolve product {legacy_product_code}"
            )

        warehouse_code = _as_text(line.get("warehouse_code"))
        warehouse_id = warehouse_by_code.get(warehouse_code)
        if warehouse_id is None:
            raise ValueError(
                "Receiving audit line "
                f"{source_identifier} cannot resolve warehouse {warehouse_code}"
            )

        stock_adjustment_id = _tenant_scoped_uuid(
            tenant_id,
            "legacy-receiving-adjustment",
            source_identifier,
        )
        created_at = _resolve_legacy_receiving_created_at(
            line,
            headers_by_doc.get(doc_number),
            batch_fallback_day,
        )
        quantity_change, quantity_note = _coerce_quantity_for_integer_schema(
            line.get("qty"),
            field_name=f"Receiving audit line {source_identifier} quantity",
        )
        notes = f"Legacy import: invoice {doc_number}"
        if quantity_note:
            notes = f"{notes}; {quantity_note}"

        await connection.execute(
            """
			INSERT INTO stock_adjustment (
				id,
				tenant_id,
				product_id,
				warehouse_id,
				quantity_change,
				reason_code,
				actor_id,
				notes,
				transfer_id,
				created_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (id) DO NOTHING
			""",
            stock_adjustment_id,
            tenant_id,
            product_id,
            warehouse_id,
            quantity_change,
            ReasonCode.SUPPLIER_DELIVERY.value,
            "legacy_import",
            notes,
            None,
            created_at,
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="stock_adjustment",
                canonical_id=stock_adjustment_id,
                source_table=LEGACY_RECEIVING_SOURCE,
                source_identifier=source_identifier,
                source_row_number=_as_int(line.get("source_row_number")),
            )
        )
        count += 1
        lineage_count += 1

    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    fallback_count = sum(_receiving_date_fallback_counts.values())
    return count, lineage_count, holding_count, fallback_count


async def _import_sales_history(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    headers: list[dict[str, object]],
    lines: list[dict[str, object]],
    customer_by_code: dict[str, uuid.UUID],
    business_number_by_code: dict[str, str],
    product_by_code: dict[str, uuid.UUID],
    product_snapshot_by_code: dict[str, dict[str, str | None]],
    product_mappings: dict[str, str],
) -> tuple[int, int, int, int, int]:
    lines_by_doc: dict[str, list[dict[str, object]]] = {}
    for row in lines:
        lines_by_doc.setdefault(_as_text(row.get("doc_number")), []).append(row)

    order_count = 0
    order_line_count = 0
    invoice_count = 0
    invoice_line_count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []

    for header in headers:
        doc_number = _as_text(header.get("doc_number"))
        customer_code = _as_text(header.get("customer_code"))
        customer_id = customer_by_code.get(customer_code)
        if customer_id is None:
            continue

        invoice_date = _as_legacy_date(header.get("invoice_date"))
        created_at = _as_timestamp(invoice_date)
        order_id = _tenant_scoped_uuid(tenant_id, "order", doc_number)
        invoice_id = _tenant_scoped_uuid(tenant_id, "invoice", doc_number)
        order_status = _map_legacy_order_status(_as_text(header.get("source_status")))
        legacy_header_snapshot = _build_sales_header_snapshot(header)

        await connection.execute(
            """
			INSERT INTO orders (
				id,
				tenant_id,
				customer_id,
				order_number,
				status,
				payment_terms_code,
				payment_terms_days,
				subtotal_amount,
                discount_amount,
                discount_percent,
				tax_amount,
				total_amount,
				invoice_id,
				notes,
                legacy_header_snapshot,
				created_by,
				created_at,
				updated_at,
				confirmed_at
			)
            VALUES (
                $1,
                $2,
                $3,
                $4,
                $5,
                'NET_30',
                30,
                $6,
                0.00,
                0.0000,
                $7,
                $8,
                NULL,
                $9,
                $10::json,
                $11,
                $12,
                $12,
                $12
            )
			ON CONFLICT (id) DO UPDATE SET
				customer_id = EXCLUDED.customer_id,
				order_number = EXCLUDED.order_number,
				status = EXCLUDED.status,
				subtotal_amount = EXCLUDED.subtotal_amount,
                discount_amount = EXCLUDED.discount_amount,
                discount_percent = EXCLUDED.discount_percent,
				tax_amount = EXCLUDED.tax_amount,
				total_amount = EXCLUDED.total_amount,
				notes = EXCLUDED.notes,
                legacy_header_snapshot = EXCLUDED.legacy_header_snapshot,
				created_by = EXCLUDED.created_by,
				updated_at = NOW(),
				confirmed_at = EXCLUDED.confirmed_at
			""",
            order_id,
            tenant_id,
            customer_id,
            doc_number,
            order_status,
            _as_decimal(header.get("subtotal"), "0.00"),
            _as_decimal(header.get("tax_amount"), "0.00"),
            _as_decimal(header.get("total_amount"), "0.00"),
            _as_text(header.get("remark")) or None,
            json.dumps(legacy_header_snapshot),
            _as_text(header.get("created_by")) or "legacy-import",
            created_at,
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="orders",
                canonical_id=order_id,
                source_table="tbsslipx",
                source_identifier=doc_number,
                source_row_number=_as_int(header.get("source_row_number")),
            )
        )
        order_count += 1
        lineage_count += 1

        await connection.execute(
            """
			INSERT INTO invoices (
				id,
				tenant_id,
				invoice_number,
				invoice_date,
				customer_id,
				buyer_type,
				buyer_identifier_snapshot,
				currency_code,
				subtotal_amount,
				tax_amount,
				total_amount,
				status,
				version,
                legacy_header_snapshot,
				order_id,
				created_at,
				updated_at
			)
            VALUES (
                $1,
                $2,
                $3,
                $4,
                $5,
                'b2b',
                $6,
                $7,
                $8,
                $9,
                $10,
                $11,
                1,
                $12::json,
                $13,
                $14,
                $14
            )
			ON CONFLICT (id) DO UPDATE SET
				invoice_number = EXCLUDED.invoice_number,
				invoice_date = EXCLUDED.invoice_date,
				customer_id = EXCLUDED.customer_id,
				buyer_type = EXCLUDED.buyer_type,
				buyer_identifier_snapshot = EXCLUDED.buyer_identifier_snapshot,
				currency_code = EXCLUDED.currency_code,
				subtotal_amount = EXCLUDED.subtotal_amount,
				tax_amount = EXCLUDED.tax_amount,
				total_amount = EXCLUDED.total_amount,
				status = EXCLUDED.status,
                legacy_header_snapshot = EXCLUDED.legacy_header_snapshot,
				order_id = EXCLUDED.order_id,
				updated_at = NOW()
			""",
            invoice_id,
            tenant_id,
            doc_number,
            invoice_date,
            customer_id,
            business_number_by_code.get(customer_code) or "00000000",
            _currency_code(header.get("currency_code")),
            _as_decimal(header.get("subtotal"), "0.00"),
            _as_decimal(header.get("tax_amount"), "0.00"),
            _as_decimal(header.get("total_amount"), "0.00"),
            _map_legacy_status_to_canonical(_as_text(header.get("source_status"))),
            json.dumps(legacy_header_snapshot),
            order_id,
            created_at,
        )
        await connection.execute(
            """
			UPDATE orders
			SET invoice_id = $1, updated_at = NOW()
			WHERE id = $2 AND tenant_id = $3
			""",
            invoice_id,
            order_id,
            tenant_id,
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="invoices",
                canonical_id=invoice_id,
                source_table="tbsslipx",
                source_identifier=doc_number,
                source_row_number=_as_int(header.get("source_row_number")),
            )
        )
        invoice_count += 1
        lineage_count += 1

        for line in sorted(
            lines_by_doc.get(doc_number, []), key=lambda item: _as_int(item.get("line_number"), 0)
        ):
            legacy_product_code = _as_text(line.get("product_code"))
            mapped_product_code = product_mappings.get(legacy_product_code) or legacy_product_code
            if mapped_product_code not in product_by_code:
                mapped_product_code = UNKNOWN_PRODUCT_CODE
            product_id = product_by_code.get(mapped_product_code)
            if product_id is None:
                raise ValueError(
                    "Sales line "
                    f"{doc_number}:{_as_int(line.get('line_number'))} "
                    f"cannot resolve product {legacy_product_code}"
                )

            (
                product_name_snapshot,
                product_category_snapshot,
            ) = _resolve_order_line_product_snapshots(
                line,
                legacy_product_code=legacy_product_code,
                mapped_product_code=mapped_product_code,
                product_snapshot_by_code=product_snapshot_by_code,
            )

            line_number = _as_int(line.get("line_number"), 1)
            # col_21 = discounted/actual unit price; col_19 = foldprice (may be pre-adjusted)
            list_unit_price = _as_decimal(line.get("list_unit_price"), "0.00")
            unit_price = _as_decimal(line.get("unit_price"), "0.00")
            extended_amount = _as_decimal(line.get("extended_amount"), "0.00")
            # col_23 = actual quantity
            quantity = _as_decimal(line.get("qty"), "0")
            # Check for pre-adjusted foldprice: sexp1/col_44 holds original list when
            # foldprice was already set to the post-discount price (fnewprice * fdisper)
            original_list_price = _as_decimal(line.get("original_list_price"), None)
            original_discount_ratio = _as_decimal(line.get("original_discount_ratio"), None)
            if (
                original_list_price is not None
                and original_discount_ratio is not None
                and original_list_price > list_unit_price
                and Decimal("0") < original_discount_ratio < Decimal("1")
            ):
                # foldprice was pre-adjusted; use sexp1 as the true original list price
                actual_list_price = original_list_price
            else:
                actual_list_price = list_unit_price
            # Discount per unit: original list - unit (always >= 0)
            discount_amount = max(
                Decimal("0.00"),
                (actual_list_price - unit_price).quantize(Decimal("0.01")),
            )
            subtotal = extended_amount  # already the discounted subtotal
            # col_22 = line tax amount, col_23 = qty, col_29 = subtotal
            # Derive effective tax rate: rate = line_tax / subtotal
            line_tax_amount = _as_decimal(line.get("line_tax_amount"), "0.00")
            line_total = subtotal + line_tax_amount
            # Clamp BEFORE quantizing to avoid rounding overflow; max(0, ...) handles bad data
            MAX_TAX_RATE = Decimal("99.9999")
            MIN_TAX_RATE = Decimal("0.0000")
            raw_rate = (
                (line_tax_amount / extended_amount * Decimal("100"))
                if extended_amount
                else Decimal("0")
            )
            tax_rate = max(MIN_TAX_RATE, min(raw_rate, MAX_TAX_RATE)).quantize(Decimal("0.0001"))
            tax_policy_code = "standard" if line_tax_amount > 0 else "exempt"
            tax_type = 1 if line_tax_amount > 0 else 3
            order_line_id = _tenant_scoped_uuid(
                tenant_id,
                "order-line",
                doc_number,
                str(line_number),
            )
            invoice_line_id = _tenant_scoped_uuid(
                tenant_id, "invoice-line", doc_number, str(line_number)
            )


            await connection.execute(
                """
				INSERT INTO order_lines (
					id,
					tenant_id,
					order_id,
					product_id,
					line_number,
					quantity,
					list_unit_price,
					unit_price,
					discount_amount,
					tax_policy_code,
					tax_type,
					tax_rate,
					tax_amount,
					subtotal_amount,
					total_amount,
					description,
                    product_name_snapshot,
                    product_category_snapshot,
					available_stock_snapshot,
					backorder_note,
					created_at
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
                    $16,
                    $17,
                    $18,
                    $19,
                    $20,
                    NOW()
                )
				ON CONFLICT (id) DO UPDATE SET
					product_id = EXCLUDED.product_id,
					line_number = EXCLUDED.line_number,
					quantity = EXCLUDED.quantity,
					list_unit_price = EXCLUDED.list_unit_price,
					unit_price = EXCLUDED.unit_price,
					discount_amount = EXCLUDED.discount_amount,
					tax_policy_code = EXCLUDED.tax_policy_code,
					tax_type = EXCLUDED.tax_type,
					tax_rate = EXCLUDED.tax_rate,
					tax_amount = EXCLUDED.tax_amount,
					subtotal_amount = EXCLUDED.subtotal_amount,
					total_amount = EXCLUDED.total_amount,
					description = EXCLUDED.description,
                    product_name_snapshot=COALESCE(
                        order_lines.product_name_snapshot,
                        EXCLUDED.product_name_snapshot,
                    ),
                    product_category_snapshot=COALESCE(
                        order_lines.product_category_snapshot,
                        EXCLUDED.product_category_snapshot,
                    ),
					available_stock_snapshot = EXCLUDED.available_stock_snapshot
				""",
                order_line_id,
                tenant_id,
                order_id,
                product_id,
                line_number,
                quantity,
                actual_list_price,
                unit_price,
                discount_amount,
                tax_policy_code,
                tax_type,
                tax_rate,
                line_tax_amount,
                subtotal,
                line_total,
                _as_text(line.get("product_name")) or legacy_product_code,
                product_name_snapshot,
                product_category_snapshot,
                _as_decimal(line.get("available_stock_snapshot"), "0"),
                None,  # backorder_note: legacy import does not calculate backorder status
            )
            pending_lineage.append(
                PendingLineageResolution(
                    canonical_table="order_lines",
                    canonical_id=order_line_id,
                    source_table="tbsslipdtx",
                    source_identifier=f"{doc_number}:{line_number}",
                    source_row_number=_as_int(line.get("source_row_number")),
                )
            )
            order_line_count += 1
            lineage_count += 1

            await connection.execute(
                """
				INSERT INTO invoice_lines (
					id,
					invoice_id,
					tenant_id,
					line_number,
					product_id,
					product_code_snapshot,
					description,
					quantity,
					unit_price,
					subtotal_amount,
					tax_type,
					tax_rate,
					tax_amount,
					total_amount,
					zero_tax_rate_reason,
					created_at
				)
				VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NULL, NOW())
				ON CONFLICT (id) DO UPDATE SET
					invoice_id = EXCLUDED.invoice_id,
					line_number = EXCLUDED.line_number,
					product_id = EXCLUDED.product_id,
					product_code_snapshot = EXCLUDED.product_code_snapshot,
					description = EXCLUDED.description,
					quantity = EXCLUDED.quantity,
					unit_price = EXCLUDED.unit_price,
					subtotal_amount = EXCLUDED.subtotal_amount,
					tax_type = EXCLUDED.tax_type,
					tax_rate = EXCLUDED.tax_rate,
					tax_amount = EXCLUDED.tax_amount,
					total_amount = EXCLUDED.total_amount
				""",
                invoice_line_id,
                invoice_id,
                tenant_id,
                line_number,
                product_id,
                legacy_product_code,
                _as_text(line.get("product_name")) or legacy_product_code,
                quantity,
                unit_price,
                subtotal,
                tax_type,
                tax_rate,
                line_tax_amount,
                line_total,
            )
            pending_lineage.append(
                PendingLineageResolution(
                    canonical_table="invoice_lines",
                    canonical_id=invoice_line_id,
                    source_table="tbsslipdtx",
                    source_identifier=f"{doc_number}:{line_number}",
                    source_row_number=_as_int(line.get("source_row_number")),
                )
            )
            invoice_line_count += 1
            lineage_count += 1

        # Recalculate order and invoice totals from the inserted lines
        # to correct discrepancies between tbsslipx header totals and actual line sums
        line_totals = await connection.fetch(
            """
            SELECT
                SUM(subtotal_amount) AS subtotal,
                SUM(tax_amount) AS tax,
                SUM(total_amount) AS total
            FROM order_lines
            WHERE tenant_id = $1 AND order_id = $2
            """,
            tenant_id,
            order_id,
        )
        if line_totals and line_totals[0]:
            row = line_totals[0]
            recalc_subtotal = row["subtotal"] or Decimal("0.00")
            recalc_tax = row["tax"] or Decimal("0.00")
            recalc_total = row["total"] or Decimal("0.00")
            await connection.execute(
                """
                UPDATE orders
                SET subtotal_amount = $1, tax_amount = $2, total_amount = $3, updated_at = NOW()
                WHERE id = $4
                """,
                recalc_subtotal,
                recalc_tax,
                recalc_total,
                order_id,
            )
            await connection.execute(
                """
                UPDATE invoices
                SET subtotal_amount = $1, tax_amount = $2, total_amount = $3, updated_at = NOW()
                WHERE id = $4
                """,
                recalc_subtotal,
                recalc_tax,
                recalc_total,
                invoice_id,
            )

    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return order_count, order_line_count, invoice_count, invoice_line_count, lineage_count


def _allocate_tax_amounts(
    subtotals: list[Decimal],
    total_tax_amount: Decimal,
) -> list[Decimal]:
    if not subtotals:
        return []

    total_tax_amount = _as_money(total_tax_amount)
    if total_tax_amount == Decimal("0.00"):
        return [Decimal("0.00")] * len(subtotals)

    subtotal_total = sum(subtotals, Decimal("0.00"))
    if subtotal_total == Decimal("0.00"):
        allocations = [Decimal("0.00")] * len(subtotals)
        allocations[-1] = total_tax_amount
        return allocations

    allocations: list[Decimal] = []
    running_total = Decimal("0.00")
    for index, subtotal in enumerate(subtotals):
        if index == len(subtotals) - 1:
            allocation = total_tax_amount - running_total
        else:
            allocation = _as_money((total_tax_amount * subtotal) / subtotal_total)
            running_total += allocation
        allocations.append(_as_money(allocation))
    return allocations


async def _import_purchase_history(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    headers: list[dict[str, object]],
    lines: list[dict[str, object]],
    supplier_by_code: dict[str, uuid.UUID],
    product_by_code: dict[str, uuid.UUID],
    product_mappings: dict[str, str],
) -> tuple[int, int, int]:
    lines_by_doc: dict[str, list[dict[str, object]]] = {}
    for row in lines:
        lines_by_doc.setdefault(_as_text(row.get("doc_number")), []).append(row)

    invoice_count = 0
    invoice_line_count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []

    for header in headers:
        doc_number = _as_text(header.get("doc_number"))
        if not doc_number:
            raise ValueError("Purchase header is missing doc_number")
        invoice_number = _as_text(header.get("invoice_number")) or doc_number
        if not invoice_number:
            raise ValueError(f"Purchase header {doc_number} is missing invoice_number")
        supplier_code = _as_text(header.get("supplier_code"))
        supplier_id = supplier_by_code.get(supplier_code)
        if supplier_id is None:
            raise ValueError(
                f"Purchase header {doc_number} references missing supplier {supplier_code}"
            )

        invoice_date = _as_legacy_date(header.get("invoice_date"))
        if invoice_date is None:
            raise ValueError(f"Purchase header {doc_number} is missing invoice_date")

        created_at = _as_timestamp(invoice_date)
        supplier_invoice_id = _tenant_scoped_uuid(tenant_id, "supplier-invoice", doc_number)
        header_lines = sorted(
            lines_by_doc.get(doc_number, []), key=lambda item: _as_int(item.get("line_number"), 0)
        )
        tax_amount = _as_money(_as_decimal(header.get("tax_amount"), "0.00"))
        remaining_payable_amount = _as_money(_as_decimal(header.get("must_pay_amount"), "0.00"))
        line_total_amount = _as_money(
            sum(
                (_as_decimal(line.get("extended_amount"), "0.00") for line in header_lines),
                Decimal("0.00"),
            )
        )
        total_amount = _resolve_purchase_invoice_total(
            header.get("subtotal"),
            header.get("tax_amount"),
            header.get("must_pay_amount"),
            line_total_amount,
        )
        supplier_invoice_status = _map_purchase_invoice_status(header.get("must_pay_amount"))
        legacy_header_snapshot = _build_purchase_header_snapshot(header)

        await connection.execute(
            """
			INSERT INTO supplier_invoices (
				id,
				tenant_id,
				supplier_id,
				invoice_number,
				invoice_date,
				currency_code,
				subtotal_amount,
				tax_amount,
				total_amount,
                remaining_payable_amount,
				status,
				notes,
                legacy_header_snapshot,
				created_at,
				updated_at
			)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::json, $14, $14)
			ON CONFLICT (id) DO UPDATE SET
				supplier_id = EXCLUDED.supplier_id,
				invoice_number = EXCLUDED.invoice_number,
				invoice_date = EXCLUDED.invoice_date,
				currency_code = EXCLUDED.currency_code,
				subtotal_amount = EXCLUDED.subtotal_amount,
				tax_amount = EXCLUDED.tax_amount,
				total_amount = EXCLUDED.total_amount,
                remaining_payable_amount = EXCLUDED.remaining_payable_amount,
				status = EXCLUDED.status,
				notes = EXCLUDED.notes,
                legacy_header_snapshot = EXCLUDED.legacy_header_snapshot,
				updated_at = NOW()
			""",
            supplier_invoice_id,
            tenant_id,
            supplier_id,
            invoice_number,
            invoice_date,
            _currency_code(header.get("currency_code")),
            _as_money(_as_decimal(header.get("subtotal"), "0.00")),
            tax_amount,
            total_amount,
            remaining_payable_amount,
            supplier_invoice_status,
            _as_text(header.get("notes")) or None,
            json.dumps(legacy_header_snapshot),
            created_at,
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="supplier_invoices",
                canonical_id=supplier_invoice_id,
                source_table="tbsslipj",
                source_identifier=doc_number,
                source_row_number=_as_int(header.get("source_row_number")),
            )
        )
        invoice_count += 1
        lineage_count += 1

        line_subtotals = [
            _as_money(_as_decimal(line.get("extended_amount"), "0.00"))
            for line in header_lines
        ]
        line_tax_amounts = _allocate_tax_amounts(line_subtotals, tax_amount)

        for line, line_tax_amount in zip(header_lines, line_tax_amounts, strict=False):
            legacy_product_code = _as_text(line.get("product_code"))
            mapped_product_code = product_mappings.get(legacy_product_code) or legacy_product_code
            if mapped_product_code not in product_by_code:
                mapped_product_code = UNKNOWN_PRODUCT_CODE
            product_id = product_by_code.get(mapped_product_code)
            if product_id is None:
                raise ValueError(
                    "Purchase line "
                    f"{doc_number}:{_as_int(line.get('line_number'))} "
                    f"cannot resolve product {legacy_product_code}"
                )

            line_number = _as_int(line.get("line_number"), 1)
            quantity = _as_decimal(line.get("qty"), "0")
            unit_price = _as_money(_as_decimal(line.get("unit_price"), "0.00"))
            subtotal = _as_money(_as_decimal(line.get("extended_amount"), "0.00"))
            line_total = _as_money(subtotal + line_tax_amount)
            _, tax_type, tax_rate = _tax_policy_code(line_tax_amount)
            supplier_invoice_line_id = _tenant_scoped_uuid(
                tenant_id,
                "supplier-invoice-line",
                doc_number,
                str(line_number),
            )

            await connection.execute(
                """
				INSERT INTO supplier_invoice_lines (
					id,
					supplier_invoice_id,
					tenant_id,
					line_number,
					product_id,
					product_code_snapshot,
					description,
					quantity,
					unit_price,
					subtotal_amount,
					tax_type,
					tax_rate,
					tax_amount,
					total_amount,
					created_at
				)
				VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW())
				ON CONFLICT (id) DO UPDATE SET
					supplier_invoice_id = EXCLUDED.supplier_invoice_id,
					line_number = EXCLUDED.line_number,
					product_id = EXCLUDED.product_id,
					product_code_snapshot = EXCLUDED.product_code_snapshot,
					description = EXCLUDED.description,
					quantity = EXCLUDED.quantity,
					unit_price = EXCLUDED.unit_price,
					subtotal_amount = EXCLUDED.subtotal_amount,
					tax_type = EXCLUDED.tax_type,
					tax_rate = EXCLUDED.tax_rate,
					tax_amount = EXCLUDED.tax_amount,
					total_amount = EXCLUDED.total_amount
				""",
                supplier_invoice_line_id,
                supplier_invoice_id,
                tenant_id,
                line_number,
                product_id,
                legacy_product_code,
                _as_text(line.get("product_name")) or legacy_product_code,
                quantity,
                unit_price,
                subtotal,
                tax_type,
                tax_rate,
                line_tax_amount,
                line_total,
            )
            pending_lineage.append(
                PendingLineageResolution(
                    canonical_table="supplier_invoice_lines",
                    canonical_id=supplier_invoice_line_id,
                    source_table=LEGACY_RECEIVING_SOURCE,
                    source_identifier=f"{doc_number}:{line_number}",
                    source_row_number=_as_int(line.get("source_row_number")),
                )
            )
            invoice_line_count += 1
            lineage_count += 1

    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return invoice_count, invoice_line_count, lineage_count


async def _try_upsert_holding_and_lineage(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    domain_name: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
    row_identity: int,
    payload: dict[str, object],
    notes: str,
) -> bool:
    """Insert holding payload and lineage entry in one savepoint.

    The nested transaction becomes a savepoint inside the outer import transaction,
    so a holding-state failure rolls back both writes for this source row without
    aborting the rest of the batch.

    Also creates a lineage entry with canonical_table='__holding__' so that every
    held row is visible in the lineage audit trail (AC2 guarantee).
    """
    try:
        holding_id = source_resolution.build_holding_id(
            tenant_id,
            domain_name=domain_name,
            source_table=source_table,
            source_identifier=source_identifier,
            source_row_number=source_row_number,
            row_identity=row_identity,
        )
        async with connection.transaction():
            await source_resolution.hold_source_row(
                connection,
                schema_name=schema_name,
                run_id=run_id,
                tenant_id=tenant_id,
                batch_id=batch_id,
                domain_name=domain_name,
                source_table=source_table,
                source_identifier=source_identifier,
                source_row_number=source_row_number,
                row_identity=row_identity,
                holding_id=holding_id,
                payload=payload,
                notes=notes,
            )
            # AC2: Every held row gets a lineage entry with __holding__ sentinel.
            # This entry will be updated (not duplicated) when the drain path
            # later upserts a lineage record for the same source identifiers.
            await _upsert_lineage_record_for_holding(
                connection,
                schema_name=schema_name,
                run_id=run_id,
                tenant_id=tenant_id,
                batch_id=batch_id,
                canonical_id=holding_id,
                source_table=source_table,
                source_identifier=source_identifier,
                source_row_number=source_row_number,
            )
        return True
    except asyncio.CancelledError:
        raise
    except Exception:
        _LOGGER.error(
            "Failed to insert source-row holding state for %s at source_id=%s",
            domain_name,
            row_identity or source_identifier,
            exc_info=True,
        )
        return False


async def _hold_payment_adjacent_history(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
) -> int:
    quoted_schema = _quoted_identifier(schema_name)
    total = 0
    for table_name in ("tbsprepay", "tbsspay"):
        if not await _table_exists(connection, schema_name, table_name):
            continue
        async for raw_row in _iter_query_rows(
            connection,
            f"""
			SELECT *
			FROM {quoted_schema}.{table_name}
			WHERE _batch_id = $1
			ORDER BY _source_row_number
			""",
            batch_id,
        ):
            source_identifier = (
                _as_text(raw_row.get("col_2"))
                or f"{table_name}:{_as_int(raw_row.get('_source_row_number'))}"
            )
            source_row_number = _as_int(raw_row.get("_source_row_number"))
            ok = await _try_upsert_holding_and_lineage(
                connection,
                schema_name,
                run_id,
                tenant_id,
                batch_id,
                "payment_history",
                table_name,
                source_identifier,
                source_row_number,
                source_row_number,
                raw_row,
                (
                    "Payment-adjacent legacy rows are preserved in holding "
                    "until a verified payment mapping is defined."
                ),
            )
            if ok:
                total += 1
    return total


async def run_canonical_import(
    *,
    batch_id: str,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str | None = None,
    # Story 15.26: Scoped incremental parameters
    selected_domains: Sequence[str] | None = None,
    entity_scope: Mapping[str, object] | None = None,
    batch_mode: str | None = None,
    last_successful_batch_ids: Mapping[str, str] | None = None,
) -> CanonicalImportResult:
    """Run canonical import with optional incremental scope.

    Args:
        batch_id: The batch identifier for this import run.
        tenant_id: The tenant UUID (defaults to DEFAULT_TENANT_ID).
        schema_name: The raw legacy schema name (defaults to settings.legacy_import_schema).
        selected_domains: Optional sequence of domain names to process.
            If None, all domains are processed (full batch behavior).
        entity_scope: Optional per-domain closure keys from the delta manifest.
            Maps domain_name -> {closure_keys: [...], ...}.
            For sales/purchase: closure_keys are doc_numbers.
            For parties/products/warehouses/inventory: closure_keys are legacy codes.
        batch_mode: Optional batch mode ('full' or 'incremental').
            If 'incremental', respects selected_domains and entity_scope.
        last_successful_batch_ids: Optional mapping of domain -> last successful batch_id.
            Used for deterministic dependent-master lookup in scoped reruns.

    Returns:
        CanonicalImportResult with counts and scoped metadata.

    AC1: When selected_domains and entity_scope are provided with batch_mode=incremental,
         only impacted masters, inventory tuples, and full document families are upserted.
    AC2: Full header+line families are rebuilt deterministically for in-scope documents.
    AC3: Unresolved issues outside scope do not make the batch review-required.
    AC4: Same manifest scope produces idempotent results (deterministic IDs preserved).
    AC5: Dependent master resolution uses scoped handoff deterministically.
    """
    from collections.abc import Mapping as MappingABC

    # Normalize batch_mode for scope determination
    is_incremental = str(batch_mode).lower() == "incremental" if batch_mode else False

    # Normalize selected_domains to tuple (only used when incremental)
    # In full batch mode, selected_domains is ignored
    normalized_selected: tuple[str, ...] = ()
    if is_incremental and selected_domains is not None:
        normalized_selected = tuple(str(d) for d in selected_domains)

    # Build entity_scope closure keys lookup (only used when incremental)
    scope_closure_keys = _build_entity_scope_closure_keys(
        entity_scope if is_incremental and isinstance(entity_scope, MappingABC) else None
    )

    # Determine which domains are skipped (not in scope)
    ALL_CANONICAL_DOMAINS = frozenset({
        "customers", "suppliers", "products", "warehouses",
        "inventory", "receiving_audit", "sales_history", "purchase_history",
    })
    skipped_domains_list: list[str] = []
    if is_incremental and normalized_selected:
        for domain in ALL_CANONICAL_DOMAINS:
            if domain not in normalized_selected:
                skipped_domains_list.append(domain)
    skipped_domains_tuple = tuple(skipped_domains_list)

    _receiving_date_fallback_counts.clear()
    _receiving_date_fallback_counts.update({
        "receiving_date_fallback_receipt_to_invoice": 0,
        "receiving_date_fallback_to_batch": 0,
        "receiving_date_fallback_to_import_day": 0,
    })
    resolved_schema = schema_name or settings.legacy_import_schema
    connection = await _open_raw_connection()
    run_id = uuid.uuid4()
    attempt_number = 1
    step_outcomes: list[tuple[str, int, str, str | None]] = []
    counts: dict[str, int] = {
        "customer_count": 0,
        "supplier_count": 0,
        "product_count": 0,
        "warehouse_count": 0,
        "inventory_count": 0,
        "receiving_audit_count": 0,
        "order_count": 0,
        "order_line_count": 0,
        "invoice_count": 0,
        "invoice_line_count": 0,
        "supplier_invoice_count": 0,
        "supplier_invoice_line_count": 0,
        "holding_count": 0,
        "lineage_count": 0,
    }
    # Story 15.26: Track scoped document count
    scoped_document_count = 0
    current_step: str | None = None

    # Track unresolved mapping issues seen in current scope
    scope_review_required_issues: list[str] = []

    # Initialize lineage counts for all domains (may be skipped in scoped runs)
    customer_lineage_count = 0
    supplier_lineage_count = 0
    product_lineage_count = 0
    warehouse_lineage_count = 0
    inventory_lineage_count = 0
    receiving_audit_lineage_count = 0
    receiving_holding_count = 0
    receiving_date_fallback_count = 0
    sales_lineage_count = 0
    purchase_lineage_count = 0

    try:
        await _ensure_canonical_support_tables(connection, resolved_schema)
        attempt_number = await _next_attempt_number(
            connection, resolved_schema, batch_id, tenant_id
        )

        product_mappings = await _fetch_product_mappings(connection, resolved_schema, tenant_id)

        async with connection.transaction():
            await _upsert_run_row(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                attempt_number,
                "running",
                counts,
                None,
            )

            # Initialize master lookups (needed even if domain is skipped, for dependent resolution)
            # Story 15.26: customers domain
            current_step = "customers"
            customer_by_code: dict[str, uuid.UUID] = {}
            business_number_by_code: dict[str, str] = {}
            if _domain_in_selected("customers", normalized_selected):
                (
                    counts["customer_count"],
                    customer_lineage_count,
                    customer_by_code,
                    business_number_by_code,
                ) = await _import_customers(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    _iter_normalized_parties(connection, resolved_schema, batch_id, tenant_id),
                )
                counts["lineage_count"] += customer_lineage_count
                step_outcomes.append(("customers", counts["customer_count"], "completed", None))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "customers",
                    counts["customer_count"],
                    "completed",
                )
            else:
                step_outcomes.append(("customers", 0, "skipped", "domain not in scope"))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "customers",
                    0,
                    "skipped",
                )

            # Story 15.26: suppliers domain
            current_step = "suppliers"
            supplier_by_code: dict[str, uuid.UUID] = {}
            if _domain_in_selected("suppliers", normalized_selected):
                (
                    counts["supplier_count"],
                    supplier_lineage_count,
                    supplier_by_code,
                ) = await _import_suppliers(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    _iter_normalized_parties(connection, resolved_schema, batch_id, tenant_id),
                )
                counts["lineage_count"] += supplier_lineage_count
                step_outcomes.append(("suppliers", counts["supplier_count"], "completed", None))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "suppliers",
                    counts["supplier_count"],
                    "completed",
                )
            else:
                step_outcomes.append(("suppliers", 0, "skipped", "domain not in scope"))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "suppliers",
                    0,
                    "skipped",
                )

            # Story 15.26: products domain
            current_step = "products"
            product_by_code: dict[str, uuid.UUID] = {}
            product_snapshot_by_code: dict[str, dict[str, str | None]] = {}
            if _domain_in_selected("products", normalized_selected):
                (
                    counts["product_count"],
                    product_lineage_count,
                    product_by_code,
                    product_snapshot_by_code,
                ) = await _import_products(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    _iter_normalized_products(connection, resolved_schema, batch_id, tenant_id),
                )
                counts["lineage_count"] += product_lineage_count
                step_outcomes.append(("products", counts["product_count"], "completed", None))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "products",
                    counts["product_count"],
                    "completed",
                )
            else:
                step_outcomes.append(("products", 0, "skipped", "domain not in scope"))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "products",
                    0,
                    "skipped",
                )

            # Story 15.26: warehouses domain
            current_step = "warehouses"
            warehouse_by_code: dict[str, uuid.UUID] = {}
            if _domain_in_selected("warehouses", normalized_selected):
                (
                    counts["warehouse_count"],
                    warehouse_lineage_count,
                    warehouse_by_code,
                ) = await _import_warehouses(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    _iter_normalized_warehouses(connection, resolved_schema, batch_id, tenant_id),
                )
                counts["lineage_count"] += warehouse_lineage_count
                step_outcomes.append(("warehouses", counts["warehouse_count"], "completed", None))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "warehouses",
                    counts["warehouse_count"],
                    "completed",
                )
            else:
                step_outcomes.append(("warehouses", 0, "skipped", "domain not in scope"))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "warehouses",
                    0,
                    "skipped",
                )

            # Story 15.26: inventory domain
            current_step = "inventory"
            if _domain_in_selected("inventory", normalized_selected):
                counts["inventory_count"], inventory_lineage_count = await _import_inventory(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    _iter_normalized_inventory(connection, resolved_schema, batch_id, tenant_id),
                    product_by_code,
                    warehouse_by_code,
                )
                counts["lineage_count"] += inventory_lineage_count
                step_outcomes.append(("inventory", counts["inventory_count"], "completed", None))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "inventory",
                    counts["inventory_count"],
                    "completed",
                )
            else:
                step_outcomes.append(("inventory", 0, "skipped", "domain not in scope"))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "inventory",
                    0,
                    "skipped",
                )

            # Story 15.26: Fetch purchase data with scope filtering
            # Note: receiving_audit needs ALL lines (including blank doc_numbers for holding)
            # while purchase_history needs only scoped lines by header doc_number
            purchase_headers_all = (
                await _fetch_purchase_headers(connection, resolved_schema, batch_id)
                if await _table_exists(connection, resolved_schema, "tbsslipj")
                else []
            )
            purchase_lines_all = (
                await _fetch_purchase_lines(connection, resolved_schema, batch_id)
                if await _table_exists(connection, resolved_schema, LEGACY_RECEIVING_SOURCE)
                else []
            )

            # Apply scope filtering to purchase headers
            scoped_purchase_headers = _filter_purchase_headers_by_scope(
                purchase_headers_all, scope_closure_keys
            )

            # Story 15.26: receiving_audit domain gets ALL lines (including blank doc_numbers)
            # because blank doc_number lines need to be routed to holding
            current_step = "receiving_audit"
            if _domain_in_selected("receiving_audit", normalized_selected):
                (
                    counts["receiving_audit_count"],
                    receiving_audit_lineage_count,
                    receiving_holding_count,
                    receiving_date_fallback_count,
                ) = await _import_legacy_receiving_audit(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    scoped_purchase_headers,
                    purchase_lines_all,  # All lines for receiving audit (handles blank doc_numbers)
                    product_by_code,
                    warehouse_by_code,
                    product_mappings,
                )
                counts["lineage_count"] += receiving_audit_lineage_count
                counts["holding_count"] += receiving_holding_count
                step_outcomes.append(
                    (
                        "receiving_audit",
                        counts["receiving_audit_count"],
                        "completed",
                        None,
                    )
                )
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "receiving_audit",
                    counts["receiving_audit_count"],
                    "completed",
                )
            else:
                step_outcomes.append(("receiving_audit", 0, "skipped", "domain not in scope"))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "receiving_audit",
                    0,
                    "skipped",
                )

            # Story 15.26: Fetch sales data with scope filtering
            sales_headers_all = await _fetch_sales_headers(connection, resolved_schema, batch_id)
            sales_lines_all = await _fetch_sales_lines(connection, resolved_schema, batch_id)

            # Apply scope filtering to sales documents
            scoped_sales_headers = _filter_sales_headers_by_scope(
                sales_headers_all, scope_closure_keys
            )
            scoped_sales_doc_numbers = frozenset(
                _as_text(h.get("doc_number")) for h in scoped_sales_headers
            )
            scoped_sales_lines = _filter_sales_lines_by_scope(
                sales_lines_all, scoped_sales_doc_numbers
            )

            # Apply scope filtering to purchase lines for purchase_history
            scoped_purchase_doc_numbers = frozenset(
                _as_text(h.get("doc_number")) for h in scoped_purchase_headers
            )
            scoped_purchase_lines = _filter_purchase_lines_by_scope(
                purchase_lines_all, scoped_purchase_doc_numbers
            )

            scoped_document_count = len(scoped_sales_headers) + len(scoped_purchase_headers)

            # =================================================================
            # AC5: Enrich master lookups from prior batch lineage
            # When a scoped run doesn't have all master entities in staging,
            # look them up from the last successful batch's lineage.
            # =================================================================
            if is_incremental and last_successful_batch_ids is not None:
                # Get customer codes needed for scoped sales headers
                needed_customer_codes = frozenset(
                    _as_text(h.get("customer_code"))
                    for h in scoped_sales_headers
                    if _as_text(h.get("customer_code"))
                )
                missing_customer_codes = [
                    code for code in needed_customer_codes
                    if code and code not in customer_by_code
                ]
                if missing_customer_codes:
                    prior_customers = await _build_prior_master_lookup(
                        connection,
                        resolved_schema,
                        tenant_id,
                        last_successful_batch_ids,
                        "customers",
                        "tbscust",
                        missing_customer_codes,
                    )
                    customer_by_code.update(prior_customers)
                    _LOGGER.info(
                        "AC5: Resolved %d missing customer codes from prior batch lineage",
                        len(prior_customers),
                    )

                # Get product codes needed for scoped sales lines
                needed_product_codes = frozenset(
                    _as_text(line.get("product_code"))
                    for line in scoped_sales_lines
                    if _as_text(line.get("product_code"))
                )
                missing_product_codes = [
                    code for code in needed_product_codes
                    if code and code not in product_by_code
                ]
                if missing_product_codes:
                    prior_products = await _build_prior_master_lookup(
                        connection,
                        resolved_schema,
                        tenant_id,
                        last_successful_batch_ids,
                        "product",
                        "tbsstock",
                        missing_product_codes,
                    )
                    product_by_code.update(prior_products)
                    _LOGGER.info(
                        "AC5: Resolved %d missing product codes from prior batch lineage",
                        len(prior_products),
                    )

            # =================================================================
            # AC3: Track unknown product codes for review-required issues
            # Only mark in-scope issues as review-required.
            # =================================================================
            if is_incremental and _domain_in_selected(DOMAIN_PRODUCTS, normalized_selected):
                # Check if any product codes in scope map to UNKNOWN_PRODUCT_CODE
                scoped_product_codes = frozenset(
                    scope_closure_keys.get(DOMAIN_PRODUCTS, frozenset())
                )
                if scoped_product_codes:
                    for product_code in scoped_product_codes:
                        if product_code not in product_by_code:
                            # Product in scope but not found - this is a review-required issue
                            issue = f"unknown_product_code:{product_code}"
                            scope_review_required_issues.append(issue)

            # Story 15.26: sales_history domain
            current_step = "sales_history"
            if _domain_in_selected("sales_history", normalized_selected):
                (
                    counts["order_count"],
                    counts["order_line_count"],
                    counts["invoice_count"],
                    counts["invoice_line_count"],
                    sales_lineage_count,
                ) = await _import_sales_history(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    scoped_sales_headers,
                    scoped_sales_lines,
                    customer_by_code,
                    business_number_by_code,
                    product_by_code,
                    product_snapshot_by_code,
                    product_mappings,
                )
                counts["lineage_count"] += sales_lineage_count
                step_outcomes.append(
                    (
                        "sales_history",
                        counts["order_line_count"] + counts["invoice_line_count"],
                        "completed",
                        None,
                    )
                )
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "sales_history",
                    counts["order_line_count"] + counts["invoice_line_count"],
                    "completed",
                )
            else:
                step_outcomes.append(("sales_history", 0, "skipped", "domain not in scope"))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "sales_history",
                    0,
                    "skipped",
                )

            # =================================================================
            # AC5: Enrich supplier lookup from prior batch lineage for purchase
            # Only needed here since purchase_history requires supplier codes.
            # =================================================================
            if is_incremental and last_successful_batch_ids is not None:
                # Get supplier codes needed for scoped purchase headers
                needed_supplier_codes = frozenset(
                    _as_text(h.get("supplier_code"))
                    for h in scoped_purchase_headers
                    if _as_text(h.get("supplier_code"))
                )
                missing_supplier_codes = [
                    code for code in needed_supplier_codes
                    if code and code not in supplier_by_code
                ]
                if missing_supplier_codes:
                    prior_suppliers = await _build_prior_master_lookup(
                        connection,
                        resolved_schema,
                        tenant_id,
                        last_successful_batch_ids,
                        "supplier",
                        "tbscust",
                        missing_supplier_codes,
                    )
                    supplier_by_code.update(prior_suppliers)
                    _LOGGER.info(
                        "AC5: Resolved %d missing supplier codes from prior batch lineage",
                        len(prior_suppliers),
                    )

            # Story 15.26: purchase_history domain
            current_step = "purchase_history"
            if _domain_in_selected("purchase_history", normalized_selected):
                (
                    counts["supplier_invoice_count"],
                    counts["supplier_invoice_line_count"],
                    purchase_lineage_count,
                ) = await _import_purchase_history(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    scoped_purchase_headers,
                    scoped_purchase_lines,
                    supplier_by_code,
                    product_by_code,
                    product_mappings,
                )
                counts["lineage_count"] += purchase_lineage_count
                step_outcomes.append(
                    (
                        "purchase_history",
                        counts["supplier_invoice_count"] + counts["supplier_invoice_line_count"],
                        "completed",
                        None,
                    )
                )
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "purchase_history",
                    counts["supplier_invoice_count"] + counts["supplier_invoice_line_count"],
                    "completed",
                )
            else:
                step_outcomes.append(("purchase_history", 0, "skipped", "domain not in scope"))
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    "purchase_history",
                    0,
                    "skipped",
                )

            # Story 15.26: unsupported_history is always processed (payment-adjacent cleanup)
            current_step = "unsupported_history"
            payment_holding_count = await _hold_payment_adjacent_history(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
            )
            counts["holding_count"] += payment_holding_count
            step_outcomes.append(
                ("unsupported_history", counts["holding_count"], "completed", None)
            )
            await _upsert_step_row(
                connection,
                resolved_schema,
                run_id,
                "unsupported_history",
                counts["holding_count"],
                "completed",
            )

            await _upsert_run_row(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                attempt_number,
                "completed",
                counts,
                None,
            )
            current_step = None

        return CanonicalImportResult(
            batch_id=batch_id,
            schema_name=resolved_schema,
            attempt_number=attempt_number,
            customer_count=counts["customer_count"],
            supplier_count=counts["supplier_count"],
            product_count=counts["product_count"],
            warehouse_count=counts["warehouse_count"],
            inventory_count=counts["inventory_count"],
            order_count=counts["order_count"],
            order_line_count=counts["order_line_count"],
            invoice_count=counts["invoice_count"],
            invoice_line_count=counts["invoice_line_count"],
            supplier_invoice_count=counts["supplier_invoice_count"],
            supplier_invoice_line_count=counts["supplier_invoice_line_count"],
            holding_count=counts["holding_count"],
            lineage_count=counts["lineage_count"],
            receiving_date_fallback_count=receiving_date_fallback_count,
            # Story 15.26: Scoped incremental metadata
            selected_domains=normalized_selected,
            scoped_document_count=scoped_document_count,
            skipped_domains=skipped_domains_tuple,
            review_required_issues=tuple(scope_review_required_issues),
        )
    except Exception as exc:
        if current_step is not None:
            step_outcomes.append(
                (
                    current_step,
                    _step_row_count(current_step, counts),
                    "failed",
                    str(exc),
                )
            )
        failure_summary = dict(counts)
        async with connection.transaction():
            await _upsert_run_row(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                attempt_number,
                "failed",
                failure_summary,
                str(exc),
            )
            for step_name, row_count, status, error_message in step_outcomes:
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    step_name,
                    row_count,
                    status,
                    error_message,
                )
        raise
    finally:
        await connection.close()
