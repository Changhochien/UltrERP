"""Service layer for runtime-editable settings."""

from __future__ import annotations

import json
import logging
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import Settings, get_settings
from domains.audit.service import write_audit
from domains.settings.introspection import _read_settings_metadata
from domains.settings.models import AppSetting
from domains.settings.schemas import SettingItem, SettingSection

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "jwt_secret",
    "line_channel_secret",
    "line_channel_access_token",
    "object_store_secret_key",
    "object_store_access_key",
    "mcp_api_keys",
}
NULL_SENTINEL = "__NULL__"


def _bool_encode(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in ("true", "1", "yes", "on"):
        return "true"
    if normalized in ("false", "0", "no", "off"):
        return "false"
    raise HTTPException(422, detail=f"Invalid boolean value: {value!r}")


def _bool_decode(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in ("true", "1", "yes", "on"):
        return True
    if normalized in ("false", "0", "no", "off"):
        return False
    raise HTTPException(422, detail=f"Invalid boolean value in DB: {value!r}")


def _build_merged_dict() -> dict:
    """Build dict of all settings using Python attr names as keys; DB overrides env defaults."""
    meta = _read_settings_metadata()
    settings_obj = get_settings()
    result = {}
    for key in meta:
        result[key] = getattr(settings_obj, key, None)
    return result


def _revalidate_setting(key: str, raw_value: str) -> str:
    """Re-validate a raw string value against Pydantic validators.

    Return the cleaned string or raise.
    """
    all_settings = _build_merged_dict()
    meta = _read_settings_metadata()
    value_type = meta.get(key, {}).get("value_type", "str")
    nullable = meta.get(key, {}).get("nullable", False)

    if nullable and raw_value == NULL_SENTINEL:
        return NULL_SENTINEL

    if value_type == "bool":
        return _bool_encode(raw_value)

    if value_type == "int":
        try:
            int_val = int(raw_value)
        except ValueError:
            raise HTTPException(422, detail=f"Invalid integer: {raw_value!r}")
        all_settings[key] = int_val
    elif value_type in ("tuple", "json"):
        try:
            parsed = json.loads(raw_value)
            all_settings[key] = parsed
        except json.JSONDecodeError:
            raise HTTPException(422, detail=f"Invalid JSON: {raw_value!r}")
    else:
        all_settings[key] = raw_value

    try:
        validated = Settings.model_validate(all_settings)
        return str(getattr(validated, key))
    except ValidationError as e:
        raise HTTPException(422, detail=e.errors())


async def get_setting(db: AsyncSession, key: str) -> str:
    """Get a single setting value; DB value takes priority over env fallback."""
    meta = _read_settings_metadata()
    if key not in meta:
        raise HTTPException(404, detail=f"Unknown setting: {key}")

    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()

    if row is not None:
        return row.value

    settings_obj = get_settings()
    return str(getattr(settings_obj, key))


async def set_setting(db: AsyncSession, key: str, value: str, actor_id: UUID) -> SettingItem:
    """Update or insert a setting value, validate it, write audit log, return SettingItem."""
    meta = _read_settings_metadata()
    if key not in meta:
        raise HTTPException(404, detail=f"Unknown setting: {key}")

    if key in SENSITIVE_KEYS:
        raise HTTPException(
            403,
            detail=(
                f"Sensitive key '{key}' cannot be modified at runtime. "
                "Use environment variables."
            ),
        )

    nullable = meta[key].get("nullable", False)
    is_null = value == NULL_SENTINEL

    if not is_null:
        cleaned = _revalidate_setting(key, value)
    else:
        if not nullable:
            raise HTTPException(422, detail=f"Setting '{key}' is not nullable")
        cleaned = NULL_SENTINEL

    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    existing = result.scalar_one_or_none()
    old_value = existing.value if existing else None

    if existing:
        existing.value = cleaned
        existing.updated_by = actor_id
    else:
        new_row = AppSetting(key=key, value=cleaned, updated_by=actor_id)
        db.add(new_row)

    await write_audit(
        db,
        actor_id=str(actor_id),
        action="settings.update",
        entity_type="app_settings",
        entity_id=key,
        before_state={"key": key, "value": old_value} if old_value else None,
        after_state={"key": key, "value": cleaned},
        notes=f"Setting '{key}' updated by user {actor_id}",
    )
    await db.commit()

    get_settings.cache_clear()

    meta_info = meta[key]
    updated_at = existing.updated_at if existing else None
    updated_by_str = str(existing.updated_by) if existing and existing.updated_by else None

    return SettingItem(
        key=key,
        value=cleaned if not is_null else "",
        display_value="********" if meta_info["is_sensitive"] else cleaned,
        value_type=meta_info["value_type"],
        allowed_values=meta_info.get("allowed_values"),
        nullable=nullable,
        is_null=is_null,
        is_sensitive=meta_info["is_sensitive"],
        description=meta_info["description"],
        category=meta_info["category"],
        updated_at=updated_at,
        updated_by=updated_by_str,
    )


async def get_all_settings(db: AsyncSession) -> list[SettingSection]:
    """Return all settings grouped by category."""
    meta = _read_settings_metadata()

    result = await db.execute(select(AppSetting))
    db_rows = {row.key: row for row in result.scalars().all()}

    settings_obj = get_settings()

    sections: dict[str, dict] = {}
    for key, meta_info in meta.items():
        if meta_info["is_sensitive"]:
            continue

        category = meta_info["category"]
        if category not in sections:
            sections[category] = {
                "category": category,
                "description": category.capitalize(),
                "items": [],
            }

        db_row = db_rows.get(key)
        raw_value: str | None = db_row.value if db_row else None
        is_null = False

        if raw_value is None:
            env_val = getattr(settings_obj, key, None)
            if env_val is None:
                raw_value = NULL_SENTINEL
                is_null = True
            else:
                raw_value = (
                    str(env_val)
                    if not isinstance(env_val, bool)
                    else ("true" if env_val else "false")
                )
        elif raw_value == NULL_SENTINEL:
            is_null = True

        value_type = meta_info["value_type"]
        display_value = raw_value

        if value_type == "bool" and raw_value not in (NULL_SENTINEL,):
            display_value = str(_bool_decode(raw_value)).lower()

        updated_at = db_row.updated_at if db_row else None
        updated_by_str = str(db_row.updated_by) if db_row and db_row.updated_by else None

        sections[category]["items"].append(
            SettingItem(
                key=key,
                value=raw_value if not meta_info["is_sensitive"] else "********",
                display_value=display_value,
                value_type=value_type,
                allowed_values=meta_info.get("allowed_values"),
                nullable=meta_info.get("nullable", False),
                is_null=is_null,
                is_sensitive=meta_info["is_sensitive"],
                description=meta_info["description"],
                category=category,
                updated_at=updated_at,
                updated_by=updated_by_str,
            )
        )

    return [SettingSection(**s) for s in sections.values()]


async def reset_setting(db: AsyncSession, key: str, actor_id: UUID) -> None:
    """Delete a setting from DB, restoring env var default."""
    meta = _read_settings_metadata()
    if key not in meta:
        raise HTTPException(404, detail=f"Unknown setting: {key}")

    if key in SENSITIVE_KEYS:
        raise HTTPException(403, detail="Sensitive keys cannot be reset at runtime")

    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    existing = result.scalar_one_or_none()

    if existing is None:
        raise HTTPException(404, detail=f"Setting '{key}' has no DB override to reset")

    old_value = existing.value
    await db.delete(existing)

    await write_audit(
        db,
        actor_id=str(actor_id),
        action="settings.reset",
        entity_type="app_settings",
        entity_id=key,
        before_state={"key": key, "value": old_value},
        after_state={"key": key, "value": None},
        notes=f"Setting '{key}' reset to env default by user {actor_id}",
    )
    await db.commit()
    get_settings.cache_clear()
