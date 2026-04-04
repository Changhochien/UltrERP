# Story 9.3: LINE Order Confirmation

Status: completed

## Story

As a system,
I want to confirm order receipt via LINE to customers,
so that they know their order was received and is being processed.

## Acceptance Criteria

**AC1:** Confirmation message sent after order creation
**Given** a customer submits an order via LINE BOT (Story 9.2)
**When** the order is parsed and created successfully
**Then** a confirmation message is sent to the customer via LINE
**And** the message includes: order number, item list with quantities, estimated processing note

**AC2:** Confirmation uses reply_message when possible
**Given** the order is created within the webhook handler flow
**When** the reply token is still valid (up to 20 minutes after webhook event per LINE API spec)
**Then** the system uses `reply_message` (free, no quota cost)
**And** if reply fails (token expired), falls back to `push_message`

**AC3:** Confirmation message format is clear and informative
**Given** an order is created
**When** the confirmation is sent
**Then** the message format is:
```
✅ Order Received: {order_number}

Items:
• {description} × {quantity}
• {description} × {quantity}

Total: NT${total_amount}

-- or for LINE BOT draft orders --

Total: Pricing pending (staff will confirm)
Status: Pending

We'll process your order shortly. Thank you!
```

**AC4:** Failed order creation sends error reply
**Given** a customer submits a LINE message that is parsed as an order
**When** order creation fails (validation error, stock issue, etc.)
**Then** a friendly error reply is sent explaining the issue
**And** the customer is advised to try again or contact staff

**AC5:** Backend tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass
**And** LINE confirmation tests are added (≥ 6 tests)

## Tasks / Subtasks

- [x] **Task 1: Create confirmation message formatter** (AC1, AC3)
  - [ ] Create `backend/domains/line/confirmation.py`:
    ```python
    """
    Format LINE confirmation messages for orders.
    """
    from __future__ import annotations

    from dataclasses import dataclass
    from decimal import Decimal


    @dataclass
    class OrderLineInfo:
        description: str   # from OrderLine.description (product name)
        quantity: Decimal   # from OrderLine.quantity (Numeric(18,3))


    _MAX_LINE_MESSAGE_CHARS = 5000


    def format_order_confirmation(
        *,
        order_number: str,
        lines: list[OrderLineInfo],
        total_amount: Decimal | None,
    ) -> str:
        """Format order confirmation message text.

        For LINE BOT draft orders, total_amount may be 0 (unit_price=0).
        In that case, show 'Pricing pending' instead of NT$0.
        Truncates to LINE's 5,000 character limit.
        """
        items_text = "\n".join(
            f"• {line.description} × {line.quantity:g}"
            for line in lines
        )
        # LINE BOT draft orders have unit_price=0, so total=0
        if total_amount and total_amount > 0:
            total_line = f"Total: NT${total_amount:,.2f}"
        else:
            total_line = "Total: Pricing pending (staff will confirm)"
        message = (
            f"✅ Order Received: {order_number}\n\n"
            f"Items:\n{items_text}\n\n"
            f"{total_line}\n"
            f"Status: Pending\n\n"
            f"We'll process your order shortly. Thank you!"
        )
        if len(message) > _MAX_LINE_MESSAGE_CHARS:
            message = message[:_MAX_LINE_MESSAGE_CHARS - 3] + "..."
        return message


    def format_order_error(error_message: str) -> str:
        """Format order creation failure message."""
        return (
            f"❌ Order could not be created\n\n"
            f"Reason: {error_message}\n\n"
            f"Please check your order and try again, "
            f"or contact our staff for assistance."
        )


    def format_parse_help() -> str:
        """Format help message for unparseable input."""
        return (
            "📋 To place an order, send a message like:\n\n"
            "商品A x 3, 商品B x 5\n\n"
            "or\n\n"
            "ProductA 3\n"
            "ProductB 5\n\n"
            "Each item should have a product name and quantity."
        )


    def format_unregistered_user() -> str:
        """Message for LINE users not linked to a customer account."""
        return (
            "👤 Your LINE account is not linked to a customer account.\n\n"
            "Please contact our staff to register your LINE account "
            "before placing orders."
        )
    ```

