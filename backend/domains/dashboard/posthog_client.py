"""PostHog API client for querying visitor analytics."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0  # seconds


@dataclass(frozen=True)
class VisitorStats:
    visitor_count: int
    inquiry_count: int


async def get_visitor_stats(
    *,
    host: str,
    project_id: str,
    api_key: str,
    target_date: date,
) -> VisitorStats:
    """Query PostHog HogQL API for visitor and inquiry counts on *target_date*.

    Raises ``httpx.HTTPError`` on connection / HTTP failures.
    """
    url = f"{host.rstrip('/')}/api/projects/{project_id}/query/"
    headers = {"Authorization": f"Bearer {api_key}"}

    visitor_count = await _run_hogql_count(
        url,
        headers,
        event="$pageview",
        target_date=target_date,
    )
    inquiry_count = await _run_hogql_count(
        url,
        headers,
        event="inquiry_submitted",
        target_date=target_date,
    )

    return VisitorStats(visitor_count=visitor_count, inquiry_count=inquiry_count)


async def _run_hogql_count(
    url: str,
    headers: dict[str, str],
    *,
    event: str,
    target_date: date,
) -> int:
    """Execute a HogQL COUNT(DISTINCT distinct_id) query for a single event type."""
    date_str = target_date.isoformat()
    hogql = (
        f"SELECT count(DISTINCT distinct_id) FROM events "
        f"WHERE event = '{event}' "
        f"AND timestamp >= toDate('{date_str}') "
        f"AND timestamp < toDate('{date_str}') + INTERVAL 1 DAY"
    )
    body = {"query": {"kind": "HogQLQuery", "query": hogql}}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()

    data = resp.json()
    # HogQL response: {"results": [[count_value]], ...}
    return int(data["results"][0][0])
