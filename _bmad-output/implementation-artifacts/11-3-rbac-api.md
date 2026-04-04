# Story 11.3: RBAC in API

Status: completed

## Story

As a system,
I want to enforce role-based access control consistently in the API layer,
so that unauthorized access is blocked at all endpoints and access attempts are logged.

## Context

UltrERP currently has no API-level authentication. All endpoints are open. The MCP layer has API key auth (`app/mcp_auth.py`) with `TOOL_SCOPES` and `DEFAULT_ROLE_SCOPES`, but REST API endpoints have zero auth. This story adds JWT-based authentication and RBAC to all REST API endpoints.

### Existing Auth Infrastructure

- `app/mcp_auth.py` already defines `DEFAULT_ROLE_SCOPES` (admin, finance, sales, agent) and `TOOL_SCOPES`
- PyJWT 2.12.1 is already in the lockfile (transitive dep from another package)
- User model created in Story 11.1 with `email`, `password_hash`, `role`, `status`
- `verify_password()` from `domains/users/auth.py` (Story 11.1)

### Role → Permission Matrix (FR44, FR45, NFR14)

| Endpoint Pattern | owner | finance | warehouse | sales |
|---|---|---|---|---|
| `GET /api/v1/inventory/*` | ✅ | ❌ | ✅ | ✅ (read-only) |
| `POST/PATCH /api/v1/inventory/*` | ✅ | ❌ | ✅ | ❌ |
| `GET /api/v1/customers/*` | ✅ | ✅ (read-only) | ❌ | ✅ |
| `POST/PATCH /api/v1/customers/*` | ✅ | ❌ | ❌ | ✅ |
| `GET /api/v1/invoices/*` | ✅ | ✅ | ❌ | ✅ (read-only) |
| `POST /api/v1/invoices/*` | ✅ | ✅ | ❌ | ✅ |
| `GET /api/v1/orders/*` | ✅ | ❌ | ✅ (read-only) | ✅ |
| `POST/PATCH /api/v1/orders/*` | ✅ | ❌ | ❌ | ✅ |
| `GET /api/v1/payments/*` | ✅ | ✅ | ❌ | ❌ |
| `POST /api/v1/payments/*` | ✅ | ✅ | ❌ | ❌ |
| `GET /api/v1/dashboard/*` | ✅ | ✅ | ✅ | ✅ |
| `/api/v1/admin/*` | ✅ | ❌ | ❌ | ❌ |
| `GET /api/v1/health/*` | ✅ | ✅ | ✅ | ✅ |
| AEO endpoints (jsonld, aeo, sitemap) | No auth (public) | | | |

### Architecture Decision

- **JWT tokens** with HS256 signing, configurable secret via `JWT_SECRET` env var
- **Login endpoint**: `POST /api/v1/auth/login` (email + password → JWT)
- **Auth dependency**: `get_current_user` extracts and validates JWT from `Authorization: Bearer <token>` header
- **Role enforcement**: `require_role(*roles)` dependency factory returns 403 if user's role is not in allowed roles
- **New `backend/domains/auth/` domain** for login endpoint
- **New `backend/common/auth.py`** for reusable auth dependencies (used across all routers)
- Token payload: `{"sub": str(user_id), "tenant_id": str(tenant_id), "role": "finance", "exp": ...}`
- Access token TTL: configurable via `JWT_ACCESS_TOKEN_MINUTES` (default 480 = 8 hours for desktop ERP)
- **Public endpoints** (health, AEO/sitemap, root) remain unauthenticated
- Audit log records 403 access attempts with `actor_type="user"`, `action="auth.forbidden"`
- **No refresh tokens in this story** — desktop ERP app, 8-hour session is sufficient

### Critical Security Decisions

- JWT secret MUST be at least 32 characters, validated at startup
- Passwords verified via `bcrypt.checkpw()` (constant-time comparison)
- Failed login returns generic 401 "Invalid credentials" — never reveals whether email or password is wrong
- Token expiry is enforced; expired tokens return 401
- Disabled users (`status != "active"`) cannot log in

## Acceptance Criteria

