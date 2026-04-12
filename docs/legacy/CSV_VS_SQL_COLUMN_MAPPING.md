# CSV vs SQL Column Mapping: tbsslipdtj

## 1. Parser.py: Column Source Analysis

**How parser.py extracts column names:**

The `SQLDumpParser` class (parser.py lines 16-61) uses this INSERT regex:
```
INSERT INTO (\w+)\s*(?:\(([^)]+)\))?\s*VALUES\s*(.+?);
```

- Group 1 captures the **table name**
- Group 2 captures the **column list in parentheses** (optional)
- Group 3 captures the VALUES data

**Critical finding:** Column names are only extracted if the INSERT statement includes an explicit column list like:
```sql
INSERT INTO tbsslipdtj (skind, sslipno, iidno, ...) VALUES (...);
```

If no column list is present, `columns` remains an empty list `[]`.

---

## 2. Do INSERT Statements Specify Explicit Column Lists?

**Answer: NO.** The raw SQL dump uses bare INSERT statements with NO column lists.

Example from line 408153 of the SQL dump:
```sql
INSERT INTO tbsslipdtj VALUES ('4', '1130827001', 2, '2024-08-27', ...);
```

All 61,728 rows for tbsslipdtj follow this pattern. The parser correctly captures an empty column list for all of them.

---

## 3. CREATE TABLE Schema for tbsslipdtj (78 columns)

Source: `legacy data/cao50001.sql` lines 13086-13165

