# Epic 5 — Round 2 Validation Summary (Post-Fix)

**Date:** 2026-04-02
**Context:** Stories were updated after Round 1 validation. This report re-checks all issues against the updated stories.
**Validator count:** 5 parallel agents, 4 iterations each

---

## Net Assessment: Progress Made, Issues Remain

The fixes addressed some issues but left others unfixed, and in some cases introduced new inconsistencies. **Epic 5 is still not ready-for-dev** — the foundational orders domain (Story 5.1) has zero implementation.

---

## Cross-Cutting Issues (Unresolved)

### 🚨 Migration Chain — Still Unresolved (All Stories)

The migration branching issue from Round 1 remains completely unaddressed in all Epic 5 stories.

**Evidence:** Analysis of actual migrations confirms two existing heads (`ee5b6cc6d7e8` and `hh888jj88k10`). The story's migration `ii999kk99l21` with `down_revision = hh888jj88k10` creates a **third head** with no Alembic branching guidance.

**Impact:** `alembic upgrade head` will apply only one branch. The orders tables migration would be missed unless the developer explicitly handles branching.

---

### 🚨 Orders Domain — Still Zero Implementation (All Stories)

Every Epic 5 story references `backend/domains/orders/` and `src/domain/orders/` that do not exist. No code has been written for Story 5.1. All stories remain spec-only.

---

## Per-Story Round 2 Results

### Story 5.1 — PARTIALLY FIXED

| Issue | Round 1 | Round 2 | Status |
|-------|---------|---------|--------|
| Migration chain branching | CRITICAL | CRITICAL | STILL BROKEN |
| `actor_type` explicit | CRITICAL | CRITICAL | STILL BROKEN |
| Collision retry | WARNING | WARNING | STILL BROKEN (no guidance added) |
| `actor_id` value | WARNING | WARNING | NEW: pattern inconsistency found |

**What was fixed:** None of the 3 critical issues were addressed.
**What got worse:** New issue identified — `create_order()` hardcodes `actor_id` rather than passing it as a parameter (inconsistent with inventory pattern).
**What remained partial:** Collision retry mentioned but no implementation guidance.

---

### Story 5.2 — NO FIXES APPLIED

| Issue | Round 1 | Round 2 | Status |
|-------|---------|---------|--------|
| Orders domain non-existent | CRITICAL | CRITICAL | STILL BROKEN |
| Stock check in wrong domain | CRITICAL | CRITICAL | STILL BROKEN |
| Schema field name mismatch | CRITICAL | CRITICAL | STILL BROKEN |

Story 5.2 was not in the modified set — all 3 critical issues remain.
**Recommendation:** Move stock check endpoint to `inventory` domain (`GET /api/v1/inventory/stock-availability/{product_id}`) to maintain domain cohesion.

---

### Story 5.3 — PARTIALLY FIXED, NEW INCONSISTENCY

| Issue | Round 1 | Round 2 | Status |
|-------|---------|---------|--------|
| AC4 order immutability | CRITICAL | — | FIXED (note added) |
| Dev Notes NFR21 claim | WARNING | NEW CRITICAL | INTRODUCED CONTRADICTION |
| ReasonCode path wrong | CRITICAL | CRITICAL | STILL BROKEN |
| Story 5.1 "scaffolded" | CRITICAL | CRITICAL | STILL BROKEN |

**What was fixed:** AC4 now clarifies "order STATUS changes via Story 5.5 are still allowed" ✅

**What got worse:** Dev Notes line 88 was NOT updated — it still says:
> "Orders cannot be modified after creation — matching the invoice immutability pattern (NFR21)"

This directly contradicts the AC4 fix and Story 5.5's state machine. The story is now **internally inconsistent** — AC4 says orders are mutable through status transitions, Dev Notes says they're immutable like invoices.

**What remains broken:** ReasonCode enum reference still points to wrong file path (`domains/inventory/schemas.py` instead of `common/models/stock_adjustment.py`).

---

### Story 5.4 — OPTION A IS PRESCRIPTION, NOT CODE

