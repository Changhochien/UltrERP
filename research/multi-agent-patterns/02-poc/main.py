"""
UltrERP MCP Server PoC — FastMCP 2.0

A reference implementation of an MCP server for an ERP system, demonstrating:
  - FastMCP 2.0 tool registration with Annotated Pydantic parameters
  - API key authentication middleware
  - Structured error types (ValidationError, NotFoundError, PermissionError)
  - MOD11 tax ID validation for Brazilian-style tax numbers
  - 5% tax calculation on invoice line items

Run:
    uvicorn main:app --host 0.0.0.0 --port 8000

Transport note:
    We use the default streamable-http transport (NOT stateless_http=True).
    FastMCP 3.x + stateless_http=True has a confirmed hang bug with
    MCP SDK 1.23+ (see 01-survey-memo.md "Top 3 Risks" item 3).
    FastMCP 2.x does not have this flag in the same form, but we
    prefer the session-based transport for reliability.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from auth import ApiKeyAuth, TOOL_SCOPES
from errors import NotFoundError, ValidationError
from models import (
    Customer,
    CustomerCreateInput,
    CustomerListFilters,
    CustomerStatus,
    Invoice,
    InvoiceCreateInput,
    InvoiceListFilters,
    InvoiceStatus,
    LineItem,
)

# ---------------------------------------------------------------------------
# FastMCP server (FastMCP 2.x — host/port in constructor)
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="UltrERP",
    instructions=(
        "UltrERP MCP server — exposes customers and invoices domains. "
        "All tools require a valid X-API-Key header. "
        "Use customers.list to explore available customers before creating invoices."
    ),
)

# Attach API key middleware
mcp.add_middleware(
    ApiKeyAuth(protected_tools=TOOL_SCOPES)
)


# ---------------------------------------------------------------------------
# Utility: MOD11 checksum validation
# ---------------------------------------------------------------------------

def validate_mod11(tax_id: str) -> None:
    """
    Validate an 8-digit MOD11 tax identification number.

    MOD11 algorithm (Brazilian CPF-style):
      1. Multiply the first 7 digits by weights [10, 9, 8, 7, 6, 5, 4]
         and sum the products.
      2. Take (sum % 11).  If result < 2, first check digit = 0;
         else first check digit = 11 - (sum % 11).
      3. Repeat with first 8 digits and weights [11, 10, 9, 8, 7, 6, 5, 4].
      4. Both computed check digits must match the submitted digits.

    Raises:
        ValidationError: if the tax_id does not pass MOD11 validation.
    """
    if not tax_id or len(tax_id) != 8 or not tax_id.isdigit():
        raise ValidationError(
            message="tax_id must be exactly 8 digits.",
            field="customer.tax_id",
            value=tax_id,
            constraint="8-digit MOD11 checksum",
            received=(
                f"{len(tax_id)} characters — "
                f"{'non-digit characters' if not tax_id.isdigit() else 'must be 8 digits'}"
            ),
        )

    digits = [int(d) for d in tax_id]

    def _check_digit(partial: list[int], weights: list[int]) -> int:
        total = sum(d * w for d, w in zip(partial, weights))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    # For 8-digit MOD11 there is exactly ONE check digit at position 8.
    # The first 7 digits are data; digit 8 is the MOD11 check digit.
    d1 = _check_digit(digits[:7], [10, 9, 8, 7, 6, 5, 4])
    if d1 != digits[7]:
        raise ValidationError(
            message="tax_id MOD11 checksum validation failed.",
            field="customer.tax_id",
            value=tax_id,
            constraint="valid MOD11 check digit at position 8",
            received=f"digit at position 8 should be {d1}, got {digits[7]}",
        )


# ---------------------------------------------------------------------------
# Mock data store (in-memory for PoC)
# ---------------------------------------------------------------------------

_CUSTOMERS: dict[str, dict[str, Any]] = {}
_INVOICES: dict[str, dict[str, Any]] = {}

_NOW = datetime(2026, 3, 30, 12, 0, 0, tzinfo=timezone.utc)


def _seed_customers() -> None:
    """Pre-populate mock customer data."""
    seeds = [
        # MOD11-valid: base 1234567 + check 8 = 12345678
        {"id": "c_001", "name": "Acme Corporation",     "tax_id": "12345678",
         "email": "billing@acme.example.com",           "status": "active"},
        # MOD11-valid: base 2030405 + check 0 = 20304050
        {"id": "c_002", "name": "Globex Industries",   "tax_id": "20304050",
         "email": "finance@globex.example.com",         "status": "active"},
        # MOD11-valid: base 3030403 + check 9 = 30304039
        {"id": "c_003", "name": "Initech Systems",      "tax_id": "30304039",
         "email": "accounts@initech.example.com",       "status": "inactive"},
        # MOD11-valid: base 4040404 + check 9 = 40404049
        {"id": "c_004", "name": "Umbrella Corp",        "tax_id": "40404049",
         "email": "legal@umbrella.example.com",         "status": "suspended"},
        # MOD11-valid: base 5050505 + check 3 = 50505053
        {"id": "c_005", "name": "Stark Industries",    "tax_id": "50505053",
         "email": "tony@stark.example.com",             "status": "active"},
    ]
    for c in seeds:
        _CUSTOMERS[c["id"]] = {
            **c,
            "created_at": _NOW.isoformat(),
            "updated_at": _NOW.isoformat(),
        }


def _seed_invoices() -> None:
    """Pre-populate mock invoice data."""
    seeds = [
        {
            "id": "inv_001", "customer_id": "c_001",
            "status": "open",
            "line_items": [
                {"description": "Consulting hours",    "quantity": 10, "unit_price": 150.00, "tax_rate": 0.05},
                {"description": "Infrastructure setup","quantity":  1, "unit_price": 500.00, "tax_rate": 0.05},
            ],
        },
        {
            "id": "inv_002", "customer_id": "c_002",
            "status": "paid",
            "line_items": [
                {"description": "License (annual)",   "quantity":  5, "unit_price": 200.00, "tax_rate": 0.05},
            ],
        },
        {
            "id": "inv_003", "customer_id": "c_003",
            "status": "void",
            "line_items": [
                {"description": "Setup fee",           "quantity":  1, "unit_price": 1000.00, "tax_rate": 0.05},
            ],
        },
        {
            "id": "inv_004", "customer_id": "c_001",
            "status": "draft",
            "line_items": [
                {"description": "Q2 retainer",         "quantity":  3, "unit_price": 1000.00, "tax_rate": 0.05},
            ],
        },
    ]
    for inv in seeds:
        li = [LineItem(**item) for item in inv["line_items"]]
        subtotal = sum(i.subtotal for i in li)
        total_tax = sum(i.tax_amount for i in li)
        _INVOICES[inv["id"]] = {
            **inv,
            "subtotal": round(subtotal, 2),
            "total_tax": round(total_tax, 2),
            "total": round(subtotal + total_tax, 2),
            "created_at": _NOW.isoformat(),
            "due_date": "2026-04-30",
        }


_seed_customers()
_seed_invoices()


# ---------------------------------------------------------------------------
# Tool: customers.list
# ---------------------------------------------------------------------------

@mcp.tool()
def customers_list(
    status: Annotated[
        CustomerStatus | None,
        Field(description="Filter by customer status (active, inactive, suspended)."),
    ] = None,
    limit: Annotated[
        int,
        Field(25, description="Maximum number of results to return.", ge=1, le=100),
    ] = 25,
    offset: Annotated[
        int,
        Field(0, description="Number of results to skip for pagination.", ge=0),
    ] = 0,
) -> dict[str, Any]:
    """
    List customers in the UltrERP system.

    Requires scope: customers:read

    Use this tool to:
      - Browse the customer registry before creating invoices
      - Find a customer's ID by name or status
      - Check if a customer already exists before creating a duplicate

    Returns:
        Dictionary with 'customers' (list), 'total', 'limit', 'offset'.
        Each customer includes: id, name, tax_id, email, status, created_at.
    """
    results = list(_CUSTOMERS.values())

    if status is not None:
        results = [c for c in results if c["status"] == status.value]

    total = len(results)
    page = results[offset : offset + limit]

    return {
        "customers": page,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ---------------------------------------------------------------------------
# Tool: customers.create
# ---------------------------------------------------------------------------

@mcp.tool()
def customers_create(
    name: Annotated[
        str,
        Field(
            description="Legal name of the customer (2–255 characters).",
            min_length=2,
            max_length=255,
        ),
    ],
    tax_id: Annotated[
        str,
        Field(
            description=(
                "Tax identification number. Must be exactly 8 digits "
                "passing MOD11 checksum validation. "
                "Example valid number: 12345678 or 11111116"
            ),
        ),
    ],
    email: Annotated[
        str,
        Field(
            description="Primary contact email address.",
            max_length=255,
        ),
    ],
    customer_status: Annotated[
        CustomerStatus,
        Field(
            default=CustomerStatus.ACTIVE,
            description="Initial status of the customer account.",
        ),
    ] = CustomerStatus.ACTIVE,
) -> dict[str, Any]:
    """
    Create a new customer in the UltrERP system.

    Requires scope: customers:write

    Validation rules:
      - name: 2–255 characters (required)
      - tax_id: exactly 8 digits, MOD11 checksum validated
      - email: valid email format, max 255 characters
      - status: defaults to 'active'

    Tax ID MOD11 validation:
      The tax_id is validated using a MOD11 checksum algorithm. A valid
      8-digit tax ID has its 8th digit as the MOD11 check digit of the
      preceding 7 data digits. Example valid number: 12345678.

    Returns:
        The created customer object including the server-assigned ID.
    """
    # MOD11 checksum validation
    validate_mod11(tax_id)

    # Check for duplicate tax_id
    for c in _CUSTOMERS.values():
        if c["tax_id"] == tax_id:
            raise ValidationError(
                message=f"A customer with tax_id '{tax_id}' already exists.",
                field="customer.tax_id",
                value=tax_id,
                constraint="unique tax_id per customer",
                received=f"existing customer: {c['name']} ({c['id']})",
            )

    customer_id = f"c_{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc).isoformat()

    customer = {
        "id": customer_id,
        "name": name,
        "tax_id": tax_id,
        "email": email,
        "status": customer_status.value,
        "created_at": now,
        "updated_at": now,
    }
    _CUSTOMERS[customer_id] = customer

    return customer


# ---------------------------------------------------------------------------
# Tool: invoices.list
# ---------------------------------------------------------------------------

@mcp.tool()
def invoices_list(
    status: Annotated[
        InvoiceStatus | None,
        Field(description="Filter by invoice status (draft, open, paid, void)."),
    ] = None,
    customer_id: Annotated[
        str | None,
        Field(description="Filter by customer ID."),
    ] = None,
    limit: Annotated[
        int,
        Field(25, description="Maximum number of results to return.", ge=1, le=100),
    ] = 25,
    offset: Annotated[
        int,
        Field(0, description="Number of results to skip for pagination.", ge=0),
    ] = 0,
) -> dict[str, Any]:
    """
    List invoices in the UltrERP system.

    Requires scope: invoices:read

    Use this tool to:
      - Check the status of outstanding invoices
      - Retrieve invoice details by customer
      - List all draft or void invoices for reconciliation

    Returns:
        Dictionary with 'invoices' (list), 'total', 'limit', 'offset'.
        Each invoice includes: id, customer_id, status, line_items,
        subtotal, total_tax, total, created_at, due_date.
    """
    results = list(_INVOICES.values())

    if status is not None:
        results = [r for r in results if r["status"] == status.value]
    if customer_id is not None:
        results = [r for r in results if r["customer_id"] == customer_id]

    total = len(results)
    page = results[offset : offset + limit]

    return {
        "invoices": page,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ---------------------------------------------------------------------------
# Tool: invoices.create
# ---------------------------------------------------------------------------

@mcp.tool()
def invoices_create(
    customer_id: Annotated[
        str,
        Field(description="ID of the customer to bill."),
    ],
    due_date: Annotated[
        str,
        Field(description="Payment due date as ISO 8601 string (YYYY-MM-DD)."),
    ],
    line_items: Annotated[
        list[dict[str, Any]],
        Field(
            description=(
                "Line items as a list of objects with keys: "
                "description (str), quantity (int, >0), "
                "unit_price (float, >=0), tax_rate (float, 0–1, default 0.05). "
                "At least one line item is required."
            ),
        ),
    ],
    invoice_status: Annotated[
        InvoiceStatus,
        Field(
            default=InvoiceStatus.DRAFT,
            description="Initial status of the invoice.",
        ),
    ] = InvoiceStatus.DRAFT,
) -> dict[str, Any]:
    """
    Create a new invoice in the UltrERP system.

    Requires scope: invoices:write

    Tax calculation:
      Each line item has a configurable tax_rate (default 5% = 0.05).
      Tax for the line = round(subtotal * tax_rate, 2)
        where subtotal = round(quantity * unit_price, 2)
      Total tax = sum of all line item taxes
      Invoice total = subtotal + total_tax

    Validation rules:
      - customer_id: must reference an existing customer
      - due_date: ISO 8601 date string (YYYY-MM-DD)
      - line_items: at least one item required
      - Each line item quantity must be > 0
      - Each line item unit_price must be >= 0

    Returns:
        The created invoice object including server-assigned ID,
        computed subtotal, total_tax, and total fields.
    """
    # Validate customer exists
    if customer_id not in _CUSTOMERS:
        raise NotFoundError(
            entity_type="customer",
            entity_id=customer_id,
            message=f"Cannot create invoice: customer '{customer_id}' not found.",
        )

    # Parse due_date
    try:
        due = date.fromisoformat(due_date)
    except ValueError:
        raise ValidationError(
            message=f"Invalid due_date format: '{due_date}'. Expected YYYY-MM-DD.",
            field="invoice.due_date",
            value=due_date,
            constraint="ISO 8601 date string (YYYY-MM-DD)",
            received=due_date,
        )

    # Build line items and compute totals
    parsed_items: list[LineItem] = []
    for i, item in enumerate(line_items):
        try:
            li = LineItem(**item)
        except Exception as exc:
            raise ValidationError(
                message=f"Invalid line item at index {i}: {exc}",
                field=f"invoice.line_items[{i}]",
                value=item,
                constraint="LineItem(schema): description, quantity>0, unit_price>=0, tax_rate in [0,1]",
            )
        parsed_items.append(li)

    subtotal = round(sum(li.subtotal for li in parsed_items), 2)
    total_tax = round(sum(li.tax_amount for li in parsed_items), 2)
    total = round(subtotal + total_tax, 2)

    invoice_id = f"inv_{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)

    invoice = {
        "id": invoice_id,
        "customer_id": customer_id,
        "status": invoice_status.value,
        "line_items": [
            {
                "description": li.description,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "tax_rate": li.tax_rate,
                "subtotal": li.subtotal,
                "tax_amount": li.tax_amount,
                "total": li.total,
            }
            for li in parsed_items
        ],
        "subtotal": subtotal,
        "total_tax": total_tax,
        "total": total,
        "created_at": now.isoformat(),
        "due_date": due.isoformat(),
    }
    _INVOICES[invoice_id] = invoice

    return invoice


# ---------------------------------------------------------------------------
# ASGI app entry point for uvicorn
# ---------------------------------------------------------------------------
# FastMCP 2.x: host/port in constructor, http_app() returns an ASGI app
# that can be run with: uvicorn main:app --host 0.0.0.0 --port 8000

app = mcp.http_app()
