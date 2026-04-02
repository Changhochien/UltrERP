# UI/UX Survey

## Known Facts

### Stack Viability
- **Tauri 2.x + Vite + React** is a stable, well-documented combination. Installer size advantage (8MB vs 120MB Electron) is real and significant for SMB distribution.
- **shadcn/ui + Radix UI** works on Tauri but requires attention to React version. As of early 2026, React 19 is required to fix a known dropdown/transform bug on Tauri (`github.com/shadcn-ui/ui/issues/7433`). React 18 has unresolved rendering quirks in Tauri webview.
- **Radix UI maintenance**: There is active community concern (2025-2026) about Radix UI bug backlog (e.g., Tooltip-within-Popover bugs unfixed for years). shadcn's team has acknowledged this and is exploring Base UI as a fallback for some components. For the PoC, Radix is acceptable but document all Radix-specific bug workarounds.
- **shadcn/ui Table** needs virtualization for datasets above ~5,000 rows. Use `react-virtual` or TanStack Table with virtual scrolling. Without it, the customer list and inventory screens will stutter on SMB-scale data (a few thousand rows is typical).

### Taiwan Localization

- **ROC Date Format**: Always display as `YYY/MM/DD` where `YYY = Gregorian year - 1911`. So March 30, 2025 is `114/03/30`. Storage must be ISO 8601 (`YYYY-MM-DD`) internally. UI layer handles display conversion only. Both input and output need ROC format everywhere in the UI.
- **Tax ID (統一編號)** validation: 8 digits using the current Taiwan business-number checksum guidance. Weighting pattern is `12121241` (`1,2,1,2,1,2,4,1`). Two-digit products are split into individual digits before summing. Current compatible acceptance uses the revised divisibility-by-5 rule, with the documented seventh-digit special case when digit 7 equals `7`. Real-time validation feedback must occur on the 8th digit entry (not on form submit), since users are accustomed to seeing immediate feedback from other Taiwan government systems. Use a non-blocking inline message (green check or red warning below the field, not a modal).
- **Taiwan phone formats**: Mobile 09xx-xxx-xxx, landline (02) xxxx-xxxx, plus international +886 prefix for API contexts. Address format: postal code (3 digits) + city/district + road name + number. No special character for floor/room.
- **Traditional Chinese** throughout UI. Use `noto-sans-tc` or system font on macOS (Ping Fang TC). Do not use zh-CN simplified characters anywhere.

### System Integration

- **System Tray (Tauri 2.x)**: Enable via `tauri = { features = ["tray-icon"] }`. JS APIs at `@tauri-apps/api/tray` and `@tauri-apps/api/menu`. Tray icon keeps the app alive when all windows are closed. Events available: Click, DoubleClick, Enter, Move, Leave. Menu attaches with `menuOnLeftClick` option. This is the correct pattern for "run in background" on both macOS and Windows.
- **Notifications**: `tauri-plugin-notification` (Rust) + `@tauri-apps/plugin-notification` (JS). macOS requires notification permission request at runtime (call `requestPermission()` before first `sendNotification()`). Historically had permission/harden issues on macOS - test early. Notification is appropriate for eGUI state transitions (issued / validated / invalidated by tax authority).
- **Global Shortcuts**: `tauri-plugin-global-shortcut`. Requires Rust 1.77.2. Supports Windows, macOS, Linux (X11 only). For power users: `Ctrl+Shift+E` to open invoice creation, `Ctrl+Shift+L` for customer list. Register shortcuts at app startup and handle conflicts gracefully (show a warning if a shortcut is already in use by another app).

### eGUI (Taiwan e-Invoice) UX

- eGUI has been mandatory for B2B, B2C, B2G since January 2021. Invoices must be in MIG 4.0/4.1 XML format with digital signature.
- Invoice creation screen must show eGUI state indicator: `草稿` (draft) → `已送出` (submitted) → `已開立` (issued) → `已作廢` (voided). These state transitions can take minutes to hours (async). Use a status badge with timestamp and a refresh button; do not auto-poll more than every 60 seconds.
- eGUI submission is asynchronous. The app should send notification when state changes from background API polling. Background operation (via system tray) is essential for this reason.

### Keyboard Shortcuts (Power Users)

- Power users expect CLI-like efficiency. Document shortcuts in a dismissible overlay (`?` key).
- Suggested baseline: `Ctrl+Shift+N` new invoice, `Ctrl+Shift+C` new customer, `Escape` close dialog/sheet, `Ctrl+F` focus search filter on current screen.
- In lists: arrow keys for row navigation, Enter to open, `Ctrl+E` to edit inline.

