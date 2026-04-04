"""Tests for LINE webhook endpoint (Story 9.2)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from linebot.v3.exceptions import InvalidSignatureError


@pytest.fixture
def _mock_line_configured():
	"""Patch settings to have LINE configured."""
	mock = MagicMock()
	mock.line_channel_secret = "test-secret"
	mock.line_channel_access_token = "test-token"
	mock.line_staff_group_id = "Cxxxxxx"
	with patch("domains.line.webhook.get_settings", return_value=mock):
		yield mock


@pytest.fixture
def _mock_line_unconfigured():
	"""Patch settings to have LINE unconfigured."""
	mock = MagicMock()
	mock.line_channel_secret = None
	with patch("domains.line.webhook.get_settings", return_value=mock):
		yield mock


def _make_webhook_body(user_id: str = "U" + "a" * 32, text: str = "商品A x 3"):
	"""Build a minimal LINE webhook body."""
	return json.dumps({
		"events": [{
			"type": "message",
			"replyToken": "test-reply-token",
			"source": {"type": "user", "userId": user_id},
			"message": {"type": "text", "id": "1234", "text": text},
			"timestamp": 1234567890,
			"mode": "active",
		}],
		"destination": "Uxxxxxxxxxx",
	})


async def test_webhook_rejects_missing_signature(_mock_line_configured):
	"""Webhook returns 400 for invalid/missing signature."""
	from httpx import ASGITransport, AsyncClient

	from app.main import create_app

	app = create_app()
	body = _make_webhook_body()

	# Mock the parser to raise InvalidSignatureError
	with patch("domains.line.webhook._get_parser") as mock_get_parser:
		mock_parser = MagicMock()
		mock_parser.parse.side_effect = InvalidSignatureError("")
		mock_get_parser.return_value = mock_parser

		async with AsyncClient(
			transport=ASGITransport(app=app), base_url="http://test"
		) as client:
			resp = await client.post(
				"/api/v1/line/webhook",
				content=body,
				headers={"X-Line-Signature": "bad"},
			)
			assert resp.status_code == 400


async def test_webhook_returns_503_when_unconfigured(_mock_line_unconfigured):
	"""Webhook returns 503 when LINE is not configured."""
	from httpx import ASGITransport, AsyncClient

	from app.main import create_app

	app = create_app()

	async with AsyncClient(
		transport=ASGITransport(app=app), base_url="http://test"
	) as client:
		resp = await client.post(
			"/api/v1/line/webhook",
			content="{}",
			headers={"X-Line-Signature": "test"},
		)
		assert resp.status_code == 503


async def test_webhook_valid_message_triggers_handler(_mock_line_configured):
	"""Valid webhook call processes events and returns 200."""

	with (
		patch("domains.line.webhook._get_parser") as mock_get_parser,
		patch("domains.line.webhook._handle_text_message", new_callable=AsyncMock),
	):
		# Make parser return events that pass isinstance checks
		mock_event = MagicMock()
		mock_event.__class__ = type("MessageEvent", (), {})

		mock_parser = MagicMock()
		mock_parser.parse.return_value = []  # no events to process
		mock_get_parser.return_value = mock_parser

		from httpx import ASGITransport, AsyncClient

		from app.main import create_app

		app = create_app()

		async with AsyncClient(
			transport=ASGITransport(app=app), base_url="http://test"
		) as client:
			resp = await client.post(
				"/api/v1/line/webhook",
				content=_make_webhook_body(),
				headers={"X-Line-Signature": "valid"},
			)
			assert resp.status_code == 200


async def test_handle_text_message_unregistered_user():
	"""_handle_text_message sends registration reply for unknown user."""
	from domains.line.webhook import _handle_text_message

	event = MagicMock()
	event.source.user_id = "U" + "b" * 32
	event.reply_token = "reply-token"
	event.message.text = "商品A x 3"

	mock_session = AsyncMock()
	mock_result = MagicMock()
	mock_result.scalar_one_or_none.return_value = None
	mock_session.execute = AsyncMock(return_value=mock_result)

	with patch("domains.line.webhook.reply_or_push_message", new_callable=AsyncMock) as mock_reply:
		await _handle_text_message(event, mock_session)
		mock_reply.assert_called_once()
		call_text = mock_reply.call_args[0][2]
		assert "not linked" in call_text


async def test_handle_text_message_unparseable():
	"""_handle_text_message sends format help for unparseable text."""
	from domains.line.webhook import _handle_text_message

	event = MagicMock()
	event.source.user_id = "U" + "c" * 32
	event.reply_token = "reply-token"
	event.message.text = "hello"

	mock_mapping = MagicMock()
	mock_mapping.customer_id = "fake-customer-id"

	mock_session = AsyncMock()
	mock_result = MagicMock()
	mock_result.scalar_one_or_none.return_value = mock_mapping
	mock_session.execute = AsyncMock(return_value=mock_result)

	with patch("domains.line.webhook.reply_or_push_message", new_callable=AsyncMock) as mock_reply:
		await _handle_text_message(event, mock_session)
		mock_reply.assert_called_once()
		call_text = mock_reply.call_args[0][2]
		assert "To place an order" in call_text
