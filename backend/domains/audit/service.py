"""Centralized audit log service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from common.models.audit_log import AuditLog
from common.tenant import DEFAULT_TENANT_ID


async def write_audit(
	session: AsyncSession,
	*,
	actor_id: str,
	actor_type: str = "user",
	action: str,
	entity_type: str,
	entity_id: str,
	before_state: dict[str, Any] | None = None,
	after_state: dict[str, Any] | None = None,
	correlation_id: str | None = None,
	notes: str | None = None,
) -> AuditLog:
	"""Create an audit log entry with DEFAULT_TENANT_ID."""
	entry = AuditLog(
		tenant_id=DEFAULT_TENANT_ID,
		actor_id=actor_id,
		actor_type=actor_type,
		action=action,
		entity_type=entity_type,
		entity_id=entity_id,
		before_state=before_state,
		after_state=after_state,
		correlation_id=correlation_id,
		notes=notes,
	)
	session.add(entry)
	return entry
