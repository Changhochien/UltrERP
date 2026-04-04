# Story 9.1: LINE Notification on New Order

Status: completed

## Story

As a staff member,
I want to receive LINE notifications when new orders are created,
so that I can respond quickly to customer orders.

## Acceptance Criteria

**AC1:** LINE push notification sent on order creation
**Given** a new order is created via API
**When** the order is saved successfully
**Then** a LINE push message is sent to the configured staff group/user
**And** the message includes: order number, customer name, order total, line-item count
**And** the notification does not block order creation (fire-and-forget with error logging)

**AC2:** LINE client configuration via environment variables
**Given** the backend starts
**When** LINE environment variables are set (`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET`, `LINE_STAFF_GROUP_ID`)
**Then** the LINE client is configured and ready to send messages
**And** if variables are missing, the system starts normally but logs a warning and skips notifications

**AC3:** Graceful degradation on LINE API failure
**Given** a LINE notification is triggered
**When** the LINE API call fails (network error, invalid token, rate limit)
**Then** the error is logged with full context (order_number, error details)
**And** the order creation is NOT affected (already committed)
**And** no exception propagates to the caller

**AC4:** Backend tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing 399 tests continue to pass
**And** LINE notification tests are added (≥ 6 tests)

## Tasks / Subtasks

- [x] **Task 1: Add LINE SDK dependency** (AC2)
  - [x] Add `line-bot-sdk>=3.x` to `backend/pyproject.toml` under `[project.dependencies]`
  - [x] Run `pip install -e .` to install

- [x] **Task 2: Add LINE settings to config** (AC2)
  - [ ] Add to `backend/common/config.py` Settings class:
    ```python
    line_channel_access_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LINE_CHANNEL_ACCESS_TOKEN", "line_channel_access_token"),
    )
    line_channel_secret: str | None = Field(  # Used by Story 9.2 for webhook signature verification
        default=None,
        validation_alias=AliasChoices("LINE_CHANNEL_SECRET", "line_channel_secret"),
    )
    line_staff_group_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LINE_STAFF_GROUP_ID", "line_staff_group_id"),
    )
    ```
  - [ ] Note: `line_channel_secret` is not used by this story (push only needs access_token). It is defined here for Story 9.2's `WebhookParser` signature verification. Pre-provisioning in config avoids config changes in 9.2.

- [x] **Task 3: Create LINE domain module** (AC1, AC2, AC3)
  - [x] Create `backend/domains/line/__init__.py`
  - [x] Create `backend/domains/line/client.py`:
    ```python
    """
    LINE Messaging API client wrapper.

    Uses AsyncMessagingApi from line-bot-sdk v3.
    LINE Notify was terminated March 31, 2025 — all notifications
    use LINE Messaging API push_message.
    """
    from __future__ import annotations

    import logging
    from contextlib import asynccontextmanager

    from linebot.v3.messaging import (
        AsyncApiClient,
        AsyncMessagingApi,
        Configuration,
        PushMessageRequest,
        TextMessage,
    )

    from common.config import get_settings

    logger = logging.getLogger(__name__)


    def _get_configuration() -> Configuration | None:
        """Build LINE SDK config from settings. Returns None if unconfigured."""
        settings = get_settings()
        if not settings.line_channel_access_token:
            return None
        return Configuration(access_token=settings.line_channel_access_token)


    @asynccontextmanager
    async def get_line_api():
        """Async context manager yielding AsyncMessagingApi or None."""
        config = _get_configuration()
        if config is None:
            logger.warning("LINE not configured — skipping")
            yield None
            return
        async with AsyncApiClient(config) as api_client:
            yield AsyncMessagingApi(api_client)


    async def push_text_message(to: str, text: str) -> bool:
        """Push a text message. Returns True on success, False on failure."""
        async with get_line_api() as api:
            if api is None:
                return False
            try:
                await api.push_message(
                    PushMessageRequest(
                        to=to,
                        messages=[TextMessage(text=text)],
                    )
                )
                return True
            except Exception:
                logger.exception("LINE push_message failed to=%s", to)
                return False
    ```
  - [x] Verify `AsyncMessagingApi` and `AsyncApiClient` exist in `linebot.v3.messaging`
    (Context7 confirms these are available in line-bot-sdk v3.x)

