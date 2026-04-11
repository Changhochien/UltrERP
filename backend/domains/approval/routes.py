"""Admin approval workflow routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from domains.approval.schemas import ApprovalListResponse, ApprovalResponse, ResolveRequest
from domains.approval.service import (
    ApprovalConflictError,
    ApprovalNotFoundError,
    list_approvals,
    resolve_approval,
)

router = APIRouter(dependencies=[Depends(require_role("finance"))])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(require_role("finance"))]


@router.get("", response_model=ApprovalListResponse)
async def list_approvals_endpoint(
    db: DbSession,
    user: CurrentUser,
    status: str | None = Query(default=None),
) -> ApprovalListResponse:
    import uuid
    tenant_id = uuid.UUID(user["tenant_id"])
    items = await list_approvals(db, tenant_id, status=status)
    await db.commit()
    return ApprovalListResponse(
        items=[ApprovalResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.post("/{approval_id}/resolve", response_model=ApprovalResponse)
async def resolve_approval_endpoint(
    approval_id: UUID,
    body: ResolveRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ApprovalResponse:
    try:
        import uuid as uuid_mod
        tenant_id = uuid_mod.UUID(current_user["tenant_id"])
        approval = await resolve_approval(
            db,
            approval_id,
            action=body.action,
            resolved_by=str(current_user.get("sub") or "unknown"),
            tenant_id=tenant_id,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Approval request not found") from exc
    except ApprovalConflictError as exc:
        await db.commit()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    await db.commit()
    return ApprovalResponse.model_validate(approval)
