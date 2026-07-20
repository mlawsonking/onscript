"""S3.7 Step 2 — The Safe-Seat Vessel Test, run EXACTLY as registered (docs/13 §S3.7).

The registration is FROZEN. This script does not add a knob, a floor, or a rescope; it executes the
pre-registered design and appends whichever verdict falls out.

  unit                = member (bioguide)
  MoV                 = (winner - runner-up) / total votes per member per cycle  (Step 1 table:
                        data/reference/search/mov-by-member.json)
  script participation= the concordance on-script index (build.build_concordance,
                        PEAK_FLOOR=15, MIN_STATEMENTS=10)
  test                = member-level Spearman rho(MoV, concordance) WITHIN chamber (never pooled across
                        chambers — the #143 chamber trap), within-lane halves (docs/17)
  CONFIRM  iff |rho| >= 0.20  and  p < 0.05  and  same sign in both halves (either direction)
  REFUTE   iff |rho| <  0.20  in a well-powered cell
  power floor         = a chamber.lane.half cell reports a verdict only with >= 100 members carrying
                        BOTH a MoV and a concordance score
  artifact            = aggregate MoV-quintile mean-concordance table; NO member-level leaderboard (R2/#143)

LANES / HALVES (docs/17 §2, frozen):
  propublica  A = congresses 113-114 (2013-2016),  B = 115-116 (2017-2020)
  scraped     A = congress   117     (2021-2022),  B = 118-119 (2023-2026)

HOW the concordance is sourced within a lane-half WITHOUT touching production (launch-eve rule: read-
only imports; no writes to config.DERIVED / config.STATE / derived/days):
  * kept set: stream the committed per-lane phrase_index cache (peak == peak_units, verified) and keep
    ngrams with peak >= 15 in the half's congresses -> a MINIMAL ledger {ng: {peak_units}}; that is the
    ONLY thing build.build_concordance reads a ledger for.
  * statements: alexandria.load_congress_records(c, lane) -> normalize.normalize_records (no roster, as
    the shards were built) yielded LAZILY per-congress so only one era is resident at a time.
  * build.build_concordance(statements, kept_ledger, out_dir=None, ...) -> per-member index. out_dir
    None => it returns without writing. Faithful to how deterministic.run builds the daily concordance.

MoV reduction to one value per member per window (disclosed; NOT a registered knob — Spearman is rank-
based and safe-seat margins are stable across a member's own cycles, so the choice is rank-inert):
  MoV(member, window) = mean of the member's per-cycle MoV over the elections whose SEATED TERM overlaps
  the window's date span, restricted to the member's chamber in that window (House 2-yr / Senate 6-yr).

Re-runnable:  PYTHONHASHSEED=0 C:/ProgramData/miniconda3/python.exe scripts/search/s3_7_safe_seat.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import alexandria, build, config, normalize, roster, util  # noqa: E402
from pipeline.search import harness as H  # noqa: E402

MOV = Path(__file__).resolve().parents[2] / "data" / "reference" / "search" / "mov-by-member.json"
EVID = Path("X:/onscript-data/elections/derived")
RESULT = Path(__file__).resolve().parent / "evidence" / "s3_7_safe_seat.result.json"

PEAK_FLOOR = 15          # registration (== CONCORDANCE_PEAK_FLOOR)
MIN_STATEMENTS = 10      # registration (== CONCORDANCE_MIN_STATEMENTS)
RHO_GATE = 0.20          # registration
P_GATE = 0.05            # registration
POWER_FLOOR = 100        # registration: >=100 members with BOTH scores per chamber.lane.half cell

LANES = {
    "propublica": {"A": [113, 114], "B": [115, 116]},
    "scraped":    {"A": [117],      "B": [118, 119]},
}


# ------------------------------------------------------------------ Spearman (no scipy in this env)
def _rankdata(a):
    a = np.asarray(a, dtype=float)
    n = len(a)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and a[order[j + 1]] == a[order[i]]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0  # average rank for ties, 1-based
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
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def spearman(x, y):
    """rho, two-sided p (t-distribution via incomplete beta, the classical Spearman test), n."""
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), n
    rho = _pearson(_rankdata(x), _rankdata(y))
    if not math.isfinite(rho):
        return rho, float("nan"), n
    if abs(rho) >= 1.0:
        return rho, 0.0, n
    t = rho * math.sqrt((n - 2) / (1.0 - rho * rho))
    df = n - 2
    p = _betai(df / 2.0, 0.5, df / (df + t * t))
    return rho, p, n


# ------------------------------------------------------------------ concordance per lane-half
def kept_ledger(lane: str, congresses: list[int]) -> dict:
    """Minimal ledger {ng: {peak_units}} for the half: phrase_index rows with peak >= PEAK_FLOOR in the
    half's congresses (peak == peak_units, verified in pipeline/phrases.py). build.build_concordance
    reads a ledger ONLY to derive `kept`, so this reproduces its kept set exactly."""
    cset = set(congresses)
    led: dict[str, dict] = {}
    for row in H.iter_phrase_index(lane=lane):
        if row.get("congress") in cset and (row.get("peak", 0) or 0) >= PEAK_FLOOR:
            ng = row["ng"]
            pu = row["peak"]
            cur = led.get(ng)
            if cur is None or pu > cur["peak_units"]:
                led[ng] = {"peak_units": pu}
    return led


def statements_iter(lane: str, congresses: list[int]):
    """Lazily yield normalized statements for the half, one congress resident at a time (memory-bound).
    No roster passed to normalize — matches how the per-lane shards were built (run_shard)."""
    for c in congresses:
        recs = alexandria.load_congress_records(c, lane=lane)
        stmts = normalize.normalize_records(recs, run_id=f"s37-{lane}-{c}")
        print(f"    [{lane} c{c}] {len(recs)} recs -> {len(stmts)} statements", flush=True)
        for s in stmts:
            yield s


def concordance_for(lane: str, congresses: list[int], rmap: dict) -> dict:
    led = kept_ledger(lane, congresses)
    print(f"  kept ledger ({lane} {congresses}): {len(led)} phrases peak>={PEAK_FLOOR}", flush=True)
    conc = build.build_concordance(statements_iter(lane, congresses), led, out_dir=None,
                                   roster_map=rmap, min_statements=MIN_STATEMENTS, peak_floor=PEAK_FLOOR)
    print(f"  concordance: {conc['counts']}", flush=True)
    return conc


# ------------------------------------------------------------------ MoV reduction per member/window
def window_years(congresses: list[int]) -> tuple[int, int]:
    lo = int(alexandria.congress_range(min(congresses))[0][:4])
    hi = int(alexandria.congress_range(max(congresses))[1][:4])  # exclusive
    return lo, hi


def term_years(cycle: int, chamber: str) -> tuple[int, int]:
    start = cycle + 1
    return start, start + (2 if chamber == "house" else 6)  # [start, end) exclusive


def reduce_mov(rows: list[dict], chamber: str, wlo: int, whi: int):
    vals = []
    for r in rows:
        if r["chamber"] != chamber:
            continue
        ts, te = term_years(r["cycle"], chamber)
        if ts < whi and te > wlo:  # the seat's term overlaps the concordance window
            vals.append(r["mov"])
    return (sum(vals) / len(vals)) if vals else None


# ------------------------------------------------------------------ verdict + artifact
def quintiles(pairs):
    """pairs = [(mov, index)]; return 5 MoV-quantile bins with mean index (the registered artifact)."""
    if len(pairs) < 5:
        return []
    order = sorted(pairs, key=lambda p: p[0])
    n = len(order)
    out = []
    for q in range(5):
        lo = q * n // 5
        hi = (q + 1) * n // 5
        seg = order[lo:hi]
        movs = [p[0] for p in seg]
        idx = [p[1] for p in seg]
        out.append({"quintile": q + 1, "n": len(seg),
                    "mov_lo": round(min(movs), 4), "mov_hi": round(max(movs), 4),
                    "mean_mov": round(sum(movs) / len(seg), 4),
                    "mean_concordance": round(sum(idx) / len(seg), 4)})
    return out


def cell_verdict(rho, p, n):
    if n < POWER_FLOOR:
        return "underpowered"
    if abs(rho) >= RHO_GATE and p < P_GATE:
        return "signal"          # meets |rho| & p; sign-agreement checked at the lane level
    if abs(rho) < RHO_GATE:
        return "null"            # well-powered REFUTE evidence
    return "weak"                # powered, |rho|>=.20 but p>=.05 (rare at n>=100)


def main():
    mov_data = json.load(open(MOV, encoding="utf-8"))
    mov_by_bio: dict[str, list] = defaultdict(list)
    for r in mov_data["rows"]:
        mov_by_bio[r["bioguide"]].append(r)
    print(f"MoV table: {len(mov_data['rows'])} rows, {len(mov_by_bio)} members "
          f"(join coverage {mov_data['audit']['totals']['match_pct']}%)\n", flush=True)

    rmap = roster.load()
    cells: dict = {}   # (chamber, lane, half) -> result

    for lane, halves in LANES.items():
        for half, congs in halves.items():
            print(f"===== {lane} half {half} (congresses {congs}) =====", flush=True)
            wlo, whi = window_years(congs)
            conc = concordance_for(lane, congs, rmap)
            by_chamber: dict[str, list] = defaultdict(list)   # chamber -> [(mov, index, bio)]
            missing_mov = 0
            for m in conc["members"]:
                bio = m["bioguide"]
                chamber = (m.get("chamber") or "").strip().lower()
                if chamber not in ("house", "senate"):
                    continue
                mv = reduce_mov(mov_by_bio.get(bio, []), chamber, wlo, whi)
                if mv is None:
                    missing_mov += 1
                    continue
                by_chamber[chamber].append((mv, m["index"], bio))
            for chamber, pairs in by_chamber.items():
                movs = [p[0] for p in pairs]
                idx = [p[1] for p in pairs]
                rho, p, n = spearman(movs, idx)
                v = cell_verdict(rho, p, n)
                cells[f"{chamber}.{lane}.{half}"] = {
                    "chamber": chamber, "lane": lane, "half": half,
                    "window_years": [wlo, whi], "congresses": congs,
                    "n": n, "rho": None if not math.isfinite(rho) else round(rho, 4),
                    "p": None if not math.isfinite(p) else p,
                    "powered": n >= POWER_FLOOR, "cell_verdict": v,
                    "quintiles": quintiles([(a, b) for a, b, _ in pairs]),
                }
                print(f"  {chamber:6s}: n={n:4d} rho={rho:+.4f} p={p:.4g} powered={n>=POWER_FLOOR} -> {v}",
                      flush=True)
            print(f"  (members with concordance but no MoV: {missing_mov})\n", flush=True)

    # -------- lane-level adjudication (CONFIRM needs BOTH halves powered, |rho|>=.20, p<.05, same sign)
    adjud: dict = {}
    for chamber in ("house", "senate"):
        for lane in LANES:
            a = cells.get(f"{chamber}.{lane}.A")
            b = cells.get(f"{chamber}.{lane}.B")
            if not a or not b:
                continue
            key = f"{chamber}.{lane}"
            if not (a["powered"] and b["powered"]):
                adjud[key] = "UNDERPOWERED (a cell below the 100-member floor)"
                continue
            ra, rb = a["rho"], b["rho"]
            if abs(ra) >= RHO_GATE and abs(rb) >= RHO_GATE and a["p"] < P_GATE and b["p"] < P_GATE \
                    and (ra > 0) == (rb > 0):
                adjud[key] = f"CONFIRM (rho {ra:+.3f}/{rb:+.3f}, same sign, both p<0.05)"
            elif abs(ra) < RHO_GATE or abs(rb) < RHO_GATE:
                adjud[key] = f"REFUTE (a well-powered half has |rho|<0.20: {ra:+.3f}/{rb:+.3f})"
            else:
                adjud[key] = f"MIXED (powered, |rho|>=0.20, but signs differ or p>=0.05: {ra:+.3f}/{rb:+.3f})"

    powered_cells = [c for c in cells.values() if c["powered"]]
    any_confirm = any(v.startswith("CONFIRM") for v in adjud.values())
    if any_confirm:
        overall = "CONFIRM"
    elif powered_cells and all(cell_verdict(c["rho"] or 0, c["p"] or 1, c["n"]) == "null"
                               for c in powered_cells):
        overall = "REFUTE"
    elif not powered_cells:
        overall = "UNDERPOWERED"
    else:
        overall = "REFUTE (well-powered cells null; any remaining cells underpowered)" \
            if any(c["cell_verdict"] == "null" for c in powered_cells) else "UNDERPOWERED/MIXED"

    print("===== LANE-LEVEL ADJUDICATION =====")
    for k, v in adjud.items():
        print(f"  {k:20s} {v}")
    print(f"\n===== S3.7 OVERALL VERDICT: {overall} =====")

    RESULT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": util.now_utc_iso(),
        "registration": {"peak_floor": PEAK_FLOOR, "min_statements": MIN_STATEMENTS,
                         "rho_gate": RHO_GATE, "p_gate": P_GATE, "power_floor": POWER_FLOOR},
        "mov_join_coverage_pct": mov_data["audit"]["totals"]["match_pct"],
        "cells": cells, "adjudication": adjud, "overall": overall,
    }
    util.write_json(RESULT, payload)
    util.write_json(EVID / "s3_7_safe_seat.result.json", payload)
    print(f"\nwrote {RESULT}\nwrote {EVID / 's3_7_safe_seat.result.json'}")


if __name__ == "__main__":
    main()
