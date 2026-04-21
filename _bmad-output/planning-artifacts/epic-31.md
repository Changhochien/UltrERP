# Epic 31: Assets, Regional Compliance, and Administrative Controls

## Epic Goal

Close the validated long-tail operations gaps after the commercial core is stable by adding asset lifecycle support, regional compliance extensions, fleet and admin utilities, and stronger deletion-grade audit controls.

## Business Value

- Fixed assets stop living outside the ERP.
- Maintenance and repair workflows become schedulable and auditable.
- Regional growth does not require reworking the commercial core for each tax pack.
- Admin-heavy cleanup and compliance tasks move out of manual spreadsheets and ad hoc scripts.

## Scope

**Backend:**
- Fixed asset register and lifecycle events.
- Asset maintenance, asset repair, and driver or vehicle records.
- Regional compliance extension points beyond Taiwan-first invoicing.
- Administrative utilities such as terms templates, bulk rename, deletion audit, and portal-content-ready utilities.

**Frontend:**
- Asset, maintenance, repair, and fleet workspaces.
- Admin utilities for reusable terms, compliance settings, and controlled bulk operations.
- Audit and deletion-review views for administrators.

**Data Model:**
- Asset identity, lifecycle status, maintenance schedules, repairs, and fleet records.
- Regional tax and compliance configuration entities.
- Deletion-grade audit metadata and reusable admin-content records.

## Non-Goals

- Replacing the current Taiwan eGUI compliance baseline.
- Building a full enterprise asset management suite on day one.
- Replacing dedicated CMS or DAM products for rich media.
- Reworking earlier finance or commercial write models.

## Technical Approach

- Treat this epic as a set of operational extensions on top of stable inventory, finance, and service foundations.
- Keep regional compliance modular so new packs can be added without rewriting the transaction core.
- Use admin utilities to reduce manual overhead while preserving strong confirmation and audit flows.
- Keep asset work compatible with issue and warranty linkage from Epic 28.

## Key Constraints

- Asset and compliance extensions should not delay higher-priority operational gaps from earlier waves.
- Bulk rename, deletion audit, and template utilities must emphasize safety and reversibility.
- Regional packs extend the ledger and tax model from Epic 26; they do not replace it.

## Dependency and Phase Order

1. Asset register lands before maintenance and repair scheduling.
2. Regional packs depend on stable finance and tax foundations.
3. Administrative utilities can be split into smaller stories as risk requires.

---

## Story 31.1: Fixed Asset Register and Lifecycle Controls

- Add fixed asset records, ownership details, lifecycle states, and acquisition metadata.
- Keep the model compatible with later depreciation and finance posting work.
- Link assets to serializable products or service records where appropriate.

**Acceptance Criteria:**

- Given an asset is created, identity, location, owner, and acquisition context are explicit.
- Given an asset changes lifecycle state, the change is traceable.
- Given finance later extends depreciation, the asset model already exposes the required hooks.

## Story 31.2: Asset Maintenance and Repair Workflows

- Add maintenance schedules, maintenance logs, repair records, and cost-ready fields.
- Link service tickets or warranty issues to the asset when relevant.
- Keep planned maintenance and unplanned repair clearly separated.

**Acceptance Criteria:**

- Given a maintenance plan exists, future work can be scheduled and reviewed.
- Given an asset repair occurs, the repair history and status remain visible.
- Given service or warranty context exists, the related asset linkage is preserved.

## Story 31.3: Fleet, Driver, and Shift-Oriented Operations

- Add driver and vehicle records with assignment-ready metadata.
- Leave room for shift allocation or route planning without making it mandatory on day one.
- Support delivery or service operations that need equipment or vehicle context.

**Acceptance Criteria:**

- Given a company tracks drivers or vehicles, those records can be managed in one place.
- Given service or logistics work references a vehicle, the linkage is explicit.
- Given future fleet planning is added, current records remain reusable.

## Story 31.4: Regional Packs, Portal Content, and Reusable Administrative Templates

- Add modular regional compliance settings and reusable terms-and-conditions or content templates.
- Support admin-managed templates for contracts, portal content, document footers, and a lightweight first-class video or rich-content record.
- Keep video and knowledge-base content deliberately lightweight on day one without requiring a full media-management suite.
- Keep the structure compatible with later market-specific tax packs.

**Acceptance Criteria:**

- Given a new regional pack is enabled, configuration remains isolated from unrelated markets.
- Given a reusable terms template is created, commercial documents can reference it consistently.
- Given portal or knowledge content is needed, administrators can manage a lightweight first-class video or rich-content record with at least title, content URL, description, and category or tag metadata without reworking the compliance model.
- Given portal or document content needs admin management, the reusable template path exists.

## Story 31.5: Bulk Rename, Deletion Audit, and Admin Safety Utilities

- Add controlled bulk-rename support for key masters where operationally justified.
- Add deletion-grade audit records for destructive or archival admin actions.
- Require explicit confirmation and reversible logging for high-impact utilities.

**Acceptance Criteria:**

- Given an administrator performs a bulk rename, the affected records and before/after state are logged.
- Given a destructive action occurs, the system records a deletion-grade audit trail beyond generic logging.
- Given an unsafe or ambiguous admin action is attempted, the workflow demands explicit confirmation before execution.