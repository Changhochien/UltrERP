## Epic 15: Legacy Data Import Pipeline

### Epic Goal

Operations and AI agents can stage, map, import, and validate legacy ERP data into UltrERP through a repeatable CLI-backed workflow plus a task-specific skill that preserves lineage and exposes unresolved data-quality issues instead of hiding them.

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

---

