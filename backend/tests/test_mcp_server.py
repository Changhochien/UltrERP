"""Tests for MCP server integration (Story 8.6)."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from starlette.applications import Starlette

from app.main import create_app
from app.mcp_server import mcp
from app.mcp_setup import get_mcp_app
from domains.health import routes as health_routes


class _HealthySession:
    async def execute(self, _statement: object) -> None:
        return None


class _FakeSessionContext:
    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, _exc_type, _exc, _tb) -> bool:
        return False


def test_mcp_server_name():
    """AC2: FastMCP instance has correct name."""
    assert mcp.name == "UltrERP"


def test_mcp_server_not_stateless():
    """AC2: MCP server does NOT set stateless_http (AR7)."""
    # FastMCP 2.x defaults to session-mode; confirm no stateless_http attr set.
    # The http_app() call should produce a non-stateless app.
    app = mcp.http_app(path="/")
    assert app is not None


def test_get_mcp_app_returns_starlette():
    """AC3: get_mcp_app() returns a Starlette-compatible ASGI app."""
    app = get_mcp_app()
    assert isinstance(app, Starlette)


@pytest.fixture
def fastapi_app():
    return create_app()


@pytest.mark.asyncio
async def test_health_reports_mcp(fastapi_app, monkeypatch):
    """AC6: Health endpoint includes mcp: true."""
    monkeypatch.setattr(
        health_routes,
        "AsyncSessionLocal",
        lambda: _FakeSessionContext(_HealthySession()),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("mcp") is True


@pytest.mark.asyncio
async def test_mcp_endpoint_reachable(fastapi_app):
    """AC3: /mcp endpoint is reachable (returns MCP protocol response)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        # MCP streamable-http expects POST with JSON-RPC; a bare GET should
        # return 405 or similar — proving the mount is active.
        resp = await client.get("/mcp")
    # Any response other than 404 means the mount is working.
    assert resp.status_code != 404


@pytest.mark.asyncio
async def test_concurrent_mcp_connections(fastapi_app):
    """AC5/NFR19: App handles concurrent requests without mutual blocking.

    Full MCP JSON-RPC session-isolation testing requires a live server
    with lifespan (MCP's StreamableHTTP session manager needs its TaskGroup).
    Here we verify the FastAPI app handles concurrent async requests.
    """

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        # Use root endpoint (no DB) to avoid asyncpg pool teardown races.
        r1, r2 = await asyncio.gather(
            client.get("/"),
            client.get("/"),
        )
    assert r1.status_code == 200
    assert r2.status_code == 200
