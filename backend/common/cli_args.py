"""Shared argparse helpers for backend CLIs."""

from __future__ import annotations

import argparse
import re
import uuid

TOKEN_RE = re.compile(r"[^A-Za-z0-9._-]+")


def parse_tenant_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("tenant-id must be a valid UUID") from exc


def parse_non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative integer")
    return parsed


def normalize_token(value: str, *, default: str = "unknown") -> str:
    cleaned = TOKEN_RE.sub("-", value.strip()).strip("-._")
    return cleaned or default