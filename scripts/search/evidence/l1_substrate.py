"""L1 substrate check (law L2: substrate before spec).

Measure `date_source` as it ACTUALLY exists in the 303 mirror files, rather than trusting
canon's numbers. Answers: what values exist, how many records lack the field, where each
lane starts/stops, the party mix per lane, and the true shape of the 2021-01-03 seam.
"""
import sys, json, collections
sys.path.insert(0, ".")
from pipeline import fetch, util

_PARTY = {"D": "D", "R": "R", "I": "I", "Democrat": "D", "Republican": "R",
          "Independent": "I", "ID": "I"}

vals = collections.Counter()
by_year = collections.defaultdict(collections.Counter)
party_by_lane = collections.defaultdict(collections.Counter)
minmax = {}
total = 0
missing_examples = []

for f in sorted(fetch.MIRROR.glob("*.jsonl")):
    for r in util.iter_jsonl(f):
        total += 1
        ds = r.get("date_source")
        key = ds if ds is not None else "<MISSING>"
        vals[key] += 1
        date = (r.get("date") or "")[:10]
        if len(date) != 10:
            continue
        by_year[date[:4]][key] += 1
        m = r.get("member") or {}
        p = _PARTY.get(m.get("party"))
        if p:
            party_by_lane[key][p] += 1
        lo, hi = minmax.get(key, ("9999", "0000"))
        minmax[key] = (min(lo, date), max(hi, date))
        if ds is None and len(missing_examples) < 3:
            missing_examples.append({k: r.get(k) for k in ("date", "url", "member")})

print(f"TOTAL RECORDS: {total:,}\n")
print("=== date_source VALUES ===")
for k, n in vals.most_common():
    lo, hi = minmax.get(k, ("-", "-"))
    print(f"  {k:12s} {n:8,}  ({100*n/total:5.2f}%)   {lo} -> {hi}")

print("\n=== PARTY MIX PER LANE (the 7.7pt shift canon claims) ===")
for k, c in party_by_lane.items():
    d, r = c["D"], c["R"]
    ratio = (d / r) if r else float("inf")
    print(f"  {k:12s} D={d:7,} R={r:7,} I={c['I']:5,}  D:R ratio = {ratio:.3f}")

print("\n=== PER-YEAR LANE COUNTS ===")
lanes = [k for k, _ in vals.most_common()]
print(f"  {'year':6s}" + "".join(f"{l:>12s}" for l in lanes))
for y in sorted(by_year):
    row = by_year[y]
    print(f"  {y:6s}" + "".join(f"{row[l]:12,}" for l in lanes))

print("\n=== THE SEAM: records near 2021-01-03 by lane ===")
seam = collections.defaultdict(collections.Counter)
for f in sorted(fetch.MIRROR.glob("2020-1*.jsonl")) + sorted(fetch.MIRROR.glob("2021-0*.jsonl")):
    for r in util.iter_jsonl(f):
        date = (r.get("date") or "")[:10]
        if "2020-12-01" <= date <= "2021-02-28":
            seam[date[:7]][r.get("date_source") or "<MISSING>"] += 1
for mth in sorted(seam):
    print(f"  {mth}: {dict(seam[mth])}")

if missing_examples:
    print("\n=== EXAMPLES OF RECORDS WITH NO date_source ===")
    for e in missing_examples:
        print(" ", json.dumps(e)[:200])
