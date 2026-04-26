"""Manufacturing domain Pydantic schemas - BOM, Work Orders, Routing, Workstations, Production Planning, and OEE."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from backend.domains.manufacturing.models import (
	BomStatus,
	DowntimeReason,
	ManufacturingProposalStatus,
	ProductionPlanStatus,
	RoutingStatus,
	WorkOrderStatus,
	WorkOrderTransferMode,
	WorkstationStatus,
)


# ---------------------------------------------------------------------------
# BOM Schemas
# ---------------------------------------------------------------------------


class BomItemCreate(BaseModel):
	item_id: UUID
	item_code: str
	item_name: str
	required_quantity: Annotated[Decimal, Field(gt=0)]
	unit: str = "pcs"
	source_warehouse_id: UUID | None = None
	idx: int = 0
	notes: str | None = None


class BomItemUpdate(BaseModel):
	item_id: UUID | None = None
	item_code: str | None = None
	item_name: str | None = None
	required_quantity: Decimal | None = None
	unit: str | None = None
	source_warehouse_id: UUID | None = None
	idx: int | None = None
	notes: str | None = None


class BomItemResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	bom_id: UUID
	item_id: UUID
	item_code: str
	item_name: str
	required_quantity: Decimal
	unit: str
	source_warehouse_id: UUID | None
	idx: int
	notes: str | None
	created_at: datetime


class BomCreate(BaseModel):
	product_id: UUID
	code: str | None = None
	name: str | None = None
	bom_quantity: Annotated[Decimal, Field(gt=0)] = Decimal("1")
	unit: str = "pcs"
	revision: str | None = None
	routing_id: UUID | None = None
	notes: str | None = None
	items: list[BomItemCreate] = []


class BomUpdate(BaseModel):
	name: str | None = None
	bom_quantity: Decimal | None = None
	unit: str | None = None
	revision: str | None = None
	routing_id: UUID | None = None
	notes: str | None = None
	items: list[BomItemCreate] | None = None


class BomSubmit(BaseModel):
	notes: str | None = None


class BomSupersede(BaseModel):
	notes: str | None = None


class BomResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	product_id: UUID
	code: str
	name: str
	bom_quantity: Decimal
	unit: str
	status: BomStatus
	revision: str | None
	is_active: bool
	supersedes_bom_id: UUID | None
	routing_id: UUID | None
	notes: str | None
	submitted_at: datetime | None
	submitted_by: UUID | None
	created_at: datetime
	updated_at: datetime
	item_count: int = 0
	items: list[BomItemResponse] = []


class BomListResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	product_id: UUID
	code: str
	name: str
	bom_quantity: Decimal
	status: BomStatus
	revision: str | None
	is_active: bool
	submitted_at: datetime | None
	item_count: int = 0
	created_at: datetime
	updated_at: datetime


class BomHistoryResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	code: str
	name: str
	status: BomStatus
	revision: str | None
	is_active: bool
	submitted_at: datetime | None
	submitted_by: UUID | None
	created_at: datetime
	updated_at: datetime


# ---------------------------------------------------------------------------
# Work Order Schemas
# ---------------------------------------------------------------------------


class WorkOrderMaterialLineCreate(BaseModel):
	item_id: UUID
	item_code: str
	item_name: str
	required_quantity: Annotated[Decimal, Field(gt=0)]
	unit: str = "pcs"
	source_warehouse_id: UUID | None = None
	idx: int = 0
	notes: str | None = None


class WorkOrderMaterialLineResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	work_order_id: UUID
	item_id: UUID
	item_code: str
	item_name: str
	required_quantity: Decimal
	unit: str
	source_warehouse_id: UUID | None
	reserved_quantity: Decimal
	transferred_quantity: Decimal
	consumed_quantity: Decimal
	idx: int
	notes: str | None
	created_at: datetime


class WorkOrderCreate(BaseModel):
	product_id: UUID
	bom_id: UUID
	quantity: Annotated[Decimal, Field(gt=0)]
	source_warehouse_id: UUID | None = None
	wip_warehouse_id: UUID | None = None
	fg_warehouse_id: UUID | None = None
	transfer_mode: WorkOrderTransferMode = WorkOrderTransferMode.DIRECT
	planned_start_date: datetime | None = None
	due_date: datetime | None = None
	notes: str | None = None


class WorkOrderUpdate(BaseModel):
	quantity: Decimal | None = None
	source_warehouse_id: UUID | None = None
	wip_warehouse_id: UUID | None = None
	fg_warehouse_id: UUID | None = None
	transfer_mode: WorkOrderTransferMode | None = None
	planned_start_date: datetime | None = None
	due_date: datetime | None = None
	notes: str | None = None


class WorkOrderStatusTransition(BaseModel):
	status: WorkOrderStatus
	reason: str | None = None


class WorkOrderComplete(BaseModel):
	produced_quantity: Annotated[Decimal, Field(ge=0)]
	notes: str | None = None


class WorkOrderMaterialReserve(BaseModel):
	action: Literal["reserve", "release"]
	material_line_ids: list[UUID] | None = None


class WorkOrderTransfer(BaseModel):
	material_line_ids: list[UUID] | None = None
	quantity_by_line: dict[UUID, Decimal] | None = None


class WorkOrderResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	code: str
	name: str
	product_id: UUID
	bom_id: UUID
	bom_snapshot: dict | None
	quantity: Decimal
	produced_quantity: Decimal
	source_warehouse_id: UUID | None
	wip_warehouse_id: UUID | None
	fg_warehouse_id: UUID | None
	status: WorkOrderStatus
	transfer_mode: WorkOrderTransferMode
	planned_start_date: datetime | None
	due_date: datetime | None
	started_at: datetime | None
	completed_at: datetime | None
	stopped_reason: str | None
	cancelled_reason: str | None
	routing_id: UUID | None
	routing_snapshot: dict | None
	notes: str | None
	created_at: datetime
	updated_at: datetime
	material_lines: list[WorkOrderMaterialLineResponse] = []


class WorkOrderListResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	code: str
	name: str
	product_id: UUID
	bom_id: UUID
	quantity: Decimal
	produced_quantity: Decimal
	status: WorkOrderStatus
	transfer_mode: WorkOrderTransferMode
	planned_start_date: datetime | None
	due_date: datetime | None
	created_at: datetime
	updated_at: datetime


# ---------------------------------------------------------------------------
# Workstation Schemas
# ---------------------------------------------------------------------------


class WorkstationWorkingHourCreate(BaseModel):
	day_of_week: Annotated[int, Field(ge=0, le=6)]
	start_time: str
	end_time: str


class WorkstationCreate(BaseModel):
	code: str
	name: str
	description: str | None = None
	hourly_cost: Annotated[Decimal, Field(ge=0)] = Decimal("0")
	capacity: Annotated[int, Field(ge=1)] = 1
	hours: list[WorkstationWorkingHourCreate] = []


class WorkstationUpdate(BaseModel):
	name: str | None = None
	description: str | None = None
	hourly_cost: Decimal | None = None
	capacity: int | None = None
	disabled: bool | None = None
	hours: list[WorkstationWorkingHourCreate] | None = None


class WorkstationResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	code: str
	name: str
	description: str | None
	status: WorkstationStatus
	hourly_cost: Decimal
	capacity: int
	disabled: bool
	created_at: datetime
	updated_at: datetime
	hours: list[WorkstationWorkingHourCreate] = []


class WorkstationListResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	code: str
	name: str
	status: WorkstationStatus
	hourly_cost: Decimal
	capacity: int
	disabled: bool
	created_at: datetime
	updated_at: datetime


# ---------------------------------------------------------------------------
# Routing Schemas
# ---------------------------------------------------------------------------


class RoutingOperationCreate(BaseModel):
	operation_name: str
	workstation_id: UUID | None = None
	sequence: Annotated[int, Field(ge=0)]
	setup_minutes: int = 0
	fixed_run_minutes: int = 0
	variable_run_minutes_per_unit: Decimal = Decimal("0")
	batch_size: Annotated[int, Field(ge=1)] = 1
	overlap_lag_minutes: int = 0
	idx: int = 0
	notes: str | None = None


class RoutingOperationUpdate(BaseModel):
	operation_name: str | None = None
	workstation_id: UUID | None = None
	sequence: int | None = None
	setup_minutes: int | None = None
	fixed_run_minutes: int | None = None
	variable_run_minutes_per_unit: Decimal | None = None
	batch_size: int | None = None
	overlap_lag_minutes: int | None = None
	idx: int | None = None
	notes: str | None = None


class RoutingCreate(BaseModel):
	code: str
	name: str
	description: str | None = None
	operations: list[RoutingOperationCreate] = []


class RoutingUpdate(BaseModel):
	name: str | None = None
	description: str | None = None
	disabled: bool | None = None
	operations: list[RoutingOperationCreate] | None = None


class RoutingOperationResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	routing_id: UUID
	operation_name: str
	workstation_id: UUID | None
	sequence: int
	setup_minutes: int
	fixed_run_minutes: int
	variable_run_minutes_per_unit: Decimal
	batch_size: int
	overlap_lag_minutes: int
	idx: int
	notes: str | None
	created_at: datetime


class RoutingResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	code: str
	name: str
	description: str | None
	status: RoutingStatus
	disabled: bool
	created_at: datetime
	updated_at: datetime
	operations: list[RoutingOperationResponse] = []


class RoutingListResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	code: str
	name: str
	status: RoutingStatus
	disabled: bool
	operation_count: int = 0
	created_at: datetime
	updated_at: datetime


# ---------------------------------------------------------------------------
# Production Planning Schemas
# ---------------------------------------------------------------------------


class ProposalGenerateRequest(BaseModel):
	product_ids: list[UUID] | None = None  # None = all manufactured items with active BOMs


class ProposalDecision(BaseModel):
	decision: Literal["accept", "reject"]
	proposed_quantity: Decimal | None = None
	reason: str | None = None


class ManufacturingProposalResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	product_id: UUID
	bom_id: UUID | None
	demand_source: str
	demand_source_id: UUID | None
	demand_quantity: Decimal
	proposed_quantity: Decimal
	available_quantity: Decimal
	status: ManufacturingProposalStatus
	decision: str | None
	decision_reason: str | None
	decided_by: UUID | None
	decided_at: datetime | None
	work_order_id: UUID | None
	shortages: dict | None
	notes: str | None
	created_at: datetime
	updated_at: datetime


class ProductionPlanLineCreate(BaseModel):
	product_id: UUID
	bom_id: UUID | None = None
	routing_id: UUID | None = None
	forecast_demand: Decimal = Decimal("0")
	proposed_qty: Decimal = Decimal("0")
	idx: int = 0
	notes: str | None = None


class ProductionPlanLineUpdate(BaseModel):
	bom_id: UUID | None = None
	routing_id: UUID | None = None
	forecast_demand: Decimal | None = None
	proposed_qty: Decimal | None = None
	notes: str | None = None


class ProductionPlanCreate(BaseModel):
	name: str
	planning_strategy: str = "make_to_order"
	start_date: datetime
	end_date: datetime
	notes: str | None = None
	lines: list[ProductionPlanLineCreate] = []


class ProductionPlanUpdate(BaseModel):
	name: str | None = None
	planning_strategy: str | None = None
	start_date: datetime | None = None
	end_date: datetime | None = None
	notes: str | None = None


class ProductionPlanFirm(BaseModel):
	line_ids: list[UUID] | None = None  # None = all lines


class ProductionPlanLineResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	plan_id: UUID
	product_id: UUID
	bom_id: UUID | None
	routing_id: UUID | None
	sales_order_demand: Decimal
	forecast_demand: Decimal
	total_demand: Decimal
	open_work_order_qty: Decimal
	available_stock: Decimal
	proposed_qty: Decimal
	firmed_qty: Decimal
	completed_qty: Decimal
	shortage_summary: dict | None
	capacity_summary: dict | None
	idx: int
	notes: str | None
	created_at: datetime


class ProductionPlanResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	code: str
	name: str
	status: ProductionPlanStatus
	planning_strategy: str
	start_date: datetime
	end_date: datetime
	firmed_at: datetime | None
	firmed_by: UUID | None
	notes: str | None
	created_at: datetime
	updated_at: datetime
	lines: list[ProductionPlanLineResponse] = []


class ProductionPlanListResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	code: str
	name: str
	status: ProductionPlanStatus
	planning_strategy: str
	start_date: datetime
	end_date: datetime
	line_count: int = 0
	firmed_at: datetime | None
	created_at: datetime
	updated_at: datetime


# ---------------------------------------------------------------------------
# Downtime and OEE Schemas
# ---------------------------------------------------------------------------


class DowntimeCreate(BaseModel):
	workstation_id: UUID
	work_order_id: UUID | None = None
	reason: DowntimeReason
	start_time: datetime
	end_time: datetime | None = None
	remarks: str | None = None


class DowntimeUpdate(BaseModel):
	work_order_id: UUID | None = None
	reason: DowntimeReason | None = None
	start_time: datetime | None = None
	end_time: datetime | None = None
	remarks: str | None = None


class DowntimeResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	workstation_id: UUID
	work_order_id: UUID | None
	reason: DowntimeReason
	start_time: datetime
	end_time: datetime | None
	duration_minutes: int | None
	remarks: str | None
	reporter_id: UUID | None
	created_at: datetime
	updated_at: datetime


class OeeRecordCreate(BaseModel):
	workstation_id: UUID
	work_order_id: UUID | None = None
	record_date: datetime
	planned_production_time: Annotated[int, Field(gt=0)]
	stop_time: int = 0
	ideal_cycle_time: Annotated[int, Field(gt=0)]
	total_count: int = 0
	good_count: int = 0
	reject_count: int = 0


class OeeRecordUpdate(BaseModel):
	work_order_id: UUID | None = None
	planned_production_time: int | None = None
	stop_time: int | None = None
	ideal_cycle_time: int | None = None
	total_count: int | None = None
	good_count: int | None = None
	reject_count: int | None = None


class OeeRecordResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	workstation_id: UUID
	work_order_id: UUID | None
	record_date: datetime
	planned_production_time: int
	stop_time: int
	run_time: int
	ideal_cycle_time: int
	total_count: int
	good_count: int
	reject_count: int
	availability: float
	performance: float
	quality: float
	oee: float
	created_at: datetime


class OeeDashboardResponse(BaseModel):
	workstation_id: UUID | None = None
	current_oee: float
	availability: float
	performance: float
	quality: float
	trend_data: list[OeeRecordResponse] = []
	downtime_pareto: list[dict[str, Any]] = []
	period_start: datetime
	period_end: datetime


class DowntimeParetoResponse(BaseModel):
	reason: DowntimeReason
	frequency: int
	total_duration_minutes: int
	percentage: float


# ---------------------------------------------------------------------------
# Utility imports
# ---------------------------------------------------------------------------


from typing import Literal
