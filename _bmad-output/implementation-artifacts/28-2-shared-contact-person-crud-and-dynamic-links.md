# Story 28.2: Shared Contact-Person CRUD and Dynamic Links

**Status:** ready-for-dev

**Story ID:** 28.2

**Epic:** Epic 28 - Workforce, Contacts, and Service Desk Foundations

---

## Story

As a sales, procurement, or service user,
I want standalone contact-person records that can be linked to customers, suppliers, CRM records, and issues,
so that the same human record can be reused across workflows without duplicating names, emails, or phone numbers.

---

## Problem Statement

UltrERP's current domains still lean on record-local contact fields. CRM can capture lead data, orders and procurement need named people, and the portal or engagement roadmap depends on stable human identities. If Epic 28 does not centralize contacts now, later portal access, service tickets, and omnichannel history will fragment across duplicate or stale contact fields scattered across separate modules.

## Solution

Add a shared contact foundation that:

- creates tenant-scoped `Contact` records with primary communication and organization context
- adds a generic `ContactLink` relation that points at allowed business objects through an explicit `entity_type` and `entity_id` contract
- preserves historical meaning by letting links end or change role without deleting the underlying person record

Keep the first slice pragmatic. Land primary phone or email, role, company or title, active or inactive state, and reusable links while deferring address-book merge tooling, portal credentials, social profiles, and full communication-preference management.

## Acceptance Criteria

1. Given a customer, supplier, CRM record, or issue needs a named person, when a contact is selected or created, then the system stores that human as a standalone reusable contact record instead of another embedded freeform field.
2. Given one contact is linked to multiple records, when any linked record is viewed, then the relationship is explicit through a dynamic-link relation that identifies the business object type, role, and primary-contact status.
3. Given a contact changes role or leaves, when the active link is ended or replaced, then historical business records remain understandable without deleting the person record or erasing prior ownership context.
4. Given later portal or omnichannel work needs stable party and person identity, when Story 30.1 or Story 30.5 reuses contacts, then the shared contact model does not require a second portal-specific contact system.
5. Given a user starts creating a contact that appears to already exist, when the primary email or phone collides within the same tenant, then the system returns duplicate-reuse guidance instead of silently creating another likely duplicate.

## Tasks / Subtasks

- [ ] Task 1: Add contact and contact-link persistence. (AC: 1-4)
  - [ ] Add `Contact` and `ContactLink` ORM models under `backend/domains/contacts/models.py`.
  - [ ] Store core fields for full name, role title, organization name, primary email, primary phone, notes, and active status.
  - [ ] Store link fields for `entity_type`, `entity_id`, `role_label`, `is_primary`, `valid_from`, and `valid_to` or equivalent lifecycle markers.
  - [ ] Add the required Alembic migration under `migrations/versions/`.
- [ ] Task 2: Implement CRUD, reuse, and lifecycle-safe linking services. (AC: 1-5)
  - [ ] Add create, update, list, detail, deactivate, link, unlink, and relink service methods.
  - [ ] Validate `entity_type` against an explicit initial allowlist of `customer`, `supplier`, `lead`, `opportunity`, and `issue` rather than permitting arbitrary table names.
  - [ ] Add duplicate-suggestion rules that prefer reusing an existing contact when name plus primary email or phone already matches within the tenant.
- [ ] Task 3: Expose APIs and reusable selector surfaces. (AC: 1-4)
  - [ ] Add `backend/domains/contacts/routes.py` endpoints for contact CRUD and contact-link operations.
  - [ ] Return linked-record summaries so CRM, supplier, customer, and issue UIs can show contact context without rehydrating every parent record.
- [ ] Task 4: Build the contacts workspace in the frontend. (AC: 1-3)
  - [ ] Add `src/pages/contacts/` list and detail pages plus a link-management panel.
  - [ ] Add `src/domain/contacts/` hooks, form components, and types plus `src/lib/api/contacts.ts`.
  - [ ] Provide a shared contact picker component for later use in customer, supplier, CRM, and issue forms.
- [ ] Task 5: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for link-allowlist validation, duplicate suggestions, primary-contact switching, and historical-link preservation.
  - [ ] Add frontend tests for contact creation, linking, relinking, and primary-contact display.

## Dev Notes

### Context

- Epic 28 makes shared contacts the system of record for customers, suppliers, CRM, and service flows.
- The vendored ERPNext tree does not expose a directly reusable contact doctype inside `reference/erpnext-develop/erpnext/`, so UltrERP should define its own contact model rather than assume hidden Frappe internals.
- Frappe's Dynamic Link guidance confirms the upstream pattern is an explicit type-plus-record indirection rather than a separate embedded contact schema on every business record.

### Architecture Compliance

- Create a dedicated `backend/domains/contacts/` domain and register it in `backend/app/main.py`.
- Express dynamic relationships as a validated relation table, not as raw unvalidated text fields repeated across domains.
- Keep the initial contact-link allowlist narrow to `customer`, `supplier`, `lead`, `opportunity`, and `issue`; add new targets intentionally in later stories instead of leaving the table open-ended.
- Keep shared contacts compatible with existing CRM records, but do not force automatic lead-to-contact conversion in this story.
- Preserve backward compatibility by adding shared-contact selectors and response payloads before removing any existing local contact text fields elsewhere.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/contacts/models.py`
  - `backend/domains/contacts/schemas.py`
  - `backend/domains/contacts/service.py`
  - `backend/domains/contacts/routes.py`
  - `backend/app/main.py`
  - `migrations/versions/*_contacts_foundation.py`
- Likely frontend files:
  - `src/lib/api/contacts.ts`
  - `src/domain/contacts/types.ts`
  - `src/domain/contacts/hooks/useContacts.ts`
  - `src/domain/contacts/components/ContactForm.tsx`
  - `src/domain/contacts/components/ContactLinkManager.tsx`
  - `src/pages/contacts/ContactListPage.tsx`
  - `src/pages/contacts/ContactDetailPage.tsx`
- Keep the first implementation on primary communication fields and relationship management; a richer multi-method contact profile can land later if Epic 30 truly needs it.

### What NOT to implement

- Do **not** implement a full duplicate-merge wizard, contact hierarchy graph, or portal-account invitation flow.
- Do **not** remove all existing embedded contact fields in unrelated domains in the same story; incremental replacement is sufficient.
- Do **not** introduce omnichannel preference centers or campaign-consent management here.

### Testing Standards

- Include a regression proving historical links remain queryable after a contact changes role or is replaced on a business record.
- Include a regression proving unsupported `entity_type` values are rejected cleanly.
- Keep frontend locale files synchronized if shared-contact labels are added.

## Dependencies & Related Stories

- **Blocks:** Story 30.1, Story 30.5
- **Related to:** Story 23.1 for CRM lead compatibility, Story 28.4 for issue-party linkage

## References

- `../planning-artifacts/epic-28.md`
- `../planning-artifacts/epic-30.md`
- `backend/domains/crm/models.py`
- `backend/domains/crm/routes.py`
- `https://docs.frappe.io/framework/user/en/basics/doctypes/fieldtypes`
- `backend/app/main.py`
- `src/App.tsx`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 28 contact-system requirements, Frappe dynamic-link guidance, and the current UltrERP CRM and workspace patterns.

### File List

- `_bmad-output/implementation-artifacts/28-2-shared-contact-person-crud-and-dynamic-links.md`