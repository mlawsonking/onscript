"""HX.8 · Prolific-office concentration + intensity-vs-reach (docs/05 §3, the registration-wave bank).

A cheap self-audit descriptive, #146/R3-shaped: denominators live in the VIEW, chambers are NEVER
pooled (the #143 trap), lanes are NEVER pooled (docs/12 L1). Two questions, both descriptive — there
is no CONFIRM/REFUTE gate, so there is nothing to p-hack; the distribution IS the finding:

  (1) CONCENTRATION — how unequally is press-release VOLUME distributed across offices? Reported as the
      top-decile share (what fraction of a cell's statements come from its most prolific 10% of offices)
      and the Gini coefficient of the office-volume distribution.
  (2) INTENSITY-vs-REACH — does a prolific office also RIDE more coordinated phrases (a coordination
      hub), or does volume just buy self-repetition? intensity = the office's statement count; reach =
      the number of distinct synchronized phrases (peak>=15, member_index) the office participated in.
      Spearman rho(intensity, reach) WITHIN each chamber x party x lane cell, plus the intensity-quintile
      mean-reach artifact.

Floors PRE-DECLARED (L4, before measuring): MIN_STMTS = 10 (an office enters the rho computation only
with >=10 statements — a tiny office's rank is noise); MIN_OFFICES = 30 (a cell reports rho only with
>=30 qualifying offices). These are disclosed knobs, not tuned to a result (a descriptive has no result
to tune toward).

Substrate (all local, pre-built caches — no corpus normalize, no network):
  data/derived/search/stmt_meta.{lane}.jsonl   (per-statement metadata: bioguide, party, chamber)
  data/derived/search/member_index.{lane}.jsonl (per peak>=15 phrase: the members who used it)

Re-runnable:  PYTHONHASHSEED=0 C:/ProgramData/miniconda3/python.exe scripts/search/hx_8_office_concentration.py
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import util  # noqa: E402
from pipeline.search import harness as H  # noqa: E402

RESULT = Path(__file__).resolve().parent / "evidence" / "hx_8_office_concentration.result.json"
EVID = Path("X:/onscript-data/elections/derived")
LANES = ("propublica", "scraped")
MIN_STMTS = 10       # floor: an office enters the rho computation only with >=10 statements
MIN_OFFICES = 30     # floor: a cell reports rho only with >=30 qualifying offices


# ---- Spearman (no scipy; same implementation as scripts/search/s3_7_safe_seat.py) ----
def _rankdata(a):
    a = np.asarray(a, float); n = len(a)
    order = np.argsort(a, kind="mergesort"); ranks = np.empty(n, float); i = 0
    while i < n:
        j = i
        while j + 1 < n and a[order[j + 1]] == a[order[i]]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def _pearson(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    xm = x - x.mean(); ym = y - y.mean()
    d = math.sqrt(float((xm * xm).sum()) * float((ym * ym).sum()))
    return float((xm * ym).sum() / d) if d > 0 else float("nan")


def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 300, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0; d = 1.0 - qab * x / qap
    if abs(d) < FPMIN: d = FPMIN
    d = 1.0 / d; h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d; c = 1.0 + aa / c
        if abs(d) < FPMIN: d = FPMIN
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d; c = 1.0 + aa / c
        if abs(d) < FPMIN: d = FPMIN
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d; de = d * c; h *= de
        if abs(de - 1.0) < EPS: break
    return h


def _betai(a, b, x):
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lb + a * math.log(x) + b * math.log(1.0 - x))
    return bt * _betacf(a, b, x) / a if x < (a + 1.0) / (a + b + 2.0) else 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def spearman(x, y):
    n = len(x)
    if n < 3: return float("nan"), float("nan"), n
    rho = _pearson(_rankdata(x), _rankdata(y))
    if not math.isfinite(rho): return rho, float("nan"), n
    if abs(rho) >= 1.0: return rho, 0.0, n
    t = rho * math.sqrt((n - 2) / (1.0 - rho * rho)); df = n - 2
    return rho, _betai(df / 2.0, 0.5, df / (df + t * t)), n


def gini(vals) -> float:
    xs = sorted(v for v in vals if v >= 0)
    n = len(xs); s = sum(xs)
    if n == 0 or s == 0: return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return round((2 * cum) / (n * s) - (n + 1) / n, 4)


def top_decile_share(vals) -> float:
    xs = sorted(vals, reverse=True)
    n = len(xs); s = sum(xs)
    if n == 0 or s == 0: return 0.0
    k = max(1, n // 10)
    return round(sum(xs[:k]) / s, 4)


def quintile_reach(pairs):
    """pairs=[(intensity, reach)]; 5 intensity-quantile bins with mean reach (the artifact)."""
    if len(pairs) < 5: return []
    order = sorted(pairs, key=lambda p: p[0]); n = len(order); out = []
    for q in range(5):
        seg = order[q * n // 5:(q + 1) * n // 5]
        out.append({"quintile": q + 1, "n": len(seg),
                    "mean_intensity": round(sum(p[0] for p in seg) / len(seg), 1),
                    "mean_reach": round(sum(p[1] for p in seg) / len(seg), 2)})
    return out


def main():
    print(f"HX.8 office concentration + intensity-vs-reach  (MIN_STMTS={MIN_STMTS}, MIN_OFFICES={MIN_OFFICES})\n",
          flush=True)
    cells = {}
    for lane in LANES:
        # intensity + modal chamber/party per office (stmt_meta), reach per office (member_index)
        intensity = Counter()
        chamber = defaultdict(Counter)
        party = defaultdict(Counter)
        for r in H.iter_stmt_meta(lane=lane):
            b = r.get("bioguide")
            if not b:
                continue
            intensity[b] += 1
            if r.get("chamber"): chamber[b][r["chamber"]] += 1
            if r.get("party") in ("D", "R"): party[b][r["party"]] += 1
        reach = defaultdict(set)
        for row in H.iter_member_index(lane=lane):
            for b in row.get("members", []):
                if not str(b).startswith(("joint:", "njoint:")):
                    reach[b].add(row["ng"])
        # bucket offices into chamber x party cells
        by_cell = defaultdict(list)   # (chamber, party) -> [(bio, intensity, reach)]
        for b, cnt in intensity.items():
            ch = chamber[b].most_common(1)[0][0] if chamber[b] else None
            pa = party[b].most_common(1)[0][0] if party[b] else None
            if ch in ("House", "Senate") and pa in ("D", "R"):
                by_cell[(ch, pa)].append((b, cnt, len(reach.get(b, ()))))
        for (ch, pa), offs in sorted(by_cell.items()):
            vols = [o[1] for o in offs]
            qual = [(o[1], o[2]) for o in offs if o[1] >= MIN_STMTS]
            rho = p = None; nq = len(qual)
            if nq >= MIN_OFFICES:
                rr, pp, _ = spearman([q[0] for q in qual], [q[1] for q in qual])
                rho = None if not math.isfinite(rr) else round(rr, 4)
                p = None if not math.isfinite(pp) else pp
            key = f"{ch}.{pa}.{lane}"
            cells[key] = {
                "chamber": ch, "party": pa, "lane": lane,
                "offices": len(offs), "statements": sum(vols),
                "top_decile_share": top_decile_share(vols), "gini": gini(vols),
                "qualifying_offices": nq, "rho_intensity_reach": rho, "p": p,
                "reported": nq >= MIN_OFFICES,
                "quintiles": quintile_reach(qual) if nq >= MIN_OFFICES else [],
            }
            print(f"  {key:22s} offices={len(offs):4d} stmts={sum(vols):7d} "
                  f"top10%share={cells[key]['top_decile_share']} gini={cells[key]['gini']} | "
                  f"intensity~reach rho={rho} (n={nq}, p={p})", flush=True)

    payload = {"generated_at": util.now_utc_iso(),
               "floors": {"MIN_STMTS": MIN_STMTS, "MIN_OFFICES": MIN_OFFICES},
               "note": "Descriptive self-audit (HX.8). Chambers never pooled (#143), lanes never pooled "
                       "(L1). reach = distinct peak>=15 phrases the office participated in; intensity = "
                       "its statement count. rho is descriptive, no CONFIRM/REFUTE gate.",
               "cells": cells}
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    util.write_json(RESULT, payload)
    EVID.mkdir(parents=True, exist_ok=True)
    util.write_json(EVID / "hx_8_office_concentration.result.json", payload)
    print(f"\nwrote {RESULT}\nwrote {EVID / 'hx_8_office_concentration.result.json'}")


if __name__ == "__main__":
    main()
