# Story 2.1: Create MIG-Ready Invoice Snapshot

**Status:** done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a finance clerk,
I want to create an invoice with multiple line items, customer reference, and automatic tax calculation,
so that I can quickly issue compliant invoices without manual math.

## Acceptance Criteria

1. Given a valid existing customer and between 1 and 9999 invoice lines, when the finance clerk enters product, quantity, unit price, and the required tax inputs for each line, then the system calculates each line subtotal, tax type, allowed tax rate, tax amount, and the invoice running totals automatically from backend-owned policy.
2. Given valid invoice input, when the clerk submits the invoice, then the system persists the invoice, links it to the selected customer, snapshots the submitted line-item and buyer-identity values, and allocates the next invoice number from the configured government-issued range matching `[A-Z]{2}\d{8}`.
3. Given the invoice is displayed before downstream print/export work, when totals are rendered in the UI or returned by the API, then the clerk can see subtotal, tax breakdown, and grand total derived from the persisted line items.
4. Given invalid invoice input, when the clerk attempts to submit, then the system rejects the request with clear validation errors for missing customer, empty line set, more than 9999 lines, non-positive quantity, invalid pricing data, unsupported tax configuration, or invalid buyer identity data, and no invoice is created.
5. Given the invoice is for a B2B or B2C buyer, when the system persists the snapshot for later MIG 4.1 generation, then it stores the buyer identifier in compliant form, including `0000000000` for B2C invoices.

## Tasks / Subtasks

- [ ] Task 1: Create the invoice domain backend skeleton (AC: 1, 2, 4)
  - [ ] Create `backend/domains/invoices/__init__.py`, `backend/domains/invoices/models.py`, `backend/domains/invoices/schemas.py`, `backend/domains/invoices/service.py`, and `backend/domains/invoices/routes.py`.
  - [ ] Add the invoices router to `backend/app/main.py` under `/api/v1/invoices`.
  - [ ] Define invoice and invoice-line persistence models with `tenant_id`, customer reference, immutable line snapshot fields, line-level and summary tax fields, buyer identity snapshot fields, and invoice status fields that remain compatible with later MIG 4.1 stories.
- [ ] Task 2: Implement invoice number allocation and tax calculation policies (AC: 1, 2, 4, 5)
  - [ ] Create a calculation/policy module such as `backend/domains/invoices/policies.py` or `backend/domains/invoices/tax.py`.
  - [ ] Use `Decimal` plus PostgreSQL `NUMERIC` semantics for quantity, unit price, subtotal, tax, and total calculations; do not use floating-point math.
  - [ ] Implement a database-backed allocator for configured government-issued invoice number ranges that produces `[A-Z]{2}\d{8}` values and prevents reuse.
  - [ ] Introduce a configuration-backed or seed-data-backed tax policy mapping that resolves `TaxType` plus an allowed MIG 4.1 `TaxRate` set without hardcoding frontend tax assumptions.
- [ ] Task 3: Implement create-invoice API behavior (AC: 1, 2, 4, 5)
  - [ ] Add `POST /api/v1/invoices` request/response schemas in `backend/domains/invoices/schemas.py`.
  - [ ] Validate customer existence, line-item presence, 1..9999 line count, positive quantity, non-negative unit price, and buyer identity rules in the service layer.
  - [ ] Normalize B2C buyer identifiers to `0000000000` and reject malformed B2B identifiers before persistence.
  - [ ] Persist invoice header and line rows in one database transaction.
  - [ ] Expose an internal domain event or hook for later `InvoiceIssued` outbox work, but do not implement MinIO XML persistence or FIA submission in this story.
- [ ] Task 4: Implement the minimal finance-clerk UI for invoice creation (AC: 1, 3, 4)
  - [ ] Create `src/domain/invoices/types.ts` for request/response types.
  - [ ] Create `src/lib/api/invoices.ts` for API calls.
  - [ ] Create invoice form components such as `src/components/invoices/InvoiceLineEditor.tsx` and `src/components/invoices/InvoiceTotalsCard.tsx`.
  - [ ] Create a page such as `src/pages/invoices/CreateInvoicePage.tsx` and mount it in the current app shell.
  - [ ] If no routing library exists yet, render the create-invoice page directly from `src/App.tsx` rather than introducing full app-wide routing in this story.
