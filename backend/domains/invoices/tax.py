"""Tax policy helpers for invoice creation.

This module keeps invoice tax rules backend-owned so frontend code only
submits policy identifiers and receives persisted totals back from the API.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from types import MappingProxyType

_TWOPLACES = Decimal("0.01")


class TaxPolicyCode(StrEnum):
    STANDARD = "standard"
    ZERO = "zero"
    EXEMPT = "exempt"
    SPECIAL = "special"


@dataclass(frozen=True, slots=True)
class TaxPolicy:
    code: TaxPolicyCode
    tax_type: int
    tax_rate: Decimal
    zero_tax_rate_reason: str | None = None


@dataclass(frozen=True, slots=True)
class InvoiceLineAmounts:
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    tax_type: int
    tax_rate: Decimal
    zero_tax_rate_reason: str | None = None


_POLICIES: dict[TaxPolicyCode, TaxPolicy] = MappingProxyType(
    {
        TaxPolicyCode.STANDARD: TaxPolicy(
            code=TaxPolicyCode.STANDARD,
            tax_type=1,
            tax_rate=Decimal("0.05"),
        ),
        TaxPolicyCode.ZERO: TaxPolicy(
            code=TaxPolicyCode.ZERO,
            tax_type=2,
            tax_rate=Decimal("0.00"),
            zero_tax_rate_reason="export",
        ),
        TaxPolicyCode.EXEMPT: TaxPolicy(
            code=TaxPolicyCode.EXEMPT,
            tax_type=3,
            tax_rate=Decimal("0.00"),
            zero_tax_rate_reason=None,
        ),
        TaxPolicyCode.SPECIAL: TaxPolicy(
            code=TaxPolicyCode.SPECIAL,
            tax_type=4,
            tax_rate=Decimal("0.10"),
        ),
    }
)


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_TWOPLACES, rounding=ROUND_HALF_UP)


def get_tax_policy(policy_code: TaxPolicyCode) -> TaxPolicy:
    return _POLICIES[policy_code]


def calculate_line_amounts(
    *,
    quantity: Decimal,
    unit_price: Decimal,
    policy_code: TaxPolicyCode,
    discount_amount: Decimal | None = None,
) -> InvoiceLineAmounts:
    policy = get_tax_policy(policy_code)
    list_subtotal = _quantize(quantity * unit_price)
    if discount_amount is not None:
        subtotal = _quantize(list_subtotal - discount_amount)
    else:
        subtotal = list_subtotal
    tax_amount = _quantize(subtotal * policy.tax_rate)
    total_amount = _quantize(subtotal + tax_amount)

    return InvoiceLineAmounts(
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        tax_type=policy.tax_type,
        tax_rate=policy.tax_rate,
        zero_tax_rate_reason=policy.zero_tax_rate_reason,
    )


def aggregate_invoice_totals(
    lines: list[InvoiceLineAmounts],
    discount_amount: Decimal | None = None,
    discount_percent: Decimal | None = None,
) -> dict[str, Decimal]:
    subtotal_amount = _quantize(sum((line.subtotal for line in lines), start=Decimal("0.00")))
    if discount_amount is not None:
        subtotal_after_discount = _quantize(subtotal_amount - discount_amount)
    elif discount_percent is not None:
        subtotal_after_discount = _quantize(subtotal_amount * (Decimal("1") - discount_percent))
    else:
        subtotal_after_discount = subtotal_amount
    tax_amount = _quantize(sum((line.tax_amount for line in lines), start=Decimal("0.00")))
    total_amount = _quantize(subtotal_after_discount + tax_amount)

    return {
        "subtotal_amount": subtotal_amount,
        "tax_amount": tax_amount,
        "total_amount": total_amount,
    }
