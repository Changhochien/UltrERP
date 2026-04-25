"""Master import helpers for canonical legacy import flows."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import AsyncIterable, AsyncIterator, Sequence, cast

from domains.legacy_import.canonical_common import (
    _as_decimal,
    _as_int,
    _as_text,
    _compact_snapshot,
    _normalized_business_number,
)
from domains.legacy_import.canonical_persistence import (
    PendingLineageResolution,
    _flush_lineage_resolutions,
)
from domains.legacy_import.canonical_readers import _iter_normalized_parties
from domains.legacy_import.mapping import UNKNOWN_PRODUCT_CODE
from domains.legacy_import.normalization import deterministic_legacy_uuid
from domains.legacy_import.shared import execute_many


def _tenant_scoped_uuid(tenant_id: uuid.UUID, kind: str, *parts: str) -> uuid.UUID:
    return deterministic_legacy_uuid(kind, str(tenant_id), *parts)


async def _iter_buffered_rows(
    rows: Sequence[dict[str, object]],
) -> AsyncIterator[dict[str, object]]:
    for row in rows:
        yield row


async def _partition_normalized_parties(
    connection,
    schema_name: str,
    batch_id: str,
    tenant_id: uuid.UUID,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    customer_rows: list[dict[str, object]] = []
    supplier_rows: list[dict[str, object]] = []
    async for row in _iter_normalized_parties(connection, schema_name, batch_id, tenant_id):
        role = _as_text(row.get("role"))
        if role == "customer":
            customer_rows.append(row)
        elif role == "supplier":
            supplier_rows.append(row)
    return customer_rows, supplier_rows


def _build_party_master_snapshot(row: dict[str, object]) -> dict[str, object]:
    return _compact_snapshot(
        {
            "legacy_code": _as_text(row.get("legacy_code")),
            "role": _as_text(row.get("role")),
            "company_name": _as_text(row.get("company_name")),
            "short_name": _as_text(row.get("short_name")),
            "tax_id": _as_text(row.get("tax_id")),
            "full_address": _as_text(row.get("full_address")),
            "address": _as_text(row.get("address")),
            "phone": _as_text(row.get("phone")),
            "email": _as_text(row.get("email")),
            "contact_person": _as_text(row.get("contact_person")),
            "source_table": _as_text(row.get("source_table")),
            "source_row_number": _as_int(row.get("source_row_number")),
        }
    )


def _build_product_master_snapshot(row: dict[str, object]) -> dict[str, object]:
    return _compact_snapshot(
        {
            "legacy_code": _as_text(row.get("legacy_code")),
            "name": _as_text(row.get("name")),
            "category": _as_text(row.get("category")),
            "legacy_category": _as_text(row.get("legacy_category")),
            "stock_kind": _as_text(row.get("stock_kind")),
            "category_source": _as_text(row.get("category_source")),
            "category_rule_id": _as_text(row.get("category_rule_id")),
            "category_confidence": _as_text(row.get("category_confidence")),
            "description": _as_text(row.get("description")),
            "unit": _as_text(row.get("unit")),
            "status": _as_text(row.get("status")),
            "source_table": _as_text(row.get("source_table")),
            "source_row_number": _as_int(row.get("source_row_number")),
        }
    )


async def _load_category_cache(
    connection,
    tenant_id: uuid.UUID,
) -> dict[str, tuple[uuid.UUID, str]]:
    rows = await connection.fetch(
        """
		SELECT id, name
		FROM category
		WHERE tenant_id = $1
		""",
        tenant_id,
    )
    cache: dict[str, tuple[uuid.UUID, str]] = {}
    for row in rows:
        category_id = cast(uuid.UUID, row["id"])
        category_name = _as_text(row["name"])
        if not category_name:
            continue
        cache[category_name.casefold()] = (category_id, category_name)
    return cache


async def _ensure_product_category(
    connection,
    tenant_id: uuid.UUID,
    category_name: str | None,
    *,
    category_cache: dict[str, tuple[uuid.UUID, str]],
    pending_translation_rows: list[tuple[object, ...]],
) -> tuple[uuid.UUID | None, str | None]:
    normalized_name = _as_text(category_name)
    if not normalized_name:
        return None, None

    cache_key = normalized_name.casefold()
    cached = category_cache.get(cache_key)
    if cached is not None:
        return cached

    category_row = await connection.fetchrow(
        """
		INSERT INTO category (
			id,
			tenant_id,
			name,
			is_active,
			created_at,
			updated_at
		)
		VALUES ($1::uuid, $2::uuid, $3::varchar, TRUE, NOW(), NOW())
		ON CONFLICT (tenant_id, name) DO UPDATE SET
			is_active = TRUE,
			updated_at = NOW()
		RETURNING id, name
		""",
        _tenant_scoped_uuid(tenant_id, "category", cache_key),
        tenant_id,
        normalized_name,
    )
    resolved_category_id = cast(uuid.UUID, category_row["id"])
    resolved_category_name = _as_text(category_row["name"])

    pending_translation_rows.append(
        (
            _tenant_scoped_uuid(tenant_id, "category-translation", str(resolved_category_id), "en"),
            resolved_category_id,
            resolved_category_name,
        )
    )

    category_cache[cache_key] = (resolved_category_id, resolved_category_name)
    return resolved_category_id, resolved_category_name


async def _prime_product_category_cache(
    connection,
    tenant_id: uuid.UUID,
    product_rows: Sequence[dict[str, object]],
    *,
    category_cache: dict[str, tuple[uuid.UUID, str]],
) -> dict[str, tuple[uuid.UUID, str]]:
    missing_category_names: list[tuple[str, str]] = []
    seen_cache_keys: set[str] = set()
    for row in product_rows:
        normalized_name = _as_text(row.get("category"))
        if not normalized_name:
            continue
        cache_key = normalized_name.casefold()
        if cache_key in category_cache or cache_key in seen_cache_keys:
            continue
        seen_cache_keys.add(cache_key)
        missing_category_names.append((cache_key, normalized_name))

    if not missing_category_names:
        return category_cache

    await execute_many(
        connection,
        """
			INSERT INTO category (
				id,
				tenant_id,
				name,
				is_active,
				created_at,
				updated_at
			)
			VALUES ($1::uuid, $2::uuid, $3::varchar, TRUE, NOW(), NOW())
			ON CONFLICT (tenant_id, name) DO UPDATE SET
				is_active = TRUE,
				updated_at = NOW()
			""",
        [
            (
                _tenant_scoped_uuid(tenant_id, "category", cache_key),
                tenant_id,
                category_name,
            )
            for cache_key, category_name in missing_category_names
        ],
    )

    refreshed_cache = await _load_category_cache(connection, tenant_id)
    translation_rows: list[tuple[object, ...]] = []
    for cache_key, category_name in missing_category_names:
        resolved_category = refreshed_cache.get(cache_key)
        if resolved_category is None:
            raise ValueError(f"Category cache missing row after upsert for {category_name}")
        translation_rows.append(
            (
                _tenant_scoped_uuid(
                    tenant_id,
                    "category-translation",
                    str(resolved_category[0]),
                    "en",
                ),
                resolved_category[0],
                resolved_category[1],
            )
        )

    await execute_many(
        connection,
        """
			INSERT INTO category_translation (
				id,
				category_id,
				locale,
				name
			)
			VALUES ($1::uuid, $2::uuid, 'en', $3::varchar)
			ON CONFLICT (category_id, locale) DO UPDATE SET
				name = EXCLUDED.name
			""",
        translation_rows,
    )
    return refreshed_cache


async def _import_customers(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    party_rows: AsyncIterable[dict[str, object]],
) -> tuple[int, int, dict[str, uuid.UUID], dict[str, str]]:
    count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    customer_by_code: dict[str, uuid.UUID] = {}
    business_number_by_code: dict[str, str] = {}
    async for row in party_rows:
        if _as_text(row.get("role")) != "customer":
            continue
        legacy_code = _as_text(row.get("legacy_code"))
        customer_id = _tenant_scoped_uuid(tenant_id, "party", "customer", legacy_code)
        business_number = _normalized_business_number(row.get("tax_id"), legacy_code)
        company_name = _as_text(row.get("company_name")) or legacy_code
        contact_name = (
            _as_text(row.get("contact_person"))
            or _as_text(row.get("company_name"))
            or legacy_code
        )
        contact_phone = _as_text(row.get("phone")) or "N/A"
        contact_email = _as_text(row.get("email")) or "N/A"
        billing_address = _as_text(row.get("address")) or _as_text(row.get("full_address")) or "N/A"
        legacy_master_snapshot = _build_party_master_snapshot(row)
        if contact_phone and len(contact_phone) > 30:
            contact_phone = contact_phone[:30]
        actual_row = await connection.fetchrow(
            """
			INSERT INTO customers (
				id,
				tenant_id,
				company_name,
				normalized_business_number,
				billing_address,
				contact_name,
				contact_phone,
				contact_email,
				credit_limit,
				status,
                customer_type,
                legacy_master_snapshot,
				version,
				created_at,
				updated_at
			)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::json, 1, NOW(), NOW())
			ON CONFLICT (tenant_id, normalized_business_number) DO UPDATE SET
				company_name = EXCLUDED.company_name,
				billing_address = EXCLUDED.billing_address,
				contact_name = EXCLUDED.contact_name,
				contact_phone = EXCLUDED.contact_phone,
				contact_email = EXCLUDED.contact_email,
				status = EXCLUDED.status,
                customer_type = CASE
                    WHEN EXCLUDED.customer_type = 'unknown' THEN customers.customer_type
                    ELSE EXCLUDED.customer_type
                END,
                legacy_master_snapshot = EXCLUDED.legacy_master_snapshot,
				updated_at = NOW()
			RETURNING id
			""",
            customer_id,
            tenant_id,
            company_name,
            business_number,
            billing_address,
            contact_name,
            contact_phone,
            contact_email,
            Decimal("0.00"),
            "active",
            _as_text(row.get("customer_type")) or "unknown",
            json.dumps(legacy_master_snapshot),
        )
        if actual_row is None:
            raise ValueError(
                f"No customer found for BN {business_number} after upsert RETURNING id"
            )
        actual_customer_id = actual_row["id"]
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="customers",
                canonical_id=actual_customer_id,
                source_table=_as_text(row.get("source_table")) or "tbscust",
                source_identifier=legacy_code,
                source_row_number=_as_int(row.get("source_row_number")),
            )
        )
        customer_by_code[legacy_code] = actual_customer_id
        business_number_by_code[legacy_code] = business_number
        count += 1
        lineage_count += 1
    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return count, lineage_count, customer_by_code, business_number_by_code


async def _import_suppliers(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    party_rows: AsyncIterable[dict[str, object]],
) -> tuple[int, int, dict[str, uuid.UUID]]:
    count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    supplier_by_code: dict[str, uuid.UUID] = {}
    async for row in party_rows:
        if _as_text(row.get("role")) != "supplier":
            continue
        legacy_code = _as_text(row.get("legacy_code"))
        supplier_id = _tenant_scoped_uuid(tenant_id, "party", "supplier", legacy_code)
        legacy_master_snapshot = _build_party_master_snapshot(row)
        await connection.execute(
            """
			INSERT INTO supplier (
				id,
				tenant_id,
				name,
				contact_email,
				phone,
				address,
                legacy_master_snapshot,
				default_lead_time_days,
				is_active,
				created_at
			)
            VALUES ($1, $2, $3, $4, $5, $6, $7::json, NULL, TRUE, NOW())
			ON CONFLICT (id) DO UPDATE SET
				name = EXCLUDED.name,
				contact_email = EXCLUDED.contact_email,
				phone = EXCLUDED.phone,
				address = EXCLUDED.address,
                legacy_master_snapshot = EXCLUDED.legacy_master_snapshot,
				default_lead_time_days = EXCLUDED.default_lead_time_days,
				is_active = EXCLUDED.is_active
			""",
            supplier_id,
            tenant_id,
            _as_text(row.get("company_name")) or legacy_code,
            _as_text(row.get("email")) or None,
            _as_text(row.get("phone")) or None,
            _as_text(row.get("address")) or _as_text(row.get("full_address")) or None,
            json.dumps(legacy_master_snapshot),
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="supplier",
                canonical_id=supplier_id,
                source_table=_as_text(row.get("source_table")) or "tbscust",
                source_identifier=legacy_code,
                source_row_number=_as_int(row.get("source_row_number")),
            )
        )
        supplier_by_code[legacy_code] = supplier_id
        count += 1
        lineage_count += 1
    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return count, lineage_count, supplier_by_code


async def _import_products(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    product_rows: AsyncIterable[dict[str, object]],
) -> tuple[int, int, dict[str, uuid.UUID], dict[str, dict[str, str | None]]]:
    count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    category_translation_rows: list[tuple[object, ...]] = []
    product_upsert_rows: list[tuple[object, ...]] = []
    product_by_code: dict[str, uuid.UUID] = {}
    product_snapshot_by_code: dict[str, dict[str, str | None]] = {}
    buffered_product_rows = [row async for row in product_rows]
    if not any(
        _as_text(row.get("legacy_code")) == UNKNOWN_PRODUCT_CODE for row in buffered_product_rows
    ):
        buffered_product_rows.append(
            {
                "legacy_code": UNKNOWN_PRODUCT_CODE,
                "name": "Unknown Product",
                "category": None,
                "unit": "unknown",
                "status": "placeholder",
                "source_table": "product_code_mapping",
                "source_row_number": 0,
            }
        )

    category_cache = await _load_category_cache(connection, tenant_id)
    category_cache = await _prime_product_category_cache(
        connection,
        tenant_id,
        buffered_product_rows,
        category_cache=category_cache,
    )

    async def _upsert_product_row(row: dict[str, object]) -> None:
        nonlocal count, lineage_count
        legacy_code = _as_text(row.get("legacy_code"))
        product_id = _tenant_scoped_uuid(tenant_id, "product", legacy_code)
        legacy_master_snapshot = _build_product_master_snapshot(row)
        product_name = _as_text(row.get("name")) or legacy_code
        product_category_id, product_category = await _ensure_product_category(
            connection,
            tenant_id,
            _as_text(row.get("category")) or None,
            category_cache=category_cache,
            pending_translation_rows=category_translation_rows,
        )
        status = (
            "inactive"
            if legacy_code == UNKNOWN_PRODUCT_CODE
            else (
                "active"
                if _as_text(row.get("status")) in {"A", "ACTIVE", "placeholder", "PLACEHOLDER"}
                else "inactive"
            )
        )
        product_upsert_rows.append(
            (
                product_id,
                tenant_id,
                legacy_code,
                product_name,
                product_category,
                product_category_id,
                _as_text(row.get("description")) if row.get("description") else None,
                _as_text(row.get("unit")) or "pcs",
                status,
                json.dumps(legacy_master_snapshot),
            )
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="product",
                canonical_id=product_id,
                source_table=_as_text(row.get("source_table")) or "tbsstock",
                source_identifier=legacy_code,
                source_row_number=_as_int(row.get("source_row_number")),
            )
        )
        product_by_code[legacy_code] = product_id
        product_snapshot_by_code[legacy_code] = {
            "name": product_name,
            "category": product_category,
        }
        count += 1
        lineage_count += 1

    for row in buffered_product_rows:
        await _upsert_product_row(row)

    await execute_many(
        connection,
        """
            INSERT INTO category_translation (
                id,
                category_id,
                locale,
                name
            )
            VALUES ($1::uuid, $2::uuid, 'en', $3::varchar)
            ON CONFLICT (category_id, locale) DO UPDATE SET
                name = EXCLUDED.name
            """,
        category_translation_rows,
    )

    await execute_many(
        connection,
        """
			INSERT INTO product (
				id,
				tenant_id,
				code,
				name,
				category,
                category_id,
				description,
				unit,
				status,
                legacy_master_snapshot,
				search_vector,
				created_at,
				updated_at
			)
			VALUES (
                $1::uuid, $2::uuid, $3::varchar, $4::varchar, $5::varchar, $6::uuid, $7::text,
                $8::varchar, $9::varchar, $10::json,
                to_tsvector(
                    'simple',
                    coalesce($3::text, '')
                    || ' '
                    || coalesce($4::text, '')
                    || ' '
                    || coalesce($5::text, '')
                ),
				NOW(), NOW()
			)
			ON CONFLICT (id) DO UPDATE SET
				code = EXCLUDED.code,
				name = EXCLUDED.name,
				category = EXCLUDED.category,
                category_id = EXCLUDED.category_id,
				description = EXCLUDED.description,
				unit = EXCLUDED.unit,
				status = EXCLUDED.status,
                legacy_master_snapshot = EXCLUDED.legacy_master_snapshot,
				search_vector = EXCLUDED.search_vector,
				updated_at = NOW()
			""",
        product_upsert_rows,
    )

    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return count, lineage_count, product_by_code, product_snapshot_by_code


async def _import_warehouses(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    warehouse_rows: AsyncIterable[dict[str, object]],
) -> tuple[int, int, dict[str, uuid.UUID]]:
    count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    warehouse_upsert_rows: list[tuple[object, ...]] = []
    warehouse_by_code: dict[str, uuid.UUID] = {}
    async for row in warehouse_rows:
        code = _as_text(row.get("code"))
        warehouse_id = _tenant_scoped_uuid(tenant_id, "warehouse", code)
        warehouse_upsert_rows.append(
            (
                warehouse_id,
                tenant_id,
                _as_text(row.get("name")) or code,
                code,
                _as_text(row.get("location")) or None,
                _as_text(row.get("address")) or None,
                None,
            )
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="warehouse",
                canonical_id=warehouse_id,
                source_table=_as_text(row.get("source_table")) or "normalized_warehouses",
                source_identifier=code,
                source_row_number=_as_int(row.get("source_row_number")),
            )
        )
        warehouse_by_code[code] = warehouse_id
        count += 1
        lineage_count += 1

    await execute_many(
        connection,
        """
			INSERT INTO warehouse (
				id,
				tenant_id,
				name,
				code,
				location,
				address,
				contact_email,
				is_active,
				created_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, NOW())
			ON CONFLICT (id) DO UPDATE SET
				name = EXCLUDED.name,
				code = EXCLUDED.code,
				location = EXCLUDED.location,
				address = EXCLUDED.address,
				contact_email = EXCLUDED.contact_email,
				is_active = EXCLUDED.is_active
			""",
        warehouse_upsert_rows,
    )
    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return count, lineage_count, warehouse_by_code


async def _import_inventory(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    batch_id: str,
    inventory_rows: AsyncIterable[dict[str, object]],
    product_by_code: dict[str, uuid.UUID],
    warehouse_by_code: dict[str, uuid.UUID],
) -> tuple[int, int]:
    count = 0
    lineage_count = 0
    pending_lineage: list[PendingLineageResolution] = []
    inventory_upsert_rows: list[tuple[object, ...]] = []
    async for row in inventory_rows:
        product_code = _as_text(row.get("product_legacy_code"))
        warehouse_code = _as_text(row.get("warehouse_code"))
        product_id = product_by_code.get(product_code)
        warehouse_id = warehouse_by_code.get(warehouse_code)
        if product_id is None or warehouse_id is None:
            raise ValueError(
                "Inventory dependency missing for "
                f"product={product_code} warehouse={warehouse_code}"
            )
        inventory_id = _tenant_scoped_uuid(
            tenant_id,
            "inventory-stock",
            product_code,
            warehouse_code,
        )
        inventory_upsert_rows.append(
            (
                inventory_id,
                tenant_id,
                product_id,
                warehouse_id,
                int(_as_decimal(row.get("quantity_on_hand"))),
                _as_int(row.get("reorder_point")),
            )
        )
        pending_lineage.append(
            PendingLineageResolution(
                canonical_table="inventory_stock",
                canonical_id=inventory_id,
                source_table=_as_text(row.get("source_table")) or "tbsstkhouse",
                source_identifier=f"{product_code}:{warehouse_code}",
                source_row_number=_as_int(row.get("source_row_number")),
            )
        )
        count += 1
        lineage_count += 1

    await execute_many(
        connection,
        """
			INSERT INTO inventory_stock (
				id,
				tenant_id,
				product_id,
				warehouse_id,
				quantity,
				reorder_point,
				updated_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, NOW())
			ON CONFLICT (id) DO UPDATE SET
				quantity = EXCLUDED.quantity,
				reorder_point = EXCLUDED.reorder_point,
				updated_at = NOW()
			""",
        inventory_upsert_rows,
    )
    await _flush_lineage_resolutions(
        connection,
        schema_name,
        run_id,
        tenant_id,
        batch_id,
        pending_lineage,
    )
    return count, lineage_count