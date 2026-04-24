"""Inventory domain service — warehouse CRUD, stock transfers."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import and_, asc, case, desc, distinct, func, literal, or_, select, text, update
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from common.errors import (
    DuplicateCategoryNameError,
    DuplicateProductCodeError,
    DuplicateUnitCodeError,
    ValidationError,
)
from common.events import StockChangedEvent, emit
from common.models.audit_log import AuditLog
from common.models.category import Category, CategoryTranslation
from common.models.inventory_stock import InventoryStock
from common.models.physical_count_line import PhysicalCountLine
from common.models.physical_count_session import (
    PhysicalCountSession,
    PhysicalCountSessionStatus,
)
from common.models.product import Product
from common.models.product_supplier import ProductSupplier
from common.models.reorder_alert import AlertStatus, ReorderAlert
from common.models.stock_adjustment import ReasonCode, StockAdjustment
from common.models.stock_transfer import StockTransferHistory
from common.models.supplier import Supplier
from common.models.supplier_invoice import SupplierInvoice, SupplierInvoiceLine
from common.models.supplier_order import SupplierOrder, SupplierOrderLine, SupplierOrderStatus
from common.models.unit_of_measure import UnitOfMeasure
from common.models.warehouse import Warehouse
from common.time import today, utc_now

if TYPE_CHECKING:
    from domains.inventory.schemas import (
        CategoryCreate,
        CategoryUpdate,
        ProductCreate,
        ProductUpdate,
        SupplierCreate,
        SupplierUpdate,
        UnitOfMeasureCreate,
        UnitOfMeasureUpdate,
    )


class InsufficientStockError(Exception):
    """Raised when a transfer exceeds available stock."""

    def __init__(self, available: int = 0, requested: int = 0) -> None:
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient stock: available={available}, requested={requested}",
        )


class TransferValidationError(Exception):
    """Raised for invalid transfer parameters."""


class PhysicalCountNotFoundError(Exception):
    """Raised when a physical count session or line does not exist."""


class PhysicalCountConflictError(Exception):
    """Raised when a physical count operation conflicts with live stock."""


class PhysicalCountStateError(Exception):
    """Raised when a physical count action is invalid for the current state."""


_PLANNING_QUANTITY_QUANT = Decimal("0.001")
_PLANNING_INDEX_QUANT = Decimal("0.001")
_STANDARD_COST_QUANT = Decimal("0.0001")
_VALUATION_AMOUNT_QUANT = Decimal("0.0001")
_ZERO_QUANTITY = Decimal("0.000")
DEFAULT_UNIT_OF_MEASURE_SEEDS: tuple[tuple[str, str, int], ...] = (
    ("pcs", "Pieces", 0),
    ("kg", "Kilogram", 3),
    ("g", "Gram", 0),
    ("box", "Box", 0),
    ("carton", "Carton", 0),
    ("pallet", "Pallet", 0),
    ("liter", "Liter", 3),
    ("ml", "Milliliter", 0),
    ("meter", "Meter", 3),
    ("cm", "Centimeter", 0),
)
SUPPORTED_CATEGORY_LOCALES: tuple[str, ...] = ("en", "zh-Hant")
DEFAULT_CATEGORY_LOCALE = "en"
ZH_HANT_LOCALE = "zh-Hant"


def _shift_months(value: date, months: int) -> date:
    month_index = (value.year * 12 + value.month - 1) + months
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _iter_month_starts(start_month: date, end_month: date) -> list[date]:
    month_starts: list[date] = []
    cursor = start_month
    while cursor <= end_month:
        month_starts.append(cursor)
        cursor = _shift_months(cursor, 1)
    return month_starts


def _format_month(month_start: date) -> str:
    return month_start.strftime("%Y-%m")


def _quantize_quantity(value: Decimal | int | float | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(_PLANNING_QUANTITY_QUANT, rounding=ROUND_HALF_UP)


def _quantize_index(value: Decimal) -> Decimal:
    return value.quantize(_PLANNING_INDEX_QUANT, rounding=ROUND_HALF_UP)


def _quantize_valuation_amount(value: Decimal | int | float | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(_VALUATION_AMOUNT_QUANT, rounding=ROUND_HALF_UP)


def _normalize_standard_cost(value: object | None) -> Decimal | None:
    if value is None or value == "":
        return None

    standard_cost = value if isinstance(value, Decimal) else Decimal(str(value))
    if standard_cost < 0:
        raise ValidationError(
            [
                {
                    "loc": ("standard_cost",),
                    "msg": "standard_cost must be greater than or equal to 0",
                    "type": "value_error",
                }
            ]
        )
    return standard_cost.quantize(_STANDARD_COST_QUANT, rounding=ROUND_HALF_UP)


def _normalize_unit_code(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValidationError(
            [{"loc": ("code",), "msg": "code cannot be blank", "type": "value_error"}]
        )
    return normalized


def _normalize_unit_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(
            [{"loc": ("name",), "msg": "name cannot be blank", "type": "value_error"}]
        )
    return normalized


async def _find_unit_by_code(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    code: str,
    *,
    exclude_unit_id: uuid.UUID | None = None,
) -> UnitOfMeasure | None:
    stmt = select(UnitOfMeasure).where(
        UnitOfMeasure.tenant_id == tenant_id,
        UnitOfMeasure.code == code,
    )
    if exclude_unit_id is not None:
        stmt = stmt.where(UnitOfMeasure.id != exclude_unit_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ── Warehouse queries ──────────────────────────────────────────


async def list_warehouses(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    active_only: bool = True,
) -> list[Warehouse]:
    stmt = select(Warehouse).where(Warehouse.tenant_id == tenant_id).order_by(Warehouse.name)
    if active_only:
        stmt = stmt.where(Warehouse.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_warehouse(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
) -> Warehouse | None:
    stmt = select(Warehouse).where(
        Warehouse.id == warehouse_id,
        Warehouse.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_warehouse(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str,
    code: str,
    location: str | None = None,
    address: str | None = None,
    contact_email: str | None = None,
) -> Warehouse:
    warehouse = Warehouse(
        tenant_id=tenant_id,
        name=name,
        code=code,
        location=location,
        address=address,
        contact_email=contact_email,
    )
    session.add(warehouse)
    await session.flush()
    return warehouse


def _normalize_optional_product_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_category_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValidationError(
            [{"loc": ("name",), "msg": "name cannot be blank", "type": "value_error"}]
        )
    return normalized


def _normalize_category_locale(locale: str | None) -> str | None:
    if locale is None:
        return None

    normalized = locale.strip().replace("_", "-")
    if not normalized:
        return None

    lower = normalized.lower()
    if lower.startswith("zh-hant"):
        return ZH_HANT_LOCALE
    if lower.startswith("en"):
        return DEFAULT_CATEGORY_LOCALE
    if normalized in SUPPORTED_CATEGORY_LOCALES:
        return normalized
    return None


def resolve_category_locale(
    locale: str | None,
    accept_language: str | None = None,
) -> str:
    normalized = _normalize_category_locale(locale)
    if normalized is not None:
        return normalized

    if accept_language:
        for candidate in accept_language.split(","):
            language_tag = candidate.split(";", 1)[0].strip()
            normalized = _normalize_category_locale(language_tag)
            if normalized is not None:
                return normalized

    return DEFAULT_CATEGORY_LOCALE


def _normalize_category_translations(
    translations: dict[str, str] | None,
) -> dict[str, str]:
    normalized: dict[str, str] = {}
    if not translations:
        return normalized

    errors: list[dict[str, str | tuple[str, ...]]] = []
    for locale, value in translations.items():
        normalized_locale = _normalize_category_locale(locale)
        if normalized_locale is None:
            errors.append(
                {
                    "loc": ("translations", locale),
                    "msg": "unsupported locale",
                    "type": "value_error",
                }
            )
            continue
        try:
            normalized[normalized_locale] = _normalize_category_name(value)
        except ValidationError:
            errors.append(
                {
                    "loc": ("translations", normalized_locale),
                    "msg": "name cannot be blank",
                    "type": "value_error",
                }
            )

    if errors:
        raise ValidationError(errors)

    return normalized


def _category_translation_map(category: Category) -> dict[str, str]:
    translations = {translation.locale: translation.name for translation in category.translations}
    if DEFAULT_CATEGORY_LOCALE not in translations and category.name:
        translations[DEFAULT_CATEGORY_LOCALE] = category.name
    return translations


def _localized_category_name(
    category: Category | None,
    locale: str,
    *,
    fallback_name: str | None = None,
) -> str | None:
    if category is None:
        return fallback_name

    translations = _category_translation_map(category)
    return (
        translations.get(locale)
        or translations.get(DEFAULT_CATEGORY_LOCALE)
        or category.name
        or fallback_name
    )


def serialize_category(category: Category, locale: str) -> dict[str, object]:
    translations = _category_translation_map(category)
    return {
        "id": category.id,
        "tenant_id": category.tenant_id,
        "name": translations.get(locale) or translations.get(DEFAULT_CATEGORY_LOCALE) or category.name,
        "name_en": translations.get(DEFAULT_CATEGORY_LOCALE) or category.name,
        "name_zh_hant": translations.get(ZH_HANT_LOCALE),
        "translations": translations,
        "is_active": category.is_active,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
    }


def _normalize_product_payload(
    data: object,
) -> tuple[str, str, uuid.UUID | None, str | None, str, Decimal | None]:
    code = str(getattr(data, "code", "")).strip()
    name = str(getattr(data, "name", "")).strip()
    unit = str(getattr(data, "unit", "")).strip()
    category_id = getattr(data, "category_id", None)
    description = _normalize_optional_product_text(getattr(data, "description", None))
    standard_cost = _normalize_standard_cost(getattr(data, "standard_cost", None))

    errors: list[dict[str, str | tuple[str, ...]]] = []
    if not code:
        errors.append({"loc": ("code",), "msg": "code cannot be blank", "type": "value_error"})
    if not name:
        errors.append({"loc": ("name",), "msg": "name cannot be blank", "type": "value_error"})
    if not unit:
        errors.append({"loc": ("unit",), "msg": "unit cannot be blank", "type": "value_error"})
    if errors:
        raise ValidationError(errors)

    return code, name, category_id, description, unit, standard_cost


def _normalize_supplier_payload(
    data: object,
) -> tuple[str, str | None, str | None, str | None, int | None]:
    name = str(getattr(data, "name", "")).strip()
    contact_email = _normalize_optional_product_text(getattr(data, "contact_email", None))
    phone = _normalize_optional_product_text(getattr(data, "phone", None))
    address = _normalize_optional_product_text(getattr(data, "address", None))
    lead_time_value = getattr(data, "default_lead_time_days", None)
    default_lead_time_days = int(lead_time_value) if lead_time_value is not None else None

    errors: list[dict[str, str | tuple[str, ...]]] = []
    if not name:
        errors.append({"loc": ("name",), "msg": "name cannot be blank", "type": "value_error"})
    if default_lead_time_days is not None and default_lead_time_days < 0:
        errors.append(
            {
                "loc": ("default_lead_time_days",),
                "msg": "default_lead_time_days must be greater than or equal to 0",
                "type": "value_error",
            }
        )
    if errors:
        raise ValidationError(errors)

    return name, contact_email, phone, address, default_lead_time_days


async def _find_product_by_code(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    code: str,
    *,
    exclude_product_id: uuid.UUID | None = None,
) -> Product | None:
    stmt = select(Product).where(
        Product.tenant_id == tenant_id,
        func.lower(Product.code) == code.lower(),
    )
    if exclude_product_id is not None:
        stmt = stmt.where(Product.id != exclude_product_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _find_category_by_name(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
    *,
    exclude_category_id: uuid.UUID | None = None,
) -> Category | None:
    stmt = select(Category).where(
        Category.tenant_id == tenant_id,
        func.lower(Category.name) == name.lower(),
    )
    if exclude_category_id is not None:
        stmt = stmt.where(Category.id != exclude_category_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _find_category_by_id(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category | None:
    stmt = (
        select(Category)
        .options(selectinload(Category.translations))
        .where(
            Category.id == category_id,
            Category.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _resolve_product_category(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID | None,
) -> Category | None:
    if category_id is None:
        return None

    category = await _find_category_by_id(session, tenant_id, category_id)
    if category is None:
        raise ValidationError(
            [
                {
                    "loc": ("category_id",),
                    "msg": "category_id does not reference an existing category",
                    "type": "value_error",
                }
            ]
        )
    return category


# ── Category queries ──────────────────────────────────────────


async def create_category(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: "CategoryCreate",
    *,
    locale: str = DEFAULT_CATEGORY_LOCALE,
) -> Category:
    requested_locale = resolve_category_locale(locale)
    translations = _normalize_category_translations(data.translations)
    translations[requested_locale] = _normalize_category_name(data.name)
    fallback_name = translations.get(DEFAULT_CATEGORY_LOCALE) or translations[requested_locale]

    existing = await _find_category_by_name(session, tenant_id, fallback_name)
    if existing is not None:
        raise DuplicateCategoryNameError(existing_id=existing.id, existing_name=existing.name)

    category = Category(
        tenant_id=tenant_id,
        name=fallback_name,
        is_active=True,
        translations=[
            CategoryTranslation(locale=translation_locale, name=translation_name)
            for translation_locale, translation_name in translations.items()
        ],
    )
    try:
        session.add(category)
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await _find_category_by_name(session, tenant_id, fallback_name)
        if existing is not None:
            raise DuplicateCategoryNameError(existing_id=existing.id, existing_name=existing.name)
        raise

    return category


async def list_categories(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    locale: str = DEFAULT_CATEGORY_LOCALE,
    q: str = "",
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Category], int]:
    where_conditions = [Category.tenant_id == tenant_id]
    if active_only:
        where_conditions.append(Category.is_active.is_(True))

    stmt = (
        select(Category)
        .options(selectinload(Category.translations))
        .where(*where_conditions)
        .order_by(Category.name)
    )
    result = await session.execute(stmt)
    categories = list(result.scalars().all())

    stripped = q.strip().lower()
    if stripped:
        categories = [
            category
            for category in categories
            if stripped in (category.name or "").lower()
            or any(stripped in translation.name.lower() for translation in category.translations)
        ]

    resolved_locale = resolve_category_locale(locale)
    categories.sort(
        key=lambda category: (
            _localized_category_name(category, resolved_locale) or category.name or ""
        ).lower()
    )
    total = len(categories)
    return categories[offset : offset + limit], total


async def get_category(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category | None:
    return await _find_category_by_id(session, tenant_id, category_id)


async def update_category(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID,
    data: "CategoryUpdate",
    *,
    locale: str = DEFAULT_CATEGORY_LOCALE,
) -> Category | None:
    category = await get_category(session, tenant_id, category_id)
    if category is None:
        return None

    requested_locale = resolve_category_locale(locale)
    old_fallback_name = category.name
    translations = _category_translation_map(category)
    if data.translations is not None:
        translations.update(_normalize_category_translations(data.translations))
    if data.name is not None:
        translations[requested_locale] = _normalize_category_name(data.name)

    next_fallback_name = (
        translations.get(DEFAULT_CATEGORY_LOCALE)
        or old_fallback_name
        or next(iter(translations.values()), None)
    )
    if next_fallback_name is None:
        raise ValidationError(
            [{"loc": ("name",), "msg": "name cannot be blank", "type": "value_error"}]
        )

    if next_fallback_name != old_fallback_name:
        existing = await _find_category_by_name(
            session,
            tenant_id,
            next_fallback_name,
            exclude_category_id=category.id,
        )
        if existing is not None:
            raise DuplicateCategoryNameError(existing_id=existing.id, existing_name=existing.name)

    category.name = next_fallback_name
    existing_translations = {translation.locale: translation for translation in category.translations}
    for translation_locale, translation_name in translations.items():
        translation = existing_translations.get(translation_locale)
        if translation is None:
            category.translations.append(
                CategoryTranslation(locale=translation_locale, name=translation_name)
            )
        else:
            translation.name = translation_name

    try:
        if next_fallback_name != old_fallback_name:
            await session.execute(
                update(Product)
                .where(
                    Product.tenant_id == tenant_id,
                    Product.category_id == category.id,
                )
                .values(category=next_fallback_name)
            )
        await session.flush()
    except IntegrityError:
        await session.rollback()
        if next_fallback_name != old_fallback_name:
            existing = await _find_category_by_name(
                session,
                tenant_id,
                next_fallback_name,
                exclude_category_id=category_id,
            )
            if existing is not None:
                raise DuplicateCategoryNameError(existing_id=existing.id, existing_name=existing.name)
        raise

    return category


async def set_category_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID,
    *,
    is_active: bool,
) -> Category | None:
    category = await get_category(session, tenant_id, category_id)
    if category is None:
        return None

    category.is_active = is_active
    await session.flush()
    return category


async def seed_default_units(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[UnitOfMeasure]:
    stmt = select(UnitOfMeasure).where(UnitOfMeasure.tenant_id == tenant_id)
    result = await session.execute(stmt)
    existing_units = list(result.scalars().all())
    existing_codes = {unit.code for unit in existing_units}

    created_units: list[UnitOfMeasure] = []
    for code, name, decimal_places in DEFAULT_UNIT_OF_MEASURE_SEEDS:
        if code in existing_codes:
            continue
        created_units.append(
            UnitOfMeasure(
                tenant_id=tenant_id,
                code=code,
                name=name,
                decimal_places=decimal_places,
                is_active=True,
            )
        )

    if created_units:
        session.add_all(created_units)
        await session.flush()

    return created_units


async def create_unit(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: "UnitOfMeasureCreate",
) -> UnitOfMeasure:
    code = _normalize_unit_code(data.code)
    name = _normalize_unit_name(data.name)

    existing = await _find_unit_by_code(session, tenant_id, code)
    if existing is not None:
        raise DuplicateUnitCodeError(existing_id=existing.id, existing_code=existing.code)

    unit = UnitOfMeasure(
        tenant_id=tenant_id,
        code=code,
        name=name,
        decimal_places=data.decimal_places,
        is_active=True,
    )
    try:
        session.add(unit)
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await _find_unit_by_code(session, tenant_id, code)
        if existing is not None:
            raise DuplicateUnitCodeError(existing_id=existing.id, existing_code=existing.code)
        raise

    return unit


async def list_units(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    q: str = "",
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
    seed_defaults: bool = True,
) -> tuple[list[UnitOfMeasure], int]:
    if seed_defaults:
        await seed_default_units(session, tenant_id)

    where_conditions = [UnitOfMeasure.tenant_id == tenant_id]
    if active_only:
        where_conditions.append(UnitOfMeasure.is_active.is_(True))

    stripped = q.strip().lower()
    if stripped:
        q_like = stripped.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where_conditions.append(
            or_(
                UnitOfMeasure.code.ilike(f"%{q_like}%", escape="\\"),
                UnitOfMeasure.name.ilike(f"%{q_like}%", escape="\\"),
            )
        )

    count_stmt = select(func.count(UnitOfMeasure.id)).where(*where_conditions)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = (
        select(UnitOfMeasure)
        .where(*where_conditions)
        .order_by(UnitOfMeasure.code)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    units = result.scalars().all()
    return list(units), total


async def get_unit(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unit_id: uuid.UUID,
) -> UnitOfMeasure | None:
    stmt = select(UnitOfMeasure).where(
        UnitOfMeasure.id == unit_id,
        UnitOfMeasure.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_unit(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unit_id: uuid.UUID,
    data: "UnitOfMeasureUpdate",
) -> UnitOfMeasure | None:
    unit = await get_unit(session, tenant_id, unit_id)
    if unit is None:
        return None

    code = _normalize_unit_code(data.code)
    name = _normalize_unit_name(data.name)
    existing = await _find_unit_by_code(
        session,
        tenant_id,
        code,
        exclude_unit_id=unit.id,
    )
    if existing is not None:
        raise DuplicateUnitCodeError(existing_id=existing.id, existing_code=existing.code)

    unit.code = code
    unit.name = name
    unit.decimal_places = data.decimal_places
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await _find_unit_by_code(
            session,
            tenant_id,
            code,
            exclude_unit_id=unit_id,
        )
        if existing is not None:
            raise DuplicateUnitCodeError(existing_id=existing.id, existing_code=existing.code)
        raise

    return unit


async def set_unit_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unit_id: uuid.UUID,
    *,
    is_active: bool,
) -> UnitOfMeasure | None:
    unit = await get_unit(session, tenant_id, unit_id)
    if unit is None:
        return None

    unit.is_active = is_active
    await session.flush()
    return unit


# ── Product creation ───────────────────────────────────────────


async def create_product(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: "ProductCreate",
) -> Product:
    """Create a new product for a tenant."""
    code, name, category_id, description, unit, standard_cost = _normalize_product_payload(data)
    category = await _resolve_product_category(session, tenant_id, category_id)

    # Check for duplicate code within tenant
    row = await _find_product_by_code(session, tenant_id, code)
    if row is not None:
        raise DuplicateProductCodeError(existing_id=row.id, existing_code=row.code)

    product = Product(
        tenant_id=tenant_id,
        code=code,
        name=name,
        category=category.name if category is not None else None,
        category_id=category.id if category is not None else None,
        description=description,
        unit=unit,
        standard_cost=standard_cost,
        status="active",
        search_vector=func.to_tsvector("simple", name + " " + code),
    )
    try:
        session.add(product)
        await session.flush()
    except IntegrityError:
        await session.rollback()
        # Race condition: another request inserted the same code between our
        # pre-check and insert. Query for the conflicting product and raise
        # DuplicateProductCodeError so the route returns a proper 409.
        existing = await _find_product_by_code(session, tenant_id, code)
        if existing is not None:
            raise DuplicateProductCodeError(existing_id=existing.id, existing_code=existing.code)
        raise
    return product


async def update_product(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    data: "ProductUpdate",
) -> Product | None:
    """Update an existing product for a tenant."""
    code, name, category_id, description, unit, standard_cost = _normalize_product_payload(data)

    stmt = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if product is None:
        return None

    existing = await _find_product_by_code(
        session,
        tenant_id,
        code,
        exclude_product_id=product.id,
    )
    if existing is not None:
        raise DuplicateProductCodeError(existing_id=existing.id, existing_code=existing.code)

    category = await _resolve_product_category(session, tenant_id, category_id)
    code_or_name_changed = product.code != code or product.name != name
    product.code = code
    product.name = name
    product.category = category.name if category is not None else None
    product.category_id = category.id if category is not None else None
    product.description = description
    product.unit = unit
    product.standard_cost = standard_cost
    if code_or_name_changed:
        product.search_vector = func.to_tsvector("simple", name + " " + code)

    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await _find_product_by_code(
            session,
            tenant_id,
            code,
            exclude_product_id=product_id,
        )
        if existing is not None:
            raise DuplicateProductCodeError(existing_id=existing.id, existing_code=existing.code)
        raise

    return product


async def set_product_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    status: str,
) -> Product | None:
    """Set the active/inactive lifecycle status for an existing product."""
    stmt = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if product is None:
        return None

    product.status = status
    await session.flush()
    return product

# ── Stock transfer ─────────────────────────────────────────────


async def transfer_stock(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    from_warehouse_id: uuid.UUID,
    to_warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    quantity: int,
    actor_id: str,
    notes: str | None = None,
) -> StockTransferHistory:
    """Execute an atomic inter-warehouse stock transfer."""
    if from_warehouse_id == to_warehouse_id:
        raise TransferValidationError(
            "Source and destination warehouse must be different",
        )
    if quantity <= 0:
        raise TransferValidationError("Quantity must be positive")

    # 1. Lock source inventory row (FOR UPDATE)
    source_stmt = (
        select(InventoryStock)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
            InventoryStock.warehouse_id == from_warehouse_id,
        )
        .with_for_update()
    )
    source_result = await session.execute(source_stmt)
    source_stock = source_result.scalar_one_or_none()

    if source_stock is None:
        raise InsufficientStockError(available=0, requested=quantity)
    if source_stock.quantity < quantity:
        raise InsufficientStockError(
            available=source_stock.quantity,
            requested=quantity,
        )

    # 2. Get or create target inventory row
    target_stmt = (
        select(InventoryStock)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
            InventoryStock.warehouse_id == to_warehouse_id,
        )
        .with_for_update()
    )
    target_result = await session.execute(target_stmt)
    target_stock = target_result.scalar_one_or_none()

    if target_stock is None:
        target_stock = InventoryStock(
            tenant_id=tenant_id,
            product_id=product_id,
            warehouse_id=to_warehouse_id,
            quantity=0,
            reorder_point=0,
        )
        session.add(target_stock)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            target_result = await session.execute(target_stmt)
            target_stock = target_result.scalar_one()

    # 3. Update quantities
    before_source = source_stock.quantity
    before_target = target_stock.quantity
    source_stock.quantity -= quantity
    target_stock.quantity += quantity

    # 4. Record transfer history
    transfer = StockTransferHistory(
        tenant_id=tenant_id,
        product_id=product_id,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        quantity=quantity,
        actor_id=actor_id,
        notes=notes,
    )
    session.add(transfer)
    await session.flush()

    # 5. Create adjustment records (outbound + inbound)
    adj_out = StockAdjustment(
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=from_warehouse_id,
        quantity_change=-quantity,
        reason_code=ReasonCode.TRANSFER_OUT,
        actor_id=actor_id,
        transfer_id=transfer.id,
        notes=notes,
    )
    adj_in = StockAdjustment(
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=to_warehouse_id,
        quantity_change=quantity,
        reason_code=ReasonCode.TRANSFER_IN,
        actor_id=actor_id,
        transfer_id=transfer.id,
        notes=notes,
    )
    session.add_all([adj_out, adj_in])

    # 6. Audit log
    audit = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="stock_transfer",
        entity_type="stock_transfer_history",
        entity_id=str(transfer.id),
        before_state={
            "source_quantity": before_source,
            "target_quantity": before_target,
        },
        after_state={
            "source_quantity": source_stock.quantity,
            "target_quantity": target_stock.quantity,
        },
        correlation_id=str(transfer.id),
        notes=notes,
    )
    session.add(audit)

    # 7. Emit stock changed events for both warehouses
    await emit(StockChangedEvent(
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=from_warehouse_id,
        before_quantity=before_source,
        after_quantity=source_stock.quantity,
        reorder_point=source_stock.reorder_point,
        actor_id=actor_id,
    ), session)
    await emit(StockChangedEvent(
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=to_warehouse_id,
        before_quantity=before_target,
        after_quantity=target_stock.quantity,
        reorder_point=target_stock.reorder_point,
        actor_id=actor_id,
    ), session)

    await session.flush()
    return transfer


# ── Physical count sessions ───────────────────────────────────


def _physical_count_status_value(status: PhysicalCountSessionStatus | str) -> str:
    return status.value if isinstance(status, PhysicalCountSessionStatus) else str(status)


def _serialize_physical_count_line(line: PhysicalCountLine) -> dict[str, object | None]:
    product = getattr(line, "product", None)
    return {
        "id": line.id,
        "product_id": line.product_id,
        "product_code": getattr(product, "code", None),
        "product_name": getattr(product, "name", None),
        "system_qty_snapshot": line.system_qty_snapshot,
        "counted_qty": line.counted_qty,
        "variance_qty": line.variance_qty,
        "notes": line.notes,
        "created_at": line.created_at,
        "updated_at": line.updated_at,
    }


async def list_transfers(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    source_warehouse = aliased(Warehouse)
    destination_warehouse = aliased(Warehouse)

    where_conditions = [StockTransferHistory.tenant_id == tenant_id]
    if product_id is not None:
        where_conditions.append(StockTransferHistory.product_id == product_id)
    if warehouse_id is not None:
        where_conditions.append(
            or_(
                StockTransferHistory.from_warehouse_id == warehouse_id,
                StockTransferHistory.to_warehouse_id == warehouse_id,
            )
        )

    count_stmt = select(func.count(StockTransferHistory.id)).where(*where_conditions)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = (
        select(
            StockTransferHistory.id.label("id"),
            StockTransferHistory.tenant_id.label("tenant_id"),
            StockTransferHistory.product_id.label("product_id"),
            Product.code.label("product_code"),
            Product.name.label("product_name"),
            StockTransferHistory.from_warehouse_id.label("from_warehouse_id"),
            source_warehouse.name.label("from_warehouse_name"),
            source_warehouse.code.label("from_warehouse_code"),
            StockTransferHistory.to_warehouse_id.label("to_warehouse_id"),
            destination_warehouse.name.label("to_warehouse_name"),
            destination_warehouse.code.label("to_warehouse_code"),
            StockTransferHistory.quantity.label("quantity"),
            StockTransferHistory.actor_id.label("actor_id"),
            StockTransferHistory.notes.label("notes"),
            StockTransferHistory.created_at.label("created_at"),
        )
        .join(Product, Product.id == StockTransferHistory.product_id)
        .join(source_warehouse, source_warehouse.id == StockTransferHistory.from_warehouse_id)
        .join(
            destination_warehouse,
            destination_warehouse.id == StockTransferHistory.to_warehouse_id,
        )
        .where(*where_conditions)
        .order_by(desc(StockTransferHistory.created_at), desc(StockTransferHistory.id))
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [dict(row) for row in result.mappings().all()], total


async def get_transfer(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    transfer_id: uuid.UUID,
) -> dict[str, Any] | None:
    source_warehouse = aliased(Warehouse)
    destination_warehouse = aliased(Warehouse)
    stmt = (
        select(
            StockTransferHistory.id.label("id"),
            StockTransferHistory.tenant_id.label("tenant_id"),
            StockTransferHistory.product_id.label("product_id"),
            Product.code.label("product_code"),
            Product.name.label("product_name"),
            StockTransferHistory.from_warehouse_id.label("from_warehouse_id"),
            source_warehouse.name.label("from_warehouse_name"),
            source_warehouse.code.label("from_warehouse_code"),
            StockTransferHistory.to_warehouse_id.label("to_warehouse_id"),
            destination_warehouse.name.label("to_warehouse_name"),
            destination_warehouse.code.label("to_warehouse_code"),
            StockTransferHistory.quantity.label("quantity"),
            StockTransferHistory.actor_id.label("actor_id"),
            StockTransferHistory.notes.label("notes"),
            StockTransferHistory.created_at.label("created_at"),
        )
        .join(Product, Product.id == StockTransferHistory.product_id)
        .join(source_warehouse, source_warehouse.id == StockTransferHistory.from_warehouse_id)
        .join(
            destination_warehouse,
            destination_warehouse.id == StockTransferHistory.to_warehouse_id,
        )
        .where(
            StockTransferHistory.id == transfer_id,
            StockTransferHistory.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    row = result.mappings().one_or_none()
    return dict(row) if row is not None else None


def _serialize_physical_count_session(
    count_session: PhysicalCountSession,
    *,
    include_lines: bool,
) -> dict[str, object | None]:
    lines = list(getattr(count_session, "lines", []))
    lines.sort(
        key=lambda line: (
            getattr(getattr(line, "product", None), "name", "") or "",
            getattr(getattr(line, "product", None), "code", "") or "",
            str(line.product_id),
        )
    )
    counted_lines = sum(1 for line in lines if line.counted_qty is not None)
    variance_total = sum(int(line.variance_qty or 0) for line in lines)

    payload: dict[str, object | None] = {
        "id": count_session.id,
        "warehouse_id": count_session.warehouse_id,
        "warehouse_name": getattr(getattr(count_session, "warehouse", None), "name", None),
        "status": _physical_count_status_value(count_session.status),
        "created_by": count_session.created_by,
        "submitted_by": count_session.submitted_by,
        "submitted_at": count_session.submitted_at,
        "approved_by": count_session.approved_by,
        "approved_at": count_session.approved_at,
        "created_at": count_session.created_at,
        "updated_at": count_session.updated_at,
        "total_lines": len(lines),
        "counted_lines": counted_lines,
        "variance_total": variance_total,
    }
    if include_lines:
        payload["lines"] = [_serialize_physical_count_line(line) for line in lines]
    return payload


def _add_physical_count_audit(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor_id: str,
    count_session: PhysicalCountSession,
    action: str,
    before_state: dict[str, object] | None,
    after_state: dict[str, object],
    notes: str | None = None,
) -> None:
    session.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            entity_type="physical_count_session",
            entity_id=str(count_session.id),
            before_state=before_state,
            after_state=after_state,
            correlation_id=str(count_session.id),
            notes=notes,
        )
    )


async def _get_physical_count_session_record(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
) -> PhysicalCountSession | None:
    stmt = (
        select(PhysicalCountSession)
        .options(
            selectinload(PhysicalCountSession.warehouse),
            selectinload(PhysicalCountSession.lines).selectinload(PhysicalCountLine.product),
        )
        .where(
            PhysicalCountSession.id == session_id,
            PhysicalCountSession.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_physical_count_session(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID,
    actor_id: str,
) -> dict[str, object | None]:
    warehouse_stmt = select(Warehouse).where(
        Warehouse.id == warehouse_id,
        Warehouse.tenant_id == tenant_id,
    )
    warehouse_result = await session.execute(warehouse_stmt)
    warehouse = warehouse_result.scalar_one_or_none()
    if warehouse is None:
        raise PhysicalCountNotFoundError("Warehouse not found")

    existing_stmt = select(PhysicalCountSession.id).where(
        PhysicalCountSession.tenant_id == tenant_id,
        PhysicalCountSession.warehouse_id == warehouse_id,
        PhysicalCountSession.status.in_(
            [PhysicalCountSessionStatus.IN_PROGRESS, PhysicalCountSessionStatus.SUBMITTED]
        ),
    )
    existing = await session.execute(existing_stmt)
    if existing.scalar_one_or_none() is not None:
        raise PhysicalCountConflictError(
            "An open physical count session already exists for this warehouse"
        )

    stock_stmt = (
        select(InventoryStock)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.warehouse_id == warehouse_id,
        )
        .order_by(InventoryStock.product_id)
    )
    stock_rows = list((await session.execute(stock_stmt)).scalars().all())

    count_session = PhysicalCountSession(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        created_by=actor_id,
        status=PhysicalCountSessionStatus.IN_PROGRESS,
    )
    count_session.warehouse = warehouse
    try:
        session.add(count_session)
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await session.execute(existing_stmt)
        if existing.scalar_one_or_none() is not None:
            raise PhysicalCountConflictError(
                "An open physical count session already exists for this warehouse"
            )
        raise

    lines = [
        PhysicalCountLine(
            session_id=count_session.id,
            product_id=stock.product_id,
            system_qty_snapshot=stock.quantity,
            counted_qty=None,
            variance_qty=None,
        )
        for stock in stock_rows
    ]
    if lines:
        session.add_all(lines)

    _add_physical_count_audit(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        count_session=count_session,
        action="physical_count_session_created",
        before_state=None,
        after_state={
            "status": PhysicalCountSessionStatus.IN_PROGRESS.value,
            "warehouse_id": str(warehouse_id),
            "line_count": len(lines),
        },
    )
    await session.flush()

    refreshed = await _get_physical_count_session_record(session, tenant_id, count_session.id)
    if refreshed is None:
        raise PhysicalCountNotFoundError("Physical count session was not persisted")
    return _serialize_physical_count_session(refreshed, include_lines=True)


async def list_physical_count_sessions(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, object | None]], int]:
    filters = [PhysicalCountSession.tenant_id == tenant_id]
    if warehouse_id is not None:
        filters.append(PhysicalCountSession.warehouse_id == warehouse_id)
    if status is not None:
        filters.append(PhysicalCountSession.status == PhysicalCountSessionStatus(status))

    count_stmt = select(func.count(PhysicalCountSession.id)).where(*filters)
    total = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(PhysicalCountSession)
        .options(
            selectinload(PhysicalCountSession.warehouse),
            selectinload(PhysicalCountSession.lines),
        )
        .where(*filters)
        .order_by(desc(PhysicalCountSession.created_at))
        .offset(offset)
        .limit(limit)
    )
    items = list((await session.execute(stmt)).scalars().all())
    return [
        _serialize_physical_count_session(item, include_lines=False) for item in items
    ], total


async def get_physical_count_session(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
) -> dict[str, object | None] | None:
    count_session = await _get_physical_count_session_record(session, tenant_id, session_id)
    if count_session is None:
        return None
    return _serialize_physical_count_session(count_session, include_lines=True)


async def update_physical_count_line(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    line_id: uuid.UUID,
    *,
    counted_qty: int,
    notes: str | None,
) -> dict[str, object | None]:
    count_session = await _get_physical_count_session_record(session, tenant_id, session_id)
    if count_session is None:
        raise PhysicalCountNotFoundError("Physical count session not found")
    if count_session.status != PhysicalCountSessionStatus.IN_PROGRESS:
        raise PhysicalCountStateError("Only in-progress sessions can be edited")

    line = next((item for item in count_session.lines if item.id == line_id), None)
    if line is None:
        raise PhysicalCountNotFoundError("Physical count line not found")

    line.counted_qty = counted_qty
    line.variance_qty = counted_qty - line.system_qty_snapshot
    line.notes = notes
    await session.flush()
    return _serialize_physical_count_session(count_session, include_lines=True)


async def submit_physical_count_session(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    actor_id: str,
) -> dict[str, object | None]:
    count_session = await _get_physical_count_session_record(session, tenant_id, session_id)
    if count_session is None:
        raise PhysicalCountNotFoundError("Physical count session not found")
    if count_session.status == PhysicalCountSessionStatus.APPROVED:
        return _serialize_physical_count_session(count_session, include_lines=True)
    if count_session.status == PhysicalCountSessionStatus.SUBMITTED:
        return _serialize_physical_count_session(count_session, include_lines=True)

    if any(line.counted_qty is None for line in count_session.lines):
        raise PhysicalCountStateError("All count lines must be entered before submission")

    count_session.status = PhysicalCountSessionStatus.SUBMITTED
    count_session.submitted_by = actor_id
    count_session.submitted_at = utc_now()

    _add_physical_count_audit(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        count_session=count_session,
        action="physical_count_session_submitted",
        before_state={"status": PhysicalCountSessionStatus.IN_PROGRESS.value},
        after_state={
            "status": PhysicalCountSessionStatus.SUBMITTED.value,
            "variance_total": sum(int(line.variance_qty or 0) for line in count_session.lines),
        },
    )
    await session.flush()
    return _serialize_physical_count_session(count_session, include_lines=True)


async def approve_physical_count_session(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    actor_id: str,
) -> dict[str, object | None]:
    count_session = await _get_physical_count_session_record(session, tenant_id, session_id)
    if count_session is None:
        raise PhysicalCountNotFoundError("Physical count session not found")
    if count_session.status == PhysicalCountSessionStatus.APPROVED:
        return _serialize_physical_count_session(count_session, include_lines=True)
    if count_session.status != PhysicalCountSessionStatus.SUBMITTED:
        raise PhysicalCountStateError("Only submitted sessions can be approved")

    product_ids = [line.product_id for line in count_session.lines]
    live_stock_rows: list[InventoryStock] = []
    if product_ids:
        stock_stmt = (
            select(InventoryStock)
            .where(
                InventoryStock.tenant_id == tenant_id,
                InventoryStock.warehouse_id == count_session.warehouse_id,
                InventoryStock.product_id.in_(product_ids),
            )
            .with_for_update()
        )
        live_stock_rows = list((await session.execute(stock_stmt)).scalars().all())

    live_stock_by_product = {stock.product_id: stock for stock in live_stock_rows}
    for line in count_session.lines:
        live_qty = live_stock_by_product.get(line.product_id)
        current_qty = live_qty.quantity if live_qty is not None else 0
        if current_qty != line.system_qty_snapshot:
            product_name = (
                getattr(getattr(line, "product", None), "name", None) or str(line.product_id)
            )
            raise PhysicalCountConflictError(
                f"Physical count snapshot is stale for {product_name}"
            )

    adjustment_count = 0
    for line in count_session.lines:
        if line.counted_qty is None:
            raise PhysicalCountStateError("Cannot approve a session with incomplete count lines")
        line.variance_qty = line.counted_qty - line.system_qty_snapshot
        variance_qty = line.variance_qty
        if variance_qty is None:
            raise PhysicalCountStateError("Cannot approve a session with incomplete variance data")
        if variance_qty == 0:
            continue
        adjustment_count += 1
        note_parts = [f"Physical count session {count_session.id}"]
        if line.notes:
            note_parts.append(line.notes)
        await create_stock_adjustment(
            session,
            tenant_id,
            product_id=line.product_id,
            warehouse_id=count_session.warehouse_id,
            quantity_change=variance_qty,
            reason_code=ReasonCode.PHYSICAL_COUNT,
            actor_id=actor_id,
            notes=" - ".join(note_parts),
        )

    count_session.status = PhysicalCountSessionStatus.APPROVED
    count_session.approved_by = actor_id
    count_session.approved_at = utc_now()

    _add_physical_count_audit(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        count_session=count_session,
        action="physical_count_session_approved",
        before_state={"status": PhysicalCountSessionStatus.SUBMITTED.value},
        after_state={
            "status": PhysicalCountSessionStatus.APPROVED.value,
            "adjustment_count": adjustment_count,
        },
    )
    await session.flush()
    return _serialize_physical_count_session(count_session, include_lines=True)


# ── Reorder alert helper ───────────────────────────────────────


def _compute_severity(current_stock: int, reorder_point: int) -> str:
    """Compute alert severity based on stock level."""
    if current_stock == 0:
        return "CRITICAL"
    if reorder_point > 0 and current_stock < reorder_point * 0.25:
        return "CRITICAL"
    if current_stock < reorder_point:
        return "WARNING"
    return "INFO"


def _release_expired_snooze(alert: ReorderAlert, *, now) -> None:
    if (
        alert.status == AlertStatus.SNOOZED
        and alert.snoozed_until is not None
        and alert.snoozed_until <= now
    ):
        alert.status = AlertStatus.PENDING
        alert.snoozed_until = None
        alert.snoozed_by = None


async def _check_reorder_alert(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    current_quantity: int,
    reorder_point: int,
) -> None:
    """Create or resolve reorder alert based on stock level."""
    if reorder_point <= 0:
        return

    now = utc_now()

    stmt = select(ReorderAlert).where(
        ReorderAlert.tenant_id == tenant_id,
        ReorderAlert.product_id == product_id,
        ReorderAlert.warehouse_id == warehouse_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    # NOTE: Alerts trigger at <= (proactive), while is_below_reorder
    # display flag uses strict < ("at reorder point" is not "below").
    if current_quantity <= reorder_point:
        severity = _compute_severity(current_quantity, reorder_point)
        if alert is None:
            alert = ReorderAlert(
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                current_stock=current_quantity,
                reorder_point=reorder_point,
                status=AlertStatus.PENDING,
                severity=severity,
            )
            session.add(alert)
        else:
            previous_stock = alert.current_stock
            _release_expired_snooze(alert, now=now)
            alert.current_stock = current_quantity
            alert.severity = severity
            # Only collapse RESOLVED → PENDING; preserve ACKNOWLEDGED
            if alert.status == AlertStatus.RESOLVED:
                alert.status = AlertStatus.PENDING
            elif alert.status == AlertStatus.DISMISSED and previous_stock > reorder_point:
                alert.status = AlertStatus.PENDING
                alert.dismissed_at = None
                alert.dismissed_by = None
            # ACKNOWLEDGED stays acknowledged — do not demote
    elif alert is not None:
        _release_expired_snooze(alert, now=now)
        alert.current_stock = current_quantity
        if alert.status in {AlertStatus.PENDING, AlertStatus.SNOOZED}:
            # Only active alerts auto-resolve when stock is restored.
            # ACKNOWLEDGED alerts require explicit resolution or a real supplier delivery.
            alert.status = AlertStatus.RESOLVED
            alert.snoozed_until = None
            alert.snoozed_by = None
    # If alert is ACKNOWLEDGED and stock is above threshold: do nothing (keep acknowledged)


# ── Reorder alert queries ─────────────────────────────────────


async def list_reorder_alerts(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status_filter: str | None = None,
    warehouse_id: uuid.UUID | None = None,
    sort_by: str = "severity",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List reorder alerts with product/warehouse names."""
    from sqlalchemy import func as sqlfunc

    now = utc_now()

    base_where = [ReorderAlert.tenant_id == tenant_id]
    if status_filter:
        if status_filter == AlertStatus.PENDING.value:
            base_where.append(
                or_(
                    ReorderAlert.status == AlertStatus.PENDING,
                    and_(
                        ReorderAlert.status == AlertStatus.SNOOZED,
                        ReorderAlert.snoozed_until.is_not(None),
                        ReorderAlert.snoozed_until <= now,
                    ),
                )
            )
        elif status_filter == AlertStatus.SNOOZED.value:
            base_where.append(ReorderAlert.status == AlertStatus.SNOOZED)
            base_where.append(
                or_(
                    ReorderAlert.snoozed_until.is_(None),
                    ReorderAlert.snoozed_until > now,
                )
            )
        else:
            base_where.append(ReorderAlert.status == AlertStatus(status_filter))
    if warehouse_id:
        base_where.append(ReorderAlert.warehouse_id == warehouse_id)

    # Count
    count_stmt = select(sqlfunc.count(ReorderAlert.id)).where(*base_where)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # Days-until-stockout expression: current_stock / GREATEST(avg_daily_usage_estimate, 0.001)
    # avg_daily_usage_estimate = reorder_point / 14 (2-week lead time at 0.5 safety factor proxy)
    days_until_stockout = ReorderAlert.current_stock / func.greatest(
        ReorderAlert.reorder_point / 14.0, 0.001,
    )

    # Severity tier ordering: CRITICAL=1, WARNING=2, INFO=3
    severity_order = case(
        (ReorderAlert.severity == "CRITICAL", 1),
        (ReorderAlert.severity == "WARNING", 2),
        else_=3,
    )

    # Apply sort
    if sort_by == "created_at":
        order_col = ReorderAlert.created_at.desc()
    elif sort_by == "current_stock":
        order_col = ReorderAlert.current_stock.asc()
    else:
        # Default: severity tier, then days_until_stockout ascending (most urgent first)
        order_col = [severity_order.asc(), days_until_stockout.asc()]

    # Fetch with joins
    stmt = (
        select(
            ReorderAlert.id,
            ReorderAlert.product_id,
            Product.name.label("product_name"),
            ReorderAlert.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            ReorderAlert.current_stock,
            ReorderAlert.reorder_point,
            ReorderAlert.status,
            ReorderAlert.severity,
            ReorderAlert.created_at,
            ReorderAlert.acknowledged_at,
            ReorderAlert.acknowledged_by,
            ReorderAlert.snoozed_until,
            ReorderAlert.snoozed_by,
            ReorderAlert.dismissed_at,
            ReorderAlert.dismissed_by,
        )
        .join(Product, ReorderAlert.product_id == Product.id)
        .join(Warehouse, ReorderAlert.warehouse_id == Warehouse.id)
        .where(*base_where)
        .order_by(*order_col if isinstance(order_col, list) else (order_col,))
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.all()

    items = [
        {
            "id": row.id,
            "product_id": row.product_id,
            "product_name": row.product_name,
            "warehouse_id": row.warehouse_id,
            "warehouse_name": row.warehouse_name,
            "current_stock": row.current_stock,
            "reorder_point": row.reorder_point,
            "status": (
                AlertStatus.PENDING.value
                if (
                    row.status == AlertStatus.SNOOZED
                    and row.snoozed_until is not None
                    and row.snoozed_until <= now
                )
                else (row.status.value if hasattr(row.status, "value") else row.status)
            ),
            "severity": row.severity,
            "created_at": row.created_at,
            "acknowledged_at": row.acknowledged_at,
            "acknowledged_by": row.acknowledged_by,
            "snoozed_until": row.snoozed_until,
            "snoozed_by": row.snoozed_by,
            "dismissed_at": row.dismissed_at,
            "dismissed_by": row.dismissed_by,
        }
        for row in rows
    ]
    return items, total


async def acknowledge_alert(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    *,
    actor_id: str,
) -> dict | None:
    """Acknowledge a reorder alert."""
    stmt = select(ReorderAlert).where(
        ReorderAlert.id == alert_id,
        ReorderAlert.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if alert is None:
        return None

    _release_expired_snooze(alert, now=utc_now())

    if alert.status in {AlertStatus.RESOLVED, AlertStatus.DISMISSED}:
        return None

    now = utc_now()
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = now
    alert.acknowledged_by = actor_id
    await session.flush()

    return {
        "id": alert.id,
        "status": alert.status.value,
        "acknowledged_at": now,
        "acknowledged_by": actor_id,
    }


async def snooze_alert(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    *,
    actor_id: str,
    duration_minutes: int,
) -> dict | None:
    """Snooze a reorder alert for the requested duration."""
    stmt = select(ReorderAlert).where(
        ReorderAlert.id == alert_id,
        ReorderAlert.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if alert is None:
        return None

    _release_expired_snooze(alert, now=utc_now())

    if alert.status in {AlertStatus.RESOLVED, AlertStatus.DISMISSED}:
        return None

    now = utc_now()
    snoozed_until = now + timedelta(minutes=duration_minutes)
    alert.status = AlertStatus.SNOOZED
    alert.snoozed_until = snoozed_until
    alert.snoozed_by = actor_id
    await session.flush()

    return {
        "id": alert.id,
        "status": alert.status.value,
        "snoozed_until": snoozed_until,
        "snoozed_by": actor_id,
    }


async def dismiss_alert(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    *,
    actor_id: str,
) -> dict | None:
    """Dismiss a reorder alert until stock recovers and breaches again."""
    stmt = select(ReorderAlert).where(
        ReorderAlert.id == alert_id,
        ReorderAlert.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if alert is None:
        return None

    _release_expired_snooze(alert, now=utc_now())

    if alert.status in {AlertStatus.RESOLVED, AlertStatus.DISMISSED}:
        return None

    now = utc_now()
    alert.status = AlertStatus.DISMISSED
    alert.dismissed_at = now
    alert.dismissed_by = actor_id
    alert.snoozed_until = None
    alert.snoozed_by = None
    await session.flush()

    return {
        "id": alert.id,
        "status": alert.status.value,
        "dismissed_at": now,
        "dismissed_by": actor_id,
    }


async def _load_reorder_suggestion_source(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
):
    stmt = (
        select(
            InventoryStock.product_id,
            Product.name.label("product_name"),
            Product.code.label("product_code"),
            InventoryStock.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity.label("current_stock"),
            InventoryStock.reorder_point,
            InventoryStock.target_stock_qty,
            InventoryStock.on_order_qty,
            InventoryStock.in_transit_qty,
            InventoryStock.reserved_qty,
        )
        .join(Product, Product.id == InventoryStock.product_id)
        .join(Warehouse, Warehouse.id == InventoryStock.warehouse_id)
        .where(
            InventoryStock.tenant_id == tenant_id,
            Product.tenant_id == tenant_id,
            Warehouse.tenant_id == tenant_id,
            Product.id == product_id,
            Warehouse.id == warehouse_id,
        )
    )
    result = await session.execute(stmt)
    return result.first()


def _int_field(row: object, name: str) -> int:
    return int(getattr(row, name, 0) or 0)


def _serialize_reorder_suggestion_row(
    row: object,
    *,
    supplier_hint: dict | None,
    suggested_qty_override: int | None = None,
) -> dict:
    current_stock = _int_field(row, "current_stock")
    reorder_point = _int_field(row, "reorder_point")
    on_order_qty = _int_field(row, "on_order_qty")
    in_transit_qty = _int_field(row, "in_transit_qty")
    reserved_qty = _int_field(row, "reserved_qty")
    raw_target_stock_qty = _int_field(row, "target_stock_qty")
    target_stock_qty = raw_target_stock_qty if raw_target_stock_qty > 0 else None
    inventory_position = current_stock + on_order_qty + in_transit_qty - reserved_qty
    base_target = target_stock_qty if target_stock_qty is not None else reorder_point
    suggested_qty = max(0, base_target - inventory_position)
    if suggested_qty_override is not None:
        suggested_qty = suggested_qty_override

    return {
        "product_id": getattr(row, "product_id"),
        "product_name": getattr(row, "product_name"),
        "product_code": getattr(row, "product_code", None),
        "warehouse_id": getattr(row, "warehouse_id"),
        "warehouse_name": getattr(row, "warehouse_name"),
        "current_stock": current_stock,
        "reorder_point": reorder_point,
        "inventory_position": inventory_position,
        "target_stock_qty": target_stock_qty,
        "suggested_qty": suggested_qty,
        "supplier_hint": supplier_hint,
    }


async def _batch_get_product_suppliers(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_ids: list[uuid.UUID],
) -> dict[uuid.UUID, dict | None]:
    unique_product_ids = list(dict.fromkeys(product_ids))
    if not unique_product_ids:
        return {}

    supplier_sources = (
        select(
            SupplierOrderLine.product_id.label("product_id"),
            SupplierOrder.supplier_id.label("supplier_id"),
            SupplierOrder.received_date.label("effective_date"),
            SupplierOrderLine.unit_price.label("unit_cost"),
            SupplierOrderLine.id.label("source_row_id"),
            literal(0).label("source_priority"),
        )
        .join(SupplierOrder, SupplierOrder.id == SupplierOrderLine.order_id)
        .where(
            SupplierOrder.tenant_id == tenant_id,
            SupplierOrderLine.product_id.in_(unique_product_ids),
            SupplierOrder.received_date.isnot(None),
            SupplierOrderLine.unit_price.isnot(None),
        )
        .union_all(
            select(
                SupplierInvoiceLine.product_id.label("product_id"),
                SupplierInvoice.supplier_id.label("supplier_id"),
                SupplierInvoice.invoice_date.label("effective_date"),
                SupplierInvoiceLine.unit_price.label("unit_cost"),
                SupplierInvoiceLine.id.label("source_row_id"),
                literal(1).label("source_priority"),
            )
            .join(
                SupplierInvoice,
                SupplierInvoice.id == SupplierInvoiceLine.supplier_invoice_id,
            )
            .where(
                SupplierInvoice.tenant_id == tenant_id,
                SupplierInvoiceLine.product_id.in_(unique_product_ids),
                SupplierInvoiceLine.unit_price.isnot(None),
            )
        )
        .subquery()
    )

    fallback_ranked = (
        select(
            supplier_sources.c.product_id,
            supplier_sources.c.supplier_id,
            Supplier.name.label("name"),
            Supplier.default_lead_time_days.label("default_lead_time_days"),
            supplier_sources.c.unit_cost,
            func.row_number().over(
                partition_by=supplier_sources.c.product_id,
                order_by=(
                    supplier_sources.c.effective_date.desc(),
                    supplier_sources.c.source_priority.desc(),
                    supplier_sources.c.source_row_id.desc(),
                ),
            ).label("row_number"),
        )
        .join(
            Supplier,
            and_(
                Supplier.id == supplier_sources.c.supplier_id,
                Supplier.tenant_id == tenant_id,
            ),
        )
        .subquery()
    )

    fallback_candidates = select(
        fallback_ranked.c.product_id,
        fallback_ranked.c.supplier_id,
        fallback_ranked.c.name,
        fallback_ranked.c.unit_cost,
        fallback_ranked.c.default_lead_time_days,
        literal(1).label("candidate_priority"),
    ).where(fallback_ranked.c.row_number == 1)

    explicit_candidates = (
        select(
            ProductSupplier.product_id.label("product_id"),
            Supplier.id.label("supplier_id"),
            Supplier.name.label("name"),
            ProductSupplier.unit_cost.label("unit_cost"),
            func.coalesce(
                ProductSupplier.lead_time_days,
                Supplier.default_lead_time_days,
            ).label("default_lead_time_days"),
            literal(0).label("candidate_priority"),
        )
        .join(
            Supplier,
            and_(
                Supplier.id == ProductSupplier.supplier_id,
                Supplier.tenant_id == tenant_id,
            ),
        )
        .where(
            ProductSupplier.tenant_id == tenant_id,
            ProductSupplier.product_id.in_(unique_product_ids),
            ProductSupplier.is_default.is_(True),
        )
    )

    def _ranked_stmt(candidate_select):
        explicit_or_fallback = candidate_select.subquery("explicit_or_fallback")
        ranked_candidates = (
            select(
                explicit_or_fallback.c.product_id,
                explicit_or_fallback.c.supplier_id,
                explicit_or_fallback.c.name,
                explicit_or_fallback.c.unit_cost,
                explicit_or_fallback.c.default_lead_time_days,
                func.row_number().over(
                    partition_by=explicit_or_fallback.c.product_id,
                    order_by=(explicit_or_fallback.c.candidate_priority.asc(),),
                ).label("row_number"),
            )
            .select_from(explicit_or_fallback)
            .subquery()
        )
        return select(
            ranked_candidates.c.product_id,
            ranked_candidates.c.supplier_id,
            ranked_candidates.c.name,
            ranked_candidates.c.unit_cost,
            ranked_candidates.c.default_lead_time_days,
        ).where(ranked_candidates.c.row_number == 1)

    supplier_map: dict[uuid.UUID, dict | None] = {
        product_id: None for product_id in unique_product_ids
    }

    candidates = (
        explicit_candidates.union_all(fallback_candidates)
        if await _product_supplier_table_exists(session)
        else fallback_candidates
    )
    result = await session.execute(_ranked_stmt(candidates))

    for row in result.all():
        supplier_map[row.product_id] = {
            "supplier_id": row.supplier_id,
            "name": row.name,
            "unit_cost": float(row.unit_cost) if row.unit_cost is not None else None,
            "default_lead_time_days": row.default_lead_time_days,
        }
    return supplier_map


def _is_missing_product_supplier_table(exc: ProgrammingError) -> bool:
    return "product_supplier" in str(exc).lower()


async def _product_supplier_table_exists(session: AsyncSession) -> bool:
    session_info = getattr(session, "info", None)
    cached = session_info.get("product_supplier_table_exists") if isinstance(session_info, dict) else None
    if isinstance(cached, bool):
        return cached

    result = await session.execute(select(func.to_regclass("product_supplier")))
    exists = result.scalar_one_or_none() is not None
    if isinstance(session_info, dict):
        session_info["product_supplier_table_exists"] = exists
    return exists


async def _load_product_supplier_explicit_row(session: AsyncSession, explicit_stmt):
    try:
        return (await session.execute(explicit_stmt)).first()
    except ProgrammingError as exc:
        if _is_missing_product_supplier_table(exc):
            return None
        raise


async def list_reorder_suggestions(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
) -> tuple[list[dict], int]:
    stmt = (
        select(
            InventoryStock.product_id,
            Product.name.label("product_name"),
            Product.code.label("product_code"),
            InventoryStock.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity.label("current_stock"),
            InventoryStock.reorder_point,
            InventoryStock.target_stock_qty,
            InventoryStock.on_order_qty,
            InventoryStock.in_transit_qty,
            InventoryStock.reserved_qty,
        )
        .join(Product, Product.id == InventoryStock.product_id)
        .join(Warehouse, Warehouse.id == InventoryStock.warehouse_id)
        .where(
            InventoryStock.tenant_id == tenant_id,
            Product.tenant_id == tenant_id,
            Warehouse.tenant_id == tenant_id,
            Product.status == "active",
            InventoryStock.quantity <= InventoryStock.reorder_point,
        )
        .order_by(Warehouse.name, Product.name)
    )
    if warehouse_id is not None:
        stmt = stmt.where(InventoryStock.warehouse_id == warehouse_id)

    result = await session.execute(stmt)
    rows = result.all()

    product_ids = [row.product_id for row in rows]
    supplier_map = await _batch_get_product_suppliers(session, tenant_id, product_ids)

    items: list[dict] = []
    for row in rows:
        items.append(
            _serialize_reorder_suggestion_row(
                row,
                supplier_hint=supplier_map.get(row.product_id),
            )
        )

    return items, len(items)


async def create_reorder_suggestion_orders(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    items: list[dict],
    actor_id: str,
) -> dict:
    grouped_lines: dict[uuid.UUID, dict[str, object]] = {}
    unresolved_rows: list[dict] = []
    order_date = today()

    product_ids = [item["product_id"] for item in items]
    supplier_map = await _batch_get_product_suppliers(session, tenant_id, product_ids)

    for item in items:
        product_id = item["product_id"]
        warehouse_id = item["warehouse_id"]
        suggested_qty = int(item["suggested_qty"])

        supplier_hint = supplier_map.get(product_id)
        if supplier_hint is None:
            row = await _load_reorder_suggestion_source(
                session,
                tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
            )
            if row is not None:
                unresolved_rows.append(
                    _serialize_reorder_suggestion_row(
                        row,
                        supplier_hint=None,
                        suggested_qty_override=suggested_qty,
                    )
                )
            continue

        supplier_id = supplier_hint["supplier_id"]
        group = grouped_lines.setdefault(
            supplier_id,
            {
                "supplier_hint": supplier_hint,
                "lines": [],
            },
        )
        cast(list[dict], group["lines"]).append(
            {
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "quantity_ordered": suggested_qty,
                "unit_price": supplier_hint.get("unit_cost"),
            }
        )

    created_orders: list[dict] = []
    for supplier_id, group in grouped_lines.items():
        supplier_hint = cast(dict[str, object], group["supplier_hint"])
        lines = cast(list[dict], group["lines"])
        lead_time_days = supplier_hint.get("default_lead_time_days")
        expected_arrival_date = (
            order_date + timedelta(days=int(lead_time_days))
            if lead_time_days is not None
            else None
        )
        created_order = await create_supplier_order(
            session,
            tenant_id,
            supplier_id=supplier_id,
            order_date=order_date,
            expected_arrival_date=expected_arrival_date,
            lines=lines,
            actor_id=actor_id,
        )
        created_orders.append(
            {
                "order_id": created_order["id"],
                "order_number": created_order["order_number"],
                "supplier_id": created_order["supplier_id"],
                "supplier_name": created_order["supplier_name"],
                "line_count": len(lines),
            }
        )

    return {
        "created_orders": created_orders,
        "unresolved_rows": unresolved_rows,
    }


def _serialize_below_reorder_report_row(
    row: object,
    *,
    default_supplier: str | None,
) -> dict:
    current_stock = int(getattr(row, "current_stock", 0) or 0)
    reorder_point = int(getattr(row, "reorder_point", 0) or 0)

    return {
        "product_id": getattr(row, "product_id"),
        "product_code": getattr(row, "product_code"),
        "product_name": getattr(row, "product_name"),
        "category": getattr(row, "category", None),
        "warehouse_id": getattr(row, "warehouse_id"),
        "warehouse_name": getattr(row, "warehouse_name"),
        "current_stock": current_stock,
        "reorder_point": reorder_point,
        "shortage_qty": max(0, reorder_point - current_stock),
        "on_order_qty": int(getattr(row, "on_order_qty", 0) or 0),
        "in_transit_qty": int(getattr(row, "in_transit_qty", 0) or 0),
        "default_supplier": default_supplier,
    }


async def list_below_reorder_products(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
) -> tuple[list[dict], int]:
    stmt = (
        select(
            InventoryStock.product_id,
            Product.code.label("product_code"),
            Product.name.label("product_name"),
            Product.category,
            InventoryStock.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity.label("current_stock"),
            InventoryStock.reorder_point,
            InventoryStock.on_order_qty,
            InventoryStock.in_transit_qty,
        )
        .join(Product, Product.id == InventoryStock.product_id)
        .join(Warehouse, Warehouse.id == InventoryStock.warehouse_id)
        .where(
            InventoryStock.tenant_id == tenant_id,
            Product.tenant_id == tenant_id,
            Warehouse.tenant_id == tenant_id,
            Product.status == "active",
            InventoryStock.reorder_point > 0,
            InventoryStock.quantity < InventoryStock.reorder_point,
        )
        .order_by(Warehouse.name, Product.code)
    )
    if warehouse_id is not None:
        stmt = stmt.where(InventoryStock.warehouse_id == warehouse_id)

    result = await session.execute(stmt)
    rows = result.all()

    product_ids = [row.product_id for row in rows]
    supplier_map = await _batch_get_product_suppliers(session, tenant_id, product_ids)

    items: list[dict] = []
    for row in rows:
        supplier_hint = supplier_map.get(row.product_id)
        items.append(
            _serialize_below_reorder_report_row(
                row,
                default_supplier=(
                    str(supplier_hint.get("name"))
                    if supplier_hint is not None and supplier_hint.get("name")
                    else None
                ),
            )
        )

    return items, len(items)


def _resolve_inventory_valuation_cost(
    row: object,
) -> tuple[Decimal | None, str]:
    standard_cost = _normalize_standard_cost(getattr(row, "standard_cost", None))
    if standard_cost is not None:
        return standard_cost, "standard_cost"

    latest_purchase_cost = _normalize_standard_cost(getattr(row, "latest_purchase_unit_cost", None))
    if latest_purchase_cost is not None:
        return latest_purchase_cost, "latest_purchase"

    return None, "missing"


def _serialize_inventory_valuation_row(row: object) -> dict:
    quantity = int(getattr(row, "quantity", 0) or 0)
    unit_cost, cost_source = _resolve_inventory_valuation_cost(row)
    extended_value = _quantize_valuation_amount(
        Decimal(quantity) * (unit_cost or Decimal("0"))
    )

    return {
        "product_id": getattr(row, "product_id"),
        "product_code": getattr(row, "product_code"),
        "product_name": getattr(row, "product_name"),
        "category": getattr(row, "category", None),
        "warehouse_id": getattr(row, "warehouse_id"),
        "warehouse_name": getattr(row, "warehouse_name"),
        "quantity": quantity,
        "unit_cost": unit_cost,
        "extended_value": extended_value,
        "cost_source": cost_source,
    }


async def get_inventory_valuation(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
) -> dict:
    latest_purchase_ranked = (
        select(
            SupplierOrderLine.product_id.label("product_id"),
            SupplierOrderLine.unit_price.label("unit_cost"),
            SupplierOrder.received_date.label("received_date"),
            func.row_number().over(
                partition_by=SupplierOrderLine.product_id,
                order_by=(
                    SupplierOrder.received_date.desc(),
                    SupplierOrder.created_at.desc(),
                    SupplierOrderLine.id.desc(),
                ),
            ).label("row_number"),
        )
        .join(SupplierOrder, SupplierOrder.id == SupplierOrderLine.order_id)
        .where(
            SupplierOrder.tenant_id == tenant_id,
            SupplierOrder.received_date.isnot(None),
            SupplierOrderLine.unit_price.isnot(None),
        )
        .subquery()
    )

    latest_purchase = (
        select(
            latest_purchase_ranked.c.product_id,
            latest_purchase_ranked.c.unit_cost,
            latest_purchase_ranked.c.received_date,
        )
        .where(latest_purchase_ranked.c.row_number == 1)
        .subquery()
    )

    stmt = (
        select(
            InventoryStock.product_id,
            Product.code.label("product_code"),
            Product.name.label("product_name"),
            Product.category,
            Product.standard_cost,
            InventoryStock.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity.label("quantity"),
            latest_purchase.c.unit_cost.label("latest_purchase_unit_cost"),
        )
        .join(Product, Product.id == InventoryStock.product_id)
        .join(Warehouse, Warehouse.id == InventoryStock.warehouse_id)
        .outerjoin(latest_purchase, latest_purchase.c.product_id == InventoryStock.product_id)
        .where(
            InventoryStock.tenant_id == tenant_id,
            Product.tenant_id == tenant_id,
            Warehouse.tenant_id == tenant_id,
        )
        .order_by(Warehouse.name, Product.code)
    )
    if warehouse_id is not None:
        stmt = stmt.where(InventoryStock.warehouse_id == warehouse_id)

    result = await session.execute(stmt)
    rows = result.all()

    items: list[dict] = []
    warehouse_totals: dict[uuid.UUID, dict] = {}
    grand_total_value = Decimal("0")
    grand_total_quantity = 0

    for row in rows:
        item = _serialize_inventory_valuation_row(row)
        items.append(item)

        warehouse_total = warehouse_totals.setdefault(
            item["warehouse_id"],
            {
                "warehouse_id": item["warehouse_id"],
                "warehouse_name": item["warehouse_name"],
                "total_quantity": 0,
                "total_value": Decimal("0"),
                "row_count": 0,
            },
        )
        warehouse_total["total_quantity"] = int(warehouse_total["total_quantity"]) + item["quantity"]  # noqa: E501
        warehouse_total["total_value"] = _quantize_valuation_amount(
            Decimal(str(warehouse_total["total_value"])) + item["extended_value"]
        )
        warehouse_total["row_count"] = int(warehouse_total["row_count"]) + 1

        grand_total_quantity += item["quantity"]
        grand_total_value = _quantize_valuation_amount(grand_total_value + item["extended_value"])

    return {
        "items": items,
        "warehouse_totals": list(warehouse_totals.values()),
        "grand_total_value": grand_total_value,
        "grand_total_quantity": grand_total_quantity,
        "total_rows": len(items),
    }


# ── Stock queries ──────────────────────────────────────────────


async def get_inventory_stocks(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
) -> list[InventoryStock]:
    """Get stock levels for a product, optionally filtered by warehouse."""
    stmt = select(InventoryStock).where(
        InventoryStock.tenant_id == tenant_id,
        InventoryStock.product_id == product_id,
    )
    if warehouse_id is not None:
        stmt = stmt.where(InventoryStock.warehouse_id == warehouse_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ── Stock adjustment ───────────────────────────────────────────


async def create_stock_adjustment(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity_change: int,
    reason_code: ReasonCode,
    actor_id: str,
    notes: str | None = None,
) -> dict:
    """Atomically adjust stock and record adjustment + audit + reorder alert."""
    if quantity_change == 0:
        raise TransferValidationError("Quantity change must be non-zero")

    # 1. Lock inventory row
    stock_stmt = (
        select(InventoryStock)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
            InventoryStock.warehouse_id == warehouse_id,
        )
        .with_for_update()
    )
    stock_result = await session.execute(stock_stmt)
    stock = stock_result.scalar_one_or_none()

    if stock is None:
        if quantity_change < 0:
            raise InsufficientStockError(available=0, requested=abs(quantity_change))
        stock = InventoryStock(
            tenant_id=tenant_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=0,
            reorder_point=0,
        )
        session.add(stock)
        await session.flush()

    # 2. Validate sufficient stock for removals
    if quantity_change < 0 and stock.quantity < abs(quantity_change):
        raise InsufficientStockError(
            available=stock.quantity,
            requested=abs(quantity_change),
        )

    # 3. Update stock
    before_qty = stock.quantity
    stock.quantity += quantity_change

    # 4. Record adjustment
    adj_id = uuid.uuid4()
    adj_created = utc_now()
    adjustment = StockAdjustment(
        id=adj_id,
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity_change=quantity_change,
        reason_code=reason_code,
        actor_id=actor_id,
        notes=notes,
        created_at=adj_created,
    )
    session.add(adjustment)
    await session.flush()

    # 5. Audit log
    audit = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="stock_adjustment",
        entity_type="stock_adjustment",
        entity_id=str(adj_id),
        before_state={"quantity": before_qty},
        after_state={"quantity": stock.quantity},
        correlation_id=str(adj_id),
        notes=notes,
    )
    session.add(audit)

    # 6. Emit stock changed event
    await emit(StockChangedEvent(
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        before_quantity=before_qty,
        after_quantity=stock.quantity,
        reorder_point=stock.reorder_point,
        actor_id=actor_id,
    ), session)

    await session.flush()

    return {
        "id": adj_id,
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "quantity_change": quantity_change,
        "reason_code": reason_code.value,
        "actor_id": actor_id,
        "notes": notes,
        "updated_stock": stock.quantity,
        "created_at": adj_created,
    }


# ── Product detail ─────────────────────────────────────────────


async def get_product_detail(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    locale: str = DEFAULT_CATEGORY_LOCALE,
    history_limit: int = 100,
    history_offset: int = 0,
) -> dict | None:
    """Return product with per-warehouse stock info and adjustment history."""
    # 1. Fetch product
    product_stmt = (
        select(Product)
        .options(selectinload(Product.category_ref).selectinload(Category.translations))
        .where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
        )
    )
    product_result = await session.execute(product_stmt)
    product = product_result.scalar_one_or_none()
    if product is None:
        return None

    # 2. Fetch warehouse stocks with warehouse name and last adjustment date
    last_adj_sq = (
        select(
            StockAdjustment.warehouse_id,
            StockAdjustment.product_id,
            func.max(StockAdjustment.created_at).label("last_adjusted"),
        )
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
        )
        .group_by(StockAdjustment.warehouse_id, StockAdjustment.product_id)
        .subquery()
    )

    stock_stmt = (
        select(
            InventoryStock.id.label("stock_id"),
            InventoryStock.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity,
            InventoryStock.reorder_point,
            InventoryStock.safety_factor,
            InventoryStock.lead_time_days,
            InventoryStock.policy_type,
            InventoryStock.target_stock_qty,
            InventoryStock.on_order_qty,
            InventoryStock.in_transit_qty,
            InventoryStock.reserved_qty,
            InventoryStock.planning_horizon_days,
            InventoryStock.review_cycle_days,
            last_adj_sq.c.last_adjusted,
        )
        .join(Warehouse, InventoryStock.warehouse_id == Warehouse.id)
        .outerjoin(
            last_adj_sq,
            (InventoryStock.warehouse_id == last_adj_sq.c.warehouse_id)
            & (InventoryStock.product_id == last_adj_sq.c.product_id),
        )
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
        )
        .order_by(Warehouse.name)
    )
    stock_result = await session.execute(stock_stmt)
    stock_rows = stock_result.all()

    warehouses = []
    total_stock = 0
    for row in stock_rows:
        total_stock += row.quantity
        warehouses.append(
            {
                "stock_id": row.stock_id,
                "warehouse_id": row.warehouse_id,
                "warehouse_name": row.warehouse_name,
                "current_stock": row.quantity,
                "reorder_point": row.reorder_point,
                "safety_factor": row.safety_factor,
                "lead_time_days": row.lead_time_days,
                "policy_type": row.policy_type,
                "target_stock_qty": row.target_stock_qty,
                "on_order_qty": row.on_order_qty,
                "in_transit_qty": row.in_transit_qty,
                "reserved_qty": row.reserved_qty,
                "planning_horizon_days": row.planning_horizon_days,
                "review_cycle_days": row.review_cycle_days,
                "is_below_reorder": (row.reorder_point > 0 and row.quantity < row.reorder_point),
                "last_adjusted": row.last_adjusted,
            }
        )

    # 3. Fetch adjustment history with pagination
    history_stmt = (
        select(StockAdjustment)
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
        )
        .order_by(StockAdjustment.created_at.desc())
        .offset(history_offset)
        .limit(history_limit)
    )
    history_result = await session.execute(history_stmt)
    adjustments = [
        adjustment
        for adjustment in history_result.scalars().all()
        if adjustment.actor_id != "reconciliation-apply"
    ]

    history = [
        {
            "id": adj.id,
            "created_at": adj.created_at,
            "quantity_change": adj.quantity_change,
            "reason_code": adj.reason_code.value,
            "actor_id": adj.actor_id,
            "notes": adj.notes,
        }
        for adj in adjustments
    ]

    return {
        "id": product.id,
        "code": product.code,
        "name": product.name,
        "category_id": product.category_id,
        "category": _localized_category_name(
            product.category_ref,
            resolve_category_locale(locale),
            fallback_name=product.category,
        ),
        "description": product.description,
        "unit": product.unit,
        "standard_cost": product.standard_cost,
        "status": product.status,
        "legacy_master_snapshot": getattr(product, "legacy_master_snapshot", None),
        "total_stock": total_stock,
        "warehouses": warehouses,
        "adjustment_history": history,
    }


