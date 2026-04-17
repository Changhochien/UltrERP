# Purchase Invoice Table Analysis: tbsslipj and tbsslipdtj

## Overview

| Table | Rows | Columns | Purpose |
|-------|------|---------|---------|
| tbsslipj | 9,250 | 96 | Purchase invoice header |
| tbsslipdtj | 61,728 | 78 | Purchase invoice line items |

## TBSSLIPJ (Purchase Invoice Header)

### Column Mapping (from CSV position to field meaning)

Based on analysis of sample data and existing schema migrations:

| Pos | Field Name | Sample Value | Purpose |
|-----|------------|--------------|---------|
| 1 | slip_type | '4' | Document type: 4=Purchase |
| 2 | doc_number | '1130827001' | **Primary key** - Invoice number (ROC date + sequence) |
| 3 | invoice_date | '2024-08-27' | **Date when invoice was issued** |
| 4 | invoice_number | '1130827001' | Invoice number (same as doc_number) |
| 5 | date_pattern | 'YYYMMDD999' | Format pattern |
| 7 | supplier_code | 'T067' | FK to tbscust (supplier) |
| 8 | supplier_name | '勝梨' | Supplier name (denormalized) |
| 9 | address | '桃園市中壢區...' | Delivery address |
| 10 | dept_code | '0001' | Department/business unit |
| 11 | currency_name | '新臺幣' | Currency |
| 12 | exchange_rate | 1.00000000 | Exchange rate |
| 13 | payment_term | 'T067' | Payment terms code |
| 17 | subtotal | 1265.00000000 | Amount before tax |
| 18 | tax_type | '3' | Tax classification |
| 19 | tax_amount | 0.00000000 | Tax amount |
| 30 | period_code | '11308' | ROC accounting period (2024-08) |
| 31 | created_by | '系統管理員' | User who created |
| 33 | order_status | '1' | Status: 1=Active |
| 34 | record_sequence | 1 | Sequence number |
| 37 | contact_phone | '03-4614001~3' | Contact phone |
| 41 | business_unit | '21' | Business unit code |
| 48 | subtotal_2 | 1265.00000000 | Alternate subtotal |
| 49 | total_amount | 1265.00000000 | **Final total amount** |
| 50 | payment_status | '0' | Payment status flag |
| 51 | **date_field** | '2024-08-27' | **Possibly payment date or receiving confirmation date** |
| 52 | exchange_rate_2 | 0.40728182 | Alternate exchange rate |
| 53 | fax | '03-4614501' | Fax number |
| 57 | create_timestamp | '202408270946290879' | Creation timestamp (ROC format) |
| 62 | **date_field_2** | '2024-08-27' | **Another date - possibly due date or receiving date** |
| 73 | status | 'A' | Record status |
| 74 | numeric_field | 45531.40728275 | Unknown numeric |
| 75 | warehouse_status | 'A' | Warehouse status |
| 77 | cost | 45531.40684502 | Cost value |
| 78 | tax_rate | 0.05000000 | Tax rate (5%) |
| 88 | **date_1900** | '1900-01-01' | Placeholder date |

### Date Fields in tbsslipj

| Column Position | Likely Meaning | Evidence |
|----------------|----------------|----------|
| Field 3 | **Invoice date** - when invoice was issued | '2024-08-27' matches ROC date in doc_number |
| Field 51 | **Unknown** - possibly payment confirmation or receiving confirmation | '2024-08-27' in sample |
| Field 62 | **Unknown** - possibly due date or receiving date | '2024-08-27' in sample |
| Field 88 | Placeholder (1900-01-01) | Default empty value |

**Note**: The dates are already in AD format (2024-08-27), NOT ROC format. The ROC date is encoded in the doc_number (e.g., 1130827 = Year 113 ROC = 2024).

## TBSSLIPDTJ (Purchase Invoice Detail)

### Column Mapping

