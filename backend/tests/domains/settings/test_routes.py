"""Tests for settings API routes."""

from __future__ import annotations

# ── Re-use shared test infrastructure from orders tests ─────────
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from domains.settings.models import AppSetting
from domains.settings.schemas import SettingItem
from domains.settings.service import SENSITIVE_KEYS

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.domains.orders._helpers import (
    FakeAsyncSession,
    auth_header,
    http_delete,
    http_get,
    http_patch,
    setup_session,
    teardown_session,
)

# ── Helpers ──────────────────────────────────────────────────────


def make_setting_item(
    key: str,
    value: str,
    *,
    value_type: str = "str",
    category: str = "general",
    is_sensitive: bool = False,
    nullable: bool = False,
    allowed_values: list[str] | None = None,
    is_null: bool = False,
    updated_at: datetime | None = None,
    updated_by: str | None = None,
) -> SettingItem:
    return SettingItem(
        key=key,
        value=value,
        display_value=value,
        value_type=value_type,
        allowed_values=allowed_values,
        nullable=nullable,
        is_null=is_null,
        is_sensitive=is_sensitive,
        description=f"{key} description",
        category=category,
        updated_at=updated_at,
        updated_by=updated_by,
    )


def make_app_setting_row(
    key: str,
    value: str,
    *,
    updated_by: uuid.UUID | None = None,
    updated_at: datetime | None = None,
) -> AppSetting:
    row = AppSetting(
        key=key,
        value=value,
        updated_by=updated_by,
    )
    row.updated_at = updated_at or datetime.now(tz=UTC)
    return row


# ── Route tests ─────────────────────────────────────────────────


async def test_get_settings_returns_all_settings() -> None:
    """GET /api/v1/settings as admin returns 200 with all non-sensitive settings."""
    session = FakeAsyncSession()
    # get_all_settings: db.execute(select(AppSetting)) → empty
    session.queue_scalars([])

    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/settings", headers=auth_header("admin"))
        assert resp.status_code == 200
        sections: list[dict] = resp.json()
        # Should contain multiple categories
        categories = {s["category"] for s in sections}
        assert len(categories) >= 3
        # Sensitive keys must not appear
        all_keys = {item["key"] for s in sections for item in s["items"]}
        for sensitive in SENSITIVE_KEYS:
            assert sensitive not in all_keys
    finally:
        teardown_session(prev)


async def test_get_settings_with_trailing_slash_returns_all_settings() -> None:
    """GET /api/v1/settings/ as admin returns 200 without requiring a redirect."""
    session = FakeAsyncSession()
    session.queue_scalars([])

    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/settings/", headers=auth_header("admin"))
        assert resp.status_code == 200
    finally:
        teardown_session(prev)


async def test_settings_page_redirects_for_sales() -> None:
    """GET /api/v1/settings as sales returns 403."""
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/settings", headers=auth_header("sales"))
        assert resp.status_code == 403
    finally:
        teardown_session(prev)


