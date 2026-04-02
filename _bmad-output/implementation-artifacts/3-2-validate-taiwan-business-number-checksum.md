# Story 3.2: Validate Taiwan Business Number Checksum

Status: completed

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a system,
I want to validate Taiwan business numbers using the current Ministry of Finance checksum logic,
so that customer data stays compliant for both legacy and newly issued numbers.

## Acceptance Criteria

1. Given I'm creating or updating a customer, when I enter an 8-digit Taiwan business number, then the system validates it using the weighted checksum family defined by current Ministry of Finance guidance, including the special-case handling for the seventh digit.
2. Given existing and expanded business-number allocations may both appear in the dataset, when validation runs, then the validator applies the current officially published acceptance rule, including the post-2023 divisibility-by-5 revision for expanded allocations, instead of hardcoding stale divisible-by-10 or "MOD11" assumptions.
3. Given the checksum or format is invalid, when validation runs, then the system returns a clear validation error and prevents save.
4. Given both frontend and backend customer flows need the same decision, when validation helpers are implemented, then the logic is reusable and covered by shared pass/fail fixtures in automated tests.

## Tasks / Subtasks

- [x] Task 1: Implement the canonical backend validator (AC: 1, 2, 3, 4)
  - [x] Create `backend/domains/customers/validators.py` for business-number normalization and checksum validation.
  - [x] Implement the weighted checksum algorithm using weights `1,2,1,2,1,2,4,1`, digit-splitting for two-digit products, the documented special-case handling for the seventh digit, and the revised divisibility-by-5 acceptance rule.
  - [x] Expose a domain-friendly validation API that returns structured errors instead of boolean-only results.
  - [x] Do not copy the existing repo's older `MOD11` shorthand or MIG PoC validator blindly; reconcile those artifacts against the current official guidance first.
- [x] Task 2: Implement the matching frontend pure utility (AC: 1, 3, 4)
  - [x] Create `src/lib/validation/taiwanBusinessNumber.ts` as a pure utility for format normalization and checksum validation.
  - [x] Keep the frontend implementation behaviorally identical to the backend validator and document the expected pass/fail fixtures.
  - [x] Return explicit validation states that create/update forms can render inline rather than via modal dialogs.
- [x] Task 3: Define shared test vectors and integration contracts (AC: 2, 4)
  - [x] Add backend validator tests in `backend/tests/domains/customers/test_business_number_validation.py` using official example values, including at least one direct-pass official fixture and the special-case seventh-digit scenario `19312376`.
  - [x] Add frontend unit tests in `src/tests/customers/taiwanBusinessNumber.test.ts` that mirror the backend fixtures.
  - [x] Record at least one fixture set that demonstrates the rule drift between stale repo shorthand and the current official rule so future refactors do not regress to the wrong checksum logic.
  - [x] Include one invalid-checksum mutation of a valid fixture and one non-8-digit format failure fixture in the shared test set.
- [x] Task 4: Prepare integration points for create and update flows (AC: 1, 3, 4)
  - [x] Ensure Story 3.3 and Story 3.5 can call the backend validator from the service layer before persistence.
  - [x] Ensure future forms can surface inline validation feedback after the eighth digit is entered, using debounce only for the validation work and not for the controlled input state itself.
  - [x] Keep validation logic out of ad hoc route handlers and out of unrelated invoice code.

## Dev Notes

### Story Context

- The repo's PRD and architecture still use the older shorthand "MOD11" for Taiwan business-number validation, but external validation against Ministry of Finance and North Area National Taxation Bureau notices shows the official checksum guidance was revised for expanded allocations.
- This story exists to create one authoritative validator that later customer create, update, search, and MCP surfaces can all share.
- Story 3.3 and Story 3.5 should not implement their own checksum logic. They should consume the outputs of this story.

### Dependency Sequencing

- Implement this story first within Epic 3.
- Treat this story as a hard prerequisite for Story 3.3, Story 3.4, and Story 3.5.
- Story 8.5 should reuse the finalized rule description from this story when codifying Taiwan tax/domain knowledge for AI surfaces.

### Scope Guardrails

- Do not implement a literal MOD11 algorithm simply because older repo text says MOD11. The story's job is to align implementation to current official guidance.
- Do not bury the rule inside a form component or an API route. Keep it as a standalone, well-tested pure function in both runtimes.
- Do not broaden this story into full customer CRUD screens. It establishes validation primitives and fixtures for the stories that follow.

### Algorithm Reference

- Treat Taiwan business numbers as exactly 8 digits after normalization.
- Apply weights `1, 2, 1, 2, 1, 2, 4, 1` to digits 1 through 8.
- Multiply each digit by its weight, then split any two-digit product into its decimal digit sum before calculating the final total.
- Apply the current compatible official acceptance rule: accept when `sum % 5 == 0`; if the seventh digit is `7`, also accept when `(sum + 1) % 5 == 0`.
- Do not branch on guessed issuance dates. Older divisible-by-10 examples remain compatible with the revised rule because any value divisible by 10 is also divisible by 5.