**AC1:** Login endpoint
**Given** a user exists with email "admin@example.com" and a valid password
**When** I request `POST /api/v1/auth/login` with `{"email": "admin@example.com", "password": "correctpassword"}`
**Then** the response includes `access_token` (JWT string) and `token_type: "bearer"`
**And** the JWT contains `sub` (user_id), `tenant_id`, `role`, `exp`

**AC2:** Login failure
**Given** wrong credentials
**When** I request `POST /api/v1/auth/login`
**Then** the response is 401 with `{"detail": "Invalid credentials"}`
**And** no token is issued
**And** the error message does NOT reveal whether email or password is wrong

**AC3:** Disabled user cannot login
**Given** a user with status="disabled"
**When** they attempt to login with correct credentials
**Then** the response is 401 with `{"detail": "Invalid credentials"}`

**AC4:** Protected endpoints require Bearer token
**Given** a protected endpoint (any under `/api/v1/` except health, auth, and public AEO)
**When** I request without `Authorization` header
**Then** the response is 401

**AC5:** Role enforcement
**Given** a user with role="warehouse" has a valid token
**When** they access `GET /api/v1/invoices/` (requires finance, sales, or owner)
**Then** the response is 403 Forbidden
**And** an audit log entry is created with action="auth.forbidden"

**AC6:** Owner has full access
**Given** a user with role="owner" has a valid token
**When** they access any endpoint
**Then** access is granted (owner bypasses role checks)

**AC7:** Me endpoint
**Given** a valid JWT token
**When** I request `GET /api/v1/auth/me`
**Then** the response includes the current user's id, email, display_name, role, status

**AC8:** JWT configuration
**Given** `JWT_SECRET` is not set or is shorter than 32 characters
**When** the application starts
**Then** it fails with a clear error message (do not start with insecure defaults)

**AC9:** All existing tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass (tests that call API endpoints need Bearer token mocking or test auth bypass)
**And** new auth tests are added (≥ 15 tests)

## Tasks / Subtasks

- [x] **Task 1: Add JWT configuration** (AC8)
  - [x] Add to `backend/common/config.py`:
    ```python
    jwt_secret: str = Field(
        ...,  # REQUIRED — no default
        validation_alias=AliasChoices("JWT_SECRET", "jwt_secret"),
    )
    jwt_access_token_minutes: int = Field(
        default=480,
        validation_alias=AliasChoices("JWT_ACCESS_TOKEN_MINUTES", "jwt_access_token_minutes"),
    )
    ```
  - [x] Add `pyjwt[crypto]>=2.12.0` to `pyproject.toml` dependencies (make explicit)
  - [x] **CRITICAL:** Since `jwt_secret` is required (no default), ALL existing tests will break unless env provides it. Add `JWT_SECRET=test-secret-at-least-32-characters-long` to the test fixtures or conftest.py.

- [x] **Task 2: Auth dependencies** (AC4, AC5, AC6)
  - [x] Create `backend/common/auth.py`:
    ```python
    """Authentication dependencies for FastAPI routes."""
    from __future__ import annotations
    import jwt
    from fastapi import Depends, HTTPException, status
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    from common.config import settings

    _bearer_scheme = HTTPBearer(auto_error=False)

    async def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    ) -> dict:
        """Decode JWT, return payload dict with sub, tenant_id, role."""
        if not credentials:
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret,
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload

    def require_role(*allowed_roles: str):
        """Dependency factory: returns 403 if user role not in allowed_roles."""
        async def _check(user: dict = Depends(get_current_user)) -> dict:
            if user["role"] == "owner":
                return user  # owner bypasses all role checks
            if user["role"] not in allowed_roles:
                raise HTTPException(status_code=403, detail="Forbidden")
            return user
        return _check
    ```

- [x] **Task 3: Login endpoint** (AC1, AC2, AC3)
  - [x] Create `backend/domains/auth/__init__.py`
  - [x] Create `backend/domains/auth/routes.py`:
    - `POST /login` — validate email+password, check user active, issue JWT
    - `GET /me` — return current user info from token (AC7)
  - [x] Create `backend/domains/auth/schemas.py`:
    - `LoginRequest`: email (str), password (str)
    - `TokenResponse`: access_token (str), token_type (str = "bearer")
  - [x] Mount at `/api/v1/auth` in main.py

