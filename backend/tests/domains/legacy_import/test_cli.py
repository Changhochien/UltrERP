from __future__ import annotations

from pathlib import Path

import pytest

from domains.legacy_import import cli
from domains.legacy_import.currency import CurrencyImportResult
from domains.legacy_import.mapping import (
    ProductMappingBatchResult,
    ProductMappingReviewExportResult,
    ProductMappingReviewImportResult,
)
from domains.legacy_import.staging import StageBatchResult, StageTableResult
from domains.legacy_import.validation import (
    ImportReplayMetadata,
    MigrationBatchValidationResult,
    MigrationValidationReport,
    ProductMappingValidationSummary,
)


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


def test_stage_cli_rejects_invalid_tenant_id(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["stage", "--batch-id", "batch-001", "--tenant-id", "invalid"])

    assert exc_info.value.code == 2
    assert "tenant-id must be a valid UUID" in capsys.readouterr().err


def test_map_products_cli_invokes_mapping_seed(monkeypatch, capsys) -> None:
    async def fake_run_product_mapping_seed(**kwargs):
        assert kwargs["batch_id"] == "batch-003"
        assert kwargs["schema_name"] is None
        return ProductMappingBatchResult(
            batch_id="batch-003",
            schema_name="raw_legacy",
            mapping_count=2,
            candidate_count=1,
            exact_match_count=1,
            unknown_count=1,
            orphan_code_count=1,
            orphan_row_count=3,
        )

    monkeypatch.setattr(cli, "run_product_mapping_seed", fake_run_product_mapping_seed)

    result = cli.main(["map-products", "--batch-id", "batch-003"])
    output = capsys.readouterr().out

    assert result == 0
    assert "Mapped batch batch-003" in output
    assert "orphans=1/3" in output


def test_export_product_review_cli_invokes_export(monkeypatch, capsys, tmp_path: Path) -> None:
    output_path = tmp_path / "review.csv"

    async def fake_export_product_mapping_review(**kwargs):
        assert kwargs["batch_id"] == "batch-003"
        assert kwargs["output_path"] == output_path
        assert kwargs["schema_name"] is None
        return ProductMappingReviewExportResult(
            batch_id="batch-003",
            schema_name="raw_legacy",
            output_path=output_path,
            exported_row_count=4,
        )

    monkeypatch.setattr(
        cli,
        "export_product_mapping_review",
        fake_export_product_mapping_review,
    )

    result = cli.main(
        ["export-product-review", "--batch-id", "batch-003", "--output", str(output_path)]
    )
    output = capsys.readouterr().out

    assert result == 0
    assert "Exported 4 review rows" in output


def test_import_product_review_cli_invokes_import(monkeypatch, capsys, tmp_path: Path) -> None:
    input_path = tmp_path / "review.csv"

    async def fake_import_product_mapping_review(**kwargs):
        assert kwargs["batch_id"] == "batch-003"
        assert kwargs["input_path"] == input_path
        assert kwargs["approved_by"] == "analyst@example.com"
        assert kwargs["schema_name"] is None
        return ProductMappingReviewImportResult(
            batch_id="batch-003",
            schema_name="raw_legacy",
            input_path=input_path,
            applied_decision_count=2,
        )

    monkeypatch.setattr(
        cli,
        "import_product_mapping_review",
        fake_import_product_mapping_review,
    )

    result = cli.main(
        [
            "import-product-review",
            "--batch-id",
            "batch-003",
            "--input",
            str(input_path),
            "--approved-by",
            "analyst@example.com",
        ]
    )
    output = capsys.readouterr().out

    assert result == 0
    assert "Imported 2 review decisions" in output


