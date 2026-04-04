# UltrERP System Tray Mode

## Scope

Story 12.4 extends the production Tauri shell from Story 12.2 with tray lifecycle control and desktop notifications backed by the durable eGUI state surface from Story 12.3.

The desktop lifecycle source of truth lives in `src-tauri/src/lib.rs`. Browser-safe frontend bridges live in `src/lib/desktop/window.ts` and `src/lib/desktop/notifications.ts`. Hidden-window eGUI polling and dedupe live in `src/lib/desktop/eguiMonitor.ts` and `src/components/desktop/DesktopTrayController.tsx`.

## Runtime Behavior

| Event | Behavior | Source |
| --- | --- | --- |
| Window close button | Prevents process exit and hides the main window to tray | `src-tauri/src/lib.rs` |
| Tray icon click | Restores and focuses the existing main window | `src-tauri/src/lib.rs` |
| Tray `Restore` menu item | Restores and focuses the existing main window | `src-tauri/src/lib.rs` |
| Tray `Quit` menu item | Sets an explicit-quit guard and exits cleanly | `src-tauri/src/lib.rs` |
| Meaningful hidden eGUI transition | Sends one desktop notification when permission is granted | `src/lib/desktop/eguiMonitor.ts` |

## Safety Rules

- The browser build never eagerly imports Tauri window or notification APIs.
- Notification delivery is runtime-gated: check permission, request if needed, and degrade to a no-op when denied.
- Only meaningful eGUI transitions notify: `SENT`, `ACKED`, `FAILED`, `RETRYING`, and `DEAD_LETTER`.
- Duplicate notifications are suppressed with local last-seen and last-notified metadata under `ultrerp_desktop_egui_watch_v1`.
- Local desktop storage is dedupe metadata only; the backend remains the system of record for invoice and eGUI state.

## Manual Validation

### Browser build

1. Run `pnpm dev`.
2. Open an invoice detail page with and without `egui_submission` data.
3. Verify the invoice detail page renders normally and no tray or notification runtime errors appear in the browser console.
4. Verify no desktop permission prompt appears in the browser-only path.

### macOS desktop shell

1. Run `pnpm tauri:dev` on a macOS workstation.
2. Open an invoice detail page for an invoice that already has `egui_submission` state.
3. Close the main window with the window chrome close action.
4. Verify the UltrERP process stays alive and a tray or menu-bar icon remains available.
5. Click the tray icon and verify the existing main window is restored and focused instead of spawning a second instance.
6. Hide the window again, then trigger a meaningful backend eGUI transition for the watched invoice, such as `QUEUED -> SENT` or `SENT -> ACKED`.
7. Verify exactly one desktop notification is shown for that transition.
8. Repeat the same poll cycle without another state change and verify no duplicate notification appears.
9. Use the tray `Quit` action and verify the process exits fully.
10. Relaunch the app and verify stale notifications are not replayed immediately on startup.

### Windows desktop shell

1. Run `pnpm tauri:dev` on a Windows workstation.
2. Open an invoice detail page for an invoice with `egui_submission` state.
3. Close the main window and verify UltrERP moves to the notification area instead of exiting.
4. If the icon is hidden in the overflow area, expose it and verify tray presence there.
5. Verify tray icon click and the tray `Restore` menu both return focus to the same window instance.
6. Hide the window again and trigger a meaningful eGUI transition; verify the Windows notification path delivers once when permission is granted.
7. Deny notification permission and verify the app stays functional without throwing or hanging.
8. Use the tray `Quit` action and verify the process terminates completely.

## Tauri Capability Notes

- `src-tauri/Cargo.toml` enables the `tray-icon` feature on `tauri` and wires `tauri-plugin-notification`.
- `src-tauri/capabilities/default.json` explicitly grants window show, hide, unminimize, focus, visibility, and notification permissions used by the desktop bridge.
- If a packaged desktop build also ships a backend sidecar on Windows, keep WiX preferred over NSIS until the known NSIS sidecar reinstall issue is no longer relevant.