"""Dashboard domain services — revenue and top-products queries."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.product import Product
from common.tenant import set_tenant
from domains.dashboard.schemas import (
    RevenueSummaryResponse,
    TopProductItem,
    TopProductsResponse,
)
from domains.invoices.models import Invoice

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
        end_ts = datetime(end_date.year, end_date.month, end_date.day, tzinfo=UTC) + timedelta(days=1)

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
