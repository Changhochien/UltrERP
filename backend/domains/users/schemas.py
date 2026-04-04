"""Request / response schemas for user management."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreateRequest(BaseModel):
	email: EmailStr
	password: str = Field(min_length=8)
	display_name: str
	role: Literal["owner", "finance", "warehouse", "sales"]


class UserUpdateRequest(BaseModel):
	display_name: str | None = None
	role: Literal["owner", "finance", "warehouse", "sales"] | None = None
	status: Literal["active", "disabled"] | None = None
	password: str | None = Field(default=None, min_length=8)


class UserResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	email: str
	display_name: str
	role: str
	status: str
	created_at: datetime
	updated_at: datetime | None = None


class UserListResponse(BaseModel):
	items: list[UserResponse]
	total: int
