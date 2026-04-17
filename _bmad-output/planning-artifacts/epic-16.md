## Epic 16: Extended Legacy Import — Purchase Transactions and Payments

### Epic Goal

Operations and AI agents can stage, normalize, map, import, and validate extended legacy ERP purchase data (purchase invoices, purchase orders, and payment records) into UltrERP through the same repeatable CLI-backed workflow used for Epic 15, adding coverage for the purchase side of the business and completing the financial transaction picture alongside the already-imported sales data.

### Stories

### Story 16.1: Raw Purchase Invoice Staging

As a migration operator,
I want extracted purchase invoice headers and line items loaded into the raw_legacy staging schema,
So that the purchase transaction data is available for normalization and canonical import alongside the sales data already staged in Epic 15.

**Acceptance Criteria:**

**Given** the verified legacy export set includes tbsslipj and tbsslipdtj CSV files
**When** I run the staging import command for the purchase tables
**Then** the pipeline creates or refreshes raw_legacy.tbsslipj and raw_legacy.tbsslipdtj tables for the configured batch
**And** the CLI supports --table tbsslipj and --table tbsslipdtj flags to stage only purchase invoice tables
**And** loads source files with PostgreSQL-native bulk loading (COPY)
**And** records source table, source key, batch/run identifier, and import status for every staged row
**And** tbsslipj.supplier_code (field 7) is validated as a FK to tbscust.customer_code where type='1' (supplier)
**And** ROC-encoded dates in tbsslipj and tbsslipdtj are preserved as-is during staging for later normalization

**Given** the staging job completes for a batch that already has tbsslipj/tbsslipdtj staged
**When** I re-run the staging command for the same batch
**Then** the existing rows for those tables are replaced atomically without affecting other already-staged tables in the batch

### Story 16.2: Normalize Purchase Master Data

As a migration operator,
I want purchase master data normalized before canonical import,
So that suppliers, products, and warehouses are consistent with the canonical schema and the same product mapping used in Epic 15.

**Acceptance Criteria:**

**Given** raw_legacy.tbsslipj and raw_legacy.tbsslipdtj are staged
**When** the normalization step runs for the purchase batch
**Then** supplier records are derived from tbscust rows where type='1' (matching the pattern used in Epic 15 normalization)
**And** ROC-encoded dates are converted to AD dates using the same ROC→AD conversion applied in Epic 15
**And** tbscust type='1' suppliers are written to the canonical customers table with supplier role
**And** the same product_code_mapping table used in Epic 15 is referenced for tbsslipdtj.product_code
**And** warehouse codes in tbsslipj are resolved using the warehouse mapping established during Epic 15 staging of tbsstkhouse
**And** the normalization output for purchase data is idempotent — re-running produces the same canonical keys

### Story 16.3: Raw Purchase Order Staging

As a migration operator,
I want extracted purchase order headers loaded into the raw_legacy staging schema,
So that purchase orders are available for canonical import.

**Acceptance Criteria:**

**Given** the verified legacy export set includes tbsslipo CSV
**When** I run the staging import command for tbsslipo
**Then** the pipeline creates or refreshes raw_legacy.tbsslipo for the configured batch
**And** the CLI supports --table tbsslipo to stage only the purchase order table
**And** records source table, source key, batch/run identifier, and import status for every staged row
**And** tbsslipo.supplier_code (field 5) is validated as a FK to tbscust.customer_code where type='1'
**And** ROC-encoded dates are preserved during staging

### Story 16.4: Canonical Purchase Order Import

As a migration operator,
I want staged purchase orders imported into the canonical orders schema,
So that historical purchase order data is available in UltrERP alongside sales orders from Epic 15.

**Acceptance Criteria:**

