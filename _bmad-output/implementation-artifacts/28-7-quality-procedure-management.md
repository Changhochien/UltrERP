# Story 28.7: Quality Procedure Management

**Status:** ready-for-dev

**Story ID:** 28.7

**Epic:** Epic 28 - Workforce, Contacts, and Service Desk Foundations

---

## Story

As a quality manager,
I want versioned quality procedures with hierarchy and acknowledgment tracking,
so that NCRs, inspections, and recurring quality work reference governed SOPs instead of scattered documents.

---

## Problem Statement

UltrERP has no first-class SOP or quality-procedure model today. Without governed procedures, inspection plans, NCRs, and later quality reviews would either link to external files or duplicate operating instructions inside every record. Epic 28 needs a quality-procedure backbone before quality incidents, corrective actions, and quality goals can anchor themselves to stable process definitions.

## Solution

Add a quality-procedure foundation that:

- creates `QualityProcedure` records with tree-style hierarchy and immutable revision history
- tracks effective dates, responsible department or owner, review cadence, and employee acknowledgments
- links procedures to future NCRs, CAPAs, and inspections without requiring a full document-management platform

Keep the first slice governed but narrow. Land procedure hierarchy, revision history, and acknowledgment tracking while deferring e-signature suites, LMS depth, graphical flowchart editors, and heavy attachment-management features.

## Acceptance Criteria

1. Given a quality manager creates a procedure, when it is saved, then title, owner, department, content, effective dates, and review schedule are stored on a dedicated procedure record.
2. Given a procedure is revised, when a new active version is published, then prior revisions remain queryable and superseded without overwriting historical content.
3. Given a procedure has sub-procedures, when users browse the quality-procedure workspace, then the hierarchy is navigable in a tree view without losing the ability to open a single procedure detail record.
4. Given employees acknowledge procedure training, when auditors review the procedure, then acknowledgments are timestamped and linked to the relevant revision.

## Tasks / Subtasks

- [ ] Task 1: Add procedure, revision, and acknowledgment persistence. (AC: 1-4)
  - [ ] Add `QualityProcedure`, `QualityProcedureRevision`, and `ProcedureAcknowledgment` ORM models under `backend/domains/quality/models.py`.
  - [ ] Store procedure fields for title, code, department, owner, status, effective dates, review due date, parent procedure, and display order.
  - [ ] Store immutable revision snapshots for procedure content and metadata.
  - [ ] Add the required Alembic migration under `migrations/versions/`.
- [ ] Task 2: Implement procedure lifecycle and hierarchy services. (AC: 1-4)
  - [ ] Add service methods to create, revise, activate, supersede, archive, and browse procedures.
  - [ ] Keep hierarchy navigation explicit with parent-child relationships rather than requiring a copy of Frappe's nested-set internals.
  - [ ] Add review-due queries and acknowledgment capture tied to specific revisions.
- [ ] Task 3: Expose APIs and build the procedure workspace. (AC: 1-4)
  - [ ] Add `backend/domains/quality/routes.py` endpoints for tree listing, detail, revision history, and acknowledgment operations.
  - [ ] Add frontend pages under `src/pages/quality/` for procedure tree and detail views plus revision history.
  - [ ] Add `src/domain/quality/` hooks and components for procedure forms, revision tables, and acknowledgment panels.
- [ ] Task 4: Add link-ready surfaces for related quality records. (AC: 1-3)
  - [ ] Provide procedure references that later NCR, CAPA, and inspection screens can reuse.
  - [ ] Expose procedure-summary payloads for related-record sidebars instead of forcing duplicate procedure fetching everywhere.
- [ ] Task 5: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for revision immutability, tree navigation, and acknowledgment capture.
  - [ ] Add frontend tests for tree rendering, revision history, and acknowledgment submission.

## Dev Notes

### Context

- Epic 28 requires quality procedures before later NCR and quality-goal work becomes meaningful.
- Vendored ERPNext quality-procedure references show the core upstream ideas worth reusing here: procedure hierarchy, process ownership, and links into other quality records.
- The official ERPNext docs frame a procedure as an SOP that can contain steps and sub-procedures, which fits the tree-style workspace Epic 28 describes.

### Architecture Compliance

- Implement quality procedures inside the shared `backend/domains/quality/` domain.
- Use a simple adjacency-list tree with `parent_id` plus ordering metadata unless the repo already has a reusable tree utility; do not force Frappe-style `lft`/`rgt` internals into SQLAlchemy just for parity.
- Keep procedure content as markdown or rich text plus metadata; treat binary attachments as optional references rather than requiring a new document-management subsystem.
- Link acknowledgments to both employee and revision so audit review stays precise.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/quality/models.py`
  - `backend/domains/quality/schemas.py`
  - `backend/domains/quality/service.py`
  - `backend/domains/quality/routes.py`
  - `migrations/versions/*_quality_procedures.py`
- Likely frontend files:
  - `src/lib/api/quality.ts`
  - `src/domain/quality/types.ts`
  - `src/domain/quality/hooks/useQualityProcedures.ts`
  - `src/domain/quality/components/QualityProcedureForm.tsx`
  - `src/domain/quality/components/QualityProcedureTree.tsx`
  - `src/pages/quality/QualityProcedurePage.tsx`
  - `src/pages/quality/QualityProcedureDetailPage.tsx`
- If review reminders are surfaced, make them explicit due-date queries first; do not build a separate scheduler in this story.

### What NOT to implement

- Do **not** implement e-signature workflows, SCORM or LMS features, or a graphical flowchart editor in this story.
- Do **not** require a full attachment platform before procedure content can go live.
- Do **not** overwrite active procedure content in place when a revision is needed.

### Testing Standards

- Include a regression proving prior revisions remain queryable after a new active version is published.
- Include a regression proving acknowledgments are tied to the exact revision acknowledged.
- Keep frontend locale files synchronized if quality-procedure labels are added.

## Dependencies & Related Stories

- **Blocks:** Story 28.6, Story 28.8
- **Related to:** Story 29.1 for inspection references, Story 28.6 for NCR root-cause context

## References

- `../planning-artifacts/epic-28.md`
- `../planning-artifacts/epic-29.md`
- `reference/erpnext-develop/erpnext/quality_management/doctype/quality_procedure/quality_procedure.json`
- `https://docs.frappe.io/erpnext/quality_procedure`
- `backend/common/models/audit_log.py`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 28 quality-procedure scope, ERPNext quality-procedure references, and the current UltrERP quality-domain planning seams.

### File List

- `_bmad-output/implementation-artifacts/28-7-quality-procedure-management.md`