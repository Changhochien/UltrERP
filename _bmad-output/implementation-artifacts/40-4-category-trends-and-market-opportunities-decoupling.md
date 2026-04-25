# Story 40.4: Category Trends and Market Opportunities Decoupling

**Status:** review

**Story ID:** 40.4

**Epic:** Epic 40 - Intelligence Service Modularization and Architecture Hardening

---

## Story

As a backend developer,
I want category trends and market opportunities extracted into separate modules with a shared lower-level seam,
so that market-signal composition stops depending on another public service entrypoint.

---

## Problem Statement

`get_market_opportunities()` currently composes one intelligence surface by calling another public intelligence service entrypoint. That works functionally, but it creates the wrong architectural dependency: one public use case is coupled to another public use case instead of both depending on a shared lower-level loader or pure builder.

This is the right story to fix that dependency while extracting the category and signal composition modules out of the monolith.

## Solution

Extract category trends and market opportunities into dedicated modules and replace the current public-service dependency with an explicit shared seam.

The refactor should preserve current business behavior:

- category trend ordering and support semantics
- concentration-risk and category-growth signal logic
- deterministic opportunity sorting
- current route and MCP contracts

## Acceptance Criteria

1. Given Story 40.1 is complete, when Story 40.4 lands, then `get_category_trends()` and `get_market_opportunities()` are implemented outside `backend/domains/intelligence/service.py` and are re-exported through it.
2. Given market opportunities currently reuse category-trend behavior, when Story 40.4 is complete, then they share a lower-level loader or pure builder instead of calling the public `get_category_trends()` entrypoint.
3. Given the focused intelligence suite runs, when the story is complete, then category ranking, support floors, signal composition, and deterministic signal ordering remain unchanged.
4. Given routes and MCP tools remain mounted through the facade, when focused route and MCP tests run, then the public contract remains unchanged.

## Tasks / Subtasks

- [x] Task 1: Extract category-trend logic into a dedicated module. (AC: 1, 3, 4)
  - [x] Move `get_category_trends()` into `services/category_trends.py`.
  - [x] Keep current period-window semantics and support floors stable.
- [x] Task 2: Extract market-opportunity logic into a dedicated module. (AC: 1-4)
  - [x] Move `get_market_opportunities()` into `services/market_opportunities.py`.
  - [x] Replace the current dependency on the public `get_category_trends()` entrypoint with a shared lower-level seam.
  - [x] Preserve deterministic signal sorting and deferred signal type behavior.
- [x] Task 3: Re-export through the facade and validate the mounted app surface. (AC: 1, 4)
  - [x] Keep `routes.py` and `mcp.py` importing through `service.py`.
  - [x] Re-run focused service, route, MCP, and reporting-semantics tests.

## Dev Notes

### Architecture Compliance

- The important architectural correction in this story is dependency direction, not a public-contract rewrite.
- A shared lower-level seam may be a pure builder or loader, but it should not become a second public monolith.
- Avoid dragging aggregate-backed logic into this story.

### Suggested File Targets

- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/services/category_trends.py`
- `backend/domains/intelligence/services/market_opportunities.py`
- `backend/tests/domains/intelligence/test_service.py`
- `backend/tests/domains/intelligence/test_reporting_semantics.py`
- `backend/tests/domains/intelligence/test_routes.py`
- `backend/tests/test_mcp_intelligence.py`

### Validation Commands

- `cd /Users/changtom/Downloads/UltrERP/backend && uv run pytest tests/domains/intelligence/test_service.py tests/domains/intelligence/test_reporting_semantics.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/test_mcp_auth.py -q`

## References

- `../planning-artifacts/epic-40.md`
- `backend/domains/intelligence/service.py`
- `backend/tests/domains/intelligence/test_service.py`
- `backend/tests/domains/intelligence/test_reporting_semantics.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-25: Drafted Story 40.4 to remove the current public-service dependency between category trends and market opportunities while extracting both modules.
- 2026-04-25: Implemented Story 40.4 - created category_trends.py and market_opportunities.py modules. Refactored to use shared lower-level seam instead of calling public entrypoint. All 94 tests pass.

### File List

- `_bmad-output/implementation-artifacts/40-4-category-trends-and-market-opportunities-decoupling.md`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/services/category_trends.py`
- `backend/domains/intelligence/services/market_opportunities.py`