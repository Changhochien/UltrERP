"""Seed the minimal development bootstrap data into a migrated database."""

from __future__ import annotations

import asyncio

from common.database import AsyncSessionLocal
from common.model_registry import register_all_models
from domains.settings.seed import seed_settings_if_empty
from domains.users.seed import seed_dev_users_if_empty

register_all_models()


async def bootstrap_dev_database() -> None:
    async with AsyncSessionLocal() as session:
        await seed_settings_if_empty(session)
        await seed_dev_users_if_empty(session)
        await session.commit()


def main() -> None:
    asyncio.run(bootstrap_dev_database())
    print(
        "Bootstrapped development database defaults: app settings plus dev users."
    )


if __name__ == "__main__":
    main()