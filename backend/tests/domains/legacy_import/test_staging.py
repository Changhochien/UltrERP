from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from domains.legacy_import import staging
from domains.legacy_import import shared as legacy_shared
from domains.legacy_import.staging import (
    DiscoveredLegacyTable,
    LegacySourceColumnMetadata,
    LegacySourceCompatibilityError,
    LegacySourceConnectionSettings,
    StageSourceDescriptor,
    build_legacy_source_text_query,
    discover_legacy_tables,
    parse_legacy_row,
    parse_manifest_rows,
    serialize_legacy_source_record,
    stage_table,
)


class FakeRawStageConnection:
    def __init__(
        self,
        *,
        fetch_rows_by_query: dict[str, list[dict[str, object]]] | None = None,
        fetchvals_by_query: dict[str, object] | None = None,
    ) -> None:
        self.executed: list[str] = []
        self.copy_calls: list[dict[str, object]] = []
        self.fetch_rows_by_query = fetch_rows_by_query or {}
        self.fetchvals_by_query = fetchvals_by_query or {}
        self.closed = False

    async def execute(self, query: str) -> str:
        self.executed.append(query)
        return "OK"

    async def copy_records_to_table(
        self,
        table_name: str,
        *,
        schema_name: str | None = None,
        columns: list[str] | tuple[str, ...] | None = None,
        records: object,
        timeout: float | None = None,
    ) -> str:
        rows = list(records)
        self.copy_calls.append(
            {
                "table_name": table_name,
                "schema_name": schema_name,
                "columns": tuple(columns or ()),
                "rows": rows,
                "timeout": timeout,
            }
        )
        return f"COPY {len(rows)}"

    async def fetch(self, query: str, *args: object):
        for needle, rows in self.fetch_rows_by_query.items():
            if needle in query:
                return rows
        return []

    async def fetchval(self, query: str, *args: object):
        for needle, value in self.fetchvals_by_query.items():
            if needle in query:
                return value
        return None

    async def close(self) -> None:
        self.closed = True


class FakeLegacySourceTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeLegacySourceCursor:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._rows):
            raise StopAsyncIteration
        row = self._rows[self._index]
        self._index += 1
        return row


class FakeLegacySourceConnection:
    def __init__(
        self,
        *,
        fetch_rows_by_query: dict[str, list[dict[str, object]]] | None = None,
        fetchvals_by_query: dict[str, object] | None = None,
        cursor_rows_by_query: dict[str, list[dict[str, object]]] | None = None,
    ) -> None:
        self.fetch_rows_by_query = fetch_rows_by_query or {}
        self.fetchvals_by_query = fetchvals_by_query or {}
        self.cursor_rows_by_query = cursor_rows_by_query or {}
        self.cursor_calls: list[dict[str, object]] = []
        self.type_codec_calls: list[dict[str, object]] = []
        self.transaction_readonly_args: list[bool] = []
        self.closed = False

    async def fetch(self, query: str, *args: object):
        for needle, rows in self.fetch_rows_by_query.items():
            if needle in query:
                return rows
        return []

    async def fetchval(self, query: str, *args: object):
        for needle, value in self.fetchvals_by_query.items():
            if needle in query:
                return value
        return None

    def cursor(self, query: str, *args: object, prefetch: int | None = None):
        self.cursor_calls.append(
            {
                "query": query,
                "args": args,
                "prefetch": prefetch,
            }
        )
        for needle, rows in self.cursor_rows_by_query.items():
            if needle in query:
                return FakeLegacySourceCursor(rows)
        return FakeLegacySourceCursor([])

    def transaction(self, *, readonly: bool = False):
        self.transaction_readonly_args.append(readonly)
        return FakeLegacySourceTransaction()

    async def set_type_codec(
        self,
        type_name: str,
        *,
        schema: str,
        encoder,
        decoder,
        format: str,
    ) -> None:
        self.type_codec_calls.append(
            {
                "type_name": type_name,
                "schema": schema,
                "encoder": encoder,
                "decoder": decoder,
                "format": format,
            }
        )

    async def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def begin(self):
        return FakeSessionTransaction(self)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


class FakeSessionTransaction:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self.session.committed = True
        else:
            self.session.rolled_back = True
        return False


class FakeSessionContext:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeSettingsScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> FakeSettingsScalarResult:
        return self

    def all(self) -> list[object]:
        return self._rows


class FakeSettingsDbSession:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    async def execute(self, _query):
        return FakeSettingsScalarResult(self._rows)


class FakeLegacyImportRunRecord:
    def __init__(self, **kwargs) -> None:
        self.id = uuid.uuid4()
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeLegacyImportTableRunRecord:
    def __init__(self, **kwargs) -> None:
        self.id = uuid.uuid4()
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.mark.asyncio
async def test_load_runtime_legacy_source_connection_settings_prefers_db_overrides(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        staging,
        "settings",
        SimpleNamespace(
            legacy_db_host=None,
            legacy_db_port=5432,
            legacy_db_user=None,
            legacy_db_password=None,
            legacy_db_name=None,
            legacy_db_client_encoding="BIG5",
        ),
    )
    db_session = FakeSettingsDbSession(
        [
            SimpleNamespace(key="legacy_db_host", value="100.77.54.101"),
            SimpleNamespace(key="legacy_db_user", value="postgres"),
            SimpleNamespace(key="legacy_db_password", value="secret"),
            SimpleNamespace(key="legacy_db_name", value="cao50001"),
            SimpleNamespace(key="legacy_db_client_encoding", value="BIG5"),
        ]
    )

    result = await staging.load_runtime_legacy_source_connection_settings(db_session)

    assert result.host == "100.77.54.101"
    assert result.user == "postgres"
    assert result.password == "secret"
    assert result.database == "cao50001"
    assert result.port == 5432


def patch_control_table_models(monkeypatch) -> None:
    monkeypatch.setattr(staging, "LegacyImportRun", FakeLegacyImportRunRecord)
    monkeypatch.setattr(staging, "LegacyImportTableRun", FakeLegacyImportTableRunRecord)


