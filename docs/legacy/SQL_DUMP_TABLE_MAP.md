# SQL Dump Table Map — cao50001.sql

**Source:** `legacy data/cao50001.sql`
**Total tables:** 514 CREATE TABLE statements
**Extracted:** 2026-04-12

---

## Overview

The dump contains 514 tables. Many `otb*` prefixed tables (e.g., `otbainvorail`, `otbainvodetail`) are **empty** (0 rows) — these appear to be staging/archival shadow tables that were never populated in the legacy system. The primary business tables use the `tbs*` prefix.

---

## Inventory / Stock Tables

These are the tables most relevant to the stock/inventory/delivery/receiving domain.

### `tbsstkhouse` — Inventory by Product + Warehouse
**Rows: 6,588**

Primary stock-on-hand table. One row per (product code, warehouse) combination.

| Column | Type | Purpose |
|--------|------|---------|
| `sstkno` | varchar(30) | Product code (PK part 1) |
| `shouseno` | varchar(10) | Warehouse code (PK part 2) |
| `sstoreplace` | varchar(30) | Storage location |
| `fbeginqty` | numeric | Opening/qty at period start |
| `fsafeqty` | numeric | Safety stock threshold |
| `flimitqty` | numeric | Reorder point / limit qty |
| `fcurqty` | numeric | Current quantity on hand |
| `fbrowqty` | numeric | Borrowed quantity |
| `flendqty` | numeric | Lent quantity |
| `fstkendqty` | numeric | Closing qty at period end |
| `fslendqty` | numeric | Lent qty (secondary) |
| `fsbrowqty` | numeric | Borrowed qty (secondary) |
| `stimestamp` | varchar(18) | Last-modified timestamp |
| `smodifyflag` | varchar(80) | Modification flag |
| `splacerem` | varchar(250) | Place remarks |

**Key fields for receiving/delivery:** `fcurqty`, `fbeginqty`, `fstkendqty`, `flimitqty`, `fsafeqty`
**Stock movement relationship:** Links `sstkno` → `tbsstock.sstkno` and `shouseno` → warehouse master.

---

### `tbsstock` — Product Master
**Rows: 6,611**

Core product/stock item master. Contains pricing, units, specs, reorder parameters.

| Column | Type | Purpose |
|--------|------|---------|
| `sstkno` | varchar(30) | Product code (PK) |
| `sstkname` | varchar(80) | Product name |
| `sstkname2` | varchar(120) | Product name (alt) |
| `sclassno` | varchar(10) | Product class |
| `sstkspec` | text | Specifications |
| `sstkkind` | varchar(1) | Stock kind |
| `scustno` | varchar(16) | Preferred supplier code |
| `scustname` | varchar(250) | Preferred supplier name |
| `sunitbase` | varchar(16) | Base unit |
| `sunit1`, `sunit2` | varchar(16) | Alternate units |
| `frate1`, `frate2` | numeric | Conversion rates |
| `fprice1`–`fprice6` | numeric | Various prices |
| `finprice` | numeric | Cost/inbound price |
| `foutprice` | numeric | Sales/outbound price |
| `fbeginqty` | numeric | Opening stock qty |
| `fsafeqty` | numeric | Safety stock |
| `fcurqty` | numeric | Current stock |
| `fecmqty` | numeric | On-order qty |
| `forderpoint` | numeric | Reorder point |
| `fminorderqty` | numeric | Minimum order qty |
| `fmaxorderqty` | numeric | Maximum order qty |
| `iorderperiod` | integer | Order review period |
| `ipoleadtime` | integer | PO lead time days |
| `iphperiod` | integer | Planning horizon days |
| `iassembleleadtime` | integer | Assembly lead time |
| `itotalleadtime` | integer | Total lead time |
| `sorderpolicy` | varchar(3) | Replenishment policy (LFL etc.) |
| `favrgpave` | numeric | Average price |
| `dtindate` | date | Stock-in date |
| `dtoutdate` | date | Stock-out date |
| `scorpcode` | varchar(4) | Corporation code |

**Relationships:** `scustno` → `tbscust`. `sstkno` → `tbsstkhouse`, `tbsslipdtx`, `tbsslipdtj`.

---

### `tbsstkserial` — Stock Serial / Lot Tracking
**Rows: 248**

Tracks individual serial numbers or lot numbers per product.

