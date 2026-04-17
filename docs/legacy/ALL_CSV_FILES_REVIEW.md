# All CSV Files Review - Legacy Migration Pipeline (cao50001)

**Reviewed:** 2026-04-12
**Total CSV files:** 95 (in `/legacy-migration-pipeline/extracted_data/cao50001/`)

---

## Complete Table Inventory (95 files)

| # | Table Name | Rows | Cols | Inventory/Stock Related? | Notes |
|---|-----------|------|------|--------------------------|-------|
| 1 | tbaaccounts.csv | 0 | 57 | No | Empty |
| 2 | tbaadjust.csv | 4 | 6 | No | Small adjustment table |
| 3 | tbaamnt.csv | 231 | 6 | No | Amount references |
| 4 | tbaarapctlsub.csv | 23 | 8 | No | AR/AP control sub |
| 5 | tbabank.csv | 7830 | 5 | No | Bank master |
| 6 | tbabankitem.csv | 3 | 4 | No | Bank items |
| 7 | tbabankzh.csv | 260 | 3 | No | Chinese bank names |
| 8 | tbacashflow.csv | 102 | 8 | No | Cash flow categories |
| 9 | tbacashpaytype.csv | 3 | 4 | No | Cash payment types |
| 10 | tbacodefmt.csv | 0 | 6 | No | Empty |
| 11 | tbacost.csv | 68 | 3 | No | Cost categories |
| 12 | tbacostdetail.csv | 17 | 8 | No | Cost detail |
| 13 | tbactlsub.csv | 48 | 4 | No | Control sub |
| 14 | tbadoevent.csv | 0 | 9 | No | Empty |
| 15 | tbaemploy.csv | 0 | 134 | No | Empty |
| 16 | tbaemployitem.csv | 24 | 17 | No | Employee items |
| 17 | tbaemplt.csv | 61 | 3 | No | Employee plate |
| 18 | tbaetgood.csv | 0 | 5 | No | Empty |
| 19 | tbaflagdc.csv | 27 | 4 | No | Flag D/C |
| 20 | tbafncuse.csv | 5 | 3 | No | Financial use |
| 21 | tbahealth.csv | 49 | 9 | No | Health related |
| 22 | tbaholiday.csv | 7304 | 3 | No | Holiday calendar |
| 23 | tbahosthealth.csv | 49 | 7 | No | Host health |
| 24 | tbahostlbtb.csv | 809 | 28 | No | Host LBTB (tax?) |
| 25 | **tbainvorail.csv** | **89** | **35** | **YES - KEY** | Stock movement/rail - NOT fully analyzed yet |
| 26 | tbaiotypeset.csv | 8 | 7 | No | IO type set |
| 27 | tbalbtb.csv | 809 | 51 | No | LBTB records |
| 28 | tbalog.csv | 8 | 10 | No | Log |
| 29 | tbarate.csv | 24 | 9 | No | Rate table |
| 30 | tbaraterefer.csv | 14 | 4 | No | Rate reference |
| 31 | tbareptlst.csv | 48 | 6 | No | Report list |
| 32 | tbarichkind.csv | 7 | 6 | No | Rich kind |
| 33 | tbarptitvset.csv | 25 | 5 | No | Report ITV set |
| 34 | tbasadset.csv | 126 | 3 | No | SAD set |
| 35 | tbasalaryset.csv | 0 | 17 | No | Empty |
| 36 | tbasecondlang.csv | 62 | 4 | No | Second language |
| 37 | tbasetinfo.csv | 73 | 7 | No | System set info |
| 38 | **tbastktokj.csv** | **247** | **6** | **YES** | Stock token/keyword journal - partially analyzed |
| 39 | tbasubbase.csv | 8 | 5 | No | Sub base |
| 40 | tbasubclass.csv | 24 | 7 | No | Subclass |
| 41 | tbasubject.csv | 231 | 27 | No | Accounting subject |
| 42 | tbasyspara.csv | 0 | 202 | No | Empty |
| 43 | tbatax.csv | 839 | 15 | No | Tax rates |
| 44 | tbazjrptaddi.csv | 2 | 5 | No | ZJ report additional |
| 45 | tbazjrptfml.csv | 517 | 9 | No | ZJ report formula |
| 46 | tbazjsub.csv | 186 | 3 | No | ZJ sub |
| 47 | tbcaddress.csv | 3642 | 6 | No | Address book |
| 48 | tbcarapcon.csv | 5 | 12 | No | AR/AP config |
| 49 | tbcbaseno.csv | 1 | 4 | No | Base number |
| 50 | tbcpasswd.csv | 0 | 18 | No | Empty |
| 51 | tbcphrase.csv | 52 | 14 | No | Phrases |
| 52 | tbcpubsyspara.csv | 9 | 10 | No | Public system params |
| 53 | tbctacdef.csv | 1 | 12 | No | TAC definition |
| 54 | tbcversion.csv | 2 | 9 | No | Version |
| 55 | tbhsyspara.csv | 639 | 12 | No | Host system params |
| 56 | tbsagio.csv | 1 | 13 | No | AGIO |
| 57 | tbscurrency.csv | 5 | 21 | No | Currency master |
| 58 | tbscusfunkey.csv | 80 | 8 | No | Customer function keys |
| 59 | tbscust.csv | 1021 | 100 | No | Customer/supplier master |
| 60 | tbscustreptdef.csv | 72 | 4 | No | Customer report def |
| 61 | tbscustreptset.csv | 72 | 12 | No | Customer report set |
| 62 | tbscxdt.csv | 9 | 35 | No | CX detail |
| 63 | tbscxmain.csv | 9 | 22 | No | CX main |
| 64 | tbsdoevent.csv | 0 | 9 | No | Empty |
| 65 | tbsexpdefdt.csv | 377 | 6 | No | Expense definition detail |
| 66 | tbsexpdefmain.csv | 23 | 5 | No | Expense definition main |
| 67 | tbsfunkey.csv | 60 | 12 | No | Function keys |
| 68 | tbslocation.csv | 0 | 12 | No | Empty |
| 69 | tbslog.csv | 301459 | 10 | No | System log (large) |
| 70 | tbsno.csv | 6055 | 7 | No | Numbering sequence |
| 71 | tbsplusetsec.csv | 11 | 2 | No | Plus set security |
| 72 | tbsprepay.csv | 507 | 15 | No | Prepayment |
| 73 | tbsratio.csv | 59 | 8 | No | Ratio table |
| 74 | tbsremark.csv | 2219 | 5 | No | Remarks |
| 75 | tbsslipcpd.csv | 3 | 33 | No | Slip CPD |
| 76 | tbsslipctz.csv | 470 | 35 | No | Slip CTZ (sales?) |
| 77 | tbsslipdtcpd.csv | 12 | 32 | No | Slip detail CPD |
| 78 | tbsslipdtctz.csv | 5425 | 30 | No | Slip detail CTZ |
| 79 | tbsslipdtj.csv | 61727 | 78 | No | Purchase invoice DETAILS |
| 80 | tbsslipdto.csv | 832 | 94 | No | Slip DTO (other?) |
| 81 | tbsslipdtx.csv | 593016 | 73 | No | Sales invoice details (massive) |
| 82 | tbsslipexp.csv | 116 | 9 | No | Slip expense |
| 83 | tbsslipj.csv | 9249 | 96 | No | Purchase invoice HEADER |
| 84 | tbsslipo.csv | 269 | 114 | No | Purchase order header |
| 85 | tbsslipx.csv | 133418 | 103 | No | Sales invoice header |
| 86 | tbsspay.csv | 5 | 91 | No | Payment slip |
| 87 | **tbsstkhouse.csv** | **6587** | **15** | **YES - KEY** | Current inventory by warehouse |
| 88 | **tbsstkpave.csv** | **1646** | **56** | **YES - KEY** | Periodic stock snapshot (pave=avement=periodic) |
| 89 | **tbsstock.csv** | **6610** | **136** | **YES - KEY** | Product master (136 cols, very detailed) |
| 90 | tbsstorehouse.csv | 0 | 13 | No | Warehouse master (EMPTY) |
| 91 | tbssyspara.csv | 1174 | 10 | No | System parameters |
| 92 | **tbstmpqty.csv** | **22** | **3** | **YES** | Temp qty - small, possibly temp working data |
| 93 | tbsusrempl.csv | 0 | 8 | No | Empty |
| 94 | tbsusrhouse.csv | 0 | 7 | No | Empty |

