"""Audit log query service with pagination and filtering."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.audit_log import AuditLog
from common.tenant import DEFAULT_TENANT_ID

AuditSortBy = Literal["created_at", "actor_id", "actor_type", "action", "entity_id"]
AuditSortDirection = Literal["asc", "desc"]

AUDIT_SORT_COLUMNS = {
    "created_at": AuditLog.created_at,
    "actor_id": AuditLog.actor_id,
    "actor_type": AuditLog.actor_type,
    "action": AuditLog.action,
    "entity_id": AuditLog.entity_id,
}


async def list_audit_logs(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
    *,
    page: int = 1,
    page_size: int = 50,
    entity_type: str | None = None,
    action: str | None = None,
    actor_id: str | None = None,
    actor_type: str | None = None,
    entity_id: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    sort_by: AuditSortBy = "created_at",
    sort_direction: AuditSortDirection = "desc",
) -> dict[str, Any]:
    """Query audit logs with optional filtering and offset-based pagination."""
    tid = tenant_id if tenant_id is not None else DEFAULT_TENANT_ID
    base = select(AuditLog).where(AuditLog.tenant_id == tid)
    count_base = select(func.count(AuditLog.id)).where(
        AuditLog.tenant_id == tid,
    )

    if entity_type is not None:
        base = base.where(AuditLog.entity_type == entity_type)
        count_base = count_base.where(AuditLog.entity_type == entity_type)
    if action is not None:
        base = base.where(AuditLog.action == action)
        count_base = count_base.where(AuditLog.action == action)
    if actor_id is not None:
        base = base.where(AuditLog.actor_id == actor_id)
        count_base = count_base.where(AuditLog.actor_id == actor_id)
    if actor_type is not None:
        base = base.where(AuditLog.actor_type == actor_type)
        count_base = count_base.where(AuditLog.actor_type == actor_type)
    if entity_id is not None:
        base = base.where(AuditLog.entity_id == entity_id)
        count_base = count_base.where(AuditLog.entity_id == entity_id)
    if created_after is not None:
        base = base.where(AuditLog.created_at >= created_after)
        count_base = count_base.where(AuditLog.created_at >= created_after)
    if created_before is not None:
        base = base.where(AuditLog.created_at <= created_before)
        count_base = count_base.where(AuditLog.created_at <= created_before)

    total_result = await session.execute(count_base)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    sort_column = AUDIT_SORT_COLUMNS[sort_by]
    sort_clause = sort_column.asc() if sort_direction == "asc" else sort_column.desc()
    query = base.order_by(sort_clause).offset(offset).limit(page_size)
    result = await session.execute(query)
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
