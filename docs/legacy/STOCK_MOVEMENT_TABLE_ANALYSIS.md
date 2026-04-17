# Stock Movement Table Analysis: tbainvorail and tbastktokj

## Executive Summary

| Table | Manifest Description | Actual Content | Rows | Assessment |
|-------|---------------------|----------------|------|------------|
| tbainvorail | Inventory rail settings | Period-based allocation rules (ROC bimonthly periods 2002-2016) | 90 | NOT a stock movement journal |
| tbastktokj | Stock to KJ mapping | Accounting journal entries (D/C accounts) | 248 | NOT a stock movement journal |

**Conclusion:** Neither table is a usable stock movement/delivery history record. tbastktokj contains accounting journal data, and tbainvorail contains period-based allocation settings.

---

## 1. tbainvorail Analysis

### File Locations
- `/Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/extracted_data/tbainvorail.csv` (90 rows)
- `/Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/extracted_data/cao50001/tbainvorail.csv` (identical)

### Data Structure
**Columns (28 fields per row):**
| Position | Content | Type | Example |
|----------|---------|------|---------|
| 1 | Year (ROC) | string | '2002' |
| 2 | Period (bimonthly) | string | '01', '03', '05'... |
| 3-26 | Product/account codes | string | 'LA', 'LB', 'LC'... |
| 27-28 | Empty | - | '' |

### All Data Rows (90 rows)
The data spans **ROC years 2002-2016** in bimonthly periods (01, 03, 05, 07, 09, 11 = Jan, Mar, May, Jul, Sep, Nov).

| Row# | Year | Period | Code Set |
|------|------|--------|----------|
| 1-2 | 2002 | 01, 03 | LA-LY, LZ-MX |
| 3-4 | 2002 | 05, 07 | MY-NW, NX-PV |
| 5-6 | 2002 | 09, 11 | PW-QU, QV-RT |
| 7-8 | 2003 | 01, 03 | RU-ST, SU-TT |
| 9-10 | 2003 | 05, 07 | TU-VT, UU-VT |
| ... | ... | ... | ... |
| 85-86 | 2016 | 01, 03 | AU-FG, BM-HN |
| 87-88 | 2016 | 05, 07 | CD-JR, CV-JR |
| 89-90 | 2016 | 09, 11 | DM-MN, ED-LX |

### Pattern Analysis
- **Year format:** ROC (民國) - 2002 = 1911+2002 = AD 2013? No - this appears to be raw ROC without adding 1911
- **Period codes:** Single or double digit bimonthly periods (01, 03, 05, 07, 09, 11)
- **Product-like codes:** LA, LB, LC... AZ, BA, BB... etc. (alphabetical, 2-letter codes)

### Interpretation
This appears to be **period-based allocation rules or rail settings** mapping bimonthly periods to product groups (LA, LB, etc.). It is NOT a stock movement journal with individual transaction records.

---

## 2. tbastktokj Analysis

### File Locations
- `/Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/extracted_data/tbastktokj.csv` (248 rows)
- `/Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/extracted_data/cao50001/tbastktokj.csv` (identical)

### Data Structure
**Columns (6 fields per row):**
| Position | Content | Type | Example |
|----------|---------|------|---------|
| 1 | Slip/Group ID | string | '0', '1', '2'... 'V' |
| 2 | Line number | integer | 1, 2, 3... |
| 3 | Account code | string | '5101', '1194', '1111'... |
| 4 | Account name (Big5) | string | '本期進貨', '進項稅額', '現金'... |
| 5 | D/C (Debit/Credit) | string | 'D' or 'C' |
| 6 | Empty | string | '' |

### All Data Rows (248 rows)

#### Group '0' (Rows 1-5): 本期進貨 (Current Period Purchases)
| Line | Acct Code | Account Name | D/C |
|------|-----------|--------------|-----|
| 1 | 5101 | 本期進貨 | D |
| 2 | 1194 | 進項稅額 | D |
| 3 | 1111 | 現金 | C |
| 4 | 2122 | 應付帳款 | C |
| 5 | 5103 | 進貨折讓 | C |

