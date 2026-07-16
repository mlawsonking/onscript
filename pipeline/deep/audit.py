"""The coverage audit (docs/15 §D0.1 / docs/14 §coverage-audit) — the gate every deep lane passes
before ANY finding rides on it. Deterministic, stdlib-only, JSON-serializable + reproducible.

Default posture: fill only where symmetry is PROVEN; otherwise honest gap. The seven gates:
  1. both-party floor      — >= MIN_MEMBERS distinct attributed members per party in the window.
  2. symmetry ratio        — min(D,R)/max(D,R) >= MIN_RATIO (no worse than 3:1) on distinct members.
  3. attribution complete  — >= MIN_ATTR of units carry a machine-verified member+party.
  4. integrity rate        — stub/boilerplate rejection rate, reported (informational floor only).
  5. provenance == 100%    — every unit has url + unit_date + stable_id, else the window fails.
  6. genre isolation       — the audited set is a SINGLE lane (raises on a mixed set).
  7. temporal coverage     — a cross-era claim requires BOTH eras to pass gates 1-2 (A1-style).
"""
from __future__ import annotations

from collections import defaultdict

from . import lanes

MIN_MEMBERS = 5        # gate 1: distinct attributed members per party
MIN_RATIO = 1 / 3      # gate 2: min/max member symmetry — no worse than 3:1 (exactly 1/3, not 0.33)
MIN_ATTR = 0.40        # gate 3: fraction of units with a resolved member+party


def gate_result(nD_mem: int, nR_mem: int, nD_stmt: int, nR_stmt: int,
                attribution_rate: float, provenance_complete: bool,
                integrity_rate: float | None = None) -> dict:
    """Pure gate logic over pre-aggregated coverage numbers. Symmetry is computed on distinct MEMBERS
    (the selection-bias-relevant quantity), never on raw statement volume."""
    lo, hi = min(nD_mem, nR_mem), max(nD_mem, nR_mem)
    ratio = (lo / hi) if hi else 0.0
    floor = nD_mem >= MIN_MEMBERS and nR_mem >= MIN_MEMBERS
    gates = {
        "both_party_floor": floor,
        # symmetry is meaningless without the both-party floor, so it depends on it (a 6/0 split must
        # fail BOTH, never pass symmetry by vacuous ratio arithmetic).
        "symmetry_ratio": floor and ratio >= MIN_RATIO,
        "attribution_completeness": attribution_rate >= MIN_ATTR,
        "provenance_complete": bool(provenance_complete),
    }
    return {
        "members": {"D": nD_mem, "R": nR_mem},
        "statements": {"D": nD_stmt, "R": nR_stmt},
        "symmetry_ratio": round(ratio, 4),
        "attribution_rate": round(attribution_rate, 4),
        "integrity_rate": (round(integrity_rate, 4) if integrity_rate is not None else None),
        "gates": gates,
        "PASS": all(gates.values()),
    }


def audit_units(units: list[dict], window: str, *, n_raw: int | None = None,
                expect_lane: str | None = None) -> dict:
    """Audit a set of lane-tagged units for one window. Enforces genre isolation (gate 6) FIRST, then
    aggregates distinct members/statements/attribution/provenance and applies the gates. `n_raw` (the
    pre-filter unit count) lets gate 4 report the integrity/rejection rate. `expect_lane` guards against
    a wholly-untagged deep set silently auditing as 'press'. Reproducible: a function of the input only."""
    lane = lanes.lane_of(units)                       # gate 6 — raises GenreIsolationError on a mixed set
    if lane is not None and lane not in lanes.LANES:  # a typo'd/unregistered lane must never report PASS
        raise ValueError(f"unregistered lane {lane!r} — not in lanes.LANES")
    if expect_lane is not None and lane != expect_lane:
        raise lanes.GenreIsolationError(
            f"expected lane {expect_lane!r}, resolved {lane!r} (untagged rows default to 'press')")
    dmem, rmem = set(), set()
    dst = rst = attributed = 0
    provenance_complete = True
    for u in units:
        p = u.get("party")
        mid = u.get("member_id") or u.get("bioguide")
        if mid and p in ("D", "R"):
            attributed += 1
        if p == "D":
            dst += 1
            if mid:
                dmem.add(mid)
        elif p == "R":
            rst += 1
            if mid:
                rmem.add(mid)
        if not (u.get("url") and u.get("unit_date") and u.get("stable_id")):
            provenance_complete = False
    attr_rate = (attributed / len(units)) if units else 0.0
    integrity_rate = (1 - len(units) / n_raw) if (n_raw and n_raw > 0) else None
    res = gate_result(len(dmem), len(rmem), dst, rst, attr_rate, provenance_complete, integrity_rate)
    return {"lane": lane, "window": window, **res}


