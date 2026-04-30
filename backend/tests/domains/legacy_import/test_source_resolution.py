from __future__ import annotations

import copy
import json
import uuid

import pytest

import domains.legacy_import.source_resolution as source_resolution


class FakeResolutionTransaction:
    def __init__(self, connection: "FakeResolutionConnection") -> None:
        self.connection = connection
        self.buffer: list[tuple[str, tuple[object, ...]]] = []
        self._snapshot: tuple[
            dict[tuple[object, ...], dict[str, object]],
            list[dict[str, object]],
            dict[tuple[object, ...], dict[str, object]],
            dict[tuple[object, ...], dict[str, object]],
        ] | None = None

    async def __aenter__(self) -> "FakeResolutionTransaction":
        self.connection.transaction_started = True
        self.connection.transaction_buffers.append(self.buffer)
        self._snapshot = (
            copy.deepcopy(self.connection._fake_resolution_rows),
            copy.deepcopy(self.connection._fake_resolution_events),
            copy.deepcopy(self.connection._fake_holding_rows),
            copy.deepcopy(self.connection._fake_lineage_rows),
        )
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
            assert self._snapshot is not None
            (
                self.connection._fake_resolution_rows,
                self.connection._fake_resolution_events,
                self.connection._fake_holding_rows,
                self.connection._fake_lineage_rows,
            ) = self._snapshot
        return False


class FakeResolutionConnection:
    def __init__(self) -> None:
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.committed_execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.fetch_calls: list[tuple[str, tuple[object, ...]]] = []
        self.executemany_calls: list[tuple[str, list[tuple[object, ...]]]] = []
        self.transaction_buffers: list[list[tuple[str, tuple[object, ...]]]] = []
        self.transaction_started = False
        self.transaction_committed = False
        self.transaction_rolled_back = False
        self._fake_resolution_rows: dict[tuple[object, ...], dict[str, object]] = {}
        self._fake_resolution_events: list[dict[str, object]] = []
        self._fake_holding_rows: dict[tuple[object, ...], dict[str, object]] = {}
        self._fake_lineage_rows: dict[tuple[object, ...], dict[str, object]] = {}

    def transaction(self) -> FakeResolutionTransaction:
        return FakeResolutionTransaction(self)

    async def fetchrow(self, query: str, *args: object):
        if 'FROM "raw_legacy".source_row_resolution' in query:
            key = (args[0], args[1], args[2], args[3], args[4])
            row = self._fake_resolution_rows.get(key)
            return None if row is None else dict(row)
        return None

    async def fetch(self, query: str, *args: object):
        self.fetch_calls.append((query, args))
        if 'FROM "raw_legacy".source_row_resolution AS resolution' in query:
            tenant_id = args[0]
            batch_id = args[1]
            source_tables = list(args[2])
            source_identifiers = list(args[3])
            source_row_numbers = list(args[4])
            rows: list[dict[str, object]] = []
            for source_table, source_identifier, source_row_number in zip(
                source_tables,
                source_identifiers,
                source_row_numbers,
            ):
                key = (
                    tenant_id,
                    batch_id,
                    source_table,
                    source_identifier,
                    source_row_number,
                )
                payload = self._fake_resolution_rows.get(key)
                if payload is not None:
                    rows.append(dict(payload))
            return rows
        return []

    async def execute(self, query: str, *args: object) -> str:
        call = (query, args)
        self.execute_calls.append(call)
        if self.transaction_buffers:
            self.transaction_buffers[-1].append(call)
        else:
            self.committed_execute_calls.append(call)

        if 'INSERT INTO "raw_legacy".unsupported_history_holding' in query:
            key = (args[1], args[2], args[4], args[5], args[6])
            self._fake_holding_rows[key] = {
                "id": args[0],
                "tenant_id": args[1],
                "batch_id": args[2],
                "domain_name": args[3],
                "source_table": args[4],
                "source_identifier": args[5],
                "source_row_number": args[6],
                "payload": json.loads(args[7]),
                "notes": args[8],
                "import_run_id": args[9],
            }
        elif 'DELETE FROM "raw_legacy".unsupported_history_holding' in query:
            key = (args[0], args[1], args[2], args[3], args[4])
            self._fake_holding_rows.pop(key, None)
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
        elif 'INSERT INTO "raw_legacy".canonical_record_lineage' in query:
            key = (args[0], args[1], args[2], args[4], args[5], args[6])
            self._fake_lineage_rows[key] = {
                "canonical_id": args[3],
                "import_run_id": args[7],
            }
        return "OK"

    async def executemany(self, query: str, args_iterable) -> None:
        rows = [tuple(args) for args in args_iterable]
        self.executemany_calls.append((query, rows))
        for args in rows:
            await self.execute(query, *args)


