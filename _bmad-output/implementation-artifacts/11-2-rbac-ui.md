# Story 11.2: RBAC in UI

Status: completed

## Story

As a system,
I want to enforce RBAC in the UI,
so that users only see features appropriate to their role.

## Context

UltrERP's React frontend (`src/`) built with Vite currently shows all menu items to all users. Story 11.3 added JWT-based API authentication. This story wires the frontend to:
1. Store the JWT token and user info
2. Send the token with all API requests
3. Filter navigation/menu items based on the user's role
4. Redirect unauthenticated users to a login page

### Role → UI Visibility (FR44)

| Menu Item | owner | finance | warehouse | sales |
|-----------|-------|---------|-----------|-------|
| Dashboard | ✅ | ✅ | ✅ | ✅ |
| Inventory | ✅ | ❌ | ✅ | ✅ (read-only) |
| Customers | ✅ | ✅ (read-only) | ❌ | ✅ |
| Invoices | ✅ | ✅ | ❌ | ✅ (read-only) |
| Orders | ✅ | ❌ | ✅ (read-only) | ✅ |
| Payments | ✅ | ✅ | ❌ | ❌ |
| Admin (Users) | ✅ | ❌ | ❌ | ❌ |
| Admin (Audit) | ✅ | ❌ | ❌ | ❌ |

### Existing Frontend Structure

- `src/App.tsx` — main app with routing
- `src/pages/` — page components
- `src/components/` — shared components (likely navigation/sidebar)
- `src/lib/` — API client utilities
- `src/hooks/` — custom hooks
- TypeScript, Vite, React

### Architecture Decision

- **Auth context** via React Context + `useAuth()` hook
- **Token storage**: `localStorage` (acceptable for desktop ERP, Tauri app)
- **API interceptor**: Add `Authorization: Bearer <token>` to all API requests via the existing fetch/API client
- **Login page**: New `src/pages/LoginPage.tsx`
- **Route guard**: `ProtectedRoute` component wrapping authenticated routes
- **Role filter**: `usePermissions()` hook exposes `canAccess(feature)` function
- **Logout**: Clear token, redirect to login

## Acceptance Criteria

**AC1:** Login page
**Given** I'm not logged in
**When** I visit any page
**Then** I'm redirected to the login page
**And** I can enter email and password
**And** on success, I'm redirected to the dashboard
**And** on failure, I see a generic error message

**AC2:** Menu filtering by role
**Given** I'm logged in as a finance user
**When** I see the navigation menu
**Then** I see: Dashboard, Customers (read-only), Invoices, Payments
**And** I do NOT see: Inventory, Orders, Admin

**AC3:** Warehouse role menu
**Given** I'm logged in as a warehouse user
**When** I see the navigation menu
**Then** I see: Dashboard, Inventory, Orders (read-only)
**And** I do NOT see: Customers, Invoices, Payments, Admin

**AC4:** Sales role menu
**Given** I'm logged in as a sales user
**When** I see the navigation menu
**Then** I see: Dashboard, Inventory (read-only), Customers, Invoices (read-only), Orders
**And** I do NOT see: Payments, Admin

**AC5:** Owner sees everything
**Given** I'm logged in as an owner
**When** I see the navigation menu
**Then** I see all menu items including Admin

**AC6:** Token sent with API requests
**Given** I'm logged in
**When** any API request is made
**Then** the `Authorization: Bearer <token>` header is included
**And** if the token is expired (401 response), I'm redirected to login

**AC7:** Logout
**Given** I'm logged in
**When** I click logout
**Then** the token is cleared from storage
**And** I'm redirected to the login page

**AC8:** Direct URL access protection
**Given** I'm a warehouse user
**When** I navigate directly to `/invoices`
**Then** I'm redirected to the dashboard (or see a "forbidden" message)

**AC9:** Frontend tests/lint pass
**Given** the updated frontend code
**When** I run `pnpm lint && pnpm build`
**Then** no errors
**And** TypeScript compiles cleanly

## Tasks / Subtasks

- [x] **Task 1: Auth context & JWT lifecycle**
  - [x] `src/hooks/useAuth.tsx` persists the token, decodes Base64URL JWT payloads, restores sessions from `localStorage`, and clears auth state on logout or expiry.

