"""CLI entry point for legacy import workflows."""

from __future__ import annotations

import argparse
import asyncio
import uuid
from collections.abc import Sequence

from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.staging import StageBatchResult, run_stage_import


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
		default=str(DEFAULT_TENANT_ID),
		help="Tenant UUID for control-table tracking",
	)
	stage_parser.add_argument(
		"--table",
		action="append",
		dest="tables",
		help="Limit staging to specific table names (repeatable)",
	)
	return parser


async def _run_stage(args: argparse.Namespace) -> int:
	result = await run_stage_import(
		batch_id=args.batch_id,
		source_dir=args.source_dir,
		selected_tables=tuple(args.tables or ()),
		tenant_id=uuid.UUID(args.tenant_id),
		schema_name=args.schema,
	)
	_print_stage_summary(result)
	return 0


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


def main(argv: Sequence[str] | None = None) -> int:
	parser = build_parser()
	args = parser.parse_args(argv)
	if args.command == "stage":
		return asyncio.run(_run_stage(args))
	parser.error(f"Unsupported command: {args.command}")
	return 2


if __name__ == "__main__":
	raise SystemExit(main())