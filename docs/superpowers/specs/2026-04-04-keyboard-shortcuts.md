# UltrERP Keyboard Shortcuts

## Scope

Story 12.2 adds a single shortcut registry for app-scoped navigation, a discoverable overlay, and a minimal desktop-global shortcut path for the production Tauri shell scaffold.

The source of truth lives in `src/lib/shortcuts.ts`. The browser-safe desktop bridge lives in `src/lib/desktop/globalShortcuts.ts`. Tauri capability files live under `src-tauri/capabilities/`.

## Supported Shortcuts

### Global

| Action | Binding | Notes |
| --- | --- | --- |
| Open shortcuts | `?` | App-scoped only |
| Open shortcuts | `Cmd+/` on macOS, `Ctrl+/` on Windows/Linux | App-scoped in browser and desktop-global in Tauri |
| Go to dashboard | `G` then `D` | Requires dashboard access |
| Go to inventory | `G` then `I` | Requires inventory access |
| Go to customers | `G` then `C` | Requires customers access |
| Go to invoices | `G` then `V` | Requires invoices access |
| Go to orders | `G` then `O` | Requires orders access |
| Go to payments | `G` then `P` | Requires payments access |
| Go to admin | `G` then `A` | Requires admin access |

### Screen-local

| Screen | Action | Binding | Notes |
| --- | --- | --- | --- |
| Customers list | New customer | `C` then `N` | Requires customer write access |
| Invoices list | New invoice | `V` then `N` | Requires invoice write access |
| Orders list | New order | `O` then `N` | Requires order write access |

## Safety Rules

- Shortcuts are suppressed inside `input`, `textarea`, `contenteditable`, and ARIA `textbox` controls.
- The browser build never imports `@tauri-apps/plugin-global-shortcut` eagerly.
- The only desktop-global shortcut is the overlay opener. No destructive write actions are registered globally.
- Desktop registration uses explicit Tauri v2 capabilities instead of implicit plugin access.

## Manual Validation

### Browser build

1. Run `pnpm dev`.
2. Verify `?` opens the overlay and `Escape` closes it.
3. Verify `G` then `C` navigates to Customers, and `C` then `N` opens the create-customer flow.
4. Focus an input or rich textbox and verify the same bindings do nothing.

### macOS desktop shell

1. Run `pnpm tauri:dev`.
2. Verify `Cmd+/` opens the overlay while UltrERP is focused.
3. Verify the same binding is registered through the Tauri plugin path backed by `src-tauri/capabilities/shortcuts.json`.
4. Verify app-scoped navigation sequences still work after the desktop shell starts.
5. Close the app and relaunch it to confirm the shortcut can be registered again without stale-registration failures.

### Windows desktop shell

1. Run `pnpm tauri:dev` on a Windows workstation.
2. Verify `Ctrl+/` opens the overlay and `G`-prefixed navigation sequences work.
3. Verify the desktop shell does not bind any `Alt+<letter>` shortcuts that could collide with menu accelerators.
4. Temporarily remove `src-tauri/capabilities/shortcuts.json` from the build and confirm registration fails explicitly rather than silently broadening permission scope.

## Tauri Capability Notes

- `src-tauri/capabilities/default.json` keeps the shell on `core:default`.
- `src-tauri/capabilities/shortcuts.json` explicitly grants `global-shortcut:allow-is-registered`, `global-shortcut:allow-register`, and `global-shortcut:allow-unregister`.
- If desktop shortcut registration fails, the browser-safe app-scoped shortcuts still work because the frontend bridge catches registration errors and does not hard-crash the UI.