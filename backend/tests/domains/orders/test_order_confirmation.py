"""Tests for order confirmation — Story 5.4."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from domains.orders.services import confirm_order

from ._helpers import (
    FakeAsyncSession,
    FakeCustomer,
    FakeInventoryStock,
    FakeInvoiceNumberRange,
    FakeOrder,
    FakeOrderLine,
)
from ._helpers import (
    http_patch as _patch,
)
from ._helpers import (
    setup_session as _setup,
)
from ._helpers import (
    teardown_session as _teardown,
)

# ── Confirm order tests ──────────────────────────────────────


def _make_product_row(
    product_id: uuid.UUID,
    index: int,
    *,
    name: str | None = None,
    category: str | None = None,
):
    return type(
        "Row",
        (),
        {
            "id": product_id,
            "code": f"PROD-{index}",
            "name": name or f"Product {index}",
            "category": category or f"Category {index}",
        },
    )()


def _find_executed_statement(session: FakeAsyncSession, needle: str) -> object:
    for stmt, _params in session.executed_statements:
        if needle in str(stmt):
            return stmt
    raise AssertionError(f"Executed statement not found: {needle}")


def _queue_confirm_success(
    session: FakeAsyncSession,
    order: FakeOrder,
    customer: FakeCustomer,
    *,
    unit_costs: list[Decimal | None] | None = None,
    product_rows: list[object] | None = None,
):
    """Queue all results needed for successful confirm_order call.

    Execution flow:
      1. set_tenant → scalar(None)
      2. order lookup (selectinload + for_update) → scalar(order)
      3. product code lookup → rows[(product_id, code)]
      4. customer lookup in confirm_order → scalar(customer)
      5. _create_invoice_core: customer lookup → scalar(customer)
      6. _create_invoice_core: number_range lookup → scalar(number_range)
      7. supplier invoice unit_cost lookup (per line) → scalar(Decimal | None)
      8. warehouse_id lookup (inside _get_default_warehouse_id) → scalar(uuid)
      9. stock FOR UPDATE (per line) → scalar(FakeInventoryStock)
     10. flush (invoice + lines), flush (audits)
     11. get_order reload: set_tenant → scalar(None)
     12. get_order reload: selectinload → scalar(confirmed_order)
    """
    resolved_unit_costs = unit_costs or [None] * len(order.lines)

    session.queue_scalar(None)  # 1. set_tenant
    session.queue_scalar(order)  # 2. order lookup
    # Product code lookup — return fake rows with id and code attributes
    resolved_product_rows = product_rows or [
        _make_product_row(line.product_id, i) for i, line in enumerate(order.lines)
    ]
    session.queue_rows(resolved_product_rows)  # 3. product code lookup
    session.queue_scalar(customer)  # 4. customer lookup (confirm_order)
    session.queue_scalar(customer)  # 5. customer lookup (_create_invoice_core)
    session.queue_scalar(FakeInvoiceNumberRange())  # 6. number_range
    for unit_cost in resolved_unit_costs:
        if unit_cost is None:
            session.queue_rows([])  # 7. supplier invoice unit_cost lookup
            continue
        session.queue_rows(
            [
                type(
                    "Row",
                    (),
                    {
                        "effective_date": datetime.now(tz=UTC).date(),
                        "unit_cost": unit_cost,
                        "source_priority": 1,
                    },
                )()
            ]
        )
    session.queue_scalar(order.tenant_id)  # 8. warehouse_id lookup
    # Stock rows for each line (FOR UPDATE lock)
    for _line in order.lines:
        session.queue_scalar(FakeInventoryStock(quantity=100))  # 9. stock rows
    session.queue_scalar(None)  # 10. flush scalar
    session.queue_scalar(None)  # 11. set_tenant (get_order)
    session.queue_scalar(order)  # 12. get_order reload


async def test_confirm_order_success() -> None:
    """Confirming a pending order creates an invoice and returns confirmed order."""
    customer = FakeCustomer()
    line = FakeOrderLine()
    order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

    session = FakeAsyncSession()
    _queue_confirm_success(session, order, customer)

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "confirmed"},
        )
        print(f"DEBUG resp.status={resp.status_code} body={resp.json()}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "confirmed"
        assert body["invoice_id"] is not None
    finally:
        _teardown(prev)


async def test_confirm_order_stamps_missing_product_snapshots() -> None:
    customer = FakeCustomer()
    line = FakeOrderLine(description="Invoice description")
    order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

    session = FakeAsyncSession()
    _queue_confirm_success(
        session,
        order,
        customer,
        product_rows=[
            _make_product_row(
                line.product_id,
                0,
                name="Catalog Widget",
                category="Belts",
            )
        ],
    )

    await confirm_order(session, order.id, tenant_id=order.tenant_id)

    assert line.product_name_snapshot == "Catalog Widget"
    assert line.product_category_snapshot == "Belts"


async def test_confirm_order_preserves_existing_product_snapshots() -> None:
    customer = FakeCustomer()
    line = FakeOrderLine(
        product_name_snapshot="Frozen Widget",
        product_category_snapshot="Frozen Belts",
    )
    order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

    session = FakeAsyncSession()
    _queue_confirm_success(
        session,
        order,
        customer,
        product_rows=[
            _make_product_row(
                line.product_id,
                0,
                name="Renamed Widget",
                category="Renamed Category",
            )
        ],
    )

    await confirm_order(session, order.id, tenant_id=order.tenant_id)

    assert line.product_name_snapshot == "Frozen Widget"
    assert line.product_category_snapshot == "Frozen Belts"


async def test_confirm_order_preserves_non_null_empty_product_snapshots() -> None:
    customer = FakeCustomer()
    line = FakeOrderLine(
        product_name_snapshot="",
        product_category_snapshot="",
    )
    order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

    session = FakeAsyncSession()
    _queue_confirm_success(
        session,
        order,
        customer,
        product_rows=[
            _make_product_row(
                line.product_id,
                0,
                name="Renamed Widget",
                category="Renamed Category",
            )
        ],
    )

    await confirm_order(session, order.id, tenant_id=order.tenant_id)

    assert line.product_name_snapshot == ""
    assert line.product_category_snapshot == ""


async def test_confirm_order_scopes_product_lookup_to_tenant() -> None:
    customer = FakeCustomer()
    line = FakeOrderLine()
    order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

    session = FakeAsyncSession()
    _queue_confirm_success(session, order, customer)

    await confirm_order(session, order.id, tenant_id=order.tenant_id)

    product_lookup = _find_executed_statement(session, "product.code")
    assert "product.tenant_id" in str(product_lookup)


async def test_confirm_order_resolves_invoice_line_unit_costs() -> None:
    """Confirming an order stamps resolved unit cost onto the created invoice lines."""
    customer = FakeCustomer()
    line = FakeOrderLine()
    order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

    session = FakeAsyncSession()
    _queue_confirm_success(session, order, customer, unit_costs=[Decimal("55.00")])

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "confirmed"},
        )
        assert resp.status_code == 200

        from domains.invoices.models import Invoice

        invoice = next(obj for obj in session.added if isinstance(obj, Invoice))
        assert invoice.lines[0].unit_cost == Decimal("55.00")
    finally:
        _teardown(prev)


async def test_confirm_non_pending_order_returns_409() -> None:
    """Cannot confirm an order that is not 'pending'."""
    order = FakeOrder(status="confirmed")

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # order lookup

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "confirmed"},
        )
        assert resp.status_code == 409
    finally:
        _teardown(prev)


async def test_confirm_order_with_existing_invoice_returns_409() -> None:
    """Cannot confirm if order already has an invoice_id."""
    order = FakeOrder(invoice_id=uuid.uuid4())

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # order lookup

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "confirmed"},
        )
        # status check happens first (order is still "pending"), then invoice_id check
        assert resp.status_code == 409
    finally:
        _teardown(prev)


async def test_confirm_order_no_lines_returns_409() -> None:
    """Cannot confirm an order with no lines."""
    order = FakeOrder(lines=[])

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # order lookup

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "confirmed"},
        )
        assert resp.status_code == 409
    finally:
        _teardown(prev)


async def test_confirm_order_not_found_returns_404() -> None:
    """Confirming a non-existent order returns 404."""
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(None)  # order not found

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{uuid.uuid4()}/status",
            json={"new_status": "confirmed"},
        )
        assert resp.status_code == 404
    finally:
        _teardown(prev)


async def test_confirm_order_customer_missing_returns_409() -> None:
    """If customer no longer exists at confirmation time, return 409."""
    order = FakeOrder()

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # order lookup
    product_rows = [
        _make_product_row(line.product_id, i)
        for i, line in enumerate(order.lines)
    ]
    session.queue_rows(product_rows)  # product code lookup
    session.queue_scalar(None)  # customer not found

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "confirmed"},
        )
        assert resp.status_code == 409
    finally:
        _teardown(prev)


async def test_confirm_order_product_missing_returns_409() -> None:
    """If an order line product no longer resolves in-tenant, confirmation fails closed."""
    order = FakeOrder()

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # order lookup
    session.queue_rows([])  # product lookup misses every line

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "confirmed"},
        )
        assert resp.status_code == 409
        assert "product" in resp.json()["detail"].lower()
    finally:
        _teardown(prev)


async def test_unsupported_status_transition_returns_422() -> None:
    """Unknown new_status returns 422."""
    session = FakeAsyncSession()

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{uuid.uuid4()}/status",
            json={"new_status": "bogus_status"},
        )
        assert resp.status_code == 422
    finally:
        _teardown(prev)


async def test_confirm_order_creates_audit_logs() -> None:
    """Confirm creates both ORDER_STATUS_CHANGED and INVOICE_CREATED audit entries."""
    customer = FakeCustomer()
    line = FakeOrderLine()
    order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

    session = FakeAsyncSession()
    _queue_confirm_success(session, order, customer)

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{order.id}/status",
            json={"new_status": "confirmed"},
        )
        assert resp.status_code == 200

        # Check audit logs in session.added
        from common.models.audit_log import AuditLog

        audits = [o for o in session.added if isinstance(o, AuditLog)]
        actions = {a.action for a in audits}
        assert "ORDER_STATUS_CHANGED" in actions
        assert "INVOICE_CREATED" in actions
    finally:
        _teardown(prev)