| # | Column Name | Data Type | Sample Value | Notes |
|---|-------------|-----------|-------------|-------|
| 1 | skind | varchar(4) | '4' | slip kind |
| 2 | sslipno | varchar(17) | '1130827001' | slip number |
| 3 | iidno | integer | 2 | line item number |
| 4 | dtslipdate | date | '2024-08-27' | slip date |
| 5 | scustno | varchar(16) | 'T067' | customer/supplier code |
| 6 | sstkno | varchar(30) | '0013' | stock number (product code) |
| 7 | sstkname | varchar(120) | '郵寄運費' | stock name |
| 8 | sinvno | varchar(14) | '' | invoice number |
| 9 | sinvkind | varchar(2) | '' | invoice kind |
| 10 | fstkanava | numeric(21,8) | 1.00000000 | kanava factor |
| 11 | sstkanaop | varchar(2) | '*' | kanava operator |
| 12 | ssrslipno | varchar(16) | '' | related slip number |
| 13 | isrslipidno | integer | 0 | related slip ID |
| 14 | ssrkind | varchar(4) | '' | related slip kind |
| 15 | ssrtype | varchar(1) | '' | slip type |
| 16 | shouseno | varchar(10) | 'A' | warehouse number |
| 17 | shousename | varchar(20) | '總倉' | warehouse name |
| 18 | sunit | varchar(16) | '回' | unit |
| 19 | foldprice | numeric(21,8) | 100.00000000 | original price |
| 20 | fdisper | numeric(14,8) | 0.80000000 | discount percent |
| 21 | fnewprice | numeric(21,8) | 80.00000000 | discounted price |
| 22 | fstkqty | numeric(21,8) | 1.00000000 | stock quantity |
| 23 | sstkgive | varchar(1) | 'N' | is free (Y/N) |
| 24 | fqtyrate | numeric(14,8) | 1.00000000 | quantity rate |
| 25 | stax | varchar(1) | 'Y' | taxable |
| 26 | fstotal | numeric(21,8) | 80.00000000 | line total |
| 27 | fprepave | numeric(21,8) | 0.00000000 | prep average |
| 28 | funitpave | numeric(21,8) | 0.00000000 | unit prep average |
| 29 | fsendqty | numeric(21,8) | 0.00000000 | sent quantity |
| 30 | fpickoutqty | numeric(21,8) | 0.00000000 | picked quantity |
| 31 | srem1 | varchar(250) | '' | remark 1 |
| 32 | sstkrem1 | varchar(250) | '' | stock remark 1 |
| 33 | sstkyardno | varchar(30) | '' | yard number |
| 34 | fhcurqty | numeric(21,8) | 0.00000000 | current quantity (history) |
| 35 | fcurqty | numeric(21,8) | 0.00000000 | current quantity |
| 36 | fotheramt | numeric(21,8) | 0.00000000 | other amount |
| 37 | sstkspec | text | '' | stock specification |
| 38 | iabsno | integer | 3 | abs number |
| 39 | idabsno | integer | -1 | detail abs number |
| 40 | frepdiscount | numeric(21,8) | 0.00000000 | replace discount |
| 41 | fnewpricebk | numeric(21,8) | 80.00000000 | price backup |
| 42 | sexp1 | varchar(50) | '' | spare field 1 |
| 43 | sexp2 | varchar(50) | '' | spare field 2 |
| 44 | sversion | varchar(1) | '' | version |
| 45 | fdiscounttax | numeric(21,8) | 0.00000000 | discount tax |
| 46 | dtinvo | date | '2024-08-27' | invoice date |
| 47 | sdtaxtype | varchar(1) | '1' | tax type |
| 48 | sactno | varchar(20) | '' | account number |
| 49 | fdtcommissionamt | numeric(21,8) | 0.00000000 | commission amount |
| 50 | scommissionno | varchar(10) | '' | commission number |
| 51 | scommissionname | varchar(80) | '' | commission name |
| 52 | sexp3 | varchar(50) | '' | spare field 3 |
| 53 | sexp4 | varchar(50) | '' | spare field 4 |
| 54 | sexp5 | varchar(50) | '' | spare field 5 |
| 55 | sbatchno | varchar(16) | '' | batch number |
| 56 | sbatchnumber | varchar(30) | '' | batch number extended |
| 57 | dteffectivedate | date | '1900-01-01' | effective date |
| 58 | isbeenmrps | varchar(1) | '21' | MRP status |
| 59 | smrpsno | varchar(20) | '' | MRP number |
| 60 | sdinvkind | varchar(2) | '' | detail invoice kind |
| 61 | sdinvno | varchar(240) | '' | detail invoice number |
| 62 | scorpcode | varchar(4) | '' | corp code |
| 63 | commno | integer | 0 | commission number (int) |
| 64 | bstktax | varchar(1) | '1' | stock tax |
| 65 | fdiscprice | numeric(21,8) | 80.00000000 | discount price |
| 66 | fdiscpricen | numeric(21,8) | 80.00000000 | discount price (N) |
| 67 | fdisctotal | numeric(21,8) | 80.00000000 | discount total |
| 68 | fdisctotaln | numeric(21,8) | 80.00000000 | discount total (N) |
| 69 | svalorem | varchar(1) | '' | ad valorem |
| 70 | smaterialmarkno | varchar(20) | '' | material mark number |
| 71 | smarkno | varchar(20) | '' | mark number |
| 72 | spermissionno | varchar(2) | '' | permission number |
| 73 | sdeclarationidno | varchar(2) | '' | declaration ID |
| 74 | sreserved1 | varchar(30) | '' | reserved 1 |
| 75 | sreserved2 | varchar(30) | '' | reserved 2 |
| 76 | sreserved3 | varchar(30) | '' | reserved 3 |
| 77 | sreserved4 | varchar(30) | '' | reserved 4 |
| 78 | sreserved5 | varchar(30) | '' | reserved 5 |

---

## 4. tbsslipdtj INSERT at Line 408153: Full Positional Mapping

**Raw INSERT:**
```sql
INSERT INTO tbsslipdtj VALUES
('4', '1130827001', 2, '2024-08-27', 'T067', '0013', '�l�H�B�O', '', '',
 1.00000000, '*', '', 0, '', '', 'A', '�`��', '�^', 100.00000000, 0.80000000,
 80.00000000, 1.00000000, 'N', 1.00000000, 'Y', 80.00000000, 0.00000000, 0.00000000,
 0.00000000, 0.00000000, '', '', '', 0.00000000, 0.00000000, 0.00000000, '', 3, -1,
 0.00000000, 80.00000000, '', '', '', 0.00000000, '2024-08-27', '1', '', 0.00000000,
 '', '', '', '', '', '', '', '1900-01-01', '', '', '21', '', '', 0, '1', 80.00000000,
 80.00000000, 80.00000000, 80.00000000, '', '', '', '', '', '0.000', '', '', '', '');
