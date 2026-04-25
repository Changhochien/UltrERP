# Story 39.3: Shared Frontend Chart Shell and Control Primitives

Status: done

## Story

As a frontend developer,
I want reusable chart shells and controls,
so that charts across dashboard, intelligence, and inventory share one interaction language for states and simple filtering.

## Problem Statement

Current chart surfaces repeat the same concerns in slightly different ways: section shell, loading skeleton, error block, empty state, legends, period buttons, and chart-mode toggles. Even where the visual structure is similar, the code is fragmented across domains. That duplication slows down chart work and makes the UI feel inconsistent.

## Solution

Create a shared frontend chart platform under `src/components/charts/` with primitives for:

- chart shell and section composition
- loading, error, and empty states
- legends and tooltip scaffolding
- preset groups and chart-mode toggles
- formatting helpers for money, quantity, dates, and units

The v1 file layout is explicit:

```text
src/components/charts/
  types.ts
  formatters.ts
  ChartShell.tsx
  ChartStateView.tsx
  ChartLegend.tsx
  controls/
    RangePresetGroup.tsx
    ChartModeToggle.tsx
  explorer/
    useExplorerRange.ts
    OverviewNavigator.tsx
    ExplorerChartFrame.tsx
  index.ts
```

This story standardizes shared primitives for all chart tiers, but it must not force explorer-only controls onto simple charts.

## Acceptance Criteria

1. Given a chart needs loading, error, empty, legend, tooltip, and preset controls, when it adopts the shared platform, then it can compose `ChartShell`, `ChartStateView`, `ChartLegend`, `RangePresetGroup`, and `ChartModeToggle` rather than custom in-component markup.
2. Given chart controls are rendered, when users interact with them, then they follow one accessible pattern for labels, `aria-pressed`, focus, and disabled states.
3. Given summary- or comparison-tier charts migrate, when reviewed, then they share shell and formatting behavior without inheriting explorer-only controls and without replacing existing `Card` or `SectionCard` wrappers unless the story explicitly says so.
4. Given shared formatters are introduced, when monetary, quantity, or date values are rendered in tooltips and axes, then callers pass `i18n.resolvedLanguage` or `i18n.language` into pure formatter helpers in `src/components/charts/formatters.ts` instead of hard-coding locales.

## Tasks / Subtasks

- [x] Task 1: Create shared chart shell primitives. (AC: 1-3)
  - [x] Add `ChartShell.tsx` and `ChartStateView.tsx` for chart card or section framing, loading, error, and empty states.
  - [x] Support both `Card` and `SectionCard` hosting patterns used in the current app.
  - [x] Keep shell components neutral enough for dashboard, inventory, and customer surfaces.
- [x] Task 2: Create shared control primitives. (AC: 1-3)
  - [x] Add `controls/RangePresetGroup.tsx` and `controls/ChartModeToggle.tsx`.
  - [x] Standardize aria labels, button states, and focus semantics.
  - [x] Avoid embedding explorer-specific logic in simple period selectors.
- [x] Task 3: Create shared legend, tooltip, and formatting utilities. (AC: 1, 4)
  - [x] Add `ChartLegend.tsx` and shared tooltip presentation primitives where renderer-independent reuse is practical.
  - [x] Add `formatters.ts` with pure helpers such as `formatChartCurrency`, `formatChartQuantity`, and `formatChartDate`.
  - [x] Keep domain-specific text translation responsibility at the caller boundary.
- [x] Task 4: Add focused tests. (AC: 1-4)
  - [x] Add `src/components/charts/__tests__/formatters.test.ts` with locale-sensitive output tests.

## Dev Notes

### Context

- `src/domain/intelligence/components/CategoryTrendRadar.tsx`, `src/domain/dashboard/components/RevenueTrendChart.tsx`, and `src/domain/inventory/components/AnalyticsTab.tsx` already share enough surface-level structure to justify a common shell.
- Some charts live in `Card` surfaces while others live in `SectionCard`; the shared layer must work with both.

### Expected Public APIs

```ts
// src/components/charts/ChartShell.tsx
interface ChartShellProps {
  title?: ReactNode;
  description?: ReactNode;
  controls?: ReactNode;
  children: ReactNode;
}

// src/components/charts/ChartStateView.tsx
interface ChartStateViewProps {
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyMessage?: ReactNode;
  onRetry?: () => void;
  children: ReactNode;
}

// src/components/charts/formatters.ts
export function formatChartCurrency(value: number, locale: string, currency?: string): string;
export function formatChartQuantity(value: number, locale: string, maximumFractionDigits?: number): string;
export function formatChartDate(value: string, locale: string, options?: Intl.DateTimeFormatOptions): string;
```

### Architecture Compliance

- Build shared platform primitives, not a monolithic chart super-component.
- Keep renderer-specific geometry inside domain or engine-specific components.
- Keep translation ownership local to feature components.
- Formatters are pure helpers and do not call `useTranslation()` directly.

### Testing Requirements

- Test keyboard and screen-reader semantics of control groups.
- Test that simple charts can adopt the shell without explorer affordances appearing unexpectedly.

### Validation Commands

- `cd /Users/changtom/Downloads/UltrERP && pnpm exec vitest run src/components/charts/**/*.test.ts* src/domain/inventory/components/AnalyticsTab.test.tsx src/domain/dashboard/__tests__/RevenueTrendChart.test.tsx --reporter=dot`
- `cd /Users/changtom/Downloads/UltrERP && pnpm exec tsc --noEmit`

## References

- `../planning-artifacts/epic-39.md`
- `src/domain/dashboard/components/RevenueTrendChart.tsx`
- `src/domain/intelligence/components/CategoryTrendRadar.tsx`
- `src/domain/inventory/components/AnalyticsTab.tsx`
- `src/components/layout/PageLayout.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-24: Drafted Story 39.3 to standardize chart shells and controls across domains without collapsing all charts into one renderer-specific abstraction.
- 2026-04-25: Review pass hardened shared currency formatting options, fixed ISO currency usage in migrated charts, and validated chart platform formatter tests.

### File List

- `_bmad-output/implementation-artifacts/39-3-shared-frontend-chart-shell-and-control-primitives.md`
- `src/components/charts/formatters.ts`
- `src/components/charts/ChartShell.tsx`
- `src/components/charts/ChartStateView.tsx`
- `src/components/charts/ChartLegend.tsx`
- `src/components/charts/controls/RangePresetGroup.tsx`
- `src/components/charts/controls/ChartModeToggle.tsx`
- `src/components/charts/__tests__/formatters.test.ts`