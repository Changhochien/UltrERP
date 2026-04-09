# Story 17.9: AR Aging Card (Frontend)

Status: done

## Implementation Status

**Frontend:** DONE — Component and hook exist; API path bug fixed

**Completed:**
- `ARAgingCard` component exists at `src/domain/dashboard/components/ARAgingCard.tsx`
- `useARAging` hook exists in `useDashboard.ts`
- API path bug fixed: `fetchARAging()` now calls `/api/v1/reports/ar-aging` (correct path)

## Story

As an owner,
I want to see accounts receivable aging in four bucket columns,
So that I can identify overdue payments and follow up.

## Acceptance Criteria

**AC1:** AR Aging Card displays four bucket columns
**Given** the owner dashboard is loaded
**When** the `ar-aging` endpoint (story 17.3) returns data
**Then** an `ARAgingCard` shows four aging buckets as columns:
- 0–30 days: green indicator (healthy)
- 31–60 days: amber indicator (attention)
- 61–90 days: orange indicator (warning)
- 90+ days: red indicator (critical)

**AC2:** Bucket amounts formatted as TWD currency
**Given** a bucket has outstanding amounts
**When** the amount is displayed
**Then** it is formatted as TWD currency with `NT$` prefix and comma separators

**AC3:** Summary row
**Given** the AR aging data is loaded
**When** the card renders
**Then** a summary row displays:
- `total_outstanding`: sum of all buckets
- `total_overdue`: sum of buckets 31–60, 61–90, and 90+

**AC4:** Loading skeleton state
**Given** the owner dashboard is loading
**When** the `ar-aging` API call is in flight
**Then** a Skeleton placeholder is shown instead of the card

**AC5:** Error state with retry
**Given** the `ar-aging` API call fails
**When** an error occurs
**Then** an error message is displayed with a retry button

## Tasks / Subtasks

- [x] **Task 1: ARAgingCard Component** (AC1-AC3)
  - [x] Create `src/domain/dashboard/components/ARAgingCard.tsx`:
    - Props: `data: ARAgingResponse | null`, `isLoading: boolean`, `error: string | null`, `onRetry: () => void`
    - Layout: 4-column grid for buckets + summary row
    - Each bucket: colored indicator dot + label + amount
    - Bucket colors: green (#22c55e), amber (#eab308), orange (#f97316), red (#ef4444)
    - Summary row: total_outstanding and total_overdue

- [x] **Task 2: AR Aging Data Type** (AC1, AC3)
  - [x] Add to `src/domain/dashboard/types.ts`:
    ```typescript
    export interface ARAgingBucket {
      bucket_label: string; // "0-30", "31-60", "61-90", "90+"
      amount: string;       // Decimal as string, TWD
      invoice_count: number;
    }

    export interface ARAgingResponse {
      as_of_date: string;
      buckets: ARAgingBucket[];
      total_outstanding: string;
      total_overdue: string;
    }
    ```

- [x] **Task 3: Dashboard Hook for AR Aging** (AC4, AC5)
  - [x] Add `useARAging()` to `src/domain/dashboard/hooks/useDashboard.ts`:
    - Fetches from `/api/v1/reports/ar-aging` (story 17.3 backend)
    - Returns `{ data, isLoading, error, refetch }`

- [x] **Task 4: Loading and Error States** (AC4, AC5)
  - [x] ARAgingCard renders `Skeleton` when `isLoading`
  - [x] ARAgingCard renders error `SurfaceMessage` with retry button when `error`

- [x] **Task 5: Frontend Tests** (AC1-AC5)
  - [x] Create `src/domain/dashboard/__tests__/ARAgingCard.test.tsx`
  - [x] Test: renders all 4 buckets with correct colors
  - [x] Test: renders summary row with totals
  - [x] Test: amounts formatted as TWD
  - [x] Test: loading skeleton during fetch
  - [x] Test: error state with retry button

## Dev Notes

### AR Aging API Contract (Story 17.3)

The `GET /api/v1/reports/ar-aging` endpoint returns:
```typescript
interface ARAgingResponse {
  as_of_date: string;          // ISO date
  buckets: [
    { bucket_label: "0-30", amount: "50000.00", invoice_count: 5 },
    { bucket_label: "31-60", amount: "25000.00", invoice_count: 2 },
    { bucket_label: "61-90", amount: "12000.00", invoice_count: 1 },
    { bucket_label: "90+", amount: "8000.00", invoice_count: 1 },
  ];
  total_outstanding: "95000.00";
  total_overdue: "45000.00";
}
```

### Bucket Color Coding

| Bucket | Label | Color | Tailwind/hex |
|--------|-------|-------|--------------|
| 0–30 days | Healthy | Green | `text-green-500` / `#22c55e` |
| 31–60 days | Attention | Amber | `text-amber-500` / `#eab308` |
| 61–90 days | Warning | Orange | `text-orange-500` / `#f97316` |
| 90+ days | Critical | Red | `text-red-500` / `#ef4444` |

Use colored dots/badges to indicate severity, not just text color.

### TWD Currency Formatting

```typescript
const formatTWD = (value: string | number) =>
  `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
```

### Loading Skeleton Pattern

```typescript
if (isLoading) {
  return (
    <Card ...>
      <div data-testid="ar-aging-loading">
        <Skeleton className="h-4 w-24 mb-2" />
        <Skeleton className="h-20 w-full" />
      </div>
    </Card>
  );
}
```

### Card Component Reference

Uses `Card`, `CardHeader`, `CardTitle`, `CardContent` from `components/ui/card` (same as LowStockAlertsCard).

### Project Structure Notes

- Component: `src/domain/dashboard/components/ARAgingCard.tsx`
- Hook: extend `src/domain/dashboard/hooks/useDashboard.ts`
- Types: extend `src/domain/dashboard/types.ts`
- API fetch: add to `src/lib/api/dashboard.ts`
- Tests: `src/domain/dashboard/__tests__/ARAgingCard.test.tsx`

### Mirror of APAgingCard (Story 17.10)

This card and APAgingCard (17.10) share identical layout. Consider extracting shared logic if duplication becomes burdensome, but do not premature abstract — implement APAgingCard first and extract only if a clear pattern emerges.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.9] AC definitions
- [Source: src/domain/dashboard/components/LowStockAlertsCard.tsx] Card + Badge pattern
- [Source: src/domain/dashboard/types.ts] Existing dashboard types
- [Source: _bmad-output/implementation-artifacts/17-3-ar-aging-report-endpoint.md] Backend endpoint