@dataclass(slots=True, frozen=True)
class InlineStageTable:
    table_name: str
    source_name: str
    rows: tuple[tuple[str, ...], ...]
    expected_row_count: int | None = None

    async def get_column_count(self) -> int:
        if not self.rows:
            raise ValueError(f"No importable rows found in {self.source_name}")
        return max(len(row) for row in self.rows)

    async def iter_rows(self):
        for row_number, row in enumerate(self.rows, start=1):
            yield row_number, list(row)


class InlineStageSourceAdapter:
    def __init__(
        self,
        *,
        source_descriptor: StageSourceDescriptor,
        tables: list[InlineStageTable],
    ) -> None:
        self.source_descriptor = source_descriptor
        self._tables = tables
        self.closed = False
        self.discover_calls: list[dict[str, object]] = []

    async def discover_tables(
        self,
        *,
        required_tables,
        selected_tables=None,
    ) -> list[InlineStageTable]:
        self.discover_calls.append(
            {
                "required_tables": tuple(required_tables),
                "selected_tables": tuple(selected_tables or ()),
            }
        )
        selected = tuple(dict.fromkeys(selected_tables or ()))
        if not selected:
            return list(self._tables)
        table_map = {table.table_name: table for table in self._tables}
        return [table_map[table_name] for table_name in selected]

    async def close(self) -> None:
        self.closed = True


class FailingStageSourceAdapter:
    def __init__(self, *, source_descriptor: StageSourceDescriptor, error: Exception) -> None:
        self.source_descriptor = source_descriptor
        self._error = error
        self.closed = False

    async def discover_tables(
        self,
        *,
        required_tables,
        selected_tables=None,
    ) -> list[InlineStageTable]:
        raise self._error

    async def close(self) -> None:
        self.closed = True


def test_parse_legacy_row_handles_wrapped_export_format() -> None:
    row = parse_legacy_row("\"'1149', '2', '昌弘五金實業有限公司'\"")

    assert row == ["1149", "2", "昌弘五金實業有限公司"]


def test_parse_legacy_row_allows_commas_inside_quoted_fields() -> None:
    row = parse_legacy_row("\"'1', 'ACME, LTD', 8.00000000\"")

    assert row == ["1", "ACME, LTD", "8.00000000"]


def test_parse_legacy_row_accepts_sql_escaped_quotes_and_numeric_literals() -> None:
    row = parse_legacy_row("\"'1149', '莫''S', 0.00000000, 1, -2.5, 6.02E+23\"")

    assert row == ["1149", "莫'S", "0.00000000", "1", "-2.5", "6.02E+23"]


def test_parse_legacy_row_rejects_malformed_rows() -> None:
    with pytest.raises(ValueError, match="Malformed legacy row"):
        parse_legacy_row("\"'1', 'A', 'unterminated\"")

    with pytest.raises(ValueError, match="Malformed legacy row"):
        parse_legacy_row("\"'1', 'A', bad\"")


def test_build_legacy_source_text_query_supports_text_numeric_and_date_types() -> None:
    query = build_legacy_source_text_query(
        schema_name="public",
        table_name="tbscust",
        columns=(
            LegacySourceColumnMetadata(
                table_name="tbscust",
                column_name="scustno",
                ordinal_position=1,
                data_type="character varying",
                udt_name="varchar",
                is_nullable=False,
            ),
            LegacySourceColumnMetadata(
                table_name="tbscust",
                column_name="balance",
                ordinal_position=2,
                data_type="numeric",
                udt_name="numeric",
                is_nullable=True,
            ),
            LegacySourceColumnMetadata(
                table_name="tbscust",
                column_name="created_on",
                ordinal_position=3,
                data_type="date",
                udt_name="date",
                is_nullable=True,
            ),
        ),
    )

    assert (
        query
        == 'SELECT COALESCE("scustno"::text, \'NULL\') AS "scustno", '
        'COALESCE("balance"::text, \'NULL\') AS "balance", '
        'COALESCE("created_on"::text, \'NULL\') AS "created_on" '
        'FROM "public"."tbscust" ORDER BY ctid'
    )


def test_build_legacy_source_text_query_rejects_unsupported_types() -> None:
    with pytest.raises(
        LegacySourceCompatibilityError,
        match="Unsupported live-source column types",
    ):
        build_legacy_source_text_query(
            schema_name="public",
            table_name="tbscust",
            columns=(
                LegacySourceColumnMetadata(
                    table_name="tbscust",
                    column_name="raw_blob",
                    ordinal_position=1,
                    data_type="bytea",
                    udt_name="bytea",
                    is_nullable=True,
                ),
            ),
        )


def test_serialize_legacy_source_record_requires_text_values() -> None:
    columns = (
        LegacySourceColumnMetadata(
            table_name="tbscust",
            column_name="scustno",
            ordinal_position=1,
            data_type="character varying",
            udt_name="varchar",
            is_nullable=False,
        ),
        LegacySourceColumnMetadata(
            table_name="tbscust",
            column_name="balance",
            ordinal_position=2,
            data_type="numeric",
            udt_name="numeric",
            is_nullable=True,
        ),
    )

    assert serialize_legacy_source_record(
        {"scustno": "T068", "balance": "NULL"},
        columns,
    ) == ["T068", "NULL"]

    with pytest.raises(
        LegacySourceCompatibilityError,
        match="must be projected to text before staging",
    ):
        serialize_legacy_source_record(
            {"scustno": "T068", "balance": 12},
            columns,
        )


def test_live_source_text_contract_preserves_legacy_pk_semantics() -> None:
    columns = (
        LegacySourceColumnMetadata(
            table_name="tbscust",
            column_name="scustno",
            ordinal_position=1,
            data_type="character varying",
            udt_name="varchar",
            is_nullable=False,
        ),
        LegacySourceColumnMetadata(
            table_name="tbscust",
            column_name="scustname",
            ordinal_position=2,
            data_type="character varying",
            udt_name="varchar",
            is_nullable=False,
        ),
        LegacySourceColumnMetadata(
            table_name="tbscust",
            column_name="balance",
            ordinal_position=3,
            data_type="numeric",
            udt_name="numeric",
            is_nullable=True,
        ),
        LegacySourceColumnMetadata(
            table_name="tbscust",
            column_name="created_on",
            ordinal_position=4,
            data_type="date",
            udt_name="date",
            is_nullable=True,
        ),
    )

    live_row = serialize_legacy_source_record(
        {
            "scustno": "T068",
            "scustname": "達基",
            "balance": "NULL",
            "created_on": "2024-01-02",
        },
        columns,
    )
    file_row = parse_legacy_row("\"'T068', '達基', NULL, '2024-01-02'\"")

    assert live_row == file_row
    assert staging._legacy_row_identity("tbscust", live_row) == staging._legacy_row_identity(
        "tbscust",
        file_row,
    )


