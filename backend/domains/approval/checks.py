"""Approval gate utilities for sensitive write actions."""

from __future__ import annotations

from common.config import settings


def needs_approval(
	*,
	actor_type: str,
	action: str,
	quantity: int | None = None,
) -> bool:
	if actor_type == "user":
		return False
	if action == "inventory.adjust" and quantity is not None:
		return abs(quantity) > settings.approval_threshold_inventory_adjust
	if action in {"invoices.void", "invoices.submit"}:
		return True
	return False