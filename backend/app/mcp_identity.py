"""Shared MCP identity helpers."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping

import jwt
from fastmcp.exceptions import ToolError

from common.config import settings


def parse_uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ToolError(
            json.dumps(
                {
                    "code": "VALIDATION_ERROR",
                    "field": field,
                    "message": f"Invalid UUID: {value}",
                    "retry": False,
                }
            )
        ) from exc


def resolve_tenant_id_from_headers(headers: Mapping[str, str] | None) -> uuid.UUID:
    resolved_headers = dict(headers or {})

    if resolved_headers.get("x-api-key"):
        tenant_header = resolved_headers.get("x-tenant-id")
        if tenant_header:
            return parse_uuid(tenant_header, "tenant_id")
        raise ToolError(
            json.dumps(
                {
                    "code": "TENANT_REQUIRED",
                    "message": "X-Tenant-ID is required for tenant-bound MCP API keys",
                    "retry": True,
                }
            )
        )

    auth_header = resolved_headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        except jwt.InvalidTokenError as exc:
            raise ToolError(
                json.dumps(
                    {
                        "code": "INVALID_TOKEN",
                        "message": "Invalid or expired Bearer token",
                        "retry": True,
                    }
                )
            ) from exc

        tenant_id = payload.get("tenant_id")
        if not isinstance(tenant_id, str) or not tenant_id:
            raise ToolError(
                json.dumps(
                    {
                        "code": "INVALID_TOKEN",
                        "message": "Invalid or expired Bearer token",
                        "retry": True,
                    }
                )
            )
        resolved_tenant = parse_uuid(tenant_id, "tenant_id")
        tenant_header = resolved_headers.get("x-tenant-id")
        if tenant_header:
            header_tenant = parse_uuid(tenant_header, "tenant_id")
            if header_tenant != resolved_tenant:
                raise ToolError(
                    json.dumps(
                        {
                            "code": "INVALID_TENANT",
                            "message": "X-Tenant-ID does not match the Bearer token tenant",
                            "retry": False,
                        }
                    )
                )
        return resolved_tenant

    tenant_header = resolved_headers.get("x-tenant-id")
    if tenant_header:
        return parse_uuid(tenant_header, "tenant_id")

    raise ToolError(
        json.dumps(
            {
                "code": "TENANT_REQUIRED",
                "message": "X-Tenant-ID or Authorization: Bearer token with tenant_id is required",
                "retry": True,
            }
        )
    )