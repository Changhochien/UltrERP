# Story 15.9: Legacy Product Family Categorization Hardening

Status: ready-for-review

## Story

As a migration operator and intelligence owner,
I want legacy product families derived from code + cleaned name + stock_kind with auditable overrides,
so that imported products land in stable, sales-meaningful categories without polluting downstream Story 19 category analytics.

## Acceptance Criteria

**AC1:** Normalization derives a backend-owned family category from raw product fields
**Given** staged `tbsstock` rows expose raw `legacy_code`, raw `name`, `legacy_category`, and `stock_kind`
**When** the `legacy-import normalize` phase runs
**Then** `raw_legacy.normalized_products` preserves those raw fields separately
**And** the pipeline derives a low-cardinality family category using this priority: manual override, non-merchandise/accessory rules, code-prefix family rules, cleaned-name fallback, final fallback
**And** `legacy_category` remains provenance only rather than the canonical live category
**And** examples such as `PC240` / `三角皮帶 C-240`, `SPA-1432 OH`, and `XPB-2410 進口` land in `V-Belts`
**And** examples such as `RL225*19M/M` / `225L*19M/M` land in `Timing Belts`

**AC2:** Category provenance and confidence are explicit
**Given** a product family is derived or overridden
**When** normalized product rows are written
**Then** the system stores `category_source`, `category_rule_id`, and `category_confidence`
**And** provenance distinguishes manual override, heuristic family match, accessory/non-merchandise exclusion, and final fallback
**And** confidence values are deterministic and documented well enough for operator review exports and validation artifacts

**AC3:** Overrides are auditable and applied before heuristics
**Given** a product family needs correction
**When** an operator reviews category assignments
**Then** the workflow uses an auditable override table keyed by `tenant_id + legacy_code`
**And** the normalization phase applies overrides before any heuristic rule
**And** approval source, approver, notes, and timestamp are stored explicitly
**And** the review loop follows the same CLI-backed operator pattern as Story 15.3 rather than ad hoc SQL updates

**AC4:** Canonical import preserves the new category contract without breaking current consumers
**Given** normalized products are canonically imported
**When** `legacy-import canonical-import` runs
**Then** live `product.category` receives the derived low-cardinality family
**And** `product.legacy_master_snapshot` preserves raw code, raw name, `legacy_category`, `stock_kind`, `category_source`, `category_rule_id`, and `category_confidence`
**And** existing inventory and Story 19 services continue reading `Product.category` as the same nullable string contract

**AC5:** Low-confidence and fallback rows are reviewable before analytics are treated as authoritative
**Given** normalization produces low-confidence or fallback category assignments
**When** the operator exports a review report or runs batch validation
**Then** those rows are listed in a machine-readable and operator-readable artifact
**And** the report highlights products assigned by fallback rules, low confidence, or excluded non-merchandise/accessory paths
**And** downstream analytics have an explicit basis for treating those categories as provisional until reviewed

## Tasks / Subtasks

- [x] **Task 1: Extend the normalized-product schema for derived-category provenance** (AC1, AC2, AC4)
  - [x] Keep raw `legacy_code`, `name`, `legacy_category`, and `stock_kind` unchanged in `raw_legacy.normalized_products`
  - [x] Add explicit derived-category metadata such as `category_rule_id` and `category_confidence`
  - [x] Provide an upgrade path for already-created `raw_legacy.normalized_products` tables instead of relying on `CREATE TABLE IF NOT EXISTS` alone

- [x] **Task 2: Replace the legacy-class-first shortcut with a rule engine built around code + cleaned name + stock_kind** (AC1, AC2)
  - [x] Add code normalization and cleaned-name helpers that strip spacing/import noise without destroying belt-series signals
  - [x] Implement stable family rules for `V-Belts`, `Timing Belts`, `Ribbed Belts`, `Variable-Speed Belts`, `Flat / Specialty Belts`, `Vehicle Belts`, `Belt Supplies`, `Non-Merchandise`, and `Other Power Transmission`
  - [x] Preserve `category_source` as explicit provenance and add deterministic `category_rule_id` values for every rule branch
  - [x] Replace the current regression that prefers `legacy_category` with tests that lock the new rule order and operator examples

- [x] **Task 3: Add an auditable override and review workflow** (AC2, AC3, AC5)
  - [x] Create Alembic-managed `raw_legacy` tables for category overrides and any needed review-candidate rows, patterned after Story 15.3 mapping tables
  - [x] Apply overrides by `tenant_id + legacy_code` before heuristic rules during normalization reruns
  - [x] Expose reviewed CLI commands or an equivalently safe operator path for exporting/importing category-review decisions
  - [x] Record approver, notes, timestamp, and approval source for every override

- [x] **Task 4: Preserve canonical and analytics compatibility** (AC4, AC5)
  - [x] Update canonical product snapshot/import code so live `product.category` receives the derived family while `legacy_master_snapshot` retains raw provenance plus confidence metadata
  - [x] Keep `Product.category` as the existing nullable string contract used by inventory and intelligence services
  - [x] Add a low-confidence/fallback artifact surfaced through validation output or a dedicated review export so Story 19 consumers know when categories are still provisional

