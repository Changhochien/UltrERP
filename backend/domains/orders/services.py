"""Order domain services — create, list, get orders."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.errors import ValidationError as ServiceValidationError
from common.models.audit_log import AuditLog
from common.models.inventory_stock import InventoryStock
from common.models.order import Order
from common.models.order_line import OrderLine
from common.models.warehouse import Warehouse
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.invoices.enums import InvoiceStatus
from domains.invoices.models import Invoice
from domains.invoices.service import enrich_invoices_with_payment_status
from domains.invoices.tax import TaxPolicyCode, aggregate_invoice_totals, calculate_line_amounts
from domains.orders.schemas import (
    ALLOWED_TRANSITIONS,
    PAYMENT_TERMS_CONFIG,
    OrderBillingStatus,
    OrderCommercialStatus,
    OrderCreate,
    OrderFulfillmentStatus,
    OrderReservationStatus,
    OrderStatus,
    OrderUTMAttributionOrigin,
)
from domains.payments.models import Payment
from domains.settings.commercial_profile_service import CommercialValueSource
from domains.settings.document_currency import (
    apply_document_currency_snapshot,
    apply_line_currency_snapshot,
    validate_document_line_header_snapshot,
)
from domains.settings.payment_terms_service import generate_schedule

logger = logging.getLogger(__name__)

TENANT_ID = DEFAULT_TENANT_ID
ACTOR_ID = str(DEFAULT_TENANT_ID)
_COMMISSION_QUANT = Decimal("0.01")
_ORDER_UTM_FIELDS = ("utm_source", "utm_medium", "utm_campaign", "utm_content")


def _build_sales_team_snapshot(
    sales_team: Sequence[object],
    *,
    commissionable_amount: Decimal,
) -> tuple[list[dict[str, str]], Decimal]:
    if not sales_team:
        return [], Decimal("0.00")

    total_allocated_percentage = sum(member.allocated_percentage for member in sales_team)
    if total_allocated_percentage > Decimal("100.00"):
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "field": "sales_team",
                    "message": "Sales team allocation cannot exceed 100%.",
                }
            ],
        )

    normalized_team: list[dict[str, str]] = []
    total_commission = Decimal("0.00")
    for member in sales_team:
        allocated_amount = (
            commissionable_amount
            * member.allocated_percentage
            * member.commission_rate
            / Decimal("10000")
        ).quantize(_COMMISSION_QUANT)
        normalized_team.append(
            {
                "sales_person": member.sales_person,
                "allocated_percentage": str(member.allocated_percentage),
                "commission_rate": str(member.commission_rate),
                "allocated_amount": str(allocated_amount),
            }
        )
        total_commission += allocated_amount

    return normalized_team, total_commission.quantize(_COMMISSION_QUANT)


def _trim_text(value: object | None) -> str:
    return value.strip() if isinstance(value, str) else ""


def extract_order_utm_attribution(
    crm_context_snapshot: dict[str, Any] | None,
) -> dict[str, str | None]:
    snapshot = crm_context_snapshot if isinstance(crm_context_snapshot, dict) else {}
    attribution = {field: _trim_text(snapshot.get(field)) for field in _ORDER_UTM_FIELDS}
    raw_origin = _trim_text(snapshot.get("utm_attribution_origin"))
    origin = raw_origin if raw_origin in {origin.value for origin in OrderUTMAttributionOrigin} else None
    return {
        **attribution,
        "utm_attribution_origin": origin,
    }


def build_order_crm_context_snapshot(data: OrderCreate) -> dict[str, Any] | None:
    snapshot = dict(data.crm_context_snapshot or {})
    current = extract_order_utm_attribution(snapshot)
    current_values = {field: str(current[field] or "") for field in _ORDER_UTM_FIELDS}
    explicit_fields = {field: field in data.model_fields_set for field in _ORDER_UTM_FIELDS}
    explicit_values = {field: _trim_text(getattr(data, field, "")) for field in _ORDER_UTM_FIELDS}
    has_explicit_values = any(explicit_fields.values())

    if has_explicit_values:
        effective_values = {
            field: explicit_values[field] if explicit_fields[field] else current_values[field]
            for field in _ORDER_UTM_FIELDS
        }
    else:
        effective_values = current_values

    has_effective_values = any(effective_values.values())
    for field in _ORDER_UTM_FIELDS:
        if effective_values[field]:
            snapshot[field] = effective_values[field]
        else:
            snapshot.pop(field, None)

    origin: str | None
    if not has_effective_values:
        origin = None
    elif has_explicit_values and effective_values != current_values:
        origin = OrderUTMAttributionOrigin.MANUAL_OVERRIDE.value
    else:
        origin = str(current["utm_attribution_origin"] or "") or (
            OrderUTMAttributionOrigin.SOURCE_DOCUMENT.value
            if any(current_values.values())
            else OrderUTMAttributionOrigin.MANUAL_OVERRIDE.value
        )

    if origin:
        snapshot["utm_attribution_origin"] = origin
    else:
        snapshot.pop("utm_attribution_origin", None)

    return snapshot or None


async def check_stock_availability(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> dict:
    """Return available stock per warehouse for a product."""
    stmt = (
        select(
            InventoryStock.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity,
        )
        .join(Warehouse, InventoryStock.warehouse_id == Warehouse.id)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
        )
        .order_by(Warehouse.name)
    )

    async with session.begin():
        await set_tenant(session, tenant_id)
        result = await session.execute(stmt)
        rows = result.all()

    warehouses = []
    total = 0
    for row in rows:
        warehouses.append(
            {
                "warehouse_id": row.warehouse_id,
                "warehouse_name": row.warehouse_name,
                "available": row.quantity,
            }
        )
        total += row.quantity

    return {
        "product_id": product_id,
        "warehouses": warehouses,
        "total_available": total,
    }


async def create_order(
    session: AsyncSession,
    data: OrderCreate,
    tenant_id: uuid.UUID | None = None,
) -> Order:
    tid = tenant_id or TENANT_ID

    # Validate customer exists
    from domains.customers.models import Customer

    async with session.begin():
        await set_tenant(session, tid)

        if data.source_quotation_id is None and any(
            line.source_quotation_line_no is not None for line in data.lines
        ):
            raise HTTPException(
                status_code=422,
                detail=[
                    {
                        "field": "source_quotation_id",
                        "message": "source_quotation_id is required when quotation line mappings are provided.",
                    }
                ],
            )

        result = await session.execute(
            select(Customer).where(
                Customer.id == data.customer_id,
                Customer.tenant_id == tid,
            )
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            raise HTTPException(
                status_code=422,
                detail=[
                    {"field": "customer_id", "message": "Customer does not exist."},
                ],
            )

        # Validate products exist
        from common.models.product import Product

        product_ids = [line.product_id for line in data.lines]
        result = await session.execute(
            select(Product.id).where(
                Product.id.in_(product_ids),
                Product.tenant_id == tid,
            )
        )
        found_ids = {row for row in result.scalars().all()}
        missing = [str(pid) for pid in product_ids if pid not in found_ids]
        if missing:
            raise HTTPException(
                status_code=422,
                detail=[
                    {"field": "lines", "message": f"Products not found: {', '.join(missing)}"},
                ],
            )

        source_quotation = None
        if data.source_quotation_id is not None:
            from domains.crm.models import Quotation

            result = await session.execute(
                select(Quotation).where(
                    Quotation.id == data.source_quotation_id,
                    Quotation.tenant_id == tid,
                )
            )
            source_quotation = result.scalar_one_or_none()
            if source_quotation is None:
                raise HTTPException(
                    status_code=422,
                    detail=[
                        {
                            "field": "source_quotation_id",
                            "message": "Source quotation does not exist.",
                        }
                    ],
                )

            valid_source_lines = {int(item.get("line_no") or 0) for item in source_quotation.items}
            mapped_source_lines = [
                line.source_quotation_line_no for line in data.lines if line.source_quotation_line_no is not None
            ]
            if not mapped_source_lines:
                raise HTTPException(
                    status_code=422,
                    detail=[
                        {
                            "field": "lines",
                            "message": "At least one order line must preserve quotation line lineage for quotation conversion.",
                        }
                    ],
                )

            invalid_source_lines = sorted(
                {line_no for line_no in mapped_source_lines if line_no not in valid_source_lines}
            )
            if invalid_source_lines:
                raise HTTPException(
                    status_code=422,
                    detail=[
                        {
                            "field": "lines",
                            "message": "Unknown quotation line mappings: "
                            + ", ".join(str(line_no) for line_no in invalid_source_lines),
                        }
                    ],
                )

        # Generate order number (12 hex chars ≈ 281 trillion combos/day)
        order_number = (
            f"ORD-{datetime.now(tz=UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:12].upper()}"
        )

        # Resolve payment terms
        terms_config = PAYMENT_TERMS_CONFIG[data.payment_terms_code]
        header_discount_supplied = (
            "discount_amount" in data.model_fields_set or "discount_percent" in data.model_fields_set
        )
        normalized_discount_amount = (
            data.discount_amount if data.discount_amount > 0 else Decimal("0.00")
        )
        normalized_discount_percent = (
            data.discount_percent
            if normalized_discount_amount == 0 and data.discount_percent > 0
            else customer.default_discount_percent
            if normalized_discount_amount == 0
            and not header_discount_supplied
            and customer.default_discount_percent > 0
            else Decimal("0.0000")
        )
        crm_context_snapshot = build_order_crm_context_snapshot(data)
        explicit_currency = data.currency_code.upper().strip() if data.currency_code else None
        source_currency = (
            source_quotation.currency.upper().strip()
            if source_quotation is not None and source_quotation.currency
            else None
        )
        profile_currency = (
            customer.default_currency_code.upper().strip()
            if getattr(customer, "default_currency_code", None)
            else None
        )
        if source_currency:
            currency_code = source_currency
            currency_source = CommercialValueSource.SOURCE_DOCUMENT.value
        elif explicit_currency:
            currency_code = explicit_currency
            currency_source = CommercialValueSource.MANUAL_OVERRIDE.value
        elif profile_currency:
            currency_code = profile_currency
            currency_source = CommercialValueSource.PROFILE_DEFAULT.value
        else:
            currency_code = "TWD"
            currency_source = CommercialValueSource.LEGACY_COMPATIBILITY.value
        payment_terms_source = (
            CommercialValueSource.MANUAL_OVERRIDE.value
            if "payment_terms_code" in data.model_fields_set
            else CommercialValueSource.LEGACY_COMPATIBILITY.value
        )

        order = Order(
            tenant_id=tid,
            customer_id=data.customer_id,
            source_quotation_id=data.source_quotation_id,
            order_number=order_number,
            status=OrderStatus.PENDING.value,
            currency_code=currency_code,
            currency_source=currency_source,
            payment_terms_code=data.payment_terms_code.value,
            payment_terms_days=int(terms_config["days"]),
            payment_terms_source=payment_terms_source,
            discount_amount=normalized_discount_amount,
            discount_percent=normalized_discount_percent,
            crm_context_snapshot=crm_context_snapshot,
            notes=data.notes,
            created_by=ACTOR_ID,
        )
        session.add(order)
        try:
            await session.flush()
        except IntegrityError:
            raise HTTPException(
                status_code=409,
                detail="Order number collision — please retry.",
            )

        # Create line items with tax calculation and stock snapshot
        line_amounts_list = []
        order_lines: list[OrderLine] = []
        for idx, line_data in enumerate(data.lines, start=1):
            try:
                policy_code = TaxPolicyCode(line_data.tax_policy_code)
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=[
                        {
                            "field": f"lines[{idx - 1}].tax_policy_code",
                            "message": f"Invalid tax policy code: {line_data.tax_policy_code}",
                        },
                    ],
                )

            amounts = calculate_line_amounts(
                quantity=line_data.quantity,
                unit_price=line_data.unit_price,
                policy_code=policy_code,
            )
            line_amounts_list.append(amounts)

            # Stock availability snapshot (read-only, no reservation)
            stock_stmt = select(func.coalesce(func.sum(InventoryStock.quantity), 0)).where(
                InventoryStock.tenant_id == tid,
                InventoryStock.product_id == line_data.product_id,
            )
            stock_result = await session.execute(stock_stmt)
            total_available = int(stock_result.scalar())

            backorder_note = None
            if line_data.quantity > total_available:
                backorder_qty = line_data.quantity - total_available
                backorder_note = f"Backorder: {backorder_qty} units"

            order_line = OrderLine(
                tenant_id=tid,
                order_id=order.id,
                product_id=line_data.product_id,
                source_quotation_line_no=line_data.source_quotation_line_no,
                line_number=idx,
                quantity=line_data.quantity,
                list_unit_price=line_data.list_unit_price,
                unit_price=line_data.unit_price,
                discount_amount=line_data.discount_amount,
                tax_policy_code=line_data.tax_policy_code,
                tax_type=amounts.tax_type,
                tax_rate=amounts.tax_rate,
                tax_amount=amounts.tax_amount,
                subtotal_amount=amounts.subtotal,
                total_amount=amounts.total_amount,
                description=line_data.description,
                available_stock_snapshot=total_available,
                backorder_note=backorder_note,
            )
            session.add(order_line)
            order_lines.append(order_line)

        await session.flush()

        # Aggregate totals
        discount_amount = normalized_discount_amount if normalized_discount_amount > 0 else None
        discount_percent = normalized_discount_percent if normalized_discount_percent > 0 else None
        totals = aggregate_invoice_totals(
            line_amounts_list,
            discount_amount=discount_amount,
            discount_percent=discount_percent,
        )
        order.subtotal_amount = totals["subtotal_amount"]
        order.tax_amount = totals["tax_amount"]
        order.total_amount = totals["total_amount"]
        snapshot = await apply_document_currency_snapshot(
            session,
            tid,
            order,
            currency_code=currency_code,
            transaction_date=date.today(),
            subtotal=order.subtotal_amount or Decimal("0.00"),
            tax_amount=order.tax_amount or Decimal("0.00"),
            total=order.total_amount or Decimal("0.00"),
            currency_source=currency_source,
        )
        for order_line, amounts in zip(order_lines, line_amounts_list, strict=True):
            apply_line_currency_snapshot(
                snapshot,
                order_line,
                unit_price=order_line.unit_price,
                subtotal=amounts.subtotal,
                tax_amount=amounts.tax_amount,
                total=amounts.total_amount,
            )
        validate_document_line_header_snapshot(
            snapshot,
            order_lines,
            (order.base_subtotal_amount or Decimal("0.00"))
            + (order.base_tax_amount or Decimal("0.00")),
        )
        await generate_schedule(
            session,
            tid,
            document_type="order",
            document_id=order.id,
            template_id=None,
            document_date=date.today(),
            total_amount=order.total_amount or Decimal("0.00"),
            payment_terms_code=order.payment_terms_code,
        )
        sales_team_snapshot, total_commission = _build_sales_team_snapshot(
            data.sales_team,
            commissionable_amount=order.subtotal_amount or Decimal("0.00"),
        )
        order.sales_team = sales_team_snapshot or None
        order.total_commission = total_commission

        # Audit log
        audit = AuditLog(
            tenant_id=tid,
            actor_id=ACTOR_ID,
            action="ORDER_CREATED",
            entity_type="order",
            entity_id=str(order.id),
            after_state={
                "order_number": order.order_number,
                "customer_id": str(data.customer_id),
                "source_quotation_id": str(data.source_quotation_id) if data.source_quotation_id else None,
                "status": OrderStatus.PENDING.value,
                "line_count": len(data.lines),
                "total_amount": str(order.total_amount),
                "utm_source": crm_context_snapshot.get("utm_source") if crm_context_snapshot else None,
                "utm_medium": crm_context_snapshot.get("utm_medium") if crm_context_snapshot else None,
                "utm_campaign": crm_context_snapshot.get("utm_campaign") if crm_context_snapshot else None,
                "utm_content": crm_context_snapshot.get("utm_content") if crm_context_snapshot else None,
                "utm_attribution_origin": crm_context_snapshot.get("utm_attribution_origin") if crm_context_snapshot else None,
                "sales_team": sales_team_snapshot,
                "total_commission": str(order.total_commission),
            },
            correlation_id=str(order.id),
        )
        session.add(audit)
        if source_quotation is not None:
            from domains.crm.service import sync_quotation_order_coverage_in_transaction

            await sync_quotation_order_coverage_in_transaction(session, source_quotation, tid)
        await session.flush()

    # Reload with relationships
    return await get_order(session, order.id, tid)


async def confirm_order(
    session: AsyncSession,
    order_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
    actor_id: str = ACTOR_ID,
) -> Order:
    """Confirm an order and auto-generate an invoice atomically."""
    from domains.customers.models import Customer
    from domains.inventory.order_confirmation import reserve_stock_for_order_confirmation
    from domains.invoices.enums import BuyerType
    from domains.invoices.schemas import InvoiceCreate, InvoiceCreateLine
    from domains.invoices.service import create_invoice_in_transaction, normalize_buyer_identifier

    tid = tenant_id or TENANT_ID

    async with session.begin():
        await set_tenant(session, tid)

        # Fetch order with lines + FOR UPDATE lock
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.lines))
            .where(Order.id == order_id, Order.tenant_id == tid)
            .with_for_update()
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        # Validate status
        if order.status != OrderStatus.PENDING.value:
            raise HTTPException(
                status_code=409,
                detail=f"Order is '{order.status}', not '{OrderStatus.PENDING.value}'",
            )

        # Validate lines
        if not order.lines:
            raise HTTPException(status_code=409, detail="Order has no line items")

        # Prevent duplicate invoice
        if order.invoice_id is not None:
            raise HTTPException(status_code=409, detail="Order already has an invoice")

        # Look up product codes for invoice lines
        from common.models.product import Product

        line_product_ids = [line.product_id for line in order.lines]
        result = await session.execute(
            select(Product.id, Product.code, Product.name, Product.category).where(
                Product.id.in_(line_product_ids),
                Product.tenant_id == tid,
            )
        )
        product_rows = {row.id: row for row in result.all()}
        product_code_map = {product_id: row.code for product_id, row in product_rows.items()}

        missing_product_ids: list[str] = []
        for line in order.lines:
            product_row = product_rows.get(line.product_id)
            if product_row is None:
                missing_product_ids.append(str(line.product_id))
                continue
            if getattr(line, "product_name_snapshot", None) is None:
                line.product_name_snapshot = product_row.name or line.description
            if getattr(line, "product_category_snapshot", None) is None:
                line.product_category_snapshot = product_row.category or None

        if missing_product_ids:
            raise HTTPException(
                status_code=409,
                detail=f"Products no longer exist: {', '.join(missing_product_ids)}",
            )

        # Validate customer
        result = await session.execute(
            select(Customer).where(
                Customer.id == order.customer_id,
                Customer.tenant_id == tid,
            )
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=409, detail="Customer no longer exists")

        # Build InvoiceCreate from order
        buyer_type = BuyerType.B2B
        buyer_identifier = customer.normalized_business_number or ""
        if not buyer_identifier:
            buyer_type = BuyerType.B2C

        try:
            buyer_identifier_normalized = normalize_buyer_identifier(
                buyer_type, buyer_identifier if buyer_type == BuyerType.B2B else None
            )
        except ValueError:
            logger.warning(
                "Customer %s has invalid business_number %r; falling back to B2C",
                customer.id,
                buyer_identifier,
            )
            buyer_identifier_normalized = "0000000000"
            buyer_type = BuyerType.B2C

        invoice_data = InvoiceCreate(
            customer_id=order.customer_id,
            invoice_date=date.today(),
            currency_code=order.currency_code or "TWD",
            order_id=order.id,
            buyer_type=buyer_type,
            buyer_identifier=buyer_identifier if buyer_type == BuyerType.B2B else None,
            lines=[
                InvoiceCreateLine(
                    product_id=line.product_id,
                    product_code=product_code_map.get(line.product_id),
                    description=line.description,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    unit_cost=getattr(line, "unit_cost", None),
                    tax_policy_code=TaxPolicyCode(line.tax_policy_code),
                )
                for line in order.lines
            ],
        )

        # Create invoice within this transaction (no nested begin)
        try:
            invoice = await create_invoice_in_transaction(
                session, invoice_data, tid, buyer_identifier_normalized
            )
        except ServiceValidationError as e:
            raise HTTPException(status_code=409, detail=e.errors)
        invoice.order_id = order.id

        try:
            await reserve_stock_for_order_confirmation(
                session,
                tid,
                order_number=order.order_number,
                order_lines=order.lines,
                actor_id=actor_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))

        # Update order
        now = datetime.now(tz=UTC)
        order.status = OrderStatus.CONFIRMED.value
        order.confirmed_at = now
        order.invoice_id = invoice.id

        # Audit logs
        order_audit = AuditLog(
            tenant_id=tid,
            actor_id=actor_id,
            action="ORDER_STATUS_CHANGED",
            entity_type="order",
            entity_id=str(order.id),
            before_state={"status": OrderStatus.PENDING.value},
            after_state={
                "status": OrderStatus.CONFIRMED.value,
                "invoice_id": str(invoice.id),
            },
            correlation_id=str(order.id),
        )
        session.add(order_audit)

        invoice_audit = AuditLog(
            tenant_id=tid,
            actor_id=actor_id,
            action="INVOICE_CREATED",
            entity_type="invoice",
            entity_id=str(invoice.id),
            after_state={
                "invoice_number": invoice.invoice_number,
                "order_id": str(order.id),
                "total_amount": str(invoice.total_amount),
            },
            correlation_id=str(order.id),
        )
        session.add(invoice_audit)
        await session.flush()

    return order


async def update_order_status(
    session: AsyncSession,
    order_id: uuid.UUID,
    new_status: str | OrderStatus,
    tenant_id: uuid.UUID | None = None,
    actor_id: str = ACTOR_ID,
) -> Order:
    """Transition order to a new status via state machine."""
    tid = tenant_id or TENANT_ID

    # Normalize to OrderStatus enum
    try:
        target = OrderStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid status: {new_status}")

    # Delegate confirmed transition to confirm_order (handles invoice creation)
    if target is OrderStatus.CONFIRMED:
        return await confirm_order(session, order_id, tenant_id=tid, actor_id=actor_id)

    async with session.begin():
        await set_tenant(session, tid)

        result = await session.execute(
            select(Order)
            .where(Order.id == order_id, Order.tenant_id == tid)
            .options(selectinload(Order.lines), selectinload(Order.customer))
            .with_for_update()
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        try:
            current = OrderStatus(order.status)
        except ValueError:
            raise HTTPException(status_code=409, detail=f"Unknown current status: {order.status}")

        if target not in ALLOWED_TRANSITIONS.get(current, frozenset()):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot transition from '{order.status}' to '{target.value}'",
            )

        old_status = order.status
        order.status = target.value

        audit = AuditLog(
            tenant_id=tid,
            actor_id=actor_id,
            action="ORDER_STATUS_CHANGED",
            entity_type="order",
            entity_id=str(order.id),
            before_state={"status": old_status},
            after_state={"status": target.value},
            correlation_id=str(order.id),
        )
        session.add(audit)
        if target is OrderStatus.CANCELLED and getattr(order, "source_quotation_id", None) is not None:
            from domains.crm.models import Quotation
            from domains.crm.service import sync_quotation_order_coverage_in_transaction

            result = await session.execute(
                select(Quotation).where(
                    Quotation.id == order.source_quotation_id,
                    Quotation.tenant_id == tid,
                )
            )
            source_quotation = result.scalar_one_or_none()
            if source_quotation is not None:
                await sync_quotation_order_coverage_in_transaction(session, source_quotation, tid)
        await session.flush()

    return order


async def list_orders(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
    *,
    status: str | Sequence[str] | None = None,
    customer_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    workflow_view: Literal[
        "pending_intake",
        "ready_to_ship",
        "shipped_not_completed",
        "invoiced_not_paid",
    ]
    | None = None,
    sort_by: Literal["created_at", "order_number", "total_amount", "status"] | None = None,
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Order], int]:
    tid = tenant_id or TENANT_ID

    filters = [Order.tenant_id == tid]
    if isinstance(status, Sequence) and not isinstance(status, str):
        status_values = [value for value in status if value]
        if status_values:
            filters.append(Order.status.in_(status_values))
    elif status:
        filters.append(Order.status == status)
    if customer_id:
        filters.append(Order.customer_id == customer_id)
    if date_from:
        filters.append(
            Order.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
        )
    if date_to:
        filters.append(
            Order.created_at <= datetime.combine(date_to, datetime.max.time(), tzinfo=UTC)
        )
    if search:
        filters.append(Order.order_number.ilike(f"%{search}%"))

    if workflow_view == "pending_intake":
        filters.append(Order.status == OrderStatus.PENDING.value)
    elif workflow_view == "ready_to_ship":
        blocking_line_exists = (
            select(OrderLine.id)
            .where(
                OrderLine.order_id == Order.id,
                OrderLine.tenant_id == tid,
                or_(
                    OrderLine.backorder_note.is_not(None),
                    OrderLine.available_stock_snapshot.is_(None),
                    OrderLine.quantity > OrderLine.available_stock_snapshot,
                ),
            )
            .exists()
        )
        filters.extend(
            [
                Order.status == OrderStatus.CONFIRMED.value,
                ~blocking_line_exists,
            ]
        )
    elif workflow_view == "shipped_not_completed":
        filters.append(Order.status == OrderStatus.SHIPPED.value)
    elif workflow_view == "invoiced_not_paid":
        matched_payment_total = (
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.invoice_id == Order.invoice_id,
                Payment.tenant_id == tid,
                Payment.match_status == "matched",
            )
            .scalar_subquery()
        )
        open_invoice_exists = (
            select(Invoice.id)
            .where(
                Invoice.id == Order.invoice_id,
                Invoice.tenant_id == tid,
                Invoice.status != InvoiceStatus.VOIDED.value,
                Invoice.status != InvoiceStatus.PAID.value,
                matched_payment_total < Invoice.total_amount,
            )
            .exists()
        )
        filters.extend([Order.invoice_id.is_not(None), open_invoice_exists])

    # Sorting
    sort_column = {
        "created_at": Order.created_at,
        "order_number": Order.order_number,
        "total_amount": Order.total_amount,
        "status": Order.status,
    }.get(sort_by, Order.created_at)
    if sort_order == "asc":
        sort_column = sort_column.asc()
    else:
        sort_column = sort_column.desc()

    # Count
    count_stmt = select(func.count()).select_from(Order).where(*filters)

    # Fetch page
    offset = (page - 1) * page_size
    stmt = (
        select(Order)
        .options(selectinload(Order.lines))
        .where(*filters)
        .order_by(sort_column)
        .offset(offset)
        .limit(page_size)
    )

    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(count_stmt)
        total = result.scalar() or 0
        result = await session.execute(stmt)
        orders = list(result.scalars().all())

    return orders, total


async def get_order(
    session: AsyncSession,
    order_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> Order:
    tid = tenant_id or TENANT_ID

    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tid)
        .options(
            selectinload(Order.lines),
            selectinload(Order.customer),
        )
    )

    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


def derive_order_execution(
    order: Order,
    *,
    invoice_payment_status: str | None = None,
) -> dict[str, Any]:
    lines = list(getattr(order, "lines", []) or [])
    backorder_line_count = sum(1 for line in lines if getattr(line, "backorder_note", None))
    has_backorder = backorder_line_count > 0
    ready_line_count = sum(
        1
        for line in lines
        if getattr(line, "available_stock_snapshot", None) is not None
        and line.quantity <= line.available_stock_snapshot
        and not getattr(line, "backorder_note", None)
    )
    ready_to_ship = bool(
        order.status == OrderStatus.CONFIRMED.value
        and lines
        and ready_line_count == len(lines)
        and not has_backorder
    )

    if order.status == OrderStatus.CANCELLED.value:
        commercial_status = OrderCommercialStatus.CANCELLED.value
        fulfillment_status = OrderFulfillmentStatus.CANCELLED.value
        reservation_status = OrderReservationStatus.RELEASED.value
    elif order.status == OrderStatus.PENDING.value:
        commercial_status = OrderCommercialStatus.PRE_COMMIT.value
        fulfillment_status = OrderFulfillmentStatus.NOT_STARTED.value
        reservation_status = OrderReservationStatus.NOT_RESERVED.value
    else:
        commercial_status = OrderCommercialStatus.COMMITTED.value
        reservation_status = OrderReservationStatus.RESERVED.value
        if order.status == OrderStatus.SHIPPED.value:
            fulfillment_status = OrderFulfillmentStatus.SHIPPED.value
        elif order.status == OrderStatus.FULFILLED.value:
            fulfillment_status = OrderFulfillmentStatus.FULFILLED.value
        elif ready_to_ship:
            fulfillment_status = OrderFulfillmentStatus.READY_TO_SHIP.value
        else:
            fulfillment_status = OrderFulfillmentStatus.NOT_STARTED.value

    billing_status = (
        invoice_payment_status
        if order.invoice_id and invoice_payment_status
        else OrderBillingStatus.NOT_INVOICED.value
    )

    return {
        "commercial_status": commercial_status,
        "fulfillment_status": fulfillment_status,
        "billing_status": billing_status,
        "reservation_status": reservation_status,
        "ready_to_ship": ready_to_ship,
        "has_backorder": has_backorder,
        "backorder_line_count": backorder_line_count,
    }


async def build_order_workspace_meta(
    session: AsyncSession,
    orders: Sequence[Order],
    *,
    tenant_id: uuid.UUID,
) -> dict[uuid.UUID, dict[str, Any]]:
    if not orders:
        return {}

    invoice_ids = list({order.invoice_id for order in orders if order.invoice_id is not None})
    invoice_by_id: dict[uuid.UUID, Invoice] = {}
    payment_summary_by_invoice_id: dict[uuid.UUID, dict[str, Any]] = {}

    if invoice_ids:
        async with session.begin():
            await set_tenant(session, tenant_id)
            result = await session.execute(
                select(Invoice).where(
                    Invoice.id.in_(invoice_ids),
                    Invoice.tenant_id == tenant_id,
                )
            )
            invoices = list(result.scalars().all())
            invoice_by_id = {invoice.id: invoice for invoice in invoices}
            payment_summaries = await enrich_invoices_with_payment_status(session, invoices, tenant_id)
            payment_summary_by_invoice_id = {
                summary["id"]: summary for summary in payment_summaries
            }

    meta_by_order_id: dict[uuid.UUID, dict[str, Any]] = {}
    for order in orders:
        invoice = invoice_by_id.get(order.invoice_id) if order.invoice_id else None
        payment_summary = (
            payment_summary_by_invoice_id.get(invoice.id, {}) if invoice is not None else {}
        )
        invoice_payment_status = payment_summary.get("payment_status")
        meta_by_order_id[order.id] = {
            "invoice_number": invoice.invoice_number if invoice is not None else None,
            "invoice_payment_status": invoice_payment_status,
            "execution": derive_order_execution(
                order,
                invoice_payment_status=invoice_payment_status,
            ),
        }

    return meta_by_order_id
