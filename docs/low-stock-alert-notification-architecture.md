# Low Stock Alert Notification System Architecture

**Status:** Proposed  
**Created:** 2026-04-11  
**Last Updated:** 2026-04-11

---

## 1. Executive Summary

This document specifies the notification architecture for the UltrERP low stock alert system. Building on the existing event-driven infrastructure (`StockChangedEvent`, `ReorderAlert`), this architecture extends the system to deliver multi-channel notifications with user preferences, tracking, and scalable background processing.

**Key Design Decisions:**
- Leverage existing `StockChangedEvent` → `emit()` dispatcher pattern
- Add new `AlertCreatedEvent` / `AlertEscalatedEvent` for notification triggers
- Notification delivery via background job queue (avoid blocking transactions)
- Per-user preference system with channel routing logic

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           NOTIFICATION SYSTEM ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────────┐     │
│  │ Stock Change  │    │  Alert       │    │     Notification Queue           │     │
│  │ Service       │───▶│  Event       │───▶│  (Background Job Processing)     │     │
│  └──────────────┘    │  Emitter      │    │                                  │     │
│         │            └──────────────┘    │  • Rate limiting                  │     │
│         ▼                       │         │  • Retry with exponential backoff│     │
│  ┌──────────────┐               ▼         │  • Priority queues (CRITICAL first)│     │
│  │ ReorderAlert │    ┌──────────────────┐ │  • Dead letter queue              │     │
│  │ Handler       │──▶│ Notification     │ │  └──────────────────────────────────┘     │
│  └──────────────┘    │  Preference      │ │            │                               │
│         │            │  Resolver         │ │            ▼                               │
│         │            └──────────────────┘ │  ┌──────────────────────────────────┐     │
│         │                       │         │  │      Notification Workers        │     │
│         ▼                       ▼         │  │  ┌─────────┐ ┌─────────┐        │     │
│  ┌──────────────┐    ┌──────────────────┐ │  │  │ In-App  │ │  Email  │        │     │
│  │ ReorderAlert │    │ Notification     │ │  │  │ Worker  │ │ Worker  │        │     │
│  │ Model        │───▶│ Request Builder  │ │  │  └─────────┘ └─────────┘        │     │
│  │ (updated)    │    └──────────────────┘ │  │  ┌─────────┐ ┌─────────┐        │     │
│  └──────────────┘              │           │  │  │  Push   │ │Webhook  │        │     │
│                                │           │  │  │ Worker  │ │ Worker  │        │     │
│                                ▼           │  │  └─────────┘ └─────────┘        │     │
│                      ┌──────────────────┐  │  └──────────────────────────────────┘     │
│                      │ Notification     │  │            │                               │
│                      │ Record (DB)      │  │            ▼                               │
│                      └──────────────────┘  │  ┌──────────────┐ ┌──────────────┐       │
│                                             │  │  Delivery   │ │   Click      │       │
│                                             │  │  Tracker    │ │  Tracker     │       │
│                                             │  └──────────────┘ └──────────────┘       │
│                                             └──────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Model

### 3.1 Notification Preferences

```sql
-- Per-user notification settings
CREATE TABLE notification_preference (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    channel VARCHAR(20) NOT NULL,          -- 'in_app', 'email', 'push', 'webhook', 'sms'
    enabled BOOLEAN DEFAULT true,
    severity_threshold VARCHAR(20) DEFAULT 'INFO',  -- Min severity to trigger this channel
    frequency VARCHAR(20) DEFAULT 'immediate',       -- 'immediate', 'hourly_digest', 'daily_digest'
    quiet_hours_enabled BOOLEAN DEFAULT false,
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    quiet_hours_timezone VARCHAR(50) DEFAULT 'Asia/Taipei',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_user_channel UNIQUE (user_id, channel)
);

CREATE INDEX ix_notification_preference_user ON notification_preference(user_id);
```

### 3.2 Notification Record

