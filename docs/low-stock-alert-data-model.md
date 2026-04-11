# Low Stock Alert System — Enhanced Data Model

**Document Version:** 1.0  
**Date:** 2026-04-11  
**Author:** Data Architecture

---

## 1. Overview

This document specifies the enhanced data model for the Low Stock Alert System, extending the current `reorder_alert.py` model with additional fields for notification tracking, alert context, extended lifecycle, and linked actions.

---

## 2. Current Model Analysis

### Existing Model: `ReorderAlert`

```python
class ReorderAlert(Base):
    __tablename__ = "reorder_alert"
    
    id: Mapped[uuid.UUID]
    tenant_id: Mapped[uuid.UUID]
    product_id: Mapped[uuid.UUID]
    warehouse_id: Mapped[uuid.UUID]
    current_stock: Mapped[int]
    reorder_point: Mapped[int]
    severity: Mapped[str]  # CRITICAL, WARNING, INFO
    status: Mapped[AlertStatus]  # PENDING, ACKNOWLEDGED, RESOLVED
    created_at: Mapped[datetime]
    acknowledged_at: Mapped[datetime | None]
    acknowledged_by: Mapped[str | None]
```

### Gaps Identified
- Missing lifecycle states (SNOOZED, DISMISSED)
- No notification tracking
- No suggested order quantity
- No days until stockout
- No linked supplier order
- No audit trail for state transitions

---

## 3. Enhanced Model

### 3.1 Extended ReorderAlert Table

```python
from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from common.database import Base
import enum
import uuid
from datetime import datetime

class AlertStatus(str, enum.Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SNOOZED = "snoozed"
    DISMISSED = "dismissed"

class AlertSeverity(str, enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

class ResolutionType(str, enum.Enum):
    AUTO_RESOLVED = "auto_resolved"      # Stock restored automatically
    SUPPLIER_ORDER = "supplier_order"    # PO created
    MANUAL_RESTOCK = "manual_restock"    # Manual stock adjustment
    DISMISSED = "dismissed"             # User dismissed
    SNOOZED_INDEFINITELY = "snoozed"    # Snoozed until manually resolved

class ReorderAlert(Base):
    __tablename__ = "reorder_alert"
    __table_args__ = (
        Index(
            "uq_reorder_alert_tenant_product_warehouse",
            "tenant_id", "product_id", "warehouse_id",
            unique=True,
        ),
        Index(
            "ix_reorder_alert_tenant_status_warehouse",
            "tenant_id", "status", "warehouse_id",
        ),
        Index(
            "ix_reorder_alert_snoozed_until",
            "snoozed_until",
            postgresql_where="snoozed_until IS NOT NULL",
        ),
    )

    # Primary keys
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )

    # Foreign keys
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=False,
    )

    # Stock information
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_stock: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Alert classification
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(
            AlertSeverity,
            name="alert_severity_enum",
            create_constraint=True,
        ),
        default=AlertSeverity.INFO,
        nullable=False,
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(
            AlertStatus,
            name="alert_status_enum",
            create_constraint=True,
        ),
        default=AlertStatus.PENDING,
        nullable=False,
    )

    # Computed context fields
    suggested_order_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    suggested_supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier.id"), nullable=True,
    )
    days_until_stockout: Mapped[float | None] = mapped_column(
        # Computed: current_stock / avg_daily_usage
        # Store as nullable - recalculated on stock changes
    )
    avg_daily_usage: Mapped[float | None] = mapped_column(
        # Computed from historical sales
    )
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Denormalized display fields
    product_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Lifecycle timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # Acknowledgment
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[str | None] = mapped_column(String(100))

    # Snooze
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snoozed_by: Mapped[str | None] = mapped_column(String(100))

    # Dismissal
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dismissed_by: Mapped[str | None] = mapped_column(String(100))
    dismissal_reason: Mapped[str | None] = mapped_column(Text)

    # Resolution
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[str | None] = mapped_column(String(100))
    resolution_type: Mapped[ResolutionType | None] = mapped_column(
        Enum(ResolutionType, name="resolution_type_enum", create_constraint=True),
    )

    # Linked actions
    linked_supplier_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_order.id"), nullable=True,
    )
    linked_stock_adjustment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stock_adjustment.id"), nullable=True,
    )

    # Notification tracking
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notification_channels: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, default=list,
    )

    # Audit trail
    state_transition_log: Mapped[list[dict] | None] = mapped_column(
        JSON, nullable=True, default=list,
    )
```

### 3.2 New Table: NotificationPreference

