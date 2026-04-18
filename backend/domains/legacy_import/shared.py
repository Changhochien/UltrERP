"""Shared helpers used across the legacy-import modules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def coerce_mapping(record: Mapping[str, object] | object) -> dict[str, object]:
    if isinstance(record, Mapping):
        return {str(key): value for key, value in record.items()}
    return {str(key): value for key, value in dict(record).items()}


def resolve_row_identity(source_row_number: int | None, fallback: int) -> int:
    return source_row_number if source_row_number not in (None, 0) else fallback


async def execute_many(
    connection: Any,
    query: str,
    rows: Sequence[Sequence[object]],
) -> None:
    if not rows:
        return

    executemany = getattr(connection, "executemany", None)
    if callable(executemany):
        await executemany(query, rows)
        return

    for row in rows:
        await connection.execute(query, *row)