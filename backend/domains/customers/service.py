"""Customer service layer — create, read, and update operations."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import DuplicateBusinessNumberError, ValidationError, VersionConflictError
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.customers.models import Customer
from domains.customers.schemas import CustomerCreate, CustomerListParams, CustomerUpdate
from domains.customers.validators import validate_taiwan_business_number

# Taiwan phone: mobile 09xx-xxx-xxx or landline (0X) xxxx-xxxx, with optional +886 prefix.
_TAIWAN_PHONE_RE = re.compile(
    r"^(?:"
    r"\+886[\s-]?9\d{2}[\s-]?\d{3}[\s-]?\d{3}"  # +886 mobile
    r"|09\d{2}[\s-]?\d{3}[\s-]?\d{3}"  # 09xx mobile
    r"|\(0\d{1,2}\)[\s-]?\d{4}[\s-]?\d{4}"  # (0X) landline
    r"|0\d{1,2}[\s-]?\d{4}[\s-]?\d{4}"  # 0X landline
    r")$"
)

# Conservative email: user@domain.tld (RFC-5322 subset)
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

_CREDIT_LIMIT_MAX = Decimal("9999999999.99")  # NUMERIC(12,2) max


def _validate_customer_fields(data: CustomerCreate) -> list[dict[str, str]]:
    """Return a list of field-level validation errors (may be empty)."""
    errors: list[dict[str, str]] = []

    # Business number
    ban_result = validate_taiwan_business_number(data.business_number)
    if not ban_result.valid:
        errors.append({"field": "business_number", "message": ban_result.error or "Invalid."})

    # Phone
    if not _TAIWAN_PHONE_RE.match(data.contact_phone):
        errors.append(
            {
                "field": "contact_phone",
                "message": "Phone must be a valid Taiwan phone number.",
            }
        )

    # Email
    if not _EMAIL_RE.match(data.contact_email):
        errors.append(
            {
                "field": "contact_email",
                "message": "Email must be a valid email address.",
            }
        )

    # Credit limit bounds
    try:
        limit = Decimal(str(data.credit_limit))
    except InvalidOperation:
        limit = data.credit_limit
    if limit < 0:
        errors.append({"field": "credit_limit", "message": "Credit limit must not be negative."})
    elif limit > _CREDIT_LIMIT_MAX:
        errors.append(
            {
                "field": "credit_limit",
                "message": f"Credit limit exceeds maximum ({_CREDIT_LIMIT_MAX}).",
            }
        )

    return errors


async def create_customer(
    session: AsyncSession,
    data: CustomerCreate,
    tenant_id: uuid.UUID | None = None,
) -> Customer:
    """Validate and persist a new customer record.

    Raises :class:`ValidationError` if any field is invalid.
    Raises :class:`DuplicateBusinessNumberError` if the BAN already exists.
    Returns the persisted :class:`Customer` with its assigned ID and version.
    """
    errors = _validate_customer_fields(data)
    if errors:
        raise ValidationError(errors)

    tid = tenant_id or DEFAULT_TENANT_ID

    # Normalize BAN to digits-only for storage
    normalized_ban = re.sub(r"\D", "", data.business_number)

    # Optimistic duplicate pre-check
    existing_stmt = select(Customer).where(
        Customer.normalized_business_number == normalized_ban,
        Customer.tenant_id == tid,
    )
    async with session.begin():
        await set_tenant(session, tid)
        existing_result = await session.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            raise DuplicateBusinessNumberError(
                existing_id=existing.id,
                existing_name=existing.company_name,
                normalized_business_number=normalized_ban,
            )

    customer = Customer(
        tenant_id=tid,
        company_name=data.company_name.strip(),
        normalized_business_number=normalized_ban,
        billing_address=data.billing_address.strip(),
        contact_name=data.contact_name.strip(),
        contact_phone=data.contact_phone.strip(),
        contact_email=data.contact_email.strip(),
        credit_limit=data.credit_limit,
    )

    try:
        async with session.begin():
            await set_tenant(session, tid)
            session.add(customer)
    except IntegrityError as ie:
        # Only handle the BAN uniqueness constraint; re-raise anything else.
        if ie.orig is None or "uq_customers_tenant_business_number" not in str(ie.orig):
            raise
        # Race condition fallback: another request inserted same BAN between
        # our pre-check and insert. Query for the conflicting record.
        async with session.begin():
            await set_tenant(session, tid)
            conflict_result = await session.execute(existing_stmt)
            conflict = conflict_result.scalar_one_or_none()
        if conflict is not None:
            raise DuplicateBusinessNumberError(
                existing_id=conflict.id,
                existing_name=conflict.company_name,
                normalized_business_number=normalized_ban,
            )
        raise  # Re-raise if we can't find the conflicting record

    await session.refresh(customer)
    return customer


async def list_customers(
    session: AsyncSession,
    params: CustomerListParams,
    tenant_id: uuid.UUID | None = None,
) -> tuple[list[Customer], int]:
    """Return a paginated list of customers with total count.

    Searches by partial business number or company name when ``params.q``
    is provided. Filters by status when ``params.status`` is provided.
    """
    tid = tenant_id or DEFAULT_TENANT_ID

    base = select(Customer).where(Customer.tenant_id == tid)

    if params.q:
        # Escape LIKE metacharacters to prevent wildcard injection
        escaped_q = params.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like_pattern = f"%{escaped_q}%"
        # Normalize: strip non-digits for potential BAN search
        normalized_q = re.sub(r"\D", "", params.q)
        if normalized_q:
            # Search both BAN (partial) and company name (partial)
            base = base.where(
                Customer.normalized_business_number.contains(normalized_q)
                | Customer.company_name.ilike(like_pattern, escape="\\")
            )
        else:
            base = base.where(Customer.company_name.ilike(like_pattern, escape="\\"))

    if params.status:
        base = base.where(Customer.status == params.status)

    # Count
    count_stmt = select(func.count()).select_from(base.subquery())

    # Page
    offset = (params.page - 1) * params.page_size
    items_stmt = (
        base.order_by(Customer.company_name.asc(), Customer.id.asc())
        .offset(offset)
        .limit(params.page_size)
    )

    async with session.begin():
        await set_tenant(session, tid)
        total_result = await session.execute(count_stmt)
        total_count = total_result.scalar() or 0
        result = await session.execute(items_stmt)
        items = list(result.scalars().all())

    return items, total_count


async def get_customer(
    session: AsyncSession,
    customer_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> Customer | None:
    """Retrieve a single customer by ID."""
    tid = tenant_id or DEFAULT_TENANT_ID
    stmt = select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tid)
    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def lookup_customer_by_ban(
    session: AsyncSession,
    business_number: str,
    tenant_id: uuid.UUID | None = None,
) -> Customer | None:
    """Exact-match lookup by normalized business number."""
    tid = tenant_id or DEFAULT_TENANT_ID
    normalized = re.sub(r"\D", "", business_number)
    stmt = select(Customer).where(
        Customer.normalized_business_number == normalized,
        Customer.tenant_id == tid,
    )
    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


def _validate_update_fields(data: CustomerUpdate) -> list[dict[str, str]]:
    """Validate only the fields that were actually provided in the update."""
    errors: list[dict[str, str]] = []
    fields = data.model_fields_set - {"version"}

    if "business_number" in fields and data.business_number is not None:
        ban_result = validate_taiwan_business_number(data.business_number)
        if not ban_result.valid:
            errors.append({"field": "business_number", "message": ban_result.error or "Invalid."})

    if "contact_phone" in fields and data.contact_phone is not None:
        if not _TAIWAN_PHONE_RE.match(data.contact_phone):
            errors.append(
                {
                    "field": "contact_phone",
                    "message": "Phone must be a valid Taiwan phone number.",
                }
            )

    if "contact_email" in fields and data.contact_email is not None:
        if not _EMAIL_RE.match(data.contact_email):
            errors.append(
                {
                    "field": "contact_email",
                    "message": "Email must be a valid email address.",
                }
            )

    if "credit_limit" in fields and data.credit_limit is not None:
        try:
            limit = Decimal(str(data.credit_limit))
        except InvalidOperation:
            limit = data.credit_limit
        if limit < 0:
            errors.append(
                {
                    "field": "credit_limit",
                    "message": "Credit limit must not be negative.",
                }
            )
        elif limit > _CREDIT_LIMIT_MAX:
            errors.append(
                {
                    "field": "credit_limit",
                    "message": f"Credit limit exceeds maximum ({_CREDIT_LIMIT_MAX}).",
                }
            )

    return errors


async def update_customer(
    session: AsyncSession,
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    tenant_id: uuid.UUID | None = None,
) -> Customer | None:
    """Update an existing customer record with optimistic locking.

    Raises :class:`ValidationError` if any field is invalid.
    Raises :class:`VersionConflictError` if the version doesn't match.
    Raises :class:`DuplicateBusinessNumberError` if the BAN already exists.
    Returns the updated :class:`Customer`, or ``None`` if not found.
    """
    errors = _validate_update_fields(data)
    if errors:
        raise ValidationError(errors)

    tid = tenant_id or DEFAULT_TENANT_ID
    fields = data.model_fields_set - {"version"}

    async with session.begin():
        await set_tenant(session, tid)
        stmt = select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tid)
        result = await session.execute(stmt)
        customer = result.scalar_one_or_none()

        if customer is None:
            return None

        # Optimistic locking
        if customer.version != data.version:
            raise VersionConflictError(expected=data.version, actual=customer.version)

        # Check for BAN change and run duplicate detection
        if "business_number" in fields and data.business_number is not None:
            new_ban = re.sub(r"\D", "", data.business_number)
            if new_ban != customer.normalized_business_number:
                dup_stmt = select(Customer).where(
                    Customer.normalized_business_number == new_ban,
                    Customer.tenant_id == tid,
                    Customer.id != customer_id,
                )
                dup_result = await session.execute(dup_stmt)
                existing = dup_result.scalar_one_or_none()
                if existing is not None:
                    raise DuplicateBusinessNumberError(
                        existing_id=existing.id,
                        existing_name=existing.company_name,
                        normalized_business_number=new_ban,
                    )
                customer.normalized_business_number = new_ban

        # Apply field changes
        if "company_name" in fields and data.company_name is not None:
            customer.company_name = data.company_name.strip()
        if "billing_address" in fields and data.billing_address is not None:
            customer.billing_address = data.billing_address.strip()
        if "contact_name" in fields and data.contact_name is not None:
            customer.contact_name = data.contact_name.strip()
        if "contact_phone" in fields and data.contact_phone is not None:
            customer.contact_phone = data.contact_phone.strip()
        if "contact_email" in fields and data.contact_email is not None:
            customer.contact_email = data.contact_email.strip()
        if "credit_limit" in fields and data.credit_limit is not None:
            customer.credit_limit = data.credit_limit

        customer.version += 1
        customer.updated_at = datetime.now(tz=UTC)

    await session.refresh(customer)
    return customer
