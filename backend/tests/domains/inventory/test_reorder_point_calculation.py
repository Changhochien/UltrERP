"""Unit tests for reorder point calculation service."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.supplier import Supplier
from common.models.supplier_order import SupplierOrder, SupplierOrderLine, SupplierOrderStatus
from common.models.warehouse import Warehouse
from common.tenant import DEFAULT_TENANT_ID
from domains.inventory.reorder_point import (
    DEFAULT_LEAD_TIME_DAYS,
    MIN_DEMAND_EVENTS,
    SOURCE_UNRESOLVED,
    apply_reorder_points,
    compute_reorder_point_preview_row,
    get_average_daily_usage,
    get_lead_time_days,
    resolve_replenishment_source,
)
from tests.db import isolated_async_session

# ── Fixtures ──────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_session():
    """Provide a real async session for reorder point calculation tests."""
    async with isolated_async_session() as session:
        yield session


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return DEFAULT_TENANT_ID


@pytest_asyncio.fixture
async def warehouse(db_session: AsyncSession, tenant_id: uuid.UUID) -> Warehouse:
    w = Warehouse(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Test Warehouse",
        code="TW1",
        is_active=True,
    )
    db_session.add(w)
    await db_session.flush()
    return w


@pytest_asyncio.fixture
async def product(db_session: AsyncSession, tenant_id: uuid.UUID) -> Product:
    p = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="TEST-001",
        name="Test Product",
        category="TestCategory",
        status="active",
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def inventory_stock(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    product: Product,
    warehouse: Warehouse,
) -> InventoryStock:
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
    return stock


@pytest_asyncio.fixture
async def supplier(db_session: AsyncSession, tenant_id: uuid.UUID) -> Supplier:
    s = Supplier(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Test Supplier",
        default_lead_time_days=10,
        is_active=True,
    )
    db_session.add(s)
    await db_session.flush()
    return s


# ── Helpers ──────────────────────────────────────────────────────


async def _make_adjustment(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity_change: int,
    reason: ReasonCode,
    days_ago: int = 1,
) -> StockAdjustment:
    adj = StockAdjustment(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity_change=quantity_change,
        reason_code=reason,
        actor_id="test-actor",
        created_at=datetime.now() - timedelta(days=days_ago),
    )
    db_session.add(adj)
    await db_session.flush()
    return adj


async def _make_received_order(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    order_date: date,
    received_date: date,
) -> tuple[SupplierOrder, SupplierOrderLine]:
    order = SupplierOrder(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        order_number=f"PO-TEST-{uuid.uuid4().hex[:6]}",
        status=SupplierOrderStatus.RECEIVED,
        order_date=order_date,
        received_date=received_date,
        created_by="test",
    )
    db_session.add(order)
    await db_session.flush()

    line = SupplierOrderLine(
        id=uuid.uuid4(),
        order_id=order.id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity_ordered=50,
        quantity_received=50,
    )
    db_session.add(line)
    await db_session.flush()
    return order, line


# ── Tests ────────────────────────────────────────────────────────


class TestFormulaCalculation:
    """AC1 / AC6: ROP = Safety Stock + (Lead Time x Average Daily Usage).

    Safety Stock = avg_daily_usage x safety_factor x lead_time_days
    """

    @pytest.mark.asyncio
    async def test_formula_calculation(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        product: Product,
        warehouse: Warehouse,
        supplier: Supplier,
    ):
        """Verify ROP = safety_stock + (lead_time x avg_daily_usage)."""
        # Set up demand: 90 units over 90 days = 1.0 unit/day
        lookback = 90
        for i in range(MIN_DEMAND_EVENTS, lookback + 1):
            await _make_adjustment(
                db_session, tenant_id, product.id, warehouse.id,
                quantity_change=-1,
                reason=ReasonCode.SALES_RESERVATION,
                days_ago=i,
            )

        # Set up lead time: 10 days
        await _make_received_order(
            db_session, tenant_id, supplier.id, product.id, warehouse.id,
            order_date=date.today() - timedelta(days=20),
            received_date=date.today() - timedelta(days=10),
        )

        safety_factor = 0.5
        lead_time, _ = await get_lead_time_days(
            db_session, tenant_id, product.id, warehouse.id,
        )
        avg_daily, _ = await get_average_daily_usage(
            db_session, tenant_id, product.id, warehouse.id,
        )

        expected_safety_stock = round(avg_daily * safety_factor * lead_time, 2)
        expected_rop = round(expected_safety_stock + (lead_time * avg_daily))

        row = await compute_reorder_point_preview_row(
            db_session, tenant_id, product.id, warehouse.id,
            safety_factor=safety_factor,
        )

        assert row["skipped_reason"] is None
        assert row["reorder_point"] == expected_rop
        assert row["safety_stock"] == expected_safety_stock
        assert row["avg_daily_usage"] == round(avg_daily, 4)
        assert row["lead_time_days"] == lead_time

    @pytest.mark.asyncio
    async def test_zero_demand_returns_insufficient_history(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        product: Product,
        warehouse: Warehouse,
    ):
        """Rows with no demand history are skipped with insufficient_history."""
        row = await compute_reorder_point_preview_row(
            db_session, tenant_id, product.id, warehouse.id,
        )
        assert row["skipped_reason"] == "insufficient_history"
        assert row["reorder_point"] == 0


class TestDemandReasonFiltering:
    """AC2: Only whitelisted outbound reasons are included in usage math."""

    @pytest.mark.asyncio
    async def test_only_sales_reservation_included(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        product: Product,
        warehouse: Warehouse,
    ):
        """Only SALES_RESERVATION adjustments contribute to average daily usage."""
        lookback = 90
        # Add SALES_RESERVATION events
        for i in range(MIN_DEMAND_EVENTS, lookback + 1):
            await _make_adjustment(
                db_session, tenant_id, product.id, warehouse.id,
                quantity_change=-10,
                reason=ReasonCode.SALES_RESERVATION,
                days_ago=i,
            )
        # Add noise from other reasons — should be ignored
        for i in range(1, 10):
            await _make_adjustment(
                db_session, tenant_id, product.id, warehouse.id,
                quantity_change=-100,
                reason=ReasonCode.CORRECTION,
                days_ago=i,
            )
            await _make_adjustment(
                db_session, tenant_id, product.id, warehouse.id,
                quantity_change=5,
                reason=ReasonCode.RETURNED,
                days_ago=i,
            )

        avg_daily, movement_count = await get_average_daily_usage(
            db_session, tenant_id, product.id, warehouse.id,
            allowed_reasons=(ReasonCode.SALES_RESERVATION,),
        )

        # 1 event per day * 10 units = 10 units/day
        # Due to timing precision in cutoff calculation, movement_count may be 88 or 89
        # Accept either value as valid (edge case at boundary)
        assert movement_count in (lookback - MIN_DEMAND_EVENTS, lookback - MIN_DEMAND_EVENTS + 1)
        # Verify avg_daily is approximately correct (10 units/day scaled by event ratio)
        # Allow for both 88 and 89 event scenarios due to timing edge case
        expected_88 = round(10 * 88 / lookback, 4)  # 9.7778
        expected_89 = round(10 * 89 / lookback, 4)  # 9.8889
        assert avg_daily == expected_88 or avg_daily == expected_89

    @pytest.mark.asyncio
    async def test_non_sales_reservation_excluded(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        product: Product,
        warehouse: Warehouse,
    ):
        """Non-SALES_RESERVATION adjustments produce zero usage."""
        for i in range(1, 10):
            await _make_adjustment(
                db_session, tenant_id, product.id, warehouse.id,
                quantity_change=-50,
                reason=ReasonCode.CORRECTION,
                days_ago=i,
            )

        avg_daily, movement_count = await get_average_daily_usage(
            db_session, tenant_id, product.id, warehouse.id,
        )

        assert avg_daily == 0.0
        assert movement_count == 0


class TestLeadTimeFallbackChain:
    """AC3: Lead time resolves through actual → supplier default → 7-day fallback."""

    @pytest.mark.asyncio
    async def test_actual_lead_time_used(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        product: Product,
        warehouse: Warehouse,
        supplier: Supplier,
    ):
        """When received orders exist, actual lead time is returned."""
        # Order placed 15 days ago, received 5 days ago → 10 day lead time
        await _make_received_order(
            db_session, tenant_id, supplier.id, product.id, warehouse.id,
            order_date=date.today() - timedelta(days=15),
            received_date=date.today() - timedelta(days=5),
        )

        lead_time, source = await get_lead_time_days(
            db_session, tenant_id, product.id, warehouse.id,
        )

        assert source == "actual"
        assert lead_time == 10

    @pytest.mark.asyncio
    async def test_supplier_default_used_when_no_received_orders(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        product: Product,
        warehouse: Warehouse,
        supplier: Supplier,
    ):
        """When no received orders exist, supplier.default_lead_time_days is used."""
        # Create pending order (not received) — should be ignored
        order = SupplierOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            supplier_id=supplier.id,
            order_number=f"PO-PENDING-{uuid.uuid4().hex[:6]}",
            status=SupplierOrderStatus.PENDING,
            order_date=date.today() - timedelta(days=5),
            created_by="test",
        )
        db_session.add(order)
        await db_session.flush()

        line = SupplierOrderLine(
            id=uuid.uuid4(),
            order_id=order.id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity_ordered=50,
            quantity_received=0,
        )
        db_session.add(line)
        await db_session.flush()

        lead_time, source = await get_lead_time_days(
            db_session, tenant_id, product.id, warehouse.id,
        )

        assert source == "supplier_default"
        assert lead_time == supplier.default_lead_time_days

    @pytest.mark.asyncio
    async def test_fallback_to_default_lead_time_days(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        product: Product,
        warehouse: Warehouse,
    ):
        """When no supplier history exists and no default, the shared fallback is used."""
        lead_time, source = await get_lead_time_days(
            db_session, tenant_id, product.id, warehouse.id,
        )

        assert source == "fallback_7d"
        assert lead_time == DEFAULT_LEAD_TIME_DAYS


class TestAmbiguousSourceSkip:
    """AC3 / AC6: Competing suppliers without a dominant source returns source_unresolved."""

    @pytest.mark.asyncio
    async def test_ambiguous_source_returns_source_unresolved(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        product: Product,
        warehouse: Warehouse,
    ):
        """When two suppliers each have ~50% of orders, source is unresolved."""
        supplier_a = Supplier(
            id=uuid.uuid4(), tenant_id=tenant_id, name="Supplier A",
            default_lead_time_days=5, is_active=True,
        )
        supplier_b = Supplier(
            id=uuid.uuid4(), tenant_id=tenant_id, name="Supplier B",
            default_lead_time_days=15, is_active=True,
        )
        db_session.add_all([supplier_a, supplier_b])
        await db_session.flush()

        # 3 orders from supplier A, 3 from supplier B — neither has >60%
        for _ in range(3):
            await _make_received_order(
                db_session, tenant_id, supplier_a.id, product.id, warehouse.id,
                order_date=date.today() - timedelta(days=20),
                received_date=date.today() - timedelta(days=10),
            )
            await _make_received_order(
                db_session, tenant_id, supplier_b.id, product.id, warehouse.id,
                order_date=date.today() - timedelta(days=20),
                received_date=date.today() - timedelta(days=10),
            )

        result = await resolve_replenishment_source(
            db_session, tenant_id, product.id, warehouse.id,
        )
        assert result == SOURCE_UNRESOLVED

    @pytest.mark.asyncio
    async def test_dominant_supplier_resolved(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        product: Product,
        warehouse: Warehouse,
    ):
        """When one supplier has >60% of orders, it is resolved."""
        supplier_a = Supplier(
            id=uuid.uuid4(), tenant_id=tenant_id, name="Supplier A",
            default_lead_time_days=5, is_active=True,
        )
        supplier_b = Supplier(
            id=uuid.uuid4(), tenant_id=tenant_id, name="Supplier B",
            default_lead_time_days=15, is_active=True,
        )
        db_session.add_all([supplier_a, supplier_b])
        await db_session.flush()

        # 7 orders from A, 3 from B → A has >60%
        for _ in range(7):
            await _make_received_order(
                db_session, tenant_id, supplier_a.id, product.id, warehouse.id,
                order_date=date.today() - timedelta(days=20),
                received_date=date.today() - timedelta(days=10),
            )
        for _ in range(3):
            await _make_received_order(
                db_session, tenant_id, supplier_b.id, product.id, warehouse.id,
                order_date=date.today() - timedelta(days=20),
                received_date=date.today() - timedelta(days=10),
            )

        result = await resolve_replenishment_source(
            db_session, tenant_id, product.id, warehouse.id,
        )
        assert result == supplier_a.id


class TestApplyReorderPoints:
    """AC5: Apply only updates explicitly selected rows."""

    @pytest.mark.asyncio
    async def test_apply_updates_selected_rows(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        product: Product,
        warehouse: Warehouse,
        inventory_stock: InventoryStock,
        supplier: Supplier,
    ):
        """Only rows in selected_rows are updated; unselected rows stay unchanged."""
        # Set up demand so computation succeeds
        for i in range(MIN_DEMAND_EVENTS, 91):
            await _make_adjustment(
                db_session, tenant_id, product.id, warehouse.id,
                quantity_change=-1,
                reason=ReasonCode.SALES_RESERVATION,
                days_ago=i,
            )
        await _make_received_order(
            db_session, tenant_id, supplier.id, product.id, warehouse.id,
            order_date=date.today() - timedelta(days=20),
            received_date=date.today() - timedelta(days=10),
        )

        preview_row = await compute_reorder_point_preview_row(
            db_session, tenant_id, product.id, warehouse.id,
        )
        assert preview_row["skipped_reason"] is None

        # Apply with the computed row
        result = await apply_reorder_points(
            db_session, tenant_id,
            selected_rows=[preview_row],
            safety_factor=0.5,
            demand_lookback_days=90,
            lead_time_lookback_days=180,
        )

        assert result["updated_count"] == 1
        assert result["skipped_count"] == 0

        # Verify stock was updated
        await db_session.refresh(inventory_stock)
        assert inventory_stock.reorder_point == preview_row["reorder_point"]

    @pytest.mark.asyncio
    async def test_apply_empty_list(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
    ):
        """Applying an empty selection returns zero updated."""
        result = await apply_reorder_points(
            db_session, tenant_id,
            selected_rows=[],
            safety_factor=0.5,
            demand_lookback_days=90,
            lead_time_lookback_days=180,
        )
        assert result["updated_count"] == 0


# ── Order confirmation integration ────────────────────────────


class TestOrderConfirmationDemandHistory:
    """AC1: Confirming a sales order creates demand history for reorder points.

    Given a confirmed sales order exists with line items
    When the order is confirmed
    Then StockAdjustment records are created for each line with reason sales_reservation
    And StockChangedEvent is emitted so reorder alerts can fire
    And those outbound adjustments become eligible demand history.
    """

    async def test_confirm_order_emits_stock_changed_event(self) -> None:
        """Confirming a sales order emits StockChangedEvent for each line."""
        from common.events import StockChangedEvent, _registered_handlers
        from domains.orders.services import confirm_order
        from tests.domains.orders._helpers import (
            FakeAsyncSession,
            FakeCustomer,
            FakeInvoiceNumberRange,
            FakeOrder,
            FakeOrderLine,
            setup_session,
            teardown_session,
        )

        # Track emitted events
        emitted_events: list[StockChangedEvent] = []
        original_handlers = _registered_handlers.copy()

        async def capture_handler(event: StockChangedEvent, _session: object) -> None:
            emitted_events.append(event)

        _registered_handlers.clear()
        _registered_handlers.append(("StockChangedEvent", capture_handler))

        try:
            customer = FakeCustomer()
            product_a = uuid.uuid4()
            product_b = uuid.uuid4()
            line_a = FakeOrderLine(product_id=product_a)
            line_b = FakeOrderLine(product_id=product_b)
            lines = [line_a, line_b]
            order = FakeOrder(customer_id=customer.id, lines=lines, customer=customer)

            session = FakeAsyncSession()
            # Queue confirm_order execution flow
            session.queue_scalar(None)  # set_tenant
            session.queue_scalar(order)  # order lookup with lines
            product_rows = [
                type(
                    "Row",
                    (),
                    {
                        "id": line.product_id,
                        "code": f"PROD-{i}",
                        "name": f"Product {i}",
                        "category": f"Category {i}",
                    },
                )()
                for i, line in enumerate(order.lines)
            ]
            session.queue_rows(product_rows)  # product code lookup
            session.queue_scalar(customer)  # customer lookup (confirm_order)
            session.queue_scalar(customer)  # customer lookup (_create_invoice_core)
            session.queue_scalar(FakeInvoiceNumberRange())  # number_range
            for _line in order.lines:
                session.queue_scalar(None)  # supplier invoice unit_cost lookup
            session.queue_scalar(uuid.uuid4())  # warehouse_id lookup
            for _line in order.lines:
                # InventoryStock per line (for _create_invoice_core stock update)
                from tests.domains.orders._helpers import FakeInventoryStock
                session.queue_scalar(FakeInventoryStock(quantity=100))
            session.queue_scalar(None)  # flush
            session.queue_scalar(None)  # set_tenant (get_order reload)
            session.queue_scalar(order)  # get_order reload

            prev = setup_session(session)
            try:
                await confirm_order(session, order.id, tenant_id=order.tenant_id)
            finally:
                teardown_session(prev)

            # Verify StockChangedEvent was emitted for each line
            assert len(emitted_events) == 2, f"Expected 2 events, got {len(emitted_events)}"
            emitted_product_ids = {e.product_id for e in emitted_events}
            assert product_a in emitted_product_ids
            assert product_b in emitted_product_ids

            for event in emitted_events:
                assert isinstance(event, StockChangedEvent)
                # Each line's stock is FakeInventoryStock(quantity=100) initially.
                # My code decrements each by line.quantity (10 units), so 100 → 90.
                assert event.before_quantity == 100
                assert event.after_quantity == 90  # 100 - 10 outbound

            # Verify StockAdjustment records with sales_reservation reason were created
            sales_reservation_adjustments = [
                o for o in session.added
                if isinstance(o, StockAdjustment) and o.reason_code == ReasonCode.SALES_RESERVATION
            ]
            assert len(sales_reservation_adjustments) == 2, (
                "Expected 2 sales_reservation adjustments, got "
                f"{len(sales_reservation_adjustments)}"
            )

            adjustment_product_ids = {adj.product_id for adj in sales_reservation_adjustments}
            assert product_a in adjustment_product_ids
            assert product_b in adjustment_product_ids

            for adj in sales_reservation_adjustments:
                assert adj.quantity_change < 0, "quantity_change must be negative for outbound"
                assert adj.actor_id is not None

        finally:
            _registered_handlers.clear()
            _registered_handlers.extend(original_handlers)

    async def test_confirm_order_sales_reservation_quantity_is_negative(self) -> None:
        """The quantity_change on a sales_reservation adjustment is negative (outbound)."""
        from domains.orders.services import confirm_order
        from tests.domains.orders._helpers import (
            FakeAsyncSession,
            FakeCustomer,
            FakeInvoiceNumberRange,
            FakeOrder,
            FakeOrderLine,
            setup_session,
            teardown_session,
        )

        customer = FakeCustomer()
        product_id = uuid.uuid4()
        line = FakeOrderLine(product_id=product_id)
        order = FakeOrder(customer_id=customer.id, lines=[line], customer=customer)

        session = FakeAsyncSession()
        session.queue_scalar(None)  # set_tenant
        session.queue_scalar(order)  # order lookup
        product_rows = [
            type(
                "Row",
                (),
                {
                    "id": line.product_id,
                    "code": "PROD-1",
                    "name": "Product 1",
                    "category": "Category 1",
                },
            )()
        ]
        session.queue_rows(product_rows)
        session.queue_scalar(customer)
        session.queue_scalar(customer)
        session.queue_scalar(FakeInvoiceNumberRange())
        session.queue_scalar(None)
        session.queue_scalar(uuid.uuid4())
        from tests.domains.orders._helpers import FakeInventoryStock
        session.queue_scalar(FakeInventoryStock(quantity=100))
        session.queue_scalar(None)
        session.queue_scalar(None)
        session.queue_scalar(order)

        prev = setup_session(session)
        try:
            await confirm_order(session, order.id, tenant_id=order.tenant_id)
        finally:
            teardown_session(prev)

        sales_reservation_adjustments = [
            o for o in session.added
            if isinstance(o, StockAdjustment) and o.reason_code == ReasonCode.SALES_RESERVATION
        ]
        assert len(sales_reservation_adjustments) == 1
        adj = sales_reservation_adjustments[0]
        # FakeOrderLine defaults to quantity=10
        assert adj.quantity_change == -10
