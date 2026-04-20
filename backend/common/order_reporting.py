"""Shared reporting semantics for commercially committed orders."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func

from common.models.order import Order

COMMERCIALLY_COMMITTED_ORDER_STATUSES = ("confirmed", "shipped", "fulfilled")


def commercially_committed_order_filter():
    return Order.status.in_(COMMERCIALLY_COMMITTED_ORDER_STATUSES)


def commercially_committed_timestamp_expr():
    return func.coalesce(Order.confirmed_at, Order.created_at)


def commercially_committed_timestamp_value(order: Order) -> datetime:
    return order.confirmed_at or order.created_at