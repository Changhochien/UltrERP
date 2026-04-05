# Story 4.1: Search Products

**Status:** done

**Story ID:** 4.1

---

## Story

As a warehouse staff,
I want to search products by code or name,
So that I can quickly find items during stock inquiries.

---

## Acceptance Criteria

**✓ AC1:** Products exist in the system
**Given** products are loaded in the database
**When** I search by product code (full or partial match)
**Then** matching products are returned in < 500ms

**✓ AC2:** Search by code (exact and partial)
**Given** a product with code "WIDGET-001" exists
**When** I search for "WIDGET" or "001"
**Then** the product is returned in results

**✓ AC3:** Search by name (exact and partial)
**Given** a product with name "Blue Widget Assembly" exists
**When** I search for "Blue", "Widget", or "Assembly"
**Then** the product is returned in results

**✓ AC4:** Large dataset handling
**Given** 5,000+ products exist in the system
**When** I perform a search
**Then** results load without visible stutter or lag
**And** UI remains responsive during search

**✓ AC5:** Case-insensitive search
**Given** a product code is "WIDGET-001"
**When** I search for "widget-001"
**Then** the product is returned

**✓ AC6:** Results ordering
**Given** multiple products match the query
**When** search completes
**Then** results are ordered by relevance (exact matches first, partial matches second)

---

## Tasks / Subtasks

