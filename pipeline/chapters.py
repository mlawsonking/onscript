"""Alexandria chapter layer (§1.3): era-granular composite-voice chapters over the 25-year ledger.

"Map everything deterministically, explain sparsely at era granularity." The deterministic
engine already built the ledger; here we build the grounded INPUTS for each chapter (code-
computed stats + verbatim phrase fragments — no per-statement LLM), the era-chapter prompt is
P4, and the same deterministic verifier gates every generated chapter (only ledger numbers +
verbatim quotes). Cross-era claims are coverage-gated (§1.3 temporal honesty): a thin era gets
a code stub, never generated prose.

Generation itself runs on the Claude SUBSCRIPTION (agentic workflow / claude -p, §1.3 policy),
never the metered API key.
"""
from __future__ import annotations

import json

from . import alexandria, build, config, llm, privacy, roster, util, verify

CHAPTERS_DIR = config.DERIVED / "chapters"
MIN_STATEMENTS = 3000          # coverage gate: below this an era is "too thin to characterize"
MIN_TOP_PHRASES = 3
PRESELECT = 60                 # collapse only the top-N candidates/bucket (was a full O(n^2)
                               # pairwise collapse over 100k+ phrases/congress — the ~80min hang)
TOP_K = 8                      # phrases surfaced per chapter


def _name(bio: str | None, rmap: dict) -> str:
    return (rmap.get(bio or "", {}) or {}).get("name") or (bio or "unknown")


def era_top_phrases(ledger: dict, party: str, start: str, end: str, k: int = 8) -> list[dict]:
    """Top synchronized phrases for a party within [start, end), collapsed to maximal phrases."""
    rows = []
    for ng, e in ledger.items():
        peak = 0
        peak_day = None
        members: set = set()
        for day, d in e["daily"].items():
            if start <= day < end:
                c = d.get(party, 0)
                if c > peak:
                    peak, peak_day = c, day
                    members = set(d.get(f"members_{party}", []))
        if peak >= config.SYNC_MIN_MEMBERS and not privacy.is_suppressed(ng):
            # Art. XIII. Chapters use their own _collapse_top, NOT build.collapse_and_rank, so the
            # chokepoint there does not cover them. Same pre-LLM argument as run_assemble: a chapter
            # is LLM prose, so an unfiltered name here gets laundered into fluent text that the
            # verifier passes (the members really did type it).
            rows.append({"phrase": ng, "peak_members": peak, "peak_day": peak_day,
                         "first_date": e["first_seen"]["date"], "first_bioguide": e["first_seen"]["bioguide"],
                         "_members": frozenset(members)})
    # collapse nested sub-phrases (keep the longest with the same peak-day member set)
    rows.sort(key=lambda r: len(r["phrase"]), reverse=True)
    kept: list[dict] = []
    for r in rows:
        short = f" {r['phrase']} "
        if not any(short in f" {k2['phrase']} " and r["_members"] and r["_members"] <= k2["_members"] for k2 in kept):
            kept.append(r)
    kept.sort(key=lambda r: (r["peak_members"], r["phrase"]), reverse=True)
    out = []
    for r in kept[:k]:
        out.append({"phrase": r["phrase"], "peak_members": r["peak_members"], "peak_day": r["peak_day"],
                    "first_date": r["first_date"], "first_bioguide": r["first_bioguide"]})
    return out


def _members_at(ledger: dict, ng: str, party: str, day: str) -> frozenset:
    """The set of members who used `ng` on its peak `day` for `party` — fetched lazily (only
    for the few top candidates) so the bucket itself never stores 2.77M member frozensets."""
    return frozenset(((ledger.get(ng, {}).get("daily", {}) or {}).get(day, {}) or {})
                     .get(f"members_{party}", []))


def _collapse_top(rows: list[tuple], ledger: dict, party: str, *, members_aware: bool) -> list[tuple]:
    """Members-aware nested-phrase collapse over a BOUNDED candidate set (`rows` already the
    top-PRESELECT by (peak,len)). Keeps a phrase unless it's a sub-phrase of an already-kept
    longer phrase covering a superset of its members. Stops at TOP_K. O(PRESELECT·TOP_K)."""
    kept: list[tuple] = []          # (ng, v, members)
    for ng, v in rows:
        mem = _members_at(ledger, ng, party, v["day"]) if members_aware else frozenset()
        short = f" {ng} "
        nested = any(short in f" {k2} " and (not members_aware or (mem and mem <= km))
                     for k2, _kv, km in kept)
        if not nested:
            kept.append((ng, v, mem))
            if len(kept) >= TOP_K:
                break
    return kept


