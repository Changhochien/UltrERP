"""Audit log query API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from domains.audit.queries import list_audit_logs
from domains.audit.schemas import AuditLogListResponse, AuditLogResponse

router = APIRouter(dependencies=[Depends(require_role("owner"))])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=AuditLogListResponse)
async def get_audit_logs(
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    actor_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
) -> AuditLogListResponse:
    """List audit log entries with pagination and filtering."""
    result = await list_audit_logs(
        db,
        page=page,
        page_size=page_size,
        entity_type=entity_type,
        action=action,
        actor_id=actor_id,
        actor_type=actor_type,
        entity_id=entity_id,
        created_after=created_after,
        created_before=created_before,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