---

## Inventory/Stock/Delivery Related Tables (DETAILED)

### 1. tbsstkhouse.csv - Current Inventory by Warehouse
- **Rows:** 6,587 | **Cols:** 15
- **Status:** Well documented in RELATIONSHIPS.md
- **Key columns (based on sample rows):**
  - Col 1: product_code (FK to tbsstock)
  - Col 2: status ('A'=Active)
  - Col 3: (empty)
  - Col 4: qty_onhand?
  - Col 5: qty_committed?
  - Col 6: (zero)
  - Col 7: qty_onorder?
  - Cols 8-11: more qty fields
  - Cols 12-14: (empty/zero)
  - Col 15: qty field
- **Purpose:** Current inventory levels by product+warehouse

### 2. tbsstkpave.csv - Periodic Stock Snapshot (PAVE = periodic/avenue snapshot)
- **Rows:** 1,646 | **Cols:** 56
- **Status:** NOT in RELATIONSHIPS.md - NEW discovery worth noting
- **Key columns (based on sample rows):**
  - Col 1: product_code
  - Col 2: warehouse_code ('0000')
  - Cols 3-55: many qty fields (all zeros in first rows) - possibly stock at different points in time or different warehouse sub-locations
  - Col 56: date-like field ('0000000000011')
- **Sample data:** Products like 'XPB-2410-P', 'RL165*18M/M', 'AT10-1720*12M/M' with all zeros
- **Hypothesis:** This is a **periodic stock snapshot** table - possibly monthly/weekly stock levels. The 56 columns may include:
  - Product + warehouse
  - Stock levels at different periods (e.g., 52 weeks = weekly snapshots)
  - Or stock across 56 warehouse sub-locations
