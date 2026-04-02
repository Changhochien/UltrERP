# Story 3.3: Create Customer Record

Status: completed

Depends on: Story 3.2

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a sales rep,
I want to create a new customer with business number, address, contact details, and credit limit,
so that I can add new B2B customers to the system without re-entering them in later flows.

## Acceptance Criteria

1. Given I'm creating a new customer, when I fill in company name, Taiwan business number validated by Story 3.2, billing address, primary contact name, contact phone, contact email, and credit limit, then the customer is saved to the database.
2. Given the customer is saved, when persistence succeeds, then `tenant_id` is set correctly and I receive confirmation with the created customer ID.
3. Given invalid customer input such as malformed Taiwan phone data, malformed email data, negative credit limits, or an invalid business number, when I attempt to save, then the system returns clear validation errors and no customer is created.
4. Given the customer will be reused by invoices and orders, when the create flow finishes, then the created record is persisted with a stable customer ID and returned in a shape that downstream read APIs and UI can retrieve without reshaping.

## Tasks / Subtasks

- [ ] Task 0: Lock the shared Epic 3 frontend foundation before building customer UI (supports AC: 1, 3, 4)
  - [ ] Complete and merge this task before any Epic 3 UI work starts in Story 3.3, Story 3.1, or Story 3.5.
  - [ ] Choose one Epic 3 UI path and document it in the implementation notes for the rest of the epic: native React state plus existing CSS, or a deliberate shared setup that adds Tailwind/shadcn/ui, `react-hook-form`, and `zod` together.
  - [ ] If the shared-setup path is chosen, update `package.json` and the required styling/bootstrap files in one dedicated preparatory commit before Story 3.1 or Story 3.5 start UI work.
  - [ ] Establish one no-router page-switch pattern in `src/App.tsx` or a small local shell so create, browse, and edit screens can coexist without each story inventing a different navigation mechanism.
- [ ] Task 1: Create the customer domain backend skeleton (AC: 1, 2, 3, 4)
  - [ ] Create `backend/domains/customers/__init__.py`, `backend/domains/customers/models.py`, `backend/domains/customers/schemas.py`, `backend/domains/customers/service.py`, and `backend/domains/customers/routes.py`.
  - [ ] Mount the customer router in `backend/app/main.py` under `/api/v1/customers`.
  - [ ] Create `backend/common/tenant.py` or an equivalent helper and wire it through `backend/app/deps.py` or the customer service layer so request-scoped tenant context is applied before database work.
  - [ ] Expand `backend/common/errors.py` and register the needed FastAPI handlers so customer APIs return one structured error contract reused by Stories 3.2, 3.4, and 3.5.
  - [ ] Define a `customers` table with `tenant_id`, company name, normalized business number, billing address, primary contact fields, credit limit, status, optimistic-lock `version`, and timestamps.
  - [ ] If a `status` column is introduced for browse parity, default it to a read-only active/normal value and leave lifecycle transitions or disable rules out of Epic 3.
  - [ ] Use `Decimal`/PostgreSQL `NUMERIC(12,2)` semantics for `credit_limit`; reject negative values and values outside that schema precision.
- [ ] Task 2: Implement customer-create service behavior (AC: 1, 2, 3)
  - [ ] Add `POST /api/v1/customers` request/response schemas.
  - [ ] Call the Story 3.2 backend validator before persistence.
  - [ ] Validate required fields, Taiwan-localized contact formats, non-negative credit limits, and the numeric bounds implied by `NUMERIC(12,2)` in the service layer.
  - [ ] Implement concrete phone validation for the approved Taiwan formats and basic application-level email validation before persistence.
  - [ ] Persist the customer in one transaction and return a stable response payload with the new customer ID and initial optimistic-lock `version`.
  - [ ] Roll back the transaction and return the structured customer error contract if validation, tenant setup, or persistence helpers fail before commit.
- [ ] Task 3: Build the minimal create-customer UI (AC: 1, 2, 3)
  - [ ] Create `src/domain/customers/types.ts` for create payloads and responses.
  - [ ] Create `src/lib/api/customers.ts` for create calls.
  - [ ] Create `src/components/customers/CustomerForm.tsx` and `src/pages/customers/CreateCustomerPage.tsx`.
  - [ ] If no shared form stack exists yet, either use explicit React state or intentionally introduce `react-hook-form` plus `zod`; do not add an unplanned third form library later.
  - [ ] If no routing exists yet, render the create page directly from `src/App.tsx` or via a controlled in-app screen switch.
- [ ] Task 4: Add implementation-facing tests (AC: 1, 2, 3, 4)
  - [ ] Add backend service tests in `backend/tests/domains/customers/test_create_service.py`.
  - [ ] Add backend API tests for `POST /api/v1/customers` in `backend/tests/api/test_create_customer.py`.
  - [ ] Add a frontend test for submit-state validation and success handling in `src/tests/customers/CreateCustomerPage.test.tsx`.

## Dev Notes

### Story Context

- This story establishes the customer aggregate used later by invoice, order, MCP, and update flows.
- Journey 2 and Journey 4 both assume a new customer can be created from the same desktop workflow that later issues invoices or orders.
- The architecture build order places customers immediately after invoice foundations, so this story should set stable patterns rather than throwaway scaffolding.
- This story owns the shared Epic 3 frontend bootstrap decision so Stories 3.1 and 3.5 do not fragment the UI stack.
- This story also owns the shared customer error contract and tenant-context helper that later Epic 3 stories depend on.

### Dependency Sequencing

