# Story 12.1: Virtualized Lists for 5,000+ Rows

Status: ready-for-dev

## Story

As a user,
I want customer and inventory list surfaces to stay responsive with 5,000+ rows,
So that I can browse large datasets without visible lag.

## Acceptance Criteria

**AC1:** Inventory search remains smooth at large result counts  
**Given** the inventory search surface returns 5,000+ products  
**When** I scroll or refine the query  
**Then** the visible list mounts within 2 seconds (p95) on target hardware  
**And** scrolling shows no visible stutter

**AC2:** Customer flows stay responsive without loading the full tenant dataset into the DOM  
**Given** the tenant has 5,000+ customers  
**When** I browse customers or pick a customer from invoice/payment flows  
**Then** the UI remains responsive  
**And** customer browse keeps server pagination in place  
**And** high-volume customer pickers use searchable, bounded rendering instead of eager full-list selects

**AC3:** Keyboard and assistive behavior survives virtualization  
**Given** I navigate the large-data surfaces with keyboard or assistive tech  
**When** focus moves through rows or picker options  
**Then** the currently active item remains discoverable  
**And** selection works without relying on the mouse only

**AC4:** Existing query/filter contracts do not regress  
**Given** current customer and inventory APIs already support filtering and pagination  
**When** this story lands  
**Then** existing routes and query params continue to work  
**And** the story does not replace server pagination with a client-side 5,000-row fetch

## Tasks / Subtasks

- [ ] **Task 1: Lock the scope to the repo's real bottlenecks** (AC2, AC4)
  - [ ] Keep the existing customer browse API pagination contract in `backend/domains/customers/routes.py` (`page_size <= 100`)
  - [ ] Reuse the existing `react-window` dependency already in `package.json`
  - [ ] Do **not** introduce TanStack Table / TanStack Virtual in this story; they are not currently in the production stack
  - [ ] Treat FR50 as "virtualization and/or pagination" and avoid rewriting working pagination purely to satisfy the story title literally

- [ ] **Task 2: Harden the existing inventory virtualization surface** (AC1, AC3)
  - [ ] Extend `src/domain/inventory/components/ProductSearch.tsx`
  - [ ] Keep `react-window` as the renderer for large product result sets
  - [ ] Add explicit result-count and loading/error/empty-state behavior that does not cause layout thrash while searching
  - [ ] Ensure the virtualized rows remain keyboard reachable and screen-reader discoverable
  - [ ] Validate that fast scrolling does not create obvious white-gap or focus-loss regressions

- [ ] **Task 3: Replace eager high-volume customer selects with a searchable bounded picker** (AC2, AC3)
  - [ ] Replace the eager `page_size: 200` customer loads in `src/pages/invoices/CreateInvoicePage.tsx`
  - [ ] Replace the eager `page_size: 200` customer loads in `src/domain/payments/components/RecordUnmatchedPayment.tsx`
  - [ ] Introduce a shared async customer picker component under `src/components/customers/` or `src/domain/customers/components/`
  - [ ] Query customers incrementally through the existing `listCustomers()` API helper instead of rendering one giant native `<select>`
  - [ ] Virtualize rendered option rows when the picker result set is large enough to justify it

- [ ] **Task 4: Keep customer browse semantic and bounded** (AC2, AC4)
  - [ ] Preserve pagination in `src/pages/customers/CustomerListPage.tsx` and `src/components/customers/CustomerResultsTable.tsx`
  - [ ] If a larger page-size option is added, keep DOM node count bounded and avoid loading all pages into memory at once
  - [ ] Do not replace the semantic browse table with a fake 5,000-row client grid unless product explicitly changes the browse contract later

- [ ] **Task 5: Add focused regression and performance checks** (AC1, AC2, AC3)
  - [ ] Add frontend tests covering the shared customer picker search, keyboard selection, and empty/error states
  - [ ] Add a focused test for the inventory search surface proving only the visible virtualized rows render at a time
  - [ ] Add a manual performance checklist using seeded/mock 5,000+ datasets and record the expected pass criteria in the story's implementation notes

## Dev Notes

### Repo Reality

- `src/domain/inventory/components/ProductSearch.tsx` already uses `react-window`; Story 12.1 is not greenfield.
- Customer browse is already paginated end-to-end. `backend/domains/customers/routes.py` caps `page_size` at 100, so the correct solution is to preserve pagination rather than fetch 5,000 rows into the client.
- The real unbounded customer pain points in current code are the eager active-customer loads in:
  - `src/pages/invoices/CreateInvoicePage.tsx`
  - `src/domain/payments/components/RecordUnmatchedPayment.tsx`

### Critical Warnings

- Do **not** defeat server pagination to satisfy the word "virtualized" in the story title. FR50 explicitly allows virtualization and/or pagination.
- Do **not** add TanStack Table or TanStack Virtual here. The repo already standardizes on `react-window`, and this story should reduce churn, not create a second list stack.
- Native HTML table virtualization with `react-window` is awkward. Keep the browse table semantic if page sizes remain small, and solve the real high-volume problem in searchable pickers and inventory results.

### Implementation Direction

- Preferred strategy:
  - inventory search: strengthen the existing `react-window` list
  - customer browse: keep paginated
  - invoice/payment customer selection: replace eager select controls with async bounded rendering
- If keyboard interaction becomes difficult in a virtualized picker, prefer a simpler ARIA listbox pattern over a fake table abstraction.

### Validation Follow-up

- `react-window` 2.2.7 is already installed, and `src/domain/inventory/components/ProductSearch.tsx` already uses the v2 `List` API with fixed 48px rows. Keep the implementation on the fixed-size path unless a new measured requirement forces variable sizing later.
- Customer browse is already correctly bounded by backend pagination (`page_size <= 100`). The real high-volume work remains the eager `page_size: 200` customer loads in invoice and unmatched-payment flows.
- When the async customer picker replaces the native `<select>`, treat it as a real ARIA listbox implementation checklist: `role="listbox"`, `role="option"`, `aria-activedescendant`, and active-option scroll-into-view behavior.
- AC1's 2-second p95 target should not stay manual-only. The current repo has no Playwright harness or `performance.mark()` instrumentation, so this story should introduce explicit timing hooks and the narrowest automated browser-level check that can enforce the budget.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 12 / Story 12.1 / FR50
- `_bmad-output/planning-artifacts/prd.md` - FR50 and customer/inventory responsiveness NFR
- `src/domain/inventory/components/ProductSearch.tsx` - existing virtualization anchor
- `src/pages/customers/CustomerListPage.tsx` - existing customer browse page
- `src/components/customers/CustomerResultsTable.tsx` - existing customer browse renderer
- `src/pages/invoices/CreateInvoicePage.tsx` - eager 200-customer load to remove
- `src/domain/payments/components/RecordUnmatchedPayment.tsx` - eager 200-customer load to remove
- `backend/domains/customers/routes.py` - current page-size cap and pagination contract
- `https://web.dev/articles/virtualize-long-lists-react-window` - windowing guidance and fixed-size list rationale

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Completion Notes List

- Story authored against the actual repo bottlenecks, not a generic "virtualize everything" assumption.
- The story keeps customer browse pagination intact and targets the real eager-load surfaces instead.
- Dependency churn was intentionally avoided: `react-window` stays the list solution for this slice.