"""Legacy raw-staging import helpers and orchestration."""

from __future__ import annotations

import csv
import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import asyncpg
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.database import AsyncSessionLocal
from common.models.legacy_import import LegacyImportRun, LegacyImportTableRun
from common.tenant import DEFAULT_TENANT_ID

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_MANIFEST_ROW_RE = re.compile(r"^\|\s*([a-z0-9_]+)\s*\|\s*([0-9,]+)\s*\|")
_NUMERIC_LITERAL_RE = re.compile(r"^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?$")
_STAGE_COPY_BATCH_SIZE = 25_000


@dataclass(slots=True, frozen=True)
class DiscoveredLegacyTable:
    table_name: str
    csv_path: Path
    expected_row_count: int | None = None


@dataclass(slots=True, frozen=True)
class StageTableResult:
    table_name: str
    row_count: int
    column_count: int
    source_file: str
    validation_message: str | None = None


@dataclass(slots=True, frozen=True)
class StageBatchResult:
    batch_id: str
    schema_name: str
    source_dir: Path
    tables: tuple[StageTableResult, ...]


@dataclass(slots=True)
class AttemptTableAudit:
    table_name: str
    source_file: str
    expected_row_count: int | None
    loaded_row_count: int = 0
    column_count: int = 0
    status: str = "running"
    error_message: str | None = None


class RawStageConnection(Protocol):
    async def execute(self, query: str) -> str: ...

    async def fetch(self, query: str, *args: object): ...

    async def fetchval(self, query: str, *args: object): ...

    async def copy_records_to_table(
        self,
        table_name: str,
        *,
        schema_name: str | None = None,
        columns: list[str] | tuple[str, ...] | None = None,
        records: object,
        timeout: float | None = None,
    ) -> str: ...


