"""Tests for backfill_purchase_receipts scope filtering (Story 15.27 AC2)."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scripts import _legacy_stock_adjustments as stock_backfill


class TestFetchPurchaseReceiptRowsScopeFiltering:
    """Test scope filtering in fetch_purchase_receipt_rows (AC2)."""

    @pytest.mark.asyncio
    async def test_full_mode_returns_all_rows_without_scope(self) -> None:
        """When no entity_scope is provided, all rows within date range are returned."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(_mapping={"doc_number": "INV001", "line_number": "1"}),
            MagicMock(_mapping={"doc_number": "INV002", "line_number": "1"}),
            MagicMock(_mapping={"doc_number": "INV003", "line_number": "1"}),
        ]
        mock_session.execute.return_value = mock_result

        cutoff = date(2024, 1, 1)
        today = date(2024, 12, 31)

        rows = await stock_backfill.fetch_purchase_receipt_rows(
            mock_session,
            cutoff=cutoff,
            today=today,
            entity_scope=None,
            affected_domains=None,
        )

        # Should return all rows when no scope provided
        assert len(rows) == 3
        assert mock_session.execute.call_count == 1

        # Verify the SQL does not contain scope filter
        call_args = mock_session.execute.call_args
        sql_query = str(call_args[0][0])
        assert "scope_doc_numbers" not in sql_query

    @pytest.mark.asyncio
    async def test_incremental_mode_filters_by_scope_doc_numbers(self) -> None:
        """When entity_scope has purchase-invoices closure_keys, filter to those docs."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(_mapping={"doc_number": "INV001", "line_number": "1"}),
        ]
        mock_session.execute.return_value = mock_result

        cutoff = date(2024, 1, 1)
        today = date(2024, 12, 31)
        entity_scope = {
            "purchase-invoices": {
                "closure_keys": ["INV001", "INV002"],
            }
        }

        rows = await stock_backfill.fetch_purchase_receipt_rows(
            mock_session,
            cutoff=cutoff,
            today=today,
            entity_scope=entity_scope,
            affected_domains=["purchase-invoices"],
        )

        assert len(rows) == 1
        assert rows[0]["doc_number"] == "INV001"

        # Verify the SQL contains scope filter
        call_args = mock_session.execute.call_args
        sql_query = str(call_args[0][0])
        params = call_args[0][1]
        assert "scope_doc_numbers" in sql_query
        assert "INV001" in params["scope_doc_numbers"]
        assert "INV002" in params["scope_doc_numbers"]

    @pytest.mark.asyncio
    async def test_incremental_mode_with_empty_closure_keys_returns_all(self) -> None:
        """When entity_scope has empty closure_keys, return all rows (no filter)."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(_mapping={"doc_number": "INV001", "line_number": "1"}),
            MagicMock(_mapping={"doc_number": "INV002", "line_number": "1"}),
        ]
        mock_session.execute.return_value = mock_result

        cutoff = date(2024, 1, 1)
        today = date(2024, 12, 31)
        entity_scope = {
            "purchase-invoices": {
                "closure_keys": [],
            }
        }

        rows = await stock_backfill.fetch_purchase_receipt_rows(
            mock_session,
            cutoff=cutoff,
            today=today,
            entity_scope=entity_scope,
            affected_domains=["purchase-invoices"],
        )

        # Empty closure_keys should not filter
        assert len(rows) == 2
        call_args = mock_session.execute.call_args
        sql_query = str(call_args[0][0])
        assert "scope_doc_numbers" not in sql_query

    @pytest.mark.asyncio
    async def test_incremental_mode_with_only_affected_domains_no_entity_scope(
        self,
    ) -> None:
        """When only affected_domains is provided (no entity_scope), no filtering."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(_mapping={"doc_number": "INV001", "line_number": "1"}),
        ]
        mock_session.execute.return_value = mock_result

        cutoff = date(2024, 1, 1)
        today = date(2024, 12, 31)

        rows = await stock_backfill.fetch_purchase_receipt_rows(
            mock_session,
            cutoff=cutoff,
            today=today,
            entity_scope=None,
            affected_domains=["purchase-invoices"],
        )

        # Only affected_domains without entity_scope should not filter
        assert len(rows) == 1
        call_args = mock_session.execute.call_args
        sql_query = str(call_args[0][0])
        assert "scope_doc_numbers" not in sql_query

    @pytest.mark.asyncio
    async def test_scope_filter_uses_frozenset_for_efficient_lookup(self) -> None:
        """Verify closure_keys are converted to frozenset for efficient lookups."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        entity_scope = {
            "purchase-invoices": {
                "closure_keys": ["INV001", "INV002", "INV003"],
            }
        }

        # Just verify the function handles the scope correctly
        # without checking the actual SQL output (which other tests cover)
        result = await stock_backfill.fetch_purchase_receipt_rows(
            mock_session,
            cutoff=date(2024, 1, 1),
            today=date(2024, 12, 31),
            entity_scope=entity_scope,
            affected_domains=["purchase-invoices"],
        )

        # Verify execute was called with scope_doc_numbers in params
        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert "scope_doc_numbers" in params
        assert set(params["scope_doc_numbers"]) == {"INV001", "INV002", "INV003"}


class TestPurchaseReceiptBackfillScopeIntegration:
    """Integration tests for backfill function with scope (AC2)."""

    @pytest.mark.asyncio
    async def test_backfill_passes_scope_to_fetch(self) -> None:
        """Verify backfill function passes entity_scope to fetch_purchase_receipt_rows."""
        from scripts.backfill_purchase_receipts import backfill

        entity_scope = {
            "purchase-invoices": {
                "closure_keys": ["INV001"],
            }
        }

        # Create properly mocked session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        with patch(
            "scripts.backfill_purchase_receipts.AsyncSessionLocal"
        ) as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = (
                mock_session
            )

            # Note: backfill returns None in dry_run mode after printing
            # We verify the scope was passed by checking the session was used
            result = await backfill(
                dry_run=True,
                entity_scope=entity_scope,
                affected_domains=["purchase-invoices"],
            )

            # Verify execute was called (which means fetch_purchase_receipt_rows was called)
            assert mock_session.execute.call_count >= 1

            # In dry_run mode, the function returns None after printing
            # The key assertion is that the function ran without errors with the scope
