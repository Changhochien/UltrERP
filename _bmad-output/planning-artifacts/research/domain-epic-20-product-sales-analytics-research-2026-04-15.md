---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - "/Volumes/2T_SSD_App/Projects/UltrERP/_bmad-output/planning-artifacts/epic-20.md"
workflowType: 'research'
lastStep: 6
research_type: 'domain'
research_topic: 'Epic 20 Product Sales Analytics for UltrERP'
research_goals: 'Investigate whether Epic 20 is the correct development direction for UltrERP, validate it against current analytics and inventory-planning best practices, and recommend how it should be implemented.'
user_name: 'Hcchang'
date: '2026-04-15'
web_research_enabled: true
source_verification: true
---

# From Ad Hoc Intelligence to Durable Sales Facts: Comprehensive Epic 20 Product Sales Analytics Research

**Date:** 2026-04-15
**Author:** Hcchang
**Research Type:** domain

---

## Research Overview

This research evaluated Epic 20 against two realities at the same time: current dimensional-modeling best practice and UltrERP's actual codebase. The strongest conclusion is that Epic 20 is directionally correct, but not yet shaped tightly enough for this repository. External sources strongly support three ideas in the epic: preserve historical product attributes at the time of sale, introduce a periodic product sales fact at month grain, and keep a recent/live path for current-period data. Sources: [Kimball periodic snapshot fact tables](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/periodic-snapshot-fact-table/), [Kimball Type 2 SCD](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-2/), [dbt snapshots](https://docs.getdbt.com/docs/build/snapshots), [PostgreSQL materialized views](https://www.postgresql.org/docs/current/rules-materializedviews.html), [Power BI star schema guidance](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema)

The repo review, however, surfaced several design mismatches that matter before implementation starts. UltrERP already has an `intelligence` module for customer and category analytics, and the `inventory` domain already exposes product-level monthly demand, sales history, top customer, supplier, and reorder-point planning behavior. Epic 20 therefore should not land as an isolated second analytics silo with duplicated logic. It should become a shared analytics foundation used by both `intelligence` and `inventory`, with user-facing features added in phases. Relevant repo references: [backend/domains/inventory/routes.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/inventory/routes.py:475), [backend/domains/inventory/services.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/inventory/services.py:1715), [backend/domains/intelligence/service.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/intelligence/service.py:223)

The practical conclusion for UltrERP is:

- Yes, Epic 20 is the right direction.
- No, it should not be implemented exactly as written.
- The correct v1 is a phased analytics foundation: order-line snapshots first, one consistent monthly product fact second, then revenue and performance APIs on top, while reusing existing inventory and intelligence surfaces where possible.

---

## Executive Summary

