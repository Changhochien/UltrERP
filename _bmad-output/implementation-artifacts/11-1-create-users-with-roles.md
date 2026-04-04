# Story 11.1: Create Users with Roles

Status: completed

## Story

As an admin,
I want to create users with specific roles,
so that I can control who has access to what in the ERP system.

## Context

UltrERP has no User model yet. All operations use `DEFAULT_TENANT_ID` from `common/tenant.py` and `actor_id="system"` in audit logs. This story creates the foundational User model, CRUD operations, and password hashing. The invitation flow mentioned in the AC is simplified to a "create user with temporary password" flow — email invitation is deferred to a future story since there is no email service configured.

### Role Definitions (FR43, NFR11)

Per PRD and existing `DEFAULT_ROLE_SCOPES` in `app/mcp_auth.py`:

| Role | Scope | Description |
|------|-------|-------------|
| `owner` | Full access | System owner, can manage users and all data |
| `finance` | customers:read, invoices:read/write, payments:read/write | Finance clerk |
| `warehouse` | inventory:read/write, orders:read | Warehouse staff |
| `sales` | customers:read/write, invoices:read/create, orders:read/write | Sales representative |

### Password Requirements

- Hashed with `bcrypt` (industry standard, already proven pattern)
- `bcrypt` package must be added to `pyproject.toml` dependencies
- Minimum 8 characters enforced at schema validation level
- No plaintext password storage ever

### Architecture Decision

- New `backend/domains/users/` domain module
- User model in `common/models/user.py` (follows existing pattern)
- CRUD endpoints at `POST /api/v1/admin/users`, `GET /api/v1/admin/users`, `GET /api/v1/admin/users/{id}`, `PATCH /api/v1/admin/users/{id}`
- Admin-only endpoints — auth enforcement deferred to Story 11.3 (RBAC API). For now, endpoints are open but tagged `admin`.
- Audit log via `write_audit()` from Story 11.6
- Alembic migration for `users` table

### Existing Codebase Patterns

- All models live in `common/models/` and are registered in `common/models/__init__.py`
- All models have `tenant_id` (UUID, indexed) — NFR31
- Routes return Pydantic schemas, not raw ORM objects
- `FakeAsyncSession` with `queue_scalar`/`queue_rows` for service tests
- httpx `ASGITransport` + `AsyncClient` for API tests

## Acceptance Criteria

**AC1:** Create user with role
**Given** I provide email, display_name, password, and role
**When** I request `POST /api/v1/admin/users`
**Then** a user is created with the specified role
**And** the password is stored as a bcrypt hash (never plaintext)
**And** the user status is "active"
**And** an audit log entry is created with action="user.create"
**And** the response includes id, email, display_name, role, status, created_at (NOT password_hash)

**AC2:** Role validation
**Given** I create a user
**When** I specify a role not in ["owner", "finance", "warehouse", "sales"]
**Then** the request is rejected with 422

**AC3:** Duplicate email prevention
**Given** a user with email "alice@example.com" exists for the tenant
**When** I try to create another user with the same email
**Then** the request is rejected with 409 Conflict
**And** the response includes a clear error message

**AC4:** List users
**Given** users exist
**When** I request `GET /api/v1/admin/users`
**Then** the response includes a list of users with id, email, display_name, role, status, created_at
**And** passwords are NEVER included in the response
**And** only users for the current tenant are returned

**AC5:** Get single user
**Given** a user exists
**When** I request `GET /api/v1/admin/users/{id}`
**Then** the response includes the user details (without password)
**And** 404 if user not found

**AC6:** Update user
**Given** a user exists
**When** I request `PATCH /api/v1/admin/users/{id}` with partial update (role, display_name, status)
**Then** the user is updated
**And** an audit log entry is created with action="user.update" and before_state/after_state
**And** password can be reset via `password` field in the PATCH body (re-hashed)

