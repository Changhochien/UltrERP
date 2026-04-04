"""Tests for the visitor-stats dashboard endpoint and PostHog client."""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from domains.dashboard.posthog_client import VisitorStats, get_visitor_stats


# ---------------------------------------------------------------------------
# PostHog client unit tests
# ---------------------------------------------------------------------------


def _mock_response(visitor_count: int, inquiry_count: int):
    """Return a pair of mock httpx responses for visitor + inquiry queries."""
    call_count = 0

    async def _post(url, *, json, headers):
        nonlocal call_count
        call_count += 1
        count = visitor_count if call_count == 1 else inquiry_count
        req = httpx.Request("POST", url)
        resp = httpx.Response(200, json={"results": [[count]]}, request=req)
        return resp

    return _post


@pytest.mark.asyncio
async def test_posthog_client_returns_stats():
    mock_post = _mock_response(100, 5)
    with patch("domains.dashboard.posthog_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = mock_post
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        stats = await get_visitor_stats(
            host="https://ph.example.com",
            project_id="123",
            api_key="phx_test",
            target_date=date(2026, 4, 1),
        )

    assert stats.visitor_count == 100
    assert stats.inquiry_count == 5


@pytest.mark.asyncio
async def test_posthog_client_raises_on_http_error():
    with patch("domains.dashboard.posthog_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()

        async def _fail(*args, **kwargs):
            req = httpx.Request("POST", "https://ph.example.com/api/projects/123/query/")
            resp = httpx.Response(500, request=req)
            resp.raise_for_status()

        instance.post = _fail
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        with pytest.raises(httpx.HTTPStatusError):
            await get_visitor_stats(
                host="https://ph.example.com",
                project_id="123",
                api_key="phx_test",
                target_date=date(2026, 4, 1),
            )


# ---------------------------------------------------------------------------
# Route-level tests via HTTPX TestClient
# ---------------------------------------------------------------------------

from httpx import ASGITransport, AsyncClient as HttpxAsyncClient

from app.main import create_app

from tests.domains.orders._helpers import auth_header


@pytest.mark.asyncio
async def test_visitor_stats_not_configured():
    """When PostHog keys are not set, returns is_configured=False."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with HttpxAsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as client:
        with patch("domains.dashboard.routes.settings") as mock_settings:
            mock_settings.posthog_api_key = None
            mock_settings.posthog_project_id = None
            resp = await client.get("/api/v1/dashboard/visitor-stats")

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_configured"] is False
    assert body["visitor_count"] == 0


@pytest.mark.asyncio
async def test_visitor_stats_api_error():
    """When PostHog API fails, returns error message."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with HttpxAsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as client:
        with (
            patch("domains.dashboard.routes.settings") as mock_settings,
            patch("domains.dashboard.posthog_client.get_visitor_stats", side_effect=Exception("timeout")),
        ):
            mock_settings.posthog_api_key = "phx_test"
            mock_settings.posthog_project_id = "123"
            mock_settings.posthog_host = "https://ph.example.com"
            resp = await client.get("/api/v1/dashboard/visitor-stats")

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_configured"] is True
    assert body["error"] == "Analytics unavailable"
    assert body["visitor_count"] == 0


@pytest.mark.asyncio
async def test_visitor_stats_success():
    """Happy path: PostHog returns data, conversion rate computed."""
    app = create_app()
    transport = ASGITransport(app=app)
    stats = VisitorStats(visitor_count=200, inquiry_count=10)

    async with HttpxAsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as client:
        with (
            patch("domains.dashboard.routes.settings") as mock_settings,
            patch("domains.dashboard.posthog_client.get_visitor_stats", return_value=stats),
        ):
            mock_settings.posthog_api_key = "phx_test"
            mock_settings.posthog_project_id = "123"
            mock_settings.posthog_host = "https://ph.example.com"
            resp = await client.get("/api/v1/dashboard/visitor-stats")

    assert resp.status_code == 200
    body = resp.json()
    assert body["visitor_count"] == 200
    assert body["inquiry_count"] == 10
    assert body["conversion_rate"] == "5.0"
    assert body["is_configured"] is True
    assert body["error"] is None


@pytest.mark.asyncio
async def test_visitor_stats_zero_visitors():
    """Zero visitors → conversion_rate is null."""
    app = create_app()
    transport = ASGITransport(app=app)
    stats = VisitorStats(visitor_count=0, inquiry_count=0)

    async with HttpxAsyncClient(transport=transport, base_url="http://test", headers=auth_header()) as client:
        with (
            patch("domains.dashboard.routes.settings") as mock_settings,
            patch("domains.dashboard.posthog_client.get_visitor_stats", return_value=stats),
        ):
            mock_settings.posthog_api_key = "phx_test"
            mock_settings.posthog_project_id = "123"
            mock_settings.posthog_host = "https://ph.example.com"
            resp = await client.get("/api/v1/dashboard/visitor-stats")

    assert resp.status_code == 200
    body = resp.json()
    assert body["visitor_count"] == 0
    assert body["conversion_rate"] is None
