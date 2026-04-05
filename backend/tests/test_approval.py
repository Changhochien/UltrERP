"""Tests for approval workflow (Story 11.5)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from common.tenant import DEFAULT_TENANT_ID
from domains.approval.checks import needs_approval
from domains.approval.service import (
    ApprovalConflictError,
    ApprovalNotFoundError,
    create_approval,
    list_approvals,
    resolve_approval,
)
from tests.domains.orders._helpers import (
    FakeAsyncSession,
    auth_header,
    http_get,
    http_post,
    setup_session,
    teardown_session,
)


class FakeApproval:
    def __init__(self, **kwargs: Any) -> None:
        now = datetime.now(tz=UTC)
        self.id = kwargs.get("id", uuid.uuid4())
        self.tenant_id = kwargs.get("tenant_id", DEFAULT_TENANT_ID)
        self.action = kwargs.get("action", "inventory.adjust")
        self.entity_type = kwargs.get("entity_type", "stock_adjustment")
        self.entity_id = kwargs.get("entity_id", None)
        self.requested_by = kwargs.get("requested_by", "agent-1")
        self.requested_by_type = kwargs.get("requested_by_type", "agent")
        self.context = kwargs.get(
            "context",
            {
                "product_id": str(uuid.uuid4()),
                "warehouse_id": str(uuid.uuid4()),
                "quantity_change": 150,
                "reason_code": "correction",
                "notes": "Large automated correction",
            },
        )
        self.status = kwargs.get("status", "pending")
        self.resolved_by = kwargs.get("resolved_by", None)
        self.resolved_at = kwargs.get("resolved_at", None)
        self.expires_at = kwargs.get("expires_at", now + timedelta(hours=24))
        self.created_at = kwargs.get("created_at", now)


class FakeInventoryStock:
    def __init__(
        self,
        *,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        quantity: int = 200,
        reorder_point: int = 25,
    ) -> None:
        self.id = uuid.uuid4()
        self.tenant_id = DEFAULT_TENANT_ID
        self.product_id = product_id
        self.warehouse_id = warehouse_id
        self.quantity = quantity
        self.reorder_point = reorder_point
        self.updated_at = datetime.now(tz=UTC)


@pytest.mark.anyio
async def test_needs_approval_user_bypasses() -> None:
    assert needs_approval(actor_type="user", action="inventory.adjust", quantity=500) is False


@pytest.mark.anyio
async def test_needs_approval_agent_below_threshold() -> None:
    assert needs_approval(actor_type="agent", action="inventory.adjust", quantity=50) is False


@pytest.mark.anyio
async def test_needs_approval_agent_above_threshold() -> None:
    assert needs_approval(actor_type="agent", action="inventory.adjust", quantity=150) is True


@pytest.mark.anyio
async def test_needs_approval_invoice_void_always() -> None:
    assert needs_approval(actor_type="automation", action="invoices.void") is True


@pytest.mark.anyio
async def test_create_approval_request() -> None:
    session = FakeAsyncSession()
    approval = await create_approval(
        session,
        action="inventory.adjust",
        entity_type="stock_adjustment",
        entity_id=None,
        requested_by="agent-1",
        requested_by_type="agent",
        context={"quantity_change": 150},
    )
    assert approval.status == "pending"
    assert approval.requested_by == "agent-1"
    assert approval.tenant_id == DEFAULT_TENANT_ID


@pytest.mark.anyio
async def test_list_pending_approvals() -> None:
    session = FakeAsyncSession()
    approval = FakeApproval(status="pending")
    session.queue_scalars([approval])
    items = await list_approvals(session, status="pending")
    assert len(items) == 1
    assert items[0].status == "pending"


@pytest.mark.anyio
async def test_auto_expire_on_list() -> None:
    session = FakeAsyncSession()
    approval = FakeApproval(
        status="pending", expires_at=datetime.now(tz=UTC) - timedelta(minutes=1)
    )
    session.queue_scalars([approval])
    items = await list_approvals(session)
    assert len(items) == 1
    assert items[0].status == "expired"
    assert items[0].resolved_by is None


@pytest.mark.anyio
async def test_resolve_approval_approve_executes_action() -> None:
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    approval = FakeApproval(
        context={
            "product_id": str(product_id),
            "warehouse_id": str(warehouse_id),
            "quantity_change": -25,
            "reason_code": "damaged",
            "notes": "Approved inventory adjustment",
        },
    )
    stock = FakeInventoryStock(product_id=product_id, warehouse_id=warehouse_id)
    session = FakeAsyncSession()
    session.queue_scalar(approval)
    session.queue_scalar(stock)
    session.queue_scalar(None)
    resolved = await resolve_approval(
        session,
        approval.id,
        action="approve",
        resolved_by="owner-1",
    )
    assert resolved.status == "approved"
    assert resolved.entity_id is not None
    assert any(getattr(item, "action", None) == "approval.approve" for item in session.added)


@pytest.mark.anyio
async def test_resolve_approval_reject() -> None:
    approval = FakeApproval()
    session = FakeAsyncSession()
    session.queue_scalar(approval)
    resolved = await resolve_approval(
        session,
        approval.id,
        action="reject",
        resolved_by="finance-1",
    )
    assert resolved.status == "rejected"
    assert any(getattr(item, "action", None) == "approval.reject" for item in session.added)


@pytest.mark.anyio
async def test_resolve_expired_approval_fails() -> None:
    approval = FakeApproval(expires_at=datetime.now(tz=UTC) - timedelta(minutes=1))
    session = FakeAsyncSession()
    session.queue_scalar(approval)
    with pytest.raises(ApprovalConflictError):
        await resolve_approval(
            session,
            approval.id,
            action="approve",
            resolved_by="finance-1",
        )
    assert approval.status == "expired"
    assert approval.resolved_by is None


@pytest.mark.anyio
async def test_resolve_missing_approval_fails() -> None:
    session = FakeAsyncSession()
    session.queue_scalar(None)
    with pytest.raises(ApprovalNotFoundError):
        await resolve_approval(
            session,
            uuid.uuid4(),
            action="approve",
            resolved_by="finance-1",
        )


@pytest.mark.anyio
async def test_approval_api_list() -> None:
    session = FakeAsyncSession()
    approval = FakeApproval(status="pending")
    session.queue_scalars([approval])
    previous = setup_session(session)
    try:
        resp = await http_get(
            "/api/v1/admin/approvals?status=pending", headers=auth_header("finance")
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["status"] == "pending"
    finally:
        teardown_session(previous)


@pytest.mark.anyio
async def test_approval_api_resolve() -> None:
    approval = FakeApproval(status="pending")
    session = FakeAsyncSession()
    session.queue_scalar(approval)
    previous = setup_session(session)
    try:
        resp = await http_post(
            f"/api/v1/admin/approvals/{approval.id}/resolve",
            {"action": "reject"},
            headers=auth_header("finance"),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"
    finally:
        teardown_session(previous)


@pytest.mark.anyio
async def test_inventory_adjustment_above_threshold_returns_approval_required() -> None:
    session = FakeAsyncSession()
    previous = setup_session(session)
    product_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    try:
        resp = await http_post(
            "/api/v1/inventory/adjustments",
            {
                "product_id": str(product_id),
                "warehouse_id": str(warehouse_id),
                "quantity_change": 150,
                "reason_code": "correction",
            },
            headers={
                **auth_header("warehouse"),
                "X-Actor-Type": "agent",
                "X-Actor-Id": "inventory-agent",
            },
        )
        assert resp.status_code == 202
        body = resp.json()
        assert body["approval_required"] is True
        assert body["status"] == "pending"
    finally:
        teardown_session(previous)
