# UI/UX Research Findings

## Overview

This document consolidates UX research findings for the UltrERP Taiwan localization PoC. Based on analysis of the survey data and context documents, these findings guide component selection, interaction design, and Tauri-specific integration decisions.

---

## 1. shadcn/ui Component Recommendations by Screen

### Screen 1: Customer Management (客戶管理)

| Component | Recommendation | Rationale |
|-----------|----------------|-----------|
| `Table` | Use `shadcn Table` with TanStack Table + virtual scrolling | 5000+ customer rows require virtualization; sortable columns for 公司名稱, 帳餘 |
| `Input` | `shadcn Input` wrapped in `Form` with Zod | Search fields (統一編號, 名稱) need inline validation |
| `Select` | `shadcn Select` for 狀態 filter | Single-select dropdown, values: 全部/正常/停用 |
| `Button` | `Button` variant: default (primary), outline (secondary) | Consistent with other screens |
| `Badge` | `shadcn Badge` for status indicators | 正常=green, 停用=gray/muted |
| `Dialog` | `shadcn Dialog` for 檢視/修改 customer details | Modal pattern keeps context visible |
| `Tooltip` | `shadcn Tooltip` for keyboard shortcut hints | Power user efficiency; show `?` to reveal |
| `Pagination` | TanStack Pagination or custom | 5000+ rows = ~100 pages at 50/page |

**Radix-specific note**: The `Table` component uses native HTML `<table>` with shadcn styling. No Radix dependency. The virtual scrolling library (react-virtual or TanStack virtual) replaces Radix-based solutions.

### Screen 2: Invoice Creation (銷貨發票建立)

| Component | Recommendation | Rationale |
|-----------|----------------|-----------|
| `Table` | `shadcn Table` with inline-editable rows | Invoice line items (品項) need real-time calculation |
| `Select` | `shadcn Select` for 客戶, 稅率, 課稅別 | Multiple dropdowns; consider async search for 客戶 |
| `Input` | `shadcn Input` for 數量, 單價, 品名 | Numeric inputs with thousand separators on blur |
| `Button` | `primary` (送出eGUI), `secondary` (儲存草稿), `outline` (取消) | Clear action hierarchy |
| `Badge` | `shadcn Badge` for eGUI state indicator | 草稿=gray, 已送出=yellow, 已開立=green, 已作廢=red |
| `Dialog` | `shadcn Dialog` for 確認送出, 錯誤訊息 | Destructive action confirmation |
| `Toast` | `shadcn Toast` / Sonner for operation feedback | Immediate feedback for save/submit actions |
| `Form` | `shadcn Form` with Zod validation | Unified validation for all invoice fields |

**Radix risk note**: The dropdown for 客戶 selection may hit the known Tauri dropdown bug (`github.com/shadcn-ui/ui/issues/7433`). Mitigation: Use React 19 as required by survey findings.

### Screen 3: Inventory Check (庫存查詢)

| Component | Recommendation | Rationale |
|-----------|----------------|-----------|
| `Table` | `shadcn Table` + TanStack Table + react-virtual | 5000+ SKUs need virtualized scrolling |
| `Input` | `shadcn Input` for 產品代號, 產品名稱 search | Live search with debounce (300ms) |
| `Select` | `shadcn Select` for 倉庫 filter | Options: 總倉, 分倉, 在途 |
| `Button` | `primary` (調整庫存), `secondary` (補貨建議), `outline` (庫存報表) | Action-oriented layout |
| `Alert` | `shadcn Alert` (variant: warning) for low stock warning | Prominent but non-blocking |
| `Badge` | `shadcn Badge` for stock status | 正常=green, 警告=yellow, 緊急=red, 缺貨=destructive |
| `Card` | `shadcn Card` for inventory summary display | Group related metrics |
| `Sheet` | `shadcn Sheet` for 調整庫存, 補貨建議 side panels | Multi-step without losing context |

**Performance note**: Inventory tables with 5000+ rows will stutter without virtualization. Install `react-virtual` or use TanStack Table's built-in virtual scrolling feature.

---

## 2. Taiwan Localization Decisions

### ROC Date Format

**Decision**: Display ROC dates as `YYY/MM/DD` (e.g., `114/03/30`) in all UI contexts.