| Column | Type | Purpose |
|--------|------|---------|
| `sstkno` | varchar(30) | Product code (PK part 1) |
| `sserialno` | varchar(30) | Serial/lot number (PK part 2) |
| `sstate` | varchar(1) | State (in/out) |
| `dtindate` | date | Date received |
| `dtoutdate` | date | Date shipped |
| `dtdonedate` | date | Date completed |
| `sfactoryno` | varchar(16) | Factory code |
| `scustno` | varchar(16) | Customer/supplier code |
| `sslipno` | varchar(17) | Related slip number |
| `shouseno` | varchar(10) | Warehouse |
| `dtbhdate` | date | Manufacture date |
| `scorpcode` | varchar(4) | Corporation code |

---

### `tbsstkserialdt` — Stock Serial Detail / Movement Log
**Rows: Not present (0)**

Appears to track movements/changes to serial numbers but is empty.

---

### `tbsstkpave` — Stock Pave / Periodic Stock Summary
**Rows: 0 (empty)**

Monthly stock quantity and amount summaries (month01–month12 columns). Empty in this dump.

---

### `tbsstklocation` — Stock Location (Product + Warehouse + Bin)
**Rows: 0 (empty)**

Bin-level location tracking per product per warehouse. Empty.

---

### `tbsstklendqty` — Stock Lending/Borrowing Quantity
**Rows: 0 (empty)**

Tracks inter-company or inter-warehouse stock lending. Empty.

---

### `tbsstkblback` — Stock Borrow/Lend Balance
**Rows: 0 (empty)**

Borrow/lend balance tracking. Empty.

---

### `tbsstkinvoice` — Stock Invoice
**Rows: 0 (empty)**

Monthly stock invoice header. Empty.

---

### `tbsstkyard` — Stock Yard / Factory Yard
**Rows: 0 (empty)**

Yard/stockyard tracking. Empty.

---

### `tbsstkrpl` — Stock Replenishment
**Rows: 0 (empty)**

Replenishment rules. Empty.

---

### `tbsstkmeans` — Stock Means / Methods
**Rows: 0 (empty)**

Stock handling methods. Empty.

---

### `tbsstkclass` — Stock Classification
**Rows: 0 (empty)**

Product/stock classification master. Empty.

---

### `tbainvorail` — Inventory Rail / Summary (tb prefix)
**Rows: 90**

Period-based inventory summary with period codes a1–a4, b1–b7.

| Column | Type | Purpose |
|--------|------|---------|
| `syear` | varchar(4) | Year |
| `perioddate` | varchar(2) | Period/month |
| `a1`–`a4`, `b1`–`b7` | varchar(2) | Period allocation codes |

**Note:** Only 90 rows. Likely a small summary/aggregation table.

---

### `otbainvorail` — Inventory Rail (otb prefix / shadow archive)
**Rows: 0 (empty)**

Shadow version of `tbainvorail`. Empty.

---

### `otbainvodetail` — Inventory Detail (otb prefix / shadow archive)
**Rows: 0 (empty)**

Shadow archive of inventory detail. Empty.

---

### `tbsinout` — Stock In/Out Transactions
**Rows: 0 (empty)**

Direct stock in/out transaction log. Empty — likely movements are tracked through slip tables instead.

---

### `tbainvodetail` — Inventory Detail (tb prefix)
**Rows: 0 (empty)**

---

### `tbainvstock` — Inventory Stock (tb prefix)
**Rows: 0 (empty)**

---

### `tbastktokj` — Stock Token/Kind Mapping
**Rows: 248**

| Column | Type | Purpose |
|--------|------|---------|
| `kind` | varchar(1) | Kind code (PK) |
| `iserial` | integer | Serial (PK) |
| `subno` | varchar(14) | Sub-number |
| `subname` | varchar(40) | Sub-name |
| `doc` | varchar(1) | Document kind |
| `smodifyflag` | varchar(80) | Modification flag |

**Note:** 248 rows matching `tbsstkserial` count. Appears to be a kind/class reference for serial numbers.

---

## Receiving / Delivery / In-Out Slip Tables

### `tbsslipj` — Purchase Receipt Header (AP/入庫)
**Rows: 9,250**

Purchase invoice/receipt header. Links to supplier, totals, tax, payment terms.

