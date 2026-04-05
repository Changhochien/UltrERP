"""Admin user management routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from common.database import get_db
from domains.users.schemas import (
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from domains.users.service import create_user, get_user, list_users, update_user

router = APIRouter(dependencies=[Depends(require_role("owner"))])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(require_role("owner"))]


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user_endpoint(
    body: UserCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> UserResponse:
    try:
        user = await create_user(
            db,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            role=body.role,
            actor_id=str(current_user.get("sub") or "unknown"),
        )
        await db.commit()
        return UserResponse.model_validate(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A user with this email already exists")


@router.get("/", response_model=UserListResponse)
async def list_users_endpoint(db: DbSession) -> UserListResponse:
    users = await list_users(db)
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=len(users),
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_endpoint(user_id: UUID, db: DbSession) -> UserResponse:
    user = await get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user_endpoint(
    user_id: UUID,
    body: UserUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> UserResponse:
    user = await update_user(
        db,
        user_id,
        display_name=body.display_name,
        role=body.role,
        status=body.status,
        password=body.password,
        actor_id=str(current_user.get("sub") or "unknown"),
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    await db.commit()
    return UserResponse.model_validate(user)
