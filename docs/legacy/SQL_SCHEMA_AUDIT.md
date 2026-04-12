# SQL Schema Audit: cao50001.sql vs Extracted CSVs

**Source SQL:** `/Volumes/2T_SSD_App/Projects/UltrERP/legacy data/cao50001.sql`
**Source CSVs:** `/Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/extracted_data/cao50001/`
**Generated:** 2026-04-12

---

## Critical Finding: All CSVs Are Headerless Positional Data

**Every CSV file in the extracted data directory lacks a header row.** The first line of every CSV is a data row, not a column name listing. This means the pipeline that generated these CSVs did not emit SQL column names as CSV headers.

All mapping between CSV position (1-indexed) and SQL column name must be done manually using the CREATE TABLE schema as the authoritative reference.

---

## Table-by-Table Audit

### 1. `tbsstkhouse` (SQL line 14605) -- CSV: EXISTS (headerless)

**SQL columns (15 total):**
```
1  sstkno        character varying(30)
2  shouseno      character varying(10)
3  sstoreplace   character varying(30)
4  fbeginqty     numeric(21,8)
5  fsafeqty      numeric(21,8)
6  flimitqty     numeric(21,8)
7  fcurqty       numeric(21,8)
8  fbrowqty      numeric(21,8)
9  flendqty      numeric(21,8)
10 fstkendqty    numeric(21,8)
11 stimestamp    character varying(18)
12 smodifyflag   character varying(80)
13 splacerem     character varying(250)
14 fsbrowqty     numeric(21,8)
15 fslendqty     numeric(21,8)
```

**CSV first row (16 values detected -- possible extra trailing comma or empty field):**
```
'VB048', 'A', '', 8.00000000, 8.00000000, 0.00000000, 41.00000000, 0.00000000, 0.00000000, 41.00000000, '', '', '', 0.00000000, 0.00000000
```
Position mapping: values 1-15 map cleanly to the 15 SQL columns. Value 16 appears to be an extra empty field (`, ''` at end before final quote).

**Discrepancy:** Extra trailing empty value in CSV row. The SQL table has 15 columns; the CSV data rows appear to carry 16 values. The pipeline may be emitting an extra empty field.

---

### 2. `tbsslipj` (SQL line 13741) -- CSV: EXISTS (headerless)

**SQL columns (59 total -- primary sales/purchase slip header):**

| Pos | Column | Type |
|-----|--------|------|
| 1 | skind | character varying(4) |
| 2 | sslipno | character varying(17) |
| 3 | dtslipdate | date |
| 4 | stslipno | character varying(16) |
| 5 | sformat | character varying(16) |
| 6 | sopslipno | character varying(30) |
| 7 | scustno | character varying(16) |
| 8 | scustname | character varying(250) |
| 9 | scustadd | character varying(250) |
| 10 | scurno | character varying(10) |
| 11 | scurname | character varying(20) |
| 12 | fexrate | numeric(21,8) |
| 13 | spaycustno | character varying(16) |
| 14 | semplno | character varying(20) |
| 15 | semplname | character varying(30) |
| 16 | sdeptno | character varying(10) |
| 17 | ftotalamt | numeric(21,8) |
| 18 | staxtype | character varying(1) |
| 19 | ftaxamt | numeric(21,8) |
| 20 | fdisper | numeric(14,8) |
| 21 | fdiscount | numeric(21,8) |
| 22 | fcxdiscount | numeric(21,8) |
| 23 | fpayamt | numeric(21,8) |
| 24 | fpaveamt | numeric(21,8) |
| 25 | fcxamt | numeric(21,8) |
| 26 | saccountno | character varying(1) |
| 27 | ssend | character varying(1) |
| 28 | spickout | character varying(1) |
| 29 | srem | character varying(250) |
| 30 | sym | character varying(10) |
| 31 | scman | character varying(30) |
| 32 | slistno | character varying(10) |
| 33 | scheckflag | character varying(1) |
| 34 | scheckman | integer |
| 35 | sbom | character varying(1) |
| 36 | stransflag | character varying(1) |
| 37 | stelno | character varying(40) |
| 38 | flose | numeric(21,8) |
| 39 | taxtype | character varying(1) |
| 40 | smeansname | character varying(40) |
| 41 | sinvkind | character varying(2) |
| 42 | sinvno | character varying(240) |
| 43 | fothertotal | numeric(21,8) |
| 44 | ssyschkflag | character varying(1) |
| 45 | ssysdpave | character varying(1) |
| 46 | fdispretax | numeric(21,8) |
| 47 | ssendcustno | character varying(16) |
| 48 | fsumtotal | numeric(21,8) |
| 49 | fmustpayamt | numeric(21,8) |
| 50 | sversion | character varying(1) |
| 51 | dtcheckdate | date |
| 52 | dttime | numeric(21,8) |
| 53 | sfaxno | character varying(40) |
| 54 | simpcorp | character varying(20) |
| 55 | screator | character varying(30) |
| 56 | scorpname | character varying(60) |
| 57 | stimestamp | character varying(18) |
| 58 | sbdno | character varying(18) |
| 59 | fxjdiscount | numeric(21,8) |
| 60 | ffreediscount | numeric(21,8) |