- [x] **Task 4: Apply auth to existing routers** (AC4, AC5)
  - [x] Update each domain router to use `Depends(get_current_user)` or `Depends(require_role(...))`:
    - `domains/inventory/routes.py` — `require_role("warehouse", "sales")` for GET, `require_role("warehouse")` for POST/PATCH
    - `domains/customers/routes.py` — `require_role("finance", "sales")` for GET, `require_role("sales")` for POST/PATCH
    - `domains/invoices/routes.py` — `require_role("finance", "sales")` for GET, `require_role("finance", "sales")` for POST
    - `domains/orders/routes.py` — `require_role("warehouse", "sales")` for GET, `require_role("sales")` for POST/PATCH
    - `domains/payments/routes.py` — `require_role("finance")` for all
    - `domains/dashboard/routes.py` — `Depends(get_current_user)` (any authenticated role)
    - `domains/users/routes.py` — `require_role("owner")` (admin only from 11.1)
    - `domains/audit/routes.py` — `require_role("owner")` (admin only from 11.6)
  - [x] **Leave public:** health, AEO (jsonld, aeo, sitemap), root `/`, LINE webhook
  - [x] **Audit 403 attempts:** In `require_role`, write audit log for forbidden attempts

- [x] **Task 5: Fix existing tests** (AC9)
  - [x] Create a test helper/conftest fixture that provides a valid Bearer token:
    ```python
    # In conftest.py or test helpers
    import jwt
    from datetime import datetime, timedelta, timezone

    def make_test_token(role="owner", user_id="00000000-0000-0000-0000-000000000111"):
        payload = {
            "sub": user_id,
            "tenant_id": str(DEFAULT_TENANT_ID),
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        }
        return jwt.encode(payload, "test-secret-at-least-32-characters-long", algorithm="HS256")
    ```
  - [x] Update ALL existing API tests to include `Authorization: Bearer <token>` header
  - [x] Set `JWT_SECRET=test-secret-at-least-32-characters-long` in test environment

- [x] **Task 6: Auth tests** (AC1-AC9)
  - [x] Create `backend/tests/test_auth.py`:
    - `test_login_success` — returns token with correct payload
    - `test_login_wrong_password_401`
    - `test_login_nonexistent_email_401`
    - `test_login_disabled_user_401`
    - `test_login_generic_error_message` — verify message doesn't reveal which field is wrong
    - `test_protected_endpoint_no_token_401`
    - `test_protected_endpoint_expired_token_401`
    - `test_protected_endpoint_invalid_token_401`
    - `test_role_enforcement_forbidden_403`
    - `test_owner_bypasses_role_check`
    - `test_me_endpoint_returns_user_info`
    - `test_warehouse_cannot_access_invoices_403`
    - `test_finance_can_access_invoices`
    - `test_sales_can_access_customers`
    - `test_forbidden_creates_audit_log`

## File Changes

### New Files
| File | Purpose |
|------|---------|
| `backend/common/auth.py` | `get_current_user`, `require_role` dependencies |
| `backend/domains/auth/__init__.py` | Module init |
| `backend/domains/auth/routes.py` | Login + me endpoints |
| `backend/domains/auth/schemas.py` | Login request/response models |
| `backend/tests/test_auth.py` | Auth tests |

### Modified Files
| File | Change |
|------|--------|
| `backend/common/config.py` | Add `jwt_secret`, `jwt_access_token_minutes` |
| `backend/pyproject.toml` | Add `pyjwt[crypto]>=2.12.0` |
| `backend/app/main.py` | Mount auth router at `/api/v1/auth` |
| `backend/domains/inventory/routes.py` | Add role dependencies |
| `backend/domains/customers/routes.py` | Add role dependencies |
| `backend/domains/invoices/routes.py` | Add role dependencies |
| `backend/domains/orders/routes.py` | Add role dependencies |
| `backend/domains/payments/routes.py` | Add role dependencies |
| `backend/domains/dashboard/routes.py` | Add auth dependency |
| `backend/domains/users/routes.py` | Add owner-only dependency |
| `backend/domains/audit/routes.py` | Add owner-only dependency |
| `backend/tests/conftest.py` (or test helpers) | Add `make_test_token` fixture |
| ALL existing test files | Add Bearer token to API calls |

