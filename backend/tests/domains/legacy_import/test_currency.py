from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.dialects import postgresql

import domains.legacy_import.currency as currency
from domains.legacy_import import shared as legacy_shared


class FakeSession:
    def __init__(self, *, scalar_values: list[object] | None = None) -> None:
        self.scalar_values = list(scalar_values or [])
        self.added: list[object] = []
        self.executed: list[object] = []
        self.committed = False
        self.rolled_back = False

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def begin(self):
        return FakeSessionTransaction(self)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None and hasattr(obj, "id"):
                setattr(obj, "id", uuid.uuid4())

    async def scalar(self, statement):
        if self.scalar_values:
            return self.scalar_values.pop(0)
        return None

    async def execute(self, statement):
        self.executed.append(statement)
        return None


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


def _write_currency_export(tmp_path: Path) -> None:
    rows = [
        (
            "\"'0001', '新臺幣', 'NTD', 'NT Dollars', '1', 1.00000000, "
            "'1900-01-01', '', '0', '1', '', 2, 2, '0', '0', 0, 0, 0, 'A', '', "
            "0.00000000\""
        ),
        (
            "\"'0002', '美金', 'USD', 'US Dollars', '0', 32.00000000, "
            "'1900-01-01', '', '0', '1', '', 2, 2, '0', '0', 2, 2, 0, 'A', '', "
            "0.00000000\""
        ),
        (
            "\"'0005', '港幣', 'HKD', 'HK Dollars', '0', 4.00000000, "
            "'1900-01-01', '', '0', '1', '', 2, 2, '0', '0', 4, 4, 0, 'A', '', "
            "0.00000000\""
        ),
    ]
    (tmp_path / "tbscurrency.csv").write_text(
        "\n".join(rows) + "\n",
        encoding="utf-8",
    )


def test_load_currency_source_normalizes_default_code_and_precision(tmp_path: Path) -> None:
    _write_currency_export(tmp_path)

    source = currency._load_currency_source(tmp_path)

    row_by_code = {row.code: row for row in source.rows}
    assert tuple(row_by_code) == ("TWD", "USD", "HKD")
    assert source.default_currency_code == "TWD"
    assert source.column_count == 21
    assert row_by_code["TWD"].symbol == "NT$"
    assert row_by_code["USD"].symbol == "$"
    assert row_by_code["USD"].decimal_places == 2
    assert row_by_code["HKD"].decimal_places == 4


@pytest.mark.asyncio
async def test_run_currency_import_upserts_settings_and_tracks_attempt(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _write_currency_export(tmp_path)
    session = FakeSession(scalar_values=[None])

    monkeypatch.setattr(currency, "LegacyImportRun", FakeLegacyImportRunRecord)
    monkeypatch.setattr(currency, "LegacyImportTableRun", FakeLegacyImportTableRunRecord)

    async def fake_next_batch_attempt_number(*args, **kwargs) -> int:
        return 1

    monkeypatch.setattr(currency, "_next_batch_attempt_number", fake_next_batch_attempt_number)
    monkeypatch.setattr(currency, "AsyncSessionLocal", lambda: FakeSessionContext(session))

    result = await currency.run_currency_import(
        batch_id="batch-currency-001",
        export_dir=tmp_path,
    )

    run = next(obj for obj in session.added if isinstance(obj, FakeLegacyImportRunRecord))
    table_run = next(
        obj for obj in session.added if isinstance(obj, FakeLegacyImportTableRunRecord)
    )
    statements = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        for statement in session.executed
    ]

    assert result.batch_id == "batch-currency-001"
    assert result.attempt_number == 1
    assert result.currency_count == 3
    assert result.upserted_setting_count == 7
    assert result.default_currency_code == "TWD"
    assert run.batch_id == "batch-currency-001"
    assert run.requested_tables == ["tbscurrency"]
    assert run.status == "completed"
    assert table_run.table_name == "tbscurrency"
    assert table_run.loaded_row_count == 3
    assert table_run.column_count == 21
    assert table_run.status == "completed"
    assert session.committed is True
    assert len(statements) == 7
    assert all("ON CONFLICT" in statement for statement in statements)
    assert any(
        "currency.TWD.symbol" in statement and "NT$" in statement
        for statement in statements
    )
    assert any(
        "currency.HKD.decimal_places" in statement and "4" in statement
        for statement in statements
    )
    assert any("currency.default" in statement and "TWD" in statement for statement in statements)


@pytest.mark.asyncio
async def test_run_currency_import_requires_explicit_export_dir_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(legacy_shared.settings, "legacy_import_data_dir", "")

    with pytest.raises(ValueError, match="Dump-era file import requires an explicit --export-dir"):
        await currency.run_currency_import(batch_id="currency-settings")
