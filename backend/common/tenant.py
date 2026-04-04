"""Request-scoped tenant context for multi-tenancy.

Sets ``app.tenant_id`` as a PostgreSQL session variable with
``set_config(..., true)``, scoping tenant isolation to the current transaction.
"""

from __future__ import annotations

import uuid

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