@pytest.mark.asyncio
async def test_open_raw_connection_disables_command_timeout(monkeypatch) -> None:
    captured: dict[str, object] = {}
    sentinel_conn = object()

    class FakePool:
        async def acquire(self):
            return sentinel_conn

    async def fake_create_pool(*, dsn: str, command_timeout, **kwargs):
        captured["dsn"] = dsn
        captured["command_timeout"] = command_timeout
        return FakePool()

    monkeypatch.setattr(staging, "_asyncpg_dsn", lambda _: "postgresql://example")
    monkeypatch.setattr(staging.asyncpg, "create_pool", fake_create_pool)

    # Clear the cached pool so our patched function gets called
    staging._RAW_CONNECTION_POOL = None

    result = await staging._open_raw_connection()

    # Verify the result wraps our sentinel connection
    assert result._connection is sentinel_conn
    assert captured == {
        "dsn": "postgresql://example",
        "command_timeout": None,
    }


@pytest.mark.asyncio
async def test_open_legacy_source_connection_uses_big5_and_read_only(monkeypatch) -> None:
    captured: dict[str, object] = {}
    sentinel_conn = FakeLegacySourceConnection(
        fetchvals_by_query={"SHOW default_transaction_read_only": "on"},
    )

    async def fake_connect(**kwargs):
        captured.update(kwargs)
        return sentinel_conn

    monkeypatch.setattr(staging.asyncpg, "connect", fake_connect)

    result = await staging._open_legacy_source_connection(
        LegacySourceConnectionSettings(
            host="100.77.54.101",
            port=5432,
            user="postgres",
            password="secret",
            database="cao50001",
            client_encoding="BIG5",
        )
    )

    assert result._connection is sentinel_conn
    assert captured["host"] == "100.77.54.101"
    assert captured["port"] == 5432
    assert captured["user"] == "postgres"
    assert captured["database"] == "cao50001"
    assert captured["statement_cache_size"] == 0
    assert captured["command_timeout"] is None
    assert captured["server_settings"] == {
        "default_transaction_read_only": "on",
        "client_encoding": "BIG5",
    }
    assert sentinel_conn.type_codec_calls[0]["type_name"] == "text"
    assert sentinel_conn.type_codec_calls[0]["schema"] == "pg_catalog"
    assert sentinel_conn.type_codec_calls[0]["format"] == "binary"
    decoded = sentinel_conn.type_codec_calls[0]["decoder"](b"\xffA")
    assert decoded.endswith("A")


@pytest.mark.asyncio
async def test_open_legacy_source_connection_allows_superuser_when_session_is_guarded(
    monkeypatch,
) -> None:
    sentinel_conn = FakeLegacySourceConnection(
        fetchvals_by_query={"SHOW default_transaction_read_only": "on"},
    )

    async def fake_connect(**kwargs):
        return sentinel_conn

    monkeypatch.setattr(staging.asyncpg, "connect", fake_connect)

    result = await staging._open_legacy_source_connection(
        LegacySourceConnectionSettings(
            host="100.77.54.101",
            port=5432,
            user="postgres",
            password="secret",
            database="cao50001",
            client_encoding="BIG5",
        )
    )

    assert result._connection is sentinel_conn
    assert sentinel_conn.closed is False


@pytest.mark.asyncio
async def test_read_only_legacy_source_connection_rejects_write_like_queries() -> None:
    connection = staging._ReadOnlyLegacySourceConnection(FakeLegacySourceConnection())

    with pytest.raises(LegacySourceCompatibilityError, match="SHOW/SELECT"):
        await connection.fetch("UPDATE tbscust SET scustno = 'X'")


def test_read_only_legacy_source_connection_requires_explicit_readonly_transaction() -> None:
    connection = staging._ReadOnlyLegacySourceConnection(FakeLegacySourceConnection())

    with pytest.raises(LegacySourceCompatibilityError, match="explicitly read-only"):
        connection.transaction()


@pytest.mark.asyncio
async def test_probe_live_source_connection_collects_metadata_and_streams_rows() -> None:
    connection = FakeLegacySourceConnection(
        fetch_rows_by_query={
            "FROM pg_catalog.pg_tables": [
                {"tablename": "tbscust"},
                {"tablename": "tbsstock"},
            ],
            "FROM information_schema.columns": [
                {
                    "table_name": "tbscust",
                    "column_name": "scustno",
                    "ordinal_position": 1,
                    "data_type": "character varying",
                    "udt_name": "varchar",
                    "is_nullable": "NO",
                },
                {
                    "table_name": "tbscust",
                    "column_name": "balance",
                    "ordinal_position": 2,
                    "data_type": "numeric",
                    "udt_name": "numeric",
                    "is_nullable": "YES",
                },
            ],
        },
        fetchvals_by_query={
            "SHOW server_version": "8.2.23",
            "SHOW server_encoding": "SQL_ASCII",
            "SHOW client_encoding": "BIG5",
            "SHOW transaction_read_only": "on",
        },
        cursor_rows_by_query={
            'FROM "public"."tbscust"': [
                {"scustno": "T068", "balance": "NULL"},
                {"scustno": "T069", "balance": "12.5000"},
            ]
        },
    )

    report = await staging._probe_live_source_connection(
        connection,
        schema_name="public",
        required_tables=("tbscust", "tbsstock"),
        sample_tables=("tbscust",),
        sample_row_limit=2,
    )

    assert report.connector_name == "asyncpg"
    assert report.server_version == "8.2.23"
    assert report.server_encoding == "SQL_ASCII"
    assert report.client_encoding == "BIG5"
    assert report.read_only_verified is True
    assert report.public_table_count == 2
    assert report.missing_required_tables == ()
    assert report.required_tables_present == ("tbscust", "tbsstock")
    assert report.sampled_tables[0].table_name == "tbscust"
    assert report.sampled_tables[0].sample_rows == (
        ("T068", "NULL"),
        ("T069", "12.5000"),
    )
    assert connection.transaction_readonly_args == [True]
    assert "COALESCE" in connection.cursor_calls[0]["query"]
    assert "::text" in connection.cursor_calls[0]["query"]


