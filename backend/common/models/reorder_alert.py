"""Reorder alert model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class AlertStatus(str, enum.Enum):
	PENDING = "pending"
	ACKNOWLEDGED = "acknowledged"
	RESOLVED = "resolved"


def _alert_status_values(enum_cls: type[AlertStatus]) -> list[str]:
	return [status.value for status in enum_cls]


class ReorderAlert(Base):
	__tablename__ = "reorder_alert"
	__table_args__ = (
		Index(
			"uq_reorder_alert_tenant_product_warehouse",
			"tenant_id", "product_id", "warehouse_id",
			unique=True,
		),
		Index(
			"ix_reorder_alert_tenant_status_warehouse",
			"tenant_id", "status", "warehouse_id",
		),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	product_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("product.id"), nullable=False,
	)
	warehouse_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=False,
	)
	current_stock: Mapped[int] = mapped_column(Integer, nullable=False)
	reorder_point: Mapped[int] = mapped_column(Integer, nullable=False)
	severity: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO")
	status: Mapped[AlertStatus] = mapped_column(
		Enum(
			AlertStatus,
			name="alert_status_enum",
			create_constraint=True,
			values_callable=_alert_status_values,
		),
		default=AlertStatus.PENDING,
		nullable=False,
	)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
	acknowledged_by: Mapped[str | None] = mapped_column(String(100))
