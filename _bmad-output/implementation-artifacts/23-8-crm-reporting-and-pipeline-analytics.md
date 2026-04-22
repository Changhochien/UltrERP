# Story 23.8: CRM Reporting and Pipeline Analytics

Status: completed

## Story

As a sales manager or commercial leader,
I want a CRM dashboard and pipeline analytics layer,
so that I can understand funnel health, forecast coverage, rep performance, and loss patterns from the CRM records already captured in Epic 23.

## Problem Statement

Stories 23.1 through 23.7 create the CRM records, setup masters, attribution flow, and conversion lineage needed for pipeline oversight, but leadership still needs one analytics slice that turns those stored fields into stable operational metrics. The validated research confirms the CRM model already carries sales stage, probability, expected closing, lost reasons, competitors, and attribution data, while the corrected roadmap explicitly expects pipeline visibility without dragging in a full BI platform. Without a dedicated analytics story, managers will rely on fragmented list views and inconsistent spreadsheet formulas for forecasting and performance review.

## Solution

Add a CRM analytics slice that:

- builds a manager-facing dashboard from lead, opportunity, quotation, order-handoff, and conversion-lineage data already owned by earlier stories
- defines stable metric formulas for pipeline value, weighted forecast, win or loss outcomes, conversion rate, and average deal size
- exposes funnel, loss-reason, rep-performance, and period-comparison views without creating a generic analytics platform

This story should provide CRM and pipeline analytics, not finance dashboards, marketing-automation analytics, or a general-purpose report builder.

## Acceptance Criteria

1. Given a sales manager opens the CRM dashboard, when the dashboard loads, then it shows stable KPI cards for open pipeline value, weighted pipeline value, win rate, lead-conversion rate, and average deal size using one documented metric definition set.
2. Given a funnel or stage analysis is requested, when the manager views pipeline analytics, then lead, opportunity, quotation, and converted outcomes are visible by stage with drop-off counts and conversion percentages.
3. Given win or loss analysis is requested, when the manager reviews terminal CRM outcomes, then lost reasons, competitor mentions, and terminal counts are visible in ranked views grounded in stored CRM status data.
4. Given rep-performance or forecast views are requested, when the manager filters by owner and period, then assigned leads, owned opportunities, open pipeline, weighted forecast, converted revenue, and time-to-conversion measures are visible.
5. Given a comparison period is selected, when analytics are rendered, then current-period versus prior-period trends for pipeline, win rate, conversion rate, and converted revenue are visible from the same metric definitions.
6. Given this story is implemented, when the touched code is reviewed, then it extends Story 23.5 reporting and Story 23.6 attribution reporting instead of replacing them, and it does not introduce a generic BI builder, finance-ledger reporting, or marketing-campaign automation.

## Tasks / Subtasks

- [x] Task 1: Define the CRM analytics metric contract. (AC: 1-5)
  - [x] Document metric definitions for open pipeline value, weighted pipeline value, win rate, lead-conversion rate, average deal size, converted revenue, and time-to-conversion.
  - [x] Keep Epic 23 metrics in current base-currency semantics until Epic 25 extends them for cross-currency reporting.
  - [x] Make period filters, owner filters, stage filters, territory filters, and attribution filters explicit and reusable.
- [x] Task 2: Build analytics projections and service endpoints. (AC: 1-5)
  - [x] Add read-oriented projections or queries for KPI cards, funnel counts, terminal outcome analysis, rep scorecards, and forecast views.
  - [x] Reuse stored lead, opportunity, quotation, order-handoff, and conversion-lineage fields rather than recomputing history heuristically.
  - [x] Extend the Story 23.5 reporting layer and the Story 23.6 attribution segments instead of creating an isolated analytics stack.
- [x] Task 3: Build manager-facing dashboard and analytics views. (AC: 1-5)
  - [x] Add a CRM dashboard with KPI cards and quick filter controls.
  - [x] Add funnel, win or loss, rep-performance, and forecast views with readable breakdowns and trend comparisons.
  - [x] Reuse Epic 22 shared dashboard, table, chart, filter, and feedback primitives.
