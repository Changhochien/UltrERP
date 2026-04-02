# Story 3.3 Validation Report

**Story:** 3.3 Create Customer Record
**Validator:** Claude Code (multi-iteration validation)
**Date:** 2026-04-01
**Status:** Needs revision before dev

---

## Iteration 1 Findings

### Sources Reviewed

| Source | Key Findings Relevant to Story 3.3 |
|--------|-------------------------------------|
| `prd.md` | FR18 (create customer with tax ID, address, contact, credit limit), FR17 (MOD11 validation), FR19 (duplicate flag) |
| Architecture v2 | Section 4.2 modular monolith pattern, `/api/v1/customers` mount, `tenant_id` requirement, asyncpg `statement_cache_size=0` |
| `epics.md` | Epic 3 story descriptions, story sequencing: 3.2 before 3.3 before 3.1 |
| `01-survey-memo.md` | Taiwan phone formats (09xx-xxx-xxx, 0X-xxxx-xxxx, +886), MOD11 real-time validation UX, Radix/shadcn stability risks |
| `01-customer-management.md` | shadcn/ui components, table virtualization, keyboard shortcuts |
| `backend/common/database.py` | AsyncSessionLocal already configured, `statement_cache_size=0` already set |
| `backend/app/deps.py` | `db_session` dependency uses simple generator pattern (no FastAPI `Depends` yield pattern) |
| `backend/common/errors.py` | `ApplicationError` is a bare stub - no structured error fields |
| `package.json` | React 19, no form framework, no routing, no Tailwind, no shadcn/ui |

---

## Iteration 2 Findings (Confirmation Round)

### AC4 Sequencing Problem — Confirmed Issue

AC4 states: "when the create flow finishes, then the created record is immediately retrievable through the customer read APIs and UI."

Story 3.1 (Search and Browse Customers) implements the read/browse APIs. Per `epics.md` story order, Story 3.3 precedes Story 3.1. This means when Story 3.3 ships, there are NO customer read APIs yet. The story cannot satisfy its own AC4 until Story 3.1 exists.

**Fix required:** Either (a) AC4 should be reframed as "I receive confirmation with the created customer ID and the record exists in the database" (matching what this story actually delivers), or (b) Story 3.1 must be reordered before 3.3 (breaking the 3.2 → 3.3 → 3.1 sequencing in the epic).

### Frontend Stack Decision — Process Is Clear, Outcome Is Not

Task 0 requires choosing between two paths before UI work starts. This is the correct approach. However:

- package.json has zero form/routing libraries installed
- `src/App.tsx` is a bare single-page shell with no routing
- The "shared form stack" does not exist

The decision process described in Task 0 is sound, but Task 0 itself creates risk: if the team delays choosing the form stack, Story 3.3 (and Stories 3.1/3.5) all stall. The story should add a gate: "Task 0 must be completed and merged before any UI subtask begins."

### Structured Error Response Pattern — Missing

`common/errors.py` contains only `class ApplicationError(Exception): pass` — a bare stub. FastAPI's default HTTPException returns JSON, but there is no application-wide structured error response format defined. This means:

- Validation errors from the service layer have no guaranteed shape
- Frontend cannot reliably parse error messages
- Each developer will invent ad-hoc error shapes

The architecture spec does not prescribe an error response schema, so this is an implementation gap to fill in Story 3.3 (not a story defect).

### Tenant Context Pattern — Needs Implementation Detail

The dev notes state: "Follow the architecture's request-scoped tenant context pattern, including `SET LOCAL app.tenant_id` or the repo's equivalent helper." But:

- `backend/app/deps.py` has `db_session` but no tenant context setup
- `SET LOCAL app.tenant_id` requires `ALTER DATABASE` setup or a per-session trigger
- There is no `set_tenant_context()` helper in the existing codebase

This is architecture debt that Story 3.3 will expose. The dev notes correctly flag it, but Task 1 should include creating or using a tenant helper, not just mention it in dev notes.

### Unique Constraint Planning — Adequate

The dev notes mention: "Create the schema/migration in a way Story 3.4 can later enforce a unique constraint on normalized business number without redesigning the table." This is appropriate. Story 3.4 owns the unique constraint; Story 3.3 must only design the table so it can be added cleanly.

### Taiwan Phone Validation — Scope Ambiguity