```sql
-- Tracks all notification attempts and delivery status
CREATE TABLE notification (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id),
    user_id UUID NOT NULL REFERENCES auth_user(id),
    
    -- Alert reference
    reorder_alert_id UUID REFERENCES reorder_alert(id),
    
    -- Channel & delivery
    channel VARCHAR(20) NOT NULL,           -- 'in_app', 'email', 'push', 'webhook', 'sms'
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'sent', 'delivered', 'failed', 'read'
    
    -- Content
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',            -- {product_code, stock_level, action_url, etc.}
    
    -- Tracking
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    click_url TEXT,
    click_at TIMESTAMPTZ,
    
    -- Retry handling
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    next_retry_at TIMESTAMPTZ,
    
    -- Deduplication
    idempotency_key VARCHAR(100),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_notification_user ON notification(user_id);
CREATE INDEX ix_notification_status ON notification(status);
CREATE INDEX ix_notification_alert ON notification(reorder_alert_id);
CREATE INDEX ix_notification_idempotency ON notification(idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE INDEX ix_notification_pending_retry ON notification(next_retry_at) WHERE status = 'failed' AND retry_count < max_retries;
```

### 3.3 Webhook Configuration

```sql
-- External webhook endpoints for Slack, Teams, etc.
CREATE TABLE webhook_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id),
    name VARCHAR(100) NOT NULL,
    channel_type VARCHAR(20) NOT NULL,     -- 'slack', 'teams', 'generic'
    url TEXT NOT NULL,
    secret VARCHAR(255),                    -- For HMAC signature verification
    enabled BOOLEAN DEFAULT true,
    severity_threshold VARCHAR(20) DEFAULT 'WARNING',
    headers JSONB DEFAULT '{}',
    created_by UUID REFERENCES auth_user(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_webhook_config_tenant ON webhook_config(tenant_id);
```

### 3.4 Alert Escalation Tracking

```sql
-- Tracks escalation state for stale alerts
CREATE TABLE alert_escalation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES reorder_alert(id),
    escalation_level INTEGER DEFAULT 1,     -- 1=first reminder, 2=second, etc.
    escalated_at TIMESTAMPTZ DEFAULT NOW(),
    notification_ids UUID[] DEFAULT '{}',   -- Notifications sent for this escalation
    action_taken VARCHAR(50),               -- 'notified_user', 'escalated_to_manager', 'auto_created_po'
    notes TEXT
);

CREATE INDEX ix_alert_escalation_alert ON alert_escalation(alert_id);
```

---

## 4. Event Model Extensions

### 4.1 New Domain Events

```python
# common/events.py additions

@dataclass(slots=True)
class AlertCreatedEvent(DomainEvent):
    """Fired when a new reorder alert is created."""
    name: str = "alert_created"
    alert_id: uuid.UUID = field(default_factory=uuid.uuid4)
    severity: str = "INFO"                   # 'CRITICAL', 'WARNING', 'INFO'
    product_id: uuid.UUID = field(default_factory=uuid.uuid4)
    warehouse_id: uuid.UUID = field(default_factory=uuid.uuid4)
    current_stock: int = 0
    reorder_point: int = 0


@dataclass(slots=True)
class AlertEscalatedEvent(DomainEvent):
    """Fired when an alert remains unacknowledged beyond threshold."""
    name: str = "alert_escalated"
    alert_id: uuid.UUID = field(default_factory=uuid.uuid4)
    escalation_level: int = 1
    severity: str = "WARNING"


@dataclass(slots=True)
class AlertAcknowledgedEvent(DomainEvent):
    """Fired when user acknowledges an alert."""
    name: str = "alert_acknowledged"
    alert_id: uuid.UUID = field(default_factory=uuid.uuid4)
    acknowledged_by: str = ""
```

### 4.2 Event Flow

```
StockChangedEvent (emitted by stock mutation)
        │
        ▼
┌───────────────────┐
│ handle_reorder_   │  Existing handler
│ alert()           │
└───────────────────┘
        │
        ├──────────────────────┐
        ▼                      ▼
   [Stock restored]      [Alert created/updated]
        │                      │
        │                 AlertCreatedEvent
        │                      │
        │                      ▼
        │            ┌─────────────────────┐
        │            │ Notification        │
        │            │ Preference Resolver │
        │            └─────────────────────┘
        │                      │
        ▼                      ▼
   [No action]         [Enqueue to background queue]
```

---

## 5. Notification Channel Design

### 5.1 Channel Matrix

| Channel | Immediate (CRITICAL) | Batch (WARNING/INFO) | Retry | Rate Limit |
|---------|---------------------|---------------------|-------|------------|
| In-App | ✅ Always | ✅ Digest option | N/A | Unlimited |
| Email | ✅ Optional | ✅ Daily digest | 3 retries | 100/hr/user |
| Push (FCM/APNs) | ✅ Required | ❌ Disabled | 3 retries | 1000/day/app |
| Webhook | ✅ Optional | ✅ Batch webhook | 5 retries | 200/hr/tenant |
| SMS | ⚠️ Optional | ❌ Disabled | 2 retries | 50/day/user |

