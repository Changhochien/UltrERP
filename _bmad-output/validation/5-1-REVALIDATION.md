# Story 5.1 Re-Validation Report

**Story:** Create Order Linked to Customer
**Revalidation Date:** 2026-04-01
**Prior Validation Found:** 4 issues

---

## Issue-by-Issue Assessment

### Issue 1: Migration Chain Branching

**Status: STILL BROKEN**

**Prior Finding:** `hh888jj88k10` is already HEAD — story uses it as down_revision creating a branch

**Current Status:** The migration chain analysis confirms there are **TWO heads**:
- `ee5b6cc6d7e8` (end of inventory/customer chain)
- `hh888jj88k10` (end of invoice chain)

The story's migration `ii999kk99l21` with `down_revision = hh888jj88k10` would extend one head of an already-branched chain. This creates a third head.

**Does the story acknowledge this?** NO.

The story (line 69) simply states:
> Create migration `ii999kk99l21_create_orders_tables.py` with revision chain `hh888jj88k10` → new

No guidance is provided on:
- How to handle the existing branching
- Whether to use `alembic revision --head=hh888jj88k10` to explicitly target this head
- How to merge branches if needed
- Whether `ee5b6cc6d7e8` also needs migration(s)

**Verification:**
```bash
$ alembic heads
# Returns: ee5b6cc6d7e8, hh888jj88k10 (multiple heads)
```

---

### Issue 2: actor_type Not Explicit

**Status: STILL BROKEN**

**Prior Finding:** AuditLog needs explicit `actor_type="user"` not just DB default

**Current Status:** The story says (line 127):
> Use existing `common.models.audit_log.AuditLog` model — same pattern as inventory services.

The AuditLog model has `default="user"` at the DB level (line 26 of audit_log.py):
```python
actor_type: Mapped[str] = mapped_column(
    String(20), nullable=False, default="user",
)
```

The story never explicitly sets `actor_type="user"` in the implementation. It relies on the DB default. The issue is NOT addressed.

---

### Issue 3: No Collision Retry Implementation Guidance

**Status: PARTIALLY FIXED**

**Prior Finding:** AC2 mentions retry but no implementation guidance for order number uniqueness

**Current Status:** Line 152 now states:
> Unique constraint + retry on collision (extremely unlikely with 4 billion combinations per day)

This acknowledges retry is needed but provides **no implementation guidance**:
- No retry count specified
- No code snippet showing the retry loop
- No guidance on what exception to catch
- No guidance on backoff strategy

The pattern exists in `create_supplier_order()` (inventory/services.py line 781) but is not referenced or copied.

---

### Issue 4: actor_id Inconsistency

**Status: STILL BROKEN**

**Prior Finding:** `str(DEFAULT_TENANT_ID)` vs inventory's `"system"`

**Current Status:** Two separate problems:

**4a. Value inconsistency:**
- Story line 95: `ACTOR_ID = str(DEFAULT_TENANT_ID)` → `"00000000-0000-0000-0000-000000000001"`
- Inventory routes.py line 67: `ACTOR_ID = "system"`

These are fundamentally different values. The story does not acknowledge or justify this difference.

**4b. Pattern inconsistency (NEW ISSUE introduced by fix attempt):**
The inventory pattern passes `actor_id` as a **parameter** to service functions:
```python
# inventory/services.py
async def create_supplier_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    supplier_id: uuid.UUID,
    ...
    actor_id: str,  # <-- passed as parameter
) -> dict:
```

But the story's `create_order()` task (line 93) does NOT list `actor_id` as a parameter. Line 95 says to use a hardcoded `ACTOR_ID = str(DEFAULT_TENANT_ID)` instead of passing it.

**Verification of inventory pattern (inventory/routes.py:407):**
```python
result = await create_supplier_order(
    session,
    TENANT_ID,
    ...
    actor_id=ACTOR_ID,  # <-- passed from route to service
)
```

The story's hardcoded approach is inconsistent with the inventory pattern it claims to follow.

---

## New Issues Introduced by "Fixes"

