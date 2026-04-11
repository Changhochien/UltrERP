"""User CRUD service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.user import User
from common.tenant import DEFAULT_TENANT_ID
from domains.audit.service import write_audit
from domains.users.auth import hash_password


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
    role: str,
    actor_id: str = "system",
    tenant_id: uuid.UUID | None = None,
) -> User:
    """Create a new user. Raises IntegrityError on duplicate email."""
    tid = tenant_id or DEFAULT_TENANT_ID
    user = User(
        tenant_id=tid,
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        role=role,
        status="active",
        created_at=datetime.now(tz=UTC),
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError:
        raise

    await write_audit(
        session,
        actor_id=actor_id,
        action="user.create",
        entity_type="user",
        entity_id=str(user.id),
        after_state={"email": email, "display_name": display_name, "role": role},
    )
    return user


async def list_users(session: AsyncSession, tenant_id: uuid.UUID | None = None) -> list[User]:
    tid = tenant_id or DEFAULT_TENANT_ID
    stmt = select(User).where(User.tenant_id == tid).order_by(User.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_user(session: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID | None = None) -> User | None:
    tid = tenant_id or DEFAULT_TENANT_ID
    stmt = select(User).where(
        User.id == user_id,
        User.tenant_id == tid,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    display_name: str | None = None,
    role: str | None = None,
    status: str | None = None,
    password: str | None = None,
    actor_id: str = "system",
    tenant_id: uuid.UUID | None = None,
) -> User | None:
    user = await get_user(session, user_id, tenant_id=tenant_id)
    if user is None:
        return None

    before: dict[str, str] = {}
    after: dict[str, str] = {}

    if display_name is not None:
        before["display_name"] = user.display_name
        user.display_name = display_name
        after["display_name"] = display_name

    if role is not None:
        before["role"] = user.role
        user.role = role
        after["role"] = role

    if status is not None:
        before["status"] = user.status
        user.status = status
        after["status"] = status

    if password is not None:
        user.password_hash = hash_password(password)
        after["password"] = "***changed***"

    if after:
        await write_audit(
            session,
            actor_id=actor_id,
            action="user.update",
            entity_type="user",
            entity_id=str(user.id),
            before_state=before,
            after_state=after,
        )

    await session.flush()
    return user


async def get_user_by_email(session: AsyncSession, email: str, tenant_id: uuid.UUID | None = None) -> User | None:
    tid = tenant_id or DEFAULT_TENANT_ID
    stmt = select(User).where(
        func.lower(User.email) == email.lower(),
        User.tenant_id == tid,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
