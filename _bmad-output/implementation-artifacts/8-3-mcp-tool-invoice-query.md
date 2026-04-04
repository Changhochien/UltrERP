# Story 8.3: MCP Tool — Invoice Query

Status: complete

## Story

As an AI agent,
I want to query invoice data via MCP tools,
So that I can retrieve invoice information.

## Acceptance Criteria

**AC1:** `invoices_list` tool returns paginated invoices
**Given** I'm an AI agent with MCP access and `invoices:read` scope
**When** I call `invoices_list` with optional filters (payment_status, sort_by, sort_order, page, page_size)
**Then** I receive a paginated list of invoices with id, invoice_number, customer, total_amount, tax, status, payment_status
**And** results are filterable by payment status (paid, unpaid, partial, overdue)

**AC2:** `invoices_get` tool returns a single invoice
**Given** I'm an AI agent with MCP access and `invoices:read` scope
**When** I call `invoices_get` with an `invoice_id`
**Then** I receive the full invoice record including line items
**And** the response includes: invoice_number, customer_id, total_amount, tax_amount, status, line items, payment summary
**And** invoice totals and tax are included (per AC in epics)

**AC3:** Invoice not found returns structured error
**Given** I call `invoices_get` with a non-existent `invoice_id`
**When** the service returns `None`
**Then** the tool raises `ToolError` with a JSON-encoded `NotFoundError`
**And** `entity_type` is `"invoice"`

**AC4:** Payment status enrichment
**Given** I call `invoices_list` or `invoices_get`
**When** the invoice data is returned
**Then** payment status is computed (paid/unpaid/partial/overdue) using `enrich_invoices_with_payment_status` or `compute_invoice_payment_summary`
**And** includes: amount_paid, outstanding_balance, due_date, days_overdue (if applicable)

**AC5:** Tenant scoping enforced
**Given** the MCP server is running
**When** any invoice tool is called
**Then** all queries are scoped to `DEFAULT_TENANT_ID`
**And** RLS is enforced via `set_tenant(session, tenant_id)`

**AC6:** Backend tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass
**And** invoice MCP tool tests are added (≥ 5 tests)

## Tasks / Subtasks

- [ ] **Task 1: Create invoice MCP tools module** (AC1, AC2, AC3, AC4, AC5)
  - [ ] Create `backend/domains/invoices/mcp.py`:
    ```python
    """
    MCP tools for the Invoices domain.

    Tools:
      - invoices_list: List invoices with payment status filtering
      - invoices_get: Get a single invoice with line items and payment summary
    """
    from __future__ import annotations
    import uuid
    import json
    from typing import Annotated, Literal
    from decimal import Decimal
    from datetime import date
    from pydantic import Field
    from fastmcp.exceptions import ToolError

    from app.mcp_server import mcp
    from common.database import AsyncSessionLocal
    from common.tenant import set_tenant, DEFAULT_TENANT_ID
    from domains.invoices.service import (
        list_invoices,
        get_invoice,
        compute_invoice_payment_summary,
    )

    @mcp.tool()
    async def invoices_list(
        payment_status: Annotated[Literal["paid", "unpaid", "partial", "overdue"] | None, Field(description="Filter: paid, unpaid, partial, overdue")] = None,
        sort_by: Annotated[Literal["created_at", "total_amount", "invoice_number"], Field(description="Sort field", default="created_at")] = "created_at",
        sort_order: Annotated[Literal["asc", "desc"], Field(description="Sort direction", default="desc")] = "desc",
        page: Annotated[int, Field(description="Page number", default=1, ge=1)] = 1,
        page_size: Annotated[int, Field(description="Results per page", default=20, ge=1, le=100)] = 20,
    ) -> dict:
        """List invoices with optional payment status filtering and sorting."""
        async with AsyncSessionLocal() as session:
            # NOTE: Do NOT call set_tenant here — list_invoices uses session.begin()
            # internally and calls set_tenant itself.
            invoices, total = await list_invoices(
                session,
                tenant_id=DEFAULT_TENANT_ID,
                page=page,
                page_size=page_size,
                payment_status=payment_status,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            return {
                "invoices": invoices,  # already enriched dicts from service
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    @mcp.tool()
    async def invoices_get(
        invoice_id: Annotated[str, Field(description="UUID of the invoice")],
    ) -> dict:
        """Get full invoice details including line items and payment summary."""
        iid = uuid.UUID(invoice_id)
        async with AsyncSessionLocal() as session:
            await set_tenant(session, DEFAULT_TENANT_ID)
            invoice = await get_invoice(session, iid, DEFAULT_TENANT_ID)
            if invoice is None:
                raise ToolError(json.dumps({
                    "code": "NOT_FOUND",
                    "entity_type": "invoice",
                    "entity_id": invoice_id,
                    "message": f"Invoice {invoice_id} not found",
                    "retry": False,
                }))
            # Enrich with payment summary
            payment = await compute_invoice_payment_summary(
                session, invoice, DEFAULT_TENANT_ID,
            )
            return _serialize_invoice(invoice, payment)
    ```
  - [ ] Implement `_serialize_invoice(invoice, payment_summary)` helper to convert SQLAlchemy Invoice model + payment dict → plain dict:
    ```python
    def _serialize_invoice(invoice: "Invoice", payment: "PaymentSummaryDict") -> dict:
        """Convert Invoice model + payment summary to JSON-safe dict."""
        return {
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "customer_id": str(invoice.customer_id),
            "order_id": str(invoice.order_id) if invoice.order_id else None,
            "status": invoice.status,
            "invoice_date": invoice.invoice_date.isoformat(),
            "total_amount": str(invoice.total_amount),
            "tax_amount": str(invoice.tax_amount),
            "line_items": [
                {
                    "id": str(line.id),
                    "product_name": line.product_name,
                    "quantity": line.quantity,
                    "unit_price": str(line.unit_price),
                    "amount": str(line.amount),
                    "tax_amount": str(line.tax_amount),
                }
                for line in invoice.lines
            ],
            # Payment summary fields
            "amount_paid": str(payment["amount_paid"]),
            "outstanding_balance": str(payment["outstanding_balance"]),
            "payment_status": payment["payment_status"],
            "due_date": payment["due_date"].isoformat(),
            "days_overdue": payment["days_overdue"],
        }
    ```
  - [ ] Ensure tool names match `TOOL_SCOPES` in `backend/app/mcp_auth.py` (Story 8.4)

