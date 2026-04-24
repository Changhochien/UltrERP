# Story 39.1: Chart Taxonomy, Platform Contract, and Migration Matrix

Status: review

## Story

As a frontend and architecture team,
I want every chart surface classified into a stable chart tier with a documented platform contract,
so that new work follows one architecture instead of producing more one-off chart implementations.

## Problem Statement

UltrERP currently mixes `recharts` and `@visx` across dashboard, inventory, customer, and intelligence surfaces. That is not inherently wrong, but the renderer split has also produced inconsistent interaction patterns, duplicated tooltip and empty-state logic, and no shared rule for deciding whether a chart is a simple summary or a long-history explorer. Without a platform contract, each new chart story risks reopening the same architecture decision and extending drift.

## Solution

Create the chart platform foundation before broad migration:

- inventory the current chart surfaces
- classify them into `summary`, `comparison`, or `explorer` tier
- define the shared chart platform contract for state handling, series metadata, and renderer choice
- publish a migration matrix that makes future adoption deterministic

This story produces concrete deliverables in both docs and code:

- `docs/chart-platform-architecture.md` for the contract and decision rules
- `docs/chart-taxonomy.md` for the inventory and migration matrix
- `src/components/charts/types.ts` for platform-wide TypeScript contracts
- `src/components/charts/registry.ts` for a typed chart-surface registry used in review and migration planning

This story is the decision and governance layer, not the rendering implementation itself.

## Acceptance Criteria

1. Given the current chart surfaces in the app, when the architecture inventory is completed, then each surface is assigned to `summary`, `comparison`, or `explorer` tier with a documented rationale.
2. Given the shared platform contract is defined, when a chart adopts it, then the contract exists in `src/components/charts/types.ts` and gives one common vocabulary for `loading`, `error`, `empty`, series metadata, units, optional range behavior, and renderer tier.
3. Given the mixed renderer stack, when a new chart is proposed, then a documented decision matrix exists in `docs/chart-platform-architecture.md` and `src/components/charts/registry.ts` and explains whether it should remain `recharts`, use `@visx`, or intentionally defer a future adapter.
4. Given this story is completed, when the migration plan is reviewed in `docs/chart-taxonomy.md`, then first-wave, second-wave, deferred, and non-chart holdout surfaces are clearly separated.

## Tasks / Subtasks

- [x] Task 1: Inventory current chart surfaces. (AC: 1, 4)
  - [x] Review dashboard, inventory, intelligence, and customer chart surfaces.
  - [x] Record renderer, interaction model, data density, and business purpose for each surface.
  - [x] Publish the inventory in `docs/chart-taxonomy.md` as a version-controlled table.
  - [x] Mark which surfaces are tables or KPI cards and should not be force-migrated into charts.
- [x] Task 2: Define chart tiers and contract vocabulary. (AC: 1-3)
  - [x] Define `summary`, `comparison`, and `explorer` tier semantics.
  - [x] Define `ChartTier`, `ChartRenderer`, `ChartSeriesPoint`, `ChartRangeMetadata`, and `ChartSurfaceRegistration` in `src/components/charts/types.ts`.
  - [x] Define the shared backend vocabulary for bucket, timezone, requested range, available range, and visible range in `docs/chart-platform-architecture.md`.
- [x] Task 3: Publish renderer and adoption decision matrix. (AC: 2-4)
  - [x] Document when `recharts` is acceptable by default.
  - [x] Document when `@visx` is required because of overlays, custom geometry, or explorer interactions.
  - [x] Document that a future Lightweight Charts adapter is optional and not a prerequisite for this epic.
  - [x] Create `src/components/charts/registry.ts` with a typed registry of existing chart surfaces.
- [x] Task 4: Produce migration matrix and sequencing guidance. (AC: 4)
  - [x] Identify first-wave explorer migrations.
  - [x] Identify second-wave summary/comparison standardization work.
  - [x] Mark any intentional holdouts and explain why they remain unchanged.
  - [x] Add a PR review checklist to `docs/chart-platform-architecture.md` so new chart work must update the taxonomy.

## Dev Notes

### Context

- `src/domain/dashboard/components/RevenueTrendChart.tsx` already shows a partial navigator pattern via `Brush`.
- `src/domain/inventory/components/StockTrendChart.tsx` and `src/domain/inventory/components/MonthlyDemandChart.tsx` already justify custom-chart behavior.
- `src/domain/intelligence/components/CategoryTrendRadar.tsx` and `src/components/customers/CustomerAnalyticsTab.tsx` are simpler chart surfaces and should not automatically inherit explorer behavior.

### Expected Contract Shape

```ts
// src/components/charts/types.ts
export type ChartTier = "summary" | "comparison" | "explorer";
export type ChartRenderer = "recharts" | "visx";

export interface ChartSeriesPoint {
  x: string;
  y: number;
  label?: string;
  periodStatus?: "closed" | "partial";
  source?: "aggregate" | "live" | "zero-filled";
}

export interface ChartRangeMetadata {
  requestedStart: string;
  requestedEnd: string;
  availableStart: string | null;
  availableEnd: string | null;
  defaultVisibleStart: string;
  defaultVisibleEnd: string;
  bucket: "day" | "week" | "month";
  timezone: string;
}

export interface ChartSurfaceRegistration {
  id: string;
  componentPath: string;
  tier: ChartTier;
  renderer: ChartRenderer;
  owner: "dashboard" | "inventory" | "intelligence" | "customers";
  notes: string;
}
```

### Architecture Compliance

- Standardize the architecture, not a single universal component.
- Keep domain data ownership local to each domain hook or API helper.
- Put only reusable chart primitives and contracts into the shared chart platform.

### Testing Requirements

- This story is primarily architecture and documentation work.
- Validate that the migration matrix references only existing files and chart surfaces.

### Validation Commands

- `cd /Users/changtom/Downloads/UltrERP && pnpm exec tsc --noEmit`
- `cd /Users/changtom/Downloads/UltrERP && pnpm exec vitest run src/components/charts/**/*.test.ts* --reporter=dot`
- Manual review: `docs/chart-taxonomy.md` references only real chart components in `src/domain/**` or `src/components/**`.

## References

- `../planning-artifacts/epic-39.md`
- `package.json`
- `src/domain/dashboard/components/RevenueTrendChart.tsx`
- `src/domain/dashboard/components/CashFlowCard.tsx`
- `src/domain/intelligence/components/CategoryTrendRadar.tsx`
- `src/components/customers/CustomerAnalyticsTab.tsx`
- `src/domain/inventory/components/StockTrendChart.tsx`
- `src/domain/inventory/components/MonthlyDemandChart.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-24: Drafted Story 39.1 to establish the chart taxonomy, shared platform vocabulary, and migration matrix before broader chart refactoring.

### File List

- `_bmad-output/implementation-artifacts/39-1-chart-taxonomy-platform-contract-and-migration-matrix.md`
- `docs/chart-platform-architecture.md` (new)
- `docs/chart-taxonomy.md` (new)
- `src/components/charts/types.ts` (new)
- `src/components/charts/registry.ts` (new)
- `src/components/charts/index.ts` (new)