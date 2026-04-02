# Legacy Migration Pipeline

Extracts and migrates data from legacy Taiwanese ERP SQL dumps to clean UTF-8 data with documented schema.

## Project Structure

```
legacy-migration-pipeline/
├── src/                      # Decoder tools
│   ├── detector.py          # Big5 encoding detection
│   ├── parser.py            # SQL INSERT parser
│   ├── cleaner.py           # Mojibake fixer
│   └── cli.py               # CLI interface
├── extracted_data/           # Clean UTF-8 CSV data (94 tables, 1.1M rows)
│   ├── README.md            # Data overview
│   ├── RELATIONSHIPS.md     # Entity relationship map
│   ├── MANIFEST.md         # Table index with row counts
│   └── *.csv               # All 94 tables
├── schema/                   # Target database schemas
│   ├── postgresql_schema.sql
│   └── sqlite_schema.sql
├── COLUMN_ANALYSIS.md        # Field-by-field analysis
├── FK_VALIDATION.md          # Foreign key validation results
└── SPEC.md                   # Specification document
```

## Data Summary

- **Source**: 聯泰興實業有限公司 legacy ERP (鼎新 or similar)
- **Format**: PostgreSQL SQL dump (Big5 encoded)
- **Size**: 569MB SQL dump → 1.1M rows across 94 tables
- **Extraction**: 99.996% complete (45 rows lost)

### Key Tables

| Table | Rows | Description |
|-------|------|-------------|
| tbscust | 1,022 | Customers + suppliers |
| tbsstock | 6,611 | Products (V-belts, industrial parts) |
| tbsslipx | 133,419 | Sales invoice headers |
| tbsslipdtx | 593,017 | Sales invoice line items |
| tbsslipj | 9,250 | Purchase invoice headers |
| tbsslipdtj | 61,728 | Purchase invoice line items |
| tbsstkhouse | 6,588 | Inventory levels |
| tbasubject | 232 | Chart of accounts |
| tbabank | 7,831 | Bank master |

## Critical Data Issue

**Product code mismatch in tbsslipdtx**

The sales detail table uses numeric product codes (`1138`, `1000`, `2206`) while the product master (`tbsstock`) uses alphanumeric codes (`PC240`, `XPB-2410-P`).

- **660 product codes** in transactions do NOT exist in product master
- This is a legacy system artifact from a product code migration
- See `FK_VALIDATION.md` for details

## Usage

### Extract Data from SQL Dump

```bash
cd src
python3 cli.py "/path/to/legacy.sql" -o output_dir --format csv
```

### Create Target Database

```bash
# PostgreSQL
psql -U postgres -d newdb -f schema/postgresql_schema.sql

# SQLite
sqlite3 new.db < schema/sqlite_schema.sql
```

### Import Extracted Data

```python
import csv
import sqlite3

conn = sqlite3.connect('new.db')
cursor = conn.cursor()

# Example: Import customers
with open('extracted_data/tbscust.csv', 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        # Parse and insert based on schema
        pass
```

## Entity Relationships

```
parties (customers + suppliers)
    ├── products (from tbsstock)
    │       └── inventory (from tbsstkhouse)
    ├── sales_orders (from tbsslipx)
    │       └── sales_order_lines (from tbsslipdtx)
    └── purchase_orders (from tbsslipj)
            └── purchase_order_lines (from tbsslipdtj)
```

See `RELATIONSHIPS.md` for full FK documentation.

## Next Steps

1. **Investigate product code mismatch** - Find legacy code mapping or accept orphan transactions
2. **Create staging database** - Import CSVs into mirror schema first
3. **Validate data** - Check FK relationships after staging import
4. **Transform to target schema** - Map legacy columns to new design
5. **Import to target** - Load into final database (InvenTree, Odoo, custom)

## Documentation

- `extracted_data/README.md` - Data overview
- `extracted_data/RELATIONSHIPS.md` - Entity relationships
- `COLUMN_ANALYSIS.md` - Field-by-field analysis
- `FK_VALIDATION.md` - FK validation results
