# AI-Native ERP: Multi-Agent Research Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Conduct a full proof-of-concept research sprint across 5 areas — Legacy Data, Tech Viability, eGUI Compliance, Multi-Agent Patterns, UI/UX — producing survey memos, working PoCs, and a consolidated "Whole Picture" document.

**Architecture:** Sequential survey phase (5 one-day agents) followed by parallel PoC sprint (5 simultaneous agents) followed by consolidation. Each area operates in its own git worktree with Claude Code as the research agent.

**Tech Stack:** Claude Code, Git Worktrees, Markdown, Python/CLI tools for PoCs

---

## Phase 0: Infrastructure Setup

**Purpose:** Create the worktree structure and output directories before any research begins.

### Task 0.1: Create Base Directory Structure

**Files:**
- Create: `research/legacy-data/`
- Create: `research/tech-viability/`
- Create: `research/egui-compliance/`
- Create: `research/multi-agent-patterns/`
- Create: `research/ui-ux/`
- Create: `research/00-consolidation/`

- [ ] **Step 1: Create directory structure**

Run:
```bash
mkdir -p /Volumes/2T_SSD_App/Projects/UltrERP/research/{legacy-data,tech-viability,egui-compliance,multi-agent-patterns,ui-ux,00-consolidation}
```

### Task 0.2: Initialize Git Worktrees (if repo becomes git)

> **Skip this task** if the UltrERP directory remains a non-git directory. If git is initialized later, use `superpowers:using-git-worktrees` skill at that time.

### Task 0.3: Copy Reference Context into Each Research Directory

**Files:**
- Modify: `research/legacy-data/00-context.md` — copy relevant legacy data files
- Modify: `research/tech-viability/00-context.md` — copy architecture design
- Modify: `research/egui-compliance/00-context.md` — copy eGUI section from architecture
- Modify: `research/multi-agent-patterns/00-context.md` — copy MCP section from architecture
- Modify: `research/ui-ux/00-context.md` — copy UI section from architecture

- [ ] **Step 1: Create context files**

Run:
```bash
# Legacy data context
cat > research/legacy-data/00-context.md << 'EOF'
# Legacy Data Context

Source: /Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/

Key files:
- README.md — project overview, 94 tables, 1.1M rows
- COLUMN_ANALYSIS.md — field-by-field analysis
- FK_VALIDATION.md — FK validation results
- extracted_data/*.csv — 94 clean CSV files
- schema/postgresql_schema.sql — target schema
EOF

# Tech viability context
cat > research/tech-viability/00-context.md << 'EOF'
# Tech Viability Context

Source: /Volumes/2T_SSD_App/Projects/UltrERP/design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md

Key decisions to validate:
- Tauri 2.x + Python sidecar pattern
- FastMCP 2.0 stateless HTTP mode
- FastAPI sub-apps (mounts) for modular monolith
- SQLAlchemy 2.0 async + PgBouncer

Reference repos:
- github.com/dieharders/example-tauri-v2-python-server-sidecar
- github.com/YoraiLevi/modular-monolith-fastapi
EOF

# eGUI context
cat > research/egui-compliance/00-context.md << 'EOF'
# eGUI Compliance Context

Source: /Volumes/2T_SSD_App/Projects/UltrERP/design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md

Key requirements:
- MIG 4.1 XML format (effective Jan 1, 2026)
- FIA API submission within 48 hours
- Tax rates: 5%, 10%, 0%
- State machine: PENDING→QUEUED→SENT→ACKED|FAILED→RETRYING→DEAD_LETTER
- Void/reissue: same month only

Reference:
- MIG 4.1 from ecosio.com/en/blog/taiwan-einvoicing-explained
EOF

# Multi-agent patterns context
cat > research/multi-agent-patterns/00-context.md << 'EOF'
# Multi-Agent Patterns Context

Source: /Volumes/2T_SSD_App/Projects/UltrERP/design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md

Key topics:
- FastMCP 2.0 tool design principles
- MCP OAuth 2.1 for agent auth
- Capability-based ACL for agents
- Stateless HTTP scaling mode
- RBAC: admin, finance, warehouse, sales, agent roles

Reference: modelcontextprotocol/servers
EOF

# UI/UX context
cat > research/ui-ux/00-context.md << 'EOF'
# UI/UX Context

Source: /Volumes/2T_SSD_App/Projects/UltrERP/design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md

Key requirements:
- Tauri 2.x + Vite + React + shadcn/ui + Radix
- Casual users (GUI) vs. power users (CLI)
- Taiwan localization: ROC dates, tax ID validation
- System tray, native notifications
- Screens: customers, invoices, inventory, orders
EOF
```

