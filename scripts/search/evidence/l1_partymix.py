"""Reproduce canon's claim: "legacy D:R = 1.538, scraper D:R = 1.12" (a 7.7pt shift).

Canon's split-halves boundary is A=2013-2020, B=2022-2026. Measure the party mix per lane
under every plausible definition (statements vs distinct members, full-lane vs half-window,
and the same-window overlap that controls for era) to find which one canon computed -- or
establish that none of them reproduce it.
"""
import sys, json, collections
sys.path.insert(0, ".")
from pipeline import fetch, util

_PARTY = {"D": "D", "R": "R", "I": "I", "Democrat": "D", "Republican": "R",
          "Independent": "I", "ID": "I"}

stmts = collections.defaultdict(collections.Counter)     # (lane, window) -> party counts
members = collections.defaultdict(lambda: collections.defaultdict(set))  # (lane,window) -> party -> bioguides
offices = collections.defaultdict(set)
sample = {}

def windows_for(date):
    w = []
    if "2013-01-01" <= date <= "2020-12-31": w.append("A:2013-2020")
    if "2022-01-01" <= date <= "2026-12-31": w.append("B:2022-2026")
    if "2013-01-01" <= date <= "2020-12-31": w.append("overlap_era:2013-2020")
    return w

for f in sorted(fetch.MIRROR.glob("*.jsonl")):
    for r in util.iter_jsonl(f):
        date = (r.get("date") or "")[:10]
        if len(date) != 10:
            continue
        lane = r.get("date_source") or "<MISSING>"
        m = r.get("member") or {}
        p = _PARTY.get(m.get("party"))
        bio = m.get("bioguide_id")
        if lane not in sample:
            sample[lane] = r
        stmts[(lane, "FULL")][p] += 1
        if bio and p:
            members[(lane, "FULL")][p].add(bio)
        for w in windows_for(date):
            stmts[(lane, w)][p] += 1
            if bio and p:
                members[(lane, w)][p].add(bio)

def ratio(c):
    d, r = c.get("D", 0), c.get("R", 0)
    return (d / r) if r else float("inf")

print("=== D:R BY STATEMENTS ===")
for (lane, w), c in sorted(stmts.items()):
    if c.get("D", 0) + c.get("R", 0) == 0:
        continue
    print(f"  {lane:11s} {w:22s} D={c.get('D',0):7,} R={c.get('R',0):7,}  D:R = {ratio(c):.3f}")

print("\n=== D:R BY DISTINCT MEMBERS ===")
for (lane, w), pm in sorted(members.items()):
    d, r = len(pm.get("D", ())), len(pm.get("R", ()))
    if d + r == 0:
        continue
    print(f"  {lane:11s} {w:22s} D={d:4d} R={r:4d}  D:R = {(d/r) if r else float('inf'):.3f}")

print("\n=== CANON'S CLAIM ===")
la = ratio(stmts[("legacy", "A:2013-2020")])
sb = ratio(stmts[("scraper", "B:2022-2026")])
print(f"  canon:    legacy(halfA) D:R = 1.538   scraper(halfB) D:R = 1.12   (shift 7.7pt)")
print(f"  measured: legacy(halfA) D:R = {la:.3f}   scraper(halfB) D:R = {sb:.3f}   (shift {abs(la-sb)*100:.1f}pt)")

print("\n=== SAME-ERA CONTROL (both lanes, 2013-2020 only) ===")
lo = ratio(stmts[("legacy", "overlap_era:2013-2020")])
so = ratio(stmts[("scraper", "overlap_era:2013-2020")])
print(f"  legacy  = {lo:.3f}")
print(f"  scraper = {so:.3f}   <- lane effect with era held constant")

print("\n=== RAW RECORD SHAPE PER LANE ===")
for lane, r in sample.items():
    keys = sorted(r.keys())
    print(f"\n  --- {lane} --- keys: {keys}")
    print("   ", json.dumps({k: (str(r.get(k))[:60]) for k in keys if k != 'text'})[:400])