- [ ] Task 5: Add implementation-facing tests (AC: 1, 2, 3, 4, 5)
  - [ ] Add backend service tests for tax calculation, invoice-number allocation format, B2C sentinel handling, and validation failures in `backend/tests/domains/invoices/test_service.py`.
  - [ ] Add API tests for `POST /api/v1/invoices` in `backend/tests/api/test_create_invoice.py`.
  - [ ] Add frontend tests for totals rendering and submit-state validation only if Story 1.3 test scaffolding is present; otherwise prioritize backend coverage and a minimal frontend smoke test.

## Dev Notes

### Story Context

- This is the first story in the invoice epic and establishes the invoice aggregate, create flow, and tax calculation baseline that later stories depend on.
- Story 2.2 and Story 2.6 depend on this story producing a stable invoice snapshot and totals contract.
- Story 2.3 and Story 2.7 depend on this story persisting invoice data in a way that can later be enforced as immutable.
- Story 2.5 depends on this story exposing an invoice-issued domain event or equivalent hook for MIG 4.1 XML persistence and archival.

### Dependency Sequencing

- Implement Story 2.1 first. It is the Epic 2 foundation and unlocks all other invoice lifecycle work.
- Do not start Story 2.2, 2.3, 2.4, 2.5, 2.6, or 2.7 implementation until this story has shipped the persisted invoice snapshot, buyer snapshot, and invoice-number allocation contract.

### Scope Guardrails

- Do not implement full customer management here. Story 2.1 requires selecting an existing customer only. Customer CRUD/search workflows belong to Epic 3.
- Do not implement full inventory workflows here. Product selection may depend on seeded catalog data or a minimal read-only lookup, but stock management belongs to Epic 4.
- Do not implement print layout, PDF export, MinIO storage, FIA submission, or invoice voiding in this story.
- Do implement an invoice data model that is compatible with later eGUI and immutability stories so those stories extend this work instead of replacing it.

### Backend Architecture Requirements

- Keep all backend work inside the approved modular-monolith structure under `backend/app`, `backend/common`, and `backend/domains`.
- Mount invoice endpoints under `/api/v1/invoices`; do not introduce non-versioned routes.
- Reuse `backend/common/config.py` and `backend/common/database.py` from Epic 1 foundation work.
- Keep database access async and ensure the asyncpg engine continues using `statement_cache_size=0` for PgBouncer compatibility.
- Include `tenant_id` on invoice-owned tables even if solo/team mode does not yet enforce RLS.

### Invoice Domain Rules

- Invoice numbers must match `[A-Z]{2}\d{8}` and be allocated from configured government-issued ranges. Reuse of invoice numbers is not allowed.
- MIG 4.1 requires tax information at both summary and line-item levels. Each invoice line must persist `tax_type`, `tax_rate`, and `tax_amount`, and the invoice header must persist the summary values needed for later XML generation.
- Buyer identity must be persisted in a MIG-compatible form. B2B invoices use the buyer BAN; B2C invoices use `0000000000`.
- Use integer-safe or decimal-safe arithmetic for totals. All user-visible totals must come from persisted values, not a separate frontend-only calculation path.
- The system must support the MIG 4.1 tax-type model from day one: `TaxType=1`, `2`, `3`, and policy-approved `4` values, with allowed rates chosen from the validated MIG rate set rather than hardcoded UI assumptions.
- `ZeroTaxRateReason` must remain modelable for zero-rate cases even if later stories are the first to serialize it into XML.
- The precise product-category-to-tax mapping is not yet fully formalized in repo artifacts. Implement the mapping through a backend-owned policy/configuration layer so business rules can be refined without rewriting the UI.
- MIG 4.1 supports up to 9999 line items per invoice; the create flow must enforce that cap.

### Data and Persistence Requirements

- Expected persistence footprint for this story:
  - `invoices` table for invoice header data
  - `invoice_lines` table for immutable line snapshots
  - an invoice-range allocation table or equivalent locking strategy for government-issued invoice numbers
- Persist invoice header and line rows in one transaction.
- Leave a clear extension point for a later `InvoiceIssued` domain event so Story 2.5 can add XML persistence and outbox integration without reworking the create flow.
- Do not make MinIO or FIA connectivity a runtime dependency for Story 2.1.

### Frontend Requirements

