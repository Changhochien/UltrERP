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


def test_run_repair_missing_serializes_dates_and_reports_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_months = [date(2026, 1, 1), date(2026, 3, 1)]

    async def fake_repair_missing_sales_monthly_months(
        session,
        tenant_id: uuid.UUID,
        missing_months: list[date],
    ) -> SalesMonthlyRangeRefreshResult:
        assert tenant_id == TENANT_ID
        assert missing_months == requested_months
        return _range_result(*requested_months)

    monkeypatch.setattr(
        refresh,
        "repair_missing_sales_monthly_months",
        fake_repair_missing_sales_monthly_months,
    )

    result = asyncio.run(
        refresh.run_repair_missing(
            tenant_id=TENANT_ID,
            missing_months=requested_months,
        )
    )

    assert result.repaired_months == ("2026-01-01", "2026-03-01")
    assert result.refreshed_month_count == 2
    assert result.idempotent is True


def test_main_refresh_defaults_affected_domains_to_none(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_refresh_closed_sales_monthly_history(**kwargs):
        assert kwargs["tenant_id"] == TENANT_ID
        assert kwargs["affected_domains"] is None
        return refresh.SalesMonthlyHistoryRefreshResult(
            batch_mode="full",
            affected_domains=(),
            start_month=date(2026, 1, 1),
            end_month=date(2026, 3, 1),
            refreshed_month_count=3,
            total_upserted_row_count=3,
            total_deleted_row_count=0,
            skipped_line_count=0,
            cleared_row_count=0,
        )

    monkeypatch.setattr(
        refresh,
        "refresh_closed_sales_monthly_history",
        fake_refresh_closed_sales_monthly_history,
    )

    exit_code = refresh.main([
        "--tenant-id",
        str(TENANT_ID),
        "refresh",
    ])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert '"refreshed_month_count": 3' in output