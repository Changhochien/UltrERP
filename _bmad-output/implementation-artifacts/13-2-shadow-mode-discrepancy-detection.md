# Story 13.2: Shadow-Mode Discrepancy Detection

Status: planning

## Story

As a system,
I want to detect and report discrepancies between old and new systems,
So that we can identify issues before cutover.

## Acceptance Criteria

**AC1:** Discrepancy alerts are generated when differences are found  
**Given** both systems are processing transactions  
**When** a discrepancy is detected between shadow-mode output and legacy source  
**Then** an alert is generated with: discrepancy_id, spec_line_id, expected_value, actual_value, severity, detected_at

**AC2:** Severity-1 discrepancies block cutover  
**Given** a severity_1 discrepancy exists  
**When** cutover readiness is evaluated  
**Then** the cutover is blocked until the discrepancy is resolved  

**AC3:** Daily discrepancy report is generated  
**Given** reconciliation runs daily during parallel run  
**When** a day completes  
**Then** a discrepancy report is generated covering all discrepancies detected that day  

**AC4:** Alerts are actionable  
**Given** a discrepancy alert is created  
**When** an operator views it  
**Then** the alert includes: affected entity type, entity identifier, specific field with mismatch, historical context, suggested investigation steps  

## Tasks / Subtasks

- [ ] **Task 1: Design discrepancy alert schema**
  - [ ] Define `discrepancy_alert` table with id, reconciliation_run_id, spec_line_id, entity_type, entity_id, expected_value, actual_value, severity, status, detected_at, resolved_at, resolved_by, resolution_notes
  - [ ] Create Alembic migration for discrepancy_alert table
  - [ ] Add indexes on (severity, status) and (detected_at) for report queries

- [ ] **Task 2: Implement discrepancy detection engine**
  - [ ] Extend reconciliation engine from Story 13.1 to execute comparison methods
  - [ ] For each spec line, fetch expected value from legacy source (raw_legacy lineage) and actual value from canonical tables
  - [ ] Apply comparison method (EXACT, NUMERIC_TOLERANCE, DATE_TOLERANCE, REFERENCE_MATCH)
  - [ ] Create discrepancy_alert record when comparison fails

- [ ] **Task 3: Implement alert severity blocking**
  - [ ] Add cutover_readiness_check function that queries for open severity_1 discrepancies
  - [ ] Block cutover API when unresolved severity_1 discrepancies exist
  - [ ] Return cutover_readiness report with: eligible (bool), blocking_discrepancies (count), severity_2_warnings (count)

- [ ] **Task 4: Generate daily discrepancy report**
  - [ ] Add reconciliation_report table: id, run_date, spec_version, total_comparisons, discrepancies_found, severity_1_count, severity_2_count, generated_at
  - [ ] Create daily scheduled job (or on-demand endpoint) to generate report
  - [ ] Store report JSON artifact in MinIO for long-term retention
  - [ ] Add API endpoint: GET /reconciliation/reports/{date}

- [ ] **Task 5: Make alerts actionable**
  - [ ] Enrich discrepancy_alert with entity context (customer name, invoice number, product code)
  - [ ] Add historical context: previous reconciliation results for same entity
  - [ ] Add suggested investigation steps based on entity type and comparison field
  - [ ] Add API endpoint: GET /discrepancies/{id} with full context

- [ ] **Task 6: Add notification for critical discrepancies**
  - [ ] Send notification (email or LINE) when new severity_1 discrepancy is detected
  - [ ] Include discrepancy summary and link to detailed report in notification

- [ ] **Task 7: Add focused tests for discrepancy detection**
  - [ ] Test EXACT comparison failure creates severity_2 alert
  - [ ] Test NUMERIC_TOLERANCE passes within tolerance, fails outside
  - [ ] Test severity_1 discrepancy blocks cutover readiness
  - [ ] Test daily report aggregates discrepancies correctly
  - [ ] Test actionable alert contains required context fields

## Dev Notes

### Repo Reality

- The discrepancy detection engine must work against both legacy source data (raw_legacy tables from Epic 15/16) and canonical UltrERP tables
- Lineage join from canonical tables to raw_legacy provides the expected values: `canonical_record_lineage.source_table`, `canonical_record_lineage.source_identifier`
- The existing MINIO integration (FR48, FR49) can store discrepancy report artifacts
- Notification infrastructure may leverage existing LINE integration from Epic 9 or add email via configured SMTP

### Critical Warnings

- Do **not** compare floating-point numeric values without NUMERIC_TOLERANCE; use Python Decimal for currency comparisons
- Do **not** block cutover on severity_2 discrepancies; they are warnings only
- Do **not** miss entity context in alerts; bare field mismatches without identifiers are not actionable

### Implementation Direction

- Discrepancy detection runs as part of the daily reconciliation job, reading spec lines and comparing legacy vs canonical values
- Alert enrichment joins canonical entity tables (invoices, customers, products, orders) for human-readable context
- Report generation aggregates daily alerts and stores JSON in MinIO with date-based path: `reconciliation-reports/{YYYY}/{MM}/{DD}/report.json`

### Validation Follow-up

- Confirm that re-running reconciliation for same transactions does not create duplicate alerts (use ON CONFLICT or upsert logic)
- Confirm that cutover blocking is enforced at the API level and cannot be bypassed
- Confirm that report artifact is retrievable from MinIO after generation

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 13 / Story 13.2
- `_bmad-output/planning-artifacts/prd.md` - NFR20 shadow-mode, AR20 severity-1 blocks cutover
- `_bmad-output/implementation-artifacts/13-1-versioned-reconciliation-spec.md` - Story 13.1 spec schema
- `_bmad-output/implementation-artifacts/15-4-canonical-historical-transaction-import.md` - lineage join pattern
- `_bmad-output/implementation-artifacts/2-5-store-invoice-artifacts-minio.md` - MINIO integration pattern
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` - AR9 discrepancy alerts
