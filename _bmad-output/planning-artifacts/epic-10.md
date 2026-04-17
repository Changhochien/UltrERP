## Epic 10: AEO (AI SEO)

### Epic Goal

Products are structured for discoverability in AI-generated search answers.

### Stories

### Story 10.1: Auto-Generate JSON-LD Structured Data

As a system,
I want to auto-generate JSON-LD structured data for products on create,
So that search engines can understand our product data.

**Acceptance Criteria:**

**Given** a product is created or updated
**When** the product is saved
**Then** JSON-LD structured data is automatically generated
**And** includes: name, description, price, availability, SKU
**And** is accessible at `/products/{id}/jsonld` endpoint

### Story 10.2: Auto-Generate XML Sitemap

As a system,
I want to auto-generate an XML sitemap for all products,
So that search engines can crawl our catalog.

**Acceptance Criteria:**

**Given** products exist
**When** the sitemap is requested
**Then** an XML sitemap is generated at `/sitemap-products.xml`
**And** includes all active product URLs
**And** is updated when products are created/modified
**And** is submitted to search engines automatically

### Story 10.3: Product Content for AI Citation

As a system,
I want product content to be structured for maximum citation in AI-generated answers,
So that our products appear in AI search recommendations.

**Acceptance Criteria:**

**Given** a product exists
**When** AI systems crawl or query our data
**Then** product descriptions are written in clear, factual format
**And** include: specifications, use cases, differentiators
**And** structured data follows schema.org Product specification

---

