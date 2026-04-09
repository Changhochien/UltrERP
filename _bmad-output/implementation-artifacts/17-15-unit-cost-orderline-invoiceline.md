# Story 17.15: Add unit_cost to OrderLine and InvoiceLine

Status: done

## Implementation Status

**Backend:** DONE

**Completed:**
- `backend/common/models/order_line.py` — added `unit_cost: Mapped[Numeric(20, 2) | None]` field after `unit_price`
- `backend/domains/invoices/models.py` — added `unit_cost: Mapped[Numeric(20, 2) | None]` field after `unit_price` in `InvoiceLine` class
- Migration file already existed: `migrations/versions/a1b2c3d4e5f6_add_unit_cost_order_line_invoice_line.py`

**Migration:** `a1b2c3d4e5f6_add_unit_cost_order_line_invoice_line` — adds `unit_cost` column (nullable) to both `order_lines` and `invoice_lines` tables

**Critical Issues:**
- `backend/common/models/order_line.py` missing `unit_cost` field
- `backend/domains/invoices/models.py` missing `unit_cost` field on InvoiceLine
- No alembic migration created
- Required for Story 17.14 (Gross Margin) to show actual margin data instead of "unavailable"

## Story

As a backend developer,
I want to add `unit_cost` to the OrderLine and InvoiceLine models,
so that gross profit can be calculated from revenue minus cost of goods sold.

## Acceptance Criteria

1. [AC-1] Given the existing OrderLine and InvoiceLine SQLAlchemy models, when a migration is created via `alembic revision -m "add unit_cost to OrderLine InvoiceLine"`, then both models have a `unit_cost: Mapped[Numeric(20, 2) | None]` field
2. [AC-2] The field is nullable (backwards-compatible with existing data)
3. [AC-3] Existing API endpoints for orders/invoices continue to work without modification
4. [AC-4] The gross_margin field can be added to the revenue aggregation endpoints

## Tasks / Subtasks

- [x] Task 1 (AC: 1)
  - [x] Subtask 1.1: Create alembic migration `add_unit_cost_to_order_line_invoice_line`
  - [x] Subtask 1.2: Add `unit_cost: Mapped[Numeric(20, 2) | None]` to `OrderLine` model at `backend/common/models/order_line.py`
  - [x] Subtask 1.3: Add `unit_cost: Mapped[Numeric(20, 2) | None]` to `InvoiceLine` model at `backend/domains/invoices/models.py`
- [x] Task 2 (AC: 2)
  - [x] Subtask 2.1: Ensure `nullable=True` on both model fields
- [x] Task 3 (AC: 3)
  - [x] Subtask 3.1: Verify existing orders/invoices API routes still return valid responses
- [x] Task 4 (AC: 4)
  - [x] Subtask 4.1: Ensure revenue aggregation endpoints (Stories 17.2, 17.5, 17.6) can be extended with gross_margin

## Dev Notes

- SQLAlchemy model style: use `Mapped[Numeric(20, 2) | None]` with `nullable=True`
- Import `Numeric` from `sqlalchemy`
- No default value needed (nullable field)
- OrderLine model at: `backend/common/models/order_line.py` (line 20-59)
- InvoiceLine model at: `backend/domains/invoices/models.py` (line 152-182)
- Existing field pattern to follow: `unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)`
- Alembic migration must add column to both `order_lines` and `invoice_lines` tables

### Project Structure Notes

- Model files: `backend/common/models/order_line.py`, `backend/domains/invoices/models.py`
- Migration: `alembic/versions/` directory
- No conflicts with existing structure

### References

- [Source: backend/common/models/order_line.py]
- [Source: backend/domains/invoices/models.py]
- [Source: Story 17.14 — Gross Margin KPI]
- [Source: Story 17.2 — KPI Summary Backend Endpoint]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List

- `backend/common/models/order_line.py` (update)
- `backend/domains/invoices/models.py` (update)
- `alembic/versions/<migration_file>.py` (new)