| Column | Type | Purpose |
|--------|------|---------|
| `skind` | varchar(4) | Document kind (PK) |
| `sslipno` | varchar(17) | Slip number (PK) |
| `dtslipdate` | date | Slip date |
| `stslipno` | varchar(16) | Transfer slip number |
| `sformat` | varchar(16) | Format |
| `sopslipno` | varchar(30) | Operation slip number |
| `scustno` | varchar(16) | Supplier code |
| `scustname` | varchar(250) | Supplier name |
| `scurno` | varchar(10) | Currency code |
| `fexrate` | numeric | Exchange rate |
| `ftotalamt` | numeric | Total amount |
| `ftaxamt` | numeric | Tax amount |
| `fpayamt` | numeric | Payment amount |
| `fcxamt` | numeric | Cash amount |
| `staxtype` | varchar(1) | Tax type |
| `fdiscount` | numeric | Discount |
| `fdisper` | numeric | Discount percent |
| `sman` | varchar(30) | Sales/purchase rep |
| `scheckflag` | varchar(1) | Check flag |
| `ssyschkflag` | varchar(1) | System check flag |
| `stransflag` | varchar(1) | Transfer flag |
| `sinvkind` | varchar(2) | Invoice kind |
| `sinvno` | varchar(240) | Invoice number |
| `scorpcode` | varchar(4) | Corporation code |
| `ssrslip` | varchar(17) | Related SR slip |

**Relationships:** `scustno` → `tbscust`. Lines in `tbsslipdtj`. Stock updates `tbsstkhouse` via receiving.

---

### `tbsslipdtj` — Purchase Receipt Detail
**Rows: 61,728**

Purchase invoice/receipt line items. Contains product, qty, price, warehouse.

| Column | Type | Purpose |
|--------|------|---------|
| `skind` | varchar(4) | Document kind (PK) |
| `sslipno` | varchar(17) | Slip number (PK) |
| `iabsno` | integer | Line number (PK) |
| `dtslipdate` | date | Slip date |
| `sstkno` | varchar(30) | Product code |
| `sstkname` | varchar(80) | Product name |
| `shouseno` | varchar(10) | Warehouse code |
| `shousename` | varchar(20) | Warehouse name |
| `fstkqty` | numeric | Quantity |
| `sunit` | varchar(16) | Unit |
| `fprice` | numeric | Unit price |
| `fsttotal` | numeric | Line total |
| `ftax` | numeric | Tax |
| `fcxamt` | numeric | Cash amount |
| `fdisper` | numeric | Discount percent |
| `fdiscount` | numeric | Discount |
| `srem` | varchar(250) | Remark |
| `stransflag` | varchar(1) | Transfer flag |
| `scorpcode` | varchar(4) | Corporation code |

**Relationships:** `sstkno` → `tbsstock`. `shouseno` → warehouse. `sslipno` → `tbsslipj`.

---

### `tbsslipx` — Sales Slip Header
**Rows: 133,448**

Sales invoice/order header. Primary sales transaction table.

| Column | Type | Purpose |
|--------|------|---------|
| `skind` | varchar(4) | Document kind (PK) |
| `sslipno` | varchar(17) | Slip number (PK) |
| `dtslipdate` | date | Slip date |
| `scustno` | varchar(16) | Customer code |
| `scustname` | varchar(250) | Customer name |
| `ftotalamt` | numeric | Total amount |
| `ftaxamt` | numeric | Tax amount |
| `fpayamt` | numeric | Payment amount |
| `fcxamt` | numeric | Cash amount |
| `staxtype` | varchar(1) | Tax type |
| `scheckflag` | varchar(1) | Check flag |
| `stransflag` | varchar(1) | Transfer flag |
| `scorpcode` | varchar(4) | Corporation code |

---

### `tbsslipdtx` — Sales Slip Detail
**Rows: 593,017**

Sales line items.

| Column | Type | Purpose |
|--------|------|---------|
| `skind` | varchar(4) | Document kind (PK) |
| `sslipno` | varchar(17) | Slip number (PK) |
| `iabsno` | integer | Line number (PK) |
| `dtslipdate` | date | Slip date |
| `sstkno` | varchar(30) | Product code |
| `sstkname` | varchar(80) | Product name |
| `shouseno` | varchar(10) | Warehouse code |
| `fstkqty` | numeric | Quantity sold |
| `sunit` | varchar(16) | Unit |
| `fprice` | numeric | Unit price |
| `fsttotal` | numeric | Line total |
| `fcxamt` | numeric | Cash amount |

---

### `tbssliph` — Slip H (empty)
**Rows: 0**

---

### `tbsslipdth` — Slip Detail H (empty)
**Rows: 0**