Epic 20 is correct in principle because UltrERP now needs a durable historical sales layer, not only live window queries. Microsoft, Kimball, dbt, and PostgreSQL documentation all point in the same broad direction: use a consistent-grain fact table for aggregation, preserve slowly changing descriptive attributes explicitly, and refresh precomputed summaries on a schedule or on demand when current-state precision is not required. Sources: [Power BI star schema guidance](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema), [Kimball periodic snapshot fact tables](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/periodic-snapshot-fact-table/), [Kimball Type 2 SCD](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-2/), [dbt snapshots](https://docs.getdbt.com/docs/build/snapshots), [PostgreSQL materialized views](https://www.postgresql.org/docs/current/rules-materializedviews.html)

The main corrections are architectural, not conceptual:

- Do not mix category rollups and product rows in the same monthly fact table.
- Do not assume `order_lines.product_id` can be `NULL`; the current schema requires it.
- Do not store quantities as `Integer` without resolving the repo's existing decimal quantity behavior.
- Do not introduce month partitioning yet; current scale does not justify it.
- Do not rely on an imaginary scheduler or "Alembic cron-like job"; the app has no scheduler framework today.
- Do not duplicate reorder-point or customer-intelligence logic that already exists in `inventory` and `intelligence`.

The best v1 direction is:

1. Add immutable `product_name_snapshot` and `product_category_snapshot` to `order_lines`, and populate them on legacy import plus order confirmation.
2. Standardize one analytics date basis for sales facts, ideally `confirmed_at` or invoice/legacy confirmed date, not the current mixed reliance on `Order.created_at`.
3. Build one product-month aggregate table with a single grain and index strategy first, without partitioning.
4. Reuse that aggregate layer behind inventory and intelligence features before launching a broad new standalone module.
5. Defer the full SCD Type 2 `product_snapshots` table unless there is a clearly stated need to analyze product master changes independently from sales transactions, or else make it the actual conformed dimension referenced by the fact table.

### Key Findings

- Historical product snapshots on order lines are a strong and necessary addition.
- A monthly periodic snapshot fact is best practice, but Epic 20 currently defines the grain too loosely.
- The proposed `sales_monthly` shape mixes dimension text and mixed-grain rollups in a way best-practice sources discourage.
- PostgreSQL supports the nightly-refresh plus current-period-live pattern, but not the scheduling mechanism Epic 20 assumes.
- Inventory planning should extend the existing replenishment engine, not create a separate analytics-only planning logic.
- Customer buying behavior should extend Epic 19 rather than create a parallel customer analytics stack.

### Strategic Recommendation

Treat Epic 20 as an analytics-foundation epic, not as four independent feature quadrants. Ship the data foundation first, then compose the user-facing features out of shared services.

---

## Table of Contents

1. Research Introduction and Methodology
2. Current UltrERP Fit
3. Best-Practice Findings
4. Validation of Epic 20 by Design Area
5. Required Corrections to Epic 20
6. Recommended Development Direction
7. Risks and Open Questions
8. Research Methodology and Source Verification

## 1. Research Introduction and Methodology

### Research Significance

Epic 20 is not just another analytics page. It decides whether UltrERP will keep stretching live operational queries for historical sales analysis, or introduce a stable analytical layer that can support long-range product history, revenue diagnosis, and better replenishment decisions. Because the repo already has early analytics surfaces, this decision also determines whether the architecture converges or fragments.

### Research Methodology

- **Repository review:** Read `epic-20.md`, PRD context, current `intelligence`, `inventory`, `orders`, and `legacy_import` code paths.
- **Validation framework:** Compare Epic 20 to current best practice for fact-table grain, slowly changing dimensions, periodic snapshots, precomputed summaries, and inventory planning semantics.
- **Source preference:** Primary or official technical sources first.
- **Time period:** Sources accessed on 2026-04-15.

### Research Goals and Objectives

**Original Goals:** Investigate whether Epic 20 is the correct development direction for UltrERP, validate it against current analytics and inventory-planning best practices, and recommend how it should be implemented.

**Achieved Objectives:**

- Confirmed that the overall direction is valid.
- Identified the parts of the epic that align well with best practice.
- Identified the specific design mismatches that should be corrected before implementation.
- Produced a phased implementation direction that fits UltrERP's current architecture.

## 2. Current UltrERP Fit

### Existing Product and Customer Analytics Already Exist

UltrERP is not starting from zero. The `inventory` domain already has:

- product monthly demand,
- product sales history,
- top customer by product,
- supplier lookup,
- reorder-point calculation and planning metadata.

Relevant code: [backend/domains/inventory/routes.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/inventory/routes.py:475), [backend/domains/inventory/services.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/inventory/services.py:1715)

The `intelligence` domain already has:

- category trend analysis,
- customer product profile,
- risk signals,
- prospect gaps,
- market opportunities.

Relevant code: [backend/domains/intelligence/service.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/intelligence/service.py:223), [backend/domains/intelligence/service.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/intelligence/service.py:1464)

Inference from the repo: Epic 20 should become a shared aggregate substrate for these domains, not a separate second analytics stack.

### Current Data and Workflow Realities Matter

The legacy dataset is large enough to justify historical aggregation, but not obviously large enough to justify aggressive physical partitioning on day one. The repo research documents show `tbsslipx` at 133,419 sales headers and `tbsslipdtx` at 593,017 sales detail rows. Sources: [research/legacy-data/00-context.md](/Volumes/2T_SSD_App/Projects/UltrERP/research/legacy-data/00-context.md:13), [research/legacy-data/03-findings.md](/Volumes/2T_SSD_App/Projects/UltrERP/research/legacy-data/03-findings.md:95)

That is enough history to justify monthly rollups for repeated analytical queries. It is not automatically enough to justify partition management overhead for the aggregate tables themselves.

### Current Schema Constraints Conflict with Epic 20 Assumptions

Epic 20 assumes some order lines can have `product_id = NULL`, for example freight or discount lines. The current schema does not allow that.

- `OrderLine.product_id` is `nullable=False`. Source: [backend/common/models/order_line.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/common/models/order_line.py:35)
- Order creation requires `product_id` on every line. Source: [backend/domains/orders/schemas.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/orders/schemas.py:44)

Epic 20 also assumes integer quantities, while current order lines store quantity as `Numeric(18,3)`. Source: [backend/common/models/order_line.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/common/models/order_line.py:41)

There is also a deeper repo inconsistency: order confirmation converts `line.quantity` to `int(...)` when creating stock adjustments. Source: [backend/domains/orders/services.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/orders/services.py:392)

Inference: before Epic 20 locks `quantity_sold` to integer, UltrERP should explicitly decide whether sales quantity is semantically integral or decimal.

### Current Date Semantics Are Not Yet Clean

Epic 20 wants confirmed/shipped/fulfilled sales activity. That direction is sensible. But current `intelligence` queries use `Order.created_at` for time windows while filtering on countable statuses. Sources: [backend/domains/intelligence/service.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/intelligence/service.py:223), [backend/domains/intelligence/service.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/intelligence/service.py:1464)

Meanwhile, legacy import writes both `created_at` and `confirmed_at` from the historical invoice date. Source: [backend/domains/legacy_import/canonical.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/legacy_import/canonical.py:1558)

Inference: Epic 20 should explicitly define one analytics date basis and then use it consistently across new and existing analytics code.

### No General Scheduler Exists Yet

The FastAPI app bootstraps routers and startup seeding, but there is no scheduler or worker framework in `backend/app/main.py`. Source: [backend/app/main.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/app/main.py:31)

Inference: Epic 20 should not assume background cron infrastructure already exists.

## 3. Best-Practice Findings

### Fact Tables Need a Consistent Grain

Microsoft's star-schema guidance states that fact tables should contain dimension keys plus numeric measures and that fact tables should always load data at a consistent grain. Source: [Power BI star schema guidance](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema)

Kimball's periodic snapshot guidance says the row in a periodic snapshot fact table summarizes measurement events over a standard period and that the grain is the period, not the individual transaction. Source: [Kimball periodic snapshot fact tables](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/periodic-snapshot-fact-table/)

Implication for Epic 20:

- `sales_monthly` should have one explicit grain, such as `tenant x month x product_snapshot`.
- Category-only rollups should not share the same table with product-level rows.
- If category rollups are needed for performance, they should be a separate aggregate or a query/view on top of the product-grain fact.

### SCD Type 2 Is a Valid Pattern, but Only If You Actually Use It as a Dimension

Kimball and Microsoft both describe Type 2 SCD as a versioned dimension pattern that requires surrogate keys and validity-range columns so historical facts stay tied to the correct dimension version. Sources: [Kimball Type 2 SCD](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-2/), [Power BI star schema guidance](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema)

dbt's snapshot documentation reinforces the same idea: mutable rows need explicit version capture when historical state matters, and a timestamp-based strategy is preferred when a reliable `updated_at` exists. Source: [dbt snapshots](https://docs.getdbt.com/docs/build/snapshots)

Implication for Epic 20:

- A `product_snapshots` table is justified if UltrERP wants a real conformed product dimension with historical versions.
- If it exists, the monthly fact should reference the snapshot version, not only the live `product_id`.
- If the monthly fact is built entirely from `order_line` frozen text snapshots, then `product_snapshots` becomes optional for v1 and may be deferred.

### Text in Fact Tables Should Be Minimized

Kimball explicitly warns against letting text fields enter fact tables and recommends handling textual values through dimensions instead. Source: [Kimball Fistful of Flaws](https://www.kimballgroup.com/2003/10/fistful-of-flaws/)

Implication for Epic 20:

- Keeping `product_name_snapshot` and `product_category_snapshot` on `order_lines` is pragmatically acceptable because the operational transaction itself is the immutable event record.
- Duplicating the same descriptive text in `sales_monthly` should be treated as a convenience optimization, not the primary modeling strategy.
- If `product_snapshots` is retained, a `product_snapshot_id` foreign key is cleaner than using both `product_id` and multiple text descriptors in the fact.

### Precomputed Summaries Plus Live Current-Period Data Are a Supported Pattern

PostgreSQL's materialized-view documentation gives a sales-summary example that excludes the current date and refreshes the summary nightly, precisely because historical graphs often do not require fully current data. Source: [PostgreSQL materialized views](https://www.postgresql.org/docs/current/rules-materializedviews.html)

Implication for Epic 20:

- The proposed "historical months from summary, current month live" strategy is sound.
- The missing piece is the runtime execution model, not the analytical concept.

### Partitioning Should Be Earned, Not Assumed

PostgreSQL documentation says partitioning is usually worthwhile only when a table would otherwise be very large, with a rule of thumb that the table should exceed physical memory, and warns that too many partitions increase planning time and memory use. Source: [PostgreSQL table partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)

Implication for Epic 20:

- Month partitioning for `sales_monthly` and `customer_monthly` is premature for v1.
- Composite indexes and a disciplined grain should come first.
- Partitioning can be added later if observed query plans justify it.

### Inventory Planning Is More Than Historical Sales Velocity

Microsoft Business Central's planning guidance frames reorder-point logic around projected available inventory, lead time, time buckets, existing supply already on order, and order modifiers such as minimum order quantity and order multiple. Source: [Business Central reordering policies](https://learn.microsoft.com/en-us/dynamics365/business-central/design-details-handling-reordering-policies)

Implication for Epic 20:

- Product analytics can improve inventory planning.
- But a standalone "inventory planning API" should not become a second reorder engine that ignores `inventory_stock`, inbound supply, lead time settings, and the current `reorder_point` logic already implemented in UltrERP.
- The better approach is to feed better sales history into the existing replenishment model.

## 4. Validation of Epic 20 by Design Area

### Story 20.1: Product Snapshot on OrderLine

**Validation:** Strongly correct. This is the highest-value and lowest-regret part of the epic.

Why it fits:

- It directly fixes the historical-category drift problem.
- It aligns with the repo's existing snapshot-heavy patterns in invoices and legacy imports.
- It can be populated during both legacy import and order confirmation.

Repo fit:

- Legacy import already writes the resolved product description into `order_lines.description`. Source: [backend/domains/legacy_import/canonical.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/legacy_import/canonical.py:1811)
- Confirmation flow is the right runtime hook for operational orders. Source: [backend/domains/orders/services.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/orders/services.py:399)

Correction needed:

- Remove the assumption that `product_id` can be null unless the operational schema is changed first.

### Story 20.2: Product Dimension SCD Type 2

**Validation:** Best-practice-valid, but overcommitted for v1 as currently written.

Why it is valid:

- SCD2 is a standard way to preserve slowly changing descriptive attributes over time.

Why it is risky in current form:

- Epic 20 proposes both order-line frozen snapshots and a versioned product dimension, but does not specify which one is authoritative for the monthly fact.
- The story references `backend/domains/products/service.py`, but the repo currently has product read surfaces inside the `inventory` domain and no standalone `products` domain service file. Relevant repo evidence: [backend/domains/inventory/routes.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/inventory/routes.py:475)
- Public product create/update flows are not clearly established yet, so the hook points are underspecified.

Recommended correction:

- Either defer `product_snapshots` to phase 2, after order-line snapshots and the monthly fact exist.
- Or keep it, but make it a true dimension with a surrogate key used by the monthly fact.

### Story 20.3: Monthly Aggregation Tables

**Validation:** Correct direction, but the current schema should be redesigned.

Problems in the current epic shape:

- `sales_monthly` mixes product-level and category-level rows by making `product_id` nullable.
- It stores text descriptors in the fact table as primary design elements.
- It forces integer quantity without resolving source precision.
- It assumes partitioning and scheduler infrastructure too early.

Recommended v1 shape:

| Area | Epic 20 Current | Recommended v1 |
| --- | --- | --- |
| Grain | `tenant x year x month x product_id` plus category-only rows | `tenant x month x product_snapshot` only |
| Product key | `product_id` natural key | `product_snapshot_id` if SCD kept, else `product_id` plus frozen snapshot fields derived from order lines |
| Quantity | `Integer` | `Numeric(18,3)` until UltrERP explicitly standardizes integral-only sales units |
| Category rollups | mixed into fact | derive in query or separate aggregate later |
| Refresh | assumed scheduler | admin/CLI/on-demand refresh first |
| Partitioning | month partitioned | no partitioning initially; add indexes first |

### Story 20.4: Revenue Diagnosis API

**Validation:** Good feature, but should come after the fact layer and should use explicit support metadata.

This aligns with the repo's existing `intelligence` pattern of evidence-first outputs. It is a sensible consumer of the aggregate layer, not part of the foundation itself.

### Story 20.5: Inventory Planning API

**Validation:** Business need is real, but current scope should be reframed.

Why:

- UltrERP already has reorder-point calculation, lead-time handling, and product demand history in `inventory`.
- Best-practice inventory planning depends on projected inventory and supply conditions, not only trailing sales velocity.

Recommended correction:

- Recast this story as "analytics inputs and explainer overlays for replenishment."
- Reuse the existing `inventory` planning services instead of inventing a second planning model inside `product_analytics`.

### Story 20.6: Product Performance API

**Validation:** Strong candidate once the foundation exists.

This is a good analytics consumer of monthly product facts and order-line snapshots. It does not create deep architectural conflict by itself.

### Story 20.7: Customer Buying Behavior API

**Validation:** Directionally useful, but overlaps heavily with Epic 19.

Epic 20 itself says this story builds on Epic 19. The repo already has customer profile, risk, and category intelligence. This should be an extension of the shared intelligence layer, not a parallel customer analytics domain.

### Stories 20.8 and 20.9: Feature Gates and Tests

**Validation:** Correct and consistent with repo patterns.

The only correction is scope: these should follow the shared-domain decision. If the feature lands partly in `inventory` and partly in `intelligence`, the gating and tests should mirror that shape instead of assuming one isolated domain.

## 5. Required Corrections to Epic 20

1. Replace the mixed-grain `sales_monthly` design with a single-grain product-month fact.
2. Remove or explicitly redesign the `product_id = NULL` assumption for order lines.
3. Standardize one analytics date basis for commercial activity, preferably `confirmed_at` or invoice-confirmed date semantics.
4. Do not hardcode integer quantities until the repo-wide quantity precision decision is made.
5. Do not partition the monthly fact tables in v1.
6. Do not assume a background scheduler or Alembic-driven cron behavior exists.
7. Decide whether `product_snapshots` is truly a conformed SCD dimension or a deferred phase-2 capability.
8. Reuse `inventory` and `intelligence` services instead of duplicating them behind a fully separate `product_analytics` silo.

## 6. Recommended Development Direction

### Recommended Phase Plan

#### Phase 1: Historical Correctness First

- Add `product_name_snapshot` and `product_category_snapshot` to `order_lines`.
- Populate on legacy import.
- Populate on order confirmation if missing.
- Define and document the canonical analytics timestamp.

#### Phase 2: Shared Aggregate Foundation

- Create one monthly product sales fact table.
- Add CLI/admin refresh.
- Use live query fallback for current month.
- Add indexes, not partitions.

#### Phase 3: Reuse Existing Surfaces

- Point inventory monthly demand and similar product history views at the shared aggregate where appropriate.
- Extend intelligence/category/customer views with the shared aggregate when historical depth or performance requires it.

#### Phase 4: Higher-Level Analytics

- Revenue diagnosis
- Product performance
- Customer segment behavior
- Optional SCD2-backed master-data history views

### Proposed Target Architecture

| Layer | Responsibility |
| --- | --- |
| `orders` and `legacy_import` | write immutable sale-time product snapshots |
| shared analytics service or `product_analytics` foundation module | build and refresh monthly product facts |
| `inventory` | replenishment and operational planning using aggregate inputs plus current stock and supply |
| `intelligence` | customer, category, and opportunity reasoning using the same aggregate inputs |
| frontend | compose these surfaces into one experience without duplicating business logic |

### Bottom-Line Recommendation

Epic 20 should proceed, but only after being reframed from "new analytics silo" into "shared historical product-sales foundation." That is the correct development direction for UltrERP.

## 7. Risks and Open Questions

### Risks

- **Date semantics drift:** if Epic 20 uses `confirmed_at` but Epic 19 keeps using `created_at`, users will see conflicting results.
- **Quantity precision drift:** if aggregate tables use integers while orders allow decimals, reporting and stock logic may diverge.
- **Domain duplication:** if `product_analytics`, `inventory`, and `intelligence` each compute their own sales history, trust and maintainability will degrade.
- **Premature physical design:** partitioning and scheduling complexity may consume time without real benefit at current scale.

### Open Questions

- Should the canonical analytics event date be `confirmed_at`, invoice date, or a dedicated commercial activity date?
- Are fractional sales quantities actually allowed in the business domain, or is `Numeric(18,3)` only a schema convenience?
- Does UltrERP need to analyze product master changes independent of sales transactions in v1, or is sale-time freezing enough?
- Should the shared aggregate live in a new foundation module or inside the existing `intelligence` domain first?

## 8. Research Methodology and Source Verification

### External Sources Used

- [Power BI star schema guidance](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema)
- [Kimball periodic snapshot fact tables](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/periodic-snapshot-fact-table/)
- [Kimball Type 2 SCD](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-2/)
- [Kimball Fistful of Flaws](https://www.kimballgroup.com/2003/10/fistful-of-flaws/)
- [dbt snapshots](https://docs.getdbt.com/docs/build/snapshots)
- [PostgreSQL materialized views](https://www.postgresql.org/docs/current/rules-materializedviews.html)
- [PostgreSQL table partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [Business Central reordering policies](https://learn.microsoft.com/en-us/dynamics365/business-central/design-details-handling-reordering-policies)

### Repository Inputs Reviewed

- [epic-20.md](/Volumes/2T_SSD_App/Projects/UltrERP/_bmad-output/planning-artifacts/epic-20.md:1)
- [prd.md](/Volumes/2T_SSD_App/Projects/UltrERP/_bmad-output/planning-artifacts/prd.md:1)
- [backend/common/models/order_line.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/common/models/order_line.py:20)
- [backend/domains/orders/services.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/orders/services.py:392)
- [backend/domains/legacy_import/canonical.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/legacy_import/canonical.py:1551)
- [backend/domains/intelligence/service.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/intelligence/service.py:223)
- [backend/domains/inventory/services.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/inventory/services.py:1715)
- [backend/app/main.py](/Volumes/2T_SSD_App/Projects/UltrERP/backend/app/main.py:31)

### Confidence Assessment

- **High confidence:** historical snapshots on `order_lines`, monthly product fact necessity, no-v1 partitioning recommendation, and scheduler mismatch.
- **Medium confidence:** whether SCD2 should be deferred versus included immediately depends on how soon UltrERP needs master-data-history analysis beyond transactional reporting.
- **High confidence inference:** Epic 20 is the right direction only if it is reframed as a shared analytics foundation rather than a disconnected second analytics domain.
