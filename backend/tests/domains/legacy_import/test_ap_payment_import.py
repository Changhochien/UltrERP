from __future__ import annotations

import json
import uuid
from typing import cast

import pytest

import domains.legacy_import.ap_payment_import as ap_payment_import
import domains.legacy_import.source_resolution as source_resolution


class FakePaymentTransaction:
    def __init__(self, connection: "FakePaymentConnection") -> None:
        self.connection = connection
        self.buffer: list[tuple[str, tuple[object, ...]]] = []

    async def __aenter__(self) -> "FakePaymentTransaction":
        self.connection.transaction_started = True
        self.connection.transaction_buffers.append(self.buffer)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        self.connection.transaction_buffers.pop()
        if exc_type is None:
            self.connection.transaction_committed = True
            if self.connection.transaction_buffers:
                self.connection.transaction_buffers[-1].extend(self.buffer)
            else:
                self.connection.committed_execute_calls.extend(self.buffer)
        else:
            self.connection.transaction_rolled_back = True
        return False


class FakePaymentConnection:
    def __init__(self, rows_by_key: dict[str, list[dict[str, object]]]) -> None:
        self.rows_by_key = rows_by_key
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.committed_execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.transaction_buffers: list[list[tuple[str, tuple[object, ...]]]] = []
        self.transaction_started = False
        self.transaction_committed = False
        self.transaction_rolled_back = False
        self.closed = False
        self._fake_lineage_rows: dict[tuple[object, ...], dict[str, object]] = {}
        self._fake_resolution_rows: dict[tuple[object, ...], dict[str, object]] = {}
        self._fake_resolution_events: list[dict[str, object]] = []
        self._fake_holding_rows: dict[tuple[object, ...], dict[str, object]] = {}

    def transaction(self) -> FakePaymentTransaction:
        return FakePaymentTransaction(self)

    async def fetch(self, query: str, *args: object):
        if 'FROM "raw_legacy".tbscust' in query:
            return self.rows_by_key.get("tbscust", [])
        if 'FROM "raw_legacy".tbsspay' in query:
            return self.rows_by_key.get("tbsspay", [])
        if 'FROM "raw_legacy".tbsprepay' in query:
            return self.rows_by_key.get("tbsprepay", [])
        if "FROM supplier" in query:
            return self.rows_by_key.get("supplier", [])
        return []

    async def fetchval(self, query: str, *args: object):
        if "MAX(attempt_number)" in query and "legacy_import_runs" in query:
            return 0
        if "to_regclass" in query and "tbscust" in query:
            return "raw_legacy.tbscust" if "tbscust" in self.rows_by_key else None
        if "to_regclass" in query and "tbsspay" in query:
            return "raw_legacy.tbsspay" if "tbsspay" in self.rows_by_key else None
        if "to_regclass" in query and "tbsprepay" in query:
            return "raw_legacy.tbsprepay" if "tbsprepay" in self.rows_by_key else None
        return None

    async def fetchrow(self, query: str, *args: object):
        if 'FROM "raw_legacy".source_row_resolution' in query:
            key = (args[0], args[1], args[2], args[3], args[4])
            row = self._fake_resolution_rows.get(key)
            return None if row is None else dict(row)
        return None

    async def execute(self, query: str, *args: object) -> str:
        call = (query, args)
        self.execute_calls.append(call)
        if self.transaction_buffers:
            self.transaction_buffers[-1].append(call)
        else:
            self.committed_execute_calls.append(call)

        if 'INSERT INTO "raw_legacy".canonical_record_lineage' in query:
            # Source-identifier-only key (used for ON CONFLICT DO UPDATE)
            # The full key is (tenant_id, batch_id, canonical_table, source_table,
            # source_identifier, source_row_number), but ON CONFLICT matches on
            # (batch_id, tenant_id, source_table, source_identifier, source_row_number)
            source_key = (args[1], args[0], args[4], args[5], args[6])
            full_key = (args[0], args[1], args[2], args[4], args[5], args[6])
            # Check if any entry with the same source identity exists
            # existing_key: (tenant_id, batch_id, canonical_table, source_table, source_identifier, source_row_number)
            for existing_key in list(self._fake_lineage_rows.keys()):
                if (
                    existing_key[0] == args[0]  # tenant_id
                    and existing_key[1] == args[1]  # batch_id
                    and existing_key[3] == args[4]  # source_table
                    and existing_key[4] == args[5]  # source_identifier
                    and existing_key[5] == args[6]  # source_row_number
                ):
                    # ON CONFLICT DO UPDATE - remove old entry
                    del self._fake_lineage_rows[existing_key]
                    break
            self._fake_lineage_rows[full_key] = {
                "canonical_id": args[3],
                "import_run_id": args[7],
            }
        elif 'INSERT INTO "raw_legacy".source_row_resolution_events' in query:
            self._fake_resolution_events.append(
                {
                    "event_id": args[0],
                    "tenant_id": args[1],
                    "batch_id": args[2],
                    "source_table": args[3],
                    "source_identifier": args[4],
                    "source_row_number": args[5],
                    "domain_name": args[6],
                    "previous_status": args[7],
                    "new_status": args[8],
                    "holding_id": args[9],
                    "canonical_table": args[10],
                    "canonical_id": args[11],
                    "notes": args[12],
                    "import_run_id": args[13],
                }
            )
        elif 'INSERT INTO "raw_legacy".source_row_resolution' in query:
            key = (args[0], args[1], args[2], args[3], args[4])
            self._fake_resolution_rows[key] = {
                "tenant_id": args[0],
                "batch_id": args[1],
                "source_table": args[2],
                "source_identifier": args[3],
                "source_row_number": args[4],
                "domain_name": args[5],
                "status": args[6],
                "holding_id": args[7],
                "canonical_table": args[8],
                "canonical_id": args[9],
                "notes": args[10],
                "import_run_id": args[11],
            }
        elif 'INSERT INTO "raw_legacy".unsupported_history_holding' in query:
            key = (args[1], args[2], args[4], args[5], args[6])
            self._fake_holding_rows[key] = {
                "id": args[0],
                "tenant_id": args[1],
                "batch_id": args[2],
                "domain_name": args[3],
                "source_table": args[4],
                "source_identifier": args[5],
                "source_row_number": args[6],
            }
        elif 'DELETE FROM "raw_legacy".unsupported_history_holding' in query:
            key = (args[0], args[1], args[2], args[3], args[4])
            self._fake_holding_rows.pop(key, None)
        return "OK"

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_run_ap_payment_import_imports_verified_special_payments_and_holds_rest(
    monkeypatch,
) -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000501")
    supplier_id = ap_payment_import._tenant_scoped_uuid(tenant_id, "party", "supplier", "T008")
    connection = FakePaymentConnection(
        {
            "tbscust": [
                {"legacy_code": "T008", "legacy_type": "1"},
                {"legacy_code": "2530", "legacy_type": "2"},
            ],
            "supplier": [{"id": supplier_id}],
            "tbsspay": [
                {
                    "col_2": "SUP-PAY-001",
                    "col_4": "2016-05-05",
                    "col_6": "T008",
                    "col_8": "0001",
                    "col_10": "570.00000000",
                    "col_12": "CHK-001",
                    "col_18": "legacy ap payment",
                    "_source_row_number": 1,
                },
                {
                    "col_2": "CUS-PAY-002",
                    "col_4": "2016-05-06",
                    "col_6": "2530",
                    "col_8": "0001",
                    "col_10": "200.00000000",
                    "col_18": "customer receipt",
                    "_source_row_number": 2,
                },
            ],
            "tbsprepay": [
                {
                    "col_1": "1",
                    "col_2": "T008",
                    "col_3": "2",
                    "col_4": "0",
                    "col_5": "0001",
                    "col_7": "0.00000000",
                    "col_8": "0.00000000",
                    "col_10": "0.00000000",
                    "col_11": "0.00000000",
                    "col_12": "0.00000000",
                    "col_13": "0.00000000",
                    "_source_row_number": 3,
                }
            ],
        }
    )

    async def fake_open_raw_connection() -> FakePaymentConnection:
        return connection

    monkeypatch.setattr(ap_payment_import, "_open_raw_connection", fake_open_raw_connection)

    result = await ap_payment_import.run_ap_payment_import(
        batch_id="batch-ap-001",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.payment_count == 1
    assert result.allocation_count == 0
    assert result.holding_count == 2
    assert result.lineage_count == 1
    assert result.attempt_number == 1
    assert connection.transaction_started is True
    assert connection.transaction_committed is True
    assert connection.transaction_rolled_back is False
    assert connection.closed is True

    lock_index = next(
        index
        for index, (query, _args) in enumerate(connection.execute_calls)
        if "pg_advisory_xact_lock" in query
    )
    run_index = next(
        index
        for index, (query, _args) in enumerate(connection.execute_calls)
        if "INSERT INTO legacy_import_runs" in query
    )
    assert lock_index < run_index
    run_query = next(
        query for query, _args in connection.execute_calls if "INSERT INTO legacy_import_runs" in query
    )
    assert "$8::text" in run_query

    payment_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO supplier_payments" in query
    )
    assert payment_args[2] == supplier_id
    assert payment_args[3] == "SUP-PAY-001"
    assert payment_args[4] == "special_payment"
    assert payment_args[5] == "unapplied"
    assert str(payment_args[8]) == "570.00"
    assert str(payment_args[12]) == "570.00"
    assert payment_args[14] == "CHK-001"
    assert payment_args[15] == "legacy ap payment"

    holding_args = [
        args
        for query, args in connection.execute_calls
        if 'INSERT INTO "raw_legacy".unsupported_history_holding' in query
    ]
    assert len(holding_args) == 2
    customer_holding = next(args for args in holding_args if args[4] == "tbsspay")
    assert "customer role" in cast(str, customer_holding[8])
    customer_payload = json.loads(cast(str, customer_holding[7]))
    assert customer_payload["col_2"] == "CUS-PAY-002"

    prepay_holding = next(args for args in holding_args if args[4] == "tbsprepay")
    assert "no verified payment document number" in cast(str, prepay_holding[8])
    assert "all candidate prepayment amount fields are zero" in cast(str, prepay_holding[8])

    customer_resolution = connection._fake_resolution_rows[
        (tenant_id, "batch-ap-001", "tbsspay", "CUS-PAY-002", 2)
    ]
    assert customer_resolution["status"] == source_resolution.STATUS_HOLDING
    prepay_resolution = connection._fake_resolution_rows[
        (tenant_id, "batch-ap-001", "tbsprepay", "T008", 3)
    ]
    assert prepay_resolution["status"] == source_resolution.STATUS_HOLDING
    drained_resolution = connection._fake_resolution_rows[
        (tenant_id, "batch-ap-001", "tbsspay", "SUP-PAY-001", 1)
    ]
    assert drained_resolution["status"] == source_resolution.STATUS_RESOLVED
    assert drained_resolution["canonical_table"] == "supplier_payments"
    assert not any(key[2] == "__holding__" for key in connection._fake_lineage_rows)

    table_run_args = [
        args
        for query, args in connection.execute_calls
        if "INSERT INTO legacy_import_table_runs" in query
    ]
    table_run_query = next(
        query
        for query, _args in connection.execute_calls
        if "INSERT INTO legacy_import_table_runs" in query
    )
    assert "$8::text" in table_run_query
    assert all(isinstance(args[0], uuid.UUID) for args in table_run_args)
    assert any(
        args[2] == "tbsspay" and args[5] == 2 and args[7] == "completed"
        for args in table_run_args
    )
    assert any(
        args[2] == "tbsprepay" and args[5] == 1 and args[7] == "completed"
        for args in table_run_args
    )


