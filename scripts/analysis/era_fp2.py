"""Era Fingerprints: the log-odds-distinctive phrases per Congress x party, with a procedural-token
stoplist so the front-page artifact isn't topped by boilerplate ('of the united states', 'a member
of the senate'). Writes data/derived/era_fingerprints.json — the committed artifact the Archive
(Build-Program 1.1) renders (Art. VI: reproducible from this committed module).

  python scripts/analysis/era_fp2.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline import config, util  # noqa: E402

LEDGER = config.STATE / "ledger.json"
OUT = config.DERIVED / "era_fingerprints.json"
CONG = {113: "2013-14", 114: "2015-16", 115: "2017-18", 116: "2019-20",
        117: "2021-22", 118: "2023-24", 119: "2025-26"}
# procedural / function tokens: drop any phrase made ENTIRELY of these (keeps content phrases)
STOP = set(
    "of the a an u s united states member members senate house representatives congress "
    "to and in for on that this with as at by is are was were be been being will would has have had "
    "i we our my me his her their they it he she you your from or not but which who what when act".split()
)


def is_proc(w: str) -> bool:
    """True if the phrase is entirely procedural/function tokens (not a distinctive talking point)."""
    return all(t in STOP for t in w.split())


def collapse(rows, k: int = 10):
    """Keep the top-k non-nested phrases (a longer phrase already kept subsumes its sub-phrases)."""
    kept = []
    for sc, c, ng in rows:
        if not any(f" {ng} " in f" {k2} " for _, _, k2 in kept):
            kept.append((sc, c, ng))
        if len(kept) >= k:
            break
    return kept


def build(ledger: dict) -> dict:
    """Per (Congress, party): log-odds-distinctive phrases vs all other eras of the same party."""
    cnt = defaultdict(lambda: defaultdict(int))
    tot = defaultdict(int)
    for ng, e in ledger.items():
        pk = max((max(d.get("D", 0), d.get("R", 0)) for d in e["daily"].values()), default=0)
        if pk < 15:
            continue
        for day, d in e["daily"].items():
            if day < "2013-01-01":
                continue
            cg = util.congress_for_date(day)
            for P in ("D", "R"):
                c = d.get(P, 0)
                if c:
                    cnt[(cg, P)][ng] += c
                    tot[(cg, P)] += c
    out = {}
    for cg in range(113, 120):
        for P in ("D", "R"):
            here = cnt.get((cg, P), {})
            n_here = tot.get((cg, P), 0)
            if n_here < 1000:
                continue
            rest = defaultdict(int)
            n_rest = 0
            for (c2, p2), d2 in cnt.items():
                if p2 == P and c2 != cg:
                    n_rest += tot[(c2, p2)]
                    for w, v in d2.items():
                        rest[w] += v
            rows = []
            for w, y in here.items():
                if y < 20 or is_proc(w):
                    continue
                score = math.log((y + 0.5) / (n_here + 0.5)) - math.log((rest.get(w, 0) + 0.5) / (n_rest + 0.5))
                rows.append((score, y, w))
            rows.sort(reverse=True)
            top = [{"phrase": w, "uses": c} for _, c, w in collapse(rows)]
            out[f"{cg}-{P}"] = {"congress": cg, "years": CONG[cg], "party": P, "top": top}
    return out


def main() -> int:
    t0 = time.time()
    print("[EF2] loading merged ledger …", flush=True)
    with LEDGER.open(encoding="utf-8") as f:
        ledger = json.load(f)
    print(f"[EF2] {len(ledger):,} phrases in {time.time()-t0:.0f}s", flush=True)
    out = build(ledger)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[EF2] wrote {OUT} ({len(out)} era-party fingerprints) in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
