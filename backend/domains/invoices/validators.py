"""Invoice validation — totals recomputation and immutability guards."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from domains.invoices.models import Invoice


_TWOPLACES = Decimal("0.01")


def _quantize(amount: Decimal) -> Decimal:
	return amount.quantize(_TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class TotalsDiscrepancy:
	"""Structured report of a totals mismatch."""
	field: str
	expected: Decimal
	actual: Decimal

	@property
	def difference(self) -> Decimal:
		return self.actual - self.expected


def validate_invoice_totals(invoice: Invoice) -> list[TotalsDiscrepancy]:
	"""Recompute invoice totals from persisted line snapshots.

	Returns an empty list if totals are consistent, or a list of
	discrepancies if any field does not match.
	"""
	discrepancies: list[TotalsDiscrepancy] = []

	recomputed_subtotal = _quantize(
		sum((line.subtotal_amount for line in invoice.lines), start=Decimal("0.00"))
	)
	recomputed_tax = _quantize(
		sum((line.tax_amount for line in invoice.lines), start=Decimal("0.00"))
	)
	recomputed_total = _quantize(recomputed_subtotal + recomputed_tax)

	if recomputed_subtotal != invoice.subtotal_amount:
		discrepancies.append(TotalsDiscrepancy(
			field="subtotal_amount",
			expected=recomputed_subtotal,
			actual=invoice.subtotal_amount,
		))

	if recomputed_tax != invoice.tax_amount:
		discrepancies.append(TotalsDiscrepancy(
			field="tax_amount",
			expected=recomputed_tax,
			actual=invoice.tax_amount,
		))

	if recomputed_total != invoice.total_amount:
		discrepancies.append(TotalsDiscrepancy(
			field="total_amount",
			expected=recomputed_total,
			actual=invoice.total_amount,
		))

	return discrepancies


# ── Immutability guard ─────────────────────────────────────────

# Fields that must never change after invoice creation.
IMMUTABLE_FIELDS: frozenset[str] = frozenset({
	"invoice_number",
	"invoice_date",
	"customer_id",
	"buyer_type",
	"buyer_identifier_snapshot",
	"currency_code",
	"subtotal_amount",
	"tax_amount",
	"total_amount",
})

IMMUTABLE_ERROR = "Invoices are immutable after creation"
