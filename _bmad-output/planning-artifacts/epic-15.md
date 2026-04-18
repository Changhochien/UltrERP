## Epic 15: Legacy Data Import Pipeline

### Epic Goal

Operations and AI agents can stage, map, import, and validate legacy ERP data into UltrERP from file-backed extracts or a read-only live legacy DB through a repeatable CLI-backed workflow plus a task-specific skill that preserves lineage and exposes unresolved data-quality issues instead of hiding them.

### Stories

### Story 15.1: Raw Legacy Staging Import

As a migration operator,
I want extracted legacy CSVs loaded into a read-only staging schema,
So that every migration run starts from a reproducible source snapshot inside PostgreSQL.

**Acceptance Criteria:**

**Given** a verified legacy export set is available
**When** I run the staging import command
**Then** the pipeline creates or refreshes `raw_legacy` tables for the configured batch
**And** the staging workflow is exposed through a stable CLI command surface that later skill automation can call
**And** loads the source files with PostgreSQL-native bulk loading rather than row-by-row inserts
**And** records source table, source key, batch/run identifier, and import status for every staged row

### Story 15.2: Canonical Master Data Normalization

As a migration operator,
I want ROC dates, sentinel dates, and core master records normalized before canonical import,
So that downstream loads use consistent customer, supplier, product, and warehouse data.

**Acceptance Criteria:**

**Given** raw legacy tables are loaded
**When** the normalization step runs
**Then** ROC-encoded dates are converted to AD dates
**And** `1900-01-01` sentinel values are converted according to the documented import policy
**And** customer/supplier, product, and warehouse staging outputs are generated with deterministic legacy-to-canonical keys

### Story 15.3: Product Variant Mapping Workflow

As a data analyst,
I want unresolved legacy product variants managed through an explicit mapping workflow,
So that transaction history is preserved without claiming false product certainty.

**Acceptance Criteria:**

**Given** the migration pipeline encounters legacy product codes not present in the product master
**When** the mapping workflow runs
**Then** exact matches are auto-linked into `raw_legacy.product_code_mapping`
**And** unresolved codes are surfaced for analyst review with confidence metadata
**And** rows that remain unresolved are routed to an `UNKNOWN` placeholder product instead of being dropped

### Story 15.4: Canonical Historical Transaction Import

As a migration operator,
I want staged legacy headers and lines imported into UltrERP's canonical tables,
So that historical sales, purchase, inventory, and party data are available in the new system.

**Acceptance Criteria:**

**Given** normalized master data and product mappings are available
**When** I run the canonical import step
**Then** parties, products, warehouses, inventory, sales headers/lines, and purchase headers/lines load into the approved UltrERP schema
**And** every canonical record retains lineage back to the originating legacy table and source identifier
**And** unresolved variant rows use the documented fallback behavior rather than violating foreign keys

### Story 15.5: Migration Validation and Replay Safety

As a cutover owner,
I want migration runs to emit actionable validation reports and support safe reruns,
So that cutover is blocked by real data problems while repeat imports remain auditable.

**Acceptance Criteria:**

**Given** a migration batch completes
**When** validation runs
**Then** the system produces row-count reconciliation, orphan/mapping summaries, and severity-ranked discrepancy reports
**And** emits machine-readable artifacts that a reviewed agent skill can inspect without scraping prose only
**And** unresolved severity-1 issues block cutover readiness
**And** rerunning the same batch or cutoff window does not create duplicate canonical records

### Story 15.6: Agent-Invocable Legacy Import Skill

As an operator working with an AI agent,
I want the agent to invoke the reviewed legacy-import workflow through a dedicated skill backed by the CLI,
So that the workflow is reusable, guided, and safe across VS Code, Copilot CLI, and coding-agent contexts.

**Acceptance Criteria:**

**Given** the legacy import CLI exposes stable subcommands
**When** the agent loads the legacy-import skill
**Then** the skill tells the agent which CLI subcommands to run for staging, normalization, canonical import, and validation
**And** references supporting resources from the skill directory rather than duplicating the import logic in markdown alone

**Given** the skill is packaged for agent discovery
**When** the skill is installed in the repository
**Then** it lives in a supported skills directory with valid frontmatter (`name`, `description`, and invocation behavior)
**And** its directory name matches the skill name

**Given** the skill may invoke terminal commands
**When** tool permissions are configured
**Then** shell execution is left unapproved by default or tightly scoped to the reviewed CLI path
**And** destructive or high-impact import scopes still require explicit operator confirmation

### Story 15.9: Legacy Product Family Categorization Hardening

