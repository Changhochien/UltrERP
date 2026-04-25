"""Canonical import persistence helpers for run tracking and lineage state."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass

from domains.legacy_import import source_resolution
from domains.legacy_import.canonical_common import (
    HOLDING_LINEAGE_TABLE,
    _lineage_record_query_for_holding,
)
from domains.legacy_import.shared import execute_many
from domains.legacy_import.staging import _quoted_identifier

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class PendingLineageResolution:
    canonical_table: str
    canonical_id: uuid.UUID
    source_table: str
    source_identifier: str
    source_row_number: int
    domain_name: str | None = None
    resolution_notes: str | None = None


async def _next_attempt_number(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id: uuid.UUID,
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
    """Insert or update a lineage record for a holding-path row."""
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
    """Insert holding payload and lineage entry in one savepoint."""
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