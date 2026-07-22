"""Derived-artifact builder: turn statements + ledger into the small JSON the site reads.

Deterministic (no LLM). Produces top-synchronized-phrase tables, per-phrase adoption
curves, the discipline index, per-day summaries, and coverage tables (temporal honesty,
§1.3). The LLM Daily Lines are merged into the per-day files by the (later) assemble stage.
"""
from __future__ import annotations

from collections import defaultdict

from . import boilerplate, config, privacy, util


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


# A fragment may exceed its fuller phrase's peak by at most this and still count as "the same
# coordinated message"; beyond it the short phrase appears in too many other contexts (a hub) and must
# stay its own row. Since a strict sub-gram's member count is always >= the fuller phrase's, this bounds
# how much MORE the fragment is used. Tuned so the real cases (~1.1-1.2x) merge and hubs (>3x) don't.
_SUBGRAM_PEAK_RATIO = 1.25


def _content_subrun(short: str, long: str) -> bool:
    """True iff `short` is a strict contiguous token sub-run of `long`. After the padding pass, any such
    pair differs by ≥1 CONTENT token, so `long` is the more specific/informative label."""
    ts, tl = short.split(), long.split()
    if len(ts) >= len(tl):
        return False
    return any(tl[i:i + len(ts)] == ts for i in range(len(tl) - len(ts) + 1))


def _collapse_subgrams(rows: list[dict]) -> list[dict]:
    """Second collapse pass: fold a shorter phrase into a longer one that CONTAINS it when their peaks
    are comparable — i.e. the fragment essentially only appears as part of the longer coordinated
    message ("children born in" → "children born in the united states"). Keeps the LONGER (more
    specific) label at ITS OWN, honest peak — never inflated by the fragment. Guarded by the peak RATIO
    so a generic hub is never absorbed: "born in the united states" (36) is NOT folded into "children
    born in the united states" (12) because 36 ≫ 12 (it appears across many messages, not just that
    one), and "the trump administration" (20) is not folded into "sue the trump administration" (6).
    This is the safe realization of "nested sub-grams → maximal phrase" without the over-merge trap.
    §Session-8f."""
    kept: list[dict] = []
    for r in sorted(rows, key=lambda x: (-len(x["ngram"].split()), -x["day_peak"])):  # longest first
        host = next((k for k in kept if r["party"] == k["party"]
                     and _content_subrun(r["ngram"], k["ngram"])
                     and r["day_peak"] <= k["day_peak"] * _SUBGRAM_PEAK_RATIO), None)
        if host is None:
            kept.append(r)      # else: r is a redundant fragment of `host` -> drop it (host keeps its own peak)
    return kept


def collapse_and_rank(rows: list[dict], k: int = 50) -> list[dict]:
    """Collapse near-duplicate phrase families, then rank for display and truncate. Two SAFE merges:
    (1) stopword-padding variants ("the X" → "X"), (2) a fragment folded into the fuller phrase that
    contains it when peaks are comparable (a hub is never absorbed). Reusable at BUILD time (from the
    ledger) AND at RENDER time (re-applied to a stored day's list so the CURRENT merge rules take effect
    on already-built pages without re-running the engine — the same display-time refresh the boilerplate
    guard uses). §Session-8f."""
    # Art. XIII privacy floor, FIRST and before any collapse — order is load-bearing. Filtered after
    # the collapse, a suppressed row can be elected family representative for a clean sub-gram and
    # carry a private name into the merged row. This one line is the chokepoint for every display
    # path that routes through here: top_synchronized (-> every day JSON's table, phrases/top.json,
    # and the `surfaced` set that decides which phrase pages exist), top_by_velocity, duet
    # candidates, and site.sync_table's render-time refresh of ALREADY-BUILT day pages.
    rows, _ = privacy.filter_rows(rows)
    rows = _collapse_subgrams(_collapse_nested(rows))
    # Rank: coordination magnitude first, then CONTENT-richness (a generic 2-word phrase sinks below a
    # substantive one of equal peak), then distinctiveness, then velocity. §Session-7 (C-iii).
    rows.sort(key=lambda r: (r.get("day_peak", 0), boilerplate.content_word_count(r["ngram"]),
                             r.get("df_weight", 0), r.get("velocity", 0)), reverse=True)
    return rows[:k]


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
        # Art. XIII: same established display-time-refresh position as the boilerplate guard, so an
        # already-built ledger is corrected without re-running the engine. Stops a suppressed row
        # before _members_on/_velocity do any work. (collapse_and_rank re-checks; this is the cheap
        # early cut, not the only one.)
        if privacy.is_suppressed(ngram):
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
    rows = collapse_and_rank(rows, k)
    for r in rows:
        r.pop("_members", None)
    return rows


