"""Tests for orders API endpoints — Story 5.1."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

from common.models.order import Order
from common.models.order_line import OrderLine
from domains.orders.services import list_orders

from ._helpers import (
    FakeAsyncSession,
    FakeCustomer,
    FakeOrder,
    FakeOrderLine,
    auth_header,
)
from ._helpers import (
    http_get as _get,
)
from ._helpers import (
    http_patch as _patch,
)
from ._helpers import (
    http_post as _post,
)
from ._helpers import (
    setup_session as _setup,
)
from ._helpers import (
    teardown_session as _teardown,
)

# ── File-specific fakes ──────────────────────────────────────


class FakeProduct:
    def __init__(self, *, product_id: uuid.UUID | None = None):
        self.id = product_id or uuid.uuid4()


# ── Payment terms tests ──────────────────────────────────────


async def test_list_payment_terms() -> None:
    session = FakeAsyncSession()
    prev = _setup(session)
    try:
        resp = await _get("/api/v1/orders/payment-terms")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        codes = [item["code"] for item in body["items"]]
        assert "NET_30" in codes
        assert "NET_60" in codes
        assert "COD" in codes
    finally:
        _teardown(prev)


# ── Order list tests ─────────────────────────────────────────


async def test_list_orders_empty() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_count(0)  # count query
    session.queue_scalars([])  # items query

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/orders")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []
    finally:
        _teardown(prev)


async def test_list_orders_with_items() -> None:
    o1 = FakeOrder(status="pending")
    o2 = FakeOrder(status="confirmed")

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_count(2)
    session.queue_scalars([o1, o2])

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/orders")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        assert body["items"][0]["execution"]["commercial_status"] == "pre_commit"
        assert body["items"][1]["execution"]["commercial_status"] == "committed"
    finally:
        _teardown(prev)


async def test_list_orders_allows_warehouse_read_access() -> None:
    order = FakeOrder(status="pending")

    session = FakeAsyncSession()
    session.queue_scalar(None)
    session.queue_count(1)
    session.queue_scalars([order])

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/orders", headers=auth_header("warehouse"))
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
    finally:
        _teardown(prev)


async def test_list_orders_denies_finance_read_access() -> None:
    session = FakeAsyncSession()

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/orders", headers=auth_header("finance"))
        assert resp.status_code == 403
    finally:
        _teardown(prev)


async def test_list_orders_with_status_filter() -> None:
    o1 = FakeOrder(status="pending")

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_count(1)
    session.queue_scalars([o1])

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/orders?status=pending")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
    finally:
        _teardown(prev)


async def test_list_orders_includes_invoice_payment_cues() -> None:
    class FakeInvoice:
        def __init__(self, *, invoice_id: uuid.UUID, order_id: uuid.UUID) -> None:
            self.id = invoice_id
            self.order_id = order_id
            self.invoice_number = "AA00000001"
            self.invoice_date = date.today()
            self.customer_id = uuid.uuid4()
            self.currency_code = "TWD"
            self.total_amount = Decimal("1050.00")
            self.status = "issued"
            self.created_at = datetime.now(tz=UTC)

    invoice_id = uuid.uuid4()
    ready_line = FakeOrderLine(product_id=uuid.uuid4(), available_stock_snapshot=25)
    order = FakeOrder(status="confirmed", lines=[ready_line], invoice_id=invoice_id)
    invoice = FakeInvoice(invoice_id=invoice_id, order_id=order.id)

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_count(1)
    session.queue_scalars([order])
    session.queue_scalar(None)  # set_tenant for workspace meta
    session.queue_scalars([invoice])
    session.queue_rows([(invoice.id, Decimal("100.00"))])
    session.queue_rows([(order.id, 30)])

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/orders")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"][0]["invoice_number"] == "AA00000001"
        assert body["items"][0]["invoice_payment_status"] == "partial"
        assert body["items"][0]["execution"]["fulfillment_status"] == "ready_to_ship"
        assert body["items"][0]["execution"]["reservation_status"] == "reserved"
    finally:
        _teardown(prev)


async def test_list_orders_invoiced_not_paid_view_uses_payment_state_filter() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    session = FakeAsyncSession()
    session.queue_scalar(None)
    session.queue_count(0)
    session.queue_scalars([])

    await list_orders(
        session,
        tenant_id=tenant_id,
        workflow_view="invoiced_not_paid",
    )

    executed_sql = "\n".join(str(statement) for statement, _params in session.executed_statements)
    normalized_sql = executed_sql.lower()

    assert "payments" in normalized_sql
    assert "match_status" in normalized_sql
    assert "total_amount" in normalized_sql
    assert "invoice_id" in normalized_sql


# ── Order detail tests ───────────────────────────────────────


async def test_get_order_found() -> None:
    customer = FakeCustomer()
    line = FakeOrderLine(product_id=uuid.uuid4())
    order = FakeOrder(
        customer_id=customer.id,
        lines=[line],
        customer=customer,
        sales_team=[
            {
                "sales_person": "Alice Chen",
                "allocated_percentage": "60.00",
                "commission_rate": "5.00",
                "allocated_amount": "30.00",
            }
        ],
        total_commission=Decimal("30.00"),
    )

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(order)  # get_order query

    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/orders/{order.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["order_number"] == order.order_number
        assert body["status"] == "pending"
        assert body["execution"]["commercial_status"] == "pre_commit"
        assert body["invoice_payment_status"] is None
        assert body["total_commission"] == "30.00"
        assert body["sales_team"][0]["sales_person"] == "Alice Chen"
        assert body["sales_team"][0]["allocated_amount"] == "30.00"
        assert len(body["lines"]) == 1
        assert body["lines"][0]["description"] == "Test product"
    finally:
        _teardown(prev)


async def test_get_order_not_found() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(None)  # not found

    prev = _setup(session)
    try:
        resp = await _get(f"/api/v1/orders/{uuid.uuid4()}")
        assert resp.status_code == 404
    finally:
        _teardown(prev)


# ── Order creation tests ─────────────────────────────────────

_PRODUCT_ID = str(uuid.uuid4())


def _valid_order_payload(customer_id: str | None = None) -> dict:
    return {
        "customer_id": customer_id or str(uuid.uuid4()),
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


async def test_create_order_validation_empty_lines() -> None:
    session = FakeAsyncSession()
    prev = _setup(session)
    try:
        payload = _valid_order_payload()
        payload["lines"] = []
        resp = await _post("/api/v1/orders", json=payload)
        assert resp.status_code == 422
    finally:
        _teardown(prev)


async def test_create_order_validation_missing_customer() -> None:
    session = FakeAsyncSession()
    prev = _setup(session)
    try:
        payload = _valid_order_payload()
        del payload["customer_id"]
        resp = await _post("/api/v1/orders", json=payload)
        assert resp.status_code == 422
    finally:
        _teardown(prev)


async def test_create_order_customer_not_found() -> None:
    session = FakeAsyncSession()
    # set_tenant execute
    session.queue_scalar(None)
    # customer lookup — not found
    session.queue_scalar(None)

    prev = _setup(session)
    try:
        resp = await _post("/api/v1/orders", json=_valid_order_payload())
        assert resp.status_code == 422
        body = resp.json()
        assert any("customer" in str(e).lower() for e in body["detail"])
    finally:
        _teardown(prev)


async def test_create_order_success() -> None:
    customer = FakeCustomer()
    product = FakeProduct(product_id=uuid.UUID(_PRODUCT_ID))

    # For the reload after creation (get_order)
    line = FakeOrderLine(product_id=product.id)
    order = FakeOrder(
        customer_id=customer.id,
        lines=[line],
        customer=customer,
    )

    session = FakeAsyncSession()
    # Inside create_order (within session.begin):
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(customer)  # customer lookup
    session.queue_scalars([product.id])  # product IDs check
    session.queue_count(100)  # stock availability for line
    # After flush/commit, reload via get_order:
    session.queue_scalar(None)  # set_tenant (get_order)
    session.queue_scalar(order)  # get_order with selectinload

    prev = _setup(session)
    try:
        payload = _valid_order_payload(customer_id=str(customer.id))
        payload["lines"][0]["product_id"] = str(product.id)
        resp = await _post("/api/v1/orders", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "pending"
        assert body["payment_terms_code"] == "NET_30"
        assert body["payment_terms_days"] == 30
        assert len(body["lines"]) == 1
    finally:
        _teardown(prev)


async def test_create_order_preserves_quotation_lineage_and_context() -> None:
    quotation_id = uuid.uuid4()
    customer = FakeCustomer()
    product = FakeProduct(product_id=uuid.UUID(_PRODUCT_ID))
    crm_context_snapshot = {
        "source_document_type": "quotation",
        "party_label": "Rotor Works",
        "billing_address": "No. 1, Zhongshan Rd, Taipei",
    }
    source_quotation = SimpleNamespace(
        id=quotation_id,
        items=[{"line_no": 1}],
        ordered_amount=Decimal("0.00"),
        order_count=0,
        status="open",
        valid_till=date(2026, 5, 21),
        grand_total=Decimal("1000.00"),
        updated_at=datetime.now(tz=UTC),
    )

    line = FakeOrderLine(product_id=product.id, source_quotation_line_no=1)
    order = FakeOrder(
        customer_id=customer.id,
        source_quotation_id=quotation_id,
        lines=[line],
        customer=customer,
        crm_context_snapshot=crm_context_snapshot,
    )

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(customer)  # customer lookup
    session.queue_scalars([product.id])  # product check
    session.queue_scalar(source_quotation)  # quotation lookup
    session.queue_count(100)  # stock availability
    session.queue_rows([])  # linked order rows for quotation coverage sync
    session.queue_scalar(None)  # set_tenant (get_order)
    session.queue_scalar(order)  # get_order

    prev = _setup(session)
    try:
        payload = _valid_order_payload(customer_id=str(customer.id))
        payload["source_quotation_id"] = str(quotation_id)
        payload["crm_context_snapshot"] = crm_context_snapshot
        payload["lines"][0]["product_id"] = str(product.id)
        payload["lines"][0]["source_quotation_line_no"] = 1

        resp = await _post("/api/v1/orders", json=payload)

        assert resp.status_code == 201
        body = resp.json()
        assert body["source_quotation_id"] == str(quotation_id)
        assert body["crm_context_snapshot"]["party_label"] == "Rotor Works"
        assert body["lines"][0]["source_quotation_line_no"] == 1

        created_order = next(obj for obj in session.added if isinstance(obj, Order))
        created_line = next(obj for obj in session.added if isinstance(obj, OrderLine))
        assert created_order.source_quotation_id == quotation_id
        assert created_order.crm_context_snapshot == crm_context_snapshot
        assert created_line.source_quotation_line_no == 1
    finally:
        _teardown(prev)


async def test_create_order_with_cod_terms() -> None:
    customer = FakeCustomer()
    product = FakeProduct(product_id=uuid.UUID(_PRODUCT_ID))

    line = FakeOrderLine(product_id=product.id)
    order = FakeOrder(
        customer_id=customer.id,
        lines=[line],
        customer=customer,
    )
    order.payment_terms_code = "COD"
    order.payment_terms_days = 0

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(customer)  # customer lookup
    session.queue_scalars([product.id])  # product check
    session.queue_count(100)  # stock availability for line
    session.queue_scalar(None)  # set_tenant (get_order)
    session.queue_scalar(order)  # get_order

    prev = _setup(session)
    try:
        payload = _valid_order_payload(customer_id=str(customer.id))
        payload["payment_terms_code"] = "COD"
        payload["lines"][0]["product_id"] = str(product.id)
        resp = await _post("/api/v1/orders", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["payment_terms_code"] == "COD"
        assert body["payment_terms_days"] == 0
    finally:
        _teardown(prev)


async def test_create_order_with_sales_team_commission() -> None:
    customer = FakeCustomer()
    product = FakeProduct(product_id=uuid.UUID(_PRODUCT_ID))

    line = FakeOrderLine(product_id=product.id)
    order = FakeOrder(
        customer_id=customer.id,
        lines=[line],
        customer=customer,
        sales_team=[
            {
                "sales_person": "Alice Chen",
                "allocated_percentage": "60.00",
                "commission_rate": "5.00",
                "allocated_amount": "30.00",
            },
            {
                "sales_person": "Bob Lin",
                "allocated_percentage": "40.00",
                "commission_rate": "2.50",
                "allocated_amount": "10.00",
            },
        ],
        total_commission=Decimal("40.00"),
    )

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(customer)  # customer lookup
    session.queue_scalars([product.id])  # product check
    session.queue_count(100)  # stock availability for line
    session.queue_scalar(None)  # set_tenant (get_order)
    session.queue_scalar(order)  # get_order

    prev = _setup(session)
    try:
        payload = _valid_order_payload(customer_id=str(customer.id))
        payload["lines"][0]["product_id"] = str(product.id)
        payload["sales_team"] = [
            {
                "sales_person": "Alice Chen",
                "allocated_percentage": "60.00",
                "commission_rate": "5.00",
            },
            {
                "sales_person": "Bob Lin",
                "allocated_percentage": "40.00",
                "commission_rate": "2.50",
            },
        ]
        resp = await _post("/api/v1/orders", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["total_commission"] == "40.00"
        assert [member["sales_person"] for member in body["sales_team"]] == [
            "Alice Chen",
            "Bob Lin",
        ]
        assert body["sales_team"][0]["allocated_amount"] == "30.00"
        assert body["sales_team"][1]["allocated_amount"] == "10.00"

        created_order = next(obj for obj in session.added if isinstance(obj, Order))
        assert created_order.total_commission == Decimal("40.00")
        assert created_order.sales_team == [
            {
                "sales_person": "Alice Chen",
                "allocated_percentage": "60.00",
                "commission_rate": "5.00",
                "allocated_amount": "30.00",
            },
            {
                "sales_person": "Bob Lin",
                "allocated_percentage": "40.00",
                "commission_rate": "2.50",
                "allocated_amount": "10.00",
            },
        ]

        from common.models.audit_log import AuditLog

        audit = next(obj for obj in session.added if isinstance(obj, AuditLog))
        assert audit.action == "ORDER_CREATED"
        assert audit.after_state["total_commission"] == "40.00"
        assert audit.after_state["sales_team"] == created_order.sales_team
    finally:
        _teardown(prev)




async def test_create_order_persists_header_discounts() -> None:
    customer = FakeCustomer()
    product = FakeProduct(product_id=uuid.UUID(_PRODUCT_ID))

    line = FakeOrderLine(product_id=product.id)
    order = FakeOrder(
        customer_id=customer.id,
        lines=[line],
        customer=customer,
    )
    order.discount_amount = Decimal("100.00")
    order.discount_percent = Decimal("0.0000")
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
        payload["discount_amount"] = 100.0
        payload["lines"][0]["product_id"] = str(product.id)
        resp = await _post("/api/v1/orders", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["discount_amount"] == "100.00"
        assert body["discount_percent"] == "0.0000"
        assert body["total_amount"] == "950.00"

        created_order = next(obj for obj in session.added if isinstance(obj, Order))
        assert created_order.discount_amount == Decimal("100.00")
        assert created_order.discount_percent == Decimal("0.0000")
        assert created_order.total_amount == Decimal("950.00")
    finally:
        _teardown(prev)


async def test_create_order_rejects_multiple_header_discount_modes() -> None:
    session = FakeAsyncSession()
    prev = _setup(session)
    try:
        payload = _valid_order_payload()
        payload["discount_amount"] = 100.0
        payload["discount_percent"] = 0.1
        resp = await _post("/api/v1/orders", json=payload)
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any("discount_amount and discount_percent" in item["msg"] for item in detail)
    finally:
        _teardown(prev)


async def test_create_order_rejects_sales_team_over_100_percent() -> None:
    customer = FakeCustomer()
    product = FakeProduct(product_id=uuid.UUID(_PRODUCT_ID))

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(customer)  # customer lookup
    session.queue_scalars([product.id])  # product check
    session.queue_count(100)  # stock availability for line

    prev = _setup(session)
    try:
        payload = _valid_order_payload(customer_id=str(customer.id))
        payload["lines"][0]["product_id"] = str(product.id)
        payload["sales_team"] = [
            {
                "sales_person": "Alice Chen",
                "allocated_percentage": "60.00",
                "commission_rate": "5.00",
            },
            {
                "sales_person": "Bob Lin",
                "allocated_percentage": "50.00",
                "commission_rate": "2.50",
            },
        ]
        resp = await _post("/api/v1/orders", json=payload)
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"][0]["field"] == "sales_team"
    finally:
        _teardown(prev)


async def test_create_order_denies_warehouse_write_access() -> None:
    session = FakeAsyncSession()

    prev = _setup(session)
    try:
        resp = await _post(
            "/api/v1/orders",
            json=_valid_order_payload(),
            headers=auth_header("warehouse"),
        )
        assert resp.status_code == 403
    finally:
        _teardown(prev)


async def test_update_order_status_denies_warehouse_write_access() -> None:
    session = FakeAsyncSession()

    prev = _setup(session)
    try:
        resp = await _patch(
            f"/api/v1/orders/{uuid.uuid4()}/status",
            json={"new_status": "confirmed"},
            headers=auth_header("warehouse"),
        )
        assert resp.status_code == 403
    finally:
        _teardown(prev)


async def test_create_order_invalid_payment_terms() -> None:
    """Invalid payment_terms_code returns 422."""
    session = FakeAsyncSession()
    prev = _setup(session)
    try:
        payload = _valid_order_payload()
        payload["payment_terms_code"] = "NET_999"
        resp = await _post("/api/v1/orders", json=payload)
        assert resp.status_code == 422
    finally:
        _teardown(prev)


async def test_list_orders_sort_by_created_at_asc() -> None:
    o1 = FakeOrder(status="pending")
    o2 = FakeOrder(status="confirmed")

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_count(2)
    session.queue_scalars([o1, o2])

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/orders?sort_by=created_at&sort_order=asc")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
    finally:
        _teardown(prev)


async def test_list_orders_sort_by_total_amount_desc() -> None:
    o1 = FakeOrder(status="pending")
    o2 = FakeOrder(status="confirmed")

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_count(2)
    session.queue_scalars([o1, o2])

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/orders?sort_by=total_amount&sort_order=desc")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
    finally:
        _teardown(prev)


async def test_list_orders_sort_by_order_number_asc() -> None:
    o1 = FakeOrder(status="pending")
    o2 = FakeOrder(status="confirmed")

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_count(2)
    session.queue_scalars([o1, o2])

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/orders?sort_by=order_number&sort_order=asc")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
    finally:
        _teardown(prev)


async def test_list_orders_sort_by_status_desc() -> None:
    o1 = FakeOrder(status="pending")
    o2 = FakeOrder(status="confirmed")

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_count(2)
    session.queue_scalars([o1, o2])

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/orders?sort_by=status&sort_order=desc")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
    finally:
        _teardown(prev)


async def test_list_orders_with_date_range_filter() -> None:
    o1 = FakeOrder(status="pending")

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_count(1)
    session.queue_scalars([o1])

    prev = _setup(session)
    try:
        resp = await _get("/api/v1/orders?date_from=2026-01-01&date_to=2026-12-31")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
    finally:
        _teardown(prev)


async def test_create_order_defaults_to_net30() -> None:
    """Omitting payment_terms_code defaults to NET_30."""
    customer = FakeCustomer()
    product = FakeProduct(product_id=uuid.UUID(_PRODUCT_ID))

    line = FakeOrderLine(product_id=product.id)
    order = FakeOrder(
        customer_id=customer.id,
        lines=[line],
        customer=customer,
    )
    order.payment_terms_code = "NET_30"
    order.payment_terms_days = 30

    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session.queue_scalar(customer)  # customer lookup
    session.queue_scalars([product.id])  # product check
    session.queue_count(100)  # stock availability for line
    session.queue_scalar(None)  # set_tenant (get_order)
    session.queue_scalar(order)  # get_order

    prev = _setup(session)
    try:
        payload = _valid_order_payload(customer_id=str(customer.id))
        payload["lines"][0]["product_id"] = str(product.id)
        del payload["payment_terms_code"]
        resp = await _post("/api/v1/orders", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["payment_terms_code"] == "NET_30"
        assert body["payment_terms_days"] == 30
    finally:
        _teardown(prev)