- [x] **Task 2: Create reply/push message helper** (AC2)
  - [ ] Add to `backend/domains/line/client.py`:
    ```python
    async def reply_or_push_message(
        reply_token: str | None,
        user_id: str,
        text: str,
    ) -> bool:
        """
        Reply using reply_token if available, fall back to push_message.

        reply_token is free (no quota cost) but expires up to 20 minutes after the webhook event (per LINE API spec).
        push_message is always available but counts against monthly quota.
        """
        if reply_token:
            success = await _reply_text_message(reply_token, text)
            if success:
                return True
            logger.warning("Reply failed (token expired?), falling back to push")

        return await push_text_message(user_id, text)


    async def _reply_text_message(reply_token: str, text: str) -> bool:
        """Reply with text message using reply token."""
        async with get_line_api() as api:
            if api is None:
                return False
            try:
                await api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text=text)],
                    )
                )
                return True
            except Exception:
                logger.exception("LINE reply_message failed")
                return False
    ```
  - [ ] Add `ReplyMessageRequest` to imports in `client.py`:
    ```python
    from linebot.v3.messaging import (
        AsyncApiClient,
        AsyncMessagingApi,
        Configuration,
        PushMessageRequest,
        ReplyMessageRequest,  # NEW
        TextMessage,
    )
    ```

- [x] **Task 3: Integrate confirmation into webhook flow** (AC1, AC2, AC4)
  - [ ] In `backend/domains/line/webhook.py`, after order creation:
    1. On success: Build `OrderLineInfo` list from `order.lines` using `line.description` and `line.quantity`
    2. Format confirmation with `format_order_confirmation(order_number=order.order_number, lines=..., total_amount=order.total_amount)`
    3. Call `reply_or_push_message(reply_token, user_id, confirmation_text)`
    4. On parse failure: `reply_or_push_message(reply_token, user_id, format_parse_help())`
    5. On unregistered user: `reply_or_push_message(reply_token, user_id, format_unregistered_user())`
    6. On order creation error: `reply_or_push_message(reply_token, user_id, format_order_error(str(e)))`
  - [ ] ⚠️ The reply_token and user_id come from the webhook event:
    ```python
    reply_token = event.reply_token
    user_id = event.source.user_id
    ```
  - [ ] ⚠️ Building OrderLineInfo from Order model:
    ```python
    # Order.lines is eagerly/lazily loaded OrderLine list
    # Use line.description (already set to product name by Story 9.2)
    line_infos = [
        OrderLineInfo(description=line.description, quantity=line.quantity)
        for line in order.lines
    ]
    ```

- [x] **Task 4: Create confirmation tests** (AC1, AC2, AC3, AC4, AC5)
  - [ ] Create `backend/tests/test_line_confirmation.py`:
    - Test: `format_order_confirmation` produces expected format with normal total
    - Test: `format_order_confirmation` shows "Pricing pending" when total_amount is 0 (draft orders)
    - Test: `format_order_confirmation` shows "Pricing pending" when total_amount is None
    - Test: `format_order_error` produces expected format
    - Test: `format_parse_help` produces expected format
    - Test: `format_unregistered_user` produces expected format
    - Test: `reply_or_push_message` uses reply_token first
    - Test: `reply_or_push_message` falls back to push when reply fails
    - Test: `reply_or_push_message` uses push when no reply_token
    - Test: Quantity Decimal formatting (3.000 → "3", 1.500 → "1.5")
    - Test: Message truncation at 5,000 chars for very large orders
  - [ ] Mock `AsyncMessagingApi.reply_message` and `push_message`
  - [ ] Run full test suite

## Dev Notes

### Architecture Compliance
- **FR36:** "System confirms order receipt via LINE to customer" — this story implements confirmation after LINE BOT order creation.
- **Pattern:** Reply messages are free (no monthly quota impact). Push messages are fallback. Always try reply first.
- **Separation of concerns:** Message formatting in `confirmation.py`, delivery in `client.py`, orchestration in `webhook.py`.

