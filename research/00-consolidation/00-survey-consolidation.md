# Survey Consolidation

## Cross-Area Dependencies

**1. UI/UX → eGUI Compliance (critical)**
The invoice creation screen requires MIG 4.1 schema field definitions (TaxType at detail level, InvoiceNumber pattern `[A-Z]{2}\d{8}`, decimal precision rules). The eGUI state indicator ("草稿 → 已送出 → 已開立 → 已作廢") maps directly to the FIA state machine (PENDING → QUEUED → SENT → ACKED | FAILED → RETRYING → DEAD_LETTER). UI cannot design the status badge and async submission flow without the eGUI state machine being explicitly defined first. Even when live FIA submission is feature-flagged off, the invoice screen still needs the state model, persistence, and deadline awareness designed in from day 1.

**2. UI/UX → Tech Viability (critical)**
React 19 is required to fix the known Tauri webview dropdown/transform bug (shadcn-ui/ui#7433). React 18 has unresolved rendering quirks in Tauri webview on Intel Macs. The UI/UX memo explicitly makes React 19 a first-PoC-gate requirement. This cascades to Tauri 2.x + Vite + React 19 being the confirmed stack before any screen development begins.

**3. UI/UX → Legacy Data (medium)**
Invoice and customer screens depend on legacy data being staged and mapped. The customer list (tbscust, 1,022 rows) needs ROC date display and UBN real-time MOD11 validation. The invoice creation screen needs product codes from tbsstock (6,611 SKUs). The actual orphan rate is 0.09% (523 rows out of 593,017) with 190 alphanumeric variant codes (RB052-6, 3V0710-2, etc.). 32 fuzzy-match candidates exist for manual mapping. The product code mismatch is NOT a blocking issue -- it is manageable via the product_code_mapping table and a 1-hour manual mapping sprint.

**4. Multi-Agent Patterns → Tech Viability (high)**
FastMCP version and transport choice are shared between both areas. The consolidated decision is FastMCP 2.14.6 with session-mode HTTP transport: Tech Viability contributes the session-mode requirement to avoid the stateless HTTP sampling hang bug, and Multi-Agent Patterns contributes the FastMCP 2.x requirement because FastMCP 3.x pins `mcp<1.23` and blocks newer SDK features.

**5. Multi-Agent Patterns → Legacy Data (low)**
The FastMCP invoice tools (when built) will call legacy invoice data (tbsslipx, tbsslipdtx). The product code mismatch affects only 523 rows (0.09% of 593,017). Invoice tool test scenarios should use the matched rows (99.91%) which join cleanly. The orphan product codes are alphanumeric variants (RB052-6, etc.) and 32 fuzzy-match candidates exist for manual resolution.

**6. eGUI Compliance → Legacy Data (low)**
MIG 4.1 XML invoice generation must pull data from tbsslipx (sales invoice headers) and tbsslipdtx (line items). The invoice number format in tbsslipx (e.g., 1130826001 = 2024-08-26-001) must be parsed into MIG 4.1 InvoiceNumber format `[A-Z]{2}\d{8}`. For the 523 orphan rows (0.09%), MIG 4.1 ProductItem descriptions may be incomplete, but 99.91% of invoice lines have clean product references.

**7. Tech Viability ↔ Multi-Agent Patterns (shared risk)**
Both areas independently surface the Tauri sidecar NSIS binary-replacement bug (#15134). Tech Viability flags it for Windows packaging; Multi-Agent Patterns will use Tauri sidecar for the Python FastMCP server. A single Windows NSIS workaround must cover both the Tauri app and the sidecar binary simultaneously.

---

## Updated Risk Register (ranked globally by severity × likelihood)

### Tier 1: Critical (act before Wave 2 begins)

| # | Risk | Area | Severity | Likelihood | Score |
|---|------|------|----------|------------|-------|
| R1 | **Product Code Orphan Risk**: 190 orphan codes (0.09% of 593,017 rows = 523 rows) are alphanumeric variants of existing products. 32 fuzzy-match candidates can be resolved manually in ~1 hour. If not mapped, those 523 rows show as UNKNOWN_PRODUCT. Manageable via product_code_mapping table. | Legacy Data | Medium | Low | 8 |
| R2 | **MIG 4.1 Schema Not Implemented**: MIG 4.1 became mandatory 2026-01-01. Key changes: TaxType moved to line-item level, CheckNumber removed, SequenceNumber/Remark/RelateNumber lengths extended. Existing MIG 4.0 XML will be rejected. | eGUI Compliance | Critical | Already生效 | 25 |

### Tier 2: High

| # | Risk | Area | Severity | Likelihood | Score |
|---|------|------|----------|------------|-------|
| R3 | **FastMCP Stateless HTTP Sampling Hang**: `stateless_http=True` causes sampling/elicitation calls to hang indefinitely. Conflicts with stated horizontal-scaling architecture. No fix until MCP spec formally defines stateless HTTP. | Tech Viability | High | Near-certain (if stateless HTTP used) | 20 |
| R4 | **48-Hour B2C Submission Deadline with No Confirmed Grace Period**: FIA cross-checks InvoiceDate+Time vs. server-received timestamp. Late submissions enter RETRYING → DEAD_LETTER. Penalty up to TW$15,000 + late tax penalties. | eGUI Compliance | High | High | 20 |
| R5 | **Tauri NSIS Sidecar Binary Not Replaced on Upgrade** (issue #15134): Windows auto-update will ship outdated Python sidecar after first reinstall. Affects every Tauri component using sidecar (including all FastMCP servers on Windows). | Tech Viability | High | High (on Windows) | 16 |
| R6 | **Radix UI Stability / Bug Backlog**: Known Tooltip/Popover/Dropdown bugs unfixed for years. shadcn actively evaluating Base UI as replacement. Supply-chain risk for long-term ERP development. | UI/UX | Medium-High | High | 16 |
| R7 | **FIA API Registration Blocker / No Public Sandbox**: Cannot test FIA API without approved App ID + API Key. Approval may take weeks to months. No self-service public sandbox exists. Blocks eGUI PoC entirely. | eGUI Compliance | High | High | 20 |

### Tier 3: Medium-High

| # | Risk | Area | Severity | Likelihood | Score |
|---|------|------|----------|------------|-------|
| R8 | **eGUI State UX Race Condition**: Async state transitions (minutes to hours) can be lost if app is closed/reopened. Webview may be unloaded while tray keeps app alive. | UI/UX | Medium | High | 15 |
| R9 | **SQLAlchemy 2.0 asyncpg + PgBouncer Transaction Mode Conflict**: `statement_cache_size=0` required to avoid "prepared statement does not exist" errors. Silent failure under load if missed. | Tech Viability | Medium | Medium-High (if PgBouncer used) | 12 |
| R10 | **Taiwan Localization Field Quality**: UBN MOD11 validation and ROC date handling must be error-free. Finance staff copy-paste from spreadsheets. Incorrect Tax IDs are a compliance violation. | UI/UX | Medium | High | 15 |
| R11 | **FastMCP 3.x Pins MCP SDK <1.23**: FastMCP 3.x cannot use MCP SDK 1.23+ features (November 2025 update). This blocks access to newer protocol capabilities. | Multi-Agent Patterns | Medium-High | High (if v3 adopted) | 16 |
| R12 | **Human-in-the-Loop Verification Complexity**: MCP spec requires human confirmation for sensitive operations. "SHOULD" not "MUST" prompt. Misunderstanding creates security gaps or UX failures in multi-agent invoice void/issue flows. | Multi-Agent Patterns | High | Medium | 15 |
| R13 | **Target Schema FK Constraints Will Fail on Import**: Staging PostgreSQL has FK constraints referencing products. ~591K tbsslipdtx rows will violate FK on direct import. Must disable constraints or use placeholder products. | Legacy Data | Medium | Certain (if FK enforced) | 12 |

### Tier 4: Medium

| # | Risk | Area | Severity | Likelihood | Score |
|---|------|------|----------|------------|-------|
| R14 | **Token Audience Validation Gaps** ("confused deputy"): MCP OAuth 2.1 requires strict audience claim validation. Generic OAuth provider or misconfigured audience allows token replay across MCP servers. | Multi-Agent Patterns | Critical | Medium (if generic OAuth used) | 15 |
| R15 | **Data Lineage Traceability Lost**: Single-row tables (tbaaccounts, tbasyspara, tbcpasswd, etc.) likely contain company-wide settings. Minimal-row tables may cause inconsistent behavior post-import. | Legacy Data | Medium | High | 12 |
| R16 | **Decision Drift from Resolved FastMCP Baseline**: The architecture baseline is FastMCP 2.14.6 with session-mode HTTP. Reopening the 2.x vs 3.x question without new evidence risks reintroducing SDK and transport instability. | Tech Viability / Multi-Agent | Medium | Medium | 9 |
| R17 | **React 19 Intel Mac Webview Issues**: React 19 fixes known Tauri webview bugs but may itself have rendering quirks on Intel Macs. Requires hardware testing before commit. | UI/UX | Medium | Medium | 9 |

### NEWLY VISIBLE RISKS (only visible when cross-area analysis is performed)

| # | Risk | Visibility Trigger |
|---|------|--------------------|
| N1 | **Product code mismatch is lower risk than survey suggested**. R1 was scored as Critical based on 99.7% orphan rate; PoC corrected this to 0.09% (523 rows, 190 codes). 32 fuzzy-match candidates can be manually mapped. The invoice tool's value proposition is intact for 99.91% of transactions. This risk should be re-scored as Medium/Low. |
| N2 | **React 19 on Intel Mac + Tauri NSIS sidecar + FastMCP version conflict creates a three-way compatibility matrix that no single area surveyed**. UI/UX requires React 19; Tech Viability surfaces Tauri NSIS bug; Multi-Agent restricts FastMCP to 2.x. The PoC must test all three simultaneously to catch interaction failures. |
| N3 | **SQLAlchemy asyncpg cache issue + PgBouncer + multi-tenant MCP session mode**: If the multi-agent layer runs multiple MCP servers (customers, invoices, inventory) each with its own session-mode connection, the cumulative connection count under PgBouncer transaction mode amplifies the prepared-statement risk described in Tech Viability R9. This only becomes visible when combining Tech Viability + Multi-Agent + Legacy Data connection topology. |
| N4 | **MIG 4.1 TaxType at detail level + product code mismatch = contained data quality failure**. eGUI Compliance requires TaxType at line-item level (new in MIG 4.1). For the 523 orphan rows (0.09%), TaxType cannot be automatically determined from product category. This is a contained issue -- 99.91% of invoice lines have both valid product_id and determinable TaxType. The 523 affected rows need either mapped product_id or explicit TaxType override. |

---

## Wave 2 Guidance

### Phase 0 -- PoC Prerequisites (parallel, before any PoC feature work)

1. **Initiate FIA API registration immediately.** This is the single longest-lead-time item (weeks to months). No eGUI compliance PoC can transmit real invoices without approved credentials. Apply at fia.gov.tw or einvoice.nat.gov.tw now.
2. **Validate Tauri + React 19 webview on real hardware (Apple Silicon AND Intel Mac).** UI/UX makes this a first PoC gate. Book hardware now. This is a prerequisite before any screen development begins.
3. **Adopt the resolved FastMCP baseline.** Use FastMCP 2.14.6 with session-mode HTTP as the immediate implementation baseline and set a 6-month horizon to re-evaluate 3.x.

### Phase 1 -- Foundation (Weeks 1-2)

1. **Build staging database (Legacy Data).** Load all 94 CSVs into PostgreSQL staging schema WITHOUT FK constraints. Add staging columns (`_legacy_table`, `_import_status`, `_fk_violation`). Validate 1.1M row count.
2. **Run FK validation, produce orphan report.** Confirm 190 orphan product codes (523 rows, 0.09%). Create product_code_mapping table. Top 10 codes are mostly product size variants (RB052-6, 3V0710-2) and can be manually mapped in under an hour. This data is needed by both invoice MCP tools and MIG 4.1 XML generation.
3. **Build MIG 4.1 XML invoice generator with schema validation (eGUI Compliance).** Start with A0101 message tree. Key validation: InvoiceNumber format, TaxType at both summary and detail level, decimal precision, ZeroTaxRateReason when TaxType=2. Build against MIG 4.0/4.1 PDF schema in parallel with FIA application.
4. **Mock eGUI state machine for UI.** Build a mock FIA state transition service with realistic timing (PENDING → QUEUED → SENT → ACKED | FAILED). UI needs this to validate status badge and notification UX before real FIA credentials exist.
5. **Set `statement_cache_size=0` in asyncpg pool from day 1** (Tech Viability R9). Add to connection string before any load testing.

### Phase 2 -- Reference Integration (Weeks 3-5)

1. **Build one reference MCP server end-to-end (Multi-Agent Patterns).** Use FastMCP 2.x. Choose the `invoices` domain as reference: full OAuth integration, error handling, pagination, RBAC scopes (`erp:finance:invoice:void`, `erp:agent:invoice:create`). This surfaces integration issues (auth flow, cursor encoding, SDK quirks) before scaling to all domains.
2. **Design system tray + notification architecture (UI/UX).** eGUI state tracking requires background operation. Implement minimal tray + notification flow in first sprint: show notification when mocked invoice state changes. Verify macOS notification permissions on a fresh install. This is not deferrable -- the entire async invoice workflow depends on it.
3. **Start PgBouncer transaction-mode load test** with reference MCP server running concurrent invoice tool calls. Verify no "prepared statement does not exist" or "idle in transaction" errors emerge under concurrent load.
4. **Validate ROC date and UBN MOD11 as standalone, fully-tested utilities (UI/UX).** These are pure functions called throughout the UI. Unit test thoroughly before any screen work. Validate UBN on 8th digit entry with 300ms debounce.

### Phase 3 -- Integration & Scaling (Weeks 6-8)

1. **Connect MIG 4.1 XML generator to invoice MCP server.** Use tbsslipx/tbsslipdtx staging data. Test with matched rows (592,494 rows, 99.91%) and orphan rows (523 rows, 0.09%). Verify TaxType inference for orphan items using product_code_mapping table.
2. **Build remaining MCP servers from reference template** (customers, inventory, orders, payments). Map RBAC scopes to OAuth 2.1 claims via Auth0 or Okta.
3. **Windows NSIS + sidecar packaging test.** Validate that the sidecar binary IS replaced on reinstall (workaround for issue #15134). Test WiX as alternative if NSIS fails.
4. **End-to-end invoice PoC with real FIA credentials** (once API access approved). Verify actual submission, PENDING→ACKED flow, and 48-hour deadline enforcement.
