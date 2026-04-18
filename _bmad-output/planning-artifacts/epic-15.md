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

---