**Given** normalized master data and product mappings are available from Epic 15 and Story 16.2
**When** I run the canonical import step for purchase orders
**Then** tbsslipo rows are imported into the canonical orders table with order_type='PURCHASE_ORDER'
**And** each purchase order line is imported into order_lines linked to the canonical product
**And** supplier is resolved through the tbscust→canonical customer mapping from Story 16.2
**And** every canonical record retains lineage back to the originating legacy table and source identifier (doc_number)
**And** the same replay-safety rules from Epic 15 Story 15.5 apply — rerunning does not create duplicate canonical records

### Story 16.5: Payment Transaction Staging

As a migration operator,
I want special payment and prepayment records staged into raw_legacy,
So that the full payment picture from the legacy system is available for canonical import.

**Acceptance Criteria:**

**Given** the verified legacy export set includes tbsspay and tbsprepay CSV files
**When** I run the staging import for payment tables
**Then** raw_legacy.tbsspay (special payments, 6 rows) and raw_legacy.tbsprepay (prepayments, 508 rows) are created
**And** the CLI supports --table tbsspay and --table tbsprepay flags
**And** customer/supplier references in these tables are validated against tbscust
**And** ROC-encoded dates are preserved during staging
**And** the payment staging is tracked in legacy_import_table_runs with the same batch_id and attempt semantics

### Story 16.6: Currency Settings Import

As a migration operator,
I want currency settings from the legacy system available in UltrERP,
So that the canonical app_settings reflects the currencies used in historical transactions.

**Acceptance Criteria:**

**Given** tbscurrency contains currency configuration (6 rows)
**When** the currency import step runs
**Then** each currency row is upserted into app_settings with keys like 'currency.{code}.symbol', 'currency.{code}.decimal_places'
**And** the default currency is marked in app_settings as 'currency.default'
**And** existing app_settings.currency.* keys are preserved unless the same currency code is being re-imported
**And** the import is idempotent — re-running does not create duplicate currency settings

### Story 16.7: Canonical Purchase Invoice Import

As a migration operator,
I want staged purchase invoice headers and lines imported into a canonical AP schema,
So that historical supplier invoice data is available in UltrERP without forcing purchase history into sales AR tables or unsupported holding records.

**Acceptance Criteria:**

**Given** normalized supplier master data, product mappings, and staged tbsslipj/tbsslipdtj rows are available
**When** I run the canonical import step for purchase invoices
**Then** each purchase invoice header is upserted into `supplier_invoices`
**And** each purchase invoice line is upserted into `supplier_invoice_lines`
**And** supplier references resolve through the normalized supplier-party mapping from Story 16.2
**And** product references reuse the same product_code_mapping flow already established for Epic 15

**Given** the same purchase-invoice batch is imported again
**When** the canonical import reruns for that batch
**Then** deterministic tenant-scoped IDs and upsert semantics prevent duplicate supplier invoices or supplier invoice lines
**And** unsupported payment-adjacent tables remain in holding until a verified AP payment model exists

### Story 16.8: Supplier Invoice Read API

As a finance or warehouse operator,
I want read-only API access to imported supplier invoices,
So that I can inspect and verify migrated AP history after canonical import completes.

**Acceptance Criteria:**

**Given** supplier invoices exist in the canonical AP tables
**When** I call the purchase read API
**Then** `GET /api/v1/purchases/supplier-invoices` returns paginated supplier invoice summaries with supplier name, totals, status, and line count
**And** `GET /api/v1/purchases/supplier-invoices/{invoice_id}` returns supplier invoice detail with line-level product enrichment
**And** only finance, warehouse, or owner roles can access these endpoints

**Given** a requested supplier invoice does not exist
**When** I request the detail route
**Then** the API returns a 404 response
**And** the new surface remains read-only with no purchase-invoice write endpoints introduced

### Story 16.9: Purchases Frontend Workspace

As a finance or warehouse operator,
I want a purchases workspace inside the UltrERP shell,
So that I can review imported supplier invoices without calling backend endpoints manually.

**Acceptance Criteria:**

**Given** a finance, warehouse, or owner user signs into the frontend shell
**When** they navigate to `/purchases`
**Then** the route is available through feature gating, navigation, and shortcut wiring
**And** unauthorized roles are blocked from the new purchases surface