- [x] **Task 5: Add focused regression coverage across normalization, canonical import, and category-consuming services** (AC1, AC2, AC4, AC5)
  - [x] Add unit coverage for the operator examples plus accessory/non-merchandise exclusions
  - [x] Add canonical snapshot tests for `category_rule_id` and `category_confidence`
  - [x] Add at least one targeted intelligence regression proving excluded/provisional categories do not silently pollute category trend consumers

## Dev Notes

### Repo Reality

- `backend/domains/legacy_import/normalization.py` already owns category derivation. `_derive_product_category()` currently returns `legacy_category` immediately when present, which is the exact behavior this story replaces.
- `backend/domains/legacy_import/normalization.py` already persists `category`, `legacy_category`, `stock_kind`, and `category_source` into `raw_legacy.normalized_products`, so this story extends the existing normalization contract rather than adding a parallel data-cleaning surface.
- `backend/domains/legacy_import/canonical.py` copies `normalized_products.category` into live `product.category` and preserves product provenance in `legacy_master_snapshot`.
- `backend/domains/intelligence/service.py` groups directly on `Product.category` for Story 19.2, Story 19.3, Story 19.5, and Story 19.6. `_is_excluded_category()` filters only after category strings already exist, so upstream category quality remains the controlling factor.

### Previous Story Intelligence

- Story 15.2 established `normalization.py` as the single authoritative cleanup boundary before canonical import. Reuse that boundary instead of adding category-cleaning heuristics inside intelligence services or one-off scripts.
- Story 15.3 already solved the operator-review pattern for uncertain legacy data via Alembic-managed `raw_legacy.product_code_mapping*` tables and CLI review export/import commands. Mirror that auditable design for category overrides instead of inventing a second approval path.
- Story 15.4 and `docs/legacy/canonical-import-target-matrix.md` confirm that `raw_legacy.normalized_products` is the supported source for live `product` rows; any category contract change must flow through canonical import and preserve rerun safety.

### Critical Warnings

- Do **not** keep `legacy_category` as the live `product.category` value; that preserves noisy source classification rather than the sales-meaningful family taxonomy Story 19 needs.
- Do **not** move belt-family logic into `backend/domains/intelligence/service.py`; that would fork category semantics between live product data and analytics queries.
- Do **not** add columns to `raw_legacy.normalized_products` without an explicit upgrade path for already-created schemas. The current bootstrap uses `CREATE TABLE IF NOT EXISTS` only.
- Do **not** change `Product.category` into a foreign key or new category table in this story. Story 19 and inventory code currently rely on the existing string-column contract.
- Do **not** treat fallback or low-confidence categories as authoritative in analytics without surfacing their provisional status.

### Implementation Direction

