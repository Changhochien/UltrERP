# Multi-Agent Patterns Survey

## Known Facts

### Tool Registration (FastMCP 3.x)
- Tools registered via `@mcp.tool()` decorator on Python functions; function name becomes tool name, docstring becomes description, type annotations generate input schema automatically
- `Annotated[T, "description"]` with Pydantic `Field` for rich parameter descriptions and validation (ge, le, pattern)
- Decorator returns callable function (v3 change from v2) enabling direct unit testing of tools
- Supports `version="1.0"` parameter for side-by-side multiple versions
- Annotations available: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`, `title`
- Tool result: primitives wrapped under `"result"` key, objects/dicts returned as structured content
- Raise `ToolError` for explicit client-facing error messages; `mask_error_details=True` hides internal details
- Context parameter (`ctx: Context`) provides `ctx.info()`, `ctx.report_progress()`, `ctx.read_resource()`

### MCP OAuth 2.1 Authorization Flow
- MCP client acts as OAuth 2.1 client; MCP server acts as OAuth 2.1 resource server
- Servers MUST implement RFC 9728 (Protected Resource Metadata) to advertise authorization server location
- Discovery: MCP server returns `401` with `WWW-Authenticate` header containing `resource_metadata` URL or falls back to well-known URIs (/.well-known/oauth-protected-resource)
- Authorization server discovery: tries OAuth 2.0 Authorization Server Metadata first, then OpenID Connect Discovery 1.0
- Clients MUST support PKCE with `S256` code challenge method; servers MUST refuse proceed if PKCE unsupported
- `resource` parameter (RFC 8707) MUST be in both authorization and token requests, identifying target MCP server canonical URI
- Token sent via `Authorization: Bearer <token>` header on every HTTP request
- Server returns `403 Forbidden` with `WWW-Authenticate: Bearer error="insufficient_scope", scope="required_scope1"` for insufficient scope
- Step-up authorization: client retries with increased scopes on scope-related errors
- Token audience validation REQUIRED: server MUST reject tokens not issued for it specifically

### Claude Code MCP Server Connection
- Global MCP servers: configured in `~/.claude/settings.json`
- Project-scoped servers: `.mcp.json` in project directory
- Configuration includes `command`, `args`, `env` for process-based servers
- Supports stdio and HTTP(S) transports for remote servers
- Claude Desktop can connect to remote MCP servers via Settings > Connectors

### Tool Design Patterns (from official spec and servers)
- Tool names: kebab-case unique identifiers (e.g., `get_weather`)
- Optional `title` for human-readable display, `description` explains when/why to use
- `inputSchema` uses standard JSON Schema; `outputSchema` optional for structured results
- Pagination: opaque cursor-based, cursor passed in `tools/list` request, `nextCursor` in response
- Tool result: `content[]` array with text/image/audio/resource_link types, `isError: true` for errors
- Protocol errors: JSON-RPC error code + message (e.g., -32602 for invalid arguments)
- Official servers (github.com/modelcontextprotocol/servers): filesystem, git, fetch, memory, time, sequential-thinking -- all TypeScript reference implementations

### Error Response Architecture (from design doc)
- `ValidationError`: field-level details with constraint information
- `NotFoundError`: entity type + ID of missing resource
- `PermissionError`: required OAuth scope that was missing
- All errors include `retry: true/false` guidance

### RBAC Scopes (from design doc)
- admin: full CRUD all domains
- finance: invoices CRUD+void, payments CRUD
- warehouse: inventory CRUD
- sales: customers CRUD, orders CRUD, inventory read
- agent: read all, create invoices
- Scope format: `domain:action` (e.g., `customers:read`, `customers:write`)

## Unknowns / Open Questions

1. **How does per-tool authorization checking interact with OAuth scope validation at runtime?** Specifically, does the MCP server validate scopes on every `tools/call` request, or is this delegated to the authorization server via token introspection?

2. **What is the minimal viable OAuth 2.1 authorization server for PoC?** The spec is comprehensive but the minimum viable implementation for an internal ERP is unclear -- should we use an existing OIDC provider (Auth0, Okta) or build a simple token issuer?

3. **How do agent sessions maintain token lifecycle?** When an agent holds a long conversation, tokens may expire. Is refresh token rotation handled automatically by the MCP client SDK, or must the agent runtime manage this?

4. **How does FastMCP 3.x `auth` parameter map to OAuth scopes?** The blog mentions `require_scopes("super-user")` but the mapping between FastMCP component-level auth and the RFC 9728 scope format is not documented.

5. **What is the recommended strategy for tool naming hierarchy across domains?** The design doc suggests `domain.action.entity` but does not resolve conflicts when a single operation touches multiple entities.

6. **How should pagination cursors be encoded and validated?** The spec says "opaque cursor" but does not specify encoding (base64? JWT?). Cursor tampering could bypass access controls.

7. **Does the MCP spec support streaming tool responses for long-running operations?** The spec mentions `report_progress` but it is unclear if this maps to SSE or polling.

## Top 3 Risks

### 1. Token Audience Validation Gaps (Critical)
The MCP OAuth 2.1 spec requires servers to validate that tokens were issued specifically for them (audience claim). If we use a generic OAuth provider or fail to set audience claims correctly, tokens issued for one MCP server could be replayed against another. This is the "confused deputy" problem. Mitigation: strict audience validation on every request, use RFC 9068 JWT profile if available.

### 2. Human-in-the-Loop Verification Complexity (High)
The MCP spec requires human confirmation for sensitive operations. Implementing this correctly in a multi-agent ERP workflow is complex -- does each tool call pause the agent? Is there batch approval? Misunderstanding this requirement could create security gaps or UX failures. The spec states clients "SHOULD" prompt for confirmation, not "MUST."

### 3. FastMCP 3.x Stability with MCP SDK 1.23+ (Medium-High)
FastMCP 3.x pins `mcp<1.23` as a precautionary measure because MCP SDK 1.23 introduced protocol changes (November 2025 update) that break certain FastMCP features. This means we cannot use the latest MCP SDK features. We need to track when FastMCP 3.x unblocks MCP SDK 1.23+ compatibility.

## 3-Point Recommendation

### 1. Start with FastMCP 2.x for PoC, plan v3 migration at 6-month horizon
FastMCP 3.x is too new (January 2026) and locks us out of MCP SDK 1.23+ features. Use FastMCP 2.x (`fastmcp>=2.0,<3.0`) for the initial PoC. Set a calendar reminder to re-evaluate FastMCP 3.x adoption when it ships a stable release supporting MCP SDK 1.23+.

### 2. Use Auth0 or Okta as the OAuth 2.1 authorization server for PoC
Building a compliant OAuth 2.1 authorization server from scratch is high-effort and high-risk for security. Use an established OIDC provider (Auth0, Okta, Azure AD) that supports PKCE, RFC 8728 Resource Indicators, and short-lived tokens. This accelerates PoC and reduces security risk. Map RBAC roles to OAuth scopes: `erp:admin`, `erp:finance`, `erp:warehouse`, `erp:sales`, `erp:agent`.

### 3. Build one reference MCP server end-to-end before scaling to all domains
Before building 5 MCP servers (customers, invoices, inventory, orders, payments), build a single reference server (e.g., `customers`) with full OAuth integration, error handling, pagination, and tool annotations. This surfaces integration issues (auth flow, cursor encoding, SDK quirks) before they affect all domains. The reference server becomes the template for subsequent domains.

## Sources

- FastMCP Tools: https://gofastmcp.com/servers/tools
- FastMCP 3.0 Introduction: https://jlowin.dev/blog/fastmcp-3
- FastMCP Changelog (SDK pinning): https://gofastmcp.com/changelog
- MCP Tools Specification (2025-06-18): https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- MCP Authorization Specification (2025-11-25): https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- MCP Pagination: https://modelcontextprotocol.info/specification/draft/server/utilities/pagination/
- MCP Server Reference Implementations: https://github.com/modelcontextprotocol/servers
- Claude Code MCP Configuration: https://code.claude.com/docs/en/settings
- Building Secure MCP Server with OAuth 2.1 and Azure AD: https://devblogs.microsoft.com/ise/aca-secure-mcp-server-oauth21-azure-ad/
- MCP OAuth 2.1 Deep Dive: https://kane.mx/posts/2025/mcp-authorization-oauth-rfc-deep-dive/
