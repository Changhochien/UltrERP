"""Authentication dependencies for FastAPI routes."""

from __future__ import annotations

import logging
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.database import get_db
from domains.audit.service import write_audit

_bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)
_API_ROLES = frozenset({"owner", "admin", "finance", "warehouse", "sales"})


async def get_current_user(
	request: Request,
	credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
	"""Decode JWT, return payload dict with sub, tenant_id, role.

	Stores tenant_id in request.state for access by get_tenant_id().
	"""
	if not credentials:
		raise HTTPException(status_code=401, detail="Not authenticated")
	try:
		payload = jwt.decode(
			credentials.credentials,
			settings.jwt_secret,
			algorithms=["HS256"],
			options={"require": ["exp", "sub", "tenant_id", "role"]},
		)
	except jwt.ExpiredSignatureError:
		raise HTTPException(status_code=401, detail="Token expired")
	except jwt.InvalidTokenError:
		raise HTTPException(status_code=401, detail="Invalid token")
	sub = payload.get("sub")
	tenant_id = payload.get("tenant_id")
	role = payload.get("role")
	if not isinstance(role, str) or role not in _API_ROLES:
		raise HTTPException(status_code=401, detail="Invalid token")
	try:
		UUID(sub)
		request.state.user_id = UUID(sub)
		request.state.tenant_id = UUID(tenant_id)
	except (TypeError, ValueError):
		raise HTTPException(status_code=401, detail="Invalid token")
	return payload


def require_role(*allowed_roles: str):
	"""Dependency factory: returns 403 if user role not in allowed_roles.

	``owner`` bypasses all role checks.
	"""

	async def _check(
		request: Request,
		session: AsyncSession = Depends(get_db),
		user: dict = Depends(get_current_user),
	) -> dict:
		if user["role"] == "owner":
			return user
		if user["role"] not in allowed_roles:
			try:
				await write_audit(
					session,
					actor_id=str(user.get("sub", "unknown")),
					action="auth.forbidden",
					entity_type="route",
					entity_id=request.url.path,
					before_state={"role": user.get("role")},
					after_state={
						"allowed_roles": list(allowed_roles),
						"method": request.method,
					},
					notes=f"Forbidden access attempt to {request.url.path}",
				)
				await session.commit()
			except Exception:
				logger.warning("Failed to audit forbidden access attempt", exc_info=True)
			raise HTTPException(status_code=403, detail="Forbidden")
		return user

	return _check


async def get_tenant_id_from_request(request: Request) -> UUID:
	"""Extract tenant_id from request state (set by get_current_user)."""
	if not hasattr(request.state, "tenant_id"):
		raise HTTPException(status_code=401, detail="Not authenticated")
	return request.state.tenant_id


async def get_user_id_from_request(request: Request) -> UUID:
	"""Extract user_id from request state (set by get_current_user)."""
	if not hasattr(request.state, "user_id"):
		raise HTTPException(status_code=401, detail="Not authenticated")
	return request.state.user_id