def top_by_velocity(ledger: dict, day: str, k: int = 50) -> list[dict]:
    rows = top_synchronized(ledger, day, k=10_000)
    rows.sort(key=lambda r: (r["velocity"], r["day_peak"]), reverse=True)
    return rows[:k]


def top_synchronized_by_party(ledger: dict, day: str, k_per_party: int = 10) -> dict:
    """Each party's OWN top-k synchronized phrases for the day, ranked by THAT PARTY's member count
    (#146 / R3). The pooled top_synchronized ranks by raw peak and truncates, so the larger caucus
    structurally fills the table (measured 88% D). Ranking each party separately and giving each its own
    slots removes that display artifact — the fix goes in the VIEW, never the threshold: SYNC_MIN is
    untouched (a phrase is eligible for a party's column iff that party used it >= SYNC_MIN times, the
    same bar), only the ranking + per-party truncation change. Returns {party: [rows]}; each row is a
    top_synchronized row (carries counts{D,R}, so the render can show that party's count + denominator)."""
    allrows = top_synchronized(ledger, day, k=10_000)
    out: dict[str, list[dict]] = {}
    for p in config.COMPOSITE_PARTIES:
        prows = [r for r in allrows if (r.get("counts") or {}).get(p, 0) >= config.SYNC_MIN_MEMBERS]
        prows.sort(key=lambda r: ((r.get("counts") or {}).get(p, 0),
                                  boilerplate.content_word_count(r.get("ngram", "")),
                                  r.get("df_weight", 0)), reverse=True)
        out[p] = prows[:k_per_party]
    return out


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


