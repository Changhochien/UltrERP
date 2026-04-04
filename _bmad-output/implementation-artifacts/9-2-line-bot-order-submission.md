# Story 9.2: LINE BOT — Order Submission

Status: completed

## Story

As a customer,
I want to submit orders via LINE BOT,
so that I can place orders easily through our existing communication channel.

## Acceptance Criteria

**AC1:** Webhook endpoint receives and verifies LINE messages
**Given** a LINE Official Account is configured with webhook URL
**When** a customer sends a message to the BOT
**Then** the system receives the webhook event at `POST /api/v1/line/webhook`
**And** the `X-Line-Signature` header is validated against the channel secret
**And** invalid signatures return 400 (never process unverified requests)

**AC2:** Text message parsed into order draft
**Given** a customer sends a text message with order items
**When** the message format matches supported patterns (e.g., "商品A x 3, 商品B x 5" or "ProductA 3, ProductB 5")
**Then** the system parses product names and quantities from the text
**And** looks up products by name/code using existing `search_products` service
**And** creates a draft order in PENDING status via `create_order` service

**AC3:** Customer-LINE mapping enables order attribution
**Given** a LINE user sends a message
**When** the system receives the webhook with `source.userId`
**Then** the system looks up the LINE user ID in the `line_customer_mappings` table
**And** if found, creates the order linked to that customer
**And** if not found, sends a reply asking the customer to register first

**AC4:** Unparseable messages handled gracefully
**Given** a customer sends a message that cannot be parsed as an order
**When** the parser fails to extract valid products/quantities
**Then** a friendly reply is sent explaining the expected format
**And** no order is created
**And** the event is logged for monitoring

**AC5:** Database migration for LINE customer mapping
**Given** the LINE integration is being set up
**When** the migration runs
**Then** a `line_customer_mappings` table is created with columns:
  - `id` (UUID PK)
  - `tenant_id` (UUID, NOT NULL, indexed — no FK, follows codebase pattern)
  - `line_user_id` (VARCHAR(64), unique per tenant, indexed)
  - `customer_id` (UUID FK to customers)
  - `created_at`, `updated_at` (timestamps)

**AC6:** Backend tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass
**And** LINE BOT tests are added (≥ 10 tests)

## Tasks / Subtasks

- [x] **Task 1: Create Alembic migration for line_customer_mappings** (AC5)
  - [ ] Generate migration:
    ```bash
    cd backend && alembic revision --autogenerate -m "add_line_customer_mappings"
    ```
  - [ ] Table definition:
    ```python
    # Table: line_customer_mappings
    # id: UUID PK (server_default=gen_random_uuid())
    # tenant_id: UUID NOT NULL, indexed (no FK — follows existing codebase pattern)
    # line_user_id: VARCHAR(64) NOT NULL
    # customer_id: UUID NOT NULL, FK → customers.id
    # display_name: VARCHAR(200) NULL  -- LINE display name cache
    # created_at: TIMESTAMP WITH TIME ZONE, server_default=now()
    # updated_at: TIMESTAMP WITH TIME ZONE, server_default=now(), onupdate=now()
    # UNIQUE constraint: (tenant_id, line_user_id)
    ```
  - [ ] Follow existing migration patterns in `migrations/versions/`

- [x] **Task 2: Create LineCustomerMapping SQLAlchemy model** (AC3, AC5)
  - [ ] Create `backend/domains/line/models.py`:
    ```python
    """LINE integration database models."""
    from __future__ import annotations

    import uuid
    from datetime import datetime

    from sqlalchemy import (
        DateTime, ForeignKey, String, UniqueConstraint, func,
    )
    from sqlalchemy.dialects.postgresql import UUID
    from sqlalchemy.orm import Mapped, mapped_column

    from common.database import Base


    class LineCustomerMapping(Base):
        __tablename__ = "line_customer_mappings"
        __table_args__ = (
            UniqueConstraint("tenant_id", "line_user_id", name="uq_line_mapping_tenant_user"),
        )

        id: Mapped[uuid.UUID] = mapped_column(
            UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
        )
        tenant_id: Mapped[uuid.UUID] = mapped_column(
            UUID(as_uuid=True), nullable=False, index=True,
        )
        line_user_id: Mapped[str] = mapped_column(
            String(64), nullable=False,
        )
        customer_id: Mapped[uuid.UUID] = mapped_column(
            UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False,
        )
        display_name: Mapped[str | None] = mapped_column(
            String(200), nullable=True,
        )
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(),
        )
        updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        )
    ```
  - [ ] Import model in a central location so Alembic sees it (check existing pattern)
  - [ ] ⚠️ Follow existing model patterns: `UUID(as_uuid=True)`, `server_default=func.gen_random_uuid()`, timezone-aware timestamps

