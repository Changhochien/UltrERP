---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - "/Volumes/2T_SSD_App/Projects/UltrERP/_bmad-output/planning-artifacts/17-owner-financial-dashboard.md"
workflowType: 'research'
lastStep: 6
research_type: 'domain'
research_topic: 'Owner financial dashboard for SME ERP'
research_goals: 'Identify best-practice KPI structure, financial dashboard UX/UI patterns, and highest-value scope refinements for Epic 17 Owner Financial Dashboard.'
user_name: 'Hcchang'
date: '2026-04-08'
web_research_enabled: true
source_verification: true
---

# From Morning Pulse to Owner Control Tower: Comprehensive Owner Financial Dashboard Domain Research

**Date:** 2026-04-08
**Author:** Hcchang
**Research Type:** domain

---

## Research Overview

This research reviewed how mature finance and analytics products structure owner and CFO dashboards, then translated those patterns into practical product guidance for UltrERP Epic 17. The strongest cross-source pattern is that high-value financial dashboards are not just "more KPIs." They are working-capital control surfaces. They prioritize liquidity, overdue receivables, payable timing, trend context, and drill-down actions ahead of passive summary widgets. Inference from SAP Working Capital Insights, SAP Working Capital Dashboard, Microsoft Dynamics 365 vendor aging guidance, Xero small-business finance guidance, Tableau dashboard design guidance, and Microsoft Power BI guidance: the best owner dashboard helps answer a small set of urgent business questions in one screen, then routes the user into action.

Epic 17 is directionally strong. It already includes the right foundation areas: revenue trend, AR aging, AP aging, cash flow, gross margin, and top customers. The main gaps are information hierarchy, actionability, and metric definitions. In particular, the current idea of a single summary card with many unrelated values is too dense for fast owner scanning, the current AP aging definition appears anchored to invoice date instead of due date, and the current "cash position" framing is really net cash movement unless bank balances are modeled.

The highest-value v1 for UltrERP is a page that helps an owner answer five questions quickly:

1. Are we generating or consuming cash?
2. Which receivables need action now?
3. Which payables are due soon, overdue, or safe to delay?
4. Is revenue and margin trending in the right direction?
5. Are we over-dependent on a few customers or a narrow slice of revenue?

---

## Executive Summary

