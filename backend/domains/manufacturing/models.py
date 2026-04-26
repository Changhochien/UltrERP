"""Manufacturing domain models - BOM, Work Orders, Routing, Workstations, Production Planning, and OEE."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
	Boolean,
	DateTime,
	Enum as SAEnum,
	Float,
	ForeignKey,
	Index,
	Integer,
	Numeric,
	String,
	Text,
	func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
	from common.models.product import Product
	from common.models.warehouse import Warehouse


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BomStatus(str, Enum):
	DRAFT = "draft"
	SUBMITTED = "submitted"
	INACTIVE = "inactive"
	SUPERSEDED = "superseded"


class WorkOrderStatus(str, Enum):
	DRAFT = "draft"
	SUBMITTED = "submitted"
	NOT_STARTED = "not_started"
	IN_PROGRESS = "in_progress"
	COMPLETED = "completed"
	STOPPED = "stopped"
	CANCELLED = "cancelled"


class WorkOrderTransferMode(str, Enum):
	DIRECT = "direct"
	MANUFACTURE = "manufacture"


class RoutingStatus(str, Enum):
	DRAFT = "draft"
	SUBMITTED = "submitted"
	INACTIVE = "inactive"


class WorkstationStatus(str, Enum):
	ACTIVE = "active"
	DISABLED = "disabled"


class ProductionPlanStatus(str, Enum):
	DRAFT = "draft"
	REVIEWED = "reviewed"
	FIRMED = "firmed"
	CLOSED = "closed"


class ManufacturingProposalStatus(str, Enum):
	PROPOSED = "proposed"
	ACCEPTED = "accepted"
	REJECTED = "rejected"
	STALE = "stale"


class DowntimeReason(str, Enum):
	PLANNED_MAINTENANCE = "planned_maintenance"
	UNPLANNED_BREAKDOWN = "unplanned_breakdown"
	CHANGEOVER = "changeover"
	MATERIAL_SHORTAGE = "material_shortage"
	QUALITY_HOLD = "quality_hold"


# ---------------------------------------------------------------------------
# BOM Models
# ---------------------------------------------------------------------------


class BillOfMaterials(Base):
	"""Bill of Materials master record."""

	__tablename__ = "bill_of_materials"
	__table_args__ = (
		Index("ix_bom_tenant_product", "tenant_id", "product_id"),
		Index("ix_bom_tenant_status", "tenant_id", "status"),
		Index("uq_bom_tenant_product_active", "tenant_id", "product_id", unique=True),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	product_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
	)
	product: Mapped[Product] = relationship(back_populates=None)
	code: Mapped[str] = mapped_column(String(100), nullable=False)
	name: Mapped[str] = mapped_column(String(300), nullable=False)
	bom_quantity: Mapped[Decimal] = mapped_column(Numeric(19, 6), default=Decimal("1"), nullable=False)
	unit: Mapped[str] = mapped_column(String(50), default="pcs", nullable=False)
	status: Mapped[BomStatus] = mapped_column(
		SAEnum(BomStatus, name="bom_status"), default=BomStatus.DRAFT, nullable=False,
	)
	revision: Mapped[str | None] = mapped_column(String(50), nullable=True)
	is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	supersedes_bom_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), nullable=True,
	)
	routing_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), nullable=True,
	)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)
	submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	submitted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	items: Mapped[list[BillOfMaterialsItem]] = relationship(
		back_populates="bom",
		cascade="all, delete-orphan",
	)


class BillOfMaterialsItem(Base):
	"""BOM material line item."""

	__tablename__ = "bill_of_materials_item"
	__table_args__ = (
		Index("ix_bom_item_tenant_bom", "tenant_id", "bom_id"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	bom_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("bill_of_materials.id"), nullable=False,
	)
	bom: Mapped[BillOfMaterials] = relationship(back_populates="items")
	item_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
	)
	item: Mapped[Product] = relationship()
	item_code: Mapped[str] = mapped_column(String(100), nullable=False)
	item_name: Mapped[str] = mapped_column(String(300), nullable=False)
	required_quantity: Mapped[Decimal] = mapped_column(Numeric(19, 6), nullable=False)
	unit: Mapped[str] = mapped_column(String(50), default="pcs", nullable=False)
	source_warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=True,
	)
	source_warehouse: Mapped[Warehouse | None] = relationship()
	idx: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)


# ---------------------------------------------------------------------------
# Work Order Models
# ---------------------------------------------------------------------------


class WorkOrder(Base):
	"""Manufacturing work order."""

	__tablename__ = "work_order"
	__table_args__ = (
		Index("ix_wo_tenant_status", "tenant_id", "status"),
		Index("ix_wo_tenant_product", "tenant_id", "product_id"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	code: Mapped[str] = mapped_column(String(100), nullable=False)
	name: Mapped[str] = mapped_column(String(300), nullable=False)
	product_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
	)
	product: Mapped[Product] = relationship()
	bom_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("bill_of_materials.id"), nullable=False,
	)
	bom: Mapped[BillOfMaterials] = relationship()
	bom_snapshot: Mapped[dict | None] = mapped_column(nullable=True)
	quantity: Mapped[Decimal] = mapped_column(Numeric(19, 6), nullable=False)
	produced_quantity: Mapped[Decimal] = mapped_column(Numeric(19, 6), default=Decimal("0"), nullable=False)
	source_warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=True,
	)
	source_warehouse: Mapped[Warehouse | None] = relationship(foreign_keys=[source_warehouse_id])
	wip_warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=True,
	)
	wip_warehouse: Mapped[Warehouse | None] = relationship(foreign_keys=[wip_warehouse_id])
	fg_warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=True,
	)
	fg_warehouse: Mapped[Warehouse | None] = relationship(foreign_keys=[fg_warehouse_id])
	status: Mapped[WorkOrderStatus] = mapped_column(
		SAEnum(WorkOrderStatus, name="work_order_status"),
		default=WorkOrderStatus.DRAFT,
		nullable=False,
	)
	transfer_mode: Mapped[WorkOrderTransferMode] = mapped_column(
		SAEnum(WorkOrderTransferMode, name="wo_transfer_mode"),
		default=WorkOrderTransferMode.DIRECT,
		nullable=False,
	)
	planned_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	stopped_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
	cancelled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
	routing_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
	routing_snapshot: Mapped[dict | None] = mapped_column(nullable=True)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	material_lines: Mapped[list[WorkOrderMaterialLine]] = relationship(
		back_populates="work_order",
		cascade="all, delete-orphan",
	)


class WorkOrderMaterialLine(Base):
	"""Work order material requirement line."""

	__tablename__ = "work_order_material_line"
	__table_args__ = (
		Index("ix_woml_wo_id", "work_order_id"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	work_order_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("work_order.id"), nullable=False,
	)
	work_order: Mapped[WorkOrder] = relationship(back_populates="material_lines")
	item_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
	)
	item: Mapped[Product] = relationship()
	item_code: Mapped[str] = mapped_column(String(100), nullable=False)
	item_name: Mapped[str] = mapped_column(String(300), nullable=False)
	required_quantity: Mapped[Decimal] = mapped_column(Numeric(19, 6), nullable=False)
	unit: Mapped[str] = mapped_column(String(50), default="pcs", nullable=False)
	source_warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=True,
	)
	source_warehouse: Mapped[Warehouse | None] = relationship()
	reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(19, 6), default=Decimal("0"), nullable=False)
	transferred_quantity: Mapped[Decimal] = mapped_column(Numeric(19, 6), default=Decimal("0"), nullable=False)
	consumed_quantity: Mapped[Decimal] = mapped_column(Numeric(19, 6), default=Decimal("0"), nullable=False)
	idx: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)


# ---------------------------------------------------------------------------
# Routing and Workstation Models
# ---------------------------------------------------------------------------


class Workstation(Base):
	"""Manufacturing workstation master."""

	__tablename__ = "workstation"
	__table_args__ = (
		Index("ix_ws_tenant_status", "tenant_id", "status"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	code: Mapped[str] = mapped_column(String(100), nullable=False)
	name: Mapped[str] = mapped_column(String(300), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	status: Mapped[WorkstationStatus] = mapped_column(
		SAEnum(WorkstationStatus, name="workstation_status"),
		default=WorkstationStatus.ACTIVE,
		nullable=False,
	)
	hourly_cost: Mapped[Decimal] = mapped_column(Numeric(19, 6), default=Decimal("0"), nullable=False)
	capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
	disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	hours: Mapped[list[WorkstationWorkingHour]] = relationship(
		back_populates="workstation",
		cascade="all, delete-orphan",
	)


class WorkstationWorkingHour(Base):
	"""Workstation working hours definition."""

	__tablename__ = "workstation_working_hour"

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	workstation_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("workstation.id"), nullable=False,
	)
	workstation: Mapped[Workstation] = relationship(back_populates="hours")
	day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday, 6=Sunday
	start_time: Mapped[str] = mapped_column(String(10), nullable=False)  # HH:MM
	end_time: Mapped[str] = mapped_column(String(10), nullable=False)  # HH:MM


class Routing(Base):
	"""Manufacturing routing template."""

	__tablename__ = "routing"
	__table_args__ = (
		Index("ix_routing_tenant_status", "tenant_id", "status"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	code: Mapped[str] = mapped_column(String(100), nullable=False)
	name: Mapped[str] = mapped_column(String(300), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	status: Mapped[RoutingStatus] = mapped_column(
		SAEnum(RoutingStatus, name="routing_status"),
		default=RoutingStatus.DRAFT,
		nullable=False,
	)
	disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	operations: Mapped[list[RoutingOperation]] = relationship(
		back_populates="routing",
		cascade="all, delete-orphan",
		order_by="RoutingOperation.sequence",
	)


class RoutingOperation(Base):
	"""Routing operation definition."""

	__tablename__ = "routing_operation"
	__table_args__ = (
		Index("ix_routing_op_routing", "routing_id"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	routing_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("routing.id"), nullable=False,
	)
	routing: Mapped[Routing] = relationship(back_populates="operations")
	operation_name: Mapped[str] = mapped_column(String(200), nullable=False)
	workstation_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), ForeignKey("workstation.id"), nullable=True,
	)
	workstation: Mapped[Workstation | None] = relationship()
	sequence: Mapped[int] = mapped_column(Integer, nullable=False)
	setup_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	fixed_run_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	variable_run_minutes_per_unit: Mapped[Decimal] = mapped_column(
		Numeric(19, 6), default=Decimal("0"), nullable=False,
	)
	batch_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
	overlap_lag_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	idx: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)


# ---------------------------------------------------------------------------
# Production Planning Models
# ---------------------------------------------------------------------------


class ManufacturingProposal(Base):
	"""Manufacturing proposal for work order creation."""

	__tablename__ = "manufacturing_proposal"
	__table_args__ = (
		Index("ix_mp_tenant_status", "tenant_id", "status"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	product_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
	)
	product: Mapped[Product] = relationship()
	bom_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), ForeignKey("bill_of_materials.id"), nullable=True,
	)
	bom: Mapped[BillOfMaterials | None] = relationship()
	demand_source: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "sales_order", "forecast"
	demand_source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
	demand_quantity: Mapped[Decimal] = mapped_column(Numeric(19, 6), nullable=False)
	proposed_quantity: Mapped[Decimal] = mapped_column(Numeric(19, 6), nullable=False)
	available_quantity: Mapped[Decimal] = mapped_column(Numeric(19, 6), default=Decimal("0"), nullable=False)
	status: Mapped[ManufacturingProposalStatus] = mapped_column(
		SAEnum(ManufacturingProposalStatus, name="manufacturing_proposal_status"),
		default=ManufacturingProposalStatus.PROPOSED,
		nullable=False,
	)
	decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
	decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
	decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
	decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	work_order_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), ForeignKey("work_order.id"), nullable=True,
	)
	shortages: Mapped[dict | None] = mapped_column(nullable=True)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)


class ProductionPlan(Base):
	"""Production plan for demand aggregation and work order generation."""

	__tablename__ = "production_plan"
	__table_args__ = (
		Index("ix_pp_tenant_status", "tenant_id", "status"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	code: Mapped[str] = mapped_column(String(100), nullable=False)
	name: Mapped[str] = mapped_column(String(300), nullable=False)
	status: Mapped[ProductionPlanStatus] = mapped_column(
		SAEnum(ProductionPlanStatus, name="production_plan_status"),
		default=ProductionPlanStatus.DRAFT,
		nullable=False,
	)
	planning_strategy: Mapped[str] = mapped_column(
		String(50), default="make_to_order", nullable=False,
	)  # make_to_order, make_to_stock
	start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	firmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	firmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	lines: Mapped[list[ProductionPlanLine]] = relationship(
		back_populates="plan",
		cascade="all, delete-orphan",
	)


class ProductionPlanLine(Base):
	"""Production plan line item."""

	__tablename__ = "production_plan_line"
	__table_args__ = (
		Index("ix_pp_line_plan", "plan_id"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	plan_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("production_plan.id"), nullable=False,
	)
	plan: Mapped[ProductionPlan] = relationship(back_populates="lines")
	product_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
	)
	product: Mapped[Product] = relationship()
	bom_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), ForeignKey("bill_of_materials.id"), nullable=True,
	)
	bom: Mapped[BillOfMaterials | None] = relationship()
	routing_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
	sales_order_demand: Mapped[Decimal] = mapped_column(
		Numeric(19, 6), default=Decimal("0"), nullable=False,
	)
	forecast_demand: Mapped[Decimal] = mapped_column(
		Numeric(19, 6), default=Decimal("0"), nullable=False,
	)
	total_demand: Mapped[Decimal] = mapped_column(Numeric(19, 6), nullable=False)
	open_work_order_qty: Mapped[Decimal] = mapped_column(
		Numeric(19, 6), default=Decimal("0"), nullable=False,
	)
	available_stock: Mapped[Decimal] = mapped_column(
		Numeric(19, 6), default=Decimal("0"), nullable=False,
	)
	proposed_qty: Mapped[Decimal] = mapped_column(Numeric(19, 6), nullable=False)
	firmed_qty: Mapped[Decimal] = mapped_column(Numeric(19, 6), default=Decimal("0"), nullable=False)
	completed_qty: Mapped[Decimal] = mapped_column(Numeric(19, 6), default=Decimal("0"), nullable=False)
	shortage_summary: Mapped[dict | None] = mapped_column(nullable=True)
	capacity_summary: Mapped[dict | None] = mapped_column(nullable=True)
	idx: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)


# ---------------------------------------------------------------------------
# Downtime and OEE Models
# ---------------------------------------------------------------------------


class DowntimeEntry(Base):
	"""Manufacturing downtime record."""

	__tablename__ = "downtime_entry"
	__table_args__ = (
		Index("ix_dt_tenant_workstation", "tenant_id", "workstation_id"),
		Index("ix_dt_tenant_date", "tenant_id", "start_time"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	workstation_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("workstation.id"), nullable=False,
	)
	workstation: Mapped[Workstation] = relationship()
	work_order_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), ForeignKey("work_order.id"), nullable=True,
	)
	work_order: Mapped[WorkOrder | None] = relationship()
	reason: Mapped[DowntimeReason] = mapped_column(
		SAEnum(DowntimeReason, name="downtime_reason"), nullable=False,
	)
	start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
	remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
	reporter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)


class OeeRecord(Base):
	"""OEE calculation record for a workstation/period."""

	__tablename__ = "oee_record"
	__table_args__ = (
		Index("ix_oee_tenant_workstation_date", "tenant_id", "workstation_id", "record_date"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	workstation_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("workstation.id"), nullable=False,
	)
	workstation: Mapped[Workstation] = relationship()
	work_order_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True), ForeignKey("work_order.id"), nullable=True,
	)
	record_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	planned_production_time: Mapped[int] = mapped_column(Integer, nullable=False)  # minutes
	stop_time: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # minutes
	run_time: Mapped[int] = mapped_column(Integer, nullable=False)  # minutes
	ideal_cycle_time: Mapped[int] = mapped_column(Integer, nullable=False)  # minutes per unit
	total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	good_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	reject_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	availability: Mapped[float] = mapped_column(Float, nullable=False)
	performance: Mapped[float] = mapped_column(Float, nullable=False)
	quality: Mapped[float] = mapped_column(Float, nullable=False)
	oee: Mapped[float] = mapped_column(Float, nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