### Review Findings

- [x] [Review][Patch] JWT claim validation now fails closed: `get_current_user()` requires `exp/sub/tenant_id/role`, validates UUID-shaped `sub`/`tenant_id`, and rejects unknown REST roles before route code sees the payload.
- [x] [Review][Patch] `/me` coverage asserts the returned id, email, display_name, role, and status fields in `tests/test_auth.py`.
- [x] [Review][Patch] `LoginRequest.email` already uses `EmailStr` in `domains/auth/schemas.py`; the stale finding was closed as documentation drift.
- [x] [Review][Patch] `jwt_access_token_minutes` now has `ge=1` bounds in `common/config.py`; the stale finding was closed as documentation drift.
- [x] [Review][Patch] Login flow guards against missing `password_hash` before `verify_password()` is called.
- [x] [Review][Patch] AC5: Forbidden API access now writes an `auth.forbidden` audit entry before the 403 response, with focused coverage in `tests/test_auth.py`

## Dev Agent Record

### Implementation Notes
- JWT auth with HS256 and configurable secret via `JWT_SECRET` env var (≥32 chars, required, no default)
- Changed Settings from eager `settings = get_settings()` to lazy `_LazySettings` proxy to prevent import-time crash when JWT_SECRET is not set
- Created `common/auth.py` with `get_current_user` (JWT decode, 401) and `require_role(*roles)` (factory, owner bypass, 403)
- Login endpoint verifies email+password+active status; uses same "Invalid credentials" message for all failure modes (no info leak)
- Applied auth to all 8 domain routers: payments (finance), dashboard (any auth), audit (owner), users (owner), invoices (finance/sales), customers (per-endpoint read/write), orders (per-endpoint read/write), inventory (per-endpoint read/write)
- AEO endpoints (`get_product_jsonld`, `get_product_aeo`) left public intentionally
- Updated `_helpers.py` with `make_test_token()` and `auth_header()` defaults for all `http_*` functions
- Manually updated 11 test files using direct `AsyncClient` on protected endpoints
- 17 new auth tests covering login success/failures, token validation, role enforcement, owner bypass, and cross-role access
- 2026-04-04 follow-up: REST JWT validation now uses PyJWT required-claim enforcement plus explicit role and UUID claim checks, closing the malformed-token acceptance gap.
- 2026-04-04 follow-up: owner-only intent for `/api/v1/admin/users` and `/api/v1/admin/audit-logs` is now explicit in routing, with focused 403 coverage for non-owner requests.

### Follow-up Resolution: Audit 403 Attempts
The deferred AC5 gap was closed in the Epic 11 follow-up review. `require_role` now performs a best-effort audit write for forbidden requests before returning 403, and the focused auth test slice was updated to assert the `auth.forbidden` entry exists.

### Test Results
- 530 total tests (513 existing + 17 new auth)
- 529 passing, 1 flaky pre-existing (`test_health_reports_mcp` — event loop issue in MCP SSE test, unrelated)
- All 17 auth tests passing
- 2026-04-04 follow-up review: focused `tests/test_auth.py` slice passed with 20 tests after tightening malformed-token validation and keeping the forbidden-access audit coverage in place

## Dev Notes

- **THIS IS THE HIGHEST RISK STORY** — it modifies every existing router and breaks every existing API test. Plan the test fixture approach FIRST before touching routers.
- **JWT_SECRET is REQUIRED (no default)** — this is a security decision. The app must not start without it. Tests must provide it via env or monkeypatch.
- **Owner role is the super-admin** — bypasses all role checks. This is consistent with the MCP `admin` scope bypass in `mcp_auth.py`.
- **Login returns generic error** — "Invalid credentials" for ALL failure cases (wrong email, wrong password, disabled user). This prevents user enumeration attacks.
- **Audit log for 403** — the story AC says "audit_log records the access attempt". This means the `require_role` dependency must have access to a DB session to write the audit log. Consider making audit 403 logging best-effort (catch exceptions, log warning, don't fail the request).
- **LINE webhook must remain unauthenticated** — LINE sends POST requests with its own signature verification. Do not add Bearer auth to `/api/v1/line/webhook`.
- TAB indentation. Ruff py312 rules E/F/I.
