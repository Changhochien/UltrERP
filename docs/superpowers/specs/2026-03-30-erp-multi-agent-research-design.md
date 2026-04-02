# AI-Native ERP: Multi-Agent Research Design

**Date:** 2026-03-30
**Version:** 1.0.0
**Status:** Approved — Ready for Planning

---

## 1. Overview

**Purpose:** Conduct a full proof-of-concept research sprint across 5 areas to establish the complete picture of building an AI-native ERP for Taiwan SMBs, before writing any production code.

**Context:**
- Architecture design is already documented in `design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md`
- Legacy data: 94 tables, 1.1M rows from 聯泰興實業有限公司 (鼎新-style ERP)
- Key known risk: 660 product codes in transaction tables (tbsslipdtx) don't exist in product master (tbsstock)

**Goal:** Each research area produces a working PoC + full findings doc. All 5 areas consolidate into a "Whole Picture" document.

---

## 2. Research Areas

### Area 1: Legacy Data Landscape

**Agent:** `legacy-data-analyst`
**Research deep-dive into:**
- 94 tables, 1.1M rows — full FK relationship map
- The 660 mismatched product codes: root cause analysis, whether a mapping table exists, and resolution strategy
- Data quality issues: nulls, encoding edge cases, ROC date parsing
- Staging schema design: raw import vs. cleaned schema

**PoC:** Staged migration pipeline — legacy CSV files → cleaned PostgreSQL with FK resolution for mismatched codes.

**Success criteria:** Can import all 94 CSVs into PostgreSQL with validated FKs, and the 660 mismatched codes have documented resolution (map table, accept orphans, or reject).

---

### Area 2: Technology Viability

**Agent:** `tech-viability-researcher`
**Validate current versions of:**
- Tauri 2.x — latest release, known issues with Python sidecar on macOS/Windows
- FastMCP 2.0 — stateless HTTP mode, tool registration, scaling behavior
- FastAPI sub-apps (mounts) — isolation properties, internal RPC pattern
- SQLAlchemy 2.0 async — current best practice for connection pooling with PgBouncer

**Reference repos to validate against:**
- `example-tauri-v2-python-server-sidecar` — does it still work with latest Tauri 2.x?
- `modular-monolith-fastapi` — does the mount pattern still work with FastAPI 0.115+?

**PoC:** Minimal Tauri app + Python FastAPI sidecar running on localhost, proving the IPC pattern works with current library versions.

**Success criteria:** A Tauri desktop app can spawn a Python FastAPI server via sidecar and the webview can call `localhost:8000/api/ping` and receive a response.

---

### Area 3: Taiwan eGUI Compliance

**Agent:** `egui-compliance-researcher`
**Research:**
- FIA API — App ID + API Key authentication, endpoint URLs, rate limits
- MIG 4.1 XML schema — full field mapping for invoices (must be effective Jan 1, 2026)
- 48-hour submission window — enforcement mechanism, what happens at hour 49
- Void/reissue rules — same-month constraint, how to handle cross-month voids
- State machine: PENDING → QUEUED → SENT → ACKED | FAILED → RETRYING → DEAD_LETTER

**PoC:** MIG 4.1 XML generator that produces a valid invoice XML + FIA API mock submission showing full lifecycle (submit → ack/reject → retry → dead letter).

**Success criteria:** A Python script can generate a MIG 4.1 compliant XML for a sample invoice and the mock FIA API responds with both ack and reject scenarios.

---

### Area 4: Multi-Agent Patterns

**Agent:** `multi-agent-patterns-researcher`
**Research:**
- FastMCP 2.0 tool design: how to structure tools so Claude Code can use them effectively
- Auth patterns: JWT vs API keys for agent authentication, capability-based ACL design
- MCP OAuth 2.1 flow for agent authorization
- Error handling: structured errors with retry guidance for agents
- Scaling: stateless HTTP mode for horizontal scaling of MCP server

**Reference:** `modelcontextprotocol/servers` — official MCP server patterns

**PoC:** FastMCP 2.0 server exposing `customers.list`, `customers.create`, `invoices.create`, `invoices.list` tools with auth and proper error responses, deployable as a standalone HTTP service.

**Success criteria:** Claude Code can connect to the MCP server, call the tools with proper auth, receive structured responses, and handle retryable errors correctly.

