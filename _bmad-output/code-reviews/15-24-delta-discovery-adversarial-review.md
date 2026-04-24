# Story 15.24 Adversarial Code Review

**Date:** 2026-04-24  
**Reviewer:** Code Review Agent  
**Files Reviewed:**
- `backend/domains/legacy_import/delta_discovery.py`
- `backend/tests/domains/legacy_import/test_delta_discovery.py`
- `backend/domains/legacy_import/incremental_state.py`

**Test Result:** ✅ 12/12 PASSED

---

## Acceptance Criteria Coverage Analysis

| AC | Requirement | Test Coverage | Status |
|----|-------------|---------------|--------|
| AC1 | No watermark advancement | `test_discover_delta_does_not_mutate_plan` | ✅ Covered |
| AC2 | Closure keys for inventory/docs | `test_discover_delta_applies_warehouse_product_closure_for_inventory`, `test_discover_delta_applies_header_and_line_closure_for_sales` | ⚠️ Partial |
| AC3 | Append-only manifest shape | `test_build_delta_manifest_shape_is_append_only_and_audit_ready` | ⚠️ Partial |
| AC4 | No-op domain marking | `test_discover_delta_marks_domains_with_no_changes_as_no_op`, `test_build_delta_manifest_preserves_no_op_domains_separately` | ✅ Covered |
| AC5 | Deterministic on rerun | `test_discover_delta_is_deterministic_on_rerun` | ✅ Covered |

---

## Critical Findings

### C1: Missing Schema Validation in `changed_keys` (Medium-High)

**Location:** `delta_discovery.py:_cursor_key()` lines 95-99

**Issue:** The `_cursor_key` function extracts values from source rows without validating schema compliance:

```python
def _cursor_key(
    contract: IncrementalDomainContract,
    row: Mapping[str, Any],
) -> dict[str, Any]:
    return {component: row.get(component) for component in contract.cursor_components}
```

If a `source_projection` callable returns malformed data (missing cursor components, wrong types), the malformed cursor is silently included in `changed_keys` and propagated to the manifest.

**Risk:** Silent data corruption in manifest if upstream projection has bugs.

**Recommendation:** Add validation:
```python
def _cursor_key(
    contract: IncrementalDomainContract,
    row: Mapping[str, Any],
) -> dict[str, Any]:
    result = {}
    for component in contract.cursor_components:
        value = row.get(component)
        if value is None:
            raise ValueError(
                f"Row missing required cursor component '{component}' for domain"
            )
        result[component] = value
    return result
```

---

### C2: `changed_keys` Semantic Ambiguity (Medium)

**Location:** `delta_discovery.py:discover_delta()` rows 122-130

**Issue:** For `single-table` rules, `changed_keys` captures ALL rows (including duplicates with identical cursors), but this is never tested. The test `test_discover_delta_keeps_single_table_rule_for_parties` only verifies `closure_count == 2`, not that `changed_keys` has the expected count.

**Scenario:**
```python
# Test data: P1 appears twice
rows = [
    {"source-change-ts": "2026-04-18T01:00:00+00:00", "party-code": "P1"},
    {"source-change-ts": "2026-04-18T01:05:00+00:00", "party-code": "P1"},  # duplicate
    {"source-change-ts": "2026-04-18T01:10:00+00:00", "party-code": "P2"},
]
# changed_keys = 3 (all rows), closure_keys = 2 (unique entities)
```

**Risk:** Downstream consumers may assume `changed_keys` has one entry per entity, causing incorrect downstream processing.

**Recommendation:** Add explicit test:
```python
assert parties.changed_keys == (
    {"source-change-ts": "2026-04-18T01:00:00+00:00", "party-code": "P1"},
    {"source-change-ts": "2026-04-18T01:05:00+00:00", "party-code": "P1"},
    {"source-change-ts": "2026-04-18T01:10:00+00:00", "party-code": "P2"},
)
```

---

### C3: AC2 Incomplete Verification for Inventory Closure (Medium)

**Location:** `test_delta_discovery.py:test_discover_delta_applies_warehouse_product_closure_for_inventory`

**Issue:** Test verifies `closure_count == 2` and `closure_keys == (...)`, but doesn't explicitly assert the tuple structure matches `(warehouse_code, product_code)` format. If closure keys were generated as `{"product_code": "P1", "warehouse_code": "W1"}` (wrong key order) or contained extra fields, test would pass.

**Recommendation:** Add explicit structural assertions:
```python
assert sales.closure_keys == (
    {"warehouse_code": "W1", "product_code": "P1"},
    {"warehouse_code": "W2", "product_code": "P1"},
)
# Not just closure_count, but exact tuple values
```

---

## Minor Findings

### M1: `watermark_out_proposed` for Bootstrap Not Tested

**Location:** `test_discover_delta_flags_bootstrap_resume_mode_for_first_run`

The test creates a bootstrap scenario (first run, `resume_from_watermark=None`) but never asserts on `watermark_out_proposed`. This is acceptable because bootstrap doesn't use the proposed watermark for resumption, but explicit assertion would improve documentation.

---

### M2: Contract Version Not Verified in Manifest Tests

**Location:** `test_build_delta_manifest_shape_is_append_only_and_audit_ready`

The manifest includes `contract_version` but tests only verify `manifest_version`. AC3 requires complete manifest shape verification.

---

### M3: No Test for Empty Rows with Non-None Cursor

**Location:** `discover_delta()` line 186

Edge case: What if `source_projection` returns rows with all cursor components as `None`? The current code checks:
```python
if not any(v is None for v in candidate) and (best_cursor is None or candidate > best_cursor):
```

This skips rows with `None` components from watermark computation, but they ARE added to `changed_keys`. This could lead to confusing manifests with "empty" cursor keys.

---

### M4: `header-and-line-pair` Cursor/Watermark Mismatch

**Location:** `delta_discovery.py` line 170

For `header-and-line-pair` domains, `watermark_out_proposed` uses the full cursor `(document-date, document-number, line-number)`, not just `document_number`. The replay behavior with line-level watermarks is unclear from the contract.

**Verification:** The incremental_state.py contract says cursor is `document-date|document-number|line-number`, so line-level is correct. However, downstream consumers need to understand this.

---

## Architecture Compliance

| Rule | Status | Notes |
|------|--------|-------|
| Discovery is read-only | ✅ | `test_discover_delta_does_not_mutate_plan` verifies no mutation |
| Manifest is append-only | ✅ | Only `build_delta_manifest` creates artifacts |
| Watermarks never advanced in discovery | ✅ | `watermark_out_proposed` is proposed only |
| Manifest is single source of truth | ⚠️ | Task 4 (integration) not completed per story |

**Note:** Task 4 ("Integrate manifest into runner output and dry-run") is marked `[ ]` in the story. The implementation is correct but not integrated into the runner yet.

---

## Summary

| Category | Count |
|----------|-------|
| Critical Issues | 0 |
| Medium Issues | 3 |
| Minor Issues | 4 |
| Passed | 12/12 |

**Overall Assessment:** The implementation is solid and passes all tests. The main concerns are around test coverage gaps (C2, C3) that could hide subtle bugs, and the missing schema validation (C1) that could propagate malformed data. The architecture compliance is good.

**Recommended Actions:**
1. Add `changed_keys` explicit assertions in `test_discover_delta_keeps_single_table_rule_for_parties`
2. Add explicit structural assertions for inventory closure keys
3. Consider adding schema validation in `_cursor_key()` for production robustness
4. Complete Task 4 (runner integration) per story requirements
