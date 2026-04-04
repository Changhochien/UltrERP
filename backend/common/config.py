import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILES = (str(PROJECT_ROOT / ".env"), str(BACKEND_ROOT / ".env"))


def _normalize_origins(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
	return tuple(
		item
		for item in (str(value).strip() for value in values)
		if item
	)


def _parse_cors_origins(raw: str) -> tuple[str, ...]:
	raw = raw.strip()
	if not raw:
		return ()

	try:
		decoded = json.loads(raw)
	except json.JSONDecodeError:
		trimmed = raw.removeprefix("[").removesuffix("]")
		if not trimmed:
			return ()
		return tuple(
			item
			for item in (part.strip().strip('"\'') for part in trimmed.split(","))
			if item
		)

	if isinstance(decoded, str):
		decoded = decoded.strip()
		return (decoded,) if decoded else ()

	if isinstance(decoded, (list, tuple)):
		return _normalize_origins(decoded)

	raise ValueError(
		"CORS_ORIGINS must be a JSON array, a single origin, or a comma-separated list."
	)


def _parse_string_tuple(raw: str) -> tuple[str, ...]:
	raw = raw.strip()
	if not raw:
		return ()

	try:
		decoded = json.loads(raw)
	except json.JSONDecodeError:
		trimmed = raw.removeprefix("[").removesuffix("]")
		if not trimmed:
			return ()
		return tuple(
			item
			for item in (part.strip().strip('"\'') for part in trimmed.split(","))
			if item
		)

	if isinstance(decoded, str):
		decoded = decoded.strip()
		return (decoded,) if decoded else ()

	if isinstance(decoded, (list, tuple)):
		return _normalize_origins(tuple(str(item) for item in decoded))

	raise ValueError("Expected a JSON array, a single value, or a comma-separated list.")


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
	cors_origins: Annotated[tuple[str, ...], NoDecode] = Field(
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
	legacy_import_data_dir: str = Field(
		default=str(PROJECT_ROOT / "legacy-migration-pipeline" / "extracted_data"),
		validation_alias=AliasChoices("LEGACY_IMPORT_DATA_DIR", "legacy_import_data_dir"),
	)
	legacy_import_schema: str = Field(
		default="raw_legacy",
		validation_alias=AliasChoices("LEGACY_IMPORT_SCHEMA", "legacy_import_schema"),
	)
	legacy_import_required_tables: Annotated[tuple[str, ...], NoDecode] = Field(
		default=("tbscust", "tbsstock", "tbsslipx", "tbsslipdtx", "tbsstkhouse"),
		validation_alias=AliasChoices(
			"LEGACY_IMPORT_REQUIRED_TABLES",
			"legacy_import_required_tables",
		),
	)

	@field_validator("cors_origins", mode="before")
	@classmethod
	def _validate_cors_origins(cls, value: Any) -> tuple[str, ...] | Any:
		if isinstance(value, (list, tuple)):
			return _normalize_origins(value)
		if isinstance(value, str):
			return _parse_cors_origins(value)
		return value

	@field_validator("legacy_import_required_tables", mode="before")
	@classmethod
	def _validate_legacy_import_required_tables(cls, value: Any) -> tuple[str, ...] | Any:
		if isinstance(value, (list, tuple)):
			return _normalize_origins(tuple(str(item) for item in value))
		if isinstance(value, str):
			return _parse_string_tuple(value)
		return value


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
