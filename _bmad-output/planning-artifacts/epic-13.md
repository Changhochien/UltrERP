## Epic 13: Shadow-Mode Validation

### Epic Goal

System validates correctness against legacy ERP during parallel run before cutover.

### Stories

### Story 13.1: Versioned Reconciliation Spec

As a system,
I want to use a versioned reconciliation specification,
So that we can track what should be compared during shadow-mode.

**Acceptance Criteria:**

**Given** shadow-mode is running
**When** comparing systems
**Then** the comparison follows the versioned reconciliation spec
**And** spec covers: invoice totals/tax, payments, inventory movements, customer balances, order status
**And** severity levels are defined: severity_1 (blocking), severity_2 (warning)

### Story 13.2: Shadow-Mode Discrepancy Detection

As a system,
I want to detect and report discrepancies between old and new systems,
So that we can identify issues before cutover.

**Acceptance Criteria:**

**Given** both systems are processing transactions
**When** a discrepancy is detected
**Then** an alert is generated
**And** severity_1 discrepancies block cutover
**And** discrepancy report is generated daily
**And** alerts are actionable (not vague warnings)

### Story 13.3: 30-Day Parallel Run

As a system,
I want to run in shadow-mode for 30 days with zero unresolved severity-1 discrepancies,
So that we can confidently cutover to the new system.

**Acceptance Criteria:**

**Given** shadow-mode has been running
**When** 30 days have passed with zero unresolved severity-1 discrepancies
**Then** the system is cleared for cutover
**And** a cutover readiness report is generated

### Story 13.4: Backup Strategy for 10+ Year Retention

As a system,
I want to support policy-based 10+ year retention for records,
So that we comply with Taiwan tax requirements.

**Acceptance Criteria:**

**Given** retention policies are configured
**When** records are stored
**Then** retention is enforced by record class
**And** backups support 10+ year recovery
**And** company-policy can extend beyond 10 years

---

