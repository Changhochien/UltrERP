"""Tests for sales reservation stock backfill scope filtering."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scripts import _legacy_stock_adjustments as stock_backfill
from scripts import backfill_sales_reservations


class TestFetchSalesRowsScopeFiltering:
    @pytest.mark.asyncio
    async def test_full_mode_returns_all_rows_without_scope(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(_mapping={"doc_number": "SO001", "line_number": "1"}),
            MagicMock(_mapping={"doc_number": "SO002", "line_number": "1"}),
        ]
        mock_session.execute.return_value = mock_result

        rows = await stock_backfill.fetch_sales_rows(
            mock_session,
            cutoff=date(2024, 1, 1),
            today=date(2024, 12, 31),
            entity_scope=None,
            affected_domains=None,
        )

        assert len(rows) == 2
        sql_query = str(mock_session.execute.call_args[0][0])
        assert "scope_doc_numbers" not in sql_query

    @pytest.mark.asyncio
    async def test_incremental_mode_filters_by_scope_doc_numbers(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(_mapping={"doc_number": "SO001", "line_number": "1"}),
        ]
        mock_session.execute.return_value = mock_result
        entity_scope = {
            "sales": {
                "closure_keys": [
                    {"document_number": "SO001"},
                    {"document-number": "SO002"},
                ],
            }
        }

        rows = await stock_backfill.fetch_sales_rows(
            mock_session,
            cutoff=date(2024, 1, 1),
            today=date(2024, 12, 31),
            entity_scope=entity_scope,
            affected_domains=["sales"],
        )

        assert len(rows) == 1
        assert rows[0]["doc_number"] == "SO001"
        sql_query = str(mock_session.execute.call_args[0][0])
        params = mock_session.execute.call_args[0][1]
        assert "scope_doc_numbers" in sql_query
        assert "SO001" in params["scope_doc_numbers"]
        assert "SO002" in params["scope_doc_numbers"]

    @pytest.mark.asyncio
    async def test_backfill_passes_entity_scope_to_fetch_sales_rows(self, monkeypatch) -> None:
        captured: dict[str, object] = {}
        entity_scope = {"sales": {"closure_keys": [{"document_number": "SO001"}]}}

        async def fake_fetch_product_mappings(*args, **kwargs):
            return {}

        async def fake_fetch_product_by_code(*args, **kwargs):
            return {}

        async def fake_fetch_warehouse_by_code(*args, **kwargs):
            return {}

        async def fake_fetch_sales_rows(*args, **kwargs):
            captured.update(kwargs)
            return []

        async def fake_count_legacy_sales_redundancies(*args, **kwargs):
            return 0

        class FakeSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr(
            backfill_sales_reservations,
            "AsyncSessionLocal",
            lambda: FakeSession(),
        )
        monkeypatch.setattr(
            backfill_sales_reservations,
            "fetch_product_mappings",
            fake_fetch_product_mappings,
        )
        monkeypatch.setattr(
            backfill_sales_reservations,
            "fetch_product_by_code",
            fake_fetch_product_by_code,
        )
        monkeypatch.setattr(
            backfill_sales_reservations,
            "fetch_warehouse_by_code",
            fake_fetch_warehouse_by_code,
        )
        monkeypatch.setattr(
            backfill_sales_reservations,
            "fetch_sales_rows",
            fake_fetch_sales_rows,
        )
        monkeypatch.setattr(
            backfill_sales_reservations,
            "count_legacy_sales_redundancies",
            fake_count_legacy_sales_redundancies,
        )

        await backfill_sales_reservations.backfill(
            lookback_days=10,
            dry_run=True,
            entity_scope=entity_scope,
            affected_domains=["sales"],
        )

        assert captured["entity_scope"] == entity_scope
        assert captured["affected_domains"] == ["sales"]
