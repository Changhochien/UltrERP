# Story 17.11: Cash Flow Card (Frontend)

Status: done

## Implementation Status

**Frontend:** DONE — Component and hook exist and are wired to backend

**Completed:**
- `CashFlowCard` component exists at `src/domain/dashboard/components/CashFlowCard.tsx`
- `useCashFlow` hook exists in `useDashboard.ts`
- Backend endpoint now available at `/api/v1/dashboard/cash-flow` (story 17.5 complete)

## Story

As an owner,
I want to see a bar chart of weekly cash inflows vs. outflows,
so that I can understand if the business is generating or consuming cash.

## Acceptance Criteria

1. [AC-1] Given the owner dashboard is loaded, when the `cash-flow` endpoint returns data, then a `CashFlowCard` displays a recharts `<BarChart>` with:
   - X-axis: weeks (or days if range < 14 days)
   - Two bars per period: inflows (green) and outflows (red)
   - A third bar or line showing net cash flow
2. [AC-2] A summary row shows total inflows, total outflows, net for the period
3. [AC-3] The chart is responsive

## Tasks / Subtasks

- [x] Task 1 (AC: 1)
  - [x] Subtask 1.1: Create `CashFlowCard` component at `src/domain/dashboard/components/CashFlowCard.tsx`
  - [x] Subtask 1.2: Use recharts `<BarChart>` with `<Bar>` elements for inflows (green #22c55e), outflows (red #ef4444), net (blue #3b82f6)
  - [x] Subtask 1.3: Implement x-axis with week/day labels based on data range
- [x] Task 2 (AC: 2)
  - [x] Subtask 2.1: Add summary row with total inflows, total outflows, net cash flow
- [x] Task 3 (AC: 3)
  - [x] Subtask 3.1: Wrap chart in responsive container

## Dev Notes

- Fetch data from `GET /api/v1/dashboard/cash-flow` (Story 17.5)
- Response shape: `{ inflows: { period: string, amount: string }[], outflows: { period: string, amount: string }[], net: { period: string, amount: string }[] }`
- Use `<ResponsiveContainer>` from recharts for responsive sizing
- Match existing card patterns from `RevenueCard.tsx` (loading skeleton, error surface)

### Project Structure Notes

- Component location: `src/domain/dashboard/components/CashFlowCard.tsx`
- Types location: `src/domain/dashboard/types.ts` (add `CashFlowResponse` interface)
- No conflicts with existing structure

### References

- [Source: Story 17.5 — Cash Flow Endpoint]
- [Source: src/domain/dashboard/components/RevenueCard.tsx]
- [Source: src/domain/dashboard/types.ts]
- [Source: recharts ResponsiveContainer]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List

- `src/domain/dashboard/components/CashFlowCard.tsx` (new)
- `src/domain/dashboard/types.ts` (update — add CashFlowResponse)