# ── Product search ─────────────────────────────────────────────


async def search_products(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    query: str,
    *,
    warehouse_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    category: str | None = None,
    locale: str = DEFAULT_CATEGORY_LOCALE,
    include_inactive: bool = False,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "code",
    sort_dir: str = "asc",
) -> tuple[list[dict], int]:
    """Hybrid search: exact/prefix code → trigram → tsvector ranking."""
    q = query.strip()
    search_query = func.plainto_tsquery("simple", q) if q else None

    # Escape LIKE wildcards to prevent pattern injection
    q_like = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    exact_code_match = func.lower(Product.code) == func.lower(q)
    prefix_code_match = Product.code.ilike(q_like + "%", escape="\\")
    name_prefix_match = Product.name.ilike(q_like + "%", escape="\\")
    name_contains_match = Product.name.ilike("%" + q_like + "%", escape="\\")
    text_search_match = (
        Product.search_vector.op("@@")(search_query) if search_query is not None else None
    )

    # Relevance scoring via CASE + trigram + tsvector
    exact_code = case(
        (exact_code_match, literal(10.0)),
        else_=literal(0.0),
    )
    prefix_code = case(
        (prefix_code_match, literal(5.0)),
        else_=literal(0.0),
    )
    trgm_score = func.similarity(Product.name, q)
    ts_rank_score = func.coalesce(
        func.ts_rank(
            Product.search_vector,
            search_query,
        ),
        literal(0.0),
    )
    code_trgm = func.similarity(Product.code, q)
    relevance = exact_code + prefix_code + trgm_score + ts_rank_score + code_trgm

    # Stock aggregation subquery
    stock_sq = select(
        InventoryStock.product_id,
        func.coalesce(func.sum(InventoryStock.quantity), 0).label(
            "total_stock",
        ),
    ).where(InventoryStock.tenant_id == tenant_id)
    if warehouse_id is not None:
        stock_sq = stock_sq.where(
            InventoryStock.warehouse_id == warehouse_id,
        )
    stock_sq = stock_sq.group_by(InventoryStock.product_id).subquery()

    base_conditions = [Product.tenant_id == tenant_id]
    if not include_inactive:
        base_conditions.append(Product.status == "active")
    if category_id is not None:
        base_conditions.append(Product.category_id == category_id)
    elif category and category.strip():
        base_conditions.append(Product.category == category.strip())

    resolved_locale = resolve_category_locale(locale)
    category_translation = aliased(CategoryTranslation)
    category_name = func.coalesce(category_translation.name, Category.name, Product.category)

    # Main query
    stmt = (
        select(
            Product.id,
            Product.code,
            Product.name,
            Product.category_id,
            category_name.label("category"),
            Product.status,
            func.coalesce(stock_sq.c.total_stock, 0).label("current_stock"),
            relevance.label("relevance"),
        )
        .outerjoin(stock_sq, Product.id == stock_sq.c.product_id)
        .outerjoin(
            Category,
            and_(
                Category.id == Product.category_id,
                Category.tenant_id == tenant_id,
            ),
        )
        .outerjoin(
            category_translation,
            and_(
                category_translation.category_id == Category.id,
                category_translation.locale == resolved_locale,
            ),
        )
        .where(*base_conditions)
    )

    def build_broader_conditions():
        return (
            fast_match
            | name_contains_match
            | text_search_match
            | (relevance >= literal(0.35))
        )

    def apply_pagination(s, limit_val, offset_val):
        return s.limit(limit_val).offset(offset_val)

    def apply_order_by(s):
        """Apply user sort; fall back to code for tie-breaking."""
        dir_fn = desc if sort_dir == "desc" else asc
        if sort_by == "name":
            return s.order_by(dir_fn(Product.name), asc(Product.code))
        elif sort_by == "current_stock":
            return s.order_by(dir_fn(text("current_stock")), asc(Product.code))
        elif sort_by == "category":
            return s.order_by(dir_fn(category_name), asc(Product.code))
        elif sort_by == "status":
            return s.order_by(dir_fn(Product.status), asc(Product.code))
        else:
            return s.order_by(dir_fn(Product.code))

    if q:
        # Phase 1: fast B-tree-indexed matches only.
        fast_match = (
            exact_code_match
            | prefix_code_match
            | name_prefix_match
        )
        fast_stmt = apply_pagination(
            select(
                Product.id,
                Product.code,
                Product.name,
                Product.category_id,
                category_name.label("category"),
                Product.status,
                func.coalesce(stock_sq.c.total_stock, 0).label("current_stock"),
                relevance.label("relevance"),
            )
            .outerjoin(stock_sq, Product.id == stock_sq.c.product_id)
            .outerjoin(
                Category,
                and_(
                    Category.id == Product.category_id,
                    Category.tenant_id == tenant_id,
                ),
            )
            .outerjoin(
                category_translation,
                and_(
                    category_translation.category_id == Category.id,
                    category_translation.locale == resolved_locale,
                ),
            )
            .where(*base_conditions)
            .where(fast_match)
            .order_by(relevance.desc(), Product.code),
            limit,
            offset,
        )
        fast_result = await session.execute(apply_order_by(fast_stmt))
        fast_rows = fast_result.all()

        # Phase 2: only compute trigram/tsvector if fast results are insufficient.
        if len(fast_rows) < limit:
            broader_stmt = apply_pagination(
                select(
                    Product.id,
                    Product.code,
                    Product.name,
                    Product.category_id,
                    category_name.label("category"),
                    Product.status,
                    func.coalesce(stock_sq.c.total_stock, 0).label("current_stock"),
                    relevance.label("relevance"),
                )
                .outerjoin(stock_sq, Product.id == stock_sq.c.product_id)
                .outerjoin(
                    Category,
                    and_(
                        Category.id == Product.category_id,
                        Category.tenant_id == tenant_id,
                    ),
                )
                .outerjoin(
                    category_translation,
                    and_(
                        category_translation.category_id == Category.id,
                        category_translation.locale == resolved_locale,
                    ),
                )
                .where(*base_conditions)
                .where(build_broader_conditions()),
                limit,
                offset,
            )
            broader_result = await session.execute(apply_order_by(broader_stmt))
            seen_ids = {row.id for row in fast_rows}
            rows = fast_rows + [
                row for row in broader_result.all() if row.id not in seen_ids
            ]
        else:
            rows = fast_rows

        # Total count: count distinct products matching the broader conditions
        count_stmt = select(func.count(distinct(Product.id))).select_from(
            Product
        ).outerjoin(stock_sq, Product.id == stock_sq.c.product_id).where(*base_conditions).where(
            build_broader_conditions()
        )
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0
    else:
        count_sq = select(
            InventoryStock.product_id,
        ).where(InventoryStock.tenant_id == tenant_id)
        if warehouse_id is not None:
            count_sq = count_sq.where(InventoryStock.warehouse_id == warehouse_id)
        count_sq = count_sq.subquery()
        count_stmt = (
            select(func.count(distinct(Product.id)))
            .select_from(Product)
            .outerjoin(count_sq, Product.id == count_sq.c.product_id)
            .where(*base_conditions)
        )
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        rows_stmt = apply_pagination(
            apply_order_by(stmt),
            limit,
            offset,
        )
        result = await session.execute(rows_stmt)
        rows = result.all()

    serialized = [
        {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "category_id": row.category_id,
            "category": row.category,
            "status": row.status,
            "current_stock": row.current_stock,
            "relevance": float(row.relevance) if row.relevance is not None else 0.0,
        }
        for row in rows
    ]
    return serialized, total