def build_concordance(statements, ledger, *, out_dir=None, roster_map=None,
                      min_statements: int | None = None, receipts_max: int | None = None,
                      peak_floor: int | None = None) -> dict:
    """1.4 The Concordance (R4 / docs/21 §3.2) — the per-MEMBER on-script index.

    The discipline index is per-party-per-day; this is the per-member version. For each member, of
    their SOLO (non-joint) Lane-1 press releases, the share that contained >=1 phrase their party
    genuinely CONVERGED on (a kept ledger phrase that reached peak_floor members in one day) that is
    NOT an OFFICIAL NAME (bill title / committee name). The three R4 guarantees are structural here:

      * denominators on every line — every score carries its raw (on_script / statements) counts;
      * SPAN-gated — nomenclature.is_nomenclature() drops official-name occurrences from the
        numerator, so a member typing a bill's name is never counted as "on-script" (the #143
        confound). Degrades to a no-op where no verdicts table exists (fresh checkout / pre-108);
      * no predictive claim — this returns a measured overlap SHARE and its receipts, nothing about
        motive or direction (the render states so).

    The peak_floor is the #143 confound control: without it the index saturates near 1.0 (over a wide
    window nearly every release shares SOME 3-member-co-used gram — names, titles, generic language).

    JOINT / co-signed releases are EXCLUDED: a signed-together letter is coordination, not the
    member's solo voice, and folding it in reintroduces the participation confound #143 warned about.

    Members with < `min_statements` solo statements are NOT named (R2: no swarm of tied-at-zero
    "vessels"); their count is disclosed in aggregate. Party set = the two composites (D/R), matching
    every other cross-party metric (Independents enter the ledger but not the composites, §config).

    Reuses the engine's OWN tokenizer + n-gram set (phrases._doc_ngrams) so the intersection with the
    ledger is exact. Pure function of (statements, ledger): rebuild reproduces it byte-for-byte.
    """
    from .phrases import _doc_ngrams  # exact engine tokenization — the intersection must align
    from . import nomenclature

    min_statements = config.CONCORDANCE_MIN_STATEMENTS if min_statements is None else min_statements
    receipts_max = config.CONCORDANCE_RECEIPTS_MAX if receipts_max is None else receipts_max
    peak_floor = config.CONCORDANCE_PEAK_FLOOR if peak_floor is None else peak_floor
    if roster_map is None:
        from . import roster as _roster
        roster_map = _roster.load()
    # The "on-script" set is NOT the raw ledger. A phrase counts as "the party script" only if it:
    #   * coordinated at scale — peak_units >= peak_floor (#143 confound control; without it the index
    #     saturates near 1.0 because generic 3-member-co-used language swamps real talking points);
    #   * survives the Art. XIII privacy floor — a suppressed private-name phrase must never count toward
    #     on-script NOR appear as a receipt (ledger.json still holds it; suppression is applied at render);
    #   * survives the same display-time boilerplate/weak-label guards top_synchronized() applies.
    # (SPAN/nomenclature exclusion is per-occurrence below, since it depends on the statement's congress.)
    kept = {ng for ng, e in ledger.items()
            if (e.get("peak_units", 0) or 0) >= peak_floor
            and not privacy.is_suppressed(ng)
            and not boilerplate.is_boilerplate_ngram(ng)
            and not boilerplate.is_low_content(ng)
            and not boilerplate.is_weak_label(ng)}

    denom: dict[str, int] = defaultdict(int)          # bio -> solo statement count
    numer: dict[str, int] = defaultdict(int)          # bio -> solo statements with >=1 non-name sync phrase
    receipts: dict[str, list] = defaultdict(list)     # bio -> [{phrase,date,url}] (distinct phrases, capped)
    seen_phrase: dict[str, set] = defaultdict(set)
    meta: dict[str, dict] = {}
    nom_cache: dict[tuple, bool] = {}
    days: list[str] = []

    def _is_name(ngram: str, congress: int) -> bool:
        key = (ngram, congress)
        if key not in nom_cache:
            nom_cache[key] = bool(nomenclature.is_nomenclature(ngram, congress)) if congress else False
        return nom_cache[key]

    for s in statements:
        if s.get("lane") != 1 or s.get("syndicated") or s.get("joint_group"):
            continue
        m = s.get("member") or {}
        party = m.get("party")
        bio = m.get("bioguide")
        if party not in config.COMPOSITE_PARTIES or not bio:
            continue
        day = s.get("published_at")
        days.append(day)
        denom[bio] += 1
        if bio not in meta:
            r = roster_map.get(bio) or {}   # canonical name/state/chamber, statement value preferred
            meta[bio] = {"name": m.get("name") or r.get("name"), "party": party,
                         "state": m.get("state") or r.get("state"),
                         "chamber": m.get("chamber") or r.get("chamber")}
        congress = int(s.get("congress") or util.congress_for_date(day) or 0)
        matches = [ng for ng, _n in _doc_ngrams(s.get("text", ""))
                   if ng in kept and not _is_name(ng, congress)]
        if matches:
            numer[bio] += 1
            if len(receipts[bio]) < receipts_max:
                ng = next((g for g in matches if g not in seen_phrase[bio]), matches[0])
                seen_phrase[bio].add(ng)
                receipts[bio].append({"phrase": ng, "date": day, "url": s.get("url")})

    members = []
    excluded = 0
    for bio, n in denom.items():
        if n < min_statements:
            excluded += 1
            continue
        on = numer.get(bio, 0)
        info = meta[bio]
        members.append({
            "bioguide": bio, "name": info["name"], "party": info["party"],
            "state": info["state"], "chamber": info["chamber"],
            "statements": n, "on_script": on,
            "index": round(on / n, 4) if n else 0.0,
            "receipts": receipts.get(bio, []),
        })
    # Within-party rank by share (a reference INDEX, not a single-winner award — the #143/R2 construct);
    # both parties ship together, the render groups them. Deterministic tie-break so rebuild matches.
    members.sort(key=lambda r: (-r["index"], -r["statements"], (r["name"] or r["bioguide"] or "")))

    result = {
        "schema_version": 1,
        "generated_at": util.now_utc_iso(),
        "window": {"start": min(days) if days else None, "end": max(days) if days else None},
        "min_statements": min_statements,
        "peak_floor": peak_floor,
        "span_gated": True,
        "nomenclature_index_version": nomenclature.index_version(),
        "counts": {"named": len(members), "excluded_below_floor": excluded, "members_seen": len(denom)},
        "members": members,
    }
    if out_dir is not None:
        util.write_json(out_dir / "concordance.json", result)
    return result


