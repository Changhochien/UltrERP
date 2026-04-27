from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from domains.manufacturing.models import ManufacturingProposal, ManufacturingProposalStatus
from domains.manufacturing.schemas import ProposalGenerateRequest
from domains.manufacturing.service import generate_proposals


class _ScalarListResult:
	def __init__(self, values: list[object]) -> None:
		self._values = values

	def scalars(self) -> _ScalarListResult:
		return self

	def all(self) -> list[object]:
		return self._values


class _ScalarValueResult:
	def __init__(self, value: object) -> None:
		self._value = value

	def scalar(self) -> object:
		return self._value


class _SingleRowResult:
	def __init__(self, row: object | None) -> None:
		self._row = row

	def scalar(self) -> object | None:
		if self._row is None:
			return None
		return getattr(self._row, "demand", self._row)

	def one_or_none(self) -> object | None:
		return self._row


class _FakeSession:
	def __init__(self, results: list[object]) -> None:
		self.results = results
		self.added: list[ManufacturingProposal] = []
		self.flush_calls = 0

	async def execute(self, _statement: object) -> object:
		if not self.results:
			raise AssertionError("Unexpected execute() call")
		return self.results.pop(0)

	def add(self, instance: ManufacturingProposal) -> None:
		instance.id = uuid.uuid4()
		now = datetime.utcnow()
		instance.created_at = now
		instance.updated_at = now
		self.added.append(instance)

	async def flush(self) -> None:
		self.flush_calls += 1


def _make_bom(product_id: uuid.UUID, component_code: str) -> SimpleNamespace:
	return SimpleNamespace(
		id=uuid.uuid4(),
		product_id=product_id,
		bom_quantity=Decimal("1.000000"),
		items=[
			SimpleNamespace(
				item_id=uuid.uuid4(),
				item_code=component_code,
				item_name="Steel Blank",
				required_quantity=Decimal("2.000000"),
				source_warehouse_id=None,
			)
		],
	)


@pytest.mark.asyncio
async def test_generate_proposals_uses_confirmed_order_lines_and_stales_previous_results() -> None:
	tenant_id = uuid.uuid4()
	product_id = uuid.uuid4()
	bom = _make_bom(product_id, component_code="RM-001")

	first_session = _FakeSession(
		results=[
			_ScalarListResult([bom]),
			_ScalarListResult([]),
			_SingleRowResult(SimpleNamespace(demand=Decimal("5.000"))),
			_ScalarValueResult(Decimal("0")),
			_ScalarValueResult(Decimal("0")),
			_ScalarValueResult(Decimal("0")),
		]
	)

	first_run = await generate_proposals(
		first_session,
		tenant_id,
		ProposalGenerateRequest(product_ids=[product_id]),
	)

	assert len(first_run) == 1
	assert first_run[0].product_id == product_id
	assert first_run[0].demand_quantity == Decimal("5.000")
	assert first_run[0].proposed_quantity == Decimal("5.000")
	assert first_run[0].status == ManufacturingProposalStatus.PROPOSED
	assert first_run[0].shortages is not None
	assert first_run[0].shortages[0]["item_code"] == "RM-001"
	assert first_session.flush_calls == 1

	existing_proposal = first_session.added[0]
	second_session = _FakeSession(
		results=[
			_ScalarListResult([bom]),
			_ScalarListResult([existing_proposal]),
			_SingleRowResult(SimpleNamespace(demand=Decimal("5.000"))),
			_ScalarValueResult(Decimal("0")),
			_ScalarValueResult(Decimal("0")),
			_ScalarValueResult(Decimal("0")),
		]
	)

	second_run = await generate_proposals(
		second_session,
		tenant_id,
		ProposalGenerateRequest(product_ids=[product_id]),
	)

	assert len(second_run) == 1
	assert existing_proposal.status == ManufacturingProposalStatus.STALE
	assert second_session.added[0].status == ManufacturingProposalStatus.PROPOSED