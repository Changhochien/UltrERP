from __future__ import annotations

from pathlib import Path

import pytest

from domains.legacy_import.staging import (
	DiscoveredLegacyTable,
	discover_legacy_tables,
	parse_legacy_row,
	parse_manifest_rows,
	stage_table,
)


class FakeRawStageConnection:
	def __init__(self) -> None:
		self.executed: list[str] = []
		self.copy_calls: list[dict[str, object]] = []

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
	) -> str:
		rows = list(records)
		self.copy_calls.append(
			{
				"table_name": table_name,
				"schema_name": schema_name,
				"columns": tuple(columns or ()),
				"rows": rows,
			}
		)
		return f"COPY {len(rows)}"


def test_parse_legacy_row_handles_wrapped_export_format() -> None:
	row = parse_legacy_row('"\'1149\', \'2\', \'昌弘五金實業有限公司\'"')

	assert row == ["1149", "2", "昌弘五金實業有限公司"]


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
	(tmp_path / "tbscust.csv").write_text('"\'1\', \'A\'"\n', encoding="utf-8")

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
	(tmp_path / "tbscust.csv").write_text('"\'1\', \'A\'"\n"\'2\', \'B\'"\n', encoding="utf-8")
	(tmp_path / "tbsstock.csv").write_text('"\'P001\', \'Widget\'"\n', encoding="utf-8")

	tables = discover_legacy_tables(tmp_path, ["tbscust", "tbsstock"])

	assert [table.table_name for table in tables] == ["tbscust", "tbsstock"]
	assert tables[0].expected_row_count == 2
	assert tables[1].expected_row_count == 1


@pytest.mark.asyncio
async def test_stage_table_uses_copy_records_and_lineage(tmp_path: Path) -> None:
	data_file = tmp_path / "tbscust.csv"
	data_file.write_text(
		'"\'1\', \'A\', \'Alpha\'"\n"\'2\', \'B\', \'Beta\'"\n',
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
		"DROP TABLE IF EXISTS \"raw_legacy\".\"tbscust\"" in query
		for query in connection.executed
	)
	assert len(connection.copy_calls) == 1
	copy_call = connection.copy_calls[0]
	assert copy_call["table_name"] == "tbscust"
	assert copy_call["schema_name"] == "raw_legacy"
	first_row = copy_call["rows"][0]
	assert first_row[0:3] == ("1", "A", "Alpha")
	assert first_row[-4:] == (1, "batch-001", "loaded", "1")


@pytest.mark.asyncio
async def test_stage_table_fails_on_manifest_row_count_mismatch(tmp_path: Path) -> None:
	data_file = tmp_path / "tbscust.csv"
	data_file.write_text('"\'1\', \'A\'"\n', encoding="utf-8")
	table = DiscoveredLegacyTable("tbscust", data_file, expected_row_count=2)

	with pytest.raises(ValueError, match="Manifest row count mismatch"):
		await stage_table(
			FakeRawStageConnection(),
			table=table,
			schema_name="raw_legacy",
			batch_id="batch-001",
		)