"""Pydantic schemas for the settings domain."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SettingItem(BaseModel):
    key: str
    value: str
    display_value: str
    value_type: Literal["str", "int", "bool", "tuple", "json", "literal"]
    allowed_values: list[str] | None
    nullable: bool
    is_null: bool
    is_sensitive: bool
    description: str
    category: str
    updated_at: datetime | None
    updated_by: str | None


class SettingSection(BaseModel):
    category: str
    description: str
    items: list[SettingItem]


class SettingUpdate(BaseModel):
    value: str
