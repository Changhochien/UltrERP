# Low Stock Alert System — Gap Analysis Report

**Document Version:** 1.0  
**Date:** 2026-04-11  
**Status:** Analysis Complete  
**Author:** Technical Audit

---

## 1. Executive Summary

This report analyzes the implementation of the Low Stock Alert System against the business requirements. The implementation provides a solid foundation with alert creation, listing, and acknowledgment functionality, but significant gaps exist in notification channels, lifecycle management, supplier integration, and real-time updates.

### Implementation Scorecard

| Category | Status | Coverage |
|----------|--------|----------|
| Core Alert Model & Storage | ✅ Complete | 85% |
| Alert Triggering Logic | ✅ Complete | 90% |
| Alert Listing & Filtering | ⚠️ Partial | 70% |
| Lifecycle States | ⚠️ Partial | 60% |
| Notification Channels | ❌ Missing | 20% |
| Supplier Integration | ❌ Missing | 30% |
| Real-time Updates | ❌ Missing | 10% |
| Dashboard Widgets | ✅ Complete | 80% |
| User Preferences | ❌ Missing | 0% |
| Audit Trail | ⚠️ Partial | 50% |

---

## 2. Backend Implementation Analysis

### 2.1 What Is Implemented ✅

#### Model (`common/models/reorder_alert.py`)
| Feature | Status | Notes |
|---------|--------|-------|
| AlertStatus enum (PENDING, ACKNOWLEDGED, RESOLVED) | ✅ | Matches business requirements |
| Unique constraint (tenant, product, warehouse) | ✅ | Prevents duplicate alerts |
| Status + warehouse index | ✅ | Supports efficient filtering |
| Alert severity tracking | ✅ | String field with CRITICAL/WARNING/INFO |
| Acknowledgment timestamps | ✅ | acknowledged_at, acknowledged_by |
| UUID primary keys | ✅ | Proper distributed ID generation |

#### Services (`domains/inventory/services.py`)
| Function | Status | Quality |
|----------|--------|---------|
| `_check_reorder_alert()` | ✅ | Correctly creates/updates/resolves alerts |
| `list_reorder_alerts()` | ✅ | Filters, pagination, sorting |
| `acknowledge_alert()` | ✅ | Proper state transitions |
| `_compute_severity()` | ✅ | CRITICAL/WARNING/INFO logic |
| StockChangedEvent handler | ✅ | Event-driven architecture |
| days_until_stockout calculation | ✅ | Backend computes, not exposed |

### 2.2 What's Incomplete or Missing ❌

#### Missing Features

| Feature | Gap | Priority |
|---------|-----|----------|
| **SNOOZED state** | Only PENDING/ACKNOWLEDGED/RESOLVED exist; snooze not implemented | HIGH |
| **DISMISSED state** | No dismissal capability | MEDIUM |
| **Escalation rules** | No automatic escalation for stale alerts | MEDIUM |
| **Alert bulk operations** | Cannot acknowledge/dismiss multiple alerts | HIGH |
| **Manual alert creation** | No API to manually create alerts | LOW |
| **Alert deduplication** | Uses unique constraint, but no configurable dedup window | LOW |
| **Re-send notifications** | Cannot re-trigger notification for existing alert | MEDIUM |

#### API Endpoints Missing

```
POST   /alerts/reorder/bulk-acknowledge  # Bulk acknowledge
POST   /alerts/reorder/bulk-dismiss     # Bulk dismiss  
PUT    /alerts/reorder/{id}/snooze      # Snooze alert
PUT    /alerts/reorder/{id}/dismiss     # Dismiss alert
GET    /alerts/reorder/{id}            # Single alert detail
PATCH  /alerts/reorder/{id}            # Update alert fields
```

### 2.3 Design Gaps & Inconsistencies

#### Gap 1: Severity Field Type Mismatch
**Issue:** Backend stores severity as `String` but requirements imply enum behavior.

```python
# Backend - reorder_alert.py
severity: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO")

# Frontend types - doesn't enforce valid values
severity: string | null;  // Should be 'CRITICAL' | 'WARNING' | 'INFO'
```

**Recommendation:** Create `AlertSeverity` enum in Python and TypeScript.

#### Gap 2: Severity Calculation Inconsistency
**Issue:** Frontend and backend compute severity differently.

```python
# Backend - services.py
def _compute_severity(current_stock, reorder_point):
    if current_stock == 0: return "CRITICAL"
    if reorder_point > 0 and current_stock < reorder_point * 0.5: return "WARNING"
    return "INFO"

# Frontend - AlertFeed.tsx - uses different logic
if (item.current_stock === 0) return "critical";
if (item.current_stock < item.reorder_point * 0.5) return "critical";
return "low_stock";
```

**Impact:** Frontend shows "low_stock" vs backend "INFO", and thresholds differ (backend uses 0.5× for WARNING, frontend uses 0.5× for CRITICAL).

#### Gap 3: days_until_stockout Not Exposed
**Issue:** Backend computes but frontend cannot display.

**Recommendation:** Add to response schema and frontend types.

#### Gap 4: Suggested Order Quantity Not Returned
**Issue:** Requirements specify `suggested_order_qty` but not implemented.

---

## 3. Frontend Implementation Analysis

### 3.1 What Is Implemented ✅

