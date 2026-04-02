#!/usr/bin/env python3
"""
CLI for legacy SQL dump decoder.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

from detector import EncodingDetector, EncodingResult
from parser import SQLDumpParser, TableData
from cleaner import MojibakeCleaner, TaiwanDataCleaner


def detect_encoding(filepath: str) -> EncodingResult:
    """Detect encoding of file."""
    detector = EncodingDetector()
    return detector.detect_from_file(filepath)


def process_table(table: TableData, cleaner: MojibakeCleaner) -> TableData:
    """Clean table data."""
    cleaned_rows = []
    for row in table.rows:
        cleaned_row = [cleaner.clean_text(cleaner.try_fixing_mojibake(v) if cleaner.is_corrupted(v) else v) for v in row]
        cleaned_rows.append(cleaned_row)

    return TableData(
        table_name=table.table_name,
        columns=table.columns,
        rows=cleaned_rows,
    )


def write_csv(table: TableData, output_dir: Path) -> Path:
    """Write table to CSV."""
    filepath = output_dir / f"{table.table_name}.csv"
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if table.columns:
            writer.writerow(table.columns)
        writer.writerows(table.rows)
    return filepath


def write_json(table: TableData, output_dir: Path) -> Path:
    """Write table to JSON."""
    filepath = output_dir / f"{table.table_name}.json"
    data = {
        "table": table.table_name,
        "columns": table.columns,
        "rows": table.rows,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Decode legacy SQL dump to clean UTF-8")
    parser.add_argument("input", help="Input SQL dump file")
    parser.add_argument("-o", "--output", default="output", help="Output directory")
    parser.add_argument("-f", "--format", choices=["csv", "json", "both"], default="csv")
    parser.add_argument("--encoding", help="Force encoding (auto-detect if not specified)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Detect encoding
    if args.encoding:
        encoding_result = EncodingResult(encoding=args.encoding, confidence=1.0)
    else:
        print("Detecting encoding...", file=sys.stderr)
        encoding_result = detect_encoding(str(input_path))

    print(f"Detected encoding: {encoding_result.encoding} "
          f"(confidence: {encoding_result.confidence:.0%})",
          file=sys.stderr)

    # Parse and clean
    cleaner = MojibakeCleaner()
    sql_parser = SQLDumpParser()

    table_count = 0
    total_rows = 0

    print(f"Processing {input_path}...", file=sys.stderr)

    for table in sql_parser.parse_file(str(input_path), encoding_result.encoding):
        table = process_table(table, cleaner)

        if args.format == "csv":
            write_csv(table, output_dir)
        elif args.format == "json":
            write_json(table, output_dir)
        else:
            write_csv(table, output_dir)
            write_json(table, output_dir)

        table_count += 1
        total_rows += len(table.rows)
        print(f"  {table.table_name}: {len(table.rows)} rows")

    print(f"\nDone: {table_count} tables, {total_rows} total rows",
          file=sys.stderr)


if __name__ == "__main__":
    main()
