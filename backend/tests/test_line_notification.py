"""Tests for LINE notification service (Story 9.1)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── push_text_message tests ──────────────────────────────────


@pytest.fixture
def _mock_settings_configured():
	"""Patch get_settings to return configured LINE settings."""
	mock = MagicMock()
	mock.line_channel_access_token = "test-token"
	mock.line_staff_group_id = "Cxxxxxx"
	with patch("domains.line.client.get_settings", return_value=mock):
		yield mock


@pytest.fixture
def _mock_settings_unconfigured():
	"""Patch get_settings to return unconfigured LINE settings."""
	mock = MagicMock()
	mock.line_channel_access_token = None
	mock.line_staff_group_id = None
	with patch("domains.line.client.get_settings", return_value=mock):
		yield mock


async def test_push_text_message_success(_mock_settings_configured):
	mock_api = AsyncMock()
	mock_api.push_message = AsyncMock(return_value=None)

	with patch("domains.line.client.AsyncApiClient") as mock_client_cls:
		mock_client_instance = AsyncMock()
		mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
		mock_client_instance.__aexit__ = AsyncMock(return_value=False)
		mock_client_cls.return_value = mock_client_instance

		with patch("domains.line.client.AsyncMessagingApi", return_value=mock_api):
			from domains.line.client import push_text_message

			result = await push_text_message("U1234", "Hello")
			assert result is True
			mock_api.push_message.assert_called_once()
			call_args = mock_api.push_message.call_args[0][0]
			assert call_args.to == "U1234"
			assert call_args.messages[0].text == "Hello"


async def test_push_text_message_unconfigured(_mock_settings_unconfigured):
	from domains.line.client import push_text_message

	result = await push_text_message("U1234", "Hello")
	assert result is False


async def test_push_text_message_api_error(_mock_settings_configured):
	mock_api = AsyncMock()
	mock_api.push_message = AsyncMock(side_effect=RuntimeError("API down"))

	with patch("domains.line.client.AsyncApiClient") as mock_client_cls:
		mock_client_instance = AsyncMock()
		mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
		mock_client_instance.__aexit__ = AsyncMock(return_value=False)
		mock_client_cls.return_value = mock_client_instance

		with patch("domains.line.client.AsyncMessagingApi", return_value=mock_api):
			from domains.line.client import push_text_message

			result = await push_text_message("U1234", "Hello")
			assert result is False


# ── notify_new_order tests ───────────────────────────────────


async def test_notify_new_order_sends_message():
	mock_settings = MagicMock()
	mock_settings.line_staff_group_id = "Cxxxxxx"

	with (
		patch("domains.line.notification.get_settings", return_value=mock_settings),
		patch("domains.line.notification.push_text_message", new_callable=AsyncMock) as mock_push,
	):
		mock_push.return_value = True
		from domains.line.notification import notify_new_order

		await notify_new_order(
			order_number="ORD-001",
			customer_name="Test Corp",
			total_amount="1500",
			line_count=3,
		)
		mock_push.assert_called_once()
		call_args = mock_push.call_args
		assert call_args[0][0] == "Cxxxxxx"
		text = call_args[0][1]
		assert "ORD-001" in text
		assert "Test Corp" in text
		assert "3" in text
		assert "NT$1500" in text


async def test_notify_new_order_skips_when_no_group_id():
	mock_settings = MagicMock()
	mock_settings.line_staff_group_id = None

	with (
		patch("domains.line.notification.get_settings", return_value=mock_settings),
		patch("domains.line.notification.push_text_message", new_callable=AsyncMock) as mock_push,
	):
		from domains.line.notification import notify_new_order

		await notify_new_order(
			order_number="ORD-001",
			customer_name="Test Corp",
			total_amount="1500",
			line_count=3,
		)
		mock_push.assert_not_called()


async def test_notify_new_order_handles_push_failure():
	mock_settings = MagicMock()
	mock_settings.line_staff_group_id = "Cxxxxxx"

	with (
		patch("domains.line.notification.get_settings", return_value=mock_settings),
		patch("domains.line.notification.push_text_message", new_callable=AsyncMock) as mock_push,
	):
		mock_push.return_value = False
		from domains.line.notification import notify_new_order

		# Should not raise even when push fails
		await notify_new_order(
			order_number="ORD-002",
			customer_name="Fail Corp",
			total_amount="0",
			line_count=1,
		)
		mock_push.assert_called_once()
