"""Current source-row resolution state and append-only transition history."""

from __future__ import annotations

from dataclasses import dataclass
import json
import uuid
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from domains.legacy_import.normalization import deterministic_legacy_uuid
from domains.legacy_import.shared import execute_many
from domains.legacy_import.staging import _quoted_identifier

STATUS_HOLDING = "holding"
STATUS_RESOLVED = "resolved"
STATUS_FAILED = "failed"
STATUS_RETRYING = "retrying"
STATUS_REPAIRED = "repaired"
_ALLOWED_STATUSES = (
    STATUS_HOLDING,
    STATUS_RESOLVED,
    STATUS_FAILED,
    STATUS_RETRYING,
    STATUS_REPAIRED,
)


@dataclass(slots=True, frozen=True)
class ResolvedSourceRow:
    domain_name: str
    source_table: str
    source_identifier: str
    source_row_number: int
    canonical_table: str
    canonical_id: uuid.UUID
    notes: str | None = None


def build_holding_id(
    tenant_id: uuid.UUID,
    *,
    domain_name: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
    row_identity: int,
) -> uuid.UUID:
    return deterministic_legacy_uuid(
        "unsupported-history",
        str(tenant_id),
        domain_name,
        source_table,
        source_identifier,
        str(source_row_number),
        str(row_identity),
    )


