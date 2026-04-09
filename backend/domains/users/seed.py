"""Seed default dev users on startup if they don't exist."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.user import User
from domains.users.service import create_user

logger = logging.getLogger(__name__)

DEV_USERS = [
    {"email": "admin@ultr.dev", "password": "admin123", "display_name": "Admin User", "role": "admin"},
    {"email": "owner@ultr.dev", "password": "owner123", "display_name": "Owner User", "role": "owner"},
]


async def seed_dev_users_if_empty(db: AsyncSession) -> None:
    """Create default dev users if they don't already exist."""
    for user_data in DEV_USERS:
        result = await db.execute(
            select(func.count()).select_from(User).where(
                func.lower(User.email) == user_data["email"].lower()
            )
        )
        count = result.scalar()
        if count and count > 0:
            logger.info("User %s already exists; skipping", user_data["email"])
            continue
        try:
            await create_user(db, **user_data, actor_id="seed-script")
            logger.info("Created dev user: %s / %s", user_data["email"], user_data["password"])
        except IntegrityError:
            logger.warning("User %s already exists (race); skipping", user_data["email"])