# ---------------------------------------------------------------------------
# Story 15.21 — Drain path resolves held source state atomically
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_drain_path_resolves_existing_holding_state(monkeypatch) -> None:
    """A previously held AP payment row should resolve to canonical lineage,
    clear holding payload state, and update the current resolution row."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000503")
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
                    "col_2": "SUP-PAY-001",
                    "col_4": "2016-05-05",
                    "col_6": "T008",
                    "col_8": "0001",
                    "col_10": "570.00000000",
                    "col_12": "CHK-001",
                    "col_18": "legacy ap payment",
                    "_source_row_number": 1,
                },
            ],
            "tbsprepay": [],
        }
    )
    holding_id = source_resolution.build_holding_id(
        tenant_id,
        batch_id="batch-ap-drain",
        domain_name="payment_history",
        source_table="tbsspay",
        source_identifier="SUP-PAY-001",
        source_row_number=1,
        row_identity=1,
    )
    connection._fake_holding_rows[(tenant_id, "batch-ap-drain", "tbsspay", "SUP-PAY-001", 1)] = {
        "id": holding_id,
        "tenant_id": tenant_id,
        "batch_id": "batch-ap-drain",
        "domain_name": "payment_history",
        "source_table": "tbsspay",
        "source_identifier": "SUP-PAY-001",
        "source_row_number": 1,
    }
    connection._fake_resolution_rows[(tenant_id, "batch-ap-drain", "tbsspay", "SUP-PAY-001", 1)] = {
        "tenant_id": tenant_id,
        "batch_id": "batch-ap-drain",
        "source_table": "tbsspay",
        "source_identifier": "SUP-PAY-001",
        "source_row_number": 1,
        "domain_name": "payment_history",
        "status": source_resolution.STATUS_HOLDING,
        "holding_id": holding_id,
        "canonical_table": None,
        "canonical_id": None,
        "notes": "held before verification",
        "import_run_id": uuid.uuid4(),
    }

    async def fake_open_raw_connection() -> FakePaymentConnection:
        return connection

    monkeypatch.setattr(ap_payment_import, "_open_raw_connection", fake_open_raw_connection)

    result = await ap_payment_import.run_ap_payment_import(
        batch_id="batch-ap-drain",
        tenant_id=tenant_id,
        schema_name="raw_legacy",
    )

    assert result.payment_count == 1
    assert result.holding_count == 0
    assert result.lineage_count == 1

    lineage_keys_for_row = [
        key
        for key in connection._fake_lineage_rows
        if key[3] == "tbsspay" and key[4] == "SUP-PAY-001" and key[5] == 1
    ]
    assert len(lineage_keys_for_row) == 1, (
        f"Expected exactly 1 lineage entry for the drained row, got {len(lineage_keys_for_row)}"
    )

    _tenant_id, _batch_id, canonical_table, _source_table, _source_identifier, _source_row_number = (
        lineage_keys_for_row[0]
    )
    assert canonical_table == "supplier_payments"

    resolution_row = connection._fake_resolution_rows[
        (tenant_id, "batch-ap-drain", "tbsspay", "SUP-PAY-001", 1)
    ]
    assert resolution_row["status"] == source_resolution.STATUS_RESOLVED
    assert resolution_row["holding_id"] is None
    assert resolution_row["canonical_table"] == "supplier_payments"
    assert not connection._fake_holding_rows
    assert connection._fake_resolution_events[-1]["new_status"] == source_resolution.STATUS_RESOLVED


@pytest.mark.asyncio
async def test_run_ap_payment_import_requires_tbscust_stage(monkeypatch) -> None:
    connection = FakePaymentConnection({"tbsspay": []})

    async def fake_open_raw_connection() -> FakePaymentConnection:
        return connection

    monkeypatch.setattr(ap_payment_import, "_open_raw_connection", fake_open_raw_connection)

    with pytest.raises(ValueError, match="tbscust must be staged"):
        await ap_payment_import.run_ap_payment_import(
            batch_id="batch-ap-002",
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000502"),
            schema_name="raw_legacy",
        )