from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILES = (str(PROJECT_ROOT / ".env"), str(BACKEND_ROOT / ".env"))


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=ENV_FILES, extra="ignore")

	database_url: str = Field(
		default="postgresql+asyncpg://ultr_erp@localhost:5432/ultr_erp",
		validation_alias=AliasChoices("DATABASE_URL", "database_url"),
	)
	redis_url: str | None = Field(
		default=None,
		validation_alias=AliasChoices("REDIS_URL", "redis_url"),
	)
	app_env: str = Field(default="development", validation_alias=AliasChoices("APP_ENV", "app_env"))
	log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
		default="INFO",
		validation_alias=AliasChoices("LOG_LEVEL", "log_level"),
	)
	cors_origins: tuple[str, ...] = Field(
		default=("http://localhost:5173", "tauri://localhost"),
		validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"),
	)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()


settings = get_settings()
