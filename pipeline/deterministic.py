"""The deterministic core run: normalize -> phrase engine -> ledger -> derived JSON.

Shared by the Stage-1 backfill and rebuild.py (§1.4.8 reproducibility). $0 LLM. Everything
here is a pure function of its input records, so `rebuild` from the raw mirror reproduces the
same derived JSON as the original run.
"""
from __future__ import annotations

from collections import Counter

from . import build, config, normalize, roster, util
from .phrases import PhraseEngine


def run(records, *, run_id: str, focus_day: str | None = None, source_freshness: dict | None = None) -> dict:
    rmap = roster.load()
    statements = normalize.normalize_records(records, run_id=run_id, roster=rmap)
    norm_stats = getattr(normalize.normalize_records, "last_stats", {})

    engine = PhraseEngine()
    ledger = engine.build(statements, progress=len(statements) > 100_000)  # Alexandria-scale progress
    fin_stats = engine.last_finalize_stats

    # Persist state (Release-asset-destined, gitignored).
    util.write_jsonl(config.STATE / "statements.jsonl.gz", statements)
    util.write_json(config.STATE / "ledger.json", ledger, indent=None)

    days_present = sorted({s["published_at"] for s in statements})
    focus_day = focus_day or (days_present[-1] if days_present else util.product_day())

    summary = build.build_derived(statements, ledger, engine.discipline_index(), config.DERIVED, focus_day=focus_day)

    per_party = {}
    for p in config.ALL_PARTIES:
        stmts = [s for s in statements if (s.get("member") or {}).get("party") == p]
        per_party[p] = {
            "statements_in": len(stmts),
            "members_covered": len({(s.get("member") or {}).get("bioguide") for s in stmts if (s.get("member") or {}).get("bioguide")}),
        }

    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "kind": "deterministic",
        "generated_at": util.now_utc_iso(),
        "focus_day": focus_day,
        "days_present": [days_present[0], days_present[-1]] if days_present else None,
        "source_freshness": source_freshness or {},
        "normalize": norm_stats,
        "phrase_engine": fin_stats,
        "per_party": per_party,
        "derived": summary,
        "spend_estimate_usd": 0.0,
        "governor_state": "nominal",
        "alerts": [],
    }
    util.write_json(config.DERIVED / "manifest" / f"{run_id}.json", manifest)
    util.write_json(config.DERIVED / "manifest" / "latest.json", manifest)

    return {"manifest": manifest, "engine": engine, "ledger": ledger, "statements": statements,
            "focus_day": focus_day, "days_present": days_present}