- Implement Story 3.2 first and consume its validator here.
- Story 3.1 should follow this story so browse/read flows operate on the same persisted customer shape.
- Story 3.4 and Story 3.5 should extend this story's customer domain rather than replacing its schemas or service layer.
- FastMCP customer tool bindings remain Epic 8 work; this story only needs to expose a stable service contract they can reuse later.

### Scope Guardrails

- Do not implement duplicate-resolution UX here beyond the minimum persistence constraint needed to protect the table. Friendly duplicate handling belongs to Story 3.4.
- Do not implement customer edit, disable, or delete behavior in this story.
- The customer-management wireframe shows a disable action, but that behavior is not backed by the current PRD or architecture. Leave disable/soft-delete out of this create story.
- Do not implement credit-limit enforcement against orders here; store the credit-limit field only. Order-time enforcement belongs in Epic 5.
- Do not invent an accounts-receivable balance field just because a later browse wireframe shows one.

### Backend Architecture Requirements

- Keep all backend code under `backend/domains/customers/` and mount routes only under `/api/v1/customers`.
- Reuse `backend/common/config.py`, `backend/common/database.py`, and the async SQLAlchemy session pattern already in place.
- Follow the architecture's request-scoped tenant context pattern, including `SET LOCAL app.tenant_id` or the repo's equivalent helper, before create/read/update queries run.
- Include `tenant_id` on the customer table even if solo/team mode does not yet turn on row-level security.
- Establish one reusable tenant-context helper rather than scattering raw tenant SQL across routes and services.
- Create the schema/migration in a way Story 3.4 can later enforce a unique constraint on normalized business number without redesigning the table.

### Frontend Requirements

- The current frontend has no routing, no form framework, and no schema-validation helper. Before UI work starts, choose one Epic 3 form stack and keep it consistent across the rest of the epic: explicit React state plus current CSS, or a deliberate shared setup step that adds Tailwind/shadcn/ui, `react-hook-form`, and `zod` together.
- Do not half-adopt shadcn/ui without its styling/bootstrap foundation or mix multiple form libraries inside one epic.
- Show validation feedback inline for customer fields, especially the business-number field and credit-limit field.
- Keep form state explicit and serializable; do not rely on hidden DOM state.

### Contact Validation Rules

- If phone validation is implemented now, accept Taiwan-relevant formats from the UX research: local mobile patterns such as `09xx-xxx-xxx`, landline patterns such as `(0X) xxxx-xxxx`, and any approved normalized `+886` API form.
- Email validation should stay at a basic application-format level such as a conservative RFC-5322 subset or `user@domain.tld` shape check, not a deliverability or MX-record guarantee.

### Testing Requirements

- Mandatory backend coverage:
  - valid customer creation
  - required-field failures
  - invalid business number
  - invalid phone/email if format checks are implemented
  - negative credit limit rejection
  - structured validation error payloads
- Frontend coverage should verify validation messaging and successful submit handling, not deep implementation details of unrelated layout code.

### Project Structure Notes

- Backend customer files belong under `backend/domains/customers/`.
- Shared backend infrastructure added by this story belongs under `backend/common/` and `backend/app/`.
- Shared customer types should live under `src/domain/customers/` and API helpers under `src/lib/api/`.
- UI form components should live under `src/components/customers/`.
- Because the root app currently renders directly from `src/App.tsx`, establish one minimal screen-switch pattern here and reuse it in the browse and edit stories instead of introducing a second navigation abstraction later.

### Risks / Open Questions

- Task 0 must lock the Epic 3 UI stack before any downstream customer UI work begins; do not let later stories reopen that decision implicitly.
- Contact-field formatting rules exist in UX research, but the repo does not yet define whether all fields are strictly required. Keep the required/optional split aligned with FR18 and current workflow needs.

### References

- `_bmad-output/epics.md` — Story 3.3 acceptance criteria and adjacent customer stories.
- `_bmad-output/planning-artifacts/prd.md` — Journey 2, Journey 4, FR18, and customer creation role context.
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` — customer domain model, `/api/v1/customers`, and build order.
- `research/ui-ux/01-survey-memo.md` — Taiwan-localized field entry expectations for business number, phone, and address.
- `research/ui-ux/02-wireframes/01-customer-management.md` — customer-management wireframe and form/browse interaction hints.
- `backend/common/database.py` — async engine/session conventions that the customer domain must reuse.
- `vite.config.ts` — existing `/api` proxy target for frontend integration.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `/Users/hcchang/Library/Application Support/Code - Insiders/User/workspaceStorage/4320abfca0ca1465bc6bebe187407283/GitHub.copilot-chat/debug-logs/6f0af2c8-127f-429b-8f9b-f9f78e0f0e40`

### Completion Notes List

- Story scoped the first real customer aggregate and kept credit-limit enforcement intentionally out of this slice.
- File targets were aligned to the existing FastAPI modular-monolith layout and the current routing-free React shell.
- Validation was made a hard dependency on Story 3.2 rather than duplicated in create logic.

### File List

- `backend/app/main.py`
- `backend/app/deps.py`
- `backend/common/errors.py`
- `backend/common/tenant.py`
- `backend/domains/customers/__init__.py`
- `backend/domains/customers/models.py`
- `backend/domains/customers/schemas.py`
- `backend/domains/customers/service.py`
- `backend/domains/customers/routes.py`
- `backend/tests/domains/customers/test_create_service.py`
- `backend/tests/api/test_create_customer.py`
- `migrations/versions/*_create_customers_table.py`
- `src/domain/customers/types.ts`
- `src/lib/api/customers.ts`
- `src/components/customers/CustomerForm.tsx`
- `src/pages/customers/CreateCustomerPage.tsx`
- `src/App.tsx`
- `src/tests/customers/CreateCustomerPage.test.tsx`
- `package.json` if a shared form/validation stack is introduced