# ── Supplier queries ──────────────────────────────────────────


async def list_suppliers(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    q: str | None = None,
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Supplier], int]:
    """List suppliers with search, active filter, and pagination."""
    where_conditions = [Supplier.tenant_id == tenant_id]

    if active_only:
        where_conditions.append(Supplier.is_active.is_(True))

    stripped = q.strip() if q else ""
    if stripped:
        q_like = stripped.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where_conditions.append(Supplier.name.ilike(f"%{q_like}%", escape="\\"))

    count_stmt = select(func.count(Supplier.id)).where(*where_conditions)
    count_result = await session.execute(count_stmt)
    raw_total = count_result.scalar()

    prefetched_rows: list[Supplier] = []
    if raw_total is None:
        prefetched_rows = cast(list[Supplier], list(count_result.scalars().all()))
    if prefetched_rows:
        return prefetched_rows, len(prefetched_rows)

    stmt = (
        select(Supplier)
        .where(*where_conditions)
        .order_by(Supplier.name)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    suppliers = list(result.scalars().all())
    total = int(raw_total or 0) if raw_total is not None else len(suppliers)
    return suppliers, total


async def get_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> Supplier | None:
    stmt = select(Supplier).where(
        Supplier.id == supplier_id,
        Supplier.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: "SupplierCreate",
) -> Supplier:
    name, contact_email, phone, address, default_lead_time_days = _normalize_supplier_payload(data)

    supplier = Supplier(
        tenant_id=tenant_id,
        name=name,
        contact_email=contact_email,
        phone=phone,
        address=address,
        default_lead_time_days=default_lead_time_days,
        is_active=True,
    )
    session.add(supplier)
    await session.flush()
    return supplier


async def update_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    data: "SupplierUpdate",
) -> Supplier | None:
    supplier = await get_supplier(session, tenant_id, supplier_id)
    if supplier is None:
        return None

    name, contact_email, phone, address, default_lead_time_days = _normalize_supplier_payload(data)
    supplier.name = name
    supplier.contact_email = contact_email
    supplier.phone = phone
    supplier.address = address
    supplier.default_lead_time_days = default_lead_time_days
    await session.flush()
    return supplier