async def ensure_source_resolution_tables(connection, schema_name: str) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.source_row_resolution (
			tenant_id UUID NOT NULL,
			batch_id TEXT NOT NULL,
			source_table TEXT NOT NULL,
			source_identifier TEXT NOT NULL,
			source_row_number INTEGER NOT NULL,
			domain_name TEXT NOT NULL,
			status TEXT NOT NULL,
			holding_id UUID,
			canonical_table TEXT,
			canonical_id UUID,
			notes TEXT,
			import_run_id UUID NOT NULL,
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			PRIMARY KEY (
				tenant_id,
				batch_id,
				source_table,
				source_identifier,
				source_row_number
			),
            CONSTRAINT source_row_resolution_status_check CHECK (status IN ('holding', 'resolved', 'failed', 'retrying', 'repaired'))
		)
		"""
    )
    await connection.execute(
        f"""
		CREATE TABLE IF NOT EXISTS {quoted_schema}.source_row_resolution_events (
			event_id UUID PRIMARY KEY,
			tenant_id UUID NOT NULL,
			batch_id TEXT NOT NULL,
			source_table TEXT NOT NULL,
			source_identifier TEXT NOT NULL,
			source_row_number INTEGER NOT NULL,
			domain_name TEXT NOT NULL,
			previous_status TEXT,
			new_status TEXT NOT NULL,
			holding_id UUID,
			canonical_table TEXT,
			canonical_id UUID,
			notes TEXT,
			import_run_id UUID NOT NULL,
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT source_row_resolution_events_status_check CHECK ((previous_status IS NULL OR previous_status IN ('holding', 'resolved', 'failed', 'retrying', 'repaired')) AND new_status IN ('holding', 'resolved', 'failed', 'retrying', 'repaired'))
		)
		"""
    )
    await connection.execute(
        f"""
		CREATE INDEX IF NOT EXISTS source_row_resolution_status_idx
		ON {quoted_schema}.source_row_resolution (tenant_id, batch_id, status)
		"""
    )
    await connection.execute(
        f"""
		CREATE INDEX IF NOT EXISTS source_row_resolution_events_lookup_idx
		ON {quoted_schema}.source_row_resolution_events (
			tenant_id,
			batch_id,
			source_table,
			source_identifier,
			source_row_number,
			created_at
		)
		"""
    )


def _coerce_row(row: Mapping[str, object] | object | None) -> dict[str, object]:
    if row is None:
        return {}
    if isinstance(row, Mapping):
        return {str(key): value for key, value in row.items()}
    return dict(row)


def _source_identity_key(
    source_table: str,
    source_identifier: str,
    source_row_number: int,
) -> tuple[str, str, int]:
    return (source_table, source_identifier, source_row_number)


async def _fetch_current_resolution(
    connection,
    *,
    schema_name: str,
    tenant_id: uuid.UUID,
    batch_id: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
) -> dict[str, object] | None:
    quoted_schema = _quoted_identifier(schema_name)
    row = await connection.fetchrow(
        f"""
		SELECT
			tenant_id,
			batch_id,
			source_table,
			source_identifier,
			source_row_number,
			domain_name,
			status,
			holding_id,
			canonical_table,
			canonical_id,
			notes,
			import_run_id
		FROM {quoted_schema}.source_row_resolution
		WHERE tenant_id = $1
			AND batch_id = $2
			AND source_table = $3
			AND source_identifier = $4
			AND source_row_number = $5
		""",
        tenant_id,
        batch_id,
        source_table,
        source_identifier,
        source_row_number,
    )
    if row is None:
        return None
    return _coerce_row(row)


async def _fetch_current_resolutions(
    connection,
    *,
    schema_name: str,
    tenant_id: uuid.UUID,
    batch_id: str,
    rows: list[ResolvedSourceRow],
) -> dict[tuple[str, str, int], dict[str, object]]:
    if not rows:
        return {}

    quoted_schema = _quoted_identifier(schema_name)
    fetched_rows = await connection.fetch(
        f"""
		SELECT
			resolution.tenant_id,
			resolution.batch_id,
			resolution.source_table,
			resolution.source_identifier,
			resolution.source_row_number,
			resolution.domain_name,
			resolution.status,
			resolution.holding_id,
			resolution.canonical_table,
			resolution.canonical_id,
			resolution.notes,
			resolution.import_run_id
		FROM {quoted_schema}.source_row_resolution AS resolution
		JOIN UNNEST($3::TEXT[], $4::TEXT[], $5::INTEGER[]) AS identities (
			source_table,
			source_identifier,
			source_row_number
		)
			ON resolution.source_table = identities.source_table
			AND resolution.source_identifier = identities.source_identifier
			AND resolution.source_row_number = identities.source_row_number
		WHERE resolution.tenant_id = $1
			AND resolution.batch_id = $2
		""",
        tenant_id,
        batch_id,
        [row.source_table for row in rows],
        [row.source_identifier for row in rows],
        [row.source_row_number for row in rows],
    )
    return {
        _source_identity_key(
            str(payload.get("source_table") or ""),
            str(payload.get("source_identifier") or ""),
            int(payload.get("source_row_number") or 0),
        ): payload
        for payload in (_coerce_row(row) for row in fetched_rows)
    }


def _current_resolution_query(schema_name: str) -> str:
    quoted_schema = _quoted_identifier(schema_name)
    return f"""
		INSERT INTO {quoted_schema}.source_row_resolution (
			tenant_id,
			batch_id,
			source_table,
			source_identifier,
			source_row_number,
			domain_name,
			status,
			holding_id,
			canonical_table,
			canonical_id,
			notes,
			import_run_id,
			updated_at
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
		ON CONFLICT (
			tenant_id,
			batch_id,
			source_table,
			source_identifier,
			source_row_number
		)
		DO UPDATE SET
			domain_name = EXCLUDED.domain_name,
			status = EXCLUDED.status,
			holding_id = EXCLUDED.holding_id,
			canonical_table = EXCLUDED.canonical_table,
			canonical_id = EXCLUDED.canonical_id,
			notes = EXCLUDED.notes,
			import_run_id = EXCLUDED.import_run_id,
			updated_at = NOW()
		"""


def _current_resolution_args(
    *,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
    domain_name: str,
    status: str,
    holding_id: uuid.UUID | None,
    canonical_table: str | None,
    canonical_id: uuid.UUID | None,
    notes: str | None,
) -> tuple[object, ...]:
    return (
        tenant_id,
        batch_id,
        source_table,
        source_identifier,
        source_row_number,
        domain_name,
        status,
        holding_id,
        canonical_table,
        canonical_id,
        notes,
        run_id,
    )


def _resolution_event_query(schema_name: str) -> str:
    quoted_schema = _quoted_identifier(schema_name)
    return f"""
		INSERT INTO {quoted_schema}.source_row_resolution_events (
			event_id,
			tenant_id,
			batch_id,
			source_table,
			source_identifier,
			source_row_number,
			domain_name,
			previous_status,
			new_status,
			holding_id,
			canonical_table,
			canonical_id,
			notes,
			import_run_id
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
		"""


def _resolution_event_args(
    *,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
    domain_name: str,
    previous_status: str | None,
    new_status: str,
    holding_id: uuid.UUID | None,
    canonical_table: str | None,
    canonical_id: uuid.UUID | None,
    notes: str | None,
) -> tuple[object, ...]:
    return (
        uuid.uuid4(),
        tenant_id,
        batch_id,
        source_table,
        source_identifier,
        source_row_number,
        domain_name,
        previous_status,
        new_status,
        holding_id,
        canonical_table,
        canonical_id,
        notes,
        run_id,
    )


def _delete_holding_payload_query(schema_name: str) -> str:
    quoted_schema = _quoted_identifier(schema_name)
    return f"""
		DELETE FROM {quoted_schema}.unsupported_history_holding
		WHERE tenant_id = $1
			AND batch_id = $2
			AND source_table = $3
			AND source_identifier = $4
			AND source_row_number = $5
		"""


def _delete_holding_payload_args(
    *,
    tenant_id: uuid.UUID,
    batch_id: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
) -> tuple[object, ...]:
    return (
        tenant_id,
        batch_id,
        source_table,
        source_identifier,
        source_row_number,
    )


def _state_matches(
    existing: Mapping[str, object] | None,
    *,
    domain_name: str,
    status: str,
    holding_id: uuid.UUID | None,
    canonical_table: str | None,
    canonical_id: uuid.UUID | None,
    notes: str | None,
) -> bool:
    if existing is None:
        return False
    return (
        existing.get("domain_name") == domain_name
        and existing.get("status") == status
        and existing.get("holding_id") == holding_id
        and existing.get("canonical_table") == canonical_table
        and existing.get("canonical_id") == canonical_id
        and existing.get("notes") == notes
    )


async def _upsert_current_resolution(
    connection,
    *,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
    domain_name: str,
    status: str,
    holding_id: uuid.UUID | None,
    canonical_table: str | None,
    canonical_id: uuid.UUID | None,
    notes: str | None,
) -> None:
    await connection.execute(
        _current_resolution_query(schema_name),
        *_current_resolution_args(
            run_id=run_id,
            tenant_id=tenant_id,
            batch_id=batch_id,
            source_table=source_table,
            source_identifier=source_identifier,
            source_row_number=source_row_number,
            domain_name=domain_name,
            status=status,
            holding_id=holding_id,
            canonical_table=canonical_table,
            canonical_id=canonical_id,
            notes=notes,
        ),
    )


async def _append_resolution_event(
    connection,
    *,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
    domain_name: str,
    previous_status: str | None,
    new_status: str,
    holding_id: uuid.UUID | None,
    canonical_table: str | None,
    canonical_id: uuid.UUID | None,
    notes: str | None,
) -> None:
    await connection.execute(
        _resolution_event_query(schema_name),
        *_resolution_event_args(
            run_id=run_id,
            tenant_id=tenant_id,
            batch_id=batch_id,
            source_table=source_table,
            source_identifier=source_identifier,
            source_row_number=source_row_number,
            domain_name=domain_name,
            previous_status=previous_status,
            new_status=new_status,
            holding_id=holding_id,
            canonical_table=canonical_table,
            canonical_id=canonical_id,
            notes=notes,
        ),
    )


async def _upsert_holding_payload(
    connection,
    *,
    schema_name: str,
    run_id: uuid.UUID,
    holding_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    domain_name: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
    payload: dict[str, object],
    notes: str,
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    await connection.execute(
        f"""
		INSERT INTO {quoted_schema}.unsupported_history_holding (
			id,
			tenant_id,
			batch_id,
			domain_name,
			source_table,
			source_identifier,
			source_row_number,
			payload,
			notes,
			import_run_id,
			updated_at
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, NOW())
		ON CONFLICT (
			tenant_id,
			batch_id,
			source_table,
			source_identifier,
			source_row_number
		) DO UPDATE SET
			domain_name = EXCLUDED.domain_name,
			payload = EXCLUDED.payload,
			notes = EXCLUDED.notes,
			import_run_id = EXCLUDED.import_run_id,
			updated_at = NOW()
		""",
        holding_id,
        tenant_id,
        batch_id,
        domain_name,
        source_table,
        source_identifier,
        source_row_number,
        json.dumps(payload),
        notes,
        run_id,
    )


async def _delete_holding_payload(
    connection,
    *,
    schema_name: str,
    tenant_id: uuid.UUID,
    batch_id: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
) -> None:
    await connection.execute(
        _delete_holding_payload_query(schema_name),
        *_delete_holding_payload_args(
            tenant_id=tenant_id,
            batch_id=batch_id,
            source_table=source_table,
            source_identifier=source_identifier,
            source_row_number=source_row_number,
        ),
    )


async def hold_source_row(
    connection,
    *,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    domain_name: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
    row_identity: int,
    holding_id: uuid.UUID,
    payload: dict[str, object],
    notes: str,
) -> uuid.UUID:
    await _upsert_holding_payload(
        connection,
        schema_name=schema_name,
        run_id=run_id,
        holding_id=holding_id,
        tenant_id=tenant_id,
        batch_id=batch_id,
        domain_name=domain_name,
        source_table=source_table,
        source_identifier=source_identifier,
        source_row_number=source_row_number,
        payload=payload,
        notes=notes,
    )

    existing = await _fetch_current_resolution(
        connection,
        schema_name=schema_name,
        tenant_id=tenant_id,
        batch_id=batch_id,
        source_table=source_table,
        source_identifier=source_identifier,
        source_row_number=source_row_number,
    )
    if _state_matches(
        existing,
        domain_name=domain_name,
        status=STATUS_HOLDING,
        holding_id=holding_id,
        canonical_table=None,
        canonical_id=None,
        notes=notes,
    ):
        return holding_id

    await _upsert_current_resolution(
        connection,
        schema_name=schema_name,
        run_id=run_id,
        tenant_id=tenant_id,
        batch_id=batch_id,
        source_table=source_table,
        source_identifier=source_identifier,
        source_row_number=source_row_number,
        domain_name=domain_name,
        status=STATUS_HOLDING,
        holding_id=holding_id,
        canonical_table=None,
        canonical_id=None,
        notes=notes,
    )
    await _append_resolution_event(
        connection,
        schema_name=schema_name,
        run_id=run_id,
        tenant_id=tenant_id,
        batch_id=batch_id,
        source_table=source_table,
        source_identifier=source_identifier,
        source_row_number=source_row_number,
        domain_name=domain_name,
        previous_status=existing.get("status") if existing else None,
        new_status=STATUS_HOLDING,
        holding_id=holding_id,
        canonical_table=None,
        canonical_id=None,
        notes=notes,
    )
    return holding_id


async def resolve_source_row(
    connection,
    *,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    domain_name: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
    canonical_table: str,
    canonical_id: uuid.UUID,
    notes: str | None,
    canonical_write: Callable[[], Awaitable[None]] | None = None,
) -> None:
    existing = await _fetch_current_resolution(
        connection,
        schema_name=schema_name,
        tenant_id=tenant_id,
        batch_id=batch_id,
        source_table=source_table,
        source_identifier=source_identifier,
        source_row_number=source_row_number,
    )

    if canonical_write is not None:
        await canonical_write()

    if _state_matches(
        existing,
        domain_name=domain_name,
        status=STATUS_RESOLVED,
        holding_id=None,
        canonical_table=canonical_table,
        canonical_id=canonical_id,
        notes=notes,
    ) and existing.get("holding_id") is None:
        return

    if existing is not None and existing.get("holding_id") is not None:
        await _delete_holding_payload(
            connection,
            schema_name=schema_name,
            tenant_id=tenant_id,
            batch_id=batch_id,
            source_table=source_table,
            source_identifier=source_identifier,
            source_row_number=source_row_number,
        )

    await _upsert_current_resolution(
        connection,
        schema_name=schema_name,
        run_id=run_id,
        tenant_id=tenant_id,
        batch_id=batch_id,
        source_table=source_table,
        source_identifier=source_identifier,
        source_row_number=source_row_number,
        domain_name=domain_name,
        status=STATUS_RESOLVED,
        holding_id=None,
        canonical_table=canonical_table,
        canonical_id=canonical_id,
        notes=notes,
    )
    await _append_resolution_event(
        connection,
        schema_name=schema_name,
        run_id=run_id,
        tenant_id=tenant_id,
        batch_id=batch_id,
        source_table=source_table,
        source_identifier=source_identifier,
        source_row_number=source_row_number,
        domain_name=domain_name,
        previous_status=existing.get("status") if existing else None,
        new_status=STATUS_RESOLVED,
        holding_id=None,
        canonical_table=canonical_table,
        canonical_id=canonical_id,
        notes=notes,
    )


async def resolve_source_rows(
    connection,
    *,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    rows: list[ResolvedSourceRow],
) -> None:
    if not rows:
        return

    existing_rows = await _fetch_current_resolutions(
        connection,
        schema_name=schema_name,
        tenant_id=tenant_id,
        batch_id=batch_id,
        rows=rows,
    )

    delete_rows: list[tuple[object, ...]] = []
    current_rows: list[tuple[object, ...]] = []
    event_rows: list[tuple[object, ...]] = []

    for row in rows:
        existing = existing_rows.get(
            _source_identity_key(
                row.source_table,
                row.source_identifier,
                row.source_row_number,
            )
        )
        if _state_matches(
            existing,
            domain_name=row.domain_name,
            status=STATUS_RESOLVED,
            holding_id=None,
            canonical_table=row.canonical_table,
            canonical_id=row.canonical_id,
            notes=row.notes,
        ) and existing.get("holding_id") is None:
            continue

        if existing is not None and existing.get("holding_id") is not None:
            delete_rows.append(
                _delete_holding_payload_args(
                    tenant_id=tenant_id,
                    batch_id=batch_id,
                    source_table=row.source_table,
                    source_identifier=row.source_identifier,
                    source_row_number=row.source_row_number,
                )
            )

        current_rows.append(
            _current_resolution_args(
                run_id=run_id,
                tenant_id=tenant_id,
                batch_id=batch_id,
                source_table=row.source_table,
                source_identifier=row.source_identifier,
                source_row_number=row.source_row_number,
                domain_name=row.domain_name,
                status=STATUS_RESOLVED,
                holding_id=None,
                canonical_table=row.canonical_table,
                canonical_id=row.canonical_id,
                notes=row.notes,
            )
        )
        event_rows.append(
            _resolution_event_args(
                run_id=run_id,
                tenant_id=tenant_id,
                batch_id=batch_id,
                source_table=row.source_table,
                source_identifier=row.source_identifier,
                source_row_number=row.source_row_number,
                domain_name=row.domain_name,
                previous_status=str(existing.get("status")) if existing else None,
                new_status=STATUS_RESOLVED,
                holding_id=None,
                canonical_table=row.canonical_table,
                canonical_id=row.canonical_id,
                notes=row.notes,
            )
        )

    await execute_many(
        connection,
        _delete_holding_payload_query(schema_name),
        delete_rows,
    )
    await execute_many(
        connection,
        _current_resolution_query(schema_name),
        current_rows,
    )
    await execute_many(
        connection,
        _resolution_event_query(schema_name),
        event_rows,
    )