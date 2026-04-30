from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime

from domains.legacy_import import live_delta_projection


def test_master_cursor_clause_binds_datetime_watermark() -> None:
    where_clause, params = live_delta_projection._master_cursor_clause(
        change_ts_expr="src.change_ts",
        code_exprs=("src.party_code",),
        watermark={
            "source-change-ts": "2026-04-22T02:53:59.500587+00:00",
            "party-code": "CUST-001",
        },
        timestamp_key="source-change-ts",
        code_keys=("party-code",),
        bootstrap_anchor=None,
    )

    assert where_clause
    assert params == [
        datetime(2026, 4, 22, 2, 53, 59, 500587, tzinfo=UTC),
        "CUST-001",
    ]


def test_master_cursor_clause_binds_datetime_bootstrap_anchor() -> None:
    anchor = datetime(2026, 4, 22, 2, 53, 59, 500587, tzinfo=UTC)

    where_clause, params = live_delta_projection._master_cursor_clause(
        change_ts_expr="src.change_ts",
        code_exprs=("src.party_code",),
        watermark=None,
        timestamp_key="source-change-ts",
        code_keys=("party-code",),
        bootstrap_anchor=anchor,
    )

    assert where_clause
    assert params == [anchor]


def test_document_cursor_clause_binds_date_watermark() -> None:
    header_where, detail_where, params = live_delta_projection._document_cursor_clause(
        header_alias="hdr",
        detail_alias="dtl",
        watermark={
            "document-date": "2026-04-18",
            "document-number": "SO-0009",
            "line-number": 1,
        },
        bootstrap_anchor=None,
        header_change_ts_expr="hdr.change_ts",
    )

    assert header_where
    assert detail_where
    assert params == [date(2026, 4, 18), "SO-0009", 1]


def test_change_ts_expression_clamps_legacy_timestamp_ranges() -> None:
    expression = live_delta_projection._change_ts_expression(
        "src",
        timestamp_column="stimestamp",
        modify_column="dtmodify",
    )

    assert "BETWEEN '1900' AND '9999'" in expression
    assert str(live_delta_projection._MAX_EXCEL_SERIAL) in expression


def test_format_change_ts_falls_back_for_out_of_range_text() -> None:
    assert live_delta_projection._format_change_ts("294276-01-01 00:00:00+00") == (
        live_delta_projection._DEFAULT_CHANGE_TS.isoformat(timespec="microseconds")
    )


def test_fetch_current_incremental_watermarks_reads_latest_domain_cursors(monkeypatch) -> None:
    async def fake_fetch_records(*, query, parameters, connection_settings):
        assert parameters == []
        if "inventory_watermarks" in query:
            return [
                {
                    "change_ts_text": "2026-04-27 08:09:18.000168+00",
                    "warehouse_code": "A",
                    "product_code": "BO108",
                }
            ]
        if "document_watermarks" in query and '"tbsslipx"' in query:
            return [
                {
                    "document_date": date(2026, 5, 4),
                    "document_number": "1150504007",
                    "line_number": 6,
                }
            ]
        if "document_watermarks" in query and '"tbsslipj"' in query:
            return [
                {
                    "document_date": date(2026, 4, 29),
                    "document_number": "1150429001",
                    "line_number": 2,
                }
            ]
        if '"tbscust"' in query:
            return [
                {
                    "change_ts_text": "2026-04-30 01:19:19.000974+00",
                    "code_value": "2717",
                }
            ]
        if '"tbsstock"' in query:
            return [
                {
                    "change_ts_text": "2026-04-27 08:09:18.000168+00",
                    "code_value": "BO108",
                }
            ]
        if '"tbsstkhouse"' in query:
            return [
                {
                    "change_ts_text": "2026-04-20 00:00:00.000000+00",
                    "code_value": "A",
                }
            ]
        return []

    monkeypatch.setattr(live_delta_projection, "_fetch_records", fake_fetch_records)

    watermarks = asyncio.run(
        live_delta_projection.fetch_current_incremental_watermarks(source_schema="public")
    )

    assert watermarks["sales"] == {
        "document-date": "2026-05-04",
        "document-number": "1150504007",
        "line-number": 6,
    }
    assert watermarks["purchase-invoices"] == {
        "document-date": "2026-04-29",
        "document-number": "1150429001",
        "line-number": 2,
    }
    assert watermarks["inventory"] == {
        "source-change-ts": "2026-04-27T08:09:18.000168+00:00",
        "warehouse-code": "A",
        "product-code": "BO108",
    }


