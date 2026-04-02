# Legacy Data Landscape Survey

## Known Facts

**Source & Scale**
- Company: 聯泰興實業有限公司 (Taiwan hardware/V-belt distributor, 鼎新-style ERP)
- 94 tables, 1.1M rows total; 569MB SQL dump extracted at 99.996% completeness (45 rows lost)
- Original Big5 encoding converted to clean UTF-8 CSV

**Key Tables**
| Table | Rows | Issue |
|-------|------|-------|
| tbscust | 1,022 | Customers + suppliers combined; tax_id in col 20 |
| tbsstock | 6,611 | Products (V-belts); alphanumeric codes (PC240, XPB-2410-P) |
| tbsslipx | 133,419 | Sales invoice headers |
| tbsslipdtx | 593,017 | Sales invoice line items; **NUMERIC product codes** |
| tbsslipj | 9,250 | Purchase invoice headers |
| tbsslipdtj | 61,728 | Purchase invoice line items |
| tbsstkhouse | 6,588 | Inventory levels (product-to-warehouse) |
| tbasubject | 232 | Chart of accounts |
| tbabank | 7,831 | Bank master |

**FK Validation Results**
- tbsslipx.customer_code → tbscust: 99.85% match (OK)
- tbsslipdtx.product_code → tbsstock: **0.30% match** (CRITICAL)
- tbsslipdtx.doc_number → tbsslipx: 99.98% match (OK)
- tbsslipj.supplier_code → tbscust: 98.04% match (OK)
- tbsslipdtj.product_code → tbsstock: 96.56% match (OK)
- tbsstkhouse.product_code → tbsstock: 100% match (OK)

**Critical: Product Code Mismatch**
- tbsslipdtx (sales detail) uses NUMERIC codes: 1138, 1000, 2206, 001, 0001
- tbsstock uses ALPHANUMERIC codes: PC240, XPB-2410-P, P5V-1250 OH
- 660 unique product codes in transactions do NOT exist in product master
- Root cause: System underwent product code migration; historical transaction records were not updated
- Only ~3 alphanumeric product codes (P5V-1250 OH, PC240, XPB-2410-P) appear in both tables

**Date Format**
- ROC (民國) dates: Year + 1911 = AD
- Invoice number pattern: 1130826001 = 2024-08-26-001
- Some records show 1900-01-01 as default/empty date

**Data Quality Issues**
- 9 tables have only 1 row (likely seed data): tbaaccounts, tbacodefmt, tbaemploy, tbasyspara, tbcpasswd, tbslocation, tbsstorehouse, tbsusrempl, tbsusrhouse
- tbslog: 301,460 rows (system audit log - may need archival)
- Some small tables with 2-4 rows: tbsagio, tbabankitem, tbacashpaytype

**Staging Schema Available**
- postgresql_schema.sql defines clean target schema with normalized tables
- Tables: parties, products, warehouses, inventory, sales_orders, sales_order_lines, purchase_orders, purchase_order_lines, chart_of_accounts, banks

## Unknowns / Open Questions

1. **Product Code Mapping**: Is there a legacy mapping table (e.g., tbsoldcode, tbscodemap) that links numeric codes to alphanumeric codes? Not found in current extraction.
2. **Numeric Code Pattern**: Do the numeric codes (1138, 1000, etc.) correspond to a warehouse_code (field 6) or some other internal ID system?
3. **Historical Records**: The oldest tbsslipdtx records date to 1999 (ROC 88). Were these older records ever meant to be migrated after the code change?
4. **Orphan Handling**: The 660 unmatched product codes represent ~591K rows (99.7% of sales detail). Should these be excluded, mapped manually, or linked to a "generic/misc" product?
5. **ROC Date Edge Cases**: How should dates like 1900-01-01 (empty date sentinel) be handled? Should 2016-2024 date range be validated?

## Top 3 Risks

**1. Sales Detail Product Link Broken (CRITICAL - Impact: High)**
- 99.7% of sales invoice line items (593K rows) cannot be linked to product master
- This affects: sales analytics by product, product profitability reports, inventory deduction validation
- Without resolution, sales order lines will have NULL product_id or require artificial "unknown product" entries
- Mitigation: Create product_code mapping or accept orphan transactions with manual review flag

**2. Target Schema FK Constraints Will Fail (HIGH - Impact: Medium)**
- Target PostgreSQL schema has FK constraints: `sales_order_lines.product_id REFERENCES products(product_id)`
- Importing tbsslipdtx directly will violate FK constraints for ~591K rows
- Must decide: disable FK during staging, create placeholder products, or exclude these rows
- Recommendation: Stage import WITHOUT FK constraints first, then resolve

**3. Data Lineage Traceability Lost (MEDIUM - Impact: High)**
- Many tables have minimal rows (1-5 rows): tbaaccounts, tbasyspara, tbcpasswd, tbslocation, tbsstorehouse
- These single-row tables likely contain company-wide settings needed for full system replication
- Without proper documentation, imported data may behave inconsistently (e.g., missing tax configuration)
- Mitigation: Document all single-row tables and validate their content during PoC

## 3-Point Recommendation

**Point 1: Investigate Product Code Resolution Strategy (Week 1)**
- Search SQL dump for any legacy code mapping tables (tbsold*, tbscode*, tbsmap*)
- Analyze whether numeric codes in slipdtx (field 6 = warehouse_code) can be used to derive product
- If no mapping found, decide on strategy:
  - Option A: Create "UNKNOWN_PRODUCT" placeholder and flag for manual mapping
  - Option B: Exclude affected rows from sales analytics
  - Option C: Attempt fuzzy match on product_name between slipdtx.field 8 and tbsstock.field 3
- Output: Documented resolution strategy for 660 orphan codes

**Point 2: Build Staging Database WITHOUT FK Constraints (Week 1-2)**
- Import all 94 CSVs into PostgreSQL staging schema matching postgresql_schema.sql
- Disable all FK constraints during initial load (SET foreign_key_checks = 0)
- Load order: parties → products → warehouses → inventory → chart_of_accounts → banks → sales_orders → sales_order_lines → purchase_orders → purchase_order_lines
- Add staging columns: `_legacy_table`, `_legacy_pk`, `_import_status`, `_fk_violation`
- Validate row counts match manifest (1.1M total)
- Output: Functional staging database with full data loaded

**Point 3: Run FK Validation and Produce Orphan Report (Week 2)**
- Execute FK validation queries against staging database
- Generate orphan report: list all rows violating FK constraints with legacy IDs
- Prioritize orphan categories:
  - P0: 660 product codes in tbsslipdtx (591K rows)
  - P1: 1 customer_code in tbsslipx (1 row)
  - P2: 219 product codes in tbsslipdtj (purchase detail)
- For PoC, demonstrate working scenario with matching records (~1,779 rows that DO join)
- Output: Orphan report with remediation recommendations for each priority level
