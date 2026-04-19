from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from domains.inventory import routes as inventory_routes
from tests.domains.orders._helpers import auth_header


class FakeAsyncSession:
    def __init__(self) -> None:
        self.commit_calls = 0

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        pass


_MISSING_OVERRIDE = object()


def _setup(session: FakeAsyncSession) -> Any:
    previous = app.dependency_overrides.get(get_db, _MISSING_OVERRIDE)

    async def override() -> AsyncGenerator[FakeAsyncSession, None]:
        yield session

    app.dependency_overrides[get_db] = override
    return previous


def _teardown(previous: Any) -> None:
    if previous is _MISSING_OVERRIDE:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


async def test_apply_reorder_points_updates_only_selected_rows(
    monkeypatch: Any,
) -> None:
    session = FakeAsyncSession()
    previous = _setup(session)
    warehouse_id = uuid.uuid4()
    selected_stock_id = uuid.uuid4()
    unselected_stock_id = uuid.uuid4()
    captured: dict[str, object] = {}

    async def fake_compute_reorder_points_preview(
        _session: FakeAsyncSession,
        tenant_id: uuid.UUID,
        *,
        safety_factor: float,
        demand_lookback_days: int,
        lead_time_lookback_days: int,
        warehouse_id: uuid.UUID | None,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        captured["warehouse_id"] = warehouse_id
        row_base = {
            "tenant_id": tenant_id,
            "warehouse_id": warehouse_id or uuid.uuid4(),
            "review_cycle_days": 7,
            "lead_time_days": 12,
            "safety_factor": safety_factor,
            "reorder_point": 18,
        }
        return (
            [
                {
                    **row_base,
                    "stock_id": selected_stock_id,
                    "product_id": uuid.uuid4(),
                },
                {
                    **row_base,
                    "stock_id": unselected_stock_id,
                    "product_id": uuid.uuid4(),
                },
            ],
            [],
        )

    async def fake_apply_reorder_points(
        _session: FakeAsyncSession,
        tenant_id: uuid.UUID,
        *,
        selected_rows: list[dict[str, object]],
        safety_factor: float,
        demand_lookback_days: int,
        lead_time_lookback_days: int,
    ) -> dict[str, object]:
        captured["selected_rows"] = selected_rows
        return {
            "updated_count": len(selected_rows),
            "skipped_count": 0,
            "tenant_id": tenant_id,
            "safety_factor": safety_factor,
            "demand_lookback_days": demand_lookback_days,
            "lead_time_lookback_days": lead_time_lookback_days,
        }

    monkeypatch.setattr(
        inventory_routes,
        "compute_reorder_points_preview",
        fake_compute_reorder_points_preview,
    )
    monkeypatch.setattr(
        inventory_routes,
        "apply_reorder_points",
        fake_apply_reorder_points,
    )

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.put(
                "/api/v1/inventory/reorder-points/apply",
                json={
                    "selected_stock_ids": [str(selected_stock_id)],
                    "safety_factor": 0.5,
                    "lookback_days": 90,
                    "lookback_days_lead_time": 180,
                    "warehouse_id": str(warehouse_id),
                },
            )

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["updated_count"] == 1
        assert body["skipped_count"] == 0
        assert captured["warehouse_id"] == warehouse_id
        assert len(captured["selected_rows"]) == 1
        assert captured["selected_rows"][0]["stock_id"] == selected_stock_id
        assert session.commit_calls == 1
    finally:
        _teardown(previous)


async def test_patch_stock_settings_returns_manual_override(monkeypatch: Any) -> None:
    session = FakeAsyncSession()
    previous = _setup(session)
    stock_id = uuid.uuid4()
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    captured: dict[str, object] = {}

    async def fake_update_stock_settings(
        _session: FakeAsyncSession,
        tenant_id: uuid.UUID,
        row_stock_id: uuid.UUID,
        *,
        reorder_point: int | None = None,
        safety_factor: float | None = None,
        lead_time_days: int | None = None,
        policy_type: str | None = None,
        target_stock_qty: int | None = None,
        on_order_qty: int | None = None,
        in_transit_qty: int | None = None,
        reserved_qty: int | None = None,
        planning_horizon_days: int | None = None,
        review_cycle_days: int | None = None,
    ) -> SimpleNamespace:
        captured["stock_id"] = row_stock_id
        captured["reorder_point"] = reorder_point
        return SimpleNamespace(
            id=row_stock_id,
            tenant_id=tenant_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=14,
            reorder_point=reorder_point or 0,
            safety_factor=safety_factor or 0.5,
            lead_time_days=lead_time_days or 7,
            policy_type=policy_type or "continuous",
            target_stock_qty=target_stock_qty or 0,
            on_order_qty=on_order_qty or 0,
            in_transit_qty=in_transit_qty or 0,
            reserved_qty=reserved_qty or 0,
            planning_horizon_days=planning_horizon_days or 0,
            review_cycle_days=review_cycle_days or 0,
            updated_at=datetime.now(tz=UTC),
        )

    monkeypatch.setattr(
        inventory_routes,
        "update_stock_settings",
        fake_update_stock_settings,
    )

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            resp = await client.patch(
                f"/api/v1/inventory/stocks/{stock_id}",
                json={"reorder_point": 22},
            )

        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["reorder_point"] == 22
        assert captured["stock_id"] == stock_id
        assert captured["reorder_point"] == 22
        assert session.commit_calls == 1
    finally:
        _teardown(previous)
