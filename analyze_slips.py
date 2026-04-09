import csv
from pathlib import Path

BASE = Path('/Volumes/2T_SSD_App/Projects/UltrERP/legacy-migration-pipeline/extracted_data')

def parse_row(line):
    tokens, current, in_quote = [], [], False
    for char in line:
        if char == "'" and not in_quote:
            in_quote = True
        elif char == "'" and in_quote:
            in_quote = False
        elif char == "," and not in_quote:
            tokens.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    tokens.append("".join(current).strip())
    return tokens

def read_col(path, col_idx):
    vals = set()
    with open(path, 'r', encoding='utf-8') as f:
        next(f, None)
        for raw in f:
            try:
                row = parse_row(raw.strip())
                if len(row) > col_idx:
                    v = row[col_idx].strip().strip("'\"")
                    if v:
                        vals.add(v)
            except:
                pass
    return vals

def read_meta(path):
    types, dates, n = set(), [], 0
    with open(path, 'r', encoding='utf-8') as f:
        next(f, None)
        for raw in f:
            try:
                row = parse_row(raw.strip())
                n += 1
                if len(row) > 0:
                    types.add(row[0].strip().strip("'\""))
                if len(row) > 3:
                    d = row[3].strip().strip("'\"")
                    if d:
                        dates.append(d)
            except:
                pass
    return types, dates, n

print("=== SLIP TYPE + DATE RANGE ===")
for t in ['tbslipx','tbslipj','tbslipo','tbslipdto','tbsslipctz','tbsslipcpd']:
    p = BASE / f'{t}.csv'
    types, dates, n = read_meta(p)
    dmin = min(dates) if dates else '?'
    dmax = max(dates) if dates else '?'
    print(f"{t}: type={types}, rows={n}, dates=[{dmin} .. {dmax}]")

print("\n=== OVERLAP vs CANONICAL ===")
slipx = read_col(BASE / 'tbsslipx.csv', 2)
slipj = read_col(BASE / 'tbsslipj.csv', 2)
lipo  = read_col(BASE / 'tbslipo.csv', 2)
dto   = read_col(BASE / 'tbslipdto.csv', 2)
ctz   = read_col(BASE / 'tbsslipctz.csv', 2)
cpd   = read_col(BASE / 'tbsslipcpd.csv', 2)

print(f"tbslipo:    {len(lipo)} rows, in slipx={len(lipo&slipx)}, in slipj={len(lipo&slipj)}, UNCOVERED={len(lipo-slipx-slipj)}")
print(f"tbslipdto:  {len(dto)} rows, in slipx={len(dto&slipx)}, in slipj={len(dto&slipj)}, in lipo={len(dto&lipo)}, UNCOVERED={len(dto-slipx-slipj-lipo)}")
print(f"tbsslipctz: {len(ctz)} rows, in slipx={len(ctz&slipx)}, in slipj={len(ctz&slipj)}, in lipo={len(ctz&lipo)}, UNCOVERED={len(ctz-slipx-slipj-lipo)}")
print(f"tbsslipcpd: {len(cpd)} rows, in slipx={len(cpd&slipx)}, in slipj={len(cpd&slipj)}, in lipo={len(cpd&lipo)}, UNCOVERED={len(cpd-slipx-slipj-lipo)}")
print(f"\ntbslipo sample doc_numbers: {sorted(lipo)[:5]}")
print(f"tbslipdto sample doc_numbers: {sorted(dto)[:5]}")
