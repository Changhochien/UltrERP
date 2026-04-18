"""Import verified AP payment history into canonical supplier payment tables."""

from __future__ import annotations

import json
import uuid
import zlib
from dataclasses import dataclass

from common.config import settings
from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import import source_resolution
from domains.legacy_import.canonical import (
    _as_decimal,
    _as_int,
    _as_legacy_date,
    _as_money,
    _as_text,
    _coerce_row,
    _currency_code,
    _ensure_canonical_support_tables,
    _table_exists,
    _tenant_scoped_uuid,
    _upsert_lineage_record,
)
from domains.legacy_import.shared import resolve_row_identity as _resolve_row_identity
from domains.legacy_import.staging import _open_raw_connection, _quoted_identifier

_TABLE_NAMES = ("tbsprepay", "tbsspay")
_TARGET_SCHEMA = "public"
_ROLE_BY_LEGACY_TYPE = {
    "1": "supplier",
    "2": "customer",
}
_TBSPREPAY_AMOUNT_COLUMNS = {
    "col_7": "fprepay",
    "col_8": "fcxowe",
    "col_10": "fdiscount",
    "col_11": "fcomprepay",
    "col_12": "fcomcxowe",
    "col_13": "fcomdiscount",
}


@dataclass(slots=True, frozen=True)
class SupplierPaymentImportResult:
    batch_id: str
    schema_name: str
    attempt_number: int
    payment_count: int
    allocation_count: int
    holding_count: int
    lineage_count: int


def _source_identifier(table_name: str, row: dict[str, object]) -> str:
    return _as_text(row.get("col_2")) or f"{table_name}:{_as_int(row.get('_source_row_number'))}"


def _stage_column_count(row: dict[str, object]) -> int:
    indices = [
        int(key[4:])
        for key in row
        if key.startswith("col_") and key[4:].isdigit()
    ]
    return max(indices, default=0)


def _join_reasons(*parts: str) -> str:
    return "; ".join(part for part in parts if part)


def _party_role(value: object | None) -> str | None:
    raw = _as_text(value)
    return _ROLE_BY_LEGACY_TYPE.get(raw)


def _special_payment_method(row: dict[str, object]) -> str | None:
    method_code = _as_text(row.get("col_3"))
    return None if method_code in {"", "0"} else method_code


def _special_payment_reference(row: dict[str, object]) -> str | None:
    return _as_text(row.get("col_12")) or None


def _special_payment_notes(row: dict[str, object]) -> str | None:
    return _as_text(row.get("col_18")) or None


def _tbsprepay_positive_amounts(row: dict[str, object]) -> list[str]:
    positive_fields: list[str] = []
    for column_name, field_name in _TBSPREPAY_AMOUNT_COLUMNS.items():
        if _as_decimal(row.get(column_name), "0") > 0:
            positive_fields.append(field_name)
    return positive_fields


def _tbsspay_hold_reason(
    row: dict[str, object],
    *,
    party_role: str | None,
    supplier_exists: bool,
) -> str | None:
    payment_number = _as_text(row.get("col_2"))
    party_code = _as_text(row.get("col_6"))
    payment_date = _as_legacy_date(row.get("col_4"))
    gross_amount = _as_money(_as_decimal(row.get("col_10"), "0.00"))

    reasons: list[str] = []
    if not payment_number:
        reasons.append("missing legacy payment number")
    if not party_code:
        reasons.append("missing counterparty code")
    elif party_role is None:
        reasons.append("counterparty is not staged in tbscust")
    elif party_role != "supplier":
        reasons.append(f"counterparty resolves to {party_role} role, not supplier")
    if payment_date is None:
        reasons.append("missing verified payment date")
    if gross_amount <= 0:
        reasons.append("missing positive payment amount")
    if party_role == "supplier" and not supplier_exists:
        reasons.append("supplier is not present in canonical supplier master")

    if not reasons:
        return None
    return _join_reasons(*reasons)


def _tbsprepay_hold_reason(
    row: dict[str, object],
    *,
    party_role: str | None,
) -> str:
    party_code = _as_text(row.get("col_2"))
    positive_amounts = _tbsprepay_positive_amounts(row)

    reasons: list[str] = []
    if not party_code:
        reasons.append("missing counterparty code")
    elif party_role is None:
        reasons.append("counterparty is not staged in tbscust")
    elif party_role != "supplier":
        reasons.append(f"counterparty resolves to {party_role} role, not supplier")
    reasons.append("tbsprepay has no verified payment document number")
    reasons.append("tbsprepay has no verified payment date")
    if positive_amounts:
        reasons.append(
            "tbsprepay amount fields need verified AP semantics before import "
            f"({', '.join(positive_amounts)})"
        )
    else:
        reasons.append("all candidate prepayment amount fields are zero")
    return _join_reasons(*reasons)