def _identity_key(
    tenant_id: uuid.UUID,
    batch_id: str,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
) -> tuple[object, ...]:
    return (tenant_id, batch_id, source_table, source_identifier, source_row_number)


def test_build_holding_id_is_batch_scoped_and_stable() -> None:
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000720")

    first_batch_id = source_resolution.build_holding_id(
        tenant_id,
        batch_id="batch-holding-a",
        domain_name="payment_history",
        source_table="tbsspay",
        source_identifier="SUP-PAY-001",
        source_row_number=1,
        row_identity=1,
    )
    first_batch_replay_id = source_resolution.build_holding_id(
        tenant_id,
        batch_id="batch-holding-a",
        domain_name="payment_history",
        source_table="tbsspay",
        source_identifier="SUP-PAY-001",
        source_row_number=1,
        row_identity=1,
    )
    second_batch_id = source_resolution.build_holding_id(
        tenant_id,
        batch_id="batch-holding-b",
        domain_name="payment_history",
        source_table="tbsspay",
        source_identifier="SUP-PAY-001",
        source_row_number=1,
        row_identity=1,
    )

    assert first_batch_id == first_batch_replay_id
    assert first_batch_id != second_batch_id


async def _canonical_lineage_write(
    connection: FakeResolutionConnection,
    *,
    tenant_id: uuid.UUID,
    batch_id: str,
    run_id: uuid.UUID,
    source_table: str,
    source_identifier: str,
    source_row_number: int,
    canonical_table: str,
    canonical_id: uuid.UUID,
) -> None:
    await connection.execute(
        '''
        INSERT INTO "raw_legacy".canonical_record_lineage (
            tenant_id,
            batch_id,
            canonical_table,
            canonical_id,
            source_table,
            source_identifier,
            source_row_number,
            import_run_id
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ''',
        tenant_id,
        batch_id,
        canonical_table,
        canonical_id,
        source_table,
        source_identifier,
        source_row_number,
        run_id,
    )


@pytest.mark.asyncio
async def test_ensure_source_resolution_tables_create_state_and_event_tables() -> None:
    connection = FakeResolutionConnection()

    await source_resolution.ensure_source_resolution_tables(connection, "raw_legacy")

    ddl = "\n".join(query for query, _ in connection.execute_calls)
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".source_row_resolution' in ddl
    assert 'CREATE TABLE IF NOT EXISTS "raw_legacy".source_row_resolution_events' in ddl
    assert 'CHECK (status IN (' in ddl


@pytest.mark.asyncio
async def test_hold_transition_writes_current_state_and_event_without_lineage_sentinel() -> None:
    connection = FakeResolutionConnection()
    run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000721")
    holding_id = uuid.UUID("00000000-0000-0000-0000-000000000811")

    await source_resolution.hold_source_row(
        connection,
        schema_name="raw_legacy",
        run_id=run_id,
        tenant_id=tenant_id,
        batch_id="batch-resolution-hold",
        domain_name="payment_history",
        source_table="tbsspay",
        source_identifier="SUP-PAY-001",
        source_row_number=1,
        row_identity=1,
        holding_id=holding_id,
        payload={"col_2": "SUP-PAY-001"},
        notes="missing verified supplier mapping",
    )

    key = _identity_key(tenant_id, "batch-resolution-hold", "tbsspay", "SUP-PAY-001", 1)
    state_row = connection._fake_resolution_rows[key]
    assert state_row["status"] == source_resolution.STATUS_HOLDING
    assert state_row["holding_id"] == holding_id
    assert state_row["canonical_table"] is None
    assert len(connection._fake_resolution_events) == 1
    assert connection._fake_resolution_events[0]["previous_status"] is None
    assert connection._fake_resolution_events[0]["new_status"] == source_resolution.STATUS_HOLDING
    assert not any("__holding__" in query for query, _ in connection.execute_calls)