**Given** imported supplier invoices exist in the purchases API
**When** the workspace loads
**Then** the list view shows supplier invoice summaries with supplier name, status, totals, and line count
**And** selecting a row opens a read-only detail view with invoice summary, notes, and imported line enrichment

**Given** the purchases API fails or returns no data
**When** the operator opens the workspace
**Then** the page shows a clear empty or error state
**And** the operator can return from detail to the list without leaving the page

### Story 16.10: AP Payment Model Design

As a migration operator and ERP architect,
I want a verified canonical model for supplier payments and prepayments,
So that `tbsspay` and `tbsprepay` can be imported later without corrupting AR payment semantics.

**Acceptance Criteria:**

**Given** the current AR-side `payments` table is reviewed
**When** the AP settlement design is documented
**Then** the design explains why the existing customer/invoice payment model is not a safe target for supplier-side history
**And** it defines dedicated AP tables for supplier cash events and supplier-invoice allocations

**Given** supplier prepayments and special payments may be unapplied or partially applied
**When** the canonical target is defined
**Then** one supplier payment may allocate to many supplier invoices
**And** prepayments are represented as a supplier payment kind rather than a separate ad hoc operational table

**Given** legacy payment-column semantics remain partially unverified
**When** import rules are written down
**Then** `tbsspay` and `tbsprepay` remain on the holding path until supplier linkage, amount/sign rules, ROC dates, and invoice-link columns are verified
**And** the design includes an explicit verification checklist before implementation starts

### Story 16.11: Canonical AP Payment Architecture

As an ERP engineer,
I want the canonical AP payment tables and relationships implemented,
So that the deferred supplier-payment import has a stable backend target before legacy allocation logic is turned on.

**Acceptance Criteria:**

**Given** AP settlement history needs its own schema foundation
**When** the backend migration runs
**Then** `supplier_payments` and `supplier_payment_allocations` exist as first-class tables
**And** they use AP-specific enums for payment kind, status, and allocation kind
**And** supplier payments relate to `supplier` while allocations bridge supplier payments to `supplier_invoices`

**Given** supplier prepayments and later settlements will share the same cash-event model
**When** the ORM layer is implemented
**Then** `supplier_payments` supports prepayment, special-payment, and adjustment kinds
**And** the many-to-many allocation model is available without reusing the AR `payments` table

**Given** legacy column semantics are still only partially verified
**When** this architecture ships
**Then** no guessed canonical import is added for `tbsspay` or `tbsprepay`
**And** the new schema is validated with focused backend tests and lint checks only

### Story 16.12: Supplier Payment Import CLI

As a migration operator,
I want a dedicated CLI step to import staged supplier payment history into the canonical AP payment tables,
So that `tbsprepay` and `tbsspay` can be migrated deliberately without coupling payment import to `canonical-import`.

**Acceptance Criteria:**

**Given** staged `tbsprepay` and `tbsspay` rows exist for a batch and the AP payment schema from Story 16.11 is present
**When** I run the new AP payment import CLI command
**Then** the legacy-import CLI exposes an explicit payment import step for that batch
**And** the command remains separate from `canonical-import`
**And** the run is tracked with batch/attempt semantics

**Given** verified payment mapping rules from Story 16.10 are available
**When** the AP payment import command runs
**Then** supplier-side cash events are written into `supplier_payments`
**And** verified invoice allocations are written into `supplier_payment_allocations`
**And** deterministic IDs and lineage records make the import replay-safe

**Given** some legacy payment rows still cannot be linked safely to a supplier invoice or have unresolved semantics
**When** the command processes those rows
**Then** they stay on the holding path or fail with explicit diagnostics instead of guessed imports
**And** unrelated verified rows in the batch still import safely when the design allows partial progress

**Given** the story is implemented
**When** focused backend validation runs
**Then** pytest covers the CLI command and canonical AP payment import behavior
**And** Ruff passes on the touched legacy-import and AP payment files

---