---

## Phase 1: Sequential Survey

**Purpose:** Each area produces a 1-page survey memo before PoC work begins.

### Task 1.1: Legacy Data Landscape Survey

**Files:**
- Create: `research/legacy-data/01-survey-memo.md`

**Agent prompt for survey (run via Claude Code in research directory):**

```
You are the Legacy Data Analyst for an AI-native ERP migration project.

Your task: Spend up to 4 hours researching and producing a 1-page survey memo
on the legacy data landscape.

CONTEXT:
- Source: /Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/
- 94 tables, 1.1M rows from 聯泰興實業有限公司 (鼎新-style ERP)
- Key tables: tbscust (customers), tbsstock (products), tbsslipx (sales invoices),
  tbsslipdtx (593K invoice lines), tbsslipj (purchase invoices), tbsstkhouse (inventory)
- CRITICAL ISSUE: Product codes in tbsslipdtx are numeric (1138, 1000) while
  tbsstock uses alphanumeric codes (PC240, XPB-2410-P). 660 codes don't match.

RESEARCH TASKS:
1. Read all files in the legacy-migration-pipeline/ directory
2. Analyze the FK relationships and identify all dependency chains
3. Investigate the product code mismatch: is there a mapping table?
4. Identify data quality issues (nulls, encoding, ROC date edge cases)
5. Assess staging schema options: raw import vs. cleaned schema

OUTPUT FORMAT:
Create research/legacy-data/01-survey-memo.md with:

# Legacy Data Landscape Survey

## Known Facts
(what you confirmed from reading the files)

## Unknowns / Open Questions
(top 5 things you couldn't determine)

## Top 3 Risks
(ranked by impact)

## 3-Point Recommendation
(what to do next for the PoC)
```

- [ ] **Step 1: Run legacy data survey agent**

```bash
cd /Volumes/2T_SSD_App/Projects/UltrERP/research/legacy-data
# Launch Claude Code with the survey prompt (command depends on CLI interface)
claude --prompt "Act as Legacy Data Analyst. Read /Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/* and /Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/**/*.md. Then write survey memo to 01-survey-memo.md"
```

### Task 1.2: Tech Viability Survey

**Files:**
- Create: `research/tech-viability/01-survey-memo.md`

**Agent prompt:**
```
You are the Tech Viability Researcher for an AI-native ERP project.

Your task: Spend up to 4 hours researching and producing a 1-page survey memo
on technology viability.

CONTEXT:
Architecture decisions to validate:
- Tauri 2.x desktop shell + Python FastAPI sidecar
- FastMCP 2.0 with stateless HTTP mode
- FastAPI sub-apps (mounts) for modular monolith
- SQLAlchemy 2.0 async with PostgreSQL 17+ + pgvector
- Redis 7+ for sessions/cache, MinIO for S3-compatible storage

REFERENCE REPOS (validate current state):
- github.com/dieharders/example-tauri-v2-python-server-sidecar
- github.com/YoraiLevi/modular-monolith-fastapi
- github.com/prefecthq/fastmcp

RESEARCH TASKS:
1. Check latest releases of: Tauri 2.x, FastMCP 2.0, FastAPI 0.115+
2. Verify the Python sidecar pattern still works with current Tauri 2.x
3. Check FastMCP 2.0 changelog for breaking changes
4. Verify FastAPI mount pattern for sub-apps still works as documented
5. Check SQLAlchemy 2.0 async compatibility with PgBouncer transaction mode

OUTPUT FORMAT:
Create research/tech-viability/01-survey-memo.md with:

# Technology Viability Survey

## Known Facts
(confirmed version compatibility)

## Unknowns / Open Questions
(top issues needing PoC verification)

## Top 3 Risks
(ranked by impact)

## 3-Point Recommendation
(what to do next for the PoC)
```

- [ ] **Step 1: Run tech viability survey agent**

### Task 1.3: eGUI Compliance Survey

**Files:**
- Create: `research/egui-compliance/01-survey-memo.md`