@pytest.mark.asyncio
async def test_run_live_stage_import_uses_shared_loader_and_descriptor(
    monkeypatch,
) -> None:
    live_connection = FakeLegacySourceConnection(
        fetch_rows_by_query={
            "FROM pg_catalog.pg_tables": [{"tablename": "tbscust"}],
            "FROM information_schema.columns": [
                {
                    "table_name": "tbscust",
                    "column_name": "scustno",
                    "ordinal_position": 1,
                    "data_type": "character varying",
                    "udt_name": "varchar",
                    "is_nullable": "NO",
                },
                {
                    "table_name": "tbscust",
                    "column_name": "balance",
                    "ordinal_position": 2,
                    "data_type": "numeric",
                    "udt_name": "numeric",
                    "is_nullable": "YES",
                },
            ],
        },
        fetchvals_by_query={"SHOW transaction_read_only": "on"},
        cursor_rows_by_query={
            'FROM "public"."tbscust"': [
                {"scustno": "T068", "balance": "NULL"},
                {"scustno": "T069", "balance": "12.5000"},
            ]
        },
    )
    raw_connection = FakeRawStageConnection()
    session = FakeSession()

    patch_control_table_models(monkeypatch)
    monkeypatch.setattr(staging, "AsyncSessionLocal", lambda: FakeSessionContext(session))
    monkeypatch.setattr(staging.settings, "legacy_import_required_tables", ("tbscust",))

    async def fake_open_legacy_source_connection(*args, **kwargs):
        return live_connection

    async def fake_load_existing_batch_table_names(*args, **kwargs) -> tuple[str, ...]:
        return ()

    async def fake_next_batch_attempt_number(*args, **kwargs) -> int:
        return 1

    async def fake_raw_stage_connection_from_session(*args, **kwargs) -> FakeRawStageConnection:
        return raw_connection

    monkeypatch.setattr(
        staging,
        "_open_legacy_source_connection",
        fake_open_legacy_source_connection,
    )
    monkeypatch.setattr(
        staging,
        "_load_existing_batch_table_names",
        fake_load_existing_batch_table_names,
    )
    monkeypatch.setattr(staging, "_next_batch_attempt_number", fake_next_batch_attempt_number)
    monkeypatch.setattr(
        staging,
        "_raw_stage_connection_from_session",
        fake_raw_stage_connection_from_session,
    )

    result = await staging.run_live_stage_import(
        batch_id="batch-001",
        source_schema="public",
        connection_settings=LegacySourceConnectionSettings(
            host="100.77.54.101",
            port=5432,
            user="postgres",
            password="secret",
            database="cao50001",
            client_encoding="BIG5",
        ),
    )

    assert result.source_display_name == "legacy-db:cao50001/public"
    assert result.tables == (
        staging.StageTableResult(
            table_name="tbscust",
            row_count=2,
            column_count=2,
            source_file="public.tbscust",
        ),
    )
    assert session.added[0].source_path == "legacy-db:cao50001/public"
    copy_call = raw_connection.copy_calls[0]
    first_row = copy_call["rows"][0]
    expected_identity = hashlib.sha256(
        b"tbscust\0" + b"T068\x1fNULL\x1f"
    ).hexdigest()
    assert first_row[:2] == ("T068", "NULL")
    assert first_row[-4:-1] == (1, "batch-001", "loaded")
    assert first_row[-1] == expected_identity
    assert live_connection.transaction_readonly_args == [True]
    assert live_connection.closed is True


@pytest.mark.asyncio
async def test_run_live_stage_import_limits_scope_to_selected_tables(
    monkeypatch,
) -> None:
    live_connection = FakeLegacySourceConnection(
        fetch_rows_by_query={
            "FROM pg_catalog.pg_tables": [{"tablename": "tbsstock"}],
            "FROM information_schema.columns": [
                {
                    "table_name": "tbsstock",
                    "column_name": "stockno",
                    "ordinal_position": 1,
                    "data_type": "character varying",
                    "udt_name": "varchar",
                    "is_nullable": "NO",
                },
                {
                    "table_name": "tbsstock",
                    "column_name": "stockname",
                    "ordinal_position": 2,
                    "data_type": "character varying",
                    "udt_name": "varchar",
                    "is_nullable": "YES",
                },
            ],
        },
        fetchvals_by_query={"SHOW transaction_read_only": "on"},
        cursor_rows_by_query={
            'FROM "public"."tbsstock"': [
                {"stockno": "P001", "stockname": "Widget"},
            ]
        },
    )
    raw_connection = FakeRawStageConnection()
    session = FakeSession()

    patch_control_table_models(monkeypatch)
    monkeypatch.setattr(staging, "AsyncSessionLocal", lambda: FakeSessionContext(session))
    monkeypatch.setattr(staging.settings, "legacy_import_required_tables", ("tbscust", "tbsstock"))

    async def fake_open_legacy_source_connection(*args, **kwargs):
        return live_connection

    async def fake_load_existing_batch_table_names(*args, **kwargs) -> tuple[str, ...]:
        return ()

    async def fake_next_batch_attempt_number(*args, **kwargs) -> int:
        return 2

    async def fake_raw_stage_connection_from_session(*args, **kwargs) -> FakeRawStageConnection:
        return raw_connection

    monkeypatch.setattr(
        staging,
        "_open_legacy_source_connection",
        fake_open_legacy_source_connection,
    )
    monkeypatch.setattr(
        staging,
        "_load_existing_batch_table_names",
        fake_load_existing_batch_table_names,
    )
    monkeypatch.setattr(staging, "_next_batch_attempt_number", fake_next_batch_attempt_number)
    monkeypatch.setattr(
        staging,
        "_raw_stage_connection_from_session",
        fake_raw_stage_connection_from_session,
    )

    result = await staging.run_live_stage_import(
        batch_id="batch-002",
        source_schema="public",
        selected_tables=("tbsstock", "tbsstock"),
        connection_settings=LegacySourceConnectionSettings(
            host="100.77.54.101",
            port=5432,
            user="postgres",
            password="secret",
            database="cao50001",
            client_encoding="BIG5",
        ),
    )

    assert result.tables == (
        staging.StageTableResult(
            table_name="tbsstock",
            row_count=1,
            column_count=2,
            source_file="public.tbsstock",
        ),
    )
    assert session.added[0].requested_tables == ["tbsstock"]
    assert len(raw_connection.copy_calls) == 1
    assert raw_connection.copy_calls[0]["table_name"] == "tbsstock"
    assert live_connection.closed is True


