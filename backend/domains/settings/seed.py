"""Seed non-sensitive settings from introspection into app_settings on startup."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.settings.introspection import _read_settings_metadata
from domains.settings.models import AppSetting

logger = logging.getLogger(__name__)


async def seed_settings_if_empty(db: AsyncSession) -> None:
    """Seed app_settings from introspection if the table is empty."""
    count_result = await db.execute(select(func.count()).select_from(AppSetting))
    count = count_result.scalar()

    if count > 0:
        logger.info("app_settings table already has %d rows; skipping seed", count)
        return

    meta = _read_settings_metadata()
    seeded = 0

    for key, meta_info in meta.items():
        if meta_info.get("is_sensitive", False):
            continue

        nullable = meta_info.get("nullable", False)
        value_type = meta_info["value_type"]

        if nullable:
            value = "__NULL__"
        elif value_type == "bool":
            value = "false"
        elif value_type == "int":
            value = "0"
        elif value_type in ("tuple", "json"):
            value = "[]"
        else:
            value = ""

        db.add(AppSetting(key=key, value=value))
        seeded += 1

    await db.commit()
    logger.info("Seeded %d non-sensitive settings into app_settings", seeded)
