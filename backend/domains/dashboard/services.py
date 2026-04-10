"""Dashboard domain services — revenue and top-products queries."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from common.time import today as get_today
from decimal import Decimal
from typing import Literal

from sqlalchemy import cast, func, select, String
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
    GrossMarginResponse,
    KpiSummaryResponse,
    RevenueSummaryResponse,
    RevenueTrendItem,
    RevenueTrendResponse,
    RunningBalanceItem,
    TopCustomerItem,
    TopCustomersResponse,
    TopProductItem,
    TopProductsResponse,
)
from domains.invoices.models import Invoice, InvoiceLine
from domains.payments.models import Payment

_COUNTABLE_STATUSES = ("confirmed", "shipped", "fulfilled")


async def get_revenue_summary(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> RevenueSummaryResponse:
    """Return today vs yesterday invoiced revenue with percentage change."""
    async with session.begin():
        await set_tenant(session, tenant_id)

        today = get_today()
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
            target_date = get_today()
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
        # Use a payment subquery + outerjoin (not correlated subquery) to avoid
        # PostgreSQL grouping error: "subquery uses ungrouped column from outer query"
        payment_subq = (
            select(
                Payment.invoice_id,
                func.coalesce(func.sum(Payment.amount), 0).label("paid_amount"),
            )
            .where(Payment.tenant_id == tenant_id)
            .group_by(Payment.invoice_id)
            .subquery()
        )
        outstanding_expr = (
            func.coalesce(Invoice.total_amount, 0)
            - func.coalesce(payment_subq.c.paid_amount, 0)
        )
        open_invoice_stmt = (
            select(
                func.count(Invoice.id).label("count"),
                func.coalesce(func.sum(outstanding_expr), 0).label("outstanding"),
            )
            .select_from(Invoice)
            .outerjoin(payment_subq, Invoice.id == payment_subq.c.invoice_id)
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

        # --- Overdue receivables (issued invoices past computed due_date) ---
        # due_date = invoice_date + payment_terms_days (default 30 days from Order)
        order_terms_subq = (
            select(Order.payment_terms_days)
            .where(
                Order.id == Invoice.order_id,
                Order.tenant_id == tenant_id,
            )
            .correlate(Invoice)
            .scalar_subquery()
        )
        due_date_expr = Invoice.invoice_date + func.coalesce(order_terms_subq, 30)
        overdue_stmt = (
            select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.status == "issued",
                due_date_expr < today,
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

        today = get_today()
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
                cast(SupplierPayment.status, String) == "applied",
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
            start_date=start_date,
            end_date=end_date,
            cash_inflows=cash_inflows_list,
            cash_outflows=cash_outflows_list,
            net_cash_flow=net_cash_flow,
            running_balance_by_date=running_balance_list,
        )


async def get_gross_margin(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> GrossMarginResponse:
    """Return gross margin = revenue - COGS for the current month."""
    async with session.begin():
        await set_tenant(session, tenant_id)

        today = get_today()
        start_of_month = date(today.year, today.month, 1)

        # Revenue: sum of total_amount for non-voided invoices in current month
        revenue_stmt = (
            select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
                Invoice.invoice_date >= start_of_month,
                Invoice.invoice_date <= today,
                Invoice.status != "voided",
            )
        )
        revenue_result = await session.execute(revenue_stmt)
        revenue = Decimal(str(revenue_result.scalar() or "0"))

        # COGS: sum of unit_cost * quantity for invoice lines in the same invoices
        cogs_stmt = (
            select(
                func.coalesce(
                    func.sum(InvoiceLine.unit_cost * InvoiceLine.quantity),
                    0,
                )
            )
            .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
            .where(
                Invoice.invoice_date >= start_of_month,
                Invoice.invoice_date <= today,
                Invoice.status != "voided",
                InvoiceLine.unit_cost.isnot(None),
            )
        )
        cogs_result = await session.execute(cogs_stmt)
        cogs = Decimal(str(cogs_result.scalar() or "0"))

        gross_margin = revenue - cogs

        margin_percent: Decimal | None
        if revenue == 0:
            margin_percent = None
        else:
            margin_percent = (gross_margin / revenue * 100).quantize(Decimal("0.1"))

        return GrossMarginResponse(
            gross_margin=gross_margin,
            revenue=revenue,
            cogs=cogs,
            margin_percent=margin_percent,
        )


async def get_revenue_trend(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    granularity: Literal["day", "week", "month"] = "month",
    months: int = 12,
    days: int = 30,
    before: str | None = None,
) -> RevenueTrendResponse:
    """Return revenue trend with configurable granularity.

        - day:  daily revenue for the last `days` days. `before` pages backward by day.
        - week: weekly revenue (ISO week starting Monday) for the last `months` months.
            `before` pages backward by week.
        - month: monthly revenue — initial load = last `months` months from today.
            `before` pages backward by month.
    """
    async with session.begin():
        await set_tenant(session, tenant_id)

        today = get_today()

        if granularity == "day":
            if before:
                end_date = date.fromisoformat(before) - timedelta(days=1)
            else:
                end_date = today
            start_date = end_date - timedelta(days=days - 1)
            stmt = (
                select(
                    Invoice.invoice_date.label("date"),
                    func.coalesce(func.sum(Invoice.total_amount), 0).label("revenue"),
                    func.count(Invoice.id).label("order_count"),
                )
                .where(
                    Invoice.invoice_date >= start_date,
                    Invoice.invoice_date <= end_date,
                    Invoice.status != "voided",
                )
                .group_by(Invoice.invoice_date)
                .order_by(Invoice.invoice_date)
            )
        elif granularity == "week":
            # ISO week: Monday to Sunday, grouped by week start (Monday)
            if before:
                end_date = date.fromisoformat(before) - timedelta(days=1)
            else:
                end_date = today
            start_date = end_date - timedelta(weeks=months * 4)
            week_trunc = func.date_trunc("week", Invoice.invoice_date)
            stmt = (
                select(
                    week_trunc.label("date"),
                    func.coalesce(func.sum(Invoice.total_amount), 0).label("revenue"),
                    func.count(Invoice.id).label("order_count"),
                )
                .where(
                    Invoice.invoice_date >= start_date,
                    Invoice.invoice_date <= end_date,
                    Invoice.status != "voided",
                )
                .group_by(week_trunc)
                .order_by(week_trunc)
            )
        else:  # month
            # Initial load: last `months` months from current month (excl current).
            # Load More: `before` = oldest date in current results; get all earlier months.
            if before:
                # Get `months` months before the `before` date
                before_date = date.fromisoformat(before)
                end_date = date(before_date.year, before_date.month, 1)  # 1st of that month
                start_date = end_date - timedelta(days=1)
                start_date = date(start_date.year, start_date.month, 1)
                # Go back (months-1) more months
                for _ in range(months - 1):
                    start_date = start_date - timedelta(days=1)
                    start_date = date(start_date.year, start_date.month, 1)
            else:
                # Last `months` complete months before current month
                end_month = date(today.year, today.month, 1)
                start_date = end_month - timedelta(days=1)
                start_date = date(start_date.year, start_date.month, 1)
                # Go back (months-1) more months
                for _ in range(months - 1):
                    start_date = start_date - timedelta(days=1)
                    start_date = date(start_date.year, start_date.month, 1)
                end_date = date(today.year, today.month, 1)
            month_trunc = func.date_trunc("month", Invoice.invoice_date)
            stmt = (
                select(
                    month_trunc.label("date"),
                    func.coalesce(func.sum(Invoice.total_amount), 0).label("revenue"),
                    func.count(Invoice.id).label("order_count"),
                )
                .where(
                    Invoice.invoice_date >= start_date,
                    Invoice.invoice_date < end_date,
                    Invoice.status != "voided",
                )
                .group_by(month_trunc)
                .order_by(month_trunc)
            )

        result = await session.execute(stmt)
        rows = result.all()

        items = [
            RevenueTrendItem(
                date=row.date.date() if hasattr(row.date, "date") else row.date,
                revenue=Decimal(str(row.revenue or "0")),
                order_count=int(row.order_count or 0),
            )
            for row in rows
        ]

        # has_more: for month granularity, check if any data exists BEFORE oldest result
        has_more = False
        if items:
            oldest = items[0].date

            if granularity == "day":
                check_stmt = (
                    select(Invoice.invoice_date)
                    .where(
                        Invoice.invoice_date < oldest,
                        Invoice.invoice_date <= today,
                        Invoice.status != "voided",
                    )
                    .order_by(Invoice.invoice_date.desc())
                    .limit(1)
                )
            elif granularity == "week":
                week_expr = func.date_trunc("week", Invoice.invoice_date)
                check_stmt = (
                    select(week_expr)
                    .where(
                        week_expr < oldest,
                        Invoice.invoice_date <= today,
                        Invoice.status != "voided",
                    )
                    .group_by(week_expr)
                    .order_by(week_expr.desc())
                    .limit(1)
                )
            else:
                check_end = oldest - timedelta(days=1)
                check_end = date(check_end.year, check_end.month, 1)
                month_expr = func.date_trunc("month", Invoice.invoice_date)
                check_stmt = (
                    select(month_expr)
                    .where(
                        Invoice.invoice_date < check_end,
                        Invoice.invoice_date <= today,
                        Invoice.status != "voided",
                    )
                    .group_by(month_expr)
                    .order_by(month_expr.desc())
                    .limit(1)
                )

            prev_result = await session.execute(check_stmt)
            prev_row = prev_result.first()
            has_more = prev_row is not None

        # Response boundaries: start = oldest result, end = newest result (or current month for initial)
        if granularity == "month":
            resp_start = items[0].date if items else start_date
            resp_end = date(today.year, today.month, 1)
        else:
            resp_start = start_date
            resp_end = today

        return RevenueTrendResponse(
            items=items,
            start_date=resp_start,
            end_date=resp_end,
            has_more=has_more,
        )


async def get_top_customers(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    period: Literal["month", "quarter", "year"] = "month",
    limit: int = 10,
    anchor_date: date | None = None,
) -> TopCustomersResponse:
    """Return top customers by revenue for the given period."""
    from domains.customers.models import Customer

    async with session.begin():
        await set_tenant(session, tenant_id)

        reference_date = anchor_date or get_today()
        if period == "year":
            start_date = date(reference_date.year, 1, 1)
            end_date = date(reference_date.year, 12, 31)
        elif period == "quarter":
            quarter_month = ((reference_date.month - 1) // 3) * 3 + 1
            start_date = date(reference_date.year, quarter_month, 1)
            if quarter_month == 10:
                end_date = date(reference_date.year, 12, 31)
            else:
                end_date = date(reference_date.year, quarter_month + 3, 1) - timedelta(days=1)
        else:
            start_date = date(reference_date.year, reference_date.month, 1)
            end_date = (
                date(reference_date.year, reference_date.month + 1, 1) - timedelta(days=1)
                if reference_date.month < 12
                else date(reference_date.year, 12, 31)
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

        def row_value(row: object, attr: str, index: int) -> object:
            return getattr(row, attr) if hasattr(row, attr) else row[index]

        customers = [
            TopCustomerItem(
                customer_id=row_value(row, "customer_id", 0),
                company_name=row_value(row, "company_name", 1),
                total_revenue=row_value(row, "total_revenue", 2) or Decimal("0"),
                invoice_count=row_value(row, "invoice_count", 3),
                last_invoice_date=row_value(row, "last_invoice_date", 4),
            )
            for row in rows
        ]

        return TopCustomersResponse(
            period=period,
            start_date=start_date,
            end_date=end_date,
            customers=customers,
        )