```

Note: Chinese text (columns 7, 17, 18) is mojibake because the raw SQL dump was read with incorrect encoding (original is Big5 but parsed as UTF-8).

**Mapped to CREATE TABLE column names:**

| Position | Column Name | Value | Notes |
|----------|-------------|-------|-------|
| 1 | skind | '4' | |
| 2 | sslipno | '1130827001' | |
| 3 | iidno | 2 | |
| 4 | dtslipdate | '2024-08-27' | |
| 5 | scustno | 'T067' | supplier code |
| 6 | sstkno | '0013' | product code |
| 7 | sstkname | '�l�H�B�O' | mojibake (should be 郵寄運費) |
| 8 | sinvno | '' | |
| 9 | sinvkind | '' | |
| 10 | fstkanava | 1.00000000 | |
| 11 | sstkanaop | '*' | |
| 12 | ssrslipno | '' | |
| 13 | isrslipidno | 0 | |
| 14 | ssrkind | '' | |
| 15 | ssrtype | '' | |
| 16 | shouseno | 'A' | |
| 17 | shousename | '�`��' | mojibake (should be 總倉) |
| 18 | sunit | '�^' | mojibake (should be 回) |
| 19 | foldprice | 100.00000000 | |
| 20 | fdisper | 0.80000000 | 80% = 0.8 |
| 21 | fnewprice | 80.00000000 | |
| 22 | fstkqty | 1.00000000 | |
| 23 | sstkgive | 'N' | not free |
| 24 | fqtyrate | 1.00000000 | |
| 25 | stax | 'Y' | taxable |
| 26 | fstotal | 80.00000000 | |
| 27 | fprepave | 0.00000000 | |
| 28 | funitpave | 0.00000000 | |
| 29 | fsendqty | 0.00000000 | |
| 30 | fpickoutqty | 0.00000000 | |
| 31 | srem1 | '' | |
| 32 | sstkrem1 | '' | |
| 33 | sstkyardno | '' | |
| 34 | fhcurqty | 0.00000000 | |
| 35 | fcurqty | 0.00000000 | |
| 36 | fotheramt | 0.00000000 | |
| 37 | sstkspec | '' | |
| 38 | iabsno | 3 | |
| 39 | idabsno | -1 | |
| 40 | frepdiscount | 0.00000000 | |
| 41 | fnewpricebk | 80.00000000 | |
| 42 | sexp1 | '' | |
| 43 | sexp2 | '' | |
| 44 | sversion | '' | |
| 45 | fdiscounttax | 0.00000000 | |
| 46 | dtinvo | '2024-08-27' | |
| 47 | sdtaxtype | '1' | |
| 48 | sactno | '' | |
| 49 | fdtcommissionamt | 0.00000000 | |
| 50 | scommissionno | '' | |
| 51 | scommissionname | '' | |
| 52 | sexp3 | '' | |
| 53 | sexp4 | '' | |
| 54 | sexp5 | '' | |
| 55 | sbatchno | '' | |
| 56 | sbatchnumber | '' | |
| 57 | dteffectivedate | '1900-01-01' | |
| 58 | isbeenmrps | '21' | |
| 59 | smrpsno | '' | |
| 60 | sdinvkind | '' | |
| 61 | sdinvno | '' | |
| 62 | scorpcode | '' | |
| 63 | commno | 0 | |
| 64 | bstktax | '1' | |
| 65 | fdiscprice | 80.00000000 | |
| 66 | fdiscpricen | 80.00000000 | |
| 67 | fdisctotal | 80.00000000 | |
| 68 | fdisctotaln | 80.00000000 | |
| 69 | svalorem | '' | |
| 70 | smaterialmarkno | '' | |
| 71 | smarkno | '' | |
| 72 | spermissionno | '' | |
| 73 | sdeclarationidno | '' | |
| 74 | sreserved1 | '' | |
| 75 | sreserved2 | '' | |
| 76 | sreserved3 | '' | |
| 77 | sreserved4 | '' | |
| 78 | sreserved5 | '' | |

