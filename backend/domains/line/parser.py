"""Parse LINE text messages into order line items.

Supported formats (product-first):
  - "商品A x 3, 商品B x 5" / "商品A X 3" / "商品A × 3"
  - "商品A 3\\n商品B 5"       (space separator)
  - "商品A=3, 商品B=5"
  - "商品A:3, 商品B:5"
  - "商品A*3"
Supported formats (quantity-first Chinese):
  - "3個商品A, 5個商品B"

Returns a list of (product_query, quantity) tuples for product lookup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParsedOrderLine:
	product_query: str
	quantity: int


def parse_order_text(text: str) -> list[ParsedOrderLine]:
	"""Parse message text into order lines. Returns empty list if unparseable."""
	lines: list[ParsedOrderLine] = []
	segments = re.split(r"[,\n、]+", text.strip())
	for segment in segments:
		segment = segment.strip()
		if not segment:
			continue
		parsed = _parse_segment(segment)
		if parsed:
			lines.append(parsed)
	return lines


def _parse_segment(segment: str) -> ParsedOrderLine | None:
	"""Parse a single segment into a ParsedOrderLine."""
	# Pattern 1: Quantity-first Chinese — "3個商品A"
	match = re.match(r"^(\d+)\s*個\s*(.+)$", segment)
	if match:
		qty = int(match.group(1))
		name = match.group(2).strip()
		if name and qty > 0:
			return ParsedOrderLine(product_query=name, quantity=qty)

	# Pattern 2: "ProductName x Quantity" (x/X/×)
	match = re.match(r"^(.+?)\s*[xX×]\s*(\d+)$", segment)
	if match:
		name = match.group(1).strip()
		qty = int(match.group(2))
		if name and qty > 0:
			return ParsedOrderLine(product_query=name, quantity=qty)

	# Pattern 3: "ProductName=Quantity" or ":Quantity" or "*Quantity"
	match = re.match(r"^(.+?)\s*[=:*]\s*(\d+)$", segment)
	if match:
		name = match.group(1).strip()
		qty = int(match.group(2))
		if name and qty > 0:
			return ParsedOrderLine(product_query=name, quantity=qty)

	# Pattern 4: "ProductName Quantity" (space — most ambiguous, try last)
	match = re.match(r"^(.+?)\s+(\d+)$", segment)
	if match:
		name = match.group(1).strip()
		qty = int(match.group(2))
		if name and qty > 0:
			return ParsedOrderLine(product_query=name, quantity=qty)

	return None