As a migration operator and intelligence owner,
I want legacy product families derived from code + cleaned name + stock_kind with auditable overrides,
So that imported products land in stable, sales-meaningful categories for downstream analytics instead of inheriting noisy source classifications.

**Acceptance Criteria:**

**Given** staged `tbsstock` rows expose raw `legacy_code`, raw `name`, `legacy_category`, and `stock_kind`
**When** the normalization step runs
**Then** `raw_legacy.normalized_products` preserves those raw fields separately
**And** derives a backend-owned low-cardinality product family using this priority: manual override, non-merchandise/accessory rules, code-prefix family rules, cleaned-name fallback, final fallback
**And** `legacy_category` remains provenance only instead of the canonical live category

**Given** a product family is derived or overridden
**When** normalized product rows are written
**Then** the system stores explicit provenance such as `category_source`, `category_rule_id`, and `category_confidence`
**And** low-confidence or fallback assignments can be surfaced for analyst review rather than silently treated as authoritative

**Given** a product family needs correction
**When** an operator reviews category assignments
**Then** the workflow uses an auditable override table keyed by `tenant_id + legacy_code`
**And** records approval source, approver, notes, and timestamp
**And** applies the override before any heuristic rule on rerun

**Given** normalized products are canonically imported
**When** `legacy-import canonical-import` runs
**Then** live `product.category` receives the derived low-cardinality family
**And** the product `legacy_master_snapshot` preserves raw provenance plus rule/confidence metadata
**And** existing Story 19 category analytics continue to read `Product.category` without requiring a new category table or foreign key contract

### Story 15.10: Live Legacy Source Compatibility Contract

As a migration operator and ERP engineer,
I want the live legacy source contract verified before we build against it,
So that dual-source staging uses a proven read-only connector and a stable row-serialization contract.

**Acceptance Criteria:**

**Given** `LEGACY_DB_*` settings are configured
**When** a compatibility probe runs against the live legacy PostgreSQL 8.2 source over Tailscale
**Then** the repo proves or rejects the chosen connector in read-only mode
**And** captures the table discovery, column metadata, and streaming-read behaviors needed by staging
**And** does not issue write operations to the legacy DB

**Given** the live-source connector contract is approved
**When** staging code consumes rows from the live source
**Then** the contract defines how `NULL`, numerics, strings, and date-like values are serialized for the shared raw loader
**And** preserves the text semantics needed by existing lineage fields such as `_legacy_pk`
**And** fails fast with explicit diagnostics for unsupported types or incompatible connector behavior

### Story 15.11: Dual-Source Staging Architecture Refactor

As a migration operator,
I want file and live source staging to share one orchestration path,
So that both source modes preserve the same batch semantics, control-table behavior, and `raw_legacy` contracts.

**Acceptance Criteria:**

**Given** file-based staging already exists
**When** the staging domain is refactored around source adapters plus a shared loader/orchestration layer
**Then** `legacy-import stage` remains backward compatible for manifest-backed CSV imports
**And** the shared orchestration owns attempt numbering, overlapping-table cleanup, raw-table recreation, lineage fields, validation hooks, and control-table persistence

**Given** either a file adapter or live adapter supplies discovered tables and row streams
**When** the shared orchestration stages them
**Then** `_batch_id`, `_source_row_number`, `_legacy_pk`, and partial rerun cleanup rules remain consistent with the current file-based behavior
**And** shared stage summaries and persisted source metadata use a source-agnostic descriptor that works for both file and live runs without leaking secrets

### Story 15.12: Live Legacy DB Stage CLI

As a migration operator,
I want a `legacy-import live-stage` command that stages selected tables from the live legacy DB over Tailscale,
So that I can run the migration pipeline without generating a SQL dump or extracted CSV set first.

**Acceptance Criteria:**

**Given** live DB settings are configured and the connector contract is approved
**When** I run `legacy-import live-stage --batch-id <id> [--table ...]`
**Then** the CLI discovers `public` tables or limits to the requested subset
**And** stages them into `raw_legacy` through the shared orchestration path
**And** prints the same operator-friendly batch/table summary shape as file-based `stage`

**Given** a live-stage run completes
**When** operator summaries, control tables, and docs are inspected
**Then** `legacy_import_runs` and `legacy_import_table_runs` capture non-secret live-source metadata sufficient for audit and validation
**And** `.env.example` plus the legacy-import skill document the `live-stage` command and required `LEGACY_DB_*` settings without embedding credentials

