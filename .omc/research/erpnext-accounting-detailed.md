# ERPnext Accounting and Finance Module - Detailed Analysis

## Table of Contents
1. [Core Architecture](#core-architecture)
2. [Chart of Accounts (Account Doctype)](#chart-of-accounts-account-doctype)
3. [GL Entry](#gl-entry)
4. [Sales Invoice](#sales-invoice)
5. [Purchase Invoice](#purchase-invoice)
6. [Journal Entry](#journal-entry)
7. [Payment Entry](#payment-entry)
8. [Payment Terms and Schedule](#payment-terms-and-schedule)
9. [Fiscal Year](#fiscal-year)
10. [Cost Center](#cost-center)
11. [Budget](#budget)
12. [Finance Book](#finance-book)
13. [Exchange Rate Revaluation](#exchange-rate-revaluation)
14. [Payment Gateway](#payment-gateway)
15. [POS Invoice](#pos-invoice)
16. [Dunning (Collection Letters)](#dunning-collection-letters)
17. [Loyalty Program](#loyalty-program)
18. [Tax Categories and Templates](#tax-categories-and-templates)
19. [Accounting Dimension](#accounting-dimension)
20. [Company Settings](#company-settings)
21. [GL Entry Creation Flow](#gl-entry-creation-flow)
22. [Payment Reconciliation](#payment-reconciliation)
23. [Credit Limit Mechanism](#credit-limit-mechanism)
24. [Accounts Controller Logic](#accounts-controller-logic)

---

## Core Architecture

### Key Files
- **accounts_controller.py** (149,191 bytes) - Central controller for all accounting transactions
- **general_ledger.py** (19,320 bytes) - GL entry creation and processing
- **party.py** (33,623 bytes) - Party (Customer/Supplier) handling
- **taxes_and_totals.py** - Tax calculation logic
- **status_updater.py** - Document status management

### Transaction Flow
```
Sales/Purchase Invoice → AccountsController.validate()
                       → calculate_taxes_and_totals()
                       → on_submit() → make_gl_entries()
                       → PaymentLedgerEntry creation
```

### Sales Transaction Types
```python
SALES_TRANSACTION_TYPES = {
    "Quotation",
    "Sales Order",
    "Delivery Note",
    "Sales Invoice",
    "POS Invoice",
}
```

### Purchase Transaction Types
```python
PURCHASE_TRANSACTION_TYPES = {
    "Supplier Quotation",
    "Purchase Order",
    "Purchase Receipt",
    "Purchase Invoice",
}
```

---

## Chart of Accounts (Account Doctype)

**Location:** `erpnext/setup/doctype/account/`

### Fields
| Field | Type | Description |
|-------|------|-------------|
| account_name | Data | Name of the account |
| account_number | Data | Account code (for filtering) |
| is_group | Check | Whether this is a parent/group account |
| company | Link | Company this account belongs to |
| root_type | Select | Asset/Liability/Income/Expense/Equity |
| report_type | Select | Balance Sheet/Profit and Loss |
| account_currency | Link | Currency for the account |
| parent_account | Link | Parent in hierarchy |
| account_type | Select | Detailed type (Payable, Receivable, Bank, Cash, etc.) |
| tax_rate | Float | Tax rate applied |
| freeze_account | Select | No/Yes - restricts entries if frozen |
| balance_must_be | Select | Debit/Credit - balance constraint |
| include_in_gross | Check | Include in gross calculations |
| disabled | Check | Disable the account |

### Account Types
- Accumulated Depreciation
- Asset Received But Not Billed
- Bank
- Cash
- Chargeable
- Cost of Goods Sold
- Current Asset
- Current Liability
- Depreciation
- Direct Expense
- Direct Income
- Equity
- Expense Account
- Fixed Asset
- Income Account
- Payable
- Receivable
- Round Off
- Stock
- Stock Adjustment
- Tax
- Temporary

### Tree Structure
- Default view: Tree (hierarchical)
- Uses `lft` and `rgt` for nested set model

---

## GL Entry

**Location:** `erpnext/accounts/doctype/gl_entry/`

### Fields
| Field | Type | Description |
|-------|------|-------------|
| posting_date | Date | Date of the entry |
| transaction_date | Date | Transaction date |
| fiscal_year | Link | Fiscal year |
| account | Link | Account (required) |
| account_currency | Link | Currency |
| party_type | Link | Customer/Supplier/Employee |
| party | DynamicLink | Party name |
| against | Text | Against account(s) |
| against_voucher_type | Link | Reference doctype |
| against_voucher | DynamicLink | Reference document |
| debit | Currency | Debit amount |
| credit | Currency | Credit amount |
| debit_in_account_currency | Currency | Debit in account currency |
| credit_in_account_currency | Currency | Credit in account currency |
| cost_center | Link | Cost center |
| project | Link | Project |
| finance_book | Link | Finance book |
| company | Link | Company |
| is_opening | Check | Opening entry |
| is_advance | Check | Advance payment |
| is_cancelled | Check | Cancelled |
| remarks | Text | Comments |

### Key Properties
- **is_submittable:** Yes (can submit/reverse)
- **autoname:** ACC-GLE-.YYYY.-.#####

---

## Sales Invoice

**Location:** `erpnext/accounts/doctype/sales_invoice/`

### Fields (Key)
| Field | Type | Description |
|-------|------|-------------|
| naming_series | Select | ACC-SINV-.YYYY.- / ACC-SINV-RET-.YYYY.- |
| customer | Link | Customer (required) |
| posting_date | Date | Invoice date |
| due_date | Date | Payment due date |
| is_pos | Check | POS (cash sale) |
| pos_profile | Link | POS Profile |
| is_return | Check | Is Credit Note |
| return_against | Link | Original invoice for returns |
| is_debit_note | Check | Is Debit Note |
| debit_to | Link | Receivable account |
| update_stock | Check | Update stock |
| update_billed_amount_in_sales_order | Check | Update SO billed amt |
| currency | Link | Transaction currency |
| conversion_rate | Float | Exchange rate |
| selling_price_list | Link | Price list |
| taxes_and_charges | Link | Tax template |
| taxes | Table | Tax rows |
| grand_total | Currency | Total after tax |
| outstanding_amount | Currency | Amount due |
| payment_terms_template | Link | Payment terms |
| payment_schedule | Table | Installment schedule |
| cash_bank_account | Link | For POS payments |
| paid_amount | Currency | Amount received |
| write_off_amount | Currency | Amount written off |
| redeem_loyalty_points | Check | Redeem loyalty |
| loyalty_points | Int | Points to redeem |
| cost_center | Link | Cost center |
| project | Link | Project |

### Child Tables
- **items** (Sales Invoice Item): item_code, qty, rate, amount, income_account, cost_center
- **sales_taxes_and_charges**: Tax template rows
- **sales_invoice_advance**: Advance allocations
- **payment_schedule**: Due date installments
- **sales_team**: Sales persons with commission

### Status Transitions (from status_updater.py)
```
Draft → (submit) → Submitted
      → Cancelled (cancel)
      
For submitted:
  → Status calculated based on:
    - per_billed (billing %)
    - per_delivered (delivery %)
    - outstanding_amount
```

### Key Controller Methods (sales_invoice.py)
```python
class SalesInvoice(SellingController):
    def validate(self):
        # Party validation
        # Price list/currency
        # Tax calculation
        # Payment schedule
        # Credit limit check
        
    def on_submit(self):
        # Create GL entries
        # Update outstanding
        # Create stock ledger
        # Allocate advances
        # Create payment ledger entries
        
    def on_cancel(self):
        # Reverse GL entries
        # Update outstanding
        # Unlink advances
        # Cancel stock ledger
```

---

## Purchase Invoice

**Location:** `erpnext/accounts/doctype/purchase_invoice/`

### Fields (Key)
| Field | Type | Description |
|-------|------|-------------|
| naming_series | Select | ACC-PINV-.YYYY.- / ACC-PINV-RET-.YYYY.- |
| supplier | Link | Supplier (required) |
| posting_date | Date | Invoice date |
| due_date | Date | Payment due date |
| bill_no | Data | Supplier's invoice number |
| bill_date | Date | Supplier's invoice date |
| is_paid | Check | Is paid immediately |
| is_return | Check | Is Debit Note |
| credit_to | Link | Payable account |
| update_stock | Check | Update stock |
| taxes_and_charges | Link | Tax template |
| taxes | Table | Tax rows |
| grand_total | Currency | Total after tax |
| outstanding_amount | Currency | Amount due |
| mode_of_payment | Link | Payment mode |
| cash_bank_account | Link | Payment account |
| paid_amount | Currency | Amount paid |
| on_hold | Check | Invoice on hold |
| release_date | Date | Hold release date |

### Child Tables
- **items** (Purchase Invoice Item)
- **purchase_taxes_and_charges**
- **purchase_invoice_advance**
- **payment_schedule**
- **supplied_items** (for subcontracting)

### Status Transitions
```
Draft → Submitted → Cancelled
      → On Hold (manual)
```

---

## Journal Entry

**Location:** `erpnext/accounts/doctype/journal_entry/`

### Fields (Key)
| Field | Type | Description |
|-------|------|-------------|
| naming_series | Select | ACC-JV-.YYYY.- |
| voucher_type | Select | Entry type |
| posting_date | Date | Entry date |
| company | Link | Company |
| multi_currency | Check | Multi-currency support |
| finance_book | Link | Finance book |
| accounts | Table | Accounting entries (Journal Entry Account) |
| total_debit | Currency | Sum of debits |
| total_credit | Currency | Sum of credits |
| difference | Currency | Dr - Cr (should be 0) |
| cheque_no | Data | Reference number |
| cheque_date | Date | Reference date |
| clearance_date | Date | Bank clearance date |
| user_remark | SmallText | Comments |
| is_opening | Check | Opening entry |

### Voucher Types
- Journal Entry
- Inter Company Journal Entry
- Bank Entry
- Cash Entry
- Credit Card Entry
- Debit Note
- Credit Note
- Contra Entry
- Excise Entry
- Write Off Entry
- Opening Entry
- Depreciation Entry
- Asset Disposal
- Periodic Accounting Entry
- Exchange Rate Revaluation
- Exchange Gain Or Loss
- Deferred Revenue
- Deferred Expense

### Child Tables
- **journal_entry_account**: account, party_type, party, debit, credit, reference_type, reference_name, cost_center, project

### Key Validation
- Total debit must equal total credit (difference = 0)
- Each account entry must balance

---

## Payment Entry

**Location:** `erpnext/accounts/doctype/payment_entry/`

### Fields (Key)
| Field | Type | Description |
|-------|------|-------------|
| naming_series | Select | ACC-PAY-.YYYY.- |
| payment_type | Select | Receive/Pay/Internal Transfer |
| posting_date | Date | Payment date |
| company | Link | Company |
| party_type | Link | Customer/Supplier/Employee |
| party | DynamicLink | Party name |
| paid_from | Link | Source account |
| paid_to | Link | Target account |
| paid_amount | Currency | Payment amount |
| received_amount | Currency | Amount received |
| source_exchange_rate | Float | Exchange rate |
| base_paid_amount | Currency | In company currency |
| references | Table | Payment Entry Reference |
| total_allocated_amount | Currency | Allocated to invoices |
| unallocated_amount | Currency | Remaining unallocated |
| difference_amount | Currency | Rounding difference |
| mode_of_payment | Link | Cash/Bank/Credit Card |
| clearence_date | Date | Bank clearance |

### Child Tables
- **payment_entry_reference**: reference_doctype, reference_name, due_date, payment_term, allocated_amount
- **deductions**: account, cost_center, amount

### Status
- Draft
- Submitted
- Cancelled

### Payment Type Specifics
**Receive (from Customer):**
- paid_from = Bank/Cash account
- paid_to = Receivable account (debit_to)

**Pay (to Supplier):**
- paid_from = Payable account (credit_to)
- paid_to = Bank/Cash account

### Key Controller Methods
```python
class PaymentEntry(AccountsController):
    def validate(self):
        self.validate_payment_type()
        self.validate_party_details()
        self.validate_reference_documents()
        self.validate_allocated_amount()
        
    def on_submit(self):
        # Create GL entries
        # Update outstanding amounts
        # Create payment ledger entries
        
    def on_cancel(self):
        # Reverse GL entries
        # Unlink allocations
```

---

## Payment Terms and Schedule

### Payment Terms Template

**Location:** `erpnext/accounts/doctype/payment_terms_template/`

| Field | Type |
|-------|------|
| template_name | Data (unique) |
| allocate_payment_based_on_payment_terms | Check |
| terms | Table (Payment Terms Template Detail) |

### Payment Schedule (Child Table)

**Location:** `erpnext/accounts/doctype/payment_schedule/`

| Field | Type | Description |
|-------|------|-------------|
| payment_term | Link | Payment Term |
| description | SmallText | From template |
| due_date | Date | Due date |
| invoice_portion | Percent | % of invoice |
| payment_amount | Currency | Amount due |
| outstanding | Currency | Remaining |
| paid_amount | Currency | Amount paid |
| discounted_amount | Currency | Early payment discount |
| discount_date | Date | Discount valid until |
| discount | Float | Discount % or amount |
| credit_days | Int | Days credit |
| credit_months | Int | Months credit |
| mode_of_payment | Link | Payment mode |

### Payment Term (Master)

| Field | Type |
|-------|------|
| term_name | Data |
| description | Text |
| due_date_based_on | Select |
| credit_days | Int |
| credit_months | Int |
| discount_validity | Int |
| discount | Float |

---

## Fiscal Year

**Location:** `erpnext/accounts/doctype/fiscal_year/`

### Fields
| Field | Type | Description |
|-------|------|-------------|
| year | Data | Year name (e.g., "2024", "2024-25") |
| year_start_date | Date | FY start |
| year_end_date | Date | FY end |
| disabled | Check | Disable FY |
| is_short_year | Check | Less/more than 12 months |
| companies | Table | Companies using this FY |
| auto_created | Check | Auto-created |

### Permissions
- System Manager: Full
- Accounts Manager: Read
- All Users: Read

---

## Cost Center

**Location:** `erpnext/accounts/doctype/cost_center/`

### Fields
| Field | Type | Description |
|-------|------|-------------|
| cost_center_name | Data | Name |
| cost_center_number | Data | Code |
| parent_cost_center | Link | Parent in tree |
| company | Link | Company |
| is_group | Check | Is group |
| disabled | Check | Disabled |

### Properties
- Tree structure (default view)
- nsm_parent_field: parent_cost_center
- Used for expense tracking and allocation

### Budget Allocation
Cost centers can have allocation percentages to distribute expenses across multiple centers.

---

## Budget

**Location:** `erpnext/accounts/doctype/budget/`

### Fields
| Field | Type | Description |
|-------|------|-------------|
| budget_against | Select | Cost Center/Project |
| company | Link | Company |
| cost_center | Link | Cost center (if budget_against=Cost Center) |
| project | Link | Project (if budget_against=Project) |
| from_fiscal_year | Link | Start FY |
| to_fiscal_year | Link | End FY |
| budget_amount | Currency | Total budget |
| budget_distribution | Table | Monthly distribution |
| applicable_on_material_request | Check | Check on MR |
| applicable_on_purchase_order | Check | Check on PO |
| applicable_on_booking_actual_expenses | Check | Check on actual GL |

### Actions When Budget Exceeded
- **Stop:** Prevent the transaction
- **Warn:** Show alert but allow
- **Ignore:** No action

### Monthly Distribution
Distribution via Monthly Distribution table (percentage per month).

---

## Finance Book

**Location:** `erpnext/accounts/doctype/finance_book/`

### Fields
| Field | Type |
|-------|------|
| finance_book_name | Data (unique) |

### Purpose
Allows separate accounting books within same company for different entities/divisions.

### Permissions
- Accounts User: Read
- Accounts Manager: Full
- Auditor: Read

---

## Exchange Rate Revaluation

**Location:** `erpnext/accounts/doctype/exchange_rate_revaluation/`

### Purpose
Revalue foreign currency accounts when exchange rates change.

### Fields
| Field | Type | Description |
|-------|------|-------------|
| posting_date | Date | Revaluation date |
| company | Link | Company |
| gain_loss_unbooked | Currency | Unbooked gain/loss |
| gain_loss_booked | Currency | Already booked |
| total_gain_loss | Currency | Total |
| rounding_loss_allowance | Float | Tolerance for zero |
| accounts | Table | Accounts to revalue |

### Process
1. Click "Get Entries" to fetch accounts with balance in foreign currency
2. Calculate gain/loss based on new exchange rate
3. Submit to create GL entries for revaluation

---

## Payment Gateway

**Location:** `erpnext/accounts/doctype/payment_gateway_account/`

### Fields
| Field | Type | Description |
|-------|------|-------------|
| payment_gateway | Link | Gateway name |
| payment_channel | Select | Email/Phone/Other |
| company | Link | Company |
| is_default | Check | Default gateway |
| payment_account | Link | Bank account |
| currency | ReadOnly | Account currency |
| message | SmallText | Request message |

### Common Gateways
- Stripe
- PayPal
- Braintree
-razorpay
- Instamojo

---

## POS Invoice

**Location:** `erpnext/accounts/doctype/pos_invoice/`

### Overview
Point-of-Sale transaction (cash sale) with immediate payment.

### Key Differences from Sales Invoice
| Field | POS Invoice | Sales Invoice |
|-------|------------|---------------|
| is_pos | Always set | Optional |
| payments | Required table | Optional |
| change_amount | Calculated | N/A |
| cash_bank_account | Required | Optional |
| consolidated_invoice | For batch posting | N/A |
| pos_profile | Required | N/A |

### Fields (Key)
- Same base fields as Sales Invoice
- pos_profile: Links to POS Profile with settings
- consolidated_invoice: Groups multiple POS into one SI
- payments: Table of payment methods
- change_amount: Cash back to customer

### Child Tables
- **items** (POS Invoice Item)
- **payments**: mode_of_payment, amount, card_number, account
- **taxes**
- **advances**
- **payment_schedule**

### POS Profile Settings
- Company
- Warehouse
- POS Opening Entry
- Print settings
- Apply tax
- Allow sales return
- Payment methods

---

## Dunning (Collection Letters)

**Location:** `erpnext/accounts/doctype/dunning/`

### Purpose
Automated collection process for overdue invoices.

### Fields
| Field | Type | Description |
|-------|------|-------------|
| naming_series | Select | DUNN-.MM.-.YY.- |
| customer | Link | Customer |
| company | Link | Company |
| posting_date | Date | Date |
| dunning_type | Link | Dunning Type |
| rate_of_interest | Float | Monthly interest rate |
| total_interest | Currency | Calculated interest |
| dunning_fee | Currency | Collection fee |
| dunning_amount | Currency | Total dues |
| total_outstanding | Currency | Outstanding before dunning |
| grand_total | Currency | Invoice total |
| language | Link | Print language |
| body_text | HTML | Letter text |
| closing_text | HTML | Closing text |
| income_account | Link | Fee income account |
| cost_center | Link | Cost center |

### Dunning Type
| Field | Type |
|-------|------|
| dunning_fee | Currency |
| rate_of_interest | Float |
| dunning_letter_text | Table |

### Process
1. Create Dunning based on overdue invoices
2. Calculate interest and fees
3. Send collection letter
4. Track collection status

---

## Loyalty Program

**Location:** `erpnext/accounts/doctype/loyalty_program/`

### Fields
| Field | Type | Description |
|-------|------|-------------|
| loyalty_program_name | Data | Program name |
| loyalty_program_type | Select | Single/Multiple Tier |
| from_date | Date | Start date |
| to_date | Date | End date |
| customer_group | Link | Applicable group |
| customer_territory | Link | Applicable territory |
| auto_opt_in | Check | Auto enroll all |
| collection_rules | Table | Points earning rules |
| conversion_factor | Float | 1 point = X currency |
| expiry_duration | Int | Days until expiry |
| expense_account | Link | Points expense |
| cost_center | Link | Cost center |

### Collection Rules (Loyalty Program Collection)
| Field | Type | Description |
|-------|------|-------------|
| tier | Data | Tier name |
| min_spent | Currency | Minimum spend |
| collected_points | Int | Points earned |

### Redemption in Sales Invoice
- redeem_loyalty_points: Check
- loyalty_points: Int
- loyalty_amount: Currency
- loyalty_redemption_account: Link
- loyalty_redemption_cost_center: Link

### Loyalty Point Entry
| Field | Type |
|-------|------|
| loyalty_program | Link |
| customer | Link |
| loyalty_points | Int |
| type | Earned/Redeemed/Cancelled |
| expiry_date | Date |

---

## Tax Categories and Templates

### Tax Category

**Location:** `erpnext/accounts/doctype/tax_category/`

| Field | Type |
|-------|------|
| title | Data (unique) |
| disabled | Check |

### Tax Rule

**Location:** `erpnext/accounts/doctype/tax_rule/`

| Field | Type | Description |
|-------|------|-------------|
| tax_type | Select | Sales/Purchase |
| tax_category | Link | Category |
| party_type | Link | Customer/Supplier type |
| party | Link | Specific party |
| billing_city | Data | City match |
| shipping_city | Data | Shipping city |
| billing_state | Data | State match |
| tax_template | Link | Tax template |

### Sales/Purchase Taxes and Charges Template

| Field | Type | Description |
|-------|------|-------------|
| title | Data | Template name |
| company | Link | Company |
| taxes | Table | Tax rows |

### Tax Row Fields
| Field | Type | Description |
|-------|------|-------------|
| account_head | Link | Tax account |
| cost_center | Link | Tax cost center |
| charge_type | Select | On Net Total/On Item Quantity/Actual |
| row_id | Link | Parent tax row |
| rate | Float | Tax rate % |
| amount | Currency | Fixed amount |
| included_in_print_rate | Check | Tax inclusive in price |
| expense_account | Link | Tax expense account |
| description | Data | Tax description |

### Item Tax Template

| Field | Type |
|-------|------|
| title | Data |
| taxes | Table (Item Tax Template Detail) |

---

## Accounting Dimension

**Location:** `erpnext/accounts/doctype/accounting_dimension/`

### Purpose
Flexible dimensions for reporting (beyond Cost Center and Project).

### Fields
| Field | Type | Description |
|-------|------|-------------|
| label | Data | Dimension name |
| fieldname | Data | Fieldname for filtering |
| document_type | Link | Applicable doctype |
| disabled | Check | Disabled |

### Dimension Detail (Table)
| Field | Type |
|-------|------|
| company | Link |
| offsetting_account | Link |
| automatically_post_balancing_entry | Check |

### Common Dimensions
- Department
- Division
- Employee
- Location
- Project (built-in)

---

## Company Settings

**Location:** `erpnext/setup/doctype/company/`

### Accounting-Related Fields

#### Default Accounts
- default_bank_account
- default_cash_account
- default_receivable_account
- default_payable_account
- write_off_account
- unrealized_profit_loss_account
- default_expense_account
- default_income_account
- default_discount_account
- round_off_account
- round_off_cost_center

#### Deferred Accounting
- default_deferred_revenue_account
- default_deferred_expense_account

#### Advance Payments
- book_advance_payments_in_separate_party_account
- default_advance_received_account
- default_advance_paid_account

#### Exchange Rate Revaluation
- auto_exchange_rate_revaluation
- auto_err_frequency
- exchange_gain_loss_account
- unrealized_exchange_gain_loss_account

#### Budget Settings
- exception_budget_approver_role
- default finance_book

#### Fixed Asset Defaults
- accumulated_depreciation_account
- depreciation_expense_account
- disposal_account
- depreciation_cost_center
- capital_work_in_progress_account
- asset_received_but_not_billed

---

## GL Entry Creation Flow

### From Sales Invoice (on_submit)

```python
# In SalesInvoice.on_submit():
def on_submit(self):
    # 1. Update outstanding amount
    update_voucher_outstanding(self.debit_to, "Customer", self.customer, ...)
    
    # 2. Make GL Entries
    gl_map = []
    for item in self.items:
        # Income entry
        gl_map.append(frappe._dict({
            "account": item.income_account,
            "party_type": "Customer",
            "party": self.customer,
            "debit": 0,
            "credit": item.amount,
            "cost_center": item.cost_center,
            "project": self.project
        }))
    
    # Receivable entry
    gl_map.append(frappe._dict({
        "account": self.debit_to,
        "party_type": "Customer",
        "party": self.customer,
        "debit": self.grand_total,
        "credit": 0
    }))
    
    # Tax entries
    for tax in self.taxes:
        gl_map.append(frappe._dict({
            "account": tax.account_head,
            "debit": tax.tax_amount,
            "credit": 0
        }))
    
    make_gl_entries(gl_map)
```

### From Payment Entry (on_submit)

```python
# For Receive payment:
# Debit: Bank/Cash account
# Credit: Receivable account (debit_to)

# For Pay payment:
# Debit: Payable account (credit_to)
# Credit: Bank/Cash account
```

### General Ledger Processing

```python
# In general_ledger.py:
def make_gl_entries(gl_map, cancel=False, adv_adj=False):
    if not cancel:
        # Validate accounts not disabled
        validate_disabled_accounts(gl_map)
        
        # Validate accounting period not closed
        validate_accounting_period(gl_map)
        
        # Budget validation
        BudgetValidation(gl_map).validate()
        
        # Merge similar entries
        gl_map = process_gl_map(gl_map)
        
        # Create Payment Ledger Entry
        create_payment_ledger_entry(gl_map, ...)
        
        # Save GL entries
        save_entries(gl_map, ...)
    else:
        make_reverse_gl_entries(gl_map, ...)
```

---

## Payment Reconciliation

### Process Flow

1. **Get Outstanding Invoices**
   ```python
   get_outstanding_invoices(party_type, party, account, payment_type)
   ```

2. **Allocate Payment**
   ```python
   # Creates payment_entry_reference for each invoice
   # Updates outstanding_amount on invoices
   ```

3. **Unreconcile**
   ```python
   # Reverses allocations
   # Restores original outstanding amounts
   ```

### Payment Entry Reference Fields
| Field | Type | Description |
|-------|------|-------------|
| reference_doctype | Link | SI/PO/JE/PE |
| reference_name | DynamicLink | Document name |
| due_date | Date | Invoice due date |
| payment_term | Link | Payment term |
| allocated_amount | Currency | Amount allocated |

### Unreconcile Payment

**Location:** `erpnext/accounts/doctype/unreconcile_payment/`

Allows reversing payment allocations.

---

## Credit Limit Mechanism

### Implementation
```python
# In AccountsController or SalesInvoice:
def validate_credit_limit(self):
    customer = frappe.get_doc("Customer", self.customer)
    
    if customer.credit_limit:
        outstanding = getOutstandingAmount(customer.name)
        
        if outstanding + self.outstanding_amount > customer.credit_limit:
            frappe.throw(_("Credit limit exceeded"))
```

### Customer Fields
- credit_limit: Currency
- credit_days_based_on: Select (Linked Invoice Date/Due Date)
- payment_terms: Link

### Territory-Based Limits
Credit limits can be managed per territory or customer group.

---

## Accounts Controller Logic

**Location:** `erpnext/controllers/accounts_controller.py` (149KB)

### Key Methods

#### validate()
```python
def validate(self):
    # Date with fiscal year
    self.validate_date_with_fiscal_year()
    
    # Party accounts
    self.validate_party_accounts()
    
    # Currency
    self.validate_currency()
    
    # Taxes and totals
    self.calculate_taxes_and_totals()
    
    # Payment schedule
    self.validate_invoice_documents_schedule()
    
    # Due date
    self.validate_due_date()
    
    # Advance allocations
    self.set_advances()
    
    # Pricing rules
    apply_pricing_rule_on_transaction(self)
```

#### on_submit()
```python
def on_submit(self):
    # Make GL entries
    make_gl_entries(self.get_gl_map())
    
    # Update outstanding
    update_voucher_outstanding(...)
    
    # Allocate advances
    self.allocate_advances(...)
```

#### on_cancel()
```python
def on_cancel(self):
    # Reverse GL entries
    make_reverse_gl_entries(self.get_gl_map())
    
    # Update outstanding
    update_voucher_outstanding(..., cancel=True)
    
    # Unlink advances
    self.unlink_advances(...)
```

### Helper Classes

#### StatusUpdater
Manages document status based on percentages.

```python
# status_map shows all status transitions
status_map = {
    "Sales Order": [
        ["Draft", None],
        ["To Deliver and Bill", "eval:self.per_delivered < 100 and self.per_billed < 100"],
        ["To Bill", "eval:(per_delivered >= 100 or skip_delivery_note) and per_billed < 100"],
        ["Completed", "eval:per_delivered >= 100 and per_billed >= 100"],
        ["Cancelled", "eval:self.docstatus==2"],
        ["Closed", "eval:self.status=='Closed'"],
    ],
    # ... more doctypes
}
```

### Taxes and Totals Calculation

```python
# In taxes_and_totals.py:
class calculate_taxes_and_totals:
    def calculate(self):
        self.validate_conversion_rate()
        self.calculate_item_values()
        self.initialize_taxes()
        self.determine_exclusive_rate()
        self.calculate_net_total()
        self.calculate_taxes()
        self.adjust_grand_total_for_inclusive_tax()
        self.calculate_totals()
```

### Deferred Revenue/Expense

```python
def validate_deferred_income_expense_account(self):
    for item in self.items:
        if item.get("enable_deferred_revenue"):
            if not item.get("deferred_revenue_account"):
                # Get from company defaults
                pass
```

### Inter-Company Transactions

```python
def validate_inter_company_reference(self):
    if self.is_internal_transfer():
        if not self.inter_company_reference:
            frappe.throw("Internal Sale or Delivery Reference missing")
```

### Advance Allocation

```python
def set_advances(self):
    if self.allocate_advances_automatically:
        # Fetch unallocated advances
        # Create advance allocations
```

---

## Reports in Accounts Module

### Standard Reports
1. **General Ledger** - All GL entries with filters
2. **Sales Ledger** - Customer-wise Outstanding
3. **Purchase Ledger** - Supplier-wise Outstanding
4. **Bank Reconciliation Statement**
5. **Trial Balance**
6. **Profit and Loss**
7. **Balance Sheet**
8. **Account Receivable Ageing**
9. **Account Payable Ageing**
10. **Cash Flow Statement**
11. **Financial Ratios**

### Dashboard Charts
- Income by Customer Group
- Expenses by Cost Center
- Budget Variance
- Party Ledger Summary

---

## Integration with Other Modules

### Stock
- Stock Ledger Entry created on submit
- Valuation based on valuation method (FIFO/MAV)
- Inventory accounts updated

### Buying/Purchasing
- Purchase Receipt linked
- Subcontracting flow
- Landed Cost Voucher

### Selling/Distribution
- Delivery Note linked
- Sales Order billing
- Territory management

### Projects
- Timesheet billing
- Project cost tracking
- Progress invoicing

### HR
- Salary processing
- Employee advances
- Expense claims

---

## Key Doctypes Summary

| Doctype | Purpose | Key Account |
|---------|---------|-------------|
| Sales Invoice | Revenue recognition | debit_to (Receivable) |
| Purchase Invoice | Expense recognition | credit_to (Payable) |
| Journal Entry | Manual adjustments | Any |
| Payment Entry | Cash flow | Bank/Cash |
| GL Entry | Ledger record | All |
| Payment Schedule | Installments | - |
| Dunning | Collections | - |
| Loyalty Program | Customer retention | - |
| Budget | Expense control | - |
| Cost Center | Expense allocation | - |
| Fiscal Year | Reporting period | - |
| Finance Book | Multi-book | - |

---

## Child Tables Reference

| Parent | Child Table | Purpose |
|--------|------------|---------|
| Sales Invoice | items | Line items |
| Sales Invoice | taxes | Tax rows |
| Sales Invoice | sales_invoice_advance | Advance allocations |
| Sales Invoice | payment_schedule | Installments |
| Sales Invoice | sales_team | Commission |
| Purchase Invoice | items | Line items |
| Purchase Invoice | taxes | Tax rows |
| Purchase Invoice | advances | Advance allocations |
| Journal Entry | accounts | Entry rows |
| Payment Entry | references | Invoice allocations |
| Payment Entry | deductions | Write-off |
| Budget | accounts | Account budgets |
| Loyalty Program | collection_rules | Points earning |
| Payment Terms Template | details | Term rows |
| Account | defaults | Company defaults |

---

## Permissions Model

### Roles with Access
- **System Manager**: Full access to all
- **Accounts Manager**: Full to accounts
- **Accounts User**: Read/Write/Create
- **Auditor**: Read-only
- **Sales User**: Sales invoices
- **Purchase User**: Purchase invoices

### Key Permissions
```python
# GL Entry permissions
{"read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1}

# Most accounting doctypes
{"read": 1, "write": 1, "create": 1, "report": 1, "export": 1}
```

---

*Document generated from ERPnext v14/v15 source analysis*
*Source: /reference/erpnext-develop/erpnext/accounts/ and /reference/erpnext-develop/erpnext/controllers/*