# Story 3.1 Validation Report: Search and Browse Customers

**Story:** `3-1-search-and-browse-customers.md`
**Validator:** Claude Code (compliance validation)
**Date:** 2026-04-01
**Status:** `needs-revision`

---

## Iteration Protocol Summary

- **Iteration 1** (2026-04-01): Read all source documents, performed 3 web searches (React table pagination/virtualization, Taiwan business number search patterns, FastAPI async pagination), inspected codebase structure.
- **Iteration 2** (2026-04-01): Cross-checked each finding against source documents, best practices, and codebase reality; confirmed or invalidated each issue.

---

## 1. Confirmed Valid Points

The following aspects of the story are confirmed correct and aligned with source documents:

1. **AC completeness and testability**: All 4 ACs are unambiguously testable with concrete Given/When/Then language. No vague qualifiers that cannot be verified programmatically.

2. **AC1 -- search by tax ID or name, partial match**: Matches Epic 3 AC and FR16 ("Sales rep can search for existing customers by 統一編號 or name"). Partial match is explicitly called out, which is appropriate for SMB user workflows.

3. **AC2 -- detail lookup**: Correctly scoped to read-only retrieval. Maps to the architecture's `customers.list` and `customers.get` MCP contracts.

4. **AC3 -- pagination/virtualization for 5,000+ rows**: Directly maps to FR50 ("Customer and inventory lists support virtualization and/or pagination for 5,000+ rows without visible stutter"). The alternative ("pagination and/or virtualization") is correctly permissive since both approaches are valid.

5. **AC4 -- <500ms performance**: Maps to NFR performance target and FR50's responsiveness requirement. The "indexed search fields" qualifier appropriately constrains the requirement to indexed database queries.

6. **Scope guardrails are correct**:
   - Do NOT implement create/update forms (correctly deferred to Stories 3.3 and 3.5)
   - Do NOT fabricate balance data (correctly treated as deferred -- no accounts-receivable source defined)
   - Do NOT implement status transitions / disable actions (correctly deferred -- lifecycle not defined in PRD/architecture)
   - Do NOT render entire dataset in DOM (correctly prohibited)

7. **TanStack guidance is correct**: The explicit note that "TanStack Table alone is not sufficient" for virtualization, and that `@tanstack/react-virtual` (or equivalent) must be added separately, matches current TanStack guidance (as of 2026, TanStack Table + TanStack Virtual are separate libraries).

8. **No half-adoption of shadcn/ui**: The Tech Requirements explicitly prohibit adding shadcn/ui without its complete styling/bootstrap foundation. This aligns with the UI/UX survey's finding that shadcn requires careful React 19 compatibility management on Tauri.

9. **asyncpg + PgBouncer compatibility**: Story correctly specifies `statement_cache_size=0` for asyncpg, consistent with the architecture spec and tech-viability research.

10. **Multi-tenancy tenant context**: Story correctly references using `SET LOCAL app.tenant_id` or equivalent helper, consistent with the architecture's multi-tenancy model.

11. **Dependency ordering notes are directionally correct**: Story notes that 3.2 (MOD11 validator) and 3.3 (customer model) should be implemented first so this story can reuse them. Story 3.4 correctly depends on this story.

12. **Read-only service contract for MCP reuse**: The story's instruction to keep service methods "framework-neutral" for later MCP reuse is correct and matches the architecture's `customers.list` and `customers.get` tool definitions.

---

## 2. Issues by Severity

### CRITICAL

#### C1: Dependency sequencing not formalized as story dependencies

**Finding:** The story's Dev Notes say "Implement Story 3.2 and Story 3.3 first" and "Implement this story before Story 3.4," but these are stated as advisory notes, not as formal dependency declarations. The story is marked `Status: ready-for-dev` without any explicit "depends on" block.

**Why critical:** Story 3.1 requires:
- The canonical business-number normalization utility from Story 3.2 (Task 2: "Normalize user-entered business-number queries to the same canonical format used by Story 3.2 and Story 3.3")
- The customer persistence model (`Customer` SQLAlchemy model) from Story 3.3 (the backend files at `backend/domains/customers/` do not exist yet -- the entire customer domain is unstarted)
- The shared frontend bootstrap and no-router screen-switch pattern from Story 3.3

Without these as formal blocking dependencies, a dev team could start Story 3.1 in parallel with 3.2 and 3.3 and produce incompatible code.