def _window_days(days: list[str], focus_day: str | None, window_days: int) -> tuple[str, str]:
    """The trailing window [start, focus] as ISO strings (ISO dates sort lexically = chronologically)."""
    import datetime as _dt
    end = focus_day or (max(days) if days else util.product_day())
    start = (_dt.date.fromisoformat(end) - _dt.timedelta(days=window_days - 1)).isoformat()
    return start, end


def _active_solo_offices(statements) -> dict:
    """{(day, party): {bioguide}} — distinct party offices that published a SOLO (non-joint), non-
    syndicated Lane-1 release that day. This is The Unison's DENOMINATOR population, computed with the
    exact same filter the phrase engine's members_{party} list uses (`_eligible` + not joint_group), so a
    phrase's office set is a subset of it by construction and the office-share is always in [0, 1]."""
    active: dict[tuple[str, str], set] = defaultdict(set)
    for s in statements:
        if s.get("lane") != 1 or s.get("syndicated") or s.get("joint_group"):
            continue
        m = s.get("member") or {}
        party, bio = m.get("party"), m.get("bioguide")
        if party in config.COMPOSITE_PARTIES and bio:
            active[(s["published_at"], party)].add(bio)
    return active


def _office_info(statements, roster_map) -> dict:
    """bioguide -> {name, state} for labeling award cards, statement value preferred over roster."""
    info: dict[str, dict] = {}
    for s in statements:
        m = s.get("member") or {}
        bio = m.get("bioguide")
        if bio and bio not in info:
            r = (roster_map or {}).get(bio) or {}
            info[bio] = {"name": m.get("name") or r.get("name"), "state": m.get("state") or r.get("state")}
    return info