def _pg_lock_key(value: str) -> int:
    lock_key = zlib.crc32(value.encode("utf-8"))
    if lock_key >= 2**31:
        lock_key -= 2**32
    return lock_key


async def _lock_attempt_allocation(connection, tenant_id: uuid.UUID, batch_id: str) -> None:
    await connection.execute(
        "SELECT pg_advisory_xact_lock($1::integer, $2::integer)",
        _pg_lock_key("ap-payment-import"),
        _pg_lock_key(f"{tenant_id}:{batch_id}"),
    )


async def _next_attempt_number(connection, tenant_id: uuid.UUID, batch_id: str) -> int:
    latest_attempt = await connection.fetchval(
        """
		SELECT COALESCE(MAX(attempt_number), 0)
		FROM legacy_import_runs
		WHERE tenant_id = $1 AND batch_id = $2
		""",
        tenant_id,
        batch_id,
    )
    return int(latest_attempt or 0) + 1


async def _upsert_run_row(
    connection,
    *,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    source_path: str,
    attempt_number: int,
    requested_tables: list[str],
    status: str,
    error_message: str | None,
) -> None:
    await connection.execute(
        """
		INSERT INTO legacy_import_runs (
			id,
			tenant_id,
			batch_id,
			source_path,
			target_schema,
			attempt_number,
			requested_tables,
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
			$6,
			$7::jsonb,
            $8::text,
			$9,
			NOW(),
			CASE
                WHEN $8::text = 'completed' OR $8::text = 'failed' THEN NOW()
				ELSE NULL
			END
		)
		ON CONFLICT (tenant_id, batch_id, attempt_number) DO UPDATE SET
			source_path = EXCLUDED.source_path,
			target_schema = EXCLUDED.target_schema,
			requested_tables = EXCLUDED.requested_tables,
			status = EXCLUDED.status,
			error_message = EXCLUDED.error_message,
			completed_at = EXCLUDED.completed_at
		""",
        run_id,
        tenant_id,
        batch_id,
        source_path,
        _TARGET_SCHEMA,
        attempt_number,
        json.dumps(requested_tables),
        status,
        error_message,
    )


async def _upsert_table_run_row(
    connection,
    *,
    run_id: uuid.UUID,
    table_name: str,
    source_file: str,
    expected_row_count: int,
    loaded_row_count: int,
    column_count: int,
    status: str,
    error_message: str | None,
) -> None:
    await connection.execute(
        """
		INSERT INTO legacy_import_table_runs (
            id,
			run_id,
			table_name,
			source_file,
			expected_row_count,
			loaded_row_count,
			column_count,
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
			$6,
            $7,
            $8::text,
            $9,
			NOW(),
			CASE
                WHEN $8::text = 'completed' OR $8::text = 'failed' THEN NOW()
				ELSE NULL
			END
		)
		ON CONFLICT (run_id, table_name) DO UPDATE SET
			source_file = EXCLUDED.source_file,
			expected_row_count = EXCLUDED.expected_row_count,
			loaded_row_count = EXCLUDED.loaded_row_count,
			column_count = EXCLUDED.column_count,
			status = EXCLUDED.status,
			error_message = EXCLUDED.error_message,
			completed_at = EXCLUDED.completed_at
		""",
        uuid.uuid4(),
        run_id,
        table_name,
        source_file,
        expected_row_count,
        loaded_row_count,
        column_count,
        status,
        error_message,
    )


