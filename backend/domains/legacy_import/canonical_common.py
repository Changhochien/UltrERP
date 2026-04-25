"""Shared canonical import helpers reused across legacy import modules."""

from __future__ import annotations

import re
import uuid
import zlib
from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Mapping, overload, cast

from domains.legacy_import import source_resolution
from domains.legacy_import.normalization import normalize_legacy_date
from domains.legacy_import.staging import _quoted_identifier

_DIGITS_ONLY_RE = re.compile(r"\D+")


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


@overload
def _as_decimal(value: object | None) -> Decimal: ...


@overload
def _as_decimal(value: object | None, default: str) -> Decimal: ...


@overload
def _as_decimal(value: object | None, default: None) -> Decimal | None: ...


def _as_decimal(value: object | None, default: str | None = "0") -> Decimal | None:
    text = _as_text(value)
    if not text:
        return Decimal(default) if default is not None else None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal value: {text}") from exc


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


def _tenant_scoped_uuid(tenant_id: uuid.UUID, kind: str, *parts: str) -> uuid.UUID:
    return uuid.uuid5(tenant_id, "::".join((kind, *parts)))


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


HOLDING_LINEAGE_TABLE = "__holding__"


def _lineage_record_query_for_holding(schema_name: str) -> str:
    """Lineage upsert query that matches on source identifiers only."""
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


async def _table_exists(connection, schema_name: str, table_name: str) -> bool:
    quoted_schema = _quoted_identifier(schema_name)
    value = await connection.fetchval(f"SELECT to_regclass('{quoted_schema}.{table_name}')")
    return bool(value)