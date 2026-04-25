# Story 40.2: Affinity and Customer Profile Service Extraction

**Status:** ready-for-dev

**Story ID:** 40.2

**Epic:** Epic 40 - Intelligence Service Modularization and Architecture Hardening

---

## Story

As a backend developer,
I want the affinity and customer-profile read models extracted into dedicated modules,
so that low-coupling intelligence features stop sharing incidental implementation state with unrelated analytics.

---

## Problem Statement

`get_product_affinity_map()`, `build_empty_customer_product_profile()`, and `get_customer_product_profile()` are comparatively self-contained, but they still live inside the domain monolith. That keeps even low-risk maintenance tied to a file that also owns category trends, aggregate-backed analytics, and buying-behavior logic.

This is the lowest-risk feature extraction slice after Story 40.1 because it exercises the new facade without immediately touching the more coupled category or aggregate-backed paths.

## Solution

Extract the affinity and customer-profile implementations into dedicated modules under `backend/domains/intelligence/services/` and re-export them through `backend/domains/intelligence/service.py`.

The extraction should preserve all current behavior:

- affinity scoring and tie ordering
- customer-profile rollup metrics
- dormant detection and confidence semantics
- empty-state profile construction

## Acceptance Criteria

1. Given Story 40.1 has established the compatibility facade, when Story 40.2 lands, then `get_product_affinity_map()`, `build_empty_customer_product_profile()`, and `get_customer_product_profile()` execute from dedicated modules outside `backend/domains/intelligence/service.py` and are re-exported through it.
2. Given the focused service tests audit those features, when the extraction is complete, then affinity ranking, overlap math, customer-profile dormant detection, confidence calculation, and empty-profile behavior remain unchanged.
3. Given the extracted modules are reviewed, when their imports are inspected, then they depend only on shared support modules, schemas, common models, and owning collaborators rather than unrelated intelligence feature modules.
4. Given routes and MCP tools continue to import through the facade, when focused route and MCP tests run, then the public contract remains unchanged.
5. Given Story 40.2 is complete, when `backend/domains/intelligence/service.py` is inspected, then it no longer owns implementation bodies for these extracted functions.

## Tasks / Subtasks

- [ ] Task 1: Extract product-affinity logic into its own feature module. (AC: 1-3)
  - [ ] Move `get_product_affinity_map()` and its feature-specific helper logic into a dedicated module.
  - [ ] Keep any shared helper logic in the Story 40.1 support layer instead of copying it.
  - [ ] Preserve current ordering and score rounding behavior.
- [ ] Task 2: Extract customer-profile logic into its own feature module. (AC: 1-3)
  - [ ] Move `build_empty_customer_product_profile()` and `get_customer_product_profile()` into a dedicated module.
  - [ ] Keep empty-profile construction explicit and reusable by the feature module.
  - [ ] Preserve dormant and trend semantics exactly.
- [ ] Task 3: Keep the compatibility facade and app surface stable. (AC: 1, 4, 5)
  - [ ] Re-export the extracted functions from `backend/domains/intelligence/service.py`.
  - [ ] Avoid route or MCP caller changes in this story.
  - [ ] Re-run the focused intelligence route and MCP tests.

## Dev Notes

### Architecture Compliance

- Keep this story limited to low-coupling transactional features.
- Do not pull category-trend, market-opportunity, or aggregate-backed helpers into this slice.
- Preserve the existing backend and MCP contracts exactly.

### Suggested File Targets

- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/services/affinity.py`
- `backend/domains/intelligence/services/customer_profile.py`
- `backend/tests/domains/intelligence/test_service.py`
- `backend/tests/domains/intelligence/test_routes.py`
- `backend/tests/test_mcp_intelligence.py`

### Validation Commands

- `cd /Users/changtom/Downloads/UltrERP/backend && uv run pytest tests/domains/intelligence/test_service.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py -q`

## References

- `../planning-artifacts/epic-40.md`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/routes.py`
- `backend/domains/intelligence/mcp.py`
- `backend/tests/domains/intelligence/test_service.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-25: Drafted Story 40.2 as the first feature-extraction slice after the facade is in place.

### File List

- `_bmad-output/implementation-artifacts/40-2-affinity-and-customer-profile-service-extraction.md`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/services/affinity.py`
- `backend/domains/intelligence/services/customer_profile.py`