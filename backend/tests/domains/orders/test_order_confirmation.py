"""Tests for order confirmation — Story 5.4."""

from __future__ import annotations

import uuid

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


def _queue_confirm_success(session: FakeAsyncSession, order: FakeOrder, customer: FakeCustomer):
    """Queue all results needed for successful confirm_order call.

    Execution flow:
      1. set_tenant → scalar(None)
      2. order lookup (selectinload + for_update) → scalar(order)
      3. product code lookup → rows[(product_id, code)]
      4. customer lookup in confirm_order → scalar(customer)
      5. _create_invoice_core: customer lookup → scalar(customer)
      6. _create_invoice_core: number_range lookup → scalar(number_range)
      7. warehouse_id lookup (inside _get_default_warehouse_id) → scalar(uuid)
      8. stock FOR UPDATE (per line) → scalar(FakeInventoryStock)
      9. flush (invoice + lines), flush (audits)
     10. get_order reload: set_tenant → scalar(None)
     11. get_order reload: selectinload → scalar(confirmed_order)
    """
    session.queue_scalar(None)  # 1. set_tenant
    session.queue_scalar(order)  # 2. order lookup
    # Product code lookup — return fake rows with id and code attributes
    product_rows = [
        type("Row", (), {"id": line.product_id, "code": f"PROD-{i}"})()
        for i, line in enumerate(order.lines)
    ]
    session.queue_rows(product_rows)  # 3. product code lookup
    session.queue_scalar(customer)  # 4. customer lookup (confirm_order)
    session.queue_scalar(customer)  # 5. customer lookup (_create_invoice_core)
    session.queue_scalar(FakeInvoiceNumberRange())  # 6. number_range
    session.queue_scalar(order.tenant_id)  # 7. warehouse_id lookup
    # Stock rows for each line (FOR UPDATE lock)
    for _line in order.lines:
        session.queue_scalar(FakeInventoryStock(quantity=100))  # 8. stock rows
    session.queue_scalar(None)  # 9. flush scalar
    session.queue_scalar(None)  # 10. set_tenant (get_order)
    session.queue_scalar(order)  # 11. get_order reload


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
        type("Row", (), {"id": line.product_id, "code": f"PROD-{i}"})()
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
