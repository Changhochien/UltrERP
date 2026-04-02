# Legacy ERP Column Analysis

## TBSCUST (Customer/Supplier Master)
**1,022 rows, 100 columns**

| Col | Field | Sample | Notes |
|-----|-------|--------|-------|
| 1 | customer_code | '1149' | Primary key |
| 2 | customer_type | '2' | 1=Supplier, 2=Customer |
| 3 | company_name | '昌弘五金實業有限公司' | Full name |
| 4 | company_name_alt | '昌弘五金實業有限公司' | Short name |
| 7 | zip_code | '300' | Postal code |
| 8 | full_address | '300 新竹市東區...' | Address with zip |
| 13 | address | '新竹市東區寶山路...' | Address |
| 14 | phone | '03-5627542' | Phone |
| 15 | fax | '03-5627543' | Fax |
| 17 | email | | Email |
| 18 | contact_person | '莫''S' | Contact name |
| 20 | tax_id | '12603075' | 統一編號 |
| 21 | create_date | '2025-04-07' | Created |
| 22 | status | '6' | Status code |
| 46 | dept_code | '0001' | Branch code |
| 51 | credit_limit | 1.0 | Credit limit |
| 57 | last_update | '2019-08-14' | Last modified |
| 65 | status_code | 'A' | A=Active |
| 66 | balance | 45070.60 | Current balance |
| 75 | record_status | 'A' | Status |
| 81 | area_code | '2443' | Sales area |
| 90 | taxable_flag | 'N' | Y/N |
| 93 | invoice_flag | 'N' | Y/N |

## TBSSCUST / TBSSTOCK (Product Master)
**6,611 rows, 136 columns**

| Col | Field | Sample | Notes |
|-----|-------|--------|-------|
| 1 | product_code | 'PC240' | Primary key |
| 3 | product_name | '三角皮帶 C-240' | Description |
| 7 | category | '0' | Category |
| 8 | supplier_code | 'T001' | FK to tbscust |
| 9 | origin | '泰國' | Country |
| 16 | unit | '條' | Unit of measure |
| 21 | qty_in_stock | 288.0 | Current stock |
| 22 | amount | 1267.20 | Value |
| 29 | create_date | '2022-06-28' | Created |
| 30 | last_sale_date | '2025-04-22' | Last transaction |
| 31 | avg_cost | 314.26 | Average cost |
| 41 | sale_price_1 | 316.80 | Selling price |
| 42 | sale_price_2 | 850.00 | Alt price |
| 85 | status | 'A' | A=Active |

## TBSSLIPX (Sales Invoice Header)
**133,419 rows, 103 columns**

| Col | Field | Sample | Notes |
|-----|-------|--------|-------|
| 1 | slip_type | '1' | 1=Sales |
| 2 | invoice_number | '1130826001' | ROC date + seq |
| 3 | invoice_date | '2024-08-26' | Date |
| 7 | customer_code | '1143' | FK to tbscust |
| 8 | customer_name | '恆峰' | Denormalized |
| 9 | address | '台北市大同區...' | Delivery addr |
| 10 | currency_code | '0001' | NTD |
| 11 | currency_name | '新臺幣' | |
| 12 | exchange_rate | 1.0 | |
| 17 | subtotal | 10680.00 | Before tax |
| 18 | tax_type | '3' | |
| 19 | tax_amount | 0.00 | |
| 24 | total_amount | 10680.00 | Final total |
| 30 | remark | '8/22出貨' | Note |
| 31 | period_code | '11308' | ROC 2024-08 |
| 32 | created_by | '系統管理員' | |
| 85 | tax_rate | 0.05000000 | 5% VAT |
| 80 | status | 'A' | |

## TBSSLIPDTX (Sales Invoice Detail)
**593,017 rows, 73 columns**

| Col | Field | Sample | Notes |
|-----|-------|--------|-------|
| 2 | doc_number | '11032433' | FK to tbsslipx |
| 3 | line_number | 1 | Line seq |
| 6 | warehouse_code | '1138' | **Numeric!** |
| 7 | product_code | 'P5V-1250 OH' | FK to tbsstock |
| 8 | product_name | '5V-1250 OH' | Denormalized |
| 15 | status | 'A' | |
| 16 | warehouse_name | '總倉' | Main warehouse |
| 18 | unit | '條' | |
| 19 | qty | 175.0 | Quantity |
| 20 | unit_price | 1.0 | Price |
| 21 | extended_amount | 175.0 | Line total |
| 22 | amount_1 | 127.5 | |
| 23 | amount_2 | 18.0 | Tax |
| 24 | tax_flag | 'N' | |
| 32 | inventory_flag | 'Y' | |
| 54 | cost_center | '469' | |

**NOTE:** Product codes in this table use numeric system (1138, 1000, etc.) different from tbsstock (PC240, XPB-2410-P). **CRITICAL MISMATCH**.

## TBSSLIPJ (Purchase Invoice Header)
**9,250 rows, 96 columns**

| Col | Field | Sample | Notes |
|-----|-------|--------|-------|
| 1 | slip_type | '4' | 4=Purchase |
| 2 | invoice_number | '1130827001' | ROC date + seq |
| 3 | invoice_date | '2024-08-27' | Date |
| 7 | supplier_code | 'T067' | FK to tbscust |
| 8 | supplier_name | '勝梨' | Denormalized |
| 9 | address | '桃園市中壢區...' | |
| 17 | subtotal | 1265.00 | Before tax |
| 30 | period_code | '11308' | ROC period |
| 49 | total_amount | 1265.00 | Final total |
| 78 | tax_rate | 0.05000000 | 5% VAT |

## TBSSSLIPDTJ (Purchase Invoice Detail)
**61,728 rows**

| Col | Field | Sample | Notes |
|-----|-------|--------|-------|
| 2 | doc_number | | FK to tbsslipj |
| 3 | line_number | | Line seq |
| 6 | product_code | | FK to tbsstock |
| 19 | qty | | Quantity |
| 20 | unit_price | | Price |
| 21 | extended_amount | | Line total |

## TBSSSTKHOUSE (Inventory)
**6,588 rows, 15 columns**

| Col | Field | Sample | Notes |
|-----|-------|--------|-------|
| 1 | product_code | 'VB048' | FK to tbsstock |
| 2 | status | 'A' | A=Active |
| 4 | qty_in | 8.0 | Received |
| 5 | qty_out | 8.0 | Shipped |
| 6 | qty_adjust | 0.0 | Adjustment |
| 7 | qty_on_hand | 41.0 | Current stock |
| 8 | qty_reserved | 0.0 | Reserved |
| 9 | qty_available | 0.0 | Available |
| 10 | qty_committed | 41.0 | Committed |

## TBASUBJECT (Chart of Accounts)
**232 rows**

| Col | Field | Sample | Notes |
|-----|-------|--------|-------|
| 3 | account_code | '0001' | Primary key |
| 4 | account_name | '應收帳款' | AR |
| 5 | account_type | 'D' | D=Debit |
| 6 | parent_code | | Hierarchy |
| 7 | subclass | | Classification |

## Date Format Note

ROC (民國) dates: Year + 1911 = AD
- `1130826001` = 2024-08-26-001
- `11308` = 2024-08