**Given** the live connection, table discovery, or table load fails
**When** the command aborts
**Then** the operator receives clear diagnostics that distinguish the failure type
**And** no partial committed stage snapshot is left behind for that batch attempt

### Story 15.13: Batch Rerun Idempotency At The Lineage Layer

As a migration operator,
I want rerunning the same batch to remain idempotent at the lineage layer,
So that repeat imports do not create duplicate `canonical_record_lineage` rows or corrupt run metadata.

**Acceptance Criteria:**

**Given** a batch has already been canonically imported
**When** I rerun the same batch
**Then** `canonical_record_lineage` contains exactly one lineage row per batch-scoped source record
**And** the latest run metadata updates safely without creating duplicate lineage entries

**Given** a different batch imports the same source identifiers
**When** that later batch completes
**Then** each batch keeps its own lineage record
**And** deduplication remains batch-scoped rather than cross-batch

### Story 15.14: Holding-Path Lineage Coverage

As a migration operator,
I want rows placed into `unsupported_history_holding` to create lineage immediately,
So that every source row remains traceable even when it is quarantined instead of canonically imported.

**Acceptance Criteria:**

**Given** a source row is routed into `unsupported_history_holding`
**When** the holding write occurs
**Then** a corresponding lineage record is created at hold time
**And** operators can distinguish holding-path lineage from canonically imported lineage

**Given** a held row is later drained into a supported canonical target
**When** the drain path succeeds
**Then** the lineage record updates to the canonical destination instead of creating a duplicate audit trail

### Story 15.15: Legacy Refresh Orchestrator

As a migration operator,
I want one reviewed command to run the full live refresh workflow in the correct order,
So that shadow refreshes are repeatable and do not depend on manual step sequencing.

**Acceptance Criteria:**

**Given** `LEGACY_DB_*`, tenant, and schema settings are configured
**When** I run the refresh orchestrator with a fresh batch id
**Then** it executes the approved workflow in order: `live-stage`, `normalize`, mapping/review prerequisites, `canonical-import`, `validate-import`, and the required stock follow-up scripts
**And** it records one structured run summary containing batch id, tenant id, schema, timing, exit status, and artifact paths

**Given** a step fails or validation/reconciliation exceeds the configured threshold
**When** the orchestrator aborts
**Then** it exits non-zero
**And** it does not promote the batch automatically
**And** the operator receives enough evidence to diagnose the failure from artifacts alone

### Story 15.16: Scheduled Shadow Refresh And Batch State Tracking

As a cutover owner,
I want the live refresh workflow to run on a schedule against a shadow lane,
So that the team can monitor freshness and migration quality without disturbing the working database.

**Acceptance Criteria:**

**Given** the refresh orchestrator exists
**When** a scheduled shadow refresh runs nightly or at another approved cadence
**Then** it generates an immutable shadow batch id
**And** writes the latest successful run metadata including batch id, completion time, and status to a durable state record
**And** produces a compact operator summary for validation status, blocker count, and reconciliation count

**Given** a scheduled shadow refresh runs
**When** it completes or fails
**Then** only the shadow lane is affected
**And** the team-facing working lane changes only through downstream promotion gate evaluation
**And** if the latest shadow batch is not eligible for promotion the previously promoted working batch remains active

### Story 15.17: Gated Automatic Promotion To The Working Lane

As a cutover owner,
I want the latest eligible shadow batch to be promoted into the working lane automatically when all promotion gates pass,
So that routine refreshes land without manual intervention while blocked batches leave the current working lane untouched.

**Acceptance Criteria:**

**Given** a shadow batch is the latest successful candidate and all promotion gates pass
**When** promotion evaluation runs
**Then** the system refreshes or switches the working lane to that batch atomically
**And** the system records the promoted batch id, previous promoted batch id, actor identity, promotion time, validation status, reconciliation gap count, threshold used, and source summary path

**Given** a candidate batch fails validation, exceeds reconciliation thresholds, still requires analyst review, or otherwise fails promotion policy
**When** promotion evaluation runs
**Then** promotion is refused
**And** the working lane remains on the previously promoted batch
**And** the refusal records the specific blocking gate and emits an operator-visible alert

**Given** the candidate batch is already the current working batch
**When** promotion evaluation runs again
**Then** the system exits idempotently without rebuilding the working lane or writing duplicate promotion history

### Story 15.18: Automated Promotion Gate Policy And Approved Corrections

As a cutover owner,
I want explicit automated promotion thresholds and a manual exception policy,
So that routine refreshes can auto-promote when drift is acceptable while out-of-policy batches pause for operator review.