**Source:** Dev Notes section, Dependency Sequencing; Architecture spec Section 5.1 (customer model not yet defined); codebase inspection confirms `backend/domains/customers/` does not exist.

**Resolution required:** Either (a) add explicit "depends on: Story 3.2, Story 3.3" declaration at the top of the story, or (b) re-sequence the sprint so 3.2 and 3.3 are completed before 3.1 starts. The current `ready-for-dev` status is misleading without this clarification.

---

#### C2: Backend codebase is empty -- "extend" language is misleading

**Finding:** The story uses verbs like "Extend `backend/domains/customers/routes.py`" and "Extend `backend/domains/customers/schemas.py`" which imply these files already exist. Inspection reveals:
- `backend/domains/` exists but contains only `__init__.py` and a `health/` subdomain
- `backend/domains/customers/` does not exist
- `backend/common/` contains only `__init__.py`
- `backend/app/` contains only `__init__.py`

The entire backend domain layer is unstarted skeleton code.

**Why critical:** A developer reading this story would reasonably expect to "extend" existing files. Starting from empty directories will cause confusion and potential incorrect file creation.

**Source:** Backend codebase glob results; story file list in Dev Agent Record.

**Resolution required:** Update story file list to distinguish between files to be created (`routes.py`, `schemas.py`, `service.py`) vs. files to be extended if they existed. Add a note in Dev Notes that the entire `backend/domains/customers/` tree must be created fresh.

---

#### C3: Frontend `src/` is empty -- same issue for frontend files

**Finding:** The story references `src/pages/customers/CustomerListPage.tsx`, `src/components/customers/CustomerSearchBar.tsx`, `src/components/customers/CustomerResultsTable.tsx`, `src/domain/customers/types.ts`, `src/lib/api/customers.ts`, `src/App.tsx`. Inspection of `src/` reveals only `vite-env.d.ts` exists.

