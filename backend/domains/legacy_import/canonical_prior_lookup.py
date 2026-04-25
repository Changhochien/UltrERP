"""Prior-batch master lookup helpers for scoped canonical reruns."""

from __future__ import annotations

import logging
import uuid
from typing import Mapping, MutableMapping, Sequence, cast

from domains.legacy_import.canonical_common import _as_text
from domains.legacy_import.staging import _quoted_identifier

_LOGGER = logging.getLogger(__name__)


async def _resolve_master_uuid_from_prior_batch(
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
    canonical_table: str,
    source_table: str,
    source_identifier: str,
    last_successful_batch_id: str | None,
) -> uuid.UUID | None:
    if last_successful_batch_id is None:
        return None

    quoted_schema = _quoted_identifier(schema_name)
    row = await connection.fetchrow(
        f"""
        SELECT canonical_id
        FROM {quoted_schema}.canonical_record_lineage
        WHERE batch_id = $1
          AND tenant_id = $2
          AND canonical_table = $3
          AND source_table = $4
          AND source_identifier = $5
          AND canonical_table != '__holding__'
        LIMIT 1
        """,
        last_successful_batch_id,
        tenant_id,
        canonical_table,
        source_table,
        source_identifier,
    )
    if row is None:
        return None
    return cast(uuid.UUID, row["canonical_id"])


async def _build_prior_master_lookup(
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
    last_successful_batch_ids: Mapping[str, str] | None,
    canonical_table: str,
    source_table: str,
    legacy_codes: Sequence[str],
) -> dict[str, uuid.UUID]:
    result: dict[str, uuid.UUID] = {}
    if not legacy_codes or last_successful_batch_ids is None:
        return result

    domain_map = {
        "customers": "customers",
        "supplier": "suppliers",
        "product": "products",
    }
    domain_name = domain_map.get(canonical_table)
    if domain_name is None:
        return result

    last_batch_id = last_successful_batch_ids.get(domain_name)
    if last_batch_id is None:
        return result

    for legacy_code in legacy_codes:
        prior_uuid = await _resolve_master_uuid_from_prior_batch(
            connection,
            schema_name,
            tenant_id,
            canonical_table,
            source_table,
            legacy_code,
            last_batch_id,
        )
        if prior_uuid is not None:
            result[legacy_code] = prior_uuid

    return result


async def _enrich_prior_master_lookup(
    connection,
    schema_name: str,
    tenant_id: uuid.UUID,
    last_successful_batch_ids: Mapping[str, str] | None,
    rows: Sequence[Mapping[str, object]],
    code_field: str,
    existing_lookup: MutableMapping[str, uuid.UUID],
    *,
    canonical_table: str,
    source_table: str,
    log_label: str,
) -> None:
    if last_successful_batch_ids is None:
        return

    needed_codes = frozenset(
        _as_text(row.get(code_field))
        for row in rows
        if _as_text(row.get(code_field))
    )
    missing_codes = [
        code for code in needed_codes
        if code and code not in existing_lookup
    ]
    if not missing_codes:
        return

    prior_lookup = await _build_prior_master_lookup(
        connection,
        schema_name,
        tenant_id,
        last_successful_batch_ids,
        canonical_table,
        source_table,
        missing_codes,
    )
    existing_lookup.update(prior_lookup)
    if prior_lookup:
        _LOGGER.info(
            "AC5: Resolved %d missing %s codes from prior batch lineage",
            len(prior_lookup),
            log_label,
        )