@pytest.mark.asyncio
async def test_hold_transition_is_idempotent_for_same_state() -> None:
    connection = FakeResolutionConnection()
    run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000722")
    holding_id = uuid.UUID("00000000-0000-0000-0000-000000000812")

    await source_resolution.hold_source_row(
        connection,
        schema_name="raw_legacy",
        run_id=run_id,
        tenant_id=tenant_id,
        batch_id="batch-resolution-idempotent",
        domain_name="receiving_audit",
        source_table="tbsslipdtj",
        source_identifier=":3",
        source_row_number=0,
        row_identity=3,
        holding_id=holding_id,
        payload={"doc_number": ""},
        notes="blank doc_number held",
    )
    await source_resolution.hold_source_row(
        connection,
        schema_name="raw_legacy",
        run_id=run_id,
        tenant_id=tenant_id,
        batch_id="batch-resolution-idempotent",
        domain_name="receiving_audit",
        source_table="tbsslipdtj",
        source_identifier=":3",
        source_row_number=0,
        row_identity=3,
        holding_id=holding_id,
        payload={"doc_number": ""},
        notes="blank doc_number held",
    )

    assert len(connection._fake_resolution_rows) == 1
    assert len(connection._fake_resolution_events) == 1


@pytest.mark.asyncio
async def test_resolve_transition_updates_state_appends_event_and_cleans_up_holding() -> None:
    connection = FakeResolutionConnection()
    hold_run_id = uuid.uuid4()
    resolve_run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000723")
    holding_id = uuid.UUID("00000000-0000-0000-0000-000000000813")
    canonical_id = uuid.UUID("00000000-0000-0000-0000-000000000913")

    await source_resolution.hold_source_row(
        connection,
        schema_name="raw_legacy",
        run_id=hold_run_id,
        tenant_id=tenant_id,
        batch_id="batch-resolution-drain",
        domain_name="payment_history",
        source_table="tbsspay",
        source_identifier="SUP-PAY-001",
        source_row_number=1,
        row_identity=1,
        holding_id=holding_id,
        payload={"col_2": "SUP-PAY-001"},
        notes="held before verification",
    )

    async def canonical_write() -> None:
        await _canonical_lineage_write(
            connection,
            tenant_id=tenant_id,
            batch_id="batch-resolution-drain",
            run_id=resolve_run_id,
            source_table="tbsspay",
            source_identifier="SUP-PAY-001",
            source_row_number=1,
            canonical_table="supplier_payments",
            canonical_id=canonical_id,
        )

    await source_resolution.resolve_source_row(
        connection,
        schema_name="raw_legacy",
        run_id=resolve_run_id,
        tenant_id=tenant_id,
        batch_id="batch-resolution-drain",
        domain_name="payment_history",
        source_table="tbsspay",
        source_identifier="SUP-PAY-001",
        source_row_number=1,
        canonical_table="supplier_payments",
        canonical_id=canonical_id,
        notes="drained to canonical supplier payment",
        canonical_write=canonical_write,
    )

    key = _identity_key(tenant_id, "batch-resolution-drain", "tbsspay", "SUP-PAY-001", 1)
    state_row = connection._fake_resolution_rows[key]
    assert state_row["status"] == source_resolution.STATUS_RESOLVED
    assert state_row["holding_id"] is None
    assert state_row["canonical_table"] == "supplier_payments"
    assert state_row["canonical_id"] == canonical_id
    assert not connection._fake_holding_rows
    assert [event["new_status"] for event in connection._fake_resolution_events] == [
        source_resolution.STATUS_HOLDING,
        source_resolution.STATUS_RESOLVED,
    ]


@pytest.mark.asyncio
async def test_resolve_transition_rolls_back_state_cleanup_and_event_on_failure() -> None:
    connection = FakeResolutionConnection()
    hold_run_id = uuid.uuid4()
    resolve_run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000724")
    holding_id = uuid.UUID("00000000-0000-0000-0000-000000000814")
    canonical_id = uuid.UUID("00000000-0000-0000-0000-000000000914")

    await source_resolution.hold_source_row(
        connection,
        schema_name="raw_legacy",
        run_id=hold_run_id,
        tenant_id=tenant_id,
        batch_id="batch-resolution-rollback",
        domain_name="payment_history",
        source_table="tbsspay",
        source_identifier="SUP-PAY-FAIL",
        source_row_number=2,
        row_identity=2,
        holding_id=holding_id,
        payload={"col_2": "SUP-PAY-FAIL"},
        notes="held before verification",
    )

    async def failing_canonical_write() -> None:
        await _canonical_lineage_write(
            connection,
            tenant_id=tenant_id,
            batch_id="batch-resolution-rollback",
            run_id=resolve_run_id,
            source_table="tbsspay",
            source_identifier="SUP-PAY-FAIL",
            source_row_number=2,
            canonical_table="supplier_payments",
            canonical_id=canonical_id,
        )
        raise RuntimeError("supplier payment insert failed")

    with pytest.raises(RuntimeError, match="supplier payment insert failed"):
        async with connection.transaction():
            await source_resolution.resolve_source_row(
                connection,
                schema_name="raw_legacy",
                run_id=resolve_run_id,
                tenant_id=tenant_id,
                batch_id="batch-resolution-rollback",
                domain_name="payment_history",
                source_table="tbsspay",
                source_identifier="SUP-PAY-FAIL",
                source_row_number=2,
                canonical_table="supplier_payments",
                canonical_id=canonical_id,
                notes="drained to canonical supplier payment",
                canonical_write=failing_canonical_write,
            )

    key = _identity_key(tenant_id, "batch-resolution-rollback", "tbsspay", "SUP-PAY-FAIL", 2)
    state_row = connection._fake_resolution_rows[key]
    assert state_row["status"] == source_resolution.STATUS_HOLDING
    assert state_row["holding_id"] == holding_id
    assert len(connection._fake_resolution_events) == 1
    assert connection._fake_resolution_events[0]["new_status"] == source_resolution.STATUS_HOLDING
    assert connection._fake_holding_rows
    assert not connection._fake_lineage_rows


