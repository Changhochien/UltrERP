# Legacy Database — Connection Reference

> **Credentials are sensitive.** Keep them in your shell environment or a local untracked `.env`, never commit them.

## Connection Parameters

| Variable | Value |
|---|---|
| `LEGACY_DB_HOST` | `100.77.54.101` (Tailscale IP) |
| `LEGACY_DB_PORT` | `5432` |
| `LEGACY_DB_NAME` | `cao50001` (main ERP data) or `cao50` |
| `LEGACY_DB_CLIENT_ENCODING` | `BIG5` |

### Credentials

```
LEGACY_DB_USER=postgres
LEGACY_DB_PASSWORD=<password>
```

> **Note:** The reviewed live refresh pipeline now hard-blocks write-like SQL on the
> legacy source connection. It forces `default_transaction_read_only=on`, allows only
> `SHOW` and `SELECT` queries through the live-source wrapper, and refuses any
> non-read-only transaction request in the pipeline path.

## Databases

| DB | Description |
|---|---|
| `cao50001` | Main operational ERP database (~350+ tables) |
| `cao50` | Small company / subsidiary data (3 tables) |
| `postgres` | Default PostgreSQL system database |

## Key Tables in `cao50001`

### Stock / Inventory
`tbsstock`, `tbsstockdt`, `tbsstkinvoice`, `tbsstkclass`, `tbsstklocation`, `tbsstkserial`, `tbsstockfactory`, `tbsstockinfofactory`, `tbsstockmaterial`, `tbstrans`, `tbsinvstock`

### Sales / Slip (Orders)
`tbaslip`, `tbaslipx`, `tbaslipdtx`, `otbsslip*` (various slip types), `tbainvodetail`, `tbainvorail`

### Finance / Accounting
`tbaaccounts`, `tbaacsub`, `tbaapay`, `tbacash`, `tbacashflow`, `tbabank`, `tbabankact`, `tbacost`, `tbacostdetail`, `tbaforap`, `tbaarapral`

### HR / Payroll
`tbaemploy`, `tbaemploy1`, `tbasalary`, `tbasalaryset`, `tbasalaryitem`, `tbaemployset`, `tbaemployitem`

### Customers & Suppliers
`tbscust`, `tbscustname`, `tbscustconn`, `tbscusttel`, `tbscustadd`

### System / Config
`tbasyspara`, `tbssyspara`, `tbcpubsyspara`, `tbagroupset`, `tbasetinfo`, `tbano`, `tbano1`

## Test Connection

```bash
# From project root — set env and run:
LEGACY_DB_HOST=100.77.54.101 \
LEGACY_DB_PORT=5432 \
LEGACY_DB_USER=postgres \
LEGACY_DB_PASSWORD=<password> \
LEGACY_DB_NAME=cao50001 \
python3 -c "
import asyncio, asyncpg
async def test():
    conn = await asyncpg.connect(
        host='$LEGACY_DB_HOST', port=int('$LEGACY_DB_PORT'),
        user='$LEGACY_DB_USER', password='$LEGACY_DB_PASSWORD',
        database='$LEGACY_DB_NAME', timeout=10
    )
    print('Connected! Tables:', await conn.fetchval(\"SELECT count(*) FROM pg_tables WHERE schemaname='public'\"))
    await conn.close()
asyncio.run(test())
"
```

## Environment Setup

Add to your `.env` (or shell export):

```env
LEGACY_DB_HOST=100.77.54.101
LEGACY_DB_PORT=5432
LEGACY_DB_USER=postgres
LEGACY_DB_PASSWORD=<your-password>
LEGACY_DB_NAME=cao50001
LEGACY_DB_CLIENT_ENCODING=BIG5
```

Then use in the app via `backend/common/config.py` → `LegacyDbSettings`.
