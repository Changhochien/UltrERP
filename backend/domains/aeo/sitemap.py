"""XML sitemap generator for products."""

from __future__ import annotations

import logging
import time
from urllib.parse import quote
from xml.etree.ElementTree import Element, SubElement, tostring

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.models.product import Product
from common.tenant import DEFAULT_TENANT_ID

logger = logging.getLogger(__name__)

_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

# Bounded TTL cache: only ONE entry is ever stored (xml_bytes), preventing unbounded growth.
# TTL expiration is enforced via _cache_timestamp; manual invalidate clears it.
_cached_xml: bytes | None = None
_cache_timestamp: float = 0.0


async def generate_product_sitemap_xml(db: AsyncSession) -> bytes:
    """Generate XML sitemap for active tenant products.

    The cache holds at most one XML payload — bounded to a single entry regardless of
    product count or update frequency. TTL (default 3600 s) is enforced on each call;
    once expired the stale entry is replaced on the next request, not accumulated.

    Note: Module-level cache is adequate for single-process deployment.
    For multi-worker uvicorn, consider shared cache (Redis) in the future.
    """
    global _cached_xml, _cache_timestamp  # noqa: PLW0603

    settings = get_settings()
    now = time.monotonic()
    if _cached_xml is not None and (now - _cache_timestamp) < settings.sitemap_cache_ttl:
        return _cached_xml

    base_url = settings.public_base_url.rstrip("/")

    stmt = (
        select(Product)
        .where(Product.tenant_id == DEFAULT_TENANT_ID)
        .where(Product.status == "active")
        .order_by(Product.code)
    )
    result = await db.execute(stmt)
    products = result.scalars().all()

    urlset = Element("urlset", xmlns=_SITEMAP_NS)

    for product in products:
        url_el = SubElement(urlset, "url")
        loc = SubElement(url_el, "loc")
        # RFC 3986 — encode the UUID path segment
        product_path = quote(str(product.id), safe="")
        loc.text = f"{base_url}/api/v1/inventory/products/{product_path}/jsonld"

        if product.updated_at:
            lastmod = SubElement(url_el, "lastmod")
            lastmod.text = product.updated_at.isoformat()

        changefreq = SubElement(url_el, "changefreq")
        changefreq.text = "weekly"
        priority = SubElement(url_el, "priority")
        priority.text = "0.6"

    xml_bytes = tostring(urlset, encoding="utf-8", xml_declaration=True)

    # Replace (not grow) the single cache entry.
    _cached_xml = xml_bytes
    _cache_timestamp = now

    logger.info("Sitemap regenerated with %d product URLs", len(products))
    return xml_bytes


def invalidate_sitemap_cache() -> None:
    """Clear the sitemap cache. Call after product create/update/delete."""
    global _cached_xml, _cache_timestamp  # noqa: PLW0603
    _cached_xml = None
    _cache_timestamp = 0.0
