from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime

import pytest

from domains.product_analytics.service import (
    SalesMonthlyRangeRefreshResult,
    SalesMonthlyRefreshResult,
)
from scripts import refresh_sales_monthly as refresh
from scripts.legacy_refresh_common import RefreshBatchMode

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _range_result(*months: date) -> SalesMonthlyRangeRefreshResult:
    return SalesMonthlyRangeRefreshResult(
        results=tuple(
            SalesMonthlyRefreshResult(
                month_start=month_start,
                upserted_row_count=1,
                deleted_row_count=0,
                skipped_lines=(),
            )
            for month_start in months
        ),
        refreshed_month_count=len(months),
    )


def test_refresh_closed_sales_monthly_history_uses_rolling_window_for_incremental_upkeep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_fetch_earliest_order_timestamp(tenant_id: uuid.UUID):
        assert tenant_id == TENANT_ID
        return datetime(2024, 1, 15, tzinfo=UTC)

    async def fake_refresh_sales_monthly_window(
        tenant_id: uuid.UUID,
        *,
        start_month: date,
        end_month: date,
    ) -> SalesMonthlyRangeRefreshResult:
        captured["tenant_id"] = tenant_id
        captured["start_month"] = start_month
        captured["end_month"] = end_month
        return _range_result(date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1))

    monkeypatch.setattr(refresh, "_current_month_start", lambda: date(2026, 4, 1))
    monkeypatch.setattr(
        refresh,
        "_fetch_earliest_order_timestamp",
        fake_fetch_earliest_order_timestamp,
    )
    monkeypatch.setattr(
        refresh,
        "_refresh_sales_monthly_window",
        fake_refresh_sales_monthly_window,
    )

    result = asyncio.run(
        refresh.refresh_closed_sales_monthly_history(
            tenant_id=TENANT_ID,
            batch_mode=RefreshBatchMode.INCREMENTAL,
            affected_domains=("products",),
            rolling_closed_months=3,
        )
    )

    assert captured == {
        "tenant_id": TENANT_ID,
        "start_month": date(2026, 1, 1),
        "end_month": date(2026, 3, 1),
    }
    assert result.start_month == date(2026, 1, 1)
    assert result.end_month == date(2026, 3, 1)
    assert result.refreshed_month_count == 3
    assert result.skipped_reason is None


def test_refresh_closed_sales_monthly_history_rejects_invalid_rolling_window() -> None:
    with pytest.raises(ValueError, match="rolling_closed_months must be at least 1"):
        asyncio.run(
            refresh.refresh_closed_sales_monthly_history(
                tenant_id=TENANT_ID,
                batch_mode=RefreshBatchMode.INCREMENTAL,
                rolling_closed_months=0,
            )
        )