"""Dashboard domain services — revenue and top-products queries."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.inventory_stock import InventoryStock
from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.product import Product
from common.models.supplier_payment import SupplierPayment, SupplierPaymentStatus
from common.tenant import set_tenant
from domains.dashboard.schemas import (
    CashFlowItem,
    CashFlowResponse,
    KpiSummaryResponse,
    RevenueSummaryResponse,
    RunningBalanceItem,
    TopCustomerItem,
    TopCustomersResponse,
    TopProductItem,
    TopProductsResponse,
)
from domains.invoices.models import Invoice
from domains.payments.models import Payment

_COUNTABLE_STATUSES = ("confirmed", "shipped", "fulfilled")


async def get_revenue_summary(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> RevenueSummaryResponse:
    """Return today vs yesterday invoiced revenue with percentage change."""
    async with session.begin():
        await set_tenant(session, tenant_id)

        today = datetime.now(UTC).date()
        yesterday = today - timedelta(days=1)

        today_revenue = await _sum_revenue_for_date(session, today)
        yesterday_revenue = await _sum_revenue_for_date(session, yesterday)

        change_percent: Decimal | None
        if yesterday_revenue == 0 and today_revenue == 0:
            change_percent = None
        elif yesterday_revenue == 0:
            change_percent = Decimal("100.0")
        else:
            change_percent = (
                (today_revenue - yesterday_revenue) / yesterday_revenue * 100
            ).quantize(Decimal("0.1"))

        return RevenueSummaryResponse(
            today_revenue=today_revenue,
            yesterday_revenue=yesterday_revenue,
            change_percent=change_percent,
            today_date=today,
            yesterday_date=yesterday,
        )


async def _sum_revenue_for_date(
    session: AsyncSession,
    target_date: date,
) -> Decimal:
    """Sum total_amount of non-voided invoices for a given date."""
    stmt = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
        Invoice.invoice_date == target_date,
        Invoice.status != "voided",
    )
    result = await session.execute(stmt)
    return Decimal(str(result.scalar()))


async def get_kpi_summary(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date | None = None,
) -> KpiSummaryResponse:
    """Return all primary KPIs for the dashboard: revenue, invoices, orders, stock, receivables."""
    async with session.begin():
        await set_tenant(session, tenant_id)

        if target_date is None:
            target_date = datetime.now(UTC).date()
        today = target_date
        yesterday = today - timedelta(days=1)

        # --- Revenue ---
        today_revenue = await _sum_revenue_for_date(session, today)
        yesterday_revenue = await _sum_revenue_for_date(session, yesterday)

        revenue_change_pct: Decimal | None
        if yesterday_revenue == 0:
            revenue_change_pct = None
        else:
            revenue_change_pct = (
                (today_revenue - yesterday_revenue) / yesterday_revenue * 100
            ).quantize(Decimal("0.1"))

        # --- Open invoices (status='issued', not fully paid via payments) ---
        # outstanding = total_amount - coalesce(sum(payments), 0)
        open_invoice_stmt = (
            select(
                func.count(Invoice.id).label("count"),
                func.coalesce(func.sum(Invoice.total_amount), 0)
                - func.coalesce(
                    select(func.coalesce(func.sum(Payment.amount), 0))
                    .where(Payment.invoice_id == Invoice.id)
                    .scalar_subquery(),
                    0,
                ).label("outstanding"),
            )
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status == "issued",
            )
        )
        open_result = await session.execute(open_invoice_stmt)
        open_row = open_result.one()
        open_invoice_count = open_row.count or 0
        open_invoice_amount = Decimal(str(open_row.outstanding or 0))

        # --- Pending orders (status in pending/confirmed) ---
        pending_order_stmt = (
            select(
                func.count(Order.id).label("count"),
                func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            )
            .where(
                Order.tenant_id == tenant_id,
                Order.status.in_(("pending", "confirmed")),
            )
        )
        pending_result = await session.execute(pending_order_stmt)
        pending_row = pending_result.one()
        pending_order_count = pending_row.count or 0
        pending_order_revenue = Decimal(str(pending_row.revenue or 0))

        # --- Low stock products (quantity < reorder_point) ---
        low_stock_stmt = (
            select(func.count(InventoryStock.id)).where(
                InventoryStock.tenant_id == tenant_id,
                InventoryStock.quantity < InventoryStock.reorder_point,
            )
        )
        low_stock_result = await session.execute(low_stock_stmt)
        low_stock_product_count = low_stock_result.scalar() or 0

        # --- Overdue receivables (issued invoices with due_date < today) ---
        overdue_stmt = (
            select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.status == "issued",
                Invoice.due_date < today,
            )
        )
        overdue_result = await session.execute(overdue_stmt)
        overdue_receivables_amount = Decimal(str(overdue_result.scalar() or 0))

        return KpiSummaryResponse(
            today_revenue=today_revenue,
            yesterday_revenue=yesterday_revenue,
            revenue_change_pct=revenue_change_pct,
            open_invoice_count=open_invoice_count,
            open_invoice_amount=open_invoice_amount,
            pending_order_count=pending_order_count,
            pending_order_revenue=pending_order_revenue,
            low_stock_product_count=low_stock_product_count,
            overdue_receivables_amount=overdue_receivables_amount,
        )





async def get_top_products(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    period: Literal["day", "week"] = "day",
) -> TopProductsResponse:
    """Return top 3 products by quantity sold for the given period."""
    async with session.begin():
        await set_tenant(session, tenant_id)

        today = datetime.now(UTC).date()
        if period == "week":
            start_date = today - timedelta(days=6)
        else:
            start_date = today
        end_date = today

        # Range-based filter for index friendliness on ix_orders_tenant_created
        start_ts = datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
        end_ts = datetime(end_date.year, end_date.month, end_date.day, tzinfo=UTC) + timedelta(
            days=1
        )

        qty_sold = func.sum(OrderLine.quantity).label("quantity_sold")
        revenue = func.sum(OrderLine.total_amount).label("revenue")

        stmt = (
            select(
                Product.id,
                Product.name,
                qty_sold,
                revenue,
            )
            .join(OrderLine, OrderLine.product_id == Product.id)
            .join(Order, Order.id == OrderLine.order_id)
            .where(
                Order.status.in_(_COUNTABLE_STATUSES),
                Order.created_at >= start_ts,
                Order.created_at < end_ts,
            )
            .group_by(Product.id, Product.name)
            .order_by(qty_sold.desc())
            .limit(3)
        )

        result = await session.execute(stmt)
        rows = result.all()

        items = [
            TopProductItem(
                product_id=row[0],
                product_name=row[1],
                quantity_sold=row[2],
                revenue=row[3],
            )
            for row in rows
        ]

        return TopProductsResponse(
            period=period,
            start_date=start_date,
            end_date=end_date,
            items=items,
        )


async def get_cash_flow(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> CashFlowResponse:
    """Return cash inflows, outflows, and running balance for a date range."""
    async with session.begin():
        await set_tenant(session, tenant_id)

        # Cash inflows: matched Payments grouped by payment_date
        inflow_stmt = (
            select(
                Payment.payment_date.label("date"),
                func.coalesce(func.sum(Payment.amount), Decimal("0")).label("amount"),
            )
            .where(
                Payment.tenant_id == tenant_id,
                Payment.payment_date >= start_date,
                Payment.payment_date <= end_date,
                Payment.match_status.in_(("matched", "auto_matched")),
            )
            .group_by(Payment.payment_date)
            .order_by(Payment.payment_date)
        )
        inflow_result = await session.execute(inflow_stmt)
        inflow_rows = inflow_result.all()

        # Cash outflows: applied SupplierPayments grouped by payment_date
        outflow_stmt = (
            select(
                SupplierPayment.payment_date.label("date"),
                func.coalesce(func.sum(SupplierPayment.gross_amount), Decimal("0")).label("amount"),
            )
            .where(
                SupplierPayment.tenant_id == tenant_id,
                SupplierPayment.payment_date >= start_date,
                SupplierPayment.payment_date <= end_date,
                SupplierPayment.status == SupplierPaymentStatus.APPLIED,
            )
            .group_by(SupplierPayment.payment_date)
            .order_by(SupplierPayment.payment_date)
        )
        outflow_result = await session.execute(outflow_stmt)
        outflow_rows = outflow_result.all()

        # Build lookup dicts
        inflow_by_date = {row.date: row.amount for row in inflow_rows}
        outflow_by_date = {row.date: row.amount for row in outflow_rows}

        # Build complete date range, forward-filling missing days
        current_date = start_date
        running_balance = Decimal("0")
        cash_inflows_list: list[CashFlowItem] = []
        cash_outflows_list: list[CashFlowItem] = []
        running_balance_list: list[RunningBalanceItem] = []

        while current_date <= end_date:
            inflow_amt = inflow_by_date.get(current_date, Decimal("0"))
            outflow_amt = outflow_by_date.get(current_date, Decimal("0"))
            daily_net = inflow_amt - outflow_amt

            if inflow_amt > 0:
                cash_inflows_list.append(CashFlowItem(date=current_date, amount=inflow_amt))
            if outflow_amt > 0:
                cash_outflows_list.append(CashFlowItem(date=current_date, amount=outflow_amt))

            running_balance += daily_net
            running_balance_list.append(
                RunningBalanceItem(date=current_date, cumulative_balance=running_balance)
            )

            current_date += timedelta(days=1)

        net_cash_flow = sum(item.amount for item in cash_inflows_list) - sum(
            item.amount for item in cash_outflows_list
        )

        return CashFlowResponse(
            period_start=start_date,
            period_end=end_date,
            cash_inflows=cash_inflows_list,
            cash_outflows=cash_outflows_list,
            net_cash_flow=net_cash_flow,
            running_balance_by_date=running_balance_list,
        )


async def get_top_customers(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    period: Literal["month", "quarter", "year"] = "month",
    limit: int = 10,
) -> TopCustomersResponse:
    """Return top customers by revenue for the given period."""
    from domains.customers.models import Customer

    async with session.begin():
        await set_tenant(session, tenant_id)

        today = datetime.now(UTC).date()
        if period == "year":
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
        elif period == "quarter":
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start_date = date(today.year, quarter_month, 1)
            if quarter_month == 10:
                end_date = date(today.year, 12, 31)
            else:
                end_date = date(today.year, quarter_month + 3, 1) - timedelta(days=1)
        else:
            start_date = date(today.year, today.month, 1)
            end_date = (
                date(today.year, today.month + 1, 1) - timedelta(days=1)
                if today.month < 12
                else date(today.year, 12, 31)
            )

        total_revenue = func.sum(Invoice.total_amount).label("total_revenue")
        invoice_count = func.count(Invoice.id).label("invoice_count")
        last_invoice_date = func.max(Invoice.invoice_date).label("last_invoice_date")

        stmt = (
            select(
                Customer.id.label("customer_id"),
                Customer.company_name,
                total_revenue,
                invoice_count,
                last_invoice_date,
            )
            .join(Invoice, Invoice.customer_id == Customer.id)
            .where(
                Invoice.invoice_date >= start_date,
                Invoice.invoice_date <= end_date,
                Invoice.status.in_(("paid", "issued")),
            )
            .group_by(Customer.id, Customer.company_name)
            .order_by(total_revenue.desc())
            .limit(limit)
        )

        result = await session.execute(stmt)
        rows = result.all()

        customers = [
            TopCustomerItem(
                customer_id=row.customer_id,
                company_name=row.company_name,
                total_revenue=row.total_revenue or Decimal("0"),
                invoice_count=row.invoice_count,
                last_invoice_date=row.last_invoice_date,
            )
            for row in rows
        ]

        return TopCustomersResponse(
            period=period,
            start_date=start_date,
            end_date=end_date,
            customers=customers,
        )
