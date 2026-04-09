# Story 17.12: Top Customers Card (Frontend)

Status: done

## Implementation Status

**Frontend:** DONE — Component and hook exist and are wired to backend

**Completed:**
- `TopCustomersCard` component exists at `src/domain/dashboard/components/TopCustomersCard.tsx`
- `useTopCustomers` hook exists in `useDashboard.ts`
- Backend endpoint now available at `/api/v1/dashboard/top-customers` (story 17.6 complete)

## Story

As an owner,
I want to see a ranked list of top customers by revenue,
so that I can identify and nurture key accounts.

## Acceptance Criteria

1. [AC-1] Given the owner dashboard is loaded, when the `top-customers` endpoint returns data, then a `TopCustomersCard` shows:
   - Rank number, company name, total revenue (TWD), invoice count
2. [AC-2] Period selector: Month / Quarter / Year (tabs or segmented control)
3. [AC-3] Top 10 customers displayed in a table or ranked list
4. [AC-4] Loading and error states are handled
5. [AC-5] Results update when the period selector changes

## Tasks / Subtasks

- [x] Task 1 (AC: 1, 3)
  - [x] Subtask 1.1: Create `TopCustomersCard` component at `src/domain/dashboard/components/TopCustomersCard.tsx`
  - [x] Subtask 1.2: Render ranked list/table with rank, company name, revenue, invoice count
  - [x] Subtask 1.3: Display top 10 results
- [x] Task 2 (AC: 2, 5)
  - [x] Subtask 2.1: Add period selector (Month/Quarter/Year tabs)
  - [x] Subtask 2.2: Refetch data when period changes
- [x] Task 3 (AC: 4)
  - [x] Subtask 3.1: Show skeleton loading state while data loads
  - [x] Subtask 3.2: Show error surface on failure

## Dev Notes

- Fetch data from `GET /api/v1/dashboard/top-customers` (Story 17.6)
- Query param: `?period=month|quarter|year`
- Response shape: `{ items: { rank: number, company_name: string, revenue: string, invoice_count: number }[], period: string }`
- Use `SegmentedControl` or tab-style period selector
- Currency formatting: `NT$ X,XXX.XX`
- Match loading/error patterns from `RevenueCard.tsx`

### Project Structure Notes

- Component location: `src/domain/dashboard/components/TopCustomersCard.tsx`
- Types location: `src/domain/dashboard/types.ts` (add `TopCustomerItem`, `TopCustomersResponse`)
- No conflicts with existing structure

### References

- [Source: Story 17.6 — Top Customers Endpoint]
- [Source: src/domain/dashboard/components/RevenueCard.tsx]
- [Source: src/domain/dashboard/types.ts]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List

- `src/domain/dashboard/components/TopCustomersCard.tsx` (new)
- `src/domain/dashboard/types.ts` (update — add TopCustomerItem, TopCustomersResponse)