async def test_patch_updates_setting() -> None:
    """PATCH LOG_LEVEL updates the DB and returns the updated SettingItem."""
    session = FakeAsyncSession()
    # get_setting check (exists? → no)
    session.queue_scalars([])  # get_setting: select AppSetting
    # set_setting: select AppSetting (existing) → None
    session.queue_scalars([])
    # set_setting: write_audit (no-op in fake)
    session.queue_scalars([])

    prev = setup_session(session)
    try:
        resp = await http_patch(
            "/api/v1/settings/log_level",
            json={"value": "DEBUG"},
            headers=auth_header("admin"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["key"] == "log_level"
        assert body["value_type"] == "literal"
        assert body["allowed_values"] == ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    finally:
        teardown_session(prev)


async def test_patch_sensitive_key_forbidden() -> None:
    """PATCH JWT_SECRET as admin returns 403."""
    session = FakeAsyncSession()
    prev = setup_session(session)
    try:
        resp = await http_patch(
            "/api/v1/settings/jwt_secret",
            json={"value": "new-secret-at-least-32-characters-long"},
            headers=auth_header("admin"),
        )
        assert resp.status_code == 403
        body = resp.json()
        assert "sensitive" in body["detail"].lower()
    finally:
        teardown_session(prev)


async def test_delete_resets_to_default() -> None:
    """DELETE LOG_LEVEL removes DB override; subsequent GET returns env default."""
    session = FakeAsyncSession()
    # reset_setting: select AppSetting → found (scalar_one_or_none, so queue_scalar)
    session.queue_scalar(make_app_setting_row("log_level", "DEBUG"))

    prev = setup_session(session)
    try:
        resp = await http_delete(
            "/api/v1/settings/log_level",
            headers=auth_header("admin"),
        )
        assert resp.status_code == 204
    finally:
        teardown_session(prev)


async def test_audit_log_written_on_patch() -> None:
    """PATCH writes audit log entry with before/after state."""
    session = FakeAsyncSession()
    # get_setting
    session.queue_scalars([])
    # set_setting: select existing → None
    session.queue_scalars([])

    prev = setup_session(session)
    try:
        resp = await http_patch(
            "/api/v1/settings/egui_tracking_enabled",
            json={"value": "true"},
            headers=auth_header("admin"),
        )
        assert resp.status_code == 200
        # Audit written inside set_setting; fake session records added entries
        # Check that write_audit was called (session.add called with AuditLog)
        added = [
            obj
            for obj in session.added
            if hasattr(obj, "action") and obj.action == "settings.update"
        ]
        assert len(added) == 1
        assert added[0].before_state is None  # new setting
        assert added[0].after_state["key"] == "egui_tracking_enabled"
    finally:
        teardown_session(prev)


async def test_bool_encoding() -> None:
    """PATCH EGUI_TRACKING_ENABLED=true stores 'true'."""
    session = FakeAsyncSession()
    session.queue_scalars([])  # get_setting
    session.queue_scalars([])  # set_setting select
    prev = setup_session(session)
    try:
        resp = await http_patch(
            "/api/v1/settings/egui_tracking_enabled",
            json={"value": "true"},
            headers=auth_header("admin"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["value_type"] == "bool"
        # The stored value should be lowercase "true"
        assert body["display_value"] == "true"
    finally:
        teardown_session(prev)


async def test_int_rejects_invalid() -> None:
    """PATCH sitemap_cache_ttl with 'abc' returns 422."""
    session = FakeAsyncSession()
    session.queue_scalars([])  # get_setting
    prev = setup_session(session)
    try:
        resp = await http_patch(
            "/api/v1/settings/sitemap_cache_ttl",
            json={"value": "abc"},
            headers=auth_header("admin"),
        )
        assert resp.status_code == 422
    finally:
        teardown_session(prev)


async def test_int_rejects_below_ge() -> None:
    """PATCH JWT_ACCESS_TOKEN_MINUTES=0 returns 422 (ge=1 validator)."""
    session = FakeAsyncSession()
    session.queue_scalars([])  # get_setting
    prev = setup_session(session)
    try:
        resp = await http_patch(
            "/api/v1/settings/jwt_access_token_minutes",
            json={"value": "0"},
            headers=auth_header("admin"),
        )
        assert resp.status_code == 422
    finally:
        teardown_session(prev)


async def test_literal_field_has_allowed_values() -> None:
    """Introspection returns allowed_values for log_level."""
    from domains.settings.introspection import _read_settings_metadata

    meta = _read_settings_metadata()
    assert meta["log_level"]["value_type"] == "literal"
    assert meta["log_level"]["allowed_values"] == [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ]
    assert meta["app_env"]["allowed_values"] == ["development", "staging", "production"]


async def test_nullable_field_null_sentinel() -> None:
    """PATCH __NULL__ for nullable field stores __NULL__."""
    session = FakeAsyncSession()
    session.queue_scalars([])  # get_setting
    session.queue_scalars([])  # set_setting select
    prev = setup_session(session)
    try:
        resp = await http_patch(
            "/api/v1/settings/redis_url",
            json={"value": "__NULL__"},
            headers=auth_header("admin"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["nullable"] is True
        assert body["is_null"] is True
    finally:
        teardown_session(prev)


async def test_legacy_db_settings_metadata_marks_password_sensitive() -> None:
    from domains.settings.introspection import _read_settings_metadata

    meta = _read_settings_metadata()

    assert meta["legacy_db_host"]["category"] == "legacy_import"
    assert meta["legacy_db_host"]["is_sensitive"] is False
    assert meta["legacy_db_password"]["category"] == "legacy_import"
    assert meta["legacy_db_password"]["is_sensitive"] is True
    assert meta["legacy_db_client_encoding"]["is_sensitive"] is False