### 5.2 In-App Notifications

**Implementation:** Integrate with existing React UI notification system

```python
# channels/in_app.py
class InAppChannel(NotificationChannel):
    channel_name = "in_app"
    
    async def send(self, notification: NotificationRequest) -> DeliveryResult:
        # Store in database for real-time UI polling/WebSocket
        record = NotificationRecord(
            user_id=notification.user_id,
            channel=self.channel_name,
            title=notification.title,
            body=notification.body,
            metadata=notification.metadata,
            status=NotificationStatus.DELIVERED,
        )
        await self.db.flush()
        
        # Publish to WebSocket for real-time UI update
        await self.ws_publisher.publish(
            f"notifications:{notification.user_id}",
            {"type": "new_notification", "data": record.to_dict()}
        )
```

### 5.3 Email Notifications

**SMTP Integration:** Use existing email infrastructure (configurable)

```python
# channels/email.py
class EmailChannel(NotificationChannel):
    channel_name = "email"
    rate_limit = RateLimit(limit=100, window=3600)  # 100 per hour
    
    def __init__(self, smtp_config: SMTPConfig):
        self.smtp = SMTP(smtp_config)
    
    async def send(self, notification: NotificationRequest) -> DeliveryResult:
        html_content = self._build_html_email(notification)
        text_content = self._build_text_email(notification)
        
        try:
            await self.smtp.send(
                to=notification.user_email,
                subject=notification.title,
                html=html_content,
                text=text_content,
                headers={
                    "X-Priority": self._map_severity_to_priority(notification.severity),
                    "List-Unsubscribe": f"<{notification.unsubscribe_url}>"
                }
            )
            return DeliveryResult(success=True)
        except SMTPError as e:
            return DeliveryResult(success=False, error=str(e), retryable=True)
```

**Email Template:**
```
Subject: [UltrERP] ⚠️ Low Stock Alert: {product_name}

<html>
<body>
<h2>Low Stock Alert</h2>
<img src="{product_image_url}" alt="{product_name}" />
<table>
  <tr><td>Product:</td><td><strong>{product_code} - {product_name}</strong></td></tr>
  <tr><td>Current Stock:</td><td style="color:red">{current_stock} {unit}</td></tr>
  <tr><td>Safety Stock:</td><td>{reorder_point} {unit}</td></tr>
  <tr><td>Warehouse:</td><td>{warehouse_name}</td></tr>
</table>
<p>
  <a href="{action_url}" class="btn">Create Purchase Order</a>
  <a href="{alert_detail_url}" class="btn btn-secondary">View Details</a>
</p>
</body>
</html>
```

### 5.4 Push Notifications (Firebase/APNs)

```python
# channels/push.py
class PushChannel(NotificationChannel):
    channel_name = "push"
    rate_limit = RateLimit(limit=1000, window=86400)  # 1000 per day
    
    def __init__(self, fcm_config: FCMConfig, apns_config: APNsConfig):
        self.fcm = FCM(fcm_config)
        self.apns = APNs(apns_config)
    
    async def send(self, notification: NotificationRequest) -> DeliveryResult:
        device_tokens = await self._get_user_device_tokens(notification.user_id)
        
        results = []
        for token in device_tokens:
            if token.platform == "ios":
                result = await self._send_apns(token, notification)
            else:
                result = await self._send_fcm(token, notification)
            results.append(result)
        
        # Consider partial success
        return DeliveryResult(
            success=all(r.success for r in results),
            details=results
        )
    
    async def _send_fcm(self, token: DeviceToken, notification: NotificationRequest):
        message = self.fcm.Message(
            token=token.token,
            notification={
                "title": notification.title,
                "body": notification.body[:100],  # FCM limit
            },
            data=self._build_fcm_data(notification),
            android=self._build_android_config(notification.severity),
            apns=self._build_apns_config(notification.severity),
        )
        return await self.fcm.send(message)
```

### 5.5 Webhooks (External Integrations)