@pytest.mark.asyncio
async def test_resolve_source_rows_batches_fetches_and_updates() -> None:
    connection = FakeResolutionConnection()
    run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000725")

    held_key = _identity_key(tenant_id, "batch-resolution-batch", "tbsspay", "SUP-PAY-001", 1)
    held_holding_id = uuid.UUID("00000000-0000-0000-0000-000000000815")
    connection._fake_resolution_rows[held_key] = {
        "tenant_id": tenant_id,
        "batch_id": "batch-resolution-batch",
        "source_table": "tbsspay",
        "source_identifier": "SUP-PAY-001",
        "source_row_number": 1,
        "domain_name": "payment_history",
        "status": source_resolution.STATUS_HOLDING,
        "holding_id": held_holding_id,
        "canonical_table": None,
        "canonical_id": None,
        "notes": "held before verification",
        "import_run_id": uuid.uuid4(),
    }
    connection._fake_holding_rows[(tenant_id, "batch-resolution-batch", "tbsspay", "SUP-PAY-001", 1)] = {
        "id": held_holding_id,
        "tenant_id": tenant_id,
        "batch_id": "batch-resolution-batch",
        "domain_name": "payment_history",
        "source_table": "tbsspay",
        "source_identifier": "SUP-PAY-001",
        "source_row_number": 1,
    }

    matching_id = uuid.UUID("00000000-0000-0000-0000-000000000915")
    matching_key = _identity_key(tenant_id, "batch-resolution-batch", "tbsslipx", "SO-001", 2)
    connection._fake_resolution_rows[matching_key] = {
        "tenant_id": tenant_id,
        "batch_id": "batch-resolution-batch",
        "source_table": "tbsslipx",
        "source_identifier": "SO-001",
        "source_row_number": 2,
        "domain_name": "orders",
        "status": source_resolution.STATUS_RESOLVED,
        "holding_id": None,
        "canonical_table": "orders",
        "canonical_id": matching_id,
        "notes": None,
        "import_run_id": uuid.uuid4(),
    }

    new_invoice_id = uuid.UUID("00000000-0000-0000-0000-000000000916")
    resolved_payment_id = uuid.UUID("00000000-0000-0000-0000-000000000917")

    await source_resolution.resolve_source_rows(
        connection,
        schema_name="raw_legacy",
        run_id=run_id,
        tenant_id=tenant_id,
        batch_id="batch-resolution-batch",
        rows=[
            source_resolution.ResolvedSourceRow(
                domain_name="payment_history",
                source_table="tbsspay",
                source_identifier="SUP-PAY-001",
                source_row_number=1,
                canonical_table="supplier_payments",
                canonical_id=resolved_payment_id,
                notes="drained to canonical supplier payment",
            ),
            source_resolution.ResolvedSourceRow(
                domain_name="orders",
                source_table="tbsslipx",
                source_identifier="SO-001",
                source_row_number=2,
                canonical_table="orders",
                canonical_id=matching_id,
            ),
            source_resolution.ResolvedSourceRow(
                domain_name="invoices",
                source_table="tbsslipx",
                source_identifier="INV-001",
                source_row_number=3,
                canonical_table="invoices",
                canonical_id=new_invoice_id,
                notes="resolved by canonical import",
            ),
        ],
    )

    assert len(connection.fetch_calls) == 1
    assert len(connection.executemany_calls) == 3

    delete_query, delete_rows = connection.executemany_calls[0]
    assert 'DELETE FROM "raw_legacy".unsupported_history_holding' in delete_query
    assert delete_rows == [
        (tenant_id, "batch-resolution-batch", "tbsspay", "SUP-PAY-001", 1)
    ]

    upsert_query, upsert_rows = connection.executemany_calls[1]
    assert 'INSERT INTO "raw_legacy".source_row_resolution' in upsert_query
    assert len(upsert_rows) == 2

    event_query, event_rows = connection.executemany_calls[2]
    assert 'INSERT INTO "raw_legacy".source_row_resolution_events' in event_query
    assert len(event_rows) == 2

    assert (tenant_id, "batch-resolution-batch", "tbsspay", "SUP-PAY-001", 1) not in connection._fake_holding_rows
    assert connection._fake_resolution_rows[held_key]["status"] == source_resolution.STATUS_RESOLVED
    assert connection._fake_resolution_rows[held_key]["canonical_table"] == "supplier_payments"
    new_key = _identity_key(tenant_id, "batch-resolution-batch", "tbsslipx", "INV-001", 3)
    assert connection._fake_resolution_rows[new_key]["status"] == source_resolution.STATUS_RESOLVED
    assert [event["new_status"] for event in connection._fake_resolution_events[-2:]] == [
        source_resolution.STATUS_RESOLVED,
        source_resolution.STATUS_RESOLVED,
    ]


