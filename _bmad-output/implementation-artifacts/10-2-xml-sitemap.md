# Story 10.2: Auto-Generate XML Sitemap

Status: completed

## Story

As a system,
I want to auto-generate an XML sitemap for all active products,
so that search engines can discover and crawl our product catalog efficiently.

## Context

XML sitemaps follow the Sitemaps.org protocol (`<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">`). Each product entry needs `<url>/<loc>/<lastmod>`. Since UltrERP is a B2B ERP without public-facing product pages yet, the sitemap URLs point to the JSON-LD API endpoints (`/api/v1/inventory/products/{id}/jsonld`) as canonical machine-readable product representations. When a public product catalog frontend is added, sitemap URLs can be updated to point to the frontend pages.

### Design Decisions

- **No external dependency** — use Python stdlib `xml.etree.ElementTree` for XML generation
- **Dynamic generation** — products change infrequently, so generate on each request with in-memory caching (configurable TTL, default 1 hour)
- **Active products only** — only products with `status = "active"` appear in the sitemap
- **Tenant-scoped** — sitemap serves DEFAULT_TENANT products (single-tenant MVP)
- **Route**: `GET /sitemap-products.xml` mounted at app root (not under `/api/v1/` — sitemaps are conventionally at site root)
- **Size limit**: Sitemap protocol allows max 50,000 URLs per file; sufficient for SMB product catalog

### Sitemap Entry Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/api/v1/inventory/products/{id}/jsonld</loc>
    <lastmod>2026-04-01T12:00:00+00:00</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>
</urlset>
```

## Acceptance Criteria

**AC1:** Sitemap generation at `/sitemap-products.xml`
**Given** active products exist in the database
**When** I request `GET /sitemap-products.xml`
**Then** the response is valid XML with Content-Type `application/xml`
**And** the root element is `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">`
**And** each active product has a `<url>` entry with `<loc>`, `<lastmod>`, `<changefreq>`, `<priority>`

**AC2:** Only active products included
**Given** products exist with statuses "active", "inactive", and "discontinued"
**When** the sitemap is generated
**Then** only products with status = "active" appear
**And** inactive/discontinued products are excluded

**AC3:** Correct `<loc>` URL construction
**Given** the server has a configurable base URL (env var `PUBLIC_BASE_URL`)
**When** a product entry is generated
**Then** `<loc>` is `{PUBLIC_BASE_URL}/api/v1/inventory/products/{product_id}/jsonld`
**And** if `PUBLIC_BASE_URL` is not set, defaults to `http://localhost:8000`

**AC4:** Correct `<lastmod>` timestamps
**Given** a product was last updated at 2026-04-01T12:00:00+08:00
**When** the sitemap entry is generated
**Then** `<lastmod>` is the product's `updated_at` in W3C Datetime format (ISO 8601)

**AC5:** Caching with configurable TTL
**Given** the sitemap was generated less than 1 hour ago
**When** a new request arrives for `/sitemap-products.xml`
**Then** the cached XML response is returned without querying the database
**Given** the cache has expired (> TTL)
**When** a new request arrives
**Then** the sitemap is regenerated from the database

**AC6:** Empty sitemap for no active products
**Given** no active products exist
**When** I request `GET /sitemap-products.xml`
**Then** the response is a valid XML `<urlset>` with zero `<url>` entries

**AC7:** Backend tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass
**And** sitemap tests are added (≥ 8 tests)

## Tasks / Subtasks

- [x] **Task 1: Add PUBLIC_BASE_URL config** (AC3)
  - [x] Add to `backend/common/config.py` Settings class:
    ```python
    public_base_url: str = Field(
        default="http://localhost:8000",
        validation_alias=AliasChoices("PUBLIC_BASE_URL", "public_base_url"),
    )
    ```

