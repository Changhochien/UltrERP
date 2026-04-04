# Story 12.3: eGUI Status Badge and State Persistence

Status: completed

## Story

As a user,
I want invoice screens to show async eGUI state, deadline awareness, and persisted status,
So that I can reliably track invoice submission progress.

## Acceptance Criteria

**AC1:** Invoice detail shows async eGUI state when enabled  
**Given** eGUI tracking is enabled for the tenant  
**When** I open an invoice detail screen  
**Then** I see an eGUI status badge with a persisted backend state such as `PENDING`, `QUEUED`, `SENT`, `ACKED`, or `FAILED`

**AC2:** Deadline awareness is server-derived  
**Given** an invoice is subject to eGUI timing rules  
**When** I view its status surface  
**Then** I see a server-derived submission window or deadline label  
**And** the frontend does not invent its own business-state clock from browser time alone

**AC3:** Manual refresh is available  
**Given** I suspect the current eGUI status is stale  
**When** I request a refresh  
**Then** the app re-reads status from the backend state source  
**And** the UI shows the refreshed result without requiring a full page reload

**AC4:** State survives app restarts  
**Given** the app is closed and reopened  
**When** I reopen the same invoice  
**Then** the previously known eGUI state is still present  
**And** persistence comes from durable backend state, not a frontend-only cache

**AC5:** Disabled tenants do not see fake status UI  
**Given** eGUI is not enabled for the tenant or environment  
**When** I open an invoice  
**Then** the app hides or suppresses the eGUI state surface cleanly  
**And** no fake countdown or mock badge appears by accident

## Tasks / Subtasks

- [x] **Task 1: Introduce the missing durable eGUI state model** (AC1, AC4, AC5)
  - [x] Add an `EguiSubmission` persistence model linked to invoices
  - [x] Add an explicit status enum covering the validated research states: `PENDING`, `QUEUED`, `SENT`, `ACKED`, `FAILED`, `RETRYING`, `DEAD_LETTER`
  - [x] Add the required Alembic migration for the new table/columns
  - [x] Use the existing server-owned invoice creation timestamp for deadline tracking instead of introducing browser-derived state

- [x] **Task 2: Add backend configuration and service behavior** (AC1, AC2, AC3, AC5)
  - [x] Add explicit backend settings for eGUI tracking enablement and mock/live mode selection
  - [x] Add service helpers under `backend/domains/invoices/` to read the current eGUI submission state
  - [x] Compute deadline-awareness fields on the server side
  - [x] Keep the state model compatible with the planned outbox/inbox architecture without overbuilding the FIA worker path in this story

- [x] **Task 3: Expose invoice status data and a refresh path** (AC1, AC2, AC3)
  - [x] Extend the invoice detail API response to include an `egui_submission` payload
  - [x] Add a manual refresh endpoint that rehydrates status from the backend state source
  - [x] Back the current refresh path with validated mock-state behavior and fail fast when live refresh is requested but not implemented

- [x] **Task 4: Add invoice UI surfaces** (AC1, AC2, AC3, AC5)
  - [x] Extend `src/domain/invoices/types.ts` with typed eGUI status fields
  - [x] Extend `src/domain/invoices/hooks/useInvoices.ts` and invoice API helpers to consume them
  - [x] Render an eGUI badge, deadline indicator, and refresh control in `src/domain/invoices/components/InvoiceDetail.tsx`
  - [x] Keep invoice list/detail payment status behavior intact; eGUI status is an additional operational surface, not a replacement

- [x] **Task 5: Add focused backend and frontend tests** (AC1, AC2, AC3, AC4, AC5)
  - [x] Backend tests for feature-flag off, state persistence, server-side deadline fields, manual refresh behavior, and unsupported live refresh mode
  - [x] Frontend tests for badge rendering, deadline labels, refresh states, hidden-state behavior when eGUI is disabled, and refresh-failure resilience

## Dev Notes

### Repo Reality

- The production code currently has **no** `EguiSubmission` model and **no** durable eGUI state pipeline.
- `backend/domains/invoices/service.py` already contains `compute_void_deadline()`, but that is the regulatory void rule, not the same thing as an async submission-state timeline.
- Existing invoice UI surfaces only show invoice/payment status today.

### Critical Warnings

- Do **not** persist business-state truth in `localStorage` or `sessionStorage`. AC4 requires durable operational state, so the backend database must be the system of record.
- Do **not** fake eGUI progress with client-side timers only. If live FIA is unavailable, use a backend-backed mock provider consistent with the research PoC.
- Do **not** confuse void deadlines with submission deadlines. They are related regulatory concerns but not the same state machine.
- If a precise statutory countdown depends on a timestamp the current invoice model does not reliably store, add the timestamp now rather than hand-wave the gap.

### Latest-Tech / Research Evidence