```python
# channels/webhook.py
class WebhookChannel(NotificationChannel):
    channel_name = "webhook"
    rate_limit = RateLimit(limit=200, window=3600)  # 200 per hour per tenant
    
    async def send(self, webhook: WebhookConfig, notification: NotificationRequest) -> DeliveryResult:
        payload = self._build_webhook_payload(notification, webhook.channel_type)
        signature = self._generate_signature(payload, webhook.secret)
        
        try:
            response = await self.http_client.post(
                webhook.url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-UltrERP-Timestamp": str(int(time.time())),
                },
                timeout=10.0,
            )
            return DeliveryResult(success=response.status_code < 400)
        except TimeoutError:
            return DeliveryResult(success=False, error="Timeout", retryable=True)
    
    def _build_webhook_payload(self, notification: NotificationRequest, channel_type: str):
        base = {
            "event": "low_stock_alert",
            "timestamp": datetime.now(UTC).isoformat(),
            "alert": notification.metadata,
        }
        
        if channel_type == "slack":
            return {
                "text": f"⚠️ *Low Stock Alert*\n*{notification.title}*\n{notification.body}",
                "blocks": self._build_slack_blocks(notification),
            }
        elif channel_type == "teams":
            return {
                "@type": "MessageCard",
                "themeColor": self._severity_to_color(notification.severity),
                "summary": notification.title,
                "sections": [{
                    "activityTitle": notification.title,
                    "facts": self._build_teams_facts(notification),
                }]
            }
        return base
```

### 5.6 SMS (Optional - Critical Only)

```python
# channels/sms.py
class SMSChannel(NotificationChannel):
    channel_name = "sms"
    rate_limit = RateLimit(limit=50, window=86400)  # 50 per day
    
    # Only for CRITICAL severity stockouts
    MIN_SEVERITY = "CRITICAL"
    
    async def send(self, notification: NotificationRequest) -> DeliveryResult:
        if notification.severity != "CRITICAL":
            return DeliveryResult(success=True, skipped=True)
        
        phone = await self._get_user_phone(notification.user_id)
        if not phone:
            return DeliveryResult(success=False, error="No phone number")
        
        message = self._truncate_sms(notification)
        return await self.sms_provider.send(phone, message)
```

---

## 6. Notification Triggering Logic

### 6.1 Trigger Conditions

```python
# services/notification_trigger.py
class NotificationTriggerService:
    
    async def trigger_for_alert(self, alert: ReorderAlert, db: AsyncSession) -> None:
        """Determine notification strategy based on alert state."""
        
        # Get notification recipients
        recipients = await self._get_recipients(alert, db)
        
        for user in recipients:
            preferences = await self._get_user_preferences(user.id, db)
            
            # Filter by user preferences
            channels = self._resolve_channels(preferences, alert.severity)
            
            for channel in channels:
                # Check quiet hours
                if self._is_quiet_hours(user, preferences, channel):
                    continue
                
                # Determine timing
                timing = self._resolve_timing(preferences, alert.severity)
                
                await self.queue.enqueue(
                    NotificationJob(
                        user_id=user.id,
                        alert_id=alert.id,
                        channel=channel,
                        severity=alert.severity,
                        timing=timing,
                        metadata=self._build_metadata(alert),
                    ),
                    priority=self._severity_to_priority(alert.severity),
                )
    
    def _resolve_channels(self, preferences: list[NotificationPreference], severity: str) -> list[str]:
        """Resolve enabled channels for this severity."""
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
    
    def _is_quiet_hours(self, user: User, preferences: list, channel: str) -> bool:
        """Check if current time is within user's quiet hours for this channel."""
        # Implementation checks user timezone, quiet_hours_start/end
        pass
```

### 6.2 Escalation Logic