def audit_coverage(cov_by_window: dict, lane: str) -> dict:
    """Audit a lane from pre-aggregated per-window coverage (the form the discipline/coverage shards
    give): {window: {'D': {'members': set|int, 'statements': int}, 'R': {...},
    'attribution_rate'?, 'provenance_complete'?, 'integrity_rate'?}}.

    CONTRACT (the summary form cannot re-derive what it isn't given, so the caller must be honest):
      * `members` MUST be a distinct-member SET or a pre-deduped distinct COUNT — this path cannot
        dedupe, so a duplicate-inflated int would sneak a pass. Prefer passing a set.
      * The caller MUST have aggregated a SINGLE source — genre isolation cannot be re-checked from
        pre-aggregated counts (all per-row `source` info is already gone). `lane` is validated against
        the registry to catch typos, but a genuinely mixed aggregate is the caller's sin to avoid.
      * Provenance + attribution are FAIL-CLOSED: omit them and the window FAILS. You must
        affirmatively assert `provenance_complete=True` / `attribution_rate` (adversarial-review fix).
    """
    if lane not in lanes.LANES:
        raise ValueError(f"unregistered lane {lane!r} — not in lanes.LANES")

    def n(x):
        return len(x) if hasattr(x, "__len__") else int(x)
    out = {"lane": lane, "windows": {}}
    for w in sorted(cov_by_window):
        c = cov_by_window[w]
        d, r = c.get("D", {}), c.get("R", {})
        res = gate_result(
            n(d.get("members", 0)), n(r.get("members", 0)),
            int(d.get("statements", 0)), int(r.get("statements", 0)),
            float(c.get("attribution_rate", 0.0)), bool(c.get("provenance_complete", False)),
            c.get("integrity_rate"))
        out["windows"][w] = res
    out["windows_passing"] = sorted(w for w, r in out["windows"].items() if r["PASS"])
    return out


def audit_cross_era(result_a: dict, result_b: dict) -> dict:
    """Gate 7 (temporal coverage, A1-style): a cross-era claim is ALLOWED only if BOTH windows clear
    the both-party floor + symmetry gates. Prevents a "trend" resting on an era that isn't symmetric.

    GENRE ISOLATION (Law 1) is enforced here too — the exact "genre confound in a trend costume" this
    program fears: the two eras MUST be the SAME lane, or it raises. (Each result already passed
    lane_of individually, so without this check two lane-clean halves of different genres would trend
    freely — adversarial-review BLOCKER fix.)"""
    la, lb = result_a.get("lane"), result_b.get("lane")
    if not (la and lb) or la != lb:
        raise lanes.GenreIsolationError(
            f"cross-era claim must be WITHIN ONE lane (docs/15 Law 1); got {la!r} vs {lb!r}")

    def ok(res):
        g = res.get("gates", {})
        return bool(g.get("both_party_floor") and g.get("symmetry_ratio"))
    a_ok, b_ok = ok(result_a), ok(result_b)
    allowed = a_ok and b_ok
    reason = "both eras symmetric" if allowed else (
        f"blocked: {'era A' if not a_ok else ''}{' and ' if not a_ok and not b_ok else ''}"
        f"{'era B' if not b_ok else ''} fails the both-party/symmetry floor")
    return {"allowed": allowed, "era_a_ok": a_ok, "era_b_ok": b_ok, "reason": reason}
