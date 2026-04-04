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
	posthog_api_key: str | None = Field(
		default=None,
		validation_alias=AliasChoices("POSTHOG_API_KEY", "posthog_api_key"),
	)
	posthog_project_id: str | None = Field(
		default=None,
		validation_alias=AliasChoices("POSTHOG_PROJECT_ID", "posthog_project_id"),
	)
	posthog_host: str = Field(
		default="https://us.posthog.com",
		validation_alias=AliasChoices("POSTHOG_HOST", "posthog_host"),
	)
	mcp_api_keys: str = Field(
		default="",
		validation_alias=AliasChoices("MCP_API_KEYS", "mcp_api_keys"),
	)
	line_channel_access_token: str | None = Field(
		default=None,
		validation_alias=AliasChoices("LINE_CHANNEL_ACCESS_TOKEN", "line_channel_access_token"),
	)
	line_channel_secret: str | None = Field(
		default=None,
		validation_alias=AliasChoices("LINE_CHANNEL_SECRET", "line_channel_secret"),
	)
	line_staff_group_id: str | None = Field(
		default=None,
		validation_alias=AliasChoices("LINE_STAFF_GROUP_ID", "line_staff_group_id"),
	)
	public_base_url: str = Field(
		default="http://localhost:8000",
		validation_alias=AliasChoices("PUBLIC_BASE_URL", "public_base_url"),
	)
	object_store_endpoint_url: str | None = Field(
		default=None,
		validation_alias=AliasChoices("OBJECT_STORE_ENDPOINT_URL", "object_store_endpoint_url"),
	)
	object_store_access_key: str | None = Field(
		default=None,
		validation_alias=AliasChoices("OBJECT_STORE_ACCESS_KEY", "object_store_access_key"),
	)
	object_store_secret_key: str | None = Field(
		default=None,
		validation_alias=AliasChoices("OBJECT_STORE_SECRET_KEY", "object_store_secret_key"),
	)
	object_store_region: str = Field(
		default="us-east-1",
		validation_alias=AliasChoices("OBJECT_STORE_REGION", "object_store_region"),
	)
	invoice_artifact_storage_policy: str = Field(
		default="standard",
		validation_alias=AliasChoices(
			"INVOICE_ARTIFACT_STORAGE_POLICY",
			"invoice_artifact_storage_policy",
		),
	)
	invoice_artifact_retention_class: str = Field(
		default="legal-10y",
		validation_alias=AliasChoices(
			"INVOICE_ARTIFACT_RETENTION_CLASS",
			"invoice_artifact_retention_class",
		),
	)
	invoice_seller_ban: str = Field(
		default="00000000",
		validation_alias=AliasChoices("INVOICE_SELLER_BAN", "invoice_seller_ban"),
	)
	invoice_seller_name: str = Field(
		default="UltrERP",
		validation_alias=AliasChoices("INVOICE_SELLER_NAME", "invoice_seller_name"),
	)
	egui_tracking_enabled: bool = Field(
		default=False,
		validation_alias=AliasChoices("EGUI_TRACKING_ENABLED", "egui_tracking_enabled"),
	)
	egui_submission_mode: Literal["mock", "live"] = Field(
		default="mock",
		validation_alias=AliasChoices("EGUI_SUBMISSION_MODE", "egui_submission_mode"),
	)
	sitemap_cache_ttl: int = Field(
		default=3600,
		validation_alias=AliasChoices("SITEMAP_CACHE_TTL", "sitemap_cache_ttl"),
	)
	jwt_secret: str = Field(
		...,
		validation_alias=AliasChoices("JWT_SECRET", "jwt_secret"),
		min_length=32,
	)
	jwt_access_token_minutes: int = Field(
		default=480,
		ge=1,
		validation_alias=AliasChoices("JWT_ACCESS_TOKEN_MINUTES", "jwt_access_token_minutes"),
	)
	approval_threshold_inventory_adjust: int = Field(
		default=100,
		ge=1,
		validation_alias=AliasChoices(
			"APPROVAL_THRESHOLD_INVENTORY_ADJUST",
			"approval_threshold_inventory_adjust",
		),
	)
	approval_expiry_hours: int = Field(
		default=24,
		ge=1,
		validation_alias=AliasChoices(
			"APPROVAL_EXPIRY_HOURS",
			"approval_expiry_hours",
		),
	)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()


def _get_lazy_settings() -> Settings:
	"""Lazy proxy — settings are resolved on first attribute access."""
	return get_settings()


class _LazySettings:
	"""Thin proxy so module-level ``settings`` doesn't evaluate until first use."""

	def __getattr__(self, name: str) -> object:
		return getattr(get_settings(), name)


settings: Settings = _LazySettings()  # type: ignore[assignment]
