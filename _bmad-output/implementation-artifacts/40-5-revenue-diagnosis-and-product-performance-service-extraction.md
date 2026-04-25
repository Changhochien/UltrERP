# Story 40.5: Revenue Diagnosis and Product Performance Service Extraction

**Status:** ready-for-dev

**Story ID:** 40.5

**Epic:** Epic 40 - Intelligence Service Modularization and Architecture Hardening

---

## Story

As a backend developer,
I want the aggregate-backed intelligence features extracted into dedicated modules,
so that the heaviest analytics logic can share one explicit support seam and the old monolith can collapse into a facade only.

---

## Problem Statement

The second half of `backend/domains/intelligence/service.py` contains the largest and most interdependent implementation block in the intelligence domain:

- revenue diagnosis
- product performance
- aggregate-window helpers
- product-performance evidence loading
- duplicated month/window math

Until this slice is extracted, the monolith cannot become a true compatibility facade. This story is the final restructure step because it depends on the shared support layer from Story 40.1 and benefits from the earlier feature-module extraction pattern.

## Solution

Extract the aggregate-backed intelligence features into dedicated modules and finish the facade-only conversion of `backend/domains/intelligence/service.py`.

The story should preserve shipped behavior from Epic 20:

- partial current-month handling
- aggregate versus live data-basis semantics
- snapshot label resolution
- lifecycle-stage precedence
- deterministic ranking and sorting

It should also consolidate any remaining duplicate month or window helpers into one shared support seam.

## Acceptance Criteria

1. Given Stories 40.1 through 40.4 are complete, when Story 40.5 lands, then `get_revenue_diagnosis()` and `get_product_performance()` are implemented outside `backend/domains/intelligence/service.py` and re-exported through it.
2. Given the aggregate-backed slice currently owns duplicated month or window logic, when Story 40.5 is complete, then that logic is consolidated into shared support instead of duplicated across feature modules.
3. Given the focused backend suite runs, when the extraction is complete, then partial-current-month behavior, snapshot label resolution, lifecycle precedence, and deterministic ordering remain unchanged.
4. Given Epic 40 is complete, when `backend/domains/intelligence/service.py` is inspected, then it contains facade-only imports and no remaining feature implementation bodies.
5. Given routes and MCP tools remain mounted through the facade, when focused route and MCP tests run, then the public contract remains unchanged.

## Tasks / Subtasks

- [ ] Task 1: Extract revenue-diagnosis logic into a dedicated module. (AC: 1-5)
  - [ ] Move `get_revenue_diagnosis()` and its feature-specific helper logic into `services/revenue_diagnosis.py`.
  - [ ] Preserve Story 20.4 arithmetic, data-basis, and deterministic ordering behavior.
- [ ] Task 2: Extract product-performance logic into a dedicated module. (AC: 1-5)
  - [ ] Move `get_product_performance()` and its feature-specific helper logic into `services/product_performance.py`.
  - [ ] Preserve lifecycle precedence, evidence loading, and current-window behavior.
- [ ] Task 3: Finish the facade-only conversion. (AC: 2, 4, 5)
  - [ ] Consolidate the remaining shared month/window helpers into the shared support layer.
  - [ ] Remove remaining implementation bodies from `backend/domains/intelligence/service.py`.
  - [ ] Re-export the extracted public functions through the facade.
- [ ] Task 4: Re-run the focused aggregate-backed intelligence suite. (AC: 3, 5)
  - [ ] Validate revenue diagnosis, product performance, routes, and MCP behavior with focused tests.

## Dev Notes

### Architecture Compliance

- Keep this story focused on the aggregate-backed intelligence slice plus final facade cleanup.
- Do not mix schema-file decomposition into this story unless the extraction is blocked without it.
- Preserve Story 20 data semantics exactly; this is an architecture refactor, not a business-logic rewrite.

### Suggested File Targets

- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/services/revenue_diagnosis.py`
- `backend/domains/intelligence/services/product_performance.py`
- `backend/tests/domains/intelligence/test_revenue_diagnosis_service.py`
- `backend/tests/domains/intelligence/test_product_performance_service.py`
- `backend/tests/domains/intelligence/test_routes.py`
- `backend/tests/test_mcp_intelligence.py`
- `backend/tests/test_mcp_auth.py`

### Validation Commands

- `cd /Users/changtom/Downloads/UltrERP/backend && uv run pytest tests/domains/intelligence/test_revenue_diagnosis_service.py tests/domains/intelligence/test_product_performance_service.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/test_mcp_auth.py -q`

## References

- `../planning-artifacts/epic-40.md`
- `backend/domains/intelligence/service.py`
- `backend/tests/domains/intelligence/test_revenue_diagnosis_service.py`
- `backend/tests/domains/intelligence/test_product_performance_service.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-25: Drafted Story 40.5 as the final extraction slice that retires the remaining intelligence-service monolith implementation behind the new facade.

### File List

- `_bmad-output/implementation-artifacts/40-5-revenue-diagnosis-and-product-performance-service-extraction.md`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/services/revenue_diagnosis.py`
- `backend/domains/intelligence/services/product_performance.py`