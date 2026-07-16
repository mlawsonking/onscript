"""The Owner's Brief (v2 feature 1.8; spec: 07-OPERATIONS §2 + §3) — a Monday ntfy digest carrying
the five health numbers, the streak, the dark shelf, and any decision the machine wants from its
owner. "The system reports to its owner; the owner never has to remember to ask."

THE LOAD-BEARING RULE — **an unmeasured number reads `unknown`, and `unknown` is never green.**
The brief's purpose is that a tired Monday costs zero interpretation (07-OPS §2: the thresholds
"exist so you never have to *interpret* on a tired Monday"). A brief that guesses is strictly worse
than no brief: it teaches the owner to trust a number nobody measured.

That rule has to hold at FIELD level, not just file level — the trap this module was built wrong
against once and is now built against deliberately. `try: read except: default` is honest about a
missing *file* and silent about a missing *field*: `row.get("claims_dropped") or 0` turns "the
verifier never reported" into "the verifier dropped nothing", and nothing is green. So every number
here reads its inputs through `_req()`, which returns None for absent/non-numeric fields, and every
None propagates to `unknown`. A green in this brief means *measured and healthy*, never *silent*.

Two further honesty guards, each earned from a real defect:
  * **Stale-report guard** — coverage names the day it measured and refuses to score a report older
    than MAX_REPORT_AGE_DAYS. Reading the newest *readable* report as if it were today's let a
    one-party ingest break render green off a stale healthy day.
  * **Schema-semantics guard** — `statements_ingested` changed meaning in Session 5 (cumulative
    corpus totals -> day-scoped). Medianing across that boundary made a healthy 186-statement day
    read 0.4% of a 44,546 "median" — a confident false RED that would have sent the owner into
    Playbook P2 hunting an outage that never happened. Pre-boundary reports are excluded, visibly.

Reach (health number 5) is deliberately NOT machine-collected: it is a monthly hand count (07-OPS
§2.5, "vanity is a monthly vitamin, not a daily meal"), so it reports as an owner action rather than
being fabricated from something adjacent.
"""
from __future__ import annotations

import calendar
import datetime as dt
import json

import statistics

from . import config, ops, util

COVERAGE_MIN_SHARE = 0.60     # §2.3 green: each party >= 60% of its own trailing median
COVERAGE_WINDOW = 14          # §2.3 trailing window, in CALENDAR DAYS (not "the newest 14 files")
UPSTREAM_STALE_HOURS = 36.0   # §2.3 green also requires upstream < 36h stale (P2's clock)
DROP_RATE_MAX = 0.25          # §2.4 green: < 25% of claims dropped
DROP_WINDOW = 7               # §2.4 window, in CALENDAR DAYS
SPEND_PROJECTED_MAX = 8.0     # §2.2 green: projected month-end <= $8
DEGRADED_WINDOW = 7           # the ritual is weekly, so "recent degraded days" is weekly too
MAX_REPORT_AGE_DAYS = 2       # a symmetry report older than this cannot describe current coverage
MIN_MEDIAN_SAMPLES = 3        # below this there is no baseline to compare against

# The Session-5 day-scoping fix (ops.symmetry_report: "DAY-SCOPED ... never the cumulative corpus
# total mislabeled under the day"). Reports BEFORE this day carry cumulative corpus totals under a
# per-day label, so they are not comparable to current ones and are excluded from every trend here.
# Reports written after that fix are self-identifying via `day_scoped: true`; this dated floor is the
# backstop for the ones already on disk, which predate the marker.
DAY_SCOPED_FROM = "2026-07-13"

GREEN, RED, UNKNOWN, MANUAL = "green", "red", "unknown", "manual"


def _iso(d: dt.date) -> str:
    return d.isoformat()


def _parse(day: str) -> dt.date:
    return dt.date.fromisoformat(day)


def brief_day(reference=None) -> str:
    """The day the brief REPORTS ON — the day it RUNS. `util.product_day()` is the day being
    assembled (the prior America/New_York day, §2), so the brief's day is one later. Derived from
    product_day so both share exactly one definition of "what day is it" (and one timezone)."""
    return _iso(_parse(util.product_day(reference)) + dt.timedelta(days=1))


