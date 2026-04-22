# Story 17.15: AR/AP Aging Donut Charts

**Status:** ready-for-dev

## Story

As an owner,
I want to see AR/AP aging as proportional donut charts,
so that I can immediately see the relative size of each aging bucket and spot concentration risk at a glance.

## Business Context

`ARAgingCard` and `APAgingCard` currently render a 4-column CSS grid of buckets (0-30, 31-60, 61-90, 90+ days) with colored dots. This hides magnitude — a NT$100 bucket and a NT$10M bucket look identical spatially. The donut chart shows proportion *and* absolute size simultaneously via arc length and a center KPI label.

## Reference

ERPNext `Dashboard Chart` doctype: `type: "Donut"`, `chart_type: "Report"`, `use_report_chart: 1`. The `Accounts Receivable Ageing` chart uses a donut with the four buckets as pie slices and total outstanding in the center.

## Wire Data Already Available

The backend and hooks are already wired:
- `fetchARAging()` → `GET /api/v1/reports/ar-aging` → `ARAgingResponse` with `buckets: ARAgingBucket[]`
- `fetchAPAging()` → `GET /api/v1/reports/ap-aging` → `APAgingResponse` with `buckets: APAgingBucket[]`
- Both cards already rendered in `OwnerDashboardPage` — just the visual needs upgrading

## Acceptance Criteria

**AC1 — Donut chart renders instead of bucket grid**
- Replace the 4-column bucket grid with a `Recharts PieChart` using `innerRadius` to create a donut
- Four slices correspond to the four `bucket_label` values
- Slice colors use `--chart-*` CSS tokens (see CSS color mapping below)

**AC2 — Center KPI shows total outstanding**
- `innerRadius` / `outerRadius` approach: calculate center position, render total outstanding amount in TWD as a centered label over the donut hole
- Use the same `formatTWD()` pattern already used in the cards

**AC3 — Legend is color-matched to bucket grid**
- Show a compact legend below or beside the chart matching the existing color semantics
- Color mapping (preserve existing semantics):
  - 0-30 days → `--chart-2` (green, oklch(0.664 0.147 155.2)) — healthy
  - 31-60 days → `--chart-3` (amber, oklch(0.768 0.157 78.5)) — attention
  - 61-90 days → `--chart-9` (orange, oklch(0.692 0.142 44.7)) — warning
  - 90+ days → destructive red — use `var(--destructive)` (oklch(0.577 0.245 27.325))

**AC4 — Tooltip shows bucket details**
- Hover/tap a slice → tooltip showing bucket label, amount (formatted TWD), and invoice count
- Use Recharts `Tooltip` with custom formatter

**AC5 — Both AR and AP cards updated identically**
- Apply the same donut pattern to `ARAgingCard` and `APAgingCard`
- Extract a shared `AgingDonutChart` sub-component if the pattern is identical

**AC6 — Responsive**
- Chart shrinks gracefully on mobile; min innerRadius enforced to keep center legible

**AC7 — Loading, error, and empty states preserved**
- Reuse existing Skeleton, error, and null guard patterns from the current cards

## Tasks

- [ ] Create `AgingDonutChart.tsx` sub-component using Recharts `PieChart` + `Pie` + `Cell` + `Tooltip`
  - Accept `buckets: ARAgingBucket[]` or `APAgingBucket[]` (union type)
  - Accept `totalOutstanding: string`, `isLoading`, `error` props
  - Colors mapped to `--chart-*` CSS vars via `getComputedStyle(document.documentElement).getPropertyValue('--chart-N').trim()`
  - Center label: total outstanding in TWD
  - Tooltip with bucket detail
- [ ] Replace bucket grid in `ARAgingCard` with `<AgingDonutChart>`
- [ ] Replace bucket grid in `APAgingCard` with `<AgingDonutChart>`
- [ ] Extract shared `BUCKET_COLORS` constant so both cards use identical mapping
- [ ] Verify responsive behavior on mobile viewport (min 320px)
- [ ] Add donut chart snapshots to existing test files or create `AgingDonutChart.test.tsx`

## CSS Token Color Reference

```css
--chart-1: oklch(0.646 0.189 237.6);   /* blue  */
--chart-2: oklch(0.664 0.147 155.2);   /* green */
--chart-3: oklch(0.768 0.157 78.5);    /* amber */
--chart-4: oklch(0.627 0.194 299.4);   /* purple */
--chart-5: oklch(0.627 0.194 194.8);   /* teal */
--chart-6: oklch(0.704 0.191 22.216);   /* orange */
--chart-7: oklch(0.585 0.204 262.3);   /* violet */
--chart-8: oklch(0.712 0.171 340.1);   /* pink */
--chart-9: oklch(0.692 0.142 44.7);    /* orange-amber */
--chart-10: oklch(0.618 0.104 239.4);   /* indigo */
--destructive: oklch(0.577 0.245 27.325);/* red */
```

## File Structure

```
src/domain/dashboard/components/
  ARAgingCard.tsx        — replace grid with AgingDonutChart
  APAgingCard.tsx        — replace grid with AgingDonutChart
  AgingDonutChart.tsx    — NEW shared sub-component
```

## Recharts Import

Already in `package.json` as `recharts`. Use:
```typescript
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
```

## Dev Notes

- The existing `BUCKET_LABELS` and `BUCKET_COLORS` constants in both cards should be extracted to a shared `constants.ts` file in the dashboard components directory
- Recharts `Cell` component takes `fill` as a prop — pass CSS variable values directly
- For responsive center label, use `ResponsiveContainer` + absolutely positioned div over the donut hole, OR render via Recharts `customized` layer
- Both `ARAgingCard` and `APAgingCard` share identical structure — the shared component should accept a generic `buckets` prop

## Project References

- Types: `src/domain/dashboard/types.ts` — `ARAgingBucket`, `ARAgingResponse`, `APAgingBucket`, `APAgingResponse`
- API: `src/lib/api/dashboard.ts` — `fetchARAging`, `fetchAPAging`
- Hooks: `src/domain/dashboard/hooks/useDashboard.ts` — `useARAging`, `useAPAging`
- OwnerDashboardPage: `src/domain/owner-dashboard/OwnerDashboardPage.tsx` — already renders both cards