- [x] Task 4: Add comparison and drilldown behavior. (AC: 2-5)
  - [x] Support period-over-period comparison for dashboard KPIs and trend visuals.
  - [x] Allow drilldown from KPI or chart summaries into the underlying lead, opportunity, quotation, or converted-order record sets.
  - [x] Keep drilldown read-only and analytics-focused rather than turning this into a custom report builder.
- [x] Task 5: Add focused tests and validation. (AC: 1-6)
  - [x] Add backend tests for metric formulas, forecast weighting, trend comparison, and loss-reason aggregation.
  - [x] Add frontend tests for dashboard rendering, filter interactions, drilldowns, and period comparison behavior.
  - [x] Validate that no generic BI builder, finance reporting suite, or marketing-campaign engine lands in this story.

## Dev Notes

### Context

- Story 23.5 owns the baseline CRM reporting surface and setup masters.
- Story 23.6 extends that layer with attribution-specific filters and measures.
- Story 23.8 should consolidate those stored CRM facts into manager analytics rather than recreate the reporting stack from scratch.

### Architecture Compliance

- Keep analytics read-oriented and projection-based.
- Reuse CRM status, probability, expected-closing, lost-reason, competitor, attribution, and conversion-lineage fields already owned by earlier stories.
- Keep this slice manager-focused; do not broaden into general BI or finance reporting.
- Preserve Epic 21 order ownership by consuming order-handoff results only as an analytic signal.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/crm/service.py`
  - `backend/domains/crm/routes.py`
  - CRM read models or projection helpers
  - migrations only if explicit analytics snapshots or materialized helpers are required
- Likely frontend files:
  - `src/domain/crm/` dashboard, analytics, and manager-view components
  - `src/lib/api/crm.ts`
  - shared chart and filter utilities already used in the frontend
- KPI math should be explicit and stable. If a metric definition changes later, it should be a deliberate contract update rather than a silent UI-only change.
- Forecast should be based on open opportunities using stored `probability` and `expected_closing` values. Converted revenue should come from converted quotation or order lineage, not from finance-ledger postings.
- Metric formulas in this first slice should stay simple and explicit:
  - `open_pipeline_value`: sum of open opportunity amounts in the filtered period or owner scope
  - `weighted_pipeline_value`: sum of each open opportunity amount multiplied by `probability / 100`
  - `win_rate`: converted opportunities divided by terminal opportunities (`converted` or `lost`) in the filtered period
  - `lead_conversion_rate`: leads that reached a converted-compatible state divided by qualified leads in the filtered period
  - `average_deal_size`: average converted-order amount from quotation-to-order lineage in the filtered period
  - `converted_revenue`: sum of converted-order totals linked from CRM lineage in the filtered period
  - `time_to_conversion`: elapsed time between lead creation and lead conversion timestamp

### Data Model Contract

- CRM analytics should consume at minimum these stored inputs:
  - lead status and created or converted timestamps
  - opportunity status, probability, expected closing, amount, owner, lost reason, and competitor data
  - quotation status and converted-order lineage
  - order lineage from Story 23.4
  - attribution and conversion-lineage data from Stories 23.6 and 23.7
- Metric definitions should be documented and shared across backend and frontend for at minimum:
  - `open_pipeline_value`
  - `weighted_pipeline_value`
  - `win_rate`
  - `lead_conversion_rate`
  - `average_deal_size`
  - `converted_revenue`
  - `time_to_conversion`
- Terminal opportunity outcomes for analytics in this slice should be treated as `converted` or `lost`; non-terminal statuses remain in pipeline metrics only.
- Converted revenue and average deal size should use order totals from CRM lineage rather than invoice or ledger totals, preserving Epic 21 and Epic 23 ownership boundaries.

### Testing Requirements

- Backend tests should cover deterministic KPI formulas, funnel stage counts, weighted forecast totals, and period-comparison queries.
- Frontend tests should cover KPI cards, filters, chart rendering, and drilldown behavior.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-23.md`
- `../implementation-artifacts/23-5-crm-setup-masters-and-pipeline-reporting.md`
- `../implementation-artifacts/23-6-utm-tracking-and-marketing-attribution.md`
- `../implementation-artifacts/23-7-lead-conversion-and-customer-handoff.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-crm-sales-detailed.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `.omc/research/gap-analysis.md`
- `backend/domains/crm/models.py`
- `backend/domains/crm/service.py`
- `backend/domains/crm/schemas.py`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd /Users/changtom/Downloads/UltrERP/backend && .venv/bin/python -m pytest tests/domains/crm/test_reporting_service.py`
- `cd /Users/changtom/Downloads/UltrERP && pnpm test -- --run src/tests/crm/CRMPipelineReportPage.test.tsx`