- Keep raw product provenance in the existing fields (`legacy_code`, `name`, `legacy_category`, `stock_kind`) and make the derived family category backend-owned.
- Prefer compatibility by keeping the final family value in `normalized_products.category` and live `product.category`, while adding supplemental provenance fields instead of renaming the consumer contract immediately.
- Use deterministic rule identifiers and bounded confidence values so review exports, validation artifacts, and later dashboards can explain why a product landed in a family.
- Follow the existing raw-schema migration pattern from Story 15.3 for persistent review tables. If prep-table columns change, add either Alembic coverage or idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` bootstrap logic so existing environments can rerun normalization safely.
- Expected operator flow after this story: `stage` -> `normalize` -> optional category review export/import -> `map-products` -> optional product mapping review -> `canonical-import` -> `validate-import`.

### Testing Requirements

- Focused current regression evidence: `cd backend && uv run pytest tests/domains/legacy_import/test_normalization.py -k "derive_product_category" -q`
- Required story validation should include:
  - `uv run pytest tests/domains/legacy_import/test_normalization.py tests/domains/legacy_import/test_canonical.py tests/domains/legacy_import/test_cli.py -q`
  - targeted tests for any new category-review module or CLI commands
  - one focused intelligence regression in `tests/domains/intelligence/test_service.py` if provisional/excluded category behavior changes for Story 19 consumers

### Project Structure Notes

- Primary implementation surface: `backend/domains/legacy_import/`
- Downstream compatibility surface: `backend/domains/intelligence/`, `backend/common/models/product.py`, `backend/domains/inventory/services.py`
- Migration and operator-doc surfaces: `migrations/versions/`, `docs/legacy/`, `.agents/skills/legacy-import/command-map.md`

### References

- `_bmad-output/planning-artifacts/epic-15.md` - Epic 15 legacy-import foundation
- `_bmad-output/implementation-artifacts/15-2-canonical-master-data-normalization.md` - normalization boundary and rerun constraints
- `_bmad-output/implementation-artifacts/15-3-product-variant-mapping-workflow.md` - auditable review-loop pattern
- `_bmad-output/implementation-artifacts/19-2-category-trend-radar.md` - Story 19 category consumers and support-floor contract
- `_bmad-output/implementation-artifacts/19-6-market-opportunities.md` - dependency on stable category-cleaning rules
- `docs/legacy/migration-plan.md` - migration policy and unknown/fallback handling
- `docs/legacy/canonical-import-target-matrix.md` - `raw_legacy.normalized_products` as canonical source
- `research/legacy-data/01-survey-memo.md` - catalog shape and product-code examples
- `backend/domains/legacy_import/normalization.py` - current category derivation and normalized-products schema
- `backend/domains/legacy_import/canonical.py` - product snapshot and canonical import
- `backend/domains/intelligence/service.py` - Story 19 category consumers
- `migrations/versions/0d4102e847f6_add_product_code_mapping_tables.py` - Alembic pattern for auditable `raw_legacy` review tables

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Debug Log References

- Investigated current category derivation path and canonical import contract on 2026-04-14.
- Verified the initial rule-engine slice with `cd backend && uv run pytest tests/domains/legacy_import/test_normalization.py tests/domains/legacy_import/test_category_review.py tests/domains/legacy_import/test_cli.py tests/domains/legacy_import/test_canonical.py tests/domains/legacy_import/test_validation.py tests/domains/intelligence/test_service.py -q` (`68 passed`).
- Verified downstream canonical and validation propagation with `cd backend && uv run pytest tests/domains/legacy_import/test_canonical.py tests/domains/legacy_import/test_validation.py -q` (`30 passed`).
- Verified the final heuristic and analytics slice with `cd backend && uv run pytest tests/domains/legacy_import/test_normalization.py tests/domains/intelligence/test_service.py -q` (`38 passed`).
- BMAD post-implementation code review added regression coverage for explicit `SPA-1432 OH` / `XPB-2410 進口` V-Belt handling plus category-review import safety, then reran `cd backend && uv run pytest tests/domains/legacy_import/test_normalization.py tests/domains/legacy_import/test_category_review.py -q` (`19 passed`).
- Targeted Ruff on the touched review-fix files passed: `cd backend && uv run ruff check domains/legacy_import/normalization.py domains/legacy_import/category_review.py tests/domains/legacy_import/test_normalization.py tests/domains/legacy_import/test_category_review.py`.
- Final Story 15.9 regression validation passed with `cd backend && uv run pytest tests/domains/legacy_import/test_normalization.py tests/domains/legacy_import/test_category_review.py tests/domains/legacy_import/test_cli.py tests/domains/legacy_import/test_canonical.py tests/domains/legacy_import/test_validation.py tests/domains/intelligence/test_service.py -q` (`85 passed`).
- Smoke-checked Alembic runtime state with `cd backend && uv run alembic -c ../migrations/alembic.ini current`, `... heads`, and `... upgrade head`; the database advanced cleanly from `1c2d3e4f5a6b` to `9b2f3c4d5e6f` and now reports the new head.

### Completion Notes List

- Story is intentionally placed in Epic 15 because the authoritative logic belongs to legacy normalization and canonical import, while Story 19 only consumes `Product.category`.
- Story preserves current live consumer contracts while tightening category derivation, provenance, and operator-review safety.
- Story reuses the established Story 15.3 pattern for auditable review tables and CLI-backed analyst workflows.
- Normalization now applies manual category overrides before heuristics, emits deterministic `category_rule_id` and `category_confidence`, and persists provisional rows to `raw_legacy.product_category_review_candidates` for analyst export/import.
- BMAD code review found and fixed the real operational gap in the review loop: imported category decisions now rerun normalization for the batch so `normalized_products` and downstream canonical/validation flows stop serving stale pre-review categories.
- Category-review import now rejects stale or unknown review-candidate rows and rejects `keep_current` entries that silently change category, closing the CSV safety gaps surfaced during review.
- AC1 is now explicitly locked by regression coverage for `SPA-1432 OH` and `XPB-2410 進口`, and the V-Belt prefix rules now include the `SPA` / `SPB` / `SPC` / `SPZ` / `XPA` / `XPB` / `XPZ` families instead of relying on incidental token matching.
- Canonical import now preserves `legacy_category`, `stock_kind`, `category_source`, `category_rule_id`, and `category_confidence` in `product.legacy_master_snapshot`, while validation emits `Category Review` JSON/Markdown artifacts and warns on provisional assignments.
- The only evidence-backed Belt Supplies heuristic added in this story is the conservative `PPPP*` / `皮帶現場接頭` path observed in the staged corpus; broader supplies taxonomy remains intentionally review-driven until stronger corpus evidence exists.

### File List

- `backend/domains/legacy_import/normalization.py`
- `backend/domains/legacy_import/category_review.py`
- `backend/domains/legacy_import/cli.py`
- `backend/domains/legacy_import/canonical.py`
- `backend/domains/legacy_import/validation.py`
- `backend/tests/domains/legacy_import/test_normalization.py`
- `backend/tests/domains/legacy_import/test_category_review.py`
- `backend/tests/domains/legacy_import/test_cli.py`
- `backend/tests/domains/legacy_import/test_canonical.py`
- `backend/tests/domains/legacy_import/test_validation.py`
- `backend/tests/domains/intelligence/test_service.py`
- `migrations/versions/9b2f3c4d5e6f_add_product_category_review_tables.py`
- `_bmad-output/implementation-artifacts/15-9-legacy-product-family-categorization-hardening.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`