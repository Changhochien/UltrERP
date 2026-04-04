# Story 10.3: Product Content for AI Citation

Status: completed

## Story

As a system,
I want product content to be structured for maximum citation in AI-generated answers,
so that our products appear in AI search recommendations and answer engine results.

## Context

Answer Engine Optimization (AEO) goes beyond structured data markup. AI systems (ChatGPT, Perplexity, Google AI Overviews, Bing Copilot) prefer content that is:
1. **Clearly factual** — specifications, categories, use cases in direct language
2. **Concise** — 40-60 word answer blocks that AI can directly quote
3. **Well-structured** — headings, lists, FAQ format for easy parsing
4. **E-E-A-T signals** — experience, expertise, authoritativeness, trustworthiness

This story creates a **structured content API endpoint** that returns product data in an AI-friendly format, combining:
- Product metadata (from DB)
- schema.org JSON-LD (from Story 10.1)
- FAQ-style content blocks derived from product attributes
- Semantic HTML-ready content for future frontend rendering

### Architecture Decision

- **New endpoint**: `GET /api/v1/inventory/products/{product_id}/aeo` returns structured content
- **Pure function**: `generate_aeo_content(product: Product) -> dict` composes the response
- **Reuses Story 10.1**: Embeds JSON-LD from `generate_product_jsonld()`
- **No database changes** — reads existing Product model
- **No external dependencies** — pure Python
- **Future**: Frontend can consume this endpoint to render AEO-optimized product pages

### Response Format

```json
{
  "product_summary": "Brief factual summary for AI citation (40-60 words)",
  "specifications": {
    "sku": "ABC-001",
    "category": "Electronics",
    "unit_of_measure": "pcs",
    "availability": "In Stock"
  },
  "faq": [
    {
      "question": "What is ABC-001?",
      "answer": "ABC-001 is a ... available in pcs units."
    }
  ],
  "jsonld": { ... },
  "meta": {
    "generated_at": "2026-04-01T12:00:00+08:00",
    "schema_version": "1.0"
  }
}
```

## Acceptance Criteria

**AC1:** AEO content endpoint
**Given** a product exists
**When** I request `GET /api/v1/inventory/products/{product_id}/aeo`
**Then** the response is JSON with `product_summary`, `specifications`, `faq`, `jsonld`, and `meta` sections
**And** Content-Type is `application/json`

**AC2:** Product summary generation
**Given** a product with name="Premium Widget A", category="Hardware", description="High-quality industrial widget for assembly lines"
**When** AEO content is generated
**Then** `product_summary` is a concise factual sentence combining name, category, and description
**And** the summary is between 20 and 100 words

**AC3:** Product summary without description
**Given** a product with name="Basic Part X" and description=None
**When** AEO content is generated
**Then** `product_summary` is generated from name, category, and unit only
**And** the summary is still a grammatically correct sentence

**AC4:** Specifications section
**Given** a product with code="WDG-100", category="Tools", unit="pcs", status="active"
**When** AEO content is generated
**Then** `specifications.sku` is "WDG-100"
**And** `specifications.category` is "Tools" (or "Uncategorized" if null)
**And** `specifications.unit_of_measure` is "pcs"
**And** `specifications.availability` is "In Stock" for active, "Discontinued" for discontinued, "Out of Stock" for inactive

**AC5:** FAQ generation
**Given** a product exists
**When** AEO content is generated
**Then** `faq` contains at least 2 entries
**And** each entry has `question` and `answer` strings
**And** questions use the product name/code
**And** answers are factual and concise (under 100 words each)

**AC6:** Embedded JSON-LD
**Given** a product exists
**When** AEO content is generated
**Then** `jsonld` contains the complete schema.org Product JSON-LD from Story 10.1
**And** has `@context: "https://schema.org"` and `@type: "Product"`

**AC7:** 404 for non-existent product
**Given** a product_id that does not exist
**When** I request `GET /api/v1/inventory/products/{product_id}/aeo`
**Then** the response is 404

**AC8:** Backend tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass
**And** AEO content tests are added (≥ 10 tests)

## Tasks / Subtasks