def _the_unison(statements, ledger, *, window_days, min_active, top_n, members_sample,
                focus_day, roster_map) -> dict:
    """THE UNISON (1.5 / R2) — each party's largest single-day office-share phrase over the window.

    office-share = (party offices that used the phrase in a SOLO release that day) / (party offices that
    published ANY solo release that day). Ranked WITHIN party; the #1 row is the award. SPAN-gated (an
    official name never wins — a bill title reaching high share is "everyone named the bill," not a
    message unison, the same #143 control as origination), and privacy/boilerplate/weak-label filtered
    exactly as the public sync table is. No member is named as a "vessel" — the unit is the PHRASE."""
    from . import nomenclature
    days_present = sorted({s["published_at"] for s in statements})
    start, end = _window_days(days_present, focus_day, window_days)
    active = _active_solo_offices(statements)
    info = _office_info(statements, roster_map)
    nom_cache: dict[tuple, bool] = {}

    def _is_name(ngram: str, congress: int) -> bool:
        key = (ngram, congress)
        if key not in nom_cache:
            nom_cache[key] = bool(nomenclature.is_nomenclature(ngram, congress)) if congress else False
        return nom_cache[key]

    by_party: dict[str, list[dict]] = {p: [] for p in config.COMPOSITE_PARTIES}
    for ngram, e in ledger.items():
        if (privacy.is_suppressed(ngram) or boilerplate.is_boilerplate_ngram(ngram)
                or boilerplate.is_low_content(ngram) or boilerplate.is_weak_label(ngram)):
            continue
        for day, d in e["daily"].items():
            if day < start or day > end:
                continue
            congress = int(util.congress_for_date(day) or 0)
            if _is_name(ngram, congress):
                continue
            for p in config.COMPOSITE_PARTIES:
                offices = _members_on(e, day, p) & active.get((day, p), frozenset())
                a = len(active.get((day, p), ()))
                n = len(offices)
                if n < config.SYNC_MIN_MEMBERS or a < min_active:
                    continue
                sample = [{"bioguide": b, **info.get(b, {})} for b in sorted(offices)[:members_sample]]
                by_party[p].append({
                    "ngram": ngram, "slug": phrase_slug(ngram), "day": day, "party": p,
                    "offices_using": n, "offices_active": a, "office_share": round(n / a, 4),
                    "members": sample, "members_more": max(0, n - len(sample)),
                })

    winners = {}
    for p, rows in by_party.items():
        # 1) each phrase at its single best day, so one week never shows the same line five times.
        best: dict[str, dict] = {}
        for r in rows:
            cur = best.get(r["ngram"])
            if cur is None or (r["office_share"], r["offices_using"]) > (cur["office_share"], cur["offices_using"]):
                best[r["ngram"]] = r
        rows = list(best.values())
        # 2) collapse near-duplicate phrase FAMILIES exactly as the public sync table does — stopword-
        #    padding variants ("the united states of" -> "united states of") and sub-grams folded into
        #    their maximal phrase — reusing the tested collapse so The Unison can't regress what the
        #    flagship already fixed (a bill/anniversary phrase showing as 3-5 near-identical rows).
        #    day_peak = offices_using drives the collapse magnitude the way the flagship uses the peak.
        for r in rows:
            r["day_peak"] = r["offices_using"]
            r.setdefault("df_weight", 0)
            r.setdefault("velocity", 0)
        rows = collapse_and_rank(rows, k=10_000)
        # 3) rank by office-share (collapse_and_rank ranks by magnitude); content richness breaks ties so
        #    a substantive phrase outranks a generic fragment of equal share; ngram makes it deterministic.
        rows.sort(key=lambda r: (r["office_share"], r["offices_using"],
                                 boilerplate.content_word_count(r["ngram"]), r["ngram"]), reverse=True)
        for r in rows:  # drop the collapse scaffolding; keep the award fields
            for k in ("day_peak", "df_weight", "velocity", "counts", "series", "n", "first_seen", "_members"):
                r.pop(k, None)
        winners[p] = rows[:top_n]
    return {"window": {"start": start, "end": end}, "min_active": min_active, "by_party": winners}


