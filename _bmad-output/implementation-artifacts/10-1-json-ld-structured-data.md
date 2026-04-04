# Story 10.1: Auto-Generate JSON-LD Structured Data

Status: completed

## Story

As a system,
I want to auto-generate JSON-LD structured data for products,
so that search engines and AI systems can understand our product catalog.

## Context

UltrERP is a B2B ERP system. Product structured data enables discoverability by AI answer engines (ChatGPT, Perplexity, Google AI Overviews) and traditional search crawlers. The Product model (see `common/models/product.py`) has: id, tenant_id, code, name, category, description, unit, status, created_at, updated_at. **There is no price/unit_price field** — this is a B2B system where pricing is negotiated per customer. JSON-LD is Google's preferred structured data format (over Microdata/RDFa).

### schema.org Product Mapping

| Product Field | schema.org Property | Notes |
|---|---|---|
| code | sku | Product stock-keeping unit |
| name | name | Required by schema.org |
| description | description | Optional, may be null |
| category | category | Optional, may be null |
| id | productID | Internal identifier |
| code | identifier | Also maps to SKU |
| unit | additionalProperty | Unit of measure (pcs, kg, etc.) |
| status | offers.availability | "active" → InStock, otherwise Discontinued |
| updated_at | dateModified | ISO 8601 |

No Offer.price section — B2B pricing is negotiated. The JSON-LD omits price entirely per schema.org recommendation for B2B products.

### Architecture Decision

- New `backend/domains/aeo/` domain module (Answer Engine Optimization)
- JSON-LD generation is a pure function: `Product` model → `dict`
- Exposed via API endpoint mounted on the existing products router (not a separate router)
- No database changes required
- No external dependencies required

## Acceptance Criteria

**AC1:** JSON-LD generation for a product
**Given** a product exists with name, code, and category
**When** I request `GET /api/v1/inventory/products/{product_id}/jsonld`
**Then** the response is `application/ld+json` with Content-Type header
**And** the body is valid JSON-LD with `@context: "https://schema.org"` and `@type: "Product"`
**And** `name` maps from product.name
**And** `sku` maps from product.code
**And** `productID` maps from str(product.id)
**And** `category` maps from product.category (omitted if null)
**And** `description` maps from product.description (omitted if null)
**And** `dateModified` is product.updated_at in ISO 8601 format

**AC2:** Unit of measure as additionalProperty
**Given** a product has unit = "kg"
**When** JSON-LD is generated
**Then** the output includes `additionalProperty` with `@type: PropertyValue`, `name: "unitOfMeasure"`, `value: "kg"`

**AC3:** Availability mapping from status
**Given** a product has status = "active"
**When** JSON-LD is generated
**Then** the output includes `offers.availability: "https://schema.org/InStock"`
**Given** a product has status = "discontinued"
**When** JSON-LD is generated
**Then** the output includes `offers.availability: "https://schema.org/Discontinued"`
**And** offers does NOT include price (B2B — pricing is negotiated)

**AC4:** Graceful handling of missing optional fields
**Given** a product has category=None and description=None
**When** JSON-LD is generated
**Then** the `category` and `description` keys are omitted from the output
**And** the JSON-LD is still valid schema.org Product

**AC5:** 404 for non-existent product
**Given** a product_id that does not exist
**When** I request `GET /api/v1/inventory/products/{product_id}/jsonld`
**Then** the response is 404

**AC6:** Backend tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing 431 tests continue to pass
**And** JSON-LD tests are added (≥ 8 tests)

## Tasks / Subtasks

- [x] **Task 1: Create AEO domain module** (AC1)
  - [x] Create `backend/domains/aeo/__init__.py`
  - [x] Create `backend/domains/aeo/jsonld.py`:
    ```python
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

        # Unit of measure as additionalProperty
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
    ```

- [x] **Task 2: Add JSON-LD endpoint to products router** (AC1, AC5)
  - [x] Add to `backend/domains/inventory/routes.py`:
    ```python
    from domains.aeo.jsonld import generate_product_jsonld
    from fastapi.responses import JSONResponse

    @router.get("/products/{product_id}/jsonld")
    async def get_product_jsonld(
        product_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
    ) -> JSONResponse:
        """Return JSON-LD structured data for a product."""
        product = await db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        jsonld = generate_product_jsonld(product)
        return JSONResponse(
            content=jsonld,
            media_type="application/ld+json",
        )
    ```

- [x] **Task 3: Write tests** (AC1–AC6)
  - [x] Create `backend/tests/test_aeo_jsonld.py`:
    - Test `generate_product_jsonld` with all fields populated
    - Test with category=None, description=None (omitted from output)
    - Test status → availability mapping: active, discontinued, inactive, unknown
    - Test unit of measure additionalProperty
    - Test productID is string UUID
    - Test dateModified ISO 8601 format
    - Test API endpoint returns 200 with `application/ld+json`
    - Test API endpoint returns 404 for unknown product_id
  - [x] Run full test suite: `cd backend && python -m pytest tests/ -v --tb=short`
  - [x] Run linter: `cd backend && ruff check .`

## Dev Notes

- **No migration needed** — this is read-only generation from existing Product data
- **No new dependencies** — pure Python dict construction
- **`application/ld+json`** is the official IANA media type for JSON-LD
- **B2B pricing**: schema.org recommends omitting Offer.price when pricing is not publicly available; we include Offer only for availability signaling
- **Route path**: `/products/{product_id}/jsonld` within the inventory router → full path `/api/v1/inventory/products/{product_id}/jsonld`
- **Future enhancement**: When a public product catalog frontend exists, add `url` and `@id` properties pointing to the canonical product page URL
- **schema.org validation**: Generated JSON-LD should pass https://validator.schema.org/

## References

- schema.org Product: https://schema.org/Product
- Google JSON-LD guidance: https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
- JSON-LD media type: https://www.iana.org/assignments/media-types/application/ld+json

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (fast mode)

### Completion Notes List
- Implementation verified against `backend/domains/aeo/jsonld.py` — matches story spec
- Minor improvement over story: actual code guards `additionalProperty` with `if product.unit:` (handles nullable unit)
- Endpoint at `GET /api/v1/inventory/products/{product_id}/jsonld` returns `application/ld+json`
- 14 tests in `backend/tests/test_aeo_jsonld.py`, all passing
- No migration needed — pure function over existing Product model
