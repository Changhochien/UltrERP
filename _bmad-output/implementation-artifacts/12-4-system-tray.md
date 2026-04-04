# Story 12.4: System Tray Mode with Notifications

Status: completed

## Story

As a user,
I want the desktop app to keep running in the system tray and notify me about async invoice/eGUI changes,
So that I can monitor background work even when the main window is closed.

## Acceptance Criteria

**AC1:** Closing the main window hides to tray instead of quitting  
**Given** the desktop app is running in the Tauri shell  
**When** I close the main window  
**Then** the app keeps running in the tray  
**And** the main window can be restored without starting a second app instance

**AC2:** Notifications are emitted for meaningful async state changes  
**Given** an invoice/eGUI status changes in the durable backend state source  
**When** the app is still running in tray mode  
**Then** I receive a desktop notification for the meaningful transition  
**And** duplicate notifications are suppressed

**AC3:** Tray interactions restore the app predictably  
**Given** the app is in tray mode  
**When** I click the tray icon or choose the restore action from the tray menu  
**Then** the main window becomes visible and focused

**AC4:** Explicit quit remains explicit  
**Given** I really want to exit the app  
**When** I choose the tray/menu quit action  
**Then** the application exits cleanly  
**And** hide-to-tray does not trap me in a process I cannot close

## Tasks / Subtasks

- [x] **Task 1: Add tray behavior to the production Tauri shell** (AC1, AC3, AC4)
  - [x] Extend the root `src-tauri/` app created by Story 12.2
  - [x] Add a tray icon and tray menu with at least restore/show and quit actions
  - [x] Intercept window close requests and hide the main window instead of exiting
  - [x] Ensure explicit quit still shuts the process down cleanly

- [x] **Task 2: Add desktop notification support with explicit permissions** (AC2)
  - [x] Wire the Tauri notification plugin into the production shell
  - [x] Declare the required notification capabilities/permissions explicitly
  - [x] Handle permission-denied cases gracefully instead of throwing runtime failures

- [x] **Task 3: Bridge tray/notification behavior into the frontend safely** (AC1, AC2, AC3)
  - [x] Add frontend desktop bridge helpers under `src/lib/desktop/`
  - [x] Expose `showWindow`, `hideWindowToTray`, and `notify` style helpers behind runtime guards
  - [x] Keep the browser build functional even though tray mode is desktop-only

- [x] **Task 4: Connect notifications to the real eGUI state source** (AC2)
  - [x] Consume the persisted eGUI state surface from Story 12.3
  - [x] Only notify on meaningful state transitions (`QUEUED -> SENT`, `SENT -> ACKED`, `FAILED`, etc.)
  - [x] Persist the last-notified state locally so app restarts do not replay stale notifications repeatedly
  - [x] Avoid a second shadow state machine in the tray layer

- [x] **Task 5: Add focused manual and automated validation** (AC1, AC2, AC3, AC4)
  - [x] Add narrow desktop-facing validation notes for macOS and Windows tray behavior
  - [x] Add unit/integration coverage for the frontend bridge and notification dedupe logic where feasible
  - [x] Add a manual runbook proving: close -> tray, tray click -> restore, state change -> notify, quit -> exit

## Dev Notes

### Repo Reality

- The production repo already had the root `src-tauri/` shell from Story 12.2 and the durable eGUI state source from Story 12.3; the previous blocked note was stale.
- This story extends those shipped surfaces with tray lifecycle control, explicit desktop notification handling, and a hidden-window polling bridge that reuses the existing invoice eGUI refresh path.
- The browser build remains first-class: tray and notification helpers stay behind runtime guards and dynamic imports.

### Critical Warnings

- This story should be treated as **dependent on 12.2 and 12.3**. Without the shell and the eGUI state model, tray mode has nothing real to restore or notify about.
- Do **not** create a second hidden workflow engine in Rust just to simulate business state. Consume the status source defined in Story 12.3.
- Do **not** turn close-to-tray into an inescapable background process. Explicit quit must always be available.
- Duplicate-notification suppression is required. Otherwise every restart or poll cycle becomes spam.

