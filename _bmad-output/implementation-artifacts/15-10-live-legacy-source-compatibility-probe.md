# Story 15.10 Live Legacy Source Compatibility Probe

Status: approved

## Runtime Summary

- Probe date: 2026-04-18
- Connector: `asyncpg 0.31.0`
- Source server: PostgreSQL `8.2.23`
- Source encoding: `SQL_ASCII`
- Required client encoding: `BIG5`
- Read-only enforcement: verified with `default_transaction_read_only=on` and `SHOW transaction_read_only`
- `public` table count: `528`
- Required staging tables present: `tbscust`, `tbsstock`, `tbsslipx`, `tbsslipdtx`, `tbsstkhouse`

## Approved Contract

1. Connection/session contract:
   - Open the live source with `asyncpg`
   - Set `default_transaction_read_only=on`
   - Set `client_encoding=BIG5`
   - Use `SHOW` and `SELECT` only during the compatibility probe and later live staging

2. Row serialization contract:
   - Build a metadata-driven query that projects every supported column as `COALESCE(column::text, 'NULL')`
   - Supported PostgreSQL types proven on the live source:
     - `character varying`
     - `character`
     - `text`
     - `numeric`
     - `integer`
     - `smallint`
     - `double precision`
     - `date`
     - `timestamp with time zone`
   - Database `NULL` is serialized as the literal text `NULL`
   - Empty string remains empty string
   - Numerics preserve PostgreSQL text output such as `8.00000000`
   - Date-like values arrive as PostgreSQL text such as `2024-08-26`

3. Lineage contract:
   - `_legacy_pk` continues hashing the serialized text row
   - Helper regression coverage now proves the live-source text projection matches the existing file parser semantics for `_legacy_pk`

4. Fail-fast contract:
   - Reject unsupported live column types before opening a cursor
   - Reject non-string projected values before they reach the shared raw loader
   - Reject missing `LEGACY_DB_*` settings with explicit diagnostics

## Sample Evidence

### `tbscust`

- Column count: `100`
- First five columns: `scustno`, `skind`, `scustname`, `scustname2`, `emplno`
- Sample row preview: `T068 | 1 | 達基 | 達基實業有限公司 |`

### `tbsstock`

- Column count: `136`
- First five columns: `sstkno`, `sstkyard`, `sstkname`, `sstkname2`, `sclassno`
- Sample row preview: `PM044 |  | 三角皮帶 M-44 |  |`

### `tbsslipx`

- Column count: `103`
- First five columns: `skind`, `sslipno`, `dtslipdate`, `stslipno`, `sformat`
- Sample row preview: `1 | 1130826001 | 2024-08-26 | 1130826001 | YYYMMDD999`

### `tbsslipdtx`

- Column count: `73`
- First five columns: `skind`, `sslipno`, `iidno`, `dtslipdate`, `iabsno`
- Sample row preview: `1 | 11032433 | 1 | 1922-03-24 | 1`

### `tbsstkhouse`

- Column count: `15`
- First five columns: `sstkno`, `shouseno`, `sstoreplace`, `fbeginqty`, `fsafeqty`
- Sample row preview: `VB048 | A |  | 8.00000000 | 8.00000000`

## Operational Guardrails

- Live-source credentials are environment-only. Do not commit them to `.env.example`, specs, planning artifacts, or story files.
- The probe used ephemeral local connection values during validation; those values are intentionally omitted here.
- Future Stories 15.11 and 15.12 should reuse the proven text-projection contract instead of inventing a second raw-row format.

## Rerun Recipe

Provide `LEGACY_DB_HOST`, `LEGACY_DB_PORT`, `LEGACY_DB_USER`, `LEGACY_DB_PASSWORD`, `LEGACY_DB_NAME`, and `LEGACY_DB_CLIENT_ENCODING=BIG5`, then run:

```bash
cd backend && uv run python - <<'PY'
import asyncio
import json
from dataclasses import asdict

from domains.legacy_import.staging import probe_live_legacy_source

print(
    json.dumps(
        asdict(asyncio.run(probe_live_legacy_source(sample_row_limit=2))),
        ensure_ascii=False,
        indent=2,
    )
)
PY
```