def build_era_inputs(ledger: dict, coverage: dict) -> list[dict]:
    """One chapter input per (Congress, party): code-computed stats + verbatim phrase fragments.
    SINGLE pass buckets each phrase's peak by Congress×party storing only {peak, day} (member
    sets fetched lazily for the ~8 survivors — not stored for all 2.77M phrases), with
    day->congress memoized, and the nested-collapse bounded to the top PRESELECT candidates.
    The prior version stored a frozenset per entry (~18GB, paged to disk) and ran a full O(n^2)
    collapse over 100k+ phrases/congress — an ~80-minute hang."""
    from collections import defaultdict
    rmap = roster.load()
    day_cong: dict[str, int] = {}
    parties = config.COMPOSITE_PARTIES
    smin = config.SYNC_MIN_MEMBERS
    bucket: dict[tuple, dict] = defaultdict(dict)  # (congress, party) -> ngram -> {peak, day}
    for ng, e in ledger.items():
        for day, d in e["daily"].items():
            cong = day_cong.get(day)
            if cong is None:
                cong = util.congress_for_date(day)
                day_cong[day] = cong
            for party in parties:
                c = d.get(party, 0)
                if c >= smin:
                    b = bucket[(cong, party)]
                    cur = b.get(ng)
                    if cur is None or c > cur["peak"]:
                        b[ng] = {"peak": c, "day": day}
    inputs: list[dict] = []
    for n in range(alexandria.FIRST_CONGRESS, alexandria.LAST_CONGRESS + 1):
        start, end = alexandria.congress_range(n)
        years = [str(y) for y in range(int(start[:4]), int(end[:4]))]
        for party in parties:
            stmts = sum((coverage.get(y, {}) or {}).get(party, 0) for y in years)
            rows = sorted(bucket.get((n, party), {}).items(),
                          key=lambda kv: (kv[1]["peak"], len(kv[0])), reverse=True)[:PRESELECT]
            kept = _collapse_top(rows, ledger, party, members_aware=True)
            top = []
            for ng, v, _mem in kept:
                fs = ledger[ng]["first_seen"]
                top.append({"phrase": ng, "peak_members": v["peak"], "peak_day": v["day"],
                            "first_date": fs.get("date"), "first_sayer": _name(fs.get("bioguide"), rmap)})
            inputs.append({
                "id": f"era-{n}-{party}", "kind": "era", "congress": n, "party": party,
                "label": f"{n}th Congress ({start[:4]}–{end[:4]})",
                "stats": {"statements": stmts, "top_phrases": top,
                          "coverage": "adequate" if (stmts >= MIN_STATEMENTS and len(top) >= MIN_TOP_PHRASES) else "thin"},
                "fragments": [t["phrase"] for t in top],
                "sufficient": stmts >= MIN_STATEMENTS and len(top) >= MIN_TOP_PHRASES,
            })
    return inputs


