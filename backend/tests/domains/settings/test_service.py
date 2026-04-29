"""Tests for settings service layer."""

from __future__ import annotations

import pytest

from domains.settings.service import (
    NULL_SENTINEL,
    SENSITIVE_KEYS,
    VISIBLE_SENSITIVE_KEYS,
    _bool_decode,
    _bool_encode,
    _build_merged_dict,
    _revalidate_setting,
    _serialize_setting_item,
)


class TestBoolEncode:
    def test_true_values(self) -> None:
        for val in ("true", "True", "TRUE", "1", "yes", "on"):
            assert _bool_encode(val) == "true", f"Failed for {val!r}"

    def test_false_values(self) -> None:
        for val in ("false", "False", "FALSE", "0", "no", "off"):
            assert _bool_encode(val) == "false", f"Failed for {val!r}"

    def test_invalid_raises(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _bool_encode("maybe")
        assert exc_info.value.status_code == 422


class TestBoolDecode:
    def test_true_values(self) -> None:
        for val in ("true", "True", "TRUE", "1", "yes", "on"):
            assert _bool_decode(val) is True, f"Failed for {val!r}"

    def test_false_values(self) -> None:
        for val in ("false", "False", "FALSE", "0", "no", "off"):
            assert _bool_decode(val) is False, f"Failed for {val!r}"

    def test_invalid_raises(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _bool_decode("maybe")
        assert exc_info.value.status_code == 422


class TestRevalidateSetting:
    def test_revalidate_bool_true(self) -> None:
        result = _revalidate_setting("egui_tracking_enabled", "true")
        assert result == "true"

    def test_revalidate_bool_false(self) -> None:
        result = _revalidate_setting("egui_tracking_enabled", "false")
        assert result == "false"

    def test_revalidate_int_valid(self) -> None:
        result = _revalidate_setting("sitemap_cache_ttl", "7200")
        assert result == "7200"

    def test_revalidate_int_invalid(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _revalidate_setting("sitemap_cache_ttl", "not-an-int")
        assert exc_info.value.status_code == 422

    def test_revalidate_int_below_ge(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _revalidate_setting("jwt_access_token_minutes", "0")
        assert exc_info.value.status_code == 422

    def test_revalidate_tuple_valid(self) -> None:
        result = _revalidate_setting(
            "cors_origins", '["https://example.com","https://app.example.com"]'
        )
        # The validated result is str repr of the tuple
        assert "example.com" in result

    def test_revalidate_tuple_invalid_json(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _revalidate_setting("cors_origins", "not-valid-json")
        assert exc_info.value.status_code == 422

    def test_revalidate_nullable_null_sentinel(self) -> None:
        result = _revalidate_setting("redis_url", NULL_SENTINEL)
        assert result == NULL_SENTINEL

    def test_revalidate_non_nullable_null_sentinel_raises(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _revalidate_setting("log_level", NULL_SENTINEL)
        assert exc_info.value.status_code == 422


class TestBuildMergedDict:
    def test_uses_python_attr_names(self) -> None:
        """Keys in merged dict must be Python attribute names, NOT env var names."""
        d = _build_merged_dict()
        # Python attr names (snake_case)
        assert "log_level" in d
        assert "jwt_access_token_minutes" in d
        assert "app_env" in d
        # NOT env var names (SCREAMING_SNAKE_CASE)
        assert "LOG_LEVEL" not in d
        assert "JWT_ACCESS_TOKEN_MINUTES" not in d


class TestSensitiveKeys:
    def test_sensitive_keys_list(self) -> None:
        assert SENSITIVE_KEYS == {
            "jwt_secret",
            "line_channel_secret",
            "line_channel_access_token",
            "object_store_secret_key",
            "object_store_access_key",
            "mcp_api_keys",
        }

    def test_visible_sensitive_keys_allow_legacy_db_password(self) -> None:
        assert VISIBLE_SENSITIVE_KEYS == {"legacy_db_password"}


class TestSerializeSettingItem:
    def test_masks_sensitive_value_without_marking_it_null(self) -> None:
        item = _serialize_setting_item(
            key="legacy_db_password",
            meta_info={
                "value_type": "str",
                "allowed_values": None,
                "nullable": True,
                "is_sensitive": True,
                "description": "Legacy PostgreSQL password",
                "category": "legacy_import",
            },
            raw_value="super-secret",
            is_null=False,
            updated_at=None,
            updated_by=None,
        )

        assert item.value == ""
        assert item.display_value == "********"
        assert item.is_null is False
        assert item.is_sensitive is True
