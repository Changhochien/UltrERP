"""Focused customer route RBAC tests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.domains.orders._helpers import (  # noqa: E402
    FakeAsyncSession,
    auth_header,
    http_get,
    setup_session,
    teardown_session,
)


async def test_list_customers_allows_admin_role() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)
    session.queue_count(0)
    session.queue_scalars([])

    prev = setup_session(session)
    try:
        resp = await http_get("/api/v1/customers", headers=auth_header("admin"))
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total_count"] == 0
    finally:
        teardown_session(prev)


async def test_list_customers_rejects_warehouse_role() -> None:
    resp = await http_get("/api/v1/customers", headers=auth_header("warehouse"))
    assert resp.status_code == 403