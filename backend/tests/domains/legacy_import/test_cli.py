from __future__ import annotations

from pathlib import Path

from domains.legacy_import import cli
from domains.legacy_import.staging import StageBatchResult, StageTableResult


def test_stage_cli_invokes_stage_import(monkeypatch, capsys) -> None:
	async def fake_run_stage_import(**kwargs):
		assert kwargs["batch_id"] == "batch-001"
		assert kwargs["selected_tables"] == ("tbscust",)
		return StageBatchResult(
			batch_id="batch-001",
			schema_name="raw_legacy",
			source_dir=Path("/tmp/legacy-data"),
			tables=(
				StageTableResult(
					table_name="tbscust",
					row_count=2,
					column_count=3,
					source_file="tbscust.csv",
				),
			),
		)

	monkeypatch.setattr(cli, "run_stage_import", fake_run_stage_import)

	result = cli.main(["stage", "--batch-id", "batch-001", "--table", "tbscust"])
	output = capsys.readouterr().out

	assert result == 0
	assert "batch batch-001" in output
	assert "tbscust: 2 rows" in output