**AC7:** Password validation
**Given** I create or update a user
**When** the password is shorter than 8 characters
**Then** the request is rejected with 422

**AC8:** All existing tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass
**And** new user CRUD tests are added (≥ 12 tests)

## Tasks / Subtasks

- [x] **Task 1: Add bcrypt dependency**
  - [x] Add `bcrypt>=4.2.0` to `backend/pyproject.toml` dependencies
  - [x] Run `cd backend && uv sync`

- [x] **Task 2: Create User model** (AC1, AC2)
  - [ ] Create `backend/common/models/user.py`:
    ```python
    """User model for authentication and RBAC."""
    from __future__ import annotations
    import uuid
    from datetime import datetime
    from sqlalchemy import DateTime, String, func
    from sqlalchemy.dialects.postgresql import UUID
    from sqlalchemy.orm import Mapped, mapped_column
    from common.database import Base

    class User(Base):
        __tablename__ = "users"
        __table_args__ = (
            # Unique email per tenant
            {"info": {"unique_constraints": [("tenant_id", "email")]}},
        )

        id: Mapped[uuid.UUID] = mapped_column(
            UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        )
        tenant_id: Mapped[uuid.UUID] = mapped_column(
            UUID(as_uuid=True), nullable=False, index=True,
        )
        email: Mapped[str] = mapped_column(String(255), nullable=False)
        password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
        display_name: Mapped[str] = mapped_column(String(200), nullable=False)
        role: Mapped[str] = mapped_column(String(20), nullable=False)
        status: Mapped[str] = mapped_column(
            String(20), nullable=False, default="active",
        )
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False,
        )
        updated_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), onupdate=func.now(),
        )
    ```
  - [x] Use `UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email")` in `__table_args__`
  - [x] Register in `common/models/__init__.py`

- [x] **Task 3: Alembic migration** (AC1)
  - [x] New migration: `oo555qq55r87_create_users_table.py`
  - [x] Depends on: `nn444pp44q76` (audit immutability from 11.6)
  - [x] Creates `users` table with all columns
  - [x] Adds unique constraint on (tenant_id, email)
  - [x] Adds index on email for login lookups

- [x] **Task 4: Password hashing utility** (AC1, AC7)
  - [ ] Create `backend/domains/users/auth.py`:
    ```python
    """Password hashing utilities using bcrypt."""
    import bcrypt

    def hash_password(plain: str) -> str:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

    def verify_password(plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    ```

- [x] **Task 5: User service** (AC1, AC3, AC6)
  - [ ] Create `backend/domains/users/service.py`:
    - `create_user(session, *, email, password, display_name, role)` → User
      - Hash password, create User, write audit log, handle duplicate IntegrityError → 409
    - `list_users(session)` → list[User]
      - Filter by `tenant_id = DEFAULT_TENANT_ID`
    - `get_user(session, user_id)` → User | None
      - Filter by tenant_id
    - `update_user(session, user_id, *, display_name, role, status, password)` → User
      - Partial update (only non-None fields)
      - Re-hash password if provided
      - Write audit log with before_state/after_state
    - `get_user_by_email(session, email)` → User | None
      - For login lookup (used in Story 11.3)

- [x] **Task 6: Schemas** (AC1, AC2, AC7)
  - [x] Create `backend/domains/users/schemas.py`:
    - `UserCreateRequest`: email (EmailStr), password (str, min_length=8), display_name (str), role (Literal["owner", "finance", "warehouse", "sales"])
    - `UserUpdateRequest`: display_name (str | None), role (Literal[...] | None), status (Literal["active", "disabled"] | None), password (str | None, min_length=8)
    - `UserResponse`: id, email, display_name, role, status, created_at, updated_at — NO password_hash. `model_config = ConfigDict(from_attributes=True)`
    - `UserListResponse`: items (list[UserResponse]), total (int)