**Agent prompt:**
```
You are the eGUI Compliance Researcher for a Taiwan SMB ERP project.

Your task: Spend up to 4 hours researching and producing a 1-page survey memo
on Taiwan eGUI electronic invoice compliance.

CONTEXT:
- MIG 4.1 standard effective January 1, 2026
- FIA API for invoice submission
- 48-hour submission window
- Tax rates: 5%, 10%, 0%
- State machine: PENDING→QUEUED→SENT→ACKED|FAILED→RETRYING→DEAD_LETTER
- Void/reissue: same month only

RESEARCH TASKS:
1. Research FIA API: endpoint URLs, authentication (App ID + API Key), rate limits
2. Study MIG 4.1 XML schema: required fields, optional fields, validation rules
3. Understand the 48-hour enforcement: what triggers it, what happens at hour 49
4. Research void/reissue same-month constraint and how to implement
5. Find any publicly available FIA API sandbox or test environment

OUTPUT FORMAT:
Create research/egui-compliance/01-survey-memo.md with:

# Taiwan eGUI Compliance Survey

## Known Facts
(MIG 4.1 requirements, FIA API basics)

## Unknowns / Open Questions
(top issues needing PoC verification)

## Top 3 Risks
(ranked by impact)

## 3-Point Recommendation
(what to do next for the PoC)
```

- [ ] **Step 1: Run eGUI compliance survey agent**

### Task 1.4: Multi-Agent Patterns Survey

**Files:**
- Create: `research/multi-agent-patterns/01-survey-memo.md`

**Agent prompt:**
```
You are the Multi-Agent Patterns Researcher for an AI-native ERP project.

Your task: Spend up to 4 hours researching and producing a 1-page survey memo
on how AI agents interact with MCP servers.

CONTEXT:
- FastMCP 2.0 is the MCP server framework
- Agents: Claude Code, OpenClaw, custom agents
- Auth: JWT or API keys with scopes (customers:read, invoices:write, etc.)
- MCP OAuth 2.1 for agent authorization
- Stateless HTTP mode for horizontal scaling

REFERENCE:
- modelcontextprotocol/servers (official MCP reference)
- modelcontextprotocol.info/docs/best-practices

RESEARCH TASKS:
1. Study FastMCP 2.0 tool design: naming conventions, parameter schemas, error responses
2. Understand MCP OAuth 2.1 flow for agent authentication
3. Research how Claude Code connects to custom MCP servers (tool registration)
4. Study error handling patterns: structured errors with retry guidance
5. Understand stateless HTTP mode: how it enables horizontal scaling

OUTPUT FORMAT:
Create research/multi-agent-patterns/01-survey-memo.md with:

# Multi-Agent Patterns Survey

## Known Facts
(confirmed patterns from MCP spec)

## Unknowns / Open Questions
(top issues needing PoC verification)

## Top 3 Risks
(ranked by impact)

## 3-Point Recommendation
(what to do next for the PoC)
```

- [ ] **Step 1: Run multi-agent patterns survey agent**

### Task 1.5: UI/UX Survey

**Files:**
- Create: `research/ui-ux/01-survey-memo.md`

**Agent prompt:**
```
You are the UI/UX Researcher for a Taiwan SMB ERP desktop application.

Your task: Spend up to 4 hours researching and producing a 1-page survey memo
on desktop ERP UX patterns.

CONTEXT:
- Tauri 2.x + Vite + React + shadcn/ui + Radix
- Users: casual (GUI) and power users (CLI)
- Taiwan localization: ROC dates (民國), tax ID (統一編號) validation
- Native integrations: system tray, notifications
- Core screens: customer list/create/edit, invoice creation with eGUI state,
  inventory check with reorder alerts, order workflow

RESEARCH TASKS:
1. Study shadcn/ui + Radix on Tauri: known issues, performance
2. Research Taiwan SMB ERP UX patterns: what do power users vs casual users need?
3. Understand ROC date handling: UX display format, storage format
4. Research tax ID (統一編號) validation UX: real-time feedback vs. submit-time
5. Study Tauri system tray and notification patterns on macOS/Windows

OUTPUT FORMAT:
Create research/ui-ux/01-survey-memo.md with:

# UI/UX Survey

## Known Facts
(confirmed component/library viability)

## Unknowns / Open Questions
(top issues needing wireframe verification)

## Top 3 Risks
(ranked by impact)

## 3-Point Recommendation
(what to do next for the PoC)
```

- [ ] **Step 1: Run UI/UX survey agent**

### Task 1.6: Survey Consolidation

**Files:**
- Create: `research/00-consolidation/00-survey-consolidation.md`