- [x] **Task 4: Create order notification service** (AC1, AC3)
  - [x] Create `backend/domains/line/notification.py`:
    ```python
    """
    LINE notification service for order events.

    Sends push messages to staff group when orders are created.
    All errors are caught and logged — never blocks order flow.
    """
    from __future__ import annotations

    import logging

    from common.config import get_settings
    from domains.line.client import push_text_message

    logger = logging.getLogger(__name__)


    async def notify_new_order(
        *,
        order_number: str,
        customer_name: str,
        total_amount: str,
        line_count: int,
    ) -> None:
        """Send new-order notification to staff. Fire-and-forget."""
        settings = get_settings()
        group_id = settings.line_staff_group_id
        if not group_id:
            logger.debug("LINE_STAFF_GROUP_ID not set — skipping notification")
            return

        text = (
            f"📦 New Order: {order_number}\n"
            f"Customer: {customer_name}\n"
            f"Items: {line_count}\n"
            f"Total: NT${total_amount}"
        )
        success = await push_text_message(group_id, text)
        if success:
            logger.info("LINE notification sent for order %s", order_number)
        else:
            logger.warning("LINE notification failed for order %s", order_number)
    ```

- [x] **Task 5: Hook notification into order creation route** (AC1, AC3)
  - [ ] In `backend/domains/orders/routes.py`, import and call after order creation:
    ```python
    from domains.line.notification import notify_new_order
    ```
  - [ ] Modify `create_order_endpoint` signature to accept `BackgroundTasks`:
    ```python
    from fastapi import BackgroundTasks

    @router.post(
        "",
        response_model=OrderResponse,
        status_code=201,
    )
    async def create_order_endpoint(
        data: OrderCreate,
        session: DbSession,
        background_tasks: BackgroundTasks,
    ) -> OrderResponse:
        order = await create_order(session, data, tenant_id=TENANT_ID)
        response = _to_order_response(order)
        # response.customer_name is already resolved by _to_order_response
        background_tasks.add_task(
            notify_new_order,
            order_number=order.order_number,
            customer_name=response.customer_name or "Unknown",
            total_amount=str(order.total_amount or 0),
            line_count=len(data.lines),
        )
        return response
    ```
  - [ ] ⚠️ `customer_name`: use `response.customer_name` from `_to_order_response()` — it handles lazy-loaded `order.customer` via `getattr(order, "customer", None) and order.customer.company_name`
  - [ ] ⚠️ `BackgroundTasks` runs after response — the order response is returned immediately
  - [ ] ⚠️ Do NOT pass `session` to the background task — sessions are request-scoped and will be closed

- [x] **Task 6: Create LINE notification tests** (AC1, AC2, AC3, AC4)
  - [ ] Create `backend/tests/test_line_notification.py`:
    - Test: `push_text_message` sends message successfully (mock AsyncMessagingApi)
    - Test: `push_text_message` returns False when LINE unconfigured
    - Test: `push_text_message` returns False and logs on API error
    - Test: `notify_new_order` sends formatted message to staff group
    - Test: `notify_new_order` skips when group_id not set
    - Test: `notify_new_order` handles push failure gracefully
  - [ ] Mock `linebot.v3.messaging.AsyncApiClient` and `AsyncMessagingApi`
  - [ ] Run full test suite: `cd backend && python -m pytest tests/ -v --tb=short`

## Dev Notes

### Architecture Compliance
- **LINE Notify EOL:** LINE Notify was terminated March 31, 2025. The PRD mentions "LINE Notify or Messaging API" (NFR26) — this story uses LINE Messaging API exclusively via `push_message`. The PRD reference to LINE Notify is outdated.
- **Pattern:** Fire-and-forget notification via FastAPI `BackgroundTasks` — order creation is never blocked by LINE API latency or failures.
- **Domain boundary:** New `backend/domains/line/` module owns all LINE integration. Other domains call notification functions, not LINE SDK directly.
- **Config pattern:** Follows existing `common/config.py` pattern with `pydantic_settings` and `AliasChoices` for env var names.