- [x] **Task 7: Routes** (AC1-AC6)
  - [x] Create `backend/domains/users/routes.py`:
    - `POST /` — create user
    - `GET /` — list users
    - `GET /{user_id}` — get user
    - `PATCH /{user_id}` — update user
    - All return appropriate status codes (201, 200, 404, 409, 422)

- [x] **Task 8: Mount router** (AC1)
  - [ ] In `backend/app/main.py`:
    ```python
    from domains.users.routes import router as users_router
    # ...
    api_v1.include_router(users_router, prefix="/admin/users", tags=["users"])
    ```

- [x] **Task 9: Tests** (AC8)
  - [x] Create `backend/tests/test_users.py`:
    - `test_hash_password_returns_bcrypt_hash`
    - `test_verify_password_correct`
    - `test_verify_password_incorrect`
    - `test_create_user_api_success` — POST returns 201 with user data, no password_hash
    - `test_create_user_invalid_role_422`
    - `test_create_user_short_password_422`
    - `test_create_user_duplicate_email_409`
    - `test_list_users_api` — GET returns list
    - `test_get_user_api_200`
    - `test_get_user_api_404`
    - `test_update_user_api_role_change`
    - `test_update_user_api_password_reset`
    - `test_update_user_creates_audit_log`

## File Changes

### New Files
| File | Purpose |
|------|---------|
| `backend/common/models/user.py` | User ORM model |
| `backend/domains/users/__init__.py` | Module init |
| `backend/domains/users/auth.py` | Password hashing (bcrypt) |
| `backend/domains/users/service.py` | User CRUD service |
| `backend/domains/users/schemas.py` | Request/response models |
| `backend/domains/users/routes.py` | Admin user management endpoints |
| `backend/tests/test_users.py` | Tests |
| `migrations/versions/oo555qq55r87_create_users_table.py` | Migration |

### Modified Files
| File | Change |
|------|--------|
| `backend/pyproject.toml` | Add `bcrypt>=4.2.0` |
| `backend/common/models/__init__.py` | Import and export `User` |
| `backend/app/main.py` | Mount users router at `/api/v1/admin/users` |

## Dev Notes

- **Original 11.1 delivery intentionally deferred auth enforcement to Story 11.3.** In the current Epic 11 state, `/api/v1/admin/users` is explicitly owner-only.
- **Email validation**: Use Pydantic's `EmailStr` which requires the `email-validator` package. Check if it's already a transitive dep; if not, add it.
- **No invitation email flow.** The AC says "user receives an invitation" but there is no email service. Instead, the admin creates the user with a temporary password and communicates it out-of-band. The user changes it on first login (deferred to a later story).
- **Password hash MUST NEVER appear in any API response.** Ensure `UserResponse` excludes `password_hash`.
- The `get_user_by_email()` function is exposed for Story 11.3's login flow.
- TAB indentation. Ruff py312 rules E/F/I.

## Dev Agent Record

### Implementation Notes
- **bcrypt 5.0.0** installed (>= 4.2.0 specified), email-validator 2.3.0 already a transitive dep
- User model uses `UniqueConstraint("tenant_id", "email")` as specified
- Service sets `status="active"` and `created_at=datetime.now(UTC)` explicitly (not via SQLAlchemy defaults) for compatibility with FakeAsyncSession tests
- `create_user` flushes after add (for id generation), then writes audit log — both objects added to session
- `update_user` records before/after state diffs, masks password changes as `***changed***`
- `get_user_by_email` exposed for Story 11.3 login flow
- 2026-04-04 follow-up: `/api/v1/admin/users` now uses explicit owner-only RBAC, and focused API coverage asserts non-owner requests are rejected with 403
- 2026-04-04 follow-up: `user.create` and `user.update` audit entries now record the authenticated owner ID instead of the generic `system` actor
- 17 tests: 3 password hashing, 5 service-layer, 9 API-level (POST/GET/PATCH/validation/error codes)
- Full suite: 513 passed (496 prior + 17 new), 0 regressions