### NEW ISSUE 1: actor_id Not Passed to create_order()

**Location:** Task 4, line 93

The story's `create_order()` signature doesn't include `actor_id`:
```python
create_order(): validate customer exists, validate line items (≥1, qty > 0, unit_price ≥ 0), generate order number...
```

But line 95 says:
```python
Hardcode `TENANT_ID = DEFAULT_TENANT_ID` for MVP. For actor_id, use `ACTOR_ID = str(DEFAULT_TENANT_ID)`...
```

If `actor_id` is not in the function signature, how is the audit log supposed to get the right value? This is a structural inconsistency.

---

### NEW ISSUE 2: Index Definition Truncation

**Location:** Task 1

The index `ix_orders_tenant_created (tenant_id, created_at DESC)` appears correctly specified, but the story's text has no truncation. No new issue here - removing from new issues list.

---

## Confirmed Valid Patterns

The following patterns from the story correctly match the codebase:

1. **Order number format** (line 149-151):
   - Format: `ORD-{YYYYMMDD}-{8-CHAR-HEX}` matches supplier order pattern `PO-{date}-{hex}`
   - Uses `uuid.uuid4().hex[:8].upper()` correctly

2. **UUID(as_uuid=True) for tenant_id** (line 75):
   - Correctly matches gg777 migration standardization
   - NOT using String(50)

3. **Tax calculation reuse** (line 45):
   - `calculate_line_amounts(*, quantity, unit_price, policy_code)` signature matches actual function in `domains/invoices/tax.py`

4. **Model patterns** (line 80):
   - `UUID(as_uuid=True)` for UUIDs - correct
   - `DateTime(timezone=True)` for timestamps - correct
   - SupplierOrder pattern followed correctly

5. **Unique constraints** (lines 72-73):
   - `(tenant_id, order_number)` unique - correct
   - `(tenant_id, invoice_id) WHERE invoice_id IS NOT NULL` - correctly handles nullable FK

6. **Error pattern** (line 128):
   - `HTTPException` (not JSONResponse) - matches inventory pattern, not customers

---

## Net Assessment Summary

| Issue | Status | Notes |
|-------|--------|-------|
| Migration chain branching | STILL BROKEN | Multiple heads exist; story provides no guidance |
| actor_type explicit | STILL BROKEN | DB default relied upon; not explicitly set |
| Collision retry guidance | PARTIALLY FIXED | Mentioned but no implementation details |
| actor_id inconsistency | STILL BROKEN | Different value AND wrong pattern (hardcoded vs parameter) |
| actor_id parameter missing | NEW ISSUE | create_order() doesn't accept actor_id but should follow inventory pattern |

---

## Critical Finding: Migration Chain

The Alembic migration chain has **pre-existing branching** that is not acknowledged by the story:

```
aa111dd11c43 → bb222ee22d54 → cc333ff33e65 → dd444ff44f76 → ee555gg55h87
                                                              ↓
                                          ┌───────────────────┴───────────────────┐
                                          ↓                                       ↓
                              ee5b6cc6d7e8 (HEAD 1)                    hh888jj88k10 (HEAD 2)
                                          ↓
                              [potentially more branches]
```

The story's `ii999kk99l21` with `down_revision = hh888jj88k10` creates a third head without acknowledging the multi-head state.

**Required story update:** Explicit guidance on which head to target, or instructions for handling the merge.

---

## Required Fixes Before Story is Ready

1. **Add migration chain guidance** — acknowledge multi-head state and specify `--head=hh888jj88k10` or equivalent
2. **Add explicit actor_type** — `actor_type="user"` in AuditLog creation, not relying on DB default
3. **Add retry implementation** — specify retry count (e.g., 3 attempts) and catch `IntegrityError` on unique constraint
4. **Fix actor_id pattern** — either:
   - Pass `actor_id` as parameter to `create_order()` following inventory pattern, OR
   - Explicitly document why a different pattern (hardcoded vs parameter) is used
5. **Justify actor_id value difference** — `str(DEFAULT_TENANT_ID)` vs `"system"` needs explanation or alignment