```python
class NotificationPreference(Base):
    __tablename__ = "notification_preference"
    __table_args__ = (
        Index(
            "uq_notification_pref_tenant_user",
            "tenant_id", "user_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Channel settings (JSON array of enabled channels)
    channels: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=["in_app"],
    )
    # Minimum severity to trigger notification
    severity_threshold: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity_enum", create_constraint=True),
        default=AlertSeverity.WARNING,
        nullable=False,
    )

    # Notification frequency
    frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="immediate",
    )
    # "immediate", "hourly_digest", "daily_digest"

    # Quiet hours (JSON object)
    quiet_hours: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
    )
    # {"enabled": true, "start": "22:00", "end": "08:00", "timezone": "Asia/Taipei"}

    # Category-level settings (JSON array)
    category_overrides: Mapped[list[dict] | None] = mapped_column(
        JSON, nullable=True,
    )
    # [{"category": "Electronics", "severity_threshold": "critical", "channels": ["email"]}]

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
```

### 3.3 New Table: NotificationLog

```python
class NotificationLog(Base):
    __tablename__ = "notification_log"
    __table_args__ = (
        Index("ix_notification_log_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )

    # Reference to alert
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reorder_alert.id"), nullable=False,
    )

    # Notification channel
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    # "email", "push", "webhook", "sms", "in_app"

    # Delivery status
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # "pending", "sent", "delivered", "read", "failed", "bounced"

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Recipient info
    recipient: Mapped[str | None] = mapped_column(String(255))
    # email address, device token, webhook URL, etc.

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Click tracking
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

### 3.4 New Table: WebhookConfig

```python
class WebhookConfig(Base):
    __tablename__ = "webhook_config"
    __table_args__ = (
        Index("ix_webhook_config_tenant_active", "tenant_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )

    # Webhook identity
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    endpoint_url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret_key: Mapped[str] = mapped_column(String(255), nullable=True)
    # For HMAC signature verification

    # Trigger settings
    trigger_severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity_enum", create_constraint=True),
        default=AlertSeverity.WARNING,
        nullable=False,
    )
    trigger_channels: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=["low_stock"],
    )

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # Delivery stats
    total_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    failed_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    last_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

---

## 4. Enums Summary

```python
# Add to common/models/__init__.py or create new enums.py

class AlertStatus(str, enum.Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    SNOOZED = "snoozed"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"

class AlertSeverity(str, enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

class ResolutionType(str, enum.Enum):
    AUTO_RESOLVED = "auto_resolved"
    SUPPLIER_ORDER = "supplier_order"
    MANUAL_RESTOCK = "manual_restock"
    DISMISSED = "dismissed"
    SNOOZED_INDEFINITELY = "snoozed"

class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    WEBHOOK = "webhook"
    SMS = "sms"
```

---

## 5. API Response Schemas

### 5.1 ReorderAlertResponse (Enhanced)

```typescript
// In src/domain/inventory/types.ts

interface ReorderAlertItem {
  id: string;
  product_id: string;
  product_name: string;
  product_code: string | null;
  warehouse_id: string;
  warehouse_name: string;
  current_stock: number;
  reorder_point: number;
  safety_stock: number | null;
  severity: 'critical' | 'warning' | 'info';
  status: 'pending' | 'acknowledged' | 'snoozed' | 'dismissed' | 'resolved';
  created_at: string;
  updated_at: string;
  
  // Computed context
  suggested_order_qty: number | null;
  suggested_supplier_id: string | null;
  suggested_supplier_name: string | null;
  days_until_stockout: number | null;
  avg_daily_usage: number | null;
  lead_time_days: number | null;
  
  // Lifecycle fields
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  snoozed_until: string | null;
  snoozed_by: string | null;
  dismissed_at: string | null;
  dismissed_by: string | null;
  dismissal_reason: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution_type: 'auto_resolved' | 'supplier_order' | 'manual_restock' | 'dismissed' | 'snoozed' | null;
  
  // Linked actions
  linked_supplier_order_id: string | null;
  linked_stock_adjustment_id: string | null;
  
  // Notification tracking
  notification_channels: string[] | null;
  notified_at: string | null;
  
  // Audit
  state_transition_log: Array<{
    from_status: string;
    to_status: string;
    changed_at: string;
    changed_by: string;
    reason?: string;
  }> | null;
}
```

---

## 6. Migration Strategy

### Phase 1: Add New Enums (No data migration)

```sql
-- Add new enum values to PostgreSQL
ALTER TYPE alert_status_enum ADD VALUE IF NOT EXISTS 'snoozed';
ALTER TYPE alert_status_enum ADD VALUE IF NOT EXISTS 'dismissed';

CREATE TYPE resolution_type_enum AS ENUM (
    'auto_resolved', 'supplier_order', 'manual_restock', 'dismissed', 'snoozed'
);
```

### Phase 2: Add New Columns (All nullable, no data migration)

