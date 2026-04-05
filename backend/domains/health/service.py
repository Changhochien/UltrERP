from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def health_status(session: AsyncSession) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}