def _split_legacy_tokens(line: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    in_quote = False
    index = 0
    while index < len(line):
        char = line[index]
        if char == "'":
            current.append(char)
            if in_quote and index + 1 < len(line) and line[index + 1] == "'":
                current.append("'")
                index += 2
                continue
            in_quote = not in_quote
            index += 1
            continue
        if char == "," and not in_quote:
            tokens.append("".join(current).strip())
            current = []
            index += 1
            continue
        current.append(char)
        index += 1

    if in_quote:
        raise ValueError(f"Malformed legacy row: {line}")

    tokens.append("".join(current).strip())
    return tokens


def _is_valid_legacy_token(token: str) -> bool:
    if token == "" or token.upper() == "NULL":
        return True
    if token.startswith("'") and token.endswith("'"):
        return True
    return _NUMERIC_LITERAL_RE.fullmatch(token) is not None


def parse_legacy_row(raw_line: str) -> list[str]:
    """Parse the legacy export row format into individual text fields."""

    line = raw_line.strip()
    if not line:
        return []

    if line.startswith('"') and line.endswith('"'):
        line = line[1:-1]
    line = line.replace('\\"', '"')
    if not line:
        return []

    try:
        row = next(
            csv.reader(
                [line],
                delimiter=",",
                quotechar="'",
                skipinitialspace=True,
                strict=True,
            )
        )
    except (csv.Error, StopIteration) as exc:
        raise ValueError(f"Malformed legacy row: {raw_line.strip()}") from exc

    tokens = _split_legacy_tokens(line)
    if len(tokens) != len(row) or any(not _is_valid_legacy_token(token) for token in tokens):
        raise ValueError(f"Malformed legacy row: {raw_line.strip()}")

    return [field.strip() for field in row]


def iter_legacy_rows(csv_path: Path):
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        for row_number, raw_line in enumerate(handle, start=1):
            try:
                row = parse_legacy_row(raw_line)
            except ValueError as exc:
                raise ValueError(
                    f"Malformed legacy row in {csv_path.name} at line {row_number}: {exc}"
                ) from exc
            if row:
                yield row


def parse_manifest_rows(manifest_path: Path) -> dict[str, int]:
    if not manifest_path.exists():
        return {}

    counts: dict[str, int] = {}
    for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
        match = _MANIFEST_ROW_RE.match(raw_line.strip())
        if not match:
            continue
        counts[match.group(1)] = int(match.group(2).replace(",", ""))
    return counts


def _dedupe_table_names(table_names: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    return tuple(dict.fromkeys(table_names or ()))


def discover_legacy_tables(
    source_dir: Path,
    required_tables: tuple[str, ...] | list[str],
    selected_tables: tuple[str, ...] | list[str] | None = None,
) -> list[DiscoveredLegacyTable]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Legacy export directory does not exist: {source_dir}")

    manifest_path = source_dir / "MANIFEST.md"
    manifest_counts = parse_manifest_rows(manifest_path)
    if not manifest_counts:
        raise FileNotFoundError(f"Legacy manifest not found or empty: {manifest_path}")

    selected = _dedupe_table_names(selected_tables)
    manifest_tables = tuple(sorted(manifest_counts))

    missing_required = [table for table in required_tables if table not in manifest_counts]
    if missing_required:
        missing = ", ".join(sorted(missing_required))
        raise FileNotFoundError(f"Missing required legacy tables: {missing}")

    if selected:
        missing_selected = [table for table in selected if table not in manifest_counts]
        if missing_selected:
            missing = ", ".join(sorted(missing_selected))
            raise FileNotFoundError(f"Requested legacy tables not found: {missing}")
        table_names = selected
    else:
        table_names = manifest_tables

    missing_files = [
        table_name
        for table_name in dict.fromkeys((*required_tables, *table_names))
        if not (source_dir / f"{table_name}.csv").exists()
    ]
    if missing_files:
        missing = ", ".join(sorted(missing_files))
        raise FileNotFoundError(f"Missing expected legacy CSV files: {missing}")

    return [
        DiscoveredLegacyTable(
            table_name=table_name,
            csv_path=source_dir / f"{table_name}.csv",
            expected_row_count=manifest_counts.get(table_name),
        )
        for table_name in table_names
    ]


def _quoted_identifier(value: str) -> str:
    if not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value}")
    return f'"{value}"'


def _stage_columns(column_count: int) -> list[str]:
    columns = [f"col_{index}" for index in range(1, column_count + 1)]
    columns.extend(
        [
            "_source_table",
            "_source_file",
            "_source_row_number",
            "_batch_id",
            "_import_status",
            "_legacy_pk",
        ]
    )
    return columns


def _legacy_row_identity(table_name: str, row: list[str]) -> str:
    digest = hashlib.sha256()
    digest.update(table_name.encode("utf-8"))
    digest.update(b"\0")
    for field in row:
        digest.update(field.encode("utf-8"))
        digest.update(b"\x1f")
    return digest.hexdigest()


def _analyze_legacy_file(table: DiscoveredLegacyTable) -> tuple[int, int]:
    """Determine row count and max column count via sampling, not full iteration.

    Uses file byte size divided by an estimated average row size as a fast
    upper bound for row_count, then samples the first N rows to determine the
    column count.  This avoids loading a 25,000-row CSV twice (once for
    analysis, once for staging).
    """
    file_size = table.csv_path.stat().st_size
    if file_size == 0:
        raise ValueError(f"No importable rows found in {table.csv_path.name}")

    # Estimate average bytes per row from the first 8 KB of the file.
    sample_size = min(file_size, 8192)
    with table.csv_path.open("rb") as f:
        sample = f.read(sample_size)
    newlines = sample.count(b"\n")
    estimated_row_bytes = sample_size / max(newlines, 1)

    # Use manifest count if available; otherwise estimate from file size.
    # When manifest count is present, validate it by counting non-empty lines in the
    # full file (single sequential read, no rows held in memory).
    if table.expected_row_count is not None:
        row_count = table.expected_row_count
        with table.csv_path.open("r", encoding="utf-8", newline="") as fh:
            actual_lines = sum(
                1 for line in fh if line.strip() and not line.strip().startswith("#")
            )
        if actual_lines != row_count:
            raise ValueError(
                f"Manifest row count mismatch for {table.table_name}: "
                f"expected {table.expected_row_count}, got {actual_lines}"
            )
    else:
        row_count = max(1, int(file_size / estimated_row_bytes))

    # Sample the first 200 non-empty rows to determine column count.
    column_count = 0
    rows_seen = 0
    for row in iter_legacy_rows(table.csv_path):
        column_count = max(column_count, len(row))
        rows_seen += 1
        if rows_seen >= 200:
            break

    if column_count == 0:
        raise ValueError(f"No importable rows found in {table.csv_path.name}")

    return row_count, column_count


def _iter_stage_records(table: DiscoveredLegacyTable, batch_id: str, column_count: int):
    """Yield stage records lazily — SHA256 is computed on-demand during iteration.

    Row numbers are tracked via a local counter so no full row list is held.
    """
    row_number = 0
    for row in iter_legacy_rows(table.csv_path):
        row_number += 1
        padded = row + [None] * (column_count - len(row))
        yield (
            *padded,
            table.table_name,
            table.csv_path.name,
            row_number,
            batch_id,
            "loaded",
            _legacy_row_identity(table.table_name, row),
        )


def _batched_stage_records(records, batch_size: int):
    """Yield small batches from a record generator without holding full batches in memory.

    Each batch is a list of at most `batch_size` records that is passed directly to
    `copy_records_to_table` and then discarded before the next batch is consumed.
    """
    batch: list[object] = []
    for record in records:
        batch.append(record)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


async def _drop_stage_table(
    connection: RawStageConnection,
    *,
    schema_name: str,
    table_name: str,
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    quoted_table = _quoted_identifier(table_name)
    await connection.execute(f"DROP TABLE IF EXISTS {quoted_schema}.{quoted_table} CASCADE")


async def _cleanup_stage_tables(
    connection: RawStageConnection,
    *,
    schema_name: str,
    table_names: list[str] | tuple[str, ...],
) -> None:
    for table_name in dict.fromkeys(table_names):
        await _drop_stage_table(
            connection,
            schema_name=schema_name,
            table_name=table_name,
        )


async def _recreate_stage_table(
    connection: RawStageConnection,
    *,
    schema_name: str,
    table_name: str,
    column_count: int,
) -> None:
    quoted_schema = _quoted_identifier(schema_name)
    column_defs = [
        f"{_quoted_identifier(f'col_{index}')} TEXT" for index in range(1, column_count + 1)
    ]
    column_defs.extend(
        [
            '"_source_table" TEXT NOT NULL',
            '"_source_file" TEXT NOT NULL',
            '"_source_row_number" INTEGER NOT NULL',
            '"_batch_id" TEXT NOT NULL',
            "\"_import_status\" TEXT NOT NULL DEFAULT 'loaded'",
            '"_legacy_pk" TEXT',
        ]
    )

    await connection.execute(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}")
    await _drop_stage_table(connection, schema_name=schema_name, table_name=table_name)
    quoted_table = _quoted_identifier(table_name)
    create_sql = f"CREATE TABLE {quoted_schema}.{quoted_table} ({', '.join(column_defs)})"
    await connection.execute(create_sql)


async def _stage_table_exists(
    connection: RawStageConnection,
    *,
    schema_name: str,
    table_name: str,
) -> bool:
    relation = f"{schema_name}.{table_name}"
    return await connection.fetchval("SELECT to_regclass($1)", relation) is not None


def _missing_stage_values(rows: list[object]) -> list[str]:
    values: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            raw_value = row.get("missing_value")
        else:
            raw_value = row[0]
        text = str(raw_value or "").strip()
        if text and text not in values:
            values.append(text)
    return values


async def _validate_staged_table(
    connection: RawStageConnection,
    *,
    schema_name: str,
    table_name: str,
    batch_id: str,
) -> str | None:
    quoted_schema = _quoted_identifier(schema_name)
    quoted_table = _quoted_identifier(table_name)

    if table_name == "tbsslipj":
        if not await _stage_table_exists(connection, schema_name=schema_name, table_name="tbscust"):
            return "fk_validation_skipped: tbscust not staged"

        rows = await connection.fetch(
            f"""
			SELECT DISTINCT stage.col_7 AS missing_value
			FROM {quoted_schema}.{quoted_table} AS stage
			LEFT JOIN {quoted_schema}.tbscust AS supplier
				ON supplier._batch_id = stage._batch_id
				AND supplier.col_1 = stage.col_7
				AND supplier.col_2 = '1'
			WHERE stage._batch_id = $1
				AND COALESCE(stage.col_7, '') <> ''
				AND supplier.col_1 IS NULL
			ORDER BY stage.col_7
			""",
            batch_id,
        )
        missing_values = _missing_stage_values(rows)
        if missing_values:
            missing = ", ".join(missing_values)
            raise ValueError(f"fk_violation: supplier_code -> tbscust [{missing}]")
        return None

    if table_name == "tbsslipdtj":
        if not await _stage_table_exists(
            connection,
            schema_name=schema_name,
            table_name="tbsslipj",
        ):
            return "fk_validation_skipped: tbsslipj not staged"

        rows = await connection.fetch(
            f"""
			SELECT DISTINCT stage.col_2 AS missing_value
			FROM {quoted_schema}.{quoted_table} AS stage
			LEFT JOIN {quoted_schema}.tbsslipj AS header
				ON header._batch_id = stage._batch_id
				AND header.col_2 = stage.col_2
			WHERE stage._batch_id = $1
				AND COALESCE(stage.col_2, '') <> ''
				AND header.col_2 IS NULL
			ORDER BY stage.col_2
			""",
            batch_id,
        )
        missing_values = _missing_stage_values(rows)
        if missing_values:
            missing = ", ".join(missing_values)
            raise ValueError(f"fk_violation: doc_number -> tbsslipj [{missing}]")
        return None

    if table_name == "tbsslipo":
        if not await _stage_table_exists(connection, schema_name=schema_name, table_name="tbscust"):
            return "fk_validation_skipped: tbscust not staged"

        rows = await connection.fetch(
            f"""
			SELECT DISTINCT stage.col_5 AS missing_value
			FROM {quoted_schema}.{quoted_table} AS stage
			LEFT JOIN {quoted_schema}.tbscust AS supplier
				ON supplier._batch_id = stage._batch_id
				AND supplier.col_1 = stage.col_5
				AND supplier.col_2 = '1'
			WHERE stage._batch_id = $1
				AND COALESCE(stage.col_5, '') <> ''
				AND supplier.col_1 IS NULL
			ORDER BY stage.col_5
			""",
            batch_id,
        )
        missing_values = _missing_stage_values(rows)
        if missing_values:
            missing = ", ".join(missing_values)
            return f"fk_warning: supplier_code -> tbscust [{missing}]"
        return None

    if table_name == "tbsspay":
        if not await _stage_table_exists(connection, schema_name=schema_name, table_name="tbscust"):
            return "fk_validation_skipped: tbscust not staged"

        rows = await connection.fetch(
            f"""
			SELECT DISTINCT stage.col_6 AS missing_value
			FROM {quoted_schema}.{quoted_table} AS stage
			LEFT JOIN {quoted_schema}.tbscust AS party
				ON party._batch_id = stage._batch_id
				AND party.col_1 = stage.col_6
			WHERE stage._batch_id = $1
				AND COALESCE(stage.col_6, '') NOT IN ('', '0000')
				AND party.col_1 IS NULL
			ORDER BY stage.col_6
			""",
            batch_id,
        )
        missing_values = _missing_stage_values(rows)
        if missing_values:
            missing = ", ".join(missing_values)
            return f"fk_warning: customer_code -> tbscust [{missing}]"
        return None

    if table_name == "tbsprepay":
        if not await _stage_table_exists(connection, schema_name=schema_name, table_name="tbscust"):
            return "fk_validation_skipped: tbscust not staged"

        rows = await connection.fetch(
            f"""
			SELECT DISTINCT stage.col_2 AS missing_value
			FROM {quoted_schema}.{quoted_table} AS stage
			LEFT JOIN {quoted_schema}.tbscust AS party
				ON party._batch_id = stage._batch_id
				AND party.col_1 = stage.col_2
			WHERE stage._batch_id = $1
				AND COALESCE(stage.col_2, '') NOT IN ('', '0000')
				AND party.col_1 IS NULL
			ORDER BY stage.col_2
			""",
            batch_id,
        )
        missing_values = _missing_stage_values(rows)
        if missing_values:
            missing = ", ".join(missing_values)
            return f"fk_warning: customer_code -> tbscust [{missing}]"
        return None

    return None


async def stage_table(
    connection: RawStageConnection,
    *,
    table: DiscoveredLegacyTable,
    schema_name: str,
    batch_id: str,
) -> StageTableResult:
    row_count, column_count = _analyze_legacy_file(table)
    await _recreate_stage_table(
        connection,
        schema_name=schema_name,
        table_name=table.table_name,
        column_count=column_count,
    )

    columns = _stage_columns(column_count)
    for batch_records in _batched_stage_records(
        _iter_stage_records(table, batch_id, column_count),
        _STAGE_COPY_BATCH_SIZE,
    ):
        await connection.copy_records_to_table(
            table.table_name,
            schema_name=schema_name,
            columns=columns,
            records=batch_records,
            timeout=None,
        )
    validation_message = await _validate_staged_table(
        connection,
        schema_name=schema_name,
        table_name=table.table_name,
        batch_id=batch_id,
    )
    return StageTableResult(
        table_name=table.table_name,
        row_count=row_count,
        column_count=column_count,
        source_file=table.csv_path.name,
        validation_message=validation_message,
    )


def _asyncpg_dsn(database_url: str) -> str:
    url = make_url(database_url)
    drivername = url.drivername.split("+", 1)[0]
    return url.set(drivername=drivername).render_as_string(hide_password=False)


async def _open_raw_connection() -> asyncpg.Connection:
    return await asyncpg.connect(
        dsn=_asyncpg_dsn(settings.database_url),
        command_timeout=None,
    )


async def _raw_stage_connection_from_session(session: AsyncSession) -> RawStageConnection:
    connection = await session.connection()
    raw_connection = await connection.get_raw_connection()
    return raw_connection.driver_connection


async def _load_existing_batch_table_names(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    batch_id: str,
) -> tuple[str, ...]:
    current_run_id = await session.scalar(
        select(LegacyImportRun.id)
        .where(
            LegacyImportRun.tenant_id == tenant_id,
            LegacyImportRun.batch_id == batch_id,
            LegacyImportRun.status == "completed",
        )
        .order_by(LegacyImportRun.attempt_number.desc(), LegacyImportRun.started_at.desc())
        .limit(1)
    )
    if current_run_id is None:
        return ()

    return tuple(
        dict.fromkeys(
            await session.scalars(
                select(LegacyImportTableRun.table_name).where(
                    LegacyImportTableRun.run_id == current_run_id
                )
            )
        )
    )


async def _next_batch_attempt_number(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    batch_id: str,
) -> int:
    latest_attempt = await session.scalar(
        select(func.max(LegacyImportRun.attempt_number)).where(
            LegacyImportRun.tenant_id == tenant_id,
            LegacyImportRun.batch_id == batch_id,
        )
    )
    return 1 if latest_attempt is None else int(latest_attempt) + 1


async def _record_failed_stage_attempt(
    *,
    tenant_id: uuid.UUID,
    batch_id: str,
    attempt_number: int,
    source_dir: Path,
    schema_name: str,
    requested_tables: tuple[str, ...],
    error_message: str,
    table_audits: tuple[AttemptTableAudit, ...],
) -> None:
    completed_at = datetime.now(tz=UTC)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            run = LegacyImportRun(
                tenant_id=tenant_id,
                batch_id=batch_id,
                source_path=str(source_dir),
                target_schema=schema_name,
                attempt_number=attempt_number,
                requested_tables=list(requested_tables) if requested_tables else None,
                status="failed",
                error_message=error_message,
                completed_at=completed_at,
            )
            session.add(run)
            await session.flush()

            for table_audit in table_audits:
                session.add(
                    LegacyImportTableRun(
                        run_id=run.id,
                        table_name=table_audit.table_name,
                        source_file=table_audit.source_file,
                        expected_row_count=table_audit.expected_row_count,
                        loaded_row_count=table_audit.loaded_row_count,
                        column_count=table_audit.column_count,
                        status=table_audit.status,
                        error_message=table_audit.error_message,
                        completed_at=completed_at,
                    )
                )


async def run_stage_import(
    *,
    batch_id: str,
    source_dir: Path | None = None,
    selected_tables: tuple[str, ...] | list[str] | None = None,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str | None = None,
) -> StageBatchResult:
    resolved_source_dir = Path(source_dir or settings.legacy_import_data_dir)
    resolved_schema = schema_name or settings.legacy_import_schema
    selected_scope = _dedupe_table_names(selected_tables)
    requested_tables = list(selected_scope) if selected_scope else None
    discovered_tables = discover_legacy_tables(
        resolved_source_dir,
        list(settings.legacy_import_required_tables),
        selected_scope,
    )
    results: list[StageTableResult] = []
    table_audits: list[AttemptTableAudit] = []
    attempt_number: int | None = None
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                attempt_number = await _next_batch_attempt_number(session, tenant_id, batch_id)
                previous_table_names = await _load_existing_batch_table_names(
                    session,
                    tenant_id,
                    batch_id,
                )
                connection = await _raw_stage_connection_from_session(session)

                if previous_table_names:
                    await _cleanup_stage_tables(
                        connection,
                        schema_name=resolved_schema,
                        table_names=previous_table_names,
                    )

                run = LegacyImportRun(
                    tenant_id=tenant_id,
                    batch_id=batch_id,
                    source_path=str(resolved_source_dir),
                    target_schema=resolved_schema,
                    attempt_number=attempt_number,
                    requested_tables=requested_tables,
                    status="running",
                )
                session.add(run)
                await session.flush()

                for table in discovered_tables:
                    table_audit = AttemptTableAudit(
                        table_name=table.table_name,
                        source_file=table.csv_path.name,
                        expected_row_count=table.expected_row_count,
                    )
                    table_audits.append(table_audit)

                    table_run = LegacyImportTableRun(
                        run_id=run.id,
                        table_name=table.table_name,
                        source_file=table.csv_path.name,
                        expected_row_count=table.expected_row_count,
                        status="running",
                    )
                    session.add(table_run)
                    await session.flush()

                    try:
                        result = await stage_table(
                            connection,
                            table=table,
                            schema_name=resolved_schema,
                            batch_id=batch_id,
                        )
                    except Exception as exc:
                        table_audit.status = "failed"
                        table_audit.error_message = str(exc)
                        raise

                    table_audit.status = "completed"
                    table_audit.loaded_row_count = result.row_count
                    table_audit.column_count = result.column_count
                    table_audit.error_message = result.validation_message
                    table_run.status = "completed"
                    table_run.loaded_row_count = result.row_count
                    table_run.column_count = result.column_count
                    table_run.error_message = result.validation_message
                    table_run.completed_at = datetime.now(tz=UTC)
                    results.append(result)
                    await session.flush()

                run.status = "completed"
                run.completed_at = datetime.now(tz=UTC)
    except Exception as exc:
        if attempt_number is not None:
            await _record_failed_stage_attempt(
                tenant_id=tenant_id,
                batch_id=batch_id,
                attempt_number=attempt_number,
                source_dir=resolved_source_dir,
                schema_name=resolved_schema,
                requested_tables=selected_scope,
                error_message=str(exc),
                table_audits=tuple(table_audits),
            )
        raise

    return StageBatchResult(
        batch_id=batch_id,
        schema_name=resolved_schema,
        source_dir=resolved_source_dir,
        tables=tuple(results),
    )
