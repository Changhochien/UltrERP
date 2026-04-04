"""Tests for settings parsing."""
from __future__ import annotations

from common.config import Settings


def test_settings_accept_json_cors_origins_from_env(monkeypatch):
	monkeypatch.setenv("JWT_SECRET", "x" * 32)
	monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:5173","tauri://localhost"]')

	settings = Settings()

	assert settings.cors_origins == ("http://localhost:5173", "tauri://localhost")


def test_settings_accept_bracketed_csv_cors_origins_from_env(monkeypatch):
	monkeypatch.setenv("JWT_SECRET", "x" * 32)
	monkeypatch.setenv("CORS_ORIGINS", "[http://localhost:5173,tauri://localhost]")

	settings = Settings()

	assert settings.cors_origins == ("http://localhost:5173", "tauri://localhost")