def _the_void(*, window, silence_dir, top_n) -> dict:
    """THE VOID (1.5 / R2) — the window's loudest silence, BOTH directions, rolled up from the 1.2
    absence-map boards. `silent` = topics in the news neither party will touch; `void` = topics a party
    pushes that the news ignores. Reads whatever scored boards exist on disk for the window; if none do,
    it is honestly UNAVAILABLE — 1.2's law (a gap is never rendered as a silence) carries through, so The
    Void never fabricates an award from a missing baseline (the common state until 1.2 is wired)."""
    import json as _json
    start, end = window["start"], window["end"]
    silent, void, scored = [], [], 0
    if silence_dir is not None and silence_dir.exists():
        for f in sorted(silence_dir.glob("*.json")):
            day = f.stem
            if day < start or day > end:
                continue
            try:
                b = _json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not b or not b.get("scored"):
                continue
            scored += 1
            for r in (b.get("silent") or []):
                silent.append({**r, "day": day})
            for r in (b.get("void") or []):
                void.append({**r, "day": day})
    silent.sort(key=lambda r: (r.get("news_volume") or 0, r.get("day")), reverse=True)
    void.sort(key=lambda r: ((r.get("D") or 0) + (r.get("R") or 0), r.get("day")), reverse=True)
    silent, void = silent[:top_n], void[:top_n]
    return {
        "available": scored > 0,
        "boards_scored": scored,
        "loudest_silence": silent[0] if silent else None,
        "silence_top": silent,
        "loudest_void": void[0] if void else None,
        "void_top": void,
        "note": ("the loudest topic the day's news carried that neither party would touch, and the "
                 "topic a party pushed hardest that the news ignored — both from the deterministic "
                 "absence map" if scored else
                 "the absence map has not been built for this window, so no silence is scored — a gap "
                 "is never reported as a silence"),
    }


def build_awards(statements, ledger, *, out_dir=None, focus_day: str | None = None, roster_map=None,
                 window_days: int | None = None, min_active: int | None = None,
                 top_n: int | None = None, silence_dir=None) -> dict:
    """1.5 The Unison + The Void (R2 / docs/21 §3.2) — the symmetric weekly awards that replaced the
    killed Ventriloquism Award (docs/04 R2 ruling). Two award families, both symmetric by construction:

      * THE UNISON — each party's largest single-day office-share phrase over the trailing window. See
        `_the_unison`: the numerator is the coordination magnitude, so the winner is self-evidently a
        real talking point (no separate peak floor needed); every card carries its raw offices-using /
        offices-active counts on its face; SPAN-gated so a bill title never wins; no member is shamed.
      * THE VOID — the window's loudest silence, both directions, from the 1.2 boards. See `_the_void`:
        degrades to UNAVAILABLE when no scored board exists for the window (a gap is never a silence).

    Written EVERY run (build dark / release by gate, like concordance.json and day_json['sync_by_party']);
    only site.awards_body is gated on FEATURES['awards'], so the flip is a pure release act. Pure function
    of (statements, ledger, [silence boards on disk]); rebuild reproduces it byte-for-byte (bar
    generated_at). Both parties are scored by the identical rule; Independents are not in the composites."""
    from . import nomenclature
    window_days = config.UNISON_WINDOW_DAYS if window_days is None else window_days
    min_active = config.UNISON_MIN_ACTIVE if min_active is None else min_active
    top_n = config.UNISON_TOP_N if top_n is None else top_n
    if roster_map is None:
        from . import roster as _roster
        roster_map = _roster.load()
    if silence_dir is None and out_dir is not None:
        silence_dir = out_dir / "silence"

    unison = _the_unison(statements, ledger, window_days=window_days, min_active=min_active, top_n=top_n,
                         members_sample=config.UNISON_MEMBERS_SAMPLE, focus_day=focus_day,
                         roster_map=roster_map)
    void = _the_void(window=unison["window"], silence_dir=silence_dir, top_n=config.VOID_TOP_N)

    # Caucus size (distinct offices per party across the corpus) — a SECONDARY denominator on each card,
    # so the reader sees both "of the offices that spoke that day" and "of the whole caucus" (R3 doctrine).
    caucus_seen: dict[str, set] = {p: set() for p in config.COMPOSITE_PARTIES}
    for s in statements:
        m = s.get("member") or {}
        p, bio = m.get("party"), m.get("bioguide")
        if p in caucus_seen and bio:
            caucus_seen[p].add(bio)

    result = {
        "schema_version": 1,
        "generated_at": util.now_utc_iso(),
        "window": unison["window"],
        "min_active": unison["min_active"],
        "span_gated": True,
        "nomenclature_index_version": nomenclature.index_version(),
        "caucus": {p: len(v) for p, v in caucus_seen.items()},
        "unison": unison["by_party"],
        "void": void,
    }
    if out_dir is not None:
        util.write_json(out_dir / "awards.json", result)
    return result


