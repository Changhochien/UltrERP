# Legacy SQL Dump Decoder

**Version**: 1.0
**Date**: 2026-03-30
**Status**: Built

---

## Purpose

Decode legacy Big5-encoded SQL dumps to clean UTF-8 output (CSV/JSON).

This is a focused, single-purpose tool that extracts structured data from PostgreSQL-style SQL dump files containing Traditional Chinese (Taiwan) content, converting them to clean UTF-8 outputs.

---

## Architecture

```
Input (Big5 SQL dump)
        │
        ▼
┌───────────────┐
│   detector    │  Detect Big5-HKSCS encoding via Taiwan byte patterns
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    parser     │  Parse INSERT statements into table data
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    cleaner    │  Fix mojibake, clean Taiwan-specific fields
└───────┬───────┘
        │
        ▼
Output (CSV / JSON)
```

---

## File Structure

```
legacy-migration-pipeline/src/
├── __init__.py
├── detector.py    # Encoding detection (Big5-HKSCS)
├── parser.py      # SQL INSERT parser
├── cleaner.py     # Mojibake fixer + Taiwan data cleaner
└── cli.py         # Command-line interface
```

---

## Modules

### detector.py

Detects encoding from SQL dump content using multi-point sampling.

**Key components:**
- `EncodingResult` dataclass: `encoding`, `confidence`, `has_taiwan_content`
- `TAIWAN_PATTERNS`: Byte sequences for "中華", "民國", "公司", "系統", "管理"
- `EncodingDetector.detect(content: bytes) -> EncodingResult`
- `EncodingDetector.detect_from_file(filepath: str) -> EncodingResult`
- `EncodingDetector.convert_to_utf8(content: bytes, encoding: str) -> str`

Detection strategy: Samples from 5 positions (start, 25%, 50%, 70%, 80%) and checks for Taiwan-specific Big5 byte sequences.

### parser.py

Parses SQL INSERT statements into structured table data.

**Key components:**
- `TableData` dataclass: `table_name`, `columns: List[str]`, `rows: List[List[str]]`
- `SQLDumpParser.parse_file(filepath: str, encoding: str) -> Iterator[TableData]`

Handles escaped quotes and extracts column names when present in INSERT INTO table(col1, col2) VALUES ...

### cleaner.py

Fixes encoding corruption and cleans Taiwan-specific data.

**Key components:**
- `MojibakeCleaner.is_corrupted(text: str) -> bool`
- `MojibakeCleaner.clean_text(text: str) -> str`
- `MojibakeCleaner.try_fixing_mojibake(text: str) -> str` (re-interprets Latin-1 bytes as Big5)
- `TaiwanDataCleaner.clean_phone(phone: str) -> str`
- `TaiwanDataCleaner.clean_business_number(number: str) -> str`
- `TaiwanDataCleaner.format_roc_date(date_str: str) -> Optional[str]` (民國113年09月12日 -> 2024-09-12)
- `TaiwanDataCleaner.clean_invoice_number(invoice: str) -> str`

### cli.py

Command-line interface tying it all together.

```
python -m cli <input.sql> [-o output_dir] [-f csv|json|both] [--encoding ENCODING]
```

Outputs one CSV or JSON file per table.

---

## Usage

```bash
# Auto-detect encoding
python -m cli legacy_dump.sql -o output

# Force encoding
python -m cli legacy_dump.sql -o output --encoding big5-hkscs

# Output both formats
python -m cli legacy_dump.sql -o output -f both
```

---

## Extracted Data Schema

Each table produces:

| Field | Type | Description |
|-------|------|-------------|
| `table_name` | string | Source table name from INSERT statement |
| `columns` | List[string] | Column names (if present in INSERT) |
| `rows` | List[List[string]] | Row values as string list |

Example output (CSV):
```csv
id,name,created_at
1,台北分公司,113-09-12
2,高雄辨事處,113-10-05
```

Example output (JSON):
```json
{
  "table": "branches",
  "columns": ["id", "name", "created_at"],
  "rows": [
    ["1", "台北分公司", "113-09-12"],
    ["2", "高雄辨事處", "113-10-05"]
  ]
}
```

---

## What Was Not Built

This spec documents only the decoder that was actually built (~300 lines, 4 modules). The following were specified in the original design but not implemented:

- Batch processing with parallel workers
- Transaction/rollback/checkpoint system
- InvenTree/Odoo target adapters
- FastAPI server
- Session management
- Circuit breaker
- Quality scoring framework
