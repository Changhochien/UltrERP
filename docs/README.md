# UltrERP Documentation

AI-native ERP system for Taiwan SMBs (聯泰興實業)

## Project Overview

**What we're building:** ERP system serving both human users (via Tauri desktop GUI) and AI agents (via MCP) from a single codebase.

**Technology:** Tauri 2.x + React 19 + FastAPI + PostgreSQL + MCP

**Deployment:** Solo (local sidecar + PostgreSQL) and team (central server + shared PostgreSQL)

## Documentation Structure

| Folder | Content |
|--------|---------|
| `superpowers/specs/` | Architecture and technical specifications |
| `superpowers/research/` | Research and analysis documents |

## Quick Links

- [PRD](../_bmad-output/planning-artifacts/prd.md) - Product Requirements Document
- [Architecture Specs](../docs/superpowers/specs/) - Technical architecture
- [WDS Evolution](../_bmad/evolution/) - Current improvement cycles
- [MCP Client Setup](./mcp-client-setup.md) - One-command Codex and Claude Code MCP config
