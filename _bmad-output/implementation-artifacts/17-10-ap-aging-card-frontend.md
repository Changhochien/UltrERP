# Story 17.10: AP Aging Card (Frontend)

Status: done

## Implementation Status

**Frontend:** DONE — Component and hook exist; API path bug fixed

**Completed:**
- `APAgingCard` component exists at `src/domain/dashboard/components/APAgingCard.tsx`
- `useAPAging` hook exists in `useDashboard.ts`
- API path bug fixed: `fetchAPAging()` now calls `/api/v1/reports/ap-aging` (correct path)

## Story

As an owner,
I want to see accounts payable aging in four bucket columns,
So that I can manage cash outflow timing and supplier relationships.

## Acceptance Criteria

**AC1:** AP Aging Card displays four bucket columns
**Given** the owner dashboard is loaded
**When** the `ap-aging` endpoint (story 17.4) returns data
**Then** an `APAgingCard` shows four aging buckets as columns:
- 0–30 days: green indicator (healthy)
- 31–60 days: amber indicator (attention)
- 61–90 days: orange indicator (warning)
- 90+ days: red indicator (critical)

**AC2:** Bucket amounts formatted as TWD currency
**Given** a bucket has outstanding amounts
**When** the amount is displayed
**Then** it is formatted as TWD currency with `NT$` prefix and comma separators

**AC3:** Summary row
**Given** the AP aging data is loaded
**When** the card renders
**Then** a summary row displays:
- `total_outstanding`: sum of all buckets
- `total_overdue`: sum of buckets 31–60, 61–90, and 90+

**AC4:** Visually distinct from AR Aging Card
**Given** both AR Aging Card and AP Aging Card are displayed
**When** the user views both cards
**Then** AP Aging Card is labeled with "Payables" to distinguish it from "Receivables"

**AC5:** Loading skeleton state
**Given** the owner dashboard is loading
**When** the `ap-aging` API call is in flight
**Then** a Skeleton placeholder is shown instead of the card

**AC6:** Error state with retry
**Given** the `ap-aging` API call fails
**When** an error occurs
**Then** an error message is displayed with a retry button

## Tasks / Subtasks

- [x] **Task 1: APAgingCard Component** (AC1-AC4)
  - [x] Create `src/domain/dashboard/components/APAgingCard.tsx`:
    - Props: `data: APAgingResponse | null`, `isLoading: boolean`, `error: string | null`, `onRetry: () => void`
    - Layout: 4-column grid for buckets + summary row
    - Each bucket: colored indicator dot + label + amount
    - Card title: "Payables Aging" (not "Receivables Aging")
    - Bucket colors match AR Aging Card: green, amber, orange, red

- [x] **Task 2: AP Aging Data Type** (AC1, AC3)
  - [x] Add to `src/domain/dashboard/types.ts`:
    ```typescript
    export interface APAgingBucket {
      bucket_label: string; // "0-30", "31-60", "61-90", "90+"
      amount: string;        // Decimal as string, TWD
      invoice_count: number;
    }

    export interface APAgingResponse {
      as_of_date: string;
      buckets: APAgingBucket[];
      total_outstanding: string;
      total_overdue: string;
    }
    ```

- [x] **Task 3: Dashboard Hook for AP Aging** (AC5, AC6)
  - [x] Add `useAPAging()` to `src/domain/dashboard/hooks/useDashboard.ts`:
    - Fetches from `/api/v1/reports/ap-aging` (story 17.4 backend)
    - Returns `{ data, isLoading, error, refetch }`

- [x] **Task 4: Loading and Error States** (AC5, AC6)
  - [x] APAgingCard renders `Skeleton` when `isLoading`
  - [x] APAgingCard renders error `SurfaceMessage` with retry button when `error`

- [x] **Task 5: Frontend Tests** (AC1-AC6)
  - [x] Create `src/domain/dashboard/__tests__/APAgingCard.test.tsx`
  - [x] Test: renders all 4 buckets with correct colors
  - [x] Test: renders summary row with totals
  - [x] Test: card is labeled "Payables" (not "Receivables")
  - [x] Test: amounts formatted as TWD
  - [x] Test: loading skeleton during fetch
  - [x] Test: error state with retry button

## Dev Notes

### AP Aging API Contract (Story 17.4)

The `GET /api/v1/reports/ap-aging` endpoint returns:
```typescript
interface APAgingResponse {
  as_of_date: string;          // ISO date
  buckets: [
    { bucket_label: "0-30", amount: "30000.00", invoice_count: 3 },
    { bucket_label: "31-60", amount: "15000.00", invoice_count: 2 },
    { bucket_label: "61-90", amount: "8000.00", invoice_count: 1 },
    { bucket_label: "90+", amount: "5000.00", invoice_count: 1 },
  ];
  total_outstanding: "58000.00";
  total_overdue: "28000.00";
}
```

### Bucket Color Coding

Same as AR Aging Card:

| Bucket | Label | Color | Tailwind/hex |
|--------|-------|-------|--------------|
| 0–30 days | Healthy | Green | `text-green-500` / `#22c55e` |
| 31–60 days | Attention | Amber | `text-amber-500` / `#eab308` |
| 61–90 days | Warning | Orange | `text-orange-500` / `#f97316` |
| 90+ days | Critical | Red | `text-red-500` / `#ef4444` |

### TWD Currency Formatting

```typescript
const formatTWD = (value: string | number) =>
  `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
```

### Layout Mirror with AR Aging Card

APAgingCard and ARAgingCard (story 17.9) share identical layout structure. Both have:
- 4-column bucket grid
- Summary row with total_outstanding and total_overdue
- Same loading/error states

APAgingCard differences:
- Title: "Payables Aging" instead of "Receivables Aging"
- Label: "Payables" instead of "Receivables" in the card header
- API: fetches from `/api/v1/reports/ap-aging` instead of `/api/v1/reports/ar-aging`

### Project Structure Notes

- Component: `src/domain/dashboard/components/APAgingCard.tsx`
- Hook: extend `src/domain/dashboard/hooks/useDashboard.ts`
- Types: extend `src/domain/dashboard/types.ts`
- API fetch: add to `src/lib/api/dashboard.ts`
- Tests: `src/domain/dashboard/__tests__/APAgingCard.test.tsx`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.10] AC definitions
- [Source: _bmad-output/implementation-artifacts/17-9-ar-aging-card-frontend.md] AR Aging Card layout (identical structure)
- [Source: src/domain/dashboard/types.ts] Existing dashboard types
- [Source: _bmad-output/implementation-artifacts/17-4-ap-aging-report-endpoint.md] Backend endpoint