The dev notes list three formats to accept, but:
- Task 2 says "Validate required fields, Taiwan-localized contact formats" in the service layer
- Task 3 (UI) makes no mention of phone formatting
- The UX research memo recommends real-time MOD11 feedback but says nothing about phone real-time validation

There is no task explicitly owning the phone regex/format validation implementation. If phone validation is in scope (per AC3), it needs an explicit task subtask.

### API Client Layer — Not Planned

`src/lib/api/customers.ts` is listed as a file to create in Task 3, but there is no infrastructure for:
- Typed API responses
- Error parsing from the backend
- Integration with the form submission flow

Given the bare-metal state of the frontend, this is acceptable as a first pass, but the story should note that error handling from the API client needs to be wired to react-hook-form or the chosen form stack.

---

## Validation Checklist

### Completeness

| AC | Description | Status | Notes |
|----|-------------|--------|-------|
| AC1 | All 7 fields saved to DB | OK | Covered by Tasks 1-3 |
| AC2 | tenant_id set + confirmation with ID | OK | Covered by Task 2 |
| AC3 | Validation errors for invalid input | OK | Covered by Task 2 |
| AC4 | Immediately retrievable via read APIs | **PROBLEM** | Read APIs don't exist yet (Story 3.1 is after 3.3) |

**Subtasks completeness:** Tasks 1-4 fully cover ACs 1-3. AC4 is a sequencing issue, not a coverage gap.

### Consistency

| Check | Status |
|-------|--------|
| Title and narrative match PRD FR18 | OK |
| MOD11 validation delegated to Story 3.2 | OK |
| Mount path `/api/v1/customers` matches architecture section 4.2 | OK |
| `tenant_id` included as required by architecture NFR31 | OK |
| Decimal/NUMERIC for credit_limit (not float) | OK |
| `status` column defaulting to active, no lifecycle in Epic 3 | OK |
| Exclusion of disable/delete/AR-balance correct | OK |

### Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Story 3.2 must be done first | OK | Clearly stated in dev notes |
| Task 0 frontend foundation before UI work | OK in intent, **needs gate** | Task 0 completion should gate UI subtasks |
| Story 3.1 (browse) after this story | **Causes AC4 issue** | AC4 requires read APIs that don't exist yet |

### Technical Soundness

| Pattern | Status | Notes |
|---------|--------|-------|
| AsyncSessionLocal + expire_on_commit=False | OK | Already in database.py |
| statement_cache_size=0 | OK | Already in database.py |
| SET LOCAL app.tenant_id | **Debt** | Helper doesn't exist yet; architecture debt |
| Decimal/NUMERIC for credit_limit | OK | Explicitly stated in Task 1 |
| POST /api/v1/customers schemas | OK | In Task 2 |
| Service-layer validation | OK | In Task 2 |
| Single-transaction persistence | OK | In Task 2 |
| Unique constraint design for future Story 3.4 | OK | Mentioned in dev notes |

### Frontend Stack Decision

| Check | Status | Notes |
|-------|--------|-------|
| Decision process clear (Task 0) | OK | Two-path choice with preparatory commit |
| No unplanned form library mixing | OK | Story correctly warns against this |
| Routing-free screen switch pattern | OK | In Task 0 and dev notes |
| API client infrastructure | **Partial** | File listed but no error handling pattern planned |

### Scope Guardrails

| Exclusion | Status |
|-----------|--------|
| No edit/disable/delete | OK |
| No AR balance field | OK |
| No credit-limit enforcement against orders | OK |
| No duplicate resolution UX beyond DB constraint | OK |
| Disable/soft-delete not in this story | OK |

### Best Practices

| Area | Assessment |
|------|------------|
| FastAPI async SQLAlchemy session management | Solid — follows Context7 best practices |
| SQLAlchemy 2.0 async patterns | Solid — uses AsyncSessionLocal |
| React Hook Form + Zod | Best practice for React 19 forms; should be the chosen path |
| Phone format validation | Scope ambiguous — no explicit task subtask for regex |
| Email validation | Conservative RFC-5322 subset — acceptable |
| API structured error responses | **Missing** — `ApplicationError` is a stub |
| Tenant context helper | **Missing** — needs to be built in Task 1 |
| Rollback handling if validator call fails | **Missing** — Task 2 should handle this |

---

## Issues by Severity

### SEV-1: AC4 Cannot Be Met (Sequencing Gap)

**Problem:** AC4 requires "the created record is immediately retrievable through the customer read APIs and UI." Story 3.1 (which implements those read APIs) is sequenced after Story 3.3 in the epic. When Story 3.3 ships, no customer read API exists.

