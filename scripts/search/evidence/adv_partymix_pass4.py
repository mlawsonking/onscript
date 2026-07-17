"""ADVERSARIAL REPRO pass 4 — test the CANDIDATE definition precisely.

Candidate: over the legacy lane's FINAL YEAR (2020-01-01 -> the seam at 2021-01-03), measure
each lane's party mix over IDENTICAL MONTHS (which is exactly what the ledger prose claims:
"the two lanes carry materially different party mixes over identical months").
Test that plus every nearby boundary variant, to see how fragile the match is.
"""
import sys, collections
sys.path.insert(0, ".")
from pipeline import fetch, util

_PARTY = {"D": "D", "R": "R", "I": "I", "Democrat": "D", "Republican": "R",
          "Independent": "I", "ID": "I", "Democratic": "D"}

recs = []  # (lane, date, party)
for f in sorted(fetch.MIRROR.glob("20*.jsonl")):
    for r in util.iter_jsonl(f):
        date = (r.get("date") or "")[:10]
        if len(date) != 10 or not ("2018-01-01" <= date <= "2022-12-31"):
            continue
        lane = r.get("date_source") or "<MISSING>"
        p = _PARTY.get((r.get("member") or {}).get("party"))
        if p:
            recs.append((lane, date, p))

def mix(lane, lo, hi):
    c = collections.Counter(p for l, d, p in recs if l == lane and lo <= d <= hi)
    d, r = c["D"], c["R"]
    return d, r, (d / r if r else float("nan")), (100 * d / (d + r) if d + r else float("nan"))

VARIANTS = [
    ("legacy final year -> seam", "2020-01-01", "2021-01-03"),
    ("calendar 2020 only",        "2020-01-01", "2020-12-31"),
    ("2020-01 .. 2021-01 (mo)",   "2020-01-01", "2021-01-31"),
    ("2020-01 .. 2021-02 (mo)",   "2020-01-01", "2021-02-28"),
    ("trailing 12mo to seam",     "2020-01-04", "2021-01-03"),
    ("116th 2nd session",         "2020-01-03", "2021-01-03"),
    ("2019-01 .. seam (2y)",      "2019-01-01", "2021-01-03"),
    ("2018-01 .. seam (overlap)", "2018-01-01", "2021-01-03"),
]

print(f"{'variant':28s} {'legacy D:R':>11s} {'lg D-sh%':>9s} {'n_leg':>8s} | {'scraper D:R':>12s} {'sc D-sh%':>9s} {'n_scr':>7s} | {'gap pt':>7s}")
print("-" * 108)
for name, lo, hi in VARIANTS:
    ld, lr, lx, lsh = mix("legacy", lo, hi)
    sd, sr, sx, ssh = mix("scraper", lo, hi)
    gap = lsh - ssh
    hit = ""
    if abs(round(lx, 3) - 1.538) < 0.0006 and abs(round(sx, 2) - 1.12) < 0.0006:
        hit = "  <<<< BOTH MATCH CANON"
    print(f"{name:28s} {lx:11.4f} {lsh:9.2f} {ld+lr:8,} | {sx:12.4f} {ssh:9.2f} {sd+sr:7,} | {gap:7.2f}{hit}")

print("\n=== CANON ===")
print("  legacy D:R = 1.538 (D-share 60.598%) | scraper D:R = 1.12 (D-share 52.830%) | gap 7.77pt")

print("\n=== EXACT ARITHMETIC FOR THE MATCHING VARIANT ===")
ld, lr, lx, lsh = mix("legacy", "2020-01-01", "2021-01-03")
sd, sr, sx, ssh = mix("scraper", "2020-01-01", "2021-01-03")
print(f"  legacy  2020-01-01..2021-01-03: D={ld:,} R={lr:,}  D:R = {ld}/{lr} = {lx:.6f} -> round3 = {round(lx,3)}")
print(f"  scraper 2020-01-01..2021-01-03: D={sd:,} R={sr:,}  D:R = {sd}/{sr} = {sx:.6f} -> round2 = {round(sx,2)}")
print(f"  D-share gap = {lsh:.3f}% - {ssh:.3f}% = {lsh-ssh:.2f}pt   (canon: 7.7pt)")