The best-practice structure for Epic 17 is a cash-first, working-capital-first dashboard. SAP's working capital products organize the experience around overview, liquidity and cash, receivables, payables, and inventory, with a heading row of leading KPIs and supporting charts beneath. Tableau and Power BI both stress clear audience focus, one-screen storytelling, and putting the most important information in the most visible position. Xero's small-business finance guidance repeatedly centers AR aging, cash flow visibility, payment reminders, and payment scheduling. Together, those sources point to a simple product truth: owners get the most value when the page starts with liquidity and collections, not when every metric competes equally for attention. Sources: [SAP Working Capital Insights](https://help.sap.com/docs/business-data-cloud/viewing-intelligent-applications/working-capital-insights), [SAP Working Capital Dashboard](https://help.sap.com/docs/SAP_ANALYTICS_CLOUD/42093f14b43c485fbe3adbbe81eff6c8/819a965dd7d643de8e28e125ed22a3a6.html), [Tableau dashboard best practices](https://help.tableau.com/current/pro/desktop/en-us/dashboards_best_practices.htm), [Power BI report design tips](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-tips-and-tricks-for-creating-reports), [Xero cash flow guide](https://www.xero.com/us/guides/managing-cash-flow/)

The best value change to the current epic is to replace the overloaded "single KPI summary card" concept with a KPI strip of atomic cards, then anchor the page around one major cash view and two aging views. Aging should show both current and overdue posture, not only overdue buckets, because owners need to see near-term workload as well as late exposure. For AP specifically, due-date-based aging is more decision-useful than invoice-date-based aging because supplier payment discipline is tied to terms, discounts, and due dates. Sources: [Microsoft Dynamics 365 vendor aging report](https://learn.microsoft.com/en-us/dynamics365/finance/accounts-payable/vendor-aging-report), [Xero accounts receivable guide](https://www.xero.com/au/guides/what-is-accounts-receivable/), [Xero accounts payable guide](https://www.xero.com/us/guides/how-to-do-bookkeeping/manage-accounts-payable/)

The most important product caveat is naming accuracy. Epic 17 currently frames FR71 as "cash position" while the planned endpoint calculates inflows minus outflows over a selected period. That is not a true cash balance unless opening balances and bank accounts are modeled. Best practice is to label this as net cash flow or cash movement until the product can support real balance views. This is an inference from the SAP liquidity/cash pattern, Xero cash-flow guidance, and the current UltrERP data model described in the epic.

### Key Findings

- The owner dashboard should behave like a working-capital overview, not a generic analytics board.
- A KPI strip of small, focused cards is better than a single crowded mega-card.
- AR and AP should show both current and overdue posture; overdue-only views hide important near-term obligations.
- AP aging is more actionable when based on due date, not invoice date.
- "Cash position" should not be shown unless the system has actual bank balances or opening balances.
- Top customers becomes more valuable when it exposes concentration risk, not just rank order.
- Gross margin should be treated as a setup-aware metric with a graceful "unavailable" state until COGS is ready.
- Every financial widget should connect to a next action, not stop at passive reporting.

### Strategic Recommendations

- Add a global owner filter bar: `As of date`, period, refresh timestamp, and export.
- Replace the single KPI summary card with 4-6 compact KPI cards.
- Make the first major chart a combined inflow/outflow plus running net line view.
- Add a `current/not yet due` bucket to AR/AP aging and keep overdue buckets visually prominent.
- Use due date as the default basis for AP aging.
- Relabel cash views to `Net cash flow` or `Cash movement` until bank balances exist.
- Add customer concentration percentage and outstanding receivables to the top-customer view.
- Make every KPI, bucket, or ranked row clickable into invoices, supplier invoices, payments, or customer detail.

---

## Table of Contents

1. Research Introduction and Methodology
2. Domain Overview and Product Patterns
3. Competitive and UX Pattern Analysis
4. Regulatory and Data-Definition Considerations
5. Technology and Dashboard Design Trends
6. Strategic Insights and UX/UI Recommendations
7. Implementation Considerations and Risk Assessment
8. Future Outlook and Suggested Roadmap
9. Research Methodology and Source Verification
10. Appendices and Suggested Wireframe

## 1. Research Introduction and Methodology

### Research Significance

Epic 17 is not just another dashboard page. It is the moment UltrERP starts helping owners manage working capital, collections, supplier timing, and profitability from one place. This matters because mature finance platforms frame owner reporting around financial health and liquidity, not just sales totals. SAP explicitly positions working capital management around accounts payable, accounts receivable, inventory, and cash, and Power BI's finance-oriented samples show CFO dashboards organized around profitability drivers, customer mix, and margin context. Sources: [SAP Working Capital Dashboard](https://help.sap.com/docs/SAP_ANALYTICS_CLOUD/42093f14b43c485fbe3adbbe81eff6c8/819a965dd7d643de8e28e125ed22a3a6.html), [Power BI Customer Profitability sample](https://learn.microsoft.com/en-us/power-bi/create-reports/sample-customer-profitability)

### Research Methodology

- **Research Scope:** Owner financial dashboards, working-capital reporting, aging report behavior, small-business finance guidance, and dashboard UX/UI patterns.
- **Primary Inputs:** Epic 17 planning artifact plus current public vendor and documentation sources.
- **Analysis Framework:** Compare what mature systems emphasize first, how they define aging and cash views, and how they structure visual hierarchy for fast decision-making.
- **Time Period:** Current public sources available as of 2026-04-08.
- **Geographic Coverage:** Global product patterns with practical relevance to SME ERP usage.

### Research Goals and Objectives

**Original Goals:** Identify best-practice KPI structure, financial dashboard UX/UI patterns, and highest-value scope refinements for Epic 17 Owner Financial Dashboard.

**Achieved Objectives:**

- Validated which metrics belong at the top of the owner experience.
- Identified several high-value corrections to current Epic 17 assumptions.
- Produced a practical v1 layout and backlog refinement set for UltrERP.

## 2. Domain Overview and Product Patterns

### Mature Pattern: Working Capital Before Detail

SAP's Working Capital Insights product organizes the experience into pages for Overview, Liquidity and Cash, Accounts Receivable, Accounts Payable, and Inventory. Each page begins with leading KPIs and supporting charts. The overview emphasizes financial health and liquidity, while AR and AP pages surface aging and payment-efficiency signals. This is a strong pattern match for Epic 17 because it shows that finance dashboards create value by grouping metrics into decision domains instead of mixing everything into one tile cluster. Sources: [SAP Working Capital Insights](https://help.sap.com/docs/business-data-cloud/viewing-intelligent-applications/working-capital-insights), [SAP Net Working Capital Time Series Consumption](https://help.sap.com/docs/SAP_DATASPHERE/6eb1eff34e4c4b1f90adfbfba1334240/a88a78dc6bfc1014a79e69594ccc91ad.html)

### SMB Pattern: Cash Discipline and Aging Discipline

Xero's guidance for small businesses repeatedly treats cash flow and AR aging as core operating discipline. It recommends updating records weekly, reconciling monthly, tracking AR aging regularly, and using reminder schedules at 7, 14, and 30 days past due. Its AR guidance also stresses that aging reports show which invoices are least overdue and most overdue, and that older invoices are less likely to be collected. For AP, Xero emphasizes organizing bills, scheduling payments around terms and cash flow, and preserving supplier relationships. Sources: [Xero cash flow guide](https://www.xero.com/us/guides/managing-cash-flow/), [Xero accounts receivable guide](https://www.xero.com/au/guides/what-is-accounts-receivable/), [Xero accounts payable guide](https://www.xero.com/us/guides/how-to-do-bookkeeping/manage-accounts-payable/), [Xero AP process guide](https://www.xero.com/us/guides/accounts-payable-process/)

### Product Implication for UltrERP

Inference from SAP and Xero: the most useful owner dashboard is not only descriptive. It exposes posture plus next action. That means the page should not stop at showing an overdue amount. It should help the owner move into overdue invoices, customer follow-up, supplier-payment review, or open-order investigation with a single click.

## 3. Competitive and UX Pattern Analysis

### Dashboard Design Pattern: Clear Story, Not KPI Wallpaper

Tableau recommends knowing the purpose and audience first, placing the most important view in the upper-left area, and limiting the number of views to avoid clutter and performance issues. Power BI similarly recommends telling a story on one screen, making the most important information biggest, putting the most important information at the top, and avoiding clutter or weak visual choices. These are direct warnings against a "single giant summary card plus many equal widgets" approach. Sources: [Tableau dashboard best practices](https://help.tableau.com/current/pro/desktop/en-us/dashboards_best_practices.htm), [Power BI report design tips](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-tips-and-tricks-for-creating-reports)

### Mobile and Responsive Pattern: Fewer, Stronger Elements

Power BI's mobile guidance recommends using only significant visuals, placing the most important visuals at the top, not placing complex visuals side by side on mobile, and reducing extra chrome and labels. Even though Epic 17 explicitly defers mobile-specific design, this still matters because responsive desktop-to-mobile behavior should come from a layout that already has clear prioritization. Source: [Power BI mobile-optimized report best practices](https://learn.microsoft.com/en-us/power-bi/create-reports/power-bi-create-mobile-optimized-report-best-practices)

### Finance-Specific Pattern: Profitability Needs Context

Power BI's Customer Profitability sample shows a CFO dashboard that blends high-level company metrics with customer, product, and gross-margin context. The important lesson is not to show "top customers" as a vanity leaderboard. The value comes from understanding what factors drive profitability and which slices require follow-up. Source: [Power BI Customer Profitability sample](https://learn.microsoft.com/en-us/power-bi/create-reports/sample-customer-profitability)

### Product Implication for UltrERP

The owner dashboard should have three visual layers:

1. Immediate posture: what changed and what needs attention now.
2. Mid-level diagnosis: cash trend and aging distribution.
3. Driver analysis: top customers, revenue trend, gross margin status, and drill-down links.

## 4. Regulatory and Data-Definition Considerations

### Aging Definitions Need to Be Operationally Correct

Microsoft Dynamics 365's vendor aging report allows aging based on transaction date, due date, or document date, and exposes intervals or aging definitions. This matters because it confirms that AP aging is a definitional choice and due-date-based framing is often the most operationally meaningful for payment management. For UltrERP, using `invoice_date` alone for AP aging risks telling owners the wrong story about what is actually late, what is merely old, and what is strategically payable later. Source: [Microsoft Dynamics 365 vendor aging report](https://learn.microsoft.com/en-us/dynamics365/finance/accounts-payable/vendor-aging-report)

### Current Versus Overdue Must Be Separated

SAP's AR and AP insight pages explicitly discuss overdue versus future receivables and payables, not just already-overdue buckets. Inference for UltrERP: a dashboard that only shows 0-30, 31-60, 61-90, and 90+ days overdue hides near-term exposure and makes it harder to manage the next week or month of collections and payments. Source: [SAP Working Capital Insights](https://help.sap.com/docs/business-data-cloud/viewing-intelligent-applications/working-capital-insights)

### Cash Position Naming Accuracy

SAP distinguishes liquidity and cash analysis from broader working-capital measures, and Xero's cash-flow guidance centers tracking money in and money out. Inference for UltrERP: an endpoint that calculates inflows minus outflows across a selected period should be labeled `net cash flow` or `cash movement`, not `cash position`, unless opening balances and real account balances are modeled.

### Implementation Considerations

- Add explicit metric definitions in tooltips or info popovers.
- Show `As of` timestamps consistently.
- Distinguish `cash basis`, `accrual basis`, and `data unavailable` states where relevant.
- Do not surface gross margin as a definitive metric before COGS exists.

## 5. Technology and Dashboard Design Trends

### Integrated Financial Data, Pre-Aggregated Performance

SAP's working-capital dashboard combines cash, AR, AP, and inventory into integrated KPI views and persists interim results to avoid performance problems from live calculation across large financial datasets. This aligns well with Epic 17's stated NFRs and suggests that UltrERP should keep using aggregated endpoints and caching instead of overloading the frontend with raw joins or too many page-level calls. Source: [SAP Net Working Capital Time Series Consumption](https://help.sap.com/docs/SAP_DATASPHERE/6eb1eff34e4c4b1f90adfbfba1334240/a88a78dc6bfc1014a79e69594ccc91ad.html)

### Storytelling Plus Drilldown

Power BI and Tableau both encourage guided storytelling first, then user exploration through filters, highlights, and drill-ins. For UltrERP, this implies a page that starts with one clear overview state and allows deeper investigation from each widget rather than presenting many equal-weight controls all at once. Sources: [Tableau dashboard best practices](https://help.tableau.com/current/pro/desktop/en-us/dashboards_best_practices.htm), [Power BI report design tips](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-tips-and-tricks-for-creating-reports)

### Future Metrics Maturity

SAP's KPI set includes cash conversion cycle, quick ratio, DSO, DPO, inventory turnover, and gross margin. These are good future targets for UltrERP, but most require more mature accounting definitions, balance-sheet context, or COGS support than Epic 17 currently assumes. Source: [SAP Working Capital Insights](https://help.sap.com/docs/business-data-cloud/viewing-intelligent-applications/working-capital-insights)

## 6. Strategic Insights and UX/UI Recommendations

### Highest-Value Owner Questions

The dashboard should optimize for:

- liquidity now,
- collections risk,
- supplier payment timing,
- sales and margin direction,
- customer concentration risk.

That order is an inference from the source set and should drive layout priority.

### Recommended V1 Information Architecture

#### Filter Bar

- `As of date`
- period selector: 7d / 30d / month / quarter
- refresh timestamp
- export action

#### KPI Strip

Use 4-6 compact KPI cards, not one overloaded card. Recommended cards for v1:

- Revenue today or selected period
- Revenue delta vs prior period
- Open receivables amount
- Overdue receivables amount
- Net cash flow for selected period
- Pending order revenue or low-stock exceptions

If space permits, make low stock and pending orders secondary chips or mini-cards instead of primary finance tiles.

#### Main Analysis Row

- Left, wide: Net cash flow chart with inflow bars, outflow bars, and running net line
- Right: AR aging card with `Current`, `0-30`, `31-60`, `61-90`, `90+`

#### Secondary Analysis Row

- Left: AP aging card with the same bucket model, due-date-based
- Right: Revenue trend plus gross margin setup state

#### Tertiary Analysis Row

- Left: Top customers ranked table with revenue, percentage of total revenue, and outstanding balance
- Right: Action center with overdue invoices, supplier bills due soon, pending orders, and low-stock shortcuts

### UI Behavior Recommendations

- Every tile should have a short subtitle clarifying basis and comparison window.
- Use semantic color only for state: green healthy, amber attention, red critical.
- Keep chart legends minimal and avoid circular charts for financial comparisons.
- Use tabs or segmented controls for period switching, not dense filter panels.
- Add info tooltips for ambiguous metrics such as margin and net cash flow.
- Surface refresh time and data basis in the page header.
- For missing COGS, show a purposeful empty state, not a broken metric.

### Important Metric Corrections for Epic 17

#### 1. Replace the Single Summary Card Concept

The current epic wording around a single KPI summary card is too dense. A best-practice implementation should be a summary strip made of atomic cards.

#### 2. Add a Current Bucket to Aging

Overdue-only aging omits near-term payables and receivables that owners still need to plan around.

#### 3. Use Due Date for AP Aging

AP health is about payment timing against agreed terms, not simply how long ago a bill was created.

#### 4. Relabel Cash Views

Until bank balances are modeled, use `Net cash flow`, `Cash movement`, or `Net inflow/outflow`, not `Cash position`.

#### 5. Make Top Customers More Strategic

Show concentration percentage and outstanding receivable exposure so the owner can spot customer dependency risk.

## 7. Implementation Considerations and Risk Assessment

### Suggested V1 Dashboard Wireframe

```text
[ As of: 2026-04-08 ] [ 30 Days ] [ Refreshed 09:10 ] [ Export ]

[ Revenue ] [ Delta ] [ Open AR ] [ Overdue AR ] [ Net Cash Flow ] [ Pending Orders ]

[ Cash In / Out + Running Net .................................... ] [ AR Aging ...... ]

[ AP Aging ...................................................... ] [ Revenue Trend / Margin State ]

[ Top Customers + Concentration ................................. ] [ Action Center / Exceptions ]
```

### Backend and Data Model Implications

- Keep aggregated endpoints and 5-minute caching for summary views.
- Standardize on a shared `as_of_date` across KPI, AR, AP, and cash widgets.
- Add explicit basis fields in API responses where ambiguity exists.
- Treat margin as unavailable until COGS support is real.

### Product Risks

- **Metric overload risk:** too many numbers at once reduces owner confidence.
- **Definition risk:** inaccurate labels such as "cash position" create false trust.
- **Aging risk:** overdue-only or invoice-date-based AP aging can drive poor decisions.
- **Trust risk:** passive charts without drilldown paths make the dashboard feel decorative.

### Risk Mitigation

- Use a focused KPI strip.
- Add metric glossary tooltips.
- Keep action links from every tile.
- Ship truthful labels even when the metric is a proxy.

## 8. Future Outlook and Suggested Roadmap

### Build Now

- Working-capital-first layout
- KPI strip
- AR/AP views with current plus overdue posture
- Net cash flow trend
- Top customers with concentration context

### Build Next

- DSO and DPO
- quick ratio and cash coverage
- customer concentration alerts
- on-time payment rate and captured early-payment discounts

### Build Later

- true cash position from bank balances
- budget vs actual
- forecasting and predictive collections risk
- cohort and segment profitability

## Recommendations

### Immediate Epic Refinements

- Update Story 17.7 to a KPI strip instead of a single summary card.
- Add a new page-level filter story or acceptance criteria for `As of date` and period.
- Add a `Current` bucket to AR/AP aging design.
- Change AP aging basis recommendation to `due_date`.
- Relabel FR71/Story 17.5 output as net cash flow unless bank balances are added.
- Expand top customers to include concentration percentage and open receivable amount.

### Nice-to-Have Enhancements

- DSO and DPO cards
- cash conversion cycle
- quick ratio
- early-payment discount tracking
- payment reminder workflow integration

## 9. Research Methodology and Source Verification

### Primary Sources Used

- [SAP Working Capital Insights](https://help.sap.com/docs/business-data-cloud/viewing-intelligent-applications/working-capital-insights)
- [SAP Working Capital Dashboard](https://help.sap.com/docs/SAP_ANALYTICS_CLOUD/42093f14b43c485fbe3adbbe81eff6c8/819a965dd7d643de8e28e125ed22a3a6.html)
- [SAP Net Working Capital Time Series Consumption](https://help.sap.com/docs/SAP_DATASPHERE/6eb1eff34e4c4b1f90adfbfba1334240/a88a78dc6bfc1014a79e69594ccc91ad.html)
- [Microsoft Dynamics 365 vendor aging report](https://learn.microsoft.com/en-us/dynamics365/finance/accounts-payable/vendor-aging-report)
- [Power BI report design tips](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-tips-and-tricks-for-creating-reports)
- [Power BI mobile-optimized report best practices](https://learn.microsoft.com/en-us/power-bi/create-reports/power-bi-create-mobile-optimized-report-best-practices)
- [Power BI Customer Profitability sample](https://learn.microsoft.com/en-us/power-bi/create-reports/sample-customer-profitability)
- [Tableau dashboard best practices](https://help.tableau.com/current/pro/desktop/en-us/dashboards_best_practices.htm)
- [Xero cash flow guide](https://www.xero.com/us/guides/managing-cash-flow/)
- [Xero accounts receivable guide](https://www.xero.com/au/guides/what-is-accounts-receivable/)
- [Xero accounts payable guide](https://www.xero.com/us/guides/how-to-do-bookkeeping/manage-accounts-payable/)
- [Xero AP process guide](https://www.xero.com/us/guides/accounts-payable-process/)

### Confidence and Limits

Confidence is high on the UX and information-architecture conclusions because multiple official BI and ERP sources converge on the same layout principles. Confidence is medium-high on the AP aging and cash-position recommendations because they are partly inferential, but the inference is grounded in official documentation and the current Epic 17 data model constraints.

## 10. Appendices and Suggested Wireframe

### Best-Practice Owner Dashboard Outline

```text
HEADER
- Owner Dashboard
- As of date
- Period selector
- Refreshed timestamp
- Export

ROW 1: KPI STRIP
- Revenue
- Revenue delta
- Open AR
- Overdue AR
- Net cash flow
- Pending orders / low stock

ROW 2: WORKING CAPITAL
- Cash flow and running net
- AR aging

ROW 3: PAYMENT TIMING + TREND
- AP aging
- Revenue trend / gross margin state

ROW 4: DRIVER ANALYSIS
- Top customers + concentration
- Action center / operational shortcuts
```

### Final Takeaway

Epic 17 already contains the right raw ingredients. The best-value improvement is not adding more widgets. It is reordering the experience around owner decisions, correcting a few financial definitions, and making every widget actionable.
