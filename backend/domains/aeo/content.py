"""AEO content generator for AI citation optimization."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from common.models.product import Product
from domains.aeo.jsonld import generate_product_jsonld

_STATUS_AVAILABILITY_LABEL = {
    "active": "In Stock",
    "discontinued": "Discontinued",
    "inactive": "Out of Stock",
}

_AEO_SCHEMA_VERSION = "1.0"


def _build_summary(product: Product) -> str:
    """Build a concise product summary for AI citation (target: 40-70 words, max 100)."""
    parts = [product.name]

    if product.category:
        parts.append(f"is a {product.category} product")
    else:
        parts.append("is a product")

    if product.description:
        # Use first sentence of description, capped at ~80 chars
        desc = product.description.split(".")[0].strip()
        if len(desc) > 80:
            desc = desc[:77] + "..."
        parts.append(f"— {desc}")

    parts.append(
        f"Available in {product.unit} units."
        if product.status == "active"
        else f"Currently {_STATUS_AVAILABILITY_LABEL.get(product.status, 'unavailable')}."
    )

    summary = " ".join(parts)
    # Hard cap at 100 words for AI citation optimization
    words = summary.split()
    if len(words) > 100:
        summary = " ".join(words[:100]) + "..."
    return summary


def _build_faq(product: Product) -> list[dict[str, Any]]:
    """Generate FAQ entries derived from product attributes.

    Returns FAQPage-compatible structure per schema.org:
    https://schema.org/FAQPage
    """
    faq: list[dict[str, Any]] = []

    # Q1: What is this product?
    answer_parts = [f"{product.name} (SKU: {product.code})"]
    if product.category:
        answer_parts.append(f"belongs to the {product.category} category.")
    if product.description:
        answer_parts.append(product.description[:200])
    answer_parts.append(f"It is measured in {product.unit} units.")
    faq.append(
        {
            "name": f"What is {product.name}?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": " ".join(answer_parts),
            },
        }
    )

    # Q2: Availability
    avail = _STATUS_AVAILABILITY_LABEL.get(product.status, "unknown")
    faq.append(
        {
            "name": f"Is {product.name} available?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"{product.name} is currently {avail}."
                + (f" SKU: {product.code}." if product.status == "active" else ""),
            },
        }
    )

    # Q3: Category (only if category exists)
    if product.category:
        faq.append(
            {
                "name": f"What category does {product.name} belong to?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"{product.name} is classified under {product.category}.",
                },
            }
        )

    return faq


def generate_aeo_content(product: Product) -> dict[str, Any]:
    """Generate full AEO content bundle for a product."""
    return {
        "product_summary": _build_summary(product),
        "specifications": {
            "sku": product.code,
            "category": product.category or "Uncategorized",
            "unit_of_measure": product.unit,
            "availability": _STATUS_AVAILABILITY_LABEL.get(
                product.status,
                "Unknown",
            ),
        },
        "faq": _build_faq(product),
        "jsonld": generate_product_jsonld(product),
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": _AEO_SCHEMA_VERSION,
        },
    }