async def set_supplier_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    *,
    is_active: bool,
) -> Supplier | None:
    supplier = await get_supplier(session, tenant_id, supplier_id)
    if supplier is None:
        return None

    supplier.is_active = is_active
    await session.flush()
    return supplier


# ── Supplier order creation ────────────────────────────────────


async def create_supplier_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    supplier_id: uuid.UUID,
    order_date: date,
    expected_arrival_date: date | None,
    lines: list[dict],
    actor_id: str,
) -> dict:
    """Create a new supplier order with line items."""
    # Generate order number
    order_number = f"PO-{utc_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    order = SupplierOrder(
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        order_number=order_number,
        order_date=order_date,
        expected_arrival_date=expected_arrival_date,
        created_by=actor_id,
        status=SupplierOrderStatus.PENDING,
    )
    session.add(order)
    await session.flush()

    for line_data in lines:
        line = SupplierOrderLine(
            order_id=order.id,
            product_id=line_data["product_id"],
            warehouse_id=line_data["warehouse_id"],
            quantity_ordered=line_data["quantity_ordered"],
            unit_price=line_data.get("unit_price"),
            notes=line_data.get("notes"),
        )
        session.add(line)

    await session.flush()

    # Audit log
    audit = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="create_supplier_order",
        entity_type="supplier_order",
        entity_id=str(order.id),
        after_state={
            "order_number": order.order_number,
            "supplier_id": str(supplier_id),
            "status": order.status.value,
            "line_count": len(lines),
        },
        correlation_id=str(order.id),
    )
    session.add(audit)
    await session.flush()

    return await _serialize_order(session, tenant_id, order.id)


