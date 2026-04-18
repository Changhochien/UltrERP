"""Category master model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base

if TYPE_CHECKING:
	from common.models.product import Product


class CategoryTranslation(Base):
	__tablename__ = "category_translation"
	__table_args__ = (
		Index("uq_category_translation_category_locale", "category_id", "locale", unique=True),
		Index("ix_category_translation_locale", "locale"),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	category_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("category.id", ondelete="CASCADE"),
		nullable=False,
	)
	locale: Mapped[str] = mapped_column(String(10), nullable=False)
	name: Mapped[str] = mapped_column(String(200), nullable=False)
	category: Mapped["Category"] = relationship(
		back_populates="translations",
	)


class Category(Base):
	__tablename__ = "category"
	__table_args__ = (
		Index("uq_category_tenant_name", "tenant_id", "name", unique=True),
	)

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
	)
	tenant_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), nullable=False, index=True,
	)
	name: Mapped[str] = mapped_column(String(200), nullable=False)
	is_active: Mapped[bool] = mapped_column(
		Boolean, default=True, nullable=False,
	)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False,
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)
	translations: Mapped[list["CategoryTranslation"]] = relationship(
		back_populates="category",
		cascade="all, delete-orphan",
	)
	products: Mapped[list["Product"]] = relationship(
		back_populates="category_ref",
	)
