"""Route tests for intelligence customer product profile endpoint."""

from __future__ import annotations

import sys
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

from datetime import UTC, date, datetime

import pytest

import domains.intelligence.routes as intelligence_routes
from domains.intelligence.schemas import (
    CategoryTrends,
    CustomerProductProfile,
    CustomerRiskSignals,
    MarketOpportunities,
    ProspectGaps,
    ProductAffinityMap,
    RevenueDiagnosis,
    RevenueDiagnosisComponents,
    RevenueDiagnosisDriver,
    RevenueDiagnosisSummary,
    RevenueDiagnosisWindow,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.domains.orders._helpers import (  # noqa: E402
    FakeAsyncSession,
    auth_header,
    http_get,
    setup_session,
    teardown_session,
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


async def test_market_opportunities_route_allows_sales_role() -> None:
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        with patch(
            "domains.intelligence.routes.get_market_opportunities",
            new_callable=AsyncMock,
            return_value=_sample_market_opportunities("last_30d"),
        ) as opportunities_mock:
            resp = await http_get(
                "/api/v1/intelligence/market-opportunities?period=last_30d",
                headers=auth_header("sales"),
            )
        assert resp.status_code == 200
        assert resp.json()["period"] == "last_30d"
        opportunities_mock.assert_awaited_once()
        assert opportunities_mock.await_args.args[0] is session
        assert opportunities_mock.await_args.args[1] == uuid.UUID("00000000-0000-0000-0000-000000000001")
        assert opportunities_mock.await_args.kwargs == {"period": "last_30d"}
    finally:
        teardown_session(prev)


async def test_revenue_diagnosis_route_allows_sales_role() -> None:
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        with patch(
            "domains.intelligence.routes.get_revenue_diagnosis",
            new_callable=AsyncMock,
            return_value=_sample_revenue_diagnosis(),
        ) as diagnosis_mock:
            resp = await http_get(
                "/api/v1/intelligence/revenue-diagnosis?period=1m&anchor_month=2026-03-01&category=Belts&limit=5",
                headers=auth_header("sales"),
            )
        assert resp.status_code == 200
        assert resp.json()["summary"]["revenue_delta"] == "20.00"
        diagnosis_mock.assert_awaited_once()
        assert diagnosis_mock.await_args.args[0] is session
        assert diagnosis_mock.await_args.args[1] == uuid.UUID("00000000-0000-0000-0000-000000000001")
        assert diagnosis_mock.await_args.kwargs == {
            "period": "1m",
            "anchor_month": date(2026, 3, 1),
            "category": "Belts",
            "limit": 5,
        }
    finally:
        teardown_session(prev)


async def test_prospect_gaps_route_allows_sales_role() -> None:
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        with patch(
            "domains.intelligence.routes.get_prospect_gaps",
            new_callable=AsyncMock,
            return_value=_sample_prospect_gaps("Electronics"),
        ) as gaps_mock:
            resp = await http_get(
                "/api/v1/intelligence/prospect-gaps?category=Electronics&customer_type=end_user&limit=20",
                headers=auth_header("sales"),
            )
        assert resp.status_code == 200
        assert resp.json()["target_category"] == "Electronics"
        gaps_mock.assert_awaited_once()
        assert gaps_mock.await_args.args[0] is session
        assert gaps_mock.await_args.args[1] == uuid.UUID("00000000-0000-0000-0000-000000000001")
        assert gaps_mock.await_args.kwargs == {
            "category": "Electronics",
            "customer_type": "end_user",
            "limit": 20,
        }
    finally:
        teardown_session(prev)


async def test_prospect_gaps_route_rejects_finance_role() -> None:
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_get(
            "/api/v1/intelligence/prospect-gaps?category=Electronics",
            headers=auth_header("finance"),
        )
        assert resp.status_code == 403
    finally:
        teardown_session(prev)


async def test_prospect_gaps_route_rejects_blank_category() -> None:
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_get(
            "/api/v1/intelligence/prospect-gaps?category=%20%20%20",
            headers=auth_header("sales"),
        )
        assert resp.status_code == 400
        assert resp.json() == {"detail": "category is required"}
    finally:
        teardown_session(prev)


async def test_customer_risk_signals_route_allows_sales_role() -> None:
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        with patch(
            "domains.intelligence.routes.get_customer_risk_signals",
            new_callable=AsyncMock,
            return_value=_sample_customer_risk_signals("growing"),
        ) as risk_mock:
            resp = await http_get(
                "/api/v1/intelligence/customers/risk-signals?status=growing&limit=20",
                headers=auth_header("sales"),
            )
        assert resp.status_code == 200
        assert resp.json()["status_filter"] == "growing"
        risk_mock.assert_awaited_once()
        assert risk_mock.await_args.args[0] is session
        assert risk_mock.await_args.args[1] == uuid.UUID("00000000-0000-0000-0000-000000000001")
        assert risk_mock.await_args.kwargs == {"status_filter": "growing", "limit": 20}
    finally:
        teardown_session(prev)


async def test_customer_risk_signals_route_rejects_finance_role() -> None:
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_get(
            "/api/v1/intelligence/customers/risk-signals",
            headers=auth_header("finance"),
        )
        assert resp.status_code == 403
    finally:
        teardown_session(prev)


async def test_category_trends_route_allows_sales_role() -> None:
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        with patch(
            "domains.intelligence.routes.get_category_trends",
            new_callable=AsyncMock,
            return_value=_sample_category_trends("last_30d"),
        ) as trends_mock:
            resp = await http_get(
                "/api/v1/intelligence/category-trends?period=last_30d",
                headers=auth_header("sales"),
            )
        assert resp.status_code == 200
        assert resp.json()["period"] == "last_30d"
        trends_mock.assert_awaited_once()
        assert trends_mock.await_args.args[0] is session
        assert trends_mock.await_args.args[1] == uuid.UUID("00000000-0000-0000-0000-000000000001")
        assert trends_mock.await_args.kwargs == {"period": "last_30d"}
    finally:
        teardown_session(prev)


async def test_category_trends_route_rejects_finance_role() -> None:
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_get(
            "/api/v1/intelligence/category-trends",
            headers=auth_header("finance"),
        )
        assert resp.status_code == 403
    finally:
        teardown_session(prev)


async def test_product_affinity_route_allows_admin_role() -> None:
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        with patch(
            "domains.intelligence.routes.get_product_affinity_map",
            new_callable=AsyncMock,
            return_value=_sample_affinity_map(),
        ) as affinity_mock:
            resp = await http_get(
                "/api/v1/intelligence/affinity?min_shared=3&limit=25",
                headers=auth_header("admin"),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["pairs"] == []
        assert body["min_shared"] == 2
        assert body["limit"] == 50
        affinity_mock.assert_awaited_once()
        assert affinity_mock.await_args.args[0] is session
        assert affinity_mock.await_args.args[1] == uuid.UUID("00000000-0000-0000-0000-000000000001")
        assert affinity_mock.await_args.kwargs == {"min_shared": 3, "limit": 25}
    finally:
        teardown_session(prev)


async def test_product_affinity_route_allows_sales_role() -> None:
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        with patch(
            "domains.intelligence.routes.get_product_affinity_map",
            new_callable=AsyncMock,
            return_value=_sample_affinity_map(),
        ):
            resp = await http_get(
                "/api/v1/intelligence/affinity",
                headers=auth_header("sales"),
            )
        assert resp.status_code == 200
    finally:
        teardown_session(prev)


async def test_customer_product_profile_route_allows_admin_role() -> None:
    session = FakeAsyncSession()
    customer_id = uuid.uuid4()
    prev = setup_session(session)
    try:
        with patch(
            "domains.intelligence.routes.get_customer_product_profile",
            new_callable=AsyncMock,
            return_value=_sample_profile(customer_id),
        ):
            resp = await http_get(
                f"/api/v1/intelligence/customers/{customer_id}/product-profile",
                headers=auth_header("admin"),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["company_name"] == "Acme Trading"
        assert body["frequency_trend"] == "increasing"
    finally:
        teardown_session(prev)


async def test_customer_product_profile_route_allows_sales_role() -> None:
    session = FakeAsyncSession()
    customer_id = uuid.uuid4()
    prev = setup_session(session)
    try:
        with patch(
            "domains.intelligence.routes.get_customer_product_profile",
            new_callable=AsyncMock,
            return_value=_sample_profile(customer_id),
        ):
            resp = await http_get(
                f"/api/v1/intelligence/customers/{customer_id}/product-profile",
                headers=auth_header("sales"),
            )
        assert resp.status_code == 200
    finally:
        teardown_session(prev)


async def test_customer_product_profile_route_returns_404_for_missing_customer() -> None:
    session = FakeAsyncSession()
    customer_id = uuid.uuid4()
    prev = setup_session(session)
    try:
        with patch(
            "domains.intelligence.routes.get_customer_product_profile",
            new_callable=AsyncMock,
            side_effect=ValueError("Customer not found."),
        ):
            resp = await http_get(
                f"/api/v1/intelligence/customers/{customer_id}/product-profile",
                headers=auth_header("admin"),
            )
        assert resp.status_code == 404
        assert resp.json() == {"detail": "Customer not found."}
    finally:
        teardown_session(prev)


@pytest.mark.parametrize(
    ("setting_name", "path", "detail"),
    [
        (
            "intelligence_prospect_gaps_enabled",
            "/api/v1/intelligence/prospect-gaps?category=Electronics",
            "Prospect gap analysis is disabled",
        ),
        (
            "intelligence_product_affinity_enabled",
            "/api/v1/intelligence/affinity",
            "Product affinity analysis is disabled",
        ),
        (
            "intelligence_category_trends_enabled",
            "/api/v1/intelligence/category-trends",
            "Category trend analysis is disabled",
        ),
        (
            "intelligence_customer_risk_signals_enabled",
            "/api/v1/intelligence/customers/risk-signals",
            "Customer risk signals are disabled",
        ),
        (
            "intelligence_market_opportunities_enabled",
            "/api/v1/intelligence/market-opportunities",
            "Market opportunity analysis is disabled",
        ),
        (
            "intelligence_revenue_diagnosis_enabled",
            "/api/v1/intelligence/revenue-diagnosis",
            "Revenue diagnosis is disabled",
        ),
    ],
)
async def test_intelligence_routes_return_403_when_feature_disabled(
    monkeypatch: pytest.MonkeyPatch,
    setting_name: str,
    path: str,
    detail: str,
) -> None:
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        monkeypatch.setattr(intelligence_routes.settings, setting_name, False)
        resp = await http_get(path, headers=auth_header("sales"))
        assert resp.status_code == 403
        assert resp.json() == {"detail": detail}
    finally:
        teardown_session(prev)