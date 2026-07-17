"""ADVERSARIAL REPRO pass 3 — EXHAUSTIVE window scan.

Q1: which contiguous month-windows give legacy D:R = 1.538? which give scraper D:R = 1.12?
Q2: is there ANY SINGLE window W with legacy(W)=1.538 AND scraper(W)=1.12 simultaneously?
    (that is what canon's sentence asserts: one comparison, two lanes)
"""
import sys, json, collections
sys.path.insert(0, ".")
from pipeline import fetch, util

_PARTY = {"D": "D", "R": "R", "I": "I", "Democrat": "D", "Republican": "R",
          "Independent": "I", "ID": "I", "Democratic": "D"}

# (lane, month) -> Counter(party); plus per-office month counts for mean-based defs
mon = collections.defaultdict(collections.Counter)
mon_off = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))  # (lane,month)->bio->party

for f in sorted(fetch.MIRROR.glob("*.jsonl")):
    for r in util.iter_jsonl(f):
        date = (r.get("date") or "")[:10]
        if len(date) != 10: continue
        lane = r.get("date_source") or "<MISSING>"
        m = r.get("member") or {}
        p = _PARTY.get(m.get("party"))
        if not p: continue
        mon[(lane, date[:7])][p] += 1
        bio = m.get("bioguide_id")
        if bio:
            mon_off[(lane, date[:7])][bio][p] += 1

months = sorted({mo for (_, mo) in mon})
LANES = ["legacy", "scraper"]

# prefix sums per lane
pref = {}
for lane in LANES:
    accD = accR = accI = 0
    ps = {}
    for i, mo in enumerate(months):
        c = mon.get((lane, mo), {})
        accD += c.get("D", 0); accR += c.get("R", 0); accI += c.get("I", 0)
        ps[i] = (accD, accR, accI)
    pref[lane] = ps

def rng(lane, i, j):
    """statements in months[i..j] inclusive"""
    a = pref[lane][j]
    b = pref[lane][i - 1] if i > 0 else (0, 0, 0)
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

MIN_N = 1000  # a party-mix claim about a lane would not rest on <1k statements

print("=== Q1a. CONTIGUOUS MONTH-WINDOWS WHERE legacy D:R rounds to 1.538 ===")
hits_l = []
for i in range(len(months)):
    for j in range(i, len(months)):
        d, r, _ = rng("legacy", i, j)
        if d + r < MIN_N or not r: continue
        x = d / r
        if abs(x - 1.538) < 0.0005:
            hits_l.append((months[i], months[j], d, r, x))
for a, b, d, r, x in hits_l[:25]:
    print(f"  legacy  {a} .. {b}   D={d:7,} R={r:7,}  D:R={x:.4f}  D-share%={100*d/(d+r):.2f}")
print(f"  ({len(hits_l)} windows total)")

print("\n=== Q1b. CONTIGUOUS MONTH-WINDOWS WHERE scraper D:R rounds to 1.12 ===")
hits_s = []
for i in range(len(months)):
    for j in range(i, len(months)):
        d, r, _ = rng("scraper", i, j)
        if d + r < MIN_N or not r: continue
        x = d / r
        if abs(x - 1.12) < 0.0005:
            hits_s.append((months[i], months[j], d, r, x))
for a, b, d, r, x in hits_s[:25]:
    print(f"  scraper {a} .. {b}   D={d:7,} R={r:7,}  D:R={x:.4f}  D-share%={100*d/(d+r):.2f}")
print(f"  ({len(hits_s)} windows total)")

print("\n=== Q2. SINGLE SHARED WINDOW: minimize |legacy-1.538| + |scraper-1.12| ===")
best = []
for i in range(len(months)):
    for j in range(i, len(months)):
        ld, lr, _ = rng("legacy", i, j)
        sd, sr, _ = rng("scraper", i, j)
        if ld + lr < MIN_N or sd + sr < MIN_N or not lr or not sr: continue
        lx, sx = ld / lr, sd / sr
        err = abs(lx - 1.538) + abs(sx - 1.12)
        best.append((err, months[i], months[j], lx, sx, ld + lr, sd + sr))
best.sort()
print(f"  {'window':22s} {'legacy D:R':>11s} {'scraper D:R':>12s} {'err':>7s}   n_leg    n_scr")
for err, a, b, lx, sx, nl, ns in best[:15]:
    print(f"  {a}..{b:9s} {lx:11.3f} {sx:12.3f} {err:7.3f} {nl:8,} {ns:8,}")

print("\n=== Q3. ANY SHARED WINDOW where BOTH are within rounding of canon? ===")
exact = [z for z in best if abs(z[3] - 1.538) < 0.0005 and abs(z[4] - 1.12) < 0.005]
print(f"  windows satisfying BOTH: {len(exact)}")
for err, a, b, lx, sx, nl, ns in exact[:10]:
    print(f"  {a}..{b}  legacy={lx:.4f} scraper={sx:.4f}")

print("\n=== Q4. CALENDAR-YEAR pairs: legacy(Y) vs scraper(Y) ===")
for y in range(2013, 2027):
    idx = [k for k, mo in enumerate(months) if mo[:4] == str(y)]
    if not idx: continue
    i, j = idx[0], idx[-1]
    ld, lr, _ = rng("legacy", i, j); sd, sr, _ = rng("scraper", i, j)
    lx = ld / lr if lr else float("nan"); sx = sd / sr if sr else float("nan")
    print(f"  {y}: legacy D:R={lx:7.3f} (n={ld+lr:7,})   scraper D:R={sx:7.3f} (n={sd+sr:6,})")

print("\n=== Q5. legacy FINAL-YEAR 2020 exact arithmetic ===")
idx = [k for k, mo in enumerate(months) if mo[:4] == "2020"]
d, r, i_ = rng("legacy", idx[0], idx[-1])
print(f"  legacy 2020: D={d:,} R={r:,} I={i_:,}")
print(f"    D:R = {d/r:.6f}  -> rounds to {round(d/r,3)}   truncates to {int(d/r*1000)/1000}")
print(f"    D-share (D/(D+R))     = {100*d/(d+r):.3f}%")
print(f"    canon 1.538 -> D-share  60.598%   | canon 1.12 -> D-share 52.830%  | gap 7.77pt")
