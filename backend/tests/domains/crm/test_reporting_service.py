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