- [x] **Task 2: Create sitemap generator** (AC1, AC2, AC4, AC6)
  - [x] Create `backend/domains/aeo/sitemap.py`:
    ```python
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
    _CACHE_TTL_SECONDS = 3600  # 1 hour default

    _cached_xml: bytes | None = None
    _cache_timestamp: float = 0.0


    async def generate_product_sitemap_xml(db: AsyncSession) -> bytes:
        """Generate XML sitemap for active tenant products. Uses in-memory cache.

        Note: Module-level cache is adequate for single-process deployment.
        For multi-worker uvicorn, consider shared cache (Redis) in the future.
        """
        global _cached_xml, _cache_timestamp

        now = time.monotonic()
        if _cached_xml is not None and (now - _cache_timestamp) < _CACHE_TTL_SECONDS:
            return _cached_xml

        settings = get_settings()
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
            # RFC 3986 — encode the UUID path segment (safe for UUIDs but guards edge cases)
            product_path = quote(str(product.id), safe="")
            loc.text = f"{base_url}/api/v1/inventory/products/{product_path}/jsonld"

            if product.updated_at:
                lastmod = SubElement(url_el, "lastmod")
                lastmod.text = product.updated_at.isoformat()

            changefreq = SubElement(url_el, "changefreq")
            changefreq.text = "weekly"
            priority = SubElement(url_el, "priority")
            priority.text = "0.6"

        xml_bytes = tostring(urlset, encoding="unicode", xml_declaration=True).encode("utf-8")

        _cached_xml = xml_bytes
        _cache_timestamp = now

        logger.info("Sitemap regenerated with %d product URLs", len(products))
        return xml_bytes


    def invalidate_sitemap_cache() -> None:
        """Clear the sitemap cache. Call after product create/update/delete."""
        global _cached_xml, _cache_timestamp
        _cached_xml = None
        _cache_timestamp = 0.0
    ```

- [x] **Task 3: Add sitemap route to main app** (AC1, AC5)
  - [x] Add sitemap route to `backend/app/main.py`:
    ```python
    from fastapi import Response
    from domains.aeo.sitemap import generate_product_sitemap_xml

    @app.get("/sitemap-products.xml", include_in_schema=False)
    async def product_sitemap(db: AsyncSession = Depends(get_db)) -> Response:
        xml_bytes = await generate_product_sitemap_xml(db)
        return Response(content=xml_bytes, media_type="application/xml")
    ```

- [x] **Task 4: Write tests** (AC1–AC7)
  - [x] Create `backend/tests/test_aeo_sitemap.py`:
    - Test sitemap returns valid XML with correct namespace
    - Test only active products appear (not inactive/discontinued)
    - Test only tenant's products appear (tenant_id = DEFAULT_TENANT_ID)
    - Test `<loc>` URL construction with default base URL
    - Test `<loc>` URL construction with custom PUBLIC_BASE_URL
    - Test `<loc>` URL is RFC 3986 compliant (properly escaped)
    - Test `<lastmod>` ISO 8601 format
    - Test empty sitemap (no active products)
    - Test Content-Type is `application/xml`
    - Test XML declaration is present (`<?xml version=...?>`)
    - Test cache invalidation via `invalidate_sitemap_cache()`
  - [x] Run full test suite: `cd backend && python -m pytest tests/ -v --tb=short`
  - [x] Run linter: `cd backend && ruff check .`

## Dev Notes

- **No migration needed** — reads from existing Product table
- **No external dependencies** — uses Python stdlib `xml.etree.ElementTree`
- **Cache strategy**: Simple in-memory module-level cache. Adequate for single-process deployment (UltrERP MVP runs single uvicorn worker). For multi-worker/multi-process deployment, switch to shared cache (Redis) or accept short staleness window. Document as known limitation.
- **`invalidate_sitemap_cache()`**: Not wired to product CRUD in this story. Can be integrated in future when product create/update routes are enhanced.
- **Sitemap protocol limit**: 50,000 URLs / 50MB per file. UltrERP SMB products (~1,000-5,000) is well within limits.
- **`/sitemap-products.xml` at root**: Standard convention. Not under `/api/v1/` because sitemaps are consumed by crawlers at well-known paths.
- **`include_in_schema=False`**: Hides from OpenAPI docs — sitemaps are not API endpoints for humans.
- **Future**: When public product pages exist, switch `<loc>` from JSON-LD endpoint to frontend product page URL. Currently points to `/api/v1/inventory/products/{id}/jsonld`. Add `/robots.txt` with `Sitemap: {base}/sitemap-products.xml`.

## References

- Sitemaps protocol: https://www.sitemaps.org/protocol.html
- W3C Datetime format: https://www.w3.org/TR/NOTE-datetime
- Python xml.etree.ElementTree: https://docs.python.org/3/library/xml.etree.elementtree.html

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (fast mode)

### Completion Notes List
- Implementation verified against `backend/domains/aeo/sitemap.py` — matches story spec
- Improvement over story: actual code uses `settings.sitemap_cache_ttl` instead of hardcoded constant
- Improvement over story: added `SITEMAP_CACHE_TTL` config field to `common/config.py`
- Endpoint at `GET /sitemap-products.xml` mounted at app root, returns `application/xml`
- Admin cache invalidation endpoint: `POST /api/v1/admin/sitemap-cache/invalidate`
- 16 tests in `backend/tests/test_aeo_sitemap.py`, all passing
- No migration needed — reads existing Product table
