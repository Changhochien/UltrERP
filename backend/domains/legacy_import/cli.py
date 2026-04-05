"""CLI entry point for legacy import workflows."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path

from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.canonical import CanonicalImportResult, run_canonical_import
from domains.legacy_import.extractor_cleaner import MojibakeCleaner
from domains.legacy_import.extractor_detector import EncodingDetector
from domains.legacy_import.extractor_parser import SQLDumpParser, TableData
from domains.legacy_import.mapping import (
    ProductMappingBatchResult,
    ProductMappingReviewExportResult,
    ProductMappingReviewImportResult,
    export_product_mapping_review,
    import_product_mapping_review,
    run_product_mapping_seed,
)
from domains.legacy_import.normalization import NormalizationBatchResult, run_normalization
from domains.legacy_import.staging import StageBatchResult, run_stage_import
from domains.legacy_import.validation import MigrationBatchValidationResult, validate_import_batch


def _parse_tenant_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("tenant-id must be a valid UUID") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="legacy-import", description="Legacy ERP import CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage_parser = subparsers.add_parser(
        "stage",
        help="Load extracted legacy CSVs into the raw staging schema",
    )
    stage_parser.add_argument("--batch-id", required=True, help="Deterministic batch identifier")
    stage_parser.add_argument("--source-dir", help="Override legacy export directory")
    stage_parser.add_argument("--schema", help="Override target raw schema name")
    stage_parser.add_argument(
        "--tenant-id",
        type=_parse_tenant_uuid,
        default=DEFAULT_TENANT_ID,
        help="Tenant UUID for control-table tracking",
    )
    stage_parser.add_argument(
        "--table",
        action="append",
        dest="tables",
        help="Limit staging to specific table names (repeatable)",
    )

    normalize_parser = subparsers.add_parser(
        "normalize",
        help="Normalize staged master data into canonical prep tables",
    )
    normalize_parser.add_argument("--batch-id", required=True, help="Batch identifier to normalize")
    normalize_parser.add_argument("--schema", help="Override target raw schema name")
    normalize_parser.add_argument(
        "--tenant-id",
        type=_parse_tenant_uuid,
        default=DEFAULT_TENANT_ID,
        help="Tenant UUID for normalized prep records",
    )

    map_products_parser = subparsers.add_parser(
        "map-products",
        help="Seed auditable product-code mappings from staged sales detail rows",
    )
    map_products_parser.add_argument(
        "--batch-id",
        required=True,
        help="Batch identifier to analyze",
    )
    map_products_parser.add_argument("--schema", help="Override target raw schema name")
    map_products_parser.add_argument(
        "--tenant-id",
        type=_parse_tenant_uuid,
        default=DEFAULT_TENANT_ID,
        help="Tenant UUID for mapping records",
    )

    export_review_parser = subparsers.add_parser(
        "export-product-review",
        help="Export unresolved product-code mappings and review candidates to CSV",
    )
    export_review_parser.add_argument(
        "--batch-id",
        required=True,
        help="Batch identifier to export",
    )
    export_review_parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="CSV path for analyst review export",
    )
    export_review_parser.add_argument("--schema", help="Override target raw schema name")
    export_review_parser.add_argument(
        "--tenant-id",
        type=_parse_tenant_uuid,
        default=DEFAULT_TENANT_ID,
        help="Tenant UUID for review export",
    )

    import_review_parser = subparsers.add_parser(
        "import-product-review",
        help="Import analyst-reviewed product-code mapping decisions from CSV",
    )
    import_review_parser.add_argument(
        "--batch-id",
        required=True,
        help="Batch identifier to update",
    )
    import_review_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="CSV path containing analyst review decisions",
    )
    import_review_parser.add_argument(
        "--approved-by",
        required=True,
        help="Operator or analyst identifier recorded on approved mappings",
    )
    import_review_parser.add_argument("--schema", help="Override target raw schema name")
    import_review_parser.add_argument(
        "--tenant-id",
        type=_parse_tenant_uuid,
        default=DEFAULT_TENANT_ID,
        help="Tenant UUID for review import",
    )
    canonical_parser = subparsers.add_parser(
        "canonical-import",
        help="Import normalized legacy data into supported canonical tables",
    )
    canonical_parser.add_argument("--batch-id", required=True, help="Batch identifier to import")
    canonical_parser.add_argument("--schema", help="Override target raw schema name")
    canonical_parser.add_argument(
        "--tenant-id",
        type=_parse_tenant_uuid,
        default=DEFAULT_TENANT_ID,
        help="Tenant UUID for canonical import records",
    )
    validate_parser = subparsers.add_parser(
        "validate-import",
        help="Validate an imported legacy batch and emit JSON/Markdown artifacts",
    )
    validate_parser.add_argument("--batch-id", required=True, help="Batch identifier to validate")
    validate_parser.add_argument(
        "--attempt-number",
        type=int,
        help="Specific canonical import attempt number to validate",
    )
    validate_parser.add_argument("--schema", help="Override target raw schema name")
    validate_parser.add_argument(
        "--tenant-id",
        type=_parse_tenant_uuid,
        default=DEFAULT_TENANT_ID,
        help="Tenant UUID for validation and replay metadata",
    )

    extract_parser = subparsers.add_parser(
        "extract",
        help="Decode a legacy SQL dump file into CSV/JSON files",
    )
    extract_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input SQL dump file path",
    )
    extract_parser.add_argument(
        "--output",
        type=Path,
        default=Path("extracted_data"),
        help="Output directory for extracted files (default: extracted_data/)",
    )
    extract_parser.add_argument(
        "--format",
        choices=["csv", "json", "both"],
        default="csv",
        help="Output format (default: csv)",
    )
    extract_parser.add_argument(
        "--encoding",
        help="Force source encoding (auto-detected if not specified)",
    )
    return parser


async def _run_stage(args: argparse.Namespace) -> int:
    result = await run_stage_import(
        batch_id=args.batch_id,
        source_dir=args.source_dir,
        selected_tables=tuple(args.tables or ()),
        tenant_id=args.tenant_id,
        schema_name=args.schema,
    )
    _print_stage_summary(result)
    return 0


async def _run_normalize(args: argparse.Namespace) -> int:
    result = await run_normalization(
        batch_id=args.batch_id,
        tenant_id=args.tenant_id,
        schema_name=args.schema,
    )
    _print_normalize_summary(result)
    return 0


async def _run_map_products(args: argparse.Namespace) -> int:
    result = await run_product_mapping_seed(
        batch_id=args.batch_id,
        tenant_id=args.tenant_id,
        schema_name=args.schema,
    )
    _print_product_mapping_summary(result)
    return 0


async def _run_export_product_review(args: argparse.Namespace) -> int:
    result = await export_product_mapping_review(
        batch_id=args.batch_id,
        output_path=args.output,
        tenant_id=args.tenant_id,
        schema_name=args.schema,
    )
    _print_product_mapping_review_export_summary(result)
    return 0


async def _run_import_product_review(args: argparse.Namespace) -> int:
    result = await import_product_mapping_review(
        batch_id=args.batch_id,
        input_path=args.input,
        approved_by=args.approved_by,
        tenant_id=args.tenant_id,
        schema_name=args.schema,
    )
    _print_product_mapping_review_import_summary(result)
    return 0


async def _run_canonical_import(args: argparse.Namespace) -> int:
    result = await run_canonical_import(
        batch_id=args.batch_id,
        tenant_id=args.tenant_id,
        schema_name=args.schema,
    )
    _print_canonical_import_summary(result)
    return 0


async def _run_validate_import(args: argparse.Namespace) -> int:
    result = await validate_import_batch(
        batch_id=args.batch_id,
        tenant_id=args.tenant_id,
        schema_name=args.schema,
        attempt_number=args.attempt_number,
    )
    _print_validation_summary(result)
    return 1 if result.report.status == "blocked" else 0


def _run_extract(args: argparse.Namespace) -> int:
    input_path = args.input
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Detect encoding
    if args.encoding:
        encoding_result = None
        encoding_str = args.encoding
    else:
        detector = EncodingDetector()
        encoding_result = detector.detect_from_file(str(input_path))
        encoding_str = encoding_result.encoding

    print(
        f"Detected encoding: {encoding_str} "
        f"(confidence: {encoding_result.confidence:.0%})" if encoding_result else "",
        file=sys.stderr,
    )

    # Parse and clean
    cleaner = MojibakeCleaner()
    sql_parser = SQLDumpParser()

    table_count = 0
    total_rows = 0

    print(f"Processing {input_path}...", file=sys.stderr)

    for table in sql_parser.parse_file(str(input_path), encoding_str):
        table = _process_extracted_table(table, cleaner)

        if args.format in ("csv", "both"):
            _write_extracted_csv(table, output_dir)
        if args.format in ("json", "both"):
            _write_extracted_json(table, output_dir)

        table_count += 1
        total_rows += len(table.rows)
        print(f"  {table.table_name}: {len(table.rows)} rows", file=sys.stderr)

    print(
        f"\nExtracted {table_count} tables, {total_rows} total rows to {output_dir}",
        file=sys.stderr,
    )
    return 0


def _process_extracted_table(table: TableData, cleaner: MojibakeCleaner) -> TableData:
    """Clean extracted table data."""
    cleaned_rows = []
    for row in table.rows:
        cleaned_row = [
            cleaner.clean_text(
                cleaner.try_fixing_mojibake(v) if cleaner.is_corrupted(v) else v
            )
            for v in row
        ]
        cleaned_rows.append(cleaned_row)
    return TableData(
        table_name=table.table_name,
        columns=table.columns,
        rows=cleaned_rows,
    )


def _write_extracted_csv(table: TableData, output_dir: Path) -> None:
    filepath = output_dir / f"{table.table_name}.csv"
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if table.columns:
            writer.writerow(table.columns)
        writer.writerows(table.rows)


def _write_extracted_json(table: TableData, output_dir: Path) -> None:
    filepath = output_dir / f"{table.table_name}.json"
    data = {
        "table": table.table_name,
        "columns": table.columns,
        "rows": table.rows,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _print_stage_summary(result: StageBatchResult) -> None:
    print(
        f"Staged {len(result.tables)} tables into {result.schema_name} from {result.source_dir} "
        f"(batch {result.batch_id})."
    )
    for table in result.tables:
        message = (
            f"- {table.table_name}: {table.row_count} rows, "
            f"{table.column_count} columns, source={table.source_file}"
        )
        print(message)


def _print_normalize_summary(result: NormalizationBatchResult) -> None:
    print(
        f"Normalized batch {result.batch_id} in {result.schema_name}: "
        f"parties={result.party_count}, products={result.product_count}, "
        f"warehouses={result.warehouse_count}, inventory={result.inventory_count}"
    )


def _print_product_mapping_summary(result: ProductMappingBatchResult) -> None:
    print(
        f"Mapped batch {result.batch_id} in {result.schema_name}: "
        f"mappings={result.mapping_count}, candidates={result.candidate_count}, "
        f"exact={result.exact_match_count}, unknown={result.unknown_count}, "
        f"orphans={result.orphan_code_count}/{result.orphan_row_count}"
    )


def _print_product_mapping_review_export_summary(
    result: ProductMappingReviewExportResult,
) -> None:
    print(
        f"Exported {result.exported_row_count} review rows for batch {result.batch_id} "
        f"to {result.output_path}"
    )


def _print_product_mapping_review_import_summary(
    result: ProductMappingReviewImportResult,
) -> None:
    print(
        f"Imported {result.applied_decision_count} review decisions for batch "
        f"{result.batch_id} from {result.input_path}"
    )


def _print_canonical_import_summary(result: CanonicalImportResult) -> None:
    print(
        f"Canonical imported batch {result.batch_id} in {result.schema_name}: "
        f"attempt={result.attempt_number}, "
        f"customers={result.customer_count}, suppliers={result.supplier_count}, "
        f"products={result.product_count}, "
        f"warehouses={result.warehouse_count}, inventory={result.inventory_count}, "
        f"orders={result.order_count}, order_lines={result.order_line_count}, "
        f"invoices={result.invoice_count}, invoice_lines={result.invoice_line_count}, "
        f"supplier_invoices={result.supplier_invoice_count}, "
        f"supplier_invoice_lines={result.supplier_invoice_line_count}, "
        f"holding={result.holding_count}, lineage={result.lineage_count}"
    )


def _print_validation_summary(result: MigrationBatchValidationResult) -> None:
    print(
        f"Validated batch {result.report.batch_id} in {result.report.schema_name}: "
        f"status={result.report.status}, blockers={result.report.blocking_issue_count}, "
        f"scope={result.report.replay.scope_key}, "
        f"json={result.json_path}, markdown={result.markdown_path}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "extract":
        return _run_extract(args)
    if args.command == "stage":
        return asyncio.run(_run_stage(args))
    if args.command == "normalize":
        return asyncio.run(_run_normalize(args))
    if args.command == "map-products":
        return asyncio.run(_run_map_products(args))
    if args.command == "export-product-review":
        return asyncio.run(_run_export_product_review(args))
    if args.command == "import-product-review":
        return asyncio.run(_run_import_product_review(args))
    if args.command == "canonical-import":
        return asyncio.run(_run_canonical_import(args))
    if args.command == "validate-import":
        return asyncio.run(_run_validate_import(args))
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
