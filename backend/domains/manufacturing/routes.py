"""Manufacturing domain routes - BOM, Work Orders, Routing, Workstations, Production Planning, and OEE."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from . import schemas as mschemas
from . import service as mservice
from common.auth import get_user_id_from_request
from common.database import get_db

router = APIRouter(prefix="/manufacturing", tags=["manufacturing"])


# ============================================================================
# BOM Routes
# ============================================================================


@router.post("/boms", response_model=mschemas.BomResponse, status_code=201)
async def create_bom(
	payload: mschemas.BomCreate,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Create a new BOM in draft status."""
	try:
		# Get tenant_id from user context
		from common.auth import get_tenant_id_from_request
		tenant_id = await get_tenant_id_from_request(user_id)
		return await mservice.create_bom(db, tenant_id, user_id, payload)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.get("/boms", response_model=dict[str, Any])
async def list_boms(
	product_id: UUID | None = None,
	status: str | None = None,
	is_active: bool | None = None,
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""List BOMs with pagination and filters."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	boms, total = await mservice.list_boms(
		db, tenant_id, product_id, status, is_active, page, page_size,
	)
	return {"items": boms, "total": total, "page": page, "page_size": page_size}


@router.get("/boms/{bom_id}", response_model=mschemas.BomResponse)
async def get_bom(
	bom_id: UUID,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Get BOM by ID with items."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	bom = await mservice.get_bom_by_id(db, tenant_id, bom_id)
	if not bom:
		raise HTTPException(status_code=404, detail="BOM not found")
	return bom


@router.patch("/boms/{bom_id}", response_model=mschemas.BomResponse)
async def update_bom(
	bom_id: UUID,
	payload: mschemas.BomUpdate,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Update a draft BOM."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	try:
		return await mservice.update_bom(db, tenant_id, bom_id, payload)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.post("/boms/{bom_id}/submit", response_model=mschemas.BomResponse)
async def submit_bom(
	bom_id: UUID,
	payload: mschemas.BomSubmit,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Submit a BOM to make it active for production."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	try:
		return await mservice.submit_bom(db, tenant_id, user_id, bom_id, payload)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.post("/boms/{bom_id}/supersede", response_model=mschemas.BomResponse)
async def supersede_bom(
	bom_id: UUID,
	payload: mschemas.BomSupersede,
	replacement_bom_id: UUID,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Supersede a BOM with a replacement BOM."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	try:
		return await mservice.supersede_bom(db, tenant_id, bom_id, replacement_bom_id, payload)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.get("/products/{product_id}/bom-history", response_model=list[mschemas.BomListResponse])
async def get_product_bom_history(
	product_id: UUID,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Get BOM history for a product."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	return await mservice.get_bom_history(db, tenant_id, product_id)


@router.get("/products/{product_id}/active-bom", response_model=mschemas.BomResponse)
async def get_active_bom(
	product_id: UUID,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Get the active submitted BOM for a product."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	# This is a direct DB query pattern, using service function
	bom = await mservice.get_active_bom_for_product(db, tenant_id, product_id)
	if not bom:
		raise HTTPException(status_code=404, detail="No active BOM found")
	return mschemas.BomResponse(
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
			mschemas.BomItemResponse(
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


# ============================================================================
# Work Order Routes
# ============================================================================


@router.post("/work-orders", response_model=mschemas.WorkOrderResponse, status_code=201)
async def create_work_order(
	payload: mschemas.WorkOrderCreate,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Create a new work order from a submitted BOM."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	try:
		return await mservice.create_work_order(db, tenant_id, user_id, payload)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.get("/work-orders", response_model=dict[str, Any])
async def list_work_orders(
	status: str | None = None,
	product_id: UUID | None = None,
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""List work orders with pagination and filters."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	orders, total = await mservice.list_work_orders(
		db, tenant_id, status, product_id, page, page_size,
	)
	return {"items": orders, "total": total, "page": page, "page_size": page_size}


@router.get("/work-orders/{work_order_id}", response_model=mschemas.WorkOrderResponse)
async def get_work_order(
	work_order_id: UUID,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Get work order by ID with material lines."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	wo = await mservice.get_work_order_by_id(db, tenant_id, work_order_id)
	if not wo:
		raise HTTPException(status_code=404, detail="Work order not found")
	return wo


@router.patch("/work-orders/{work_order_id}", response_model=mschemas.WorkOrderResponse)
async def update_work_order(
	work_order_id: UUID,
	payload: mschemas.WorkOrderUpdate,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Update a work order."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	try:
		return await mservice.update_work_order(db, tenant_id, work_order_id, payload)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.post("/work-orders/{work_order_id}/transition", response_model=mschemas.WorkOrderResponse)
async def transition_work_order(
	work_order_id: UUID,
	payload: mschemas.WorkOrderStatusTransition,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Transition work order to a new status."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	try:
		return await mservice.transition_work_order_status(
			db, tenant_id, work_order_id, payload,
		)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.post("/work-orders/{work_order_id}/complete", response_model=mschemas.WorkOrderResponse)
async def complete_work_order(
	work_order_id: UUID,
	payload: mschemas.WorkOrderComplete,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Complete a work order with produced quantity."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	try:
		return await mservice.complete_work_order(
			db, tenant_id, work_order_id, payload,
		)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.post("/work-orders/{work_order_id}/reserve", response_model=mschemas.WorkOrderResponse)
async def reserve_work_order_materials(
	work_order_id: UUID,
	payload: mschemas.WorkOrderMaterialReserve,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Reserve or release materials for a work order."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	try:
		return await mservice.reserve_work_order_materials(
			db, tenant_id, work_order_id, payload,
		)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.post("/work-orders/{work_order_id}/transfer", response_model=mschemas.WorkOrderResponse)
async def transfer_work_order_materials(
	work_order_id: UUID,
	payload: mschemas.WorkOrderTransfer,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Transfer materials for a work order (manufacture flow)."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	try:
		return await mservice.transfer_work_order_materials(
			db, tenant_id, work_order_id, payload,
		)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Workstation Routes
# ============================================================================


@router.post("/workstations", response_model=mschemas.WorkstationResponse, status_code=201)
async def create_workstation(
	payload: mschemas.WorkstationCreate,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Create a new workstation."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	return await mservice.create_workstation(db, tenant_id, payload)


@router.get("/workstations", response_model=dict[str, Any])
async def list_workstations(
	status: str | None = None,
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""List workstations with pagination."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	workstations, total = await mservice.list_workstations(
		db, tenant_id, status, page, page_size,
	)
	return {"items": workstations, "total": total, "page": page, "page_size": page_size}


@router.get("/workstations/{workstation_id}", response_model=mschemas.WorkstationResponse)
async def get_workstation(
	workstation_id: UUID,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Get workstation by ID."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	ws = await mservice.get_workstation_by_id(db, tenant_id, workstation_id)
	if not ws:
		raise HTTPException(status_code=404, detail="Workstation not found")
	return ws


@router.patch("/workstations/{workstation_id}", response_model=mschemas.WorkstationResponse)
async def update_workstation(
	workstation_id: UUID,
	payload: mschemas.WorkstationUpdate,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Update a workstation."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	try:
		return await mservice.update_workstation(db, tenant_id, workstation_id, payload)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Routing Routes
# ============================================================================


@router.post("/routings", response_model=mschemas.RoutingResponse, status_code=201)
async def create_routing(
	payload: mschemas.RoutingCreate,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Create a new routing."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	return await mservice.create_routing(db, tenant_id, payload)


@router.get("/routings", response_model=dict[str, Any])
async def list_routings(
	status: str | None = None,
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""List routings with pagination."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	routings, total = await mservice.list_routings(
		db, tenant_id, status, page, page_size,
	)
	return {"items": routings, "total": total, "page": page, "page_size": page_size}


@router.get("/routings/{routing_id}", response_model=mschemas.RoutingResponse)
async def get_routing(
	routing_id: UUID,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Get routing by ID with operations."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	routing = await mservice.get_routing_by_id(db, tenant_id, routing_id)
	if not routing:
		raise HTTPException(status_code=404, detail="Routing not found")
	return routing


@router.patch("/routings/{routing_id}", response_model=mschemas.RoutingResponse)
async def update_routing(
	routing_id: UUID,
	payload: mschemas.RoutingUpdate,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Update a routing."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	try:
		return await mservice.update_routing(db, tenant_id, routing_id, payload)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.post("/routings/{routing_id}/calculate")
async def calculate_routing(
	routing_id: UUID,
	quantity: float = Query(..., gt=0),
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Calculate planned time and cost for a routing."""
	from common.auth import get_tenant_id_from_request
	from decimal import Decimal
	tenant_id = await get_tenant_id_from_request(user_id)
	routing = await mservice.get_routing_by_id(db, tenant_id, routing_id)
	if not routing:
		raise HTTPException(status_code=404, detail="Routing not found")
	return mservice.calculate_routing_cost_and_time(routing, Decimal(str(quantity)))


# ============================================================================
# Production Planning Routes
# ============================================================================


@router.post("/proposals/generate", response_model=list[mschemas.ManufacturingProposalResponse])
async def generate_proposals(
	payload: mschemas.ProposalGenerateRequest | None = None,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Generate manufacturing proposals from demand signals."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	return await mservice.generate_proposals(db, tenant_id, payload)


@router.get("/proposals", response_model=dict[str, Any])
async def list_proposals(
	status: str | None = None,
	product_id: UUID | None = None,
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""List manufacturing proposals."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	proposals, total = await mservice.list_proposals(
		db, tenant_id, status, product_id, page, page_size,
	)
	return {"items": proposals, "total": total, "page": page, "page_size": page_size}


@router.post("/proposals/{proposal_id}/decide", response_model=mschemas.ManufacturingProposalResponse)
async def decide_proposal(
	proposal_id: UUID,
	payload: mschemas.ProposalDecision,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Accept or reject a manufacturing proposal."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	proposal = await mservice.decide_proposal(db, tenant_id, user_id, proposal_id, payload)
	if not proposal:
		raise HTTPException(status_code=404, detail="Proposal not found")
	return proposal


# ============================================================================
# Production Plan Routes
# ============================================================================


@router.post("/production-plans", response_model=mschemas.ProductionPlanResponse, status_code=201)
async def create_production_plan(
	payload: mschemas.ProductionPlanCreate,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Create a new production plan."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	return await mservice.create_production_plan(db, tenant_id, user_id, payload)


@router.get("/production-plans", response_model=dict[str, Any])
async def list_production_plans(
	status: str | None = None,
	page: int = Query(1, ge=1),
	page_size: int = Query(20, ge=1, le=100),
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""List production plans with pagination."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	plans, total = await mservice.list_production_plans(
		db, tenant_id, status, page, page_size,
	)
	return {"items": plans, "total": total, "page": page, "page_size": page_size}


@router.get("/production-plans/{plan_id}", response_model=mschemas.ProductionPlanResponse)
async def get_production_plan(
	plan_id: UUID,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Get production plan by ID with lines."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	plan = await mservice.get_production_plan_by_id(db, tenant_id, plan_id)
	if not plan:
		raise HTTPException(status_code=404, detail="Production plan not found")
	return plan


@router.post("/production-plans/{plan_id}/firm", response_model=mschemas.ProductionPlanResponse)
async def firm_production_plan(
	plan_id: UUID,
	payload: mschemas.ProductionPlanFirm,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Firm up a production plan, creating work orders from proposals."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	try:
		return await mservice.firm_production_plan(db, tenant_id, user_id, plan_id, payload)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Downtime and OEE Routes
# ============================================================================


@router.post("/downtime", response_model=mschemas.DowntimeResponse, status_code=201)
async def create_downtime(
	payload: mschemas.DowntimeCreate,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Create a downtime entry."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	return await mservice.create_downtime(db, tenant_id, user_id, payload)


@router.get("/downtime", response_model=dict[str, Any])
async def list_downtime(
	workstation_id: UUID | None = None,
	start_date: datetime | None = None,
	end_date: datetime | None = None,
	reason: str | None = None,
	page: int = Query(1, ge=1),
	page_size: int = Query(50, ge=1, le=100),
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""List downtime entries with filters."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	entries, total = await mservice.list_downtime(
		db, tenant_id, workstation_id, start_date, end_date, reason, page, page_size,
	)
	return {"items": entries, "total": total, "page": page, "page_size": page_size}


@router.get("/downtime/pareto", response_model=list[mschemas.DowntimeParetoResponse])
async def get_downtime_pareto(
	workstation_id: UUID | None = None,
	start_date: datetime | None = None,
	end_date: datetime | None = None,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Get downtime Pareto analysis by reason."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	return await mservice.get_downtime_pareto(
		db, tenant_id, workstation_id, start_date, end_date,
	)


@router.post("/oee", response_model=mschemas.OeeRecordResponse, status_code=201)
async def create_oee_record(
	payload: mschemas.OeeRecordCreate,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Create an OEE record with calculated factors."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	return await mservice.create_oee_record(db, tenant_id, payload)


@router.get("/oee/dashboard", response_model=mschemas.OeeDashboardResponse)
async def get_oee_dashboard(
	workstation_id: UUID | None = None,
	start_date: datetime | None = None,
	end_date: datetime | None = None,
	db: AsyncSession = Depends(get_db),
	user_id: UUID = Depends(get_user_id_from_request),
):
	"""Get OEE dashboard data with trend and Pareto."""
	from common.auth import get_tenant_id_from_request
	tenant_id = await get_tenant_id_from_request(user_id)
	return await mservice.get_oee_dashboard(
		db, tenant_id, workstation_id, start_date, end_date,
	)
