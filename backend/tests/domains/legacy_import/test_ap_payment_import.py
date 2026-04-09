from __future__ import annotations

import json
import uuid
from typing import cast

import pytest

import domains.legacy_import.ap_payment_import as ap_payment_import


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

    async def execute(self, query: str, *args: object) -> str:
        call = (query, args)
        self.execute_calls.append(call)
        if self.transaction_buffers:
            self.transaction_buffers[-1].append(call)
        else:
            self.committed_execute_calls.append(call)
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

    payment_args = next(
        args for query, args in connection.execute_calls if "INSERT INTO supplier_payments" in query
    )
    assert payment_args[2] == supplier_id
    assert payment_args[3] == "SUP-PAY-001"
    assert payment_args[4] == "special_payment"
    assert payment_args[5] == "unapplied"
    assert str(payment_args[8]) == "570.00"
    assert payment_args[10] == "CHK-001"
    assert payment_args[11] == "legacy ap payment"

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

    table_run_args = [
        args
        for query, args in connection.execute_calls
        if "INSERT INTO legacy_import_table_runs" in query
    ]
    assert any(
        args[1] == "tbsspay" and args[4] == 2 and args[6] == "completed"
        for args in table_run_args
    )
    assert any(
        args[1] == "tbsprepay" and args[4] == 1 and args[6] == "completed"
        for args in table_run_args
    )


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