**Agent prompt:**
```
You are a synthesis analyst. Read all five survey memos and produce a 1-page
consolidation memo identifying cross-area dependencies.

Run:
cat research/legacy-data/01-survey-memo.md
cat research/tech-viability/01-survey-memo.md
cat research/egui-compliance/01-survey-memo.md
cat research/multi-agent-patterns/01-survey-memo.md
cat research/ui-ux/01-survey-memo.md

Then create research/00-consolidation/00-survey-consolidation.md with:

# Survey Consolidation

## Cross-Area Dependencies
(e.g., "UI/UX depends on eGUI state machine being defined")

## Updated Risk Register
(all risks across 5 areas, ranked globally)

## Wave 2 Guidance
(how PoC phase should be sequenced based on survey findings)
```

- [ ] **Step 1: Run survey consolidation agent**

---

## Phase 2: Parallel PoC Sprint

**Purpose:** 5 agents run in parallel, each producing a working PoC and full findings doc.

### Task 2.1: Legacy Data PoC

**Files:**
- Create: `research/legacy-data/02-poc/migration_pipeline/`
- Create: `research/legacy-data/03-findings.md`

**Agent prompt:**
```
You are the Legacy Data Analyst. Build a working migration pipeline PoC.

CONTEXT from survey:
(Summarize findings from research/legacy-data/01-survey-memo.md)

WORKING DIRECTORY:
research/legacy-data/02-poc/

POC REQUIREMENTS:
1. Create a Python script import_legacy.py that:
   - Connects to PostgreSQL (use env var DATABASE_URL or default localhost)
   - Creates staging schema (raw_legacy schema)
   - Imports at least 3 key CSV files: tbscust.csv, tbsstock.csv, tbsslipx.csv
   - Handles ROC date parsing (民國 year + 1911 = AD)
   - Handles Big5 encoding verification (data is already UTF-8 per extracted_data/)

2. Create SQL resolution for the 660 product code mismatches:
   - Script or SQL file that documents the mismatch
   - Shows proposed mapping table schema OR acceptance criteria for orphan handling

3. Document the PoC in 03-findings.md (2-4 pages):
   - What worked
   - What didn't work
   - Performance measurements (import speed, FK resolution time)
   - Recommendations for full migration

SUCCESS CRITERIA:
- `python import_legacy.py` runs without error and imports at least 3 tables
- CSV encoding is verified correct (UTF-8)
- ROC dates are correctly parsed
- 660 mismatched codes are documented with resolution strategy
```

- [ ] **Step 1: Run legacy data PoC agent (background)**

### Task 2.2: Tech Viability PoC

**Files:**
- Create: `research/tech-viability/02-poc/tauri-fastapi-sidecar/`
- Create: `research/tech-viability/03-findings.md`

**Agent prompt:**
```
You are the Tech Viability Researcher. Build a working Tauri + FastAPI sidecar PoC.

CONTEXT from survey:
(Summarize findings from research/tech-viability/01-survey-memo.md)

WORKING DIRECTORY:
research/tech-viability/02-poc/

POC REQUIREMENTS:
1. Clone or reference: github.com/dieharders/example-tauri-v2-python-server-sidecar
2. Create minimal Tauri 2.x app that:
   - Has a webview (Vite + React scaffolded via `npm create tauri-app`)
   - Spawns a Python FastAPI server as sidecar on localhost:8000
   - Webview can call `http://localhost:8000/api/ping` and display "pong"

3. FastAPI sidecar (Python):
   - `/api/ping` returns `{"status": "pong", "timestamp": "..."}`
   - `/api/domains` returns `{"domains": ["customers", "invoices", "inventory"]}`
   - Use FastAPI latest with `from fastapi import FastAPI`

4. Document in 03-findings.md (2-4 pages):
   - Which Tauri version was installed
   - Sidecar spawning behavior on macOS vs. Windows
   - Any issues with the reference implementation
   - Recommendations for production build

SUCCESS CRITERIA:
- `npm run dev` in Tauri directory starts the app
- Python sidecar spawns automatically
- Webview displays pong response from FastAPI
- Document any version mismatches or workarounds needed
```

- [ ] **Step 1: Run tech viability PoC agent (background)**

### Task 2.3: eGUI Compliance PoC

**Files:**
- Create: `research/egui-compliance/02-poc/mig41_generator/`
- Create: `research/egui-compliance/03-findings.md`

**Agent prompt:**
```
You are the eGUI Compliance Researcher. Build a working MIG 4.1 XML + FIA mock PoC.

