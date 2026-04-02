"""Unit tests for inventory service — transfer validation & reorder alerts."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from domains.inventory.services import (
	InsufficientStockError,
	TransferValidationError,
	transfer_stock,
)

# ── Fake ORM objects ──────────────────────────────────────────

class FakeInventoryStock:
	def __init__(
		self,
		quantity: int = 100,
		reorder_point: int = 10,
		*,
		tenant_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001"),
		product_id: uuid.UUID | None = None,
		warehouse_id: uuid.UUID | None = None,
	):
		self.id = uuid.uuid4()
		self.tenant_id = tenant_id
		self.product_id = product_id or uuid.uuid4()
		self.warehouse_id = warehouse_id or uuid.uuid4()
		self.quantity = quantity
		self.reorder_point = reorder_point
		self.updated_at = None


class FakeResult:
	def __init__(self, obj: object | None = None):
		self._obj = obj

	def scalar_one(self) -> object:
		if self._obj is None:
			raise AssertionError("Expected a queued row for scalar_one()")
		return self._obj

	def scalar_one_or_none(self) -> object | None:
		return self._obj

	def scalars(self) -> FakeScalars:
		return FakeScalars(self._obj)


class FakeScalars:
	def __init__(self, obj: object | None):
		self._obj = obj

	def all(self) -> list:
		return [self._obj] if self._obj else []


class FakeSession:
	"""Minimal session stub for unit testing service functions."""

	def __init__(self) -> None:
		self.added: list[object] = []
		self._execute_results: list[FakeResult] = []
		self._execute_index = 0
		self._flush_errors: list[Exception] = []
		self.rollback_calls = 0

	def add(self, obj: object) -> None:
		self.added.append(obj)

	def add_all(self, objs: list[object]) -> None:
		self.added.extend(objs)

	async def execute(self, _stmt: object) -> FakeResult:
		if self._execute_index < len(self._execute_results):
			result = self._execute_results[self._execute_index]
			self._execute_index += 1
			return result
		return FakeResult(None)

	async def flush(self) -> None:
		if self._flush_errors:
			raise self._flush_errors.pop(0)

		# Assign IDs to objects that need them
		for obj in self.added:
			if hasattr(obj, "id") and obj.id is None:
				obj.id = uuid.uuid4()

	async def rollback(self) -> None:
		self.rollback_calls += 1

	def queue_result(self, obj: object | None) -> None:
		self._execute_results.append(FakeResult(obj))

	def queue_flush_error(self, exc: Exception) -> None:
		self._flush_errors.append(exc)


# ── transfer_stock validation tests ───────────────────────────

@pytest.mark.asyncio
async def test_transfer_rejects_same_warehouse() -> None:
	session = FakeSession()
	wh = uuid.uuid4()
	with pytest.raises(TransferValidationError, match="different"):
		await transfer_stock(
			session,
			uuid.UUID("00000000-0000-0000-0000-000000000001"),
			from_warehouse_id=wh,
			to_warehouse_id=wh,
			product_id=uuid.uuid4(),
			quantity=10,
			actor_id="user1",
		)


@pytest.mark.asyncio
async def test_transfer_rejects_zero_quantity() -> None:
	session = FakeSession()
	with pytest.raises(TransferValidationError, match="positive"):
		await transfer_stock(
			session,
			uuid.UUID("00000000-0000-0000-0000-000000000001"),
			from_warehouse_id=uuid.uuid4(),
			to_warehouse_id=uuid.uuid4(),
			product_id=uuid.uuid4(),
			quantity=0,
			actor_id="user1",
		)


@pytest.mark.asyncio
async def test_transfer_rejects_negative_quantity() -> None:
	session = FakeSession()
	with pytest.raises(TransferValidationError, match="positive"):
		await transfer_stock(
			session,
			uuid.UUID("00000000-0000-0000-0000-000000000001"),
			from_warehouse_id=uuid.uuid4(),
			to_warehouse_id=uuid.uuid4(),
			product_id=uuid.uuid4(),
			quantity=-5,
			actor_id="user1",
		)


@pytest.mark.asyncio
async def test_transfer_rejects_no_source_stock() -> None:
	session = FakeSession()
	session.queue_result(None)  # source stock not found
	with pytest.raises(InsufficientStockError) as exc_info:
		await transfer_stock(
			session,
			uuid.UUID("00000000-0000-0000-0000-000000000001"),
			from_warehouse_id=uuid.uuid4(),
			to_warehouse_id=uuid.uuid4(),
			product_id=uuid.uuid4(),
			quantity=10,
			actor_id="user1",
		)
	assert exc_info.value.available == 0
	assert exc_info.value.requested == 10


@pytest.mark.asyncio
async def test_transfer_rejects_insufficient_stock() -> None:
	source = FakeInventoryStock(quantity=5)
	session = FakeSession()
	session.queue_result(source)  # source stock
	with pytest.raises(InsufficientStockError) as exc_info:
		await transfer_stock(
			session,
			uuid.UUID("00000000-0000-0000-0000-000000000001"),
			from_warehouse_id=uuid.uuid4(),
			to_warehouse_id=uuid.uuid4(),
			product_id=uuid.uuid4(),
			quantity=10,
			actor_id="user1",
		)
	assert exc_info.value.available == 5
	assert exc_info.value.requested == 10


@pytest.mark.asyncio
async def test_transfer_success_creates_records() -> None:
	pid = uuid.uuid4()
	source = FakeInventoryStock(quantity=50, reorder_point=10)
	target = FakeInventoryStock(quantity=20, reorder_point=5)

	session = FakeSession()
	session.queue_result(source)   # source FOR UPDATE
	session.queue_result(target)   # target FOR UPDATE
	session.queue_result(None)     # reorder alert query for source
	session.queue_result(None)     # reorder alert query for target

	await transfer_stock(
		session,
		uuid.UUID("00000000-0000-0000-0000-000000000001"),
		from_warehouse_id=uuid.uuid4(),
		to_warehouse_id=uuid.uuid4(),
		product_id=pid,
		quantity=15,
		actor_id="user1",
		notes="test transfer",
	)

	assert source.quantity == 35
	assert target.quantity == 35

	# Should have: transfer_history, adj_out, adj_in, audit_log
	# (reorder alert not created because 35 > 10)
	type_names = [type(obj).__name__ for obj in session.added]
	assert "StockTransferHistory" in type_names
	assert type_names.count("StockAdjustment") == 2
	assert "AuditLog" in type_names


@pytest.mark.asyncio
async def test_transfer_creates_target_stock_if_absent() -> None:
	source = FakeInventoryStock(quantity=50, reorder_point=5)
	session = FakeSession()
	session.queue_result(source)  # source FOR UPDATE
	session.queue_result(None)    # target not found
	session.queue_result(None)    # reorder alert query for source
	session.queue_result(None)    # reorder alert query for target

	await transfer_stock(
		session,
		uuid.UUID("00000000-0000-0000-0000-000000000001"),
		from_warehouse_id=uuid.uuid4(),
		to_warehouse_id=uuid.uuid4(),
		product_id=uuid.uuid4(),
		quantity=10,
		actor_id="user1",
	)

	assert source.quantity == 40
	# New InventoryStock should have been added
	inv_stocks = [
		o for o in session.added if type(o).__name__ == "InventoryStock"
	]
	assert len(inv_stocks) == 1
	assert inv_stocks[0].quantity == 10


@pytest.mark.asyncio
async def test_transfer_recovers_when_target_stock_created_concurrently() -> None:
	pid = uuid.uuid4()
	source = FakeInventoryStock(quantity=50, reorder_point=5, product_id=pid)
	existing_target = FakeInventoryStock(quantity=7, reorder_point=5, product_id=pid)

	session = FakeSession()
	session.queue_result(source)          # source FOR UPDATE
	session.queue_result(None)            # target missing before insert
	session.queue_flush_error(
		IntegrityError("insert into inventory_stock", {}, Exception("duplicate key")),
	)
	session.queue_result(existing_target)  # target after rollback/retry
	session.queue_result(None)             # reorder alert query for source
	session.queue_result(None)             # reorder alert query for target

	await transfer_stock(
		session,
		uuid.UUID("00000000-0000-0000-0000-000000000001"),
		from_warehouse_id=source.warehouse_id,
		to_warehouse_id=existing_target.warehouse_id,
		product_id=pid,
		quantity=10,
		actor_id="user1",
	)

	assert session.rollback_calls == 1
	assert source.quantity == 40
	assert existing_target.quantity == 17


@pytest.mark.asyncio
async def test_transfer_triggers_reorder_alert() -> None:
	source = FakeInventoryStock(quantity=15, reorder_point=10)
	target = FakeInventoryStock(quantity=20, reorder_point=5)

	session = FakeSession()
	session.queue_result(source)   # source FOR UPDATE
	session.queue_result(target)   # target FOR UPDATE
	session.queue_result(None)     # no existing reorder alert for source
	session.queue_result(None)     # no existing reorder alert for target

	await transfer_stock(
		session,
		uuid.UUID("00000000-0000-0000-0000-000000000001"),
		from_warehouse_id=uuid.uuid4(),
		to_warehouse_id=uuid.uuid4(),
		product_id=uuid.uuid4(),
		quantity=10,
		actor_id="user1",
	)

	assert source.quantity == 5  # below reorder_point of 10
	alerts = [o for o in session.added if type(o).__name__ == "ReorderAlert"]
	assert len(alerts) == 1
	assert alerts[0].current_stock == 5