| Pos | Field Name | Sample Value | Purpose |
|-----|------------|--------------|---------|
| 1 | slip_type | '4' | Document type: 4=Purchase |
| 2 | doc_number | '1130827001' | **FK to tbsslipj.doc_number** |
| 3 | line_number | 1 | Line sequence number |
| 4 | invoice_date | '2024-08-27' | Invoice date (matches header) |
| 5 | supplier_code | 'T067' | Supplier code |
| 6 | product_code | 'XPB-2410-P' | **FK to tbsstock.product_code** |
| 7 | product_name | 'XPB-2410 進口' | Product description |
| 10 | quantity_1 | 1.00000000 | Primary quantity |
| 11 | unit | '*' | Unit indicator |
| 16 | status | 'A' | Line status |
| 17 | warehouse_name | '總倉' | **Warehouse name ("Main warehouse")** |
| 18 | unit_name | '條' | Unit of measure |
| 19 | **qty** | 395.00000000 | **Quantity ordered/received** |
| 20 | **unit_price** | 1.00000000 | **Unit price** |
| 21 | **extended_amount** | 395.00000000 | Line total (qty × unit_price) |
| 22 | tax_percent | 3.00000000 | Tax percent |
| 23 | tax_flag | 'N' | Tax included flag |
| 26 | line_total | 1185.00000000 | Total including tax |
| 34 | qty_delivered | 3.00000000 | **Quantity actually delivered** |
| 35 | qty_balance | 3.00000000 | Balance pending |
| 38 | line_seq | 1 | Line sequence |
| 39 | sub_line | -1 | Sub-line indicator |
| 41 | line_amount | 395.00000000 | Line amount |
| 46 | **delivery_date** | '2024-08-27' | **Date when goods were/will be delivered** |
| 47 | status_flag | '1' | Status flag |
| 57 | **date_1900** | '1900-01-01' | Placeholder date |
| 60 | business_unit | '21' | Business unit code |

### Date Fields in tbsslipdtj

| Column Position | Likely Meaning | Evidence |
|----------------|----------------|----------|
| Field 4 | Invoice date | Matches header field 3 |
| Field 46 | **Delivery date** - when goods are expected/received | '2024-08-27' - appears to be the planned or actual delivery date |
| Field 57 | Placeholder (1900-01-01) | Default empty value |

## Relationships

### Foreign Key Structure

```
tbscust (Suppliers)
    │
    └── tbsslipj (Purchase Invoice Header)
            │
            └── tbsslipdtj (Purchase Invoice Details)
                    │
                    └── tbsstock (Products)
                            │
                            └── tbsstkhouse (Inventory)
```

### Specific Links

| From | To | Link Fields |
|------|----|-------------|
| tbsslipj | tbscust | tbsslipj.field7 (supplier_code) → tbscust.field1 |
| tbsslipdtj | tbsslipj | tbsslipdtj.field2 (doc_number) → tbsslipj.field2 |
| tbsslipdtj | tbsstock | tbsslipdtj.field6 (product_code) → tbsstock.field1 |
| tbsstkhouse | tbsstock | tbsstkhouse.field1 (product_code) → tbsstock.field1 |

### Validation Stats (from FK_VALIDATION.md)

| Relationship | Match % | Status |
|--------------|---------|--------|
| tbsslipj → tbscust (supplier) | 98.04% | OK (51 non-matches) |
| tbsslipdtj → tbsslipj (doc_number) | 100.00% | OK |
| tbsslipdtj → tbsstock (product) | 96.56% | OK (219 orphans) |

## Warehouse/Location Information

### In tbsslipj
- **Field 10**: dept_code ('0001') - business unit/department
- **Field 41**: business_unit ('21') - another business unit identifier

### In tbsslipdtj
- **Field 17**: warehouse_name ('總倉' = "Main warehouse") - textual warehouse name
- **No warehouse code field** - only the name is present, no code that maps to a warehouse table

**Note**: Unlike tbsslipdtx (sales invoice details) which has a numeric warehouse_code in field 6, tbsslipdtj only has warehouse_name. This may limit ability to track which warehouse received goods.

## Can We Reconstruct When Deliveries Arrived?

### Assessment: PARTIALLY

**What we have:**
1. **tbsslipdtj.field46 (delivery_date)** - appears to be the expected or actual delivery date
2. **tbsslipdtj.field34 (qty_delivered)** - quantity actually delivered
3. **tbsslipdtj.field35 (qty_balance)** - balance remaining

**What we DON'T have:**
1. No explicit "received date" column in either table
2. No receiving confirmation timestamp
3. No warehouse receipt transaction log
4. No inventory movement records showing stock actually arrived

**Gap**: The purchase invoice tables record WHAT was ordered and WHEN it was supposed to be delivered, but not the actual receiving event confirmation. The receiving_date in the migrated schema (delivery_date in purchase_order_lines) may reflect the planned date rather than the actual receiving date.

**Recommendation**: To accurately track when goods actually arrived, you would need to cross-reference with:
- **tbainvorail** - possibly contains receiving transactions
- **tbastktokj** - possibly contains stock movement records
- Any receiving inspection records

## Summary of Key Column Names for Dates

### tbsslipj
| Purpose | Original Field | Migrated Column |
|---------|---------------|-----------------|
| Invoice date | Field 3 (invoice_date) | order_date |
| Unknown #1 | Field 51 | (unmapped) |
| Unknown #2 | Field 62 | (unmapped) |

