# Story 3.4 Validation Report: Flag Duplicate Business Number

## Validation Summary

**Story:** 3.4 Flag Duplicate Business Number
**Status:** CONDITIONALLY READY — 4 issues require resolution before dev handoff
**Severity breakdown:** 2 medium issues, 2 low issues, multiple confirmed strengths

---

## ITERATION 1 FINDINGS

### 1. Completeness: AC Coverage

All 5 ACs are present and testable. Tasks map cleanly to ACs:
- Task 1 → AC1, AC2, AC4 (service-layer pre-check)
- Task 2 → AC3 (DB constraint)
- Task 3 → AC1, AC2, AC4 (API + UI wiring)
- Task 4 → AC1, AC2, AC3, AC4 (tests)

**Gap (Iteration 2 confirmed):** AC5 ("mirrors the optimistic duplicate response shape") is not explicitly mapped to a task. Task 4 mentions "concurrent insert race maps to the same domain error" but does not verify shape equivalence between the two error paths. This is a test completeness gap.

### 2. Consistency: PRD Alignment

FR19 (from PRD) states: "System flags duplicate 統一編號 on customer create."

Story 3.4 fulfills FR19 with:
- AC1: clear duplicate warning with existing customer name
- AC2: normal create flow is blocked until cancel or choose existing
- AC4: stable error contract linking back to existing record

This is fully consistent. The "blocked until cancel or choose existing" wording in AC2 is more restrictive than FR19's "flags" but correctly implements the story's own goal stated in Dev Notes: prevent conflicting masters rather than merely acknowledging duplicates.

### 3. Consistency: Story 3-3 and 3-5

**Story 3-3 (Create Customer):**
- Establishes the customer aggregate, schemas, and POST endpoint
- Dev Notes explicitly defer duplicate handling to Story 3.4: "Do not implement duplicate-resolution UX here beyond the minimum persistence constraint needed to protect the table."
- Story 3.4 Task 3 correctly extends `routes.py` and the create form from 3-3 rather than replacing them
- Consistent: 3-4 builds on 3-3 correctly

**Story 3-5 (Update Customer):**
- AC2 of 3-5 states: "Given the business number changes, when the save is attempted, then the system re-runs Story 3.2 checksum validation and Story 3.4 duplicate detection before persisting."
- Dev Notes of 3.4 correctly list 3.5 as a dependent: "Story 3.5 must reuse this duplicate behavior when a user edits an existing customer's business number."
- Consistent: the dependency chain 3-3 → 3-4 → 3-5 is sound

### 4. Consistency: Architecture

Architecture spec (v2) defines MCP tools `customers.create` and `customers.update` but does not detail duplicate handling. Story 3.4 correctly fills this gap. The architecture's FastAPI modular monolith pattern (sub-apps at `/api/v1/customers`) is followed by the story's file targets.

Architecture requires `tenant_id` on all tenant-owned tables and `SET LOCAL app.tenant_id` before queries. The story mentions this in Technical Requirements and Dev Notes. Confirmed present and correct.

### 5. Race Condition Analysis (AC3 + AC5)

**The dual-layer approach is sound.** This was validated against PostgreSQL concurrency patterns.

The service-layer pre-check (SELECT for duplicate) + DB unique constraint pattern is the industry-standard approach for this problem. The pre-check provides a user-friendly response with existing customer metadata. The DB constraint is the authoritative enforcement that handles the TOCTOU race.

**Key concurrency insight (from PostgreSQL research):** When two concurrent requests both pass the service pre-check and both attempt INSERT, PostgreSQL's unique constraint guarantee means only one succeeds. The loser hits the constraint violation. Under `READ COMMITTED` isolation (PostgreSQL default), the constraint violation error fires immediately when the second transaction tries to commit its insert, even if the first transaction hasn't committed yet.

**AC5 concern (Iteration 2 resolved):** The requirement that the DB-constraint error "mirrors the optimistic duplicate response shape" is achievable but requires an explicit post-catch query: on `IntegrityError`, the service must query the DB for the conflicting customer record using the business number, then return the same metadata shape. The story does not explicitly describe this pattern in tasks, which is an omission but not a blocker.

**AC3 note:** The unique constraint must be composite `(tenant_id, normalized_business_number)` not just `(business_number)` alone, otherwise cross-tenant isolation is violated. This is implied by the tenant context requirement but not made explicit in the constraint description.

### 6. Error Contract (AC4 + AC5)

**AC4** requires the error contract includes existing customer ID, name, and business number. The story's Technical Requirements section confirms: "Return a stable duplicate response shape that includes at least the existing customer ID, existing customer name, and the normalized business number."

**Gap (Iteration 2 confirmed):** The exact API response schema (HTTP status code, JSON body structure) is described in prose but not formally specified. Specifically:
- HTTP status code: The story mentions "409-style duplicate response" but never explicitly specifies `409 Conflict` (which matches REST convention for duplicate resource creation)
- JSON body fields: Only described as "at least" the three fields, no formal schema

This is a gap but acceptable for `ready-for-dev` — API schema definition typically happens during implementation.

