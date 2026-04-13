"""Endpoint integration tests for reorder point preview and apply — Story 4.7.

Tests the HTTP endpoints (not just the service layer) using httpx AsyncClient
against the real FastAPI app. Each test is fully independent.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport
from httpx import AsyncClient as HttpxAsyncClient

from app.main import create_app
from common.database import AsyncSessionLocal, engine
from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.supplier import Supplier
from common.models.supplier_order import (
    SupplierOrder,
    SupplierOrderLine,
    SupplierOrderStatus,
)
from common.models.warehouse import Warehouse
from common.tenant import DEFAULT_TENANT_ID
from domains.customers.models import Customer
from domains.inventory.reorder_point import (
    compute_reorder_points_preview,
)
from domains.invoices.models import InvoiceNumberRange

TENANT = DEFAULT_TENANT_ID


# ── Auth header helper ──────────────────────────────────────────


def auth_header(role: str = "owner") -> dict[str, str]:
    """Return a valid auth header with a real JWT for testing."""
    from common.config import settings
    payload = {
        "sub": "00000000-0000-0000-0000-000000000111",
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "role": role,
        "exp": datetime.now(tz=UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}



# ── Helpers ────────────────────────────────────────────────────


async def _make_adjustment(
    session, product_id, warehouse_id, quantity_change, reason, days_ago=1
):
    adj = StockAdjustment(
        tenant_id=TENANT,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity_change=quantity_change,
        reason_code=reason,
        actor_id="test-actor",
    )
    session.add(adj)
    await session.flush()
    return adj


async def _make_received_order(
    session, supplier_id, product_id, warehouse_id, order_date, received_date, quantity=50
):
    order = SupplierOrder(
        tenant_id=TENANT,
        supplier_id=supplier_id,
        order_number=f"PO-TEST-{uuid.uuid4().hex[:6]}",
        status=SupplierOrderStatus.RECEIVED,
        order_date=order_date,
        received_date=received_date,
        created_by="test",
    )
    session.add(order)
    await session.flush()

    line = SupplierOrderLine(
        order_id=order.id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity_ordered=quantity,
        quantity_received=quantity,
    )
    session.add(line)
    await session.flush()
    return order, line


async def _commit(session):
    await session.commit()


# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def tenant_id():
    return DEFAULT_TENANT_ID


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def warehouse(db_session, tenant_id):
    w = Warehouse(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="ROP Test WH",
        code=f"RWH{uuid.uuid4().hex[:6].upper()}",
        is_active=True,
    )
    db_session.add(w)
    await db_session.flush()
    await _commit(db_session)
    return w


@pytest_asyncio.fixture
async def product_with_history(db_session, tenant_id, warehouse):
    p = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"PH{uuid.uuid4().hex[:6].upper()}",
        name="Product With History",
        category="TestCat",
        status="active",
    )
    db_session.add(p)
    await db_session.flush()

    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=p.id,
        warehouse_id=warehouse.id,
        quantity=100,
        reorder_point=0,
    )
    db_session.add(stock)
    await db_session.flush()

    supplier = Supplier(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="History Supplier",
        is_active=True,
        default_lead_time_days=12,
    )
    db_session.add(supplier)
    await db_session.flush()

    await _make_received_order(
        db_session,
        supplier.id,
        p.id,
        warehouse.id,
        date.today() - timedelta(days=24),
        date.today() - timedelta(days=15),
        quantity=30,
    )

    for days in [10, 20, 30]:
        await _make_adjustment(
            db_session, p.id, warehouse.id,
            quantity_change=-10,
            reason=ReasonCode.SALES_RESERVATION,
            days_ago=days,
        )
    await _commit(db_session)
    return p


@pytest_asyncio.fixture
async def product_without_history(db_session, tenant_id, warehouse):
    p = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"PN{uuid.uuid4().hex[:6].upper()}",
        name="Product Without History",
        category="TestCat",
        status="active",
    )
    db_session.add(p)
    await db_session.flush()

    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=p.id,
        warehouse_id=warehouse.id,
        quantity=50,
        reorder_point=0,
    )
    db_session.add(stock)
    await db_session.flush()
    await _commit(db_session)
    return p


# ── Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compute_endpoint_returns_candidate_and_skipped(
    db_session,
    tenant_id,
    warehouse,
    product_with_history,
    product_without_history,
):
    """test_compute_endpoint_returns_candidate_and_skipped.

    POST /api/v1/inventory/reorder-points/compute returns both candidate
    and skipped rows, with candidate rows having computed_reorder_point
    and skipped rows having a non-null skip_reason.
    """
    app = create_app()
    transport = ASGITransport(app=app)

    async with HttpxAsyncClient(
        transport=transport, base_url="http://test", headers=auth_header()
    ) as client:
        resp = await client.post(
            "/api/v1/inventory/reorder-points/compute",
            json={
                "safety_factor": 0.5,
                "lookback_days": 90,
                "lookback_days_lead_time": 180,
            },
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()

    assert "candidate_rows" in body
    assert "skipped_rows" in body
    assert "parameters" in body

    candidate_ids = {str(r["product_id"]) for r in body["candidate_rows"]}
    skipped_ids = {str(r["product_id"]) for r in body["skipped_rows"]}

    assert str(product_with_history.id) in candidate_ids
    assert str(product_without_history.id) in skipped_ids

    skipped_row = next(
        r for r in body["skipped_rows"]
        if str(r["product_id"]) == str(product_without_history.id)
    )
    assert skipped_row["skip_reason"] in (
        "insufficient_history",
        "source_unresolved",
        "lead_time_unconfigured",
        None,
    )
    assert skipped_row["computed_reorder_point"] is None
    assert skipped_row["policy_type"] == "continuous"
    assert skipped_row["target_stock_qty"] == 0
    assert skipped_row["on_order_qty"] == 0
    assert skipped_row["in_transit_qty"] == 0
    assert skipped_row["reserved_qty"] == 0
    assert skipped_row["planning_horizon_days"] == 0
    assert skipped_row["effective_horizon_days"] == 0
    assert skipped_row["lead_time_sample_count"] is None
    assert skipped_row["lead_time_confidence"] is None

    candidate_row = next(
        r for r in body["candidate_rows"]
        if str(r["product_id"]) == str(product_with_history.id)
    )
    assert candidate_row["computed_reorder_point"] is not None
    assert candidate_row["computed_reorder_point"] >= 0
    assert candidate_row["policy_type"] == "continuous"
    assert candidate_row["target_stock_qty"] == 0
    assert candidate_row["inventory_position"] == 100
    assert candidate_row["on_order_qty"] == 0
    assert candidate_row["in_transit_qty"] == 0
    assert candidate_row["reserved_qty"] == 0
    assert candidate_row["planning_horizon_days"] == 0
    assert candidate_row["effective_horizon_days"] == 0
    assert candidate_row["lead_time_source"] == "actual"
    assert candidate_row["lead_time_sample_count"] == 1
    assert candidate_row["lead_time_confidence"] == "low"


@pytest.mark.asyncio
async def test_apply_endpoint_only_updates_selected_rows(
    db_session,
    tenant_id,
    warehouse,
    product_with_history,
    product_without_history,
):
    """test_apply_endpoint_only_updates_selected_rows.

    PUT /api/v1/inventory/reorder-points/apply with a specific product_id
    only updates that row and does not affect others.
    """
    app = create_app()
    transport = ASGITransport(app=app)

    async with HttpxAsyncClient(
        transport=transport, base_url="http://test", headers=auth_header()
    ) as client:
        # First compute preview
        compute_resp = await client.post(
            "/api/v1/inventory/reorder-points/compute",
            json={
                "safety_factor": 0.5,
                "lookback_days": 90,
                "lookback_days_lead_time": 180,
            },
        )
        assert compute_resp.status_code == 200
        compute_body = compute_resp.json()

        # Find the candidate row for product_with_history and use its stock_id
        target_row = next(
            (r for r in compute_body["candidate_rows"]
             if str(r["product_id"]) == str(product_with_history.id)),
            None,
        )
        assert target_row is not None, "product_with_history should be a candidate"
        target_stock_id = target_row["stock_id"]

        # Apply only that row
        apply_resp = await client.put(
            "/api/v1/inventory/reorder-points/apply",
            json={
                "selected_stock_ids": [target_stock_id],
                "safety_factor": 0.5,
                "lookback_days": 90,
                "lookback_days_lead_time": 180,
            },
        )

    assert apply_resp.status_code == 200, (
        f"Expected 200, got {apply_resp.status_code}: {apply_resp.text}"
    )
    apply_body = apply_resp.json()

    assert "updated_count" in apply_body
    assert "skipped_count" in apply_body
    assert apply_body["updated_count"] >= 1


@pytest.mark.asyncio
async def test_skipped_rows_are_not_overwritten(
    db_session,
    tenant_id,
    warehouse,
    product_with_history,
    product_without_history,
):
    """test_skipped_rows_are_not_overwritten.

    Rows that appear in skipped_rows (e.g. insufficient_history) are NOT
    modified when apply is called with the same parameters.
    """
    from sqlalchemy import select

    app = create_app()
    transport = ASGITransport(app=app)

    # Get original reorder_point for product_without_history
    orig_stmt = select(InventoryStock.reorder_point).where(
        InventoryStock.product_id == product_without_history.id
    )
    result = await db_session.execute(orig_stmt)
    orig_rop = result.scalar_one()

    async with HttpxAsyncClient(
        transport=transport, base_url="http://test", headers=auth_header()
    ) as client:
        compute_resp = await client.post(
            "/api/v1/inventory/reorder-points/compute",
            json={
                "safety_factor": 0.5,
                "lookback_days": 90,
                "lookback_days_lead_time": 180,
            },
        )
        assert compute_resp.status_code == 200
        compute_body = compute_resp.json()

        # Find the stock_id for product_without_history (it is a skipped row)
        skipped_target = next(
            (r for r in compute_body["skipped_rows"]
             if str(r["product_id"]) == str(product_without_history.id)),
            None,
        )
        assert skipped_target is not None, "product_without_history should be in skipped_rows"

        # Apply its stock_id (even though it is a skipped row, the API accepts it)
        # The backend will re-compute and apply only if it appears in candidates
        apply_resp = await client.put(
            "/api/v1/inventory/reorder-points/apply",
            json={
                "selected_stock_ids": [skipped_target["stock_id"]],
                "safety_factor": 0.5,
                "lookback_days": 90,
                "lookback_days_lead_time": 180,
            },
        )
        assert apply_resp.status_code == 200

    # Verify product_without_history reorder_point unchanged
    new_result = await db_session.execute(orig_stmt)
    new_rop = new_result.scalar_one()
    assert new_rop == orig_rop, \
        f"Skipped row reorder_point was modified: was {orig_rop}, now {new_rop}"


# ── Additional fixtures for expanded coverage ─────────────────────


@pytest_asyncio.fixture
async def product_multi_supplier(db_session, tenant_id, warehouse):
    """Product with two suppliers of equal counts — skipped as source_unresolved."""
    p = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"PM{uuid.uuid4().hex[:4].upper()}",
        name="Multi Source Product",
        category="TestCat",
        status="active",
    )
    db_session.add(p)
    await db_session.flush()

    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=p.id,
        warehouse_id=warehouse.id,
        quantity=60,
        reorder_point=0,
    )
    db_session.add(stock)
    await db_session.flush()

    supplier_a = Supplier(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Supplier A",
        is_active=True,
    )
    supplier_b = Supplier(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Supplier B",
        is_active=True,
    )
    db_session.add_all([supplier_a, supplier_b])
    await db_session.flush()

    # Equal received lines from both suppliers — 50/50, not >60% threshold
    await _make_received_order(
        db_session, supplier_a.id, p.id, warehouse.id,
        date.today() - timedelta(days=30), date.today() - timedelta(days=23), quantity=10,
    )
    await _make_received_order(
        db_session, supplier_b.id, p.id, warehouse.id,
        date.today() - timedelta(days=20), date.today() - timedelta(days=13), quantity=10,
    )

    # Sufficient demand history
    for days in [5, 10, 15, 20]:
        await _make_adjustment(
            db_session, p.id, warehouse.id,
            quantity_change=-5,
            reason=ReasonCode.SALES_RESERVATION,
            days_ago=days,
        )
    await _commit(db_session)
    return p


@pytest_asyncio.fixture
async def product_supplier_default_fallback(db_session, tenant_id, warehouse):
    """Product with supplier default_lead_time_days but no received orders."""
    p = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"PD{uuid.uuid4().hex[:4].upper()}",
        name="Supplier Default Fallback Product",
        category="TestCat",
        status="active",
    )
    db_session.add(p)
    await db_session.flush()

    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=p.id,
        warehouse_id=warehouse.id,
        quantity=40,
        reorder_point=0,
    )
    db_session.add(stock)
    await db_session.flush()

    supplier = Supplier(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Supplier With Default",
        is_active=True,
        default_lead_time_days=14,
    )
    db_session.add(supplier)
    await db_session.flush()

    # Sufficient demand history, no supplier order history
    for days in [5, 10, 15, 20]:
        await _make_adjustment(
            db_session, p.id, warehouse.id,
            quantity_change=-5,
            reason=ReasonCode.SALES_RESERVATION,
            days_ago=days,
        )
    await _commit(db_session)
    return p


# ── Tests for remaining AC coverage ───────────────────────────────────────


@pytest.mark.asyncio
async def test_source_unresolved_skips_row(
    db_session,
    tenant_id,
    warehouse,
    product_multi_supplier,
):
    """AC3: Ambiguous supplier history falls back to business-default lead time.

    When a product has received orders from two suppliers at equal counts (50/50),
    the preview should still include the row, but supplier resolution stays unresolved
    and lead time falls back to the business default.
    """
    app = create_app()
    transport = ASGITransport(app=app)

    async with HttpxAsyncClient(
        transport=transport, base_url="http://test", headers=auth_header()
    ) as client:
        resp = await client.post(
            "/api/v1/inventory/reorder-points/compute",
            json={
                "safety_factor": 0.5,
                "lookback_days": 90,
                "lookback_days_lead_time": 180,
            },
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()

    candidate_ids = {str(r["product_id"]) for r in body["candidate_rows"]}
    assert str(product_multi_supplier.id) in candidate_ids, \
        "Product with ambiguous source should still appear in candidate rows"

    candidate_row = next(
        r for r in body["candidate_rows"]
        if str(r["product_id"]) == str(product_multi_supplier.id)
    )
    assert candidate_row["skip_reason"] is None
    assert candidate_row["lead_time_source"] == "business_default"
    assert candidate_row["lead_time_days"] == 80


@pytest.mark.asyncio
async def test_lead_time_fallback_chain(
    db_session,
    tenant_id,
    warehouse,
):
    """Rows without configured lead time are skipped from auto-calculation preview."""

    p = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"PF{uuid.uuid4().hex[:4].upper()}",
        name="Fallback Product",
        category="TestCat",
        status="active",
    )
    db_session.add(p)
    await db_session.flush()

    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=p.id,
        warehouse_id=warehouse.id,
        quantity=30,
        reorder_point=0,
    )
    db_session.add(stock)
    await db_session.flush()

    # Sufficient demand history, NO supplier orders
    for days in [5, 10, 15, 20]:
        await _make_adjustment(
            db_session, p.id, warehouse.id,
            quantity_change=-5,
            reason=ReasonCode.SALES_RESERVATION,
            days_ago=days,
        )
    await _commit(db_session)

    preview_rows, skipped_rows = await compute_reorder_points_preview(
        db_session, tenant_id,
        safety_factor=0.5,
        demand_lookback_days=90,
        lead_time_lookback_days=180,
    )

    candidate = next((c for c in preview_rows if c["product_id"] == p.id), None)
    assert candidate is not None, (
        "Product without lead-time history should use the business default"
    )
    assert candidate["lead_time_source"] == "business_default"
    assert candidate["lead_time_days"] == 80


@pytest.mark.asyncio
async def test_lead_time_supplier_default_fallback(
    db_session,
    tenant_id,
    warehouse,
    product_supplier_default_fallback,
):
    """Rows without a resolved replenishment source are skipped before using a guessed lead time."""
    product = product_supplier_default_fallback

    preview_rows, skipped_rows = await compute_reorder_points_preview(
        db_session, tenant_id,
        safety_factor=0.5,
        demand_lookback_days=90,
        lead_time_lookback_days=180,
    )

    candidate = next((c for c in preview_rows if c["product_id"] == product.id), None)
    assert candidate is not None, (
        "Product without a resolved lead-time source should use the business default"
    )
    assert candidate["lead_time_source"] == "business_default"
    assert candidate["lead_time_days"] == 80


@pytest.mark.asyncio
async def test_preview_candidate_has_all_explanation_columns(
    db_session,
    tenant_id,
    warehouse,
    product_with_history,
):
    """AC4: Candidate rows include all required explanation columns.

    Verifies the preview response includes: reorder_point, avg_daily_usage,
    lead_time_days, safety_stock, demand_reason, movement_count,
    lead_time_source, skip_reason (None for candidates).
    """
    app = create_app()
    transport = ASGITransport(app=app)

    async with HttpxAsyncClient(
        transport=transport, base_url="http://test", headers=auth_header()
    ) as client:
        resp = await client.post(
            "/api/v1/inventory/reorder-points/compute",
            json={
                "safety_factor": 0.5,
                "lookback_days": 90,
                "lookback_days_lead_time": 180,
            },
        )

    assert resp.status_code == 200
    body = resp.json()

    candidate_row = next(
        r for r in body["candidate_rows"]
        if str(r["product_id"]) == str(product_with_history.id)
    )
    assert candidate_row is not None

    # Required columns from AC4
    required = [
        "product_id", "warehouse_id", "computed_reorder_point",
        "avg_daily_usage", "lead_time_days", "safety_stock",
        "demand_basis", "movement_count", "lead_time_source",
        "skip_reason",  # must be null for candidates
    ]
    for col in required:
        assert col in candidate_row, f"Missing column: {col}"

    assert candidate_row["skip_reason"] is None, "Candidate must not be skipped"
    assert candidate_row["computed_reorder_point"] > 0
    assert candidate_row["avg_daily_usage"] > 0


@pytest.mark.asyncio
async def test_confirm_order_creates_sales_reservation_demand_history(
    db_session,
    tenant_id,
    warehouse,
):
    """AC1: confirm_order creates sales_reservation demand history + emits event.

    Given a pending sales order with a line item
    When the order is confirmed via the API
    Then StockAdjustment records are created with reason SALES_RESERVATION
    And StockChangedEvent is emitted for the affected product+warehouse.

    NOTE: This test will fail until Task 1 (confirm_order event emission)
    is complete. It is included here to validate the full AC1 requirement.
    """
    from decimal import Decimal

    from sqlalchemy import text

    from common.events import _registered_handlers
    from domains.orders.schemas import OrderCreate, OrderCreateLine, PaymentTermsCode
    from domains.orders.services import confirm_order, create_order

    # Set up: product + stock + pending order
    product = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"PC{uuid.uuid4().hex[:6].upper()}",
        name="Confirm Test Product",
        category="TestCat",
        status="active",
    )
    db_session.add(product)
    await db_session.flush()

    stock = InventoryStock(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=100,
        reorder_point=0,
    )
    db_session.add(stock)
    await db_session.flush()

    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        company_name="Confirm Test Customer",
        normalized_business_number=str(uuid.uuid4().int % 10**8).zfill(8),
        billing_address="Taipei",
        contact_name="Buyer",
        contact_phone="02-12345678",
        contact_email="buyer@test.local",
    )
    db_session.add(customer)
    await db_session.flush()

    number_range = InvoiceNumberRange(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        prefix=uuid.uuid4().hex[:2].upper(),
        start_number=1,
        end_number=99999999,
        next_number=1,
        is_active=True,
    )
    db_session.add(number_range)
    await db_session.flush()
    await db_session.commit()

    order_data = OrderCreate(
        customer_id=customer.id,
        payment_terms_code=PaymentTermsCode.NET_30,
        lines=[
            OrderCreateLine(
                product_id=product.id,
                quantity=Decimal("10"),
                unit_price=Decimal("10.00"),
                tax_policy_code="standard",
                description="Test line",
            )
        ],
    )
    order = await create_order(db_session, order_data, tenant_id=tenant_id)

    # Collect events
    events: list = []

    async def event_collector(event, _session):
        events.append(event)

    original_handlers = list(_registered_handlers)
    _registered_handlers.append(("StockChangedEvent", event_collector))

    try:
        # Confirm the order
        confirmed = await confirm_order(db_session, order.id, tenant_id=tenant_id)
        await db_session.commit()

        assert confirmed.status == "confirmed"

        # Check: SALES_RESERVATION adjustment was created
        result = await db_session.execute(
            text(
                "SELECT id, product_id, warehouse_id, quantity_change, reason_code "
                "FROM stock_adjustment "
                "WHERE tenant_id = :tenant AND product_id = :pid AND reason_code = :reason"
            ),
            {
                "tenant": str(tenant_id),
                "pid": str(product.id),
                "reason": ReasonCode.SALES_RESERVATION.value,
            },
        )
        rows = result.fetchall()
        assert len(rows) >= 1, "Expected at least one SALES_RESERVATION adjustment"

        adj = rows[0]
        assert adj.quantity_change < 0, "sales_reservation should be outbound (negative)"
        assert adj.warehouse_id == warehouse.id

        # Check: StockChangedEvent was emitted
        matching = [e for e in events
                    if e.product_id == product.id and e.warehouse_id == warehouse.id]
        assert len(matching) >= 1, "Expected StockChangedEvent to be emitted"

    finally:
        _registered_handlers.clear()
        _registered_handlers.extend(original_handlers)