---

### Area 5: UI/UX

**Agent:** `ui-ux-researcher`
**Research:**
- Desktop ERP UX patterns for Taiwan SMB power users (casual vs. power user split)
- Tauri + React component landscape: shadcn/ui + Radix on Tauri viability
- Core screens: customer list, invoice creation/edit, inventory check, order workflow
- Taiwan localization: date formats (ROC), tax ID validation feedback, Traditional Chinese typography
- System tray, notifications — native Tauri integration patterns

**PoC:** High-fidelity wireframes (ASCII or Figma) for 3 core screens:
1. Customer management (list + create/edit)
2. Invoice creation with eGUI state indicator
3. Inventory check with reorder alerts

**Success criteria:** Wireframes demonstrate the casual/power-user split, show Taiwan localization details, and are validated against typical SMB workflows.

---

## 3. Execution Structure

### Phase 1: Sequential Survey (2-3 days)

5 agents run **sequentially** (one at a time), each spending 1 day. This avoids duplicate work and allows dependency mapping.

**Dependency rules:**
- Survey must complete before PoC starts
- Findings memos are shared context for all subsequent agents

**Survey agent outputs (1-page memo each):**
- Known facts
- Unknowns / open questions
- Top 3 risks
- 3-point recommendation

### Phase 2: Parallel PoC Sprint (5-7 days)

5 agents run **in parallel**, each producing:
- Working PoC (code, wireframes, or documents as appropriate)
- Full findings document (2-4 pages)
- Cross-area dependency report (what they learned from other areas that affects their area)

### Phase 3: Consolidation (1 day)

A synthesis agent produces the **"Whole Picture" document** covering:
- Validated architecture decisions
- Remaining unknowns and how to resolve them
- Recommended implementation phasing (from architecture design doc)
- Updated risk register

---

## 4. Agent Infrastructure

**How agents are invoked:**
- Using Claude Code with project context loaded from:
  - `design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md`
  - `legacy-migration-pipeline/` (full directory)
- Each agent operates in its own worktree (see `superpowers:using-git-worktrees`)
- Agents write their outputs to `research/{area}/` directories

**Output structure:**
```
research/
├── legacy-data/
│   ├── 01-survey-memo.md
│   ├── 02-poc/
│   └── 03-findings.md
├── tech-viability/
│   ├── 01-survey-memo.md
│   ├── 02-poc/
│   └── 03-findings.md
├── egui-compliance/
│   ├── 01-survey-memo.md
│   ├── 02-poc/
│   └── 03-findings.md
├── multi-agent-patterns/
│   ├── 01-survey-memo.md
│   ├── 02-poc/
│   └── 03-findings.md
├── ui-ux/
│   ├── 01-survey-memo.md
│   ├── 02-wireframes/
│   └── 03-findings.md
└── 00-consolidation/
    └── whole-picture.md
```

---

## 5. Success Criteria

| Area | Survey Done | PoC Works | Findings Doc |
|------|-------------|-----------|--------------|
| Legacy Data | 1-page memo | Migration pipeline | 2-4 pages |
| Tech Viability | 1-page memo | Tauri+FastAPI sidecar | 2-4 pages |
| eGUI Compliance | 1-page memo | MIG 4.1 XML + FIA mock | 2-4 pages |
| Multi-Agent Patterns | 1-page memo | FastMCP server with tools | 2-4 pages |
| UI/UX | 1-page memo | 3 wireframe screens | 2-4 pages |

**Gate:** Research phase is complete when all 5 areas have working PoCs and full findings docs, plus a consolidated "Whole Picture" document.

---

## 6. Known Dependencies

- Tech Viability PoC depends on: Legacy Data (needs clean DB to query)
- eGUI Compliance PoC depends on: Tech Viability (needs FastAPI running)
- Multi-Agent Patterns PoC depends on: Tech Viability (needs MCP server scaffold)
- UI/UX depends on: eGUI Compliance (eGUI state indicator on invoices)

These dependencies are **intentional** — Wave 2 areas build on Wave 1 findings.

---

## 7. Out of Scope

- Production code (no FastAPI routes, no Tauri app production build)
- Real FIA API credentials or production eGUI submission
- Database migrations or Alembic setup
- Frontend components beyond wireframes
- Authentication beyond mock/skeleton implementations
