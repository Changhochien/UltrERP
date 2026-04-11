# Low Stock Alert System — Master Specification

**Document Version:** 1.0  
**Date:** 2026-04-11  
**Status:** Draft  
**Classification:** System Architecture & Implementation Guide  

---

## Document Control

| Field | Value |
|-------|-------|
| **Project** | UltrERP Low Stock Alert System |
| **Synthesized From** | Business Requirements, Trigger Logic, Notification Architecture, UI/UX Design |
| **Missing Documents** | Gap Analysis (pending), Data Model (pending) |
| **Review Status** | Pending team review |
| **Last Updated** | 2026-04-11 |

---

## Table of Contents

1. [Overview and Purpose](#1-overview-and-purpose)
2. [Business Context and User Needs](#2-business-context-and-user-needs)
3. [System Architecture](#3-system-architecture)
4. [Alert Lifecycle State Machine](#4-alert-lifecycle-state-machine)
5. [Trigger Logic Specification](#5-trigger-logic-specification)
6. [Notification System Architecture](#6-notification-system-architecture)
7. [UI/UX Specifications](#7-ux-specifications)
8. [Data Model](#8-data-model)
9. [API Specifications](#9-api-specifications)
10. [Implementation Roadmap](#10-implementation-roadmap)
11. [Open Questions](#11-open-questions)
12. [Appendix: Cross-References](#12-appendix-cross-references)

---

## 1. Overview and Purpose

### 1.1 Executive Summary

The Low Stock Alert System is a critical operational component of UltrERP that enables proactive inventory management by generating timely, actionable alerts when stock levels approach or fall below configured thresholds. The system transforms reactive firefighting into automated, configurable stock monitoring.

**Core Value Proposition:**
- **Immediate Visibility**: Real-time alerts when inventory reaches reorder points
- **Reduced Stockouts**: Proactive notifications prevent lost sales and customer dissatisfaction
- **Workflow Integration**: Direct links to purchase order creation and supplier management
- **Multi-Channel Delivery**: Configurable notifications via in-app, email, push, webhooks, and SMS

### 1.2 System Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LOW STOCK ALERT SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUTS                              CORE SYSTEM          OUTPUTS          │
│  ──────                              ───────────          ───────          │
│                                      ┌─────────────┐                          │
│  ┌──────────────┐                   │             │       ┌──────────────┐ │
│  │ Stock Changes │──────────────────▶│ Alert       │──────▶│ In-App       │ │
│  │ (transfers,   │                   │ Engine       │       │ Notifications│ │
│  │  adjustments, │                   │             │       └──────────────┘ │
│  │  receipts)    │                   │             │       ┌──────────────┐ │
│  └──────────────┘                   │ • Severity   │──────▶│ Email        │ │
│                                      │   Calc       │       │ Alerts       │ │
│  ┌──────────────┐                   │ • Dedupe      │       └──────────────┘ │
│  │ Product      │──────────────────▶│ • State Mgmt  │       ┌──────────────┐ │
│  │ Inventory    │                   │             │──────▶│ Push          │ │
│  │ Module       │                   └─────────────┘       │ Notifications│ │
│  └──────────────┘                                          └──────────────┘ │
│                                      ┌─────────────┐       ┌──────────────┐ │
│  ┌──────────────┐                   │ Notification│──────▶│ Webhooks     │ │
│  │ Reorder      │──────────────────▶│ Dispatcher  │       │ (Slack/Teams)│ │
│  │ Points       │                   │             │       └──────────────┘ │
│  │ (ROP, Safety)│                   │ • Routing    │       ┌──────────────┐ │
│  └──────────────┘                   │ • Templates  │──────▶│ Dashboard    │ │
│                                      │ • Tracking    │       │ Widgets      │ │
│  ┌──────────────┐                   └─────────────┘       └──────────────┘ │
│  │ Sales        │                                                       │
│  │ Velocity     │──────────────────────────────▶ Days Until Stockout Calc  │
│  │ Data         │                                                           │
│  └──────────────┘                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Key Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Event-Driven** | Stock changes emit events; alerts generated within 5 seconds |
| **Hybrid Processing** | Real-time event handling + periodic batch validation (15-min scan) |
| **User-Centric** | Per-user preferences, configurable channels, quiet hours |
| **Resilient** | Retry with exponential backoff, dead-letter queues, idempotent operations |
| **Observable** | Full audit trail, delivery tracking, metrics collection |

### 1.4 Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| Alert generation latency | < 5 seconds after inventory change |
| Dashboard widget load time | < 2 seconds |
| Email delivery | Within 60 seconds of alert creation |
| System availability | 99.5% uptime |
| Concurrent alert processing | Support 100+ simultaneous alerts |
| Notification retry | Up to 5 retries with exponential backoff |

---

## 2. Business Context and User Needs

### 2.1 Business Problem Statement

**Core Issue:** Inventory managers face stockouts causing:
- Lost sales revenue
- Customer dissatisfaction and churn
- Disrupted workflow for warehouse and purchasing teams
- Reactive (instead of proactive) inventory management

**Root Cause:** Lack of visibility into inventory health before stockouts occur.

### 2.2 User Personas

| Persona | Role | Primary Needs |
|---------|------|---------------|
| **Warehouse Managers** | Daily operations | Consolidated low-stock summary, quick triage, historical stock trends |
| **Purchasing Staff** | Replenishment | Generate supplier orders from alerts, supplier recommendations, quantity suggestions |
| **Sales Teams** | Customer-facing | Delivery timeline awareness, stock availability queries |
| **Admin Users** | System administration | Configure reorder points, thresholds, notification preferences, user access |

### 2.3 Alert Scenarios

| Scenario | Trigger Condition | Priority | Response SLA |
|----------|-------------------|----------|--------------|
| **Stockout** | Stock reaches zero (complete depletion) | CRITICAL | Immediate |
| **Safety Stock Violation** | Stock falls below minimum safety stock threshold | CRITICAL | Immediate |
| **Reorder Point Breach** | Stock dips to or below the configured reorder point | WARNING | Within 4 hours |
| **Projected Stockout** | Forecasted depletion based on sales velocity analysis | WARNING | Within 4 hours |
| **New Low-Stock Discovery** | Large orders reveal previously unknown low-stock items | INFO | Daily digest acceptable |

### 2.4 Business Value Metrics

| Metric | Current State | Target State |
|--------|---------------|-------------|
| Stockout frequency | Unknown | 40% reduction |
| Time to acknowledge alerts | Manual monitoring | < 4 hours average |
| Purchase order creation time | 15-30 minutes | < 2 minutes (from alert) |
| Alert coverage | Reactive only | 100% of threshold breaches |

---

## 3. System Architecture

### 3.1 High-Level Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM ARCHITECTURE                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                              FRONTEND LAYER                                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │  │
│  │  │ Alert       │  │ Dashboard   │  │ Product     │  │ Notification        │  │  │
│  │  │ Dashboard   │  │ Widget      │  │ Detail      │  │ Center (Toast/Bell) │  │  │
│  │  │ Page        │  │             │  │ Integration │  │                     │  │  │
│  │  │ /alerts     │  │             │  │             │  │                     │  │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │  │
│  └─────────┼────────────────┼────────────────┼───────────────────┼────────────┘  │
│            │                │                │                   │               │
│            └────────────────┴────────────────┴───────────────────┘               │
│                                          │                                        │
│                                          ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                              API GATEWAY LAYER                                │  │
│  │                           REST API + WebSocket                               │  │
│  │  GET/POST/PUT/DELETE /api/v1/alerts/*                                        │  │
│  │  GET/POST/PUT/DELETE /api/v1/notifications/*                                 │  │
│  │  WebSocket: ws://.../alerts (real-time updates)                             │  │
│  └──────────────────────────────────┬───────────────────────────────────────────┘  │
│                                     │                                              │
└─────────────────────────────────────┼────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼────────────────────────────────────────────┐
│                                     ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                              BACKEND SERVICES LAYER                           │  │
│  │                                                                              │  │
│  │  ┌────────────────────┐    ┌────────────────────┐    ┌────────────────────┐ │  │
│  │  │ Alert Engine       │    │ Notification       │    │ Batch Processing   │ │  │
│  │  │ ─────────────────  │    │ Service            │    │ ─────────────────  │ │  │
│  │  │ • handle_stock_    │    │ ─────────────────  │    │ • 15-min scan job   │ │  │
│  │  │   changed_event()  │    │ • trigger_for_     │    │ • Alert validation  │ │  │
│  │  │ • compute_severity │    │   alert()          │    │ • Auto-resolve      │ │  │
│  │  │ • alert_state_     │    │ • resolve_channels │    │ • Projected calc    │ │  │
│  │  │   transitions      │    │ • escalation_check │    │                     │ │  │
│  │  └─────────┬──────────┘    └─────────┬──────────┘    └─────────┬────────────┘ │  │
│  │            │                         │                       │               │  │
│  │            └────────────┬────────────┘                       │               │  │
│  │                         │                                     │               │  │
│  │                         ▼                                     ▼               │  │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                     EVENT BUS / MESSAGE QUEUE                          │  │  │
│  │  │  • StockChangedEvent     • AlertCreatedEvent    • AlertEscalatedEvent  │  │  │
│  │  │  • AlertAcknowledgedEvent • NotificationRequest                      │  │  │
│  │  └──────────────────────────────────┬─────────────────────────────────────┘  │  │
│  │                                     │                                        │  │
│  └─────────────────────────────────────┼────────────────────────────────────────┘  │
│                                        │                                          │
│  ┌─────────────────────────────────────┼────────────────────────────────────────┐  │
│  │                                     ▼                                          │  │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                      NOTIFICATION WORKERS (Background)                 │  │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │  │
│  │  │  │ In-App      │  │ Email       │  │ Push        │  │ Webhook    │  │  │  │
│  │  │  │ Worker      │  │ Worker      │  │ Worker      │  │ Worker     │  │  │  │
│  │  │  │ (WebSocket) │  │ (SMTP)      │  │ (FCM/APNs) │  │ (HTTP)     │  │  │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │  │  │
│  │  └────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                     │                                          │  │
│  └─────────────────────────────────────┼────────────────────────────────────────┘  │
│                                        │                                           │
│                                        ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                              DATA LAYER                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │ ReorderAlert│  │Notification │  │Notification │  │ Webhook     │        │  │
│  │  │ Table       │  │ Table       │  │Preference   │  │ Config      │        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                        │  │
│  │  │ Product     │  │ Warehouse   │  │ StockHistory│                        │  │
│  │  │ (existing)  │  │ (existing)  │  │ Table       │                        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                        │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Responsibilities

| Component | Responsibility | Key Operations |
|-----------|---------------|----------------|
| **Alert Engine** | Core alert lifecycle management | `handle_stock_changed()`, `compute_severity()`, `state_transitions()` |
| **Notification Service** | Multi-channel notification orchestration | `trigger_for_alert()`, `resolve_channels()`, `escalation_check()` |
| **Batch Processor** | Periodic validation and edge case handling | `batch_reorder_alert_scan()`, `detect_projected_stockouts()` |
| **In-App Worker** | WebSocket delivery, notification storage | `publish()`, `track_delivery()` |
| **Email Worker** | SMTP integration, HTML/text templates | `send()`, `track_delivery()` |
| **Push Worker** | FCM/APNs integration | `send()`, `track_delivery()` |
| **Webhook Worker** | External system HTTP callbacks | `send()`, `HMAC_sign()` |

### 3.3 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW SEQUENCE                              │
└─────────────────────────────────────────────────────────────────────────────┘

t=0    Stock Change (transfer, adjustment, receipt)
        │
        ▼
t=1    StockChangedEvent emitted by Stock Service
        │
        ▼
t=2    Alert Engine receives event
        │    • Evaluates trigger conditions (ROP, Safety Stock, Projected)
        │    • Computes severity
        │    • Creates/updates/resolve alerts per deduplication rules
        │
        ▼
t=3    AlertCreatedEvent emitted (if new/changed alert)
        │
        ▼
t=4    Notification Service resolves recipients and channels
        │    • Query user preferences
        │    • Filter by severity threshold
        │    • Check quiet hours
        │    • Enqueue to background queue
        │
        ▼
t=5    Background workers process queue (priority-ordered)
        │    • CRITICAL alerts: Immediate processing
        │    • WARNING alerts: Immediate or batched
        │    • INFO alerts: Digest option
        │
        ▼
t=6    Notifications delivered and tracked
        │    • Status: pending → sent → delivered → read
        │    • Click-through tracking
        │
        ▼
t=24h  (if alert unacknowledged)
        │
        ▼
t=24h  Escalation Service checks for stale alerts
        │    • Notifies managers
        │    • EscalationEscalatedEvent emitted
        │
        ▼
t=48h  (if still unacknowledged)
        │
        ▼
t=48h  Auto-create draft purchase order (optional)
```

---

## 4. Alert Lifecycle State Machine

### 4.1 State Definitions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ALERT LIFECYCLE STATE MACHINE                        │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │   PENDING   │ ← Initial state for new alerts
                              └──────┬──────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
    ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
    │ACKNOWLEDGED │          │   SNOOZED   │          │  DISMISSED  │
    └──────┬──────┘          └──────┬──────┘          └─────────────┘
           │                        │
           │                        │
           │    ┌────────────────────┘
           │    │    (after snooze period expires)
           │    │
           │    ▼
           │    ┌─────────────┐
           │    │   PENDING   │ (alert re-evaluated)
           │    └──────┬──────┘
           │           │
           │           │
           ▼           ▼
    ┌─────────────┐   OR   ┌─────────────┐
    │  RESOLVED   │        │   (repeat)  │
    └─────────────┘        └─────────────┘

LEGEND:
──────▶ State transition
│      │
│      └─ Transition label (trigger action)
```

### 4.2 State Transition Matrix

| From State | To State | Trigger | Side Effects |
|------------|----------|---------|--------------|
| PENDING | ACKNOWLEDGED | User acknowledges | `acknowledged_at`, `acknowledged_by` set |
| PENDING | SNOOZED | User snoozes (N minutes) | `snoozed_until` set, queue delayed |
| PENDING | RESOLVED | Stock restored above ROP | Auto-resolve or manual resolve |
| PENDING | DISMISSED | User dismisses | No further action |
| PENDING | RESOLVED | Purchase order created | Links to PO |
| ACKNOWLEDGED | SNOOZED | User snoozes | `snoozed_until` set |
| ACKNOWLEDGED | RESOLVED | Stock restored OR PO created | Manual resolution |
| SNOOZED | PENDING | Snooze period expires | Re-evaluated by batch scan |
| SNOOZED | RESOLVED | Stock restored during snooze | Batch scan auto-resolves |
| RESOLVED | PENDING | Stock drops below ROP again | New alert cycle |
| DISMISSED | (terminal) | - | Cannot transition out |

### 4.3 Auto-Resolution Rules

| Alert Status | Stock Restored Above ROP? | Action |
|--------------|---------------------------|--------|
| PENDING | Yes | **Auto-resolve** |
| ACKNOWLEDGED | Yes | **Keep acknowledged** (explicit resolution required) |
| SNOOZED | Yes | **Auto-resolve** (batch scan) |
| DISMISSED | Yes | No action (user explicitly dismissed) |

### 4.4 Severity Escalation Within Lifecycle

```
Alert Created → Severity = WARNING
       │
       │ Stock drops further
       ▼
Alert Updated → Severity = CRITICAL (if < 25% ROP)
       │
       │ Notification re-triggered to all channels
       ▼
User acknowledges WARNING (stock was at 20)
       │
       │ Stock drops to 5 (CRITICAL threshold)
       ▼
Alert Updated → Severity = CRITICAL
       │
       │ Re-notification sent (severity changed)
       ▼
Escalation timer starts (24h to acknowledge CRITICAL)
```

---

## 5. Trigger Logic Specification

### 5.1 Trigger Conditions

An alert is generated when **ANY** of the following conditions are met:

| Condition | Code | Formula | Severity |
|-----------|------|---------|----------|
| Stockout | `STOCKOUT` | `current_stock == 0` | CRITICAL |
| Below 25% ROP | `ROP_CRITICAL` | `current_stock < reorder_point * 0.25` | CRITICAL |
| Reorder Point Breach | `ROP_BREACH` | `current_stock <= reorder_point` AND `>= 25% ROP` | WARNING |
| Safety Stock Violation | `SAFETY_STOCK_VIOLATION` | `current_stock < safety_stock` | WARNING |
| Projected Stockout | `PROJECTED_STOCKOUT` | `days_until_stockout <= lead_time_days` | WARNING |
| ROP Change Detection | `ROP_CHANGE` | `new_ROP > old_ROP` AND `current_stock <= new_ROP` | WARNING |

### 5.2 Severity Calculation Algorithm

```python
def compute_severity(
    current_stock: int,
    reorder_point: int,
    safety_stock: float | None = None,
    avg_daily_usage: float | None = None,
    lead_time_days: int | None = None,
) -> str:
    """
    Compute alert severity based on stock level and thresholds.
    
    Priority: STOCKOUT > SAFETY_STOCK > ROP_BREACH
    """
    # CRITICAL: Stockout
    if current_stock == 0:
        return "CRITICAL"
    
    # CRITICAL: Stock below 25% of ROP
    if reorder_point > 0 and current_stock < reorder_point * 0.25:
        return "CRITICAL"
    
    # WARNING: Stock below ROP but >= 25% of ROP
    if current_stock < reorder_point:
        return "WARNING"
    
    # WARNING: Safety stock violation
    if safety_stock is not None and current_stock < safety_stock:
        return "WARNING"
    
    # WARNING: Projected stockout within lead time
    if (avg_daily_usage is not None and 
        avg_daily_usage > 0 and 
        lead_time_days is not None):
        days_until_stockout = current_stock / avg_daily_usage
        if days_until_stockout <= lead_time_days:
            return "WARNING"
    
    # INFO: Approaching ROP (stock < 150% of ROP)
    if reorder_point > 0 and current_stock < reorder_point * 1.5:
        return "INFO"
    
    return "NO_ALERT"
```

### 5.3 Severity Calculation Matrix

| Current Stock | Reorder Point | Safety Stock | Result |
|---------------|---------------|--------------|--------|
| 0 | Any | Any | **CRITICAL** |
| 5 | 25 | Any | **CRITICAL** (below 25%) |
| 10 | 25 | Any | **WARNING** |
| 8 | 10 | 10 | **WARNING** (at safety) |
| 15 | 20 | None | **WARNING** (projected) |
| 35 | 25 | None | **INFO** (approaching) |
| 40 | 25 | 10 | **NO ALERT** |

### 5.4 Alert Generation Strategy

**Hybrid Approach: Real-Time + Batch**

| Strategy | Latency | Coverage | Use Case |
|----------|---------|----------|----------|
| **Event-Driven** | < 5 seconds | Primary path | Stock transfers, adjustments, receipts |
| **Batch Scan** | 15 minutes | Edge cases, validation | Direct DB updates, velocity changes, projected stockouts |

### 5.5 Deduplication Rules

**Uniqueness Constraint:** `UNIQUE(tenant_id, product_id, warehouse_id)`

| Scenario | Action |
|----------|--------|
| Alert doesn't exist + condition met | Create new alert |
| Alert exists (PENDING) + condition still met | Update severity/stock |
| Alert exists (PENDING) + condition cleared | **Auto-resolve** |
| Alert exists (ACKNOWLEDGED) + condition cleared | Keep acknowledged |
| Alert exists (ACKNOWLEDGED) + severity escalation | Update severity, re-notify |
| Alert exists (RESOLVED) + condition met again | Transition to PENDING |
| Alert exists (SNOOZED) + condition still met | Keep snoozed |

### 5.6 Suggested Order Quantity

```python
def calculate_suggested_order_qty(
    current_stock: int,
    reorder_point: int,
    safety_stock: float | None = None,
    lead_time_days: int | None = None,
    avg_daily_usage: float | None = None,
) -> int | None:
    """Calculate suggested order quantity based on replenishment parameters."""
    
    if lead_time_days is None or avg_daily_usage is None:
        # Fallback: order to 2x ROP
        return max(0, 2 * reorder_point - current_stock) if reorder_point > 0 else None
    
    # Standard: order to cover lead time period plus safety buffer
    target_stock = (lead_time_days * avg_daily_usage) + (safety_stock or 0)
    suggested_qty = max(0, round(target_stock - current_stock))
    
    return suggested_qty
```

---

## 6. Notification System Architecture

### 6.1 Channel Matrix

| Channel | CRITICAL | WARNING | INFO | Retry | Rate Limit |
|---------|----------|---------|------|-------|------------|
| **In-App** | ✅ Always | ✅ | ✅ | N/A | Unlimited |
| **Email** | ✅ | ✅ | Digest | 3 retries | 100/hr/user |
| **Push (FCM/APNs)** | ✅ | Optional | ❌ | 3 retries | 1000/day/app |
| **Webhooks** | ✅ | ✅ | ✅ | 5 retries | 200/hr/tenant |
| **SMS** | ⚠️ Optional | ❌ | ❌ | 2 retries | 50/day/user |

### 6.2 Notification Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         NOTIFICATION SYSTEM ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────────┐     │
│  │ Stock Change │    │   Alert      │    │     Notification Queue            │     │
│  │ Service      │───▶│   Event      │───▶│  (Background Job Processing)     │     │
│  └──────────────┘    │   Emitter    │    │                                   │     │
│         │            └──────────────┘    │  • Rate limiting                  │     │
│         ▼                       │         │  • Retry with exponential backoff│     │
│  ┌──────────────┐               ▼         │  • Priority queues (CRITICAL first)│    │
│  │ ReorderAlert │    ┌──────────────────┐ │  • Dead letter queue              │     │
│  │ Handler       │──▶│ Notification     │ │  └──────────────────────────────────┘     │
│  └──────────────┘    │   Preference      │ │            │                               │
│         │            │   Resolver         │ │            ▼                               │
│         │            └──────────────────┘ │  ┌──────────────────────────────────┐     │
│         │                       │           │  │      Notification Workers        │     │
│         ▼                       ▼           │  │  ┌─────────┐ ┌─────────┐        │     │
│  ┌──────────────┐    ┌──────────────────┐ │  │  │ In-App  │ │  Email  │        │     │
│  │ ReorderAlert │    │ Notification     │ │  │  │ │ Worker  │ │ Worker  │        │     │
│  │ Model        │───▶│ Request Builder  │ │  │  │  └─────────┘ └─────────┘        │     │
│  │ (updated)    │    └──────────────────┘ │  │  ┌─────────┐ ┌─────────┐        │     │
│  └──────────────┘              │           │  │  │  Push   │ │Webhook  │        │     │
│                                │           │  │  │ │ Worker  │ │ Worker  │        │     │
│                                ▼           │  │  └─────────┘ └─────────┘        │     │
│                      ┌──────────────────┐  │  └──────────────────────────────────┘     │
│                      │ Notification     │  │            │                               │
│                      │ Record (DB)      │  │            ▼                               │
│                      └──────────────────┘  │  ┌──────────────┐ ┌──────────────┐       │
│                                             │  │  Delivery   │ │   Click      │       │
│                                             │  │  Tracker    │ │  Tracker     │       │
│                                             │  └──────────────┘ └──────────────┘       │
│                                             └──────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 User Preference Resolution

```python
def resolve_channels(preferences: list[NotificationPreference], severity: str) -> list[str]:
    """Resolve enabled channels for this severity level."""
    severity_order = {"CRITICAL": 1, "WARNING": 2, "INFO": 3}
    min_severity_level = severity_order[severity]
    
    channels = []
    for pref in preferences:
        if not pref.enabled:
            continue
        pref_level = severity_order.get(pref.severity_threshold, 3)
        if pref_level <= min_severity_level:
            channels.append(pref.channel)
    return channels
```

### 6.4 Queue Priority System

| Priority | Level | Severity | Processing |
|----------|-------|----------|------------|
| 0 | CRITICAL | Stockout | Immediate, all channels |
| 1 | HIGH | < 25% ROP | Immediate |
| 2 | NORMAL | WARNING | Immediate or batched |
| 3 | LOW | INFO | Digest only |
| 4 | BATCH | Digest | Scheduled batch |

### 6.5 Retry Policy

| Channel | Max Retries | Backoff Base | Total Time |
|---------|-------------|---------------|------------|
| Email | 3 | 60s (1m, 5m, 25m) | ~31 min |
| Push | 3 | 300s (5m, 25m, 125m) | ~2.5 hrs |
| Webhook | 5 | 30s (30s, 2.5m, 12.5m) | ~15 min |
| SMS | 2 | 300s | ~10 min |

### 6.6 Escalation Logic

```
t=0      Alert created (CRITICAL)
t=0+5s   Notification sent to assigned users
t=24h    Alert still unacknowledged
         → EscalationLevel 1
         → Notification sent to direct manager
t=48h    Alert still unacknowledged
         → EscalationLevel 2
         → Notification sent to department head
t=72h    Alert still unacknowledged
         → EscalationLevel 3
         → Auto-create draft purchase order (optional)
```

---

## 7. UI/UX Specifications

### 7.1 Design System Foundation

#### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--alert-critical` | `#DC2626` | Critical alerts |
| `--alert-critical-bg` | `#FEF2F2` | Critical alert background |
| `--alert-warning` | `#D97706` | Warning alerts |
| `--alert-warning-bg` | `#FFFBEB` | Warning alert background |
| `--alert-info` | `#2563EB` | Info alerts |
| `--alert-info-bg` | `#EFF6FF` | Info alert background |
| `--alert-success` | `#16A34A` | Resolved state |

#### Typography

| Style | Font | Size | Weight |
|-------|------|------|--------|
| Page Title | System | 28px | 600 |
| Section Header | System | 18px | 600 |
| Table Header | System | 11px | 600 (uppercase) |
| Body Text | System | 14px | 400 |
| Badge Text | System | 11px | 600 (uppercase) |

### 7.2 Key Pages and Views

| Page | Route | Purpose |
|------|-------|---------|
| Alert Dashboard | `/inventory/alerts` | Full alert management interface |
| Alert Panel | Sidebar on Inventory page | Compact urgent alerts view |
| Dashboard Widget | Homepage | KPI card with counts |
| Alert Detail Drawer | Modal/Drawer | Full alert details, actions |

### 7.3 Alert Dashboard Page Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ [PageHeader]                                                        │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Low Stock Alerts                               [Warehouse ▾]   │ │
│ └─────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│ [MetricCards]                                                      │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│ │ CRITICAL    │ │ WARNING     │ │ RESOLVED    │ │ AVG RESPONSE│   │
│ │    12       │ │    34       │ │   156       │ │   2.3 hrs   │   │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│ [DataTable]                                                         │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ [Filters ▾] [Severity ▾] [Warehouse ▾] [Date Range ▾] [🔍]    │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │ ☐ │ Severity │ Product      │ Warehouse │ Stock │ Days │ Act │ │
│ │───│──────────│──────────────│───────────│───────│──────│─────│ │
│ │ ☐ │ 🔴 CRIT  │ Widget Pro X  │ Main      │ 3/25  │ 0.5  │ ⋯   │ │
│ │ ☐ │ 🟠 WARN  │ Gadget 2000   │ East      │ 18/50 │ 2.1  │ ⋯   │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│ [Bulk Actions Bar - shows when items selected]                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.4 Alert Detail Drawer

**Trigger:** Click on alert row or card  
**Width:** 480px (desktop), full-width (mobile)  
**Animation:** Slide-in from right (250ms ease-in-out)

```
┌─────────────────────────────────────────────────────────────────────┐
│ [×]                                                                   │
├─────────────────────────────────────────────────────────────────────┤
│ [Product Image]                                                      │
│ Widget Pro X                                                         │
│ SKU: WPG-X-001 · Category: Electronics                               │
│                                                                      │
│ ┌────────────────────────────────────────────────────────────────┐  │
│ │ 🔴 CRITICAL — Stockout Risk                                    │  │
│ └────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│ CURRENT STOCK                                                        │
│ ┌────────────────────────────────────────────────────────────────┐  │
│ │      3  /  25 units                                             │  │
│ │      ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ (12%)       │  │
│ │      ⚠️ Estimated stockout in 0.5 days                          │  │
│ └────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│ STOCK HISTORY (Last 30 Days)                                         │
│ ┌────────────────────────────────────────────────────────────────┐  │
│ │ [Mini Sparkline Chart]                                          │  │
│ └────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│ SUGGESTED ORDER                                                      │
│ ┌────────────────────────────────────────────────────────────────┐  │
│ │  Supplier: Acme Supply Co.                          [Best]   │  │
│ │  Recommended Quantity: 100 units                             │  │
│ │  [Create Purchase Order]                                       │  │
│ └────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│ QUICK ACTIONS                                                        │
│ [Adjust Stock]  [Transfer Stock]  [Snooze Alert]                     │
├─────────────────────────────────────────────────────────────────────┤
│ TIMELINE                                                             │
│ ● Apr 11 — Alert Created                                            │
│ ○ Apr 10 — Stock Level: 15 units                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.5 Real-Time Updates

| Event | UI Update |
|-------|-----------|
| `alert:created` | Toast (if CRITICAL), Badge increment, List prepend |
| `alert:acknowledged` | Row update, Badge decrement |
| `alert:resolved` | Row update with strikethrough, Badge decrement |
| `alert:snoozed` | Row update with snooze indicator |
| `alert:dismissed` | Row fade out and remove |

### 7.6 Interaction Flows

#### Acknowledge Alert Flow
```
User clicks "Acknowledge"
        │
        ▼
Optimistic Update → API Call → Success/Failure Feedback
```

#### Create Purchase Order Flow
```
User clicks "Create Purchase Order"
        │
        ▼
Pre-fill PO Form → Open PO Modal → User confirms
        │
        ▼
API Call → Alert status → RESOLVED → Toast notification
```

---

## 8. Data Model

### 8.1 Core Tables

> **NOTE:** See `docs/low-stock-alert-data-model.md` for detailed schema (pending creation).

#### ReorderAlert Table (Existing)

```sql
CREATE TABLE reorder_alert (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id),
    product_id UUID NOT NULL REFERENCES product(id),
    warehouse_id UUID NOT NULL REFERENCES warehouse(id),
    
    -- Stock levels at time of alert
    current_stock INTEGER NOT NULL,
    reorder_point INTEGER NOT NULL,
    safety_stock NUMERIC(12,2),
    
    -- Computed fields
    severity VARCHAR(20) NOT NULL,  -- CRITICAL, WARNING, INFO
    alert_type VARCHAR(30) NOT NULL,  -- ROP_BREACH, STOCKOUT, PROJECTED_STOCKOUT
    
    -- Lifecycle state
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by UUID REFERENCES auth_user(id),
    snoozed_until TIMESTAMPTZ,
    
    -- Computed at query time (stored in response)
    days_until_stockout NUMERIC(10,2),
    suggested_order_qty INTEGER,
    suggested_supplier_id UUID,
    
    CONSTRAINT uq_alert_product_warehouse UNIQUE (tenant_id, product_id, warehouse_id)
);

CREATE INDEX ix_reorder_alert_tenant_status ON reorder_alert(tenant_id, status);
CREATE INDEX ix_reorder_alert_severity ON reorder_alert(severity);
```

#### NotificationPreference Table (New)

```sql
CREATE TABLE notification_preference (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    channel VARCHAR(20) NOT NULL,          -- 'in_app', 'email', 'push', 'webhook', 'sms'
    enabled BOOLEAN DEFAULT true,
    severity_threshold VARCHAR(20) DEFAULT 'INFO',
    frequency VARCHAR(20) DEFAULT 'immediate',  -- 'immediate', 'hourly_digest', 'daily_digest'
    quiet_hours_enabled BOOLEAN DEFAULT false,
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    quiet_hours_timezone VARCHAR(50) DEFAULT 'Asia/Taipei',
    
    CONSTRAINT uq_user_channel UNIQUE (user_id, channel)
);
```

#### Notification Table (New)

```sql
CREATE TABLE notification (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id),
    user_id UUID NOT NULL REFERENCES auth_user(id),
    reorder_alert_id UUID REFERENCES reorder_alert(id),
    
    channel VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, sent, delivered, failed, read
    
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    click_url TEXT,
    click_at TIMESTAMPTZ,
    
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    next_retry_at TIMESTAMPTZ,
    
    idempotency_key VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_idempotency UNIQUE (idempotency_key)
);
```

#### WebhookConfig Table (New)

```sql
CREATE TABLE webhook_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id),
    name VARCHAR(100) NOT NULL,
    channel_type VARCHAR(20) NOT NULL,  -- 'slack', 'teams', 'generic'
    url TEXT NOT NULL,
    secret VARCHAR(255),
    enabled BOOLEAN DEFAULT true,
    severity_threshold VARCHAR(20) DEFAULT 'WARNING',
    headers JSONB DEFAULT '{}',
    created_by UUID REFERENCES auth_user(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### AlertEscalation Table (New)

```sql
CREATE TABLE alert_escalation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES reorder_alert(id),
    escalation_level INTEGER DEFAULT 1,
    escalated_at TIMESTAMPTZ DEFAULT NOW(),
    notification_ids UUID[] DEFAULT '{}',
    action_taken VARCHAR(50),
    notes TEXT
);
```

### 8.2 Event Model

```python
# common/events.py

@dataclass(slots=True)
class StockChangedEvent(DomainEvent):
    """Emitted when stock levels change."""
    name: str = "stock_changed"
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    previous_stock: int
    new_stock: int
    change_type: str  # 'transfer', 'adjustment', 'receipt'

@dataclass(slots=True)
class AlertCreatedEvent(DomainEvent):
    """Fired when a new reorder alert is created."""
    name: str = "alert_created"
    alert_id: uuid.UUID
    severity: str  # 'CRITICAL', 'WARNING', 'INFO'
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    current_stock: int
    reorder_point: int

@dataclass(slots=True)
class AlertEscalatedEvent(DomainEvent):
    """Fired when an alert remains unacknowledged beyond threshold."""
    name: str = "alert_escalated"
    alert_id: uuid.UUID
    escalation_level: int
    severity: str
```

---

## 9. API Specifications

### 9.1 Alert Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/alerts` | List alerts with filters |
| GET | `/api/v1/alerts/{id}` | Get alert details |
| POST | `/api/v1/alerts/{id}/acknowledge` | Acknowledge alert |
| POST | `/api/v1/alerts/{id}/snooze` | Snooze alert |
| POST | `/api/v1/alerts/{id}/dismiss` | Dismiss alert |
| POST | `/api/v1/alerts/{id}/resolve` | Manually resolve alert |
| POST | `/api/v1/alerts/bulk-acknowledge` | Bulk acknowledge |
| POST | `/api/v1/alerts/{id}/create-po` | Create PO from alert |

### 9.2 Alert List Endpoint

```
GET /api/v1/alerts

Query Parameters:
- status: PENDING, ACKNOWLEDGED, SNOOZED, DISMISSED, RESOLVED (multi-select)
- severity: CRITICAL, WARNING, INFO (multi-select)
- warehouse_id: UUID
- category_id: UUID
- date_from: ISO date
- date_to: ISO date
- search: text search (product name, SKU)
- page: integer (default: 1)
- page_size: integer (default: 20, max: 100)
- sort_by: column name (default: severity)
- sort_order: asc, desc (default: asc)

Response:
{
  "data": [
    {
      "id": "uuid",
      "product_id": "uuid",
      "product_name": "Widget Pro X",
      "product_code": "WPG-X-001",
      "warehouse_id": "uuid",
      "warehouse_name": "Main Warehouse",
      "current_stock": 3,
      "reorder_point": 25,
      "safety_stock": null,
      "severity": "CRITICAL",
      "status": "PENDING",
      "alert_type": "ROP_BREACH",
      "days_until_stockout": 0.5,
      "suggested_order_qty": 100,
      "suggested_supplier": "Acme Supply Co.",
      "created_at": "2026-04-11T09:00:00Z",
      "acknowledged_at": null,
      "acknowledged_by": null,
      "snoozed_until": null
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 156,
    "total_pages": 8
  }
}
```

### 9.3 Snooze Endpoint

```
POST /api/v1/alerts/{id}/snooze

Request:
{
  "duration_minutes": 240  // or specific datetime
}

Response:
{
  "id": "uuid",
  "status": "SNOOZED",
  "snoozed_until": "2026-04-11T13:00:00Z"
}
```

### 9.4 Notification Preferences Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/{user_id}/notification-preferences` | Get all preferences |
| POST | `/api/v1/users/{user_id}/notification-preferences` | Create preference |
| PUT | `/api/v1/users/{user_id}/notification-preferences/{channel}` | Update preference |
| DELETE | `/api/v1/users/{user_id}/notification-preferences/{channel}` | Delete preference |

### 9.5 Notification History Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/{user_id}/notifications` | List notifications |
| GET | `/api/v1/users/{user_id}/notifications/{id}` | Get notification details |
| POST | `/api/v1/users/{user_id}/notifications/{id}/read` | Mark as read |
| POST | `/api/v1/users/{user_id}/notifications/mark-all-read` | Mark all as read |

### 9.6 Webhook Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tenants/{tenant_id}/webhooks` | List webhooks |
| POST | `/api/v1/tenants/{tenant_id}/webhooks` | Create webhook |
| PUT | `/api/v1/tenants/{tenant_id}/webhooks/{id}` | Update webhook |
| DELETE | `/api/v1/tenants/{tenant_id}/webhooks/{id}` | Delete webhook |
| POST | `/api/v1/tenants/{tenant_id}/webhooks/{id}/test` | Test webhook |

---

## 10. Implementation Roadmap

### 10.1 Phase 1: Core Alert Infrastructure (Weeks 1-3)

| Task | Description | Effort | Dependencies |
|------|-------------|--------|--------------|
| 1.1 | Database schema creation | 2 days | - |
| 1.2 | Alert Engine service implementation | 3 days | 1.1 |
| 1.3 | Trigger logic with severity calculation | 3 days | 1.2 |
| 1.4 | Event handlers (StockChangedEvent) | 2 days | 1.2 |
| 1.5 | Basic alert CRUD API endpoints | 2 days | 1.1, 1.3 |
| 1.6 | Unit tests for alert engine | 2 days | 1.2, 1.3, 1.4 |

**Deliverables:**
- ✅ Alert model with lifecycle states
- ✅ Severity calculation matching business rules
- ✅ Basic REST API for alert management
- ✅ StockChangedEvent handler

### 10.2 Phase 2: Notification System (Weeks 4-6)

| Task | Description | Effort | Dependencies |
|------|-------------|--------|--------------|
| 2.1 | Notification preference model & API | 2 days | 1.1 |
| 2.2 | In-app notification channel | 2 days | 2.1 |
| 2.3 | Email notification channel | 2 days | 2.1 |
| 2.4 | Background queue implementation | 3 days | - |
| 2.5 | Retry logic with exponential backoff | 2 days | 2.4 |
| 2.6 | Notification history API | 1 day | 2.1 |

**Deliverables:**
- ✅ Per-user notification preferences
- ✅ In-app and email notifications
- ✅ Background job processing with retry
- ✅ Delivery tracking

### 10.3 Phase 3: UI Implementation (Weeks 5-7)

| Task | Description | Effort | Dependencies |
|------|-------------|--------|--------------|
| 3.1 | Alert Dashboard page | 3 days | 1.5 |
| 3.2 | Alert Detail Drawer | 2 days | 3.1 |
| 3.3 | Dashboard Widget | 1 day | 1.5 |
| 3.4 | Alert Panel (sidebar) | 2 days | 3.1 |
| 3.5 | Real-time updates (WebSocket) | 2 days | 2.2 |
| 3.6 | Product Detail integration | 2 days | 3.1 |

**Deliverables:**
- ✅ Full alert dashboard with filtering and bulk actions
- ✅ Alert detail drawer with timeline
- ✅ Dashboard KPI widget
- ✅ Real-time toast notifications

### 10.4 Phase 4: Advanced Features (Weeks 7-9)

| Task | Description | Effort | Dependencies |
|------|-------------|--------|--------------|
| 4.1 | Batch scan job (15-min) | 2 days | 1.2 |
| 4.2 | Push notification channel | 2 days | 2.4 |
| 4.3 | Webhook integrations (Slack/Teams) | 3 days | 2.4 |
| 4.4 | Escalation service | 2 days | 2.4 |
| 4.5 | Daily digest feature | 2 days | 2.4 |
| 4.6 | Webhook management UI | 2 days | 4.3 |

**Deliverables:**
- ✅ Periodic batch validation
- ✅ Push notifications (FCM/APNs)
- ✅ External webhook integrations
- ✅ Alert escalation for stale alerts
- ✅ Digest emails

### 10.5 Phase 5: Polish & Optimization (Weeks 9-10)

| Task | Description | Effort | Dependencies |
|------|-------------|--------|--------------|
| 5.1 | Performance optimization | 2 days | All |
| 5.2 | Mobile responsive design | 2 days | 3.1-3.6 |
| 5.3 | Accessibility audit | 1 day | 3.1-3.6 |
| 5.4 | Integration testing | 2 days | All |
| 5.5 | Documentation | 2 days | All |

**Deliverables:**
- ✅ Performance targets met
- ✅ Mobile-responsive UI
- ✅ WCAG 2.1 AA compliance
- ✅ Full test coverage
- ✅ User documentation

### 10.6 Implementation Timeline

```
Week:    1   2   3   4   5   6   7   8   9   10
         ├───┼───┼───┼───┼───┼───┼───┼───┼───┤
Phase 1: [███████]
Phase 2:         [██████████]
Phase 3:             [████████████]
Phase 4:                     [████████████]
Phase 5:                             [█████████]
```

---

## 11. Open Questions

### 11.1 Business Logic

| # | Question | Status | Decision Needed By |
|---|----------|--------|-------------------|
| B1 | Should ACKNOWLEDGED alerts auto-resolve when stock is restored, or require explicit resolution? | **Open** | Week 2 |
| B2 | What is the default snooze duration? (60 min, 4 hours, 24 hours) | **Open** | Week 1 |
| B3 | Should projected stockout alerts require minimum demand history (30 days)? | **Open** | Week 2 |
| B4 | Should auto-create draft PO for CRITICAL alerts after 72 hours? | **Open** | Week 4 |

### 11.2 Technical Decisions

| # | Question | Status | Decision Needed By |
|---|----------|--------|-------------------|
| T1 | Queue backend: Redis or in-memory for V1? | **Open** | Week 1 |
| T2 | SMS provider: Twilio, AWS SNS, or skip for V1? | **Open** | Week 4 |
| T3 | Should we implement FCM/APNs for push in V1 or defer? | **Open** | Week 4 |
| T4 | Webhook retry: 5 retries sufficient? | **Open** | Week 4 |

### 11.3 Missing Documentation

| Document | Status | Notes |
|----------|--------|-------|
| `low-stock-alert-gap-analysis.md` | **Missing** | Need to analyze current vs proposed implementation |
| `low-stock-alert-data-model.md` | **Missing** | Detailed ERD and field definitions |

---

## 12. Appendix: Cross-References

### 12.1 Source Documents

| Document | Location | Key Sections |
|----------|----------|--------------|
| Business Requirements | `docs/low-stock-alert-business-requirements.md` | User personas, alert scenarios, severity levels |
| Trigger Logic | `docs/low-stock-alert-trigger-logic.md` | Trigger conditions, severity algorithm, batch scan |
| Notification Architecture | `docs/low-stock-alert-notification-architecture.md` | Channel design, queue architecture, escalation |
| UI/UX Design | `docs/low-stock-alert-ui-design.md` | Page layouts, components, interaction flows |

### 12.2 Code References

| Component | Location | Description |
|-----------|----------|-------------|
| Alert Model | `backend/common/models/reorder_alert.py` | Alert entity definition |
| Alert Service | `backend/domains/inventory/services.py` | Business logic |
| Event Handlers | `backend/domains/inventory/handlers.py` | StockChangedEvent handler |
| Reorder Point Module | `backend/domains/inventory/reorder_point.py` | ROP computation |
| Event System | `backend/common/events.py` | Domain event definitions |
| Config | `backend/common/config.py` | Settings |

### 12.3 Related Systems

| System | Integration Points |
|--------|-------------------|
| Product Inventory Module | Stock level data, product information |
| Supplier Management | Historical order data, supplier recommendations |
| Order Management | Purchase order creation, resolution linking |
| Auth/User Management | User preferences, notification recipients |
| Notification Service | Existing infrastructure for email delivery |

### 12.4 Glossary

| Term | Definition |
|------|------------|
| **ROP** | Reorder Point — the inventory level that triggers a reorder |
| **Safety Stock** | Minimum buffer inventory to prevent stockouts |
| **Stockout** | Condition where inventory reaches zero |
| **Sales Velocity** | Rate at which inventory is consumed over time |
| **Lead Time** | Time between placing an order and receiving inventory |
| **Days Until Stockout** | Estimated days before inventory depletes at current velocity |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-11 | System Architect | Initial synthesis from source documents |

---

## Document Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Business Analyst | [Pending] | | |
| System Architect | [Pending] | | |
| Product Owner | [Pending] | | |
| QA Lead | [Pending] | | |
