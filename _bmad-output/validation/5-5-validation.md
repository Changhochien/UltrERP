# Story 5.5 Validation Report — Iteration 1–4 Summary

**Story:** 5.5 Update Order Status
**Validated against:** Codebase at `/Volumes/2T_SSD_App/Projects/UltrERP`
**Story file:** `_bmad-output/implementation-artifacts/5-5-update-order-status.md`

---

## CRITICAL ISSUES (will break implementation)

### 1. Orders domain does not exist in backend
- **Finding:** `backend/domains/orders/` directory does not exist. Only `customers`, `health`, `inventory`, and `invoices` domains exist under `backend/domains/`.
- **Impact:** Story 5.5 cannot be implemented. All files referenced in the story (`backend/domains/orders/services.py`, `backend/domains/orders/routes.py`, `backend/domains/orders/schemas.py`) are non-existent. Story 5.5 is blocked by upstream dependency Story 5.1 (which creates the orders domain) and Story 5.4 (which adds to it).
- **Severity:** CRITICAL — zero code can be placed in non-existent files.

### 2. Orders domain does not exist in frontend
- **Finding:** `src/domain/orders/` directory does not exist. No `OrderDetail.tsx`, `OrderList.tsx`, `useOrderStatus.ts`, or `types.ts` exist for orders.
- **Impact:** Frontend tasks (AC6, AC7) cannot be implemented. The story's Task 4 (frontend status actions) references non-existent files.

### 3. `confirm_order()` from Story 5.4 does not exist
- **Finding:** Story 5.4 specifies `confirm_order()` in `backend/domains/orders/services.py`, but that file does not exist. Story 5.5 Task 1 Item 4 says: "If transitioning to 'confirmed', delegate to `confirm_order()` from Story 5.4." Story 5.4's Task 3 also references the same non-existent file.
- **Impact:** The delegation chain `update_order_status() → confirm_order()` cannot be implemented. The story creates a circular or forward dependency on code that doesn't exist.
- **Note:** The story correctly identifies this is a dependency, but since 5.4's code is not implemented, the delegation cannot be verified.

### 4. `Order` and `OrderStatus` models do not exist
- **Finding:** No `Order` model or `OrderStatus` enum exists anywhere in the backend. The story (Task 1) instructs to define `class OrderStatus(str, Enum)` in `backend/domains/orders/schemas.py`. The `SupplierOrderStatus` enum exists (`backend/common/models/supplier_order.py`), but no equivalent for customer/sales orders.
- **Impact:** The enum pattern must be created from scratch. Story 5.5's Task 1 correctly identifies the enum definition, but the underlying `Order` model (with `status`, `confirmed_at`, `invoice_id` fields) must exist first from Story 5.1.

### 5. `DELETE /api/v1/orders/{order_id}` cancel route has no reference pattern
- **Finding:** The story specifies a `DELETE /api/v1/orders/{order_id}` endpoint for cancellation. No such endpoint or pattern exists in the backend. The inventory domain has no DELETE route for supplier orders. The story's own reference (SupplierOrderDetail) uses a PUT PATCH-style status update, not a DELETE.
- **Impact:** The DELETE route is a novel pattern in this codebase. No existing implementation validates it.
- **Question:** Is DELETE the right verb? REST convention typically uses `POST /orders/{id}/cancel` or `PATCH /orders/{id}` with `{ "status": "cancelled" }`. The DELETE approach is non-standard and may confuse API consumers.

### 6. Story claims `FULFILLED` but inventory has `RECEIVED`
- **Finding:** Story 5.5's `OrderStatus` enum includes `FULFILLED = "fulfilled"` (the terminal state after `shipped`). The `SupplierOrderStatus` enum has `RECEIVED` (not `FULFILLED`). These are different domains so technically not an inconsistency, but the story's Dev Notes reference `update_supplier_order_status()` as the pattern source — and that function's enum uses `RECEIVED`. Dev agents implementing the order status may mistakenly look at `SupplierOrderStatus` instead of defining a separate `OrderStatus`.
- **Severity:** This is a confusion risk, not a breaking issue, since orders and supplier orders are separate domains.

---

## WARNINGS (potential issues)

### 7. `ALLOWED_TRANSITIONS` uses `set`, story specifies `frozenset`
- **Story says:** `ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]]`
- **Actual (`update_supplier_order_status()`):** `ALLOWED_TRANSITIONS: dict[SupplierOrderStatus, set[SupplierOrderStatus]]` (plain `set`, line 1148 of `inventory/services.py`)
- **Impact:** The story specifies immutability via `frozenset`, but the reference implementation uses a mutable `set`. If the dev agent follows the reference literally, the immutability guarantee is lost. If they follow the story spec exactly, they deviate from the established pattern.
- **Recommendation:** Decide whether to use `frozenset` (story spec) or `set` (reference pattern). The reference pattern is the authoritative source per the Dev Notes.

