# Story 13.3: 30-Day Parallel Run

Status: planning

## Story

As a system,
I want to run in shadow-mode for 30 days with zero unresolved severity-1 discrepancies,
So that we can confidently cutover to the new system.

## Acceptance Criteria

**AC1:** Parallel run is tracked with start and end dates  
**Given** a parallel run is initiated  
**When** the operator starts shadow-mode  
**Then** a parallel_run record is created with: run_id, start_date, end_date, status (active|completed|cancelled), spec_version

**AC2:** Daily reconciliation continues for 30 days  
**Given** parallel run is active  
**When** each day completes  
**Then** reconciliation runs against that day's transactions  
**And** discrepancies are recorded and reported per Story 13.2

**AC3:** Cutover is cleared when conditions are met  
**Given** 30 days have passed since parallel run start  
**When** cutover readiness is evaluated  
**Then** system checks for zero unresolved severity_1 discrepancies  
**And** if cleared, generates cutover readiness report  
**And** cutover readiness report includes: run duration, total comparisons, total discrepancies (by severity), days with zero severity_1

**AC4:** Operator can view parallel run progress dashboard**
**Given** parallel run is active or completed  
**When** operator views the dashboard  
**Then** they see: days elapsed / days total, current discrepancy counts by severity, trend chart of daily discrepancies, days since last severity_1

## Tasks / Subtasks

- [ ] **Task 1: Design parallel run tracking schema**
  - [ ] Define `parallel_run` table: id, tenant_id, start_date, end_date, target_end_date, status, spec_version, created_by, completed_at
  - [ ] Create Alembic migration for parallel_run table
  - [ ] Add indexes on (tenant_id, status) for dashboard queries

- [ ] **Task 2: Implement parallel run lifecycle**
  - [ ] Add API: POST /reconciliation/parallel-runs to start a new parallel run (validates no active run exists)
  - [ ] Add API: GET /reconciliation/parallel-runs/{id} to get run status
  - [ ] Add API: POST /reconciliation/parallel-runs/{id}/complete to mark run as completed
  - [ ] Add API: POST /reconciliation/parallel-runs/{id}/cancel to cancel active run
  - [ ] Auto-set target_end_date = start_date + 30 days on creation

- [ ] **Task 3: Integrate daily reconciliation with parallel run**
  - [ ] Modify reconciliation job to link to active parallel_run
  - [ ] Store reconciliation_run_id in discrepancy_alert and reconciliation_report
  - [ ] Ensure daily reconciliation does not run without an active parallel_run

- [ ] **Task 4: Implement cutover readiness evaluation**
  - [ ] Add cutover_readiness_check(parallel_run_id) function
  - [ ] Check: days_elapsed >= 30
  - [ ] Check: unresolved severity_1 count == 0
  - [ ] Generate cutover readiness report with all metrics
  - [ ] Add API: GET /reconciliation/parallel-runs/{id}/cutover-readiness

- [ ] **Task 5: Build parallel run dashboard**
  - [ ] Add API: GET /reconciliation/parallel-runs/dashboard returning: days_elapsed, days_total, severity_1_count, severity_2_count, daily_trend, days_since_severity_1
  - [ ] Frontend component: ParallelRunDashboard showing progress bar, discrepancy summary, trend chart
  - [ ] Alert banner when severity_1 is detected during active run

- [ ] **Task 6: Handle cutover clearance workflow**
  - [ ] When cutover is cleared, generate final report and store in MinIO
  - [ ] Send notification to operators when cutover is cleared
  - [ ] Allow operator to initiate cutover (epic-dependent; may be separate story)

- [ ] **Task 7: Add focused tests for parallel run lifecycle**
  - [ ] Test parallel run creation with auto-calculated end date
  - [ ] Test starting run fails when active run exists
  - [ ] Test cutover readiness blocked before 30 days
  - [ ] Test cutover readiness blocked with unresolved severity_1
  - [ ] Test cutover readiness cleared after 30 days with zero severity_1
  - [ ] Test dashboard returns correct aggregation metrics

## Dev Notes

### Repo Reality

- The 30-day parallel run is the operational culmination of Epic 13, building on the spec (13.1) and discrepancy detection (13.2)
- Parallel run must be tenant-scoped (NFR31) even if only one tenant is migrating initially
- Dashboard should use the existing React frontend infrastructure from Epics 7 and 12
- MinIO storage for reports and final cutover artifact aligns with FR48/FR49 patterns

### Critical Warnings

- Do **not** allow cutover clearance without the 30-day duration check; even a single unresolved severity_1 should block regardless of duration
- Do **not** auto-complete the parallel run at 30 days if discrepancies exist; the run must remain active until cleared
- Do **not** skip the daily reconciliation during the 30-day window; gaps in coverage invalidate the validation

### Implementation Direction

- Parallel run tracks the full migration validation window from first day of shadow-mode operation
- Daily reconciliation (Story 13.2) becomes a requirement during the parallel run; the run cannot proceed without it
- Dashboard provides at-a-glance readiness status for operators, similar to Epic 7 dashboard patterns
- Final cutover clearance generates a formal report artifact stored in MinIO for audit trail

### Validation Follow-up

- Confirm that dashboard reflects real-time discrepancy counts as alerts are created
- Confirm that parallel run status transitions correctly (active -> completed or active -> cancelled)
- Confirm that cutover readiness report is complete and meets operator expectations for cutover decision

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 13 / Story 13.3
- `_bmad-output/planning-artifacts/prd.md` - NFR20 shadow-mode validation
- `_bmad-output/implementation-artifacts/13-1-versioned-reconciliation-spec.md` - Story 13.1
- `_bmad-output/implementation-artifacts/13-2-shadow-mode-discrepancy-detection.md` - Story 13.2
- `_bmad-output/implementation-artifacts/7-1-morning-dashboard-revenue-comparison.md` - Epic 7 dashboard pattern
- `_bmad-output/implementation-artifacts/2-5-store-invoice-artifacts-minio.md` - MINIO artifact storage