def test_parse_manifest_rows_extracts_counts(tmp_path: Path) -> None:
    manifest = tmp_path / "MANIFEST.md"
    manifest.write_text(
        "| Table Name | Rows | Description |\n"
        "|------------|------|-------------|\n"
        "| tbscust | 1,022 | Customer master |\n"
        "| tbsstock | 6,611 | Product master |\n",
        encoding="utf-8",
    )

    counts = parse_manifest_rows(manifest)

    assert counts == {"tbscust": 1022, "tbsstock": 6611}


def test_discover_legacy_tables_requires_core_tables(tmp_path: Path) -> None:
    (tmp_path / "MANIFEST.md").write_text(
        "| Table Name | Rows | Description |\n"
        "|------------|------|-------------|\n"
        "| tbscust | 1 | Customer master |\n",
        encoding="utf-8",
    )
    (tmp_path / "tbscust.csv").write_text("\"'1', 'A'\"\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Missing required legacy tables"):
        discover_legacy_tables(tmp_path, ["tbscust", "tbsstock"])


def test_discover_legacy_tables_uses_manifest_counts(tmp_path: Path) -> None:
    (tmp_path / "MANIFEST.md").write_text(
        "| Table Name | Rows | Description |\n"
        "|------------|------|-------------|\n"
        "| tbscust | 2 | Customer master |\n"
        "| tbsstock | 1 | Product master |\n",
        encoding="utf-8",
    )
    (tmp_path / "tbscust.csv").write_text("\"'1', 'A'\"\n\"'2', 'B'\"\n", encoding="utf-8")
    (tmp_path / "tbsstock.csv").write_text("\"'P001', 'Widget'\"\n", encoding="utf-8")

    tables = discover_legacy_tables(tmp_path, ["tbscust", "tbsstock"])

    assert [table.table_name for table in tables] == ["tbscust", "tbsstock"]
    assert tables[0].expected_row_count == 2
    assert tables[1].expected_row_count == 1


def test_discover_legacy_tables_deduplicates_selected_tables(tmp_path: Path) -> None:
    (tmp_path / "MANIFEST.md").write_text(
        "| Table Name | Rows | Description |\n"
        "|------------|------|-------------|\n"
        "| tbscust | 1 | Customer master |\n"
        "| tbsstock | 1 | Product master |\n",
        encoding="utf-8",
    )
    (tmp_path / "tbscust.csv").write_text("\"'1', 'A'\"\n", encoding="utf-8")
    (tmp_path / "tbsstock.csv").write_text("\"'P001', 'Widget'\"\n", encoding="utf-8")

    tables = discover_legacy_tables(
        tmp_path,
        ["tbscust", "tbsstock"],
        selected_tables=["tbscust", "tbscust", "tbsstock"],
    )

    assert [table.table_name for table in tables] == ["tbscust", "tbsstock"]


def test_discover_legacy_tables_allows_selected_subset_without_all_required_tables(
    tmp_path: Path,
) -> None:
    (tmp_path / "MANIFEST.md").write_text(
        "| Table Name | Rows | Description |\n"
        "|------------|------|-------------|\n"
        "| tbscust | 1 | Customer master |\n",
        encoding="utf-8",
    )
    (tmp_path / "tbscust.csv").write_text("\"'1', 'A'\"\n", encoding="utf-8")

    tables = discover_legacy_tables(
        tmp_path,
        ["tbscust", "tbsstock"],
        selected_tables=["tbscust"],
    )

    assert [table.table_name for table in tables] == ["tbscust"]


def test_discover_legacy_tables_fails_when_manifest_file_is_missing(tmp_path: Path) -> None:
    (tmp_path / "tbscust.csv").write_text("\"'1', 'A'\"\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Legacy manifest not found or empty"):
        discover_legacy_tables(tmp_path, ["tbscust"])


def test_discover_legacy_tables_fails_when_manifest_listed_file_is_missing(tmp_path: Path) -> None:
    (tmp_path / "MANIFEST.md").write_text(
        "| Table Name | Rows | Description |\n"
        "|------------|------|-------------|\n"
        "| tbscust | 1 | Customer master |\n"
        "| tbsstock | 1 | Product master |\n",
        encoding="utf-8",
    )
    (tmp_path / "tbscust.csv").write_text("\"'1', 'A'\"\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Missing expected legacy CSV files"):
        discover_legacy_tables(tmp_path, ["tbscust", "tbsstock"])


def test_discover_legacy_tables_ignores_unlisted_csv_files(tmp_path: Path) -> None:
    (tmp_path / "MANIFEST.md").write_text(
        "| Table Name | Rows | Description |\n"
        "|------------|------|-------------|\n"
        "| tbscust | 1 | Customer master |\n",
        encoding="utf-8",
    )
    (tmp_path / "tbscust.csv").write_text("\"'1', 'A'\"\n", encoding="utf-8")
    (tmp_path / "stray.csv").write_text("\"'ignore'\"\n", encoding="utf-8")

    tables = discover_legacy_tables(tmp_path, ["tbscust"])

    assert [table.table_name for table in tables] == ["tbscust"]


