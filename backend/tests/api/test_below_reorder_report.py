from __future__ import annotations

import csv
import uuid
from collections.abc import AsyncGenerator
from io import StringIO
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.main import app
from common.database import get_db
from domains.inventory import routes as inventory_routes
from tests.domains.orders._helpers import auth_header


class FakeAsyncSession:
    async def commit(self) -> None:
        return None


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


async def test_below_reorder_preview_and_export_share_dataset_and_export_bom(monkeypatch) -> None:
    requested_warehouse_id = uuid.uuid4()
    calls: list[uuid.UUID | None] = []

    async def fake_list_below_reorder_products(
        _session: FakeAsyncSession,
        _tenant_id: uuid.UUID,
        *,
        warehouse_id: uuid.UUID | None = None,
    ) -> tuple[list[dict], int]:
        calls.append(warehouse_id)
        return (
            [
                {
                    "product_id": uuid.uuid4(),
                    "product_code": "LOW-001",
                    "product_name": "螺絲組",
                    "category": "五金",
                    "warehouse_id": requested_warehouse_id,
                    "warehouse_name": "主倉",
                    "current_stock": 3,
                    "reorder_point": 8,
                    "shortage_qty": 5,
                    "on_order_qty": 2,
                    "in_transit_qty": 1,
                    "default_supplier": None,
                }
            ],
            1,
        )

    monkeypatch.setattr(inventory_routes, "list_below_reorder_products", fake_list_below_reorder_products)
    session = FakeAsyncSession()
    previous = _setup(session)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=auth_header(),
        ) as client:
            preview = await client.get(
                f"/api/v1/inventory/reports/below-reorder?warehouse_id={requested_warehouse_id}"
            )
            export = await client.get(
                f"/api/v1/inventory/reports/below-reorder/export?warehouse_id={requested_warehouse_id}"
            )

        assert preview.status_code == 200, preview.json()
        preview_body = preview.json()
        assert preview_body["total"] == 1
        assert preview_body["items"][0]["product_name"] == "螺絲組"
        assert preview_body["items"][0]["default_supplier"] is None

        assert export.status_code == 200
        assert export.content.startswith(b"\xef\xbb\xbf")
        assert "attachment; filename=\"below-reorder-report-" in export.headers["content-disposition"]

        decoded_csv = export.content.decode("utf-8-sig")
        rows = list(csv.reader(StringIO(decoded_csv)))
        assert rows[0] == [
            "Product Code",
            "Product Name",
            "Category",
            "Warehouse",
            "Current Stock",
            "Reorder Point",
            "Shortage Qty",
            "On Order Qty",
            "In Transit Qty",
            "Default Supplier",
        ]
        assert rows[1] == [
            "LOW-001",
            "螺絲組",
            "五金",
            "主倉",
            "3",
            "8",
            "5",
            "2",
            "1",
            "",
        ]
        assert calls == [requested_warehouse_id, requested_warehouse_id]
    finally:
        _teardown(previous)