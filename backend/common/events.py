"""Lightweight domain event dispatcher — no message queue, no external dependencies."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T", bound="DomainEvent")

# Handler: async fn(event: DomainEvent, session: AsyncSession) -> None
EventHandler = Callable[["DomainEvent", Any], Awaitable[None]]

_registered_handlers: list[tuple[str, EventHandler]] = []


def on(event_type: type["DomainEvent"]) -> Callable[[EventHandler], EventHandler]:
    """Decorator: register a handler for a domain event type.

    Usage:
        @on(StockChangedEvent)
        async def handle_stock_changed(event: StockChangedEvent, session: AsyncSession) -> None:
            ...
    """
    def register(handler: EventHandler) -> EventHandler:
        _registered_handlers.append((event_type.__name__, handler))
        return handler
    return register


async def emit(event: "DomainEvent", session: Any) -> None:
    """Synchronously dispatch an event to all registered handlers within the current transaction.

    Handlers are called in registration order. If a handler raises, the transaction
    rolls back — correct behavior for stock alerts (you don't want to commit stock
    changes but fail to create an alert).
    """
    event_type_name = type(event).__name__
    for name, handler in _registered_handlers:
        if name == event_type_name:
            await handler(event, session)


@dataclass(slots=True)
class DomainEvent:
    """Base class for all domain events."""
    name: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    tenant_id: uuid.UUID | None = None


@dataclass(slots=True)
class StockChangedEvent(DomainEvent):
    """Fired whenever stock levels change for a product at a warehouse.

    Emitted by: transfer_stock, create_stock_adjustment, receive_supplier_order.
    Handled by: reorder alert logic, future notification channels.
    """
    name: str = "stock_changed"
    product_id: uuid.UUID = field(default_factory=uuid.uuid4)
    warehouse_id: uuid.UUID = field(default_factory=uuid.uuid4)
    before_quantity: int = 0
    after_quantity: int = 0
    reorder_point: int = 0
    actor_id: str = "system"