- Build the create flow with React 19, Vite, and strict TypeScript as established in Epic 1.
- Keep invoice input state explicit and serializable; avoid hidden derived state that can diverge from backend totals.
- Show line-level and invoice-level totals in the UI so the clerk sees the same data the backend will persist.
- If customer/product lookup UI is not yet available, use a narrow temporary selector strategy that can be replaced later without changing the invoice payload contract.

### Testing Requirements

- Backend tests are mandatory for this story.
- Minimum backend coverage should include:
  - taxable line calculation using a configured allowed rate
  - 0% zero-rate or tax-free line calculation
  - special-rate calculation using policy-configured MIG-compatible rates
  - multi-line invoice aggregation
  - invoice number format and range-allocation behavior
  - B2B versus B2C buyer identifier handling
  - validation failures for missing customer, invalid lines, and line counts above 9999
- Frontend coverage should verify totals rendering and validation feedback, but avoid spending story budget on broad UI framework setup if the Story 1.3 scaffolding is still incomplete.

### Project Structure Notes

- Backend invoice files belong under `backend/domains/invoices/`.
- Shared invoice-independent helpers belong under `backend/common/` only if they are genuinely reusable.
- Frontend invoice types should live under `src/domain/invoices/` and API helpers under `src/lib/api/`.
- UI components for invoice entry should live under `src/components/invoices/`.
- Do not add a second backend app, separate worker service, or standalone invoice microservice.

### Risks / Open Questions

- The repo currently lacks a finalized product-category-to-tax mapping document. Treat that as a configurable backend rule, not a hardcoded UI rule.
- Epic sequencing means Story 2.1 needs existing customer and product references before the full management epics are built. Use seeded or read-only reference data rather than pulling full Epic 3 or Epic 4 scope into this story.
- MIG 4.1 XML generation, ZeroTaxRateReason serialization, and archival belong to Story 2.5, but the line-item and buyer-snapshot data shape created here must already support them.

### References

- `_bmad-output/epics.md` — Epic 2 / Story 2.1 acceptance criteria and neighboring invoice stories.
- `_bmad-output/planning-artifacts/prd.md` — Journey 2, Taiwan compliance constraints, and invoice-first scope.
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` — invoice domain model, MCP tool shape, outbox pattern, MinIO archival model, retention baseline, and build order.
- `research/egui-compliance/01-survey-memo.md` — MIG 4.1 field requirements, tax type definitions, invoice number format, and void deadline notes.
- `_bmad-output/implementation-artifacts/1-2-project-structure.md` — approved backend/frontend file locations.
- `_bmad-output/implementation-artifacts/1-3-ci-cd-pipeline.md` — expected test and lint workflow.
- `_bmad-output/implementation-artifacts/1-5-fastapi-backend-foundation.md` — FastAPI route/versioning and shared backend conventions.
- `_bmad-output/implementation-artifacts/1-7-database-migrations-setup.md` — Alembic invocation pattern and migration layout.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `/Users/hcchang/Library/Application Support/Code - Insiders/User/workspaceStorage/4320abfca0ca1465bc6bebe187407283/GitHub.copilot-chat/debug-logs/e9fed657-b634-4e14-91d2-303118396630`

### Completion Notes List

- Story file created from Epic 2, PRD, architecture v2, Epic 1 foundation artifacts, and eGUI compliance research.
- Scoped Story 2.1 to invoice creation only and explicitly deferred print, PDF, archival, void, and full customer/product management work.
- Flagged tax policy mapping and government-issued number-range configuration as the main unresolved business inputs so implementation does not hardcode the wrong behavior.

### File List

- `backend/domains/invoices/__init__.py`
- `backend/domains/invoices/models.py`
- `backend/domains/invoices/schemas.py`
- `backend/domains/invoices/service.py`
- `backend/domains/invoices/routes.py`
- `backend/domains/invoices/tax.py` or `backend/domains/invoices/policies.py`
- `backend/tests/domains/invoices/test_service.py`
- `backend/tests/api/test_create_invoice.py`
- `migrations/versions/*_create_invoice_core_tables.py`
- `src/domain/invoices/types.ts`
- `src/lib/api/invoices.ts`
- `src/components/invoices/InvoiceLineEditor.tsx`
- `src/components/invoices/InvoiceTotalsCard.tsx`
- `src/pages/invoices/CreateInvoicePage.tsx`
- `src/App.tsx`