#### Components
| Component | Status | Quality |
|-----------|--------|---------|
| `ReorderAlerts.tsx` | ✅ | Full DataTable with filters |
| `AlertPanel.tsx` | ✅ | Compact list with i18n |
| `AlertFeed.tsx` | ✅ | Sidebar with type filtering |
| `LowStockAlertsCard.tsx` | ✅ | Dashboard widget |
| Hook `useReorderAlerts` | ✅ | Proper state management |
| Hook `useAcknowledgeAlert` | ✅ | Handles alreadyResolved case |

### 3.2 What's Incomplete or Missing ❌

| Feature | Status | Gap |
|---------|--------|-----|
| Snooze functionality | ❌ | No snooze UI or API |
| Dismiss functionality | ❌ | No dismiss UI or API |
| Bulk acknowledge | ❌ | No multi-select capability |
| Real-time updates | ❌ | No WebSocket/SSE |
| Pagination UI | ⚠️ | No next/prev buttons |
| Auto-refresh | ⚠️ | Manual reload only |

### 3.3 Design Gaps & Inconsistencies

#### Gap 1: Duplicate Component Functionality
**Issue:** Three components provide similar functionality with different feature sets.

| Feature | ReorderAlerts | AlertPanel | AlertFeed |
|---------|---------------|------------|-----------|
| Status filter | ✅ | ✅ | ❌ |
| Warehouse filter | ✅ | ❌ | ❌ |
| Acknowledge | ✅ | ✅ | ✅ |
| Type filtering | ❌ | ❌ | ✅ |
| Relative time | ❌ | ✅ | ✅ |

**Recommendation:** Consolidate into single AlertList component with configurable views.

---

## 4. Edge Cases Not Handled

### 4.1 Concurrency Issues

| Edge Case | Status | Risk |
|-----------|--------|------|
| Simultaneous stock changes for same product | ⚠️ | Race condition possible |
| Bulk acknowledge while stock changes | ⚠️ | Stale state |
| Reorder point updated during alert lifecycle | ⚠️ | Alert may become stale |

### 4.2 Data Integrity Issues

| Edge Case | Status | Risk |
|-----------|--------|------|
| Product deleted while alert exists | ❌ | Orphaned alert |
| Warehouse deleted while alert exists | ❌ | Orphaned alert |
| Reorder point set to 0 | ⚠️ | Backend skips, no user feedback |
| Negative stock quantity | ⚠️ | No validation |

---

## 5. Business Requirements Gap Analysis

### 5.1 Notification Channels

| Channel | Required | Implemented | Gap |
|---------|----------|-------------|-----|
| In-App Alerts | ✅ | ✅ | Complete |
| Dashboard Widgets | ✅ | ✅ | Complete |
| Email Notifications | ✅ | ❌ | **MISSING** |
| Push Notifications | ✅ | ❌ | **MISSING** |
| Webhooks | ✅ | ❌ | **MISSING** |

### 5.2 Lifecycle States

| State | Required | Implemented | Gap |
|-------|----------|-------------|-----|
| PENDING | ✅ | ✅ | Complete |
| ACKNOWLEDGED | ✅ | ✅ | Complete |
| RESOLVED | ✅ | ✅ | Complete |
| DISMISSED | ✅ | ❌ | **MISSING** |
| SNOOZED | ✅ | ❌ | **MISSING** |

### 5.3 Severity Levels

| Level | Required | Threshold | Implemented | Gap |
|-------|----------|-----------|-------------|-----|
| CRITICAL | ✅ | stock = 0 OR stock < 25% ROP | ⚠️ | Backend uses 0 or <50% |
| WARNING | ✅ | stock < ROP but >= 50% | ⚠️ | Backend uses <50% = WARNING |
| INFO | ✅ | stock < 150% ROP | ⚠️ | Always triggers at <=ROP |

---

## 6. Recommendations by Priority

### HIGH Priority

| # | Recommendation | Effort | Impact |
|---|----------------|--------|--------|
| 1 | Add SNOOZED lifecycle state | Medium | Enables user control |
| 2 | Implement real-time updates | High | Immediate awareness |
| 3 | Add days_until_stockout to API response | Low | Better UX |
| 4 | Fix severity threshold inconsistency | Low | Correct behavior |

### MEDIUM Priority

| # | Recommendation | Effort | Impact |
|---|----------------|--------|--------|
| 5 | Add bulk acknowledge/dismiss APIs | Medium | Batch operations |
| 6 | Add email notification channel | High | Multi-channel alerts |
| 7 | Add webhook support | High | External integrations |

### LOW Priority

| # | Recommendation | Effort | Impact |
|---|----------------|--------|--------|
| 8 | Implement DISMISSED state | Low | Complete lifecycle |
| 9 | Add suggested_order_qty computation | Medium | Purchase guidance |
| 10 | Consolidate duplicate components | Medium | Reduced maintenance |

---

## 7. Summary

The Low Stock Alert System implementation provides a functional foundation with proper event-driven architecture, efficient database design, and multiple UI representations. However, significant gaps exist:

1. **Notification channels incomplete** — Only in-app alerts exist
2. **Lifecycle states incomplete** — SNOOZED and DISMISSED states not implemented
3. **Real-time updates missing** — Users must manually refresh
4. **Severity calculations inconsistent** — Backend and frontend use different thresholds
5. **Suggested order data not provided** — suggested_order_qty and suggested_supplier missing

---

*Report generated: 2026-04-11*  
*Files analyzed: backend/common/models/reorder_alert.py, backend/domains/inventory/services.py, src/domain/inventory/components/*  
*Next review: After implementing HIGH priority items*
