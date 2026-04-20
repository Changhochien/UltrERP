from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from common.database import AsyncSessionLocal, engine


@asynccontextmanager
async def isolated_async_session() -> AsyncIterator[AsyncSession]:
    """Yield a session whose commits stay inside an outer test transaction."""
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSessionLocal(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        await session.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()
        await engine.dispose()