- [ ] **Task 2: Register invoice tools** (AC1)
  - [ ] Import `backend/domains/invoices/mcp` in `backend/app/mcp_server.py`:
    ```python
    import domains.invoices.mcp  # noqa: F401 — registers MCP tools
    ```

- [ ] **Task 3: Create invoice MCP tests** (AC1, AC2, AC3, AC4, AC6)
  - [ ] Create `backend/tests/test_mcp_invoices.py`:
    - Test: `invoices_list` returns paginated results
    - Test: `invoices_list` with payment_status filter
    - Test: `invoices_get` returns invoice with line items for valid ID
    - Test: `invoices_get` includes payment summary (amount_paid, outstanding_balance)
    - Test: `invoices_get` raises ToolError for non-existent ID
  - [ ] Run full test suite

## Dev Notes

### Architecture Compliance
- **§6.2:** Invoice tools: `invoices.list`, `invoices.get`, `invoices.create`, `invoices.void`, `invoices.submit` — this story only implements read tools. Write tools (create, void, submit) are deferred.
- **§4.3:** Tools wrap existing service functions from `domains/invoices/service.py`
- **Payment enrichment:** The `list_invoices` service already returns enriched dicts with payment status. For `get_invoice`, use `compute_invoice_payment_summary` separately.

### Critical Warnings
- ⚠️ `list_invoices` returns `tuple[list[dict], int]` — the dicts are already enriched with payment status. No need to call `enrich_invoices_with_payment_status` again.
- ⚠️ **Transaction pattern for `invoices_list`:** `list_invoices` uses `session.begin()` internally and calls `set_tenant` itself. MCP tool must NOT call `set_tenant` before `list_invoices` — doing so triggers SQLAlchemy autobegin, and the service's `session.begin()` raises `InvalidRequestError`. Just pass `tenant_id`.
- ⚠️ **Transaction pattern for `invoices_get`:** `get_invoice` and `compute_invoice_payment_summary` do NOT use `session.begin()`. The MCP tool MUST call `set_tenant` before these functions for RLS enforcement.
- ⚠️ Invoice line items are eager-loaded by `get_invoice`. Include them in the serialised response.
- ⚠️ `Decimal` values must be converted to `str` or `float` for JSON serialisation. Prefer `str` for precision (matching REST API pattern).
- ⚠️ Do NOT expose `void` or `create` tools yet — those are write operations requiring human-in-the-loop approval (architecture §7.4).

### Project Structure Notes
- `backend/domains/invoices/mcp.py` — NEW: MCP tool definitions
- `backend/domains/invoices/service.py` — EXISTING: wraps these service functions:
  - `list_invoices(session, tenant_id, page, page_size, payment_status, sort_by, sort_order)` → `tuple[list[dict], int]`
  - `get_invoice(session, invoice_id, tenant_id)` → `Invoice | None`
  - `compute_invoice_payment_summary(session, invoice, tenant_id)` → `PaymentSummaryDict`

### Previous Story Intelligence
- **Story 8.6:** Creates the MCP server — tools register on it
- **Story 8.4:** Creates the auth middleware — tool names must match `TOOL_SCOPES`
- **Story 8.1:** Same pattern for inventory tools — follow same serialisation approach
- **Story 8.2:** Same pattern for customer tools — use same not-found error handling
- **Service behaviour:** `list_invoices` already does the payment enrichment internally — check the implementation to avoid double-enrichment

### References
- Architecture v2 §4.3 (MCP Tools), §6.2 (Invoice tools)
- PRD: FR31 (invoice query via MCP)
- Backend service: `backend/domains/invoices/service.py`

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (fast mode)

### Completion Notes List
- Created `backend/domains/invoices/mcp.py` — 2 tools: `invoices_list`, `invoices_get`
- `invoices_list`: no `set_tenant` (service uses `session.begin()`)
- `invoices_get`: calls `set_tenant` + `get_invoice` + `compute_invoice_payment_summary`
- Serialization helper: `_serialize_invoice(invoice, payment)` with line items and payment summary
- 5 tests in `backend/tests/test_mcp_invoices.py`, all passing
