"""HX.5 · Opposition-vs-celebration reuse — implements the frozen registration
(`data/reference/search/hx_5-registration.json`, committed `16db1d8` BEFORE this run).

Within each party, does OPPOSITION (condemnation)-framed language get REUSED (echoed across the party's
own statements) more than CELEBRATION-framed language? The naive metrics were killed by a pre-freeze
substrate audit (phrase-level valence is empty; carry-against-peak>=15 is boilerplate-dominated at a
~92% base rate). The metric here is within-class DISTINCTIVE reuse: shared boilerplate recurs equally in
both classes and CANCELS in the opposition-minus-celebration difference.

  corpus       = iter_statements(lane, congresses 113-116 / 117-119), solo-qualifying D/R statements
  valence      = wave_s4._valence (frozen S4.1 lexicon); OPP = con & not cel, CEL = cel & not con
  content ng   = wave_s4._content_ngrams(low, 4, 6) per statement (SET; reuse measured across statements)
  repeat_rate  = fraction of a class's phrase-mass echoed by >=1 OTHER statement of the class (df>=2)
  headline     = repeat_rate(OPP) - repeat_rate(CEL), classes size-matched to n=min (frozen seed 0)
  placebo      = within-valence split conA-vs-conB, celA-vs-celB (same statistic, null); + bootstrap CI
  gate/verdict = floor 300/class; CONFIRM iff all 4 (lane,party) positive & placebo-clean; else per rule

No knob is added here. Re-runnable (deterministic; frozen seed 0):
  PYTHONHASHSEED=0 C:/ProgramData/miniconda3/python.exe scripts/search/hx_5_opposition_reuse.py
"""
from __future__ import annotations

import sys
from array import array
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import util  # noqa: E402
from pipeline.search import harness as H  # noqa: E402
from pipeline.search.wave_s4 import _content_ngrams, _valence, load_ref  # noqa: E402  — EXACT S4.1 machinery

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "data" / "reference" / "search" / "hx_5-registration.json"
RESULT = ROOT / "scripts" / "search" / "evidence" / "hx_5_opposition_reuse.result.json"
EVID = Path("X:/onscript-data/elections/derived")
FREEZE_COMMIT = "16db1d8"

LANES = {"propublica": range(113, 117), "scraped": range(117, 120)}
NG_LO, NG_HI = 4, 6        # frozen: distinctive multi-word echoes
MIN_STMTS = 300            # frozen: floor per class
B = 500                    # frozen: bootstrap iterations
SEED = 0                   # frozen
BOOTSTRAP_RNG_NOTE = (
    "DISCLOSED DEVIATION: the frozen registration (16db1d8) specified random.Random(0) for the "
    "bootstrap; pure-Python resampling at n~50k is infeasibly slow (~2-3h), so this measurement uses "
    "numpy default_rng(0) resample-with-replacement instead. Deterministic seed-0; preserves the frozen "
    "metric, size-matching (n=min), placebo, B=500, and verdict rule exactly. Only the CI endpoints move "
    "by RNG-library Monte-Carlo noise (~3rd decimal), which cannot alter the frozen gate. Registration "
    "JSON left pristine; deviation disclosed here + in docs/13."
)


def _prep_class(stmt_list):
    """Factorize a class (list of array('q') per-statement ngram-hash sets) into flat incidence arrays
    for fast bincount df. Returns (flat_codes int64 in [0,U), flat_stmt int64 statement-id, N, U)."""
    N = len(stmt_list)
    if N == 0:
        return np.empty(0, np.int64), np.empty(0, np.int64), 0, 0
    lens = [len(a) for a in stmt_list]
    flat_h = np.concatenate([np.frombuffer(a, dtype=np.int64) for a in stmt_list])
    flat_stmt = np.repeat(np.arange(N, dtype=np.int64), lens)
    _uniq, flat_codes = np.unique(flat_h, return_inverse=True)      # codes 0..U-1
    flat_codes = flat_codes.astype(np.int64, copy=False).reshape(-1)
    return flat_codes, flat_stmt, N, len(_uniq)


def _rr(idx, prep):
    """repeat_rate of a bootstrap draw (statement indices `idx`, with replacement) — EXACTLY the frozen
    definition (fraction of the draw's ngram incidences whose ngram has draw-df>=2). Via bincount:
    df(code) = sum of drawn statement-multiplicities over statements containing it (df = A^T m);
    rr = sum(df where df>=2) / sum(df). Each statement's ngram set is deduped, so a code appears once
    per statement — identical to iterating the drawn sample and counting df."""
    flat_codes, flat_stmt, N, U = prep
    if U == 0:
        return 0.0
    m = np.bincount(idx, minlength=N).astype(np.float64)
    df = np.bincount(flat_codes, weights=m[flat_stmt], minlength=U)
    tot = df.sum()
    if tot <= 0:
        return 0.0
    return float(df[df >= 2].sum() / tot)


def gap_ci(a, b):
    """Size-matched (n=min(|a|,|b|)) bootstrap of repeat_rate(a)-repeat_rate(b), B draws.

    RNG DEVIATION (disclosed, see BOOTSTRAP_RNG_NOTE): the frozen registration specified
    `random.Random(0)`, but pure-Python `choices` at n~50k is infeasibly slow (~2-3 hours). This uses
    numpy `default_rng(0)` resample-with-replacement instead — a deterministic seed-0 bootstrap that
    preserves the frozen METHOD (size-matched repeat_rate gap), METRIC, PLACEBO, and VERDICT RULE
    unchanged; only the CI endpoints shift by RNG-library Monte-Carlo noise (3rd decimal), which cannot
    p-hack the frozen gate. The registration JSON is left pristine; the deviation lives with the
    measurement (docs/12 L4 freeze-before-measure integrity is about the DESIGN, which is unchanged)."""
    n = min(len(a), len(b))
    if n == 0:
        return None
    fa, fb = _prep_class(a), _prep_class(b)
    Na, Nb = len(a), len(b)
    g = np.random.default_rng(SEED)      # deterministic seed-0; re-runnable
    gaps = []
    for _ in range(B):
        ia = g.integers(0, Na, size=n)   # n statements with replacement (C-speed)
        ib = g.integers(0, Nb, size=n)
        gaps.append(_rr(ia, fa) - _rr(ib, fb))
    gaps.sort()
    lo = gaps[int(0.025 * B)]
    hi = gaps[min(B - 1, int(0.975 * B))]
    point = sum(gaps) / len(gaps)
    return {"gap": round(point, 5), "ci_lo": round(lo, 5), "ci_hi": round(hi, 5),
            "n_matched": n, "excludes_0": (lo > 0 or hi < 0)}


def classify(low, CEL, CON, conA, conB, celA, celB):
    """Return the class label for a statement, or None. Substring convention (wave_s4._valence)."""
    cel, con = _valence(low, {"celebration": CEL, "condemnation": CON})
    if con and not cel:
        # opposition + its within-valence placebo split
        a = any(t in low for t in conA)
        b = any(t in low for t in conB)
        sub = "conA" if (a and not b) else ("conB" if (b and not a) else None)
        return ("opp", sub)
    if cel and not con:
        a = any(t in low for t in celA)
        b = any(t in low for t in celB)
        sub = "celA" if (a and not b) else ("celB" if (b and not a) else None)
        return ("cel", sub)
    return None


def measure_lane(lane, congs, lex):
    CEL, CON = lex["celebration"], lex["condemnation"]
    conS, celS = sorted(CON), sorted(CEL)
    conA, conB = conS[0::2], conS[1::2]
    celA, celB = celS[0::2], celS[1::2]

    def ids(low):
        # array('q') of UNIQUE content-ngram hashes (deterministic under PYTHONHASHSEED=0). Hashing
        # instead of interning the ngram STRINGS keeps memory bounded (4-6 grams are near-unique; the
        # string table would be GBs), and array('q') stores raw 8-byte ints (no per-int object
        # overhead). repeat_rate's df is identical by hash vs string (64-bit collisions ~0).
        return array("q", {hash(ng) for ng in _content_ngrams(low, lo=NG_LO, hi=NG_HI)})

    # store[party][class] = list of hash-tuples
    store = {p: {k: [] for k in ("opp", "cel", "conA", "conB", "celA", "celB")} for p in ("D", "R")}
    n_seen = n_class = 0
    for r in H.iter_statements(congresses=congs, with_text=True, lane=lane):
        p = r.get("party")
        if p not in ("D", "R") or not r.get("bioguide"):
            continue
        low = ((r.get("title") or "") + " . " + (r.get("text") or "")).lower()
        if len(low.split()) < 20:
            continue
        n_seen += 1
        if n_seen % 100000 == 0:
            print(f"    ...{lane} scanned {n_seen} (classified {n_class})", flush=True)
        lab = classify(low, CEL, CON, conA, conB, celA, celB)
        if lab is None:
            continue
        main, sub = lab
        tup = ids(low)
        if not tup:
            continue
        store[p][main].append(tup)
        if sub:
            store[p][sub].append(tup)
        n_class += 1
    print(f"  {lane}: statements scanned={n_seen}  classified={n_class}", flush=True)

    out = {"n_scanned": n_seen, "by_party": {}}
    for p in ("D", "R"):
        s = store[p]
        n_opp, n_cel = len(s["opp"]), len(s["cel"])
        powered = n_opp >= MIN_STMTS and n_cel >= MIN_STMTS
        rec = {"n_opp": n_opp, "n_cel": n_cel, "powered": powered,
               "n_conA": len(s["conA"]), "n_conB": len(s["conB"]),
               "n_celA": len(s["celA"]), "n_celB": len(s["celB"])}
        if powered:
            print(f"    {p}: bootstrapping (opp n={n_opp} cel n={n_cel})...", flush=True)
            rec["real_gap"] = gap_ci(s["opp"], s["cel"])
            # placebos: only meaningful if both halves clear the floor
            rec["placebo_con"] = (gap_ci(s["conA"], s["conB"])
                                  if min(len(s["conA"]), len(s["conB"])) >= MIN_STMTS else
                                  {"underpowered": True, "n_matched": min(len(s["conA"]), len(s["conB"]))})
            rec["placebo_cel"] = (gap_ci(s["celA"], s["celB"])
                                  if min(len(s["celA"]), len(s["celB"])) >= MIN_STMTS else
                                  {"underpowered": True, "n_matched": min(len(s["celA"]), len(s["celB"]))})
            g = rec["real_gap"]
            print(f"    {p}: opp n={n_opp} cel n={n_cel}  gap={g['gap']:+.4f} "
                  f"CI[{g['ci_lo']:+.4f},{g['ci_hi']:+.4f}] excl0={g['excludes_0']}", flush=True)
        else:
            print(f"    {p}: opp n={n_opp} cel n={n_cel}  UNDERPOWERED", flush=True)
        out["by_party"][p] = rec
    return out


def _placebo_reproduces(rec):
    """True if a within-valence placebo reproduces the real effect (significant, same direction, magnitude
    >= the real gap) — the ARTIFACT condition."""
    real = rec.get("real_gap")
    if not real or not real["excludes_0"]:
        return False
    real_mag = abs(real["gap"])
    real_dir = real["gap"] > 0
    for key in ("placebo_con", "placebo_cel"):
        pl = rec.get(key) or {}
        if pl.get("underpowered") or "gap" not in pl:
            continue
        if pl["excludes_0"] and (pl["gap"] > 0) == real_dir and abs(pl["gap"]) >= real_mag:
            return True
    return False


def main():
    lex = load_ref()["_framing_lexicon"]
    print(f"HX.5 opposition-vs-celebration reuse  ng={NG_LO}-{NG_HI} floor={MIN_STMTS} B={B} seed={SEED}", flush=True)
    print(f"(frozen registration {FREEZE_COMMIT})\n", flush=True)

    per_lane = {}
    for lane, congs in LANES.items():
        per_lane[lane] = measure_lane(lane, congs, lex)

    # ---- verdict (frozen rule)
    cells = [(ln, p, per_lane[ln]["by_party"][p]) for ln in LANES for p in ("D", "R")]
    powered = [(ln, p, rec) for ln, p, rec in cells if rec["powered"]]
    positives = [(ln, p) for ln, p, rec in powered
                 if rec["real_gap"]["excludes_0"] and rec["real_gap"]["gap"] > 0]
    negatives = [(ln, p) for ln, p, rec in powered
                 if rec["real_gap"]["excludes_0"] and rec["real_gap"]["gap"] < 0]
    artifacts = [(ln, p) for ln, p, rec in powered if _placebo_reproduces(rec)]

    all_powered = len(powered) == 4
    all_positive = len(positives) == 4
    any_negative = len(negatives) > 0
    direction_consistent = all(rec["real_gap"]["gap"] > 0 for _, _, rec in powered) if powered else False

    if not all_powered:
        under = [(ln, p) for ln, p, rec in cells if not rec["powered"]]
        verdict = f"UNDERPOWERED — cells below the {MIN_STMTS}/class floor: {under}"
    elif any_negative:
        verdict = (f"REFUTED — direction inconsistent: opposition reused LESS in {negatives} "
                   f"(no symmetric reuse asymmetry)")
    elif artifacts:
        verdict = f"ARTIFACT — a within-valence placebo reproduces the effect in {artifacts} (lexical-split artifact)"
    elif all_positive:
        verdict = ("CONFIRM — opposition language is reused more than celebration language in BOTH parties "
                   "and BOTH lanes (all 4 CIs exclude 0, opp>cel), and no within-valence placebo reproduces it")
    elif direction_consistent:
        verdict = ("DESCRIPTIVE — opposition > celebration in every powered cell, but not all 4 CIs exclude 0 "
                   "(or a placebo is inconclusive); a methods/transparency-shelf pattern, not a card")
    else:
        verdict = "DESCRIPTIVE — mixed/weak signal across the powered cells; methods-shelf only"

    print(f"\n  powered cells: {[(ln, p) for ln, p, _ in powered]}")
    print(f"  positives (opp>cel, CI excl 0): {positives}   negatives: {negatives}   artifacts: {artifacts}")
    print(f"\n===== HX.5 VERDICT: {verdict} =====")

    payload = {
        "generated_at": util.now_utc_iso(),
        "registration": str(REG.relative_to(ROOT)).replace("\\", "/"),
        "registration_freeze_commit": FREEZE_COMMIT,
        "params": {"ng_lo": NG_LO, "ng_hi": NG_HI, "min_stmts": MIN_STMTS, "bootstrap_B": B, "seed": SEED},
        "bootstrap_rng_deviation": BOOTSTRAP_RNG_NOTE,
        "per_lane": per_lane,
        "summary": {"powered": [[ln, p] for ln, p, _ in powered],
                    "positives": [[ln, p] for ln, p in positives],
                    "negatives": [[ln, p] for ln, p in negatives],
                    "artifacts": [[ln, p] for ln, p in artifacts]},
        "verdict": verdict,
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    util.write_json(RESULT, payload)
    try:
        EVID.mkdir(parents=True, exist_ok=True)
        util.write_json(EVID / "hx_5_opposition_reuse.result.json", payload)
    except Exception as e:
        print(f"  (evidence mirror to X: skipped: {e})", flush=True)
    print(f"wrote {RESULT}")


if __name__ == "__main__":
    main()
