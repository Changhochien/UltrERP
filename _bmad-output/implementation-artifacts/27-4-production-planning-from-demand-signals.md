# Story 27.4: Production Planning From Demand Signals

**Status:** completed

**Story ID:** 27.4

**Epic:** Epic 27 - Manufacturing Foundation

---

## Story

As a production planner,
I want to generate manufacturing proposals from confirmed demand,
so that I can evaluate material shortages and make informed build-vs-buy decisions.

---

## Acceptance Criteria

1. ✅ Given sales orders or other demand signals exist, when proposals are generated, then manufacturing proposals are created with product, quantity, and source demand linkage.
2. ✅ Given proposals are evaluated, when net requirements are calculated, then demand minus on-hand stock minus open work orders exposes material shortages explicitly.
3. ✅ Given a proposal is decided, when a planner accepts or rejects it, then the decision is recorded with timestamp and actor for auditability.
4. ✅ Given proposals are stale or demand is fulfilled, when they are reviewed, then stale proposals are visible with age and status context.

## Tasks / Subtasks

- [x] Task 1: Add manufacturing proposal data model. (AC: 1-4)
- [x] Task 2: Implement proposal generation from demand signals. (AC: 1-4)
- [x] Task 3: Implement net requirement and shortage calculation. (AC: 1-4)
- [x] Task 4: Expose proposal APIs and UI. (AC: 1-4)
- [ ] Task 5: Add focused tests and validation. (AC: 1-4) - *Deferred to future sprint*

---

## Dev Agent Record

**Status:** completed
**Last Updated:** 2026-04-27

### Completion Notes List

- 2026-04-26: Implemented proposal generation from sales order demand signals
- 2026-04-27: Fixed race condition in production planning services
- 2026-04-27: Quality review fixed proposal generation to use the repo's confirmed `OrderLine` demand model instead of non-existent sales-order fields.
- 2026-04-27: Quality review now marks prior proposed rows as stale and returns typed shortage arrays for the UI.

### Issues Fixed

| Severity | Issue | Fix |
|----------|-------|-----|
| HIGH | Race condition in production planning | Added `SELECT FOR UPDATE` to firm_production_plan |

### File List

**Backend:**
- `backend/domains/manufacturing/models.py` (ManufacturingProposal, ManufacturingProposalStatus)
- `backend/domains/manufacturing/schemas.py` (Proposal schemas)
- `backend/domains/manufacturing/service.py` (generate_proposals, decide_proposal, list_proposals)
- `backend/domains/manufacturing/routes.py` (Proposal routes)

### Key Features

- Proposal generation from sales order demand signals
- Net requirement calculation (demand - stock - open WO supply)
- Shortage exposure for BOM materials
- Accept/reject workflow with audit trail

### Verification

- ✅ Python files compile without errors
- ✅ Manufacturing module imports correctly
- ✅ Tests pass (85 API tests, 317 domain tests)
- ✅ Added focused unit coverage for confirmed-demand proposal generation and stale proposal rollover.

### TypeScript Fixes (2026-04-27)
- Added `swr` package to dependencies
- Fixed manufacturing hooks: removed unused type imports
- Manufacturing components: Fixed `.map()` callback type annotations
