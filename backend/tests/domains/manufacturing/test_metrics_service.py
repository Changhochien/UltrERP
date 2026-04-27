from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from domains.manufacturing.models import DowntimeEntry, OeeRecord
from domains.manufacturing.schemas import DowntimeCreate, OeeRecordCreate
from domains.manufacturing.service import create_downtime, create_oee_record


class _FakeMetricsSession:
	def __init__(self) -> None:
		self.entries: list[object] = []

	def add(self, instance: object) -> None:
		now = datetime.now(tz=UTC)
		instance.id = uuid.uuid4()
		instance.created_at = now
		if hasattr(instance, "updated_at"):
			instance.updated_at = now
		self.entries.append(instance)

	async def flush(self) -> None:
		return None

	async def refresh(self, _instance: object) -> None:
		return None


@pytest.mark.asyncio
async def test_create_downtime_rejects_end_time_before_start_time() -> None:
	session = _FakeMetricsSession()
	start_time = datetime.now(tz=UTC)

	with pytest.raises(ValueError, match="Downtime end time must be after start time"):
		await create_downtime(
			session,
			uuid.uuid4(),
			uuid.uuid4(),
			DowntimeCreate(
				workstation_id=uuid.uuid4(),
				reason="unplanned_breakdown",
				start_time=start_time,
				end_time=start_time - timedelta(minutes=15),
			),
		)

	assert session.entries == []


@pytest.mark.asyncio
async def test_create_oee_record_rejects_stop_time_greater_than_planned_time() -> None:
	session = _FakeMetricsSession()

	with pytest.raises(ValueError, match="Stop time cannot exceed planned production time"):
		await create_oee_record(
			session,
			uuid.uuid4(),
			OeeRecordCreate(
				workstation_id=uuid.uuid4(),
				record_date=datetime.now(tz=UTC),
				planned_production_time=60,
				stop_time=75,
				ideal_cycle_time=2,
				total_count=20,
				good_count=20,
				reject_count=0,
			),
		)

	assert session.entries == []


@pytest.mark.asyncio
async def test_create_oee_record_rejects_inconsistent_counts() -> None:
	session = _FakeMetricsSession()

	with pytest.raises(ValueError, match="Good count and reject count cannot exceed total count"):
		await create_oee_record(
			session,
			uuid.uuid4(),
			OeeRecordCreate(
				workstation_id=uuid.uuid4(),
				record_date=datetime.now(tz=UTC),
				planned_production_time=120,
				stop_time=10,
				ideal_cycle_time=2,
				total_count=40,
				good_count=35,
				reject_count=10,
			),
		)

	assert session.entries == []


@pytest.mark.asyncio
async def test_create_oee_record_calculates_expected_factors() -> None:
	session = _FakeMetricsSession()

	response = await create_oee_record(
		session,
		uuid.uuid4(),
		OeeRecordCreate(
			workstation_id=uuid.uuid4(),
			record_date=datetime.now(tz=UTC),
			planned_production_time=120,
			stop_time=20,
			ideal_cycle_time=2,
			total_count=40,
			good_count=38,
			reject_count=2,
		),
	)

	assert len(session.entries) == 1
	assert isinstance(session.entries[0], OeeRecord)
	assert response.run_time == 100
	assert response.availability == pytest.approx(100 / 120)
	assert response.performance == pytest.approx(80 / 100)
	assert response.quality == pytest.approx(38 / 40)
	assert response.oee == pytest.approx((100 / 120) * (80 / 100) * (38 / 40))


@pytest.mark.asyncio
async def test_create_downtime_calculates_duration_minutes() -> None:
	session = _FakeMetricsSession()
	start_time = datetime.now(tz=UTC)

	response = await create_downtime(
		session,
		uuid.uuid4(),
		uuid.uuid4(),
		DowntimeCreate(
			workstation_id=uuid.uuid4(),
			reason="planned_maintenance",
			start_time=start_time,
			end_time=start_time + timedelta(minutes=45),
		),
	)

	assert len(session.entries) == 1
	assert isinstance(session.entries[0], DowntimeEntry)
	assert response.duration_minutes == 45