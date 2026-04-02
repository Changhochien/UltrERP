"""
Structured error types for the UltrERP MCP server.

Each error type carries machine-readable fields that MCP clients
and agent runtimes can parse to take corrective action (retry,
prompt user, escalate, etc.).

Error response format:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human-readable description",
            "details": { ... },        # error-type specific
            "retry": true|false,
            "required_scope": "..."    # PermissionError only
        }
    }
"""

from typing import Any


class StructuredError(Exception):
    """Base class for all structured MCP server errors."""

    code: str = "INTERNAL_ERROR"
    retry: bool = True
    required_scope: str | None = None

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        retry: bool | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if retry is not None:
            self.retry = retry

    def to_dict(self) -> dict[str, Any]:
        """Render the error as a JSON-RPC-compatible dict for MCP responses."""
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "retry": self.retry,
        }
        if self.required_scope:
            error["required_scope"] = self.required_scope
        return error


class ValidationError(StructuredError):
    """
    Returned when a tool argument fails validation.

    details structure:
        {
            "field": "customer.tax_id",
            "value": "12345678",
            "constraint": "8-digit MOD11 checksum",
            "received": "7 digits — missing check digit"
        }

    retry=false because the client must fix the input before re-calling.
    """

    code = "VALIDATION_ERROR"
    retry = False

    def __init__(
        self,
        message: str,
        field: str,
        value: Any,
        constraint: str,
        received: str | None = None,
    ):
        super().__init__(
            message=message,
            details={
                "field": field,
                "value": value,
                "constraint": constraint,
                "received": received or str(value),
            },
            retry=False,
        )


class NotFoundError(StructuredError):
    """
    Returned when a referenced entity does not exist.

    details structure:
        {
            "entity_type": "customer",
            "entity_id": "c_abc123",
            "query": { "id": "c_abc123" }
        }

    retry=true if the entity may exist but was temporarily unavailable.
    """

    code = "NOT_FOUND"
    retry = True

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        message: str | None = None,
    ):
        super().__init__(
            message=message
            or f"{entity_type.capitalize()} with ID '{entity_id}' not found",
            details={
                "entity_type": entity_type,
                "entity_id": entity_id,
            },
            retry=True,
        )


class PermissionError(StructuredError):
    """
    Returned when the API key lacks the scope required for an operation.

    details structure:
        {
            "required_scope": "customers:write",
            "token_scopes": ["customers:read"],
            "operation": "customers.create"
        }

    retry=true if the caller can obtain a token with broader scopes
    (e.g., step-up auth via OIDC provider in production).
    """

    code = "PERMISSION_DENIED"
    retry = True
    required_scope: str

    def __init__(
        self,
        required_scope: str,
        token_scopes: list[str] | None = None,
        operation: str | None = None,
    ):
        self.required_scope = required_scope
        super().__init__(
            message=f"This operation requires the '{required_scope}' scope",
            details={
                "required_scope": required_scope,
                "token_scopes": token_scopes or [],
                "operation": operation,
            },
            retry=True,
        )
