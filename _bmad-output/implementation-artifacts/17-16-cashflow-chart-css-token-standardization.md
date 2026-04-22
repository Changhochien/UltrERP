# Story 17.16: CashFlowCard CSS Token Standardization

**Status:** ready-for-dev

## Story

As a developer,
I want `CashFlowCard` to use `--chart-*` CSS tokens for chart colors instead of hardcoded hex strings,
so that the chart palette is consistent with the rest of the dashboard and themeable.

## Business Context

`CashFlowCard` (`src/domain/dashboard/components/CashFlowCard.tsx`) uses `@visx/shape` `Bar` components with hardcoded hex color strings:
- `#22c55e` — inflows (green)
- `#ef4444` — outflows (red)
- `#3b82f6` — net (blue)

These same semantic roles (positive/negative/net) exist across other chart components using `--chart-*` tokens. Using hardcoded hex breaks the design token system and makes theme overrides impossible.

## Reference

- `RevenueTrendChart` already uses `stroke="#6366f1"` (not a CSS token — flagged as a follow-up issue)
- `--chart-2` is `oklch(0.664 0.147 155.2)` — green, suitable for inflows
- `--destructive` is `oklch(0.577 0.245 27.325)` — red, suitable for outflows
- `--chart-1` is `oklch(0.646 0.189 237.6)` — blue, suitable for net

The `--chart-*` tokens are already defined in `src/index.css` lines 57-65 (light) and 120-129 (dark).

## Acceptance Criteria

**AC1 — Inflows color uses CSS token**
- Replace `fill="#22c55e"` on inflow bars with `fill="var(--chart-2)"`
- Verify green semantic is correct for inflows

**AC2 — Outflows color uses CSS token**
- Replace `fill="#ef4444"` on outflow bars with `fill="var(--destructive)"`
- Verify red semantic is correct for outflows

**AC3 — Net color uses CSS token**
- Replace `fill="#3b82f6"` on net bars with `fill="var(--chart-1)"`
- Verify blue semantic is correct for net

**AC4 — Legend swatches use CSS tokens**
- Replace `bg-green-500`, `bg-red-500`, `bg-blue-500` in the legend div with CSS variable backgrounds
- `bg-[var(--chart-2)]`, `bg-[var(--destructive)]`, `bg-[var(--chart-1)]`

**AC5 — Summary row colored values use CSS tokens**
- Replace inline `text-[#22c55e]` and `text-[#ef4444]"` in the summary row with `text-[var(--chart-2)]` and `text-[var(--destructive)]`

**AC6 — Tooltip colors use CSS tokens**
- Replace hardcoded color strings in the tooltip content with CSS variable equivalents

**AC7 — Dark mode still correct**
- `--chart-*` tokens have distinct light/dark values in `:root` and `.dark` blocks in `index.css`
- No visual regression in dark mode

## Tasks

- [ ] Update `src/domain/dashboard/components/CashFlowCard.tsx`:
  - Replace `fill="#22c55e"` → `fill="var(--chart-2)"` on inflow Bar elements
  - Replace `fill="#ef4444"` → `fill="var(--destructive)"` on outflow Bar elements
  - Replace `fill="#3b82f6"` → `fill="var(--chart-1)"` on net Bar element
  - Replace legend `bg-green-500` → `bg-[var(--chart-2)]`
  - Replace legend `bg-red-500` → `bg-[var(--destructive)]`
  - Replace legend `bg-blue-500` → `bg-[var(--chart-1)]`
  - Replace summary `text-[#22c55e]` → `text-[var(--chart-2)]`
  - Replace summary `text-[#ef4444]` → `text-[var(--destructive)]`
  - Update tooltip content colors to use `var(--chart-2)` / `var(--destructive)` / `var(--chart-1)`
- [ ] Run `pnpm build` and verify no type or lint errors
- [ ] Visually verify chart renders correctly in light and dark mode

## CSS Token Reference

```css
/* Light mode */
--chart-1: oklch(0.646 0.189 237.6);   /* blue — net */
--chart-2: oklch(0.664 0.147 155.2);   /* green — inflows */
--destructive: oklch(0.577 0.245 27.325);/* red — outflows */

/* Dark mode */
--chart-1: oklch(0.716 0.156 237.6);
--chart-2: oklch(0.724 0.126 155.2);
--destructive: oklch(0.704 0.191 22.216); /* orange-red in dark */
```

## File Structure

```
src/domain/dashboard/components/CashFlowCard.tsx  — 6 color replacements
```

## Dev Notes

- `@visx/shape` `Bar` `fill` prop accepts CSS variable strings directly
- Tailwind `bg-[var(--x)]` syntax works for arbitrary CSS variable values
- The `@visx` vs Recharts split in the dashboard is a pre-existing architectural concern — this story does NOT migrate to Recharts, only standardizes colors within the existing `@visx` implementation
- Follow-up: `RevenueTrendChart` also has hardcoded `stroke="#6366f1"` that should use a CSS token — tracked separately as a follow-up story
