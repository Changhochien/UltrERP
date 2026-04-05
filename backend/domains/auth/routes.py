"""Auth routes — login and current-user endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import get_current_user
from common.config import settings
from common.database import get_db
from domains.auth.schemas import LoginRequest, TokenResponse
from domains.users.auth import verify_password
from domains.users.schemas import UserResponse
from domains.users.service import get_user, get_user_by_email

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    """Authenticate with email + password and receive a JWT."""
    user = await get_user_by_email(db, body.email)
    if (
        user is None
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.status != "active":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "exp": datetime.now(tz=UTC) + timedelta(minutes=settings.jwt_access_token_minutes),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(
    db: DbSession,
    current_user: dict = Depends(get_current_user),
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    from uuid import UUID

    user = await get_user(db, UUID(current_user["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return UserResponse.model_validate(user)
