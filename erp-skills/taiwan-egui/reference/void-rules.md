# Invoice Void Rules

## Bimonthly Filing Periods
Taiwan tax filings follow a bimonthly cycle:

| Period | Months    |
|--------|-----------|
| 1      | Jan - Feb |
| 2      | Mar - Apr |
| 3      | May - Jun |
| 4      | Jul - Aug |
| 5      | Sep - Oct |
| 6      | Nov - Dec |

## Void Deadline Calculation
An invoice can only be voided before the **15th of the first month of the NEXT filing period**.

### Formula
```
period_end_month   = invoice_month + (invoice_month % 2)
next_period_start  = period_end_month + 1
void_deadline      = date(year, next_period_start, 15)
```

### Year Boundary
When the invoice falls in Nov-Dec (period 6), `next_period_start` would be 13 (January of next year). The function handles this by rolling to January of `year + 1`.

### Examples

| Invoice Date | Period   | Void Deadline |
|-------------|----------|---------------|
| 2025-01-10  | Jan-Feb  | 2025-03-15    |
| 2025-02-28  | Jan-Feb  | 2025-03-15    |
| 2025-03-20  | Mar-Apr  | 2025-05-15    |
| 2025-06-30  | May-Jun  | 2025-07-15    |
| 2025-11-01  | Nov-Dec  | 2026-01-15    |
| 2025-12-31  | Nov-Dec  | 2026-01-15    |

## Business Rules
- Voiding after the deadline requires a manual amendment filing with the tax authority
- The system should warn users when an invoice is approaching its void deadline
- Already-submitted (ACKED) invoices require a void notice to be sent to the eGUI platform

## Codebase Reference
- `backend/domains/invoices/service.py` → `compute_void_deadline(invoice_date: date) -> date`