**Evidence:** `epics.md` story order within Epic 3: 3.1 (browse/search) comes after 3.3 (create). AC4 in the story text requires retrievability through "customer read APIs and UI."

**Fix:** Change AC4 language to: "Given the customer is saved, when persistence succeeds, then the system returns the created customer ID and the record is present in the database." OR reorder Stories 3.1 and 3.3 in the epic (but this may break Journey 2/4 assumptions which say browse/read must work on created customers).

### SEV-2: Structured Error Response Pattern Missing

**Problem:** `common/errors.py` has only `class ApplicationError(Exception): pass` — no fields, no subclasses, no Pydantic model for error responses. FastAPI will return default HTTPException JSON. The frontend cannot reliably parse consistent error shapes.

**Fix:** In Task 2, add a structured error response model (e.g., `CustomerCreateError` with fields: `code`, `message`, `details: dict`) and use it in the service layer instead of raw HTTPExceptions.

### SEV-1: Tenant Context Helper Does Not Exist

**Problem:** The dev notes say to use `SET LOCAL app.tenant_id` or "the repo's equivalent helper." The helper does not exist in `backend/common/`. `backend/app/deps.py` has no tenant setup.

**Fix:** Task 1 should explicitly include creating a `set_tenant_context(session, tenant_id)` helper or equivalent, not just mention it in dev notes.

### SEV-3: Phone Validation Not Explicitly Tasked

**Problem:** AC3 and the dev notes reference phone validation for Taiwan formats, but no Task 2 subtask explicitly calls out the phone regex/validation logic. It's implied by "Taiwan-localized contact formats" but not called out as a specific deliverable.

**Fix:** Add a subtask to Task 2: "Implement phone number format validation for Taiwan formats: mobile (09xx-xxx-xxx), landline (0X-xxxx-xxxx), and international (+886)."

### SEV-3: Task 0 Needs a Hard Gate

**Problem:** Task 0 is the frontend foundation decision. If the team does not complete it before UI work starts in Task 3, Story 3.3 will stall (and Stories 3.1 and 3.5 are blocked too). The story currently treats Task 0 as "do this first" but has no enforcement mechanism.

**Fix:** Add a note to Task 0: "This task must be completed and merged (if adding libraries) before any UI subtasks in Task 3 or parallel stories begin their UI work."

### SEV-3: Rollback Handling Not Specified

**Problem:** Task 2 calls the Story 3.2 validator before persistence. If the validator call fails (network error, not validation failure), there is no explicit rollback or error handling described.

**Fix:** Task 2 should explicitly handle the case where the validator call raises an exception, ensuring the transaction is rolled back and a meaningful error is returned.

---

## Recommended Fixes (Priority Order)

1. **Revise AC4** to remove the "read APIs" requirement (which belongs to Story 3.1), changing it to: "the system returns the created customer ID and the record is persisted in the database."

2. **Add structured error response model** in `common/errors.py` as part of Task 1 or Task 2. At minimum: a `CustomerCreateError` Pydantic model with `code`, `message`, and `field` fields.

3. **Add tenant context helper** to Task 1's scope: create `backend/common/tenant.py` with `set_tenant_context()` or equivalent, used in the service layer before queries.

4. **Add phone validation as explicit subtask** in Task 2: implement Taiwan phone format regex for the three approved formats.

5. **Add Task 0 gate note** clarifying that its completion must precede any UI work in the epic.

6. **Add rollback/exception handling** to Task 2 service behavior description for validator call failures.

---

## Overall Status

**Status: Needs revision before dev**

The story is 80% solid. The core backend (models, schemas, service, routes) and the frontend structure are well-defined. The dependency on Story 3.2 is correctly managed, the scope exclusions are appropriate, and the architecture requirements are correctly identified. The technical patterns (async SQLAlchemy, Decimal for credit_limit, tenant_id) are sound.

The three blocking issues are:
1. AC4's reliance on Story 3.1's read APIs (which don't exist yet when 3.3 ships)
2. Missing structured error response infrastructure
3. Tenant context helper not existing in the codebase

The remaining issues (phone validation specificity, Task 0 gate, rollback handling) are sev-3 and can be addressed in implementation.

---

*Report generated by Claude Code multi-iteration validation. Iteration 1: document review + web search. Iteration 2: confirmation against codebase and cross-reference check.*
