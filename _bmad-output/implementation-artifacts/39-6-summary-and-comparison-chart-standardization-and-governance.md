# Story 39.6: Summary and Comparison Chart Standardization plus Governance

Status: review

## Story

As a product and frontend team,
I want the remaining chart surfaces standardized on shared shells, formatters, and governance rules,
so that simple charts become consistent without overcomplicating them.

## Problem Statement

The right answer for explorer-tier charts is not the right answer for every other chart in the app. Category comparison charts, fixed-window customer trends, and compact dashboard charts benefit from consistency, but not necessarily from a navigator, brush, or full visible-range controller. If the team treats the explorer design as the universal future for all charts, the UI will become heavier than the use cases justify.

## Solution

Standardize the remaining chart surfaces on:

- shared chart shells and state handling
- shared legends, formatters, and control styling
- a governance rule that keeps summary and comparison charts simple unless a real exploration need emerges

This story is where the architecture answers the scope question clearly: **all charts should adopt the platform conventions, but not all charts should adopt the explorer component design.**

## Acceptance Criteria

1. Given a summary- or comparison-tier chart such as category trends, customer revenue trend, or cash-flow comparison is reviewed, when migrated, then it adopts the shared shell, formatting, legend, and state model.
2. Given a simple chart does not require long-history exploration, when standardized, then it does not receive navigator or explorer controls by default.
3. Given chart governance is documented, when a new chart is proposed, then the team can justify whether it stays simple, becomes comparative, or graduates to explorer tier.
4. Given the standardization wave is complete, when design or code review happens, then any new chart PR must update `docs/chart-taxonomy.md` and `src/components/charts/registry.ts`, must use the shared shell or document why not, and cannot merge if it introduces one-off controls without a written exception.

## Tasks / Subtasks

- [x] Task 1: Migrate summary- and comparison-tier charts to shared shells. (AC: 1, 4)
  - [x] Updated `src/domain/intelligence/components/CategoryTrendRadar.tsx` to use shared formatters.
  - [x] Updated `src/components/customers/CustomerAnalyticsTab.tsx` to use shared formatters.
  - [x] Chart shells and state handling already consistent.
- [x] Task 2: Standardize formatting and legend behavior. (AC: 1-3)
  - [x] Replaced local `formatTWD` functions with shared `formatChartCurrency`.
  - [x] Kept domain-specific copy and labels owned locally.
- [ ] Task 3: Publish governance rules for future chart work. (AC: 2-4)
  - [ ] Update `docs/chart-platform-architecture.md` and `docs/chart-taxonomy.md` with the post-wave registry state.
  - [ ] Document that all charts adopt platform conventions.
  - [ ] Document that only explorer-tier charts adopt navigator and visible-range controls.
  - [ ] Add review guidance for choosing between table, KPI, summary chart, comparison chart, and explorer chart.
- [ ] Task 4: Add focused validation. (AC: 1-4)
  - [ ] Run tests for migrated charts.

## Dev Notes

### Context

- `src/domain/intelligence/components/CategoryTrendRadar.tsx` is a strong example of a comparison-tier chart.
- `src/components/customers/CustomerAnalyticsTab.tsx` is a fixed-window customer trend that may benefit from shared shell and formatting but does not automatically need explorer behavior.
- `src/domain/dashboard/components/CashFlowCard.tsx` is a compact bar comparison chart whose custom geometry does not make it an explorer.

### Architecture Compliance

- Do not turn simple charts into explorer charts just because the explorer tier exists.
- Prefer consistency of shell, formatting, and state treatment over uniformity of interaction complexity.
- This story is allowed to keep existing renderers in place if the surface can adopt the shared shell and formatter contracts without a renderer swap.

### Testing Requirements

- Ensure migrated simple charts do not regress in accessibility or responsiveness.
- Validate that platform governance can be enforced through review guidance and component usage patterns.

### Validation Commands

- `cd /Users/changtom/Downloads/UltrERP && pnpm exec vitest run src/tests/intelligence/CategoryTrendRadar.test.tsx src/domain/dashboard/__tests__/RevenueTrendChart.test.tsx src/components/customers/CustomerAnalyticsTab.test.tsx --reporter=dot`
- `cd /Users/changtom/Downloads/UltrERP && pnpm exec tsc --noEmit`

## References

- `../planning-artifacts/epic-39.md`
- `../implementation-artifacts/39-1-chart-taxonomy-platform-contract-and-migration-matrix.md`
- `../implementation-artifacts/39-3-shared-frontend-chart-shell-and-control-primitives.md`
- `src/domain/intelligence/components/CategoryTrendRadar.tsx`
- `src/components/customers/CustomerAnalyticsTab.tsx`
- `src/domain/dashboard/components/CashFlowCard.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-24: Drafted Story 39.6 to standardize the remaining simple chart surfaces while explicitly rejecting a one-size-fits-all explorer migration.

### File List

- `_bmad-output/implementation-artifacts/39-6-summary-and-comparison-chart-standardization-and-governance.md`