**Why critical:** The story implies extending existing frontend infrastructure that does not yet exist. Specifically:
- `src/App.tsx` does not exist (the Vite template may not have been run, or it's been wiped)
- No `src/domain/`, `src/lib/`, `src/components/`, or `src/pages/` directories exist

**Source:** Frontend `src/` glob results.

**Resolution required:** Story should clarify that ALL frontend files for this story are greenfield creation, not extension. Consider adding a task to create the directory scaffold first (e.g., `mkdir -p src/domain/customers src/lib/api src/components/customers src/pages/customers`).

---

### MAJOR

#### M1: API design for `customers.get` by tax_id is ambiguous

**Finding:** AC2 says "I can view the full customer record by customer ID or business number." The story's Task 1 says to expose an "exact-match lookup contract" for business-number detail lookup "if needed outside the list flow." But:
- The only explicit endpoint is `GET /api/v1/customers/{customer_id}` (path parameter is UUID)
- There is no explicit `GET /api/v1/customers?tax_id=XXXXXXXX` or `GET /api/v1/customers/by-tax-id/{tax_id}` endpoint defined
- The architecture spec's MCP tool `customers.get` accepts "ID or tax_id" but the REST contract is not explicitly defined

**Why major:** This is a core functional requirement (AC2) but the API design is underspecified. An implementation team will have to make a design decision that should be documented in the story.

**Source:** Story Task 1; Architecture spec Section 6.1 Customers table.

**Recommended fix:** Add an explicit sub-task: "Define and document `GET /api/v1/customers/by-tax-id/{tax_id}` or `GET /api/v1/customers/lookup?tax_id=XXXXXXXX` as the exact-match tax_id lookup contract." This should not be left as "if needed" -- AC2 explicitly requires it.

---

#### M2: AC4 ("indexed search fields") is ambiguous for performance requirement

**Finding:** AC4 says "Given expected SMB-scale datasets and indexed search fields, when filters are applied, then the results load in under 500ms." The qualifier "indexed search fields" creates ambiguity:
- If indexes don't exist yet, is the AC considered "passed" or "failed"?
- The phrase could be read as a condition that must be met (i.e., the story must create those indexes), or as a pre-condition that must already be true

**Why major:** The <500ms SLA only applies "given indexed search fields." The story's Task 2 says to "Create or extend the customer migration with indexes," which suggests indexes are within-scope to create. But this should be explicit in the AC, not left to interpretation.

**Source:** AC4 wording; Task 2; PRD performance NFR.

**Recommended fix:** Rewrite AC4 to make the index-creation explicit: "Given I have created database indexes on the normalized business_number and company_name search fields, when I apply filters, then results load in under 500ms." Or move the index requirement to AC3 and keep AC4 as an unconditional performance requirement.

---

#### M3: Status filter and status display scope creep risk

**Finding:** The wireframe (`01-customer-management.md`) shows a status filter dropdown (全部/正常/停用) and a status column in the results table. The story's Scope Guardrails correctly defer status transitions and disable actions, and the Tech Notes say "Status is safe to model now." However:
- AC1 does not mention status filtering
- AC2 does not mention status in the detail view
- There is no task to add a status filter to the search UI
- The story's file list does not include any status-related components

**Why major:** The wireframe explicitly shows a status filter. If the story doesn't implement it, there is a gap between the designed UI and the implemented story. If it does implement it, it should be explicit in an AC. The current story is silent on status filtering.

**Source:** Wireframe `01-customer-management.md`; story Scope Guardrails.

**Recommended fix:** Either (a) explicitly exclude status filter from this story and note it as deferred to a future story, or (b) add an AC for status filtering ("Given status values are defined, when I filter by status, then only matching customers are returned") and add a corresponding sub-task. Given the wireframe includes it, excluding it should be a deliberate decision documented in scope guardrails.

---

#### M4: TanStack Table and TanStack Virtual not in `package.json`

**Finding:** The story references `@tanstack/react-table` (Task 3) and `@tanstack/react-virtual` (Tech Notes) as the recommended browse stack. However, `package.json` contains only:
- `@tauri-apps/api: ^2.10.1`
- `react: ^19.0.0`
- `react-dom: ^19.0.0`
- `react-window: ^2.2.7`

TanStack Table, TanStack Virtual, and shadcn/ui are absent.

**Why major:** The story's Tech Notes say "If @tanstack/react-table is adopted here..." implying it may be adopted. The dependency choice is significant (adds a non-trivial library to the stack) and should be explicitly decided and documented. The `react-window` dependency (already present) is a competing virtualization approach.

**Source:** `package.json`; story Tech Notes section.

**Recommended fix:** The story should either (a) explicitly install TanStack Table + TanStack Virtual as part of this story and update `package.json`, or (b) explicitly stay with react-window + native React controls, documented as the chosen approach. The current "if adopted" language leaves this as a runtime decision rather than a planned one.

---

#### M5: `backend/tests/api/test_customers_read.py` does not exist

**Finding:** The story references this file path in the Testing Requirements section, implying it will be created. However, `backend/tests/` contains only `__init__.py`. The file needs to be created as part of this story, but there is no explicit task for it in the task list (only backend API tests are mentioned in Task 4's bullets).

**Why major:** Test file creation is implied but not explicitly called out as a deliverable. This could be missed during sprint planning.

**Source:** `backend/tests/` directory inspection; story Task 4.

**Recommended fix:** Task 4's bullets should explicitly list the files to be created, matching the file list format used in the Dev Agent Record section. E.g., "Create `backend/tests/api/test_customers_read.py`" as part of the testing task.

---

### MINOR

#### m1: Summary fields in search results not defined

**Finding:** AC1 says "matching customers are returned with the summary fields needed to identify the right customer" but never specifies which fields. The wireframe shows: 統一編號, 公司名稱, 電話, 狀態, 帳餘. The story has no guidance on what summary fields to include.

**Why minor:** This is low-risk because the wireframe provides a clear reference, but the story should be explicit. A developer could implement a different field set and pass the AC ("summary fields needed to identify") without matching the wireframe.

**Recommended fix:** Add a note in Task 1 specifying the summary fields (e.g., "tax_id, company_name, phone, status at minimum; balance is deferred").

---

#### m2: Default sort order not defined

**Finding:** Task 2 says "Use a stable default sort order so repeated queries do not shuffle results between pages." It does not specify what the sort order should be (e.g., alphabetical by company name, most recently created, etc.).

**Why minor:** Stable sort is important for pagination correctness, but the actual sort key affects UX. The wireframe doesn't show a sort indicator.

**Recommended fix:** Specify the default sort (e.g., "company_name ASC NULLS LAST" or "created_at DESC") in the task description.

---

#### m3: AC2 detail lookup -- UI pattern not specified

**Finding:** AC2 says "when I open the selected result, then I can view the full customer record." The wireframe shows this as a Dialog (檢視/修改). The story's Task 3 lists `CustomerDetailDialog.tsx` as a component to create. However, the story doesn't specify whether this is a modal dialog, a separate page, or an inline expansion.

**Why minor:** The wireframe provides the reference, so this is low risk. But the story could be more explicit.

---

#### m4: No mention of debounced search input

**Finding:** Taiwan localization best practice (per UI/UX survey) calls for debounced real-time validation on tax ID input (300ms debounce after 8 digits entered). The story does not mention debouncing for the search bar, which is relevant for partial business-number search (AC1) where each keystroke would fire a query.

**Why minor:** Not adding debounce to search inputs can cause excessive API calls. This is an implementation detail that could be addressed in a frontend style guide rather than the story itself, but it is relevant to AC1's "search by partial" requirement.

---

## 3. Dependency Analysis

| Dependency | Story | Status relative to 3.1 |
|-----------|-------|----------------------|
| Story 3.2 (MOD11 validator) | Must implement first | Advisory only -- NOT formalized |
| Story 3.3 (Customer create/persist) | Must implement first | Advisory only -- NOT formalized |
| Story 3.4 (Duplicate flag) | Depends on this | Correctly identified |
| Story 8.2 (MCP customer retrieval) | Reuses this story's service | Correctly identified |
| FR16 (search by 統一編號/name) | Maps to this story | Correctly covered |
| FR50 (pagination/virtualization) | Maps to this story | Correctly covered |
| PRD Journey 2 (invoice creation) | Customer lookup step | Correctly covered |
| PRD Journey 4 (new order) | Customer lookup step | Correctly covered |

**Key dependency gap:** Stories 3.2 and 3.3 are called out as prerequisites in Dev Notes but are NOT formally declared as dependencies. The story's `Status: ready-for-dev` is inconsistent with this dependency reality.

---

## 4. Best Practices Compliance

### React Table Pagination/Virtualization
- **Compliant:** The story correctly states that bounded client-side pagination is acceptable for the dataset envelope, and that large in-DOM result sets require virtualization. The TanStack guidance (use `@tanstack/react-virtual` separately, TanStack Table alone is insufficient) matches current best practices.
- **Gap:** The mention of `@tanstack/react-table` in the story implies the team should install it, but it is not in `package.json`. `react-window` is present but its use for this purpose is not planned.

### Taiwan Business Number Search
- **Compliant:** The story correctly calls for normalization to canonical format, consistent with MOD11 validation in Story 3.2. The partial-match search requirement is appropriate for UX.
- **Gap:** No explicit note on whether partial business-number search uses prefix matching (e.g., `LIKE '1234%'`) or contains matching (`LIKE '%1234%'`). Prefix matching is significantly faster with standard indexes and more common in Taiwan business number UX. This should be specified.

### FastAPI Async Pagination
- **Compliant:** The story correctly specifies async service methods and explicit pagination parameters (`page`, `page_size`, `total_count`/`total_pages` or cursor/`has_next_page`). This matches FastAPI async best practices.
- **Gap:** The story mentions both offset pagination (`page`, `page_size`, `total_count`) and cursor pagination as acceptable alternatives but does not specify which to prefer. For 5,000+ row datasets with potential concurrent writes, cursor pagination is more stable. The story should express a preference or let the implementer choose but document the tradeoffs.

### Package Dependencies
- **Non-compliant:** `package.json` is missing TanStack Table, TanStack Virtual, and shadcn/ui components that the story references. `react-window` is present but its role is not specified. The story cannot be implemented as written without adding these dependencies or making an explicit "stay with react-window + native controls" decision.

---

## 5. Architecture Alignment

| Architecture Requirement | Story Coverage |
|------------------------|---------------|
| `GET /api/v1/customers` for filtered list | Covered (Task 1) |
| `GET /api/v1/customers/{customer_id}` for detail | Covered (Task 1) |
| Business-number exact-match lookup (REST) | Ambiguous -- see M1 |
| `customers.list` / `customers.get` MCP surface | Correctly deferred to Epic 8 (Story 8.2) but service contract is reusable |
| Multi-tenancy via `SET LOCAL app.tenant_id` | Correctly referenced (Tech Requirements) |
| `statement_cache_size=0` for PgBouncer | Correctly referenced (Tech Requirements) |
| Framework-neutral service methods | Correctly specified (Task 1) |
| Business number normalization (reuse Story 3.2 utility) | Correctly specified (Task 2) -- but depends on 3.2 |
| `asyncpg` for async database access | Correctly implied by architecture references |

---

## 6. Iteration 2 Disposition

| Finding | Iteration 1 Finding | Iteration 2 Status | Resolution |
|---------|---------------------|-------------------|-----------|
| C1: Dependency sequencing not formalized | New | **Confirmed** -- still unresolved | Add formal `depends on` block or re-sequence |
| C2: Backend empty -- "extend" misleading | New | **Confirmed** -- still unresolved | Update story to use "create" instead of "extend" for all backend/customer files |
| C3: Frontend empty -- same issue | New | **Confirmed** -- still unresolved | Same as C2 |
| M1: API design for tax_id lookup ambiguous | New | **Confirmed** -- still unresolved | Add explicit exact-match tax_id endpoint design |
| M2: "indexed search fields" qualifier in AC4 | New | **Confirmed** -- still unresolved | Make index creation explicit in AC4 |
| M3: Status filter not in ACs but in wireframe | New | **Confirmed** -- still unresolved | Either add AC for status filter or explicitly exclude and document |
| M4: TanStack not in package.json | New | **Confirmed** -- still unresolved | Explicitly install or explicitly choose react-window alternative |
| M5: test_customers_read.py not in task list | New | **Confirmed** -- still unresolved | Add explicit file creation to Task 4 |
| m1: Summary fields not defined | New | **Confirmed** -- minor | Add field list to Task 1 |
| m2: Default sort not defined | New | **Confirmed** -- minor | Add sort specification to Task 2 |
| m3: Detail lookup UI pattern | New | **Confirmed** -- minor | Clarify in Task 3 |
| m4: No debounce mention | New | **Confirmed** -- minor | Add to Task 3 or frontend style guide |

All 12 findings from Iteration 1 are confirmed in Iteration 2. No new issues were identified in Iteration 2.

---

## 7. Summary and Recommendation

### Status: `needs-revision`

Story 3.1 is well-structured and directionally correct. Its guardrails, scope exclusions, and technical notes show careful thinking about the Taiwan localization context, the MCP reuse story, and the TanStack/performance requirements. However, it has 5 major and 5 minor unresolved issues that prevent it from being ready for development:

**Must fix before development (Critical + Major):**
1. Formalize dependency on Stories 3.2 and 3.3 (C1)
2. Correct "extend" language to "create" for all non-existent backend/frontend files (C2, C3)
3. Define explicit exact-match tax_id lookup API endpoint (M1)
4. Make AC4's index requirement unambiguous (M2)
5. Decide on status filter scope (M3)
6. Resolve package dependency for table/virtualization stack (M4)
7. Explicitly list test files to be created (M5)

**Should fix for quality (Minor):**
8. Define summary fields for search results (m1)
9. Define default sort order (m2)
10. Specify detail dialog vs. page pattern (m3)
11. Add debounce guidance for search inputs (m4)

**Confirmed positive aspects (no change needed):**
- All 4 ACs are testable and unambiguous in their Given/When/Then structure
- Scope exclusions (no create/update, no balance fabrication, no status transitions) are correct and well-documented
- TanStack guidance (separate virtualization library required) is accurate
- Multi-tenancy and PgBouncer notes are correct
- Dependency ordering notes for 3.4 and 8.2 are correct
- Journey 2 and Journey 4 coverage is correctly identified

### Recommended Path Forward

1. **Re-baseline after Stories 3.2 and 3.3 are complete.** Story 3.1 should not start development until the customer model from 3.3 exists and the MOD11 validator from 3.2 is available for reuse.
2. **Add a formal "depends on" block** at the top of the story listing Stories 3.2 and 3.3 as blocking dependencies.
3. **Update all file path references** to distinguish files being created from files being extended.
4. **Resolve M1 (tax_id lookup API)** before dev starts -- this is a core API design decision.
5. **Resolve M4 (package dependencies)** in the Tech Notes -- explicitly decide on TanStack Table + Virtual vs. react-window + native controls.
6. **Add scope note on status filter** -- explicitly exclude or include it.
