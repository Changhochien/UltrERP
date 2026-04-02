# Story 3.5 Validation Report - Final

**Story:** 3.5 Update Customer Record
**Validator:** Claude Code
**Date:** 2026-04-01
**Validation Iterations:** 2
**Status:** ISSUES FOUND - See Summary

---

## Validation Summary

| Category | Status | Issues Found |
|----------|--------|--------------|
| Completeness | PARTIAL | AC coverage is partial; field rules and test cases missing |
| Consistency | PASS | Matches PRD, architecture, 3.2, 3.3, 3.4 |
| BN Change Handling | PARTIAL | AC2 correct but implementation detail missing |
| Immutability | WEAK | Mentioned in guardrails but not tested |
| Partial Update Semantics | FAIL | PATCH chosen correctly but merge semantics undefined |
| No-op Behavior | WEAK | Mentioned but not explicitly tested |
| Scope Guardrails | PASS | Correctly excludes delete/disable/merge |
| Best Practices | FAIL | No optimistic locking; merge semantics undefined |

---

## Confirmed Points (Iteration 2 Verified)

### 1. Correct PATCH Semantics Choice
The story correctly chooses PATCH (not PUT) for partial updates. This matches HTTP semantics (PATCH = partial modification) and FastAPI best practices.

### 2. Proper Dependency Chain
- Story 3.2 (checksum validation) is a hard prerequisite
- Story 3.4 (duplicate detection) must fire on BN change
- Story 3.3 (create) form primitives should be reused
- Dependency sequencing is correctly documented

### 3. Correct Business Number Change Behavior (AC2)
AC2 explicitly requires BOTH checksum (3.2) AND duplicate (3.4) validation when the business number changes. This is the correct business logic.

### 4. Scope Guardrails Are Appropriate
The story correctly excludes:
- Delete, disable, merge, bulk-edit
- Credit policy enforcement on orders
- Separate edit-only form stack
- Changes to customer_id or tenant_id

### 5. Reuses Existing Patterns
- Tenant context pattern from architecture
- Same validation helpers from 3.2
- Same error contracts (by reference) from 3.3/3.4
- Same schema patterns (Decimal for credit_limit)

### 6. Transaction-Based Persistence
Task 1 mentions "one transaction" for the update, which is correct for AC4's no-op guarantee.

---

## Issues (Severity)

### CRITICAL-1: No Optimistic Locking for Concurrent Updates

**Problem:** The story has no mechanism to handle concurrent edits to the same customer record.

**Scenario:**
1. User A loads customer (name="Acme", credit_limit=10000)
2. User B loads same customer
3. User A updates credit_limit to 15000, saves
4. User B updates name to "Acme Corp", saves
5. Result: User B's save overwrites User A's credit_limit change (back to 10000)

**Recommended Fix:**
Add a `version` column to the customer table:
```python
# In Customer model
version: int = Field(default=1)

# In update service
async def update_customer(customer_id: UUID, updates: CustomerUpdate, expected_version: int):
    # Check version before update
    result = await session.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.version == expected_version
        )
    )
    if not result:
        raise ConflictError("Customer was modified by another user")

    # Increment version on update
    customer.version += 1
    # ... apply updates
```

**Also Required:**
- Return `version` in GET/detail responses
- Accept `version` in PATCH request body
- Return HTTP 409 Conflict on version mismatch

**Severity:** HIGH - Without this, data loss can occur silently in multi-user scenarios.

---

### CRITICAL-2: Duplicate Check Must Exclude Self on Update

**Problem:** Story 3.4's duplicate check was designed for CREATE. When checking duplicates on UPDATE, the query must exclude the current customer_id to avoid false positives.

**Scenario:**
- Customer has BN "12345678"
- User updates address only (BN unchanged)
- Duplicate check runs, finds the customer itself, returns duplicate error

**Recommended Fix:**
In the service layer, when BN changes:
```python
# Inside update service, when BN changes
existing = await session.execute(
    select(Customer).where(
        Customer.normalized_bn == new_normalized_bn,
        Customer.id != customer_id,  # Exclude self
        Customer.tenant_id == tenant_id
    )
)
if existing:
    raise DuplicateCustomerError(...)
```

**Severity:** HIGH - Without this, legitimate updates fail incorrectly.

---

