"""Legacy raw-staging import helpers and orchestration."""

from __future__ import annotations

import csv
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import asyncpg
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url

from common.config import settings
from common.database import AsyncSessionLocal
from common.models.legacy_import import LegacyImportRun, LegacyImportTableRun
from common.tenant import DEFAULT_TENANT_ID

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_MANIFEST_ROW_RE = re.compile(r"^\|\s*([a-z0-9_]+)\s*\|\s*([0-9,]+)\s*\|")


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


@dataclass(slots=True, frozen=True)
class StageBatchResult:
	batch_id: str
	schema_name: str
	source_dir: Path
	tables: tuple[StageTableResult, ...]


class RawStageConnection(Protocol):
	async def execute(self, query: str) -> str: ...

	async def copy_records_to_table(
		self,
		table_name: str,
		*,
		schema_name: str | None = None,
		columns: list[str] | tuple[str, ...] | None = None,
		records: object,
	) -> str: ...


def parse_legacy_row(raw_line: str) -> list[str]:
	"""Parse the legacy export row format into individual text fields."""

	line = raw_line.strip()
	if not line:
		return []

	if line.startswith('"') and line.endswith('"'):
		line = line[1:-1]

	try:
		row = next(csv.reader([line], delimiter=",", quotechar="'", skipinitialspace=True))
	except (csv.Error, StopIteration):
		row = [part.strip().strip("'") for part in line.split("', '")]

	return [field.strip() for field in row]


def iter_legacy_rows(csv_path: Path):
	with csv_path.open("r", encoding="utf-8", newline="") as handle:
		for raw_line in handle:
			row = parse_legacy_row(raw_line)
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


def discover_legacy_tables(
	source_dir: Path,
	required_tables: tuple[str, ...] | list[str],
	selected_tables: tuple[str, ...] | list[str] | None = None,
) -> list[DiscoveredLegacyTable]:
	if not source_dir.exists():
		raise FileNotFoundError(f"Legacy export directory does not exist: {source_dir}")

	manifest_counts = parse_manifest_rows(source_dir / "MANIFEST.md")
	selected = tuple(selected_tables or ())
	csv_files = sorted(source_dir.glob("*.csv"))
	if not csv_files:
		raise FileNotFoundError(f"No CSV files found in legacy export directory: {source_dir}")

	discovered = {
		path.stem: DiscoveredLegacyTable(
			table_name=path.stem,
			csv_path=path,
			expected_row_count=manifest_counts.get(path.stem),
		)
		for path in csv_files
	}

	missing_required = [table for table in required_tables if table not in discovered]
	if missing_required:
		missing = ", ".join(sorted(missing_required))
		raise FileNotFoundError(f"Missing required legacy tables: {missing}")

	if selected:
		missing_selected = [table for table in selected if table not in discovered]
		if missing_selected:
			missing = ", ".join(sorted(missing_selected))
			raise FileNotFoundError(f"Requested legacy tables not found: {missing}")
		return [discovered[table] for table in selected]

	return [discovered[name] for name in sorted(discovered)]


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


def _analyze_legacy_file(table: DiscoveredLegacyTable) -> tuple[int, int]:
	row_count = 0
	column_count = 0
	for row in iter_legacy_rows(table.csv_path):
		row_count += 1
		column_count = max(column_count, len(row))

	if row_count == 0:
		raise ValueError(f"No importable rows found in {table.csv_path.name}")

	if table.expected_row_count is not None and row_count != table.expected_row_count:
		raise ValueError(
			f"Manifest row count mismatch for {table.table_name}: "
			f"expected {table.expected_row_count}, got {row_count}"
		)

	return row_count, column_count


def _iter_stage_records(table: DiscoveredLegacyTable, batch_id: str, column_count: int):
	for row_number, row in enumerate(iter_legacy_rows(table.csv_path), start=1):
		padded = row + [None] * (column_count - len(row))
		yield (
			*padded,
			table.table_name,
			table.csv_path.name,
			row_number,
			batch_id,
			"loaded",
			str(row_number),
		)


async def _recreate_stage_table(
	connection: RawStageConnection,
	*,
	schema_name: str,
	table_name: str,
	column_count: int,
) -> None:
	quoted_schema = _quoted_identifier(schema_name)
	quoted_table = _quoted_identifier(table_name)
	column_defs = [
		f'{_quoted_identifier(f"col_{index}")} TEXT'
		for index in range(1, column_count + 1)
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
	await connection.execute(f"DROP TABLE IF EXISTS {quoted_schema}.{quoted_table} CASCADE")
	create_sql = f"CREATE TABLE {quoted_schema}.{quoted_table} ({', '.join(column_defs)})"
	await connection.execute(create_sql)


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
	await connection.copy_records_to_table(
		table.table_name,
		schema_name=schema_name,
		columns=columns,
		records=_iter_stage_records(table, batch_id, column_count),
	)
	return StageTableResult(
		table_name=table.table_name,
		row_count=row_count,
		column_count=column_count,
		source_file=table.csv_path.name,
	)


def _asyncpg_dsn(database_url: str) -> str:
	url = make_url(database_url)
	drivername = url.drivername.split("+", 1)[0]
	return url.set(drivername=drivername).render_as_string(hide_password=False)


async def _open_raw_connection() -> asyncpg.Connection:
	return await asyncpg.connect(dsn=_asyncpg_dsn(settings.database_url), command_timeout=60)


async def _replace_existing_batch(tenant_id: uuid.UUID, batch_id: str) -> None:
	async with AsyncSessionLocal() as session:
		existing_ids = list(
			await session.scalars(
				select(LegacyImportRun.id).where(
					LegacyImportRun.tenant_id == tenant_id,
					LegacyImportRun.batch_id == batch_id,
				)
			)
		)
		if not existing_ids:
			return

		await session.execute(
			delete(LegacyImportTableRun).where(LegacyImportTableRun.run_id.in_(existing_ids))
		)
		await session.execute(
			delete(LegacyImportRun).where(
				LegacyImportRun.tenant_id == tenant_id,
				LegacyImportRun.batch_id == batch_id,
			)
		)
		await session.commit()


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
	discovered_tables = discover_legacy_tables(
		resolved_source_dir,
		list(settings.legacy_import_required_tables),
		selected_tables,
	)

	await _replace_existing_batch(tenant_id, batch_id)

	async with AsyncSessionLocal() as session:
		run = LegacyImportRun(
			tenant_id=tenant_id,
			batch_id=batch_id,
			source_path=str(resolved_source_dir),
			target_schema=resolved_schema,
			requested_tables=list(selected_tables) if selected_tables else None,
			status="running",
		)
		session.add(run)
		await session.flush()

		connection = await _open_raw_connection()
		results: list[StageTableResult] = []
		try:
			for table in discovered_tables:
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
					table_run.status = "failed"
					table_run.error_message = str(exc)
					table_run.completed_at = datetime.now(tz=UTC)
					run.status = "failed"
					run.error_message = str(exc)
					run.completed_at = datetime.now(tz=UTC)
					await session.commit()
					raise

				table_run.status = "completed"
				table_run.loaded_row_count = result.row_count
				table_run.column_count = result.column_count
				table_run.completed_at = datetime.now(tz=UTC)
				results.append(result)
				await session.flush()

			run.status = "completed"
			run.completed_at = datetime.now(tz=UTC)
			await session.commit()
		finally:
			await connection.close()

	return StageBatchResult(
		batch_id=batch_id,
		schema_name=resolved_schema,
		source_dir=resolved_source_dir,
		tables=tuple(results),
	)