def test_currency_import_cli_invokes_import(monkeypatch, capsys, tmp_path: Path) -> None:
    async def fake_run_currency_import(**kwargs):
        assert kwargs["batch_id"] == "currency-settings"
        assert kwargs["export_dir"] == tmp_path
        return CurrencyImportResult(
            batch_id="currency-settings",
            source_file=tmp_path / "tbscurrency.csv",
            attempt_number=1,
            currency_count=6,
            upserted_setting_count=13,
            default_currency_code="TWD",
        )

    monkeypatch.setattr(cli, "run_currency_import", fake_run_currency_import)

    result = cli.main(["currency-import", "--export-dir", str(tmp_path)])
    output = capsys.readouterr().out

    assert result == 0
    assert "Imported 6 currencies" in output
    assert "default=TWD" in output


def test_validate_import_cli_invokes_validation(monkeypatch, capsys, tmp_path: Path) -> None:
    async def fake_validate_import_batch(**kwargs):
        assert kwargs["batch_id"] == "batch-155"
        assert kwargs["attempt_number"] is None
        return MigrationBatchValidationResult(
            report=MigrationValidationReport(
                batch_id="batch-155",
                tenant_id="00000000-0000-0000-0000-000000000001",
                schema_name="raw_legacy",
                attempt_number=2,
                status="blocked",
                blocking_issue_count=1,
                stage_reconciliation=(),
                mapping_summary=ProductMappingValidationSummary(
                    mapping_count=3,
                    candidate_count=1,
                    unknown_count=1,
                    orphan_code_count=1,
                    orphan_row_count=2,
                ),
                failed_stages=(),
                issues=(),
                replay=ImportReplayMetadata(
                    scope_key="scope-155",
                    scope_cutoff_date="2024-08-31",
                    disposition="replayed-scope",
                    previous_batch_id="batch-154",
                    previous_attempt_number=1,
                ),
                epic13_handoff={"scope_key": "scope-155", "lineage_count": 8},
            ),
            json_path=tmp_path / "batch-155-validation.json",
            markdown_path=tmp_path / "batch-155-validation.md",
        )

    monkeypatch.setattr(cli, "validate_import_batch", fake_validate_import_batch, raising=False)

    result = cli.main(["validate-import", "--batch-id", "batch-155"])
    output = capsys.readouterr().out

    assert result == 1
    assert "Validated batch batch-155" in output
    assert "status=blocked" in output
    assert "scope=scope-155" in output
    assert "json=" in output
    assert "markdown=" in output


def test_validate_import_cli_passes_attempt_number(monkeypatch, capsys, tmp_path: Path) -> None:
    async def fake_validate_import_batch(**kwargs):
        assert kwargs["batch_id"] == "batch-155"
        assert kwargs["attempt_number"] == 2
        return MigrationBatchValidationResult(
            report=MigrationValidationReport(
                batch_id="batch-155",
                tenant_id="00000000-0000-0000-0000-000000000001",
                schema_name="raw_legacy",
                attempt_number=2,
                status="clean",
                blocking_issue_count=0,
                stage_reconciliation=(),
                mapping_summary=ProductMappingValidationSummary(
                    mapping_count=3,
                    candidate_count=1,
                    unknown_count=0,
                    orphan_code_count=0,
                    orphan_row_count=0,
                ),
                failed_stages=(),
                issues=(),
                replay=ImportReplayMetadata(
                    scope_key="scope-155",
                    scope_cutoff_date="2024-08-31",
                    disposition="new-scope",
                ),
                epic13_handoff={"scope_key": "scope-155", "lineage_count": 8, "holding_count": 0},
            ),
            json_path=tmp_path / "batch-155-validation.json",
            markdown_path=tmp_path / "batch-155-validation.md",
        )

    monkeypatch.setattr(cli, "validate_import_batch", fake_validate_import_batch, raising=False)

    result = cli.main(["validate-import", "--batch-id", "batch-155", "--attempt-number", "2"])
    output = capsys.readouterr().out

    assert result == 0
    assert "Validated batch batch-155" in output
    assert "status=clean" in output
    assert "json=" in output
    assert "markdown=" in output
