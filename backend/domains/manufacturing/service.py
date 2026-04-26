"""Manufacturing domain services - BOM, Work Orders, Routing, Workstations, Production Planning, and OEE."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.domains.manufacturing.models import (
	BillOfMaterials,
	BillOfMaterialsItem,
	DowntimeEntry,
	ManufacturingProposal,
	ManufacturingProposalStatus,
	OeeRecord,
	ProductionPlan,
	ProductionPlanLine,
	ProductionPlanStatus,
	Routing,
	RoutingOperation,
	RoutingStatus,
	WorkOrder,
	WorkOrderMaterialLine,
	WorkOrderStatus,
	WorkOrderTransferMode,
	Workstation,
	WorkstationStatus,
	WorkstationWorkingHour,
)
from backend.domains.manufacturing.schemas import (
	BomCreate,
	BomItemCreate,
	BomItemResponse,
	BomListResponse,
	BomResponse,
	BomSubmit,
	BomSupersede,
	BomUpdate,
	DowntimeCreate,
	DowntimeParetoResponse,
	DowntimeResponse,
	DowntimeUpdate,
	ManufacturingProposalResponse,
	OeeDashboardResponse,
	OeeRecordCreate,
	OeeRecordResponse,
	OeeRecordUpdate,
	ProductionPlanCreate,
	ProductionPlanFirm,
	ProductionPlanLineCreate,
	ProductionPlanLineResponse,
	ProductionPlanListResponse,
	ProductionPlanResponse,
	ProductionPlanUpdate,
	ProposalDecision,
	ProposalGenerateRequest,
	RoutingCreate,
	RoutingListResponse,
	RoutingOperationCreate,
	RoutingResponse,
	RoutingUpdate,
	WorkOrderComplete,
	WorkOrderCreate,
	WorkOrderListResponse,
	WorkOrderMaterialLineResponse,
	WorkOrderResponse,
	WorkOrderStatusTransition,
	WorkOrderTransfer,
	WorkOrderUpdate,
	WorkstationCreate,
	WorkstationListResponse,
	WorkstationResponse,
	WorkstationUpdate,
)
from common.models.inventory_stock import InventoryStock
from common.models.order import SalesOrder, SalesOrderLine
from common.models.product import Product

if TYPE_CHECKING:
	from decimal import Decimal


# ============================================================================
# BOM Services
# ============================================================================


async def create_bom(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	user_id: uuid.UUID | None,
	payload: BomCreate,
) -> BomResponse:
	"""Create a new BOM in draft status."""
	# Generate code
	code = f"BOM-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
	
	bom = BillOfMaterials(
		tenant_id=tenant_id,
		product_id=payload.product_id,
		code=code,
		name=payload.name or f"BOM for product {payload.product_id}",
		bom_quantity=payload.bom_quantity,
		unit=payload.unit,
		revision=payload.revision,
		routing_id=payload.routing_id,
		notes=payload.notes,
		status="draft",
	)
	db.add(bom)
	await db.flush()
	
	# Add items
	for i, item_payload in enumerate(payload.items):
		item = BillOfMaterialsItem(
			tenant_id=tenant_id,
			bom_id=bom.id,
			item_id=item_payload.item_id,
			item_code=item_payload.item_code,
			item_name=item_payload.item_name,
			required_quantity=item_payload.required_quantity,
			unit=item_payload.unit,
			source_warehouse_id=item_payload.source_warehouse_id,
			idx=item_payload.idx if item_payload.idx else i,
			notes=item_payload.notes,
		)
		db.add(item)
	
	await db.flush()
	await db.refresh(bom)
	
	return await get_bom_by_id(db, tenant_id, bom.id)


async def get_bom_by_id(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	bom_id: uuid.UUID,
) -> BomResponse | None:
	"""Get BOM by ID with items."""
	stmt = (
		select(BillOfMaterials)
		.where(
			and_(
				BillOfMaterials.id == bom_id,
				BillOfMaterials.tenant_id == tenant_id,
			)
		)
		.options(selectinload(BillOfMaterials.items))
	)
	result = await db.execute(stmt)
	bom = result.scalar_one_or_none()
	
	if not bom:
		return None
	
	return BomResponse(
		id=bom.id,
		tenant_id=bom.tenant_id,
		product_id=bom.product_id,
		code=bom.code,
		name=bom.name,
		bom_quantity=bom.bom_quantity,
		unit=bom.unit,
		status=bom.status,
		revision=bom.revision,
		is_active=bom.is_active,
		supersedes_bom_id=bom.supersedes_bom_id,
		routing_id=bom.routing_id,
		notes=bom.notes,
		submitted_at=bom.submitted_at,
		submitted_by=bom.submitted_by,
		created_at=bom.created_at,
		updated_at=bom.updated_at,
		item_count=len(bom.items),
		items=[
			BomItemResponse(
				id=item.id,
				tenant_id=item.tenant_id,
				bom_id=item.bom_id,
				item_id=item.item_id,
				item_code=item.item_code,
				item_name=item.item_name,
				required_quantity=item.required_quantity,
				unit=item.unit,
				source_warehouse_id=item.source_warehouse_id,
				idx=item.idx,
				notes=item.notes,
				created_at=item.created_at,
			)
			for item in bom.items
		],
	)


async def list_boms(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	product_id: uuid.UUID | None = None,
	status: str | None = None,
	is_active: bool | None = None,
	page: int = 1,
	page_size: int = 20,
) -> tuple[list[BomListResponse], int]:
	"""List BOMs with pagination."""
	conditions = [BillOfMaterials.tenant_id == tenant_id]
	
	if product_id:
		conditions.append(BillOfMaterials.product_id == product_id)
	if status:
		conditions.append(BillOfMaterials.status == status)
	if is_active is not None:
		conditions.append(BillOfMaterials.is_active == is_active)
	
	# Count
	count_stmt = select(func.count(BillOfMaterials.id)).where(and_(*conditions))
	count_result = await db.execute(count_stmt)
	total = count_result.scalar() or 0
	
	# Query
	stmt = (
		select(BillOfMaterials)
		.where(and_(*conditions))
		.options(selectinload(BillOfMaterials.items))
		.order_by(BillOfMaterials.created_at.desc())
		.offset((page - 1) * page_size)
		.limit(page_size)
	)
	result = await db.execute(stmt)
	boms = result.scalars().all()
	
	return [
		BomListResponse(
			id=bom.id,
			tenant_id=bom.tenant_id,
			product_id=bom.product_id,
			code=bom.code,
			name=bom.name,
			bom_quantity=bom.bom_quantity,
			status=bom.status,
			revision=bom.revision,
			is_active=bom.is_active,
			submitted_at=bom.submitted_at,
			item_count=len(bom.items),
			created_at=bom.created_at,
			updated_at=bom.updated_at,
		)
		for bom in boms
	], total


async def get_bom_history(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	product_id: uuid.UUID,
) -> list[BomListResponse]:
	"""Get BOM history for a product."""
	stmt = (
		select(BillOfMaterials)
		.where(
			and_(
				BillOfMaterials.tenant_id == tenant_id,
				BillOfMaterials.product_id == product_id,
			)
		)
		.options(selectinload(BillOfMaterials.items))
		.order_by(BillOfMaterials.created_at.desc())
	)
	result = await db.execute(stmt)
	boms = result.scalars().all()
	
	return [
		BomListResponse(
			id=bom.id,
			tenant_id=bom.tenant_id,
			product_id=bom.product_id,
			code=bom.code,
			name=bom.name,
			bom_quantity=bom.bom_quantity,
			status=bom.status,
			revision=bom.revision,
			is_active=bom.is_active,
			submitted_at=bom.submitted_at,
			item_count=len(bom.items),
			created_at=bom.created_at,
			updated_at=bom.updated_at,
		)
		for bom in boms
	]


async def get_active_bom_for_product(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	product_id: uuid.UUID,
) -> BillOfMaterials | None:
	"""Get the active submitted BOM for a product."""
	stmt = (
		select(BillOfMaterials)
		.where(
			and_(
				BillOfMaterials.tenant_id == tenant_id,
				BillOfMaterials.product_id == product_id,
				BillOfMaterials.status == "submitted",
				BillOfMaterials.is_active == True,  # noqa: E712
			)
		)
		.options(selectinload(BillOfMaterials.items))
	)
	result = await db.execute(stmt)
	return result.scalar_one_or_none()


async def submit_bom(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	user_id: uuid.UUID,
	bom_id: uuid.UUID,
	payload: BomSubmit,
) -> BomResponse:
	"""Submit a BOM - validates and makes it active for production."""
	bom = await get_bom_by_id(db, tenant_id, bom_id)
	if not bom:
		raise ValueError("BOM not found")
	
	if bom.status != "draft":
		raise ValueError(f"Cannot submit BOM in status: {bom.status}")
	
	if not bom.items:
		raise ValueError("BOM must have at least one material line")
	
	# Check for self-reference cycle
	item_ids = [item.item_id for item in bom.items]
	if bom.product_id in item_ids:
		raise ValueError("BOM cannot contain its own product as a material")
	
	# Lock the BOM row for update to prevent race conditions
	stmt = (
		select(BillOfMaterials)
		.where(
			and_(
				BillOfMaterials.id == bom_id,
				BillOfMaterials.tenant_id == tenant_id,
			)
		)
	).with_for_update()
	result = await db.execute(stmt)
	db_bom = result.scalar_one_or_none()
	
	if not db_bom:
		raise ValueError("BOM not found")
	
	# Re-validate status after lock
	if db_bom.status != "draft":
		raise ValueError(f"Cannot submit BOM in status: {db_bom.status}")
	
	# Check if there's already an active submitted BOM (now under lock)
	existing_active_stmt = (
		select(BillOfMaterials)
		.where(
			and_(
				BillOfMaterials.tenant_id == tenant_id,
				BillOfMaterials.product_id == bom.product_id,
				BillOfMaterials.is_active == True,
				BillOfMaterials.id != bom_id,
			)
		)
	).with_for_update()
	existing_result = await db.execute(existing_active_stmt)
	existing_active = existing_result.scalar_one_or_none()
	if existing_active:
		raise ValueError(
			f"Active submitted BOM already exists for this product. "
			f"Please supersede it first or set is_active=False."
		)
	
	db_bom.status = "submitted"
	db_bom.is_active = True
	db_bom.submitted_at = datetime.utcnow()
	db_bom.submitted_by = user_id
	
	await db.flush()
	await db.refresh(db_bom)
	
	return await get_bom_by_id(db, tenant_id, bom_id)


async def supersede_bom(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	bom_id: uuid.UUID,
	replacement_bom_id: uuid.UUID,
	_payload: BomSupersede,
) -> BomResponse:
	"""Supersede a BOM with a replacement."""
	stmt = (
		select(BillOfMaterials)
		.where(
			and_(
				BillOfMaterials.id == bom_id,
				BillOfMaterials.tenant_id == tenant_id,
			)
		)
	)
	result = await db.execute(stmt)
	old_bom = result.scalar_one_or_none()
	
	if not old_bom:
		raise ValueError("BOM not found")
	
	if old_bom.status != "submitted":
		raise ValueError("Can only supersede submitted BOMs")
	
	# Verify replacement exists and is submitted
	replacement = await get_bom_by_id(db, tenant_id, replacement_bom_id)
	if not replacement:
		raise ValueError("Replacement BOM not found")
	if replacement.status != "submitted":
		raise ValueError("Replacement BOM must be submitted")
	
	# Update old BOM
	old_bom.status = "superseded"
	old_bom.is_active = False
	old_bom.supersedes_bom_id = replacement_bom_id
	
	# Make replacement active
	rep_stmt = (
		select(BillOfMaterials)
		.where(
			and_(
				BillOfMaterials.id == replacement_bom_id,
				BillOfMaterials.tenant_id == tenant_id,
			)
		)
	)
	rep_result = await db.execute(rep_stmt)
	rep_db_bom = rep_result.scalar_one()
	rep_db_bom.is_active = True
	
	await db.flush()
	await db.refresh(old_bom)
	
	return await get_bom_by_id(db, tenant_id, bom_id)


async def update_bom(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	bom_id: uuid.UUID,
	payload: BomUpdate,
) -> BomResponse:
	"""Update a draft BOM."""
	bom = await get_bom_by_id(db, tenant_id, bom_id)
	if not bom:
		raise ValueError("BOM not found")
	
	if bom.status != "draft":
		raise ValueError("Can only update draft BOMs")
	
	stmt = (
		select(BillOfMaterials)
		.where(
			and_(
				BillOfMaterials.id == bom_id,
				BillOfMaterials.tenant_id == tenant_id,
			)
		)
	)
	result = await db.execute(stmt)
	db_bom = result.scalar_one()
	
	if payload.name is not None:
		db_bom.name = payload.name
	if payload.bom_quantity is not None:
		db_bom.bom_quantity = payload.bom_quantity
	if payload.unit is not None:
		db_bom.unit = payload.unit
	if payload.revision is not None:
		db_bom.revision = payload.revision
	if payload.routing_id is not None:
		db_bom.routing_id = payload.routing_id
	if payload.notes is not None:
		db_bom.notes = payload.notes
	
	# Update items if provided
	if payload.items is not None:
		# Delete existing items
		del_stmt = select(BillOfMaterialsItem).where(
			and_(
				BillOfMaterialsItem.bom_id == bom_id,
				BillOfMaterialsItem.tenant_id == tenant_id,
			)
		)
		del_result = await db.execute(del_stmt)
		existing_items = del_result.scalars().all()
		for item in existing_items:
			await db.delete(item)
		
		# Add new items
		for i, item_payload in enumerate(payload.items):
			item = BillOfMaterialsItem(
				tenant_id=tenant_id,
				bom_id=bom_id,
				item_id=item_payload.item_id,
				item_code=item_payload.item_code,
				item_name=item_payload.item_name,
				required_quantity=item_payload.required_quantity,
				unit=item_payload.unit,
				source_warehouse_id=item_payload.source_warehouse_id,
				idx=item_payload.idx if item_payload.idx else i,
				notes=item_payload.notes,
			)
			db.add(item)
	
	await db.flush()
	return await get_bom_by_id(db, tenant_id, bom_id)


# ============================================================================
# Work Order Services
# ============================================================================


def _build_bom_snapshot(bom: BillOfMaterials, quantity: Decimal) -> dict:
	"""Build a snapshot of BOM data for work order."""
	return {
		"bom_id": str(bom.id),
		"bom_code": bom.code,
		"bom_name": bom.name,
		"bom_quantity": str(bom.bom_quantity),
		"unit": bom.unit,
		"revision": bom.revision,
		"items": [
			{
				"item_id": str(item.item_id),
				"item_code": item.item_code,
				"item_name": item.item_name,
				"required_quantity": str(
					item.required_quantity * quantity / bom.bom_quantity
					if bom.bom_quantity else item.required_quantity * quantity
				),
				"unit": item.unit,
				"source_warehouse_id": str(item.source_warehouse_id) if item.source_warehouse_id else None,
			}
			for item in bom.items
		],
	}


async def create_work_order(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	user_id: uuid.UUID | None,
	payload: WorkOrderCreate,
) -> WorkOrderResponse:
	"""Create a new work order from a submitted BOM."""
	# Verify BOM is submitted and active
	bom = await get_bom_by_id(db, tenant_id, payload.bom_id)
	if not bom:
		raise ValueError("BOM not found")
	if bom.status != "submitted":
		raise ValueError("Can only create work orders from submitted BOMs")
	
	# Generate code
	code = f"WO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
	
	# Build BOM snapshot
	bom_snapshot = _build_bom_snapshot(bom, payload.quantity)
	
	wo = WorkOrder(
		tenant_id=tenant_id,
		code=code,
		name=payload.name or f"WO for {bom.name}",
		product_id=payload.product_id,
		bom_id=payload.bom_id,
		bom_snapshot=bom_snapshot,
		quantity=payload.quantity,
		source_warehouse_id=payload.source_warehouse_id,
		wip_warehouse_id=payload.wip_warehouse_id,
		fg_warehouse_id=payload.fg_warehouse_id,
		transfer_mode=payload.transfer_mode,
		planned_start_date=payload.planned_start_date,
		due_date=payload.due_date,
		status=WorkOrderStatus.DRAFT,
		notes=payload.notes,
	)
	db.add(wo)
	await db.flush()
	
	# Create material lines from BOM snapshot
	for item in bom_snapshot.get("items", []):
		mat_line = WorkOrderMaterialLine(
			tenant_id=tenant_id,
			work_order_id=wo.id,
			item_id=uuid.UUID(item["item_id"]),
			item_code=item["item_code"],
			item_name=item["item_name"],
			required_quantity=Decimal(item["required_quantity"]),
			unit=item["unit"],
			source_warehouse_id=uuid.UUID(item["source_warehouse_id"]) if item.get("source_warehouse_id") else None,
		)
		db.add(mat_line)
	
	await db.flush()
	await db.refresh(wo)
	
	return await get_work_order_by_id(db, tenant_id, wo.id)


async def get_work_order_by_id(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	work_order_id: uuid.UUID,
) -> WorkOrderResponse | None:
	"""Get work order by ID with material lines."""
	stmt = (
		select(WorkOrder)
		.where(
			and_(
				WorkOrder.id == work_order_id,
				WorkOrder.tenant_id == tenant_id,
			)
		)
		.options(selectinload(WorkOrder.material_lines))
	)
	result = await db.execute(stmt)
	wo = result.scalar_one_or_none()
	
	if not wo:
		return None
	
	return WorkOrderResponse(
		id=wo.id,
		tenant_id=wo.tenant_id,
		code=wo.code,
		name=wo.name,
		product_id=wo.product_id,
		bom_id=wo.bom_id,
		bom_snapshot=wo.bom_snapshot,
		quantity=wo.quantity,
		produced_quantity=wo.produced_quantity,
		source_warehouse_id=wo.source_warehouse_id,
		wip_warehouse_id=wo.wip_warehouse_id,
		fg_warehouse_id=wo.fg_warehouse_id,
		status=wo.status,
		transfer_mode=wo.transfer_mode,
		planned_start_date=wo.planned_start_date,
		due_date=wo.due_date,
		started_at=wo.started_at,
		completed_at=wo.completed_at,
		stopped_reason=wo.stopped_reason,
		cancelled_reason=wo.cancelled_reason,
		routing_id=wo.routing_id,
		routing_snapshot=wo.routing_snapshot,
		notes=wo.notes,
		created_at=wo.created_at,
		updated_at=wo.updated_at,
		material_lines=[
			WorkOrderMaterialLineResponse(
				id=ml.id,
				tenant_id=ml.tenant_id,
				work_order_id=ml.work_order_id,
				item_id=ml.item_id,
				item_code=ml.item_code,
				item_name=ml.item_name,
				required_quantity=ml.required_quantity,
				unit=ml.unit,
				source_warehouse_id=ml.source_warehouse_id,
				reserved_quantity=ml.reserved_quantity,
				transferred_quantity=ml.transferred_quantity,
				consumed_quantity=ml.consumed_quantity,
				idx=ml.idx,
				notes=ml.notes,
				created_at=ml.created_at,
			)
			for ml in wo.material_lines
		],
	)


async def list_work_orders(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	status: str | None = None,
	product_id: uuid.UUID | None = None,
	page: int = 1,
	page_size: int = 20,
) -> tuple[list[WorkOrderListResponse], int]:
	"""List work orders with pagination."""
	conditions = [WorkOrder.tenant_id == tenant_id]
	
	if status:
		conditions.append(WorkOrder.status == status)
	if product_id:
		conditions.append(WorkOrder.product_id == product_id)
	
	# Count
	count_stmt = select(func.count(WorkOrder.id)).where(and_(*conditions))
	count_result = await db.execute(count_stmt)
	total = count_result.scalar() or 0
	
	# Query
	stmt = (
		select(WorkOrder)
		.where(and_(*conditions))
		.order_by(WorkOrder.created_at.desc())
		.offset((page - 1) * page_size)
		.limit(page_size)
	)
	result = await db.execute(stmt)
	work_orders = result.scalars().all()
	
	return [
		WorkOrderListResponse(
			id=wo.id,
			tenant_id=wo.tenant_id,
			code=wo.code,
			name=wo.name,
			product_id=wo.product_id,
			bom_id=wo.bom_id,
			quantity=wo.quantity,
			produced_quantity=wo.produced_quantity,
			status=wo.status,
			transfer_mode=wo.transfer_mode,
			planned_start_date=wo.planned_start_date,
			due_date=wo.due_date,
			created_at=wo.created_at,
			updated_at=wo.updated_at,
		)
		for wo in work_orders
	], total


async def transition_work_order_status(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	work_order_id: uuid.UUID,
	payload: WorkOrderStatusTransition,
) -> WorkOrderResponse:
	"""Transition work order to a new status with validation."""
	stmt = (
		select(WorkOrder)
		.where(
			and_(
				WorkOrder.id == work_order_id,
				WorkOrder.tenant_id == tenant_id,
			)
		)
		.options(selectinload(WorkOrder.material_lines))
	)
	result = await db.execute(stmt)
	wo = result.scalar_one_or_none()
	
	if not wo:
		raise ValueError("Work order not found")
	
	current_status = wo.status
	new_status = payload.status
	
	# Valid transitions
	valid_transitions = {
		WorkOrderStatus.DRAFT: [WorkOrderStatus.SUBMITTED, WorkOrderStatus.CANCELLED],
		WorkOrderStatus.SUBMITTED: [WorkOrderStatus.NOT_STARTED, WorkOrderStatus.CANCELLED],
		WorkOrderStatus.NOT_STARTED: [WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.STOPPED, WorkOrderStatus.CANCELLED],
		WorkOrderStatus.IN_PROGRESS: [WorkOrderStatus.COMPLETED, WorkOrderStatus.STOPPED, WorkOrderStatus.CANCELLED],
		WorkOrderStatus.STOPPED: [WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.CANCELLED],
		WorkOrderStatus.COMPLETED: [],
		WorkOrderStatus.CANCELLED: [],
	}
	
	if new_status not in valid_transitions.get(current_status, []):
		raise ValueError(
			f"Invalid status transition from {current_status} to {new_status}"
		)
	
	wo.status = new_status
	
	if new_status == WorkOrderStatus.NOT_STARTED:
		wo.started_at = datetime.utcnow()
	elif new_status == WorkOrderStatus.IN_PROGRESS:
		if not wo.started_at:
			wo.started_at = datetime.utcnow()
	elif new_status == WorkOrderStatus.COMPLETED:
		wo.completed_at = datetime.utcnow()
	elif new_status == WorkOrderStatus.STOPPED:
		wo.stopped_reason = payload.reason
	elif new_status == WorkOrderStatus.CANCELLED:
		wo.cancelled_reason = payload.reason
	
	await db.flush()
	await db.refresh(wo)
	
	return await get_work_order_by_id(db, tenant_id, work_order_id)


async def update_work_order(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	work_order_id: uuid.UUID,
	payload: WorkOrderUpdate,
) -> WorkOrderResponse:
	"""Update a work order."""
	stmt = (
		select(WorkOrder)
		.where(
			and_(
				WorkOrder.id == work_order_id,
				WorkOrder.tenant_id == tenant_id,
			)
		)
		.options(selectinload(WorkOrder.material_lines))
	)
	result = await db.execute(stmt)
	wo = result.scalar_one_or_none()

	if not wo:
		raise ValueError("Work order not found")

	if payload.quantity is not None:
		wo.quantity = payload.quantity
	if payload.source_warehouse_id is not None:
		wo.source_warehouse_id = payload.source_warehouse_id
	if payload.wip_warehouse_id is not None:
		wo.wip_warehouse_id = payload.wip_warehouse_id
	if payload.fg_warehouse_id is not None:
		wo.fg_warehouse_id = payload.fg_warehouse_id
	if payload.transfer_mode is not None:
		wo.transfer_mode = payload.transfer_mode
	if payload.planned_start_date is not None:
		wo.planned_start_date = payload.planned_start_date
	if payload.due_date is not None:
		wo.due_date = payload.due_date
	if payload.notes is not None:
		wo.notes = payload.notes

	await db.flush()
	return await get_work_order_by_id(db, tenant_id, work_order_id)


async def complete_work_order(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	work_order_id: uuid.UUID,
	payload: WorkOrderComplete,
) -> WorkOrderResponse:
	"""Complete a work order with produced quantity."""
	stmt = (
		select(WorkOrder)
		.where(
			and_(
				WorkOrder.id == work_order_id,
				WorkOrder.tenant_id == tenant_id,
			)
		)
		.options(selectinload(WorkOrder.material_lines))
	)
	result = await db.execute(stmt)
	wo = result.scalar_one_or_none()
	
	if not wo:
		raise ValueError("Work order not found")
	
	if wo.status not in [WorkOrderStatus.NOT_STARTED, WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.SUBMITTED]:
		raise ValueError(f"Cannot complete work order in status: {wo.status}")
	
	if payload.produced_quantity > wo.quantity:
		raise ValueError(
			f"Produced quantity ({payload.produced_quantity}) cannot exceed "
			f"order quantity ({wo.quantity})"
		)
	
	wo.produced_quantity = payload.produced_quantity
	wo.status = WorkOrderStatus.COMPLETED
	wo.completed_at = datetime.utcnow()
	
	if payload.notes:
		wo.notes = (wo.notes or "") + f"\nCompletion notes: {payload.notes}"
	
	await db.flush()
	await db.refresh(wo)
	
	return await get_work_order_by_id(db, tenant_id, work_order_id)


async def reserve_work_order_materials(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	work_order_id: uuid.UUID,
	payload: WorkOrderTransfer,
) -> WorkOrderResponse:
	"""Reserve or release materials for a work order."""
	stmt = (
		select(WorkOrder)
		.where(
			and_(
				WorkOrder.id == work_order_id,
				WorkOrder.tenant_id == tenant_id,
			)
		)
		.options(selectinload(WorkOrder.material_lines))
	)
	result = await db.execute(stmt)
	wo = result.scalar_one_or_none()
	
	if not wo:
		raise ValueError("Work order not found")
	
	if wo.status not in [WorkOrderStatus.SUBMITTED, WorkOrderStatus.NOT_STARTED, WorkOrderStatus.IN_PROGRESS]:
		raise ValueError(f"Cannot reserve materials for work order in status: {wo.status}")
	
	shortages = []
	
	for line in wo.material_lines:
		if payload.material_line_ids and line.id not in payload.material_line_ids:
			continue
		
		# Check stock availability
		stock_stmt = select(InventoryStock).where(
			and_(
				InventoryStock.tenant_id == tenant_id,
				InventoryStock.product_id == line.item_id,
				InventoryStock.warehouse_id == line.source_warehouse_id,
			)
		)
		stock_result = await db.execute(stock_stmt)
		stock = stock_result.scalar_one_or_none()
		
		if payload.action == "reserve":
			if stock and stock.quantity >= line.required_quantity:
				line.reserved_quantity = line.required_quantity
			else:
				available = stock.quantity if stock else 0
				shortages.append({
					"item_code": line.item_code,
					"item_name": line.item_name,
					"required": float(line.required_quantity),
					"available": float(available),
					"shortage": float(line.required_quantity - available),
				})
		elif payload.action == "release":
			line.reserved_quantity = Decimal("0")
	
	await db.flush()
	
	if shortages and payload.action == "reserve":
		raise ValueError(f"Material shortages: {shortages}")
	
	return await get_work_order_by_id(db, tenant_id, work_order_id)


async def transfer_work_order_materials(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	work_order_id: uuid.UUID,
	payload: WorkOrderTransfer,
) -> WorkOrderResponse:
	"""Transfer materials for a work order (manufacture flow)."""
	stmt = (
		select(WorkOrder)
		.where(
			and_(
				WorkOrder.id == work_order_id,
				WorkOrder.tenant_id == tenant_id,
			)
		)
		.options(selectinload(WorkOrder.material_lines))
	)
	result = await db.execute(stmt)
	wo = result.scalar_one_or_none()
	
	if not wo:
		raise ValueError("Work order not found")
	
	if wo.status not in [WorkOrderStatus.IN_PROGRESS]:
		raise ValueError(f"Cannot transfer materials for work order in status: {wo.status}")
	
	if not wo.wip_warehouse_id:
		raise ValueError("WIP warehouse is required for material transfer")
	
	for line in wo.material_lines:
		if payload.material_line_ids and line.id not in payload.material_line_ids:
			continue
		
		transfer_qty = payload.quantity_by_line.get(line.id, line.required_quantity - line.transferred_quantity)
		
		if transfer_qty > line.required_quantity - line.transferred_quantity:
			transfer_qty = line.required_quantity - line.transferred_quantity
		
		if transfer_qty > 0:
			line.transferred_quantity += transfer_qty
			line.consumed_quantity += transfer_qty
	
	await db.flush()
	return await get_work_order_by_id(db, tenant_id, work_order_id)


# ============================================================================
# Workstation Services
# ============================================================================


async def create_workstation(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	payload: WorkstationCreate,
) -> WorkstationResponse:
	"""Create a new workstation."""
	ws = Workstation(
		tenant_id=tenant_id,
		code=payload.code,
		name=payload.name,
		description=payload.description,
		hourly_cost=payload.hourly_cost,
		capacity=payload.capacity,
		status=WorkstationStatus.ACTIVE,
	)
	db.add(ws)
	await db.flush()
	
	for hour in payload.hours:
		wh = WorkstationWorkingHour(
			workstation_id=ws.id,
			day_of_week=hour.day_of_week,
			start_time=hour.start_time,
			end_time=hour.end_time,
		)
		db.add(wh)
	
	await db.flush()
	await db.refresh(ws)
	return await get_workstation_by_id(db, tenant_id, ws.id)


async def get_workstation_by_id(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	workstation_id: uuid.UUID,
) -> WorkstationResponse | None:
	stmt = (
		select(Workstation)
		.where(
			and_(
				Workstation.id == workstation_id,
				Workstation.tenant_id == tenant_id,
			)
		)
		.options(selectinload(Workstation.hours))
	)
	result = await db.execute(stmt)
	ws = result.scalar_one_or_none()
	
	if not ws:
		return None
	
	return WorkstationResponse(
		id=ws.id,
		tenant_id=ws.tenant_id,
		code=ws.code,
		name=ws.name,
		description=ws.description,
		status=ws.status,
		hourly_cost=ws.hourly_cost,
		capacity=ws.capacity,
		disabled=ws.disabled,
		created_at=ws.created_at,
		updated_at=ws.updated_at,
		hours=[
			{
				"day_of_week": h.day_of_week,
				"start_time": h.start_time,
				"end_time": h.end_time,
			}
			for h in ws.hours
		],
	)


async def list_workstations(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	status: str | None = None,
	page: int = 1,
	page_size: int = 20,
) -> tuple[list[WorkstationListResponse], int]:
	conditions = [Workstation.tenant_id == tenant_id]
	if status:
		conditions.append(Workstation.status == status)
	
	count_stmt = select(func.count(Workstation.id)).where(and_(*conditions))
	count_result = await db.execute(count_stmt)
	total = count_result.scalar() or 0
	
	stmt = (
		select(Workstation)
		.where(and_(*conditions))
		.order_by(Workstation.created_at.desc())
		.offset((page - 1) * page_size)
		.limit(page_size)
	)
	result = await db.execute(stmt)
	workstations = result.scalars().all()
	
	return [
		WorkstationListResponse(
			id=ws.id,
			tenant_id=ws.tenant_id,
			code=ws.code,
			name=ws.name,
			status=ws.status,
			hourly_cost=ws.hourly_cost,
			capacity=ws.capacity,
			disabled=ws.disabled,
			created_at=ws.created_at,
			updated_at=ws.updated_at,
		)
		for ws in workstations
	], total


async def update_workstation(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	workstation_id: uuid.UUID,
	payload: WorkstationUpdate,
) -> WorkstationResponse:
	stmt = (
		select(Workstation)
		.where(
			and_(
				Workstation.id == workstation_id,
				Workstation.tenant_id == tenant_id,
			)
		)
		.options(selectinload(Workstation.hours))
	)
	result = await db.execute(stmt)
	ws = result.scalar_one_or_none()
	
	if not ws:
		raise ValueError("Workstation not found")
	
	if payload.name is not None:
		ws.name = payload.name
	if payload.description is not None:
		ws.description = payload.description
	if payload.hourly_cost is not None:
		ws.hourly_cost = payload.hourly_cost
	if payload.capacity is not None:
		ws.capacity = payload.capacity
	if payload.disabled is not None:
		ws.disabled = payload.disabled
		ws.status = WorkstationStatus.DISABLED if payload.disabled else WorkstationStatus.ACTIVE
	
	if payload.hours is not None:
		for h in ws.hours:
			await db.delete(h)
		for hour in payload.hours:
			wh = WorkstationWorkingHour(
				workstation_id=ws.id,
				day_of_week=hour.day_of_week,
				start_time=hour.start_time,
				end_time=hour.end_time,
			)
			db.add(wh)
	
	await db.flush()
	return await get_workstation_by_id(db, tenant_id, workstation_id)


# ============================================================================
# Routing Services
# ============================================================================


async def create_routing(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	payload: RoutingCreate,
) -> RoutingResponse:
	"""Create a new routing."""
	routing = Routing(
		tenant_id=tenant_id,
		code=payload.code,
		name=payload.name,
		description=payload.description,
		status=RoutingStatus.DRAFT,
	)
	db.add(routing)
	await db.flush()
	
	for op in payload.operations:
		operation = RoutingOperation(
			tenant_id=tenant_id,
			routing_id=routing.id,
			operation_name=op.operation_name,
			workstation_id=op.workstation_id,
			sequence=op.sequence,
			setup_minutes=op.setup_minutes,
			fixed_run_minutes=op.fixed_run_minutes,
			variable_run_minutes_per_unit=op.variable_run_minutes_per_unit,
			batch_size=op.batch_size,
			overlap_lag_minutes=op.overlap_lag_minutes,
			idx=op.idx,
			notes=op.notes,
		)
		db.add(operation)
	
	await db.flush()
	await db.refresh(routing)
	return await get_routing_by_id(db, tenant_id, routing.id)


async def get_routing_by_id(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	routing_id: uuid.UUID,
) -> RoutingResponse | None:
	stmt = (
		select(Routing)
		.where(
			and_(
				Routing.id == routing_id,
				Routing.tenant_id == tenant_id,
			)
		)
		.options(selectinload(Routing.operations))
	)
	result = await db.execute(stmt)
	routing = result.scalar_one_or_none()
	
	if not routing:
		return None
	
	return RoutingResponse(
		id=routing.id,
		tenant_id=routing.tenant_id,
		code=routing.code,
		name=routing.name,
		description=routing.description,
		status=routing.status,
		disabled=routing.disabled,
		created_at=routing.created_at,
		updated_at=routing.updated_at,
		operations=[
			{
				"id": op.id,
				"tenant_id": op.tenant_id,
				"routing_id": op.routing_id,
				"operation_name": op.operation_name,
				"workstation_id": op.workstation_id,
				"sequence": op.sequence,
				"setup_minutes": op.setup_minutes,
				"fixed_run_minutes": op.fixed_run_minutes,
				"variable_run_minutes_per_unit": op.variable_run_minutes_per_unit,
				"batch_size": op.batch_size,
				"overlap_lag_minutes": op.overlap_lag_minutes,
				"idx": op.idx,
				"notes": op.notes,
				"created_at": op.created_at,
			}
			for op in sorted(routing.operations, key=lambda x: x.sequence)
		],
	)


async def list_routings(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	status: str | None = None,
	page: int = 1,
	page_size: int = 20,
) -> tuple[list[RoutingListResponse], int]:
	conditions = [Routing.tenant_id == tenant_id]
	if status:
		conditions.append(Routing.status == status)
	
	count_stmt = select(func.count(Routing.id)).where(and_(*conditions))
	count_result = await db.execute(count_stmt)
	total = count_result.scalar() or 0
	
	stmt = (
		select(Routing)
		.where(and_(*conditions))
		.options(selectinload(Routing.operations))
		.order_by(Routing.created_at.desc())
		.offset((page - 1) * page_size)
		.limit(page_size)
	)
	result = await db.execute(stmt)
	routings = result.scalars().all()
	
	return [
		RoutingListResponse(
			id=r.id,
			tenant_id=r.tenant_id,
			code=r.code,
			name=r.name,
			status=r.status,
			disabled=r.disabled,
			operation_count=len(r.operations),
			created_at=r.created_at,
			updated_at=r.updated_at,
		)
		for r in routings
	], total


async def update_routing(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	routing_id: uuid.UUID,
	payload: RoutingUpdate,
) -> RoutingResponse:
	stmt = (
		select(Routing)
		.where(
			and_(
				Routing.id == routing_id,
				Routing.tenant_id == tenant_id,
			)
		)
		.options(selectinload(Routing.operations))
	)
	result = await db.execute(stmt)
	routing = result.scalar_one_or_none()
	
	if not routing:
		raise ValueError("Routing not found")
	
	if payload.name is not None:
		routing.name = payload.name
	if payload.description is not None:
		routing.description = payload.description
	if payload.disabled is not None:
		routing.disabled = payload.disabled
	
	if payload.operations is not None:
		for op in routing.operations:
			await db.delete(op)
		for op in payload.operations:
			operation = RoutingOperation(
				tenant_id=tenant_id,
				routing_id=routing.id,
				operation_name=op.operation_name,
				workstation_id=op.workstation_id,
				sequence=op.sequence,
				setup_minutes=op.setup_minutes,
				fixed_run_minutes=op.fixed_run_minutes,
				variable_run_minutes_per_unit=op.variable_run_minutes_per_unit,
				batch_size=op.batch_size,
				overlap_lag_minutes=op.overlap_lag_minutes,
				idx=op.idx,
				notes=op.notes,
			)
			db.add(operation)
	
	await db.flush()
	return await get_routing_by_id(db, tenant_id, routing_id)


def calculate_routing_cost_and_time(
	routing: RoutingResponse,
	quantity: Decimal,
) -> dict[str, Any]:
	"""Calculate total planned time and cost for a routing."""
	total_minutes = 0
	total_cost = Decimal("0")
	
	workstations = {}  # Cache workstation costs
	
	for op in routing.operations:
		# Get workstation cost
		ws_cost = workstations.get(op.workstation_id, Decimal("0"))
		if op.workstation_id:
			workstations[op.workstation_id] = ws_cost
		
		# Calculate operation time
		setup = op.setup_minutes
		fixed_run = op.fixed_run_minutes
		variable_run = int(op.variable_run_minutes_per_unit * quantity)
		
		op_minutes = setup + fixed_run + variable_run
		total_minutes += op_minutes
		
		# Calculate cost
		op_cost = (Decimal(op_minutes) / 60) * ws_cost
		total_cost += op_cost
	
	return {
		"total_minutes": total_minutes,
		"total_hours": total_minutes / 60,
		"total_cost": total_cost,
		"operation_count": len(routing.operations),
	}


# ============================================================================
# Production Planning Services
# ============================================================================


async def generate_proposals(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	payload: ProposalGenerateRequest,
) -> list[ManufacturingProposalResponse]:
	"""Generate manufacturing proposals from demand signals."""
	proposals = []
	
	# Get products with active BOMs
	bom_stmt = (
		select(BillOfMaterials)
		.where(
			and_(
				BillOfMaterials.tenant_id == tenant_id,
				BillOfMaterials.status == "submitted",
				BillOfMaterials.is_active == True,  # noqa: E712
			)
		)
		.options(selectinload(BillOfMaterials.items))
	)
	bom_result = await db.execute(bom_stmt)
	active_boms = {bom.product_id: bom for bom in bom_result.scalars().all()}
	
	# Filter by product_ids if provided
	if payload and payload.product_ids:
		active_boms = {k: v for k, v in active_boms.items() if k in payload.product_ids}
	
	for product_id, bom in active_boms.items():
		# Get open sales order demand for this product
		demand_stmt = (
			select(
				SalesOrderLine.product_id,
				func.sum(SalesOrderLine.quantity - SalesOrderLine.delivered_quantity).label("demand"),
			)
			.join(SalesOrder, SalesOrderLine.order_id == SalesOrder.id)
			.where(
				and_(
					SalesOrder.tenant_id == tenant_id,
					SalesOrderLine.product_id == product_id,
					SalesOrder.status == "confirmed",
					SalesOrderLine.quantity - SalesOrderLine.delivered_quantity > 0,
				)
			)
			.group_by(SalesOrderLine.product_id)
		)
		demand_result = await db.execute(demand_stmt)
		demand_row = demand_result.one_or_none()
		demand_qty = demand_row.demand if demand_row else Decimal("0")
		
		if demand_qty <= 0:
			continue
		
		# Get current stock
		stock_stmt = select(func.sum(InventoryStock.quantity)).where(
			and_(
				InventoryStock.tenant_id == tenant_id,
				InventoryStock.product_id == product_id,
			)
		)
		stock_result = await db.execute(stock_stmt)
		current_stock = stock_result.scalar() or 0
		
		# Get open work order supply
		wo_stmt = select(func.sum(WorkOrder.quantity - WorkOrder.produced_quantity)).where(
			and_(
				WorkOrder.tenant_id == tenant_id,
				WorkOrder.product_id == product_id,
				WorkOrder.status.in_([
					WorkOrderStatus.SUBMITTED,
					WorkOrderStatus.NOT_STARTED,
					WorkOrderStatus.IN_PROGRESS,
				]),
			)
		)
		wo_result = await db.execute(wo_stmt)
		open_wo_qty = wo_result.scalar() or 0
		
		available_qty = current_stock + open_wo_qty
		proposed_qty = max(Decimal("0"), demand_qty - available_qty)
		
		# Check material availability
		shortages = []
		for item in bom.items:
			item_demand = proposed_qty * item.required_quantity / bom.bom_quantity
			item_stock_stmt = select(func.sum(InventoryStock.quantity)).where(
				and_(
					InventoryStock.tenant_id == tenant_id,
					InventoryStock.product_id == item.item_id,
					InventoryStock.warehouse_id == item.source_warehouse_id if item.source_warehouse_id else True,
				)
			)
			item_stock_result = await db.execute(item_stock_stmt)
			item_stock = item_stock_result.scalar() or 0
			
			if item_stock < item_demand:
				shortages.append({
					"item_code": item.item_code,
					"item_name": item.item_name,
					"required": float(item_demand),
					"available": float(item_stock),
					"shortage": float(item_demand - item_stock),
				})
		
		proposal = ManufacturingProposal(
			tenant_id=tenant_id,
			product_id=product_id,
			bom_id=bom.id,
			demand_source="sales_order",
			demand_quantity=demand_qty,
			proposed_quantity=proposed_qty,
			available_quantity=available_qty,
			status=ManufacturingProposalStatus.PROPOSED,
			shortages=shortages if shortages else None,
		)
		db.add(proposal)
		proposals.append(proposal)
	
	await db.flush()
	
	return [
		ManufacturingProposalResponse(
			id=p.id,
			tenant_id=p.tenant_id,
			product_id=p.product_id,
			bom_id=p.bom_id,
			demand_source=p.demand_source,
			demand_source_id=p.demand_source_id,
			demand_quantity=p.demand_quantity,
			proposed_quantity=p.proposed_quantity,
			available_quantity=p.available_quantity,
			status=p.status,
			decision=p.decision,
			decision_reason=p.decision_reason,
			decided_by=p.decided_by,
			decided_at=p.decided_at,
			work_order_id=p.work_order_id,
			shortages=p.shortages,
			notes=p.notes,
			created_at=p.created_at,
			updated_at=p.updated_at,
		)
		for p in proposals
	]


async def list_proposals(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	status: str | None = None,
	product_id: uuid.UUID | None = None,
	page: int = 1,
	page_size: int = 20,
) -> tuple[list[ManufacturingProposalResponse], int]:
	conditions = [ManufacturingProposal.tenant_id == tenant_id]
	if status:
		conditions.append(ManufacturingProposal.status == status)
	if product_id:
		conditions.append(ManufacturingProposal.product_id == product_id)
	
	count_stmt = select(func.count(ManufacturingProposal.id)).where(and_(*conditions))
	count_result = await db.execute(count_stmt)
	total = count_result.scalar() or 0
	
	stmt = (
		select(ManufacturingProposal)
		.where(and_(*conditions))
		.order_by(ManufacturingProposal.created_at.desc())
		.offset((page - 1) * page_size)
		.limit(page_size)
	)
	result = await db.execute(stmt)
	proposals = result.scalars().all()
	
	return [
		ManufacturingProposalResponse(
			id=p.id,
			tenant_id=p.tenant_id,
			product_id=p.product_id,
			bom_id=p.bom_id,
			demand_source=p.demand_source,
			demand_source_id=p.demand_source_id,
			demand_quantity=p.demand_quantity,
			proposed_quantity=p.proposed_quantity,
			available_quantity=p.available_quantity,
			status=p.status,
			decision=p.decision,
			decision_reason=p.decision_reason,
			decided_by=p.decided_by,
			decided_at=p.decided_at,
			work_order_id=p.work_order_id,
			shortages=p.shortages,
			notes=p.notes,
			created_at=p.created_at,
			updated_at=p.updated_at,
		)
		for p in proposals
	], total


async def decide_proposal(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	user_id: uuid.UUID,
	proposal_id: uuid.UUID,
	payload: ProposalDecision,
) -> ManufacturingProposalResponse | None:
	"""Accept or reject a manufacturing proposal."""
	stmt = select(ManufacturingProposal).where(
		and_(
			ManufacturingProposal.id == proposal_id,
			ManufacturingProposal.tenant_id == tenant_id,
		)
	)
	result = await db.execute(stmt)
	proposal = result.scalar_one_or_none()
	
	if not proposal:
		return None
	
	proposal.decision = payload.decision
	proposal.decision_reason = payload.reason
	proposal.decided_by = user_id
	proposal.decided_at = datetime.utcnow()
	
	if payload.decision == "accept":
		proposal.status = ManufacturingProposalStatus.ACCEPTED
		
		# Create work order
		wo_payload = WorkOrderCreate(
			product_id=proposal.product_id,
			bom_id=proposal.bom_id,
			quantity=payload.proposed_quantity or proposal.proposed_quantity,
		)
		wo = await create_work_order(db, tenant_id, user_id, wo_payload)
		proposal.work_order_id = wo.id
	else:
		proposal.status = ManufacturingProposalStatus.REJECTED
	
	await db.flush()
	await db.refresh(proposal)
	
	return ManufacturingProposalResponse(
		id=proposal.id,
		tenant_id=proposal.tenant_id,
		product_id=proposal.product_id,
		bom_id=proposal.bom_id,
		demand_source=proposal.demand_source,
		demand_source_id=proposal.demand_source_id,
		demand_quantity=proposal.demand_quantity,
		proposed_quantity=proposal.proposed_quantity,
		available_quantity=proposal.available_quantity,
		status=proposal.status,
		decision=proposal.decision,
		decision_reason=proposal.decision_reason,
		decided_by=proposal.decided_by,
		decided_at=proposal.decided_at,
		work_order_id=proposal.work_order_id,
		shortages=proposal.shortages,
		notes=proposal.notes,
		created_at=proposal.created_at,
		updated_at=proposal.updated_at,
	)


# ============================================================================
# Production Plan Services
# ============================================================================


async def create_production_plan(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	user_id: uuid.UUID | None,
	payload: ProductionPlanCreate,
) -> ProductionPlanResponse:
	"""Create a production plan."""
	code = f"PP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
	
	plan = ProductionPlan(
		tenant_id=tenant_id,
		code=code,
		name=payload.name,
		planning_strategy=payload.planning_strategy,
		start_date=payload.start_date,
		end_date=payload.end_date,
		status=ProductionPlanStatus.DRAFT,
		notes=payload.notes,
	)
	db.add(plan)
	await db.flush()
	
	for i, line in enumerate(payload.lines):
		plan_line = ProductionPlanLine(
			tenant_id=tenant_id,
			plan_id=plan.id,
			product_id=line.product_id,
			bom_id=line.bom_id,
			routing_id=line.routing_id,
			forecast_demand=line.forecast_demand,
			proposed_qty=line.proposed_qty,
			idx=line.idx if line.idx else i,
			notes=line.notes,
		)
		db.add(plan_line)
	
	await db.flush()
	return await get_production_plan_by_id(db, tenant_id, plan.id)


async def get_production_plan_by_id(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	plan_id: uuid.UUID,
) -> ProductionPlanResponse | None:
	stmt = (
		select(ProductionPlan)
		.where(
			and_(
				ProductionPlan.id == plan_id,
				ProductionPlan.tenant_id == tenant_id,
			)
		)
		.options(selectinload(ProductionPlan.lines))
	)
	result = await db.execute(stmt)
	plan = result.scalar_one_or_none()
	
	if not plan:
		return None
	
	return ProductionPlanResponse(
		id=plan.id,
		tenant_id=plan.tenant_id,
		code=plan.code,
		name=plan.name,
		status=plan.status,
		planning_strategy=plan.planning_strategy,
		start_date=plan.start_date,
		end_date=plan.end_date,
		firmed_at=plan.firmed_at,
		firmed_by=plan.firmed_by,
		notes=plan.notes,
		created_at=plan.created_at,
		updated_at=plan.updated_at,
		lines=[
			ProductionPlanLineResponse(
				id=line.id,
				tenant_id=line.tenant_id,
				plan_id=line.plan_id,
				product_id=line.product_id,
				bom_id=line.bom_id,
				routing_id=line.routing_id,
				sales_order_demand=line.sales_order_demand,
				forecast_demand=line.forecast_demand,
				total_demand=line.total_demand,
				open_work_order_qty=line.open_work_order_qty,
				available_stock=line.available_stock,
				proposed_qty=line.proposed_qty,
				firmed_qty=line.firmed_qty,
				completed_qty=line.completed_qty,
				shortage_summary=line.shortage_summary,
				capacity_summary=line.capacity_summary,
				idx=line.idx,
				notes=line.notes,
				created_at=line.created_at,
			)
			for line in plan.lines
		],
	)


async def list_production_plans(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	status: str | None = None,
	page: int = 1,
	page_size: int = 20,
) -> tuple[list[ProductionPlanListResponse], int]:
	conditions = [ProductionPlan.tenant_id == tenant_id]
	if status:
		conditions.append(ProductionPlan.status == status)
	
	count_stmt = select(func.count(ProductionPlan.id)).where(and_(*conditions))
	count_result = await db.execute(count_stmt)
	total = count_result.scalar() or 0
	
	stmt = (
		select(ProductionPlan)
		.where(and_(*conditions))
		.options(selectinload(ProductionPlan.lines))
		.order_by(ProductionPlan.created_at.desc())
		.offset((page - 1) * page_size)
		.limit(page_size)
	)
	result = await db.execute(stmt)
	plans = result.scalars().all()
	
	return [
		ProductionPlanListResponse(
			id=p.id,
			tenant_id=p.tenant_id,
			code=p.code,
			name=p.name,
			status=p.status,
			planning_strategy=p.planning_strategy,
			start_date=p.start_date,
			end_date=p.end_date,
			line_count=len(p.lines),
			firmed_at=p.firmed_at,
			created_at=p.created_at,
			updated_at=p.updated_at,
		)
		for p in plans
	], total


async def firm_production_plan(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	user_id: uuid.UUID,
	plan_id: uuid.UUID,
	payload: ProductionPlanFirm,
) -> ProductionPlanResponse:
	"""Firm up a production plan, creating work orders from proposals."""
	stmt = (
		select(ProductionPlan)
		.where(
			and_(
				ProductionPlan.id == plan_id,
				ProductionPlan.tenant_id == tenant_id,
			)
		)
		.options(selectinload(ProductionPlan.lines))
	)
	result = await db.execute(stmt)
	plan = result.scalar_one_or_none()
	
	if not plan:
		raise ValueError("Production plan not found")
	
	if plan.status not in [ProductionPlanStatus.DRAFT, ProductionPlanStatus.REVIEWED]:
		raise ValueError(f"Cannot firm production plan in status: {plan.status}")
	
	plan.status = ProductionPlanStatus.FIRMED
	plan.firmed_at = datetime.utcnow()
	plan.firmed_by = user_id
	
	# Create work orders from plan lines
	for line in plan.lines:
		if payload.line_ids and line.id not in payload.line_ids:
			continue
		
		if line.proposed_qty > 0 and line.bom_id:
			wo_payload = WorkOrderCreate(
				product_id=line.product_id,
				bom_id=line.bom_id,
				quantity=line.proposed_qty,
			)
			wo = await create_work_order(db, tenant_id, user_id, wo_payload)
			line.firmed_qty = line.proposed_qty
	
	await db.flush()
	return await get_production_plan_by_id(db, tenant_id, plan_id)


# ============================================================================
# Downtime and OEE Services
# ============================================================================


async def create_downtime(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	user_id: uuid.UUID | None,
	payload: DowntimeCreate,
) -> DowntimeResponse:
	"""Create a downtime entry."""
	duration = None
	if payload.end_time:
		duration = int((payload.end_time - payload.start_time).total_seconds() / 60)
	
	entry = DowntimeEntry(
		tenant_id=tenant_id,
		workstation_id=payload.workstation_id,
		work_order_id=payload.work_order_id,
		reason=payload.reason,
		start_time=payload.start_time,
		end_time=payload.end_time,
		duration_minutes=duration,
		remarks=payload.remarks,
		reporter_id=user_id,
	)
	db.add(entry)
	await db.flush()
	await db.refresh(entry)
	
	return DowntimeResponse(
		id=entry.id,
		tenant_id=entry.tenant_id,
		workstation_id=entry.workstation_id,
		work_order_id=entry.work_order_id,
		reason=entry.reason,
		start_time=entry.start_time,
		end_time=entry.end_time,
		duration_minutes=entry.duration_minutes,
		remarks=entry.remarks,
		reporter_id=entry.reporter_id,
		created_at=entry.created_at,
		updated_at=entry.updated_at,
	)


async def list_downtime(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	workstation_id: uuid.UUID | None = None,
	start_date: datetime | None = None,
	end_date: datetime | None = None,
	reason: str | None = None,
	page: int = 1,
	page_size: int = 50,
) -> tuple[list[DowntimeResponse], int]:
	conditions = [DowntimeEntry.tenant_id == tenant_id]
	
	if workstation_id:
		conditions.append(DowntimeEntry.workstation_id == workstation_id)
	if start_date:
		conditions.append(DowntimeEntry.start_time >= start_date)
	if end_date:
		conditions.append(DowntimeEntry.start_time <= end_date)
	if reason:
		conditions.append(DowntimeEntry.reason == reason)
	
	count_stmt = select(func.count(DowntimeEntry.id)).where(and_(*conditions))
	count_result = await db.execute(count_stmt)
	total = count_result.scalar() or 0
	
	stmt = (
		select(DowntimeEntry)
		.where(and_(*conditions))
		.order_by(DowntimeEntry.start_time.desc())
		.offset((page - 1) * page_size)
		.limit(page_size)
	)
	result = await db.execute(stmt)
	entries = result.scalars().all()
	
	return [
		DowntimeResponse(
			id=e.id,
			tenant_id=e.tenant_id,
			workstation_id=e.workstation_id,
			work_order_id=e.work_order_id,
			reason=e.reason,
			start_time=e.start_time,
			end_time=e.end_time,
			duration_minutes=e.duration_minutes,
			remarks=e.remarks,
			reporter_id=e.reporter_id,
			created_at=e.created_at,
			updated_at=e.updated_at,
		)
		for e in entries
	], total


async def get_downtime_pareto(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	workstation_id: uuid.UUID | None = None,
	start_date: datetime | None = None,
	end_date: datetime | None = None,
) -> list[DowntimeParetoResponse]:
	"""Get downtime Pareto analysis by reason."""
	conditions = [DowntimeEntry.tenant_id == tenant_id]
	
	if workstation_id:
		conditions.append(DowntimeEntry.workstation_id == workstation_id)
	if start_date:
		conditions.append(DowntimeEntry.start_time >= start_date)
	if end_date:
		conditions.append(DowntimeEntry.start_time <= end_date)
	
	stmt = (
		select(
			DowntimeEntry.reason,
			func.count(DowntimeEntry.id).label("frequency"),
			func.sum(DowntimeEntry.duration_minutes).label("total_duration"),
		)
		.where(and_(*conditions))
		.group_by(DowntimeEntry.reason)
		.order_by(func.sum(DowntimeEntry.duration_minutes).desc())
	)
	result = await db.execute(stmt)
	rows = result.all()
	
	total_duration = sum(r.total_duration or 0 for r in rows)
	
	return [
		DowntimeParetoResponse(
			reason=r.reason,
			frequency=r.frequency,
			total_duration_minutes=r.total_duration or 0,
			percentage=round((r.total_duration or 0) / total_duration * 100, 2) if total_duration > 0 else 0,
		)
		for r in rows
	]


async def create_oee_record(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	payload: OeeRecordCreate,
) -> OeeRecordResponse:
	"""Create an OEE record with calculated factors."""
	run_time = payload.planned_production_time - payload.stop_time
	
	# Calculate OEE factors
	availability = run_time / payload.planned_production_time if payload.planned_production_time > 0 else 0
	
	ideal_total_time = payload.ideal_cycle_time * payload.total_count if payload.total_count > 0 else 0
	performance = ideal_total_time / run_time if run_time > 0 else 0
	
	quality = payload.good_count / payload.total_count if payload.total_count > 0 else 0
	
	oee = availability * performance * quality
	
	record = OeeRecord(
		tenant_id=tenant_id,
		workstation_id=payload.workstation_id,
		work_order_id=payload.work_order_id,
		record_date=payload.record_date,
		planned_production_time=payload.planned_production_time,
		stop_time=payload.stop_time,
		run_time=run_time,
		ideal_cycle_time=payload.ideal_cycle_time,
		total_count=payload.total_count,
		good_count=payload.good_count,
		reject_count=payload.reject_count,
		availability=availability,
		performance=performance,
		quality=quality,
		oee=oee,
	)
	db.add(record)
	await db.flush()
	await db.refresh(record)
	
	return OeeRecordResponse(
		id=record.id,
		tenant_id=record.tenant_id,
		workstation_id=record.workstation_id,
		work_order_id=record.work_order_id,
		record_date=record.record_date,
		planned_production_time=record.planned_production_time,
		stop_time=record.stop_time,
		run_time=record.run_time,
		ideal_cycle_time=record.ideal_cycle_time,
		total_count=record.total_count,
		good_count=record.good_count,
		reject_count=record.reject_count,
		availability=record.availability,
		performance=record.performance,
		quality=record.quality,
		oee=record.oee,
		created_at=record.created_at,
	)


async def get_oee_dashboard(
	db: AsyncSession,
	tenant_id: uuid.UUID,
	workstation_id: uuid.UUID | None = None,
	start_date: datetime | None = None,
	end_date: datetime | None = None,
) -> OeeDashboardResponse:
	"""Get OEE dashboard data with trend and Pareto."""
	if not end_date:
		end_date = datetime.utcnow()
	if not start_date:
		start_date = end_date - timedelta(days=30)
	
	conditions = [OeeRecord.tenant_id == tenant_id]
	
	if workstation_id:
		conditions.append(OeeRecord.workstation_id == workstation_id)
	conditions.append(OeeRecord.record_date >= start_date)
	conditions.append(OeeRecord.record_date <= end_date)
	
	stmt = (
		select(OeeRecord)
		.where(and_(*conditions))
		.order_by(OeeRecord.record_date.desc())
	)
	result = await db.execute(stmt)
	records = result.scalars().all()
	
	# Calculate current OEE (most recent)
	current_oee = 0
	current_availability = 0
	current_performance = 0
	current_quality = 0
	
	if records:
		latest = records[0]
		current_oee = latest.oee
		current_availability = latest.availability
		current_performance = latest.performance
		current_quality = latest.quality
	
	# Get trend data
	trend_data = [
		OeeRecordResponse(
			id=r.id,
			tenant_id=r.tenant_id,
			workstation_id=r.workstation_id,
			work_order_id=r.work_order_id,
			record_date=r.record_date,
			planned_production_time=r.planned_production_time,
			stop_time=r.stop_time,
			run_time=r.run_time,
			ideal_cycle_time=r.ideal_cycle_time,
			total_count=r.total_count,
			good_count=r.good_count,
			reject_count=r.reject_count,
			availability=r.availability,
			performance=r.performance,
			quality=r.quality,
			oee=r.oee,
			created_at=r.created_at,
		)
		for r in records[:30]
	]
	
	# Get downtime Pareto
	downtime_pareto = await get_downtime_pareto(
		db, tenant_id, workstation_id, start_date, end_date
	)
	
	return OeeDashboardResponse(
		workstation_id=workstation_id,
		current_oee=current_oee,
		availability=current_availability,
		performance=current_performance,
		quality=current_quality,
		trend_data=trend_data,
		downtime_pareto=[p.model_dump() for p in downtime_pareto],
		period_start=start_date,
		period_end=end_date,
	)
