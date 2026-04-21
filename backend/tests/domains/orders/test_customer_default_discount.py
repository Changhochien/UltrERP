from __future__ import annotations

import uuid
from decimal import Decimal

from common.models.order import Order

from ._helpers import FakeAsyncSession, FakeCustomer, FakeOrder, FakeOrderLine
from ._helpers import http_post as _post
from ._helpers import setup_session as _setup
from ._helpers import teardown_session as _teardown

_PRODUCT_ID = str(uuid.uuid4())


class FakeProduct:
    def __init__(self, *, product_id: uuid.UUID | None = None):
        self.id = product_id or uuid.uuid4()


def _valid_order_payload(customer_id: str) -> dict[str, object]:
    return {
        "customer_id": customer_id,
        "payment_terms_code": "NET_30",
        "notes": "Test order",
        "lines": [
            {
                "product_id": _PRODUCT_ID,
                "description": "Widget A",
                "quantity": 10,
                "unit_price": 100.00,
                "tax_policy_code": "standard",
            },
        ],
    }


async def test_create_order_uses_customer_default_discount_when_header_discount_omitted() -> None:
    customer = FakeCustomer(default_discount_percent=Decimal("0.1000"))
    product = FakeProduct(product_id=uuid.UUID(_PRODUCT_ID))

    line = FakeOrderLine(product_id=product.id)
    order = FakeOrder(
        customer_id=customer.id,
        lines=[line],
        customer=customer,
    )
    order.discount_amount = Decimal("0.00")
    order.discount_percent = Decimal("0.1000")
    order.total_amount = Decimal("950.00")

    session = FakeAsyncSession()
    session.queue_scalar(None)
    session.queue_scalar(customer)
    session.queue_scalars([product.id])
    session.queue_count(100)
    session.queue_scalar(None)
    session.queue_scalar(order)

    prev = _setup(session)
    try:
        payload = _valid_order_payload(customer_id=str(customer.id))
        payload["lines"][0]["product_id"] = str(product.id)
        resp = await _post("/api/v1/orders", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["discount_amount"] == "0.00"
        assert body["discount_percent"] == "0.1000"
        assert body["total_amount"] == "950.00"

        created_order = next(obj for obj in session.added if isinstance(obj, Order))
        assert created_order.discount_amount == Decimal("0.00")
        assert created_order.discount_percent == Decimal("0.1000")
        assert created_order.total_amount == Decimal("950.00")
    finally:
        _teardown(prev)


async def test_create_order_explicit_zero_header_discount_overrides_customer_default() -> None:
    customer = FakeCustomer(default_discount_percent=Decimal("0.1000"))
    product = FakeProduct(product_id=uuid.UUID(_PRODUCT_ID))

    line = FakeOrderLine(product_id=product.id)
    order = FakeOrder(
        customer_id=customer.id,
        lines=[line],
        customer=customer,
    )
    order.discount_amount = Decimal("0.00")
    order.discount_percent = Decimal("0.0000")
    order.total_amount = Decimal("1050.00")

    session = FakeAsyncSession()
    session.queue_scalar(None)
    session.queue_scalar(customer)
    session.queue_scalars([product.id])
    session.queue_count(100)
    session.queue_scalar(None)
    session.queue_scalar(order)

    prev = _setup(session)
    try:
        payload = _valid_order_payload(customer_id=str(customer.id))
        payload["discount_percent"] = 0.0
        payload["lines"][0]["product_id"] = str(product.id)
        resp = await _post("/api/v1/orders", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["discount_percent"] == "0.0000"
        assert body["total_amount"] == "1050.00"

        created_order = next(obj for obj in session.added if isinstance(obj, Order))
        assert created_order.discount_percent == Decimal("0.0000")
        assert created_order.total_amount == Decimal("1050.00")
    finally:
        _teardown(prev)