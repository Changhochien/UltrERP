# Story 3.1: Search and Browse Customers

Status: completed

Depends on: Story 3.2, Story 3.3

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a sales rep,
I want to search for existing customers by Taiwan business number or company name and inspect the matching record,
so that I can reuse existing customer data before creating invoices or orders.

## Acceptance Criteria

1. Given customers exist in the system, when I search by Taiwan business number (full or partial) or company name (full or partial), and optionally narrow results by read-only customer status, then matching customers are returned with the summary fields needed to identify the right customer.
2. Given a returned search result, when I open the selected result, then I can view the full customer record by stable customer ID or through a dedicated exact-match business-number lookup contract.
3. Given the customer list may grow beyond 5,000 rows, when I browse results, then the results experience uses pagination and/or virtualization so the UI remains responsive without visible stutter on target hardware.
4. Given expected SMB-scale datasets and indexed search fields, when filters are applied, then the results load in under 500ms for the normal development dataset shape.

## Tasks / Subtasks

- [ ] Task 1: Implement customer read endpoints and query contracts (AC: 1, 2, 4)
  - [ ] Extend `backend/domains/customers/routes.py` with `GET /api/v1/customers` for filtered list results and `GET /api/v1/customers/{customer_id}` for stable detail lookup.
  - [ ] Expose `GET /api/v1/customers/lookup?business_number=...` for exact-match business-number lookup rather than overloading the path parameter to mean two different identifier types.
  - [ ] Define request/response schemas in `backend/domains/customers/schemas.py` for list filters, paging, summary rows (business number, company name, phone, and read-only status at minimum), and full customer detail payloads including the optimistic-lock `version` field needed by Story 3.5.
  - [ ] Implement list/get service methods in `backend/domains/customers/service.py` that stay framework-neutral so later MCP `customers.list` and `customers.get` surfaces can reuse them.
- [ ] Task 2: Add indexed search behavior and stable result ordering (AC: 1, 4)
  - [ ] Create or extend the customer migration with indexes on normalized business number and company name search fields.
  - [ ] Normalize user-entered business-number queries to the same canonical format used by Story 3.2 and Story 3.3.
  - [ ] Add explicit pagination parameters plus response metadata such as `page`, `page_size`, and either `total_count` plus `total_pages` or an equally clear cursor/`has_next_page` contract.
  - [ ] Support read-only status filtering against the persisted customer status field without introducing new lifecycle transitions here.
  - [ ] Use a stable default sort order such as `company_name ASC, customer_id ASC` so repeated queries do not shuffle results between pages.
- [ ] Task 3: Build the customer browse UI (AC: 1, 2, 3)
  - [ ] Create `src/pages/customers/CustomerListPage.tsx` for the browse/search experience.
  - [ ] Create UI components such as `src/components/customers/CustomerSearchBar.tsx`, `src/components/customers/CustomerResultsTable.tsx`, and `src/components/customers/CustomerDetailDialog.tsx`.
  - [ ] Create or extend `src/domain/customers/types.ts` and `src/lib/api/customers.ts` for list/get payloads.
  - [ ] If no routing library exists yet, render the customer list page from `src/App.tsx` rather than introducing broad application routing in this story.
  - [ ] Add a read-only status filter to the browse/search UI using only status values that already exist in persisted customer data.
  - [ ] Debounce networked search requests at the query layer; do not debounce the controlled input state itself.
  - [ ] Choose the browse strategy intentionally: bounded client-side pagination is acceptable for this story's dataset envelope, while large in-DOM result sets require virtualization. If a table library is introduced here, pair it with explicit pagination metadata and only add virtualization through a dedicated library such as TanStack Virtual; TanStack Table alone is not sufficient.
- [ ] Task 4: Add browse/search test coverage (AC: 1, 2, 3, 4)
  - [ ] Add backend API tests for list filters, read-only status filters, partial business-number search, partial name search, paging, dedicated business-number lookup, and detail retrieval in `backend/tests/api/test_customers_read.py`.
  - [ ] Add backend service tests for normalized query behavior and stable sort rules in `backend/tests/domains/customers/test_read_service.py`.
  - [ ] Add frontend tests for filter submission, result rendering, and detail opening in `src/tests/customers/CustomerListPage.test.tsx`.

## Dev Notes

### Story Context

- Journey 2 and Journey 4 in the PRD both require customer lookup before downstream invoice or order work starts.
- This story is the implementation home for the architecture's `customers.list` and `customers.get` capabilities.
- This story owns reusable read services and UI behavior only; FastMCP tool bindings can stay deferred to Epic 8 as long as the service contract remains reusable.
- Story 3.4 depends on this browse flow so duplicate warnings can guide the user to the existing record instead of forcing blind retries.

### Dependency Sequencing

- Implement Story 3.2 and Story 3.3 first so this story can reuse the canonical business-number validator and the customer persistence model.
- Reuse the shared UI/bootstrap and no-router screen-switch pattern chosen in Story 3.3 rather than inventing a second frontend foundation here.
- Implement this story before Story 3.4 so duplicate handling can link directly to a usable browse/detail experience.
- Story 8.2 should reuse the read service from this story for MCP-facing customer retrieval.

### Scope Guardrails