---

## 5. CSV File Header Status

**Answer: CSV files are headerless (no header row).**

Evidence:
- The first line of `tbsslipdtj.csv` is the first data row: `'4', '1130827001', 2, ...`
- If there were a header, it would be text column names, not quoted values
- The parser.py produces CSVs by joining `row` lists with commas, no header injection
- `extracted_data/tbsslipdtj.csv` contains 61,728 data rows, all positional values
- Column count is **78**, matching CREATE TABLE exactly

**The pipeline currently has no way to know column names from the INSERT statements alone.**

---

## 6. Summary of Key Findings

| Question | Answer |
|----------|--------|
| Does parser.py extract from CREATE TABLE? | **No** - only from INSERT column lists (group 2 of regex) |
| Do INSERT statements have explicit column lists? | **No** - all bare `INSERT INTO tbsslipdtj VALUES` |
| Column count: INSERT vs CREATE TABLE | **Both have 78 columns** - positional alignment confirmed |
| Do CSV files have header rows? | **No** - purely positional, headerless |
| Mapping method available? | **Only by counting CREATE TABLE column positions** |

---

## 7. Required Fix: Pipeline

The pipeline MUST be updated to:

1. **Read CREATE TABLE schemas** to get column names in order
2. **Associate each CSV's positional values with CREATE TABLE column names**
3. **Write CSV with header row** using the CREATE TABLE column names

This requires either:
- Augmenting parser.py to also parse CREATE TABLE statements and store schema
- Using the existing `postgresql_schema.sql` / `sqlite_schema.sql` files as the column name source
- Generating a separate schema mapping file for the 94 legacy tables

---

## 8. CRITICAL BUG: `_fetch_purchase_lines` Column Mapping Errors

**File:** `backend/domains/legacy_import/canonical.py` lines 867-889

**Current (BROKEN) query:**
```python
async def _fetch_purchase_lines(connection, schema_name: str, batch_id: str):
    rows = await connection.fetch(f"""
        SELECT
            col_2 AS doc_number,        -- WRONG: col_2 = sslipno, not doc_number
            col_3 AS line_number,       -- WRONG: col_3 = iidno, not line_number
            col_6 AS product_code,      -- CORRECT: col_6 = sstkno
            col_19 AS unit_price,       -- WRONG: col_19 = foldprice (original price)
            col_20 AS discount_multiplier, -- OK: col_20 = fdisper
            col_21 AS foldprice,        -- WRONG: col_21 = fnewprice (discounted price)
            col_22 AS qty,              -- CORRECT: col_22 = fstkqty
            (col_19::numeric * col_20::numeric * col_22::numeric) AS extended_amount,
            _source_row_number
        FROM {schema}.tbsslipdtj
    """)
```

**Problems:**
1. `col_2` is `sslipno` (slip number) -- used as `doc_number` -- WRONG
2. `col_3` is `iidno` (line item number) -- used as `line_number` -- WRONG
3. `col_19` is `foldprice` (original price) -- used as `unit_price` -- WRONG
4. `col_21` is `fnewprice` (discounted price) -- used as `foldprice` -- WRONG positional swap
5. Extended amount formula `col_19 * col_20 * col_22` = foldprice * fdisper * fstkqty -- WRONG (should use fnewprice)
6. **Missing**: `shouseno` (warehouse code) -- not fetched at all
7. **Missing**: `sstkname` (product name) -- not fetched, used for description
8. **Missing**: `sunit` (unit) -- not fetched
9. **Missing**: `stax` (taxable Y/N) -- not fetched
10. **Missing**: `dtinvo` (invoice date) -- not fetched