@pytest.mark.asyncio
async def test_stage_table_uses_copy_records_and_lineage(tmp_path: Path) -> None:
    data_file = tmp_path / "tbscust.csv"
    data_file.write_text(
        "\"'1', 'A', 'Alpha'\"\n\"'2', 'B', 'Beta'\"\n",
        encoding="utf-8",
    )
    table = DiscoveredLegacyTable("tbscust", data_file, expected_row_count=2)
    connection = FakeRawStageConnection()

    result = await stage_table(
        connection,
        table=table,
        schema_name="raw_legacy",
        batch_id="batch-001",
    )

    assert result.row_count == 2
    assert result.column_count == 3
    assert any(
        'DROP TABLE IF EXISTS "raw_legacy"."tbscust"' in query for query in connection.executed
    )
    assert len(connection.copy_calls) == 1
    copy_call = connection.copy_calls[0]
    assert copy_call["table_name"] == "tbscust"
    assert copy_call["schema_name"] == "raw_legacy"
    assert copy_call["timeout"] is None
    first_row = copy_call["rows"][0]
    assert first_row[0:3] == ("1", "A", "Alpha")
    expected_identity = hashlib.sha256(b"tbscust\0" + b"1\x1fA\x1fAlpha\x1f").hexdigest()
    assert first_row[-4:-1] == (1, "batch-001", "loaded")
    assert first_row[-1] == expected_identity
    assert not any("INSERT INTO" in query for query in connection.executed)