def _read(path, default=None):
    """A corrupt/half-written artifact must never take down the brief — but it is an UNKNOWN, not a
    clean read. Callers distinguish by passing default=None and checking."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _req(d, key):
    """Required numeric field: None when absent/null/non-numeric. THE guard — never `or 0`, because
    a missing field means 'not measured', and not-measured must never arrive as a healthy zero."""
    if not isinstance(d, dict):
        return None
    v = d.get(key)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _day_scoped(report: dict) -> bool:
    """Is this report's `statements_ingested` comparable to today's? (See DAY_SCOPED_FROM.)"""
    if report.get("day_scoped") is True:
        return True
    day = report.get("day")
    try:
        return bool(day) and _parse(day) >= _parse(DAY_SCOPED_FROM)
    except (ValueError, TypeError):
        return False


def _published_days() -> set[str]:
    """Days that actually published, from the assemble manifests (the publish act itself). A file
    that will not parse is NOT counted as published — an unreadable receipt is not a receipt."""
    out = set()
    for p in (config.DERIVED / "manifest").glob("assemble-*.json"):
        day = p.stem.replace("assemble-", "")
        try:
            _parse(day)
        except ValueError:
            continue                       # assemble-latest.json et al. are pointers, not days
        if _read(p) is not None:
            out.add(day)
    return out


# --- the five numbers ----------------------------------------------------------------------------
def streak(today: str) -> dict:
    """§2.1 — days since the last missed publish. Day D publishes on D+1, so the newest EXPECTED day
    is yesterday; a hole there is a miss happening now (RED -> Playbook P1), not a pending run."""
    pub = _published_days()
    if not pub:
        return {"name": "streak", "value": None, "status": UNKNOWN,
                "note": "no assemble manifests — nothing has published yet"}
    expected = _iso(_parse(today) - dt.timedelta(days=1))
    if expected not in pub:
        return {"name": "streak", "value": 0, "status": RED, "last_missed": expected,
                "note": f"no publish for {expected} — Playbook P1"}
    n, cur = 0, _parse(expected)
    while _iso(cur) in pub:
        n += 1
        cur -= dt.timedelta(days=1)
    # `cur` is the day the walk stopped. That is only a MISS if it postdates the first publish ever;
    # before that there was no streak to break, and reporting one would invent a failure.
    first = min(pub)
    last_missed = _iso(cur) if _iso(cur) > first else None
    return {"name": "streak", "value": n, "status": GREEN, "last_missed": last_missed,
            "note": f"{n} consecutive days published (through {expected})"}


def spend(today: str) -> dict:
    """§2.2 — month-to-date + a projection against the $8 green line.

    `days` is the ledger's primitive and `total_usd` its cached rollup, so MTD is summed from `days`;
    an absent/empty `days` is UNKNOWN, never $0 (a silent ledger is exactly what a broken cost path
    looks like, and $0 is the most reassuring number in the file).

    The projection divides by days the LEDGER COVERS, not days elapsed in the month. Dividing by
    elapsed days systematically under-projects — in the green direction — whenever spending starts
    mid-month, which is precisely when a new cost is being evaluated."""
    d = _parse(today)
    ledger = _read(config.DERIVED / "cost" / f"{today[:7]}.json")
    days = (ledger or {}).get("days")
    if not isinstance(days, dict) or not days:
        return {"name": "spend", "value": None, "status": UNKNOWN,
                "note": f"no cost ledger for {today[:7]} — spend not measured "
                        f"(the $10 Console cap is the backstop)"}
    amounts = {k: _req(v, "usd") for k, v in days.items()}
    if any(v is None for v in amounts.values()):
        bad = sorted(k for k, v in amounts.items() if v is None)
        return {"name": "spend", "value": None, "status": UNKNOWN,
                "note": f"cost ledger has unreadable days ({', '.join(bad[:3])}) — spend not measured"}
    mtd = sum(amounts.values())
    first = min(_parse(k) for k in days)
    covered = (d - first).days + 1                       # calendar days the ledger has been running
    remaining = calendar.monthrange(d.year, d.month)[1] - d.day
    rate = mtd / covered if covered > 0 else 0.0
    projected = round(mtd + rate * remaining, 4)
    gov = ops.budget_governor(mtd)
    note = (f"${mtd:.4f} MTD, ${projected:.2f} projected month-end (green <= ${SPEND_PROJECTED_MAX:.0f}); "
            f"governor {gov}")
    return {"name": "spend", "value": round(mtd, 4), "projected": projected,
            "status": GREEN if projected <= SPEND_PROJECTED_MAX else RED,
            "governor": gov, "ledger_days": len(days), "note": note}


def _symmetry_days(today: str, window_days: int) -> list[dict]:
    """Symmetry reports within `window_days` CALENDAR DAYS before today, newest first.

    Counting FILES instead of days silently reaches back across outages — after a 3-week gap, "the
    trailing 14-day median" would be measured against pre-outage days. `latest.json` is a pointer
    copy and is skipped; counting it would double-count the newest day."""
    end = _parse(today)
    start = end - dt.timedelta(days=window_days)
    rows = []
    for p in sorted((config.DERIVED / "symmetry").glob("*.json"), reverse=True):
        if p.stem == "latest":
            continue
        try:
            day = _parse(p.stem)
        except ValueError:
            continue
        if not (start <= day < end):
            continue
        r = _read(p)
        if r is not None:
            rows.append(r)
    return rows


def upstream_freshness(today: str) -> dict:
    """§2.3's other half — how stale is `congress-press`? The real measurement is made in RUN A and
    filed in the COLLECT manifest (`source_freshness.age_hours`); the assemble-side symmetry report
    only carries a placeholder note, so reading it there is why this gate went unimplemented."""
    for i in range(0, 3):
        day = _iso(_parse(today) - dt.timedelta(days=i))
        m = _read(config.DERIVED / "manifest" / f"collect-{day}.json")
        f = (m or {}).get("source_freshness") or {}
        age = _req(f, "age_hours")
        if age is not None:
            return {"age_hours": age, "day": day,
                    "status": GREEN if age < UPSTREAM_STALE_HOURS else RED}
    return {"age_hours": None, "status": UNKNOWN}


def coverage(today: str) -> dict:
    """§2.3 — each party's newest Lane-1 ingest vs its OWN trailing median, AND upstream freshness.

    Per-party medians (never pooled): the parties legitimately differ in volume, and the question is
    whether a party fell off its own baseline — which is exactly what a one-party ingest break looks
    like, and exactly what pooling would hide."""
    rows = [r for r in _symmetry_days(today, COVERAGE_WINDOW + 1) if _day_scoped(r)]
    excluded = len(_symmetry_days(today, COVERAGE_WINDOW + 1)) - len(rows)
    fresh = upstream_freshness(today)
    if not rows:
        return {"name": "coverage", "value": None, "status": UNKNOWN, "freshness": fresh,
                "note": "no comparable symmetry reports — coverage not measured"}
    latest, prior = rows[0], rows[1:]
    used_day = latest.get("day")
    age = (_parse(today) - _parse(used_day)).days if used_day else None
    if age is None or age > MAX_REPORT_AGE_DAYS:
        return {"name": "coverage", "value": None, "status": UNKNOWN, "day": used_day,
                "freshness": fresh,
                "note": f"newest symmetry report is {used_day} ({age}d old) — cannot describe "
                        f"current coverage"}
    parties, statuses = {}, []
    for p in config.COMPOSITE_PARTIES:
        now = _req((latest.get("parties") or {}).get(p), "statements_ingested")
        hist = [_req((r.get("parties") or {}).get(p), "statements_ingested") for r in prior]
        hist = [h for h in hist if h is not None]
        if now is None or len(hist) < MIN_MEDIAN_SAMPLES:
            parties[p] = {"statements": now, "median": None, "share": None, "status": UNKNOWN}
            statuses.append(UNKNOWN)
            continue
        med = statistics.median(hist)
        share = round(now / med, 3) if med else None
        st = UNKNOWN if share is None else (GREEN if share >= COVERAGE_MIN_SHARE else RED)
        parties[p] = {"statements": now, "median": med, "share": share, "status": st}
        statuses.append(st)
    statuses.append(fresh["status"])              # §2.3: freshness is part of the green, not a sidecar
    status = RED if RED in statuses else (UNKNOWN if UNKNOWN in statuses else GREEN)
    detail = " ".join(
        f"{p} {v['statements']}/{v['median']:.0f}={v['share']:.0%}" if v["share"] is not None
        else f"{p} {v['statements']}/? " for p, v in parties.items())
    fresh_txt = (f"upstream {fresh['age_hours']:.1f}h" if fresh["age_hours"] is not None
                 else "upstream age unknown")
    note = (f"{used_day}: {detail} of own {COVERAGE_WINDOW}d median (green >= {COVERAGE_MIN_SHARE:.0%}); "
            f"{fresh_txt} (green < {UPSTREAM_STALE_HOURS:.0f}h)")
    if excluded:
        note += f"; {excluded} pre-{DAY_SCOPED_FROM} report(s) excluded (cumulative-total schema)"
    return {"name": "coverage", "day": used_day, "parties": parties, "status": status,
            "freshness": fresh, "excluded_reports": excluded, "note": note}


def verifier_drop(today: str) -> dict:
    """§2.4 — claims dropped / claims offered, 7 days, both parties pooled (the verifier is one
    instrument). A row missing either field is UNMEASURED, not zero-dropped: if the LLM layer fails
    for a party, `or 0` would report the OTHER party's healthy rate as the instrument's, in green.

    Note vs §2.4's wording ("dropped / published"): the denominator here is dropped+published =
    claims OFFERED, which is the rate the 25% line is meaningful against. Flagged in the BUILDLOG
    rather than silently diverging."""
    rows = _symmetry_days(today, DROP_WINDOW)
    pub = dropped = measured = unmeasured = 0
    for r in rows:
        for p in config.COMPOSITE_PARTIES:
            row = (r.get("parties") or {}).get(p)
            a, b = _req(row, "claims_published"), _req(row, "claims_dropped")
            if a is None or b is None:
                unmeasured += 1
                continue
            pub += a
            dropped += b
            measured += 1
    offered = pub + dropped
    if not measured or not offered:
        return {"name": "verifier_drop", "value": None, "status": UNKNOWN,
                "note": f"no measured claims in {DROP_WINDOW}d ({unmeasured} unmeasured party-rows)"
                        " — drop rate not measured"}
    rate = round(dropped / offered, 4)
    note = f"{dropped}/{offered} claims dropped over {DROP_WINDOW}d (green < {DROP_RATE_MAX:.0%})"
    if unmeasured:
        note += f"; {unmeasured} party-row(s) unmeasured"
    return {"name": "verifier_drop", "value": rate, "dropped": dropped, "offered": offered,
            "unmeasured_rows": unmeasured,
            "status": GREEN if rate < DROP_RATE_MAX else RED, "note": note}


def reach() -> dict:
    """§2.5 — followers/sessions/citations are a MONTHLY hand count by design. Reported as an owner
    action, never machine-filled, so the brief implies no measurement it did not make."""
    return {"name": "reach", "value": None, "status": MANUAL,
            "note": "monthly hand count (followers + sessions + citations) — not machine-collected"}


# --- context the numbers don't carry -------------------------------------------------------------
def degraded_days(today: str) -> list[str]:
    """Degraded runs in the last week — the "anything odd" the Monday ritual would otherwise hunt
    for. Weekly, because the ritual is weekly: month-scoping hid the whole prior week on the 1st."""
    end, out = _parse(today), []
    for p in sorted((config.DERIVED / "manifest").glob("assemble-*.json")):
        day = p.stem.replace("assemble-", "")
        try:
            d = _parse(day)
        except ValueError:
            continue
        if not (end - dt.timedelta(days=DEGRADED_WINDOW) <= d < end):
            continue
        m = _read(p) or {}
        if m.get("degraded") or m.get("governor_state") in ("warn", "degrade"):
            out.append(day)
    return out


def top_phrase(today: str) -> dict | None:
    """The week's most synchronized phrase — the one number in the brief about the PRODUCT rather
    than the plumbing."""
    best = None
    for i in range(1, 8):
        day = _iso(_parse(today) - dt.timedelta(days=i))
        rows = (_read(config.DERIVED / "days" / f"{day}.json") or {}).get("top_synchronized") or []
        for r in rows[:1]:
            if best is None or (r.get("day_peak") or 0) > (best.get("day_peak") or 0):
                best = {"ngram": r.get("ngram"), "party": r.get("party"),
                        "day_peak": r.get("day_peak"), "day": day}
    return best


def shelf() -> dict:
    """The dark shelf (docs/11): what is built + verified and waiting on a release flip — Michael's
    act, and the one standing decision the brief should keep in front of him."""
    return {"dark": sorted(k for k, v in config.FEATURES.items() if not v),
            "released": sorted(k for k, v in config.FEATURES.items() if v)}


# --- assembly + delivery -------------------------------------------------------------------------
def build_brief(today: str) -> dict:
    """The whole brief as data (rendered separately, so the numbers are testable without ntfy)."""
    numbers = [streak(today), spend(today), coverage(today), verifier_drop(today), reach()]
    reds = [n["name"] for n in numbers if n["status"] == RED]
    unknowns = [n["name"] for n in numbers if n["status"] == UNKNOWN]
    # Headline by INCLUSION: "every number I measured is green", not "nothing I recognized
    # complained". Computing it by exclusion (`not reds and not unknowns`) hands a green headline
    # to any status this function doesn't know about — including a future typo.
    all_green = all(n["status"] in (GREEN, MANUAL) for n in numbers)
    return {
        "schema_version": 1, "kind": "owners-brief", "day": today,
        "numbers": numbers, "reds": reds, "unknowns": unknowns,
        "degraded_days": degraded_days(today), "top_phrase": top_phrase(today), "shelf": shelf(),
        "headline": ("ALL GREEN" if all_green
                     else ("RED: " + ", ".join(reds)) if reds
                     else ("UNKNOWN: " + ", ".join(unknowns)) if unknowns
                     else "CHECK: unrecognized status"),
    }


def render_brief(b: dict) -> str:
    """Plain text for ntfy — reads top-to-bottom on a phone, no interpretation required. Every line
    carries its own MEASUREMENT, not just its method: a bare "[RED] coverage: each party vs its
    trailing median" tells a tired owner nothing they can act on."""
    L = [f"OnScript — week of {b['day']}", b["headline"], ""]
    for n in b["numbers"]:
        mark = {GREEN: "OK", RED: "RED", UNKNOWN: "??", MANUAL: "--"}.get(n["status"], "!!")
        L.append(f"[{mark}] {n['name']}: {n['note']}")
    if b["degraded_days"]:
        L += ["", f"Degraded days this week: {', '.join(b['degraded_days'])}"]
    tp = b.get("top_phrase")
    if tp:
        L += ["", f"Top phrase of the week: \"{tp['ngram']}\" — {tp['day_peak']} {tp['party']} on {tp['day']}"]
    L += ["", f"Dark shelf ({len(b['shelf']['dark'])} built, unreleased): {', '.join(b['shelf']['dark'])}",
          "Monday ritual: five numbers, skim both Lines with your editor hat, odd -> BUILDLOG."]
    return "\n".join(L)


def send_brief(today: str, *, force_cadence: bool = False) -> dict:
    """Fires Mondays only, and only once the feature is released. Writes the artifact regardless, so
    the numbers stay auditable while dark.

    `force_cadence` bypasses ONLY the Monday gate (an operator previewing on a Wednesday). It can
    never bypass the dark gate: the FEATURES flip is the release act — dated, public, diffable
    (docs/11 §1) — and a kwarg that defeats it would be a second, undated release path."""
    b = build_brief(today)
    util.write_json(config.DERIVED / "brief" / f"{today}.json", b)
    if not config.feature_on("owners_brief"):
        return {"sent": False, "reason": "feature dark", "brief": b}
    if _parse(today).weekday() != 0 and not force_cadence:
        return {"sent": False, "reason": "not Monday", "brief": b}
    r = ops.ntfy(f"OnScript brief — {b['headline']}", render_brief(b),
                 priority="high" if b["reds"] else "default")
    return {"sent": bool(r.get("sent")), "reason": r.get("reason"), "brief": b}


if __name__ == "__main__":  # pragma: no cover - operator preview (never sends)
    import sys
    day = sys.argv[1] if len(sys.argv) > 1 else util.product_day()
    print(render_brief(build_brief(day)))