| Context | Format | Example |
|---------|--------|---------|
| Display (UI) | ROC `YYY/MM/DD` | 114/03/30 |
| Input (UI) | ROC `YYY/MM/DD` | 114/03/30 |
| Storage (Internal) | ISO 8601 `YYYY-MM-DD` | 2025-03-30 |
| API / eGUI | ISO 8601 | 2025-03-30 |

**Implementation**: Create a `formatROCDate(date: Date): string` utility and `parseROCDate(roc: string): Date` parser. These are pure functions with no side effects - ideal for unit testing first.

### 統一編號 (UBN) Validation

**Decision**: Real-time MOD11 validation on 8th digit entry, debounced at 300ms.

```
Validation algorithm:
1. Pad to 8 digits (if shorter)
2. Weighting pattern: [1,2,1,2,1,2,1,2] (applied to each digit)
3. For two-digit results (>9): split into individual digits and sum
4. (sum % 10) == 0 → valid UBN

Example:
UBN: 1 2 3 4 5 6 7 8
Weight: 1 2 1 2 1 2 1 2
Product: 1 4 3 8 5 12 7 16
Split: 1+4+3+8+5+1+2+7+1+6 = 38
38 % 10 = 8 ≠ 0 → Invalid
```

**UX feedback**: On valid 8-digit UBN entry, show green checkmark (✓) inline below field. On invalid, show red warning icon (⚠) with specific error message. Do NOT use modal dialogs for validation feedback.

### Phone Number Format

| Type | Format | Example |
|------|--------|---------|
| Mobile | 09xx-xxx-xxx | 0912-345-678 |
| Landline (Taipei) | (02) xxxx-xxxx | (02) 2765-4321 |
| Landline (Other) | (0X) xxxx-xxxx | (03) 562-7542 |
| International (API) | +886-9xx-xxx-xxx | +886-912-345-678 |

**Address format**: `[Postal Code] [City][District][Road][Number]` without floor/room indicator in primary field.

### Font and Character Set

**Decision**: Use `Noto Sans TC` for Traditional Chinese. On macOS, system font `Ping Fang TC` is acceptable. Do NOT use zh-CN (simplified) characters anywhere.

---

## 3. Casual vs. Power User Split

### User Personas

| Aspect | Casual User | Power User |
|--------|-------------|------------|
| Primary interface | GUI clicking | CLI + keyboard shortcuts |
| Frequency | Daily, few operations | Hourly, many operations |
| Expertise | Business operations | System internals |
| Efficiency expectation | 3-5 clicks per task | <3 keystrokes per task |

### Interaction Design

**Casual User Path**:
```
1. Navigate via menu hierarchy
2. Fill forms with mouse
3. Submit and wait for confirmation
4. Close window when done
```

**Power User Path**:
```
1. Global shortcut → target screen (Ctrl+Shift+*)
2. Keyboard navigation within form (Tab, arrow keys)
3. Keyboard submission (Ctrl+Enter)
4. Continue to next task
```

### Shortcut Architecture

| Shortcut | Scope | Action |
|----------|-------|--------|
| `Ctrl+Shift+C` | Global | New customer |
| `Ctrl+Shift+N` | Global | New invoice |
| `Ctrl+Shift+L` | Global | Open inventory |
| `Ctrl+Shift+E` | Global | Open invoice list |
| `Ctrl+F` | Screen | Focus search filter |
| `Ctrl+B` | Invoice | Add line item |
| `Ctrl+Enter` | Form | Save draft |
| `Ctrl+Shift+Enter` | Invoice | Submit to eGUI |
| `Ctrl+R` | Screen | Refresh data |
| `Ctrl+P` | Screen | Print/report |
| `Escape` | Modal | Close dialog |
| `?` | Global | Show shortcut overlay |

**Implementation**: Register shortcuts via `tauri-plugin-global-shortcut` at app startup. Handle conflicts: if shortcut already registered by another app, show a warning toast and disable that shortcut.

### Shortcut Overlay Design

Press `?` to show a dismissible overlay with all shortcuts for the current screen:

