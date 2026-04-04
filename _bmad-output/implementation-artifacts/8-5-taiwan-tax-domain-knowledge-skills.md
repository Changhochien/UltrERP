# Story 8.5: Taiwan Tax Domain Knowledge (Skills)

Status: complete

## Story

As an AI agent,
I want Claude Code to use Taiwan tax domain knowledge from Skills files,
So that I can answer tax-related questions correctly.

## Acceptance Criteria

**AC1:** Skills entry point exists
**Given** Claude Code is configured with the ERP skills directory
**When** the agent loads SKILL.md
**Then** it finds the root `erp-skills/SKILL.md` entry point
**And** the entry point describes available sub-skills and when to use them

**AC2:** Taiwan eGUI skill provides tax rate knowledge
**Given** Claude Code encounters a question about Taiwan tax rates
**When** it reads `erp-skills/taiwan-egui/SKILL.md`
**Then** it learns: standard 5% VAT, zero-rated export, tax-exempt categories
**And** reference file `tax-rates.md` contains detailed rate tables and examples

**AC3:** Taiwan business-number checksum rules available
**Given** Claude Code encounters a question about 統一編號 validation
**When** it reads the taiwan-egui skill reference files
**Then** it learns the Taiwan Unified Business Number (UBN) validation algorithm
**And** the checksum logic is documented with step-by-step computation and examples

**AC4:** Regulatory void-window policy documented
**Given** Claude Code encounters a question about invoice void rules
**When** it reads the taiwan-egui skill reference files
**Then** it learns: invoices can only be void within the same filing period (bi-monthly)
**And** the void deadline computation is documented with examples
**And** references the `compute_void_deadline()` function in the codebase

**AC5:** MIG 4.1 data shape documented
**Given** Claude Code encounters a question about eGUI invoice format
**When** it reads `erp-skills/taiwan-egui/reference/mig41.md`
**Then** it learns the MIG 4.1 XML data shape for electronic invoice submission
**And** includes field mapping from UltrERP invoice model to MIG 4.1 format

**AC6:** Skills reference existing codebase
**Given** the skills files are created
**When** Claude Code reads them
**Then** each skill references the relevant backend code paths
**And** for example, `taiwan-egui/SKILL.md` points to `backend/domains/invoices/service.py`

**AC7:** Files are well-structured markdown
**Given** all skills files
**When** they are created
**Then** each follows a consistent SKILL.md format with: Overview, When to Use, Key Concepts, Reference Files section
**And** total file count is manageable (≤ 10 files including references)

## Tasks / Subtasks