### Critical Warnings
- ⚠️ LINE Notify is DEAD (terminated 2025-03-31). Do NOT use `notify-bot.line.me` or any LINE Notify API endpoints. Use LINE Messaging API `push_message` only.
- ⚠️ `line-bot-sdk` v3 uses `linebot.v3.messaging` namespace — NOT `linebot.api.LineBotApi` (v2 legacy API, deprecated).
- ⚠️ Use `AsyncMessagingApi` + `AsyncApiClient` for async compatibility with FastAPI/asyncpg backend.
- ⚠️ `push_message` requires `to` parameter with a valid LINE user ID, group ID, or room ID — not a phone number.
- ⚠️ All LINE API calls MUST be wrapped in try/except — LINE is an external service that can fail at any time.
- ⚠️ `BackgroundTasks` runs after the response is sent — test carefully that the notification function is self-contained (no session dependency).
- ⚠️ Do NOT pass SQLAlchemy session to the background task — sessions are request-scoped and will be closed.

### Project Structure Notes
- `backend/domains/line/__init__.py` — NEW: domain package
- `backend/domains/line/client.py` — NEW: LINE SDK wrapper
- `backend/domains/line/notification.py` — NEW: order notification service
- `backend/domains/orders/routes.py` — MODIFY: add BackgroundTasks + notify_new_order call
- `backend/common/config.py` — MODIFY: add 3 LINE settings
- `backend/pyproject.toml` — MODIFY: add line-bot-sdk dependency
- `backend/tests/test_line_notification.py` — NEW: notification tests

### Previous Story Intelligence
- **Story 8.1-8.6 pattern:** Domain modules under `backend/domains/{domain}/` with service logic separated from route handlers
- **Config pattern:** `common/config.py` uses `pydantic_settings.BaseSettings` with `Field(default=None, validation_alias=AliasChoices(...))`
- **Test pattern:** Mock external services, assert function behaviors, run full suite
- **Service file naming:** `services.py` (plural) in each domain
- **Import note:** `from common.config import get_settings` for dynamic access, `from common.config import settings` for module-level

### LINE SDK Reference (v3.x)
```python
# Key imports for Story 9.1:
from linebot.v3.messaging import (
    AsyncApiClient,        # async context manager for API client
    AsyncMessagingApi,      # async Messaging API class
    Configuration,          # holds access_token
    PushMessageRequest,     # push message payload
    TextMessage,            # text message type
)
```
- Package: `line-bot-sdk>=3.14` (latest 3.19.0 as of 2026)
- Auth: Channel access token (long-lived or stateless)
- Push message: `POST https://api.line.me/v2/bot/message/push`
- Rate limits: Default 100K push messages/month (free plan has lower limits)

### References
- PRD: FR34 (staff LINE notification), NFR26 (LINE Messaging API)
- Architecture v1: No specific LINE section — this story establishes the pattern
- LINE Messaging API: https://developers.line.biz/en/reference/messaging-api/
- LINE Notify EOL: https://developers.line.biz/en/news/tags/end-of-life/ (terminated 2025-03-31)
- line-bot-sdk-python: https://github.com/line/line-bot-sdk-python

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List
- Installed line-bot-sdk 3.22.0 (latest) via uv
- Created LINE domain module with AsyncMessagingApi client wrapper
- Fire-and-forget notification via BackgroundTasks — order response returns immediately
- Pre-provisioned line_channel_secret in config for Story 9.2 WebhookParser
- Also fixed pre-existing lint issues in routes.py (unsorted imports, unused PaymentTermsCode/confirm_order)
- 6 new tests, 405 total pass, ruff clean

### Change Log
- 2026-04-03: Story 9.1 implemented — LINE Messaging API push notification on order creation

### File List
- backend/pyproject.toml (MODIFIED — added line-bot-sdk>=3.14)
- backend/common/config.py (MODIFIED — added 3 LINE settings)
- backend/domains/line/__init__.py (NEW)
- backend/domains/line/client.py (NEW — async LINE client wrapper)
- backend/domains/line/notification.py (NEW — order notification service)
- backend/domains/orders/routes.py (MODIFIED — BackgroundTasks + notify_new_order)
- backend/tests/test_line_notification.py (NEW — 6 tests)