@pytest.mark.asyncio
async def test_stage_table_batches_large_copy_operations(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_file = tmp_path / "tbscust.csv"
    data_file.write_text(
        "\"'1', 'A'\"\n\"'2', 'B'\"\n",
        encoding="utf-8",
    )
    table = DiscoveredLegacyTable("tbscust", data_file, expected_row_count=2)
    connection = FakeRawStageConnection()

    monkeypatch.setattr(staging, "_STAGE_COPY_BATCH_SIZE", 1)

    await stage_table(
        connection,
        table=table,
        schema_name="raw_legacy",
        batch_id="batch-001",
    )

    assert len(connection.copy_calls) == 2
    assert all(copy_call["timeout"] is None for copy_call in connection.copy_calls)


@pytest.mark.asyncio
async def test_stage_table_fails_on_manifest_row_count_mismatch(tmp_path: Path) -> None:
    data_file = tmp_path / "tbscust.csv"
    data_file.write_text("\"'1', 'A'\"\n", encoding="utf-8")
    table = DiscoveredLegacyTable("tbscust", data_file, expected_row_count=2)

    with pytest.raises(ValueError, match="Manifest row count mismatch"):
        await stage_table(
            FakeRawStageConnection(),
            table=table,
            schema_name="raw_legacy",
            batch_id="batch-001",
        )


@pytest.mark.asyncio
async def test_stage_table_allows_zero_row_live_source_tables() -> None:
    class EmptyLiveStageTable:
        table_name = "opdaevent"
        source_name = "public.opdaevent"
        expected_row_count = None

        async def get_column_count(self) -> int:
            return 2

        async def iter_rows(self):
            if False:
                yield 0, []

    connection = FakeRawStageConnection()

    result = await stage_table(
        connection,
        table=EmptyLiveStageTable(),
        schema_name="raw_legacy",
        batch_id="batch-001",
    )

    assert result.row_count == 0
    assert result.column_count == 2
    assert result.validation_message is None
    assert connection.copy_calls == []


@pytest.mark.asyncio
async def test_run_stage_import_only_drops_overlapping_tables_on_partial_rerun(
    monkeypatch,
) -> None:
    """On partial re-run (subset of tables), only drop tables in the intersection."""
    connection = FakeRawStageConnection()
    session = FakeSession()
    source = InlineStageSourceAdapter(
        source_descriptor=StageSourceDescriptor.live(
            database="cao50001",
            schema_name="public",
        ),
        tables=[
            InlineStageTable(
                table_name="tbscust",
                source_name="public.tbscust",
                rows=(("1", "A"),),
                expected_row_count=1,
            )
        ],
    )

    patch_control_table_models(monkeypatch)
    monkeypatch.setattr(staging, "AsyncSessionLocal", lambda: FakeSessionContext(session))

    async def fake_load_existing_batch_table_names(*args, **kwargs) -> tuple[str, ...]:
        # Previous run had both tbscust and tbsstock
        return ("tbscust", "tbsstock")

    async def fake_next_batch_attempt_number(*args, **kwargs) -> int:
        return 1

    async def fake_raw_stage_connection_from_session(*args, **kwargs) -> FakeRawStageConnection:
        return connection

    monkeypatch.setattr(
        staging,
        "_load_existing_batch_table_names",
        fake_load_existing_batch_table_names,
    )
    monkeypatch.setattr(staging, "_next_batch_attempt_number", fake_next_batch_attempt_number)
    monkeypatch.setattr(
        staging,
        "_raw_stage_connection_from_session",
        fake_raw_stage_connection_from_session,
    )

    result = await staging.run_stage_import_from_source(
        batch_id="batch-001",
        source=source,
        selected_tables=("tbscust",),
    )

    # tbscust was in both → should be dropped
    assert any(
        'DROP TABLE IF EXISTS "raw_legacy"."tbscust" CASCADE' == query
        for query in connection.executed
    )
    # tbsstock was NOT in current request → must NOT be dropped (preserved for partial rerun)
    assert not any(
        'DROP TABLE IF EXISTS "raw_legacy"."tbsstock" CASCADE' in query
        for query in connection.executed
    )
    assert result.tables == (
        staging.StageTableResult(
            table_name="tbscust",
            row_count=1,
            column_count=2,
            source_file="public.tbscust",
        ),
    )
    assert session.added[0].attempt_number == 1
    assert session.added[0].source_path == "legacy-db:cao50001/public"
    assert session.committed is True
    assert source.closed is True


@pytest.mark.asyncio
async def test_run_stage_import_records_failed_attempt_after_rollback(
    monkeypatch,
) -> None:
    connection = FakeRawStageConnection()
    main_session = FakeSession()
    failure_session = FakeSession()
    sessions = iter([main_session, failure_session])
    source = InlineStageSourceAdapter(
        source_descriptor=StageSourceDescriptor.live(
            database="cao50001",
            schema_name="public",
        ),
        tables=[
            InlineStageTable(
                table_name="tbscust",
                source_name="public.tbscust",
                rows=(("1", "A"),),
                expected_row_count=1,
            ),
            InlineStageTable(
                table_name="tbsstock",
                source_name="public.tbsstock",
                rows=(("P001", "Widget"),),
                expected_row_count=1,
            ),
        ],
    )

    patch_control_table_models(monkeypatch)
    monkeypatch.setattr(
        staging,
        "AsyncSessionLocal",
        lambda: FakeSessionContext(next(sessions)),
    )

    async def fake_load_existing_batch_table_names(*args, **kwargs) -> tuple[str, ...]:
        return ()

    async def fake_next_batch_attempt_number(*args, **kwargs) -> int:
        return 3

    async def fake_raw_stage_connection_from_session(*args, **kwargs) -> FakeRawStageConnection:
        return connection

    async def fake_stage_table(
        connection: FakeRawStageConnection,
        *,
        table,
        schema_name: str,
        batch_id: str,
    ) -> staging.StageTableResult:
        if table.table_name == "tbsstock":
            raise ValueError("Malformed legacy row in tbsstock.csv at line 1")
        return staging.StageTableResult(
            table_name=table.table_name,
            row_count=1,
            column_count=2,
            source_file=table.source_name,
        )

    monkeypatch.setattr(
        staging,
        "_load_existing_batch_table_names",
        fake_load_existing_batch_table_names,
    )
    monkeypatch.setattr(staging, "_next_batch_attempt_number", fake_next_batch_attempt_number)
    monkeypatch.setattr(
        staging,
        "_raw_stage_connection_from_session",
        fake_raw_stage_connection_from_session,
    )
    monkeypatch.setattr(staging, "stage_table", fake_stage_table)

    with pytest.raises(ValueError, match="Malformed legacy row"):
        await staging.run_stage_import_from_source(
            batch_id="batch-001",
            source=source,
        )

    assert main_session.rolled_back is True
    assert failure_session.committed is True
    failed_run = next(
        obj for obj in failure_session.added if getattr(obj, "status", None) == "failed"
    )
    assert failed_run.attempt_number == 3
    assert failed_run.source_path == "legacy-db:cao50001/public"
    assert failed_run.error_message == "Malformed legacy row in tbsstock.csv at line 1"
    assert source.closed is True


@pytest.mark.asyncio
async def test_run_stage_import_continues_after_optional_table_failure(monkeypatch) -> None:
    connection = FakeRawStageConnection()
    session = FakeSession()
    source = InlineStageSourceAdapter(
        source_descriptor=StageSourceDescriptor.live(
            database="cao50001",
            schema_name="public",
        ),
        tables=[
            InlineStageTable(
                table_name="tbscust",
                source_name="public.tbscust",
                rows=(("1", "A"),),
                expected_row_count=1,
            ),
            InlineStageTable(
                table_name="tbabank",
                source_name="public.tbabank",
                rows=(("bank",),),
                expected_row_count=1,
            ),
        ],
    )

    patch_control_table_models(monkeypatch)
    monkeypatch.setattr(staging, "AsyncSessionLocal", lambda: FakeSessionContext(session))

    async def fake_load_existing_batch_table_names(*args, **kwargs) -> tuple[str, ...]:
        return ()

    async def fake_next_batch_attempt_number(*args, **kwargs) -> int:
        return 5

    async def fake_raw_stage_connection_from_session(*args, **kwargs) -> FakeRawStageConnection:
        return connection

    async def fake_stage_table(
        connection: FakeRawStageConnection,
        *,
        table,
        schema_name: str,
        batch_id: str,
    ) -> staging.StageTableResult:
        if table.table_name == "tbabank":
            raise ValueError("decode failure in tbabank")
        return staging.StageTableResult(
            table_name=table.table_name,
            row_count=1,
            column_count=2,
            source_file=table.source_name,
        )

    monkeypatch.setattr(
        staging,
        "_load_existing_batch_table_names",
        fake_load_existing_batch_table_names,
    )
    monkeypatch.setattr(staging, "_next_batch_attempt_number", fake_next_batch_attempt_number)
    monkeypatch.setattr(
        staging,
        "_raw_stage_connection_from_session",
        fake_raw_stage_connection_from_session,
    )
    monkeypatch.setattr(staging, "stage_table", fake_stage_table)
    monkeypatch.setattr(staging.settings, "legacy_import_required_tables", ("tbscust",))

    result = await staging.run_stage_import_from_source(
        batch_id="batch-001",
        source=source,
    )

    assert tuple(table.table_name for table in result.tables) == ("tbscust",)
    failed_table_run = next(
        obj
        for obj in session.added
        if getattr(obj, "table_name", None) == "tbabank" and getattr(obj, "status", None) == "failed"
    )
    assert failed_table_run.error_message == "decode failure in tbabank"
    assert source.closed is True


@pytest.mark.asyncio
async def test_run_stage_import_records_failed_attempt_when_source_discovery_fails(
    monkeypatch,
) -> None:
    main_session = FakeSession()
    failure_session = FakeSession()
    sessions = iter([main_session, failure_session])
    source = FailingStageSourceAdapter(
        source_descriptor=StageSourceDescriptor.live(
            database="cao50001",
            schema_name="public",
        ),
        error=LegacySourceCompatibilityError(
            "Requested live-source tables not found in public: missing_table"
        ),
    )

    patch_control_table_models(monkeypatch)
    monkeypatch.setattr(
        staging,
        "AsyncSessionLocal",
        lambda: FakeSessionContext(next(sessions)),
    )

    async def fake_next_batch_attempt_number(*args, **kwargs) -> int:
        return 4

    monkeypatch.setattr(staging, "_next_batch_attempt_number", fake_next_batch_attempt_number)
    monkeypatch.setattr(staging.settings, "legacy_import_required_tables", ("tbscust",))

    with pytest.raises(LegacySourceCompatibilityError, match="missing_table"):
        await staging.run_stage_import_from_source(
            batch_id="batch-001",
            source=source,
        )

    assert main_session.rolled_back is True
    assert failure_session.committed is True
    failed_run = next(
        obj for obj in failure_session.added if getattr(obj, "status", None) == "failed"
    )
    assert failed_run.attempt_number == 4
    assert failed_run.source_path == "legacy-db:cao50001/public"
    assert "missing_table" in failed_run.error_message
    assert source.closed is True


@pytest.mark.asyncio
async def test_run_stage_import_records_deduped_requested_tables(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_file = tmp_path / "tbscust.csv"
    data_file.write_text("\"'1', 'A'\"\n", encoding="utf-8")
    connection = FakeRawStageConnection()
    session = FakeSession()
    captured: dict[str, object] = {}

    patch_control_table_models(monkeypatch)
    monkeypatch.setattr(staging, "AsyncSessionLocal", lambda: FakeSessionContext(session))

    def fake_discover_legacy_tables(*args, **kwargs):
        captured["selected_tables"] = kwargs.get("selected_tables", args[2])
        return [DiscoveredLegacyTable("tbscust", data_file, expected_row_count=1)]

    async def fake_load_existing_batch_table_names(*args, **kwargs) -> tuple[str, ...]:
        return ()

    async def fake_next_batch_attempt_number(*args, **kwargs) -> int:
        return 1

    async def fake_raw_stage_connection_from_session(*args, **kwargs) -> FakeRawStageConnection:
        return connection

    async def fake_stage_table(*args, **kwargs) -> staging.StageTableResult:
        return staging.StageTableResult(
            table_name="tbscust",
            row_count=1,
            column_count=2,
            source_file="tbscust.csv",
        )

    monkeypatch.setattr(staging, "discover_legacy_tables", fake_discover_legacy_tables)
    monkeypatch.setattr(
        staging,
        "_load_existing_batch_table_names",
        fake_load_existing_batch_table_names,
    )
    monkeypatch.setattr(staging, "_next_batch_attempt_number", fake_next_batch_attempt_number)
    monkeypatch.setattr(
        staging,
        "_raw_stage_connection_from_session",
        fake_raw_stage_connection_from_session,
    )
    monkeypatch.setattr(staging, "stage_table", fake_stage_table)

    result = await staging.run_stage_import(
        batch_id="batch-001",
        source_dir=tmp_path,
        selected_tables=("tbscust", "tbscust"),
    )

    assert captured["selected_tables"] == ("tbscust",)
    assert session.added[0].requested_tables == ["tbscust"]
    assert result.tables == (
        staging.StageTableResult(
            table_name="tbscust",
            row_count=1,
            column_count=2,
            source_file="tbscust.csv",
        ),
    )
    assert session.added[0].attempt_number == 1


@pytest.mark.asyncio
async def test_stage_table_fails_on_purchase_supplier_fk_violation(tmp_path: Path) -> None:
    data_file = tmp_path / "tbsslipj.csv"
    data_file.write_text(
        '"\'1\', \'PO-001\', \'2024-08-01\', \'X\', \'X\', \'X\', \'BADSUP\'"\n',
        encoding="utf-8",
    )
    table = DiscoveredLegacyTable("tbsslipj", data_file, expected_row_count=1)
    connection = FakeRawStageConnection(
        fetchvals_by_query={"to_regclass": "raw_legacy.tbscust"},
        fetch_rows_by_query={
            'FROM "raw_legacy"."tbsslipj"': [{"missing_value": "BADSUP"}],
        },
    )

    with pytest.raises(ValueError, match="fk_violation: supplier_code"):
        await stage_table(
            connection,
            table=table,
            schema_name="raw_legacy",
            batch_id="batch-016",
        )


@pytest.mark.asyncio
async def test_run_stage_import_requires_explicit_source_dir_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(legacy_shared.settings, "legacy_import_data_dir", "")

    with pytest.raises(ValueError, match="Dump-era file import requires an explicit --source-dir"):
        await staging.run_stage_import(batch_id="batch-missing-source")


@pytest.mark.asyncio
async def test_stage_table_fails_on_purchase_line_header_fk_violation(tmp_path: Path) -> None:
    data_file = tmp_path / "tbsslipdtj.csv"
    data_file.write_text(
        '"\'1\', \'PO-001\', \'1\', \'X\', \'X\', \'P001\'"\n',
        encoding="utf-8",
    )
    table = DiscoveredLegacyTable("tbsslipdtj", data_file, expected_row_count=1)
    connection = FakeRawStageConnection(
        fetchvals_by_query={"to_regclass": "raw_legacy.tbsslipj"},
        fetch_rows_by_query={
            'FROM "raw_legacy"."tbsslipdtj"': [{"missing_value": "PO-001"}],
        },
    )

    with pytest.raises(ValueError, match="fk_violation: doc_number"):
        await stage_table(
            connection,
            table=table,
            schema_name="raw_legacy",
            batch_id="batch-016",
        )


@pytest.mark.asyncio
async def test_stage_table_records_payment_fk_warnings_without_aborting(tmp_path: Path) -> None:
    data_file = tmp_path / "tbsspay.csv"
    data_file.write_text(
        '"\'1\', \'PAY-001\', \'0\', \'2016-04-28\', \'YYYMMDD999\', \'MISSING\', \'Unknown\'"\n',
        encoding="utf-8",
    )
    table = DiscoveredLegacyTable("tbsspay", data_file, expected_row_count=1)
    connection = FakeRawStageConnection(
        fetchvals_by_query={"to_regclass": "raw_legacy.tbscust"},
        fetch_rows_by_query={
            'FROM "raw_legacy"."tbsspay"': [{"missing_value": "MISSING"}],
        },
    )

    result = await stage_table(
        connection,
        table=table,
        schema_name="raw_legacy",
        batch_id="batch-016",
    )

    assert result.table_name == "tbsspay"
    assert result.row_count == 1
    assert result.column_count == 7
    assert result.validation_message == "fk_warning: customer_code -> tbscust [MISSING]"
