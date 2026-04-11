"""Request-scoped tenant context for multi-tenancy.

Sets ``app.tenant_id`` as a PostgreSQL session variable with
``set_config(..., true)``, scoping tenant isolation to the current transaction.
"""

from __future__ import annotations

import uuid

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Default tenant for solo / team mode until real tenant resolution exists.
DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def set_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Set the tenant context for the current transaction."""
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )


async def get_tenant_id(request: Request) -> uuid.UUID:
    """Return tenant_id stored in request state by get_current_user()."""
    if hasattr(request.state, "tenant_id"):
        return request.state.tenant_id
    return DEFAULT_TENANT_ID


def get_tenant_id_or_default(request: Request) -> uuid.UUID:
    """Return tenant_id from request state, or default (sync version for module-level calls)."""
    if hasattr(request.state, "tenant_id"):
        return request.state.tenant_id
    return DEFAULT_TENANT_ID
