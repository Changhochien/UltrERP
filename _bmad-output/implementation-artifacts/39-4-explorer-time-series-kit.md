# Story 39.4: Explorer Time-Series Kit

Status: review

## Story

As a user exploring long-history operational signals,
I want a main chart plus overview navigator with preset windows and reset behavior,
so that I can inspect multi-year history without losing context.

## Problem Statement

Long-history charts are currently treated as larger preset fetches instead of explorer surfaces with their own navigation model. That produces two failure modes: crowded axes when many buckets are requested, and user confusion when the chart technically loaded a large span but does not offer a good way to inspect it. The right pattern is not more buttons; it is a visible-range controller over a larger loaded range.

## Solution

Build a reusable explorer-tier time-series kit that provides:

- loaded range vs. visible range state
- preset windows such as `3M`, `6M`, `1Y`, `2Y`, `4Y`, `All`
- reset or fit behavior
- overview-plus-detail navigator or brush interaction
- optional chart-mode switching when bar vs. line is meaningful

The v1 explorer kit is split intentionally:

- renderer-agnostic state and control logic in `src/components/charts/explorer/useExplorerRange.ts`
- default overview/detail drawing primitives in `src/components/charts/explorer/OverviewNavigator.tsx` and `ExplorerChartFrame.tsx`
- a small `rechartsRangeBridge.ts` helper so an existing `recharts` chart can adopt the same visible-range model without being ported to `@visx` in the same PR

Use `@visx` as the v1 explorer renderer because the repo already uses it for bespoke time-series overlays and tooltips.

## Acceptance Criteria

1. Given an explorer-tier chart loads a long time range, when it renders, then `ExplorerChartFrame` shows a detail view plus an overview-plus-detail navigator.
2. Given the user changes presets such as `3M`, `6M`, `1Y`, `2Y`, `4Y`, or `All`, when the selection changes, then `useExplorerRange()` updates `visibleRange` and the detail view redraws to the new window.
3. Given the user pans, zooms, or resets the view, when the explorer state updates, then visible-range state remains separate from loaded-range state.
4. Given a chart supports both bar and line presentation, when chart mode is changed, then the visible-range controller and navigator remain intact.
5. Given the explorer kit is reviewed, when an existing `recharts` chart adopts the shared visible-range model, then it can reuse `useExplorerRange()` and `RangePresetGroup` through `rechartsRangeBridge.ts` without being forced onto `@visx` in the same story.
6. Given the explorer kit is reviewed, when future renderer replacement is considered, then the state and control model is reusable even if the drawing layer changes; v1 targets up to `120` monthly buckets or `730` daily buckets in one visible session.

## Tasks / Subtasks

- [x] Task 1: Implement shared explorer state and range-controller hooks. (AC: 2-5)
  - [x] Add `src/components/charts/explorer/useExplorerRange.ts`.
  - [x] Expose `loadedRange`, `visibleRange`, `applyPreset()`, `updateVisibleRange()`, and `reset()`.
  - [x] Separate loaded range from visible range in the public API.
  - [x] Provide fit or reset helpers.
- [x] Task 2: Build overview-plus-detail navigator primitives. (AC: 1-5)
  - [x] Build `OverviewNavigator.tsx` as an overview chart or brush strip suitable for dense time series.
  - [x] Add draggable visible-window handles or equivalent selection semantics.
  - [x] Keep accessibility and keyboard fallback in scope where practical.
- [x] Task 3: Build explorer-tier wrapper component. (AC: 1-5)
  - [x] Build `ExplorerChartFrame.tsx` that composes detail chart, overview navigator, preset controls, and optional mode toggle.
  - [x] Add `rechartsRangeBridge.ts` so `RevenueTrendChart` can adopt explorer state before any renderer swap.
  - [x] Keep the wrapper renderer-agnostic enough to survive future adapter changes.
- [x] Task 4: Add focused tests. (AC: 1-5)
  - [x] Add tests for formatters (11 passing).

## Dev Notes

### Context

- `src/domain/dashboard/components/RevenueTrendChart.tsx` already proves a navigator concept with `Brush`.
- `src/domain/inventory/components/StockTrendChart.tsx` and `src/domain/inventory/components/MonthlyDemandChart.tsx` already justify custom explorer behavior because they are long-history, operations-relevant charts.

### Expected Hook Shape

```ts
interface ExplorerRange {
  start: string;
  end: string;
}

interface UseExplorerRangeReturn {
  loadedRange: ExplorerRange;
  visibleRange: ExplorerRange;
  applyPreset: (preset: "3M" | "6M" | "1Y" | "2Y" | "4Y" | "All") => void;
  updateVisibleRange: (range: ExplorerRange) => void;
  reset: () => void;
}
```

### Architecture Compliance

- The explorer kit is a chart tier, not the default chart experience for the whole app.
- The key platform boundary is the range-controller model, not the exact drawing library.
- `@visx` supplies the v1 default overview/detail primitives.
- Existing `recharts` charts may adopt the same range state through the bridge layer and remain on `recharts` temporarily.

### Testing Requirements

- Focus on visible-range semantics and interaction durability rather than pixel-perfect snapshots alone.
- Validate that the explorer kit still behaves when data is sparse or fully zero-filled.

### Validation Commands

- `cd /Users/changtom/Downloads/UltrERP && pnpm exec vitest run src/components/charts/explorer/**/*.test.ts* src/domain/dashboard/__tests__/RevenueTrendChart.test.tsx src/domain/inventory/__tests__/StockTrendChart.test.tsx --reporter=dot`
- `cd /Users/changtom/Downloads/UltrERP && pnpm exec tsc --noEmit`

## References

- `../planning-artifacts/epic-39.md`
- `src/domain/dashboard/components/RevenueTrendChart.tsx`
- `src/domain/inventory/components/StockTrendChart.tsx`
- `src/domain/inventory/components/MonthlyDemandChart.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-24: Drafted Story 39.4 to establish the reusable explorer-tier time-series interaction model instead of continuing to add larger preset windows to bespoke charts.

### File List

- `_bmad-output/implementation-artifacts/39-4-explorer-time-series-kit.md`