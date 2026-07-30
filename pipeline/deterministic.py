"""The deterministic core run: normalize -> phrase engine -> ledger -> derived JSON.

Shared by the Stage-1 backfill and rebuild.py (§1.4.8 reproducibility). $0 LLM. Everything
here is a pure function of its input records, so `rebuild` from the raw mirror reproduces the
same derived JSON as the original run.
"""
from __future__ import annotations

from collections import Counter

from . import build, config, instrument_fingerprint, normalize, privacy, roster, scan_cache, util
from .phrases import PhraseEngine


def _ledger_detail() -> str:
    """The span-scan share of the ledger build, as its own greppable field.

    The W4 person-span scan is the one component of this stage that grew without anyone watching
    (the 2026-07-28/29 collect timeouts). Publishing its share every run means the next growth
    arrives as a number in the log rather than as a workflow ceiling."""
    stats = privacy.span_stats()
    return (f"span_scan_s={stats['person_spans_s']:.1f} "
            f"span_scan_calls={int(stats['person_spans_calls'])} "
            f"admitted_form_s={stats['admitted_form_s']:.1f} "
            f"admitted_form_scans={int(stats['admitted_form_scans'])}")


def run(records, *, run_id: str, focus_day: str | None = None,
        source_freshness: dict | None = None, generated_at: str | None = None) -> dict:
    generated_at = generated_at or util.now_utc_iso()
    rmap = roster.load()
    # The corpus is append-only, so a statement proven to contain no admitted form stays proven
    # until the instrument moves. Active for the whole run: every _doc_ngrams caller downstream of
    # the engine walks the same texts. Nothing is served that was not computed under this exact
    # form list, salt and entity version (the key commits to all three).
    print(f"[scan-cache] {privacy.activate_scan_cache()}")
    with util.stage_timer("normalize"):
        statements = normalize.normalize_records(records, run_id=run_id, roster=rmap)
    norm_stats = getattr(normalize.normalize_records, "last_stats", {})

    engine = PhraseEngine()
    privacy.reset_span_stats()
    with util.stage_timer("ledger_build", detail_fn=_ledger_detail):
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

    # 1.2 The absence map (silence board + its mirror The Void), written EVERY run (build dark / release
    # by gate, like concordance.json and awards.json); rendering is gated on FEATURES["silence_board"],
    # so the flip is a pure release act. Built BEFORE build_awards so The Void, which reads the boards on
    # disk (config.DERIVED/silence), can include today's. LANE 1 ONLY: the board's per-party counts are a
    # cross-party comparison (Article III), so only press-release (Lane-1) statements feed corpus_topics;
    # a Lane-2 record (Bluesky/floor) must never enter a party count. The GDELT news baseline is itself
    # Lane 2 and only GATES topic salience inside build_day_board (never a party denominator). Same streak
    # safety belt: a dark feature must never crash RUN A (§0 streak invariant), and a missing GDELT
    # baseline writes an UNSCORED board rather than failing (a gap is never a silence).
    try:
        from . import silence
        lane1_day = [s for s in statements
                     if s.get("published_at") == focus_day and s.get("lane") == config.LANE_BY_SOURCE["press_release"]]
        silence.build_day_board(focus_day, lane1_day)
    except Exception as e:  # pragma: no cover - streak safety belt, exercised only on a real defect
        print(f"[silence] skipped (skip-and-log): {e}")

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
        # Additive (schemas stay compatible). Manifests are already excluded from the determinism
        # hash in rebuild.py because they carry run-local values, so run-local seconds are at home
        # here and nowhere else: this must never reach an artifact under a reproducibility claim.
        "stage_timings_s": util.stage_timings(),
        "span_scan": privacy.span_stats(),
        "instrument_fingerprint": instrument_fingerprint.build(),
    }
    util.write_json(config.DERIVED / "manifest" / f"{run_id}.json", manifest)
    util.write_json(config.DERIVED / "manifest" / "latest.json", manifest)

    # Persisted last, so the file records the verdicts of a run that got all the way here. The
    # write is best effort by construction: a run that cannot persist its verdicts is a correct
    # run that rescans tomorrow.
    print(f"[scan-cache] {privacy.flush_scan_cache()}")
    scan_cache.deactivate()

    return {"manifest": manifest, "engine": engine, "ledger": ledger, "statements": statements,
            "focus_day": focus_day, "days_present": days_present}
