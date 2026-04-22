"""Focused CRM pipeline reporting tests for Story 23.5 and Story 23.6."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from domains.crm.schemas import CRMPipelineRecordType, CRMPipelineReportParams
from domains.crm.service import get_crm_pipeline_report


class _FakeScalarsResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return list(self._values)


class _FakeListResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def scalars(self) -> _FakeScalarsResult:
        return _FakeScalarsResult(self._values)


class FakeSession:
    def __init__(self, execute_results: list[object]) -> None:
        self._execute_results = list(execute_results)
        self.begin_calls = 0

    async def execute(self, stmt: object, params: object = None) -> object:
        if isinstance(params, dict) and "tid" in params:
            return _FakeListResult([])
        return self._execute_results.pop(0)

    def begin(self) -> "FakeSession":
        self.begin_calls += 1
        return self

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.mark.asyncio
async def test_get_crm_pipeline_report_segments_records_by_status_dimension_and_dropoff() -> None:
    lead = SimpleNamespace(
        id=uuid.uuid4(),
        status="open",
        territory="North",
        lead_owner="alice",
        utm_source="expo",
        utm_medium="field",
        utm_campaign="spring-2026",
        utm_content="hero-banner",
    )
    opportunity = SimpleNamespace(
        id=uuid.uuid4(),
        status="quotation",
        sales_stage="proposal",
        territory="North",
        customer_group="Industrial",
        opportunity_owner="alice",
        lost_reason="",
        utm_source="expo",
        utm_medium="field",
        utm_campaign="spring-2026",
        utm_content="hero-banner",
        opportunity_amount=Decimal("25000.00"),
    )
    quotation = SimpleNamespace(
        id=uuid.uuid4(),
        opportunity_id=opportunity.id,
        status="partially_ordered",
        territory="North",
        customer_group="Industrial",
        lost_reason="",
        utm_source="expo",
        utm_medium="field",
        utm_campaign="spring-2026",
        utm_content="hero-banner",
        grand_total=Decimal("26250.00"),
        order_count=0,
        transaction_date=date(2026, 4, 21),
        valid_till=date(2026, 5, 21),
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    session = FakeSession(
        execute_results=[
            _FakeListResult([lead]),
            _FakeListResult([opportunity]),
            _FakeListResult([quotation]),
            _FakeListResult([]),
        ]
    )

    report = await get_crm_pipeline_report(session, CRMPipelineReportParams())

    assert report.totals.lead_count == 1
    assert report.totals.opportunity_count == 1
    assert report.totals.quotation_count == 1
    assert report.totals.open_count == 3
    assert report.totals.terminal_count == 0
    assert report.totals.open_pipeline_amount == Decimal("51250.00")
    assert any(segment.record_type == "opportunity" and segment.key == "proposal" for segment in report.by_sales_stage)
    assert any(segment.record_type == "quotation" and segment.key == "Industrial" for segment in report.by_customer_group)
    assert any(segment.record_type == "lead" and segment.key == "alice" for segment in report.by_owner)
    assert any(segment.key == "expo" for segment in report.by_utm_source)
    assert any(segment.key == "field" for segment in report.by_utm_medium)
    assert any(segment.key == "spring-2026" for segment in report.by_utm_campaign)
    assert any(segment.key == "hero-banner" for segment in report.by_utm_content)
    assert report.dropoff.lead_only_count == 1
    assert report.dropoff.opportunity_without_quotation_count == 0
    assert report.dropoff.quotation_without_order_count == 1


@pytest.mark.asyncio
async def test_get_crm_pipeline_report_applies_sales_stage_filter_to_opportunity_slice() -> None:
    lead = SimpleNamespace(
        id=uuid.uuid4(),
        status="open",
        territory="North",
        lead_owner="alice",
        utm_source="expo",
        utm_medium="field",
        utm_campaign="spring-2026",
        utm_content="hero-banner",
    )
    opportunities = [
        SimpleNamespace(
            id=uuid.uuid4(),
            status="open",
            sales_stage="qualification",
            territory="North",
            customer_group="Industrial",
            opportunity_owner="alice",
            lost_reason="",
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="hero-banner",
            opportunity_amount=Decimal("1000.00"),
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            status="open",
            sales_stage="proposal",
            territory="North",
            customer_group="Industrial",
            opportunity_owner="bob",
            lost_reason="",
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="partner-footer",
            opportunity_amount=Decimal("2000.00"),
        ),
    ]
    quotation = SimpleNamespace(
        id=uuid.uuid4(),
        status="open",
        territory="North",
        customer_group="Industrial",
        lost_reason="",
        utm_source="expo",
        utm_medium="field",
        utm_campaign="spring-2026",
        utm_content="hero-banner",
        grand_total=Decimal("26250.00"),
        order_count=0,
        transaction_date=date(2026, 4, 21),
        valid_till=date(2026, 5, 21),
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    session = FakeSession(
        execute_results=[
            _FakeListResult([lead]),
            _FakeListResult(opportunities),
            _FakeListResult([quotation]),
            _FakeListResult([]),
        ]
    )

    report = await get_crm_pipeline_report(
        session,
        CRMPipelineReportParams(sales_stage="proposal"),
    )

    assert report.totals.lead_count == 0
    assert report.totals.quotation_count == 0
    assert report.totals.opportunity_count == 1
    assert report.by_sales_stage[0].key == "proposal"
    assert report.totals.open_pipeline_amount == Decimal("2000.00")


@pytest.mark.asyncio
async def test_get_crm_pipeline_report_supports_utm_content_filter_and_ordered_revenue() -> None:
    lead = SimpleNamespace(
        id=uuid.uuid4(),
        status="open",
        territory="North",
        lead_owner="alice",
        utm_source="expo",
        utm_medium="field",
        utm_campaign="spring-2026",
        utm_content="hero-banner",
    )
    opportunity = SimpleNamespace(
        id=uuid.uuid4(),
        status="quotation",
        sales_stage="proposal",
        territory="North",
        customer_group="Industrial",
        opportunity_owner="alice",
        lost_reason="",
        utm_source="expo",
        utm_medium="field",
        utm_campaign="spring-2026",
        utm_content="hero-banner",
        opportunity_amount=Decimal("25000.00"),
    )
    quotation = SimpleNamespace(
        id=uuid.uuid4(),
        opportunity_id=opportunity.id,
        status="partially_ordered",
        territory="North",
        customer_group="Industrial",
        lost_reason="",
        utm_source="expo",
        utm_medium="field",
        utm_campaign="spring-2026",
        utm_content="hero-banner",
        grand_total=Decimal("26250.00"),
        order_count=1,
        transaction_date=date(2026, 4, 21),
        valid_till=date(2026, 5, 21),
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    order = SimpleNamespace(
        id=uuid.uuid4(),
        source_quotation_id=quotation.id,
        status="confirmed",
        total_amount=Decimal("1050.00"),
        crm_context_snapshot={
            "utm_source": "expo",
            "utm_medium": "field",
            "utm_campaign": "spring-2026",
            "utm_content": "hero-banner",
            "utm_attribution_origin": "source_document",
        },
    )
    session = FakeSession(
        execute_results=[
            _FakeListResult([lead]),
            _FakeListResult([opportunity]),
            _FakeListResult([quotation]),
            _FakeListResult([order]),
        ]
    )

    report = await get_crm_pipeline_report(
        session,
        CRMPipelineReportParams(
            record_type=CRMPipelineRecordType.OPPORTUNITY,
            utm_content="hero-banner",
        ),
    )

    assert report.totals.opportunity_count == 1
    assert report.totals.ordered_revenue == Decimal("1050.00")
    assert report.filters.utm_content == "hero-banner"
    assert any(segment.key == "hero-banner" for segment in report.by_utm_content)
    assert any(segment.key == "expo" and segment.ordered_revenue == Decimal("1050.00") for segment in report.by_utm_source)
    assert any(segment.key == "field" and segment.ordered_revenue == Decimal("1050.00") for segment in report.by_utm_medium)
    assert any(segment.key == "spring-2026" and segment.ordered_revenue == Decimal("1050.00") for segment in report.by_utm_campaign)
    assert any(segment.key == "hero-banner" and segment.ordered_revenue == Decimal("1050.00") for segment in report.by_utm_content)


@pytest.mark.asyncio
async def test_get_crm_pipeline_report_includes_lead_conversion_metrics() -> None:
    lead = SimpleNamespace(
        id=uuid.uuid4(),
        status="converted",
        territory="North",
        lead_owner="alice",
        source="trade-show",
        conversion_state="converted",
        conversion_path="customer+opportunity",
        converted_at=datetime(2026, 4, 22, 9, 0, tzinfo=UTC),
        created_at=datetime(2026, 4, 20, 9, 0, tzinfo=UTC),
        utm_source="expo",
        utm_medium="field",
        utm_campaign="spring-2026",
        utm_content="hero-banner",
    )
    session = FakeSession(
        execute_results=[
            _FakeListResult([lead]),
            _FakeListResult([]),
            _FakeListResult([]),
            _FakeListResult([]),
        ]
    )

    report = await get_crm_pipeline_report(session, CRMPipelineReportParams(scope="all"))

    assert report.totals.conversion_count == 1
    assert report.totals.avg_days_to_conversion == Decimal("2.00")
    assert any(segment.key == "customer+opportunity" and segment.count == 1 for segment in report.by_conversion_path)
    assert any(segment.key == "trade-show" and segment.count == 1 for segment in report.by_conversion_source)


@pytest.mark.asyncio
async def test_get_crm_pipeline_report_builds_analytics_kpis_and_period_comparison() -> None:
    opportunity_open_id = uuid.uuid4()
    opportunity_converted_id = uuid.uuid4()
    previous_opportunity_id = uuid.uuid4()
    quotation_current_id = uuid.uuid4()
    quotation_previous_id = uuid.uuid4()

    leads = [
        SimpleNamespace(
            id=uuid.uuid4(),
            status="converted",
            qualification_status="qualified",
            territory="North",
            lead_owner="alice",
            source="trade-show",
            conversion_state="converted",
            conversion_path="customer+opportunity+quotation",
            converted_customer_id=uuid.uuid4(),
            converted_opportunity_id=opportunity_open_id,
            converted_quotation_id=quotation_current_id,
            created_at=datetime(2026, 4, 10, 9, 0, tzinfo=UTC),
            converted_at=datetime(2026, 4, 12, 9, 0, tzinfo=UTC),
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="hero-banner",
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            status="open",
            qualification_status="qualified",
            territory="North",
            lead_owner="bob",
            source="web",
            conversion_state="not_converted",
            conversion_path="",
            converted_customer_id=None,
            converted_opportunity_id=None,
            converted_quotation_id=None,
            created_at=datetime(2026, 4, 11, 9, 0, tzinfo=UTC),
            converted_at=None,
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="hero-banner",
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            status="converted",
            qualification_status="qualified",
            territory="North",
            lead_owner="alice",
            source="partner",
            conversion_state="converted",
            conversion_path="customer+opportunity",
            converted_customer_id=uuid.uuid4(),
            converted_opportunity_id=previous_opportunity_id,
            converted_quotation_id=quotation_previous_id,
            created_at=datetime(2026, 3, 5, 9, 0, tzinfo=UTC),
            converted_at=datetime(2026, 3, 8, 9, 0, tzinfo=UTC),
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="hero-banner",
        ),
    ]
    opportunities = [
        SimpleNamespace(
            id=opportunity_open_id,
            status="open",
            sales_stage="proposal",
            territory="North",
            customer_group="Industrial",
            opportunity_owner="alice",
            lost_reason="",
            competitor_name="",
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="hero-banner",
            probability=40,
            opportunity_amount=Decimal("10000.00"),
            expected_closing=date(2026, 4, 18),
            opportunity_title="Rotor Expansion",
        ),
        SimpleNamespace(
            id=opportunity_converted_id,
            status="converted",
            sales_stage="proposal",
            territory="North",
            customer_group="Industrial",
            opportunity_owner="alice",
            lost_reason="",
            competitor_name="",
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="hero-banner",
            probability=100,
            opportunity_amount=Decimal("12000.00"),
            expected_closing=date(2026, 4, 15),
            opportunity_title="Won Renewal",
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            status="lost",
            sales_stage="negotiation",
            territory="North",
            customer_group="Industrial",
            opportunity_owner="bob",
            lost_reason="Price",
            competitor_name="RivalCo",
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="hero-banner",
            probability=20,
            opportunity_amount=Decimal("5000.00"),
            expected_closing=date(2026, 4, 20),
            opportunity_title="Lost Bid",
        ),
        SimpleNamespace(
            id=previous_opportunity_id,
            status="open",
            sales_stage="proposal",
            territory="North",
            customer_group="Industrial",
            opportunity_owner="alice",
            lost_reason="",
            competitor_name="",
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="hero-banner",
            probability=50,
            opportunity_amount=Decimal("8000.00"),
            expected_closing=date(2026, 3, 20),
            opportunity_title="Prior Pipeline",
        ),
    ]
    quotations = [
        SimpleNamespace(
            id=quotation_current_id,
            opportunity_id=opportunity_converted_id,
            status="ordered",
            territory="North",
            customer_group="Industrial",
            lost_reason="",
            competitor_name="",
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="hero-banner",
            grand_total=Decimal("21000.00"),
            order_count=1,
            transaction_date=date(2026, 4, 14),
            valid_till=date(2026, 5, 14),
            created_at=datetime(2026, 4, 14, 9, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 14, 9, 0, tzinfo=UTC),
            party_label="Rotor Works",
        ),
        SimpleNamespace(
            id=quotation_previous_id,
            opportunity_id=previous_opportunity_id,
            status="ordered",
            territory="North",
            customer_group="Industrial",
            lost_reason="",
            competitor_name="",
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="hero-banner",
            grand_total=Decimal("15000.00"),
            order_count=1,
            transaction_date=date(2026, 3, 16),
            valid_till=date(2026, 4, 16),
            created_at=datetime(2026, 3, 16, 9, 0, tzinfo=UTC),
            updated_at=datetime(2026, 3, 16, 9, 0, tzinfo=UTC),
            party_label="Legacy Rotor Works",
        ),
    ]
    orders = [
        SimpleNamespace(
            id=uuid.uuid4(),
            source_quotation_id=quotation_current_id,
            status="confirmed",
            total_amount=Decimal("21000.00"),
            created_at=datetime(2026, 4, 16, 9, 0, tzinfo=UTC),
            crm_context_snapshot={
                "utm_source": "expo",
                "utm_medium": "field",
                "utm_campaign": "spring-2026",
                "utm_content": "hero-banner",
            },
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            source_quotation_id=quotation_previous_id,
            status="confirmed",
            total_amount=Decimal("15000.00"),
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=UTC),
            crm_context_snapshot={
                "utm_source": "expo",
                "utm_medium": "field",
                "utm_campaign": "spring-2026",
                "utm_content": "hero-banner",
            },
        ),
    ]
    session = FakeSession(
        execute_results=[
            _FakeListResult(leads),
            _FakeListResult(opportunities),
            _FakeListResult(quotations),
            _FakeListResult(orders),
        ]
    )

    report = await get_crm_pipeline_report(
        session,
        CRMPipelineReportParams(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            compare_start_date=date(2026, 3, 1),
            compare_end_date=date(2026, 3, 31),
            territory="North",
            utm_source="expo",
            utm_medium="field",
            utm_campaign="spring-2026",
            utm_content="hero-banner",
        ),
    )

    assert report.analytics.kpis.open_pipeline_value == Decimal("10000.00")
    assert report.analytics.kpis.weighted_pipeline_value == Decimal("4000.00")
    assert report.analytics.kpis.win_rate == Decimal("50.00")
    assert report.analytics.kpis.lead_conversion_rate == Decimal("50.00")
    assert report.analytics.kpis.average_deal_size == Decimal("21000.00")
    assert report.analytics.kpis.converted_revenue == Decimal("21000.00")
    assert report.analytics.kpis.time_to_conversion == Decimal("2.00")
    assert report.analytics.comparison["open_pipeline_value"].previous_value == Decimal("8000.00")
    assert report.analytics.comparison["open_pipeline_value"].delta == Decimal("2000.00")
    assert report.analytics.comparison["converted_revenue"].previous_value == Decimal("15000.00")
    assert report.analytics.comparison["converted_revenue"].delta == Decimal("6000.00")
    assert report.analytics.funnel[1].key == "opportunity"
    assert report.analytics.funnel[1].count == 1
    assert report.analytics.funnel[1].conversion_rate == Decimal("50.00")
    assert any(segment.key == "Price" and segment.count == 1 for segment in report.analytics.terminal_by_lost_reason)
    assert any(segment.key == "RivalCo" and segment.count == 1 for segment in report.analytics.terminal_by_competitor)
    assert report.analytics.owner_scorecards[0].owner == "alice"
    assert report.analytics.owner_scorecards[0].weighted_pipeline_value == Decimal("4000.00")
    assert any(group.key == "open_pipeline" and group.records[0].label == "Rotor Expansion" for group in report.analytics.drilldowns)