---

### `tbsslips` — Slip S (POS?)
**Rows: 0**

---

## Other Slip Variants (all empty in this dump)

| Table | Purpose | Rows |
|-------|---------|------|
| `otbaslip` | Archive slip | 0 |
| `otbssliph` | Archive slip H | 0 |
| `otbsslips` | Archive slip S | 0 |
| `otbsslipx` | Archive slip X | 0 |
| `otbsslipj` | Archive slip J | 0 |
| `otbsslipdtj` | Archive slip J detail | 0 |
| `otbsslipdtx` | Archive slip X detail | 0 |
| `otbsslipw` | Archive slip W | 0 |
| `otbsslipdto` | Archive slip O detail | 0 |
| `otbsslipdtp` | Archive slip P detail | 0 |
| `otbsslipdtpc` | Archive slip PC detail | 0 |
| `otbsslipdtq` | Archive slip Q detail | 0 |
| `otbsslipdtv` | Archive slip V detail | 0 |
| `otbsslipdty` | Archive slip Y detail | 0 |
| `otbsslipdtzj` | Archive slip ZJ detail | 0 |
| `otbsslipdvr` | Archive slip DVR detail | 0 |
| `otbssliphey` | Archive slip HEY | 0 |
| `otbsslipdthey` | Archive slip HEY detail | 0 |

---

## Master Data Tables

### `tbscust` — Customer/Supplier Party Master
**Rows: 1,023**

Unified party master for both customers and suppliers. `skind` = '1' typically = customer, '2' = supplier.

| Column | Type | Purpose |
|--------|------|---------|
| `scustno` | varchar(16) | Party code (PK) |
| `skind` | varchar(1) | Kind (customer/supplier) |
| `scustname` | varchar(250) | Party name |
| `scustname2` | varchar(250) | Alt name |
| `saddr1`–`saddr3` | varchar(250) | Addresses |
| `stelno` | varchar(40) | Phone |
| `sfaxno` | varchar(40) | Fax |
| `semail` | varchar(250) | Email |
| `sunino` | varchar(20) | Tax ID / uniform number |
| `sfaxfile` | varchar(30) | Fax file |
| `sbank` | varchar(80) | Bank name |
| `sbankaccount` | varchar(80) | Bank account |
| `staxno` | varchar(80) | Tax number |
| `spricemode` | varchar(1) | Price mode |
| `fpaylimit` | numeric | Payment limit |
| `fchklimit` | numeric | Credit check limit |
| `fprepay` | numeric | Prepayment amount |
| `fdisper` | numeric | Discount percent |
| `fcxowe` | numeric | Current balance owed |
| `sacntno` | varchar(20) | AR/AP account number |
| `scurno` | varchar(10) | Currency |
| `spaymode` | varchar(10) | Payment mode |
| `sratekind` | varchar(1) | Rate kind |
| `dtcreatedate` | date | Creation date |
| `scorpcode` | varchar(4) | Corporation code |
| `slogincode` | varchar(19) | Login code |
| `scustkind` | varchar(1) | Customer kind |
| `sstksource` | varchar(1) | Stock source flag |

---

### `tbslog` — System Log
**Rows: 301,460**

System operation log. Not business-critical. Archive separately.

---

### `tbslocation` — Warehouse/Location Master
**Rows: 1**

| Column | Type | Purpose |
|--------|------|---------|
| `shouseno` | varchar(10) | Warehouse code (PK) |
| `shouseloc` | varchar(10) | Location code (PK) |
| `shousename` | varchar(20) | Warehouse name |
| `slocname` | varchar(20) | Location name |
| `sdefault` | varchar(1) | Default flag |

---

### `tbslocationdl` — Warehouse Location Detail Log
**Rows: ~90 (inferred)**

Tracks location-level stock movements.

| Column | Type | Purpose |
|--------|------|---------|
| `skind` | varchar(4) | Kind (PK) |
| `sslipno` | varchar(17) | Slip number (PK) |
| `iabsno` | integer | Abs number (PK) |
| `iidno` | integer | ID number (PK) |
| `dtslipdate` | date | Slip date |
| `sstkno` | varchar(30) | Product code |
| `shouseno` | varchar(10) | Warehouse |
| `shouseloc` | varchar(30) | Bin/location |
| `fstkqty` | numeric | Quantity |
| `sunit` | varchar(16) | Unit |

---

### `tbsstorehouse` — Store/Warehouse Master
**Rows: 1**