```
┌─────────────────────────────────────┐
│  鍵盤快捷鍵                         │
├─────────────────────────────────────┤
│  Ctrl+Shift+N    新建發票            │
│  Ctrl+B          新增品項            │
│  Ctrl+Enter      儲存草稿            │
│  Ctrl+Shift+Enter 送出eGUI           │
│  Escape          取消/關閉           │
│                                     │
│              [按任意鍵關閉]          │
└─────────────────────────────────────┘
```

---

## 4. Tauri-Specific Integration Notes

### System Tray

**Implementation**:
```rust
// Cargo.toml
[dependencies]
tauri = { version = "2", features = ["tray-icon"] }
```

```javascript
// main.tsx
import { Tray } from '@tauri-apps/api/tray';
import { Menu } from '@tauri-apps/api/menu';

// Create tray with menu
const tray = await Tray.new();
const menu = await Menu.new([/* items */]);
await tray.setMenu(menu);
```

**Tray behavior**:
- Left-click: Show/focus main window
- Right-click: Show context menu (開啟/關閉/關於)
- App keeps running when all windows closed
- Tray icon persists in dock/menu bar

### Notifications

**Implementation**:
```javascript
import { sendNotification, requestPermission } from '@tauri-apps/plugin-notification';

// Request permission on first invoice submit
const hasPermission = await requestPermission();
if (hasPermission === 'granted') {
  await sendNotification({
    title: 'eGUI 發票狀態',
    body: '發票 #INV-2026-0330 已成功開立'
  });
}
```

**macOS-specific**: Requires `com.apple.UserNotifications.notification-center` entitlement. Test on fresh macOS install early - historically had permission issues.

### Background eGUI State Tracking

**Architecture**:
1. Invoice submitted → persist to SQLite immediately (not just memory)
2. Close window but app keeps running via system tray
3. Background polling via Tauri command (Rust) every 60 seconds
4. On state change → send system notification
5. On app restart → re-hydrate pending invoices from SQLite

**Critical**: Never rely on in-memory state for eGUI status. System tray + background polling + persistent storage is the required architecture.

### Global Shortcuts

**Requirements**: Rust 1.77.2+, `tauri-plugin-global-shortcut`

**Registration**:
```javascript
import { register } from 'tauri-plugin-global-shortcut';

await register('CommandOrControl+Shift+E', () => {
  // Open invoice creation
});
```

**Conflict handling**: Wrap in try/catch. If shortcut already registered by another app, show warning toast.

### WebView and React 19 Requirement

**Critical finding**: React 19 is required for Tauri 2.x + shadcn/ui. React 18 has unresolved dropdown/transform bugs in Tauri webview (`shadcn-ui/ui#7433`).

**Recommendation**: Test on both Apple Silicon and Intel Mac before committing to React 18. If team has dependency conflicts requiring React 18, expect Tauri webview rendering quirks on Intel Macs.

---

## 5. Component Risk Assessment

| Component | Risk Level | Notes |
|-----------|------------|-------|
| Radix Tooltip in Popover | HIGH | Known unfixed bug; avoid nested Tooltip/Popover |
| Radix Dropdown Menu | MEDIUM | Fixed in React 19; requires React 19 on Tauri |
| TanStack Table + Virtual | LOW | Stable, well-documented |
| shadcn Alert | LOW | Pure CSS-based |
| shadcn Dialog | LOW | Based on Radix Dialog, stable |
| tauri-plugin-notification | MEDIUM | macOS permission issues historically |
| tauri-plugin-global-shortcut | LOW | Stable, requires Rust 1.77.2 |

---

## 6. Immediate Next Steps

1. **Validation utilities first**: Implement `formatROCDate`, `parseROCDate`, and `validateUBN` as pure, testable functions. Cover with unit tests before any screen work.

2. **Skeleton app verification**: Build minimal Tauri + React 19 + shadcn/ui shell. Validate dropdown behavior on both Apple Silicon and Intel Mac. This is the PoC gate.

3. **System tray + notification**: Implement minimal tray + notification flow in first sprint. Verify macOS notification permissions work on fresh install.

4. **Table virtualization**: Set up TanStack Table + react-virtual immediately for Customer and Inventory screens. 5000+ rows will stutter without it.

---

*Document version: 1.0*
*Date: 2026-03-30*
*Author: UI/UX Researcher*