```python
# services/escalation.py
class EscalationService:
    STALE_THRESHOLD_HOURS = 24
    
    async def check_escalations(self, db: AsyncSession) -> None:
        """Cron job: check for stale alerts needing escalation."""
        
        stale_alerts = await self._get_stale_alerts(db)
        
        for alert in stale_alerts:
            last_escalation = await self._get_last_escalation(alert.id, db)
            
            if last_escalation and self._recently_escalated(last_escalation):
                continue
            
            escalation_level = (last_escalation.escalation_level + 1) if last_escalation else 1
            
            await self._escalate_alert(alert, escalation_level, db)
            await emit(AlertEscalatedEvent(
                alert_id=alert.id,
                escalation_level=escalation_level,
                severity=alert.severity,
            ), db)
    
    async def _escalate_alert(self, alert: ReorderAlert, level: int, db: AsyncSession) -> None:
        """Create escalation record and potentially notify managers."""
        
        escalation = AlertEscalation(
            alert_id=alert.id,
            escalation_level=level,
            action_taken=self._get_escalation_action(level),
        )
        db.add(escalation)
        
        # For high escalation levels, notify managers
        if level >= 3:
            managers = await self._get_managers(alert.tenant_id, db)
            for manager in managers:
                await self.queue.enqueue(
                    NotificationJob(
                        user_id=manager.id,
                        alert_id=alert.id,
                        channel="email",
                        title=f"[ESCALATION {level}] {alert.product.name} Stockout",
                        escalation_level=level,
                    ),
                    priority=1,  # Highest priority
                )
```

### 6.3 Batch Processing

```python
# services/digest.py
class DigestService:
    """Aggregate notifications into digest format."""
    
    async def build_daily_digest(self, user_id: uuid.UUID, db: AsyncSession) -> DigestEmail:
        """Build daily digest email for user."""
        
        pending_alerts = await self._get_pending_alerts_for_user(user_id, db)
        
        if not pending_alerts:
            return None
        
        return DigestEmail(
            subject=f"UltrERP Daily Digest - {len(pending_alerts)} alerts",
            alerts_by_severity=self._group_by_severity(pending_alerts),
            action_required=len([a for a in pending_alerts if a.severity == "CRITICAL"]),
        )
```

---

## 7. Queue Architecture

### 7.1 Background Job Processing

```python
# queue/notification_queue.py
from enum import Enum
from uuid import UUID

class JobPriority(Enum):
    CRITICAL = 0      # Stockout - immediate
    HIGH = 1          # CRITICAL alert
    NORMAL = 2        # WARNING alert
    LOW = 3           # INFO alert / digest
    BATCH = 4         # Daily digest

@dataclass
class NotificationJob:
    job_id: UUID = field(default_factory=uuid.uuid4)
    user_id: UUID
    alert_id: UUID
    channel: str
    severity: str
    timing: str = "immediate"
    priority: JobPriority = JobPriority.NORMAL
    idempotency_key: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    def __post_init__(self):
        if not self.idempotency_key:
            self.idempotency_key = f"{self.alert_id}:{self.user_id}:{self.channel}"
```

### 7.2 Queue Implementation

```python
# queue/manager.py
class NotificationQueue:
    """In-memory queue with database persistence for reliability."""
    
    def __init__(self, db: AsyncSession, redis_url: str | None = None):
        self.db = db
        self.redis = Redis.from_url(redis_url) if redis_url else None
        
        # Priority queues (using Redis sorted sets or in-memory)
        self._queues: dict[JobPriority, asyncio.PriorityQueue] = {
            priority: asyncio.PriorityQueue() for priority in JobPriority
        }
        self._workers: list[Worker] = []
    
    async def enqueue(self, job: NotificationJob, priority: JobPriority | None = None) -> str:
        """Add job to queue with deduplication check."""
        
        # Check idempotency - don't send duplicate notifications
        if await self._is_duplicate(job.idempotency_key):
            return job.job_id
        
        job.priority = priority or self._severity_to_priority(job.severity)
        
        if self.redis:
            await self.redis.zadd(
                f"notification_queue:{priority.name}",
                job.job_id.hex,
                job.priority.value + time.time()
            )
            await self.redis.setex(f"idempotency:{job.idempotency_key}", 3600, "1")
        else:
            await self._queues[job.priority].put((job.priority.value, job))
        
        return job.job_id
    
    async def dequeue(self, timeout: float = 1.0) -> NotificationJob | None:
        """Get next job from highest priority queue."""
        
        for priority in JobPriority:
            if self.redis:
                job_id = await self.redis.zpopmin(f"notification_queue:{priority.name}")
                if job_id:
                    return await self._load_job(job_id)
            else:
                try:
                    _, job = await asyncio.wait_for(
                        self._queues[priority].get(),
                        timeout=timeout
                    )
                    return job
                except asyncio.TimeoutError:
                    continue
        return None
```

### 7.3 Retry Logic with Exponential Backoff

