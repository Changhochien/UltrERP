"""Repair inventory_stock warehouse alignment from raw_legacy.tbsstkhouse."""

from __future__ import annotations

import argparse
import asyncio
import uuid
from dataclasses import dataclass
from decimal import Decimal
from itertools import batched

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import AsyncSessionLocal
from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.normalization import deterministic_legacy_uuid

DEFAULT_SCHEMA_NAME = "raw_legacy"
DEFAULT_WAREHOUSE_CODE = "LEGACY_DEFAULT"
KNOWN_WAREHOUSE_NAMES = {
    "A": "Legacy General Warehouse (總倉)",
}


@dataclass(frozen=True, slots=True)
class InventorySnapshotPayload:
    id: uuid.UUID
    tenant_id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int
    reorder_point: int
    source_identifier: str
    source_row_number: int

    def inventory_row(self) -> dict[str, object]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "product_id": self.product_id,
            "warehouse_id": self.warehouse_id,
            "quantity": self.quantity,
            "reorder_point": self.reorder_point,
        }

    def lineage_row(self, *, batch_id: str, run_id: uuid.UUID) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "batch_id": batch_id,
            "canonical_table": "inventory_stock",
            "canonical_id": self.id,
            "source_table": "tbsstkhouse",
            "source_identifier": self.source_identifier,
            "source_row_number": self.source_row_number,
            "import_run_id": run_id,
        }


def _tenant_scoped_uuid(tenant_id: uuid.UUID, kind: str, *parts: str) -> uuid.UUID:
    return deterministic_legacy_uuid(kind, str(tenant_id), *parts)


def _as_text(value: object | None) -> str:
    return str(value or "").strip()


def _as_int_quantity(value: object | None) -> int:
    raw = _as_text(value)
    if not raw:
        return 0
    return int(Decimal(raw))


def _warehouse_name_for_code(code: str) -> str:
    normalized_code = _as_text(code) or DEFAULT_WAREHOUSE_CODE
    if normalized_code == DEFAULT_WAREHOUSE_CODE:
        return "Legacy Default Warehouse"
    return KNOWN_WAREHOUSE_NAMES.get(normalized_code, f"Legacy Warehouse {normalized_code}")


async def _detect_batch_id(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    schema_name: str,
) -> str:
    result = await session.execute(
        text(
            f"""
            SELECT batch_id
            FROM {schema_name}.canonical_record_lineage
            WHERE tenant_id = :tenant_id
              AND canonical_table = 'inventory_stock'
              AND source_table = 'tbsstkhouse'
            GROUP BY batch_id
            ORDER BY COUNT(*) DESC, batch_id DESC
            LIMIT 1
            """
        ),
        {"tenant_id": str(tenant_id)},
    )
    batch_id = result.scalar_one_or_none()
    if batch_id is None:
        raise ValueError("Could not detect a tbsstkhouse batch_id from canonical_record_lineage")
    return str(batch_id)


