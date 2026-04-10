"""Settings API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from domains.settings.schemas import SettingItem, SettingSection, SettingUpdate
from domains.settings.service import get_all_settings, reset_setting, set_setting

router = APIRouter(dependencies=[Depends(require_role("owner", "admin", "finance"))])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(require_role("owner", "admin", "finance"))]


@router.get("", response_model=list[SettingSection])
@router.get("/", response_model=list[SettingSection], include_in_schema=False)
async def list_settings(db: DbSession) -> list[SettingSection]:
    """List all settings grouped by category."""
    return await get_all_settings(db)


@router.get("/categories", response_model=list[dict])
async def list_categories(db: DbSession) -> list[dict]:
    """List all setting categories with descriptions."""
    sections = await get_all_settings(db)
    return [{"category": s.category, "description": s.description} for s in sections]


@router.get("/{key}", response_model=SettingItem)
async def get_setting_endpoint(key: str, db: DbSession) -> SettingItem:
    """Get a single setting by key."""
    sections = await get_all_settings(db)
    for section in sections:
        for item in section.items:
            if item.key == key:
                return item
    raise HTTPException(404, detail=f"Setting not found: {key}")


@router.patch("/{key}", response_model=SettingItem)
async def update_setting_endpoint(
    key: str,
    body: SettingUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> SettingItem:
    """Update a single setting."""
    import uuid
    actor_id = UUID(current_user["sub"])
    tenant_id = uuid.UUID(current_user["tenant_id"])
    return await set_setting(db, key, body.value, actor_id, tenant_id=tenant_id)


@router.delete("/{key}", status_code=204)
async def reset_setting_endpoint(
    key: str,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Reset a setting to its env var default."""
    import uuid
    actor_id = UUID(current_user["sub"])
    tenant_id = uuid.UUID(current_user["tenant_id"])
    await reset_setting(db, key, actor_id, tenant_id=tenant_id)