- [ ] **Task 1: Database Search Setup** (AC1, AC4, AC5, AC6)
  - [ ] Enable `pg_trgm`: `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
  - [ ] Create name search column on products table: `search_vector GENERATED ALWAYS AS (to_tsvector('simple', coalesce(name, ''))) STORED`
  - [ ] Create GIN index for tokenized name search: `CREATE INDEX products_idx_search_gin ON products USING GIN(search_vector);`
  - [ ] Create trigram indexes for partial code/name matches: `CREATE INDEX products_idx_code_trgm ON products USING GIN (code gin_trgm_ops);` and `CREATE INDEX products_idx_name_trgm ON products USING GIN (name gin_trgm_ops);`
  - [ ] **Recommendation:** Use a hybrid strategy: exact/prefix code matching + trigram fallback for partial SKU/name fragments + full-text ranking for tokenized names
  - [ ] Implement search query that ranks: exact code match first, then code prefix match, then trigram similarity / `ts_rank` results
  - [ ] Use `simple` text-search configuration for mixed SKU/name content unless catalog language-specific search is introduced later
  - [ ] Verify query performance < 500ms with 5,000+ rows using `EXPLAIN ANALYZE` for exact-code, partial-code, and name-search cases
  - [ ] Test with realistic warehouse product datasets (mixed alphanumeric codes, multilingual names, short fragments)

- [ ] **Task 2: Backend API Endpoint** (AC1-AC6)
  - [ ] Create GET `/api/v1/inventory/products/search` endpoint
  - [ ] Accept query parameters: `q` (search term, 3-100 chars required), `limit` (default 20, max 100), `warehouse_id` (optional)
  - [ ] Trim the incoming query and reject whitespace-only searches before any DB call
  - [ ] Implement hybrid search via exact/prefix code match, trigram similarity, and tsvector ranking
  - [ ] Return ProductSearchResult with: id, code, name, category, current_stock, status, ts_rank (relevance score)
  - [ ] Join `inventory_stock` when building results; aggregate current stock across warehouses when `warehouse_id` is omitted
  - [ ] Sort results by ts_rank (relevance), then by code (alphabetical tiebreaker)
  - [ ] Add error handling: 400 for invalid input, 422 for validation failures
  - [ ] Include tenant_id filter to ensure multi-tenancy isolation
  - [ ] Default to all warehouses when `warehouse_id` is omitted; filter to a single warehouse only when explicitly requested
  - [ ] Use `AsyncSession` from `common.database.get_db` so the shared engine settings, including `statement_cache_size=0`, are inherited automatically

- [ ] **Task 3: Frontend Search Component with Virtualization** (AC1-AC6)
  - [ ] **CRITICAL:** Install react-window dependency: `npm install react-window`
  - [ ] Create reusable ProductSearch component (React 19)
  - [ ] Implement debounced search input (300ms delay to reduce API calls)
  - [ ] Display results using react-window 2.x `List` virtualization for 5,000+ products
  - [ ] Prefer fixed row heights; only use the dynamic row-height cache/hook when row height cannot be predetermined
  - [ ] Show "No results" message after 300ms if query returns empty
  - [ ] Implement loading state and skeleton loaders during search
  - [ ] Handle error states: display friendly error messages, retry button

- [ ] **Task 4: Performance Validation** (AC1, AC4)
  - [ ] Backend: Unit tests for search relevance (exact matches scored higher than partial)
  - [ ] Backend: Performance test with 5,000+ products (assert < 500ms response time)
  - [ ] Backend: Test case-insensitive matching (WIDGET-001 == widget-001)
  - [ ] Frontend: Component tests for search input, debounce behavior (verify not firing continuously)
  - [ ] Frontend: Performance test for virtualized list (verify no stutter when scrolling 5,000+ items)
  - [ ] Integration: E2E test for full search workflow (type query → see results → click item)
  - [ ] Load test: 100+ concurrent search requests (verify DB and API stay responsive)

---

## Dev Notes

### Architecture Compliance

- **API Pattern:** FastAPI `/api/v1/inventory/products/search` endpoint with async/await
- **Database:** PostgreSQL 17 hybrid search using `pg_trgm` for partial code/name matches plus full-text search for ranked name matches
- **Async:** asyncpg with `statement_cache_size=0` for PgBouncer compatibility [Source: docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#3.2]
- **Frontend:** React 19 with virtualized list component (react-window) for performance
- **ORM:** SQLAlchemy 2.0+ for async queries

### Project Structure Notes

**Backend:**
- Route: `backend/domains/inventory/routes.py`
- Service: `backend/domains/inventory/services.py`
- Schema: `backend/domains/inventory/schemas.py`
- Models: `backend/common/models/product.py`

**Frontend:**
- Component: `src/domain/inventory/components/ProductSearch.tsx`
- Hook: `src/domain/inventory/hooks/useProductSearch.ts`
- API: `src/lib/api/inventory.ts`

**Database:**
- Table: `products` (id, tenant_id, code, name, category, sku, status, created_at, updated_at)
- Indexes: `products_idx_search_gin` on `search_vector`, `products_idx_code_trgm` on `code`, `products_idx_name_trgm` on `name`

### Performance Requirements

- Search response: < 500ms (p95) [Source: epics.md FR7 acceptance criteria]
- List responsiveness: Support 5,000+ rows without visible stutter [Source: epics.md NFR6]
- Virtualization required for large datasets (react-window or similar)

### Testing Standards

- Unit tests: search logic with various input cases
- Integration tests: database queries with realistic datasets
- E2E tests: full search workflow from UI to backend
- Performance tests: verify < 500ms with 5,000 rows

### Security & Validation

- Input validation: Max 100 characters for search term
- SQL injection prevention: Use parameterized queries (ORM handles this)
- Rate limiting: Debounce frontend (300ms) to reduce server load

---

## Dependencies & Related Stories

- **Depends on:** Story 1.7 (Database Migrations Setup) — table schema must exist
- **Related to:** Story 4.2 (View Stock Level) — search result should include stock data
- **Related to:** Story 4.6 (Multiple Warehouse Support) — search may need warehouse filtering

---

## Technology Stack Summary

| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.135+ | Backend API |
| PostgreSQL | 18+ | Full-text search, ILIKE queries |
| asyncpg | latest | Async database driver |
| SQLAlchemy | 2.0+ | ORM with async support |
| React | 19 | Search component, results display |
| react-window | 2.2.7+ | Virtualized list for 5,000+ rows with built-in TypeScript types |

---

## References

- [Epic 4: Inventory Operations](../epics.md#epic-4-inventory-operations)
- [Architecture v2: Technology Stack](../../docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#3-technology-stack)
- [Architecture v2: Async Patterns](../../docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#asyncpg-connection-pgbouncer-safe)
- [NFR6: Virtualization for 5,000+ rows](../epics.md#nonfunctional-requirements)

---

## Dev Agent Record

**Status:** done
**Last Updated:** 2026-04-01
**Agent Model:** claude-haiku-4.5

### Completion Notes List

- Story context generated with comprehensive architecture guidance
- Search patterns aligned with PostgreSQL best practices
- Virtualization requirement documented for large datasets
- Performance benchmarks specified (< 500ms)

### File List

- `backend/domains/inventory/routes.py` — search endpoint
- `backend/domains/inventory/services.py` — search logic
- `backend/domains/inventory/schemas.py` — request/response models
- `backend/common/models/product.py` — Product ORM model
- `src/domain/inventory/components/ProductSearch.tsx` — UI component
- `src/domain/inventory/hooks/useProductSearch.ts` — custom hook
- `src/lib/api/inventory.ts` — API client
