"""Legacy raw-staging import helpers and orchestration."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncIterator, Protocol, Sequence

import asyncpg
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.database import AsyncSessionLocal
from common.models.legacy_import import LegacyImportRun, LegacyImportTableRun
from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.shared import resolve_dump_data_dir

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_MANIFEST_ROW_RE = re.compile(r"^\|\s*([a-z0-9_]+)\s*\|\s*([0-9,]+)\s*\|")
_NUMERIC_LITERAL_RE = re.compile(r"^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?$")
_READ_ONLY_SQL_RE = re.compile(r"^(SELECT|SHOW)\b", re.IGNORECASE | re.DOTALL)
_STAGE_COPY_BATCH_SIZE = 25_000
_LIVE_SOURCE_CURSOR_PREFETCH = 1_000
_SUPPORTED_LEGACY_SOURCE_DATA_TYPES = frozenset(
    {
        "character",
        "character varying",
        "date",
        "double precision",
        "integer",
        "numeric",
        "smallint",
        "text",
        "timestamp with time zone",
    }
)
_RAW_CONNECTION_POOL: asyncpg.Pool | None = None
_RAW_CONNECTION_POOL_LOCK = asyncio.Lock()
_LEGACY_PYTHON_CODEC_ALIASES = {
    "big5": "big5hkscs",
    "big5-hkscs": "big5hkscs",
    "cp950": "big5hkscs",
}


@dataclass(slots=True, frozen=True)
class DiscoveredLegacyTable:
    table_name: str
    csv_path: Path
    expected_row_count: int | None = None

    @property
    def source_name(self) -> str:
        return self.csv_path.name

    async def get_column_count(self) -> int:
        _, column_count = _analyze_legacy_file(self)
        return column_count

    async def iter_rows(self) -> AsyncIterator[tuple[int, list[str]]]:
        row_number = 0
        for row in iter_legacy_rows(self.csv_path):
            row_number += 1
            yield row_number, row


@dataclass(slots=True, frozen=True)
class LiveDiscoveredLegacyTable:
    table_name: str
    source_schema: str
    columns: tuple[LegacySourceColumnMetadata, ...]
    query: str
    connection_settings: LegacySourceConnectionSettings
    expected_row_count: int | None = None

    @property
    def source_name(self) -> str:
        return f"{self.source_schema}.{self.table_name}"

    async def get_column_count(self) -> int:
        if not self.columns:
            raise LegacySourceCompatibilityError(
                f"No column metadata found for live source table {self.source_name}"
            )
        return len(self.columns)

    async def iter_rows(self) -> AsyncIterator[tuple[int, list[str]]]:
        connection = await _open_legacy_source_connection(self.connection_settings)
        try:
            async with connection.transaction(readonly=True):
                await _assert_read_only_transaction_async(connection)
                row_number = 0
                async for record in connection.cursor(
                    self.query,
                    prefetch=_LIVE_SOURCE_CURSOR_PREFETCH,
                ):
                    row_number += 1
                    yield row_number, serialize_legacy_source_record(record, self.columns)
        except UnicodeDecodeError as exc:
            raise LegacySourceCompatibilityError(
                "asyncpg could not decode live-source text while streaming "
                f"{self.source_name}; verify LEGACY_DB_CLIENT_ENCODING."
            ) from exc
        finally:
            await connection.close()


async def _assert_read_only_transaction_async(connection: LegacySourceConnection) -> None:
    transaction_read_only = str(
        await connection.fetchval("SHOW transaction_read_only")
    ).strip()
    if transaction_read_only.lower() != "on":
        raise LegacySourceCompatibilityError(
            "Legacy live-stage reads require a read-only transaction."
        )


async def _assert_read_only_legacy_session_async(
    connection: LegacySourceConnection,
) -> None:
    default_transaction_read_only = str(
        await connection.fetchval("SHOW default_transaction_read_only")
    ).strip()
    if default_transaction_read_only.lower() != "on":
        raise LegacySourceCompatibilityError(
            "Legacy live-stage connections must default to read-only transactions."
        )


def _assert_read_only_legacy_sql(query: str) -> None:
    normalized = query.lstrip()
    if _READ_ONLY_SQL_RE.match(normalized):
        return
    raise LegacySourceCompatibilityError(
        "Legacy live-stage allows only read-only SHOW/SELECT queries on the "
        "legacy source connection."
    )


class _ReadOnlyLegacySourceConnection:
    def __init__(self, connection: asyncpg.Connection) -> None:
        self._connection = connection

    async def fetch(self, query: str, *args: object):
        _assert_read_only_legacy_sql(query)
        return await self._connection.fetch(query, *args)

    async def fetchval(self, query: str, *args: object):
        _assert_read_only_legacy_sql(query)
        return await self._connection.fetchval(query, *args)

    def cursor(self, query: str, *args: object, prefetch: int | None = None):
        _assert_read_only_legacy_sql(query)
        return self._connection.cursor(query, *args, prefetch=prefetch)

    def transaction(self, *, readonly: bool = False) -> Any:
        if not readonly:
            raise LegacySourceCompatibilityError(
                "Legacy live-stage requires explicitly read-only transactions."
            )
        return self._connection.transaction(readonly=True)

    async def close(self) -> None:
        await self._connection.close()


@dataclass(slots=True, frozen=True)
class StageTableResult:
    table_name: str
    row_count: int
    column_count: int
    source_file: str
    validation_message: str | None = None


@dataclass(slots=True, frozen=True)
class StageSourceDescriptor:
    kind: str
    display_name: str
    audit_value: str

    @classmethod
    def file(cls, source_dir: Path) -> StageSourceDescriptor:
        source_value = str(source_dir)
        return cls(
            kind="file",
            display_name=source_value,
            audit_value=source_value,
        )

    @classmethod
    def live(cls, *, database: str, schema_name: str) -> StageSourceDescriptor:
        descriptor = f"legacy-db:{database}/{schema_name}"
        return cls(
            kind="live",
            display_name=descriptor,
            audit_value=descriptor,
        )

    def __str__(self) -> str:
        return self.display_name


@dataclass(slots=True, frozen=True)
class StageBatchResult:
    batch_id: str
    schema_name: str
    source_descriptor: StageSourceDescriptor
    tables: tuple[StageTableResult, ...]

    @property
    def source_display_name(self) -> str:
        return self.source_descriptor.display_name

    @property
    def source_path(self) -> str:
        return self.source_descriptor.audit_value

    @property
    def source_dir(self) -> Path | None:
        if self.source_descriptor.kind != "file":
            return None
        return Path(self.source_descriptor.audit_value)


@dataclass(slots=True)
class AttemptTableAudit:
    table_name: str
    source_file: str
    expected_row_count: int | None
    loaded_row_count: int = 0
    column_count: int = 0
    status: str = "running"
    error_message: str | None = None


@dataclass(slots=True, frozen=True)
class LegacySourceConnectionSettings:
    host: str
    port: int
    user: str
    password: str
    database: str
    client_encoding: str = "BIG5"


@dataclass(slots=True, frozen=True)
class LegacySourceColumnMetadata:
    table_name: str
    column_name: str
    ordinal_position: int
    data_type: str
    udt_name: str
    is_nullable: bool


@dataclass(slots=True, frozen=True)
class LegacySourceTableProbe:
    table_name: str
    column_count: int
    sample_row_count: int
    columns: tuple[LegacySourceColumnMetadata, ...]
    sample_rows: tuple[tuple[str, ...], ...]


@dataclass(slots=True, frozen=True)
class LegacySourceCompatibilityReport:
    connector_name: str
    connector_version: str
    server_version: str
    server_encoding: str
    client_encoding: str
    read_only_verified: bool
    public_table_count: int
    required_tables_present: tuple[str, ...]
    missing_required_tables: tuple[str, ...]
    sampled_tables: tuple[LegacySourceTableProbe, ...]


class LegacySourceCompatibilityError(RuntimeError):
    """Raised when the live legacy source cannot satisfy the staging contract."""


class RawStageConnection(Protocol):
    async def execute(self, query: str, *args: object) -> str: ...

    async def fetch(self, query: str, *args: object): ...

    async def fetchrow(self, query: str, *args: object): ...

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

    def transaction(self) -> Any: ...

    async def close(self) -> None: ...


class LegacySourceConnection(Protocol):
    async def fetch(self, query: str, *args: object): ...

    async def fetchval(self, query: str, *args: object): ...

    def cursor(self, query: str, *args: object, prefetch: int | None = None): ...

    def transaction(self, *, readonly: bool = False) -> Any: ...

    async def close(self) -> None: ...


class StageSourceTable(Protocol):
    table_name: str
    expected_row_count: int | None

    @property
    def source_name(self) -> str: ...

    async def get_column_count(self) -> int: ...

    async def iter_rows(self) -> AsyncIterator[tuple[int, list[str]]]: ...


class LegacyStageSourceAdapter(Protocol):
    source_descriptor: StageSourceDescriptor

    async def discover_tables(
        self,
        *,
        required_tables: Sequence[str],
        selected_tables: Sequence[str] | None = None,
    ) -> list[StageSourceTable]: ...

    async def close(self) -> None: ...


class FileLegacyStageSourceAdapter:
    def __init__(self, source_dir: Path) -> None:
        self._source_dir = source_dir
        self.source_descriptor = StageSourceDescriptor.file(source_dir)

    async def discover_tables(
        self,
        *,
        required_tables: Sequence[str],
        selected_tables: Sequence[str] | None = None,
    ) -> list[StageSourceTable]:
        return discover_legacy_tables(
            self._source_dir,
            list(required_tables),
            tuple(selected_tables or ()),
        )

    async def close(self) -> None:
        return None


class LiveLegacyStageSourceAdapter:
    def __init__(
        self,
        *,
        source_schema: str = "public",
        connection_settings: LegacySourceConnectionSettings | None = None,
    ) -> None:
        self._source_schema = source_schema
        self._connection_settings = connection_settings or _read_legacy_source_connection_settings()
        self._connection: LegacySourceConnection | None = None
        self.source_descriptor = StageSourceDescriptor.live(
            database=self._connection_settings.database,
            schema_name=source_schema,
        )

    async def _get_connection(self) -> LegacySourceConnection:
        if self._connection is not None:
            is_closed = getattr(self._connection, "is_closed", None)
            if callable(is_closed) and is_closed():
                self._connection = None
        if self._connection is None:
            self._connection = await _open_legacy_source_connection(self._connection_settings)
        return self._connection

    async def discover_tables(
        self,
        *,
        required_tables: Sequence[str],
        selected_tables: Sequence[str] | None = None,
    ) -> list[StageSourceTable]:
        connection = await self._get_connection()
        try:
            discovered_tables = await _discover_live_source_tables(
                connection,
                schema_name=self._source_schema,
            )
            available_tables = set(discovered_tables)
            selected = _dedupe_table_sequence(selected_tables)
            deduped_required_tables = _dedupe_table_sequence(required_tables)
            if selected:
                missing_selected = [
                    table_name for table_name in selected if table_name not in available_tables
                ]
                if missing_selected:
                    raise LegacySourceCompatibilityError(
                        "Requested live-source tables not found in "
                        f"{self._source_schema}: {', '.join(missing_selected)}"
                    )
                table_names = selected
            else:
                missing_required_tables = [
                    table_name
                    for table_name in deduped_required_tables
                    if table_name not in available_tables
                ]
                if missing_required_tables:
                    raise LegacySourceCompatibilityError(
                        "Missing required live-source tables in "
                        f"{self._source_schema}: {', '.join(missing_required_tables)}"
                    )
                table_names = discovered_tables

            discovered: list[StageSourceTable] = []
            for table_name in table_names:
                columns = await _load_live_source_column_metadata(
                    connection,
                    schema_name=self._source_schema,
                    table_name=table_name,
                )
                query = build_legacy_source_text_query(
                    schema_name=self._source_schema,
                    table_name=table_name,
                    columns=columns,
                )
                discovered.append(
                    LiveDiscoveredLegacyTable(
                        table_name=table_name,
                        source_schema=self._source_schema,
                        columns=columns,
                        query=query,
                        connection_settings=self._connection_settings,
                    )
                )
            return discovered
        finally:
            await self.close()

    async def close(self) -> None:
        if self._connection is None:
            return
        connection = self._connection
        self._connection = None
        await connection.close()


class _PooledRawConnection:
    def __init__(self, pool: asyncpg.Pool, connection: asyncpg.Connection) -> None:
        self._pool = pool
        self._connection = connection
        self._released = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)

    async def execute(self, query: str, *args: object) -> str:
        return await self._connection.execute(query, *args)

    async def fetch(self, query: str, *args: object):
        return await self._connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args: object):
        return await self._connection.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: object):
        return await self._connection.fetchval(query, *args)

    async def copy_records_to_table(
        self,
        table_name: str,
        *,
        schema_name: str | None = None,
        columns: list[str] | tuple[str, ...] | None = None,
        records: object,
        timeout: float | None = None,
    ) -> str:
        return await self._connection.copy_records_to_table(
            table_name,
            schema_name=schema_name,
            columns=columns,
            records=records,
            timeout=timeout,
        )

    def transaction(self) -> Any:
        return self._connection.transaction()

    async def close(self) -> None:
        if self._released:
            return
        self._released = True
        await self._pool.release(self._connection)


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


def _read_legacy_source_connection_settings() -> LegacySourceConnectionSettings:
    values = {
        "LEGACY_DB_HOST": settings.legacy_db_host,
        "LEGACY_DB_USER": settings.legacy_db_user,
        "LEGACY_DB_PASSWORD": settings.legacy_db_password,
        "LEGACY_DB_NAME": settings.legacy_db_name,
    }
    missing = [key for key, value in values.items() if value is None or str(value).strip() == ""]
    if missing:
        raise LegacySourceCompatibilityError(
            "Missing legacy source settings: " + ", ".join(missing)
        )

    return LegacySourceConnectionSettings(
        host=str(settings.legacy_db_host).strip(),
        port=int(settings.legacy_db_port),
        user=str(settings.legacy_db_user).strip(),
        password=str(settings.legacy_db_password),
        database=str(settings.legacy_db_name).strip(),
        client_encoding=str(settings.legacy_db_client_encoding).strip() or "BIG5",
    )


def _row_value(row: object, key: str, index: int) -> object:
    if isinstance(row, dict):
        return row[key]
    return row[key] if hasattr(row, "__getitem__") else row[index]


def _bool_from_nullable(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().upper() == "YES"


def build_legacy_source_text_query(
    *,
    schema_name: str,
    table_name: str,
    columns: Sequence[LegacySourceColumnMetadata],
) -> str:
    projections: list[str] = []
    unsupported: list[str] = []
    for column in columns:
        if column.data_type not in _SUPPORTED_LEGACY_SOURCE_DATA_TYPES:
            unsupported.append(
                f"{column.column_name} ({column.data_type}/{column.udt_name})"
            )
            continue
        quoted_column = _quoted_identifier(column.column_name)
        projections.append(
            f"COALESCE({quoted_column}::text, 'NULL') AS {quoted_column}"
        )

    if unsupported:
        raise LegacySourceCompatibilityError(
            "Unsupported live-source column types for "
            f"{schema_name}.{table_name}: {', '.join(unsupported)}"
        )

    quoted_schema = _quoted_identifier(schema_name)
    quoted_table = _quoted_identifier(table_name)
    return (
        f"SELECT {', '.join(projections)} FROM {quoted_schema}.{quoted_table} "
        f"ORDER BY ctid"
    )


def serialize_legacy_source_record(
    record: object,
    columns: Sequence[LegacySourceColumnMetadata],
) -> list[str]:
    serialized: list[str] = []
    for index, column in enumerate(columns):
        try:
            value = _row_value(record, column.column_name, index)
        except Exception as exc:  # pragma: no cover - defensive guard
            raise LegacySourceCompatibilityError(
                "Live-source record is missing expected projected column "
                f"{column.table_name}.{column.column_name}"
            ) from exc

        if not isinstance(value, str):
            raise LegacySourceCompatibilityError(
                "Live-source column "
                f"{column.table_name}.{column.column_name} must be projected to text "
                f"before staging; got {type(value).__name__}."
            )
        serialized.append(value)
    return serialized


def _legacy_python_codec_name(client_encoding: str) -> str:
    normalized = client_encoding.strip().lower().replace("_", "-")
    return _LEGACY_PYTHON_CODEC_ALIASES.get(normalized, normalized)


async def _configure_legacy_text_codec(
    raw_connection: asyncpg.Connection,
    *,
    client_encoding: str,
) -> None:
    python_codec = _legacy_python_codec_name(client_encoding)

    def _decode_text(value: str | bytes | bytearray | memoryview) -> str:
        if isinstance(value, str):
            return value
        return bytes(value).decode(python_codec, errors="replace")

    await raw_connection.set_type_codec(
        "text",
        schema="pg_catalog",
        encoder=lambda value: str(value).encode(python_codec, errors="replace"),
        decoder=_decode_text,
        format="binary",
    )


async def _open_legacy_source_connection(
    connection_settings: LegacySourceConnectionSettings | None = None,
) -> LegacySourceConnection:
    resolved_settings = connection_settings or _read_legacy_source_connection_settings()
    raw_connection = await asyncpg.connect(
        host=resolved_settings.host,
        port=resolved_settings.port,
        user=resolved_settings.user,
        password=resolved_settings.password,
        database=resolved_settings.database,
        statement_cache_size=0,
        command_timeout=None,
        server_settings={
            "default_transaction_read_only": "on",
            "client_encoding": resolved_settings.client_encoding,
        },
    )
    await _configure_legacy_text_codec(
        raw_connection,
        client_encoding=resolved_settings.client_encoding,
    )
    connection = _ReadOnlyLegacySourceConnection(raw_connection)
    try:
        await _assert_read_only_legacy_session_async(connection)
    except Exception:
        await connection.close()
        raise
    return connection


async def _discover_live_source_tables(
    connection: LegacySourceConnection,
    *,
    schema_name: str,
) -> tuple[str, ...]:
    rows = await connection.fetch(
        """
        SELECT tablename
        FROM pg_catalog.pg_tables
        WHERE schemaname = $1
        ORDER BY tablename
        """,
        schema_name,
    )
    return tuple(str(_row_value(row, "tablename", 0)) for row in rows)


async def _load_live_source_column_metadata(
    connection: LegacySourceConnection,
    *,
    schema_name: str,
    table_name: str,
) -> tuple[LegacySourceColumnMetadata, ...]:
    rows = await connection.fetch(
        """
        SELECT
            table_name,
            column_name,
            ordinal_position,
            data_type,
            udt_name,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = $1
            AND table_name = $2
        ORDER BY ordinal_position
        """,
        schema_name,
        table_name,
    )
    columns = tuple(
        LegacySourceColumnMetadata(
            table_name=str(_row_value(row, "table_name", 0)),
            column_name=str(_row_value(row, "column_name", 1)),
            ordinal_position=int(_row_value(row, "ordinal_position", 2)),
            data_type=str(_row_value(row, "data_type", 3)),
            udt_name=str(_row_value(row, "udt_name", 4)),
            is_nullable=_bool_from_nullable(_row_value(row, "is_nullable", 5)),
        )
        for row in rows
    )
    if not columns:
        raise LegacySourceCompatibilityError(
            f"No column metadata found for live source table {schema_name}.{table_name}"
        )
    return columns


def _dedupe_table_sequence(table_names: Sequence[str] | None) -> tuple[str, ...]:
    return tuple(dict.fromkeys(table_names or ()))


async def _probe_live_source_connection(
    connection: LegacySourceConnection,
    *,
    schema_name: str = "public",
    required_tables: Sequence[str] | None = None,
    sample_tables: Sequence[str] | None = None,
    sample_row_limit: int = 2,
) -> LegacySourceCompatibilityReport:
    if sample_row_limit < 1:
        raise ValueError("sample_row_limit must be at least 1")

    server_version = str(await connection.fetchval("SHOW server_version"))
    server_encoding = str(await connection.fetchval("SHOW server_encoding"))
    client_encoding = str(await connection.fetchval("SHOW client_encoding"))

    discovered_tables = await _discover_live_source_tables(connection, schema_name=schema_name)
    available_tables = set(discovered_tables)
    deduped_required_tables = _dedupe_table_sequence(required_tables)
    missing_required_tables = tuple(
        table_name for table_name in deduped_required_tables if table_name not in available_tables
    )
    if missing_required_tables:
        raise LegacySourceCompatibilityError(
            "Missing required live-source tables in "
            f"{schema_name}: {', '.join(missing_required_tables)}"
        )

    if sample_tables is None:
        tables_to_sample = deduped_required_tables or discovered_tables[:1]
    else:
        tables_to_sample = _dedupe_table_sequence(sample_tables)
        missing_sample_tables = [
            table_name for table_name in tables_to_sample if table_name not in available_tables
        ]
        if missing_sample_tables:
            raise LegacySourceCompatibilityError(
                "Requested live-source sample tables not found in "
                f"{schema_name}: {', '.join(missing_sample_tables)}"
            )

    sampled_tables: list[LegacySourceTableProbe] = []
    for table_name in tables_to_sample:
        columns = await _load_live_source_column_metadata(
            connection,
            schema_name=schema_name,
            table_name=table_name,
        )
        query = build_legacy_source_text_query(
            schema_name=schema_name,
            table_name=table_name,
            columns=columns,
        )

        try:
            async with connection.transaction(readonly=True):
                await _assert_read_only_transaction_async(connection)

                sample_rows: list[tuple[str, ...]] = []
                async for record in connection.cursor(
                    query,
                    prefetch=max(1, sample_row_limit),
                ):
                    sample_rows.append(tuple(serialize_legacy_source_record(record, columns)))
                    if len(sample_rows) >= sample_row_limit:
                        break
        except UnicodeDecodeError as exc:
            raise LegacySourceCompatibilityError(
                "asyncpg could not decode live-source text while streaming "
                f"{schema_name}.{table_name}; verify LEGACY_DB_CLIENT_ENCODING."
            ) from exc

        sampled_tables.append(
            LegacySourceTableProbe(
                table_name=table_name,
                column_count=len(columns),
                sample_row_count=len(sample_rows),
                columns=columns,
                sample_rows=tuple(sample_rows),
            )
        )

    return LegacySourceCompatibilityReport(
        connector_name="asyncpg",
        connector_version=asyncpg.__version__,
        server_version=server_version,
        server_encoding=server_encoding,
        client_encoding=client_encoding,
        read_only_verified=True,
        public_table_count=len(discovered_tables),
        required_tables_present=tuple(
            table_name for table_name in deduped_required_tables if table_name in available_tables
        ),
        missing_required_tables=missing_required_tables,
        sampled_tables=tuple(sampled_tables),
    )


async def probe_live_legacy_source(
    *,
    schema_name: str = "public",
    required_tables: Sequence[str] | None = None,
    sample_tables: Sequence[str] | None = None,
    sample_row_limit: int = 2,
    connection_settings: LegacySourceConnectionSettings | None = None,
) -> LegacySourceCompatibilityReport:
    connection = await _open_legacy_source_connection(connection_settings)
    try:
        return await _probe_live_source_connection(
            connection,
            schema_name=schema_name,
            required_tables=required_tables or settings.legacy_import_required_tables,
            sample_tables=sample_tables,
            sample_row_limit=sample_row_limit,
        )
    finally:
        await connection.close()


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
    return _dedupe_table_sequence(table_names)


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

    if selected:
        missing_selected = [table for table in selected if table not in manifest_counts]
        if missing_selected:
            missing = ", ".join(sorted(missing_selected))
            raise FileNotFoundError(f"Requested legacy tables not found: {missing}")
        table_names = selected
    else:
        missing_required = [table for table in required_tables if table not in manifest_counts]
        if missing_required:
            missing = ", ".join(sorted(missing_required))
            raise FileNotFoundError(f"Missing required legacy tables: {missing}")
        table_names = manifest_tables

    required_file_tables = (
        table_names
        if selected
        else tuple(dict.fromkeys((*required_tables, *table_names)))
    )
    missing_files = [
        table_name
        for table_name in required_file_tables
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


async def _iter_stage_records(
    table: StageSourceTable,
    batch_id: str,
    column_count: int,
) -> AsyncIterator[tuple[object, ...]]:
    """Yield normalized stage records lazily from any source adapter."""

    async for row_number, row in table.iter_rows():
        padded = row + [None] * (column_count - len(row))
        yield (
            *padded,
            table.table_name,
            table.source_name,
            row_number,
            batch_id,
            "loaded",
            _legacy_row_identity(table.table_name, row),
        )


async def _batched_stage_records(
    records: AsyncIterator[tuple[object, ...]],
    batch_size: int,
) -> AsyncIterator[list[tuple[object, ...]]]:
    """Yield small batches from an async record generator without buffering whole tables."""

    batch: list[tuple[object, ...]] = []
    async for record in records:
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
    table: StageSourceTable,
    schema_name: str,
    batch_id: str,
) -> StageTableResult:
    column_count = await table.get_column_count()
    await _recreate_stage_table(
        connection,
        schema_name=schema_name,
        table_name=table.table_name,
        column_count=column_count,
    )

    columns = _stage_columns(column_count)
    row_count = 0
    async for batch_records in _batched_stage_records(
        _iter_stage_records(table, batch_id, column_count),
        _STAGE_COPY_BATCH_SIZE,
    ):
        row_count += len(batch_records)
        await connection.copy_records_to_table(
            table.table_name,
            schema_name=schema_name,
            columns=columns,
            records=batch_records,
            timeout=None,
        )
    validation_message = None
    if row_count > 0:
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
        source_file=table.source_name,
        validation_message=validation_message,
    )


def _asyncpg_dsn(database_url: str) -> str:
    url = make_url(database_url)
    drivername = url.drivername.split("+", 1)[0]
    return url.set(drivername=drivername).render_as_string(hide_password=False)


async def _get_raw_connection_pool() -> asyncpg.Pool:
    global _RAW_CONNECTION_POOL  # noqa: PLW0603
    if _RAW_CONNECTION_POOL is not None:
        return _RAW_CONNECTION_POOL

    async with _RAW_CONNECTION_POOL_LOCK:
        if _RAW_CONNECTION_POOL is None:
            _RAW_CONNECTION_POOL = await asyncpg.create_pool(
                dsn=_asyncpg_dsn(settings.database_url),
                min_size=1,
                max_size=20,
                max_inactive_connection_lifetime=1800,
                statement_cache_size=0,
                command_timeout=None,
            )
    return _RAW_CONNECTION_POOL


async def close_raw_connection_pool() -> None:
    global _RAW_CONNECTION_POOL  # noqa: PLW0603
    if _RAW_CONNECTION_POOL is None:
        return

    async with _RAW_CONNECTION_POOL_LOCK:
        if _RAW_CONNECTION_POOL is None:
            return
        pool = _RAW_CONNECTION_POOL
        _RAW_CONNECTION_POOL = None
        await pool.close()


async def _open_raw_connection() -> RawStageConnection:
    pool = await _get_raw_connection_pool()
    connection = await pool.acquire()
    return _PooledRawConnection(pool, connection)


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
    source_descriptor: StageSourceDescriptor,
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
                source_path=source_descriptor.audit_value,
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


async def run_stage_import_from_source(
    *,
    batch_id: str,
    source: LegacyStageSourceAdapter,
    selected_tables: tuple[str, ...] | list[str] | None = None,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str | None = None,
) -> StageBatchResult:
    resolved_schema = schema_name or settings.legacy_import_schema
    selected_scope = _dedupe_table_sequence(selected_tables)
    fail_fast_tables = set(selected_scope or settings.legacy_import_required_tables)
    requested_tables = list(selected_scope) if selected_scope else None
    results: list[StageTableResult] = []
    table_audits: list[AttemptTableAudit] = []
    attempt_number: int | None = None
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                attempt_number = await _next_batch_attempt_number(session, tenant_id, batch_id)
                discovered_tables = await source.discover_tables(
                    required_tables=settings.legacy_import_required_tables,
                    selected_tables=selected_scope,
                )
                previous_table_names = await _load_existing_batch_table_names(
                    session,
                    tenant_id,
                    batch_id,
                )
                connection = await _raw_stage_connection_from_session(session)

                # Only drop tables that are in BOTH the previous run AND the current request.
                # This prevents accidentally deleting staged data for tables not re-requested
                # in a partial re-run of the same batch.
                if previous_table_names and selected_scope:
                    tables_to_cleanup = [t for t in previous_table_names if t in selected_scope]
                    if tables_to_cleanup:
                        await _cleanup_stage_tables(
                            connection,
                            schema_name=resolved_schema,
                            table_names=tables_to_cleanup,
                        )

                run = LegacyImportRun(
                    tenant_id=tenant_id,
                    batch_id=batch_id,
                    source_path=source.source_descriptor.audit_value,
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
                        source_file=table.source_name,
                        expected_row_count=table.expected_row_count,
                    )
                    table_audits.append(table_audit)

                    table_run = LegacyImportTableRun(
                        run_id=run.id,
                        table_name=table.table_name,
                        source_file=table.source_name,
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
                        table_run.status = "failed"
                        table_run.error_message = str(exc)
                        table_run.completed_at = datetime.now(tz=UTC)
                        await session.flush()
                        if table.table_name in fail_fast_tables:
                            raise
                        continue

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
                source_descriptor=source.source_descriptor,
                schema_name=resolved_schema,
                requested_tables=selected_scope,
                error_message=str(exc),
                table_audits=tuple(table_audits),
            )
        raise
    finally:
        await source.close()

    return StageBatchResult(
        batch_id=batch_id,
        schema_name=resolved_schema,
        source_descriptor=source.source_descriptor,
        tables=tuple(results),
    )


async def run_stage_import(
    *,
    batch_id: str,
    source_dir: Path | None = None,
    selected_tables: tuple[str, ...] | list[str] | None = None,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str | None = None,
) -> StageBatchResult:
    resolved_source_dir = resolve_dump_data_dir(source_dir, argument_name="--source-dir")
    return await run_stage_import_from_source(
        batch_id=batch_id,
        source=FileLegacyStageSourceAdapter(resolved_source_dir),
        selected_tables=selected_tables,
        tenant_id=tenant_id,
        schema_name=schema_name,
    )


async def run_live_stage_import(
    *,
    batch_id: str,
    source_schema: str = "public",
    selected_tables: tuple[str, ...] | list[str] | None = None,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str | None = None,
    connection_settings: LegacySourceConnectionSettings | None = None,
) -> StageBatchResult:
    return await run_stage_import_from_source(
        batch_id=batch_id,
        source=LiveLegacyStageSourceAdapter(
            source_schema=source_schema,
            connection_settings=connection_settings,
        ),
        selected_tables=selected_tables,
        tenant_id=tenant_id,
        schema_name=schema_name,
    )
