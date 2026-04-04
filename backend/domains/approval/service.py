"""Approval request service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from common.config import settings
from common.models.approval_request import ApprovalRequest
from common.tenant import DEFAULT_TENANT_ID
from domains.approval.executor import execute_approval_action
from domains.audit.service import write_audit


class ApprovalNotFoundError(Exception):
	"""Raised when approval request does not exist."""


class ApprovalConflictError(Exception):
	"""Raised when approval request cannot be resolved."""


async def create_approval(
	session,
	*,
	action: str,
	entity_type: str,
	entity_id: str | None,
	requested_by: str,
	requested_by_type: str,
	context: dict,
) -> ApprovalRequest:
	approval = ApprovalRequest(
		tenant_id=DEFAULT_TENANT_ID,
		action=action,
		entity_type=entity_type,
		entity_id=entity_id,
		requested_by=requested_by,
		requested_by_type=requested_by_type,
		context=context,
		status="pending",
		expires_at=datetime.now(tz=UTC) + timedelta(hours=settings.approval_expiry_hours),
	)
	session.add(approval)
	await session.flush()
	return approval


async def list_approvals(
	session,
	*,
	status: str | None = None,
) -> list[ApprovalRequest]:
	stmt = (
		select(ApprovalRequest)
		.where(ApprovalRequest.tenant_id == DEFAULT_TENANT_ID)
		.order_by(ApprovalRequest.created_at.desc())
	)
	result = await session.execute(stmt)
	items = list(result.scalars().all())
	now = datetime.now(tz=UTC)
	for item in items:
		if item.status == "pending" and item.expires_at <= now:
			item.status = "expired"
			item.resolved_by = None
			item.resolved_at = now
	await session.flush()
	if status is None:
		return items
	return [item for item in items if item.status == status]


async def resolve_approval(
	session,
	approval_id: uuid.UUID,
	*,
	action: str,
	resolved_by: str,
) -> ApprovalRequest:
	stmt = select(ApprovalRequest).where(
		ApprovalRequest.id == approval_id,
		ApprovalRequest.tenant_id == DEFAULT_TENANT_ID,
	)
	result = await session.execute(stmt)
	approval = result.scalar_one_or_none()
	if approval is None:
		raise ApprovalNotFoundError()

	now = datetime.now(tz=UTC)
	if approval.status != "pending":
		raise ApprovalConflictError("Approval request has already been resolved")
	if approval.expires_at <= now:
		approval.status = "expired"
		approval.resolved_by = None
		approval.resolved_at = now
		await session.flush()
		raise ApprovalConflictError("Approval request has expired")

	before_state = {"status": approval.status, "entity_id": approval.entity_id}
	approval.status = "approved" if action == "approve" else "rejected"
	approval.resolved_by = resolved_by
	approval.resolved_at = now

	if action == "approve":
		await execute_approval_action(session, approval)

	await write_audit(
		session,
		actor_id=resolved_by,
		action=f"approval.{action}",
		entity_type="approval_request",
		entity_id=str(approval.id),
		before_state=before_state,
		after_state={"status": approval.status, "entity_id": approval.entity_id},
		notes=f"Approval request {action}d",
	)
	await session.flush()
	return approval