### Technical Requirements

- Normalize input to digits-only before checksum evaluation and reject non-8-digit values early.
- Implement special-case seventh-digit handling exactly once and document it in code comments or test descriptions if the final code would otherwise be opaque.
- Make the rule drift explicit in fixtures and comments: older repo shorthand described a divisible-by-10/MOD11-style check, while current official guidance for expanded allocations uses the revised divisibility-by-5 acceptance rule.
- Mirror pass/fail fixtures across backend and frontend tests so both runtimes stay aligned.
- Existing repo PoCs under `research/egui-compliance/02-poc/` and `research/00-consolidation/whole-picture.md` contain older validation references. Treat them as historical context, not the source of truth.

### Testing Requirements

- Mandatory backend coverage:
  - valid official examples
  - invalid checksum examples
  - invalid format examples
  - special-case seventh-digit examples
  - regression coverage for expanded-allocation logic
- Mandatory frontend coverage:
  - digit normalization
  - valid/invalid fixture parity with backend
  - result state suitable for inline form feedback
- Seed fixture set must include one standard direct-pass official example, the seventh-digit special-case pass `19312376`, one invalid checksum mutation of a valid fixture, and one non-8-digit format failure.

### Project Structure Notes

- Backend validation logic belongs under `backend/domains/customers/validators.py` and should be imported by the customer service layer.
- Frontend validation logic belongs under `src/lib/validation/` rather than inside a specific page component so multiple forms can reuse it.
- If a shared fixture file is introduced, place it somewhere both backend and frontend tests can consume without duplicating truth manually.

### Risks / Open Questions

- There is real drift between internal repo wording and current official checksum notices. If the team has a business reason to keep legacy-only behavior, that needs an explicit product decision; it should not be inferred from stale shorthand.
- The customer-management wireframes and UX memos still describe the old logic in places. Keep those references in mind when updating inline validation copy.

### References

- `_bmad-output/epics.md` — Story 3.2 acceptance criteria and Epic 8 Taiwan-knowledge references.
- `_bmad-output/planning-artifacts/prd.md` — Journey 4 and FR17 create/update validation requirement.
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` — customer domain model and `customers.update` contract.
- `research/ui-ux/01-survey-memo.md` — Taiwan-localized inline validation expectations and historical weighting description.
- `research/ui-ux/02-wireframes/01-customer-management.md` — customer-entry field expectations and inline feedback behavior.
- `research/egui-compliance/02-poc/mig41_generator.py` — existing validator example that must be revalidated before reuse.
- `research/00-consolidation/whole-picture.md` — notes about prior PoCs that assumed older UBN/BAN validation wording.
- `https://www.ntbna.gov.tw/singlehtml/bbabfd4af20541b7859b4c5a099081f6?cntId=0625114d47274366baab1d3317f866ab` — official taxation-agency checksum logic revision notice validated during story creation.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `/Users/hcchang/Library/Application Support/Code - Insiders/User/workspaceStorage/4320abfca0ca1465bc6bebe187407283/GitHub.copilot-chat/debug-logs/6f0af2c8-127f-429b-8f9b-f9f78e0f0e40`

### Completion Notes List

- Story rewritten around current official checksum guidance because repo shorthand and web-validated government guidance diverge.
- The implementation notes explicitly prevent copying stale "MOD11" behavior into customer create/update flows.
- Shared backend/frontend fixture parity was made a hard requirement to avoid silent rule drift.
- Implementation completed: backend `ValidationResult` dataclass + `validate_taiwan_business_number()` in `backend/domains/customers/validators.py`.
- Frontend mirror: `ValidationResult` interface + `validateTaiwanBusinessNumber()` in `src/lib/validation/taiwanBusinessNumber.ts`.
- 14 backend tests, 14 frontend tests all passing with zero lint errors.
- Verified the PoC at `research/egui-compliance/02-poc/mig41_generator.py` uses the stale 9-digit mod-10 algorithm — correctly NOT copied.
- Expanded-allocation regression fixture `55555555` (sum=25, mod5=0, mod10≠0) ensures no regression to stale rule.

### File List

- `backend/domains/customers/__init__.py`
- `backend/domains/customers/validators.py`
- `backend/tests/domains/__init__.py`
- `backend/tests/domains/customers/__init__.py`
- `backend/tests/domains/customers/test_business_number_validation.py`
- `src/lib/validation/taiwanBusinessNumber.ts`
- `src/tests/customers/taiwanBusinessNumber.test.ts`