```python
# queue/retry.py
class RetryPolicy:
    MAX_RETRIES = {
        "email": 3,
        "push": 3,
        "webhook": 5,
        "sms": 2,
    }
    
    BACKOFF_BASE = {
        "email": 60,      # 1 min, 5 min, 25 min
        "push": 300,      # 5 min, 25 min, 125 min
        "webhook": 30,    # 30 sec, 2.5 min, 12.5 min
        "sms": 300,
    }
    
    @classmethod
    def get_next_retry_at(cls, channel: str, retry_count: int) -> datetime:
        """Calculate next retry time using exponential backoff."""
        base = cls.BACKOFF_BASE.get(channel, 60)
        delay = base * (2 ** retry_count)
        return datetime.now(UTC) + timedelta(seconds=delay)
    
    @classmethod
    def should_retry(cls, channel: str, retry_count: int, error: str) -> bool:
        """Determine if job should be retried."""
        if retry_count >= cls.MAX_RETRIES.get(channel, 3):
            return False
        
        # Don't retry on certain errors
        non_retryable = ["invalid_email", "unsubscribed", "permission_denied"]
        if any(e in error.lower() for e in non_retryable):
            return False
        
        return True
```

### 7.4 Rate Limiting

```python
# queue/rate_limiter.py
class TokenBucketRateLimiter:
    """Token bucket algorithm for rate limiting."""
    
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window  # seconds
        self.tokens = limit
        self.last_refill = time.time()
    
    async def acquire(self, key: str, tokens: int = 1) -> bool:
        """Acquire tokens, return True if allowed."""
        await self._refill(key)
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            await self._save_state(key)
            return True
        return False
    
    async def _refill(self, key: str) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        refill_count = (elapsed / self.window) * self.limit
        self.tokens = min(self.limit, self.tokens + refill_count)
        self.last_refill = now
```

---

## 8. API Endpoints

### 8.1 User Preferences API

```
GET    /api/v1/users/{user_id}/notification-preferences
POST   /api/v1/users/{user_id}/notification-preferences
PUT    /api/v1/users/{user_id}/notification-preferences/{channel}
DELETE /api/v1/users/{user_id}/notification-preferences/{channel}
```

**Request/Response:**
```json
// PUT /api/v1/users/{user_id}/notification-preferences/email
{
  "enabled": true,
  "severity_threshold": "WARNING",
  "frequency": "daily_digest",
  "quiet_hours_enabled": true,
  "quiet_hours_start": "22:00",
  "quiet_hours_end": "08:00",
  "quiet_hours_timezone": "Asia/Taipei"
}
```

### 8.2 Notification History API

```
GET    /api/v1/users/{user_id}/notifications
GET    /api/v1/users/{user_id}/notifications/{notification_id}
POST   /api/v1/users/{user_id}/notifications/{notification_id}/read
POST   /api/v1/users/{user_id}/notifications/mark-all-read
```

### 8.3 Webhook Management API

```
GET    /api/v1/tenants/{tenant_id}/webhooks
POST   /api/v1/tenants/{tenant_id}/webhooks
PUT    /api/v1/tenants/{tenant_id}/webhooks/{webhook_id}
DELETE /api/v1/tenants/{tenant_id}/webhooks/{webhook_id}
POST   /api/v1/tenants/{tenant_id}/webhooks/{webhook_id}/test
```

### 8.4 Admin/Debug APIs

```
GET    /api/v1/admin/notifications/queue-stats
POST   /api/v1/admin/notifications/retry-failed
GET    /api/v1/admin/notifications/{notification_id}/status
```

---

## 9. Notification Content

### 9.1 Content Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{product_name}}` | Product display name | 三角皮帶 C-240 |
| `{{product_code}}` | Product code | PC240-C240 |
| `{{product_image_url}}` | Product image URL | https://cdn.ultrerp.com/... |
| `{{current_stock}}` | Current stock level | 25 |
| `{{reorder_point}}` | Safety stock level | 50 |
| `{{unit}}` | Stock unit | 條 |
| `{{warehouse_name}}` | Warehouse name | 總倉 |
| `{{severity_label}}` | Severity display | 緊急補貨 |
| `{{suggested_quantity}}` | Suggested reorder qty | 100 |
| `{{supplier_name}}` | Primary supplier | 昌宏實業 |
| `{{action_url}}` | Create PO direct link | /purchases/new?product_id=... |
| `{{alert_detail_url}}` | Alert detail page | /inventory/alerts/{id} |
| `{{unsubscribe_url}}` | Notification settings link | /settings/notifications |

