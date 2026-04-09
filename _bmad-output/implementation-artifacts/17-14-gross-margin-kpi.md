# Story 17.14: Gross Margin KPI (Frontend, Deferred Until COGS)

Status: done

## Implementation Status

**Frontend:** DONE — Component and hook exist

**Completed:**
- `GrossMarginCard` component exists at `src/domain/dashboard/components/GrossMarginCard.tsx`
- `useGrossMargin` hook exists in `useDashboard.ts`
- Card handles `available: false` state gracefully with "Margin data unavailable" message
- unit_cost field now available on OrderLine/InvoiceLine (story 17.15 complete)

## Story

As an owner,
I want to see my gross margin %,
so that I know how much profit I'm making on sales after accounting for product costs.

## Acceptance Criteria

1. [AC-1] Given OrderLine and InvoiceLine have unit_cost populated, when the owner dashboard loads, then a `GrossMarginCard` shows:
   - Gross margin % = (Revenue − COGS) / Revenue × 100
   - COGS = sum(OrderLine.quantity × OrderLine.unit_cost) for the period
   - Revenue = sum(OrderLine.total_amount) for the period
   - Comparison to previous period (same metric, prior month)
2. [AC-2] If unit_cost is not populated on OrderLine/InvoiceLine, the card shows "Margin data unavailable — cost tracking not configured" with an info icon instead of a number
3. [AC-3] This story is gated behind Story 17.15 (COGS data model extension)

## Tasks / Subtasks

- [x] Task 1 (AC: 1)
  - [x] Subtask 1.1: Create `GrossMarginCard` component at `src/domain/dashboard/components/GrossMarginCard.tsx`
  - [x] Subtask 1.2: Fetch gross margin data from `GET /api/v1/dashboard/gross-margin` (or derive from existing endpoints)
  - [x] Subtask 1.3: Display gross margin %, COGS value, revenue value
  - [x] Subtask 1.4: Show comparison badge to previous period
- [x] Task 2 (AC: 2)
  - [x] Subtask 2.1: Detect when unit_cost data is unavailable
  - [x] Subtask 2.2: Display info-state message "Margin data unavailable — cost tracking not configured" with info icon
- [x] Task 3 (AC: 3)
  - [x] Subtask 3.1: Ensure card handles gracefully when backend returns `unit_cost` as null/missing

## Dev Notes

- Backend dependency: Story 17.15 must be completed first to populate `unit_cost`
- Frontend should handle both "data ready" and "data unavailable" states
- Use `MetricCard` pattern for consistent KPI display
- Fallback message with info icon when COGS data not available
- Response shape (when available): `{ gross_margin_percent: string, cogs: string, revenue: string, previous_period: { gross_margin_percent: string } }`
- Response shape (when unavailable): `{ available: false, message: string }`

### Project Structure Notes

- Component location: `src/domain/dashboard/components/GrossMarginCard.tsx`
- Types location: `src/domain/dashboard/types.ts` (add `GrossMarginResponse`)
- No conflicts with existing structure

### References

- [Source: Story 17.15 — Add unit_cost to OrderLine and InvoiceLine]
- [Source: src/domain/dashboard/components/RevenueCard.tsx]
- [Source: src/domain/dashboard/types.ts]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List

- `src/domain/dashboard/components/GrossMarginCard.tsx` (new)
- `src/domain/dashboard/types.ts` (update — add GrossMarginResponse)