# ── Supplier order queries ─────────────────────────────────────


async def _serialize_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
) -> dict | None:
    """Fetch and serialize a supplier order with eager-loaded lines."""
    from sqlalchemy.orm import selectinload

    stmt = (
        select(SupplierOrder)
        .options(selectinload(SupplierOrder.lines))
        .where(
            SupplierOrder.id == order_id,
            SupplierOrder.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        return None

    # Fetch supplier name
    supplier_stmt = select(Supplier.name).where(Supplier.id == order.supplier_id)
    supplier_result = await session.execute(supplier_stmt)
    supplier_name = supplier_result.scalar_one_or_none() or "Unknown"

    return {
        "id": order.id,
        "tenant_id": order.tenant_id,
        "supplier_id": order.supplier_id,
        "supplier_name": supplier_name,
        "order_number": order.order_number,
        "status": order.status.value,
        "order_date": order.order_date,
        "expected_arrival_date": order.expected_arrival_date,
        "received_date": order.received_date,
        "created_by": order.created_by,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "lines": [
            {
                "id": line.id,
                "product_id": line.product_id,
                "warehouse_id": line.warehouse_id,
                "quantity_ordered": line.quantity_ordered,
                "unit_price": getattr(line, "unit_price", None),
                "quantity_received": line.quantity_received,
                "notes": line.notes,
            }
            for line in order.lines
        ],
    }


async def get_supplier_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
) -> dict | None:
    """Fetch supplier order with line items."""
    return await _serialize_order(session, tenant_id, order_id)


async def list_supplier_orders(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status_filter: str | None = None,
    supplier_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List supplier orders with optional filters."""
    from sqlalchemy.orm import selectinload

    base_where = [SupplierOrder.tenant_id == tenant_id]
    if status_filter:
        base_where.append(SupplierOrder.status == SupplierOrderStatus(status_filter))
    if supplier_id:
        base_where.append(SupplierOrder.supplier_id == supplier_id)

    # Count
    count_stmt = select(func.count(SupplierOrder.id)).where(*base_where)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # Fetch with pagination
    stmt = (
        select(SupplierOrder)
        .options(selectinload(SupplierOrder.lines))
        .where(*base_where)
        .order_by(SupplierOrder.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    orders = result.scalars().unique().all()

    # Batch-fetch supplier names
    supplier_ids = {o.supplier_id for o in orders}
    if supplier_ids:
        name_stmt = select(Supplier.id, Supplier.name).where(Supplier.id.in_(supplier_ids))
        name_result = await session.execute(name_stmt)
        supplier_names = {row[0]: row[1] for row in name_result.all()}
    else:
        supplier_names = {}

    items = [
        {
            "id": order.id,
            "supplier_id": order.supplier_id,
            "supplier_name": supplier_names.get(order.supplier_id, "Unknown"),
            "order_number": order.order_number,
            "status": order.status.value,
            "order_date": order.order_date,
            "expected_arrival_date": order.expected_arrival_date,
            "received_date": order.received_date,
            "created_by": order.created_by,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "line_count": len(order.lines),
        }
        for order in orders
    ]

    return items, total


# ── Supplier order receipt (atomic) ────────────────────────────


async def receive_supplier_order(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
    *,
    received_quantities: dict[str, int] | None = None,
    received_date: date | None = None,
    actor_id: str,
) -> dict | None:
    """
    Atomically receive supplier order:
    1. Lock order and inventory rows
    2. Update inventory stock for each line
    3. Create stock adjustments (supplier_delivery)
    4. Resolve reorder alerts if stock restored
    5. Update order status
    """
    from sqlalchemy.orm import selectinload

    if received_quantities is None:
        received_quantities = {}

    if received_date is None:
        received_date = today()

    # Lock and fetch order with lines
    order_stmt = (
        select(SupplierOrder)
        .options(selectinload(SupplierOrder.lines))
        .where(
            SupplierOrder.id == order_id,
            SupplierOrder.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    order_result = await session.execute(order_stmt)
    order = order_result.scalar_one_or_none()

    if order is None:
        return None

    # Idempotency: if already fully received, return current state
    if order.status == SupplierOrderStatus.RECEIVED:
        return await _serialize_order(session, tenant_id, order_id)

    # Cannot receive cancelled orders
    if order.status == SupplierOrderStatus.CANCELLED:
        msg = "Cannot receive a cancelled order"
        raise ValueError(msg)

    # Process each line
    all_fully_received = True
    for line in order.lines:
        remaining_qty = line.quantity_ordered - line.quantity_received
        if remaining_qty <= 0:
            continue

        # Determine quantity to receive for this line
        line_id_str = str(line.id)
        if received_quantities:
            # When explicit quantities provided, only receive specified lines
            if line_id_str not in received_quantities:
                all_fully_received = False
                continue
            receive_qty = received_quantities[line_id_str]
        else:
            # When no quantities specified, receive full remaining for all lines
            receive_qty = remaining_qty

        if receive_qty <= 0:
            all_fully_received = False
            continue

        if receive_qty > remaining_qty:
            msg = (
                f"Cannot receive {receive_qty} units; "
                f"only {remaining_qty} remaining for line {line.id}"
            )
            raise ValueError(msg)

        # 1. Lock and update inventory stock
        stock_stmt = (
            select(InventoryStock)
            .where(
                InventoryStock.tenant_id == tenant_id,
                InventoryStock.product_id == line.product_id,
                InventoryStock.warehouse_id == line.warehouse_id,
            )
            .with_for_update()
        )
        stock_result = await session.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()

        if stock is None:
            stock = InventoryStock(
                tenant_id=tenant_id,
                product_id=line.product_id,
                warehouse_id=line.warehouse_id,
                quantity=0,
                reorder_point=0,
            )
            session.add(stock)
            await session.flush()

        before_qty = stock.quantity
        stock.quantity += receive_qty

        # 2. Record adjustment
        adj = StockAdjustment(
            tenant_id=tenant_id,
            product_id=line.product_id,
            warehouse_id=line.warehouse_id,
            quantity_change=receive_qty,
            reason_code=ReasonCode.SUPPLIER_DELIVERY,
            actor_id=actor_id,
            notes=f"From supplier order {order.order_number}",
        )
        session.add(adj)

        # 3. Emit stock changed event
        await emit(StockChangedEvent(
            tenant_id=tenant_id,
            product_id=line.product_id,
            warehouse_id=line.warehouse_id,
            before_quantity=before_qty,
            after_quantity=stock.quantity,
            reorder_point=stock.reorder_point,
            actor_id=actor_id,
        ), session)

        # 4. Update line
        line.quantity_received += receive_qty

        # 5. Audit log per line
        audit = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="receive_supplier_order_line",
            entity_type="supplier_order_line",
            entity_id=str(line.id),
            before_state={"quantity": before_qty},
            after_state={"quantity": stock.quantity},
            correlation_id=str(order_id),
            notes=f"Received {receive_qty} units; order {order.order_number}",
        )
        session.add(audit)

        # Check if this line is fully received
        if line.quantity_received < line.quantity_ordered:
            all_fully_received = False

    # Update order status
    if all_fully_received:
        order.status = SupplierOrderStatus.RECEIVED
        order.received_date = received_date
    else:
        order.status = SupplierOrderStatus.PARTIALLY_RECEIVED

    await session.flush()
    return await _serialize_order(session, tenant_id, order_id)


# ── Supplier order status update ──────────────────────────────


async def update_supplier_order_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
    *,
    new_status: str,
    actor_id: str,
    notes: str | None = None,
) -> dict | None:
    """Update supplier order status (pending → confirmed → shipped, etc.)."""
    stmt = (
        select(SupplierOrder)
        .where(
            SupplierOrder.id == order_id,
            SupplierOrder.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        return None

    # Validate status transition
    ALLOWED_TRANSITIONS: dict[SupplierOrderStatus, set[SupplierOrderStatus]] = {
        SupplierOrderStatus.PENDING: {SupplierOrderStatus.CONFIRMED, SupplierOrderStatus.CANCELLED},
        SupplierOrderStatus.CONFIRMED: {SupplierOrderStatus.SHIPPED, SupplierOrderStatus.CANCELLED},
        SupplierOrderStatus.SHIPPED: {SupplierOrderStatus.CANCELLED},
    }
    new_status_enum = SupplierOrderStatus(new_status)
    allowed = ALLOWED_TRANSITIONS.get(order.status, set())
    if new_status_enum not in allowed:
        raise ValueError(
            f"Cannot transition from {order.status.value} to {new_status}. "
            f"Allowed: {', '.join(s.value for s in allowed) or 'none'}"
        )

    old_status = order.status.value
    order.status = new_status_enum
    await session.flush()

    # Audit log
    audit = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="update_supplier_order_status",
        entity_type="supplier_order",
        entity_id=str(order_id),
        before_state={"status": old_status},
        after_state={"status": new_status},
        correlation_id=str(order_id),
        notes=notes,
    )
    session.add(audit)
    await session.flush()

    return await _serialize_order(session, tenant_id, order_id)


# ── Stock history ───────────────────────────────────────────────


async def get_stock_history(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    granularity: str = "event",
    _max_range_days: int = 730,
) -> dict:
    """Return stock history for a product+warehouse.

    - ``granularity='event'``: one row per adjustment event
    - ``granularity='daily'``: one row per day, aggregated

    ``running_stock`` at each point is computed by back-calculating the
    initial stock from the current quantity and applying adjustments forward.
    """
    from collections import Counter

    from common.time import utc_now

    def is_reconciliation_apply_adjustment(adjustment: StockAdjustment) -> bool:
        return adjustment.actor_id == "reconciliation-apply"

    # Cap start_date to at most _max_range_days ago to avoid loading huge histories
    effective_start = start_date
    if effective_start is None:
        effective_start = utc_now() - __import__("datetime").timedelta(days=_max_range_days)

    # 1. Get current stock quantity and reorder point
    stock_stmt = select(InventoryStock).where(
        InventoryStock.tenant_id == tenant_id,
        InventoryStock.product_id == product_id,
        InventoryStock.warehouse_id == warehouse_id,
    )
    stock_result = await session.execute(stock_stmt)
    stock = stock_result.scalar_one_or_none()

    current_stock = stock.quantity if stock else 0
    reorder_point = stock.reorder_point if stock else 0
    configured_safety_factor = stock.safety_factor if stock and stock.safety_factor > 0 else 0.5
    configured_lead_time_days = stock.lead_time_days if stock and stock.lead_time_days > 0 else None

    # 2. Fetch adjustments ordered ASC
    adj_where = [
        StockAdjustment.tenant_id == tenant_id,
        StockAdjustment.product_id == product_id,
        StockAdjustment.warehouse_id == warehouse_id,
    ]
    if effective_start:
        adj_where.append(StockAdjustment.created_at >= effective_start)
    if end_date:
        adj_where.append(StockAdjustment.created_at <= end_date)

    adj_stmt = (
        select(StockAdjustment)
        .where(*adj_where)
        .order_by(StockAdjustment.created_at.asc())
    )
    adj_result = await session.execute(adj_stmt)
    adjustments = list(adj_result.scalars().all())

    visible_adjustments = [
        adjustment
        for adjustment in adjustments
        if not is_reconciliation_apply_adjustment(adjustment)
    ]

    total_adjustment = sum(adj.quantity_change for adj in visible_adjustments)
    initial_stock = current_stock - total_adjustment

    # 3. Build running stock
    running = initial_stock
    points: list[dict] = []

    if granularity == "daily":
        # Group by date, sum quantity_change, pick dominant reason_code
        by_date: dict[str, dict] = {}
        for adj in visible_adjustments:
            day_key = adj.created_at.date().isoformat()
            if day_key not in by_date:
                by_date[day_key] = {"quantity_change": 0, "reason_codes": Counter(), "notes": None}
            by_date[day_key]["quantity_change"] += adj.quantity_change
            by_date[day_key]["reason_codes"][adj.reason_code.value] += 1
            if by_date[day_key]["notes"] is None and adj.notes:
                by_date[day_key]["notes"] = adj.notes

        for day_key, info in sorted(by_date.items()):
            running += info["quantity_change"]
            dominant_rc = (
                info["reason_codes"].most_common(1)[0][0]
                if info["reason_codes"]
                else "unknown"
            )
            points.append({
                "date": datetime.fromisoformat(day_key),
                "quantity_change": info["quantity_change"],
                "reason_code": dominant_rc,
                "running_stock": running,
                "notes": info["notes"],
            })
    else:
        # event-level granularity
        for adj in visible_adjustments:
            running += adj.quantity_change
            points.append({
                "date": adj.created_at,
                "quantity_change": adj.quantity_change,
                "reason_code": adj.reason_code.value,
                "running_stock": running,
                "notes": adj.notes,
            })

    # 4. Fetch metadata from reorder point helpers (avg_daily_usage, lead_time, safety_stock)
    try:
        from domains.inventory.reorder_point import (
            get_average_daily_usage,
            get_lead_time_days,
        )

        avg_daily, _mov_count = await get_average_daily_usage(
            session, tenant_id, product_id, warehouse_id, lookback_days=90,
        )
        if configured_lead_time_days is not None:
            lead_time_days = configured_lead_time_days
        else:
            lead_time_days, _lt_source = await get_lead_time_days(
                session, tenant_id, product_id, warehouse_id, lookback_days=180,
            )
        safety_stock = (
            round(avg_daily * configured_safety_factor * lead_time_days, 2)
            if avg_daily and lead_time_days
            else None
        )
    except Exception:
        avg_daily = None
        lead_time_days = None
        safety_stock = None

    return {
        "points": points,
        "current_stock": current_stock,
        "reorder_point": reorder_point,
        "avg_daily_usage": round(avg_daily, 4) if avg_daily else None,
        "lead_time_days": lead_time_days,
        "safety_stock": safety_stock,
    }


# ── Stock settings update ───────────────────────────────────────


async def update_stock_settings(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    stock_id: uuid.UUID,
    *,
    reorder_point: int | None = None,
    safety_factor: float | None = None,
    lead_time_days: int | None = None,
    policy_type: str | None = None,
    target_stock_qty: int | None = None,
    on_order_qty: int | None = None,
    in_transit_qty: int | None = None,
    reserved_qty: int | None = None,
    planning_horizon_days: int | None = None,
    review_cycle_days: int | None = None,
) -> InventoryStock | None:
    """Update replenishment settings for a stock record."""
    stmt = select(InventoryStock).where(
        InventoryStock.id == stock_id,
        InventoryStock.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    stock = result.scalar_one_or_none()
    if stock is None:
        return None

    if reorder_point is not None:
        stock.reorder_point = reorder_point
    if safety_factor is not None:
        stock.safety_factor = safety_factor
    if lead_time_days is not None:
        stock.lead_time_days = lead_time_days
    if policy_type is not None:
        stock.policy_type = policy_type
    if target_stock_qty is not None:
        stock.target_stock_qty = target_stock_qty
    if on_order_qty is not None:
        stock.on_order_qty = on_order_qty
    if in_transit_qty is not None:
        stock.in_transit_qty = in_transit_qty
    if reserved_qty is not None:
        stock.reserved_qty = reserved_qty
    if planning_horizon_days is not None:
        stock.planning_horizon_days = planning_horizon_days
    if review_cycle_days is not None:
        stock.review_cycle_days = review_cycle_days

    await session.flush()
    return stock


# ── Monthly demand ──────────────────────────────────────────────


async def get_monthly_demand(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    months: int = 12,
    include_current_month: bool = True,
) -> dict:
    """Return rolling monthly demand totals for SALES_RESERVATION.

    Uses Asia/Taipei timezone for date truncation to match the business timezone.
    """
    current_month_start = utc_now().date().replace(day=1)
    end_month = (
        current_month_start
        if include_current_month
        else _shift_months(current_month_start, -1)
    )
    requested_months = _iter_month_starts(_shift_months(end_month, -(months - 1)), end_month)
    requested_month_set = set(requested_months)

    # Convert to Taiwan timezone before truncating month, so month boundaries align with
    # Taiwan calendar months (UTC+8). Without this conversion, data stored with end-of-
    # month UTC timestamps (e.g., 2026-03-31 16:00 UTC = 2026-04-01 00:00 Taiwan) gets
    # grouped into the wrong month.
    taiwan_month_expr = func.date_trunc(
        "month",
        func.timezone("Asia/Taipei", StockAdjustment.created_at),
    ).label("month")

    stmt = (
        select(
            taiwan_month_expr,
            func.sum(StockAdjustment.quantity_change).label("total_qty"),
        )
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
            StockAdjustment.reason_code == ReasonCode.SALES_RESERVATION,
        )
        .group_by(taiwan_month_expr)
        .order_by(taiwan_month_expr)
    )
    result = await session.execute(stmt)
    rows = result.all()

    items = [
        {
            "month": row.month.strftime("%Y-%m"),
            "total_qty": int(abs(_quantize_quantity(row.total_qty or 0))),
        }
        for row in rows
        if (row.month.date() if hasattr(row.month, "date") else row.month) in requested_month_set
    ]
    total = sum(item["total_qty"] for item in items)
    return {"items": items, "total": total}


async def get_planning_support(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    months: int = 12,
    include_current_month: bool = True,
) -> dict | None:
    """Return planning support metrics for a product.

    Calculates monthly sales quantities directly from stock_adjustment table
    using Taiwan timezone (Asia/Taipei), consistent with the business timezone.
    This replaces the previous approach that relied on a pre-aggregated
    SalesMonthly table, ensuring data is always available.
    """
    current_month_start = utc_now().date().replace(day=1)
    end_month = (
        current_month_start
        if include_current_month
        else _shift_months(current_month_start, -1)
    )
    start_month = _shift_months(end_month, -(months - 1))
    requested_months = _iter_month_starts(start_month, end_month)
    includes_current_month = include_current_month and current_month_start in requested_months

    # Calculate monthly quantities directly from stock_adjustment using Taiwan timezone.
    # This is the same approach used by get_monthly_demand for consistency.
    taiwan_month_expr = func.date_trunc(
        "month",
        func.timezone("Asia/Taipei", StockAdjustment.created_at),
    ).label("month")

    # Get all months in the window with their totals
    stmt = (
        select(
            taiwan_month_expr,
            func.sum(StockAdjustment.quantity_change).label("total_qty"),
        )
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
            StockAdjustment.reason_code == ReasonCode.SALES_RESERVATION,
        )
        .group_by(taiwan_month_expr)
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Build a dict of month_start -> quantity (absolute value for display)
    monthly_quantities: dict[date, Decimal] = {}
    for row in rows:
        month_start = row.month.date() if hasattr(row.month, 'date') else row.month
        if start_month <= month_start <= end_month:
            # quantity_change is negative for sales, take absolute value for display
            monthly_quantities[month_start] = abs(_quantize_quantity(row.total_qty or 0))

    product_exists = await session.scalar(
        select(Product.id).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
        )
    )
    if product_exists is None:
        return None

    stock_context_row = (
        await session.execute(
            select(
                func.coalesce(func.sum(InventoryStock.reorder_point), 0).label("reorder_point"),
                func.coalesce(func.sum(InventoryStock.on_order_qty), 0).label("on_order_qty"),
                func.coalesce(func.sum(InventoryStock.in_transit_qty), 0).label("in_transit_qty"),
                func.coalesce(func.sum(InventoryStock.reserved_qty), 0).label("reserved_qty"),
            ).where(
                InventoryStock.tenant_id == tenant_id,
                InventoryStock.product_id == product_id,
            )
        )
    ).one()

    current_month_live_quantity = None
    if includes_current_month:
        current_month_live_quantity = _quantize_quantity(
            monthly_quantities.get(current_month_start, _ZERO_QUANTITY),
        )

    if not monthly_quantities:
        return {
            "product_id": product_id,
            "items": [],
            "avg_monthly_quantity": None,
            "peak_monthly_quantity": None,
            "low_monthly_quantity": None,
            "seasonality_index": None,
            "above_average_months": [],
            "history_months_used": 0,
            "current_month_live_quantity": current_month_live_quantity,
            "reorder_point": int(stock_context_row.reorder_point or 0),
            "on_order_qty": int(stock_context_row.on_order_qty or 0),
            "in_transit_qty": int(stock_context_row.in_transit_qty or 0),
            "reserved_qty": int(stock_context_row.reserved_qty or 0),
            "data_basis": "no_history",
            "advisory_only": True,
            "data_gap": True,
            "window": {
                "start_month": _format_month(start_month),
                "end_month": _format_month(end_month),
                "includes_current_month": includes_current_month,
                "is_partial": includes_current_month,
            },
        }

    items: list[dict[str, object]] = []
    for month_start in requested_months:
        items.append(
            {
                "month": _format_month(month_start),
                "quantity": _quantize_quantity(
                    monthly_quantities.get(month_start, _ZERO_QUANTITY)
                ),
                "source": (
                    "live"
                    if month_start == current_month_start and includes_current_month
                    else "aggregated"
                ),
            }
        )

    quantities = [item["quantity"] for item in items]
    total_quantity = sum(quantities, start=_ZERO_QUANTITY)
    avg_monthly_quantity = _quantize_quantity(total_quantity / Decimal(len(items)))
    peak_monthly_quantity = max(quantities)
    low_monthly_quantity = min(quantities)
    seasonality_index = (
        _quantize_index(peak_monthly_quantity / avg_monthly_quantity)
        if avg_monthly_quantity > 0
        else Decimal("0.000")
    )
    above_average_months = [
        str(item["month"])
        for item in items
        if item["quantity"] > avg_monthly_quantity
    ]

    if includes_current_month and start_month == current_month_start:
        data_basis = "live_current_month_only"
    elif includes_current_month:
        data_basis = "aggregated_plus_live_current_month"
    else:
        data_basis = "aggregated_only"

    return {
        "product_id": product_id,
        "items": items,
        "avg_monthly_quantity": avg_monthly_quantity,
        "peak_monthly_quantity": peak_monthly_quantity,
        "low_monthly_quantity": low_monthly_quantity,
        "seasonality_index": seasonality_index,
        "above_average_months": above_average_months,
        "history_months_used": len(items),
        "current_month_live_quantity": current_month_live_quantity,
        "reorder_point": int(stock_context_row.reorder_point or 0),
        "on_order_qty": int(stock_context_row.on_order_qty or 0),
        "in_transit_qty": int(stock_context_row.in_transit_qty or 0),
        "reserved_qty": int(stock_context_row.reserved_qty or 0),
        "data_basis": data_basis,
        "advisory_only": True,
        "data_gap": False,
        "window": {
            "start_month": _format_month(start_month),
            "end_month": _format_month(end_month),
            "includes_current_month": includes_current_month,
            "is_partial": includes_current_month,
        },
    }


# ── Sales history ────────────────────────────────────────────────


async def get_sales_history(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return paginated sales history (all reason codes) for a product."""
    count_stmt = select(func.count(StockAdjustment.id)).where(
        StockAdjustment.tenant_id == tenant_id,
        StockAdjustment.product_id == product_id,
    )
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = (
        select(StockAdjustment)
        .where(
            StockAdjustment.tenant_id == tenant_id,
            StockAdjustment.product_id == product_id,
        )
        .order_by(StockAdjustment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    adjustments = result.scalars().all()

    items = [
        {
            "date": adj.created_at,
            "quantity_change": adj.quantity_change,
            "reason_code": adj.reason_code.value,
            "actor_id": adj.actor_id,
        }
        for adj in adjustments
    ]
    return {"items": items, "total": total}


# ── Top customer ─────────────────────────────────────────────────


async def get_top_customer(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> dict | None:
    """Return the customer who has ordered the most of this product (by quantity)."""
    from common.models.order import Order
    from common.models.order_line import OrderLine
    from domains.customers.models import Customer

    stmt = (
        select(
            Customer.id.label("customer_id"),
            Customer.company_name.label("customer_name"),
            func.sum(OrderLine.quantity).label("total_qty"),
        )
        .join(Order, Order.id == OrderLine.order_id)
        .join(Customer, Customer.id == Order.customer_id)
        .where(
            Order.tenant_id == tenant_id,
            OrderLine.product_id == product_id,
        )
        .group_by(Customer.id, Customer.company_name)
        .order_by(func.sum(OrderLine.quantity).desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()

    if row is None:
        return None
    return {
        "customer_id": row.customer_id,
        "customer_name": row.customer_name,
        "total_qty": int(row.total_qty or 0),
    }


async def _validate_product_supplier_scope(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> Supplier:
    product = await session.get(Product, product_id)
    if product is None or product.tenant_id != tenant_id:
        raise ValidationError([
            {"loc": ["product_id"], "msg": "Product not found", "type": "value_error"},
        ])

    supplier = await session.get(Supplier, supplier_id)
    if supplier is None or supplier.tenant_id != tenant_id:
        raise ValidationError([
            {"loc": ["supplier_id"], "msg": "Supplier not found", "type": "value_error"},
        ])
    return supplier


def _serialize_product_supplier_association(
    association: ProductSupplier,
    supplier_name: str,
) -> dict[str, Any]:
    return {
        "id": association.id,
        "product_id": association.product_id,
        "supplier_id": association.supplier_id,
        "supplier_name": supplier_name,
        "unit_cost": float(association.unit_cost) if association.unit_cost is not None else None,
        "lead_time_days": association.lead_time_days,
        "is_default": association.is_default,
        "created_at": association.created_at,
        "updated_at": association.updated_at,
    }


async def list_product_suppliers(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> list[dict[str, Any]]:
    stmt = (
        select(ProductSupplier, Supplier.name)
        .join(
            Supplier,
            and_(
                Supplier.id == ProductSupplier.supplier_id,
                Supplier.tenant_id == tenant_id,
            ),
        )
        .where(
            ProductSupplier.tenant_id == tenant_id,
            ProductSupplier.product_id == product_id,
        )
        .order_by(desc(ProductSupplier.is_default), asc(Supplier.name))
    )
    result = await session.execute(stmt)
    return [
        _serialize_product_supplier_association(association, supplier_name)
        for association, supplier_name in result.all()
    ]


async def create_product_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    supplier_id: uuid.UUID,
    unit_cost: float | None = None,
    lead_time_days: int | None = None,
    is_default: bool = False,
) -> dict[str, Any]:
    supplier = await _validate_product_supplier_scope(session, tenant_id, product_id, supplier_id)

    existing_stmt = select(ProductSupplier).where(
        ProductSupplier.tenant_id == tenant_id,
        ProductSupplier.product_id == product_id,
        ProductSupplier.supplier_id == supplier_id,
    )
    existing_result = await session.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        raise ValidationError([
            {
                "loc": ["supplier_id"],
                "msg": "Supplier association already exists for this product",
                "type": "value_error",
            }
        ])

    if is_default:
        default_result = await session.execute(
            select(ProductSupplier).where(
                ProductSupplier.tenant_id == tenant_id,
                ProductSupplier.product_id == product_id,
                ProductSupplier.is_default.is_(True),
            )
        )
        for association in default_result.scalars().all():
            association.is_default = False

    association = ProductSupplier(
        tenant_id=tenant_id,
        product_id=product_id,
        supplier_id=supplier_id,
        unit_cost=(Decimal(str(unit_cost)) if unit_cost is not None else None),
        lead_time_days=lead_time_days,
        is_default=is_default,
    )
    session.add(association)
    await session.flush()

    return _serialize_product_supplier_association(association, supplier.name)


async def update_product_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    supplier_id: uuid.UUID,
    *,
    unit_cost: float | None = None,
    lead_time_days: int | None = None,
    is_default: bool | None = None,
) -> dict[str, Any] | None:
    stmt = (
        select(ProductSupplier, Supplier.name)
        .join(
            Supplier,
            and_(Supplier.id == ProductSupplier.supplier_id, Supplier.tenant_id == tenant_id),
        )
        .where(
            ProductSupplier.tenant_id == tenant_id,
            ProductSupplier.product_id == product_id,
            ProductSupplier.supplier_id == supplier_id,
        )
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None

    association, supplier_name = row

    if is_default:
        default_result = await session.execute(
            select(ProductSupplier).where(
                ProductSupplier.tenant_id == tenant_id,
                ProductSupplier.product_id == product_id,
                ProductSupplier.is_default.is_(True),
                ProductSupplier.supplier_id != supplier_id,
            )
        )
        for assoc in default_result.scalars().all():
            assoc.is_default = False

    if unit_cost is not None:
        association.unit_cost = Decimal(str(unit_cost))
    if lead_time_days is not None:
        association.lead_time_days = lead_time_days
    if is_default is not None:
        association.is_default = is_default

    await session.flush()
    return _serialize_product_supplier_association(association, supplier_name)


async def delete_product_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> bool:
    stmt = select(ProductSupplier).where(
        ProductSupplier.tenant_id == tenant_id,
        ProductSupplier.product_id == product_id,
        ProductSupplier.supplier_id == supplier_id,
    )
    result = await session.execute(stmt)
    association = result.scalar_one_or_none()
    if association is None:
        return False

    await session.delete(association)
    await session.flush()
    return True


# ── Product supplier ──────────────────────────────────────────────


async def get_product_supplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> dict | None:
    """Return the explicit default supplier for a product, else most-recent fallback.

    Explicit product-supplier associations are the primary source of truth.
    When no explicit default exists, falls back to the most-recent supplier
    heuristic based on supplier orders and invoices.
    """
    explicit_stmt = (
        select(
            Supplier.id,
            Supplier.name,
            ProductSupplier.unit_cost,
            func.coalesce(
                ProductSupplier.lead_time_days,
                Supplier.default_lead_time_days,
            ).label("effective_lead_time_days"),
        )
        .join(
            Supplier,
            and_(
                Supplier.id == ProductSupplier.supplier_id,
                Supplier.tenant_id == tenant_id,
            ),
        )
        .where(
            ProductSupplier.tenant_id == tenant_id,
            ProductSupplier.product_id == product_id,
            ProductSupplier.is_default.is_(True),
        )
        .limit(1)
    )
    explicit_row = await _load_product_supplier_explicit_row(session, explicit_stmt)

    if explicit_row is not None:
        return {
            "supplier_id": explicit_row.id,
            "name": explicit_row.name,
            "unit_cost": (
                float(explicit_row.unit_cost) if explicit_row.unit_cost is not None else None
            ),
            "default_lead_time_days": explicit_row.effective_lead_time_days,
        }

    supplier_sources = (
        select(
            SupplierOrder.supplier_id.label("supplier_id"),
            SupplierOrder.received_date.label("effective_date"),
            SupplierOrderLine.unit_price.label("unit_cost"),
            literal(0).label("source_priority"),
        )
        .join(SupplierOrder, SupplierOrder.id == SupplierOrderLine.order_id)
        .where(
            SupplierOrder.tenant_id == tenant_id,
            SupplierOrderLine.product_id == product_id,
            SupplierOrder.received_date.isnot(None),
        )
        .union_all(
            select(
                SupplierInvoice.supplier_id.label("supplier_id"),
                SupplierInvoice.invoice_date.label("effective_date"),
                SupplierInvoiceLine.unit_price.label("unit_cost"),
                literal(1).label("source_priority"),
            )
            .join(
                SupplierInvoice,
                SupplierInvoice.id == SupplierInvoiceLine.supplier_invoice_id,
            )
            .where(
                SupplierInvoice.tenant_id == tenant_id,
                SupplierInvoiceLine.product_id == product_id,
                SupplierInvoiceLine.unit_price.isnot(None),
            )
        )
        .subquery()
    )

    stmt = (
        select(
            Supplier.id,
            Supplier.name,
            Supplier.default_lead_time_days,
            supplier_sources.c.unit_cost,
        )
        .join(supplier_sources, Supplier.id == supplier_sources.c.supplier_id)
        .where(Supplier.tenant_id == tenant_id)
        .order_by(
            supplier_sources.c.effective_date.desc(),
            supplier_sources.c.source_priority.desc(),
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()

    if row is None:
        return None

    return {
        "supplier_id": row.id,
        "name": row.name,
        "unit_cost": float(row.unit_cost) if row.unit_cost is not None else None,
        "default_lead_time_days": row.default_lead_time_days,
    }


# ── Product audit log ─────────────────────────────────────────


async def get_product_audit_log(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Fetch audit log entries for a product.

    Returns entries for both inventory_stock field changes
    (reorder_point, safety_factor, lead_time_days) and product status changes.
    Each field that changed becomes a separate entry.
    """
    # Subquery: all inventory_stock ids for this product
    stock_ids_sq = (
        select(InventoryStock.id)
        .where(
            InventoryStock.tenant_id == tenant_id,
            InventoryStock.product_id == product_id,
        )
        .subquery()
    )

    # Query audit_log for inventory_stock field changes
    # or product status changes, unioned and ordered by created_at DESC
    stock_logs = (
        select(
            AuditLog.id,
            AuditLog.created_at,
            AuditLog.actor_id,
            AuditLog.before_state,
            AuditLog.after_state,
            AuditLog.entity_type,
        )
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.entity_type == "inventory_stock",
            AuditLog.entity_id.in_(select(stock_ids_sq)),
        )
    )

    product_logs = (
        select(
            AuditLog.id,
            AuditLog.created_at,
            AuditLog.actor_id,
            AuditLog.before_state,
            AuditLog.after_state,
            AuditLog.entity_type,
        )
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.entity_type == "product",
            AuditLog.entity_id == str(product_id),
        )
    )

    # Count total before pagination
    all_union = stock_logs.union(product_logs).subquery()
    count_stmt = select(func.count()).select_from(all_union)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # Fetch with LIMIT/OFFSET ordered by created_at DESC
    fetch_stmt = (
        select(
            AuditLog.id,
            AuditLog.created_at,
            AuditLog.actor_id,
            AuditLog.before_state,
            AuditLog.after_state,
            AuditLog.entity_type,
        )
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.entity_type.in_(["inventory_stock", "product"]),
            (
                AuditLog.entity_type == "inventory_stock"
                & AuditLog.entity_id.in_(select(stock_ids_sq))
            )
            | (AuditLog.entity_type == "product" & AuditLog.entity_id == str(product_id)),
        )
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(fetch_stmt)
    rows = result.all()

    items = []
    for row in rows:
        before = row.before_state or {}
        after = row.after_state or {}

        if row.entity_type == "inventory_stock":
            # before_state/after_state contain {reorder_point, safety_factor, lead_time_days, ...}
            # Create one entry per changed field
            for field in ("reorder_point", "safety_factor", "lead_time_days"):
                old_val = before.get(field)
                new_val = after.get(field)
                if old_val is not None or new_val is not None:
                    items.append(
                        {
                            "id": row.id,
                            "created_at": row.created_at,
                            "actor_id": row.actor_id,
                            "field": field,
                            "old_value": str(old_val) if old_val is not None else None,
                            "new_value": str(new_val) if new_val is not None else None,
                        }
                    )
        elif row.entity_type == "product":
            # before_state/after_state contain {status, ...}
            old_status = before.get("status")
            new_status = after.get("status")
            if old_status is not None or new_status is not None:
                items.append(
                    {
                        "id": row.id,
                        "created_at": row.created_at,
                        "actor_id": row.actor_id,
                        "field": "status",
                        "old_value": str(old_status) if old_status is not None else None,
                        "new_value": str(new_status) if new_status is not None else None,
                    }
                )

    # Sort combined items by created_at DESC
    items.sort(key=lambda x: x["created_at"], reverse=True)

    return {"items": items, "total": total}