Single-row warehouse master.

---

## Product & BOM Tables

### `tbsstockdt` — Stock Detail / Extended Product Info
**Rows: 0 (empty)**

Extended product details: specs, origin, manufacturing info. Empty.

---

### `tbsstockfactory` — Stock Factory/Origin Info
**Rows: 0 (empty)**

---

### `tbsbom` — Bill of Materials
**Rows: 0 (empty)**

---

### `tbsbomdt` — Bill of Materials Detail
**Rows: 0 (empty)**

---

### `tbsbomslip` / `tbsbomslipdt` — BOM Slip
**Rows: 0 (empty)**

---

## Purchase / Payment Tables

### `tbsslipdtj` — See "Purchase Receipt Detail" above

### `tbsprepay` — Prepayment
**Rows: 0 (empty)**

---

### `tbsspay` — Special Payment
**Rows: 0 (empty)**

---

### `otbaapay` — Accounts Payable Payment (archive)
**Rows: 0 (empty)**

---

## Summary: Active vs Empty Tables

| Category | Table | Rows | Status |
|----------|-------|------|--------|
| **Stock on hand** | `tbsstkhouse` | 6,588 | Active |
| **Product master** | `tbsstock` | 6,611 | Active |
| **Serial/lot tracking** | `tbsstkserial` | 248 | Active |
| **Purchase receipts** | `tbsslipj` | 9,250 | Active |
| **Purchase receipt lines** | `tbsslipdtj` | 61,728 | Active |
| **Sales slip headers** | `tbsslipx` | 133,448 | Active |
| **Sales slip lines** | `tbsslipdtx` | 593,017 | Active |
| **Customer/supplier master** | `tbscust` | 1,023 | Active |
| **Location detail log** | `tbslocationdl` | ~90 | Active |
| **Inventory rail (tb prefix)** | `tbainvorail` | 90 | Active |
| **Stock token kind** | `tbastktokj` | 248 | Active |
| **System log** | `tbslog` | 301,460 | Active (archive candidate) |
| **Stock location (P+W+B)** | `tbsstklocation` | 0 | Empty |
| **Stock lend qty** | `tbsstklendqty` | 0 | Empty |
| **Stock borrow/lend** | `tbsstkblback` | 0 | Empty |
| **Stock invoice** | `tbsstkinvoice` | 0 | Empty |
| **Stock yard** | `tbsstkyard` | 0 | Empty |
| **Stock pave** | `tbsstkpave` | 0 | Empty |
| **Stock replenishment** | `tbsstkrpl` | 0 | Empty |
| **Stock serial detail** | `tbsstkserialdt` | 0 | Empty |
| **All otb* archive tables** | (multiple) | 0 | Empty |
| **All slip H/S/W/O/P/PC/Q/V/Y/ZJ/DVR variants** | (multiple) | 0 | Empty |

---

## Key Relationships for Stock Movements

```
tbsslipdtj (purchase lines)
  ├── sstkno → tbsstock (product)
  ├── shouseno → tbsstkhouse (warehouse)
  └── sslipno → tbsslipj (purchase header)

tbsslipdtx (sales lines)
  ├── sstkno → tbsstock (product)
  ├── shouseno → tbsstkhouse (warehouse)
  └── sslipno → tbsslipx (sales header)

tbsstkhouse (inventory by P+W)
  ├── sstkno → tbsstock (product)
  └── shouseno → warehouse

tbsstkserial (serial tracking)
  ├── sstkno → tbsstock
  └── sslipno → slip source

tbastktokj (stock kind mapping)
  └── kind → serial kind reference
```

---

## Notes

- **No direct 入庫/出庫 tables found** with Chinese naming. Stock movements are tracked via slip tables (`tbsslipj`/`tbsslipdtj` for receiving, `tbsslipx`/`tbsslipdtx` for sales/delivery), NOT via separate dedicated in/out transaction tables.
- **`tbsinout`** table exists but is empty (0 rows) — no separate in/out movement log.
- **`tbsstkhouse`** is the primary current-stock table. It is NOT updated in real-time by slips but appears to be a periodic snapshot/warehouse-level rollup.
- **The `otb*` tables** (otbainvorail, otbainvodetail, otbaslip, etc.) are all empty — likely staging/archive tables from a parallel run or legacy export process that were never populated.
- **Corporation code** (`scorpcode`) appears in most tables — multi-tenant/multi-corporation ERP structure.