@pytest.mark.asyncio
async def test_resolve_source_rows_clears_singular_pointer_for_multi_target_identity() -> None:
    connection = FakeResolutionConnection()
    run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000726")
    order_id = uuid.UUID("00000000-0000-0000-0000-000000000926")
    invoice_id = uuid.UUID("00000000-0000-0000-0000-000000000927")

    await source_resolution.resolve_source_rows(
        connection,
        schema_name="raw_legacy",
        run_id=run_id,
        tenant_id=tenant_id,
        batch_id="batch-multi-target",
        rows=[
            source_resolution.ResolvedSourceRow(
                domain_name="orders",
                source_table="tbsslipx",
                source_identifier="SO-INV-001",
                source_row_number=9,
                canonical_table="orders",
                canonical_id=order_id,
            ),
            source_resolution.ResolvedSourceRow(
                domain_name="invoices",
                source_table="tbsslipx",
                source_identifier="SO-INV-001",
                source_row_number=9,
                canonical_table="invoices",
                canonical_id=invoice_id,
            ),
        ],
    )

    state_key = _identity_key(tenant_id, "batch-multi-target", "tbsslipx", "SO-INV-001", 9)
    state_row = connection._fake_resolution_rows[state_key]
    assert state_row["status"] == source_resolution.STATUS_RESOLVED
    assert state_row["canonical_table"] is None
    assert state_row["canonical_id"] is None
    assert state_row["notes"] == (
        "Resolved to multiple canonical targets; consult canonical_record_lineage."
    )
    assert [event["canonical_table"] for event in connection._fake_resolution_events] == [
        "orders",
        "invoices",
    ]


@pytest.mark.asyncio
async def test_resolve_source_row_clears_singular_pointer_when_second_target_arrives() -> None:
    connection = FakeResolutionConnection()
    first_run_id = uuid.uuid4()
    second_run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000727")
    order_id = uuid.UUID("00000000-0000-0000-0000-000000000928")
    invoice_id = uuid.UUID("00000000-0000-0000-0000-000000000929")

    await source_resolution.resolve_source_row(
        connection,
        schema_name="raw_legacy",
        run_id=first_run_id,
        tenant_id=tenant_id,
        batch_id="batch-sequential-multi-target",
        domain_name="orders",
        source_table="tbsslipx",
        source_identifier="SO-INV-002",
        source_row_number=10,
        canonical_table="orders",
        canonical_id=order_id,
        notes=None,
    )
    await source_resolution.resolve_source_row(
        connection,
        schema_name="raw_legacy",
        run_id=second_run_id,
        tenant_id=tenant_id,
        batch_id="batch-sequential-multi-target",
        domain_name="invoices",
        source_table="tbsslipx",
        source_identifier="SO-INV-002",
        source_row_number=10,
        canonical_table="invoices",
        canonical_id=invoice_id,
        notes=None,
    )

    state_key = _identity_key(
        tenant_id,
        "batch-sequential-multi-target",
        "tbsslipx",
        "SO-INV-002",
        10,
    )
    state_row = connection._fake_resolution_rows[state_key]
    assert state_row["status"] == source_resolution.STATUS_RESOLVED
    assert state_row["canonical_table"] is None
    assert state_row["canonical_id"] is None
    assert state_row["notes"] == (
        "Resolved to multiple canonical targets; consult canonical_record_lineage."
    )