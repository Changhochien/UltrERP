"""Product queries — get_product_detail, search_products, audit log."""

from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import and_, asc, case, desc, distinct, func, literal, select, text
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.category import Category, CategoryTranslation
from common.models.inventory_stock import InventoryStock
from common.models.product import Product
from common.models.stock_adjustment import StockAdjustment
from common.models.warehouse import Warehouse
from domains.inventory._product_audit_support import get_product_audit_log

DEFAULT_CATEGORY_LOCALE = "en"
ZH_HANT_LOCALE = "zh-Hant"
SUPPORTED_CATEGORY_LOCALES: tuple[str, ...] = ("en", "zh-Hant")
_VALUATION_AMOUNT_QUANT = Decimal("0.0001")


def _quantize_valuation_amount(value: Decimal | int | float | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(_VALUATION_AMOUNT_QUANT, rounding=ROUND_HALF_UP)


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