- [x] **Task 3: Create order text parser** (AC2, AC4)
  - [ ] Create `backend/domains/line/parser.py`:
    ```python
    """
    Parse LINE text messages into order line items.

    Supported formats (product-first):
      - "商品A x 3, 商品B x 5"     (x/X/× separator)
      - "商品A 3\n商品B 5"          (space separator, newline-delimited)
      - "ProductA x3, ProductB x5"  (no space before digit)
      - "商品A=3, 商品B=5"          (equals separator)
      - "商品A:3, 商品B:5"          (colon separator)
      - "商品A*3"                   (asterisk separator)
    Supported formats (quantity-first Chinese):
      - "3個商品A, 5個商品B"         (quantity + 個 + name)

    Returns a list of (product_query, quantity) tuples for product lookup.
    """
    from __future__ import annotations

    import re
    from dataclasses import dataclass


    @dataclass
    class ParsedOrderLine:
        product_query: str  # product name/code to search
        quantity: int


    def parse_order_text(text: str) -> list[ParsedOrderLine]:
        """Parse message text into order lines. Returns empty list if unparseable."""
        lines: list[ParsedOrderLine] = []
        # Split by comma, newline, or 、(Chinese comma)
        segments = re.split(r"[,\n、]+", text.strip())
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            parsed = _parse_segment(segment)
            if parsed:
                lines.append(parsed)
        return lines


    def _parse_segment(segment: str) -> ParsedOrderLine | None:
        """Parse a single segment into a ParsedOrderLine."""
        # Pattern 1: Quantity-first Chinese — "3個商品A"
        match = re.match(r"^(\d+)\s*個\s*(.+)$", segment)
        if match:
            qty = int(match.group(1))
            name = match.group(2).strip()
            if name and qty > 0:
                return ParsedOrderLine(product_query=name, quantity=qty)

        # Pattern 2: "ProductName x Quantity" (x/X/×, with or without spaces)
        match = re.match(r"^(.+?)\s*[xX×]\s*(\d+)$", segment)
        if match:
            name = match.group(1).strip()
            qty = int(match.group(2))
            if name and qty > 0:
                return ParsedOrderLine(product_query=name, quantity=qty)

        # Pattern 3: "ProductName = Quantity" or "ProductName : Quantity" or "ProductName * Quantity"
        match = re.match(r"^(.+?)\s*[=:*]\s*(\d+)$", segment)
        if match:
            name = match.group(1).strip()
            qty = int(match.group(2))
            if name and qty > 0:
                return ParsedOrderLine(product_query=name, quantity=qty)

        # Pattern 4: "ProductName Quantity" (space separator — most ambiguous, try last)
        match = re.match(r"^(.+?)\s+(\d+)$", segment)
        if match:
            name = match.group(1).strip()
            qty = int(match.group(2))
            if name and qty > 0:
                return ParsedOrderLine(product_query=name, quantity=qty)

        return None
    ```
  - [ ] Support Chinese and English text, flexible separators
  - [ ] Return empty list for unparseable input (caller decides how to handle)

- [x] **Task 4: Create LINE webhook route** (AC1, AC2, AC3, AC4)
  - [ ] Create `backend/domains/line/webhook.py`:
    ```python
    """
    LINE webhook endpoint for receiving BOT messages.

    Uses WebhookParser (not WebhookHandler) to avoid sync/async mismatch.
    WebhookParser.parse() verifies signature + returns events list,
    then we process events async in the route function.
    """
    from __future__ import annotations

    import logging
    import re
    from typing import Annotated

    from fastapi import APIRouter, Depends, Request, HTTPException
    from sqlalchemy.ext.asyncio import AsyncSession

    from linebot.v3.webhook import WebhookParser
    from linebot.v3.exceptions import InvalidSignatureError
    from linebot.v3.webhooks import MessageEvent, TextMessageContent

    from common.config import get_settings
    from common.database import get_db

    logger = logging.getLogger(__name__)
    router = APIRouter()
    DbSession = Annotated[AsyncSession, Depends(get_db)]


    def _get_parser() -> WebhookParser | None:
        settings = get_settings()
        if not settings.line_channel_secret:
            return None
        return WebhookParser(settings.line_channel_secret)


    @router.post("/webhook")
    async def line_webhook(request: Request, session: DbSession):
        """Receive LINE webhook events."""
        parser = _get_parser()
        if parser is None:
            raise HTTPException(status_code=503, detail="LINE not configured")

        signature = request.headers.get("X-Line-Signature", "")
        body = (await request.body()).decode("utf-8")

        try:
            events = parser.parse(body, signature)
        except InvalidSignatureError:
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Process events asynchronously (no sync/async mismatch)
        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                await _handle_text_message(event, session)

        return "OK"


    _LINE_USER_ID_RE = re.compile(r"^U[0-9a-f]{32}$")


    async def _handle_text_message(event: MessageEvent, session: AsyncSession):
        """Process a text message event — parse → lookup → create order → reply."""
        user_id = event.source.user_id
        if not user_id or not _LINE_USER_ID_RE.match(user_id):
            logger.warning("Invalid LINE user_id: %s", user_id)
            return
        reply_token = event.reply_token
        text = event.message.text
        # ... (implemented in Task 5)
    ```
  - [ ] ⚠️ Uses `WebhookParser` (NOT `WebhookHandler`) — `parser.parse()` returns `list[Event]` after verifying signature. This is CPU-bound (HMAC + JSON), not I/O, so it's safe to call in an async function.
  - [ ] ⚠️ Do NOT use `WebhookHandler.handle()` — it dispatches to SYNC callbacks, causing async/sync mismatch with our async service layer.
  - [ ] Register webhook router in `backend/app/main.py`:
    ```python
    from domains.line.webhook import router as line_router
    app.include_router(line_router, prefix="/api/v1/line", tags=["LINE"])
    ```

