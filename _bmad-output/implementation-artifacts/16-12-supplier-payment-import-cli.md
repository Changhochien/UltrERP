# Story 16.12: Supplier Payment Import CLI

Status: done

## Story

As a migration operator,
I want a dedicated CLI step to import staged supplier payment history into the canonical AP payment tables,
So that `tbsprepay` and `tbsspay` can be migrated deliberately without coupling payment import to `canonical-import`.

## Acceptance Criteria

**AC1:** The legacy-import CLI exposes an explicit AP payment import command
**Given** staged `tbsprepay` and `tbsspay` rows exist for a batch and the AP payment schema from Story 16.11 is present
**When** I run `uv run python -m domains.legacy_import.cli ap-payment-import --batch-id <batch-id> --tenant-id <tenant-uuid>`
**Then** the CLI runs a supplier payment import step for that batch
**And** the command remains separate from `canonical-import`
**And** the run is tracked with batch and attempt semantics

**AC2:** Verified AP cash events that pass the current evidence gate land in the canonical payment tables
**Given** the mapping rules documented in `docs/legacy/ap-payment-model.md`
**When** the AP payment import command runs
**Then** verified supplier-side special-payment rows are written into `supplier_payments`
**And** unresolved `tbsprepay` rows and unverified invoice-link semantics stay on holding instead of guessed canonical writes
**And** deterministic IDs plus lineage records keep the import replay-safe

**AC3:** Unverified or unsafe rows stay on a protected path
**Given** some legacy payment rows still cannot be linked safely to a supplier invoice or have unresolved sign/date semantics
**When** the command processes those rows
**Then** those rows remain in holding or fail with explicit diagnostics instead of guessed canonical writes
**And** the command never auto-runs from `canonical-import`

**AC4:** The CLI expansion is proven with focused validation
**Given** the new command and import module are implemented
**When** focused backend validation runs
**Then** pytest covers the CLI and AP payment import behavior
**And** Ruff passes on the touched legacy-import and AP payment files

## Tasks / Subtasks

- [x] **Task 1: Add the CLI entrypoint**
  - [x] Add `ap-payment-import` to `backend/domains/legacy_import/cli.py`
  - [x] Keep the command explicit and separate from `canonical-import`
  - [x] Reuse batch/tenant tracking semantics already used by other legacy-import steps

- [x] **Task 2: Implement the AP payment import module**
  - [x] Add a dedicated import module for staged `tbsprepay` and `tbsspay`
  - [x] Write the verified supplier-side special-payment subset into `supplier_payments`
  - [x] Keep unresolved prepayment and allocation semantics on the holding path until a later verified story

- [x] **Task 3: Preserve safety boundaries**
  - [x] Keep unresolved rows on the holding path or fail with explicit diagnostics
  - [x] Do not guess supplier or invoice linkage when the legacy fields are incomplete
  - [x] Keep replay safety via deterministic IDs and lineage records

- [x] **Task 4: Prove the CLI expansion**
  - [x] Add focused CLI and import tests
  - [x] Re-run the Epic 16 legacy-import validation slice
  - [x] Update docs/legacy notes if the verified mapping rules change

## Dev Notes

### Repo Reality

- Story 16.10 documented the AP payment model and the verification checklist.
- Story 16.11 shipped the backend schema foundation with `supplier_payments` and `supplier_payment_allocations`.
- A review hardening pass on 2026-04-05 removed an accidental coupling where `canonical-import` tried to auto-run the currency import. This story should avoid repeating that mistake: payment import must remain an explicit CLI step.

### Critical Warnings

- Do **not** auto-run AP payment import from `canonical-import`.
- Do **not** guess supplier or invoice allocation semantics that are still unresolved in `docs/legacy/ap-payment-model.md`.
- Do **not** collapse supplier payment history into the AR `payments` table.

### Implementation Direction

- Prefer a dedicated module such as `backend/domains/legacy_import/ap_payment_import.py` or similar over bloating `cli.py`.
- Reuse control-table tracking, deterministic IDs, and lineage patterns already established in `staging.py`, `currency.py`, and `canonical.py`.
- Treat holding behavior as a first-class outcome for rows that still fail the verified mapping rules.

## References

- `_bmad-output/planning-artifacts/epics.md` - Epic 16 / Story 16.12
- `_bmad-output/implementation-artifacts/16-10-ap-payment-model-design.md` - verified AP payment design rules
- `_bmad-output/implementation-artifacts/16-11-canonical-ap-payment-architecture.md` - AP payment schema foundation
- `docs/legacy/ap-payment-model.md` - canonical AP payment design note
- `backend/common/models/supplier_payment.py` - canonical AP payment tables and enums
- `backend/domains/legacy_import/cli.py` - operator entrypoint to expand

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Completion Notes List

- 2026-04-05: Created Story 16.12 to capture the next explicit Epic 16 backend step: expanding the legacy-import CLI with a standalone AP payment import command.
- Scoped the story to keep payment import separate from `canonical-import` and aligned it with the verified AP design and schema work already completed in Stories 16.10 and 16.11.
- 2026-04-06: Added `ap-payment-import` as an explicit CLI step with replay-safe run tracking, lineage writes, and protected-path holding updates.
- The implementation is intentionally strict: only supplier-role, non-zero, date-valid payment rows can land in `supplier_payments`; no guessed allocation writes are emitted.
- Current dump evidence tightened the AP mapping boundary further: `tbsspay` rows align to customer-role receipt history, and `tbsprepay` rows in this export do not expose a verified payment number/date/amount combination, so unresolved rows remain on holding with explicit diagnostics.
- 2026-04-06 review follow-up: corrected the story wording to match the shipped scope. This story does not import prepayments or payment allocations from the current dump; it only lands the verified supplier-side special-payment subset and preserves the rest on holding.
- 2026-04-06 review follow-up: serialized AP payment import attempt allocation with a transaction-level advisory lock so concurrent launches cannot split legacy run and table-run tracking.
- Focused validation passed from `backend/`: `uv run pytest tests/domains/legacy_import/test_ap_payment_import.py tests/domains/legacy_import/test_cli.py -q`, `uv run pytest tests/domains/legacy_import/test_ap_payment_import.py tests/domains/legacy_import/test_cli.py tests/domains/legacy_import/test_canonical.py tests/domains/legacy_import/test_staging.py tests/domains/legacy_import/test_validation.py -q`, and targeted `uv run ruff check ... ap_payment_import.py ... test_cli.py` all returned clean.

### File List

- _bmad-output/planning-artifacts/epics.md
- _bmad-output/implementation-artifacts/16-12-supplier-payment-import-cli.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/domains/legacy_import/ap_payment_import.py
- backend/domains/legacy_import/cli.py
- backend/tests/domains/legacy_import/test_ap_payment_import.py
- backend/tests/domains/legacy_import/test_cli.py
- docs/legacy/ap-payment-model.md

### Change Log

- 2026-04-06: Implemented the explicit AP payment import CLI step, added focused validation, and documented the stricter verified mapping boundary from the real legacy dump.
- 2026-04-06: Review follow-up corrected the story scope and hardened attempt tracking against concurrent launch races.