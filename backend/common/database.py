from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from common.config import settings

metadata = MetaData(
	naming_convention={
		"ix": "ix_%(column_0_label)s",
		"uq": "uq_%(table_name)s_%(column_0_name)s",
		"ck": "ck_%(table_name)s_%(constraint_name)s",
		"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
		"pk": "pk_%(table_name)s",
	}
)


class Base(AsyncAttrs, DeclarativeBase):
	metadata = metadata


engine = create_async_engine(
	settings.database_url,
	connect_args={"statement_cache_size": 0, "timeout": 5, "command_timeout": 30},
	pool_pre_ping=True,
	pool_size=20,
	max_overflow=30,
	pool_recycle=1800,
	pool_timeout=30,
)

AsyncSessionLocal = async_sessionmaker(
	bind=engine,
	class_=AsyncSession,
	expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
	async with AsyncSessionLocal() as session:
		yield session
