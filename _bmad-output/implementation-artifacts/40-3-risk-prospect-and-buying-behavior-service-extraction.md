# Story 40.3: Risk, Prospect, and Buying Behavior Service Extraction

**Status:** review

**Story ID:** 40.3

**Epic:** Epic 40 - Intelligence Service Modularization and Architecture Hardening

---

## Story

As a backend developer,
I want the customer-risk, prospect-gap, and segment buying-behavior logic extracted into dedicated modules,
so that customer-cohort analytics can evolve without reopening the entire intelligence monolith.

---

## Problem Statement

The customer-cohort slice currently mixes several related but distinct use cases in the monolith:

- customer risk signals
- prospect-gap ranking
- segment buying behavior and cross-sell patterns

These features share some concepts such as excluded-category handling and tenant-scoped order activity, but they still deserve separate implementation ownership. Keeping them in the monolith makes every change to customer-cohort analytics look larger and riskier than it is.

## Solution

Extract the cohort-oriented intelligence use cases into dedicated modules and re-export them through the existing facade.

This story should preserve the current shipped semantics from the Epic 19 and Epic 20 intelligence work:

- `customer_type` filtering semantics
- excluded-category handling
- deterministic ordering
- cross-sell support thresholds and null-lift behavior
- current-period versus prior-period window semantics

## Acceptance Criteria

1. Given Story 40.1 is complete, when Story 40.3 lands, then `get_customer_risk_signals()`, `get_prospect_gaps()`, and `get_customer_buying_behavior()` live in dedicated modules outside `backend/domains/intelligence/service.py` and are re-exported through it.
2. Given the shipped customer-cohort contracts already exist, when the extraction is complete, then `customer_type` handling, excluded-category filtering, cross-sell thresholds, null-lift behavior, and deterministic ordering remain unchanged.
3. Given feature-specific helpers or dataclasses exist for this slice, when the new modules are reviewed, then those internals no longer live in the facade file.
4. Given routes and MCP tools remain mounted through the facade, when focused route and MCP tests run, then the public contract remains unchanged.
5. Given the focused service tests run, when Story 40.3 is complete, then risk classification, prospect ranking, and buying-pattern output remain behaviorally identical.

## Tasks / Subtasks

- [x] Task 1: Extract customer-risk logic into a dedicated module. (AC: 1-5)
  - [x] Move `get_customer_risk_signals()` and its feature-specific support into `services/risk_signals.py`.
  - [x] Preserve current status classification and signal-string behavior.
- [x] Task 2: Extract prospect-gap logic into a dedicated module. (AC: 1-5)
  - [x] Move `get_prospect_gaps()` into `services/prospect_gaps.py`.
  - [x] Preserve target-category revenue, candidate filtering, and ranking semantics.
- [x] Task 3: Extract buying-behavior logic into a dedicated module. (AC: 1-5)
  - [x] Move `get_customer_buying_behavior()` and its cohort-specific support into `services/buying_behavior.py`.
  - [x] Keep `customer_type` semantics and cross-sell thresholds exactly as shipped.
- [x] Task 4: Re-export through the facade and re-run the focused suite. (AC: 1, 4)
  - [x] Keep `routes.py` and `mcp.py` stable.
  - [x] Re-run focused service, route, and MCP tests for the customer-cohort slice.

## Dev Notes

### Architecture Compliance

- Keep feature-specific helpers local unless they are genuinely shared across multiple extracted modules.
- Reuse the Story 40.1 shared support layer for common period, Decimal, and category-filter behavior.
- Do not change business thresholds or user-facing payload shape in this story.

### Suggested File Targets

- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/services/risk_signals.py`
- `backend/domains/intelligence/services/prospect_gaps.py`
- `backend/domains/intelligence/services/buying_behavior.py`
- `backend/tests/domains/intelligence/test_service.py`
- `backend/tests/domains/intelligence/test_customer_buying_behavior_service.py`
- `backend/tests/domains/intelligence/test_routes.py`
- `backend/tests/test_mcp_intelligence.py`

### Validation Commands

- `cd /Users/changtom/Downloads/UltrERP/backend && uv run pytest tests/domains/intelligence/test_service.py tests/domains/intelligence/test_customer_buying_behavior_service.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/test_mcp_auth.py -q`

## References

- `../planning-artifacts/epic-40.md`
- `backend/domains/intelligence/service.py`
- `backend/tests/domains/intelligence/test_service.py`
- `backend/tests/domains/intelligence/test_customer_buying_behavior_service.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-25: Drafted Story 40.3 to isolate the customer-cohort intelligence slice after the low-coupling extraction path is proven.
- 2026-04-25: Implemented Story 40.3 - created risk_signals.py, prospect_gaps.py, and buying_behavior.py modules. Moved get_customer_risk_signals, get_prospect_gaps, and get_customer_buying_behavior to dedicated modules. All 96 tests pass.

### File List

- `_bmad-output/implementation-artifacts/40-3-risk-prospect-and-buying-behavior-service-extraction.md`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/services/risk_signals.py`
- `backend/domains/intelligence/services/prospect_gaps.py`
- `backend/domains/intelligence/services/buying_behavior.py`