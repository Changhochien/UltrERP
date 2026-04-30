"""Shared helpers used across the legacy-import modules."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from common.config import settings

# Domain name constants used for incremental refresh, delta discovery, and live projection.
# These names must match the IncrementalDomainContract.name values in incremental_state.py.
#
# Canonical import uses canonical_table names for lineage: "customers", "suppliers", "product".
# Entity scope and incremental domains use different names: "parties", "products", "sales", etc.
# This file provides constants for BOTH naming conventions to ensure consistency.
#
# Canonical table names (used in canonical_record_lineage.canonical_table):
DOMAIN_CUSTOMERS = "customers"
DOMAIN_SUPPLIERS = "suppliers"
# Incremental domain names (used in entity_scope and IncrementalDomainContract.name):
DOMAIN_PARTIES = "parties"  # Covers both customers and suppliers
DOMAIN_PRODUCTS = "products"
DOMAIN_WAREHOUSES = "warehouses"
DOMAIN_INVENTORY = "inventory"
DOMAIN_SALES = "sales"
DOMAIN_PURCHASE_INVOICES = "purchase-invoices"

SUPPORTED_INCREMENTAL_DOMAINS = frozenset(
    {
        DOMAIN_PARTIES,
        DOMAIN_PRODUCTS,
        DOMAIN_WAREHOUSES,
        DOMAIN_INVENTORY,
        DOMAIN_SALES,
        DOMAIN_PURCHASE_INVOICES,
    }
)

_EXECUTE_MANY_BATCH_SIZE = 5_000


def _iter_execute_many_batches(
    rows: Iterable[Sequence[object]],
) -> Iterable[list[Sequence[object]]]:
    batch: list[Sequence[object]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= _EXECUTE_MANY_BATCH_SIZE:
            yield batch
            batch = []
    if batch:
        yield batch


def coerce_mapping(record: Mapping[str, object] | object) -> dict[str, object]:
    if isinstance(record, Mapping):
        return {str(key): value for key, value in record.items()}
    return {str(key): value for key, value in dict(record).items()}


def resolve_row_identity(source_row_number: int | None, fallback: int) -> int:
    return source_row_number if source_row_number not in (None, 0) else fallback


def resolve_dump_data_dir(explicit_path: Path | None, *, argument_name: str) -> Path:
    if explicit_path is not None:
        return Path(explicit_path)

    configured_path = settings.legacy_import_data_dir.strip()
    if configured_path:
        return Path(configured_path)

    raise ValueError(
        "Dump-era file import requires an explicit "
        f"{argument_name} or LEGACY_IMPORT_DATA_DIR. "
        "Routine operator workflows should use live-stage or run_legacy_refresh."
    )


async def execute_many(
    connection: Any,
    query: str,
    rows: Iterable[Sequence[object]],
) -> None:
    executemany = getattr(connection, "executemany", None)
    for batch in _iter_execute_many_batches(rows):
        if callable(executemany):
            await executemany(query, batch)
            continue

        for row in batch:
            await connection.execute(query, *row)