CONTEXT from survey:
(Summarize findings from research/egui-compliance/01-survey-memo.md)

WORKING DIRECTORY:
research/egui-compliance/02-poc/

POC REQUIREMENTS:
1. Create mig41_generator.py that:
   - Generates valid MIG 4.1 XML for a sample invoice
   - Includes: 統一編號, 發票日期, 品項, 稅額
   - Uses 5% tax rate, includes 2 line items
   - Validates all required fields per MIG 4.1 schema
   - Outputs to sample_invoice.xml

2. Create fia_mock_server.py that:
   - Simulates FIA API endpoint
   - Returns ACK response for valid XML
   - Returns REJECT response for invalid XML (demonstrating error handling)
   - Implements the 48-hour window check (mock only, accept any timestamp)

3. Create submit_invoice.py that:
   - Reads sample_invoice.xml
   - POSTs to mock FIA server
   - Handles ACK and REJECT responses
   - Demonstrates retry logic for FAILED states

4. Document in 03-findings.md (2-4 pages):
   - MIG 4.1 schema analysis (which fields are required vs optional)
   - FIA API mock behavior
   - State machine implementation notes
   - Recommendations for real FIA integration

SUCCESS CRITERIA:
- `python mig41_generator.py` produces valid MIG 4.1 XML
- `python fia_mock_server.py` runs on localhost:8080
- `python submit_invoice.py` successfully submits and receives ACK
- Invalid XML triggers REJECT response with error details
```

- [ ] **Step 1: Run eGUI compliance PoC agent (background)**

### Task 2.4: Multi-Agent Patterns PoC

**Files:**
- Create: `research/multi-agent-patterns/02-poc/fastmcp-server/`
- Create: `research/multi-agent-patterns/03-findings.md`

**Agent prompt:**
```
You are the Multi-Agent Patterns Researcher. Build a working FastMCP 2.0 server PoC.

CONTEXT from survey:
(Summarize findings from research/multi-agent-patterns/01-survey-memo.md)

WORKING DIRECTORY:
research/multi-agent-patterns/02-poc/

POC REQUIREMENTS:
1. Create FastMCP 2.0 server with these tools:
   - `customers.list` — list customers with status filter
   - `customers.create` — create customer with tax_id validation (8 digits)
   - `invoices.create` — create invoice with line items and tax calculation
   - `invoices.list` — list invoices with status filter
   - Each tool has comprehensive docstrings and typed parameters

2. Implement auth:
   - API key authentication via `X-API-Key` header
   - Scoped access: `customers:read`, `customers:write`, `invoices:read`, `invoices:write`
   - Capability-based rejection for unauthorized calls

3. Implement structured errors:
   - ValidationError with field-level details
   - NotFoundError with entity type and ID
   - PermissionError with required scope
   - Each error includes retry guidance

4. Run with: `uvicorn main:app --host 0.0.0.0 --port 8000 -- stateless`
   Or FastMCP built-in HTTP mode

5. Document in 03-findings.md (2-4 pages):
   - FastMCP 2.0 tool registration syntax (what worked)
   - Auth implementation notes
   - Error response format analysis
   - Recommendations for full MCP server

SUCCESS CRITERIA:
- Server starts and responds to MCP handshake
- `customers.list` returns mock customer data
- `customers.create` validates tax_id format
- Unauthorized calls are rejected with proper error format
- `invoices.create` calculates tax correctly (5% of subtotal)
```

- [ ] **Step 1: Run multi-agent patterns PoC agent (background)**

### Task 2.5: UI/UX Wireframe PoC

**Files:**
- Create: `research/ui-ux/02-wireframes/`
- Create: `research/ui-ux/03-findings.md`

**Agent prompt:**
```
You are the UI/UX Researcher. Produce wireframes and UX findings.

CONTEXT from survey:
(Summarize findings from research/ui-ux/01-survey-memo.md)

WORKING DIRECTORY:
research/ui-ux/02-wireframes/

POC REQUIREMENTS:
Produce ASCII wireframes for 3 core screens. Each wireframe should be
detailed enough to show layout, component placement, and Taiwan localization.

SCREEN 1: Customer Management
- List view with search/filter (name, tax_id, status)
- Create/edit customer modal with tax_id validation feedback
- Show ROC date format (e.g., 114/03/30 for 2025-03-30)
- Columns: 統一編號, 公司名稱, 電話, 狀態, 帳餘