- [x] **Task 5: Implement order creation from parsed message** (AC2, AC3)
  - [ ] In webhook handler, after parsing text:
    1. Look up `LineCustomerMapping` by `(tenant_id, line_user_id)`
    2. If not found → reply with registration instructions
    3. Parse message text with `parse_order_text()`
    4. If empty → reply with format instructions
    5. For each `ParsedOrderLine`, use `search_products()` to find matching product
    6. If any product not found → reply with "product not found: {name}"
    7. Build `OrderCreate` schema with found products
    8. Call `create_order()` service
    9. Reply with confirmation (Story 9.3 handles the confirmation format)
  - [ ] ⚠️ Use `DEFAULT_TENANT_ID` until multi-tenant is implemented
  - [ ] ⚠️ Tax policy: use `TAXABLE_5` default for LINE orders (standard Taiwan 5% VAT)
  - [ ] ⚠️ Payment terms: use `NET_30` default for LINE orders
  - [ ] ⚠️ **`unit_price` handling:** The `Product` model has NO `unit_price` field. `OrderCreateLine` requires `unit_price` (Decimal, ge=0). For LINE BOT draft orders, set `unit_price=Decimal("0")` — staff reviews and updates pricing before confirming. This is valid since `ge=0` allows zero.
  - [ ] ⚠️ **`description` handling:** `OrderCreateLine.description` is required (min_length=1). Use the product name from `search_products()` results as the line description.
  - [ ] ⚠️ `search_products()` returns `list[dict]` with keys: `id`, `code`, `name`, `category`, `status`, `current_stock`, `relevance`. Use `result["id"]` for `product_id` and `result["name"]` for `description`.

- [x] **Task 6: Create LINE BOT tests** (AC1, AC2, AC3, AC4, AC6)
  - [ ] Create `backend/tests/test_line_webhook.py`:
    - Test: webhook rejects missing signature (400)
    - Test: webhook rejects invalid signature (400)
    - Test: webhook returns 503 when LINE not configured
    - Test: valid text message triggers order creation
    - Test: unknown LINE user gets registration reply
  - [ ] Create `backend/tests/test_line_parser.py`:
    - Test: parse "商品A x 3, 商品B x 5" → 2 items (x separator)
    - Test: parse "ProductA 3\nProductB 5" → 2 items (space + newline)
    - Test: parse "商品A=3, 商品B=5" → 2 items (equals separator)
    - Test: parse "商品A:3" → 1 item (colon separator)
    - Test: parse "商品A*3" → 1 item (asterisk separator)
    - Test: parse "3個商品A, 5個商品B" → 2 items (quantity-first Chinese)
    - Test: parse "ProductA x3" → 1 item (no space before digit)
    - Test: parse empty/garbage text → empty list
    - Test: parse quantity 0 → skipped
    - Test: parse mixed Chinese/English separators
  - [ ] Run full test suite

## Dev Notes

### Architecture Compliance
- **FR35:** "Customers can submit orders via LINE BOT (text parsed into Orders module)" — this story implements the full flow from webhook to order creation.
- **Pattern:** Webhook route in domain module, registered on FastAPI app, reuses existing `create_order` service — no duplicate business logic.
- **Tenant scoping:** `DEFAULT_TENANT_ID` used for all LINE-originating orders until Epic 11 (multi-tenant).

