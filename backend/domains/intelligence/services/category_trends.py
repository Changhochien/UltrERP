"""Category trends service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from domains.intelligence.schemas import CategoryTrends

from .shared import load_category_trends


async def get_category_trends(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    period: Literal["last_30d", "last_90d", "last_12m"] = "last_90d",
) -> CategoryTrends:
    """Compute period-over-period category demand trends from the shared loader."""
    return CategoryTrends(
        period=period,
        trends=await load_category_trends(session, tenant_id, period=period),
        generated_at=datetime.now(tz=UTC),
    )
