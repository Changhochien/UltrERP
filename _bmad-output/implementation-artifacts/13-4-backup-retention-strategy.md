# Story 13.4: Backup Strategy for 10+ Year Retention

Status: planning

## Story

As a system,
I want to support policy-based 10+ year retention for records,
So that we comply with Taiwan tax requirements.

## Acceptance Criteria

**AC1:** Retention is enforced by record class  
**Given** a record is created in the system  
**When** retention policy is applied  
**Then** the record's class determines retention period (e.g., invoice: 10 years, log: 2 years)  

**AC2:** Backups support 10+ year recovery  
**Given** a backup is created  
**When** recovery is needed within retention window  
**Then** point-in-time recovery is available for the full retention period  
**And** backup integrity is verifiable

**AC3:** Company policy can extend beyond 10 years  
**Given** company policy requires extended retention  
**When** configuration is set  
**Then** the backup and archive policy extends to the configured period  
**And** no records are purged before the extended retention period

**AC4:** Backup strategy is documented and automated**
**Given** the backup strategy is configured  
**When** daily backup runs execute  
**Then** the strategy is documented in code/config  
**And** backups run on schedule without manual intervention

## Tasks / Subtasks

- [ ] **Task 1: Define retention policy schema**
  - [ ] Define `retention_policy` table: id, tenant_id, record_class, retention_years, extended_years (nullable), created_at, updated_at
  - [ ] Create Alembic migration for retention_policy table
  - [ ] Seed default policies: invoice (10 years), payment (10 years), order (10 years), inventory_adjustment (5 years), audit_log (7 years), reconciliation_report (10 years)
  - [ ] Add API: GET /admin/retention-policies, PUT /admin/retention-policies/{id}

- [ ] **Task 2: Implement backup strategy configuration**
  - [ ] Define backup schedule in config: daily pg_dump at 02:00 local, weekly full backup on Sunday
  - [ ] Define retention in config: daily backups kept 7 days, weekly backups kept 12 months, monthly backups kept 10+ years
  - [ ] Extend rclone configuration (AR5) for Cloudflare R2 with lifecycle rules matching retention policy
  - [ ] Document backup verification procedure (pg_restore --verify)

- [ ] **Task 3: Implement pg_dump backup automation**
  - [ ] Create backup script: `scripts/backup.sh` using pg_dump with custom format (-Fc) for compression and point-in-time recovery
  - [ ] Add backup verification step: `pg_restore --verify` after each backup
  - [ ] Generate backup manifest with timestamp, size, checksum (SHA256)
  - [ ] Upload to R2 with rclone, tagging with backup type (daily/weekly/monthly)

- [ ] **Task 4: Configure R2 lifecycle rules for extended retention**
  - [ ] Set R2 lifecycle rule: move to R2 Deep Archive tier after 1 year for monthly backups
  - [ ] Set R2 lifecycle rule: delete after extended_years retention period
  - [ ] Document the tier transition (Standard -> Deep Archive) and its cost implications
  - [ ] Ensure company-policy extended retention overrides default 10-year policy

- [ ] **Task 5: Implement point-in-time recovery capability**
  - [ ] Configure PostgreSQL WAL archiving to R2 for continuous archiving
  - [ ] Document PITR recovery procedure: restore from base backup + replay WAL to target time
  - [ ] Test recovery procedure in staging environment
  - [ ] Store recovery runbook in docs/operations/

- [ ] **Task 6: Add backup monitoring and alerting**
  - [ ] Add backup success/failure notification (email or LINE)
  - [ ] Log backup results to audit_log table
  - [ ] Add API: GET /admin/backup-status returning last backup timestamp, size, verification status
  - [ ] Alert if backup verification fails

- [ ] **Task 7: Document backup strategy**
  - [ ] Write `docs/operations/backup-retention.md` covering: retention policy table, backup schedule, R2 configuration, PITR procedure, recovery runbook
  - [ ] Document how to extend retention for specific record classes
  - [ ] Document backup verification and testing procedure

- [ ] **Task 8: Add focused tests for retention policy**
  - [ ] Test default policies are seeded on migration
  - [ ] Test retention policy update changes effective date for new records
  - [ ] Test PITR recovery restores to correct point in time (staging only)
  - [ ] Test backup verification detects corruption (inject test failure)

## Dev Notes

### Repo Reality

- AR5 already specifies: "rclone + Cloudflare R2 for cloud backups (pg_dump daily, 10+ year retention)"
- AR14 specifies: "NFR15: Retention policy is enforced by record class and issuer-side archival does not depend on MOF platform retention windows"
- The existing backup strategy from Epic 1 (Story 1.4) is the foundation; Epic 13 extends it with formal retention policy and PITR capability
- NFR22: "Database backup strategy must support policy-based 10+ year retention with optional longer company-policy retention"

### Critical Warnings

- Do **not** rely on MOF platform retention windows (FR48 note); issuer-side archival must be independent
- Do **not** use plain-text pg_dump format; use custom format (-Fc) for compression and PITR support
- Do **not** skip WAL archiving; PITR requires continuous WAL archiving, not just base backups
- Do **not** forget backup verification; untested backups are unreliable

### Implementation Direction

- Retention policy is configurable per record class, allowing different retention periods
- Backup automation uses pg_dump + rclone + R2, matching AR5 architecture
- R2 lifecycle rules handle tier transition and deletion automatically
- PITR capability requires PostgreSQL WAL archiving configuration in addition to base backups

### Validation Follow-up

- Confirm that a backup restore successfully recovers all record classes
- Confirm that R2 lifecycle rules are correctly applied to existing objects
- Confirm that PITR recovery is tested and documented in staging
- Confirm that backup monitoring alerts fire on verification failure

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 13 / Story 13.4
- `_bmad-output/planning-artifacts/prd.md` - NFR15 retention by record class, NFR22 10+ year retention
- `_bmad-output/implementation-artifacts/1-4-cloud-backup-strategy.md` - Epic 1 Story 1.4 existing backup strategy
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` - AR5 rclone + R2, AR14 retention policy
- `backend/domains/legacy_import/canonical.py` - audit log pattern for backup event logging
