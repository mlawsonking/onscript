"""ADVERSARIAL REPRO pass 5 — final hunt for a NAMEABLE scraper definition = 1.12,
plus the coincidence audit of the one shared window found by the exhaustive scan.
"""
import sys, collections
sys.path.insert(0, ".")
from pipeline import fetch, util

_PARTY = {"D": "D", "R": "R", "I": "I", "Democrat": "D", "Republican": "R",
          "Independent": "I", "ID": "I", "Democratic": "D"}

rows = []  # (lane, date, party, bioguide)
for f in sorted(fetch.MIRROR.glob("*.jsonl")):
    for r in util.iter_jsonl(f):
        date = (r.get("date") or "")[:10]
        if len(date) != 10: continue
        lane = r.get("date_source") or "<MISSING>"
        m = r.get("member") or {}
        p = _PARTY.get(m.get("party"))
        if p:
            rows.append((lane, date, p, m.get("bioguide_id")))

def mix(pred):
    c = collections.Counter(p for l, d, p, b in rows if pred(l, d, p, b))
    d, r = c["D"], c["R"]
    return d, r, (d / r if r else float("nan"))

# scraper founding cohort: offices present in scraper's first 12 months
first = sorted({b for l, d, p, b in rows if l == "scraper" and d < "2019-01-01" and b})
cohort = set(first)
first18 = sorted({b for l, d, p, b in rows if l == "scraper" and "2018-01-01" <= d < "2019-01-01" and b})
cohort18 = set(first18)

DEFS = [
    ("scraper FULL lane",                 lambda l,d,p,b: l=="scraper"),
    ("scraper half B (2022-2026)",        lambda l,d,p,b: l=="scraper" and "2022-01-01"<=d<="2026-12-31"),
    ("scraper 2018+",                     lambda l,d,p,b: l=="scraper" and d>="2018-01-01"),
    ("scraper post-seam",                 lambda l,d,p,b: l=="scraper" and d>"2021-01-03"),
    ("scraper pre-seam",                  lambda l,d,p,b: l=="scraper" and d<="2021-01-03"),
    ("scraper 117th (2021-01-03..2023-01-02)", lambda l,d,p,b: l=="scraper" and "2021-01-03"<=d<="2023-01-02"),
    ("scraper 118th",                     lambda l,d,p,b: l=="scraper" and "2023-01-03"<=d<="2025-01-02"),
    ("scraper 2021 only",                 lambda l,d,p,b: l=="scraper" and d[:4]=="2021"),
    ("scraper 2023 only",                 lambda l,d,p,b: l=="scraper" and d[:4]=="2023"),
    ("scraper founding cohort (pre-2019 offices), all time",
                                          lambda l,d,p,b: l=="scraper" and b in cohort),
    ("scraper 2018 cohort, all time",     lambda l,d,p,b: l=="scraper" and b in cohort18),
    ("scraper 2018 cohort, half B",       lambda l,d,p,b: l=="scraper" and b in cohort18 and "2022-01-01"<=d),
    ("non-legacy lanes (scraper+page_html+missing) FULL",
                                          lambda l,d,p,b: l!="legacy"),
    ("non-legacy lanes, half B",          lambda l,d,p,b: l!="legacy" and "2022-01-01"<=d<="2026-12-31"),
]

print(f"{'definition':56s} {'D':>8s} {'R':>8s} {'D:R':>8s} {'D-sh%':>7s}   dist to 1.12")
print("-" * 105)
for name, pred in DEFS:
    d, r, x = mix(pred)
    if d + r == 0: continue
    print(f"{name:56s} {d:8,} {r:8,} {x:8.3f} {100*d/(d+r):7.2f}   {abs(x-1.12):.3f}")

print("\n=== LEGACY: nameable definitions vs canon's 1.538 ===")
LDEFS = [
    ("legacy FULL lane",              lambda l,d,p,b: l=="legacy"),
    ("legacy half A (2013-2020)",     lambda l,d,p,b: l=="legacy" and "2013-01-01"<=d<="2020-12-31"),
    ("legacy 116th congress",         lambda l,d,p,b: l=="legacy" and "2019-01-03"<=d<="2021-01-03"),
    ("legacy 2020 (calendar, FINAL YEAR)", lambda l,d,p,b: l=="legacy" and d[:4]=="2020"),
    ("legacy 116th 2nd session (2020-01-03..seam)", lambda l,d,p,b: l=="legacy" and "2020-01-03"<=d<="2021-01-03"),
    ("legacy 2020-01-01..seam",       lambda l,d,p,b: l=="legacy" and "2020-01-01"<=d<="2021-01-03"),
    ("legacy 2019-2020",              lambda l,d,p,b: l=="legacy" and "2019-01-01"<=d<="2020-12-31"),
    ("legacy 2018+",                  lambda l,d,p,b: l=="legacy" and d>="2018-01-01"),
]
print(f"{'definition':56s} {'D':>8s} {'R':>8s} {'D:R':>8s} {'D-sh%':>7s}   dist to 1.538")
print("-" * 105)
for name, pred in LDEFS:
    d, r, x = mix(pred)
    if d + r == 0: continue
    print(f"{name:56s} {d:8,} {r:8,} {x:8.3f} {100*d/(d+r):7.2f}   {abs(x-1.538):.3f}")

print("\n=== COINCIDENCE AUDIT: legacy is FROZEN past the seam; scraper sweeps through 1.12 ===")
print("  window 2020-01 .. X   -> legacy D:R (constant once X >= 2021-01) vs scraper cumulative D:R")
for X in ["2020-12-31", "2021-01-31", "2021-02-28", "2021-03-31", "2021-06-30",
          "2021-12-31", "2022-06-30", "2022-12-31"]:
    ld, lr, lx = mix(lambda l,d,p,b: l=="legacy" and "2020-01-01"<=d<=X)
    sd, sr, sx = mix(lambda l,d,p,b: l=="scraper" and "2020-01-01"<=d<=X)
    mark = "  <- 'match'" if abs(round(sx,2)-1.12) < 0.0006 else ""
    print(f"    X={X}  legacy={lx:.4f} (n={ld+lr:6,})   scraper={sx:.4f} (n={sd+sr:6,}){mark}")
print("\n  -> legacy is identical for every X past 2021-01-03 (the lane has no records there).")
print("     scraper's cumulative ratio moves continuously 1.219 -> ~1.13, so it MUST cross 1.12")
print("     at some X. The 'shared window' is an intermediate-value crossing, not a definition.")
