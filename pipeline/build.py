"""Derived-artifact builder: turn statements + ledger into the small JSON the site reads.

Deterministic (no LLM). Produces top-synchronized-phrase tables, per-phrase adoption
curves, the discipline index, per-day summaries, and coverage tables (temporal honesty,
§1.3). The LLM Daily Lines are merged into the per-day files by the (later) assemble stage.
"""
from __future__ import annotations

from collections import defaultdict

from . import boilerplate, config, util


def phrase_slug(ngram: str) -> str:
    return util.sha256_hex(ngram)[:16]


def _velocity(daily: dict, day: str) -> float:
    """Distinct-unit count on `day` (max party) over the mean of the prior 14 present days."""
    days = sorted(daily.keys())
    today = 0
    for p in config.COMPOSITE_PARTIES:
        today = max(today, daily.get(day, {}).get(p, 0))
    prior = [d for d in days if d < day][-14:]
    if not prior:
        return float(today)
    base = 0.0
    for d in prior:
        base += max(daily[d].get(p, 0) for p in config.COMPOSITE_PARTIES)
    base = (base / len(prior)) or 0.5
    return round(today / base, 2)


def _members_on(entry: dict, day: str, party: str) -> frozenset:
    return frozenset((entry["daily"].get(day, {}) or {}).get(f"members_{party}", []))


def _padding_variant(a: str, b: str) -> bool:
    """True iff a and b are the SAME phrase differing only by STOPWORD padding — one is a contiguous
    token-run inside the other and every extra token is a stopword ("the water resources development
    act" vs "water resources development act"). A CONTENT difference is NOT padding: "sue the trump
    administration" vs "the trump administration" differ by "sue", and "…act" vs "…act wrda" differ by
    the acronym — those are distinct rows. This precision is what stops a generic entity phrase from
    absorbing every real message that mentions it. §Session-8."""
    ta, tb = a.split(), b.split()
    if len(ta) == len(tb):
        return a == b
    short, long = (ta, tb) if len(ta) < len(tb) else (tb, ta)
    for i in range(len(long) - len(short) + 1):
        if long[i:i + len(short)] == short:
            extra = long[:i] + long[i + len(short):]
            return all(t in boilerplate.STOPWORDS for t in extra)
    return False


def _collapse_nested(rows: list[dict]) -> list[dict]:
    """Collapse STOPWORD-padding variants of a phrase to ONE row so a bill title doesn't show as 3-6
    near-identical signals ("the water resources development act" folds into "water resources
    development act"). Deliberately conservative: a permissive substring merge would let a generic
    entity ("the trump administration", peak 20) ABSORB every distinct message containing it ("sue the
    trump administration", "hold … accountable") — hiding the real coordination behind a useless label
    (adversarial-review finding). So only pure-stopword differences merge; a content difference (incl.
    an acronym) stays its own row. Representative = the LEAST-padded form (fewest tokens), carrying the
    family's max peak. Display-only; the ledger keeps every variant. §Session-8 (near-dup)."""
    kept: list[dict] = []
    # least-padded first (fewest tokens), then highest peak -> the clean phrase represents its family
    for r in sorted(rows, key=lambda x: (len(x["ngram"].split()), -x["day_peak"])):
        fam = next((k for k in kept if r["party"] == k["party"] and _padding_variant(k["ngram"], r["ngram"])), None)
        if fam is None:
            kept.append(r)
        else:
            fam["day_peak"] = max(fam["day_peak"], r["day_peak"])  # keep the family's magnitude
    return kept


