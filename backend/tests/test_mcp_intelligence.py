"""Tests for intelligence MCP tools."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastmcp.exceptions import ToolError

import domains.intelligence.mcp as intelligence_mcp
from domains.intelligence.mcp import (
    intelligence_category_trends,
    intelligence_customer_product_profile,
    intelligence_customer_risk_signals,
    intelligence_market_opportunities,
    intelligence_prospect_gaps,
    intelligence_product_affinity,
    intelligence_product_performance,
    intelligence_revenue_diagnosis,
)
from common.config import settings
from domains.intelligence.schemas import (
    CategoryTrends,
    CustomerProductProfile,
    CustomerRiskSignals,
    MarketOpportunities,
    ProspectGaps,
    ProductAffinityMap,
    ProductPerformance,
    ProductPerformancePeriodMetrics,
    ProductPerformanceRow,
    ProductPerformanceWindow,
    RevenueDiagnosis,
    RevenueDiagnosisComponents,
    RevenueDiagnosisDriver,
    RevenueDiagnosisSummary,
    RevenueDiagnosisWindow,
)

_profile_fn = getattr(intelligence_customer_product_profile, "fn", intelligence_customer_product_profile)
_affinity_fn = getattr(intelligence_product_affinity, "fn", intelligence_product_affinity)
_product_performance_fn = getattr(intelligence_product_performance, "fn", intelligence_product_performance)
_category_trends_fn = getattr(intelligence_category_trends, "fn", intelligence_category_trends)
_risk_signals_fn = getattr(intelligence_customer_risk_signals, "fn", intelligence_customer_risk_signals)
_market_opportunities_fn = getattr(intelligence_market_opportunities, "fn", intelligence_market_opportunities)
_prospect_gaps_fn = getattr(intelligence_prospect_gaps, "fn", intelligence_prospect_gaps)
_revenue_diagnosis_fn = getattr(intelligence_revenue_diagnosis, "fn", intelligence_revenue_diagnosis)


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _patch_session():
    return patch("domains.intelligence.mcp.AsyncSessionLocal", return_value=FakeSession())


def _tenant_headers(tenant_id: str = "00000000-0000-0000-0000-000000000001") -> dict[str, str]:
    return {"x-tenant-id": tenant_id}


def _tenant_bearer_token(tenant_id: str = "00000000-0000-0000-0000-000000000001") -> str:
    return jwt.encode(
        {
            "sub": "test-user-id",
            "tenant_id": tenant_id,
            "role": "owner",
            "exp": datetime.now(tz=UTC).timestamp() + 3600,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def _sample_profile(customer_id: uuid.UUID) -> CustomerProductProfile:
    return CustomerProductProfile(
        customer_id=customer_id,
        company_name="Acme Trading",
        total_revenue_12m=Decimal("570.00"),
        order_count_12m=3,
        order_count_3m=2,
        order_count_6m=3,
        order_count_prior_12m=1,
        order_count_prior_3m=1,
        frequency_trend="increasing",
        avg_order_value=Decimal("190.00"),
        avg_order_value_prior=Decimal("90.00"),
        aov_trend="increasing",
        top_categories=[],
        top_products=[],
        last_order_date=None,
        days_since_last_order=None,
        is_dormant=False,
        new_categories=[],
        confidence="medium",
        activity_basis="confirmed_or_later_orders",
    )


def _sample_affinity_map() -> ProductAffinityMap:
    return ProductAffinityMap(
        pairs=[],
        total=0,
        min_shared=2,
        limit=50,
        computed_at=datetime.now(tz=UTC),
    )


def _sample_category_trends(period: str = "last_90d") -> CategoryTrends:
    return CategoryTrends(
        period=period,  # type: ignore[arg-type]
        trends=[],
        generated_at=datetime.now(tz=UTC),
    )


def _sample_customer_risk_signals(status_filter: str = "all") -> CustomerRiskSignals:
    return CustomerRiskSignals(
        customers=[],
        total=0,
        status_filter=status_filter,  # type: ignore[arg-type]
        limit=50,
        generated_at=datetime.now(tz=UTC),
    )


def _sample_prospect_gaps(category: str = "Electronics") -> ProspectGaps:
    return ProspectGaps(
        target_category=category,
        target_category_revenue=Decimal("500.00"),
        existing_buyers_count=2,
        prospects_count=0,
        prospects=[],
        available_categories=["Electronics", "Supplies"],
        generated_at=datetime.now(tz=UTC),
    )


def _sample_market_opportunities(period: str = "last_90d") -> MarketOpportunities:
    return MarketOpportunities(
        period=period,  # type: ignore[arg-type]
        generated_at=datetime.now(tz=UTC),
        signals=[],
        deferred_signal_types=["new_product_adoption", "churn_risk"],
    )


def _sample_revenue_diagnosis(anchor_month: str = "2026-03-01") -> RevenueDiagnosis:
    anchor = date.fromisoformat(anchor_month)
    prior = date(2026, 2, 1)
    return RevenueDiagnosis(
        period="1m",
        anchor_month=anchor,
        current_window=RevenueDiagnosisWindow(start_month=anchor, end_month=anchor),
        prior_window=RevenueDiagnosisWindow(start_month=prior, end_month=prior),
        computed_at=datetime.now(tz=UTC),
        summary=RevenueDiagnosisSummary(
            current_revenue=Decimal("120.00"),
            prior_revenue=Decimal("100.00"),
            revenue_delta=Decimal("20.00"),
            revenue_delta_pct=20.0,
        ),
        components=RevenueDiagnosisComponents(
            price_effect_total=Decimal("12.00"),
            volume_effect_total=Decimal("5.00"),
            mix_effect_total=Decimal("3.00"),
        ),
        drivers=[
            RevenueDiagnosisDriver(
                product_id=uuid.UUID("00000000-0000-0000-0000-000000000123"),
                product_name="Alpha Belt",
                product_category_snapshot="Belts",
                current_quantity=Decimal("10.000"),
                prior_quantity=Decimal("8.000"),
                current_revenue=Decimal("120.00"),
                prior_revenue=Decimal("100.00"),
                current_order_count=2,
                prior_order_count=2,
                current_avg_unit_price=Decimal("12.00"),
                prior_avg_unit_price=Decimal("12.50"),
                price_effect=Decimal("12.00"),
                volume_effect=Decimal("5.00"),
                mix_effect=Decimal("3.00"),
                revenue_delta=Decimal("20.00"),
                revenue_delta_pct=20.0,
                data_basis="aggregate_only",
                window_is_partial=False,
            )
        ],
        data_basis="aggregate_only",
        window_is_partial=False,
    )


def _sample_product_performance() -> ProductPerformance:
    return ProductPerformance(
        current_window=ProductPerformanceWindow(start_month=date(2026, 3, 1), end_month=date(2026, 5, 1)),
        prior_window=ProductPerformanceWindow(start_month=date(2025, 12, 1), end_month=date(2026, 2, 1)),
        computed_at=datetime.now(tz=UTC),
        products=[
            ProductPerformanceRow(
                product_id=uuid.UUID("00000000-0000-0000-0000-000000000321"),
                product_name="Growth Belt",
                product_category_snapshot="Belts",
                lifecycle_stage="growing",
                stage_reasons=["Current-period revenue is materially above the prior comparison window."],
                first_sale_month=date(2024, 1, 1),
                last_sale_month=date(2026, 5, 1),
                months_on_sale=29,
                current_period=ProductPerformancePeriodMetrics(
                    revenue=Decimal("450.00"),
                    quantity=Decimal("30.000"),
                    order_count=8,
                    avg_unit_price=Decimal("15.00"),
                ),
                prior_period=ProductPerformancePeriodMetrics(
                    revenue=Decimal("220.00"),
                    quantity=Decimal("16.000"),
                    order_count=5,
                    avg_unit_price=Decimal("13.75"),
                ),
                peak_month_revenue=Decimal("190.00"),
                revenue_delta_pct=104.5455,
                data_basis="aggregate_plus_live_current_month",
                window_is_partial=True,
            )
        ],
        total=1,
        data_basis="aggregate_plus_live_current_month",
        window_is_partial=True,
    )


@pytest.mark.asyncio
async def test_market_opportunities_tool_returns_payload() -> None:
    with (
        _patch_session(),
        patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()),
        patch(
            "domains.intelligence.mcp.get_market_opportunities",
            new_callable=AsyncMock,
            return_value=_sample_market_opportunities("last_30d"),
        ) as opportunities_mock,
    ):
        result = await _market_opportunities_fn(period="last_30d")

    assert result["period"] == "last_30d"
    assert result["deferred_signal_types"] == ["new_product_adoption", "churn_risk"]
    assert opportunities_mock.await_args.kwargs == {"period": "last_30d"}


@pytest.mark.asyncio
async def test_market_opportunities_tool_validates_period() -> None:
    with patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()):
        with pytest.raises(ToolError) as exc_info:
            await _market_opportunities_fn(period="qtd")

    error = json.loads(str(exc_info.value))
    assert error["code"] == "VALIDATION_ERROR"
    assert error["field"] == "period"


@pytest.mark.asyncio
async def test_revenue_diagnosis_tool_returns_payload() -> None:
    with (
        _patch_session(),
        patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()),
        patch(
            "domains.intelligence.mcp.get_revenue_diagnosis",
            new_callable=AsyncMock,
            return_value=_sample_revenue_diagnosis(),
        ) as diagnosis_mock,
    ):
        result = await _revenue_diagnosis_fn(
            period="1m",
            anchor_month="2026-03-01",
            category="Belts",
            limit=5,
        )

    assert result["summary"]["revenue_delta"] == "20.00"
    assert diagnosis_mock.await_args.args[1] == uuid.UUID("00000000-0000-0000-0000-000000000001")
    assert diagnosis_mock.await_args.kwargs == {
        "period": "1m",
        "anchor_month": date(2026, 3, 1),
        "category": "Belts",
        "limit": 5,
    }


@pytest.mark.asyncio
async def test_product_performance_tool_returns_payload() -> None:
    with (
        _patch_session(),
        patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()),
        patch(
            "domains.intelligence.mcp.get_product_performance",
            new_callable=AsyncMock,
            return_value=_sample_product_performance(),
        ) as performance_mock,
    ):
        result = await _product_performance_fn(
            category="Belts",
            lifecycle_stage="growing",
            limit=25,
            include_current_month=True,
        )

    assert result["products"][0]["lifecycle_stage"] == "growing"
    assert performance_mock.await_args.args[1] == uuid.UUID("00000000-0000-0000-0000-000000000001")
    assert performance_mock.await_args.kwargs == {
        "category": "Belts",
        "lifecycle_stage": "growing",
        "limit": 25,
        "include_current_month": True,
    }


@pytest.mark.asyncio
async def test_prospect_gaps_tool_returns_payload() -> None:
    with (
        _patch_session(),
        patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()),
        patch(
            "domains.intelligence.mcp.get_prospect_gaps",
            new_callable=AsyncMock,
            return_value=_sample_prospect_gaps("Electronics"),
        ) as gaps_mock,
    ):
        result = await _prospect_gaps_fn(category="Electronics", customer_type="end_user", limit=20)

    assert result["target_category"] == "Electronics"
    assert result["existing_buyers_count"] == 2
    assert gaps_mock.await_args.args[1] == uuid.UUID("00000000-0000-0000-0000-000000000001")
    assert gaps_mock.await_args.kwargs == {
        "category": "Electronics",
        "customer_type": "end_user",
        "limit": 20,
    }


@pytest.mark.asyncio
async def test_prospect_gaps_tool_validates_category() -> None:
    with patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()):
        with pytest.raises(ToolError) as exc_info:
            await _prospect_gaps_fn(category="   ")

    error = json.loads(str(exc_info.value))
    assert error["code"] == "VALIDATION_ERROR"
    assert error["field"] == "category"


@pytest.mark.asyncio
async def test_intelligence_tools_reject_mismatched_bearer_and_header_tenant() -> None:
    token = _tenant_bearer_token("00000000-0000-0000-0000-000000000001")

    with patch(
        "domains.intelligence.mcp.get_http_headers",
        return_value={
            "authorization": f"Bearer {token}",
            "x-tenant-id": "00000000-0000-0000-0000-000000000999",
        },
    ):
        with pytest.raises(ToolError) as exc_info:
            await _prospect_gaps_fn(category="Electronics")

    error = json.loads(str(exc_info.value))
    assert error["code"] == "INVALID_TENANT"


@pytest.mark.asyncio
async def test_customer_risk_signals_tool_returns_payload() -> None:
    with (
        _patch_session(),
        patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()),
        patch(
            "domains.intelligence.mcp.get_customer_risk_signals",
            new_callable=AsyncMock,
            return_value=_sample_customer_risk_signals("dormant"),
        ) as risk_mock,
    ):
        result = await _risk_signals_fn(status_filter="dormant", limit=20)

    assert result["status_filter"] == "dormant"
    assert result["customers"] == []
    assert risk_mock.await_args.args[1] == uuid.UUID("00000000-0000-0000-0000-000000000001")
    assert risk_mock.await_args.kwargs == {"status_filter": "dormant", "limit": 20}


@pytest.mark.asyncio
async def test_customer_risk_signals_tool_validates_status_filter() -> None:
    with patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()):
        with pytest.raises(ToolError) as exc_info:
            await _risk_signals_fn(status_filter="paused")

    error = json.loads(str(exc_info.value))
    assert error["code"] == "VALIDATION_ERROR"
    assert error["field"] == "status_filter"


@pytest.mark.asyncio
async def test_category_trends_tool_returns_payload() -> None:
    with (
        _patch_session(),
        patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()),
        patch(
            "domains.intelligence.mcp.get_category_trends",
            new_callable=AsyncMock,
            return_value=_sample_category_trends("last_30d"),
        ) as trends_mock,
    ):
        result = await _category_trends_fn(period="last_30d")

    assert result["period"] == "last_30d"
    assert result["trends"] == []
    assert trends_mock.await_args.args[1] == uuid.UUID("00000000-0000-0000-0000-000000000001")
    assert trends_mock.await_args.kwargs == {"period": "last_30d"}


@pytest.mark.asyncio
async def test_category_trends_tool_validates_period() -> None:
    with patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()):
        with pytest.raises(ToolError) as exc_info:
            await _category_trends_fn(period="qtd")

    error = json.loads(str(exc_info.value))
    assert error["code"] == "VALIDATION_ERROR"
    assert error["field"] == "period"


@pytest.mark.asyncio
async def test_product_affinity_tool_returns_map_payload() -> None:
    with (
        _patch_session(),
        patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()),
        patch(
            "domains.intelligence.mcp.get_product_affinity_map",
            new_callable=AsyncMock,
            return_value=_sample_affinity_map(),
        ) as affinity_mock,
    ):
        result = await _affinity_fn(min_shared=3, limit=25)

    assert result["pairs"] == []
    assert result["total"] == 0
    assert result["min_shared"] == 2
    assert result["limit"] == 50
    assert affinity_mock.await_args.args[1] == uuid.UUID("00000000-0000-0000-0000-000000000001")
    assert affinity_mock.await_args.kwargs == {"min_shared": 3, "limit": 25}


@pytest.mark.asyncio
async def test_customer_product_profile_tool_returns_profile_payload() -> None:
    customer_id = uuid.uuid4()
    with (
        _patch_session(),
        patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()),
        patch(
            "domains.intelligence.mcp.get_customer_product_profile",
            new_callable=AsyncMock,
            return_value=_sample_profile(customer_id),
        ),
    ):
        result = await _profile_fn(customer_id=str(customer_id))

    assert result["customer_id"] == str(customer_id)
    assert result["company_name"] == "Acme Trading"
    assert result["activity_basis"] == "confirmed_or_later_orders"


@pytest.mark.asyncio
async def test_customer_product_profile_tool_returns_not_found_for_missing_customer() -> None:
    customer_id = uuid.uuid4()
    with (
        _patch_session(),
        patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()),
        patch(
            "domains.intelligence.mcp.get_customer_product_profile",
            new_callable=AsyncMock,
            side_effect=ValueError("Customer not found."),
        ),
    ):
        with pytest.raises(ToolError) as exc_info:
            await _profile_fn(customer_id=str(customer_id))

    error = json.loads(str(exc_info.value))
    assert error == {
        "code": "NOT_FOUND",
        "field": "customer_id",
        "message": "Customer not found.",
        "retry": False,
    }


@pytest.mark.asyncio
async def test_customer_product_profile_tool_validates_uuid() -> None:
    with patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()):
        with pytest.raises(ToolError) as exc_info:
            await _profile_fn(customer_id="not-a-uuid")

    error = json.loads(str(exc_info.value))
    assert error["code"] == "VALIDATION_ERROR"
    assert error["field"] == "customer_id"


@pytest.mark.asyncio
async def test_intelligence_tools_require_tenant_context() -> None:
    with _patch_session(), patch("domains.intelligence.mcp.get_http_headers", return_value={}):
        with pytest.raises(ToolError) as exc_info:
            await _affinity_fn()

    error = json.loads(str(exc_info.value))
    assert error["code"] == "TENANT_REQUIRED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("setting_name", "tool_fn", "kwargs", "message"),
    [
        (
            "intelligence_prospect_gaps_enabled",
            _prospect_gaps_fn,
            {"category": "Electronics"},
            "Prospect gap analysis is disabled",
        ),
        (
            "intelligence_product_affinity_enabled",
            _affinity_fn,
            {},
            "Product affinity analysis is disabled",
        ),
        (
            "intelligence_product_performance_enabled",
            _product_performance_fn,
            {},
            "Product performance analysis is disabled",
        ),
        (
            "intelligence_category_trends_enabled",
            _category_trends_fn,
            {},
            "Category trend analysis is disabled",
        ),
        (
            "intelligence_customer_risk_signals_enabled",
            _risk_signals_fn,
            {},
            "Customer risk signals are disabled",
        ),
        (
            "intelligence_market_opportunities_enabled",
            _market_opportunities_fn,
            {},
            "Market opportunity analysis is disabled",
        ),
        (
            "intelligence_revenue_diagnosis_enabled",
            _revenue_diagnosis_fn,
            {},
            "Revenue diagnosis is disabled",
        ),
    ],
)
async def test_intelligence_tools_raise_when_feature_disabled(
    monkeypatch: pytest.MonkeyPatch,
    setting_name: str,
    tool_fn,
    kwargs: dict[str, object],
    message: str,
) -> None:
    monkeypatch.setattr(intelligence_mcp.settings, setting_name, False)
    with _patch_session(), patch("domains.intelligence.mcp.get_http_headers", return_value=_tenant_headers()):
        with pytest.raises(ToolError) as exc_info:
            await tool_fn(**kwargs)

    error = json.loads(str(exc_info.value))
    assert error["code"] == "FEATURE_DISABLED"
    assert error["message"] == message