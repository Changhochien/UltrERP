from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from domains.manufacturing.models import BillOfMaterials, ProductionPlan, ProductionPlanLine
from domains.manufacturing.schemas import (
	ProductionPlanCreate,
	ProductionPlanLineCreate,
	RoutingOperationResponse,
	RoutingResponse,
)
from domains.manufacturing.service import calculate_routing_cost_and_time, create_production_plan


class _ScalarResult:
	def __init__(self, value: object) -> None:
		self._value = value

	def _resolve(self) -> object:
		return self._value() if callable(self._value) else self._value

	def scalar(self) -> object:
		return self._resolve()

	def scalar_one_or_none(self) -> object:
		return self._resolve()


class _FakePlanningSession:
	def __init__(self, results: list[object]) -> None:
		self.results = results
		self.plan: ProductionPlan | None = None
		self.lines: list[ProductionPlanLine] = []

	async def execute(self, _statement: object) -> object:
		if not self.results:
			raise AssertionError("Unexpected execute() call")
		return self.results.pop(0)

	def add(self, instance: object) -> None:
		now = datetime.now(tz=UTC)
		if isinstance(instance, ProductionPlan):
			instance.id = uuid.uuid4()
			instance.created_at = now
			instance.updated_at = now
			instance.lines = []
			self.plan = instance
		elif isinstance(instance, ProductionPlanLine):
			instance.id = uuid.uuid4()
			instance.created_at = now
			self.lines.append(instance)
			if self.plan is not None:
				self.plan.lines.append(instance)

	async def flush(self) -> None:
		return None


def test_bill_of_materials_uses_partial_unique_index_for_active_versions() -> None:
	active_index = next(index for index in BillOfMaterials.__table__.indexes if index.name == "uq_bom_tenant_product_active")
	assert active_index.dialect_options["postgresql"]["where"] is not None


def test_calculate_routing_cost_and_time_uses_workstation_rates() -> None:
	workstation_id = uuid.uuid4()
	routing = RoutingResponse(
		id=uuid.uuid4(),
		tenant_id=uuid.uuid4(),
		code="ROUT-001",
		name="Assembly",
		description=None,
		status="submitted",
		disabled=False,
		created_at=datetime.now(tz=UTC),
		updated_at=datetime.now(tz=UTC),
		operations=[
			RoutingOperationResponse(
				id=uuid.uuid4(),
				tenant_id=uuid.uuid4(),
				routing_id=uuid.uuid4(),
				operation_name="Cut",
				workstation_id=workstation_id,
				sequence=1,
				setup_minutes=10,
				fixed_run_minutes=5,
				variable_run_minutes_per_unit=Decimal("2.0"),
				batch_size=1,
				overlap_lag_minutes=0,
				idx=0,
				notes=None,
				created_at=datetime.now(tz=UTC),
			),
		],
	)

	result = calculate_routing_cost_and_time(
		routing,
		Decimal("3"),
		{workstation_id: Decimal("120")},
	)

	assert result["total_minutes"] == 21
	assert result["total_cost"] == Decimal("42")


@pytest.mark.asyncio
async def test_create_production_plan_populates_aggregated_demand_fields() -> None:
	tenant_id = uuid.uuid4()
	start_date = datetime.now(tz=UTC)
	end_date = start_date + timedelta(days=7)
	session = _FakePlanningSession(results=[])
	session.results = [
		_ScalarResult(None),
		_ScalarResult(Decimal("7.000")),
		_ScalarResult(Decimal("2.000")),
		_ScalarResult(Decimal("1.000")),
		_ScalarResult(lambda: session.plan),
	]

	response = await create_production_plan(
		session,
		tenant_id,
		None,
		ProductionPlanCreate(
			name="Weekly Plan",
			planning_strategy="make_to_order",
			start_date=start_date,
			end_date=end_date,
			lines=[
				ProductionPlanLineCreate(
					product_id=uuid.uuid4(),
					forecast_demand=Decimal("3.000"),
					proposed_qty=Decimal("0"),
				)
			],
		),
	)

	assert response.lines[0].sales_order_demand == Decimal("7.000")
	assert response.lines[0].forecast_demand == Decimal("3.000")
	assert response.lines[0].total_demand == Decimal("10.000")
	assert response.lines[0].available_stock == Decimal("2.000")
	assert response.lines[0].open_work_order_qty == Decimal("1.000")
	assert response.lines[0].proposed_qty == Decimal("7.000")