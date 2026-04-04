"""Tests for customer MCP tools (Story 8.2)."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.exceptions import ToolError

from domains.customers.mcp import (
	customers_get,
	customers_list,
	customers_lookup_by_ban,
)

# Access underlying function from FunctionTool wrapper.
_list_fn = customers_list.fn
_get_fn = customers_get.fn
_lookup_fn = customers_lookup_by_ban.fn

_CID = str(uuid.uuid4())
_NOW = datetime.now(tz=UTC)


@dataclass
class FakeCustomer:
	"""Minimal Customer stand-in for serialization tests."""

	id: uuid.UUID = field(default_factory=uuid.uuid4)
	company_name: str = "Test Corp"
	normalized_business_number: str = "12345675"
	billing_address: str = "Taipei"
	contact_name: str = "Jane"
	contact_phone: str = "02-12345678"
	contact_email: str = "jane@test.com"
	credit_limit: Decimal = Decimal("50000.00")
	status: str = "active"
	version: int = 1
	created_at: datetime = field(default_factory=lambda: _NOW)
	updated_at: datetime = field(default_factory=lambda: _NOW)


class FakeSession:
	async def __aenter__(self):
		return self

	async def __aexit__(self, *args):
		pass


def _patch_session():
	return patch("domains.customers.mcp.AsyncSessionLocal", return_value=FakeSession())


@dataclass
class FakeValidationResult:
	valid: bool
	error: str | None = None


# ── Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_customers_list_returns_paginated_results():
	"""AC1: customers_list returns paginated customer list."""
	fake = FakeCustomer()
	with (
		_patch_session(),
		patch(
			"domains.customers.mcp.list_customers",
			new_callable=AsyncMock,
			return_value=([fake], 1),
		),
	):
		result = await _list_fn()

	assert result["total"] == 1
	assert result["page"] == 1
	assert len(result["customers"]) == 1
	assert result["customers"][0]["company_name"] == "Test Corp"


@pytest.mark.asyncio
async def test_customers_list_with_search():
	"""AC1: customers_list passes search parameter correctly."""
	with (
		_patch_session(),
		patch(
			"domains.customers.mcp.list_customers",
			new_callable=AsyncMock,
			return_value=([], 0),
		) as mock_list,
	):
		result = await _list_fn(search="Test", status="active", page=2, page_size=10)

	assert result["total"] == 0
	params = mock_list.call_args[0][1]
	assert params.q == "Test"
	assert params.status == "active"
	assert params.page == 2


@pytest.mark.asyncio
async def test_customers_get_returns_customer():
	"""AC2: customers_get returns full customer details."""
	fake = FakeCustomer(id=uuid.UUID(_CID))
	with (
		_patch_session(),
		patch("domains.customers.mcp.get_customer", new_callable=AsyncMock, return_value=fake),
	):
		result = await _get_fn(customer_id=_CID)

	assert result["id"] == _CID
	assert result["company_name"] == "Test Corp"
	assert result["credit_limit"] == "50000.00"


@pytest.mark.asyncio
async def test_customers_get_raises_not_found():
	"""AC4: customers_get raises ToolError for non-existent ID."""
	with (
		_patch_session(),
		patch("domains.customers.mcp.get_customer", new_callable=AsyncMock, return_value=None),
	):
		with pytest.raises(ToolError) as exc_info:
			await _get_fn(customer_id=_CID)

	error = json.loads(str(exc_info.value))
	assert error["code"] == "NOT_FOUND"
	assert error["entity_type"] == "customer"


@pytest.mark.asyncio
async def test_customers_lookup_by_ban_returns_customer():
	"""AC3: customers_lookup_by_ban returns customer for valid BAN."""
	fake = FakeCustomer()
	with (
		_patch_session(),
		patch(
			"domains.customers.mcp.validate_taiwan_business_number",
			return_value=FakeValidationResult(valid=True),
		),
		patch(
			"domains.customers.mcp.lookup_customer_by_ban",
			new_callable=AsyncMock,
			return_value=fake,
		),
	):
		result = await _lookup_fn(business_number="12345675")

	assert result["company_name"] == "Test Corp"


@pytest.mark.asyncio
async def test_customers_lookup_by_ban_invalid_checksum():
	"""AC3: customers_lookup_by_ban raises VALIDATION_ERROR for invalid BAN."""
	with (
		patch(
			"domains.customers.mcp.validate_taiwan_business_number",
			return_value=FakeValidationResult(valid=False, error="Bad checksum"),
		),
	):
		with pytest.raises(ToolError) as exc_info:
			await _lookup_fn(business_number="00000000")

	error = json.loads(str(exc_info.value))
	assert error["code"] == "VALIDATION_ERROR"
	assert error["field"] == "business_number"


@pytest.mark.asyncio
async def test_customers_lookup_by_ban_not_found():
	"""AC3: customers_lookup_by_ban raises NOT_FOUND for valid but non-existent BAN."""
	with (
		_patch_session(),
		patch(
			"domains.customers.mcp.validate_taiwan_business_number",
			return_value=FakeValidationResult(valid=True),
		),
		patch(
			"domains.customers.mcp.lookup_customer_by_ban",
			new_callable=AsyncMock,
			return_value=None,
		),
	):
		with pytest.raises(ToolError) as exc_info:
			await _lookup_fn(business_number="12345675")

	error = json.loads(str(exc_info.value))
	assert error["code"] == "NOT_FOUND"
	assert error["entity_type"] == "customer"