### Latest-Tech Evidence

- Tauri v2 tray support is documented around tray-icon creation, menu wiring, and tray event handling.
- Tauri notification support includes explicit permission concepts and OS-level permission concerns.
- Research already flags tray plus async eGUI tracking as non-deferrable for the desktop workflow.

### Validation Follow-up

- The tray menu must always expose an explicit quit path that bypasses the hide-on-close behavior and exits the app cleanly.
- Notification permission stays a runtime flow, not a static assumption: check, request when needed, and degrade cleanly if the OS denies notification access.
- The local desktop store remains dedupe metadata keyed by invoice/status; backend invoice and eGUI state stay server-owned.
- If the desktop build ships the backend sidecar, prefer WiX over NSIS until the current NSIS sidecar reinstall issue is resolved.
- Real macOS and Windows hardware validation still needs to be executed with the runbook in `docs/superpowers/specs/2026-04-04-system-tray-mode.md` because tray and notification quirks are OS-shell specific.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 12 / Story 12.4 / FR53
- `_bmad-output/planning-artifacts/prd.md` - FR53 and background-operation NFRs
- `research/00-consolidation/whole-picture.md` - tray/notification architecture recommendation and race-condition warning
- `research/tech-viability/02-poc/tauri-fastapi-poc/src-tauri/src/lib.rs` - current sidecar lifecycle reference
- `docs/superpowers/specs/2026-04-04-system-tray-mode.md` - manual validation runbook and capability notes
- `https://v2.tauri.app/learn/system-tray/` - Tauri v2 tray docs
- `https://v2.tauri.app/plugin/notification/` - Tauri notification plugin docs and permission surface

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Completion Notes List

- Revalidated Story 12.4 against the current repo before implementation: the previous blocked note was stale because the root Tauri shell from Story 12.2 and the durable eGUI state source from Story 12.3 already existed.
- The root Tauri shell now intercepts close requests, hides to tray, restores the existing window from tray interactions, and exits only through an explicit quit path.
- Browser-safe desktop bridges now cover window restore/hide and notification delivery, while a hidden tray controller reuses the server-owned eGUI refresh surface and locally suppresses duplicate notifications.
- Focused validation passed with `cargo check`, `pnpm exec vitest run src/lib/desktop/__tests__/eguiMonitor.test.ts src/lib/desktop/__tests__/window.test.ts src/lib/desktop/__tests__/notifications.test.ts src/domain/invoices/__tests__/InvoiceDetail.test.tsx`, and `pnpm build`.
- Manual macOS and Windows validation steps are captured in `docs/superpowers/specs/2026-04-04-system-tray-mode.md`; those hardware checks remain the only outstanding non-automated confirmation.

### Change Log

- 2026-04-04: Revalidated Story 12.4 prerequisites, removed the stale blocked status, and implemented production tray lifecycle handling in the root Tauri shell.
- 2026-04-04: Added browser-safe desktop window and notification bridges, hidden eGUI transition monitoring with dedupe, and focused frontend regression coverage.
- 2026-04-04: Added the system tray manual validation runbook and synchronized the sprint tracker to the validated implementation state.

### File List

- docs/superpowers/specs/2026-04-04-system-tray-mode.md
- package.json
- pnpm-lock.yaml
- src/App.tsx
- src/components/desktop/DesktopTrayController.tsx
- src/domain/invoices/__tests__/InvoiceDetail.test.tsx
- src/domain/invoices/components/InvoiceDetail.tsx
- src/lib/desktop/__tests__/eguiMonitor.test.ts
- src/lib/desktop/__tests__/notifications.test.ts
- src/lib/desktop/__tests__/window.test.ts
- src/lib/desktop/eguiMonitor.ts
- src/lib/desktop/notifications.ts
- src/lib/desktop/window.ts
- src-tauri/Cargo.toml
- src-tauri/capabilities/default.json
- src-tauri/src/lib.rs
- _bmad-output/implementation-artifacts/12-4-system-tray.md
- _bmad-output/implementation-artifacts/sprint-status.yaml