async def _fetch_snapshot_rows(
    session: AsyncSession,
    *,
    batch_id: str,
    schema_name: str,
) -> list[dict[str, object]]:
    result = await session.execute(
        text(
            f"""
            SELECT
                col_1 AS product_code,
                col_2 AS warehouse_code,
                col_7 AS qty_on_hand,
                _source_row_number AS source_row_number
            FROM {schema_name}.tbsstkhouse
            WHERE _batch_id = :batch_id
            ORDER BY _source_row_number
            """
        ),
        {"batch_id": batch_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def _fetch_product_by_code(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    result = await session.execute(
        text(
            """
            SELECT code, id
            FROM product
            WHERE tenant_id = :tenant_id
            """
        ),
        {"tenant_id": str(tenant_id)},
    )
    return {_as_text(row.code): row.id for row in result.all()}


async def _ensure_warehouses(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_codes: set[str],
) -> dict[str, uuid.UUID]:
    result = await session.execute(
        text(
            """
            SELECT code, id
            FROM warehouse
            WHERE tenant_id = :tenant_id
            """
        ),
        {"tenant_id": str(tenant_id)},
    )
    warehouse_by_code = {_as_text(row.code): row.id for row in result.all()}

    missing_codes = sorted(code for code in warehouse_codes if code not in warehouse_by_code)
    if missing_codes:
        await session.execute(
            text(
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
                VALUES (
                    :id,
                    :tenant_id,
                    :name,
                    :code,
                    NULL,
                    NULL,
                    NULL,
                    TRUE,
                    NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    code = EXCLUDED.code,
                    is_active = EXCLUDED.is_active
                """
            ),
            [
                {
                    "id": _tenant_scoped_uuid(tenant_id, "warehouse", code),
                    "tenant_id": str(tenant_id),
                    "name": _warehouse_name_for_code(code),
                    "code": code,
                }
                for code in missing_codes
            ],
        )
        warehouse_by_code.update(
            {code: _tenant_scoped_uuid(tenant_id, "warehouse", code) for code in missing_codes}
        )

    return warehouse_by_code


def _build_snapshot_payloads(
    rows: list[dict[str, object]],
    *,
    tenant_id: uuid.UUID,
    product_by_code: dict[str, uuid.UUID],
    warehouse_by_code: dict[str, uuid.UUID],
) -> list[InventorySnapshotPayload]:
    payloads: list[InventorySnapshotPayload] = []
    for row in rows:
        product_code = _as_text(row.get("product_code"))
        warehouse_code = _as_text(row.get("warehouse_code")) or DEFAULT_WAREHOUSE_CODE
        product_id = product_by_code.get(product_code)
        warehouse_id = warehouse_by_code.get(warehouse_code)
        if product_id is None:
            raise ValueError(f"Inventory snapshot cannot resolve product {product_code!r}")
        if warehouse_id is None:
            raise ValueError(f"Inventory snapshot cannot resolve warehouse {warehouse_code!r}")

        payloads.append(
            InventorySnapshotPayload(
                id=_tenant_scoped_uuid(tenant_id, "inventory-stock", product_code, warehouse_code),
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=_as_int_quantity(row.get("qty_on_hand")),
                reorder_point=0,
                source_identifier=f"{product_code}:{warehouse_code}",
                source_row_number=int(row.get("source_row_number") or 0),
            )
        )
    return payloads


async def _count_stale_default_snapshot_rows(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    batch_id: str,
    schema_name: str,
) -> int:
    result = await session.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM {schema_name}.canonical_record_lineage
            WHERE tenant_id = :tenant_id
              AND batch_id = :batch_id
              AND canonical_table = 'inventory_stock'
              AND source_table = 'tbsstkhouse'
              AND source_identifier LIKE :source_suffix
            """
        ),
        {
            "tenant_id": str(tenant_id),
            "batch_id": batch_id,
            "source_suffix": f"%:{DEFAULT_WAREHOUSE_CODE}",
        },
    )
    return int(result.scalar_one())


async def _delete_stale_default_snapshot_rows(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    batch_id: str,
    schema_name: str,
) -> int:
    await session.execute(
        text(
            f"""
            DELETE FROM inventory_stock
            WHERE tenant_id = :tenant_id
              AND warehouse_id = :default_warehouse_id
              AND id IN (
                  SELECT canonical_id
                  FROM {schema_name}.canonical_record_lineage
                  WHERE tenant_id = :tenant_id
                    AND batch_id = :batch_id
                    AND canonical_table = 'inventory_stock'
                    AND source_table = 'tbsstkhouse'
                    AND source_identifier LIKE :source_suffix
              )
            """
        ),
        {
            "tenant_id": str(tenant_id),
            "batch_id": batch_id,
            "default_warehouse_id": str(
                _tenant_scoped_uuid(tenant_id, "warehouse", DEFAULT_WAREHOUSE_CODE)
            ),
            "source_suffix": f"%:{DEFAULT_WAREHOUSE_CODE}",
        },
    )
    await session.execute(
        text(
            f"""
            DELETE FROM {schema_name}.canonical_record_lineage
            WHERE tenant_id = :tenant_id
              AND batch_id = :batch_id
              AND canonical_table = 'inventory_stock'
              AND source_table = 'tbsstkhouse'
              AND source_identifier LIKE :source_suffix
            """
        ),
        {
            "tenant_id": str(tenant_id),
            "batch_id": batch_id,
            "source_suffix": f"%:{DEFAULT_WAREHOUSE_CODE}",
        },
    )
    return await _count_stale_default_snapshot_rows(
        session,
        tenant_id=tenant_id,
        batch_id=batch_id,
        schema_name=schema_name,
    )


async def _upsert_inventory_snapshot(
    session: AsyncSession,
    payloads: list[InventorySnapshotPayload],
    *,
    batch_id: str,
    run_id: uuid.UUID,
    schema_name: str,
    batch_size: int = 500,
) -> int:
    inventory_upsert = text(
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
        VALUES (
            :id,
            :tenant_id,
            :product_id,
            :warehouse_id,
            :quantity,
            :reorder_point,
            NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            product_id = EXCLUDED.product_id,
            warehouse_id = EXCLUDED.warehouse_id,
            quantity = EXCLUDED.quantity,
            reorder_point = EXCLUDED.reorder_point,
            updated_at = NOW()
        """
    )
    lineage_upsert = text(
        f"""
        INSERT INTO {schema_name}.canonical_record_lineage (
            tenant_id,
            batch_id,
            canonical_table,
            canonical_id,
            source_table,
            source_identifier,
            source_row_number,
            import_run_id
        )
        VALUES (
            :tenant_id,
            :batch_id,
            :canonical_table,
            :canonical_id,
            :source_table,
            :source_identifier,
            :source_row_number,
            :import_run_id
        )
        ON CONFLICT (
            tenant_id,
            batch_id,
            canonical_table,
            canonical_id,
            source_table,
            source_identifier
        ) DO UPDATE SET
            source_row_number = EXCLUDED.source_row_number,
            import_run_id = EXCLUDED.import_run_id
        """
    )

    for batch in batched(payloads, batch_size):
        batch = list(batch)
        await session.execute(inventory_upsert, [payload.inventory_row() for payload in batch])
        await session.execute(
            lineage_upsert,
            [payload.lineage_row(batch_id=batch_id, run_id=run_id) for payload in batch],
        )
    return len(payloads)


async def repair_inventory_snapshot(
    *,
    batch_id: str | None,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    dry_run: bool = True,
    schema_name: str = DEFAULT_SCHEMA_NAME,
) -> None:
    async with AsyncSessionLocal() as session:
        resolved_batch_id = batch_id or await _detect_batch_id(
            session,
            tenant_id=tenant_id,
            schema_name=schema_name,
        )
        rows = await _fetch_snapshot_rows(
            session,
            batch_id=resolved_batch_id,
            schema_name=schema_name,
        )
        product_by_code = await _fetch_product_by_code(session, tenant_id=tenant_id)
        warehouse_codes = {
            _as_text(row.get("warehouse_code")) or DEFAULT_WAREHOUSE_CODE for row in rows
        }
        warehouse_by_code = await _ensure_warehouses(
            session,
            tenant_id=tenant_id,
            warehouse_codes=warehouse_codes,
        )
        payloads = _build_snapshot_payloads(
            rows,
            tenant_id=tenant_id,
            product_by_code=product_by_code,
            warehouse_by_code=warehouse_by_code,
        )
        stale_count = await _count_stale_default_snapshot_rows(
            session,
            tenant_id=tenant_id,
            batch_id=resolved_batch_id,
            schema_name=schema_name,
        )

        print(f"Batch ID           : {resolved_batch_id}")
        print(f"Dry run            : {dry_run}")
        print(f"Snapshot rows found : {len(rows)}")
        print(f"Warehouse codes     : {', '.join(sorted(warehouse_codes))}")
        print(f"Payload rows        : {len(payloads)}")
        print(f"Stale default rows  : {stale_count}")

        for payload in payloads[:10]:
            print(
                "- "
                f"{payload.source_identifier} -> warehouse={payload.warehouse_id} "
                f"qty={payload.quantity}"
            )

        if dry_run:
            await session.rollback()
            return

        run_id = uuid.uuid4()
        await _upsert_inventory_snapshot(
            session,
            payloads,
            batch_id=resolved_batch_id,
            run_id=run_id,
            schema_name=schema_name,
        )
        await _delete_stale_default_snapshot_rows(
            session,
            tenant_id=tenant_id,
            batch_id=resolved_batch_id,
            schema_name=schema_name,
        )
        await session.commit()
        print(f"Upserted {len(payloads)} inventory snapshot rows.")
        print("Deleted stale LEGACY_DEFAULT snapshot rows and lineage.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repair inventory_stock warehouse alignment from raw_legacy.tbsstkhouse."
    )
    parser.add_argument(
        "--batch-id",
        help=(
            "Canonical batch ID to repair. Defaults to the latest "
            "tbsstkhouse inventory lineage batch."
        ),
    )
    parser.add_argument(
        "--tenant-id",
        default=str(DEFAULT_TENANT_ID),
        help="Tenant UUID to repair (defaults to DEFAULT_TENANT_ID).",
    )
    parser.add_argument(
        "--schema-name",
        default=DEFAULT_SCHEMA_NAME,
        help="Schema that stores staged legacy data and canonical lineage metadata.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Persist the repaired inventory snapshot rows. Dry-run is the default.",
    )
    args = parser.parse_args()

    asyncio.run(
        repair_inventory_snapshot(
            batch_id=args.batch_id,
            tenant_id=uuid.UUID(args.tenant_id),
            dry_run=not args.live,
            schema_name=args.schema_name,
        )
    )


if __name__ == "__main__":
    main()