- Architecture and research both converge on the state machine: `PENDING -> QUEUED -> SENT -> ACKED`, with failure branches through `FAILED`, `RETRYING`, and `DEAD_LETTER`.
- Research explicitly warns about an eGUI state race condition when app lifecycle and tray mode are involved; durable persistence is therefore a first-class requirement, not optional polish.
- Live FIA submission remains blocked by credential approval and lack of a public sandbox, so this story must stay mock-compatible.

### Validation Follow-up

- Treat `EguiSubmission` as tenant-owned state from day one. The persistence model and any supporting queries should include `tenant_id` so the new status surface follows the repo's multi-tenant rules instead of creating a cross-tenant leak.
- Add an explicit allowed-transition map for the eGUI status enum rather than open-coding string transitions throughout services.
- The current invoice detail route builds `InvoiceResponse` from the invoice and then merges payment-summary fields into that response. Extend that same response path carefully so `egui_submission` data does not break the existing payment-summary merge semantics or frontend expectations.
- Frontend refresh behavior should ignore stale responses when the user leaves the screen or triggers refresh repeatedly in quick succession.
- If eGUI status later appears in invoice list results, shape the backend query deliberately to avoid an N+1 lookup pattern.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 12 / Story 12.3 / FR52 / NFR23
- `_bmad-output/planning-artifacts/prd.md` - FR52 and persistence/usability NFRs
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` - `EguiSubmission` entity and state machine definition
- `research/00-consolidation/whole-picture.md` - validated eGUI PoC findings, deadline risk, and persistence warning
- `backend/domains/invoices/service.py` - current invoice service anchor and existing void-deadline helper
- `src/domain/invoices/components/InvoiceDetail.tsx` - current UI anchor to extend
- `src/domain/invoices/types.ts` - current invoice response types to extend

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Completion Notes List

- Story 12.3 added the `EguiSubmission` persistence model, enum transition map, invoice-detail enrichment, and a backend refresh path backed by mock-state transitions.
- The invoice detail UI now renders the eGUI status surface, server-derived deadline information, and a manual refresh control without disturbing the existing payment summary behavior.
- Review follow-up fixed a real UX regression where refresh failures replaced the whole invoice screen, and the backend now rejects unsupported live-mode refresh instead of returning a false-success response.
- Focused validation passed with `uv run pytest tests/domains/payments/test_payment_status.py -q` and `pnpm test -- src/domain/invoices/__tests__/InvoiceDetail.test.tsx`.
- Revalidated on 2026-04-04 against the current repo state: the focused backend and frontend validations still pass, no additional production code changes were required, and the Epic 12 tracker note was corrected to match the implemented feature.
- Code-review follow-up on 2026-04-04 hardened first-read eGUI submission creation against duplicate-row races, made refresh tolerate invalid persisted statuses, and stopped collapsing every invoice-detail load failure into `Invoice not found`; the focused backend/frontend validation slice remained green afterward.
- Deferred review follow-up on 2026-04-04 corrected adjacent invoice-domain consistency issues the Story 12.3 review exposed: paid/unpaid list queries now align with the zero-clamped outstanding balance shown in UI, mixed-currency customer outstanding summaries fail explicitly instead of fabricating a TWD total, and backend error detail now reaches the customer outstanding card.

### Change Log

- 2026-04-04: Implemented durable eGUI state persistence, invoice detail API/status enrichment, and the invoice detail UI surface for Story 12.3.
- 2026-04-04: Completed code-review follow-up by preserving invoice detail during refresh failures and rejecting unsupported live-mode refresh requests.
- 2026-04-04: Revalidated Story 12.3 against the implemented repo and synchronized the Epic 12 tracker note with the passing validation slice.
- 2026-04-04: Addressed Story 12.3 code-review findings by hardening eGUI row creation, invalid-status refresh handling, and invoice detail error reporting.
- 2026-04-04: Completed the deferred review fixes by aligning invoice outstanding filters/sorts with clamped balances, rejecting mixed-currency customer outstanding aggregation, and surfacing backend detail in the customer outstanding UI.

### File List

- backend/common/config.py
- backend/domains/invoices/enums.py
- backend/domains/invoices/models.py
- backend/domains/invoices/routes.py
- backend/domains/invoices/schemas.py
- backend/domains/invoices/service.py
- backend/domains/customers/routes.py
- backend/tests/domains/payments/test_payment_status.py
- backend/tests/domains/orders/_helpers.py
- migrations/versions/rr888tt88u10_create_egui_submissions.py
- src/domain/customers/__tests__/CustomerOutstanding.test.tsx
- src/domain/invoices/__tests__/InvoiceDetail.test.tsx
- src/domain/invoices/components/InvoiceDetail.tsx
- src/domain/invoices/hooks/useInvoices.ts
- src/domain/invoices/types.ts
- src/lib/api/invoices.ts
- _bmad-output/implementation-artifacts/12-3-egui-status-badge.md
- _bmad-output/implementation-artifacts/sprint-status.yaml