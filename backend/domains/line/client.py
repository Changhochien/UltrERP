"""LINE Messaging API client wrapper.

Uses AsyncMessagingApi from line-bot-sdk v3.
LINE Notify was terminated March 31, 2025 — all notifications
use LINE Messaging API push_message.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from linebot.v3.messaging import (
	AsyncApiClient,
	AsyncMessagingApi,
	Configuration,
	PushMessageRequest,
	ReplyMessageRequest,
	TextMessage,
)

from common.config import get_settings

logger = logging.getLogger(__name__)


def _get_configuration() -> Configuration | None:
	"""Build LINE SDK config from settings. Returns None if unconfigured."""
	settings = get_settings()
	if not settings.line_channel_access_token:
		return None
	return Configuration(access_token=settings.line_channel_access_token)


@asynccontextmanager
async def get_line_api():
	"""Async context manager yielding AsyncMessagingApi or None."""
	config = _get_configuration()
	if config is None:
		logger.warning("LINE not configured — skipping")
		yield None
		return
	async with AsyncApiClient(config) as api_client:
		yield AsyncMessagingApi(api_client)


async def push_text_message(to: str, text: str, order_number: str | None = None) -> bool:
	"""Push a text message. Returns True on success, False on failure."""
	async with get_line_api() as api:
		if api is None:
			return False
		try:
			await api.push_message(
				PushMessageRequest(
					to=to,
					messages=[TextMessage(text=text)],
				)
			)
			return True
		except Exception:
			logger.exception("LINE push_message failed to=%s order_number=%s", to, order_number)
			return False


async def _reply_text_message(reply_token: str, text: str) -> bool:
	"""Reply with text message using reply token."""
	async with get_line_api() as api:
		if api is None:
			return False
		try:
			await api.reply_message(
				ReplyMessageRequest(
					reply_token=reply_token,
					messages=[TextMessage(text=text)],
				)
			)
			return True
		except Exception:
			logger.exception("LINE reply_message failed")
			return False


async def reply_or_push_message(
	reply_token: str | None,
	user_id: str,
	text: str,
) -> bool:
	"""Reply using reply_token if available, fall back to push_message.

	reply_token is free (no quota cost) but expires up to 20 minutes after the webhook event (per LINE API spec).
	push_message is always available but counts against monthly quota.
	"""
	if reply_token:
		success = await _reply_text_message(reply_token, text)
		if success:
			return True
		logger.warning("Reply failed (token expired?), falling back to push")

	return await push_text_message(user_id, text)
