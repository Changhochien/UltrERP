"""JSON-LD structured data generator for schema.org Product."""

from __future__ import annotations

from typing import Any

from common.models.product import Product

_STATUS_AVAILABILITY = {
    "active": "https://schema.org/InStock",
    "discontinued": "https://schema.org/Discontinued",
    "inactive": "https://schema.org/OutOfStock",
}


def generate_product_jsonld(product: Product) -> dict[str, Any]:
    """Generate schema.org Product JSON-LD from a Product model instance."""
    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "sku": product.code,
        "productID": str(product.id),
    }

    if product.description:
        data["description"] = product.description
    if product.category:
        data["category"] = product.category

    # Unit of measure as additionalProperty (only if unit is set)
    if product.unit:
        data["additionalProperty"] = {
            "@type": "PropertyValue",
            "name": "unitOfMeasure",
            "value": product.unit,
        }

    # Availability from status (no price — B2B)
    availability = _STATUS_AVAILABILITY.get(product.status)
    if availability:
        data["offers"] = {
            "@type": "Offer",
            "availability": availability,
        }

    if product.updated_at:
        data["dateModified"] = product.updated_at.isoformat()

    return data