#### Group '1' (Rows 6-10): 進貨退出 (Purchase Returns)
| Line | Acct Code | Account Name | D/C |
|------|-----------|--------------|-----|
| 1 | 1111 | 現金 | D |
| 2 | 2122 | 應付帳款 | D |
| 3 | 5103 | 進貨折讓 | D |
| 4 | 5102 | 進貨退出 | C |
| 5 | 1194 | 進項稅額 | C |

#### Group '2' (Rows 11-16): 銷貨收入 (Sales Revenue)
| Line | Acct Code | Account Name | D/C |
|------|-----------|--------------|-----|
| 1 | 1111 | 現金 | D |
| 2 | 1138 | 其他應收款－其他 | D |
| 3 | 1123 | 應收帳款 | D |
| 4 | 4103 | 銷貨折讓 | D |
| 5 | 4101 | 銷貨收入 | C |
| 6 | 2194 | 銷項稅額 | C |

#### Group '3' (Rows 17-22): 銷貨退回 (Sales Returns)
#### Group '4' (Rows 23-27): 外包加工費用 (Outsourcing Fees)
#### Group '5' (Rows 28-32): 外包加工費用 (Outsourcing - alternative)
#### Group '6' (Rows 33-76): 廣告費 (Advertising Expenses) - extensive
#### Groups '7' through 'J' and 'U', 'V' (Rows 77-248): Various accounting entries

### Pattern Analysis
- **D/C values:** 'D' (Debit) and 'C' (Credit) - standard double-entry accounting
- **Account codes:** 4-digit codes matching tbasubject (chart of accounts)
- **Account names:** Chinese names in Big5 encoding (e.g., '本期進貨', '應付帳款')
- **Group IDs:** '0'-'9', 'A'-'J', 'U', 'V' - slip types

### Interpretation
This is an **accounting journal template or mapping table** defining which accounts are debited/credited for each transaction type (slip kind). It is NOT a stock movement journal.

---

## 3. Cross-Reference: Are These Tables Referenced in Migration Code?

**File searched:** `/Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/src/canonical.py`

**Result:** No `canonical.py` file exists in the migration pipeline src directory. The migration code consists of:
- `parser.py` - SQL dump parser
- `detector.py` - Encoding detection
- `cleaner.py` - Data cleaning utilities
- `cli.py` - Command-line interface

**References to tbainvorail/tbastktokj:** None found in migration code.

---

## 4. Actual Stock Movement Tables in This Dataset

Based on the MANIFEST and RELATIONSHIPS documentation, the actual tables for stock/inventory are:

| Table | Rows | Description |
|-------|------|-------------|
| tbsstock | 6,611 | Product/Inventory master |
| tbsstkhouse | 6,588 | Stock by warehouse |
| tbsstkpave | 1,647 | Stock pavement |
| tbsslipdtj | 61,728 | Purchase invoice line items (movement in) |
| tbsslipdtx | 593,017 | Sales invoice line items (movement out) |

**tbsstkhouse** contains current inventory quantities by warehouse and would be updated from purchase invoices (tbsslipdtj).

---

## 5. Answer to Key Question

### Could tbainvorail be a usable stock movement record?
**No.** It contains period-based allocation rules/settings, not individual transaction records. It has only 90 rows spanning bimonthly periods, with product-like codes but no quantities, dates, or transaction details.

### Could it reconstruct delivery history?
**No.** There are no delivery transaction records, no supplier/customer references, no quantities, and no dates beyond year/period.

---

## 6. Recommendations

1. **Do not migrate tbainvorail or tbastktokj** as stock movement sources
2. **Use tbsslipdtj (Purchase Invoice Details)** for incoming stock movements
3. **Use tbsslipdtx (Sales Invoice Details)** for outgoing stock movements
4. **Use tbsstkhouse** for current inventory snapshots
5. **Cross-reference tbsstkhouse with purchase invoices** to reconstruct movement history if needed

---

## Appendix: Data Quality Notes

- tbainvorail has encoding issues (Big5 mojibake visible in some displays)
- tbastktokj accounting names corrupted when viewed in UTF-8 (expected Big5 content)
- Both files have Windows CRLF line endings (observed via `cat -v`)