### 7. Scope: No "Force Create" Path

The scope guardrail "Do not allow a 'force create anyway' path" is **correct and well-reasoned.**

Rationale: The story's goal is preventing conflicting customer masters. A force-create option would undermine this invariant. The business goal (Journey 2 and Journey 4 both assume one canonical customer per business number) requires blocking duplicates, not flagging them.

**Edge case not addressed:** What if a legitimate business legitimately has multiple distinct customer records that happen to share a business number? In Taiwan, a single business number (統一編號) uniquely identifies a business entity. There is no legitimate case for duplicates. This confirms the "no force create" decision is correct.

**Legacy data risk** is appropriately deferred to data migration work (Risks / Open Questions section).

### 8. Dependencies and Sequencing

| Story | Relationship |
|-------|-------------|
| 3-2 (normalization) | Hard prerequisite — 3.4 reuses normalization rules |
| 3-3 (create customer) | Must exist first — 3.4 extends the create flow |
| 3-1 (browse/detail) | Must exist first — duplicate warning must link to browse/detail destination |
| 3-5 (update customer) | Depends on 3.4 — reuses duplicate detection on business number change |

The sequencing stated in Dev Notes is correct. All dependencies are logical, not arbitrary.

### 9. TOCTOU Assessment

**Pre-check (service SELECT) is vulnerable to TOCTOU by design.** Two concurrent requests can both pass the pre-check before either inserts. This is why AC3 explicitly requires the DB constraint as the authoritative backstop.

**No additional TOCTOU vulnerability** in the dual-layer design when implemented correctly with the DB constraint as the final arbiter.

**One subtle concern (Iteration 2 partially resolved):** The story does not specify whether the pre-check and the INSERT should be in the same transaction. If they are, and the transaction rolls back after INSERT failure on constraint, the pre-check's query results remain valid for the error response. If they are separate transactions, there is a theoretical edge case where the conflicting record is deleted between the constraint failure and the post-catch query. This is extremely unlikely in practice and acceptable to ignore.

### 10. Best Practices: Optimistic Pre-check vs. DB Constraint

The dual-layer pattern (optimistic pre-check + DB constraint) is **the correct pattern** for this use case, not optimistic locking.

Reason: Optimistic locking (version columns) is designed for update conflicts on the *same* entity. Here, the conflict is between *two different entities* attempting to share the same business number. A version column on the customer record does not help — the conflict is that two *different* customers both want to use the same business number. Database unique constraint is the only correct authoritative mechanism.

**Alternative considered and rejected:** `SELECT FOR UPDATE` on the pre-check would serialize all create requests for the same business number, creating unnecessary contention. The "optimistic pre-check with DB constraint backstop" is superior because it provides a friendly UX path (pre-check hit → rich error with metadata) while only falling back to serialization on the rare concurrent race.

---

## ITERATION 2 CONFIRMATION

All Iteration 1 findings were reviewed against the source documents. Confirmed:

1. AC5 test gap is real but minor — task description mentions "concurrent insert race maps to the same domain error" but does not explicitly verify shape equivalence
2. Error contract lacks formal schema but this is acceptable for story-level spec
3. Composite unique constraint `(tenant_id, normalized_business_number)` is implied but not stated — should be explicit
4. No specification of `IntegrityError` catch-and-map in SQLAlchemy — this is implicit implementation detail but worth a note
5. No force-create decision is definitively correct

---

## FINAL REPORT

### Status: CONDITIONALLY READY FOR DEV

The story is well-structured and the dual-layer approach is technically sound. Four items require either a fix or explicit acknowledgment before development begins.

---

### Confirmed Strengths

| Area | Finding |
|------|---------|
| AC completeness | All 5 ACs present and individually testable |
| PRD alignment | Fully satisfies FR19 duplicate-flagging requirement |
| Story 3-3 consistency | Correctly extends create flow without replacing it |
| Story 3-5 consistency | Correctly establishes duplicate contract that update will reuse |
| Architecture alignment | Follows modular monolith pattern, tenant context, FastAPI sub-app mounting |
| Race condition design | Dual-layer (pre-check + DB constraint) is the industry-correct pattern for this problem |
| Scope decision | "No force create" is the right call for a master-data integrity goal |
| Sequencing | Dependencies with 3-1, 3-2, 3-3, and 3-5 are all logical and correct |
| TOCTOU | No additional vulnerabilities beyond the inherent pre-check race, which AC3 explicitly addresses |
| Best practice | Optimistic pre-check + DB constraint backstop is superior to pessimistic locking for this use case |

---

### Issues

#### Issue 1: AC5 is not explicitly covered by any task

**Severity:** Medium
**Category:** Completeness

**Description:** AC5 states that when the DB constraint fires instead of the pre-check, the error response "mirrors the optimistic duplicate response shape." Task 4 (tests) mentions "concurrent insert race maps to the same domain error" but does not describe verifying that the *response payload shape* is identical between the two paths. The test requirement listed in Testing Requirements mentions "API duplicate response shape is stable" but this only covers one path.

