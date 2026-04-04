"""Pydantic schemas for payment creation and serialization."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentMethod(str, enum.Enum):
	CASH = "CASH"
	BANK_TRANSFER = "BANK_TRANSFER"
	CHECK = "CHECK"
	CREDIT_CARD = "CREDIT_CARD"
	OTHER = "OTHER"


class PaymentCreate(BaseModel):
	invoice_id: uuid.UUID
	amount: Decimal = Field(gt=0)
	payment_method: PaymentMethod
	payment_date: date | None = None
	reference_number: str | None = Field(default=None, max_length=100)
	notes: str | None = Field(default=None, max_length=500)

	@field_validator("amount")
	@classmethod
	def amount_max_two_decimals(cls, v: Decimal) -> Decimal:
		if v.as_tuple().exponent < -2:
			raise ValueError("Amount must have at most 2 decimal places.")
		return v

	@field_validator("payment_date")
	@classmethod
	def reject_future_date(cls, v: date | None) -> date | None:
		if v is not None and v > date.today():
			raise ValueError("Payment date cannot be in the future.")
		return v


class PaymentResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: uuid.UUID
	invoice_id: uuid.UUID | None
	customer_id: uuid.UUID
	payment_ref: str
	amount: Decimal
	payment_method: str
	payment_date: date
	reference_number: str | None = None
	notes: str | None = None
	created_by: str
	created_at: datetime
	updated_at: datetime
	match_status: str
	match_type: str | None = None
	matched_at: datetime | None = None
	suggested_invoice_id: uuid.UUID | None = None


class PaymentListItem(BaseModel):
	"""Compact payment representation for list views.

	Omits notes, reference_number, suggested_invoice_id, matched_at,
	and updated_at compared to PaymentResponse.
	"""
	model_config = ConfigDict(from_attributes=True)

	id: uuid.UUID
	payment_ref: str
	amount: Decimal
	payment_method: str
	payment_date: date
	invoice_id: uuid.UUID | None
	customer_id: uuid.UUID
	created_by: str
	created_at: datetime
	match_status: str
	match_type: str | None = None


class PaymentListResponse(BaseModel):
	items: list[PaymentListItem]
	total: int
	page: int
	page_size: int


class PaymentCreateUnmatched(BaseModel):
	customer_id: uuid.UUID
	amount: Decimal = Field(gt=0)
	payment_method: PaymentMethod
	payment_date: date | None = None
	reference_number: str | None = Field(default=None, max_length=100)
	notes: str | None = Field(default=None, max_length=500)

	@field_validator("amount")
	@classmethod
	def amount_max_two_decimals(cls, v: Decimal) -> Decimal:
		if v.as_tuple().exponent < -2:
			raise ValueError("Amount must have at most 2 decimal places.")
		return v

	@field_validator("payment_date")
	@classmethod
	def reject_future_date(cls, v: date | None) -> date | None:
		if v is not None and v > date.today():
			raise ValueError("Payment date cannot be in the future.")
		return v


class ManualMatchRequest(BaseModel):
	invoice_id: uuid.UUID


class ReconciliationResultItem(BaseModel):
	payment_id: uuid.UUID
	payment_ref: str
	match_status: str
	match_type: str | None = None
	invoice_number: str | None = None
	suggested_invoice_number: str | None = None


class ReconciliationResult(BaseModel):
	matched_count: int
	suggested_count: int
	unmatched_count: int
	details: list[ReconciliationResultItem]
