# Legacy Data Context

Source: /Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/

Key files to read:
- README.md — project overview, 94 tables, 1.1M rows
- COLUMN_ANALYSIS.md — field-by-field analysis of key tables
- FK_VALIDATION.md — foreign key validation results

Key tables to understand:
- tbscust (1,022 rows) — customers + suppliers, 100 columns, tax_id in col 20
- tbsstock (6,611 rows) — products, 136 columns, alphanumeric codes like PC240
- tbsslipx (133,419 rows) — sales invoice headers, 103 columns
- tbsslipdtx (593,017 rows) — sales invoice line items, 73 columns, NUMERIC product codes
- tbsslipj (9,250 rows) — purchase invoice headers
- tbsslipdtj (61,728 rows) — purchase invoice line items
- tbsstkhouse (6,588 rows) — inventory levels

CRITICAL ISSUE: Product codes in tbsslipdtx (numeric: 1138, 1000, 2206) do NOT match
tbsstock product codes (alphanumeric: PC240, XPB-2410-P). 660 product codes in
transactions do not exist in the product master table.

ROC dates: Year + 1911 = AD (e.g., 1130826001 = 2024-08-26-001)
