from __future__ import annotations

from pathlib import Path

import asyncpg
import pytest

from domains.legacy_import import cli
from domains.legacy_import.ap_payment_import import SupplierPaymentImportResult
from domains.legacy_import.category_review import (
    ProductCategoryReviewExportResult,
    ProductCategoryReviewImportResult,
)
from domains.legacy_import.currency import CurrencyImportResult
from domains.legacy_import.mapping import (
    ProductMappingBatchResult,
    ProductMappingReviewExportResult,
    ProductMappingReviewImportResult,
)
from domains.legacy_import.staging import (
    LegacySourceCompatibilityError,
    StageBatchResult,
    StageSourceDescriptor,
    StageTableResult,
)
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
            source_descriptor=StageSourceDescriptor.file(Path("/tmp/legacy-data")),
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


def test_live_stage_cli_invokes_live_stage_import(monkeypatch, capsys) -> None:
    async def fake_run_live_stage_import(**kwargs):
        assert kwargs["batch_id"] == "batch-live-001"
        assert kwargs["source_schema"] == "public"
        assert kwargs["selected_tables"] == ("tbscust", "tbsstock")
        return StageBatchResult(
            batch_id="batch-live-001",
            schema_name="raw_legacy",
            source_descriptor=StageSourceDescriptor.live(
                database="cao50001",
                schema_name="public",
            ),
            tables=(
                StageTableResult(
                    table_name="tbscust",
                    row_count=2,
                    column_count=3,
                    source_file="public.tbscust",
                ),
                StageTableResult(
                    table_name="tbsstock",
                    row_count=1,
                    column_count=4,
                    source_file="public.tbsstock",
                ),
            ),
        )

    monkeypatch.setattr(cli, "run_live_stage_import", fake_run_live_stage_import)

    result = cli.main(
        [
            "live-stage",
            "--batch-id",
            "batch-live-001",
            "--table",
            "tbscust",
            "--table",
            "tbsstock",
        ]
    )
    output = capsys.readouterr().out

    assert result == 0
    assert "from legacy-db:cao50001/public" in output
    assert "tbscust: 2 rows" in output
    assert "tbsstock: 1 rows" in output


def test_live_stage_cli_reports_connection_failures(monkeypatch, capsys) -> None:
    async def fake_run_live_stage_import(**kwargs):
        raise OSError("timed out")

    monkeypatch.setattr(cli, "run_live_stage_import", fake_run_live_stage_import)

    result = cli.main(["live-stage", "--batch-id", "batch-live-002"])
    captured = capsys.readouterr()

    assert result == 1
    assert "Live legacy DB connection failed" in captured.err
    assert "timed out" in captured.err


def test_live_stage_cli_reports_connect_time_postgres_errors_as_connection_failures(
    monkeypatch, capsys
) -> None:
    async def fake_run_live_stage_import(**kwargs):
        raise asyncpg.InvalidCatalogNameError('database "missing" does not exist')

    monkeypatch.setattr(cli, "run_live_stage_import", fake_run_live_stage_import)

    result = cli.main(["live-stage", "--batch-id", "batch-live-002b"])
    captured = capsys.readouterr()

    assert result == 1
    assert "Live legacy DB connection failed" in captured.err
    assert 'database "missing" does not exist' in captured.err


def test_live_stage_cli_reports_discovery_failures(monkeypatch, capsys) -> None:
    async def fake_run_live_stage_import(**kwargs):
        raise LegacySourceCompatibilityError(
            "Requested live-source tables not found in public: missing_table"
        )

    monkeypatch.setattr(cli, "run_live_stage_import", fake_run_live_stage_import)

    result = cli.main(["live-stage", "--batch-id", "batch-live-003", "--table", "missing_table"])
    captured = capsys.readouterr()

    assert result == 1
    assert "Live legacy table discovery failed" in captured.err
    assert "missing_table" in captured.err


def test_print_stage_summary_supports_source_agnostic_descriptors(capsys) -> None:
    cli._print_stage_summary(
        StageBatchResult(
            batch_id="batch-010",
            schema_name="raw_legacy",
            source_descriptor=StageSourceDescriptor.live(
                database="cao50001",
                schema_name="public",
            ),
            tables=(
                StageTableResult(
                    table_name="tbscust",
                    row_count=2,
                    column_count=3,
                    source_file="public.tbscust",
                ),
            ),
        )
    )

    output = capsys.readouterr().out

    assert "from legacy-db:cao50001/public" in output
    assert "source=public.tbscust" in output


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


def test_export_category_review_cli_invokes_export(monkeypatch, capsys, tmp_path: Path) -> None:
    output_path = tmp_path / "category-review.csv"

    async def fake_export_product_category_review(**kwargs):
        assert kwargs["batch_id"] == "batch-003"
        assert kwargs["output_path"] == output_path
        assert kwargs["schema_name"] is None
        return ProductCategoryReviewExportResult(
            batch_id="batch-003",
            schema_name="raw_legacy",
            output_path=output_path,
            exported_row_count=3,
        )

    monkeypatch.setattr(
        cli,
        "export_product_category_review",
        fake_export_product_category_review,
        raising=False,
    )

    result = cli.main(
        ["export-category-review", "--batch-id", "batch-003", "--output", str(output_path)]
    )
    output = capsys.readouterr().out

    assert result == 0
    assert "Exported 3 category review rows" in output


def test_import_category_review_cli_invokes_import(monkeypatch, capsys, tmp_path: Path) -> None:
    input_path = tmp_path / "category-review.csv"

    async def fake_import_product_category_review(**kwargs):
        assert kwargs["batch_id"] == "batch-003"
        assert kwargs["input_path"] == input_path
        assert kwargs["approved_by"] == "analyst@example.com"
        assert kwargs["schema_name"] is None
        return ProductCategoryReviewImportResult(
            batch_id="batch-003",
            schema_name="raw_legacy",
            input_path=input_path,
            applied_decision_count=2,
        )

    monkeypatch.setattr(
        cli,
        "import_product_category_review",
        fake_import_product_category_review,
        raising=False,
    )

    result = cli.main(
        [
            "import-category-review",
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
    assert "Imported 2 category review decisions" in output


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


def test_ap_payment_import_cli_invokes_import(monkeypatch, capsys) -> None:
    async def fake_run_ap_payment_import(**kwargs):
        assert kwargs["batch_id"] == "batch-201"
        assert kwargs["schema_name"] is None
        return SupplierPaymentImportResult(
            batch_id="batch-201",
            schema_name="raw_legacy",
            attempt_number=2,
            payment_count=1,
            allocation_count=0,
            holding_count=5,
            lineage_count=1,
        )

    monkeypatch.setattr(cli, "run_ap_payment_import", fake_run_ap_payment_import)

    result = cli.main(["ap-payment-import", "--batch-id", "batch-201"])
    output = capsys.readouterr().out

    assert result == 0
    assert "AP payment imported batch batch-201" in output
    assert "payments=1" in output
    assert "holding=5" in output


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


def test_validate_import_cli_rejects_negative_attempt_number(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["validate-import", "--batch-id", "batch-155", "--attempt-number", "-1"])

    assert exc_info.value.code == 2
    assert "value must be a non-negative integer" in capsys.readouterr().err