**Acceptance Criteria:**

**Given** validation and reconciliation artifacts exist for a shadow batch
**When** promotion policy is evaluated
**Then** the system classifies the batch into explicit outcomes such as `eligible`, `blocked`, or `exception-required`
**And** the same policy is reused by scheduled refreshes, promotion evaluation, alerts, and operator summaries

**Given** reconciliation output reports gaps within the configured threshold and no other blocking gate is open
**When** policy is evaluated
**Then** the batch is eligible for automatic promotion

**Given** reconciliation output exceeds the configured threshold or another gate fails
**When** policy is evaluated
**Then** the batch is blocked from automatic promotion
**And** the system records which threshold or gate failed

**Given** correction proposals are generated
**When** operators decide to apply them
**Then** only explicitly approved proposal rows may be applied
**And** automated refresh jobs never auto-apply reconciliation corrections

### Story 15.19: Incremental Refresh And Auto-Promotion Watermark Contract

As a platform engineer,
I want a reviewed watermark and replay contract for incremental legacy refreshes that feed the same promotion gates as nightly batches,
So that we can move toward near-live updates without bypassing the automated safety model.

**Acceptance Criteria:**

**Given** the team wants refreshes more often than nightly
**When** the incremental sync design is implemented
**Then** each supported domain defines its watermark source, replay semantics, correction handling, and promotion-eligibility boundary explicitly
**And** sync state persists the last successful watermark, shadow batch metadata, and last promoted batch metadata for resumable reruns

**Given** incremental sync is active
**When** a run fails mid-stream or produces a blocked batch
**Then** the next run can resume safely from the last successful watermark
**And** the working lane remains on the previously promoted batch until a later eligible batch is produced

**Given** incremental sync remains lower confidence than the nightly baseline
**When** the system operates over time
**Then** a nightly full rebaseline remains available as the correctness backstop

### Story 15.20: Legacy Dump And Manual-Promotion Surface Retirement

As a platform maintainer,
I want obsolete dump-era and manual-promotion legacy surfaces retired behind explicit stability gates,
So that the repo defaults to the live gated refresh path and no longer carries duplicate operational workflows.

**Acceptance Criteria:**

**Given** the live refresh plus automatic promotion path has met agreed stability gates
**When** the deprecation story executes
**Then** the repository stops defaulting operators to dump-era sources or manual approval-driven promotion steps
**And** docs, skills, and commands point to the live gated refresh workflow as the default path

**Given** dump-era imports, manual promotion notes, or transitional remediation scripts still exist
**When** a cleanup pass is evaluated
**Then** a surface may only be removed after its logic is absorbed into the standard refresh, promotion, alerting, or exception workflow
**And** the cleanup records which fallback surfaces intentionally remain

**Given** archived CSV extracts or raw dumps still need retention for audit
**When** active repo cleanup happens
**Then** those artifacts are archived outside the working repo before deletion from default developer workflows

### Story 15.21: Canonical Source Resolution State Model Refactor

As a migration operator,
I want hold and drain state modeled explicitly outside `canonical_record_lineage`,
So that source-row transitions remain lossless, replay-safe, and crash-consistent as the legacy import pipeline evolves.

**Acceptance Criteria:**

**Given** a batch-scoped legacy source row is processed
**When** the import pipeline persists its current resolution
**Then** exactly one migration-owned state row exists for that source identity
**And** the row exposes explicit status such as `holding`, `resolved`, or `failed` instead of encoding state through `canonical_record_lineage.canonical_table`

**Given** a row is held, drained, retried, or manually repaired
**When** the transition completes
**Then** an append-only resolution event is recorded with batch, tenant, run, source identity, prior state, new state, and canonical or holding references
**And** prior transitions remain queryable rather than being overwritten in place

**Given** a held row drains into a canonical target
**When** the shared transition helper executes
**Then** the canonical write, current-state update, event append, and holding-row cleanup commit atomically in one transaction
**And** a failure in any step leaves the row in its previous consistent state

**Given** historical batches already contain `canonical_record_lineage` and `unsupported_history_holding` rows
**When** the migration and backfill run
**Then** the new state model is populated without losing tenant, batch, or run provenance
**And** ambiguous source-identity collisions fail loudly with actionable diagnostics instead of being silently merged

**Given** operators or validation code need to know whether a row is currently held or resolved
**When** they query the post-refactor system
**Then** they use the new source-resolution state surface instead of `canonical_table='__holding__'`
**And** no new sentinel `__holding__` lineage rows are written after cutover

---
