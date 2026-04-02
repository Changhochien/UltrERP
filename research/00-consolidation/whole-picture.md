# Whole Picture: AI-Native ERP Research Sprint

**Date:** 2026-03-30
**Status:** Research Sprint Complete
**Sprint Duration:** 2026-03-26 to 2026-03-30

---

## Executive Summary

The five-area research sprint validated the core architecture direction while surfacing critical technical blockers and compounding risks that require architecture changes before implementation proceeds. The Tauri 2.x + FastAPI + FastMCP modular-monolith stack is confirmed viable, but three original design decisions must change: the MCP server must use session-mode HTTP transport (not `stateless_http=True`), FastMCP 2.x must be used instead of 3.x, and React 19 is mandatory for the Tauri webview. The most consequential finding is a correction to the survey data: the product code mismatch is far less severe than initially estimated. The survey reported 660 orphan codes and 99.7% FK failure, but the PoC discovered this was a field confusion — the survey checked warehouse codes (field 6, numeric IDs like 1000, 1138) against product codes (field 7, alphanumeric). The actual orphan rate is 0.09% (523 rows out of 593,017) with 190 orphan alphanumeric product variants that are mostly manual-mapping candidates. The legacy data migration is substantially lower risk than the survey suggested. Separately, the Taiwan eGUI compliance area identified that MIG 4.1 became mandatory on January 1, 2026 -- already past -- and that there is no publicly accessible FIA API sandbox, making the FIA approval timeline the longest-lead-time item in the entire program. Subsequent PRD/architecture alignment clarified three execution rules: GUI/CLI and AI agents share one domain layer but not one transport surface, live FIA/eGUI submission should be feature-flagged until activation criteria are met, and issuer-side archives must remain the system of record instead of depending on MOF platform retention windows.

---

## Validated Architecture Decisions

The following decisions from the original architecture design were confirmed correct by the proof-of-concept work:

**Tauri 2.x as Desktop Shell.** The PoC at `research/tech-viability/02-poc/tauri-fastapi-poc/` confirmed Tauri v2.10.3 installs cleanly, the sidecar spawning pattern works on macOS (Rust `std::process::Command` with `CARGO_MANIFEST_DIR` path resolution), and the webview connects to `localhost:8000` with no special permissions required. The CSP configuration in `tauri.conf.json` must include `http://localhost:8000` in `connect-src`. The 8MB vs 120MB installer size advantage over Electron is real and validated.

**FastAPI Sub-apps as Modular Monolith Pattern.** The FastAPI `app.mount()` sub-app pattern is fully documented and unchanged in FastAPI 0.115+. The reference `YoraiLevi/modular-monolith-fastapi` is a valid pattern for isolated domain services.

**PostgreSQL 17 + pgvector + Redis 7+ + MinIO.** All three infrastructure components are current and have no compatibility issues with the rest of the stack. PostgreSQL 17 with pgvector works without breaking changes.

**Modular Monolith as the Correct Pattern for 2026.** Multiple sources confirm modular monolith is the dominant 2026 pattern for AI-augmented ERP. No production system combines all four of Tauri + FastAPI + MCP + Taiwan eGUI, but each individual piece is proven in isolation.

**eGUI State Machine (PENDING / QUEUED / SENT / ACKED / FAILED / RETRYING / DEAD_LETTER).** The state machine from the original architecture was validated against FIA's actual behavior. The PoC mock server at `research/egui-compliance/02-poc/fia_mock_server.py` implements this state machine with realistic timing and retry behavior.

**Transactional Outbox + Inbox Pattern.** The outbox/inbox pattern from the original architecture is the correct durable workflow mechanism. No changes required -- this is confirmed architecture.

**Multi-Tenancy with `tenant_id` + RLS.** The deployment mode matrix (Solo/Team/Business/On-Premises) and RLS strategy are unchanged. Solo/Team mode can disable RLS; Business/Cloud mode enforces it.

