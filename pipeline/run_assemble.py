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

from pipeline import build, cluster, config, distill, extract, llm, ops, roster, util  # noqa: E402


def _load_taxonomy() -> list[dict]:
    return util.read_json(config.TAXONOMY_FILE, {"topics": []})["topics"]


def _name(bio: str, rmap: dict) -> str:
    return (rmap.get(bio, {}) or {}).get("name") or bio


def _citations(tp: dict, stmt_by_id: dict, rmap: dict, k: int = 3) -> list[dict]:
    """Resolve a verified talking point to >=k real (member, date, URL) citations — one per
    distinct unit (joint/delegation collapses to one, §11 trap 2). This is the citation-or-silence
    receipt the public pages render (Art. XII). Persisted into the day JSON so the site is
    self-contained (no roster re-resolution at render time)."""
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
                      "state": m.get("state"), "date": s.get("published_at"), "url": s.get("url")})
        if len(cites) >= k:
            break
    return cites


def assemble(day: str) -> dict:
    statements = list(util.iter_jsonl(config.STATE / "statements.jsonl.gz"))
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
            top_phrase = {"text": r["ngram"], "members": r["day_peak"],
                          "first_sayer": _name(r["first_seen"]["bioguide"], rmap)}

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
    degraded = any(day_payload[p]["daily_line"]["fallback"] for p in config.COMPOSITE_PARTIES)
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
        "symmetry": {"prompts_sha": report["prompts_sha"], "thresholds_sha": report["thresholds_sha"]},
        "alerts": (["degraded"] if degraded else []),
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=util.product_day())
    args = ap.parse_args()
    res = assemble(args.day)
    dj = res["day_json"]
    print(f"===== RUN B assemble — {args.day} (dry_run={llm.dry_run()}) =====")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
