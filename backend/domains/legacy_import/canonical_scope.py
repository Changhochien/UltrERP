"""Scope selection helpers for canonical import runs."""

from __future__ import annotations

from typing import Mapping, Sequence

from domains.legacy_import.canonical_common import _as_text
from domains.legacy_import.shared import (
    DOMAIN_PARTIES,
    DOMAIN_PRODUCTS,
    DOMAIN_PURCHASE_INVOICES,
    DOMAIN_SALES,
    DOMAIN_WAREHOUSES,
)


def _build_entity_scope_closure_keys(
    entity_scope: Mapping[str, object] | None,
) -> dict[str, frozenset[str]]:
    if entity_scope is None:
        return {}

    domain_value_fields: dict[str, tuple[str, ...]] = {
        DOMAIN_SALES: ("document_number",),
        DOMAIN_PURCHASE_INVOICES: ("document_number",),
        DOMAIN_PRODUCTS: ("product-code", "product_code"),
        DOMAIN_PARTIES: ("party-code", "party_code"),
        DOMAIN_WAREHOUSES: ("warehouse-code", "warehouse_code"),
    }

    result: dict[str, frozenset[str]] = {}
    for domain, spec in entity_scope.items():
        if not isinstance(spec, Mapping):
            continue
        keys = spec.get("closure_keys")
        if not isinstance(keys, (list, tuple, frozenset)):
            continue

        extracted: set[str] = set()
        for key_entry in keys:
            if isinstance(key_entry, Mapping):
                for field_name in domain_value_fields.get(domain, ()): 
                    value = key_entry.get(field_name)
                    if value is None:
                        continue
                    text = str(value).strip()
                    if text:
                        extracted.add(text)
                        break
                continue

            text = str(key_entry).strip()
            if text:
                extracted.add(text)

        if extracted:
            result[domain] = frozenset(extracted)
    return result


def _domain_in_selected(
    domain: str,
    selected_domains: tuple[str, ...] | Sequence[str] | None,
) -> bool:
    if not selected_domains:
        return True
    return domain in selected_domains


def _is_sales_domain_selected(selected_domains: tuple[str, ...] | None) -> bool:
    return _domain_in_selected(DOMAIN_SALES, selected_domains)


def _is_purchase_domain_selected(selected_domains: tuple[str, ...] | None) -> bool:
    return _domain_in_selected(DOMAIN_PURCHASE_INVOICES, selected_domains)


def _filter_sales_headers_by_scope(
    headers: list[dict[str, object]],
    entity_scope_closure_keys: dict[str, frozenset[str]],
) -> list[dict[str, object]]:
    sales_keys = entity_scope_closure_keys.get(DOMAIN_SALES)
    if not sales_keys:
        return headers

    return [
        header for header in headers
        if _as_text(header.get("doc_number")) in sales_keys
    ]


def _filter_purchase_headers_by_scope(
    headers: list[dict[str, object]],
    entity_scope_closure_keys: dict[str, frozenset[str]],
) -> list[dict[str, object]]:
    purchase_keys = entity_scope_closure_keys.get(DOMAIN_PURCHASE_INVOICES)
    if not purchase_keys:
        return headers

    return [
        header for header in headers
        if _as_text(header.get("doc_number")) in purchase_keys
    ]


def _filter_sales_lines_by_scope(
    lines: list[dict[str, object]],
    scoped_header_doc_numbers: frozenset[str],
) -> list[dict[str, object]]:
    if not scoped_header_doc_numbers:
        return lines
    return [
        line for line in lines
        if _as_text(line.get("doc_number")) in scoped_header_doc_numbers
    ]


def _filter_purchase_lines_by_scope(
    lines: list[dict[str, object]],
    scoped_header_doc_numbers: frozenset[str],
) -> list[dict[str, object]]:
    if not scoped_header_doc_numbers:
        return lines
    return [
        line for line in lines
        if _as_text(line.get("doc_number")) in scoped_header_doc_numbers
    ]