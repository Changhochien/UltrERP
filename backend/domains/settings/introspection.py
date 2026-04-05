from __future__ import annotations

import typing
from typing import Any, Literal

from common.config import Settings


def _read_settings_metadata() -> dict[str, dict[str, Any]]:
    """
    Introspect the Settings class and extract field metadata.

    Returns a dict keyed by Python attribute name, each value containing:
      - description: str
      - category: str
      - is_sensitive: bool
      - value_type: str  # "str" | "int" | "bool" | "tuple" | "json" | "literal"
      - allowed_values: list[str] | None  # only for literal types
      - nullable: bool  # True if default is None
    """
    result: dict[str, dict[str, Any]] = {}

    for field_name, field_info in Settings.model_fields.items():
        json_extra = field_info.json_schema_extra
        if not json_extra:
            continue

        if isinstance(json_extra, list):
            # Pydantic may merge Annotated metadata into a list
            meta: dict[str, Any] = {}
            for item in json_extra:
                if isinstance(item, dict):
                    meta.update(item)
        elif isinstance(json_extra, dict):
            meta = json_extra
        else:
            continue

        if not meta.get("description"):
            continue

        # Only process fields that have our metadata schema
        description = meta.get("description", "")
        category = meta.get("category", "")
        is_sensitive = meta.get("is_sensitive", False)
        value_type: str = meta.get("value_type", "str")
        allowed_values: list[str] | None = None
        nullable = meta.get("nullable", False)

        # For Literal types, derive allowed_values automatically via typing
        annotation = field_info.annotation
        if hasattr(annotation, "__origin__") and annotation.__origin__ is Literal:
            allowed_values = list(typing.get_args(annotation))

        # Detect nullable from default=None
        if field_info.default is None:
            nullable = True

        result[field_name] = {
            "description": description,
            "category": category,
            "is_sensitive": is_sensitive,
            "value_type": value_type,
            "allowed_values": allowed_values,
            "nullable": nullable,
        }

    return result
