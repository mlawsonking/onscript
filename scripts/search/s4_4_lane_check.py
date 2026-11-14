"""S4.4 (Friday Night Dump) single-lane check, 2026-11-13 (docs/13 erratum E-2026-11-13).

docs/13 recorded the S4.4 halves as the lanes ("halves ARE the lanes"). They are not pure lanes: half
A (2013-2020) holds 25,491 scraper-lane statements beside 475,146 ProPublica-lane ones, and half B
holds 227 ProPublica-lane statements. The registered analysis therefore mixes two instruments inside
each half (about 5% in A). This script recomputes the registered estimator inside ONE lane per half
(A = propublica only, plus the scraped minority slice; B = scraped only), with a 2,000x day-block
bootstrap (seed 20260716) for the walk-back ratio.

Lexicons come from the committed registration data/reference/search/s4_4-registration.json, whose
sha256 must equal the value docs/13 L307 cites (6cbee4a8...6b6d5). Read-only on the corpus. Writes
X:/onscript-data/evidence/s4_4-lane-check/out.txt (evidence lives on X:, never in the repo).
Written for the P3 essay staging (X:/onscript-data/drafts/staged/P3/scripts/p3_lane_check.py).
Run: C:\\ProgramData\\miniconda3\\python.exe -I scripts/search/s4_4_lane_check.py
"""
import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from datetime import date as _date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from pipeline import fetch  # noqa: E402
from pipeline.search import harness, provenance  # noqa: E402

REGISTRATION = REPO / "data" / "reference" / "search" / "s4_4-registration.json"
REGISTERED_SHA256 = "6cbee4a8bda77ce876de4be41184362bda758b26fc33ec93b4452142d636b6d5"
HERE = Path("X:/onscript-data/evidence/s4_4-lane-check")
HERE.mkdir(parents=True, exist_ok=True)
END = "2026-07-09"
pre_bytes = REGISTRATION.read_bytes()
assert hashlib.sha256(pre_bytes).hexdigest() == REGISTERED_SHA256, "registration bytes changed"
PREREG = json.loads(pre_bytes.decode("utf-8"))


def _rx(forms):
    ordered = sorted(set(forms), key=len, reverse=True)
    parts = []
    for f in ordered:
        pat = re.escape(f).replace(r"\ ", r"\s+")
        lead = r"\b" if f[0].isalnum() else ""
        trail = r"\b" if f[-1].isalnum() else ""
        parts.append(f"(?:{lead}{pat}{trail})")
    return re.compile("|".join(parts))


RX = {"core": _rx(PREREG["lexicons"]["core"]["forms"]),
      "pos": _rx(PREREG["lexicons"]["positive_control"]["forms"]),
      "plac": _rx(PREREG["lexicons"]["placebo_lexicon"]["forms"])}
WORD_RE = re.compile(r"[a-z']+")


def half_of(d):
    if "2013-01-01" <= d <= "2020-12-31":
        return "A"
    if "2021-01-01" <= d <= END:
        return "B"
    return None


day = defaultdict(lambda: {"n": 0, "core": 0, "pos": 0, "plac": 0})   # (half, lane, date)
years = defaultdict(int)
for f in sorted(fetch.MIRROR.glob("*.jsonl")):
    if f.stem < "2013-01" or f.stem > END[:7]:
        continue
    with f.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            d = (r.get("date") or "")[:10]
            try:
                _date.fromisoformat(d)
            except Exception:
                continue
            h = half_of(d)
            if h is None:
                continue
            m = r.get("member") or {}
            if harness._PARTY.get(m.get("party")) not in ("D", "R", "I") or not m.get("bioguide_id"):
                continue
            low = (r.get("text") or "").lower()
            if len(WORD_RE.findall(low)) < 20:
                continue
            src = provenance.date_source_of(r)
            lane = str(provenance.INSTRUMENTS.get(src) if src is not None else None)
            c = day[(h, lane, d)]
            c["n"] += 1
            for k, rx in RX.items():
                c[k] += len(rx.findall(low))
            if h == "A" and lane == "scraped":
                years[d[:4]] += 1


def ratio(days, lex):
    agg = defaultdict(lambda: [0, 0])
    for d, c in days:
        wd = _date.fromisoformat(d).weekday()
        agg[wd][0] += c["n"]
        agg[wd][1] += c[lex]
    if any(agg[w][0] == 0 for w in range(5)):
        return None
    mt = [agg[w][1] / agg[w][0] for w in range(4)]
    base = sum(mt) / 4
    return (agg[4][1] / agg[4][0]) / base if base else None, agg[4][1], agg[4][0]


out = ["[LANE] half A scraped-lane statements by year: " + json.dumps(dict(sorted(years.items())))]
rng = random.Random(20260716)
for h in ("A", "B"):
    for lane in ("propublica", "scraped"):
        days = [(k[2], v) for k, v in day.items() if k[0] == h and k[1] == lane]
        if not days:
            continue
        line = f"[LANE] half {h} lane {lane}: days {len(days):,} stmts {sum(v['n'] for _, v in days):,}"
        for lex in ("core", "pos", "plac"):
            res = ratio(days, lex)
            line += (f" | {lex} " + ("n/a" if res is None or res[0] is None
                                    else f"{res[0]:.4f} ({res[1]:,}/{res[2]:,} Fri)"))
        out.append(line)
        if len(days) > 500:
            boots = []
            for _ in range(2000):
                sample = [days[rng.randrange(len(days))] for _ in range(len(days))]
                res = ratio(sample, "core")
                if res and res[0] is not None:
                    boots.append(res[0])
            boots.sort()
            lo, hi = boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots)) - 1]
            out.append(f"[LANE] half {h} lane {lane}: walk-back day-block bootstrap CI95 "
                       f"[{lo:.4f}, {hi:.4f}] over {len(boots)} resamples; upper<1.5={hi < 1.5}")
(HERE / "out.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
