# MCP Client Setup

UltrERP exposes a streamable HTTP MCP endpoint from the backend at `/mcp/`. This guide sets up project-scoped client config for Codex and Claude Code so both agents can call the same read-only ERP tools.

## One-Line Setup

From the repository root:

```bash
ULTRERP_MCP_API_KEY=dev-readonly-key ./scripts/setup-mcp-clients.sh
```

To target a non-default backend URL:

```bash
ULTRERP_MCP_API_KEY=dev-readonly-key ./scripts/setup-mcp-clients.sh https://erp.example.com/mcp/
```

The script writes:

- `.codex/config.toml` for project-scoped Codex MCP config
- `.mcp.json` for project-scoped Claude Code MCP config

Both clients read the API key from `ULTRERP_MCP_API_KEY`, so the key is not written into the repo config files.

## Backend Key Setup

The backend must trust the same key via `MCP_API_KEYS`. Example:

```bash
export MCP_API_KEYS='{
  "dev-readonly-key": [
    "customers:read",
    "inventory:read",
    "invoices:read",
    "orders:read",
    "purchases:read",
    "payments:read"
  ]
}'
```

If you keep backend settings in the repo-root `.env`, the equivalent entry is:

```dotenv
MCP_API_KEYS={"dev-readonly-key":["customers:read","inventory:read","invoices:read","orders:read","purchases:read","payments:read"]}
```

## What Gets Exposed

The generated config enables the current external read-only MCP tools:

- `customers_list`, `customers_get`, `customers_lookup_by_ban`
- `inventory_check`, `inventory_search`, `inventory_reorder_alerts`
- `invoices_list`, `invoices_get`
- `orders_list`, `orders_get`
- `supplier_invoices_list`, `supplier_invoices_get`
- `payments_list`, `payments_get`

## Verify

With the backend running, confirm the clients see the server:

```bash
codex mcp list
claude mcp list
```

Then start either client from this repo:

```bash
codex
claude
```

## Notes

- Use the `/mcp/` URL directly instead of relying on the `/mcp` redirect.
- Codex project config is supported via `.codex/config.toml` in trusted projects.
- Claude Code project-scoped MCP config lives in `.mcp.json` at the repo root and may prompt for trust approval the first time it is used.
- This setup is intentionally read-only. If you later expose write tools, create a separate narrower key for each agent role instead of reusing a broad key.
