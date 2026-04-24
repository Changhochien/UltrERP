"""Shared helpers used across the legacy-import modules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from common.config import settings

# Domain name constants used for incremental refresh, delta discovery, and live projection.
# These names must match the IncrementalDomainContract.name values in incremental_state.py.
DOMAIN_PARTIES = "parties"
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
    rows: Sequence[Sequence[object]],
) -> None:
    if not rows:
        return

    executemany = getattr(connection, "executemany", None)
    if callable(executemany):
        await executemany(query, rows)
        return

    for row in rows:
        await connection.execute(query, *row)