- Do not implement customer create or update forms in this story beyond linking to the existing screens once they exist.
- Do not invent an accounts-receivable balance engine just because the wireframe shows a balance column. If that field is not available yet, omit it or render an explicit placeholder until the payments/order stories define it.
- The wireframe also shows a disable action and multi-state lifecycle tags, but the PRD and architecture do not yet define customer disable/soft-delete behavior. Treat that as deferred rather than slipping it into this story.
- If status is displayed or filterable here, treat it as a read-only field only. Do not introduce status transitions, disable actions, or lifecycle mutation rules in this story.
- Do not render the entire customer dataset into the DOM. Pagination and/or virtualization is the requirement, not brute-force client rendering.

### Technical Requirements

- Keep all backend work inside `backend/domains/customers/` and mount endpoints under `/api/v1/customers`.
- Reuse `backend/common/database.py` async session handling and preserve `statement_cache_size=0` PgBouncer compatibility.
- Follow the architecture's request-scoped tenant context pattern, including `SET LOCAL app.tenant_id` or the repo's equivalent helper, whenever these read services touch the database.
- Normalize business-number search using the same utility or service helper used by Story 3.2; do not duplicate checksum logic inside query handlers.
- Before building the browse UI, choose one Epic 3 browse stack and keep it consistent across the rest of the epic: native React controls plus existing CSS, or a deliberate shared setup step that adds Tailwind/shadcn/ui and any TanStack helpers the team actually approves.
- Do not half-adopt shadcn/ui without its styling/bootstrap foundation and do not introduce competing table stacks in parallel.
- If `@tanstack/react-table` is adopted here, keep the table adapter thin and add virtualization only through `@tanstack/react-virtual` or equivalent. TanStack's current guidance still treats virtualization as a separate concern.

### Testing Requirements

- Mandatory backend coverage:
  - partial business-number search
  - partial company-name search
  - no-match behavior
  - paging bounds and default page size
  - customer detail lookup by stable customer ID and any separate exact-match business-number lookup contract the team adopts
- Frontend coverage should verify search inputs, results rendering, and detail opening. Avoid snapshot-heavy tests for large tables.

### Project Structure Notes

- Backend customer read files should extend the shared customer domain introduced by Story 3.3 rather than creating a second read-only module.
- Frontend browse/search files should live under `src/components/customers/`, `src/pages/customers/`, `src/domain/customers/`, and `src/lib/api/`.
- All customer-specific backend and frontend files in this story are greenfield additions on top of the existing app shell and the customer domain created by Story 3.3.
- If the story introduces table dependencies, update `package.json` and keep the dependency choice aligned with the UI/UX research recommendations.

### Risks / Open Questions

- Repo UX research recommends shadcn/ui plus TanStack Table and either virtualization or paging. The package manifest does not include those libraries yet, so this story must either install them intentionally in a dedicated setup step or stay with a simpler implementation that still satisfies FR50.
- The wireframe shows a status filter and balance column. Status is safe to model now; balance should not be fabricated without a defined accounting source.

### References

- `_bmad-output/epics.md` — Epic 3 / Story 3.1 acceptance criteria and Epic 8 customer MCP references.
- `_bmad-output/planning-artifacts/prd.md` — Journey 2, Journey 4, FR16, and FR50 browse/search expectations.
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` — customer domain structure, `/api/v1/customers`, and MCP `customers.list` / `customers.get` requirements.
- `research/ui-ux/01-survey-memo.md` — pagination/virtualization expectations for 5,000+ customer rows and Taiwan-localized field behavior.
- `research/ui-ux/02-wireframes/01-customer-management.md` — customer browse wireframe, status filter behavior, and keyboard flow ideas.
- `package.json` — confirms the frontend currently lacks routing, table, and form helper dependencies.
- `backend/tests/test_health.py` — reference FastAPI integration-test pattern for `httpx` + `ASGITransport`.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `/Users/hcchang/Library/Application Support/Code - Insiders/User/workspaceStorage/4320abfca0ca1465bc6bebe187407283/GitHub.copilot-chat/debug-logs/6f0af2c8-127f-429b-8f9b-f9f78e0f0e40`

### Completion Notes List

- Story aligned to the customer browse wireframe, architecture list/get tool contracts, and FR50 scalability guardrails.
- Pagination/virtualization guidance was rechecked against current TanStack documentation before finalizing the implementation notes.
- Scope was kept read-focused so create/update behavior remains in Stories 3.3 and 3.5.

### File List

- `backend/domains/customers/routes.py`
- `backend/domains/customers/schemas.py`
- `backend/domains/customers/service.py`
- `backend/tests/api/test_customers_read.py`
- `backend/tests/domains/customers/test_read_service.py`
- `migrations/versions/*_customer_read_indexes.py`
- `src/domain/customers/types.ts`
- `src/lib/api/customers.ts`
- `src/components/customers/CustomerSearchBar.tsx`
- `src/components/customers/CustomerResultsTable.tsx`
- `src/components/customers/CustomerDetailDialog.tsx`
- `src/pages/customers/CustomerListPage.tsx`
- `src/App.tsx`
- `src/tests/customers/CustomerListPage.test.tsx`
- `package.json` if table/pagination dependencies are added