def top_synchronized(ledger: dict, day: str, k: int = 50) -> list[dict]:
    """Top synchronized phrases active on `day`, ranked by that day's peak party count,
    with nested sub-grams collapsed to their maximal phrase."""
    rows = []
    for ngram, e in ledger.items():
        d = e["daily"].get(day)
        if not d:
            continue
        # Display-time boilerplate guard: re-apply the current suppression rules so regex/knob
        # updates take effect on an already-built ledger without re-running the engine. is_weak_label
        # also drops connective-glue phrases ("and the trump administration's") from the table (C-i).
        if (boilerplate.is_boilerplate_ngram(ngram) or boilerplate.is_low_content(ngram)
                or boilerplate.is_weak_label(ngram)):
            continue
        peak = max((d.get(p, 0) for p in config.COMPOSITE_PARTIES), default=0)
        if peak < config.SYNC_MIN_MEMBERS:
            continue
        party = max(config.COMPOSITE_PARTIES, key=lambda p: d.get(p, 0))
        # 14-day series (max party count per present day) carried on the row so EVERY table row can
        # draw a sparkline without needing a per-phrase detail page. §Session-7 (D).
        daily = e["daily"]
        sdays = sorted(dd for dd in daily if dd <= day)[-14:]
        series = [max(daily[dd].get("D", 0), daily[dd].get("R", 0)) for dd in sdays]
        rows.append({
            "ngram": ngram, "slug": phrase_slug(ngram), "n": e["n"],
            "day_peak": peak, "party": party,
            "counts": {p: d.get(p, 0) for p in config.ALL_PARTIES},
            "velocity": _velocity(e["daily"], day),
            "first_seen": e["first_seen"], "df_weight": e["df_weight"], "series": series,
            "_members": _members_on(e, day, party),
        })
    rows = _collapse_nested(rows)
    # Rank: coordination magnitude first (biggest converged phrase leads), then CONTENT-richness so a
    # generic 2-word phrase ("an important step") sinks below a substantive one of equal peak
    # ("federal financial assistance"), then distinctiveness, then velocity. §Session-7 (C-iii).
    rows.sort(key=lambda r: (r["day_peak"], boilerplate.content_word_count(r["ngram"]),
                             r.get("df_weight", 0), r["velocity"]), reverse=True)
    rows = rows[:k]
    for r in rows:
        r.pop("_members", None)
    return rows


def top_by_velocity(ledger: dict, day: str, k: int = 50) -> list[dict]:
    rows = top_synchronized(ledger, day, k=10_000)
    rows.sort(key=lambda r: (r["velocity"], r["day_peak"]), reverse=True)
    return rows[:k]


def phrase_page(ngram: str, entry: dict) -> dict:
    """Full adoption curve + roster + first-sayer for one phrase page (§8)."""
    series = []
    for day in sorted(entry["daily"].keys()):
        d = entry["daily"][day]
        series.append({"day": day, **{p: d.get(p, 0) for p in config.ALL_PARTIES}})
    return {
        "schema_version": config.SCHEMA_VERSION if hasattr(config, "SCHEMA_VERSION") else 1,
        "ngram": ngram, "slug": phrase_slug(ngram), "n": entry["n"],
        "first_seen": entry["first_seen"], "df_weight": entry["df_weight"],
        "peak_units": entry.get("peak_units"),
        "series": series,
    }


def coverage_tables(statements: list[dict]) -> dict:
    """Per-year x per-party statement counts (temporal honesty layer, §1.3/§5.4)."""
    by_year: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    for s in statements:
        party = (s.get("member") or {}).get("party")
        if party in config.ALL_PARTIES:
            by_year[s["published_at"][:4]][party] += 1
    return {y: dict(parties) for y, parties in sorted(by_year.items())}


def build_derived(statements, ledger, discipline, out_dir, *, focus_day: str, k_phrases: int = 50,
                  coverage: dict | None = None) -> dict:
    """Write all deterministic derived JSON. Returns a summary for the manifest. Takes the
    precomputed discipline dict (not the engine) so derived can be regenerated for any focus
    day from saved state without re-running the ~30-min engine. `coverage` may be passed
    precomputed (Alexandria merge) to avoid needing all statements in memory."""
    from . import util as _u
    phrases_dir = out_dir / "phrases"
    days_dir = out_dir / "days"

    _u.write_json(out_dir / "discipline.json", discipline)
    if coverage is None:
        coverage = coverage_tables(statements)
    _u.write_json(out_dir / "coverage.json", coverage)

    top_recent = top_synchronized(ledger, focus_day, k=k_phrases)
    top_vel = top_by_velocity(ledger, focus_day, k=k_phrases)
    _u.write_json(phrases_dir / "top.json", {"day": focus_day, "by_peak": top_recent, "by_velocity": top_vel})

    # Per-phrase pages for the phrases surfaced in the top tables (bounded).
    surfaced = {r["ngram"] for r in top_recent} | {r["ngram"] for r in top_vel}
    for ngram in surfaced:
        _u.write_json(phrases_dir / f"{phrase_slug(ngram)}.json", phrase_page(ngram, ledger[ngram]))

    # Per-day summary for the focus day (Daily Lines merged later by assemble).
    day_top = top_synchronized(ledger, focus_day, k=20)
    _u.write_json(days_dir / f"{focus_day}.json", {
        "day": focus_day,
        "top_synchronized": day_top,
        "discipline": {p: discipline.get(p, {}).get(focus_day) for p in config.COMPOSITE_PARTIES},
        "daily_lines": None,  # filled by the LLM assemble stage
    })

    return {
        "ledger_entries": len(ledger),
        "phrase_pages": len(surfaced),
        "focus_day": focus_day,
        "focus_day_top_phrases": len(day_top),
        "coverage_years": sorted(coverage.keys()),
    }
