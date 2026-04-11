"""Audit log query API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from domains.audit.queries import list_audit_logs
from domains.audit.schemas import AuditLogListResponse, AuditLogResponse

router = APIRouter(dependencies=[Depends(require_role("admin", "owner"))])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(require_role("admin", "owner"))]
AuditSortBy = Literal["created_at", "actor_id", "actor_type", "action", "entity_id"]
AuditSortDirection = Literal["asc", "desc"]


@router.get("/", response_model=AuditLogListResponse)
async def get_audit_logs(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    actor_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    sort_by: AuditSortBy = Query(default="created_at"),
    sort_direction: AuditSortDirection = Query(default="desc"),
) -> AuditLogListResponse:
    """List audit log entries with pagination and filtering."""
    import uuid
    tenant_id = uuid.UUID(current_user["tenant_id"])
    result = await list_audit_logs(
        db,
        tenant_id,
        page=page,
        page_size=page_size,
        entity_type=entity_type,
        action=action,
        actor_id=actor_id,
        actor_type=actor_type,
        entity_id=entity_id,
        created_after=created_after,
        created_before=created_before,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
