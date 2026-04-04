# Story 12.2: Keyboard Shortcuts with Overlay

Status: done

## Story

As a power user,
I want app-wide shortcuts and a discoverable shortcut overlay,
So that I can move through primary workflows without depending on the mouse.

## Acceptance Criteria

**AC1:** Shortcut overlay is discoverable  
**Given** I am using the app  
**When** I press `?` or `Ctrl+/`  
**Then** a shortcut overlay opens  
**And** it lists the currently supported global and screen-local shortcuts

**AC2:** App-wide shortcuts work consistently  
**Given** I am on a supported screen  
**When** I trigger a registered shortcut outside of a text-editing field  
**Then** the matching route or action executes  
**And** shortcuts do not fire accidentally while I am typing in an input, textarea, or contenteditable region

**AC3:** Desktop-only global shortcuts are explicit and capability-gated  
**Given** the app is running inside the production Tauri shell  
**When** a desktop global shortcut is registered  
**Then** it is backed by Tauri's global-shortcut plugin  
**And** the required permissions/capabilities are explicitly declared  
**And** the browser build degrades gracefully without runtime errors

**AC4:** One registry drives overlay and handlers  
**Given** a shortcut is shown in the overlay  
**When** I invoke it  
**Then** the documented keybinding matches the implemented behavior

## Tasks / Subtasks

- [x] **Task 1: Create the missing production desktop shell foundation** (AC3)
  - [x] Add a root-level `src-tauri/` app scaffold for the real product workspace
  - [x] Use `research/tech-viability/02-poc/tauri-fastapi-poc/` as the reference pattern, not as a direct copy-paste drop-in
  - [x] Add the minimum Tauri configuration needed to run the frontend inside a desktop shell
  - [x] Create explicit capabilities/permission files for any shortcut commands that the desktop build exposes
  - [x] Add a thin frontend desktop-bridge helper under `src/lib/desktop/` so web mode does not import Tauri APIs blindly

- [x] **Task 2: Create a single source of truth for shortcuts** (AC1, AC4)
  - [x] Add a shortcut registry module such as `src/lib/shortcuts.ts`
  - [x] Store label, keybinding, scope, route/action target, and desktop-only flag in one place
  - [x] Use that registry to render the overlay and dispatch the handlers so docs and behavior cannot drift

- [x] **Task 3: Implement the shortcut overlay in the React app** (AC1, AC4)
  - [x] Add a reusable overlay component such as `src/components/shortcuts/ShortcutOverlay.tsx`
  - [x] Mount it near the top-level app shell so it works on primary routes
  - [x] Support `?` and `Ctrl+/` as overlay-entry shortcuts
  - [x] Ensure focus management and escape-to-close behavior are keyboard-safe

- [x] **Task 4: Add app-scoped keyboard handlers first** (AC2)
  - [x] Implement route/navigation shortcuts for the primary daily screens already present in the app
  - [x] Guard all handlers so shortcuts do not fire while typing into editable controls
  - [x] Add screen-local shortcuts only where the local action is already real and stable; do not invent placeholder actions just to pad the overlay

- [x] **Task 5: Add desktop global shortcuts carefully** (AC3)
  - [x] Register a minimal, conservative set of desktop global shortcuts through Tauri only
  - [x] Keep the browser build app-scoped only; no Tauri hard failure in web mode
  - [x] Unregister any desktop global shortcuts cleanly on shutdown/teardown
  - [x] Do not bind destructive or sensitive write actions to OS-global shortcuts

- [x] **Task 6: Add focused tests and operator docs** (AC1, AC2, AC3, AC4)
  - [x] Add frontend tests for overlay visibility, typing guards, and route/action dispatch
  - [x] Add desktop manual validation notes for permission/capability behavior in macOS and Windows builds
  - [x] Document the supported shortcuts in repo docs or story implementation notes so onboarding does not rely on hidden UI behavior

### Review Findings

- [x] [Review][Patch] Guard desktop shortcut registration against stale async cleanup races [src/components/shortcuts/ShortcutLayer.tsx:175]
- [x] [Review][Patch] Apply editable-target suppression consistently across desktop callbacks and richer editable hosts [src/components/shortcuts/ShortcutLayer.tsx:175]
- [x] [Review][Patch] Reject reverse-order prefix conflicts in the shortcut registry [src/lib/shortcuts.ts:337]
- [x] [Review][Patch] Trap focus inside the shortcut overlay while the modal is open [src/components/shortcuts/ShortcutOverlay.tsx:77]
- [x] [Review][Patch] Hide desktop-only bindings from the overlay when the app is not running in Tauri [src/components/shortcuts/ShortcutOverlay.tsx:46]

## Dev Notes

### Repo Reality

- There is no root `src-tauri/` product app in the current workspace.
- The only Tauri implementation in-repo today is the research PoC under `research/tech-viability/02-poc/tauri-fastapi-poc/`.
- `package.json` already includes `@tauri-apps/api`, so the frontend dependency surface has started, but the production shell is still missing.

### Critical Warnings

- This story must create the missing desktop shell foundation instead of pretending it already exists.
- Tauri's global-shortcut plugin enables **no features by default**; explicit permissions/capabilities are required. That is a security feature, not a bug.
- Do not register OS-global shortcuts for sensitive write actions. FR54 and Epic 11 already raise the bar for human confirmation on risky operations.
- Keep the browser build healthy. Tauri integration must be runtime-guarded behind an environment/bridge layer.

### Latest-Tech Evidence

