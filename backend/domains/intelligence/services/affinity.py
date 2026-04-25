"""Product affinity analysis service.

Extracts co-purchase patterns from qualifying orders to identify
products that are frequently bought together.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import Float, Numeric, String, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.order_reporting import commercially_committed_order_filter
from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.product import Product
from common.tenant import set_tenant

from domains.intelligence.schemas import AffinityPair, ProductAffinityMap

from .shared import PCT_QUANT, RATIO_QUANT, to_decimal, to_ratio


def _pair_key(product_a_id: uuid.UUID, product_b_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    """Generate canonical pair key for two product IDs (sorted by string representation)."""
    return (product_a_id, product_b_id) if str(product_a_id) < str(product_b_id) else (product_b_id, product_a_id)


def _make_pitch_hint(product_a_name: str, product_b_name: str, score: Decimal) -> str:
    """Generate a bundle or cross-sell pitch hint based on affinity score."""
    if score >= Decimal("0.5000"):
        return (
            f"Strong affinity — '{product_a_name}' and '{product_b_name}' are frequently bought together. "
            "Bundle pitch recommended."
        )
    if score >= Decimal("0.2000"):
        return f"Consider pitching '{product_b_name}' when customer buys '{product_a_name}'."
    return f"'{product_a_name}' customers occasionally also buy '{product_b_name}'."


async def get_product_affinity_map(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    min_shared: int = 2,
    limit: int = 50,
) -> ProductAffinityMap:
    """Compute customer-level product affinity pairs from qualifying orders.

    Identifies products that are frequently purchased together by the same customers,
    calculates affinity scores, and generates pitch hints for cross-sell opportunities.
    """
    if min_shared < 1 or limit < 1:
        raise ValueError(f"min_shared and limit must be >= 1, got min_shared={min_shared}, limit={limit}")
    normalized_limit = limit
    computed_at = datetime.now(tz=UTC)

    async with session.begin():
        await set_tenant(session, tenant_id)

        qualifying_rows = (
            select(
                Order.customer_id.label("customer_id"),
                Order.id.label("order_id"),
                Product.id.label("product_id"),
            )
            .join(OrderLine, OrderLine.order_id == Order.id)
            .join(Product, Product.id == OrderLine.product_id)
            .where(
                Order.tenant_id == tenant_id,
                Product.tenant_id == tenant_id,
                commercially_committed_order_filter(),
            )
            .distinct()
            .cte("qualifying_rows")
        )

        customer_counts = (
            select(
                qualifying_rows.c.product_id.label("product_id"),
                func.count(func.distinct(qualifying_rows.c.customer_id)).label("customer_count"),
            )
            .group_by(qualifying_rows.c.product_id)
            .cte("customer_counts")
        )

        customer_rows_a = qualifying_rows.alias("customer_rows_a")
        customer_rows_b = qualifying_rows.alias("customer_rows_b")
        pair_customer_counts = (
            select(
                customer_rows_a.c.product_id.label("product_a_id"),
                customer_rows_b.c.product_id.label("product_b_id"),
                func.count(func.distinct(customer_rows_a.c.customer_id)).label("shared_customer_count"),
            )
            .select_from(
                customer_rows_a.join(
                    customer_rows_b,
                    and_(
                        customer_rows_a.c.customer_id == customer_rows_b.c.customer_id,
                        cast(customer_rows_a.c.product_id, String) < cast(customer_rows_b.c.product_id, String),
                    ),
                )
            )
            .group_by(customer_rows_a.c.product_id, customer_rows_b.c.product_id)
            .having(func.count(func.distinct(customer_rows_a.c.customer_id)) >= min_shared)
            .cte("pair_customer_counts")
        )

        order_rows_a = qualifying_rows.alias("order_rows_a")
        order_rows_b = qualifying_rows.alias("order_rows_b")
        pair_order_counts = (
            select(
                order_rows_a.c.product_id.label("product_a_id"),
                order_rows_b.c.product_id.label("product_b_id"),
                func.count(func.distinct(order_rows_a.c.order_id)).label("shared_order_count"),
            )
            .select_from(
                order_rows_a.join(
                    order_rows_b,
                    and_(
                        order_rows_a.c.order_id == order_rows_b.c.order_id,
                        cast(order_rows_a.c.product_id, String) < cast(order_rows_b.c.product_id, String),
                    ),
                )
            )
            .group_by(order_rows_a.c.product_id, order_rows_b.c.product_id)
            .cte("pair_order_counts")
        )

        customer_count_a = customer_counts.alias("customer_count_a")
        customer_count_b = customer_counts.alias("customer_count_b")
        product_a = Product.__table__.alias("product_a")
        product_b = Product.__table__.alias("product_b")

        total_pairs = int(
            (
                await session.execute(
                    select(func.count()).select_from(pair_customer_counts)
                )
            ).scalar_one()
            or 0
        )

        if total_pairs <= 0:
            return ProductAffinityMap(
                pairs=[],
                total=0,
                min_shared=min_shared,
                limit=normalized_limit,
                computed_at=computed_at,
            )

        affinity_rank = cast(pair_customer_counts.c.shared_customer_count, Float) / func.nullif(
            cast(
                customer_count_a.c.customer_count
                + customer_count_b.c.customer_count
                - pair_customer_counts.c.shared_customer_count,
                Float,
            ),
            0.0,
        )
        rounded_affinity_rank = func.round(cast(affinity_rank, Numeric(18, 8)), 4)

        rows = (
            await session.execute(
                select(
                    pair_customer_counts.c.product_a_id,
                    pair_customer_counts.c.product_b_id,
                    product_a.c.name.label("product_a_name"),
                    product_b.c.name.label("product_b_name"),
                    pair_customer_counts.c.shared_customer_count,
                    customer_count_a.c.customer_count.label("customer_count_a"),
                    customer_count_b.c.customer_count.label("customer_count_b"),
                    pair_order_counts.c.shared_order_count,
                )
                .select_from(
                    pair_customer_counts
                    .join(customer_count_a, customer_count_a.c.product_id == pair_customer_counts.c.product_a_id)
                    .join(customer_count_b, customer_count_b.c.product_id == pair_customer_counts.c.product_b_id)
                    .join(product_a, product_a.c.id == pair_customer_counts.c.product_a_id)
                    .join(product_b, product_b.c.id == pair_customer_counts.c.product_b_id)
                    .outerjoin(
                        pair_order_counts,
                        and_(
                            pair_order_counts.c.product_a_id == pair_customer_counts.c.product_a_id,
                            pair_order_counts.c.product_b_id == pair_customer_counts.c.product_b_id,
                        ),
                    )
                )
                .order_by(
                    rounded_affinity_rank.desc(),
                    pair_customer_counts.c.shared_customer_count.desc(),
                    product_a.c.name.asc(),
                    product_b.c.name.asc(),
                )
                .limit(normalized_limit)
            )
        ).all()

    pairs: list[AffinityPair] = []
    for row in rows:
        shared_customer_count = int(row.shared_customer_count or 0)
        customer_count_a_value = int(row.customer_count_a or 0)
        customer_count_b_value = int(row.customer_count_b or 0)
        min_customer_count = min(customer_count_a_value, customer_count_b_value)
        union_count_value = customer_count_a_value + customer_count_b_value - shared_customer_count
        if min_customer_count <= 0 or union_count_value <= 0:
            continue

        overlap_pct = (
            Decimal(shared_customer_count) * Decimal("100") / Decimal(min_customer_count)
        ).quantize(PCT_QUANT)
        affinity_score = (
            Decimal(shared_customer_count) / Decimal(union_count_value)
        ).quantize(RATIO_QUANT, rounding=ROUND_HALF_UP)

        pairs.append(
            AffinityPair(
                product_a_id=row.product_a_id,
                product_b_id=row.product_b_id,
                product_a_name=row.product_a_name,
                product_b_name=row.product_b_name,
                shared_customer_count=shared_customer_count,
                customer_count_a=customer_count_a_value,
                customer_count_b=customer_count_b_value,
                shared_order_count=(
                    int(row.shared_order_count)
                    if row.shared_order_count is not None
                    else None
                ),
                overlap_pct=to_ratio(overlap_pct, quant=PCT_QUANT),
                affinity_score=to_ratio(affinity_score),
                pitch_hint=_make_pitch_hint(row.product_a_name, row.product_b_name, affinity_score),
            )
        )

    return ProductAffinityMap(
        pairs=pairs,
        total=total_pairs,
        min_shared=min_shared,
        limit=normalized_limit,
        computed_at=computed_at,
    )