| Issue | Round 1 | Round 2 | Status |
|-------|---------|---------|--------|
| Nested `session.begin()` | CRITICAL | CRITICAL | STILL BROKEN — `_create_invoice_core()` doesn't exist |
| `buyer_type` comment | CRITICAL | CRITICAL | STILL BROKEN — comment still says "from customer" |

**What was fixed:** The story correctly identified the nested transaction problem and proposed Option A (extract `_create_invoice_core()`). ✅

**What is still broken:**
- `_create_invoice_core()` does NOT exist in `backend/domains/invoices/service.py`. Option A is a **prescription to create new code**, not a description of existing code. The story does not acknowledge this is a pre-requisite refactoring of the invoice service.
- The comment at line 159 `# BuyerType from customer` is **actively false** — the value is hardcoded to `BuyerType.B2B`, not sourced from customer. The comment misleads developers.

**New issues found:**
- `Invoice.order_id` field does not exist in the model — story describes it as a modification but it's a net-new addition
- Migration `jj000ll00m32` doesn't exist and has no orders migration to chain from

---

### Story 5.5 — INTERNAL INCONSISTENCY RESOLVED, UPSTREAM BLOCKED

| Issue | Round 1 | Round 2 | Status |
|-------|---------|---------|--------|
| `session.begin()` in Task 1 Items 3 vs 4 | WARNING | — | NOT ACTUALLY INCONSISTENT |
| `confirm_order()` / `_create_invoice_core()` exist | CRITICAL | CRITICAL | STILL BROKEN (upstream) |
| `frozenset` vs `set` | WARNING | — | ACCEPTED (intentional improvement) |

**What was fixed:** The apparent `session.begin()` inconsistency was a false alarm — Items 3 and 4 describe two separate code paths with explicit notes. ✅

**What remains broken:** All upstream dependencies on unimplemented Stories 5.1 and 5.4.

**New issue found:** `update_order_status()` uses `async with session.begin():` internally, but the cited reference `update_supplier_order_status()` does NOT — it relies on the caller. The Dev Note's "same pattern" citation is imprecise.

---

## Round 2 Summary Table

| Story | Critical Fixed | Critical Remaining | New Issues | Ready for Dev? |
|-------|---------------|-------------------|------------|----------------|
| 5.1 | 0 | 2 | 1 | NO |
| 5.2 | 0 | 3 | 0 | NO |
| 5.3 | 1 (AC4) | 2 | 1 (Dev Notes contradiction) | NO |
| 5.4 | 0 | 2 | 2 | NO |
| 5.5 | 0 | 0 (upstream) | 1 | NO |

**Net: 1 critical fixed, ~10 critical/warnings still present across stories.**

---

## Required Fixes Before Dev

### Must Fix (will break implementation)

| Story | Fix Required |
|-------|-------------|
| 5.1 | Add Alembic branching guidance for migration chain OR use sequential ID; add explicit `actor_type="user"` to AuditLog; add collision retry implementation guidance |
| 5.2 | Move stock check endpoint to inventory domain; fix schema field name `available` → `current_stock` |
| 5.3 | Update Dev Notes line 88 to remove NFR21/immutability claim; fix ReasonCode reference path to `common/models/stock_adjustment.py` |
| 5.4 | Acknowledge `_create_invoice_core()` must be extracted as a pre-requisite; remove/fix misleading `buyer_type` comment |
| 5.5 | Fix "same pattern" citation — `update_supplier_order_status()` does NOT use `session.begin()` internally |

### Required First (dependency)

| Priority | Action |
|----------|--------|
| **FIRST** | Implement Story 5.1 (creates orders domain, unblocks all other stories) |
| **SECOND** | Implement Story 5.4 `_create_invoice_core()` extraction as a pre-requisite before 5.4 dev |

---

## What the Fixes Got Right

The following were genuinely improved in Round 1:
- Story 5.3 AC4 clarification about status transitions ✅
- Story 5.4 Option A/B framing for nested transaction ✅
- Story 5.5 Item 4 note about `confirm_order()` transaction management ✅
- Story 5.5 `frozenset` choice (intentional improvement over reference) ✅

These improvements show the stories are being actively refined. The remaining issues are specific enough to be actionable.