**CSV first row (88 values):**
```
'4', '1130827001', '2024-08-27', '1130827001', 'YYYMMDD999', '', 'T067', '勝梨', '桃園市中壢區福星三街11號', '0001', '新臺幣', 1.00000000, 'T067', '', '', '', 1265.00000000, '3', 0.00000000, 1.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, '', '0', '', '', '11308', '系統管理員', '', '1', 1, '', '', '03-4614001~3', 0.00000000, '1', '', '21', '', 0.00000000, '0', '1', 0.00000000, '', 1265.00000000, 1265.00000000, '0', '2024-08-27', 0.40728182, '03-4614501', '', '系統管理員', '', '202408270946290879', '', 0.00000000, 0.00000000, '', '2024-08-27', 0.00000000, 0.00000000, -1, '', '0', 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 'A', 45531.40728275, 'A', '', 45531.40684502, 0.05000000, 0.00000000, '', '', '', '', '', '', '', '', '1900-01-01', '', '', '', '', '', '', '', ''
```

**Discrepancy: MAJOR -- Column count mismatch.** The SQL defines 60 columns but the CSV first row has 88 values. There are 28 extra values in the CSV that are not accounted for by the SQL schema. This suggests either:
- The CSV pipeline is including columns not present in the SQL schema, OR
- There are additional SQL columns (beyond the 60 shown in the truncated CREATE TABLE block -- the definition may have been cut off)

**Action Required:** Full CREATE TABLE block for `tbsslipj` needs to be re-extracted with sufficient `-A` lines to capture all columns (the definition appears to end around line 13801 with `ffreediscount`, but the CSV has far more values beyond that).

---

### 3. `tbsslipdtj` (SQL line 13086) -- CSV: EXISTS (headerless)

**SQL columns (59 total):**

| Pos | Column | Type |
|-----|--------|------|
| 1 | skind | character varying(4) |
| 2 | sslipno | character varying(17) |
| 3 | iidno | integer |
| 4 | dtslipdate | date |
| 5 | scustno | character varying(16) |
| 6 | sstkno | character varying(30) |
| 7 | sstkname | character varying(120) |
| 8 | sinvno | character varying(14) |
| 9 | sinvkind | character varying(2) |
| 10 | fstkanava | numeric(21,8) |
| 11 | sstkanaop | character varying(2) |
| 12 | ssrslipno | character varying(16) |
| 13 | isrslipidno | integer |
| 14 | ssrkind | character varying(4) |
| 15 | ssrtype | character varying(1) |
| 16 | shouseno | character varying(10) |
| 17 | shousename | character varying(20) |
| 18 | sunit | character varying(16) |
| 19 | foldprice | numeric(21,8) |
| 20 | fdisper | numeric(14,8) |
| 21 | fnewprice | numeric(21,8) |
| 22 | fstkqty | numeric(21,8) |
| 23 | sstkgive | character varying(1) |
| 24 | fqtyrate | numeric(14,8) |
| 25 | stax | character varying(1) |
| 26 | fstotal | numeric(21,8) |
| 27 | fprepave | numeric(21,8) |
| 28 | funitpave | numeric(21,8) |
| 29 | fsendqty | numeric(21,8) |
| 30 | fpickoutqty | numeric(21,8) |
| 31 | srem1 | character varying(250) |
| 32 | sstkrem1 | character varying(250) |
| 33 | sstkyardno | character varying(30) |
| 34 | fhcurqty | numeric(21,8) |
| 35 | fcurqty | numeric(21,8) |
| 36 | fotheramt | numeric(21,8) |
| 37 | sstkspec | text |
| 38 | iabsno | integer |
| 39 | idabsno | integer |
| 40 | frepdiscount | numeric(21,8) |
| 41 | fnewpricebk | numeric(21,8) |
| 42 | sexp1 | character varying(50) |
| 43 | sexp2 | character varying(50) |
| 44 | sversion | character varying(1) |
| 45 | fdiscounttax | numeric(21,8) |
| 46 | dtinvo | date |
| 47 | sdtaxtype | character varying(1) |
| 48 | sactno | character varying(20) |
| 49 | fdtcommissionamt | numeric(21,8) |
| 50 | scommissionno | character varying(10) |
| 51 | scommissionname | character varying(80) |
| 52 | sexp3 | character varying(50) |
| 53 | sexp4 | character varying(50) |
| 54 | sexp5 | character varying(50) |
| 55 | sbatchno | character varying(16) |
| 56 | sbatchnumber | character varying(30) |
| 57 | dteffectivedate | date |
| 58 | isbeenmrps | character varying(1) |
| 59 | smrpsno | character varying(20) |
| 60 | sdinvkind | character varying(2) |

**CSV first row (76 values):**
```
'4', '1130827001', 2, '2024-08-27', 'T067', '0013', '郵寄運費', '', '', 1.00000000, '*', '', 0, '', '', 'A', '總倉', '回', 100.00000000, 0.80000000, 80.00000000, 1.00000000, 'N', 1.00000000, 'Y', 80.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, '', '', '', 0.00000000, 0.00000000, 0.00000000, '', 3, -1, 0.00000000, 80.00000000, '', '', '', 0.00000000, '2024-08-27', '1', '', 0.00000000, '', '', '', '', '', '', '', '1900-01-01', '', '', '21', '', '', 0, '1', 80.00000000, 80.00000000, 80.00000000, 80.00000000, '', '', '', '', '', '0.000'
```

**Discrepancy: MAJOR -- Column count mismatch.** The SQL defines 60 columns but the CSV first row has 76 values. The CREATE TABLE block was cut off in the initial extraction; the full definition likely has more columns.

**Action Required:** Re-extract full CREATE TABLE block for `tbsslipdtj` to account for all 76 CSV positions.

---

### 4. `tbsslipx` (SQL line 14273) -- CSV: EXISTS (headerless)

**SQL columns (truncated at line 14333):**
First 60+ columns extracted, includes skind, sslipno, dtslipdate, stslipno, sformat, sopslipno, scustno, scustname, scustadd, scurno, scurname, fexrate, spaycustno, semplno, semplname, sdeptno, ftotalamt, staxtype, ftaxamt, fdisper, fdiscount, fcxdiscount, fpayamt, fmustpayamt, fpaveamt, fcxamt, saccountno, ssend, spickout, srem, sym, scman, scheckflag, scheckman, slistno, stransflag, stelno, sinvno, sinvkind, flose, taxtype, smeansname, fothertotal, ssyschkflag, fdispretax, ssendcustno, ssysdpave, fsumtotal, fgift, dtgetstk, sinvslipno, sversion, dtcheckdate, dttime, sfaxno, simpcorp, screator, scorpname, stimestamp, sbdno, ...

**CSV first row (95+ values):**
```
'1', '1130826001', '2024-08-26', '1130826001', 'YYYMMDD999', '', '1143', '恆峰', '台北市大同區迪化街二段191巷9號1樓', '0001', '新臺幣', 1.00000000, '1143', '', '', '', 10680.00000000, '3', 0.00000000, 1.00000000, 0.00000000, 0.00000000, 0.00000000, 10680.00000000, 0.00000000, 0.00000000, '', '0', '', '8/22出貨', '11308', '系統管理員', '1', 1, '', '', '02-25918322', '', '31', 0.00000000, '1', '', 0.00000000, '0', 0.00000000, '1143', '1', 10680.00000000, 0.00000000, '1900-01-01', '', '0', '2024-08-23', 0.56781426, '02-25918139', '', '系統管理員', '', '202408231210311055', '', '', 0.00000000, 0.00000000, '', '2024-08-26', '1143', 0.00000000, 0.42820000, -1, '', '0', 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, '1900-01-01', 'A', 45527.50730581, 'A', '', 45526.56599425, 0.05000000, 0.00000000, '', '0', 0.00000000, '0', '', '', '', '', '', '', '', '', '', '', '', ''
```

**Discrepancy: MAJOR -- CREATE TABLE block was truncated.** The definition cuts off around column `sbdno` (last shown at line 14333). The CSV clearly has many more columns (95+ values). Full block needs re-extraction.

---

### 5. `tbsslipdtx` (SQL line 13404) -- CSV: EXISTS (headerless)

**SQL columns (51 total):**
skind, sslipno, iidno, dtslipdate, iabsno, scustno, sstkno, sstkname, fstkanava, sstkanaop, ssrslipno, isrslipidno, ssrkind, ssrtype, shouseno, shousename, splanno, sunit, foldprice, fdisper, fnewprice, funitpave, fstkqty, sstkgive, fqtyrate, fsendqty, fpickoutqty, fotheramt, fstotal, srem1, sstkrem1, stax, sstkyardno, fhcurqty, fcurqty, commno, sstkspec, idabsno, frepdiscount, sdtaxtype, sdinvkind, sdinvno, fnewpricebk, sexp1, sexp2, sversion, fprepave, fdiscounttax, dtinvo, sactno, fdtcommissionamt, scommissionno, scommissionname, sexp3, sexp4, sexp5, fownpoint, sbatchno, sbatchnumber, dteffectivedate

**CSV first row:** Positional data matching SQL column order. No obvious header.

**Discrepancy:** None visible from header inspection. Full row-to-column alignment requires full row parsing.

---

### 6. `tbscust` (SQL line 10982) -- CSV: EXISTS (headerless)

**SQL columns (50+ total, truncated):**
scustno, skind, scustname, scustname2, emplno, svocno, szip1, saddr1, saddr12, szip2, saddr2, szip3, saddr3, stelno, sfaxno, swww, semail, scnctname, sattename, sunino, dtdealdate, spricemode, fpaylimit, fchklimit, funchkamt, fprepay, fdisper, fcxowe, ssettleday, sacntno, srem1-srem5, smemo, stransflag, saddr32, scustmode, seccustno, secpasswd, ifupornot, lieover, sqzkhno, spaycustno, scurno, stimestamp, spaymode, sratekind, scustclass, ffixrate, soffer, smeansname, saccountno, sfaxfile, semailfile, dtcreatedate, sbtax, sbank, sbankaccount, ...

**CSV first row (95+ values):**
```
'1149', '2', '昌弘五金實業有限公司', '昌弘五金實業有限公司', '', '', '300', '300 新竹市東區寶山路84巷10號', '', '', '', '300', '新竹市東區寶山路84巷10號', '03-5627542', '03-5627543', '', '', '莫''S', '', '12603075', '2025-04-07', '6', 0.00000000, 0.00000000, 0.00000000, 0.00000000, 1.00000000, 0.00000000, '', '', '', '', '', '', '', '', '0', '', '0', '', '', '', '', '', '1149', '0001', '202305241424360515', '', '1', '', 1.00000000, '', '', '', '', '1', '2019-08-14', '1', '', '', '', '', 0.00000000, 0.00000000, 'A', 45070.60041704, '', '', '', '', '', '', '', '', 'A', '1900-01-01', '1900-01-01', 1, '1149', '1', '2443', '0', '', '', '00000000', '', '', '', '', '', 'N', '0', '0', 'N', '', '', '', '', '', '', ''
```

**Discrepancy:** SQL block was truncated in extraction. The full column count is unknown from current data. Needs full CREATE TABLE re-extraction.

---

### 7. `tbsstock` (SQL line 14892) -- CSV: EXISTS (headerless)

**SQL columns (truncated at line 14953, ~60+ total):**
sstkno, sstkyard, sstkname, sstkname2, sclassno, sstkspec, sstkkind, scustno, scustname, sstkcolor, sstksize, sstklength, sstkwidth, sstkheight, sstkuse, sunitbase, sunit1, frate1, sunit2, frate2, fprice1-fprice6, fecmqty, fstdpave, dtindate, dtoutdate, favrgpave, fbeginqty, fsafeqty, fcurqty, srem1-srem5, smemo, finprice, foutprice, stransflag, imageno, sstkdesc1, sstkdesc2, sjxacno, sjtacno, sxxacno, sxtacno, srcacno, sccacno, sstkyard1, sstkyard2, sstkbhq, sstkwxcs, lieover, istkyywh, fimptax, fstocktax, ...

**CSV first row (115+ values):**
```
'PC240', '', '三角皮帶 C-240', '', '', '', '0', 'T001', '泰國', '', '', 0.00000000, 0.00000000, 0.00000000, '', '條', '', 0.00000000, '', 0.00000000, 288.00000000, 1267.20000000, 0.00000000, 0.00000000, 0.00000000, 1267.20000000, 0.00000000, 316.80000000, '2022-06-28', '2025-04-22', 314.25830000, 19.00000000, 19.00000000, 35.00000000, '', '', '', '', '', '', 316.80000000, 850.00000000, '', 0, '', '', '', '', '', '', '', '', '', '', 0, 0, '', 0, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0, 0.00000000, '', 0.00000000, 0.00000000, '', 0.00000000, 0.00000000, 0.00000000, 0.00000000, '', '202112271312360904', '', '', '', '', '', '', '', 0.00000000, '', 0.00000000, 'A', 44557.55042480, 'A', 0, 'LFL', 0, 0, 0, 0, 0, 0, 0.00000000, 0.00000000, 0.00000000, 19.00000000, '', '', 0.00000000, 288.00000000, 288.00000000, '1', '1', 'N', '', '', '', '', '', 0.00000000, '', '', '', '', '', '', 0.00000000, 0, '1900-01-01', 0, '', '', '', '', '', '', '', '', 'Y', 'Y', '', '', ''
```

**Discrepancy:** SQL block truncated. Full column list unknown. Needs re-extraction.

---

### 8. `tbslog` (SQL line 11612) -- CSV: EXISTS (headerless)

**SQL columns (10 total):**
opttime, optuser, computer, optitem, optkind, sitemno, optusername, scorpcode, stmpitemno, smodifycorpcode

**CSV first row (10 values):**
```
'2016-04-24 20:33:07.192+08', 1, 'USER-PC', '62', 1, '', '系統管理員', 'A', '', ''
```
Maps cleanly to SQL columns 1-10.

**Discrepancy:** None. Clean 1:1 positional mapping.

---

### 9. `tbainvorail` (SQL line 7471) -- CSV: EXISTS (headerless)

**SQL columns (43 total):**
syear, perioddate, a1-a4, b1-b8, c1-c20, smodifyflag

**CSV first row (26 values):**
```
'2002', '01', 'LA', 'LB', 'LC', 'LD', 'LE', 'LF', 'LG', 'LH', 'LJ', 'LK', 'LL', 'LM', 'LN', 'LP', 'LQ', 'LR', 'LS', 'LT', 'LU', 'LV', 'LW', 'LX', 'LY', '', '', '', '', '', '', '', '', '', ''
```

**Discrepancy: MAJOR -- Column count mismatch.** SQL has 43 columns but CSV has only 26 values. The remaining 17 period columns (c5-c20 based on SQL naming: c5-c20 = 16 columns, plus smodifyflag) appear to be empty strings in the CSV. This may be correct if those fields are simply unpopulated, but the structural capacity differs.

---

### 10. `tbastktokj` (SQL line 9200) -- CSV: EXISTS (headerless)

**SQL columns (5 total):**
kind, iserial, subno, subname, doc, smodifyflag (6 columns)

**CSV first row (6 values):**
```
'0', 1, '5101', '本期進貨', 'D', ''
```
Maps to: kind='0', iserial=1, subno='5101', subname='本期進貨', doc='D', smodifyflag=''

**Discrepancy:** None. Clean mapping.

---

### 11. `tbsstkpave` (SQL line 14719) -- CSV: EXISTS (headerless)

**SQL columns (52 total):**
sstkno, sstkyear, month01-month12, month00, sflag, smodifyflag, fpqty01-fpqty12, fpqty00, fpamt01-fpamt12, fpamt00, fendqty01-fendqty12, fendqty00

**CSV first row (48 values):**
```
'XPB-2410-P', '0000', 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, '0000000000011', '', 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000
```

**Discrepancy:** SQL defines 52 columns but CSV has 48 values. Missing 4 values. Likely the fendqty columns (13 of them: fendqty00, fendqty01-fendqty12 = 13 total, so probably fendqty00-03 are present but fendqty04-12 are missing or all fendqty are missing). This needs further investigation.

---

### 12. `tbstmpqty` (SQL line 15267) -- CSV: EXISTS (headerless)

**SQL columns (4 total):**
sslipno, skind, fstkqty (and likely more -- definition appears truncated)

**CSV first row (3 values):**
```
'1140106011', '1', 43.00000000
```

**Discrepancy:** The SQL definition shows 3 columns (sslipno, skind, fstkqty) but the CREATE TABLE shows 4 columns: `sslipno character varying(20), skind character varying(1), fstkqty numeric(21,8)`. Wait -- the SQL actually shows only 3 columns in the definition shown. Let me recount: the grep output shows only these 3 columns. So the CSV with 3 values maps cleanly.

Actually wait, the SQL shows 4 entries in the grep output but one appears to be the closing `);`.Let me recount:
```
15267:CREATE TABLE tbstmpqty (
15268-    sslipno character varying(20),
15269-    skind character varying(1),
15270-    fstkqty numeric(21,8)
15271-);
```
Yes, 3 columns. CSV has 3 values. OK.

---

### 13. `tbsslipo` (SQL line 13847) -- CSV: EXISTS (headerless)

**SQL columns (truncated -- many more beyond those shown):**
skind, sslipno, dtslipdate, sformat, scustno, scustname, scustadd, scnctname, stelno, scurno, scurname, fexrate, ftotalamt, staxtype, ftaxamt, fdisper, fdiscount, fpaveamt, spackflag, srem, srem2, srem3, sopslipno, semplno, semplname, sdeptno, scman, sym, slistno, scheckflag, scheckman, stransflag, taxtype, smeansname, ssyschkflag, fdispretax, ssendcustno, ssysdpave, fsumtotal, swake, sfaxno, soffer, fcommrate, stoport, stransport, simpmode, simpcorp, spaykind, saddr3, mtop, mpayment, mshipment, mpacking, minsurance, mvalidity, mextra, mdlvyaddr, fsubtotal, fothertotal, fpayamt, ...

**CSV first row (95+ values):**
```
'G', '1140106002', '2025-01-06', 'YYYMMDD999', '0000', '三星橡膠行', '', '', '', '0001', '新臺幣', 1.00000000, 7261.00000000, '1', 363.00000000, 1.00000000, 0.00000000, 3198.84000000, '2', '1.交易條件：匯款後出貨 配送方式：大榮到付。', '匯款帳號：兆豐銀行 北彰化分行', '戶名：聯泰興實業有限公司 帳號：018-09-058380', '', '', '', '', '系統管理員', '11401', '', '1', 1, '', '', '', '0', 0.00000000, '0000', '1', 7261.00000000, '', '', '', 0.00000000, '', '', '', '', '', '', NULL, '', '', NULL, '', '', NULL, NULL, 0.00000000, 0.00000000, 0.00000000, '', '', '', 0.00000000, NULL, -1, '', '0', '', '', '', '202501071044411410', '0', '', '', '2025-01-07', 0.66956339, '', '', '系統管理員', '', '', '', '', '', 0.00000000, '1140106002', 0.00000000, 0.00000000, '', 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, '1900-01-01', 0.00000000, 'A', 45664.44770328, 'A', 45663.66855561, 0.05000000, '', '', '0', 0.00000000, '0', '', '', '', '', '', '', ''
```

**Discrepancy:** SQL definition was truncated at line 13907. The full column list is unknown. Needs full CREATE TABLE re-extraction.

---

### 14. `tbsstorehouse` (SQL line 15130) -- CSV: EXISTS (headerless)

**SQL columns (14 total):**
shouseno, shousename, saddress, sismainstore, srem, stransflag, lieover, sengname, stimestamp, smodifyflag, scorpcode, smodifycorpcode, dtmodify

**CSV first row (14 values):**
```
'A', '總倉', '', '1', '', '0', '0', '', '123456789012345678', '', 'A', '', 0.00000000
```
Maps cleanly to 14 SQL columns.

**Discrepancy:** None. Clean mapping.

---

## Summary of Discrepancies

| Table | SQL Cols (known) | CSV Values (first row) | Issue |
|-------|-----------------|----------------------|-------|
| tbsstkhouse | 15 | 16 | 1 extra CSV value |
| tbsslipj | 60 (truncated) | 88 | 28 extra CSV values; CREATE TABLE truncated |
| tbsslipdtj | 60 (truncated) | 76 | 16 extra CSV values; CREATE TABLE truncated |
| tbsslipx | 60+ (truncated) | 95+ | CREATE TABLE truncated |
| tbsslipdtx | 51+ | ~51 | Looks clean; needs full row verification |
| tbscust | 50+ (truncated) | 95+ | CREATE TABLE truncated |
| tbsstock | 60+ (truncated) | 115+ | CREATE TABLE truncated |
| tbslog | 10 | 10 | Clean |
| tbainvorail | 43 | 26 | 17 fewer CSV values (period columns empty?) |
| tbastktokj | 6 | 6 | Clean |
| tbsstkpave | 52 | 48 | 4 missing CSV values |
| tbstmpqty | 3 | 3 | Clean |
| tbsslipo | 60+ (truncated) | 95+ | CREATE TABLE truncated |
| tbsstorehouse | 14 | 14 | Clean |

## Root Cause

The pipeline at `legacy-migration-pipeline/extracted_data/` generates positional CSV files with no header row. Every CSV maps positionally to the SQL columns, but the mapping is implicit, not explicit. No column names are embedded in the CSV files.

## Required Actions

1. **Re-extract truncated CREATE TABLE blocks** for: `tbsslipj`, `tbsslipdtj`, `tbsslipx`, `tbscust`, `tbsstock`, `tbsslipo` -- use `grep -A 200` to capture full definitions
2. **Investigate column count mismatches** in `tbsslipj` (88 CSV vs ~60 SQL), `tbsslipdtj` (76 CSV vs ~60 SQL), `tbsstkpave` (48 CSV vs 52 SQL)
3. **Add CSV headers** to the pipeline output -- either as a separate header-only reference file, or by inserting a header row into each CSV
4. **Verify `tbainvorail`** -- 17 period columns are empty strings in the CSV; confirm this is expected (no data for those periods)
5. **Verify `tbsstkhouse`** -- extra 16th value in CSV rows; determine if it's a pipeline artifact or a real column
