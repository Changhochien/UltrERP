# SQL Triggers and Functions Audit — cao50001.sql

**File:** `/Volumes/2T_SSD_App/Projects/UltrERP/legacy data/cao50001.sql`
**Scope:** Stock movement triggers, functions, stored procedures, and update mechanisms for `tbsstkhouse`

---

## 1. TRIGGERS — None Found

**Result:** Zero `CREATE TRIGGER` statements in the entire 543MB dump.

The dump was scanned with:
```
grep -n "CREATE.*TRIGGER" cao50001.sql   # 0 matches
```

**Implication:** Stock quantities in `tbsstkhouse` are NOT maintained by database triggers in the legacy system. Updates must occur via application logic (stored procedures called by the client app, or direct UPDATE/INSERT statements).

---

## 2. STORED PROCEDURES — None Found

**Result:** Zero `CREATE PROCEDURE` statements in the entire dump.

```
grep -n "CREATE.*PROCEDURE" cao50001.sql   # 0 matches
```

---

## 3. FUNCTIONS — Only 3 Found

All functions are utility helpers, not stock-update routines.

### 3a. `integer_to_date(integer)` — Line 31
```sql
CREATE FUNCTION integer_to_date(integer) RETURNS date
    AS $_$
 declare
 i_date alias for $1;
 begin
   return to_date('19000101','YYYYMMDD') + cast(i_date as integer);
 end;
 $_$
    LANGUAGE plpgsql STABLE STRICT;

COMMENT ON FUNCTION integer_to_date(integer) IS 'convert integer to date';
```
**Purpose:** Converts an integer (days since 1900-01-01) to a proper PostgreSQL `date`. Used throughout for date representation.

---

### 3b. `qk_unitestr(character varying, character varying)` — Line 55
```sql
CREATE FUNCTION qk_unitestr(character varying, character varying) RETURNS character varying
    AS $_$
BEGIN
RETURN (regexp_replace($1,' ','','g')||'#'|| $2 );
END;$_$
    LANGUAGE plpgsql IMMUTABLE;
```
**Purpose:** Concatenates two strings (stripping spaces from first) with a `#` separator. Likely builds a composite unit+value key.

---

### 3c. `qk_unitestr(character varying, character varying, character varying)` — Line 69
```sql
CREATE FUNCTION qk_unitestr(character varying, character varying, character varying) RETURNS character varying
    AS $_$
BEGIN
RETURN (regexp_replace($1,' ','','g') || regexp_replace($2,' ','','g') ||'#'||$3);
END;$_$
    LANGUAGE plpgsql IMMUTABLE;
```
**Purpose:** Three-argument overload of the above, strips spaces from first two args.

---

## 4. tbsstkhouse — Table Schema (Line 14605)

This is the **primary stock-quantity table** that CSV data maps to.

```sql
CREATE TABLE tbsstkhouse (
    sstkno        character varying(30) DEFAULT '' NOT NULL,  -- stock item number
    shouseno      character varying(10) DEFAULT '' NOT NULL,  -- warehouse/house number
    sstoreplace   character varying(30) DEFAULT ''::character varying,  -- store place
    fbeginqty    numeric(21,8) DEFAULT 0,   -- beginning quantity
    fsafeqty     numeric(21,8) DEFAULT 0,   -- safety quantity
    flimitqty    numeric(21,8) DEFAULT 0,   -- limit quantity
    fcurqty      numeric(21,8) DEFAULT 0,   -- current quantity
    fbrowqty     numeric(21,8) DEFAULT 0,   -- borrowed quantity
    flendqty     numeric(21,8) DEFAULT 0,   -- lent quantity
    fstkendqty   numeric(21,8) DEFAULT 0,  -- ending quantity
    stimestamp   character varying(18) DEFAULT ''::character varying,
    smodifyflag  character varying(80) DEFAULT ''::character varying,
    splacerem    character varying(250) DEFAULT ''::character varying,
    fsbrowqty    numeric(21,8) DEFAULT 0,   -- ?
    fslendqty    numeric(21,8) DEFAULT 0    -- ?
);
```

**CSV column mapping (15 columns):**
```
sstkno | shouseno | sstoreplace | fbeginqty | fsafeqty | flimitqty | fcurqty |
fbrowqty | flendqty | fstkendqty | stimestamp | smodifyflag | splacerem |
fsbrowqty | fslendqty
```

**Insert example (line 1207458):**
```sql
INSERT INTO tbsstkhouse VALUES
('VB048','A','',8.00000000,8.00000000,0.00000000,41.00000000,0.00000000,0.00000000,41.00000000,'','','',0.00000000,0.00000000);
```

---

## 5. Related Stock Tables (Potential Update Targets)

### `tbsstklocation` — Line 14666
Per-location stock quantities within a house.
```sql
CREATE TABLE tbsstklocation (
    sstkno, shouseno, shouseloc,
    fbeginqty, fcurqty, fbrowqty, flendqty, fstkendqty,
    stimestamp, smodifyflag, scorpcode, dtmodify, smodifycorpcode
);
```

### `tbsstklendqty` — Line 14648
Lending/borrowing quantities by customer and stock.
```sql
CREATE TABLE tbsstklendqty (
    skind, scustno, sstkno, shouseno,
    flendbeginqty, fretbeginqty, flendendqty, fretendqty
);
```

### `tbsstock` — Line 14892
Master stock item definition (not per-house, but per-item with aggregated qty fields).
Key qty columns: `fecmqty`, `fstdpave`, `fbeginqty`, `fsafeqty`, `fcurqty`

### `tbsinout` — Line 11531
Transaction type classification table (in/out flag per program/function).
```sql
CREATE TABLE tbsinout (
    soutcorp, sincorp, ssubcode, sfunno, imainprog,
    iinout, itrans, iadd, idelete, iupdate,
    itemno, isliptrans, ihouse
);
```
This defines which programs/functions are "in" vs "out" transactions.

---

## 6. How tbsstkhouse Was Populated

No triggers or stored procedures were found. Stock updates occur via:

1. **Direct INSERT/UPDATE statements** from the client application
2. **Batch imports** — the CSV rows in the dump are raw INSERT statements (lines 1207458+)
3. **Client application logic** — the app computes and writes quantities to `fcurqty`, `fbrowqty`, etc.

**No automatic propagation** from `tbsstock` to `tbsstkhouse` was detected in the schema.

---

## 7. Summary

| Item | Count |
|------|-------|
| CREATE TRIGGER | 0 |
| CREATE PROCEDURE | 0 |
| CREATE FUNCTION | 3 |
| tbsstkhouse inserts | ~2400+ (lines 1207458+) |

**Conclusion:** The legacy system does NOT use PostgreSQL triggers or stored procedures for stock maintenance. Stock quantity updates are handled entirely by the client application's business logic, which issues direct SQL INSERT/UPDATE commands to `tbsstkhouse`. The canonical stock record per (stock, house) is `tbsstkhouse`.