### Critical Warnings
- ⚠️ Use `WebhookParser` (from `linebot.v3.webhook`) NOT `WebhookHandler` — WebhookHandler dispatches to SYNC callbacks causing async/sync mismatch. WebhookParser just verifies signature + returns events list.
- ⚠️ LINE `userId` is different from customer ID. Need `line_customer_mappings` table. LINE userIds look like `U1234567890abcdef...` (33 chars, U prefix + 32 hex).
- ⚠️ `X-Line-Signature` verification is mandatory — never process unverified webhooks (HMAC-SHA256 of body with channel secret).
- ⚠️ Reply tokens expire in ~30 seconds. If order creation takes longer, reply will fail. Consider using `push_message` as fallback (Story 9.3 handles this).
- ⚠️ Products are searched by name — the parser extracts text, then `search_products()` does hybrid search. Ambiguous matches need careful handling (use first result or ask for clarification).
- ⚠️ **`OrderCreateLine` required fields:** `product_id` (UUID), `description` (str, min_length=1), `quantity` (Decimal, gt=0), `unit_price` (Decimal, ge=0), `tax_policy_code` (str). The webhook handler must construct this from parsed text + product lookup results.
- ⚠️ **IMPORTANT: `Product` model has NO `unit_price` field.** LINE BOT creates DRAFT orders with `unit_price=Decimal("0")`. Staff reviews and updates pricing before confirming the order. Use product `name` for `description`.
- ⚠️ Do NOT import from `linebot.api` or `linebot.models` — those are v2 legacy. Use `linebot.v3.*` exclusively.
- ⚠️ LINE user_id format: `U[0-9a-f]{32}` — validate this on webhook receipt.

### Project Structure Notes
- `backend/domains/line/models.py` — NEW: LineCustomerMapping model
- `backend/domains/line/parser.py` — NEW: text message parser
- `backend/domains/line/webhook.py` — NEW: webhook route
- `backend/app/main.py` — MODIFY: register LINE webhook router
- `migrations/versions/` — NEW: migration for line_customer_mappings
- `backend/tests/test_line_webhook.py` — NEW: webhook tests
- `backend/tests/test_line_parser.py` — NEW: parser tests

### Previous Story Intelligence
- **Story 9.1:** Creates `backend/domains/line/client.py` and `__init__.py` — this story adds webhook.py, parser.py, models.py to the same domain
- **Story 5.1:** Order creation flow is in `backend/domains/orders/services.py` — `create_order(session, OrderCreate)` returns `Order`
- **Story 5.1:** `OrderCreate` schema is in `backend/domains/orders/schemas.py` — check required fields
- **Story 3.1:** Customer model is in `backend/domains/customers/models.py` — FK target for mapping
- **Story 4.1:** Product search is in `backend/domains/inventory/services.py` — `search_products(session, tenant_id, query)` returns `list[dict]`
- **Existing migration pattern:** Check `migrations/versions/` for UUID PK, tenant_id FK, timestamp conventions
- **Model pattern:** `UUID(as_uuid=True)`, `server_default=func.gen_random_uuid()`, `DateTime(timezone=True)`

### LINE SDK Reference (v3.x)
```python
# Key imports for Story 9.2:
from linebot.v3.webhook import WebhookParser  # NOT WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent,      # user adds BOT as friend
)
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
)
```

### References
- PRD: FR35 (LINE BOT order submission)
- Orders service: `backend/domains/orders/services.py` — `create_order()`
- Orders schema: `backend/domains/orders/schemas.py` — `OrderCreate`
- Product search: `backend/domains/inventory/services.py` — `search_products()`
- Customer model: `backend/domains/customers/models.py`
- LINE Messaging API webhooks: https://developers.line.biz/en/reference/messaging-api/#webhooks
- line-bot-sdk-python (WebhookParser): https://github.com/line/line-bot-sdk-python

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List
- Migration mm333oo33p65: line_customer_mappings table with tenant_id (no FK), unique(tenant_id, line_user_id)
- LineCustomerMapping model follows codebase UUID/timestamp patterns
- Parser supports 4 pattern groups: x/X/×, =/:/* , space, quantity-first (3個商品A)
- WebhookParser for signature verification (not WebhookHandler)
- _handle_text_message: lookup mapping → parse text → search products → create_order
- Draft orders with unit_price=0, TAXABLE_5 default, NET_30 terms
- _reply_text with reply_message → push_message fallback
- LINE user_id regex validation: U[0-9a-f]{32}
- Registered at /api/v1/line/webhook in main.py
- 15 new tests (10 parser + 5 webhook), 420 total pass, ruff clean

### Change Log
- 2026-04-03: Story 9.2 implemented — LINE BOT order submission with webhook, parser, customer mapping

### File List
- migrations/versions/mm333oo33p65_add_line_customer_mappings.py (NEW)
- backend/domains/line/models.py (NEW — LineCustomerMapping)
- backend/domains/line/parser.py (NEW — order text parser)
- backend/domains/line/webhook.py (NEW — webhook endpoint)
- backend/app/main.py (MODIFIED — registered LINE webhook router)
- backend/tests/test_line_parser.py (NEW — 10 tests)
- backend/tests/test_line_webhook.py (NEW — 5 tests)

