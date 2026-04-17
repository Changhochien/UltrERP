"""ORM models for backend-only product analytics foundations."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class SalesMonthly(Base):
    __tablename__ = "sales_monthly"
    __table_args__ = (
        Index(
            "uq_sales_monthly_tenant_month_product_snapshot",
            "tenant_id",
            "month_start",
            "product_id",
            "product_name_snapshot",
            "product_category_snapshot",
            unique=True,
        ),
        Index("ix_sales_monthly_tenant_month", "tenant_id", "month_start"),
        Index("ix_sales_monthly_tenant_month_category", "tenant_id", "month_start", "product_category_snapshot"),
        Index("ix_sales_monthly_tenant_product_month", "tenant_id", "product_id", "month_start"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    month_start: Mapped[date] = mapped_column(Date, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(500), nullable=False)
    product_category_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity_sold: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    order_count: Mapped[int] = mapped_column(Integer, nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    avg_unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )
