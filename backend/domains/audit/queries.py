"""Audit log query service with pagination and filtering."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.audit_log import AuditLog
from common.tenant import DEFAULT_TENANT_ID


async def list_audit_logs(
    session: AsyncSession,
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
) -> dict[str, Any]:
    """Query audit logs with optional filtering and offset-based pagination."""
    base = select(AuditLog).where(AuditLog.tenant_id == DEFAULT_TENANT_ID)
    count_base = select(func.count(AuditLog.id)).where(
        AuditLog.tenant_id == DEFAULT_TENANT_ID,
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
    query = base.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(query)
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
