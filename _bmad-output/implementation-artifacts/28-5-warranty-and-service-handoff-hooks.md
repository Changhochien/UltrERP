# Story 28.5: Warranty and Service Handoff Hooks

**Status:** ready-for-dev

**Story ID:** 28.5

**Epic:** Epic 28 - Workforce, Contacts, and Service Desk Foundations

---

## Story

As a service coordinator or warranty administrator,
I want issues to capture warranty-relevant customer, product, and serial context,
so that support can triage service work now and hand the same record into future traceability and asset workflows later.

---

## Problem Statement

An issue queue alone is not enough for service operations that touch sold products, serialised goods, or warranty windows. Without structured product, customer, contact, and serial context, service teams lose the information needed to triage warranty cases and later asset or repair workflows have no clean handoff from the original issue. Epic 28 needs lightweight warranty-ready hooks now so later traceability and maintenance stories extend a stable issue record instead of replacing it.

## Solution

Extend the issue foundation so that it:

- captures optional warranty context on issues for customer, contact, product, serial, warranty status, and service address
- keeps the current issue queue simple while making warranty-related cases filterable and audit-friendly
- remains compatible with future typed serial and asset masters without forcing those domains to ship first

Keep the first slice narrow. Land structured warranty context and triage views while deferring AMC contracts, maintenance visits, repair scheduling, spare-part consumption, and full field-service operations.

## Acceptance Criteria

1. Given a warranty-related issue is logged, when the record is saved, then the relevant customer, contact, product, serial or serial text, and warranty status or expiry context can be attached to the issue.
2. Given service later extends into asset repair or maintenance, when those stories reuse the issue record, then the existing warranty context remains structured and reusable rather than trapped in freeform notes.
3. Given current users work only with issues, when the issue queue is viewed, then warranty hooks add clear optional context and filters without complicating the core non-warranty workflow.
4. Given a serial or asset master is not yet available, when service staff still need to log a warranty case, then the issue can preserve structured text context that can later be reconciled to typed masters.

## Tasks / Subtasks

- [ ] Task 1: Extend issue persistence with warranty context. (AC: 1-4)
  - [ ] Add a one-to-one `IssueWarrantyContext` subordinate model under `backend/domains/issues/models.py` rather than scattering more nullable fields across the core issue row.
  - [ ] Store product, customer, contact, serial reference or serial text, warranty status, warranty expiry, service address, and raised-by context.
  - [ ] Add the required Alembic migration under `migrations/versions/`.
- [ ] Task 2: Implement warranty-context services and filters. (AC: 1-4)
  - [ ] Add service logic to create and update warranty context alongside issues.
  - [ ] Validate typed foreign keys where masters already exist, while allowing explicit text fallback for serial or asset identifiers that have not landed yet.
  - [ ] Add queue filters for warranty status, product, and serial or reference context.
- [ ] Task 3: Expose APIs and UI support for warranty-aware issues. (AC: 1-3)
  - [ ] Extend issue routes and schemas with warranty-context request and response shapes.
  - [ ] Add frontend form and detail sections that surface warranty-specific fields only when relevant.
- [ ] Task 4: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for optional warranty-context creation, text fallback behavior, and queue filtering.
  - [ ] Add frontend tests for conditional warranty fields and warranty-aware queue badges or filters.

## Dev Notes

### Context

- Epic 28 explicitly wants warranty-claim-ready linkage from issues to customers, products, and serialized inventory where applicable.
- Vendored ERPNext warranty-claim references show the practical fields worth preserving in the issue model: customer, contact person, serial, item, warranty or AMC status, service address, raised-by context, and resolution details.
- Epic 29 serial traceability and Epic 31 asset lifecycle will deepen the typed references later, so this story should preserve enough structured context to bridge to them without forcing those domains first.

### Architecture Compliance

- Implement warranty hooks as an extension of the `issues` domain through a one-to-one context record rather than as a separate warranty-ticket subsystem.
- Prefer typed foreign keys where UltrERP already has the master record, but keep an explicit text fallback for serial or asset identifiers that do not yet exist as first-class records.
- Keep warranty metadata optional so non-warranty issues remain uncluttered.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/issues/models.py`
  - `backend/domains/issues/schemas.py`
  - `backend/domains/issues/service.py`
  - `backend/domains/issues/routes.py`
  - `backend/domains/issues/warranty.py` only if a separate service helper keeps the issue service from sprawling
  - `migrations/versions/*_issue_warranty_context.py`
- Likely frontend files:
  - `src/lib/api/issues.ts`
  - `src/domain/issues/types.ts`
  - `src/domain/issues/components/IssueWarrantySection.tsx`
  - `src/pages/issues/IssueDetailPage.tsx`
  - `src/pages/issues/IssueQueuePage.tsx`
- If a separate asset master later lands, migrate from explicit `serial_text` fallback to a typed reference without changing the outer issue contract.

### What NOT to implement

- Do **not** implement AMC contract management, maintenance visits, repair scheduling, or RMA workflows in this story.
- Do **not** require typed serial or asset masters before support can log a warranty-aware issue.
- Do **not** split warranty work into a second queue unless a later story proves the workflows truly diverge.

### Testing Standards

- Include a regression proving warranty context stays optional and does not break plain issue creation.
- Include a regression proving typed references and text fallback both survive issue updates and list filtering.
- Keep frontend locale files synchronized if warranty labels are added.

## Dependencies & Related Stories

- **Depends on:** Story 28.4
- **Related to:** Story 29.2 for serial traceability, Story 31.1 and Story 31.2 for asset and repair reuse

## References

- `../planning-artifacts/epic-28.md`
- `../planning-artifacts/epic-31.md`
- `reference/erpnext-develop/erpnext/support/doctype/warranty_claim/warranty_claim.json`
- `https://docs.frappe.io/erpnext/warranty-claim`
- `reference/erpnext-develop/erpnext/support/doctype/issue/issue.json`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 28 warranty-handoff scope, ERPNext warranty-claim references, and the planned compatibility with future traceability and asset stories.

### File List

- `_bmad-output/implementation-artifacts/28-5-warranty-and-service-handoff-hooks.md`