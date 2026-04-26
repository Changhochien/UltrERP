"""Payment terms template API routes (Epic 25)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from domains.settings.payment_terms_service import (
    InvalidInstallmentTotalError,
    TemplateNotFoundError,
    create_template,
    get_template,
    list_templates,
    update_template,
)
from domains.settings.schemas_payment_terms import (
    PaymentTermsTemplateCreate,
    PaymentTermsTemplateListResponse,
    PaymentTermsTemplateResponse,
    PaymentTermsTemplateUpdate,
)

router = APIRouter(
    prefix="/payment-terms-templates",
    tags=["payment-terms-templates"],
    dependencies=[Depends(require_role("owner", "admin", "finance"))],
)

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(require_role("owner", "admin", "finance"))]


def _tenant_id(current_user: CurrentUser) -> uuid.UUID:
    return uuid.UUID(current_user["tenant_id"])


def _detail_dicts(data: PaymentTermsTemplateCreate | PaymentTermsTemplateUpdate) -> list[dict] | None:
    details = data.details
    if details is None:
        return None
    return [detail.model_dump(mode="python") for detail in details]


@router.get("", response_model=PaymentTermsTemplateListResponse)
async def list_payment_terms_templates_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    include_inactive: bool = Query(default=False),
) -> PaymentTermsTemplateListResponse:
    tenant_id = _tenant_id(current_user)
    items = await list_templates(db, tenant_id, include_inactive=include_inactive)
    return PaymentTermsTemplateListResponse(
        items=[PaymentTermsTemplateResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.get("/{template_id}", response_model=PaymentTermsTemplateResponse)
async def get_payment_terms_template_endpoint(
    template_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> PaymentTermsTemplateResponse:
    tenant_id = _tenant_id(current_user)
    try:
        template = await get_template(db, template_id, tenant_id)
        return PaymentTermsTemplateResponse.model_validate(template)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("", response_model=PaymentTermsTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_terms_template_endpoint(
    data: PaymentTermsTemplateCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> PaymentTermsTemplateResponse:
    tenant_id = _tenant_id(current_user)
    try:
        template = await create_template(
            db,
            tenant_id,
            data.template_name,
            _detail_dicts(data) or [],
            description=data.description,
            allocate_payment=data.allocate_payment_based_on_payment_terms,
            legacy_code=data.legacy_code,
        )
        await db.commit()
        return PaymentTermsTemplateResponse.model_validate(template)
    except InvalidInstallmentTotalError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment terms template name already exists.",
        ) from exc


@router.patch("/{template_id}", response_model=PaymentTermsTemplateResponse)
async def update_payment_terms_template_endpoint(
    template_id: uuid.UUID,
    data: PaymentTermsTemplateUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> PaymentTermsTemplateResponse:
    tenant_id = _tenant_id(current_user)
    try:
        template = await update_template(
            db,
            tenant_id,
            template_id,
            template_name=data.template_name,
            description=data.description,
            allocate_payment=data.allocate_payment_based_on_payment_terms,
            is_active=data.is_active,
            legacy_code=data.legacy_code,
            details=_detail_dicts(data),
        )
        await db.commit()
        return PaymentTermsTemplateResponse.model_validate(template)
    except TemplateNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidInstallmentTotalError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment terms template name already exists.",
        ) from exc
