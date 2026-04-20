"""Lightweight reporting-semantic guards for intelligence queries."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.dialects import postgresql

from common.tenant import DEFAULT_TENANT_ID
from domains.intelligence.service import get_category_trends
from tests.domains.orders._helpers import FakeAsyncSession, FakeResult


@pytest.mark.asyncio
async def test_get_category_trends_uses_confirmation_timestamp_and_committed_statuses() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)  # set_tenant
    session._execute_results.extend(
        [
            FakeResult(items=[]),
            FakeResult(items=[]),
            FakeResult(items=[]),
            FakeResult(items=[]),
        ]
    )

    result = await get_category_trends(session, uuid.UUID(str(DEFAULT_TENANT_ID)), period="last_30d")

    assert result.trends == []

    executed_sql = "\n".join(
        str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        for statement, _params in session.executed_statements
        if hasattr(statement, "compile")
    ).lower()

    assert "coalesce(orders.confirmed_at, orders.created_at)" in executed_sql
    assert "'confirmed'" in executed_sql
    assert "'shipped'" in executed_sql
    assert "'fulfilled'" in executed_sql
    assert "'pending'" not in executed_sql