- [ ] **Task 1: Create skills directory structure** (AC1)
  - [ ] Create directory: `erp-skills/`
  - [ ] Create `erp-skills/SKILL.md`:
    ```markdown
    # UltrERP Domain Knowledge

    ## Overview
    Domain knowledge skills for UltrERP — a Taiwan-focused ERP system.

    ## Available Skills

    ### Taiwan eGUI & Tax
    - **Path:** `taiwan-egui/SKILL.md`
    - **Use when:** Questions about Taiwan tax rates, VAT, business number
      validation, invoice void rules, eGUI submission, MIG 4.1 format

    ### Inventory Management
    - **Path:** `inventory/SKILL.md`
    - **Use when:** Questions about reorder logic, stock adjustment workflow

    ## Codebase References
    - Backend business logic: `backend/domains/`
    - MCP tools: `backend/domains/*/mcp.py`
    ```

- [ ] **Task 2: Create Taiwan eGUI skill** (AC2, AC3, AC4, AC5)
  - [ ] Create `erp-skills/taiwan-egui/SKILL.md`:
    - Overview of Taiwan electronic invoice (eGUI) system
    - When to use this skill
    - Key concepts: VAT rates, UBN validation, void windows, filing periods
    - Reference files listing
    - Codebase references: `backend/domains/invoices/service.py`
  - [ ] Create `erp-skills/taiwan-egui/reference/tax-rates.md`:
    - Standard 5% VAT rate
    - Zero-rated exports (0%)
    - Tax-exempt categories
    - Tax calculation: `tax_amount = total_amount * 0.05`
    - Examples with TWD amounts
  - [ ] Create `erp-skills/taiwan-egui/reference/mig41.md`:
    - MIG 4.1 data shape overview
    - Required fields for B2B and B2C invoices
    - Field mapping from UltrERP Invoice model to MIG 4.1 XML
    - eGUI states: draft → submitted → accepted/rejected
    - Note: Live eGUI submission is feature-flagged (not active yet)
  - [ ] Create `erp-skills/taiwan-egui/reference/void-rules.md`:
    - Invoice void policy: same filing period (bi-monthly)
    - Filing periods: Jan-Feb, Mar-Apr, May-Jun, Jul-Aug, Sep-Oct, Nov-Dec
    - Void deadline computation: last day of the invoice's filing period
    - Reference: `compute_void_deadline()` in `backend/domains/invoices/service.py`
    - Examples with specific dates
  - [ ] Create `erp-skills/taiwan-egui/reference/ubn-validation.md`:
    - Taiwan Unified Business Number (統一編號) format: 8 digits
    - Validation algorithm steps
    - Weights: [1, 2, 1, 2, 1, 2, 4, 1]
    - Special case: digit 7 (if resulting checksum digit 6 is 7, two valid sums)
    - Examples of valid and invalid UBNs
    - Reference: validation in `backend/domains/customers/service.py`
  - [ ] Create `erp-skills/taiwan-egui/reference/submission.md` (per architecture §4.6):
    - eGUI submission workflow overview
    - FIA (Fiscal Information Agency) submission process
    - Submission states and retry logic
    - Feature flag: `eGUI submission is feature-flagged (not active yet)`
    - Reference: `backend/domains/invoices/service.py`
  - [ ] Create `erp-skills/taiwan-egui/reference/states.md` (per architecture §4.6):
    - eGUI invoice state machine: PENDING → QUEUED → SENT → ACKED
    - Error states and transitions
    - State persistence and retry semantics
    - Reference: architecture v2 §5.2

- [ ] **Task 3: Create Inventory skill** (AC6, AC7)
  - [ ] Create `erp-skills/inventory/SKILL.md`:
    - Overview of inventory management in UltrERP
    - Reorder point logic and alert system
    - Stock adjustment workflow with reason codes
    - Supplier order lifecycle
    - Codebase references: `backend/domains/inventory/services.py` (note: plural)
  - [ ] Create `erp-skills/inventory/reference/reorder.md` (per architecture §4.6):
    - Reorder point calculation and alert triggers
    - Alert statuses: PENDING, ACKNOWLEDGED, RESOLVED
    - Reference: `list_reorder_alerts()` in `backend/domains/inventory/services.py`
  - [ ] Create `erp-skills/inventory/reference/suppliers.md` (per architecture §4.6):
    - Supplier order lifecycle and statuses
    - Receiving workflow
    - Reference: `create_supplier_order()`, `receive_supplier_order()` in `backend/domains/inventory/services.py`

- [ ] **Task 4: Note deferred skills** (AC7)
  - [ ] Add a comment in `erp-skills/SKILL.md` noting that `sales-workflow/` skill (architecture §4.6) is deferred to a future epic covering orders and pricing domains

## Dev Notes

### Architecture Compliance
- **§4.6:** Skills directory structure matches architecture specification exactly
- **PRD Innovation Pattern 1:** MCP gives agents access; Skills give agents domain knowledge
- **FR32:** Claude Code can use Taiwan tax domain knowledge from Skills files
- **This story is frontend/backend code-free** — it creates markdown reference files only

### Critical Warnings
- ⚠️ This story creates documentation files only — no Python or TypeScript code changes.
- ⚠️ Tax rate information must be accurate for Taiwan. Standard VAT is 5% (not 10% or other rates).
- ⚠️ UBN validation algorithm must match what's implemented in `backend/domains/customers/service.py`. Read the actual validation code before writing the reference.
- ⚠️ Void window computation must match `compute_void_deadline()` implementation. Read the actual function before documenting.
- ⚠️ Do NOT include real customer data, real UBNs, or PII in examples. Use synthetic examples.
- ⚠️ Inventory service file is `services.py` (plural), not `service.py`.

### Project Structure Notes
- `erp-skills/SKILL.md` — NEW: root entry point
- `erp-skills/taiwan-egui/SKILL.md` — NEW: Taiwan tax skill
- `erp-skills/taiwan-egui/reference/tax-rates.md` — NEW: tax rate reference
- `erp-skills/taiwan-egui/reference/mig41.md` — NEW: MIG 4.1 format reference
- `erp-skills/taiwan-egui/reference/void-rules.md` — NEW: void window policy
- `erp-skills/taiwan-egui/reference/ubn-validation.md` — NEW: business number validation
- `erp-skills/taiwan-egui/reference/submission.md` — NEW: eGUI submission workflow (per architecture §4.6)
- `erp-skills/taiwan-egui/reference/states.md` — NEW: eGUI state machine (per architecture §4.6)
- `erp-skills/inventory/SKILL.md` — NEW: inventory management skill
- `erp-skills/inventory/reference/reorder.md` — NEW: reorder point reference (per architecture §4.6)
- `erp-skills/inventory/reference/suppliers.md` — NEW: supplier order reference (per architecture §4.6)
- `erp-skills/sales-workflow/` — DEFERRED: to a future epic (architecture §4.6 lists it)

### Previous Story Intelligence
- **Existing validation code:** `backend/domains/customers/service.py` contains the Taiwan UBN validation logic — must read and match
- **Existing void logic:** `backend/domains/invoices/service.py` contains `compute_void_deadline()` — must read and match
- **Architecture §4.6:** Shows the exact directory structure for skills files
- **PRD:** eGUI submission is feature-flagged — skills should note this clearly

### References
- Architecture v2 §4.6 (Claude Skills)
- PRD: FR32, Innovation Patterns section
- Backend: `backend/domains/invoices/service.py` (void deadline, tax calc)
- Backend: `backend/domains/customers/service.py` (UBN validation)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (fast mode)

### Completion Notes List
- Created 11 markdown files in `erp-skills/` directory
- Root: `SKILL.md` with available skills and deferred sales-workflow note
- Taiwan eGUI: `SKILL.md` + 6 reference files (tax-rates, ubn-validation, void-rules, mig41, submission, states)
- Inventory: `SKILL.md` + 2 reference files (reorder, suppliers)
- UBN algorithm verified against `backend/common/validators.py` — mod-5, weights (1,2,1,2,1,2,4,1), digit-7 special case
- Void deadline verified against `compute_void_deadline()` — bimonthly periods, 15th deadline
- No Python code changes, no tests needed
