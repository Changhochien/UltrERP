"""Reports API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import get_current_user
from common.database import get_db
from common.tenant import get_tenant_id
from domains.reports.schemas import APAgingReportResponse, ARAgingReportResponse
from domains.reports.services import get_ap_aging_report, get_ar_aging_report

router = APIRouter(dependencies=[Depends(get_current_user)])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentTenant = Annotated[uuid.UUID, Depends(get_tenant_id)]


@router.get("/ar-aging", response_model=ARAgingReportResponse)
async def get_ar_aging_endpoint(
    session: DbSession,
    tenant_id: CurrentTenant,
) -> ARAgingReportResponse:
    return await get_ar_aging_report(session, tenant_id)


@router.get("/ap-aging", response_model=APAgingReportResponse)
async def get_ap_aging_endpoint(
    session: DbSession,
    tenant_id: CurrentTenant,
) -> APAgingReportResponse:
    return await get_ap_aging_report(session, tenant_id)
