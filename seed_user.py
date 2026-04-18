import asyncio

from common.database import AsyncSessionLocal
from common.model_registry import register_all_models
from domains.users.service import create_user

register_all_models()


async def seed():
    async with AsyncSessionLocal() as session:
        user = await create_user(
            session,
            email="admin@ultr.dev",
            password="admin123",
            display_name="Admin",
            role="owner",
            actor_id="system",
        )
        await session.commit()
        print(f"Created user: {user.email} / admin123")

asyncio.run(seed())