- Tauri v2 system features are capability-driven.
- Official Tauri global-shortcut docs explicitly state no features are enabled by default because shortcuts can be inherently dangerous and application-specific.
- Official Tauri plugin-permission guidance requires the app to define what commands are allowed, instead of assuming broad default access.

### Validation Follow-up

- This story is still the real desktop-shell bootstrap point. There is no root `src-tauri/` app, no shortcut registry module, and no desktop bridge in the production workspace today.
- Treat the shortcut registry as more than a constant list: normalize modifier ordering and reject duplicate/conflicting bindings at registration time so overlay text and actual dispatch cannot silently diverge.
- Keep every `@tauri-apps/plugin-global-shortcut` import behind the desktop bridge/runtime guard. The browser build must never eagerly load Tauri plugin modules.
- Text-entry guarding should cover more than raw tag names: `input`, `textarea`, `contenteditable`, and ARIA-textbox-style editors used by richer controls all need to suppress shortcut dispatch.
- Platform notes validated during review: avoid OS-reserved or conflict-prone chords like `Cmd+Q` and Windows `Alt+<letter>` menu accelerators; if the plugin path exposes key-state events, prefer reacting on the release edge so the macOS double-fire issue is easier to contain and test.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 12 / Story 12.2 / FR51
- `_bmad-output/planning-artifacts/prd.md` - FR51 and keyboard-accessible workflow NFRs
- `research/tech-viability/02-poc/tauri-fastapi-poc/` - Tauri + sidecar reference pattern
- `design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md` - Tauri 2 + Python sidecar architecture direction
- `https://v2.tauri.app/plugin/global-shortcut/` - Tauri v2 global shortcut plugin docs and permissions model
- `https://v2.tauri.app/learn/security/writing-plugin-permissions/` - Tauri permission/capability guidance

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Debug Log

- Wrote failing shortcut-layer tests first, then implemented the registry/controller/overlay against that red case.
- Added the root `src-tauri/` scaffold, explicit shortcut capabilities, and a browser-safe desktop bridge with lazy Tauri plugin imports.
- Added operator documentation and reran focused plus full validation before marking the story complete.

### Completion Notes List

- Story 12.2 was intentionally written as the desktop-shell bootstrap point because the main product repo does not yet have a production Tauri app.
- The story distinguishes app-scoped shortcuts from desktop global shortcuts so the web build remains viable.
- Capability and permission work is part of the story, not a hidden follow-up.
- Implemented a single shortcut registry with normalized bindings, duplicate/prefix conflict rejection, role-aware filtering, and shared overlay/dispatcher metadata.
- Added the `ShortcutLayer` and `ShortcutOverlay` to the protected app shell with `?`, `Cmd/Ctrl+/`, `G`-prefixed navigation sequences, screen-local create flows, focus restoration, and `Escape` close behavior.
- Added a browser-safe desktop global shortcut bridge and a minimal root Tauri v2 shell that only exposes the overlay opener as a desktop-global shortcut.
- Added operator documentation in `docs/superpowers/specs/2026-04-04-keyboard-shortcuts.md` plus focused shortcut tests and registry unit coverage.
- Validation completed with `pnpm exec vitest run src/tests/shortcuts/ShortcutLayer.test.tsx src/tests/shortcuts/ShortcutRegistry.test.ts`, `pnpm test`, `pnpm lint`, `pnpm build`, and `cargo check --manifest-path src-tauri/Cargo.toml`.

## File List

- docs/superpowers/specs/2026-04-04-keyboard-shortcuts.md
- package.json
- pnpm-lock.yaml
- src/App.tsx
- src/index.css
- src/components/invoices/print/InvoicePrintSheet.tsx
- src/components/shortcuts/ShortcutLayer.tsx
- src/components/shortcuts/ShortcutOverlay.tsx
- src/lib/desktop/globalShortcuts.ts
- src/lib/shortcuts.ts
- src/tests/shortcuts/ShortcutLayer.test.tsx
- src/tests/shortcuts/ShortcutRegistry.test.ts
- src-tauri/Cargo.lock
- src-tauri/Cargo.toml
- src-tauri/build.rs
- src-tauri/capabilities/default.json
- src-tauri/capabilities/shortcuts.json
- src-tauri/gen/schemas/acl-manifests.json
- src-tauri/gen/schemas/capabilities.json
- src-tauri/gen/schemas/desktop-schema.json
- src-tauri/gen/schemas/macOS-schema.json
- src-tauri/icons/32x32.png
- src-tauri/icons/128x128.png
- src-tauri/icons/128x128@2x.png
- src-tauri/icons/icon.icns
- src-tauri/icons/icon.ico
- src-tauri/icons/icon.png
- src-tauri/icons/Square30x30Logo.png
- src-tauri/icons/Square44x44Logo.png
- src-tauri/icons/Square71x71Logo.png
- src-tauri/icons/Square89x89Logo.png
- src-tauri/icons/Square107x107Logo.png
- src-tauri/icons/Square142x142Logo.png
- src-tauri/icons/Square150x150Logo.png
- src-tauri/icons/Square284x284Logo.png
- src-tauri/icons/Square310x310Logo.png
- src-tauri/icons/StoreLogo.png
- src-tauri/src/lib.rs
- src-tauri/src/main.rs
- src-tauri/tauri.conf.json

## Change Log

- 2026-04-04: Implemented Story 12.2 with a shared shortcut registry, overlay/controller, browser-safe desktop global shortcut bridge, root Tauri shell scaffold, explicit shortcut capabilities, validation docs, and focused/frontend build validation.