def test_fetch_staged_incremental_watermarks_reads_full_batch_cursors(monkeypatch) -> None:
    class FakeRawConnection:
        closed = False

        async def fetch(self, query, *args):
            assert args == ("legacy-shadow-20260430T065740Z",)
            if "inventory_watermarks" in query:
                return [
                    {
                        "change_ts_text": "2026-04-27 08:09:18.000168+00",
                        "warehouse_code": "A",
                        "product_code": "BO108",
                    }
                ]
            if "document_watermarks" in query and '"tbsslipx"' in query:
                return [
                    {
                        "document_date": date(2026, 5, 4),
                        "document_number": "1150504007",
                        "line_number": 6,
                    }
                ]
            if "document_watermarks" in query and '"tbsslipj"' in query:
                return [
                    {
                        "document_date": date(2026, 4, 29),
                        "document_number": "1150429001",
                        "line_number": 2,
                    }
                ]
            if '"tbscust"' in query:
                return [
                    {
                        "change_ts_text": "2026-04-30 01:19:19.000974+00",
                        "code_value": "2717",
                    }
                ]
            if '"tbsstock"' in query:
                return [
                    {
                        "change_ts_text": "2026-04-27 08:09:18.000168+00",
                        "code_value": "BO108",
                    }
                ]
            if '"tbsstkhouse"' in query:
                return [
                    {
                        "change_ts_text": "2026-04-20 00:00:00.000000+00",
                        "code_value": "A",
                    }
                ]
            return []

        async def close(self):
            self.closed = True

    raw_connection = FakeRawConnection()

    async def fake_load_source_stage_column_map(**kwargs):
        assert kwargs["source_schema"] == "public"
        return {
            "tbscust": {
                "scustno": "col_1",
                "stimestamp": "col_2",
                "dtmodify": "col_3",
                "dtcreatedate": "col_4",
            },
            "tbsstock": {
                "sstkno": "col_1",
                "stimestamp": "col_2",
                "dtmodify": "col_3",
                "dtindate": "col_4",
            },
            "tbsstkhouse": {
                "sstkno": "col_1",
                "shouseno": "col_2",
                "stimestamp": "col_3",
            },
            "tbsslipx": {"skind": "col_1", "sslipno": "col_2", "dtslipdate": "col_3"},
            "tbsslipdtx": {
                "skind": "col_1",
                "sslipno": "col_2",
                "dtslipdate": "col_3",
                "iidno": "col_4",
            },
            "tbsslipj": {"skind": "col_1", "sslipno": "col_2", "dtslipdate": "col_3"},
            "tbsslipdtj": {
                "skind": "col_1",
                "sslipno": "col_2",
                "dtslipdate": "col_3",
                "iidno": "col_4",
            },
        }

    async def fake_open_raw_connection():
        return raw_connection

    monkeypatch.setattr(
        live_delta_projection,
        "_load_source_stage_column_map",
        fake_load_source_stage_column_map,
    )
    monkeypatch.setattr(live_delta_projection, "_open_raw_connection", fake_open_raw_connection)

    watermarks = asyncio.run(
        live_delta_projection.fetch_staged_incremental_watermarks(
            schema_name="raw_legacy",
            source_schema="public",
            batch_id="legacy-shadow-20260430T065740Z",
        )
    )

    assert raw_connection.closed is True
    assert watermarks["sales"] == {
        "document-date": "2026-05-04",
        "document-number": "1150504007",
        "line-number": 6,
    }
    assert watermarks["purchase-invoices"] == {
        "document-date": "2026-04-29",
        "document-number": "1150429001",
        "line-number": 2,
    }