### HIGH-1: Merge Semantics Not Defined

**Problem:** The story says "define merge semantics clearly in the schema and tests" but doesn't actually define them.

**Required Definition:**
The PATCH update schema should specify:
- Omitted fields: retain existing database values
- Explicitly null fields: set to null (or retain, must choose)
- Explicitly provided fields: update to new values

**Recommended Pattern:**
```python
class CustomerUpdate(BaseModel):
    company_name: Optional[str] = None
    business_number: Optional[str] = None  # normalized BN
    billing_address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    # Explicitly EXCLUDED from update: customer_id, tenant_id

# In service layer - FastAPI PATCH best practice
update_data = customer_update.model_dump(exclude_unset=True)
# update_data only contains fields explicitly set by client
for field, value in update_data.items():
    setattr(existing_customer, field, value)
```

**Severity:** HIGH - Without this, developers may implement inconsistent merge behavior.

---

### HIGH-2: Immutable Field Protection - No Explicit Tests

**Problem:** The story mentions preserving customer_id and tenant_id in Dev Notes and scope guardrails, but no task or test explicitly verifies these cannot be changed.

**Recommended Tests:**
```python
# Test: PATCH with customer_id change is ignored
response = client.patch(f"/customers/{customer_id}", json={"customer_id": "different-id"})
assert response.status_code in (200, 400)  # Either rejected or field ignored
customer = get_customer_from_db(customer_id)
assert customer.customer_id == original_customer_id  # Unchanged

# Test: PATCH with tenant_id change is ignored
response = client.patch(f"/customers/{customer_id}", json={"tenant_id": "different-tenant"})
# ... verify tenant_id unchanged
```

**Severity:** HIGH - A malicious or buggy client could attempt to change these fields.

---

### HIGH-3: AC2 BN Change Detection Not Specified

**Problem:** AC2 says "when the business number changes" but doesn't define HOW the service detects a BN change.

**Options:**
1. Compare `old_normalized_bn != new_normalized_bn` in service (CORRECT)
2. Client-side flag `bn_changed: bool` in request (FRAGILE)
3. Always run both validators (WASTEFUL but safe)

**Recommended Implementation:**
```python
# In update service
existing_customer = await get_customer(customer_id)
old_bn = existing_customer.business_number
new_bn = update_data.get("business_number")

if new_bn and old_bn != normalize_bn(new_bn):
    # BN changed - run both validators
    await validate_checksum(new_bn)  # Story 3.2
    await check_duplicate(new_bn, exclude_id=customer_id)  # Story 3.4
```

**Severity:** HIGH - Without this, the implementation may use a fragile or incorrect approach.

---

### MEDIUM-1: No-op Guarantee - Explicit Tests Missing

**Problem:** AC4 requires "existing customer row remains unchanged" on failure, but no mandatory test case explicitly verifies this.

**Required Test Cases (from Testing Requirements):**
The story's Testing Requirements section lists:
- "unchanged row after failed update" - but this is only in the optional backend coverage list

**Mandatory Test Matrix:**
| Failure Scenario | Verify Row Unchanged |
|-----------------|---------------------|
| Invalid phone format | Yes |
| Invalid email format | Yes |
| Negative credit limit | Yes |
| Duplicate BN | Yes |
| Invalid checksum | Yes |
| Customer not found | N/A (no row to preserve) |

**Severity:** MEDIUM - Without explicit tests, the no-op guarantee is not verified.

---

### MEDIUM-2: Error Contract Not Defined

**Problem:** All customer stories reference "clear errors" and "consistent error contracts" but none define the actual response shape.

**Current References:**
- Story 3.3: "returns clear validation errors"
- Story 3.4: "stable error contract"
- Story 3.5: "returns clear errors"

**Required Definition:**
```python
# Example error response shape
{
    "error": {
        "code": "VALIDATION_ERROR",  # or DUPLICATE_BN, INVALID_CHECKSUM
        "message": "Human-readable message",
        "details": {
            "field": "business_number",
            "reason": "Checksum validation failed"
        },
        "existing_customer": {  # Only for duplicate BN
            "id": "uuid",
            "name": "Existing Customer Name"
        }
    }
}
```

**Severity:** MEDIUM - Inconsistent error formats across endpoints.

---

### MEDIUM-3: Credit Limit Bounds Not Fully Specified

