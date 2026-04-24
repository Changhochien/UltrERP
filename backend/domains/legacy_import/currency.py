"""Import currency settings from tbscurrency into app_settings."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from common.database import AsyncSessionLocal
from common.models.legacy_import import LegacyImportRun, LegacyImportTableRun
from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.shared import resolve_dump_data_dir
from domains.legacy_import.staging import iter_legacy_rows
from domains.settings.models import AppSetting

_TBSCURRENCY_TABLE_NAME = "tbscurrency"
_TBSCURRENCY_FILENAME = "tbscurrency.csv"
_DEFAULT_BATCH_ID = "currency-settings"
_TARGET_SCHEMA = "public"
_EXPECTED_COLUMN_COUNT = 21
_SOURCE_CODE_INDEX = 2
_DEFAULT_FLAG_INDEX = 4
_DECIMAL_PLACE_INDICES = (11, 12, 15, 16, 17)
_CURRENCY_SYMBOLS = {
    "EUR": "€",
    "HKD": "HK$",
    "JPY": "¥",
    "TWD": "NT$",
    "USD": "$",
}


@dataclass(slots=True, frozen=True)
class CurrencySettingRow:
    code: str
    symbol: str
    decimal_places: int
    is_default: bool


@dataclass(slots=True, frozen=True)
class CurrencyImportSource:
    csv_path: Path
    rows: tuple[CurrencySettingRow, ...]
    column_count: int
    default_currency_code: str


@dataclass(slots=True, frozen=True)
class CurrencyImportResult:
    batch_id: str
    source_file: Path
    attempt_number: int
    currency_count: int
    upserted_setting_count: int
    default_currency_code: str


def _normalize_currency_code(value: str) -> str:
    raw = value.strip().upper()
    if raw in {"", "0001", "NTD", "TWD"}:
        return "TWD"
    return raw[:3]


def _decimal_places_from_row(row: list[str]) -> int:
    candidates: list[int] = []
    for index in _DECIMAL_PLACE_INDICES:
        if index >= len(row):
            continue
        text = row[index].strip()
        if not text:
            continue
        candidates.append(int(text))
    if not candidates:
        return 2
    return max(candidates)


def _symbol_for_currency(code: str) -> str:
    return _CURRENCY_SYMBOLS.get(code, code)


def _load_currency_source(export_dir: Path) -> CurrencyImportSource:
    csv_path = export_dir / _TBSCURRENCY_FILENAME
    if not csv_path.exists():
        raise FileNotFoundError(f"Currency export not found: {csv_path}")

    rows: list[CurrencySettingRow] = []
    seen_codes: set[str] = set()
    default_currency_code: str | None = None
    column_count = 0

    for parsed_row in iter_legacy_rows(csv_path):
        if len(parsed_row) < _EXPECTED_COLUMN_COUNT:
            raise ValueError(
                f"Malformed currency row in {csv_path.name}: expected at least "
                f"{_EXPECTED_COLUMN_COUNT} columns, got {len(parsed_row)}"
            )

        code = _normalize_currency_code(parsed_row[_SOURCE_CODE_INDEX])
        if not code:
            raise ValueError(f"Currency row in {csv_path.name} is missing a currency code")
        if code in seen_codes:
            raise ValueError(f"Duplicate currency code in {csv_path.name}: {code}")
        seen_codes.add(code)

        row = CurrencySettingRow(
            code=code,
            symbol=_symbol_for_currency(code),
            decimal_places=_decimal_places_from_row(parsed_row),
            is_default=parsed_row[_DEFAULT_FLAG_INDEX].strip() == "1",
        )
        rows.append(row)
        column_count = max(column_count, len(parsed_row))

        if row.is_default:
            if default_currency_code and default_currency_code != row.code:
                raise ValueError(
                    f"Multiple default currencies found in {csv_path.name}: "
                    f"{default_currency_code}, {row.code}"
                )
            default_currency_code = row.code

    if not rows:
        raise ValueError(f"No currency rows found in {csv_path.name}")
    if default_currency_code is None:
        raise ValueError(f"No default currency found in {csv_path.name}")

    return CurrencyImportSource(
        csv_path=csv_path,
        rows=tuple(rows),
        column_count=column_count,
        default_currency_code=default_currency_code,
    )


async def _next_batch_attempt_number(
    session,
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


async def _upsert_app_setting(session, *, key: str, value: str) -> None:
    statement = insert(AppSetting).values(key=key, value=value)
    statement = statement.on_conflict_do_update(
        index_elements=[AppSetting.key],
        set_={"value": value, "updated_at": func.now()},
    )
    await session.execute(statement)


async def _record_failed_currency_import_attempt(
    *,
    tenant_id: uuid.UUID,
    batch_id: str,
    attempt_number: int,
    export_dir: Path,
    error_message: str,
    expected_row_count: int | None,
    column_count: int,
    source_file: str,
) -> None:
    completed_at = datetime.now(tz=UTC)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            run = LegacyImportRun(
                tenant_id=tenant_id,
                batch_id=batch_id,
                source_path=str(export_dir),
                target_schema=_TARGET_SCHEMA,
                attempt_number=attempt_number,
                requested_tables=[_TBSCURRENCY_TABLE_NAME],
                status="failed",
                error_message=error_message,
                completed_at=completed_at,
            )
            session.add(run)
            await session.flush()

            session.add(
                LegacyImportTableRun(
                    run_id=run.id,
                    table_name=_TBSCURRENCY_TABLE_NAME,
                    source_file=source_file,
                    expected_row_count=expected_row_count,
                    loaded_row_count=0,
                    column_count=column_count,
                    status="failed",
                    error_message=error_message,
                    completed_at=completed_at,
                )
            )


async def run_currency_import(
    *,
    batch_id: str = _DEFAULT_BATCH_ID,
    export_dir: Path | None = None,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
) -> CurrencyImportResult:
    resolved_export_dir = resolve_dump_data_dir(export_dir, argument_name="--export-dir")
    source = _load_currency_source(resolved_export_dir)
    attempt_number: int | None = None

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                attempt_number = await _next_batch_attempt_number(session, tenant_id, batch_id)
                run = LegacyImportRun(
                    tenant_id=tenant_id,
                    batch_id=batch_id,
                    source_path=str(resolved_export_dir),
                    target_schema=_TARGET_SCHEMA,
                    attempt_number=attempt_number,
                    requested_tables=[_TBSCURRENCY_TABLE_NAME],
                    status="running",
                )
                session.add(run)
                await session.flush()

                table_run = LegacyImportTableRun(
                    run_id=run.id,
                    table_name=_TBSCURRENCY_TABLE_NAME,
                    source_file=source.csv_path.name,
                    expected_row_count=len(source.rows),
                    status="running",
                )
                session.add(table_run)
                await session.flush()

                for row in source.rows:
                    await _upsert_app_setting(
                        session,
                        key=f"currency.{row.code}.symbol",
                        value=row.symbol,
                    )
                    await _upsert_app_setting(
                        session,
                        key=f"currency.{row.code}.decimal_places",
                        value=str(row.decimal_places),
                    )

                await _upsert_app_setting(
                    session,
                    key="currency.default",
                    value=source.default_currency_code,
                )

                completed_at = datetime.now(tz=UTC)
                table_run.loaded_row_count = len(source.rows)
                table_run.column_count = source.column_count
                table_run.status = "completed"
                table_run.completed_at = completed_at
                run.status = "completed"
                run.completed_at = completed_at

    except Exception as exc:
        if attempt_number is not None:
            await _record_failed_currency_import_attempt(
                tenant_id=tenant_id,
                batch_id=batch_id,
                attempt_number=attempt_number,
                export_dir=resolved_export_dir,
                error_message=str(exc),
                expected_row_count=len(source.rows),
                column_count=source.column_count,
                source_file=source.csv_path.name,
            )
        raise

    return CurrencyImportResult(
        batch_id=batch_id,
        source_file=source.csv_path,
        attempt_number=attempt_number or 1,
        currency_count=len(source.rows),
        upserted_setting_count=(len(source.rows) * 2) + 1,
        default_currency_code=source.default_currency_code,
    )