### Completion Notes List

- Extended the existing CRM reporting contract with explicit period-comparison filters, analytics KPI payloads, funnel breakdowns, terminal outcome rankings, owner scorecards, and read-only drilldown record groups.
- Reused the current pipeline reporting surface for the manager dashboard instead of adding a parallel analytics route, preserving Story 23.5 and Story 23.6 ownership boundaries.
- Added focused analytics validation that locks KPI formulas, weighted forecast, period comparison, competitor and lost-reason aggregation, dashboard rendering, filter interactions, and drilldown behavior.

### File List

- `_bmad-output/implementation-artifacts/23-8-crm-reporting-and-pipeline-analytics.md`
- `backend/domains/crm/_pipeline.py`
- `backend/domains/crm/schemas.py`
- `backend/tests/domains/crm/test_reporting_service.py`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
- `src/domain/crm/types.ts`
- `src/lib/api/crm.ts`
- `src/pages/crm/CRMPipelineReportPage.tsx`
- `src/tests/crm/CRMPipelineReportPage.test.tsx`

## Simplification Pass (2026-04-22)

Following the simplify skill workflow, a code review was conducted using parallel agent analysis covering code reuse, quality, and efficiency.

### Changes Applied

| File | Change | Rationale |
|------|--------|------------|
| `backend/domains/crm/_pipeline.py` | Extracted `_build_drilldown_record()` helper function | Eliminated 4 near-identical code blocks for drilldown record construction |
| `backend/domains/crm/_pipeline.py` | Updated drilldown building to use `getattr()` with explicit defaults | Consistent handling of missing attributes across all record types; required for test fixture compatibility |
| `src/domain/crm/types.ts` | Added index signature `[key: string]: ...` to `CRMPipelineReport` | Fixed TypeScript error for dynamic segment group property access via `SEGMENT_GROUP_MAPPINGS` |

### Skipped (Low Priority / High Risk)

| Item | Reason |
|------|--------|
| `_build_analytics_snapshot` function split | At 540 lines, splitting would require significant refactoring of the analytics computation pipeline. Pre-computed attrs pattern already reduces redundant `getattr` calls. |
| Magic string constant extraction | Test fixtures use hardcoded strings which is acceptable; production code already uses `LeadConversionState` enum |

### Verification Results

| Check | Result |
|-------|--------|
| Backend Tests (`pytest tests/domains/crm/`) | 88 passed |
| Frontend Tests (`pnpm test`) | 327 passed |
| TypeScript Type Check (`pnpm tsc --noEmit`) | 0 errors |
| ESLint (`pnpm eslint src/domain/crm/types.ts`) | 0 errors |

## Change Log

- 2026-04-22: Implemented Story 23.8 CRM analytics, comparison filters, drilldowns, and focused validation.
- 2026-04-22: Simplified code via code review - extracted drilldown record builder helper, added TypeScript index signature for dynamic property access.
- 2026-04-22: Fixed 4 pre-existing lint errors by converting empty interfaces to type aliases (`CRMSettingsUpdatePayload`, `QuotationItemPayload`, `QuotationRevisionPayload`, `QuotationItemResponse`).