- **Note:** Only 1646 rows vs 6610 products in tbsstock - suggests only a subset of products have periodic snapshots, or this is for specific warehouses only
- **Flag:** Needs deeper analysis - may contain historical stock levels not available elsewhere

### 3. tbsstock.csv - Product Master
- **Rows:** 6,610 | **Cols:** 136
- **Status:** Known in RELATIONSHIPS.md but full column mapping not done
- **Key columns (from sample):**
  - Col 1: product_code (PK)
  - Col 3: product_name (Chinese)
  - Col 8: supplier_code (FK to tbscust)
  - Col 9: supplier_name (e.g., '泰國')
  - Col 21: qty (288.0)
  - Col 22: amount (1267.20)
  - Col 31: date ('2022-06-28')
  - Col 32: date ('2025-04-22')
  - Col 33: price (314.2583)
  - Col 34: tax rate (19%)
  - Col 36: unit ('條')
  - Col 85: status ('A')
  - Col 86: numeric value
  - Col 130-131: 'Y', 'Y' flags
- **Flag:** 136 columns is extremely wide - needs full column mapping. Several quantity and price fields are present.

### 4. tbainvorail.csv - Stock Movement/Rail
- **Rows:** 89 | **Cols:** 35
- **Status:** In RELATIONSHIPS.md but not fully analyzed
- **Note:** Very small (89 rows) - possibly a control/setup table for stock movements rather than transaction data
- **Requires:** Full column header analysis

### 5. tbastktokj.csv - Stock Token/Keyword Journal
- **Rows:** 247 | **Cols:** 6
- **Status:** Partially analyzed
- **Key columns:**
  - Col 1: doc_number or flag ('0')
  - Col 2: line number (1, 2, 3...)
  - Col 3: account_code ('5101', '1194', '1111')
  - Col 4: description (Chinese - '本期進貨' = current period purchases, '進項稅額' = input tax, '現金' = cash)
  - Col 5: D/C flag ('D', 'C')
  - Col 6: amount (empty)
- **Purpose:** Journal entries for stock transactions - links to accounting. '5101' = purchases, '1194' = input tax, '1111' = cash
- **Note:** This is an accounting journal, NOT a stock transaction table. It records the accounting entries generated from stock movements.

### 6. tbstmpqty.csv - Temporary Quantity
- **Rows:** 22 | **Cols:** 3
- **Status:** Not in RELATIONSHIPS.md
- **Key columns (from sample):**
  - Col 1: order_number ('1140106011', '1140106012', '1140106013')
  - Col 2: sequence ('1')
  - Col 3: qty (43.0, 36.0, 25.0)
- **Hypothesis:** Temporary working table for quantity calculations - possibly during purchase order processing or inventory counting
- **Note:** Very small, 22 rows. Possibly a scratch/temp table

---

## Tables NOT in RELATIONSHIPS.md (but not necessarily inventory-related)

These tables exist in the CSV data but are NOT documented in RELATIONSHIPS.md:

| Table | Rows | Cols | Likely Purpose |
|-------|------|------|----------------|
| tbaadjust | 4 | 6 | Small adjustment |
| tbaamnt | 231 | 6 | Amount references |
| tbaarapctlsub | 23 | 8 | AR/AP control sub |
| tbabankitem | 3 | 4 | Bank items |
| tbacost | 68 | 3 | Cost categories |
| tbacostdetail | 17 | 8 | Cost detail |
| tbactlsub | 48 | 4 | Control sub |
| tbaemployitem | 24 | 17 | Employee items |
| tbaemplt | 61 | 3 | Employee plate |
| tbaflagdc | 27 | 4 | D/C flags |
| tbafncuse | 5 | 3 | Financial use |
| tbahealth | 49 | 9 | Health |
| tbahostlbtb | 809 | 28 | Host LBTB (tax?) |
| tbaiotypeset | 8 | 7 | IO type set |
| tbalbtb | 809 | 51 | LBTB records |
| tbarate | 24 | 9 | Rate table |
| tbaraterefer | 14 | 4 | Rate reference |
| tbarichkind | 7 | 6 | Rich kind |
| tbarptitvset | 25 | 5 | Report ITV set |
| tbasadset | 126 | 3 | SAD set |
| tbasecondlang | 62 | 4 | Second language |
| tbasetinfo | 73 | 7 | System set info |
| tbastktokj | 247 | 6 | Stock journal (accounting) |
| tbazjrptaddi | 2 | 5 | ZJ report add |
| tbazjrptfml | 517 | 9 | ZJ report formula |
| tbazjsub | 186 | 3 | ZJ sub |
| tbcaddress | 3642 | 6 | Address book |
| tbcarapcon | 5 | 12 | AR/AP config |
| tbcbaseno | 1 | 4 | Base number |
| tbcphrase | 52 | 14 | Phrases |
| tbctacdef | 1 | 12 | TAC definition |
| tbsagio | 1 | 13 | AGIO |
| tbscurrency | 5 | 21 | Currency |
| tbscusfunkey | 80 | 8 | Customer function keys |
| tbscustreptdef | 72 | 4 | Customer report def |
| tbscustreptset | 72 | 12 | Customer report set |
| tbscxdt | 9 | 35 | CX detail |
| tbscxmain | 9 | 22 | CX main |
| tbsexpdefdt | 377 | 6 | Expense definition detail |
| tbsexpdefmain | 23 | 5 | Expense definition main |
| tbsprepay | 507 | 15 | Prepayment |
| tbsratio | 59 | 8 | Ratio table |
| tbsremark | 2219 | 5 | Remarks |
| tbsslipcpd | 3 | 33 | Slip CPD |
| tbsslipctz | 470 | 35 | Slip CTZ |
| tbsslipdtcpd | 12 | 32 | Slip detail CPD |
| tbsslipdtctz | 5425 | 30 | Slip detail CTZ |
| tbsslipdto | 832 | 94 | Slip DTO |
| tbsspay | 5 | 91 | Payment slip |
| tbsstkpave | 1646 | 56 | Periodic stock snapshot |
| tbstmpqty | 22 | 3 | Temp qty |

---

## Key Findings

### NEW Inventory/Stock Related Tables Discovered

1. **tbsstkpave.csv** (1646 rows, 56 cols) - Periodic stock snapshot
   - NOT in RELATIONSHIPS.md
   - Contains product_code + warehouse + many qty columns + date
   - Likely stores periodic (weekly/monthly) stock snapshots
   - May contain historical stock data not available elsewhere

2. **tbstmpqty.csv** (22 rows, 3 cols) - Temporary quantity table
   - NOT in RELATIONSHIPS.md
   - Contains order_number + sequence + qty
   - Small working table for quantity calculations

### Already-Known Inventory Tables (from RELATIONSHIPS.md)

- **tbsstkhouse.csv** - Current inventory by warehouse (6587 rows, 15 cols)
- **tbsstock.csv** - Product master (6610 rows, 136 cols)
- **tbainvorail.csv** - Stock movement rail (89 rows, 35 cols)
- **tbastktokj.csv** - Stock accounting journal (247 rows, 6 cols)

### Tables With "Stock/Inventory" in Name (all reviewed)

| Table | Rows | Cols | Status |
|-------|------|------|--------|
| tbsstkhouse | 6587 | 15 | Documented |
| tbsstkpave | 1646 | 56 | NOT documented - periodic snapshot |
| tbsstock | 6610 | 136 | Documented (partial) |
| tbastktokj | 247 | 6 | Documented (partial) |
| tbainvorail | 89 | 35 | Documented (not fully analyzed) |

### No "Delivery" or "Supplier" Specific Tables Found

- No tables explicitly named with "delivery", "receive", "supplier" in the filename
- Supplier info is in tbscust (customer/supplier combined, type='1' = supplier)
- Delivery/receiving is handled through purchase invoices (tbsslipj, tbsslipdtj) and purchase orders (tbsslipo)

---

## Recommendations for Further Analysis

1. **tbsstkpave.csv** - Need to understand the 56 column structure. Hypothesis: 52 weekly snapshots + product/warehouse cols. Check if dates appear in col 56.

2. **tbsstock.csv** - Full 136-column mapping needed. Key fields for inventory: qty fields (cols 21+), supplier info (col 8), dates (cols 31-32).

3. **tbsstkhouse.csv** - Already well understood. Current on-hand inventory by warehouse.

4. **tbainvorail.csv** - 89 rows is small. May be control records for stock movements. Full header analysis needed.

5. **tbstmpqty.csv** - 22 rows suggests temporary working data. May not be relevant for migration.