### 9.2 Severity-Specific Content

**CRITICAL (Stockout):**
```
Title: ⚠️ [URGENT] {product_name} 已缺貨！
Body: 產品 {product_code} 目前庫存為 0，低於安全存量 {reorder_point}。
      建議立即建立採購單。
```

**WARNING:**
```
Title: 🔶 低庫存警示：{product_name}
Body: 產品 {product_code} 目前在庫 {current_stock} {unit}，
      已低於安全存量 {reorder_point} {unit}。
```

**INFO:**
```
Title: ℹ️ 庫存注意：{product_name}
Body: 產品 {product_code} 庫存偏低，目前 {current_stock} {unit}。
```

---

## 10. Tracking & Analytics

### 10.1 Delivery Status Tracking

```python
# Tracking flow:
# 1. enqueue() → notification.created_at
# 2. worker picks up → notification.status = 'sent', sent_at = now()
# 3. delivery confirmed → notification.status = 'delivered', delivered_at = now()
# 4. user opens app → notification.status = 'read', read_at = now()
# 5. user clicks → notification.click_url = url, click_at = now()

# Event sequence:
async def track_delivery(notification_id: UUID, event: DeliveryEvent, db: AsyncSession):
    notification = await db.get(Notification, notification_id)
    
    if event == DeliveryEvent.SENT:
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(UTC)
    elif event == DeliveryEvent.DELIVERED:
        notification.status = NotificationStatus.DELIVERED
        notification.delivered_at = datetime.now(UTC)
    elif event == DeliveryEvent.READ:
        notification.status = NotificationStatus.READ
        notification.read_at = datetime.now(UTC)
    elif event == DeliveryEvent.CLICKED:
        notification.click_url = event.url
        notification.click_at = datetime.now(UTC)
```

### 10.2 Metrics to Track

| Metric | Description | Aggregation |
|--------|-------------|-------------|
| `notification_sent_total` | Total notifications sent | by channel, severity |
| `notification_delivered_total` | Successfully delivered | by channel |
| `notification_failed_total` | Failed deliveries | by channel, error_type |
| `notification_read_total` | Read notifications | by channel |
| `notification_click_total` | Clicked notifications | by channel |
| `notification_retry_total` | Retry attempts | by channel |
| `delivery_latency_seconds` | Time from send to delivery | p50, p95, p99 |
| `queue_depth` | Pending jobs in queue | by priority |

---

## 11. Security Considerations

### 11.1 Data Protection

- **PII Minimization:** Notification metadata should not include sensitive product cost data
- **Email Encryption:** Use TLS for SMTP connections
- **Webhook Security:** HMAC signature verification for incoming webhooks
- **Audit Logging:** Log all notification preferences changes

### 11.2 Unsubscribe Compliance

- Every email notification must include functional unsubscribe link
- Respect unsubscribe immediately, no retries
- Track unsubscribe events to prevent future sends

### 11.3 Rate Limiting Protection

- Per-user rate limits prevent notification spam
- Per-tenant webhook rate limits prevent abuse
- Circuit breaker for external services (email, SMS providers)

---

## 12. Implementation Phases

### Phase 1: Core Notification Infrastructure
- [ ] Database models (notification_preference, notification, webhook_config)
- [ ] Notification channels: In-App, Email
- [ ] Basic queue with retry
- [ ] User preferences API

### Phase 2: Multi-Channel Expansion
- [ ] Push notifications (FCM)
- [ ] Webhook integrations (Slack, Teams)
- [ ] Rate limiting implementation
- [ ] Webhook management API

### Phase 3: Intelligence & Analytics
- [ ] Escalation logic (>24h stale alerts)
- [ ] Daily digest feature
- [ ] Notification tracking & metrics
- [ ] Click-through analytics

### Phase 4: Advanced Features
- [ ] SMS notifications (CRITICAL only)
- [ ] Machine learning for optimal timing
- [ ] Notification batching optimizations
- [ ] Advanced analytics dashboard

---

## 13. Dependencies

| Component | Technology | Notes |
|-----------|------------|-------|
| Queue Backend | Redis (optional) or in-memory | Redis for production scale |
| Email | SMTP / SendGrid / SES | Configurable provider |
| Push Notifications | Firebase Cloud Messaging, APNs | Platform-specific |
| SMS | Twilio / AWS SNS | Optional, for CRITICAL alerts |
| HTTP Client | httpx | For webhook delivery |

