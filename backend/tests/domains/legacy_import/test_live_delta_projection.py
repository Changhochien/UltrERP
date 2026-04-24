from __future__ import annotations

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