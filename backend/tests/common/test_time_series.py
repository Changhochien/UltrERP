"""Tests for common.time_series dense time-series utilities."""

from __future__ import annotations

from datetime import date

import pytest

from common.time_series import (
    MAX_DAILY_POINTS,
    MAX_MONTHLY_POINTS,
    check_range_limits,
    densify_daily_series,
    densify_monthly_series,
)


class TestDensifyMonthlySeries:
    """Tests for monthly series densification."""

    def test_returns_empty_when_no_data(self):
        """No source data should return zero-filled series."""
        start = date(2025, 1, 1)
        end = date(2025, 3, 1)
        points, meta = densify_monthly_series(
            source_data={},
            requested_start=start,
            requested_end=end,
            current_date=date(2025, 4, 15),
        )

        assert len(points) == 3
        assert all(p["is_zero_filled"] for p in points)
        assert all(p["value"] == 0 for p in points)
        assert all(p["source"] == "zero-filled" for p in points)
        assert meta["bucket"] == "month"
        assert meta["timezone"] == "Asia/Taipei"

    def test_fills_gaps_in_data(self):
        """Gaps in source data should be zero-filled."""
        start = date(2025, 1, 1)
        end = date(2025, 4, 1)
        source_data = {
            "2025-01": 100.0,
            # 2025-02 is missing
            "2025-03": 200.0,
            "2025-04": 150.0,
        }
        points, _ = densify_monthly_series(
            source_data=source_data,
            requested_start=start,
            requested_end=end,
            current_date=date(2025, 5, 1),
        )

        assert len(points) == 4
        assert points[0]["value"] == 100.0
        assert points[0]["is_zero_filled"] is False
        assert points[1]["is_zero_filled"] is True
        assert points[1]["value"] == 0.0
        assert points[2]["value"] == 200.0

    def test_marks_partial_current_month(self):
        """Current month should be marked as partial."""
        start = date(2025, 1, 1)
        end = date(2025, 3, 1)
        current_date = date(2025, 2, 15)  # We're in February

        points, _ = densify_monthly_series(
            source_data={"2025-01": 100.0},
            requested_start=start,
            requested_end=end,
            current_date=current_date,
        )

        # February should be partial (current month)
        feb_point = next(p for p in points if p["bucket_start"] == "2025-02")
        assert feb_point["period_status"] == "partial"
        assert feb_point["source"] == "zero-filled"

        # January should be closed
        jan_point = next(p for p in points if p["bucket_start"] == "2025-01")
        assert jan_point["period_status"] == "closed"

    def test_tracks_available_range(self):
        """Available range should track actual data bounds."""
        start = date(2025, 1, 1)
        end = date(2025, 12, 1)
        source_data = {
            "2025-03": 100.0,
            "2025-09": 200.0,
        }

        _, meta = densify_monthly_series(
            source_data=source_data,
            requested_start=start,
            requested_end=end,
        )

        assert meta["available_start"] == "2025-03"
        assert meta["available_end"] == "2025-09"

    def test_source_provenance(self):
        """Source should indicate data origin."""
        start = date(2025, 1, 1)
        end = date(2025, 2, 1)
        current_date = date(2025, 2, 15)

        points, _ = densify_monthly_series(
            source_data={"2025-01": 100.0},
            requested_start=start,
            requested_end=end,
            current_date=current_date,
        )

        jan = next(p for p in points if p["bucket_start"] == "2025-01")
        assert jan["source"] == "aggregate"

        feb = next(p for p in points if p["bucket_start"] == "2025-02")
        assert feb["source"] == "zero-filled"


class TestDensifyDailySeries:
    """Tests for daily series densification."""

    def test_returns_empty_when_no_data(self):
        """No source data should return zero-filled series."""
        start = date(2025, 1, 1)
        end = date(2025, 1, 5)
        points, meta = densify_daily_series(
            source_data={},
            requested_start=start,
            requested_end=end,
            current_date=date(2025, 1, 10),
        )

        assert len(points) == 5
        assert all(p["is_zero_filled"] for p in points)
        assert meta["bucket"] == "day"

    def test_fills_gaps_in_data(self):
        """Gaps in daily data should be zero-filled."""
        start = date(2025, 1, 1)
        end = date(2025, 1, 5)
        source_data = {
            "2025-01-01": 100.0,
            "2025-01-03": 200.0,
            "2025-01-05": 150.0,
        }

        points, _ = densify_daily_series(
            source_data=source_data,
            requested_start=start,
            requested_end=end,
        )

        assert len(points) == 5
        # Day 2 should be zero-filled
        assert points[1]["is_zero_filled"] is True


class TestRangeLimits:
    """Tests for v1 range limit checking."""

    def test_monthly_within_limit(self):
        """Request within monthly limit should pass."""
        start = date(2020, 1, 1)
        end = date(2025, 1, 1)  # 61 months

        within, msg = check_range_limits(start, end, "month")
        assert within is True
        assert msg is None

    def test_monthly_exceeds_limit(self):
        """Request exceeding monthly limit should fail."""
        start = date(2010, 1, 1)
        end = date(2025, 1, 1)  # 181 months

        within, msg = check_range_limits(start, end, "month")
        assert within is False
        assert "exceeds v1 limit" in msg

    def test_daily_within_limit(self):
        """Request within daily limit should pass."""
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)  # 365 days

        within, msg = check_range_limits(start, end, "day")
        assert within is True
        assert msg is None

    def test_daily_exceeds_limit(self):
        """Request exceeding daily limit should fail."""
        start = date(2022, 1, 1)
        end = date(2025, 1, 1)  # 1096 days

        within, msg = check_range_limits(start, end, "day")
        assert within is False
        assert "exceeds v1 limit" in msg


class TestConstants:
    """Tests for module constants."""

    def test_max_monthly_points(self):
        """MAX_MONTHLY_POINTS should be 120."""
        assert MAX_MONTHLY_POINTS == 120

    def test_max_daily_points(self):
        """MAX_DAILY_POINTS should be 730."""
        assert MAX_DAILY_POINTS == 730