SCREEN 2: Invoice Creation
- Customer selector with autocomplete
- Line item table (品名, 數量, 單價, 稅額, 小計)
- eGUI state indicator (草稿, 待送出, 已送出, 已確認)
- Tax calculation panel (課稅別, 税率, 稅額, 總計)
- Submit to eGUI button with 48-hour countdown

SCREEN 3: Inventory Check
- Product search with code or name
- Stock levels display (目前在庫, 預留, 可用)
- Reorder alert if below threshold
- Warehouse selector (總倉, 分倉)

For each wireframe, include:
- Casual user flow (minimal clicks to complete common task)
- Power user flow (keyboard shortcuts, bulk operations)
- Taiwan-specific: ROC dates, 統一編號 validation, Traditional Chinese labels

Document in 03-findings.md (2-4 pages):
- shadcn/ui component recommendations per screen
- Taiwan localization decisions
- Casual vs. power user split implementation notes
- Tauri-specific integration notes (system tray, notifications)

SUCCESS CRITERIA:
- 3 ASCII wireframes showing complete layout
- Taiwan localization clearly demonstrated
- Casual vs. power user flows are distinct
- Component choices are specific (e.g., "use shadcn Table with sortable columns")
```

- [ ] **Step 1: Run UI/UX wireframe PoC agent (background)**

### Task 2.6: Wait for All PoCs to Complete

- [ ] **Step 1: Check PoC completion status**

Run:
```bash
# Check each area has 03-findings.md
ls -la research/legacy-data/03-findings.md 2>/dev/null && echo "legacy: OK" || echo "legacy: PENDING"
ls -la research/tech-viability/03-findings.md 2>/dev/null && echo "tech: OK" || echo "tech: PENDING"
ls -la research/egui-compliance/03-findings.md 2>/dev/null && echo "egui: OK" || echo "egui: PENDING"
ls -la research/multi-agent-patterns/03-findings.md 2>/dev/null && echo "multi: OK" || echo "multi: PENDING"
ls -la research/ui-ux/03-findings.md 2>/dev/null && echo "uiux: OK" || echo "uiux: PENDING"
```

---

## Phase 3: Consolidation

### Task 3.1: Whole Picture Document

**Files:**
- Create: `research/00-consolidation/whole-picture.md`

**Agent prompt:**
```
You are the consolidation analyst. Produce the "Whole Picture" document.

Read all findings:
cat research/legacy-data/03-findings.md
cat research/tech-viability/03-findings.md
cat research/egui-compliance/03-findings.md
cat research/multi-agent-patterns/03-findings.md
cat research/ui-ux/03-findings.md

Also read:
cat research/00-consolidation/00-survey-consolidation.md
cat /Volumes/2T_SSD_App/Projects/UltrERP/design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md

Produce research/00-consolidation/whole-picture.md (3-5 pages):

# Whole Picture: AI-Native ERP Research Consolidation

## Executive Summary
(2-3 paragraphs on what we learned)

## Validated Architecture Decisions
(what the PoCs confirmed from the original architecture design)

## Updated Risk Register
(all risks from 5 areas, ranked by severity + likelihood)

## Cross-Area Dependencies Resolved
(what was uncertain in survey, now resolved by PoC)

## Remaining Unknowns
(what still needs investigation before production)

## Implementation Phasing Recommendations
(updated from Phase 1-5 in original architecture doc, based on research findings)

## Next Steps
(immediate actions after research sprint)
```

- [ ] **Step 1: Run consolidation agent**

---

## Task Completion Checklist

| # | Task | Status |
|---|------|--------|
| 0.1 | Directory structure | ☐ |
| 0.3 | Context files | ☐ |
| 1.1 | Legacy data survey | ☐ |
| 1.2 | Tech viability survey | ☐ |
| 1.3 | eGUI compliance survey | ☐ |
| 1.4 | Multi-agent patterns survey | ☐ |
| 1.5 | UI/UX survey | ☐ |
| 1.6 | Survey consolidation | ☐ |
| 2.1 | Legacy data PoC | ☐ |
| 2.2 | Tech viability PoC | ☐ |
| 2.3 | eGUI compliance PoC | ☐ |
| 2.4 | Multi-agent patterns PoC | ☐ |
| 2.5 | UI/UX wireframes | ☐ |
| 2.6 | PoC completion check | ☐ |
| 3.1 | Whole picture doc | ☐ |
