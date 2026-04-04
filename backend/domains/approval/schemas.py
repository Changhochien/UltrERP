"""Pydantic schemas for approval workflow routes."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ApprovalRequiredResponse(BaseModel):
	approval_required: bool
	approval_request_id: UUID
	status: Literal["pending"]


class ApprovalResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	tenant_id: UUID
	action: str
	entity_type: str
	entity_id: str | None
	requested_by: str
	requested_by_type: str
	context: dict
	status: Literal["pending", "approved", "rejected", "expired"]
	resolved_by: str | None
	resolved_at: datetime | None
	expires_at: datetime
	created_at: datetime


class ApprovalListResponse(BaseModel):
	items: list[ApprovalResponse]
	total: int


class ResolveRequest(BaseModel):
	action: Literal["approve", "reject"]