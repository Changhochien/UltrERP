from __future__ import annotations

import uuid

import pytest

import domains.legacy_import.canonical as canonical
import domains.legacy_import.source_resolution as source_resolution
from domains.legacy_import.normalization import deterministic_legacy_uuid
from tests.domains.legacy_import.canonical_test_support import FakeCanonicalConnection
from tests.domains.legacy_import.test_ap_payment_import import FakePaymentConnection


# ---------------------------------------------------------------------------
# Story 15.14 — Holding lineage AC1, AC2, AC3
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_holding_state_created_on_blank_doc_number_hold(monkeypatch) -> None:
    """A blank receiving-audit doc number should create holding state and an
    append-only holding event without writing a sentinel lineage row."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000440")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "T055",
                    "role": "supplier",
                    "company_name": "Holding Supplier",
                    "tax_id": "22345678",
                    "full_address": "Taoyuan",
                    "address": "Taoyuan",
                    "phone": "03-1234",
                    "email": "ap@supplier.test",
                    "contact_person": "Betty",
                    "source_table": "tbscust",
                    "source_row_number": 7,
                    "deterministic_id": deterministic_legacy_uuid("party", "supplier", "T055"),
                }
            ],
            "normalized_products": [
                {
                    "legacy_code": "P001",
                    "name": "Widget",
                    "category": "BELT",
                    "unit": "pcs",
                    "status": "A",
                    "source_table": "tbsstock",
                    "source_row_number": 12,
                    "deterministic_id": deterministic_legacy_uuid("product", "P001"),
                }
            ],
            "normalized_warehouses": [
                {
                    "code": "WH-A",
                    "name": "Legacy Warehouse A",
                    "location": None,
                    "address": None,
                    "source_table": "tbsstkhouse",
                    "source_row_number": 31,
                    "deterministic_id": deterministic_legacy_uuid("warehouse", "WH-A"),
                }
            ],
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [],
            "sales_lines": [],
            "purchase_headers": [
                {
                    "doc_number": "1130827001",
                    "raw_invoice_number": "GG46104158",
                    "invoice_number": "GG46104158",
                    "slip_date": "2024-08-27",
                    "raw_invoice_date": "2024-08-27",
                    "invoice_date": "2024-08-27",
                    "period_code": "11308",
                    "supplier_code": "T055",
                    "supplier_name": "Holding Supplier",
                    "address": "Taoyuan",
                    "notes": "SQ04",
                    "subtotal": "90.00",
                    "tax_amount": "5.00",
                    "must_pay_amount": "95.00",
                    "total_amount": "95.00",
                    "source_row_number": 17,
                }
            ],
            "purchase_lines": [
                {
                    "col_1": "4",
                    "doc_number": "",
                    "line_number": 3,
                    "product_code": "P001",
                    "product_name": "Widget",
                    "warehouse_code": "WH-A",
                    "qty": "3",
                    "unit_price": "30.00",
                    "extended_amount": "90.00",
                    "receipt_date": "2024-08-27",
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    await canonical.run_canonical_import(
        batch_id="batch-holding-lineage-blank",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    holding_calls = [
        args
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".unsupported_history_holding' in query
        and "tbsslipdtj" in args
    ]
    assert len(holding_calls) == 1, "Expected exactly one holding insert"

    holding_keys = [
        key
        for key in connection._fake_resolution_rows
        if key[2] == "tbsslipdtj" and key[3] == ":3"
    ]
    assert len(holding_keys) == 1
    holding_state = connection._fake_resolution_rows[holding_keys[0]]
    assert holding_state["status"] == source_resolution.STATUS_HOLDING
    assert holding_state["domain_name"] == "receiving_audit"
    assert holding_state["holding_id"] is not None

    holding_lineage_keys = [
        key
        for key in connection._fake_lineage_rows
        if key[2] == "__holding__"
        and key[3] == "tbsslipdtj"
        and key[4] == ":3"
    ]
    assert len(holding_lineage_keys) == 1
    holding_lineage = connection._fake_lineage_rows[holding_lineage_keys[0]]
    assert holding_lineage["canonical_id"] is not None

    assert any(
        event["source_table"] == "tbsslipdtj"
        and event["source_identifier"] == ":3"
        and event["new_status"] == source_resolution.STATUS_HOLDING
        for event in connection._fake_resolution_events
    )


@pytest.mark.asyncio
async def test_holding_state_created_on_payment_adjacent_hold(monkeypatch) -> None:
    """A payment-adjacent row should create holding state AND lineage entry."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000441")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [],
            "normalized_products": [],
            "normalized_warehouses": [],
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [],
            "sales_lines": [],
            "payment_headers": [
                {
                    "_source_row_number": 5,
                    "col_2": "PAY-ADJ-001",
                    "col_5": "Adjacent legacy memo",
                    "col_8": "999.99",
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result = await canonical.run_canonical_import(
        batch_id="batch-holding-lineage-payment-adj",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.holding_count == 1

    holding_keys = [
        key
        for key in connection._fake_resolution_rows
        if key[2] == "tbsprepay" and key[3] == "PAY-ADJ-001"
    ]
    assert len(holding_keys) == 1
    holding_state = connection._fake_resolution_rows[holding_keys[0]]
    assert holding_state["status"] == source_resolution.STATUS_HOLDING
    assert holding_state["domain_name"] == "payment_history"

    holding_lineage_keys = [
        key
        for key in connection._fake_lineage_rows
        if key[2] == "__holding__"
        and key[3] == "tbsprepay"
        and key[4] == "PAY-ADJ-001"
    ]
    assert len(holding_lineage_keys) == 1


@pytest.mark.asyncio
async def test_holding_state_payment_adjacent_no_col2(monkeypatch) -> None:
    """When col_2 is absent, holding state should fall back to the row-number-based
    source identifier and still create a holding lineage entry."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000443")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [],
            "normalized_products": [],
            "normalized_warehouses": [],
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [],
            "sales_lines": [],
            "payment_headers": [
                {
                    "_source_row_number": 5,
                    "col_2": None,
                    "col_5": "Adjacent legacy memo",
                    "col_8": "999.99",
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    result = await canonical.run_canonical_import(
        batch_id="batch-holding-lineage-no-col2",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.holding_count == 1

    holding_keys = [
        key
        for key in connection._fake_resolution_rows
        if key[2] == "tbsprepay" and key[3] == "tbsprepay:5"
    ]
    assert len(holding_keys) == 1
    holding_state = connection._fake_resolution_rows[holding_keys[0]]
    assert holding_state["status"] == source_resolution.STATUS_HOLDING
    assert holding_state["holding_id"] is not None

    holding_lineage_keys = [
        key
        for key in connection._fake_lineage_rows
        if key[2] == "__holding__"
        and key[3] == "tbsprepay"
        and key[4] == "tbsprepay:5"
    ]
    assert len(holding_lineage_keys) == 1


@pytest.mark.asyncio
async def test_holding_and_drained_rows_are_distinguishable(monkeypatch) -> None:
    """AC3: rows with canonical_table='__holding__' are held rows; rows with
    canonical_table='supplier_payments' are drained rows."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000442")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "T055",
                    "role": "supplier",
                    "company_name": "Distinguish Supplier",
                    "tax_id": "22345678",
                    "full_address": "Taoyuan",
                    "address": "Taoyuan",
                    "phone": "03-1234",
                    "email": "ap@supplier.test",
                    "contact_person": "Betty",
                    "source_table": "tbscust",
                    "source_row_number": 7,
                    "deterministic_id": deterministic_legacy_uuid("party", "supplier", "T055"),
                }
            ],
            "normalized_products": [
                {
                    "legacy_code": "P001",
                    "name": "Widget",
                    "category": "BELT",
                    "unit": "pcs",
                    "status": "A",
                    "source_table": "tbsstock",
                    "source_row_number": 12,
                    "deterministic_id": deterministic_legacy_uuid("product", "P001"),
                }
            ],
            "normalized_warehouses": [
                {
                    "code": "WH-A",
                    "name": "Legacy Warehouse A",
                    "location": None,
                    "address": None,
                    "source_table": "tbsstkhouse",
                    "source_row_number": 31,
                    "deterministic_id": deterministic_legacy_uuid("warehouse", "WH-A"),
                }
            ],
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [],
            "sales_lines": [],
            "purchase_headers": [
                {
                    "doc_number": "1130827001",
                    "raw_invoice_number": "GG46104158",
                    "invoice_number": "GG46104158",
                    "slip_date": "2024-08-27",
                    "raw_invoice_date": "2024-08-27",
                    "invoice_date": "2024-08-27",
                    "period_code": "11308",
                    "supplier_code": "T055",
                    "supplier_name": "Distinguish Supplier",
                    "address": "Taoyuan",
                    "notes": "SQ04",
                    "subtotal": "90.00",
                    "tax_amount": "5.00",
                    "must_pay_amount": "95.00",
                    "total_amount": "95.00",
                    "source_row_number": 17,
                }
            ],
            "purchase_lines": [
                {
                    "doc_number": "1130827001",
                    "line_number": 1,
                    "product_code": "P001",
                    "warehouse_code": "WH-A",
                    "qty": "3",
                    "unit_price": "30.00",
                    "extended_amount": "90.00",
                    "receipt_date": "2024-08-27",
                    "source_row_number": 18,
                },
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    await canonical.run_canonical_import(
        batch_id="batch-distinguish-holding-vs-drained",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    holding_entries = [
        key for key in connection._fake_lineage_rows if key[2] == "__holding__"
    ]
    drained_entries = [
        key
        for key in connection._fake_lineage_rows
        if key[2] not in ("__holding__",)
    ]

    assert len(drained_entries) >= 1
    assert len(holding_entries) == 0


# ---------------------------------------------------------------------------
# Story 15.21 — Holding state and drain lineage are distinguishable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_holding_and_drained_rows_are_distinguishable_holding(monkeypatch) -> None:
    """A held receiving-audit row should exist in source resolution while drained
    rows continue to appear only in canonical lineage."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000442")
    connection = FakeCanonicalConnection(
        {
            "normalized_parties": [
                {
                    "legacy_code": "T055",
                    "role": "supplier",
                    "company_name": "Distinguish Supplier",
                    "tax_id": "22345678",
                    "full_address": "Taoyuan",
                    "address": "Taoyuan",
                    "phone": "03-1234",
                    "email": "ap@supplier.test",
                    "contact_person": "Betty",
                    "source_table": "tbscust",
                    "source_row_number": 7,
                    "deterministic_id": deterministic_legacy_uuid("party", "supplier", "T055"),
                }
            ],
            "normalized_products": [
                {
                    "legacy_code": "P001",
                    "name": "Widget",
                    "category": "BELT",
                    "unit": "pcs",
                    "status": "A",
                    "source_table": "tbsstock",
                    "source_row_number": 12,
                    "deterministic_id": deterministic_legacy_uuid("product", "P001"),
                }
            ],
            "normalized_warehouses": [
                {
                    "code": "WH-A",
                    "name": "Legacy Warehouse A",
                    "location": None,
                    "address": None,
                    "source_table": "tbsstkhouse",
                    "source_row_number": 31,
                    "deterministic_id": deterministic_legacy_uuid("warehouse", "WH-A"),
                }
            ],
            "normalized_inventory_prep": [],
            "product_code_mapping": [],
            "sales_headers": [],
            "sales_lines": [],
            "purchase_headers": [
                {
                    "doc_number": "HOLD001",
                    "raw_invoice_number": "HOLD001",
                    "invoice_number": "HOLD001",
                    "slip_date": "2024-08-27",
                    "raw_invoice_date": "2024-08-27",
                    "invoice_date": "2024-08-27",
                    "period_code": "11308",
                    "supplier_code": "T055",
                    "supplier_name": "Distinguish Supplier",
                    "address": "Taoyuan",
                    "notes": "SQ04",
                    "subtotal": "90.00",
                    "tax_amount": "5.00",
                    "must_pay_amount": "95.00",
                    "total_amount": "95.00",
                    "source_row_number": 17,
                }
            ],
            "purchase_lines": [
                {
                    "col_1": "4",
                    "doc_number": "",
                    "line_number": 1,
                    "product_code": "P001",
                    "warehouse_code": "WH-A",
                    "qty": "3",
                    "unit_price": "30.00",
                    "extended_amount": "90.00",
                    "receipt_date": "2024-08-27",
                    "source_row_number": 25,
                },
            ],
        }
    )

    async def fake_open_raw_connection() -> FakeCanonicalConnection:
        return connection

    monkeypatch.setattr(canonical, "_open_raw_connection", fake_open_raw_connection)

    await canonical.run_canonical_import(
        batch_id="batch-holding-vs-drained",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    holding_calls = [
        args
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".unsupported_history_holding' in query
        and "tbsslipdtj" in args
    ]
    assert len(holding_calls) == 1

    holding_entries = [
        key
        for key in connection._fake_resolution_rows
        if key[2] == "tbsslipdtj" and key[3] == ":1"
    ]
    assert len(holding_entries) == 1
    assert connection._fake_resolution_rows[holding_entries[0]]["status"] == source_resolution.STATUS_HOLDING

    holding_lineage_entries = [
        key
        for key in connection._fake_lineage_rows
        if key[2] == "__holding__"
        and key[3] == "tbsslipdtj"
        and key[4] == ":1"
    ]
    assert len(holding_lineage_entries) == 1

    drained_entries = [
        key
        for key in connection._fake_lineage_rows
        if key[2] != "__holding__"
    ]
    assert drained_entries


@pytest.mark.asyncio
async def test_holding_and_drained_rows_are_distinguishable_drain(monkeypatch) -> None:
    """A drained AP payment should resolve source state and write normal lineage."""
    import domains.legacy_import.ap_payment_import as ap_payment_import

    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000442")
    supplier_id = ap_payment_import._tenant_scoped_uuid(
        tenant_id, "party", "supplier", "T008"
    )

    connection = FakePaymentConnection(
        {
            "tbscust": [
                {"legacy_code": "T008", "legacy_type": "1"},
            ],
            "supplier": [{"id": supplier_id}],
            "tbsspay": [
                {
                    "col_2": "DRAIN-001",
                    "col_4": "2016-05-05",
                    "col_6": "T008",
                    "col_8": "0001",
                    "col_10": "570.00000000",
                    "col_12": "CHK-001",
                    "col_18": "drained payment",
                    "_source_row_number": 1,
                },
            ],
            "tbsprepay": [],
        }
    )
    connection._fake_lineage_rows = {}

    async def fake_open_raw_connection() -> FakePaymentConnection:
        return connection

    monkeypatch.setattr(ap_payment_import, "_open_raw_connection", fake_open_raw_connection)

    result = await ap_payment_import.run_ap_payment_import(
        batch_id="batch-holding-vs-drained-drain",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.payment_count == 1
    assert result.holding_count == 0

    all_lineage_keys = list(connection._fake_lineage_rows)
    assert len(all_lineage_keys) == 1

    _t, _b, canonical_table, source_table, source_identifier, source_row_number = all_lineage_keys[0]
    assert canonical_table == "supplier_payments"
    assert source_table == "tbsspay"
    assert source_identifier == "DRAIN-001"
    assert source_row_number == 1
    assert canonical_table != "__holding__"
    resolution_row = connection._fake_resolution_rows[
        (tenant_id, "batch-holding-vs-drained-drain", "tbsspay", "DRAIN-001", 1)
    ]
    assert resolution_row["status"] == source_resolution.STATUS_RESOLVED
    assert resolution_row["canonical_table"] == "supplier_payments"


@pytest.mark.asyncio
async def test_drain_updates_holding_lineage_entry(monkeypatch) -> None:
    """AC2: When a held row is drained, its lineage entry should be updated."""
    import domains.legacy_import.ap_payment_import as ap_payment_import

    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000442")
    supplier_id = ap_payment_import._tenant_scoped_uuid(
        tenant_id, "party", "supplier", "T008"
    )

    connection = FakePaymentConnection(
        {
            "tbscust": [
                {"legacy_code": "T008", "legacy_type": "1"},
            ],
            "supplier": [{"id": supplier_id}],
            "tbsspay": [
                {
                    "col_2": "DRAIN-002",
                    "col_4": "2016-05-05",
                    "col_6": "T008",
                    "col_8": "0001",
                    "col_10": "570.00000000",
                    "col_12": "CHK-001",
                    "col_18": "drained payment",
                    "_source_row_number": 2,
                },
            ],
            "tbsprepay": [],
        }
    )
    holding_key = (tenant_id, "batch-ac2-test", "__holding__", "tbsspay", "DRAIN-002", 2)
    connection._fake_lineage_rows = {
        holding_key: {
            "canonical_id": uuid.uuid4(),
            "import_run_id": uuid.uuid4(),
        }
    }

    async def fake_open_raw_connection() -> FakePaymentConnection:
        return connection

    monkeypatch.setattr(ap_payment_import, "_open_raw_connection", fake_open_raw_connection)

    result = await ap_payment_import.run_ap_payment_import(
        batch_id="batch-ac2-test",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.payment_count == 1
    assert result.holding_count == 0

    all_lineage_keys = list(connection._fake_lineage_rows)
    assert len(all_lineage_keys) == 1

    _t, _b, canonical_table, source_table, source_identifier, source_row_number = all_lineage_keys[0]
    assert canonical_table == "supplier_payments"
    assert source_table == "tbsspay"
    assert source_identifier == "DRAIN-002"
    assert source_row_number == 2