- [x] **Task 1: Create AEO content generator** (AC1–AC6)
  - [x] Create `backend/domains/aeo/content.py`:
    ```python
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


    def _build_faq(product: Product) -> list[dict[str, str]]:
        """Generate FAQ entries derived from product attributes."""
        faq: list[dict[str, str]] = []

        # Q1: What is this product?
        answer_parts = [f"{product.name} (SKU: {product.code})"]
        if product.category:
            answer_parts.append(f"belongs to the {product.category} category")
        if product.description:
            answer_parts.append(product.description[:200])
        answer_parts.append(f"It is measured in {product.unit} units.")
        faq.append({
            "question": f"What is {product.name}?",
            "answer": " ".join(answer_parts),
        })

        # Q2: Availability
        avail = _STATUS_AVAILABILITY_LABEL.get(product.status, "unknown")
        faq.append({
            "question": f"Is {product.name} available?",
            "answer": f"{product.name} is currently {avail}."
            + (f" SKU: {product.code}." if product.status == "active" else ""),
        })

        # Q3: Category (only if category exists)
        if product.category:
            faq.append({
                "question": f"What category does {product.name} belong to?",
                "answer": f"{product.name} is classified under {product.category}.",
            })

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
                    product.status, "Unknown",
                ),
            },
            "faq": _build_faq(product),
            "jsonld": generate_product_jsonld(product),
            "meta": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "schema_version": _AEO_SCHEMA_VERSION,
            },
        }
    ```

- [x] **Task 2: Add AEO endpoint to products router** (AC1, AC7)
  - [x] Add to `backend/domains/inventory/routes.py`:
    ```python
    from domains.aeo.content import generate_aeo_content

    @router.get("/products/{product_id}/aeo")
    async def get_product_aeo(
        product_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
    ) -> dict:
        """Return AEO-optimized content bundle for a product."""
        product = await db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return generate_aeo_content(product)
    ```

- [x] **Task 3: Write tests** (AC1–AC8)
  - [x] Create `backend/tests/test_aeo_content.py`:
    - Test `generate_aeo_content` returns all required sections
    - Test `_build_summary` with full fields (name, category, description)
    - Test `_build_summary` with missing description
    - Test `_build_summary` with missing category
    - Test `_build_summary` word count cap (100 words max)
    - Test `_build_summary` with very long description (truncated to first sentence)
    - Test `specifications.availability` mapping for active/discontinued/inactive/unknown
    - Test `specifications.category` defaults to "Uncategorized" when null
    - Test `faq` contains at least 2 entries
    - Test `faq` contains 3 entries when category is present
    - Test `jsonld` section has valid schema.org Product structure
    - Test `meta.schema_version` is "1.0"
    - Test API endpoint returns 200 with correct structure
    - Test API endpoint returns 404 for unknown product_id
  - [x] Run full test suite: `cd backend && python -m pytest tests/ -v --tb=short`
  - [x] Run linter: `cd backend && ruff check .`

## Dev Notes

- **No migration needed** — reads existing Product model
- **No external dependencies** — pure Python
- **Reuses Story 10.1** — `generate_product_jsonld()` is called within `generate_aeo_content()`
- **Summary word count**: Targeting 20-100 words ensures AI systems can directly cite without truncation issues
- **FAQ format**: Follows schema.org FAQPage pattern. Future enhancement: render as `<script type="application/ld+json">` FAQPage markup on the frontend
- **IMPORTANT — FAQ visibility**: Google requires FAQ content to be **visible on the page** for FAQPage structured data to be valid. The frontend MUST render FAQ entries as visible `<h3>` + `<p>` markup (not hidden). The `faq` section in the API response is data-only; structured data rendering is a frontend concern.
- **E-E-A-T signals**: Product data comes from the authoritative ERP system (first-party data). The `meta.generated_at` timestamp signals freshness.
- **Model limitations**: Product model currently lacks `brand` and `image` fields. When these are added (future epic), extend JSON-LD and AEO content accordingly. Do NOT modify the Product model in this story.
- **Content evolution**: As product data enriches (images, certifications, technical specs), the AEO content generator can be extended without API changes
- **Perplexity/ChatGPT**: These AIs prefer concise, factual, structured answers — the FAQ format is specifically optimized for this
- **Future**: Frontend product pages should embed `jsonld` in `<head>` and render `faq` with visible Q&A markup (Google requires FAQ content to be visible on-page, not just in structured data)

## References

- Google AEO guidance: https://developers.google.com/search/blog/2025/05/succeeding-in-ai-search
- schema.org FAQPage: https://schema.org/FAQPage
- E-E-A-T: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- AEO structured data best practices: https://geneo.app/blog/schema-markup-structured-data-best-practices-geo-ai-search-2025/

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (fast mode)

### Completion Notes List
- Implementation verified against `backend/domains/aeo/content.py` — matches story spec
- Improvement over story: actual code uses schema.org FAQPage format (`name` + `acceptedAnswer.@type.Answer.text`) vs story's simpler `question/answer` keys
- AEO bundle returns 5 sections: product_summary, specifications, faq, jsonld, meta
- Endpoint at `GET /api/v1/inventory/products/{product_id}/aeo`
- 28 tests in `backend/tests/test_aeo_content.py`, all passing
- No migration needed — pure function over existing Product model
