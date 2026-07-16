"""RUN B "assemble" (§2): extractions -> clusters -> Daily Lines -> VERIFY -> derived + symmetry.

Self-sufficient given the state RUN A leaves (statements + ledger): it extracts the focus
day's statements on demand (idempotent via the extraction cache), clusters per party, distills
+ verifies the two Daily Lines, merges them into the day's derived JSON, and publishes the
nightly symmetry audit. $0 in dry-run.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import boilerplate, brief, build, cluster, config, distill, extract, llm, ops, readiness, roster, util  # noqa: E402


def _load_taxonomy() -> list[dict]:
    return util.read_json(config.TAXONOMY_FILE, {"topics": []})["topics"]


def _name(bio: str, rmap: dict) -> str:
    return (rmap.get(bio, {}) or {}).get("name") or bio


def _citations(tp: dict, stmt_by_id: dict, rmap: dict, k: int = 3) -> list[dict]:
    """Resolve a verified talking point to >=k real (member, date, URL) citations — one per
    distinct unit (joint/delegation collapses to one, §11 trap 2). This is the citation-or-silence
    receipt the public pages render (Art. XII). Persisted into the day JSON so the site is
    self-contained (no roster re-resolution at render time)."""
    # C-ii: bind each citation to the specific fragment THAT member's statement contributed, so a
    # displayed quote sits next to the member who said it and their .gov link — a reader can click and
    # verify that exact quote, instead of a decoupled quote/citation pair that points at unrelated
    # topics. §Session-7.
    frag_by_stmt: dict = {}
    for f in tp.get("fragments", []):
        if f.get("statement") and f.get("text") and f["statement"] not in frag_by_stmt:
            frag_by_stmt[f["statement"]] = f["text"]
    cites, seen = [], set()
    for sid in tp.get("statements", []):
        s = stmt_by_id.get(sid)
        if not s:
            continue
        m = s.get("member") or {}
        unit = s.get("joint_group") or m.get("bioguide")
        if not unit or unit in seen:
            continue
        seen.add(unit)
        cites.append({"member": _name(m.get("bioguide"), rmap), "party": m.get("party"),
                      "state": m.get("state"), "date": s.get("published_at"), "url": s.get("url"),
                      "quote": frag_by_stmt.get(sid)})
        if len(cites) >= k:
            break
    return cites


def _is_final(day: str) -> bool:
    """Was this day already published? A final day is never re-assembled (and never skipped). The
    readiness gate uses this to walk the backlog oldest-first. §deploy-hardening.

    BACK-COMPAT: manifests written before the readiness gate existed have no `final` field. Their mere
    existence means the day WAS published, so default to True — otherwise the gate would treat all of
    history as pending and re-assemble old days on its first run."""
    m = util.read_json(config.DERIVED / "manifest" / f"assemble-{day}.json", {})
    return bool(m) and bool(m.get("final", True))


def _counts_by_day(statements) -> dict:
    from collections import Counter
    return dict(Counter(s["published_at"] for s in statements if s.get("lane") == 1))


def assemble(day: str, statements=None, *, readiness_info=None, forced=False) -> dict:
    statements = statements if statements is not None else list(util.iter_jsonl(config.STATE / "statements.jsonl.gz"))
    ledger = util.read_json(config.STATE / "ledger.json", {})
    if not statements or not ledger:
        raise SystemExit("no state — run RUN A (scripts/backfill_stage1.py or run_collect) first")
    taxonomy = _load_taxonomy()
    rmap = roster.load()
    sync = set(ledger)

    focus = [s for s in statements if s["published_at"] == day and s.get("lane") == 1]
    extractions, extract_cost = extract.extract(focus, sync, taxonomy)

    stmt_by_id = {s["id"]: s for s in statements}
    per_party_llm: dict[str, dict] = {}
    day_payload: dict[str, dict] = {}

    # Real Sonnet voice gate + STRICT pre-flight budget check (voice-wiring). The voice fires only
    # when a key is present (not dry_run), the LLM_VOICE_ENABLED switch is on, AND month-to-date spend
    # leaves room under the code ceiling (config.LLM_MONTHLY_CEILING_USD). Otherwise: deterministic, $0.
    projected = 2 * llm.estimate_cost(llm.VOICE_MODEL, 3000, 400, batched=False)  # ~2 voice calls, generous
    voice_state = ops.voice_budget_state(day, projected)
    allow_llm_voice = config.llm_voice_enabled() and voice_state != "halt"

    for party in config.COMPOSITE_PARTIES:
        party_stmts = [s for s in focus if (s.get("member") or {}).get("party") == party]
        annotated = []
        for s in party_stmts:
            for f in extractions.get(s["id"], {}).get("fragments", []):
                annotated.append({**f, "statement": s["id"], "joint_group": s.get("joint_group"),
                                  "bioguide": (s.get("member") or {}).get("bioguide")})
        tps = cluster.cluster_day(party, day, annotated)

        # verify talking points (>=3 distinct members + verbatim fragments); drop failures
        published, dropped = [], 0
        from pipeline import verify
        for tp in tps:
            ok, _ = verify.verify_talking_point(tp, stmt_by_id)
            # C-i: a coherent quorum (>=3 members, verbatim) is not enough — the BINDING PHRASE must
            # be a real talking point, not connective glue. A weak label ("and the trump
            # administration's") means the members share grammar, not a message, and its receipts
            # would point at unrelated topics. Suppress it (never published, never narrated).
            if ok and boilerplate.is_weak_label(tp.get("label", "")):
                ok = False
            if ok:
                tp["citations"] = _citations(tp, stmt_by_id, rmap)  # >=3 real (member,date,url)
                published.append(tp)
            else:
                dropped += 1

        # top synchronized phrase for the party that day (with first-sayer name)
        top_rows = [r for r in build.top_synchronized(ledger, day, k=5) if r["party"] == party]
        top_phrase = None
        if top_rows:
            r = top_rows[0]
            fsb = (r.get("first_seen") or {}).get("bioguide")
            fsm = rmap.get(fsb) or {}
            top_phrase = {"text": r["ngram"], "members": r["day_peak"]}
            # Expose a first-sayer ONLY when the roster fully resolves it (name + party + state).
            # first_seen is corpus-wide, so the bioguide is often a former member absent from the
            # current roster — in that case omit it entirely, so the voice has nothing to fabricate
            # (the verifier does not ground names/party/state). §Session-7 (#4). Present => the voice
            # tags it "Name (R-SC)"; may be the OTHER party (real cross-party origination).
            if fsm.get("party") and fsm.get("state") and fsm.get("name"):
                top_phrase.update({"first_sayer": _name(fsb, rmap),
                                   "first_sayer_party": fsm["party"], "first_sayer_state": fsm["state"]})

        distillation = distill.daily_line(party, day, party_stmts, published, top_phrase, stmt_by_id,
                                          allow_llm_voice=allow_llm_voice)

        # REAL token usage from the voice call (0 when the deterministic voice was used) — the
        # symmetry audit + cost ledger report actual spend, never an estimate. §voice-wiring.
        usage = distillation.get("usage") or {}
        per_party_llm[party] = {
            "tokens_in": int(usage.get("tokens_in", 0)), "tokens_out": int(usage.get("tokens_out", 0)),
            "claims_published": len(published), "claims_dropped": dropped,
        }
        day_payload[party] = {"daily_line": distillation, "talking_points": published}

    # STRICT budget accounting FIRST — persist the real spend to the month ledger BEFORE any risky
    # day-JSON write, so a write failure can never lose a billed call. Cost each run at its OWN day's
    # Sonnet rate (date-aware). The governor reads true month-to-date; the $10 Console cap is the
    # last-line backstop. §voice-wiring (LOW-7b, MEDIUM-5).
    day_cost = round(sum(llm.estimate_cost(llm.VOICE_MODEL, per_party_llm[p]["tokens_in"],
                                           per_party_llm[p]["tokens_out"], batched=False, on_date=day)
                         for p in config.COMPOSITE_PARTIES), 6)
    if not llm.dry_run():
        ops.record_cost(day, day_cost, model=llm.VOICE_MODEL,
                        tokens_in=sum(per_party_llm[p]["tokens_in"] for p in config.COMPOSITE_PARTIES),
                        tokens_out=sum(per_party_llm[p]["tokens_out"] for p in config.COMPOSITE_PARTIES))
    month_to_date = ops.month_to_date_usd(day, include_day=True)
    governor = ops.budget_governor(month_to_date)

    # merge Daily Lines into the day's derived JSON (deterministic top phrases already there)
    day_file = config.DERIVED / "days" / f"{day}.json"
    day_json = util.read_json(day_file, {"day": day})
    day_json["daily_lines"] = {p: day_payload[p]["daily_line"] for p in config.COMPOSITE_PARTIES}
    day_json["talking_points"] = {p: day_payload[p]["talking_points"] for p in config.COMPOSITE_PARTIES}
    day_json["top_synchronized"] = build.top_synchronized(ledger, day, k=20)
    util.write_json(day_file, day_json)

    freshness = {"note": "assemble stage; freshness measured in RUN A"}
    # `forced` = the readiness gate waited out MAX_WAIT_DAYS and upstream never filled: we publish what
    # we have rather than leave a hole in the series, but it is honestly degraded. §deploy-hardening.
    degraded = forced or any(day_payload[p]["daily_line"]["fallback"] for p in config.COMPOSITE_PARTIES)
    report = ops.symmetry_report(day, statements, per_party_llm, freshness=freshness, degraded=degraded)

    manifest = {
        "schema_version": 1, "run_id": f"assemble-{date.today().isoformat()}", "kind": "assemble",
        "generated_at": util.now_utc_iso(), "day": day,
        "dry_run": llm.dry_run(), "extract_cost": extract_cost,
        "per_party_llm": per_party_llm, "daily_voice_cost_usd": day_cost,
        "llm_voice_enabled": config.llm_voice_enabled(),
        "voice_used": bool(allow_llm_voice and not llm.dry_run()),
        "voice_budget_state": voice_state, "month_to_date_usd": month_to_date,
        "governor_state": governor, "degraded": degraded,
        # §deploy-hardening: this day cleared the readiness gate (or waited out MAX_WAIT and was
        # finalized degraded). final=True means PUBLISHED — never re-assembled, and never skipped.
        "final": True, "forced_finalize": forced, "readiness": readiness_info,
        "symmetry": {"prompts_sha": report["prompts_sha"], "thresholds_sha": report["thresholds_sha"]},
        "alerts": (["degraded"] if degraded else []) + (["forced-finalize: upstream never filled"] if forced else []),
    }
    util.write_json(config.DERIVED / "manifest" / f"assemble-{day}.json", manifest)
    # Pointer to the day THIS run built — post_bluesky reads it (not collect's focus_day), which
    # fixes the Session-4 day-selection no-op. Posting targets exactly what assemble published.
    util.write_json(config.DERIVED / "manifest" / "assemble-latest.json",
                    {"day": day, "generated_at": util.now_utc_iso(), "run_id": manifest["run_id"]})
    if degraded or governor != "nominal" or voice_state in ("warn", "halt"):
        ops.ntfy("OnScript assemble",
                 f"day={day} governor={governor} voice={voice_state} "
                 f"mtd=${month_to_date:.2f} degraded={degraded}",
                 priority="high" if (degraded or voice_state == "halt") else "default")
    return {"manifest": manifest, "day_json": day_json, "report": report}


def _owners_brief() -> None:
    """07-OPS §3: "RUN B appends a Monday ntfy". Dark until FEATURES["owners_brief"] flips.

    Two deliberate placements:
      * **skip-and-log** — the workflow runs this step WITHOUT `|| true` (unlike the posting leg), so
        an exception here would fail RUN B and break the streak. The brief is a report ABOUT the
        machine; it must never be able to take the machine down (CLAUDE.md: never crash the run).
      * **called from main(), not assemble()** — main() returns early when no day is ready, and a
        Monday where nothing assembled is precisely the Monday the owner needs a brief (streak would
        be RED). Wiring it inside assemble() would silence it exactly when it matters most.

    The brief's day (`brief.brief_day()`) is the day it RUNS, not the day being assembled.
    """
    try:
        day = brief.brief_day()
        r = brief.send_brief(day)
        print(f"[brief] {day}: {r['brief']['headline']} — {r.get('reason') or ('sent' if r['sent'] else 'not sent')}")
    except Exception as e:  # pragma: no cover - the whole point is that nothing escapes
        print(f"[brief] skipped (skip-and-log): {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=None,
                    help="explicit day (manual/backfill) — bypasses the readiness gate")
    args = ap.parse_args()

    # §deploy-hardening (2026-07-16): do NOT blindly assemble product_day(). If the mirror is still
    # landing, publishing a thin day and then advancing product_day() would SKIP that day forever —
    # a permanent hole in the time-series. Instead: assemble the oldest not-yet-final day that is
    # READY (oldest-first, so the series fills chronologically); if none is ready, NO-OP at $0 and let
    # a later retry cron pick it up the moment upstream fills. A day that never fills is force-
    # finalized after MAX_WAIT_DAYS so a quiet holiday can never livelock the streak.
    statements = list(util.iter_jsonl(config.STATE / "statements.jsonl.gz"))
    if args.day:
        day, forced, sel = args.day, False, {"reason": "explicit --day override", "readiness": None}
    else:
        sel = readiness.select_target_day(_counts_by_day(statements), _is_final, util.product_day())
        if sel["day"] is None:
            print(f"===== RUN B assemble — NO-OP (no cluster, no distill, no API spend) =====")
            print(sel["reason"])
            _owners_brief()      # a Monday with nothing to assemble is a Monday that needs a brief
            return 0
        day, forced = sel["day"], sel["forced"]
        print(f"[readiness] target={day} forced={forced} :: {sel['reason']}")

    res = assemble(day, statements, readiness_info=sel.get("readiness"), forced=forced)
    dj = res["day_json"]
    print(f"===== RUN B assemble — {day} (dry_run={llm.dry_run()}) =====")
    for p in config.COMPOSITE_PARTIES:
        dl = dj["daily_lines"][p]
        tps = dj["talking_points"][p]
        print(f"\n[{p}] talking points published: {len(tps)}  verifier_passed={dl['verifier']['passed']}  fallback={dl['fallback']}")
        print(f"[{p}] DAILY LINE: {dl['composite']}")
        if tps:
            receipts = " | ".join('"' + f["text"] + '"' for f in tps[0]["fragments"][:3])
            print(f"[{p}] top cluster: {tps[0]['member_count']} members — receipts: {receipts}")
    r = res["report"]
    print("\n----- symmetry audit -----")
    for p in config.COMPOSITE_PARTIES:
        pp = r["parties"][p]
        print(f"  {p}: {pp['statements_ingested']} statements, {pp['members_covered']}/{pp['caucus_size']} members "
              f"({pp['coverage_pct']}%), claims {pp['claims_published']} published / {pp['claims_dropped']} dropped")
    print(f"  prompts_sha={list(r['prompts_sha'].values())[0][:12]}…  thresholds_sha={r['thresholds_sha'][:12]}… (identical both parties)")
    _owners_brief()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