**Problem:** AC1 mentions "negative credit limits" as invalid but doesn't specify:
- Is zero (0) a valid credit limit?
- Is there a maximum value?
- What precision (Decimal scale)?

**Reference from Story 3.3:**
> "Use `Decimal`/PostgreSQL `NUMERIC` semantics for `credit_limit`; do not use floating-point storage for monetary fields."

**Should Add:**
- Non-negative (>= 0) for credit limit
- Upper bound recommended (e.g., 999999999.99)
- Decimal(12,2) precision typical for monetary values

**Severity:** MEDIUM - Inconsistent validation across implementations.

---

### MEDIUM-4: Customer Not Found Handling

**Problem:** AC1 says "Given an existing customer record" but doesn't define what happens if the customer doesn't exist (404).

**Should Specify:**
- HTTP 404 Not Found
- Error code: CUSTOMER_NOT_FOUND
- Clear message: "Customer with ID {id} not found"

**Severity:** MEDIUM - Missing this could cause 500 errors instead of proper 404.

---

## Additional Observations

### Positive: Deprecation of MOD11 Wording
Story 3.2 correctly notes that the repo's "MOD11" shorthand may not match current Ministry of Finance guidance. Story 3.5 correctly defers to 3.2's validator rather than re-implementing.

### Positive: Audit Event Extension Point
The story correctly leaves an extension point for audit logging if the codebase has an event pattern by implementation time.

### Positive: Downstream Event Propagation Warning
The Risk section correctly notes that changing BN may need event propagation for downstream systems that treat BN as a foreign reference. This is a real architectural concern.

### Concern: Story 3.4 Self-Reference Fix
The duplicate check on update (excluding self) must be coordinated with Story 3.4 implementation. Story 3.4 was designed for create, so this modification needs to be explicit.

---

## Recommended Fixes (Priority Order)

1. **[CRITICAL]** Add optimistic locking with version column
2. **[CRITICAL]** Ensure duplicate check excludes self on update
3. **[HIGH]** Define PATCH merge semantics explicitly in story
4. **[HIGH]** Add immutable field protection test tasks
5. **[HIGH]** Specify BN change detection approach in service layer
6. **[MEDIUM]** Make unchanged-row test cases mandatory (not optional)
7. **[MEDIUM]** Define error response contract shape
8. **[MEDIUM]** Specify credit limit bounds (>= 0, max value)
9. **[MEDIUM]** Add 404 handling for customer not found

---

## Validation Checklist

| Check | Status | Notes |
|-------|--------|-------|
| All 4 ACs testable | PARTIAL | AC1 field rules vague, AC3/AC4 tests weak |
| Matches PRD | PASS | FR17, Journey 4 satisfied |
| Matches Architecture | PASS | customers.update, modular monolith followed |
| Consistent with 3.2 | PASS | Reuses 3.2 validator |
| Consistent with 3.3 | PASS | Reuses form primitives |
| Consistent with 3.4 | PARTIAL | Duplicate check needs self-exclusion fix |
| BN change = checksum + duplicate | PASS | AC2 correct |
| Immutability preserved | WEAK | Mentioned, not tested |
| PATCH semantics correct | PASS | Chosen correctly |
| Merge semantics defined | FAIL | Not defined |
| No-op guarantee tested | WEAK | Mentioned, not explicit |
| Scope guardrails followed | PASS | Delete/disable/merge excluded |
| Optimistic locking | FAIL | Missing |
| Error contracts defined | FAIL | Not defined |
| Credit limit bounds | PARTIAL | Only non-negative specified |

---

## Final Verdict

**Story Status:** NEEDS REVISION before development

**Overall Quality:** The story is well-structured and has correct business logic, but has significant gaps that could cause implementation problems:

- **Optimistic locking is the most critical gap** - without it, concurrent users can silently lose each other's changes.
- **Merge semantics definition is incomplete** - the story correctly identifies this as needed but doesn't deliver it.
- **Immutable field protection lacks test coverage** - this is a data integrity risk.
- **Error contracts are referenced but undefined** - consistent error handling is a cross-cutting concern that should be standardized.

**Effort to Fix:** Low - these are documentation/specification fixes, not redesign. The story's structure and business logic are sound.

**Recommendation:** Return to author with specific fix requests for the 9 issues above.
