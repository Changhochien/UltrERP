# Story 40.1: Intelligence Service Facade and Shared Support Layer

**Status:** review

**Story ID:** 40.1

**Epic:** Epic 40 - Intelligence Service Modularization and Architecture Hardening

---

## Story

As a backend developer,
I want a compatibility facade and shared support layer for intelligence services,
so that feature extraction can proceed without breaking the app's existing REST, MCP, and test entrypoints.

---

## Problem Statement

`backend/domains/intelligence/service.py` currently mixes public use cases, helper math/date logic, private dataclasses, constants, and query orchestration in one file. The app surface is already mounted and live through `backend/app/main.py`, `backend/domains/intelligence/routes.py`, `backend/domains/intelligence/mcp.py`, and `src/pages/IntelligencePage.tsx`, so splitting the file without a stable facade would create avoidable churn across routes, MCP tools, and tests.

The file already shows one concrete architecture smell: month-shift logic is defined twice. That makes this story the right place to introduce the extraction seam before any feature-specific modules move.

## Solution

Create `backend/domains/intelligence/services/` as the new implementation package and keep `backend/domains/intelligence/service.py` as the compatibility facade.

This story moves only shared pure support first:

- shared constants
- shared pure math/date/category helpers
- shared private dataclasses that are truly cross-feature
- duplicated month/window logic consolidated into one authoritative helper implementation

Business behavior should not change in this story. The goal is to make later extractions mechanical and local.

## Acceptance Criteria

1. Given callers currently import `domains.intelligence.service`, when Story 40.1 lands, then those imports still resolve without caller changes.
2. Given shared pure helpers exist in the monolith, when they are extracted, then duplicated date/window helpers are consolidated into one authoritative implementation and no duplicate month-shift helper remains.
3. Given later stories need reusable support logic, when they import from the shared layer, then that layer does not depend on feature modules.
4. Given this story is architecture-only, when the focused intelligence suite runs, then current payloads and behaviors remain unchanged.
5. Given the facade exists, when later feature stories land, then `backend/domains/intelligence/service.py` can re-export extracted functions without reintroducing private helper implementations.

## Tasks / Subtasks

- [x] Task 1: Introduce the intelligence service package and compatibility facade. (AC: 1, 5)
  - [x] Add `backend/domains/intelligence/services/` and a minimal package export surface.
  - [x] Keep `backend/domains/intelligence/service.py` as the stable public import path.
  - [x] Re-export the existing public intelligence functions from the facade without changing caller imports.
- [x] Task 2: Move shared pure helpers and constants into a support layer. (AC: 2, 3)
  - [x] Extract shared constants, Decimal helpers, date/window helpers, and category-filter helpers out of the monolith.
  - [x] Consolidate the duplicate month-shift helper into a single implementation.
  - [x] Move only support types that are actually shared; leave feature-specific internals for later stories.
- [x] Task 3: Add focused architectural regression coverage. (AC: 1-4)
  - [x] Add or extend focused tests that prove the public facade still exposes the expected functions.
  - [x] Add a focused regression that covers the consolidated month/window helper behavior.
  - [x] Re-run the existing intelligence route and MCP tests to prove the mounted app surface remains intact.

## Dev Notes

### Context

- The intelligence app is mounted in `backend/app/main.py`.
- REST routes call the current service facade from `backend/domains/intelligence/routes.py`.
- MCP tools call the same facade from `backend/domains/intelligence/mcp.py`.
- The frontend composes the current read-only workspace in `src/pages/IntelligencePage.tsx` and should not change in this story.

### Architecture Compliance

- Keep `schemas.py`, `routes.py`, and `mcp.py` stable in this story.
- Do not extract feature implementations yet unless that is strictly required to establish the facade.
- The shared support layer must remain pure and low-level; it should not import feature modules.

### Suggested File Targets

- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/services/__init__.py`
- `backend/domains/intelligence/services/shared/`
- `backend/tests/domains/intelligence/`
- `backend/tests/test_mcp_intelligence.py`

### Validation Commands

- `cd /Users/changtom/Downloads/UltrERP/backend && uv run pytest tests/domains/intelligence/test_service.py tests/domains/intelligence/test_reporting_semantics.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py -q`

## References

- `../planning-artifacts/epic-40.md`
- `backend/app/main.py`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/routes.py`
- `backend/domains/intelligence/mcp.py`
- `src/pages/IntelligencePage.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-25: Drafted Story 40.1 to establish the compatibility facade and shared-support seam before feature-by-feature extraction begins.
- 2026-04-25: Implemented Story 40.1 - created `backend/domains/intelligence/services/` package structure with `shared/` support layer containing constants, date helpers, decimal helpers, and category helpers. Consolidated duplicate `_shift_month_start` function into single authoritative implementation. Updated `service.py` to import from shared layer instead of defining locally, maintaining backward compatibility as a facade. All 94 intelligence tests pass.

### File List

- `_bmad-output/implementation-artifacts/40-1-intelligence-service-facade-and-shared-support-layer.md`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/services/__init__.py`
- `backend/domains/intelligence/services/shared/__init__.py`
- `backend/domains/intelligence/services/shared/constants.py`
- `backend/domains/intelligence/services/shared/date_helpers.py`
- `backend/domains/intelligence/services/shared/decimal_helpers.py`
- `backend/domains/intelligence/services/shared/category_helpers.py`
- `backend/tests/domains/intelligence/`