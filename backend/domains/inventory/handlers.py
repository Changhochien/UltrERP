"""Domain event handlers for the inventory domain.

This module registers event handlers that react to domain events. It must be
imported at application startup so that the @on() decorators run and register
all handlers with the dispatcher.

Usage (in app/main.py or domains/__init__.py):
    import backend.domains.inventory.handlers  # noqa: F401 — registers handlers
"""
from __future__ import annotations

import uuid

from common.events import StockChangedEvent, on
from common.models.reorder_alert import AlertStatus, ReorderAlert
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@on(StockChangedEvent)
async def handle_reorder_alert(event: StockChangedEvent, session: AsyncSession) -> None:
    """
    React to stock changes by creating/updating/resolve reorder alerts.

    This handler is registered via @on(StockChangedEvent) — it fires automatically
    whenever a StockChangedEvent is emitted from any stock mutation.
    No need to call _check_reorder_alert directly from service code.
    """
    # Import here to avoid circular imports at module load time
    from domains.inventory.services import _check_reorder_alert

    if event.reorder_point <= 0:
        return

    await _check_reorder_alert(
        session,
        tenant_id=event.tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000000"),
        product_id=event.product_id,
        warehouse_id=event.warehouse_id,
        current_quantity=event.after_quantity,
        reorder_point=event.reorder_point,
    )