---

## Unknowns / Open Questions

1. **React 19 vs React 18 on Tauri 2.x**: Is the team pinned to React 18 for any reason (e.g., other dependencies)? If so, expect Tauri webview rendering quirks on some Intel Macs. Recommendation: test on both Apple Silicon and Intel MacBook before committing.
2. **Inventory reorder alert UX**: What is the actual reorder threshold model? Fixed safety stock per item? ML-based? The screen layout (alert banner vs. dedicated view) depends on alert frequency. If >10% of SKUs are frequently below reorder point, a dedicated "Attention Needed" view with bulk action is better than intrusive banners.
3. **eGUI API integration**: Is the team using a turnkey provider (ECPay, 嘖嘖) or direct IRS API (MIG 4.1)? Turnkey providers simplify state tracking but add a dependency. Direct API gives full control but requires handling MIG XML signing. The PoC should mock eGUI state with realistic timing so UI can be validated regardless.
4. **Taiwan address autocomplete**: Does the team have a postal code + city + district + road dataset? This is needed for a good address input UX. Third-party data providers exist; a simple JSON dataset of all Taiwan postal codes is ~5MB.
5. **Data grid row limit for PoC**: What is the expected maximum rows for customer list and inventory at the target SMB? This determines whether pagination (simpler) or virtual scrolling (better UX) is needed immediately.
6. **CLI power user shell**: Is `erp customers list` etc. a Tauri-side command (Rust) or a separate CLI binary? This affects how keyboard shortcuts are routed and whether CLI and GUI share state.

---

## Top 3 Risks

### 1. Radix UI / shadcn stability risk (HIGH)
The Radix UI component library has an active bug backlog and uncertain long-term maintenance trajectory as of 2026. Several components (Tooltip, Popover, Dropdown Menu) have known quirks that remain unfixed for extended periods. For a desktop ERP that will be actively developed for years, this is a supply-chain risk. shadcn is actively evaluating Base UI as a replacement for Radix primitives.

**Mitigation**: Pin shadcn to a known-good version. Extract and own the component source (shadcn's "copy not import" model means you own the code). Build a thin wrapper abstraction over Radix primitives so swap-in is possible. Monitor the shadcn Discord/GitHub for migration guides.

### 2. eGUI state UX race condition risk (MEDIUM)
eGUI invoice state transitions are asynchronous (submit → validation → issue, potentially taking hours). If the app is closed/reopened during this window, state can be lost or confusing. The system tray keeps the app alive, but the webview may be unloaded.

**Mitigation**: Persist pending eGUI states to local storage/SQLite immediately on submission. Re-hydrate state on app restart. Show clear "pending" badge with submission timestamp. Never rely on in-memory state alone for any eGUI-related status.

### 3. Taiwan localization field quality risk (MEDIUM)
Tax ID (統一編號) and address formats are error-prone in entry. Power users (accountants, finance staff) will copy-paste from spreadsheets. The real-time Taiwan business-number checksum validation must be robust and fast (<16ms per keystroke). Incorrect tax IDs on invoices are a compliance problem.

**Mitigation**: Implement debounced real-time validation (fire after 300ms of no input). Show clear inline validation state. On blur, if invalid, highlight the field and show the specific error. For address, offer autocomplete from a complete Taiwan postal code dataset.

---

## 3-Point Recommendation

1. **Build a skeleton Tauri window with shadcn/ui + React 19 and validate the webview on both Apple Silicon and Intel Mac before anything else.** The entire UX depends on the webview rendering correctly. Known Tauri + Intel Mac webview issues have been reported. Get a real hardware baseline now. This is the first PoC gate.

2. **Implement ROC date and UBN validation as two standalone, testable utility functions before any screen work.** Date conversion (ISO ↔ ROC) and the current Taiwan business-number checksum are pure functions - easy to unit test thoroughly. These will be called throughout the UI. Get the Taiwan localization logic correct and fully covered by tests first, so every screen inherits correct behavior. Validate UBN on every keystroke (after 8 digits entered) with debounce.

3. **Design the system tray + notification architecture on day one of the PoC.** eGUI state tracking requires the app to run in the background and push notifications on state change. This is not a "add it later" feature - the entire invoice workflow depends on it. Implement a minimal system tray + notification flow (show notification when a mocked invoice state changes) in the first sprint. Verify macOS notification permissions work correctly on a fresh macOS install.
