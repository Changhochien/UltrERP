"""Currency and exchange rate master models for Epic 25 multi-currency foundation."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class Currency(Base):
    """Tenant-scoped currency master with symbol, precision, and active-state metadata.

    This model is the authoritative source for currency metadata within a tenant,
    replacing direct lookups against app_settings for currency information.
    """

    __tablename__ = "currencies"
    __table_args__ = (
        Index("ix_currencies_tenant_active", "tenant_id", "is_active"),
        Index("uq_currencies_tenant_code", "tenant_id", "code", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # ISO 4217 currency code (e.g., "TWD", "USD", "EUR")
    code: Mapped[str] = mapped_column(String(3), nullable=False)

    # Currency symbol for display (e.g., "$", "€", "NT$")
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)

    # Decimal precision for monetary amounts (typically 0, 2, or 3)
    decimal_places: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    # Whether this currency is available for new transactions
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Only one currency per tenant should have this flag set to True
    # This is the tenant's base (functional) currency
    is_base_currency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )


class ExchangeRate(Base):
    """Tenant-scoped exchange rate master with effective-date lookup support.

    Stores exchange rates between currency pairs with effective-date semantics.
    The effective date allows historical rate lookup for transaction recording.
    """

    __tablename__ = "exchange_rates"
    __table_args__ = (
        Index(
            "ix_exchange_rates_tenant_source_target_date",
            "tenant_id",
            "source_currency_code",
            "target_currency_code",
            "effective_date",
        ),
        Index(
            "uq_exchange_rates_tenant_source_target_date",
            "tenant_id",
            "source_currency_code",
            "target_currency_code",
            "effective_date",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Source currency code (the transaction/foreign currency)
    source_currency_code: Mapped[str] = mapped_column(String(3), nullable=False)

    # Target currency code (the base/reporting currency)
    target_currency_code: Mapped[str] = mapped_column(String(3), nullable=False)

    # Effective date for this rate (rate applies from this date forward until superseded)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Exchange rate with high precision suitable for FX conversion
    # 1 unit of source_currency = rate units of target_currency
    # Uses Numeric(20, 10) for sufficient precision in FX calculations
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)

    # Optional: indicates if this is an inverse rate (system-computed from reverse pair)
    is_inverse: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Optional: reference to the source of this rate (e.g., "manual", "ecb", "central_bank")
    rate_source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Whether this rate is active (inactive rates are excluded from lookups)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )



