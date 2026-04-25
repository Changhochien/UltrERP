"""Physical count commands — session lifecycle management."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.models.audit_log import AuditLog
from common.models.inventory_stock import InventoryStock
from common.models.physical_count_line import PhysicalCountLine
from common.models.physical_count_session import (
    PhysicalCountSession,
    PhysicalCountSessionStatus,
)
from common.models.stock_adjustment import ReasonCode
from common.models.warehouse import Warehouse
from common.time import utc_now
from domains.inventory.domain import (
    PhysicalCountConflictError,
    PhysicalCountNotFoundError,
    PhysicalCountStateError,
)

from domains.inventory.commands._stock import create_stock_adjustment

if TYPE_CHECKING:
    pass


def _physical_count_status_value(status: PhysicalCountSessionStatus | str) -> str:
    return status.value if isinstance(status, PhysicalCountSessionStatus) else str(status)


def _serialize_physical_count_line(
    line: "PhysicalCountLine",
) -> dict[str, object | None]:
    return {
        "id": line.id,
        "product_id": line.product_id,
        "product_name": getattr(getattr(line, "product", None), "name", None),
        "product_code": getattr(getattr(line, "product", None), "code", None),
        "system_qty_snapshot": line.system_qty_snapshot,
        "counted_qty": line.counted_qty,
        "variance_qty": line.variance_qty,
        "notes": line.notes,
        "created_at": line.created_at,
        "updated_at": line.updated_at,
    }


def _serialize_physical_count_session(
    count_session: PhysicalCountSession,
    *,
    include_lines: bool,
) -> dict[str, object | None]:
    lines = list(getattr(count_session, "lines", []))
    lines.sort(
        key=lambda line: (
            getattr(getattr(line, "product", None), "name", "") or "",
            getattr(getattr(line, "product", None), "code", "") or "",
            str(line.product_id),
        )
    )
    counted_lines = sum(1 for line in lines if line.counted_qty is not None)
    variance_total = sum(int(line.variance_qty or 0) for line in lines)

    payload: dict[str, object | None] = {
        "id": count_session.id,
        "warehouse_id": count_session.warehouse_id,
        "warehouse_name": getattr(getattr(count_session, "warehouse", None), "name", None),
        "status": _physical_count_status_value(count_session.status),
        "created_by": count_session.created_by,
        "submitted_by": count_session.submitted_by,
        "submitted_at": count_session.submitted_at,
        "approved_by": count_session.approved_by,
        "approved_at": count_session.approved_at,
        "created_at": count_session.created_at,
        "updated_at": count_session.updated_at,
        "total_lines": len(lines),
        "counted_lines": counted_lines,
        "variance_total": variance_total,
    }
    if include_lines:
        payload["lines"] = [_serialize_physical_count_line(line) for line in lines]
    return payload


def _add_physical_count_audit(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor_id: str,
    count_session: PhysicalCountSession,
    action: str,
    before_state: dict[str, object] | None,
    after_state: dict[str, object],
    notes: str | None = None,
) -> None:
    session.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            entity_type="physical_count_session",
            entity_id=str(count_session.id),
            before_state=before_state,
            after_state=after_state,
            correlation_id=str(count_session.id),
            notes=notes,
        )
    )


async def _get_physical_count_session_record(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
) -> PhysicalCountSession | None:
    stmt = (
        select(PhysicalCountSession)
        .options(
            selectinload(PhysicalCountSession.warehouse),
            selectinload(PhysicalCountSession.lines).selectinload(PhysicalCountLine.product),
        )
        .where(
            PhysicalCountSession.id == session_id,
            PhysicalCountSession.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_physical_count_session(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID,
    actor_id: str,
) -> dict[str, object | None]:
    warehouse_stmt = select(Warehouse).where(
        Warehouse.id == warehouse_id,
        Warehouse.tenant_id == tenant_id,
    )
    warehouse_result = await session.execute(warehouse_stmt)
    warehouse = warehouse_result.scalar_one_or_none()
    if warehouse is None:
        raise PhysicalCountNotFoundError("Warehouse not found")

    existing_stmt = select(PhysicalCountSession.id).where(
        PhysicalCountSession.tenant_id == tenant_id,
        PhysicalCountSession.warehouse_id == warehouse_id,
        PhysicalCountSession.status.in_(
            [PhysicalCountSessionStatus.IN_PROGRESS, PhysicalCountSessionStatus.SUBMITTED]
        ),
    )
    existing = await session.execute(existing_stmt)
    if existing.scalar_one_or_none() is not None:
        raise PhysicalCountConflictError(
            "An open physical count session already exists for this warehouse"
        )

    stock_stmt = (
        select(InventoryStock)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.warehouse_id == warehouse_id,
        )
        .order_by(InventoryStock.product_id)
    )
    stock_rows = list((await session.execute(stock_stmt)).scalars().all())

    count_session = PhysicalCountSession(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        created_by=actor_id,
        status=PhysicalCountSessionStatus.IN_PROGRESS,
    )
    count_session.warehouse = warehouse
    try:
        session.add(count_session)
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await session.execute(existing_stmt)
        if existing.scalar_one_or_none() is not None:
            raise PhysicalCountConflictError(
                "An open physical count session already exists for this warehouse"
            )
        raise

    lines = [
        PhysicalCountLine(
            session_id=count_session.id,
            product_id=stock.product_id,
            system_qty_snapshot=stock.quantity,
            counted_qty=None,
            variance_qty=None,
        )
        for stock in stock_rows
    ]
    if lines:
        session.add_all(lines)

    _add_physical_count_audit(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        count_session=count_session,
        action="physical_count_session_created",
        before_state=None,
        after_state={
            "status": PhysicalCountSessionStatus.IN_PROGRESS.value,
            "warehouse_id": str(warehouse_id),
            "line_count": len(lines),
        },
    )
    await session.flush()

    refreshed = await _get_physical_count_session_record(session, tenant_id, count_session.id)
    if refreshed is None:
        raise PhysicalCountNotFoundError("Physical count session was not persisted")
    return _serialize_physical_count_session(refreshed, include_lines=True)


async def update_physical_count_line(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    line_id: uuid.UUID,
    *,
    counted_qty: int,
    notes: str | None,
) -> dict[str, object | None]:
    count_session = await _get_physical_count_session_record(session, tenant_id, session_id)
    if count_session is None:
        raise PhysicalCountNotFoundError("Physical count session not found")
    if count_session.status != PhysicalCountSessionStatus.IN_PROGRESS:
        raise PhysicalCountStateError("Only in-progress sessions can be edited")

    line = next((item for item in count_session.lines if item.id == line_id), None)
    if line is None:
        raise PhysicalCountNotFoundError("Physical count line not found")

    line.counted_qty = counted_qty
    line.variance_qty = counted_qty - line.system_qty_snapshot
    line.notes = notes
    await session.flush()
    return _serialize_physical_count_session(count_session, include_lines=True)


async def submit_physical_count_session(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    actor_id: str,
) -> dict[str, object | None]:
    count_session = await _get_physical_count_session_record(session, tenant_id, session_id)
    if count_session is None:
        raise PhysicalCountNotFoundError("Physical count session not found")
    if count_session.status == PhysicalCountSessionStatus.APPROVED:
        return _serialize_physical_count_session(count_session, include_lines=True)
    if count_session.status == PhysicalCountSessionStatus.SUBMITTED:
        return _serialize_physical_count_session(count_session, include_lines=True)

    if any(line.counted_qty is None for line in count_session.lines):
        raise PhysicalCountStateError("All count lines must be entered before submission")

    count_session.status = PhysicalCountSessionStatus.SUBMITTED
    count_session.submitted_by = actor_id
    count_session.submitted_at = utc_now()

    _add_physical_count_audit(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        count_session=count_session,
        action="physical_count_session_submitted",
        before_state={"status": PhysicalCountSessionStatus.IN_PROGRESS.value},
        after_state={
            "status": PhysicalCountSessionStatus.SUBMITTED.value,
            "variance_total": sum(int(line.variance_qty or 0) for line in count_session.lines),
        },
    )
    await session.flush()
    return _serialize_physical_count_session(count_session, include_lines=True)


async def approve_physical_count_session(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    actor_id: str,
) -> dict[str, object | None]:
    count_session = await _get_physical_count_session_record(session, tenant_id, session_id)
    if count_session is None:
        raise PhysicalCountNotFoundError("Physical count session not found")
    if count_session.status == PhysicalCountSessionStatus.APPROVED:
        return _serialize_physical_count_session(count_session, include_lines=True)
    if count_session.status != PhysicalCountSessionStatus.SUBMITTED:
        raise PhysicalCountStateError("Only submitted sessions can be approved")

    product_ids = [line.product_id for line in count_session.lines]
    live_stock_rows: list[InventoryStock] = []
    if product_ids:
        stock_stmt = (
            select(InventoryStock)
            .where(
                InventoryStock.tenant_id == tenant_id,
                InventoryStock.warehouse_id == count_session.warehouse_id,
                InventoryStock.product_id.in_(product_ids),
            )
            .with_for_update()
        )
        live_stock_rows = list((await session.execute(stock_stmt)).scalars().all())

    live_stock_by_product = {stock.product_id: stock for stock in live_stock_rows}
    for line in count_session.lines:
        live_qty = live_stock_by_product.get(line.product_id)
        current_qty = live_qty.quantity if live_qty is not None else 0
        if current_qty != line.system_qty_snapshot:
            product_name = (
                getattr(getattr(line, "product", None), "name", None) or str(line.product_id)
            )
            raise PhysicalCountConflictError(
                f"Physical count snapshot is stale for {product_name}"
            )

    adjustment_count = 0
    for line in count_session.lines:
        if line.counted_qty is None:
            raise PhysicalCountStateError("Cannot approve a session with incomplete count lines")
        line.variance_qty = line.counted_qty - line.system_qty_snapshot
        variance_qty = line.variance_qty
        if variance_qty is None:
            raise PhysicalCountStateError("Cannot approve a session with incomplete variance data")
        if variance_qty == 0:
            continue

        adjustment_count += 1
        note_parts = [f"Physical count session {count_session.id}"]
        if line.notes:
            note_parts.append(line.notes)
        await create_stock_adjustment(
            session,
            tenant_id,
            product_id=line.product_id,
            warehouse_id=count_session.warehouse_id,
            quantity_change=variance_qty,
            reason_code=ReasonCode.PHYSICAL_COUNT,
            actor_id=actor_id,
            notes=" - ".join(note_parts),
        )

    count_session.status = PhysicalCountSessionStatus.APPROVED
    count_session.approved_by = actor_id
    count_session.approved_at = utc_now()

    _add_physical_count_audit(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        count_session=count_session,
        action="physical_count_session_approved",
        before_state={"status": PhysicalCountSessionStatus.SUBMITTED.value},
        after_state={
            "status": PhysicalCountSessionStatus.APPROVED.value,
            "adjustment_count": adjustment_count,
        },
    )
    await session.flush()
    return _serialize_physical_count_session(count_session, include_lines=True)