### tbsslipdtj
| Purpose | Original Field | Migrated Column |
|---------|---------------|-----------------|
| Invoice date | Field 4 (invoice_date) | (carried to header) |
| **Delivery date** | **Field 46 (delivery_date)** | **delivery_date** |

## Comparison with Sales Invoice (tbsslipx/tbsslipdtx)

For reference, the sales invoice tables have:

| Feature | Purchase (tbsslipj/dtJ) | Sales (tbsslipx/dtx) |
|---------|------------------------|----------------------|
| Warehouse code | Text name only (field 17) | Numeric code (field 6) |
| Invoice date | Field 3 | Field 3 |
| Delivery date | Field 46 | Not present |
| Receiving confirmation | Not explicit | Not explicit |

Both tables lack explicit "goods received" confirmation dates.

## How tbsstkhouse Gets Updated from Purchase Invoices

### Assessment: No Automatic Mechanism in Legacy Data

The SQL dump (cao50001.sql) contains **NO triggers, stored procedures, or application logic** that link purchase invoices to inventory updates. The dump is purely data - table definitions and rows.

### What tbsstkhouse Actually Is

`tbsstkhouse` is a **current-state snapshot** of inventory, not a transaction journal:

| Column | Meaning |
|--------|---------|
| col_1 | product_code (FK to tbsstock) |
| col_2 | status ('A' = active) |
| col_4 | qty_in (cumulative received) |
| col_5 | qty_out (cumulative shipped) |
| col_7 | qty_on_hand (current stock) |
| col_8-10 | reserved, available, committed |

It has **no date columns, no transaction references** - just the running balance.

### How Stock Was Updated in the Legacy System

**Unknown.** Possible approaches:
1. **Automatic on invoice save** - the legacy app may have updated stock when tbsslipj was saved
2. **Manual separate step** - operators may have used a receiving screen to confirm delivery
3. **Batch process** - periodic sync from invoices to stock

Without the original application source code, we cannot determine which.

### How UltrERP Updates Stock (Current System)

In `backend/domains/inventory/services.py`, the `receive_supplier_order()` function handles stock updates:

```python
async def receive_supplier_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
    *,
    received_quantities: dict[str, int] | None = None,
    received_date: date | None = None,
    actor_id: str,
) -> dict | None:
```

**Process:**
1. Lock order and inventory rows
2. Update `inventory_stock.quantity` for each line
3. Create `StockAdjustment` with `ReasonCode.SUPPLIER_DELIVERY`
4. Emit `StockChangedEvent`
5. Update order status to `RECEIVED` or `PARTIALLY_RECEIVED`

**Key point:** This is a **MANUAL** separate step. Creating a supplier order does NOT automatically update stock. Someone must explicitly "receive" the order.

### Legacy Migration Approach

The migration imports `tbsstkhouse` as a **one-time snapshot**:

```python
# From canonical.py
INSERT INTO inventory_stock (
    id, tenant_id, product_id, warehouse_id,
    quantity, reorder_point, updated_at
)
VALUES ($1, $2, $3, $4, $5, $6, NOW())
ON CONFLICT (id) DO UPDATE SET
    quantity = EXCLUDED.quantity,
    reorder_point = EXCLUDED.reorder_point,
    updated_at = NOW()
```

The migration does NOT replay purchase invoices as inventory movements. This means:
- Historical receiving events are NOT preserved
- Only the final stock state is migrated
- The `delivery_date` (tbsslipdtj field 46) is not used for inventory updates

### Conclusion

| Question | Answer |
|----------|--------|
| Were stock updates automatic in legacy? | Unknown - no triggers in data dump |
| Was there a manual receiving step? | Likely, but unconfirmed |
| Does current UltrERP auto-update stock? | **No** - manual via `receive_supplier_order()` |
| Can we reconstruct receiving history? | **No** - tbsstkhouse is a snapshot, not a journal |
| Can we use delivery_date for receiving? | Delivery date is recorded but not used to update stock |

## Recommendations for Migration

1. **Map field 46 (delivery_date) as delivery_date** in purchase_order_lines - this is the best indicator of expected/actual delivery

2. **Investigate tbainvorail and tbastktokj** to see if they contain actual receiving events that can be linked to purchase invoices

3. **Consider adding receiving_date column** if actual receiving events are tracked elsewhere

4. **Warehouse mapping is incomplete** - tbsslipdtj only has warehouse name ('總倉'), not a code. The main warehouse 'A' is the default in migrated schema.

5. **Stock history is not preserved** - tbsstkhouse is a snapshot. The migration imports current stock state but not the transaction history that led to it.