---

## 14. Configuration

```python
# common/config.py additions
class NotificationSettings(BaseSettings):
    # Email
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "alerts@ultrerp.com"
    
    # Push Notifications
    fcm_server_key: str = ""
    apns_key_id: str = ""
    apns_team_id: str = ""
    apns_key_path: str = ""
    
    # Queue
    redis_url: str | None = None
    queue_workers: int = 4
    
    # Rate Limits (per hour by default)
    email_rate_limit: int = 100
    push_rate_limit: int = 1000
    webhook_rate_limit: int = 200
    sms_rate_limit: int = 50
    
    # Escalation
    escalation_check_interval_minutes: int = 60
    stale_alert_threshold_hours: int = 24
```

---

## Appendix A: Database Schema Summary

```sql
-- Core Tables
notification_preference     -- Per-user channel settings
notification                -- Notification records with tracking
webhook_config              -- External webhook endpoints
alert_escalation            -- Escalation history

-- Enums
alert_status_enum            -- pending, acknowledged, resolved (existing)
notification_channel_enum    -- in_app, email, push, webhook, sms
notification_status_enum     -- pending, sent, delivered, failed, read
severity_enum                -- CRITICAL, WARNING, INFO (existing)
```

---

## Appendix B: Event Flow Sequence

```
t=0     StockChangedEvent emitted (e.g., stock decreases to 15)
t=1     handle_reorder_alert() creates/updates ReorderAlert (status=PENDING, severity=WARNING)
t=2     AlertCreatedEvent emitted
t=3     NotificationTriggerService resolves user preferences
t=4     Jobs enqueued to background queue
t=5     Email worker picks up job
t=6     SMTP sends email
t=7     Notification.status = 'sent', sent_at = now()
t=8     Email delivered to inbox
t=9     Notification.status = 'delivered', delivered_at = now()
t=10    User reads email
t=11    Notification.status = 'read', read_at = now()
t=12    User clicks "Create PO" link
t=13    Notification.click_url = url, click_at = now()

OR for escalation:
t=24h   EscalationService detects unacknowledged CRITICAL alert
t=24h   AlertEscalatedEvent emitted
t=24h   Notification sent to manager
t=48h   If still unacknowledged, auto-create draft PO
```

---

## Appendix C: File Structure

```
backend/
├── common/
│   ├── events.py                    # Event definitions (updated)
│   └── config.py                    # Notification settings
├── domains/
│   ├── notifications/               # NEW: Notification domain
│   │   ├── __init__.py
│   │   ├── models.py                # Notification, WebhookConfig, Escalation
│   │   ├── schemas.py               # API schemas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── trigger.py           # NotificationTriggerService
│   │   │   ├── escalation.py        # EscalationService
│   │   │   └── digest.py            # DigestService
│   │   ├── routes.py                # API endpoints
│   │   ├── handlers.py              # Event handlers
│   │   └── workers/
│   │       ├── __init__.py
│   │       ├── base.py              # BaseWorker
│   │       ├── email.py             # EmailWorker
│   │       ├── push.py             # PushWorker
│   │       ├── webhook.py           # WebhookWorker
│   │       └── sms.py               # SMSWorker
│   ├── channels/                     # NEW: Channel implementations
│   │   ├── __init__.py
│   │   ├── base.py                  # NotificationChannel ABC
│   │   ├── in_app.py                # InAppChannel
│   │   ├── email.py                # EmailChannel
│   │   ├── push.py                 # PushChannel
│   │   ├── webhook.py              # WebhookChannel
│   │   └── sms.py                  # SMSChannel
│   ├── queue/                       # NEW: Queue infrastructure
│   │   ├── __init__.py
│   │   ├── manager.py               # NotificationQueue
│   │   ├── retry.py                 # RetryPolicy
│   │   └── rate_limiter.py          # TokenBucketRateLimiter
│   └── inventory/
│       ├── handlers.py              # Updated to emit AlertCreatedEvent
│       └── services.py              # Updated to include notification trigger
└── migrations/
    └── versions/
        ├── add_notification_tables.py
        ├── add_notification_preferences.py
        ├── add_alert_escalation.py
        └── add_webhook_config.py
```

---

**Document Version:** 1.0  
**Author:** Architect Agent  
**Review Status:** Draft for team review