def build_derived(statements, ledger, discipline, out_dir, *, focus_day: str, k_phrases: int = 50,
                  coverage: dict | None = None, allow_final_overwrite: bool = False) -> dict:
    """Write all deterministic derived JSON. Returns a summary for the manifest. Takes the
    precomputed discipline dict (not the engine) so derived can be regenerated for any focus
    day from saved state without re-running the ~30-min engine. `coverage` may be passed
    precomputed (Alexandria merge) to avoid needing all statements in memory.

    `allow_final_overwrite` is the deliberate escape hatch for an operator who has decided to
    rebuild a PUBLISHED day's deterministic half in place (see `scripts/regen_derived.py --force`).
    RUN A never sets it — see the immutability note at the day-JSON write below."""
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
    #
    # IMMUTABILITY OF A PUBLISHED DAY (docs/23 §7.5 R-C). This write is a full-object OVERWRITE that
    # carries `daily_lines: None`, so running it over an already-published day deletes that day's
    # composites, talking_points, duets and rejected_keys. That is not hypothetical — it destroyed
    # two published days in production (2026-07-12 and 2026-07-18). A published day is the permanent
    # public record; RUN A may not rewrite it. The only sanctioned write path to a published day is
    # `run_assemble --day <day>` (the repair), which does its own read-modify-write and never routes
    # through here.
    #
    # SKIP-AND-LOG, NEVER RAISE. RUN A runs twice a day and routinely re-focuses a day that is
    # already published, so hitting this guard is the NORMAL case, not an error condition. Raising
    # would break the streak the guard exists to protect.
    #
    # SCOPE IS DELIBERATELY NARROW — only days/{day}.json. discipline.json, coverage.json,
    # phrases/top.json and the per-phrase pages are the CURRENT STATE OF THE INSTRUMENT, not the
    # record of a date: the per-phrase pages in particular are living adoption curves, and freezing
    # them would strand every phrase at whatever day first surfaced it. They keep refreshing.
    if _u.day_is_final(focus_day, out_dir) and not allow_final_overwrite:
        print(f"[immutable] {focus_day} is published — day JSON left untouched "
              f"(repair path: python -m pipeline.run_assemble --day {focus_day})")
        day_top, focus_day_write = None, "skipped-final"
    else:
        day_top = top_synchronized(ledger, focus_day, k=20)
        _u.write_json(days_dir / f"{focus_day}.json", {
            "day": focus_day,
            "top_synchronized": day_top,
            "discipline": {p: discipline.get(p, {}).get(focus_day) for p in config.COMPOSITE_PARTIES},
            "daily_lines": None,  # filled by the LLM assemble stage
        })
        focus_day_write = "written"

    # Peak-day source evidence for every public phrase page. It is deliberately downstream of the
    # core day write and fail-soft: an optional public receipt slice must never cost the streak its
    # day artifact. Alexandria's ledger-only rebuild passes no statements and leaves this slice alone.
    if statements:
        try:
            from . import phrase_evidence
            phrase_evidence.build_phrase_evidence(statements, out_dir)
        except Exception as e:  # pragma: no cover - streak safety belt, exercised only on a real defect
            print(f"[phrase-evidence] skipped (skip-and-log): {e}")

    return {
        "ledger_entries": len(ledger),
        "phrase_pages": len(surfaced),
        "focus_day": focus_day,
        # Honest about work NOT done: a skipped day reports None, never the count it would have
        # written. The manifest must never claim a day summary it did not author.
        "focus_day_write": focus_day_write,
        "focus_day_top_phrases": (None if day_top is None else len(day_top)),
        "coverage_years": sorted(coverage.keys()),
    }
