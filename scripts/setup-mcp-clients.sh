#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SERVER_NAME="${ULTRERP_MCP_SERVER_NAME:-ultrerp}"
API_KEY_ENV_VAR="${ULTRERP_MCP_API_KEY_ENV_VAR:-ULTRERP_MCP_API_KEY}"
DEFAULT_MCP_URL="${ULTRERP_MCP_URL:-http://localhost:8000/mcp/}"

usage() {
	cat <<EOF
Usage:
  ${0##*/} [MCP_URL]

Examples:
  ${API_KEY_ENV_VAR}=dev-readonly-key ${0##*/}
  ${API_KEY_ENV_VAR}=dev-readonly-key ${0##*/} http://localhost:8000/mcp/
  ${API_KEY_ENV_VAR}=prod-readonly-key ${0##*/} https://erp.example.com/mcp/

Environment:
  ULTRERP_MCP_SERVER_NAME      MCP server name in client configs (default: ultrerp)
  ULTRERP_MCP_API_KEY_ENV_VAR  Env var name both clients will read (default: ULTRERP_MCP_API_KEY)
  ULTRERP_MCP_URL              Default MCP URL when no argument is passed

This script writes project-scoped config for:
  - Codex: .codex/config.toml
  - Claude Code: .mcp.json
EOF
}

normalize_mcp_url() {
	local raw="$1"

	if [[ "$raw" =~ /mcp/?$ ]]; then
		printf '%s\n' "${raw%/}/"
		return
	fi

	printf '%s/mcp/\n' "${raw%/}"
}

strip_managed_block() {
	local file="$1"
	local begin="$2"
	local end="$3"
	local temp_file

	temp_file="$(mktemp)"
	if [[ -f "$file" ]]; then
		awk -v begin="$begin" -v end="$end" '
			$0 == begin { skip = 1; next }
			$0 == end { skip = 0; next }
			!skip { print }
		' "$file" > "$temp_file"
	else
		: > "$temp_file"
	fi
	mv "$temp_file" "$file"
}

append_block() {
	local file="$1"
	local block="$2"

	if [[ -s "$file" ]]; then
		printf '\n%s\n' "$block" >> "$file"
	else
		printf '%s\n' "$block" > "$file"
	fi
}

assert_no_conflicting_codex_table() {
	local file="$1"
	local server_name="$2"

	if [[ ! -f "$file" ]]; then
		return
	fi

	if grep -Eq "^[[:space:]]*\\[mcp_servers\\.${server_name//./\\.}\\][[:space:]]*$" "$file"; then
		cat <<EOF >&2
Refusing to overwrite an existing Codex MCP table for '${server_name}' in:
  ${file}

Remove or rename the existing [mcp_servers.${server_name}] block, or rerun with:
  ULTRERP_MCP_SERVER_NAME=<different-name>
EOF
		exit 1
	fi
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
	usage
	exit 0
fi

if [[ -z "${!API_KEY_ENV_VAR:-}" ]]; then
	cat <<EOF >&2
${API_KEY_ENV_VAR} is not set.

Run the setup with the MCP API key inline, for example:
  ${API_KEY_ENV_VAR}=dev-readonly-key ./scripts/${0##*/}
EOF
	exit 1
fi

MCP_URL="$(normalize_mcp_url "${1:-$DEFAULT_MCP_URL}")"
CODEX_CONFIG_DIR="${REPO_ROOT}/.codex"
CODEX_CONFIG_FILE="${CODEX_CONFIG_DIR}/config.toml"
CLAUDE_CONFIG_FILE="${REPO_ROOT}/.mcp.json"

mkdir -p "$CODEX_CONFIG_DIR"

CODEX_BEGIN="# >>> UltrERP MCP (managed) >>>"
CODEX_END="# <<< UltrERP MCP (managed) <<<"
CODEX_BLOCK="$(cat <<EOF
${CODEX_BEGIN}
[mcp_servers.${SERVER_NAME}]
url = "${MCP_URL}"
env_http_headers = { "X-API-Key" = "${API_KEY_ENV_VAR}" }
enabled = true
tool_timeout_sec = 60
enabled_tools = [
  "customers_list",
  "customers_get",
  "customers_lookup_by_ban",
  "inventory_check",
  "inventory_search",
  "inventory_reorder_alerts",
  "invoices_list",
  "invoices_get",
  "orders_list",
  "orders_get",
  "supplier_invoices_list",
  "supplier_invoices_get",
  "payments_list",
  "payments_get",
]
${CODEX_END}
EOF
)"

strip_managed_block "$CODEX_CONFIG_FILE" "$CODEX_BEGIN" "$CODEX_END"
assert_no_conflicting_codex_table "$CODEX_CONFIG_FILE" "$SERVER_NAME"
append_block "$CODEX_CONFIG_FILE" "$CODEX_BLOCK"

node - "$CLAUDE_CONFIG_FILE" "$SERVER_NAME" "$MCP_URL" "$API_KEY_ENV_VAR" <<'EOF'
const fs = require("fs");

const [filePath, serverName, mcpUrl, apiKeyEnvVar] = process.argv.slice(2);
let doc = { mcpServers: {} };

if (fs.existsSync(filePath)) {
  const raw = fs.readFileSync(filePath, "utf8").trim();
  if (raw) {
    doc = JSON.parse(raw);
  }
}

if (!doc || typeof doc !== "object" || Array.isArray(doc)) {
  doc = { mcpServers: {} };
}

if (!doc.mcpServers || typeof doc.mcpServers !== "object" || Array.isArray(doc.mcpServers)) {
  doc.mcpServers = {};
}

doc.mcpServers[serverName] = {
  type: "http",
  url: mcpUrl,
  headers: {
    "X-API-Key": `\${${apiKeyEnvVar}}`,
  },
};

fs.writeFileSync(filePath, `${JSON.stringify(doc, null, 2)}\n`);
EOF

cat <<EOF
Configured project-scoped MCP access for Codex and Claude Code.

Files written:
  - ${CODEX_CONFIG_FILE}
  - ${CLAUDE_CONFIG_FILE}

Connection:
  - server name: ${SERVER_NAME}
  - MCP URL: ${MCP_URL}
  - API key env var: ${API_KEY_ENV_VAR}

Next steps:
  1. Start the backend so ${MCP_URL} is reachable.
  2. Keep ${API_KEY_ENV_VAR} exported in your shell profile.
  3. Verify with:
     codex mcp list
     claude mcp list
EOF