def build_monthly_inputs(ledger: dict, *, min_peak: int = 5, min_phrases: int = 3,
                         start_month: str = "2013-01") -> list[dict]:
    """One chapter input per (month, party) from ~2013 on (before that the corpus is too thin).
    Single ledger pass buckets each phrase's peak by (party, month) — fast. Coverage-gated:
    a month needs >= min_phrases phrases at >= min_peak members to be generated (else skipped)."""
    from collections import defaultdict
    rmap = roster.load()
    bucket: dict[tuple, dict] = defaultdict(dict)  # (party, month) -> ngram -> {peak, day, members}
    for ng, e in ledger.items():
        for day, d in e["daily"].items():
            month = day[:7]
            if month < start_month:
                continue
            for party in config.COMPOSITE_PARTIES:
                c = d.get(party, 0)
                if c >= config.SYNC_MIN_MEMBERS and not privacy.is_suppressed(ng):
                    # Art. XIII: the month lane uses _collapse_top, not build.collapse_and_rank, so
                    # it needs its own guard. Filtering here keeps it out of both `stats.top_phrases`
                    # and the `fragments` grounding list the chapter voice quotes from.
                    cur = bucket[(party, month)].get(ng)
                    if cur is None or c > cur["peak"]:
                        bucket[(party, month)][ng] = {"peak": c, "day": day}
    inputs: list[dict] = []
    for (party, month), phrases in bucket.items():
        rows = sorted(phrases.items(),
                      key=lambda kv: (kv[1]["peak"], len(kv[0])), reverse=True)[:PRESELECT]
        kept = _collapse_top(rows, ledger, party, members_aware=False)  # substring-only, bounded
        top = []
        for ng, v, _mem in kept:
            fs = ledger[ng]["first_seen"]
            top.append({"phrase": ng, "peak_members": v["peak"], "peak_day": v["day"],
                        "first_date": fs.get("date"), "first_sayer": _name(fs.get("bioguide"), rmap)})
        sufficient = sum(1 for t in top if t["peak_members"] >= min_peak) >= min_phrases
        inputs.append({"id": f"month-{month}-{party}", "kind": "month", "month": month, "party": party,
                       "label": month, "stats": {"top_phrases": top}, "fragments": [t["phrase"] for t in top],
                       "sufficient": sufficient})
    inputs.sort(key=lambda i: (i["month"], i["party"]))
    return inputs


def stub_text(inp: dict) -> str:
    s = inp["stats"].get("statements")
    vol = f"{s} statements in our corpus, " if s is not None else ""
    return (f"The record of the {inp['party']} caucus in {inp['label']} is too thin to "
            f"characterize: {vol}with no coordinated phrasing above threshold. "
            f"Our corpus begins in 2001; coverage by year is shown on the Archive Coverage page.")


def verify_chapter(inp: dict, text: str) -> dict:
    """Deterministic gate (§6.3 reused): numbers must be in STATS (or the era label — e.g. the
    "119" in "119th Congress"); quotes must be verbatim phrases (surrounding punctuation ok)."""
    stats_blob = json.dumps(inp["stats"], ensure_ascii=False) + " " + inp.get("label", "")
    ok_num, offending = verify.numbers_whitelisted(text, stats_blob)
    ok_q, off_q = verify.quotes_grounded(text, inp["fragments"])
    reasons = []
    if not ok_num:
        reasons.append(f"un-whitelisted numbers: {sorted(offending)}")
    if not ok_q:
        reasons.append(f"un-grounded quotes: {off_q}")
    return {"passed": len(reasons) == 0, "reasons": reasons}


def write_inputs(inputs: list[dict]) -> None:
    util.write_json(config.DERIVED / "chapter_inputs.json", inputs)


def finalize_chapters(inputs: list[dict], generated: dict[str, str]) -> dict:
    """generated: id -> chapter text (from the agentic workflow). Verify + write; stubs for thin eras."""
    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    published = failed = stubbed = 0
    prompt = llm.load_prompt("P4") if "P4" in getattr(llm, "_PROMPT_FILES", {}) else None
    report = []
    for inp in inputs:
        cid = inp["id"]
        if not inp["sufficient"]:
            text, gen, ver = stub_text(inp), "code_stub", {"passed": True, "reasons": []}
            stubbed += 1
        else:
            text = (generated.get(cid) or "").strip()
            if not text:
                report.append({"id": cid, "status": "missing"}); failed += 1; continue
            ver = verify_chapter(inp, text)
            gen = "subscription_agent"
            if ver["passed"]:
                published += 1
            else:
                failed += 1
        rec = {"schema_version": 1, "id": cid, "kind": inp["kind"], "congress": inp.get("congress"),
               "party": inp["party"], "label": inp["label"], "text": text, "generator": gen,
               "prompt_version": (prompt or {}).get("version", "1.0"), "verifier": ver,
               "stats": inp["stats"]}
        util.write_json(CHAPTERS_DIR / f"{cid}.json", rec)
        report.append({"id": cid, "status": "published" if ver["passed"] else "verify_failed", "gen": gen})
    summary = {"schema_version": 1, "generated_at": util.now_utc_iso(),
               "published": published, "stubbed": stubbed, "failed": failed, "report": report}
    util.write_json(CHAPTERS_DIR / "index.json", summary)
    return summary