- [x] **Task 2: Read/write-aware permissions**
  - [x] `src/hooks/usePermissions.ts` now distinguishes readable vs writable feature access so the UI can hide create/write affordances without weakening backend enforcement.

- [x] **Task 3: Login + API token propagation**
  - [x] `src/pages/LoginPage.tsx` authenticates against `/api/v1/auth/login`, and the shared API client continues to inject `Authorization: Bearer <token>` plus redirect on 401.

- [x] **Task 4: Route guards**
  - [x] `src/components/ProtectedRoute.tsx` now guards authentication, feature access, and write-only routes.

- [x] **Task 5: Navigation/menu filtering**
  - [x] A new `src/components/AppNavigation.tsx` filters nav items by role and exposes logout in the authenticated shell.

- [x] **Task 6: Route surface completion**
  - [x] `src/App.tsx` now mounts protected routes for inventory, invoices, payments, and admin, and the dashboard quick actions honor read vs write permissions.

- [x] **Task 7: Focused validation**
  - [x] Frontend RBAC tests pass and the production build completes cleanly.

## File Changes

### New Files
| File | Purpose |
|------|---------|
| `src/hooks/useAuth.tsx` | Auth context provider and hook |
| `src/hooks/usePermissions.ts` | Role-based permission checker |
| `src/pages/LoginPage.tsx` | Login page |
| `src/components/ProtectedRoute.tsx` | Route guard component |
| `src/components/AppNavigation.tsx` | Role-filtered authenticated navigation |
| `src/pages/InventoryPage.tsx` | Inventory route shell |
| `src/pages/InvoicesPage.tsx` | Invoices browse/detail route shell |
| `src/pages/PaymentsPage.tsx` | Payments reconciliation route shell |
| `src/pages/AdminPage.tsx` | Owner-only users and audit dashboard |
| `src/lib/authStorage.ts` | Shared token storage helpers and same-window auth sync event |
| `src/lib/api/admin.ts` | Admin users/audit query helpers |

### Modified Files
| File | Change |
|------|--------|
| `src/App.tsx` | Authenticated shell, protected routes, and write-gated create routes |
| `src/pages/dashboard/DashboardPage.tsx` | Role-aware quick actions for browse vs create flows |
| `src/lib/apiFetch.ts` | Bearer token injection plus same-window 401 logout synchronization |
| `src/lib/routes.ts` | Route constants for inventory, invoices, payments, and admin |
| `src/index.css` | Authenticated shell and navigation styling |
| `src/tests/auth/rbac-ui.test.tsx` | Navigation, write-permission, login redirect, and 401 logout-sync coverage |

## Dev Agent Record

- **Implemented by:** Copilot Agent
- **Date:** 2026-04-04
- **Validation:** `src/tests/auth/rbac-ui.test.tsx` passed with 15 focused tests; `pnpm exec vite build` completed successfully on the prior Epic 11 validation run.
- **Implementation notes:**
  - Read-only feature access now stays visible where the PRD expects browse access, while create/write routes are blocked separately.
  - The authenticated shell now exposes the full Epic 11 menu surface instead of only dashboard/customer/order shortcuts.
  - Admin-only visibility is enforced both in navigation and direct route access.
  - 2026-04-04 follow-up: same-window 401/logout handling now uses a shared auth-storage event because browser `storage` events only fire in other browsing contexts.
  - 2026-04-04 follow-up: authenticated users are redirected away from `/login`, and focused coverage now asserts role-filtered navigation plus read/write permission behavior.

## Dev Notes

- **Decode JWT on the client side** — the token payload contains role, email, etc. Use a lightweight JWT decode (no verification needed on client — server validates the signature).
- **Do NOT store password** in localStorage. Only the JWT token.
- **Read-only mode** for some role+feature combos (e.g., sales+inventory) is a UI hint only. The API enforces it via 403. The UI can hide write buttons or show a toast "read-only access".
- **No user registration page** — users are created by admin (Story 11.1). Only login is needed.
- **Token expiry**: When the API returns 401, clear the token and redirect to login. No automatic refresh.
- Check existing navigation components before creating new ones — the sidebar/nav likely already exists and just needs role filtering.
- TAB indentation (if TS/JSX files use spaces, follow existing convention). Run `pnpm lint` to verify.
