"""The deterministic core run: normalize -> phrase engine -> ledger -> derived JSON.

Shared by the Stage-1 backfill and rebuild.py (§1.4.8 reproducibility). $0 LLM. Everything
here is a pure function of its input records, so `rebuild` from the raw mirror reproduces the
same derived JSON as the original run.
"""
from __future__ import annotations

from collections import Counter

from . import build, config, instrument_fingerprint, normalize, roster, util
from .phrases import PhraseEngine


def run(records, *, run_id: str, focus_day: str | None = None,
        source_freshness: dict | None = None, generated_at: str | None = None) -> dict:
    generated_at = generated_at or util.now_utc_iso()
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

    # 1.4 The Concordance (R4) — the per-member on-script index, written EVERY run (build dark /
    # release by gate, like day_json["sync_by_party"]); rendering is gated on FEATURES["concordance"],
    # so the flip is a pure release act. Wrapped: a dark feature must never crash the deterministic
    # core (§0 streak invariant) — a failure here skips the artifact, it never breaks RUN A.
    try:
        build.build_concordance(
            statements, ledger, out_dir=config.DERIVED, roster_map=rmap,
            generated_at=generated_at,
        )
    except Exception as e:  # pragma: no cover - streak safety belt, exercised only on a real defect
        print(f"[concordance] skipped (skip-and-log): {e}")

    # 1.5 The Unison + The Void (R2) — symmetric weekly awards, written EVERY run (build dark / release
    # by gate); rendering is gated on FEATURES["awards"], so the flip is a pure release act. Same streak
    # safety belt: a dark feature must never crash RUN A (§0 streak invariant).
    try:
        build.build_awards(
            statements, ledger, out_dir=config.DERIVED, focus_day=focus_day, roster_map=rmap,
            generated_at=generated_at,
        )
    except Exception as e:  # pragma: no cover - streak safety belt, exercised only on a real defect
        print(f"[awards] skipped (skip-and-log): {e}")

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
        "generated_at": generated_at,
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
        "instrument_fingerprint": instrument_fingerprint.build(),
    }
    util.write_json(config.DERIVED / "manifest" / f"{run_id}.json", manifest)
    util.write_json(config.DERIVED / "manifest" / "latest.json", manifest)

    return {"manifest": manifest, "engine": engine, "ledger": ledger, "statements": statements,
            "focus_day": focus_day, "days_present": days_present}