**Corrected query:**
```python
async def _fetch_purchase_lines(connection, schema_name: str, batch_id: str):
    rows = await connection.fetch(f"""
        SELECT
            col_2 AS doc_number,           -- sslipno (slip number = document number)
            col_3 AS line_number,          -- iidno (line item number)
            col_6 AS product_code,         -- sstkno (stock number = product code)
            col_7 AS product_name,         -- sstkname (stock name, for description)
            col_16 AS warehouse_code,       -- shouseno (warehouse number)
            col_18 AS unit,                -- sunit (unit of measure)
            col_19 AS foldprice,           -- foldprice (original unit price)
            col_20 AS discount_multiplier, -- fdisper (discount multiplier, e.g. 0.8 = 80%)
            col_21 AS unit_price,          -- fnewprice (discounted unit price) -- CORRECT!
            col_22 AS qty,                 -- fstkqty (quantity)
            col_25 AS taxable,             -- stax (Y/N taxable)
            col_26 AS line_total,          -- fstotal (line total = fnewprice * fstkqty)
            (col_21::numeric * col_22::numeric) AS extended_amount,
                -- fnewprice * fstkqty (not foldprice * fdisper * fstkqty)
            _source_row_number
        FROM {schema}.tbsslipdtj
    """)
```

**Extended amount formula:**
- Current: `col_19 * col_20 * col_22` = foldprice * fdisper * fstkqty = 100 * 0.8 * 1 = 80.00
- Correct: `col_21 * col_22` = fnewprice * fstkqty = 80 * 1 = 80.00
- Note: These happen to produce the same result here (80), but the formula is semantically wrong

---

## 9. `_import_purchase_history` Field Usage Analysis

**Current usage of fetched fields in `_import_purchase_history` (lines 1934-2007):**

| Fetched Alias | Used As | Issue |
|---|---|---|
| doc_number | Groups lines to header | WRONG col (should be sslipno) |
| line_number | Line number | WRONG col (should be iidno) |
| product_code | Product lookup | CORRECT (col_6 = sstkno) |
| unit_price | Unit price for line | WRONG col (col_19 = foldprice not fnewprice) |
| discount_multiplier | Discount rate | OK (col_20 = fdisper) |
| foldprice | Not used directly | WRONG col assignment in query |
| qty | Quantity for line | CORRECT (col_22 = fstkqty) |
| extended_amount | Subtotal for line | WRONG formula |
| **Missing** | warehouse_code | Not fetched |
| **Missing** | product_name | Not used for description |
| **Missing** | unit | Not used |
| **Missing** | taxable | Not used for tax policy |
| **Missing** | dtinvo | Not fetched |

**`description` field in `supplier_invoice_lines` INSERT (line 1999-2000):**
- Currently set to `legacy_product_code` -- should use `sstkname` (product name)

**`unit_price` field (line 2002):**
- Currently reads from wrong column (col_19 = foldprice)
- Should read from col_21 = fnewprice (after query fix)

---

## 10. Quick Reference: tbsslipdtj Positional to Named Column Map

| CSV col | SQL col | Meaning | purchase_lines usage |
|---------|---------|---------|---------------------|
| 1 | skind | slip kind | No |
| 2 | sslipno | slip number = doc_number | YES (WRONG - query uses col_2 as doc_number which is correct) |
| 3 | iidno | line item number = line_number | YES (WRONG - query uses col_3 as line_number which is correct) |
| 4 | dtslipdate | slip date | No |
| 5 | scustno | customer/supplier code | No (in header) |
| 6 | sstkno | product code | YES (correct) |
| 7 | sstkname | product name | NOT FETCHED (should be description) |
| 16 | shouseno | warehouse code | NOT FETCHED |
| 18 | sunit | unit | NOT FETCHED |
| 19 | foldprice | original price | YES (WRONG - used as unit_price) |
| 20 | fdisper | discount multiplier | YES (OK as discount_multiplier) |
| 21 | fnewprice | discounted price | YES (WRONG - used as foldprice, should be unit_price) |
| 22 | fstkqty | quantity | YES (correct) |
| 25 | stax | taxable | NOT FETCHED |
| 26 | fstotal | line total | NOT FETCHED |
| 46 | dtinvo | invoice date | NOT FETCHED |
