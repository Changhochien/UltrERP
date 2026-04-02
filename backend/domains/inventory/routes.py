"""Inventory API routes — warehouses and stock transfers."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import get_db
from common.models.stock_adjustment import ReasonCode
from common.tenant import DEFAULT_TENANT_ID
from domains.inventory.schemas import (
	USER_SELECTABLE_REASON_CODES,
	AcknowledgeAlertResponse,
	InventoryStockResponse,
	ProductDetailResponse,
	ProductSearchResponse,
	ProductSearchResult,
	ReasonCodeItem,
	ReasonCodeListResponse,
	ReceiveOrderRequest,
	ReorderAlertItem,
	ReorderAlertListResponse,
	StockAdjustmentRequest,
	StockAdjustmentResponse,
	SupplierListResponse,
	SupplierOrderCreate,
	SupplierOrderListResponse,
	SupplierOrderResponse,
	SupplierResponse,
	TransferRequest,
	TransferResponse,
	UpdateOrderStatusRequest,
	WarehouseCreate,
	WarehouseList,
	WarehouseResponse,
)
from domains.inventory.services import (
	InsufficientStockError,
	TransferValidationError,
	acknowledge_alert,
	create_stock_adjustment,
	create_supplier_order,
	create_warehouse,
	get_inventory_stocks,
	get_product_detail,
	get_supplier_order,
	get_warehouse,
	list_reorder_alerts,
	list_supplier_orders,
	list_suppliers,
	list_warehouses,
	receive_supplier_order,
	search_products,
	transfer_stock,
	update_supplier_order_status,
)

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

# Hardcoded tenant for MVP — replaced by auth middleware later
TENANT_ID = DEFAULT_TENANT_ID
ACTOR_ID = "system"


# ── Warehouse endpoints ───────────────────────────────────────

@router.get(
	"/warehouses",
	response_model=WarehouseList,
)
async def list_warehouses_endpoint(
	session: DbSession,
	active_only: bool = Query(True),
) -> WarehouseList:
	warehouses = await list_warehouses(
		session, TENANT_ID, active_only=active_only,
	)
	return WarehouseList(
		items=[WarehouseResponse.model_validate(w) for w in warehouses],
		total=len(warehouses),
	)


@router.get(
	"/warehouses/{warehouse_id}",
	response_model=WarehouseResponse,
)
async def get_warehouse_endpoint(
	warehouse_id: uuid.UUID,
	session: DbSession,
) -> WarehouseResponse:
	warehouse = await get_warehouse(session, TENANT_ID, warehouse_id)
	if warehouse is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Warehouse not found",
		)
	return WarehouseResponse.model_validate(warehouse)


@router.post(
	"/warehouses",
	response_model=WarehouseResponse,
	status_code=status.HTTP_201_CREATED,
)
async def create_warehouse_endpoint(
	data: WarehouseCreate,
	session: DbSession,
) -> WarehouseResponse:
	warehouse = await create_warehouse(
		session,
		TENANT_ID,
		name=data.name,
		code=data.code,
		location=data.location,
		address=data.address,
		contact_email=data.contact_email,
	)
	await session.commit()
	return WarehouseResponse.model_validate(warehouse)


# ── Transfer endpoints ────────────────────────────────────────

@router.post(
	"/transfers",
	response_model=TransferResponse,
	status_code=status.HTTP_201_CREATED,
)
async def create_transfer_endpoint(
	data: TransferRequest,
	session: DbSession,
) -> TransferResponse:
	try:
		transfer = await transfer_stock(
			session,
			TENANT_ID,
			from_warehouse_id=data.from_warehouse_id,
			to_warehouse_id=data.to_warehouse_id,
			product_id=data.product_id,
			quantity=data.quantity,
			actor_id=ACTOR_ID,
			notes=data.notes,
		)
		await session.commit()
		return TransferResponse.model_validate(transfer)
	except TransferValidationError as exc:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
			detail=str(exc),
		) from exc
	except InsufficientStockError as exc:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail={
				"message": "Insufficient stock",
				"available": exc.available,
				"requested": exc.requested,
			},
		) from exc


# ── Reason codes endpoint ─────────────────────────────────────

@router.get(
	"/reason-codes",
	response_model=ReasonCodeListResponse,
)
async def list_reason_codes() -> ReasonCodeListResponse:
	items = [
		ReasonCodeItem(
			value=rc.value,
			label=rc.value.replace("_", " ").title(),
			user_selectable=rc.value in USER_SELECTABLE_REASON_CODES,
		)
		for rc in ReasonCode
	]
	return ReasonCodeListResponse(items=items)


# ── Stock adjustment endpoint ─────────────────────────────────

@router.post(
	"/adjustments",
	response_model=StockAdjustmentResponse,
	status_code=status.HTTP_201_CREATED,
)
async def create_adjustment_endpoint(
	data: StockAdjustmentRequest,
	session: DbSession,
) -> StockAdjustmentResponse:
	# Validate reason code is user-selectable
	if data.reason_code not in USER_SELECTABLE_REASON_CODES:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
			detail=f"Invalid reason code: {data.reason_code}. "
			f"Must be one of: {', '.join(USER_SELECTABLE_REASON_CODES)}",
		)

	try:
		reason = ReasonCode(data.reason_code)
	except ValueError:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
			detail=f"Unknown reason code: {data.reason_code}",
		)

	try:
		result = await create_stock_adjustment(
			session,
			TENANT_ID,
			product_id=data.product_id,
			warehouse_id=data.warehouse_id,
			quantity_change=data.quantity_change,
			reason_code=reason,
			actor_id=ACTOR_ID,
			notes=data.notes,
		)
		await session.commit()
		return StockAdjustmentResponse(**result)
	except TransferValidationError as exc:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
			detail=str(exc),
		) from exc
	except InsufficientStockError as exc:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail={
				"message": f"Insufficient stock: {exc.available} units available",
				"available": exc.available,
				"requested": exc.requested,
			},
		) from exc


# ── Product search endpoints ──────────────────────────────────

@router.get(
	"/products/search",
	response_model=ProductSearchResponse,
)
async def search_products_endpoint(
	session: DbSession,
	q: str = Query(..., min_length=3, max_length=100),
	limit: int = Query(20, ge=1, le=100),
	warehouse_id: uuid.UUID | None = Query(None),
) -> ProductSearchResponse:
	stripped = q.strip()
	if len(stripped) < 3:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Search query must be at least 3 characters",
		)
	results = await search_products(
		session,
		TENANT_ID,
		stripped,
		warehouse_id=warehouse_id,
		limit=limit,
	)
	return ProductSearchResponse(
		items=[ProductSearchResult(**r) for r in results],
		total=len(results),
	)


# ── Product detail endpoint ────────────────────────────────────

@router.get(
	"/products/{product_id}",
	response_model=ProductDetailResponse,
)
async def get_product_detail_endpoint(
	product_id: uuid.UUID,
	session: DbSession,
	history_limit: int = Query(100, ge=1, le=500),
	history_offset: int = Query(0, ge=0),
) -> ProductDetailResponse:
	detail = await get_product_detail(
		session,
		TENANT_ID,
		product_id,
		history_limit=history_limit,
		history_offset=history_offset,
	)
	if detail is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Product not found",
		)
	return ProductDetailResponse(**detail)


# ── Stock query endpoints ─────────────────────────────────────

@router.get(
	"/stocks/{product_id}",
	response_model=list[InventoryStockResponse],
)
async def get_product_stocks(
	product_id: uuid.UUID,
	session: DbSession,
	warehouse_id: uuid.UUID | None = Query(None),
) -> list[InventoryStockResponse]:
	stocks = await get_inventory_stocks(
		session,
		TENANT_ID,
		product_id,
		warehouse_id=warehouse_id,
	)
	return [InventoryStockResponse.model_validate(s) for s in stocks]


# ── Reorder alert endpoints ───────────────────────────────────

@router.get(
	"/alerts/reorder",
	response_model=ReorderAlertListResponse,
)
async def list_reorder_alerts_endpoint(
	session: DbSession,
	status: str | None = Query(None, pattern="^(pending|acknowledged|resolved)$"),
	warehouse_id: uuid.UUID | None = Query(None),
	limit: int = Query(50, ge=1, le=200),
	offset: int = Query(0, ge=0),
) -> ReorderAlertListResponse:
	items, total = await list_reorder_alerts(
		session,
		TENANT_ID,
		status_filter=status,
		warehouse_id=warehouse_id,
		limit=limit,
		offset=offset,
	)
	return ReorderAlertListResponse(
		items=[ReorderAlertItem(**i) for i in items],
		total=total,
	)


@router.put(
	"/alerts/reorder/{alert_id}/acknowledge",
	response_model=AcknowledgeAlertResponse,
)
async def acknowledge_alert_endpoint(
	alert_id: uuid.UUID,
	session: DbSession,
) -> AcknowledgeAlertResponse:
	result = await acknowledge_alert(
		session,
		TENANT_ID,
		alert_id,
		actor_id=ACTOR_ID,
	)
	if result is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Alert not found or already resolved",
		)
	await session.commit()
	return AcknowledgeAlertResponse(**result)


# ── Supplier endpoints ────────────────────────────────────────

@router.get(
	"/suppliers",
	response_model=SupplierListResponse,
)
async def list_suppliers_endpoint(
	session: DbSession,
	active_only: bool = Query(True),
) -> SupplierListResponse:
	suppliers = await list_suppliers(
		session, TENANT_ID, active_only=active_only,
	)
	return SupplierListResponse(
		items=[SupplierResponse(**s) for s in suppliers],
		total=len(suppliers),
	)


# ── Supplier order endpoints ──────────────────────────────────

@router.post(
	"/supplier-orders",
	response_model=SupplierOrderResponse,
	status_code=status.HTTP_201_CREATED,
)
async def create_supplier_order_endpoint(
	data: SupplierOrderCreate,
	session: DbSession,
) -> SupplierOrderResponse:
	result = await create_supplier_order(
		session,
		TENANT_ID,
		supplier_id=data.supplier_id,
		order_date=data.order_date,
		expected_arrival_date=data.expected_arrival_date,
		lines=[line.model_dump() for line in data.lines],
		actor_id=ACTOR_ID,
	)
	await session.commit()
	return SupplierOrderResponse(**result)


@router.get(
	"/supplier-orders",
	response_model=SupplierOrderListResponse,
)
async def list_supplier_orders_endpoint(
	session: DbSession,
	status_filter: str | None = Query(
		None,
		alias="status",
		pattern=r"^(pending|confirmed|shipped|partially_received|received|cancelled)$",
	),
	supplier_id: uuid.UUID | None = Query(None),
	limit: int = Query(50, ge=1, le=200),
	offset: int = Query(0, ge=0),
) -> SupplierOrderListResponse:
	items, total = await list_supplier_orders(
		session,
		TENANT_ID,
		status_filter=status_filter,
		supplier_id=supplier_id,
		limit=limit,
		offset=offset,
	)
	return SupplierOrderListResponse(
		items=items,
		total=total,
	)


@router.get(
	"/supplier-orders/{order_id}",
	response_model=SupplierOrderResponse,
)
async def get_supplier_order_endpoint(
	order_id: uuid.UUID,
	session: DbSession,
) -> SupplierOrderResponse:
	order = await get_supplier_order(session, TENANT_ID, order_id)
	if order is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Supplier order not found",
		)
	return SupplierOrderResponse(**order)


@router.put(
	"/supplier-orders/{order_id}/status",
	response_model=SupplierOrderResponse,
)
async def update_supplier_order_status_endpoint(
	order_id: uuid.UUID,
	data: UpdateOrderStatusRequest,
	session: DbSession,
) -> SupplierOrderResponse:
	try:
		result = await update_supplier_order_status(
			session,
			TENANT_ID,
			order_id,
			new_status=data.status,
			actor_id=ACTOR_ID,
			notes=data.notes,
		)
		if result is None:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Supplier order not found",
			)
		await session.commit()
		return SupplierOrderResponse(**result)
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
			detail=str(exc),
		) from exc


@router.put(
	"/supplier-orders/{order_id}/receive",
	response_model=SupplierOrderResponse,
)
async def receive_supplier_order_endpoint(
	order_id: uuid.UUID,
	data: ReceiveOrderRequest,
	session: DbSession,
) -> SupplierOrderResponse:
	try:
		result = await receive_supplier_order(
			session,
			TENANT_ID,
			order_id,
			received_quantities=data.received_quantities,
			received_date=data.received_date,
			actor_id=ACTOR_ID,
		)
		if result is None:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Supplier order not found",
			)
		await session.commit()
		return SupplierOrderResponse(**result)
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
			detail=str(exc),
		) from exc
