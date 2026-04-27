from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from domains.manufacturing.models import WorkOrderStatus
from domains.manufacturing.schemas import (
	WorkOrderMaterialReserve,
	WorkOrderStatusTransition,
	WorkOrderTransfer,
)
from domains.manufacturing import service as manufacturing_service


class _ScalarResult:
	def __init__(self, value: object) -> None:
		self._value = value

	def scalar_one_or_none(self) -> object:
		return self._value


class _FakeWorkOrderSession:
	def __init__(self, results: list[object]) -> None:
		self.results = results
		self.flush_calls = 0

	async def execute(self, _statement: object) -> object:
		if not self.results:
			raise AssertionError("Unexpected execute() call")
		return self.results.pop(0)

	async def flush(self) -> None:
		self.flush_calls += 1

	async def refresh(self, _instance: object) -> None:
		return None


def _make_material_line(**overrides: object) -> SimpleNamespace:
	base = {
		"id": uuid.uuid4(),
		"item_id": uuid.uuid4(),
		"item_code": "RM-001",
		"item_name": "Steel Blank",
		"required_quantity": Decimal("5"),
		"reserved_quantity": Decimal("0"),
		"transferred_quantity": Decimal("0"),
		"consumed_quantity": Decimal("0"),
		"source_warehouse_id": uuid.uuid4(),
	}
	base.update(overrides)
	return SimpleNamespace(**base)


def _make_work_order(**overrides: object) -> SimpleNamespace:
	base = {
		"id": uuid.uuid4(),
		"tenant_id": uuid.uuid4(),
		"code": "WO-001",
		"status": WorkOrderStatus.SUBMITTED,
		"material_lines": [],
		"wip_warehouse_id": uuid.uuid4(),
		"started_at": None,
		"completed_at": None,
		"stopped_reason": None,
		"cancelled_reason": None,
	}
	base.update(overrides)
	return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_transition_work_order_status_requires_reason_for_stop() -> None:
	work_order = _make_work_order(status=WorkOrderStatus.NOT_STARTED)
	session = _FakeWorkOrderSession([_ScalarResult(work_order)])

	with pytest.raises(ValueError, match="Reason is required for stopped transition"):
		await manufacturing_service.transition_work_order_status(
			session,
			work_order.tenant_id,
			work_order.id,
			WorkOrderStatusTransition(status=WorkOrderStatus.STOPPED),
		)

	assert session.flush_calls == 0


@pytest.mark.asyncio
async def test_reserve_work_order_materials_reports_shortages() -> None:
	line = _make_material_line(required_quantity=Decimal("4"))
	work_order = _make_work_order(material_lines=[line])
	session = _FakeWorkOrderSession([
		_ScalarResult(work_order),
		_ScalarResult(None),
	])

	with pytest.raises(ValueError, match="Material shortages"):
		await manufacturing_service.reserve_work_order_materials(
			session,
			work_order.tenant_id,
			work_order.id,
			WorkOrderMaterialReserve(action="reserve"),
		)

	assert line.reserved_quantity == Decimal("0")
	assert session.flush_calls == 1


@pytest.mark.asyncio
async def test_transfer_work_order_materials_uses_remaining_quantity_when_map_missing(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	line = _make_material_line(
		required_quantity=Decimal("5"),
		transferred_quantity=Decimal("2"),
		consumed_quantity=Decimal("2"),
	)
	work_order = _make_work_order(
		status=WorkOrderStatus.IN_PROGRESS,
		material_lines=[line],
	)
	session = _FakeWorkOrderSession([_ScalarResult(work_order)])
	transfer_calls: list[dict[str, object]] = []

	async def _fake_transfer_stock(**kwargs: object) -> None:
		transfer_calls.append(kwargs)

	async def _fake_get_work_order_by_id(*_args: object, **_kwargs: object) -> SimpleNamespace:
		return work_order

	monkeypatch.setattr(manufacturing_service, "transfer_stock", _fake_transfer_stock)
	monkeypatch.setattr(manufacturing_service, "get_work_order_by_id", _fake_get_work_order_by_id)

	result = await manufacturing_service.transfer_work_order_materials(
		session,
		work_order.tenant_id,
		work_order.id,
		WorkOrderTransfer(),
	)

	assert result is work_order
	assert session.flush_calls == 1
	assert len(transfer_calls) == 1
	assert transfer_calls[0]["quantity"] == 3
	assert line.transferred_quantity == Decimal("5")
	assert line.consumed_quantity == Decimal("5")