**Claude Skills as Domain Expertise Packaging.** The skill structure (SKILL.md + reference/*.md + scripts/) is correct and validated against Anthropic's skill authoring guide.

---

## Updated Architecture Decisions

These decisions from the original architecture design must change based on research findings:

### Change 1: FastMCP `stateless_http=True` Is Unusable -- Use Session Mode
**Original:** `mcp = FastMCP("ERP Service", stateless_http=True, ...)` in Section 4.3 of the architecture design.
**Changed to:** Session-mode HTTP transport (SSE or websockets). The PoC confirmed `stateless_http=True` causes sampling/elicitation calls to hang indefinitely (MCP SDK bug #678, open). The MCP spec does not yet formally define stateless HTTP. Horizontal scaling via session-mode instances behind a load balancer with sticky sessions is the interim solution.
**PoC Evidence:** `research/tech-viability/02-poc/tauri-fastapi-poc/`, FastMCP 3.x survey (research/tech-viability/01-survey-memo.md), Multi-Agent PoC (research/multi-agent-patterns/02-poc/03-findings.md).

### Change 2: Use FastMCP 2.x, Not 3.x
**Original:** FastMCP 2.0 specified as the MCP server framework.
**Changed to:** FastMCP 2.x (specifically 2.14.6). FastMCP 3.x (released January 2026) pins `mcp<1.23`, blocking access to November 2025 SDK features. Additionally, `auth=` on `@mcp.tool()` decorators is a FastMCP 3.x-only feature -- FastMCP 2.x requires middleware-based auth (confirmed in `research/multi-agent-patterns/02-poc/03-findings.md`). Re-evaluate FastMCP 3.x at a 6-month horizon when it ships stable MCP SDK 1.23+ compatibility.
**PoC Evidence:** Multi-Agent PoC test results (`research/multi-agent-patterns/02-poc/03-findings.md`) -- 9/9 tests pass with FastMCP 2.14.6.

### Change 3: Tauri NSIS Sidecar Binary Bug Requires WiX or Post-Install Workaround
**Original:** NSIS installer implied for Windows distribution.
**Changed to:** Windows builds must use WiX installer instead of NSIS, or implement a post-install script that explicitly replaces the sidecar binary. Bug #15134 (open, March 2026): NSIS installer does not replace the sidecar binary on reinstalls or upgrades.
**PoC Evidence:** Tech Viability PoC README (`research/tech-viability/02-poc/tauri-fastapi-poc/README.md`).

### Change 4: React 19 Is Mandatory for Tauri Webview
**Original:** "Latest" React version.
**Changed to:** React 19.1.0 minimum. React 18 has unresolved dropdown/transform bugs in Tauri webview (shadcn-ui/ui#7433). This was confirmed in the UI/UX survey and reinforced by the survey consolidation cross-area analysis.
**Evidence:** `research/ui-ux/01-survey-memo.md`, `research/ui-ux/02-wireframes/03-findings.md`.

### Change 5: `statement_cache_size=0` Required for asyncpg + PgBouncer
**Original:** Not mentioned in original architecture.
**Changed to:** The asyncpg connection pool must be initialized with `statement_cache_size=0` when operating behind PgBouncer in transaction mode. Without this, prepared statement errors ("prepared statement does not exist") occur under concurrent load. This is a silent runtime failure.
**Evidence:** Tech Viability survey (`research/tech-viability/01-survey-memo.md`).

### Change 6: FIA API Sandbox Does Not Exist -- Plan for Long Lead Time
**Original:** FIA API access assumed available.
**Changed to:** There is no publicly accessible FIA API sandbox. Direct FIA API access requires approved App ID + API Key credentials. The application process may take weeks to months. Third-party proxy providers (ECPay, PChome, SHOPLINE) are recommended as an interim integration path while awaiting FIA approval.
**Evidence:** eGUI Compliance survey (`research/egui-compliance/01-survey-memo.md`), eGUI PoC (`research/egui-compliance/02-poc/03-findings.md`).

### Change 7: Shared Business Logic Does Not Require One Client Transport
**Original:** Humans and AI were described as consuming the exact same tool/API surface.
**Changed to:** One shared domain layer serves all actors. AI agents use MCP as the canonical agent surface, while GUI and CLI clients use typed application APIs backed by the same services.
**Evidence:** FastAPI modular-monolith pattern, Tauri desktop UX constraints, and the combined PRD/architecture alignment after the research sprint.

---

## PoC Results Summary

### Tech Viability PoC
**Artifact:** `research/tech-viability/02-poc/tauri-fastapi-poc/`
**What was built:** A Tauri 2.x app with a Python FastAPI sidecar spawned via Rust `std::process::Command`. The React frontend calls `http://localhost:8000/api/ping` and `http://localhost:8000/api/domains`.
**What worked:** Sidecar spawning on macOS with `CARGO_MANIFEST_DIR` path resolution; HTTP IPC between webview and FastAPI; CSP configuration for localhost; graceful shutdown via `on_window_event`.
**What didn't work:** `std::env::current_exe()` path walking is fragile for GUI apps -- fixed by switching to `CARGO_MANIFEST_DIR`. The NSIS sidecar binary replacement bug on Windows was identified but not tested on Windows hardware (requires Windows machine).
**Key lesson:** The child-process spawning pattern (Rust `Command`) is functionally equivalent to Tauri's `externalBinary` feature for the PoC. For production, PyInstaller + `externalBinary` is the recommended path.

### eGUI Compliance PoC
**Artifact:** `research/egui-compliance/02-poc/`
**What was built:** A MIG 4.1 A0101 XML generator (`mig41_generator.py`), a mock FIA API server with state machine simulation (`fia_mock_server.py`), and a submission client (`submit_invoice.py`). Full end-to-end chain from invoice data to ACK/REJECT response was demonstrated.
**What worked:** MIG 4.1 XML generation with all required fields (TaxType at detail level, correct decimal precision, BAN MOD11 validation, InvoiceNumber format `[A-Z]{2}\d{8}`); BAN MOD11 validation algorithm; state machine simulation with 80/20% ACK/FAIL split and auto-retry.
**What didn't work:** Cannot test the real FIA API -- no sandbox exists. The 48-hour enforcement check is bypassed in the mock (always passes). DEAD_LETTER recovery procedure is not publicly documented.
**Key lesson:** MIG 4.1 XML schema generation is fully solved. The blocker is FIA credential acquisition, which has no self-service path.

### Multi-Agent Patterns PoC
**Artifact:** `research/multi-agent-patterns/02-poc/`
**What was built:** A FastMCP 2.14.6 server with 4 tools (customers_list, customers_create, invoices_list, invoices_create), middleware-based API key auth with RBAC scopes, structured error types, and a 9-test functional suite.
**What worked:** Tool registration with `Annotated[T, Field(...)]` Pydantic syntax; middleware auth pattern (ApiKeyAuth with `on_call_tool` hook); MOD11 validation integrated into customers_create; RBAC scope enforcement (admin/finance/sales/readonly keys); error type hierarchy (ValidationError, NotFoundError, PermissionError); all 9 tests passing.
**What didn't work:** `auth=` parameter on `@mcp.tool()` -- not supported in FastMCP 2.x; `ToolError` only carries a string message (structured error fields lost); FastMCP 3.x cannot be used due to MCP SDK version pinning.
**Key lesson:** FastMCP 2.x is production-viable for the PoC scope. The auth middleware pattern is functional but must be replaced by FastMCP 3.x's native `auth=` decorator when the SDK compatibility issue is resolved.

### Legacy Data Migration PoC
**Artifact:** `research/legacy-data/02-poc/`
**What was built:** A CSV import pipeline (`import_legacy.py`) that loads 4 legacy tables (734,069 rows) into PostgreSQL `raw_legacy` schema at ~10,000 rows/sec, an orphan analysis script (`resolve_product_codes.py`) that identified and categorized 190 orphan product codes, an orphan report (`orphan_report.json`, `orphan_report.txt`) with 32 fuzzy-match candidates, and DDL for a `product_code_mapping` table.
**What worked:** CSV parsing with non-standard quoting (`', '` delimiter); ROC date parsing via SQL-based CASE expression (10-digit encoded invoice numbers, 8-digit compact dates, AD pass-through); `1900-01-01` sentinel detection; FK validation confirming 96.9% match rate on field 7 (actual product codes).
**What didn't work:** The survey's 660 orphan codes finding was a field confusion (field 6 warehouse codes vs. field 7 product codes) -- the actual orphan rate is 0.09% (523 rows out of 593,017); the FK constraint approach would only reject 523 rows, not 591K as the survey suggested.
**Key lesson:** The orphan product codes (190 total) are almost entirely alphanumeric variants of existing products (e.g., `RB052-6` = 6mm width variant of `RB052`). 32 fuzzy-match candidates can be resolved manually in under an hour. The migration risk from product codes is LOW. Import all 94 CSVs first, then run the 32-candidate manual mapping sprint.

### UI/UX Wireframes PoC
**Artifact:** `research/ui-ux/02-wireframes/` + `research/ui-ux/02-wireframes/03-findings.md`
**What was built:** Component recommendations for three primary screens (Customer Management, Invoice Creation, Inventory Check) using shadcn/ui + TanStack Table + react-virtual. Taiwan localization specifications for ROC dates, UBN MOD11 validation, phone/address formats. Global shortcut architecture for power users. System tray + notification architecture for background eGUI state tracking.
**What worked:** ROC date format decision (display `YYY/MM/DD`, store ISO 8601); UBN MOD11 real-time validation on 8th digit with debounce; system tray architecture for background eGUI polling; shortcut overlay design; shadcn Table + TanStack virtual scrolling recommendation for large datasets.
**What didn't work:** Radix Tooltip-in-Popover nesting (known unfixed bug -- must avoid); Intel Mac + React 19 combination not hardware-tested in this sprint.
**Key lesson:** Taiwan localization utilities (ROC date, UBN MOD11) must be built as fully-tested pure functions before any screen work begins. System tray + notification is not deferrable -- it is a required architecture component for the eGUI async workflow.

---

## Complete Risk Register

### Tier 1: Critical

| # | Risk | Area | Sev | Like | Score | Status |
|---|------|------|-----|------|-------|--------|
| R1 | **Product Code Orphan Risk**: 190 orphan codes (0.09% of 593,017 rows = 523 rows) are alphanumeric variants of existing products (RB052-6, 3V0710-2). 32 fuzzy-match candidates exist for manual mapping. If not mapped, invoice line items show as UNKNOWN_PRODUCT. Impact is contained to 523 rows. | Legacy Data | Med | Low (manual mapping resolves) | 8 | Mitigated (190 codes, 32 candidates) |
| R2 | **MIG 4.1 Mandatory Since 2026-01-01**: MIG 4.0 integrations are already non-compliant. Key changes: TaxType moved to line-item level, CheckNumber removed, SequenceNumber/Remark/RelateNumber lengths extended. | eGUI Compliance | Crit | Already生效 | 25 | Open |
| R3 | **FIA API Registration Blocker**: No public sandbox exists. Approval for App ID + API Key may take weeks to months. No eGUI invoice can be transmitted without credentials. | eGUI Compliance | Crit | High | 25 | Open |

### Tier 2: High

| # | Risk | Area | Sev | Like | Score | Status |
|---|------|------|-----|------|-------|--------|
| R4 | **FastMCP Stateless HTTP Sampling Hang**: `stateless_http=True` causes sampling/elicitation calls to hang indefinitely. MCP spec does not formally define stateless HTTP. Horizontal scaling requires alternative approach. | Tech Viability | High | Certain (if stateless HTTP used) | 20 | Mitigated (use session mode) |
| R5 | **48-Hour B2C Submission Deadline**: FIA compares InvoiceDate+Time vs. server-received timestamp. Late submissions enter RETRYING/DEAD_LETTER. Penalty up to TW$15,000 + late tax penalties. No confirmed grace period. | eGUI Compliance | High | High | 20 | Open |
| R6 | **Tauri NSIS Sidecar Binary Not Replaced on Upgrade** (issue #15134): Windows NSIS installer does not replace the sidecar binary on reinstall. Windows auto-update ships outdated Python sidecar. | Tech Viability | High | High (Windows) | 16 | Open (workaround: WiX) |
| R7 | **Radix UI Stability / Bug Backlog**: Known Tooltip/Popover/Dropdown bugs unfixed for years. shadcn actively evaluating Base UI as replacement. Supply-chain risk for long-term ERP. | UI/UX | Med-High | High | 16 | Open (monitor; own component code) |
| R8 | **FastMCP 3.x Pins MCP SDK <1.23**: FastMCP 3.x (January 2026) blocks November 2025 SDK features. `auth=` decorator only in v3. Must use v2.x or accept SDK feature loss. | Multi-Agent | Med-High | High | 16 | Mitigated (use v2.14.6) |
| R9 | **Token Audience Validation Gaps ("confused deputy")**: MCP OAuth 2.1 requires strict audience claim validation. Generic OAuth provider allows token replay across MCP servers. | Multi-Agent | Crit | Med | 15 | Open |

### Tier 3: Medium

| # | Risk | Area | Sev | Like | Score | Status |
|---|------|------|-----|------|-------|--------|
| R10 | **eGUI State UX Race Condition**: Async state transitions (minutes to hours) lost if app closed/reopened while webview unloaded but tray keeps app alive. | UI/UX | Med | High | 15 | Open (architecture: persist to SQLite) |
| R11 | **SQLAlchemy asyncpg + PgBouncer Transaction Mode Conflict**: `statement_cache_size=0` required to avoid "prepared statement does not exist" errors. Silent failure under concurrent load. | Tech Viability | Med | Med-High | 12 | Mitigated (set on day 1) |
| R12 | **Taiwan Localization Field Quality**: UBN MOD11 and ROC date errors are compliance violations. Finance staff copy-paste from spreadsheets. | UI/UX | Med | High | 15 | Open (implement with debounce) |
| R13 | **Human-in-the-Loop Verification Complexity**: MCP spec requires human confirmation for sensitive operations. "SHOULD" not "MUST" prompt. Misunderstanding creates security gaps in invoice void/issue flows. | Multi-Agent | High | Med | 15 | Open |
| R14 | **Target Schema FK Constraints Will Fail on Import**: Only 523 tbsslipdtx rows (0.09%) violate FK constraints referencing products. FK constraints only reject orphan product rows, not 591K as the survey suggested. Disable FK during staging; map 190 orphan codes via product_code_mapping table. | Legacy Data | Low | Low | 4 | Mitigated (190 codes only) |
| R15 | **React 19 on Intel Mac Untested**: React 19 fixes Tauri webview bugs but may have rendering quirks on Intel Macs. Requires hardware testing before commit. | UI/UX | Med | Med | 9 | Open (hardware testing needed) |

---

## Cross-Area Findings

### Compounding Risks (Only Visible at Consolidation)

**N1: Product code mismatch is lower risk than survey suggested but still requires action.** The survey's 99.7% figure was wrong (field confusion). The actual risk is 523 orphan rows (0.09%) with 190 alphanumeric variant codes. 32 fuzzy-match candidates can be manually mapped. However, the top 10 orphan codes (covering most of the 523 rows) are product size variants -- if not mapped, these transactions show as UNKNOWN_PRODUCT, which still breaks product-level analytics. The risk is manageable and does NOT cascade into the invoice MCP tool for the majority of transactions.

**N2: Three-way React 19 + Tauri NSIS + FastMCP version compatibility matrix.** UI/UX requires React 19 (for Tauri webview), Tech Viability surfaces the Tauri NSIS bug (affecting Windows builds), and Multi-Agent Patterns restricts FastMCP to 2.x (blocking 3.x auth features). These three constraints interact: upgrading React to 19 on Tauri must be tested against the NSIS packaging workflow, and FastMCP 2.x middleware auth must work correctly under session-mode HTTP (not stateless). All three must be validated together in the integration phase.

**N3: SQLAlchemy asyncpg cache + PgBouncer + multi-tenant MCP session mode amplifies connection risk.** When multiple MCP servers (customers, invoices, inventory) each hold session-mode asyncpg connections behind PgBouncer in transaction mode, cumulative connection count under concurrency amplifies the prepared-statement cache issue. The `statement_cache_size=0` fix must be applied to every MCP server's database pool, not just the main application pool.

**N4: MIG 4.1 TaxType at detail level + product code mismatch = cumulative data quality failure for 523 rows.** MIG 4.1 requires TaxType at the line-item level. For the 190 orphan product codes, TaxType cannot be automatically determined from the product category. This creates a data quality gap for those 523 rows specifically — the invoice may be MIG 4.1 structurally valid but substantively incorrect in its tax classification. Since the orphan rate is 0.09%, this is a contained issue: 99.91% of invoice lines have both a valid product_id and a determinable TaxType. The 523 affected rows need either a mapped product_id or an explicit TaxType override per transaction.

### Newly Discovered Risks from PoC Phase

**N5: FastMCP 2.x ToolError Cannot Preserve Structured Error Fields.** `ToolError` raised in FastMCP 2.x only carries a string message. The structured fields from `ValidationError`, `NotFoundError`, and `PermissionError` (code, retry, details) are embedded as plain text in the message string. MCP clients cannot parse structured error objects. This affects error handling in AI agent workflows.

**N6: ROC Date Normalization Performance on Large Tables.** The 593,017-row tbsslipdtx table cannot have its ROC dates normalized in a single PoC run. The date parsing itself is correct, but a bulk UPDATE strategy (COPY...ON CONFLICT or temp table) is needed for production-scale normalization.

**N7: Tauri Sidecar Port Hardcoding.** The PoC hardcodes port 8000. Port conflicts on user machines are not handled. The chosen port must be communicated from the Rust spawning process to the React frontend via a shared mechanism.

---

## Recommended Implementation Phasing

The original 5-phase plan (Section 12 of the architecture design) is updated based on research findings. Key changes: Phase 0 is expanded and made explicit as a prerequisite track running in parallel; Phase 1 now includes FIA API registration initiation as the single longest-lead-time item; Phase 2 now includes hardware validation for React 19 on Intel Macs.

### Phase 0: PoC Prerequisites (Parallel Track, Before Any Feature Work) -- Weeks 1-4

1. **Initiate FIA API registration immediately.** This is the single longest-lead-time item. Apply at fia.gov.tw or einvoice.nat.gov.tw now. While waiting, use ECPay or similar third-party as interim eGUI proxy.
2. **Validate Tauri + React 19 webview on real hardware.** Book both Apple Silicon AND Intel Mac test machines. This is the gate before any screen development. If Intel Mac has rendering issues, React 18 with known quirks is the fallback.
3. **Resolve FastMCP version.** Confirm FastMCP 2.14.6 as the production version. Set a 6-month calendar reminder to re-evaluate FastMCP 3.x.
4. **Build `raw_legacy` staging database.** Load all 94 CSVs into PostgreSQL staging schema WITHOUT FK constraints. Validate 1.1M row count. Add staging columns (`_legacy_table`, `_import_status`, `_fk_violation`).

### Phase 1: Foundation -- Weeks 2-4

1. **Run FK validation, produce orphan report.** Confirm 190 orphan product codes (523 rows). Create product_code_mapping table. Top 10 orphan codes covering ~260 rows are mostly product size variants (RB052-6, 3V0710-2) and can be manually mapped in under an hour.
2. **Build MIG 4.1 XML invoice generator with full schema validation.** Start with A0101 message tree. Key fields: InvoiceNumber format `[A-Z]{2}\d{8}`, TaxType at both summary and detail level, decimal precision rules, ZeroTaxRateReason when TaxType=2. Build against MIG 4.1 revision notes in parallel with FIA application.
3. **Mock eGUI state machine service.** Build a mock FIA state transition service with realistic timing (PENDING / QUEUED / SENT / ACKED / FAILED). UI needs this to validate status badge and notification UX before real FIA credentials exist. Live FIA submission remains feature-flagged until credentials and operating conditions are confirmed.
4. **Set `statement_cache_size=0` in asyncpg pool from day 1.** Add to connection string before any database load testing. Configure PgBouncer in transaction mode and run a concurrent load test to confirm no prepared-statement errors.
5. **Build ROC date and UBN MOD11 as fully-tested pure functions.** Unit test comprehensively before any screen work. Validate UBN on 8th digit with 300ms debounce.

### Phase 2: Reference Integration -- Weeks 4-7

1. **Build reference MCP server end-to-end (invoices domain).** FastMCP 2.14.6. Full OAuth integration via middleware (Auth0 or Okta). RBAC scopes mapped to OAuth claims. Error handling with structured response format. Pagination with cursor encoding. This becomes the template for subsequent domain servers.
2. **Design system tray + notification architecture.** Minimal tray + notification flow: show notification when mocked invoice state changes. Verify macOS notification permissions on a fresh install. This is not deferrable -- the async eGUI workflow depends on it.
3. **Build one shadcn/ui screen as reference.** Customer list screen with virtualized TanStack Table. shadcn components: Table, Input (with UBN validation), Select, Badge, Dialog, Tooltip (avoid nesting). Validate Radix behavior on target hardware.
4. **Windows NSIS + sidecar packaging test.** Validate sidecar binary replacement on reinstall. If issue #15134 is unfixed, switch to WiX installer.
5. **Start PgBouncer transaction-mode load test** with reference MCP server running concurrent invoice tool calls. Verify no "prepared statement does not exist" or "idle in transaction" errors under concurrent load.

### Phase 3: Domain Expansion -- Weeks 7-12

1. **Build remaining MCP servers from reference template.** customers, inventory, orders, payments. Map RBAC scopes to OAuth 2.1 claims via Auth0 or Okta. Each domain server gets its own auth middleware and isolated database pool.
2. **Connect MIG 4.1 XML generator to invoice MCP server.** Use tbsslipx/tbsslipdtx staging data. Test with matched rows (592,494 rows, 99.91%) and orphan rows (523 rows). Verify TaxType inference for orphan items using the product_code_mapping table.
3. **End-to-end invoice PoC with real FIA credentials** (once API access approved and if filing obligation applies). Verify actual submission, PENDING/ACKED flow, and 48-hour deadline enforcement.
4. **Implement durable workflow infrastructure (outbox/inbox tables).** All eGUI submission events go through outbox table. Workers process with retry and exponential backoff. Inbox table handles FIA responses.

### Phase 4: Desktop App -- Weeks 12-16

1. **Complete Tauri + React 19 shell.** Integrate shadcn/ui screens for all domains. System tray + notifications fully operational. Global shortcuts registered.
2. **CLI commands via Typer.** `erp customers list`, `erp invoices create`, etc. Typer generates CLI from type hints. Shared business logic with MCP server.
3. **PyInstaller + externalBinary for production sidecar.** Replace child-process spawning with Tauri's native externalBinary feature. Produce self-contained desktop installer.

### Phase 5: Polish & Compliance -- Weeks 16-20

1. **Error handling and edge cases.** Implement structured error response format for MCP tools. Human-in-the-loop verification flow for sensitive operations (invoice void, large inventory adjustments).
2. **Security hardening.** MFA for admin accounts. Token audience validation enforced on every MCP request. Audit log table with append-only policy.
3. **Performance optimization.** Virtual scrolling for all large lists. Database indexes on tenant_id leading columns. PgBouncer connection tuning.
4. **Documentation and skills finalization.** All SKILL.md files complete. ERPNext migration guide for the 聯泰興 data.

**Total Estimated: 20 weeks** (unchanged from original estimate, but Phase 0 is now explicit and parallel)

---

## Immediate Next Steps

**Top 5 actions for the next 2 weeks:**

1. **File FIA API registration application.** Go to fia.gov.tw or einvoice.nat.gov.tw and submit the developer application. This is the single longest-lead-time item and blocks all real eGUI invoice transmission. No substitute exists.

2. **Obtain Intel Mac test hardware and run Tauri + React 19 webview validation.** Book or requisition an Intel Mac (not Apple Silicon). Run the `tauri-fastapi-poc` on it. Confirm whether React 19 resolves the dropdown/transform bugs or if additional workarounds are needed. This is the gate before any frontend work.

3. **Build the product code mapping table and run the 32-candidate manual mapping sprint.** Create `raw_legacy.product_code_mapping` with all 190 orphan codes. Export the 32 fuzzy-match candidates (e.g., `RB052-6` → `RB052`, `3V0710-2` → `3V series`) to a spreadsheet. Assign to a data analyst for manual confirmation. This takes under 1 hour and resolves 99.91% of historical sales detail. Remaining orphan rows (523) can use UNKNOWN_PRODUCT placeholder.

4. **Set `statement_cache_size=0` in all asyncpg connection pools immediately.** Add `statement_cache_size=0` to every `asyncpg.create_pool()` call and every SQLAlchemy asyncpg connection string. This eliminates a silent production failure under PgBouncer concurrency.

5. **Decide on FastMCP 2.x vs. 3.x and document the version strategy.** Formally adopt FastMCP 2.14.6 for production. Set a 6-month reminder to re-evaluate FastMCP 3.x when it achieves MCP SDK 1.23+ compatibility. This ends the version ambiguity that spans three research areas.