```sql
-- Add new columns to reorder_alert table
ALTER TABLE reorder_alert 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS safety_stock INTEGER,
ADD COLUMN IF NOT EXISTS suggested_order_qty INTEGER,
ADD COLUMN IF NOT EXISTS suggested_supplier_id UUID REFERENCES supplier(id),
ADD COLUMN IF NOT EXISTS days_until_stockout DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS avg_daily_usage DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS lead_time_days INTEGER,
ADD COLUMN IF NOT EXISTS product_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS snoozed_until TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS snoozed_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS dismissed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS dismissed_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS dismissal_reason TEXT,
ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS resolution_type resolution_type_enum,
ADD COLUMN IF NOT EXISTS linked_supplier_order_id UUID REFERENCES supplier_order(id),
ADD COLUMN IF NOT EXISTS linked_stock_adjustment_id UUID REFERENCES stock_adjustment(id),
ADD COLUMN IF NOT EXISTS notified_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS notification_channels JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS state_transition_log JSONB DEFAULT '[]'::jsonb;

-- Create new tables
CREATE TABLE notification_preference (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id VARCHAR(100),
    channels JSONB NOT NULL DEFAULT '["in_app"]'::jsonb,
    severity_threshold alert_severity_enum NOT NULL DEFAULT 'warning',
    frequency VARCHAR(20) NOT NULL DEFAULT 'immediate',
    quiet_hours JSONB,
    category_overrides JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, user_id)
);

CREATE TABLE notification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    alert_id UUID NOT NULL REFERENCES reorder_alert(id),
    channel VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    recipient VARCHAR(255),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ
);

CREATE TABLE webhook_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    endpoint_url VARCHAR(500) NOT NULL,
    secret_key VARCHAR(255),
    trigger_severity alert_severity_enum NOT NULL DEFAULT 'warning',
    trigger_channels JSONB NOT NULL DEFAULT '["low_stock"]'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    total_deliveries INTEGER DEFAULT 0,
    failed_deliveries INTEGER DEFAULT 0,
    last_delivery_at TIMESTAMPTZ
);
```

### Phase 3: Backfill Data (Optional, for existing alerts)

```sql
-- Backfill product_code
UPDATE reorder_alert ra
SET product_code = p.code
FROM product p
WHERE ra.product_id = p.id AND ra.product_code IS NULL;

-- Backfill severity (using corrected logic)
UPDATE reorder_alert
SET severity = 
    CASE 
        WHEN current_stock = 0 OR (reorder_point > 0 AND current_stock < reorder_point * 0.25) 
        THEN 'critical'::alert_severity_enum
        WHEN reorder_point > 0 AND current_stock < reorder_point 
        THEN 'warning'::alert_severity_enum
        ELSE 'info'::alert_severity_enum
    END
WHERE severity IS NULL;

-- Backfill updated_at
UPDATE reorder_alert SET updated_at = created_at WHERE updated_at IS NULL;
```

### Phase 4: Add Constraints (After backfill)

```sql
-- Add NOT NULL constraints after backfill
ALTER TABLE reorder_alert ALTER COLUMN updated_at SET NOT NULL;
ALTER TABLE reorder_alert ALTER COLUMN product_code SET NOT NULL;

-- Add index for snoozed_until queries
CREATE INDEX ix_reorder_alert_snoozed_until ON reorder_alert(snoozed_until) 
WHERE snoozed_until IS NOT NULL;

-- Add indexes for notification_log
CREATE INDEX ix_notification_log_alert_id ON notification_log(alert_id);
CREATE INDEX ix_notification_log_tenant_created ON notification_log(tenant_id, created_at DESC);
```

---

## 7. Indexes Summary

```sql
-- Existing indexes (keep)
CREATE UNIQUE INDEX uq_reorder_alert_tenant_product_warehouse ON reorder_alert(tenant_id, product_id, warehouse_id);
CREATE INDEX ix_reorder_alert_tenant_status_warehouse ON reorder_alert(tenant_id, status, warehouse_id);

-- New indexes
CREATE INDEX ix_reorder_alert_snoozed_until ON reorder_alert(snoozed_until) WHERE snoozed_until IS NOT NULL;
CREATE INDEX ix_reorder_alert_severity ON reorder_alert(severity);
CREATE INDEX ix_reorder_alert_created_at ON reorder_alert(created_at DESC);
CREATE INDEX ix_reorder_alert_linked_supplier_order ON reorder_alert(linked_supplier_order_id) WHERE linked_supplier_order_id IS NOT NULL;

CREATE UNIQUE INDEX uq_notification_pref_tenant_user ON notification_preference(tenant_id, user_id);
CREATE INDEX ix_notification_log_alert_id ON notification_log(alert_id);
CREATE INDEX ix_notification_log_tenant_created ON notification_log(tenant_id, created_at DESC);

CREATE INDEX ix_webhook_config_tenant_active ON webhook_config(tenant_id, is_active);
```

---

## 8. Related Files to Update

| File | Changes Needed |
|------|----------------|
| `backend/common/models/reorder_alert.py` | Add new fields, new enums |
| `backend/common/models/__init__.py` | Export new models and enums |
| `backend/domains/inventory/schemas.py` | Update Pydantic schemas |
| `backend/domains/inventory/services.py` | Update service functions |
| `backend/domains/inventory/routes.py` | Add new endpoints |
| `src/domain/inventory/types.ts` | Update TypeScript interfaces |
| `src/domain/inventory/hooks/*.ts` | Update hook functions |
| `migrations/` | Add new migration files |

---

*Document created: 2026-04-11*