### 8. Audit log action name mismatch
- **Story says:** `action="ORDER_STATUS_CHANGED"` (for order status transitions)
- **Actual (`update_supplier_order_status()`):** `action="update_supplier_order_status"` (line 1169 of `inventory/services.py`)
- **Impact:** The story correctly identifies the order-domain action name as `ORDER_STATUS_CHANGED` (matching Story 5.4's spec), but the reference supplier-order pattern uses a different action name. This is acceptable since they're different domains, but the Dev Notes should clarify that the order audit log action is intentionally different from the supplier order audit log action.

### 9. HTTP 409 vs 422 inconsistency for invalid transitions
- **Story says:** Invalid transitions return `409 Conflict`
- **Actual (inventory routes):** `update_supplier_order_status()` raises `ValueError` for invalid transitions; the route handler (`routes.py:484-488`) catches it and returns `422 Unprocessable Entity`
- **Finding:** 409 IS used in this codebase for `VersionConflictError` and `DuplicateBusinessNumberError` (customers domain). 409 is also used for `InsufficientStockError` in the inventory transfer endpoint. So 409 is a known pattern for state conflicts, but the existing supplier order status endpoint uses 422.
- **Impact:** The story's prescription of 409 is correct per established patterns in this codebase (VersionConflict → 409). The inventory supplier order status endpoint is the outlier using 422. For the new orders domain, 409 is the right choice.
- **Action:** Ensure the order routes explicitly catch invalid transitions and return 409, not 422.

### 10. `async with session.begin():` not used in reference pattern
- **Story says:** "All within `async with session.begin():`" (Task 1 Item 6)
- **Actual (`update_supplier_order_status()`):** Uses `await session.flush()` only (line 1163), no `async with session.begin()` wrapping
- **Finding:** Other services in the codebase DO use `async with session.begin()`: `customers/service.py` (lines 100, 123, 132, 195, 213, 231, 300), `invoices/service.py` (lines 125, 249). The supplier order functions are inconsistent with the rest of the codebase.
- **Impact:** The story correctly specifies `async with session.begin()` for atomicity, which matches the broader codebase pattern. The `update_supplier_order_status()` reference is the outlier. Dev agent should follow the story spec (which matches most of the codebase) rather than the reference.

### 11. Confirmation dialog not in existing supplier order pattern
- **Story says (AC7):** "a confirmation dialog appears before each transition"
- **Actual (`SupplierOrderDetail.tsx`):** Status buttons call `handleStatusChange()` directly with no confirmation dialog (line 150-159)
- **Finding:** The existing supplier order detail component does NOT have confirmation dialogs. Story 5.4 does mention a confirmation dialog for the confirm action specifically ("Confirming this order will auto-generate an invoice. Continue?"), but not for other transitions.
- **Impact:** The story is extending the UI pattern to add confirmation dialogs for ALL transitions. This is a net-new UI feature. Dev agent should not look at `SupplierOrderDetail` as a reference for "no dialog needed" — the story explicitly requires them.

### 12. Cancellation is status-based in orders but `shipped → cancelled` allowed in supplier orders
- **Story says:** Cancellation transitions allowed ONLY from `pending` (AC3, AC4). `cancelled` is terminal.
- **Actual (supplier order `update_supplier_order_status()`):** `SHIPPED` can transition to `CANCELLED` (line 1151: `SupplierOrderStatus.SHIPPED: {SupplierOrderStatus.CANCELLED}`). `CONFIRMED` can also cancel.
- **Finding:** The story's cancellation model is MORE restrictive than the supplier order pattern. Only `pending` orders can be cancelled. This is intentionally different.
- **Action:** Dev agent should NOT copy the supplier order's cancellation logic (which allows cancelling shipped orders). The story is explicit: only `pending → cancelled` is allowed.

### 13. Status badge color specification inconsistency
- **Story says:** `pending=yellow, confirmed=blue, shipped=purple, fulfilled=green, cancelled=red`
- **Actual (`useSupplierOrders.ts`):** `pending="#6b7280"` (gray), `confirmed="#2563eb"` (blue), `shipped="#7c3aed"` (purple), `received="#16a34a"` (green), `cancelled="#dc2626"` (red). No `fulfilled` in supplier orders.
- **Finding:** The colors for confirmed, shipped, and cancelled match between story and reference. The `pending` color differs (gray vs yellow) and `fulfilled` has no supplier order equivalent (orders use `fulfilled`, supplier orders use `received`).
- **Action:** Use the story's color spec for the orders domain. `pending=yellow` (#eab308?) should be verified with the design system.

---

## CONFIRMED VALID (patterns that check out)

### 14. `update_supplier_order_status()` function exists with local `ALLOWED_TRANSITIONS`
- **Location:** `backend/domains/inventory/services.py`, lines 1123-1180
- **Confirmed:** `ALLOWED_TRANSITIONS` is defined inside the function (line 1148), not at module level. This matches the story's Dev Note exactly.
- **Pattern:** The local dict pattern is verified. Story correctly references this as the source.

### 15. `with_for_update()` row locking confirmed
- **Location:** `backend/domains/inventory/services.py:1139`, also `services.py:122, 143, 442, 993, 1048`
- **Confirmed:** `with_for_update()` is used extensively for row locking in this codebase. The pattern is well-established.

### 16. `statusLabel()` and `statusColor()` helpers exist
- **Location:** `src/domain/inventory/hooks/useSupplierOrders.ts`, lines 212-227
- **Confirmed:** `statusLabel(s: SupplierOrderStatus): string` and `statusColor(s: SupplierOrderStatus): string` are exported. The story's Task 4 Item 3 correctly references this pattern for reuse in `useOrderStatus.ts`.

### 17. Status badge UI pattern confirmed in frontend
- **Location:** `src/domain/inventory/components/SupplierOrderDetail.tsx:98-109`, `SupplierOrderList.tsx:109-121`
- **Confirmed:** Badge pattern (colored span with `statusColor()` background and `statusLabel()` text) exists in both detail and list views.

### 18. Status filter dropdown pattern confirmed
- **Location:** `src/domain/inventory/components/SupplierOrderList.tsx:53-67`
- **Confirmed:** `STATUS_OPTIONS` array with status filter dropdown exists. Story's Task 4 Item 2 (OrderList status filter) correctly references this pattern.

### 19. `NEXT_STATUSES` map pattern confirmed
- **Location:** `src/domain/inventory/components/SupplierOrderDetail.tsx:13-19`
- **Confirmed:** `NEXT_STATUSES: Partial<Record<SupplierOrderStatus, SupplierOrderStatus[]>>` maps current status to allowed next statuses. Story's Task 4 Item 1 (action buttons for valid next statuses only) correctly uses this pattern.

### 20. Audit log model supports the required fields
- **Location:** `backend/common/models/audit_log.py`
- **Confirmed:** `AuditLog` model has all required fields: `actor_id` (String(100)), `action` (String(100)), `entity_type` (String(100)), `entity_id` (String(100)), `before_state` (JSON), `after_state` (JSON), `correlation_id` (String(100)). The story's AC2 pattern (`before_state: { "status": old_status }`, `after_state: { "status": new_status }`) fits within this model.

### 21. 409 Conflict is used in this codebase for state conflicts
- **Locations:**
  - `backend/domains/customers/routes.py:95, 118, 127` — `VersionConflictError` → 409
  - `backend/tests/api/test_update_customer.py:173, 198` — 409 for version conflict
  - `backend/tests/api/test_create_customer.py:224, 244` — 409 for duplicate
  - `backend/tests/domains/inventory/test_supplier_orders.py:461` — 409 test for invalid transition
- **Confirmed:** 409 is the established code for state conflicts (version, duplicate, business rule). The story's use of 409 for invalid state transitions is consistent with existing patterns.

### 22. `actor_id` is String(100) in audit log
- **Location:** `backend/common/models/audit_log.py:24`
- **Confirmed:** `actor_id: Mapped[str] = mapped_column(String(100), nullable=False)`. The story's Dev Notes ("use `ACTOR_ID = str(DEFAULT_TENANT_ID)` (not UUID)") is correct.

### 23. `class X(str, Enum)` enum pattern confirmed
- **Locations:**
  - `SupplierOrderStatus` in `backend/common/models/supplier_order.py:16`
  - `AlertStatus` in `backend/common/models/reorder_alert.py:16`
  - `ReasonCode` in `backend/common/models/stock_adjustment.py:20`
  - `TaxPolicyCode` in `backend/domains/invoices/tax.py:18`
- **Confirmed:** The `class X(str, Enum)` pattern is the standard throughout the codebase. Story's Task 1 enum definition follows this exactly.

### 24. `SupplierOrderStatus` enum values for reference
- **Location:** `backend/common/models/supplier_order.py:16-22`
- **Values:** `PENDING = "pending"`, `CONFIRMED = "confirmed"`, `SHIPPED = "shipped"`, `PARTIALLY_RECEIVED = "partially_received"`, `RECEIVED = "received"`, `CANCELLED = "cancelled"`
- **Note:** Orders domain should use `FULFILLED` (not `RECEIVED`) as the terminal state. The story's enum is correct for the orders domain.

### 25. Story dependencies correctly identified
- **Depends on Story 5.1:** Order model, base routes — NOT IMPLEMENTED
- **Depends on Story 5.4:** `confirm_order()` function, `PATCH /status` endpoint — NOT IMPLEMENTED
- **Extends Story 5.4:** PATCH /status endpoint is created in 5.4, extended in 5.5
- **Frontend reuses:** SupplierOrderList/SupplierOrderDetail patterns — CONFIRMED

---

## WEB SEARCH FINDINGS

### Order Status State Machine Best Practices (2025–2026)

**HTTP 409 for Invalid State Transitions — CONFIRMED**
- Source: [APIPark 409 Status Code Article](https://apipark.com/techblog/en/409-status-code-explained-what-it-means-how-to-fix-2/) (Feb 2026): "State Machine Conflicts: Invalid Transitions. Many resources within an application follow a defined lifecycle or 'state machine.' Operations..."
- Source: [APIPark - Resolving 409](https://apipark.com/techblog/en/resolving-the-409-status-code-common-causes-fixes/) (Feb 2026): "If a client attempts to Cancel an order that is already in the Delivered state, the server would return a 409."
- Source: [MDN Web Docs - 409 Conflict](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/409) (Jul 2025): "The HTTP 409 Conflict client error response status code indicates a request conflict with the current state of the target resource."
- **Conclusion:** Using HTTP 409 for invalid order status transitions is industry-standard. The story's choice of 409 is correct.

**State Machine Design Patterns — CONFIRMED**
- Industry best practice: Define allowed transitions as an immutable map/dict (the story's `frozenset` approach is more correct than the reference's `set` for this)
- Atomic transactions for state changes are required (the story's `async with session.begin():` is correct)
- Audit logging of state transitions with before/after state is standard practice

---

## ITERATION SUMMARY

### Iteration 1: Story Reading + Codebase Exploration
- Read story file in full
- Confirmed `update_supplier_order_status()` exists with local `ALLOWED_TRANSITIONS`
- Confirmed `with_for_update()` pattern
- Confirmed `statusLabel()`/`statusColor()` helpers
- Confirmed `NEXT_STATUSES` map pattern
- Identified that orders domain does not exist

### Iteration 2: Deep-dive on State Machine + Audit Log
- Confirmed `async with session.begin()` pattern exists in `customers/service.py` and `invoices/service.py` but NOT in `update_supplier_order_status()`
- Confirmed audit log model structure
- Confirmed 409 usage in customers domain for version/duplicate conflicts
- Identified HTTP 422 vs 409 discrepancy in supplier order routes

### Iteration 3: All References Verified Against Codebase
- Confirmed all source references in the story's References section
- Verified `SupplierOrderDetail` and `SupplierOrderList` component patterns
- Verified `Actor_id` is String(100) not UUID
- Confirmed no `Order` or `OrderStatus` exists in codebase
- Confirmed `FULFILLED` vs `RECEIVED` distinction between domains

### Iteration 4: Final Consistency Pass
- Cross-checked story enum against `SupplierOrderStatus` enum
- Confirmed cancellation guard (pending only) is MORE restrictive than supplier order pattern
- Confirmed confirmation dialogs are a net-new UI requirement
- Confirmed DELETE route for cancellation has no reference pattern
- Web search confirmed 409 is industry-standard for state machine conflicts

---

## RECOMMENDATIONS

1. **Block on 5.1 and 5.4:** Story 5.5 cannot be implemented until the orders domain exists. Verify Stories 5.1 and 5.4 are at least in-progress before assigning 5.5.

2. **Clarify DELETE vs PATCH for cancellation:** The DELETE route is non-standard in this REST API. Consider whether `PATCH /orders/{id}` with `status: "cancelled"` or `POST /orders/{id}/cancel` would be more consistent with the existing API style.

3. **Decide on frozenset vs set:** The story specifies `frozenset` but the reference uses `set`. Pick one and make the reference consistent. For a state machine, `frozenset` is safer.

4. **Add confirmation dialogs as explicit UI work:** The AC7 requirement for confirmation dialogs before all transitions is a net-new UI pattern. Ensure this is scoped correctly — it requires design work, not just wiring the existing action buttons.

5. **Color spec for pending (yellow vs gray):** The story says yellow for pending, but `statusColor(pending)` in the supplier order hook returns gray (#6b308). Clarify the design system colors for the orders domain.

6. **Test concurrent status updates (Task 5 Item 7):** The story mentions testing "FOR UPDATE locking prevents concurrent status updates" — this is a race condition test that requires careful async test setup. Ensure adequate time is allocated.
