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

    for party in config.COMPOSITE_PARTIES:
        party_stmts = [s for s in focus if (s.get("member") or {}).get("party") == party]
        annotated = []
        for s in party_stmts:
            for f in extractions.get(s["id"], {}).get("fragments", []):
                annotated.append({**f, "statement": s["id"], "bioguide": (s.get("member") or {}).get("bioguide")})
        tps = cluster.cluster_day(party, day, annotated)

        # verify talking points (>=3 distinct members + verbatim fragments); drop failures
        published, dropped = [], 0
        from pipeline import verify
        for tp in tps:
            ok, _ = verify.verify_talking_point(tp, stmt_by_id)
            if ok:
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

        distillation = distill.daily_line(party, day, party_stmts, published, top_phrase, stmt_by_id)

        # tokens telemetry (what the real Sonnet voice call would cost; Sonnet 5 budget +30% tokens)
        tin = int(llm.approx_tokens(str(distillation.get("stats", ""))) * 1.3) + 1500
        per_party_llm[party] = {
            "tokens_in": tin, "tokens_out": 400,
            "claims_published": len(published), "claims_dropped": dropped,
        }
        day_payload[party] = {"daily_line": distillation, "talking_points": published}

    # merge Daily Lines into the day's derived JSON (deterministic top phrases already there)
    day_file = config.DERIVED / "days" / f"{day}.json"
    day_json = util.read_json(day_file, {"day": day})
    day_json["daily_lines"] = {p: day_payload[p]["daily_line"] for p in config.COMPOSITE_PARTIES}
    day_json["talking_points"] = {p: day_payload[p]["talking_points"] for p in config.COMPOSITE_PARTIES}
    day_json["top_synchronized"] = build.top_synchronized(ledger, day, k=20)
    util.write_json(day_file, day_json)

    # budget: extraction (all-corpus, one-time in backfill) + 2 voice calls/day
    voice_cost = sum(llm.estimate_cost(llm.VOICE_MODEL, per_party_llm[p]["tokens_in"],
                                       per_party_llm[p]["tokens_out"], batched=True)
                     for p in config.COMPOSITE_PARTIES)
    day_cost = round(voice_cost, 4)  # extraction is amortized/one-time; daily marginal = the 2 voice calls
    governor = ops.budget_governor(day_cost * 22)  # rough monthly projection at in-session cadence

    freshness = {"note": "assemble stage; freshness measured in RUN A"}
    degraded = any(day_payload[p]["daily_line"]["fallback"] for p in config.COMPOSITE_PARTIES)
    report = ops.symmetry_report(day, statements, per_party_llm, freshness=freshness, degraded=degraded)

    manifest = {
        "schema_version": 1, "run_id": f"assemble-{date.today().isoformat()}", "kind": "assemble",
        "generated_at": util.now_utc_iso(), "day": day,
        "dry_run": llm.dry_run(), "extract_cost": extract_cost,
        "per_party_llm": per_party_llm, "daily_voice_cost_usd": day_cost,
        "governor_state": governor, "degraded": degraded,
        "symmetry": {"prompts_sha": report["prompts_sha"], "thresholds_sha": report["thresholds_sha"]},
        "alerts": (["degraded"] if degraded else []),
    }
    util.write_json(config.DERIVED / "manifest" / f"assemble-{day}.json", manifest)
    if degraded or governor != "nominal":
        ops.ntfy("OnScript assemble", f"day={day} governor={governor} degraded={degraded}",
                 priority="high" if degraded else "default")
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
