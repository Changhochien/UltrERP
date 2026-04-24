"""Tests for backfill_invoice_unit_cost scope filtering (Story 15.27 AC2)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domains.invoices.service import (
    InvoiceUnitCostBackfillSummary,
    backfill_missing_invoice_line_unit_costs,
    _invoice_unit_cost_backfill_decisions_cte,
)


class TestInvoiceUnitCostBackfillDecisionsCTE:
    """Test scope filtering in the invoice unit cost CTE (AC2)."""

    def test_cte_without_scope_has_no_product_filter(self) -> None:
        """When scoped_product_ids is None, no product filter is added."""
        cte = _invoice_unit_cost_backfill_decisions_cte(
            scoped_to_tenant=True,
            seek_after_invoice_line_id=False,
            scoped_product_ids=None,
        )

        # The WHERE clause should not contain scoped_product_ids filter
        assert "il.product_id = ANY(:scoped_product_ids)" not in cte

    def test_cte_with_scope_adds_product_filter(self) -> None:
        """When scoped_product_ids is provided, product filter is added."""
        product_ids = frozenset([uuid.uuid4(), uuid.uuid4()])
        cte = _invoice_unit_cost_backfill_decisions_cte(
            scoped_to_tenant=True,
            seek_after_invoice_line_id=False,
            scoped_product_ids=product_ids,
        )

        # The CTE should contain the scoped_product_ids filter
        assert "il.product_id = ANY(:scoped_product_ids)" in cte


class TestBackfillMissingInvoiceLineUnitCostsScopeFiltering:
    """Test scope filtering in backfill_missing_invoice_line_unit_costs (AC2).

    Note: These tests use mocks that return candidate_count=0 to avoid infinite loops.
    The actual scope filtering behavior is tested via CTE tests above.
    """

    @pytest.mark.asyncio
    async def test_full_mode_without_scope_processes_all_candidates(self) -> None:
        """When no entity_scope, all candidates are processed."""
        mock_session = AsyncMock(spec=AsyncSession)
        # Return 0 candidates to exit loop immediately
        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(
            candidate_count=0,
            updated_count=0,
            unmatched_count=0,
            ambiguous_count=0,
            last_invoice_line_id=None,
        )
        mock_session.execute.return_value = mock_result

        summary = await backfill_missing_invoice_line_unit_costs(
            mock_session,
            tenant_id=uuid.uuid4(),
            dry_run=True,
            entity_scope=None,
            affected_domains=None,
        )

        assert summary.candidate_count == 0
        # Verify the CTE was called without scope
        mock_session.execute.assert_called()
        call_args = mock_session.execute.call_args_list
        # Check the params don't include scoped_product_ids
        params = call_args[0][0][1]
        assert "scoped_product_ids" not in params

    @pytest.mark.asyncio
    async def test_incremental_mode_with_products_scope_filters_candidates(
        self,
    ) -> None:
        """When entity_scope has products closure_keys, filter to those products."""
        mock_session = AsyncMock(spec=AsyncSession)
        product_ids = [uuid.uuid4(), uuid.uuid4()]

        # Return 0 candidates to exit loop immediately
        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(
            candidate_count=0,
            updated_count=0,
            unmatched_count=0,
            ambiguous_count=0,
            last_invoice_line_id=None,
        )
        mock_session.execute.return_value = mock_result

        entity_scope = {
            "products": {
                "closure_keys": [str(pid) for pid in product_ids],
            }
        }

        summary = await backfill_missing_invoice_line_unit_costs(
            mock_session,
            tenant_id=uuid.uuid4(),
            dry_run=True,
            entity_scope=entity_scope,
            affected_domains=["products"],
        )

        assert summary.candidate_count == 0

        # Verify scoped_product_ids was passed in params
        call_args = mock_session.execute.call_args_list
        found_scope = False
        for call in call_args:
            params = call[0][1]
            if "scoped_product_ids" in params:
                assert set(params["scoped_product_ids"]) == set(product_ids)
                found_scope = True
                break
        assert found_scope, "scoped_product_ids should be in params for incremental mode"

    @pytest.mark.asyncio
    async def test_incremental_mode_ignores_non_products_domain(self) -> None:
        """Only 'products' domain closure_keys are used for filtering."""
        mock_session = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(
            candidate_count=0,
            updated_count=0,
            unmatched_count=0,
            ambiguous_count=0,
            last_invoice_line_id=None,
        )
        mock_session.execute.return_value = mock_result

        entity_scope = {
            "sales": {
                "closure_keys": ["some-sales-key"],
            },
            "parties": {
                "closure_keys": ["some-party-key"],
            },
        }

        summary = await backfill_missing_invoice_line_unit_costs(
            mock_session,
            tenant_id=uuid.uuid4(),
            dry_run=True,
            entity_scope=entity_scope,
            affected_domains=["sales", "parties"],
        )

        # No products domain in scope, so no filtering applied
        assert summary.candidate_count == 0
        call_args = mock_session.execute.call_args_list
        # Check that scoped_product_ids was not added to params
        has_scope_in_params = False
        for call in call_args:
            params = call[0][1]
            if "scoped_product_ids" in params:
                has_scope_in_params = True
                break
        assert not has_scope_in_params, "Should not filter when products domain is absent"

    @pytest.mark.asyncio
    async def test_incremental_mode_with_empty_closure_keys_no_filter(self) -> None:
        """When products closure_keys is empty, no filtering is applied."""
        mock_session = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(
            candidate_count=0,
            updated_count=0,
            unmatched_count=0,
            ambiguous_count=0,
            last_invoice_line_id=None,
        )
        mock_session.execute.return_value = mock_result

        entity_scope = {
            "products": {
                "closure_keys": [],
            }
        }

        summary = await backfill_missing_invoice_line_unit_costs(
            mock_session,
            tenant_id=uuid.uuid4(),
            dry_run=True,
            entity_scope=entity_scope,
            affected_domains=["products"],
        )

        # Empty closure_keys should not filter
        assert summary.candidate_count == 0
        call_args = mock_session.execute.call_args_list
        has_scope_in_params = False
        for call in call_args:
            params = call[0][1]
            if "scoped_product_ids" in params:
                has_scope_in_params = True
                break
        assert not has_scope_in_params

    @pytest.mark.asyncio
    async def test_incremental_mode_with_only_affected_domains_no_entity_scope(
        self,
    ) -> None:
        """When only affected_domains is provided (no entity_scope), no filtering."""
        mock_session = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(
            candidate_count=0,
            updated_count=0,
            unmatched_count=0,
            ambiguous_count=0,
            last_invoice_line_id=None,
        )
        mock_session.execute.return_value = mock_result

        summary = await backfill_missing_invoice_line_unit_costs(
            mock_session,
            tenant_id=uuid.uuid4(),
            dry_run=True,
            entity_scope=None,
            affected_domains=["products"],
        )

        assert summary.candidate_count == 0
        call_args = mock_session.execute.call_args_list
        has_scope_in_params = False
        for call in call_args:
            params = call[0][1]
            if "scoped_product_ids" in params:
                has_scope_in_params = True
                break
        assert not has_scope_in_params


class TestInvoiceUnitCostBackfillScriptIntegration:
    """Integration tests for backfill_invoice_unit_cost script with scope (AC2)."""

    @pytest.mark.asyncio
    async def test_script_passes_scope_to_service(self) -> None:
        """Verify script passes entity_scope to backfill_missing_invoice_line_unit_costs."""
        from scripts.backfill_invoice_unit_cost import backfill

        product_ids = [uuid.uuid4(), uuid.uuid4()]
        entity_scope = {
            "products": {
                "closure_keys": [str(pid) for pid in product_ids],
            }
        }

        with patch(
            "scripts.backfill_invoice_unit_cost.backfill_missing_invoice_line_unit_costs",
            new_callable=AsyncMock,
        ) as mock_backfill, \
        patch(
            "scripts.backfill_invoice_unit_cost.AsyncSessionLocal"
        ) as mock_session_local:
            mock_backfill.return_value = InvoiceUnitCostBackfillSummary(
                candidate_count=0,
                updated_count=0,
                skipped_count=0,
                unmatched_count=0,
                ambiguous_count=0,
                previews=[],
            )
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session_local.return_value.__aenter__.return_value = (
                mock_session
            )

            result = await backfill(
                dry_run=True,
                entity_scope=entity_scope,
                affected_domains=["products"],
            )

            # Verify service was called with scope
            mock_backfill.assert_called_once()
            call_kwargs = mock_backfill.call_args.kwargs
            assert call_kwargs["entity_scope"] == entity_scope
            assert call_kwargs["affected_domains"] == ["products"]

            assert result["batch_mode"] == "incremental"
            assert result["scoped_entity_count"] == 2

    @pytest.mark.asyncio
    async def test_script_full_mode_without_scope(self) -> None:
        """Verify script works without scope (full mode)."""
        from scripts.backfill_invoice_unit_cost import backfill

        with patch(
            "scripts.backfill_invoice_unit_cost.backfill_missing_invoice_line_unit_costs",
            new_callable=AsyncMock,
        ) as mock_backfill, \
        patch(
            "scripts.backfill_invoice_unit_cost.AsyncSessionLocal"
        ) as mock_session_local:
            mock_backfill.return_value = InvoiceUnitCostBackfillSummary(
                candidate_count=0,
                updated_count=0,
                skipped_count=0,
                unmatched_count=0,
                ambiguous_count=0,
                previews=[],
            )
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session_local.return_value.__aenter__.return_value = (
                mock_session
            )

            result = await backfill(
                dry_run=True,
                entity_scope=None,
                affected_domains=None,
            )

            mock_backfill.assert_called_once()
            call_kwargs = mock_backfill.call_args.kwargs
            assert call_kwargs["entity_scope"] is None
            assert call_kwargs["affected_domains"] is None

            assert result["batch_mode"] == "full"