### Critical Warnings
- ⚠️ Reply tokens expire approximately 20 minutes after the webhook event (LINE API spec). If order creation takes longer, the reply will fail. The fallback to `push_message` handles this.
- ⚠️ `reply_message` can only be used once per webhook event. If multiple replies are needed, only the first succeeds.
- ⚠️ LINE message text limit is 5,000 characters. For large orders with many items, consider truncating the item list.
- ⚠️ `push_message` requires the user's LINE user ID — get from `event.source.user_id` during webhook processing.
- ⚠️ Do NOT use `reply_message` for notifications triggered outside webhook context (e.g., order status updates). Those must use `push_message`.
- ⚠️ Use `linebot.v3.messaging.ReplyMessageRequest` — NOT `linebot.models.TextSendMessage` (v2 legacy).
- ⚠️ **OrderLine.quantity is Decimal(18,3)** not int. Use `:g` format spec to strip trailing zeros (e.g., `Decimal("3.000")` → `"3"`).
- ⚠️ **LINE BOT draft orders have unit_price=0** (Story 9.2). The `total_amount` will be `Decimal("0.00")`. Show 'Pricing pending' instead of NT$0.
- ⚠️ **Use `line.description` for product names** in confirmation — no separate product lookup needed. Story 9.2 sets `description` = product name.

### Project Structure Notes
- `backend/domains/line/confirmation.py` — NEW: message formatters
- `backend/domains/line/client.py` — MODIFY: add `reply_or_push_message()`, `_reply_text_message()`
- `backend/domains/line/webhook.py` — MODIFY: integrate confirmation messages into webhook flow
- `backend/tests/test_line_confirmation.py` — NEW: confirmation tests

### Previous Story Intelligence
- **Story 9.1:** Created `backend/domains/line/client.py` with `push_text_message()` and `get_line_api()` context manager
- **Story 9.2:** Created `backend/domains/line/webhook.py` with webhook route and order creation flow, `parser.py` with text parsing
- **Story 9.2:** Event handler provides `event.reply_token` and `event.source.user_id` — these are the inputs for confirmation
- **Story 5.1:** `create_order()` returns `Order` model with `order_number`, `total_amount`, and lazily loaded `lines`
- **OrderLine** model has `description` field (String(500)) — already set to product name by Story 9.2, NO separate product lookup needed
- **IMPORTANT:** For LINE BOT draft orders (Story 9.2), `unit_price=Decimal("0")` so `total_amount` will be `Decimal("0.00")`. The formatter handles this with a 'Pricing pending' message instead of showing NT$0
- **Existing pattern:** `backend/domains/line/client.py` wraps all LINE SDK calls — this story extends it with reply capabilities

### LINE SDK Reference (v3.x)
```python
# Key imports for Story 9.3:
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,   # reply to webhook event
    PushMessageRequest,     # fallback push
    TextMessage,
)
```
- `reply_message`: POST to `/v2/bot/message/reply` — FREE, no quota impact
- `push_message`: POST to `/v2/bot/message/push` — counts against monthly quota
- Reply token validity: up to 20 minutes from webhook event receipt
- Message text limit: 5,000 characters per message
- Max messages per request: 5 message objects

### References
- PRD: FR36 (confirm order receipt via LINE)
- LINE reply_message: https://developers.line.biz/en/reference/messaging-api/#send-reply-message
- LINE push_message: https://developers.line.biz/en/reference/messaging-api/#send-push-message
- Story 9.1: `backend/domains/line/client.py` — LINE client wrapper
- Story 9.2: `backend/domains/line/webhook.py` — webhook handler

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List
- confirmation.py: format_order_confirmation (with 5000-char truncation), format_order_error, format_parse_help, format_unregistered_user
- OrderLineInfo dataclass with description + quantity (Decimal)
- _fmt_qty helper: Decimal('3.000') → '3', Decimal('1.500') → '1.5' via f-format + rstrip
- client.py: added reply_or_push_message (reply first, fallback to push), _reply_text_message, ReplyMessageRequest import
- webhook.py: removed _reply_text, replaced inline messages with formatter functions
- Pricing pending shown for total_amount=0 or None (LINE BOT draft orders)
- Updated 2 Story 9.2 webhook tests to mock reply_or_push_message instead of removed _reply_text
- 11 new tests, 431 total pass, ruff clean

### Change Log
- 2026-04-03: Story 9.3 implemented — LINE order confirmation with formatters and reply/push helper

### File List
- backend/domains/line/confirmation.py (NEW — message formatters)
- backend/domains/line/client.py (MODIFIED — reply_or_push_message, _reply_text_message, ReplyMessageRequest)
- backend/domains/line/webhook.py (MODIFIED — removed _reply_text, integrated confirmation formatters)
- backend/tests/test_line_confirmation.py (NEW — 11 tests)
- backend/tests/test_line_webhook.py (MODIFIED — updated 2 tests for reply_or_push_message)

