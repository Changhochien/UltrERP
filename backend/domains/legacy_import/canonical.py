"""Canonical historical import helpers for legacy ERP batches."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from common.config import settings
from common.tenant import DEFAULT_TENANT_ID
from domains.legacy_import.canonical_common import (
    _as_decimal,
    _as_int,
    _as_legacy_date,
    _as_money,
    _as_text,
    _as_timestamp,
    _coerce_row,
    _currency_code,
    _ensure_canonical_support_tables,
    _table_exists,
    _try_as_legacy_date,
)
from domains.legacy_import.canonical_masters import (
    _build_product_master_snapshot,
    _ensure_product_category,
    _import_customers,
    _import_inventory,
    _import_products,
    _import_suppliers,
    _import_warehouses,
    _iter_buffered_rows,
    _load_category_cache,
    _partition_normalized_parties,
    _prime_product_category_cache,
)
from domains.legacy_import.canonical_receiving import (
    LEGACY_RECEIVING_SOURCE,
    _coerce_quantity_for_integer_schema,
    _hold_payment_adjacent_history,
    _import_legacy_receiving_audit,
    _receiving_date_fallback_counts,
)
from domains.legacy_import.canonical_persistence import (
    PendingLineageResolution,
    _flush_lineage_resolutions,
    _next_attempt_number,
    _try_upsert_holding_and_lineage,
    _upsert_lineage,
    _upsert_lineage_record,
    _upsert_lineage_record_for_holding,
    _upsert_run_row,
    _upsert_step_row,
)
from domains.legacy_import.canonical_prior_lookup import (
    _enrich_prior_master_lookup,
)
from domains.legacy_import.canonical_purchase_history import _import_purchase_history
from domains.legacy_import.canonical_readers import (
    _fetch_product_mappings,
    _fetch_purchase_headers,
    _fetch_purchase_lines,
    _fetch_sales_headers,
    _fetch_sales_lines,
    _iter_normalized_inventory,
    _iter_normalized_parties,
    _iter_normalized_products,
    _iter_normalized_warehouses,
    _iter_query_rows,
)
from domains.legacy_import.canonical_sales_history import _import_sales_history
from domains.legacy_import.canonical_scope import (
    _build_entity_scope_closure_keys,
    _domain_in_selected,
    _filter_purchase_headers_by_scope,
    _filter_purchase_lines_by_scope,
    _filter_sales_headers_by_scope,
    _filter_sales_lines_by_scope,
    _is_purchase_domain_selected,
    _is_sales_domain_selected,
)
from domains.legacy_import.normalization import deterministic_legacy_uuid
from domains.legacy_import.shared import (
    DOMAIN_PARTIES,
    DOMAIN_PRODUCTS,
    DOMAIN_PURCHASE_INVOICES,
    DOMAIN_SALES,
    DOMAIN_WAREHOUSES,
    execute_many,
)
from domains.legacy_import.staging import _open_raw_connection
_LOGGER = logging.getLogger(__name__)

# =============================================================================
# Domain name constants (documented in shared.py)
# =============================================================================
# These constants must match IncrementalDomainContract.name values in
# incremental_state.py. They are imported from shared.py for consistency:
#   DOMAIN_CUSTOMERS = "customers"
#   DOMAIN_PRODUCTS = "products"
#   DOMAIN_SALES = "sales"
#   DOMAIN_PURCHASE_INVOICES = "purchase-invoices"
#   (see domains/legacy_import/shared.py for the full set)
#
# Note: The canonical import uses canonical_table names ("customers", "suppliers",
# "products", etc.) for lineage and "sales_history" / "purchase_history" for
# step selection. The incremental domains use different names ("sales",
# "purchase-invoices"). The entity_scope manifest uses the incremental domain
# names ("sales", "purchase-invoices", "parties", "products").
# =============================================================================

@dataclass(slots=True, frozen=True)
class CanonicalImportResult:
    batch_id: str
    schema_name: str
    attempt_number: int
    customer_count: int
    product_count: int
    warehouse_count: int
    inventory_count: int
    order_count: int
    order_line_count: int
    invoice_count: int
    invoice_line_count: int
    holding_count: int
    lineage_count: int
    receiving_date_fallback_count: int = 0
    supplier_count: int = 0
    supplier_invoice_count: int = 0
    supplier_invoice_line_count: int = 0
    # Story 15.26: Scoped incremental metadata
    selected_domains: tuple[str, ...] = ()
    scoped_document_count: int = 0
    skipped_domains: tuple[str, ...] = ()
    review_required_issues: tuple[str, ...] = ()
def _tenant_scoped_uuid(tenant_id: uuid.UUID, kind: str, *parts: str) -> uuid.UUID:
    return deterministic_legacy_uuid(kind, str(tenant_id), *parts)


def _step_row_count(step_name: str, counts: Mapping[str, int]) -> int:
    if step_name == "sales_history":
        return counts.get("order_line_count", 0) + counts.get("invoice_line_count", 0)
    if step_name == "purchase_history":
        return counts.get("supplier_invoice_count", 0) + counts.get(
            "supplier_invoice_line_count", 0
        )
    if step_name == "receiving_audit":
        return counts.get("receiving_audit_count", 0)
    if step_name == "unsupported_history":
        return counts.get("holding_count", 0)

    step_to_count_key = {
        "customers": "customer_count",
        "suppliers": "supplier_count",
        "products": "product_count",
        "warehouses": "warehouse_count",
        "inventory": "inventory_count",
    }
    return counts.get(step_to_count_key.get(step_name, ""), 0)



async def _record_step_outcome(
    connection,
    schema_name: str,
    run_id: uuid.UUID,
    step_outcomes: list[tuple[str, int, str, str | None]],
    step_name: str,
    row_count: int,
    status: str,
    error_message: str | None = None,
) -> None:
    step_outcomes.append((step_name, row_count, status, error_message))
    await _upsert_step_row(
        connection,
        schema_name,
        run_id,
        step_name,
        row_count,
        status,
        error_message,
    )


async def _prepare_purchase_documents(
    connection,
    schema_name: str,
    batch_id: str,
    scope_closure_keys: dict[str, frozenset[str]],
    *,
    needs_receiving_audit: bool,
    needs_purchase_history: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    if not (needs_receiving_audit or needs_purchase_history):
        return [], [], []

    purchase_scope_keys = scope_closure_keys.get(DOMAIN_PURCHASE_INVOICES)
    purchase_headers_all = (
        await _fetch_purchase_headers(
            connection,
            schema_name,
            batch_id,
            doc_numbers=purchase_scope_keys,
        )
        if await _table_exists(connection, schema_name, "tbsslipj")
        else []
    )
    purchase_lines_all = (
        await _fetch_purchase_lines(
            connection,
            schema_name,
            batch_id,
            doc_numbers=None if needs_receiving_audit else purchase_scope_keys,
        )
        if await _table_exists(connection, schema_name, LEGACY_RECEIVING_SOURCE)
        else []
    )

    scoped_purchase_headers = (
        purchase_headers_all
        if purchase_scope_keys
        else _filter_purchase_headers_by_scope(purchase_headers_all, scope_closure_keys)
    )
    if not needs_purchase_history:
        return scoped_purchase_headers, purchase_lines_all, []

    if purchase_scope_keys and not needs_receiving_audit:
        return scoped_purchase_headers, purchase_lines_all, purchase_lines_all

    scoped_purchase_doc_numbers = frozenset(
        _as_text(header.get("doc_number")) for header in scoped_purchase_headers
    )
    scoped_purchase_lines = _filter_purchase_lines_by_scope(
        purchase_lines_all,
        scoped_purchase_doc_numbers,
    )
    return scoped_purchase_headers, purchase_lines_all, scoped_purchase_lines


async def _prepare_sales_documents(
    connection,
    schema_name: str,
    batch_id: str,
    scope_closure_keys: dict[str, frozenset[str]],
    *,
    needs_sales_history: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if not needs_sales_history:
        return [], []

    sales_scope_keys = scope_closure_keys.get(DOMAIN_SALES)
    sales_headers_all = await _fetch_sales_headers(
        connection,
        schema_name,
        batch_id,
        doc_numbers=sales_scope_keys,
    )
    sales_lines_all = await _fetch_sales_lines(
        connection,
        schema_name,
        batch_id,
        doc_numbers=sales_scope_keys,
    )
    if sales_scope_keys:
        return sales_headers_all, sales_lines_all

    scoped_sales_headers = _filter_sales_headers_by_scope(
        sales_headers_all,
        scope_closure_keys,
    )
    scoped_sales_doc_numbers = frozenset(
        _as_text(header.get("doc_number")) for header in scoped_sales_headers
    )
    scoped_sales_lines = _filter_sales_lines_by_scope(
        sales_lines_all,
        scoped_sales_doc_numbers,
    )
    return scoped_sales_headers, scoped_sales_lines


async def run_canonical_import(
    *,
    batch_id: str,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    schema_name: str | None = None,
    # Story 15.26: Scoped incremental parameters
    selected_domains: Sequence[str] | None = None,
    entity_scope: Mapping[str, object] | None = None,
    batch_mode: str | None = None,
    last_successful_batch_ids: Mapping[str, str] | None = None,
) -> CanonicalImportResult:
    """Run canonical import with optional incremental scope.

    Args:
        batch_id: The batch identifier for this import run.
        tenant_id: The tenant UUID (defaults to DEFAULT_TENANT_ID).
        schema_name: The raw legacy schema name (defaults to settings.legacy_import_schema).
        selected_domains: Optional sequence of domain names to process.
            If None, all domains are processed (full batch behavior).
        entity_scope: Optional per-domain closure keys from the delta manifest.
            Maps domain_name -> {closure_keys: [...], ...}.
            For sales/purchase: closure_keys are doc_numbers.
            For parties/products/warehouses/inventory: closure_keys are legacy codes.
        batch_mode: Optional batch mode ('full' or 'incremental').
            If 'incremental', respects selected_domains and entity_scope.
        last_successful_batch_ids: Optional mapping of domain -> last successful batch_id.
            Used for deterministic dependent-master lookup in scoped reruns.

    Returns:
        CanonicalImportResult with counts and scoped metadata.

    AC1: When selected_domains and entity_scope are provided with batch_mode=incremental,
         only impacted masters, inventory tuples, and full document families are upserted.
    AC2: Full header+line families are rebuilt deterministically for in-scope documents.
    AC3: Unresolved issues outside scope do not make the batch review-required.
    AC4: Same manifest scope produces idempotent results (deterministic IDs preserved).
    AC5: Dependent master resolution uses scoped handoff deterministically.
    """
    from collections.abc import Mapping as MappingABC

    # Normalize batch_mode for scope determination
    is_incremental = str(batch_mode).lower() == "incremental" if batch_mode else False

    # Normalize selected_domains to tuple (only used when incremental)
    # In full batch mode, selected_domains is ignored
    normalized_selected: tuple[str, ...] = ()
    if is_incremental and selected_domains is not None:
        normalized_selected = tuple(str(d) for d in selected_domains)

    needs_customers = _domain_in_selected("customers", normalized_selected)
    needs_suppliers = _domain_in_selected("suppliers", normalized_selected)
    needs_products = _domain_in_selected("products", normalized_selected)
    needs_warehouses = _domain_in_selected("warehouses", normalized_selected)
    needs_inventory = _domain_in_selected("inventory", normalized_selected)
    needs_receiving_audit = _domain_in_selected("receiving_audit", normalized_selected)
    needs_sales_history = _domain_in_selected("sales_history", normalized_selected)
    needs_purchase_history = _domain_in_selected("purchase_history", normalized_selected)

    # Build entity_scope closure keys lookup (only used when incremental)
    scope_closure_keys = _build_entity_scope_closure_keys(
        entity_scope if is_incremental and isinstance(entity_scope, MappingABC) else None
    )

    # Determine which domains are skipped (not in scope)
    ALL_CANONICAL_DOMAINS = frozenset({
        "customers", "suppliers", "products", "warehouses",
        "inventory", "receiving_audit", "sales_history", "purchase_history",
    })
    skipped_domains_list: list[str] = []
    if is_incremental and normalized_selected:
        for domain in ALL_CANONICAL_DOMAINS:
            if domain not in normalized_selected:
                skipped_domains_list.append(domain)
    skipped_domains_tuple = tuple(skipped_domains_list)

    _receiving_date_fallback_counts.clear()
    _receiving_date_fallback_counts.update({
        "receiving_date_fallback_receipt_to_invoice": 0,
        "receiving_date_fallback_to_batch": 0,
        "receiving_date_fallback_to_import_day": 0,
    })
    resolved_schema = schema_name or settings.legacy_import_schema
    connection = await _open_raw_connection()
    run_id = uuid.uuid4()
    attempt_number = 1
    step_outcomes: list[tuple[str, int, str, str | None]] = []
    counts: dict[str, int] = {
        "customer_count": 0,
        "supplier_count": 0,
        "product_count": 0,
        "warehouse_count": 0,
        "inventory_count": 0,
        "receiving_audit_count": 0,
        "order_count": 0,
        "order_line_count": 0,
        "invoice_count": 0,
        "invoice_line_count": 0,
        "supplier_invoice_count": 0,
        "supplier_invoice_line_count": 0,
        "holding_count": 0,
        "lineage_count": 0,
    }
    # Story 15.26: Track scoped document count
    scoped_document_count = 0
    current_step: str | None = None

    # Track unresolved mapping issues seen in current scope
    scope_review_required_issues: list[str] = []

    # Initialize lineage counts for all domains (may be skipped in scoped runs)
    customer_lineage_count = 0
    supplier_lineage_count = 0
    product_lineage_count = 0
    warehouse_lineage_count = 0
    inventory_lineage_count = 0
    receiving_audit_lineage_count = 0
    receiving_holding_count = 0
    receiving_date_fallback_count = 0
    sales_lineage_count = 0
    purchase_lineage_count = 0

    try:
        await _ensure_canonical_support_tables(connection, resolved_schema)
        attempt_number = await _next_attempt_number(
            connection, resolved_schema, batch_id, tenant_id
        )

        needs_product_mappings = (
            needs_receiving_audit or needs_sales_history or needs_purchase_history
        )
        product_mappings = (
            await _fetch_product_mappings(connection, resolved_schema, tenant_id)
            if needs_product_mappings
            else {}
        )

        async with connection.transaction():
            await _upsert_run_row(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                attempt_number,
                "running",
                counts,
                None,
            )

            customer_party_rows: list[dict[str, object]] = []
            supplier_party_rows: list[dict[str, object]] = []
            if needs_customers or needs_suppliers:
                customer_party_rows, supplier_party_rows = await _partition_normalized_parties(
                    connection,
                    resolved_schema,
                    batch_id,
                    tenant_id,
                )

            # Initialize master lookups (needed even if domain is skipped, for dependent resolution)
            # Story 15.26: customers domain
            current_step = "customers"
            customer_by_code: dict[str, uuid.UUID] = {}
            business_number_by_code: dict[str, str] = {}
            if needs_customers:
                (
                    counts["customer_count"],
                    customer_lineage_count,
                    customer_by_code,
                    business_number_by_code,
                ) = await _import_customers(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    _iter_buffered_rows(customer_party_rows),
                )
                counts["lineage_count"] += customer_lineage_count
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "customers",
                    counts["customer_count"],
                    "completed",
                )
            else:
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "customers",
                    0,
                    "skipped",
                    "domain not in scope",
                )

            # Story 15.26: suppliers domain
            current_step = "suppliers"
            supplier_by_code: dict[str, uuid.UUID] = {}
            if needs_suppliers:
                (
                    counts["supplier_count"],
                    supplier_lineage_count,
                    supplier_by_code,
                ) = await _import_suppliers(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    _iter_buffered_rows(supplier_party_rows),
                )
                counts["lineage_count"] += supplier_lineage_count
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "suppliers",
                    counts["supplier_count"],
                    "completed",
                )
            else:
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "suppliers",
                    0,
                    "skipped",
                    "domain not in scope",
                )

            # Story 15.26: products domain
            current_step = "products"
            product_by_code: dict[str, uuid.UUID] = {}
            product_snapshot_by_code: dict[str, dict[str, str | None]] = {}
            if needs_products:
                (
                    counts["product_count"],
                    product_lineage_count,
                    product_by_code,
                    product_snapshot_by_code,
                ) = await _import_products(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    _iter_normalized_products(connection, resolved_schema, batch_id, tenant_id),
                )
                counts["lineage_count"] += product_lineage_count
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "products",
                    counts["product_count"],
                    "completed",
                )
            else:
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "products",
                    0,
                    "skipped",
                    "domain not in scope",
                )

            # Story 15.26: warehouses domain
            current_step = "warehouses"
            warehouse_by_code: dict[str, uuid.UUID] = {}
            if needs_warehouses:
                (
                    counts["warehouse_count"],
                    warehouse_lineage_count,
                    warehouse_by_code,
                ) = await _import_warehouses(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    _iter_normalized_warehouses(connection, resolved_schema, batch_id, tenant_id),
                )
                counts["lineage_count"] += warehouse_lineage_count
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "warehouses",
                    counts["warehouse_count"],
                    "completed",
                )
            else:
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "warehouses",
                    0,
                    "skipped",
                    "domain not in scope",
                )

            # Story 15.26: inventory domain
            current_step = "inventory"
            if needs_inventory:
                counts["inventory_count"], inventory_lineage_count = await _import_inventory(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    _iter_normalized_inventory(connection, resolved_schema, batch_id, tenant_id),
                    product_by_code,
                    warehouse_by_code,
                )
                counts["lineage_count"] += inventory_lineage_count
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "inventory",
                    counts["inventory_count"],
                    "completed",
                )
            else:
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "inventory",
                    0,
                    "skipped",
                    "domain not in scope",
                )

            # Story 15.26: Fetch purchase data only when a selected domain needs it.
            # receiving_audit needs ALL lines (including blank doc_numbers for holding),
            # while purchase_history needs only scoped lines by header doc_number.
            (
                scoped_purchase_headers,
                purchase_lines_all,
                scoped_purchase_lines,
            ) = await _prepare_purchase_documents(
                connection,
                resolved_schema,
                batch_id,
                scope_closure_keys,
                needs_receiving_audit=needs_receiving_audit,
                needs_purchase_history=needs_purchase_history,
            )

            # Story 15.26: receiving_audit domain gets ALL lines (including blank doc_numbers)
            # because blank doc_number lines need to be routed to holding
            current_step = "receiving_audit"
            if needs_receiving_audit:
                (
                    counts["receiving_audit_count"],
                    receiving_audit_lineage_count,
                    receiving_holding_count,
                    receiving_date_fallback_count,
                ) = await _import_legacy_receiving_audit(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    scoped_purchase_headers,
                    purchase_lines_all,  # All lines for receiving audit (handles blank doc_numbers)
                    product_by_code,
                    warehouse_by_code,
                    product_mappings,
                )
                counts["lineage_count"] += receiving_audit_lineage_count
                counts["holding_count"] += receiving_holding_count
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "receiving_audit",
                    counts["receiving_audit_count"],
                    "completed",
                )
            else:
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "receiving_audit",
                    0,
                    "skipped",
                    "domain not in scope",
                )

            # Story 15.26: Fetch sales data with scope filtering
            scoped_sales_headers, scoped_sales_lines = await _prepare_sales_documents(
                connection,
                resolved_schema,
                batch_id,
                scope_closure_keys,
                needs_sales_history=needs_sales_history,
            )

            scoped_document_count = len(scoped_sales_headers) + len(scoped_purchase_headers)

            # =================================================================
            # AC5: Enrich master lookups from prior batch lineage
            # When a scoped run doesn't have all master entities in staging,
            # look them up from the last successful batch's lineage.
            # =================================================================
            if is_incremental:
                await _enrich_prior_master_lookup(
                    connection,
                    resolved_schema,
                    tenant_id,
                    last_successful_batch_ids,
                    scoped_sales_headers,
                    "customer_code",
                    customer_by_code,
                    canonical_table="customers",
                    source_table="tbscust",
                    log_label="customer",
                )
                await _enrich_prior_master_lookup(
                    connection,
                    resolved_schema,
                    tenant_id,
                    last_successful_batch_ids,
                    scoped_sales_lines,
                    "product_code",
                    product_by_code,
                    canonical_table="product",
                    source_table="tbsstock",
                    log_label="product",
                )

            # =================================================================
            # AC3: Track unknown product codes for review-required issues
            # Only mark in-scope issues as review-required.
            # =================================================================
            if is_incremental and needs_products:
                # Check if any product codes in scope map to UNKNOWN_PRODUCT_CODE
                scoped_product_codes = frozenset(
                    scope_closure_keys.get(DOMAIN_PRODUCTS, frozenset())
                )
                if scoped_product_codes:
                    for product_code in scoped_product_codes:
                        if product_code not in product_by_code:
                            # Product in scope but not found - this is a review-required issue
                            issue = f"unknown_product_code:{product_code}"
                            scope_review_required_issues.append(issue)

            # Story 15.26: sales_history domain
            current_step = "sales_history"
            if needs_sales_history:
                (
                    counts["order_count"],
                    counts["order_line_count"],
                    counts["invoice_count"],
                    counts["invoice_line_count"],
                    sales_lineage_count,
                ) = await _import_sales_history(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    scoped_sales_headers,
                    scoped_sales_lines,
                    customer_by_code,
                    business_number_by_code,
                    product_by_code,
                    product_snapshot_by_code,
                    product_mappings,
                )
                counts["lineage_count"] += sales_lineage_count
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "sales_history",
                    counts["order_line_count"] + counts["invoice_line_count"],
                    "completed",
                )
            else:
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "sales_history",
                    0,
                    "skipped",
                    "domain not in scope",
                )

            # =================================================================
            # AC5: Enrich supplier lookup from prior batch lineage for purchase
            # Only needed here since purchase_history requires supplier codes.
            # =================================================================
            if is_incremental:
                await _enrich_prior_master_lookup(
                    connection,
                    resolved_schema,
                    tenant_id,
                    last_successful_batch_ids,
                    scoped_purchase_headers,
                    "supplier_code",
                    supplier_by_code,
                    canonical_table="supplier",
                    source_table="tbscust",
                    log_label="supplier",
                )

            # Story 15.26: purchase_history domain
            current_step = "purchase_history"
            if needs_purchase_history:
                (
                    counts["supplier_invoice_count"],
                    counts["supplier_invoice_line_count"],
                    purchase_lineage_count,
                ) = await _import_purchase_history(
                    connection,
                    resolved_schema,
                    run_id,
                    tenant_id,
                    batch_id,
                    scoped_purchase_headers,
                    scoped_purchase_lines,
                    supplier_by_code,
                    product_by_code,
                    product_mappings,
                )
                counts["lineage_count"] += purchase_lineage_count
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "purchase_history",
                    counts["supplier_invoice_count"] + counts["supplier_invoice_line_count"],
                    "completed",
                )
            else:
                await _record_step_outcome(
                    connection,
                    resolved_schema,
                    run_id,
                    step_outcomes,
                    "purchase_history",
                    0,
                    "skipped",
                    "domain not in scope",
                )

            # Story 15.26: unsupported_history is always processed (payment-adjacent cleanup)
            current_step = "unsupported_history"
            payment_holding_count = await _hold_payment_adjacent_history(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
            )
            counts["holding_count"] += payment_holding_count
            await _record_step_outcome(
                connection,
                resolved_schema,
                run_id,
                step_outcomes,
                "unsupported_history",
                counts["holding_count"],
                "completed",
            )

            await _upsert_run_row(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                attempt_number,
                "completed",
                counts,
                None,
            )
            current_step = None

        return CanonicalImportResult(
            batch_id=batch_id,
            schema_name=resolved_schema,
            attempt_number=attempt_number,
            customer_count=counts["customer_count"],
            supplier_count=counts["supplier_count"],
            product_count=counts["product_count"],
            warehouse_count=counts["warehouse_count"],
            inventory_count=counts["inventory_count"],
            order_count=counts["order_count"],
            order_line_count=counts["order_line_count"],
            invoice_count=counts["invoice_count"],
            invoice_line_count=counts["invoice_line_count"],
            supplier_invoice_count=counts["supplier_invoice_count"],
            supplier_invoice_line_count=counts["supplier_invoice_line_count"],
            holding_count=counts["holding_count"],
            lineage_count=counts["lineage_count"],
            receiving_date_fallback_count=receiving_date_fallback_count,
            # Story 15.26: Scoped incremental metadata
            selected_domains=normalized_selected,
            scoped_document_count=scoped_document_count,
            skipped_domains=skipped_domains_tuple,
            review_required_issues=tuple(scope_review_required_issues),
        )
    except Exception as exc:
        if current_step is not None:
            step_outcomes.append(
                (
                    current_step,
                    _step_row_count(current_step, counts),
                    "failed",
                    str(exc),
                )
            )
        failure_summary = dict(counts)
        async with connection.transaction():
            await _upsert_run_row(
                connection,
                resolved_schema,
                run_id,
                tenant_id,
                batch_id,
                attempt_number,
                "failed",
                failure_summary,
                str(exc),
            )
            for step_name, row_count, status, error_message in step_outcomes:
                await _upsert_step_row(
                    connection,
                    resolved_schema,
                    run_id,
                    step_name,
                    row_count,
                    status,
                    error_message,
                )
        raise
    finally:
        await connection.close()