async def _fetch_party_roles(connection, schema_name: str, batch_id: str) -> dict[str, str]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT col_1 AS legacy_code, col_2 AS legacy_type
		FROM {quoted_schema}.tbscust
		WHERE _batch_id = $1
		""",
        batch_id,
    )
    role_by_code: dict[str, str] = {}
    for row in rows:
        payload = _coerce_row(row)
        legacy_code = _as_text(payload.get("legacy_code"))
        if not legacy_code:
            continue
        role = _party_role(payload.get("legacy_type"))
        if role:
            role_by_code[legacy_code] = role
    return role_by_code


async def _fetch_existing_supplier_ids(
    connection,
    *,
    tenant_id: uuid.UUID,
    supplier_ids: set[uuid.UUID],
) -> set[uuid.UUID]:
    if not supplier_ids:
        return set()

    rows = await connection.fetch(
        """
		SELECT id
		FROM supplier
		WHERE tenant_id = $1 AND id = ANY($2::uuid[])
		""",
        tenant_id,
        list(supplier_ids),
    )
    return {uuid.UUID(str(_coerce_row(row).get("id"))) for row in rows}


async def _fetch_staged_rows(
    connection,
    *,
    schema_name: str,
    table_name: str,
    batch_id: str,
) -> list[dict[str, object]]:
    quoted_schema = _quoted_identifier(schema_name)
    rows = await connection.fetch(
        f"""
		SELECT *
		FROM {quoted_schema}.{table_name}
		WHERE _batch_id = $1
		ORDER BY _source_row_number
		""",
        batch_id,
    )
    return [_coerce_row(row) for row in rows]


async def _upsert_supplier_payment(
    connection,
    *,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    raw_row: dict[str, object],
    supplier_id: uuid.UUID,
) -> tuple[int, int]:
    payment_number = _as_text(raw_row.get("col_2"))
    source_row_number = _as_int(raw_row.get("_source_row_number"))
    source_identifier = _source_identifier("tbsspay", raw_row)
    payment_id = _tenant_scoped_uuid(
        tenant_id,
        "supplier-payment",
        "tbsspay",
        source_identifier,
    )

    async def write_supplier_payment() -> None:
        await connection.execute(
            """
            INSERT INTO supplier_payments (
                id,
                tenant_id,
                supplier_id,
                payment_number,
                payment_kind,
                status,
                currency_code,
                payment_date,
                gross_amount,
                payment_method,
                reference_number,
                notes,
                created_at,
                updated_at
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
                NOW(),
                NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                supplier_id = EXCLUDED.supplier_id,
                payment_number = EXCLUDED.payment_number,
                payment_kind = EXCLUDED.payment_kind,
                status = EXCLUDED.status,
                currency_code = EXCLUDED.currency_code,
                payment_date = EXCLUDED.payment_date,
                gross_amount = EXCLUDED.gross_amount,
                payment_method = EXCLUDED.payment_method,
                reference_number = EXCLUDED.reference_number,
                notes = EXCLUDED.notes,
                updated_at = NOW()
            """,
            payment_id,
            tenant_id,
            supplier_id,
            payment_number,
            "special_payment",
            "unapplied",
            _currency_code(raw_row.get("col_8")),
            _as_legacy_date(raw_row.get("col_4")),
            _as_money(_as_decimal(raw_row.get("col_10"), "0.00")),
            _special_payment_method(raw_row),
            _special_payment_reference(raw_row),
            _special_payment_notes(raw_row),
        )
        await _upsert_lineage_record(
            connection,
            schema_name,
            run_id,
            tenant_id,
            batch_id,
            "supplier_payments",
            payment_id,
            "tbsspay",
            source_identifier,
            source_row_number,
        )

    await source_resolution.resolve_source_row(
        connection,
        schema_name=schema_name,
        run_id=run_id,
        tenant_id=tenant_id,
        batch_id=batch_id,
        domain_name="payment_history",
        source_table="tbsspay",
        source_identifier=source_identifier,
        source_row_number=source_row_number,
        canonical_table="supplier_payments",
        canonical_id=payment_id,
        notes="drained to canonical supplier payment",
        canonical_write=write_supplier_payment,
    )
    return 1, 1


async def run_ap_payment_import(
    *,
    batch_id: str,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str | None = None,
) -> SupplierPaymentImportResult:
    resolved_schema = schema_name or settings.legacy_import_schema
    connection = await _open_raw_connection()
    run_id = uuid.uuid4()
    attempt_number = 1
    available_tables: list[str] = []
    table_rows_by_name: dict[str, list[dict[str, object]]] = {}

    try:
        if not await _table_exists(connection, resolved_schema, "tbscust"):
            raise ValueError("tbscust must be staged before ap-payment-import")

        for table_name in _TABLE_NAMES:
            if await _table_exists(connection, resolved_schema, table_name):
                available_tables.append(table_name)

        if not available_tables:
            raise ValueError("No staged payment tables found for ap-payment-import")

        async with connection.transaction():
            await _ensure_canonical_support_tables(connection, resolved_schema)

            await _lock_attempt_allocation(connection, tenant_id, batch_id)
            attempt_number = await _next_attempt_number(connection, tenant_id, batch_id)
            await _upsert_run_row(
                connection,
                run_id=run_id,
                tenant_id=tenant_id,
                batch_id=batch_id,
                source_path=resolved_schema,
                attempt_number=attempt_number,
                requested_tables=available_tables,
                status="running",
                error_message=None,
            )

            party_roles = await _fetch_party_roles(connection, resolved_schema, batch_id)

            for table_name in available_tables:
                table_rows_by_name[table_name] = await _fetch_staged_rows(
                    connection,
                    schema_name=resolved_schema,
                    table_name=table_name,
                    batch_id=batch_id,
                )

            supplier_candidate_ids = {
                _tenant_scoped_uuid(tenant_id, "party", "supplier", code)
                for code, role in party_roles.items()
                if role == "supplier"
            }
            existing_supplier_ids = await _fetch_existing_supplier_ids(
                connection,
                tenant_id=tenant_id,
                supplier_ids=supplier_candidate_ids,
            )

            payment_count = 0
            allocation_count = 0
            holding_count = 0
            lineage_count = 0

            for table_name in available_tables:
                rows = table_rows_by_name[table_name]
                processed_count = 0
                column_count = 0

                for raw_row in rows:
                    processed_count += 1
                    column_count = max(column_count, _stage_column_count(raw_row))
                    source_identifier = _source_identifier(table_name, raw_row)
                    source_row_number = _as_int(raw_row.get("_source_row_number"))
                    row_identity = _resolve_row_identity(source_row_number, processed_count)

                    if table_name == "tbsspay":
                        party_code = _as_text(raw_row.get("col_6"))
                        party_role = party_roles.get(party_code)
                        supplier_id = (
                            _tenant_scoped_uuid(tenant_id, "party", "supplier", party_code)
                            if party_role == "supplier" and party_code
                            else None
                        )
                        hold_reason = _tbsspay_hold_reason(
                            raw_row,
                            party_role=party_role,
                            supplier_exists=supplier_id in existing_supplier_ids,
                        )

                        if hold_reason is None and supplier_id is not None:
                            imported_payments, imported_lineage = await _upsert_supplier_payment(
                                connection,
                                schema_name=resolved_schema,
                                run_id=run_id,
                                tenant_id=tenant_id,
                                batch_id=batch_id,
                                raw_row=raw_row,
                                supplier_id=supplier_id,
                            )
                            payment_count += imported_payments
                            lineage_count += imported_lineage
                            continue

                        await source_resolution.hold_source_row(
                            connection,
                            schema_name=resolved_schema,
                            run_id=run_id,
                            tenant_id=tenant_id,
                            batch_id=batch_id,
                            domain_name="payment_history",
                            source_table=table_name,
                            source_identifier=source_identifier,
                            source_row_number=source_row_number,
                            row_identity=row_identity,
                            holding_id=source_resolution.build_holding_id(
                                tenant_id,
                                domain_name="payment_history",
                                source_table=table_name,
                                source_identifier=source_identifier,
                                source_row_number=source_row_number,
                                row_identity=row_identity,
                            ),
                            payload=raw_row,
                            notes=hold_reason or "tbsspay row could not be verified for AP import",
                        )
                        holding_count += 1
                        continue

                    party_code = _as_text(raw_row.get("col_2"))
                    party_role = party_roles.get(party_code)
                    await source_resolution.hold_source_row(
                        connection,
                        schema_name=resolved_schema,
                        run_id=run_id,
                        tenant_id=tenant_id,
                        batch_id=batch_id,
                        domain_name="payment_history",
                        source_table=table_name,
                        source_identifier=source_identifier,
                        source_row_number=source_row_number,
                        row_identity=row_identity,
                        holding_id=source_resolution.build_holding_id(
                            tenant_id,
                            domain_name="payment_history",
                            source_table=table_name,
                            source_identifier=source_identifier,
                            source_row_number=source_row_number,
                            row_identity=row_identity,
                        ),
                        payload=raw_row,
                        notes=_tbsprepay_hold_reason(raw_row, party_role=party_role),
                    )
                    holding_count += 1

                await _upsert_table_run_row(
                    connection,
                    run_id=run_id,
                    table_name=table_name,
                    source_file=f"{resolved_schema}.{table_name}",
                    expected_row_count=len(rows),
                    loaded_row_count=processed_count,
                    column_count=column_count,
                    status="completed",
                    error_message=None,
                )

            await _upsert_run_row(
                connection,
                run_id=run_id,
                tenant_id=tenant_id,
                batch_id=batch_id,
                source_path=resolved_schema,
                attempt_number=attempt_number,
                requested_tables=available_tables,
                status="completed",
                error_message=None,
            )

        return SupplierPaymentImportResult(
            batch_id=batch_id,
            schema_name=resolved_schema,
            attempt_number=attempt_number,
            payment_count=payment_count,
            allocation_count=allocation_count,
            holding_count=holding_count,
            lineage_count=lineage_count,
        )
    except Exception as exc:
        async with connection.transaction():
            await _ensure_canonical_support_tables(connection, resolved_schema)
            await _upsert_run_row(
                connection,
                run_id=run_id,
                tenant_id=tenant_id,
                batch_id=batch_id,
                source_path=resolved_schema,
                attempt_number=attempt_number,
                requested_tables=available_tables,
                status="failed",
                error_message=str(exc),
            )
            for table_name, rows in table_rows_by_name.items():
                column_count = max((_stage_column_count(row) for row in rows), default=0)
                await _upsert_table_run_row(
                    connection,
                    run_id=run_id,
                    table_name=table_name,
                    source_file=f"{resolved_schema}.{table_name}",
                    expected_row_count=len(rows),
                    loaded_row_count=0,
                    column_count=column_count,
                    status="failed",
                    error_message=str(exc),
                )
        raise
    finally:
        await connection.close()