**Recommended fix:** Add an explicit test sub-task or test case that sends two concurrent POST requests with the same business number, catches the second one's 409 response, and asserts that its body contains `existing_customer_id`, `existing_customer_name`, and `business_number` matching the same fields returned by a non-concurrent pre-check hit.

**Recommended fix text:**
> Task 4: Add duplicate-handling tests (AC: 1, 2, 3, 4, **5**)
> ...
> - Add a test that races two simultaneous create requests and asserts the losing request's 409 response body contains the same `existing_customer_id`, `existing_customer_name`, and `business_number` fields as a non-raced pre-check hit response

---

#### Issue 2: Unique constraint must be composite (tenant_id, normalized_business_number)

**Severity:** Medium
**Category:** Correctness

**Description:** The story specifies "a unique constraint and supporting index on the normalized business-number column" (Task 2). In a multi-tenant system, the constraint must include `tenant_id` to prevent cross-tenant false positives. If tenant A creates a customer with business number "12345678" and tenant B also creates a customer with "12345678", a unique constraint on `(business_number)` alone would incorrectly reject tenant B's create.

The tenant context requirement is present in the Dev Notes and Technical Requirements, but the constraint specification omits `(tenant_id, normalized_business_number)`.

**Recommended fix:** Update Task 2 to read:
> Add or confirm a **composite** unique constraint on `(tenant_id, normalized_business_number)` and supporting index on the normalized business-number column.

---

#### Issue 3: Error response schema is informal, not formally specified

**Severity:** Low
**Category:** API Contract

**Description:** AC4 requires a "stable error contract" with existing customer ID, name, and business number. The story's Technical Requirements section describes this in prose: "Return a stable duplicate response shape that includes at least the existing customer ID, existing customer name, and the normalized business number." However, there is no formal schema definition.

This is acceptable for a story-level spec, but if the team uses this story directly as an API contract, the informal description could lead to inconsistent implementations.

**Recommended fix:** Either:
- (a) Accept as-is and let the API schema be defined during implementation (acceptable for this stage), or
- (b) Add a brief schema block to the Technical Requirements:
  ```json
  {
    "error": "duplicate_business_number",
    "message": "A customer with this business number already exists",
    "existing_customer_id": "<uuid>",
    "existing_customer_name": "<string>",
    "business_number": "<normalized string>",
    "link": "/api/v1/customers/<existing_customer_id>"
  }
  ```

---

#### Issue 4: No explicit guidance on IntegrityError mapping

**Severity:** Low
**Category:** Implementation Clarity

**Description:** Task 2 says: "Map database-level uniqueness violations to the same domain/API error used by the optimistic duplicate pre-check." This describes the *what* but not the *how*. In SQLAlchemy + asyncpg, a unique constraint violation raises `sqlalchemy.exc.IntegrityError`. The service layer must catch this, query for the conflicting record (to get the metadata), then raise the same `DuplicateCustomerBusinessNumberError`.

The story does not specify:
- Whether to query the DB after catching the IntegrityError to get the metadata for the error response (necessary for AC5)
- The transaction isolation level to use

**Recommended fix:** Add to Task 2:
> On `IntegrityError`, query for the existing customer row by normalized business number (within the same failed transaction or a new query) to populate the error metadata, ensuring AC5's shape-mirroring requirement is met.

---

## Validation Checklist

| Criterion | Status | Notes |
|-----------|--------|-------|
| All 5 ACs testable | Pass | AC1-4 clearly testable; AC5 has test coverage gap |
| Story aligns with PRD (FR19) | Pass | Fully satisfies flag-duplicate requirement |
| Story aligns with 3-3 (create) | Pass | Extends without replacing |
| Story aligns with 3-5 (update) | Pass | Establishes contract for update to reuse |
| Dual-layer race approach sound | Pass | Pre-check + DB constraint is correct pattern |
| AC3/AC5 concurrent requests addressed | Pass | DB constraint is authoritative backstop |
| Error contract defined | Partial | Prose description exists; formal schema absent |
| AC5 shape-mirror testable | Fail | Not explicitly covered by any task |
| No "force create" — right call | Pass | Correct for master data integrity |
| Scope (exact match only) appropriate | Pass | Fuzzy matching correctly deferred |
| Dependencies correctly sequenced | Pass | 3-2, 3-3, 3-1 all prerequisites |
| TOCTOU handled appropriately | Pass | No additional vulnerabilities |
| Best practice (optimistic + DB constraint) | Pass | Correct choice over pessimistic locking |
| Composite unique constraint specified | Fail | Missing `tenant_id` in constraint spec |

---

## Recommendation

**Proceed to development with the following pre-dev amendments:**

1. Add explicit AC5 shape-mirror test case to Task 4
2. Update Task 2 constraint description to specify composite `(tenant_id, normalized_business_number)` unique index
3. Add brief IntegrityError mapping note to Task 2 implementation guidance
4. Consider adding informal JSON schema to Technical Requirements for the 409 response body (optional — acceptable to defer to implementation)

With these amendments, the story provides sufficient guidance for development. The core design is sound and the dual-layer approach will handle concurrent duplicates correctly.
