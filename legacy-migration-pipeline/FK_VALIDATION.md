# Foreign Key Validation Report

## Summary

| Relationship | FK Count | Match % | Status |
|--------------|----------|---------|--------|
| tbsslipx.customer_code → tbscust | 662 | 99.85% | OK |
| tbsslipdtx.product_code → tbsstock | 662 | **0.30%** | **CRITICAL** |
| tbsslipdtx.doc_number → tbsslipx | 132,718 | 99.98% | OK |
| tbsslipj.supplier_code → tbscust | 51 | 98.04% | OK |
| tbsslipdtj.doc_number → tbsslipj | 9,245 | 100.00% | OK |
| tbsslipdtj.product_code → tbsstock | 6,364 | 96.56% | OK |
| tbsstkhouse.product_code → tbsstock | 6,588 | 100.00% | OK |
| tbsstock.supplier_code → tbscust | 44 | 97.73% | OK |

## Critical Issue: Product Code Mismatch

**tbsslipdtx uses different product codes than tbsstock**

- tbsslipdtx: Numeric codes like `2206`, `1138`, `1000`
- tbsstock: Alphanumeric codes like `PC240`, `XPB-2410-P`

This means **660 product codes (99.7%)** in sales transaction details **DO NOT exist** in the product master.

### Root Cause
The system appears to have undergone a product code migration/reconciliation, but historical transaction records were not updated to reflect the new codes.

### Impact on Migration
1. Sales detail records cannot be directly linked to product master
2. Historical sales analysis by product will be incomplete
3. Need to either:
   - Create a product code mapping table
   - Find the legacy product code relationship
   - Accept orphan transactions

## Orphan Records

| Table | Orphan Count | Example |
|-------|-------------|---------|
| tbsslipx | 1 | customer_code '3123' |
| tbsslipdtx | 660 | numeric product codes |
| tbsslipj | 1 | supplier_code '1000' |
| tbsslipdtj | 219 | product codes not in tbsstock |

## Recommendation

Before migration, investigate:
1. Whether a legacy product code mapping exists elsewhere in the database
2. If the numeric codes in tbsslipdtx correspond to a different product table
3. Whether to create a reconciliation mapping or treat as data quality issue
