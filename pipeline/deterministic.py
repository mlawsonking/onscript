"""The deterministic core run: normalize -> phrase engine -> ledger -> derived JSON.

Shared by the Stage-1 backfill and rebuild.py (§1.4.8 reproducibility). $0 LLM. Everything
here is a pure function of its input records, so `rebuild` from the raw mirror reproduces the
same derived JSON as the original run.
"""
from __future__ import annotations

from collections import Counter

from . import (build, config, instrument_fingerprint, normalize, privacy, readiness, roster,
               scan_cache, util)
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


def _sweep_unwritten_days(statements, ledger, discipline, *, focus_day: str, product_day: str,
                          out_dir) -> dict:
    """Write every judgeable day in the lookback window that is still missing its artifacts.

    WHY A SWEEP AND NOT JUST A CLAMPED CURSOR (S73). `readiness.resolve_focus_day` stops the cursor
    running ahead into a day that is not over, which removes the mechanism that skipped 2026-09-08.
    It does not remove the CLASS. Any run that does not happen, any day upstream delivers late, any
    focus that lands on a day two days back still leaves the days in between unwritten, and a
    single-focus-day writer has no way to notice. So the writer stops being a cursor: each run is
    responsible for every judgeable day in the window, not for one day, and a hole becomes a thing
    that heals on the next run instead of a thing that becomes permanent.

    That is also the transition path this change owes its own damage (docs/37 rule 4). Nothing here
    is a migration script or an operator step. The raw mirror is immutable and holds the statements,
    so the first run after deploy simply finds 2026-09-08 unwritten, sees that it holds data, and
    writes it.

    FOUR GUARDS, each of which is a way this could destroy something instead of repairing it:

      1. THE FOCUS DAY IS NOT SWEPT. `build_derived` owns it, has already written it, and owns the
         `allow_final_overwrite` escape hatch that goes with it.
      2. A PUBLISHED DAY IS NEVER REWRITTEN. `util.day_is_final` is the same authority RUN A's own
         write guard consults, so the sweep cannot become a second route to the defect that nulled
         2026-07-12 and 2026-07-18 (docs/23 section 7.5 R-C).
      3. A DATALESS DAY IS NEVER WRITTEN. Below `MIN_PUBLISHABLE` there is no day, only a gap, and
         `select_target_day` already refuses to publish one. Writing an empty record here would
         manufacture the "nothing today" page that guard exists to prevent, and would do it for
         weekends forever.
      4. A BOARD IS ONLY EVER CREATED, NEVER REPLACED. The silence board is the one artifact a
         published day can still be missing, because assemble does not build boards and only the
         focus path ever did. Writing a MISSING board fills a hole; overwriting a present one would
         edit a published day, so the condition is existence and finality does not enter it.

    A day whose record exists and carries phrases is left alone. A day whose record exists, carries
    no phrases and has not been published is rewritten: that is the premature-empty case, where the
    old cursor wrote a day while its statements were still landing (2026-09-09 was written from one
    statement) and nothing would ever have refreshed it. Recomputing it is what makes late data
    arrive on the page instead of being enshrined as a quiet day.

    Deterministic: a function of (statements, ledger, discipline, window, disk). The second pass of
    `rebuild.py` finds the first pass's writes already present and correct, so the derived tree hash
    is unchanged (docs/37 rule 5).

    COST, because the ledger is not small (316,492 entries on 2026-09-09) and `build.day_record`
    walks all of it once. The decision to walk is made from a file existence check and a lane-1
    count, never from the ledger, so a day needing nothing costs nothing. In steady state that is
    zero or one extra walk per run against the three `build_derived` already performs; the ceiling
    is `LOOKBACK_DAYS` walks on the one run that clears a full backlog, and it is a ceiling rather
    than a trend because the window does not grow with the corpus.
    """
    lane1 = config.LANE_BY_SOURCE["press_release"]
    window = [d for d in readiness.sweep_window(focus_day) if d != focus_day and d <= product_day]
    wanted = set(window)
    by_day: dict[str, list] = {}
    for s in statements:
        if s.get("lane") != lane1:
            continue
        d = s.get("published_at")
        if d in wanted:
            by_day.setdefault(d, []).append(s)

    days_dir, board_dir = out_dir / "days", out_dir / "silence"
    records_written: list[str] = []
    boards_written: list[str] = []
    held: list[dict] = []
    failed: list[dict] = []
    for day in window:                                   # oldest -> newest, like every other walk
        day_stmts = by_day.get(day, [])
        if len(day_stmts) < readiness.MIN_PUBLISHABLE:
            continue                                     # guard 3: a gap is not a day
        # Per day, not per sweep. A truncated day file makes `read_json` raise, and one unreadable
        # day must not cost the repair of the other four: the point of the sweep is that holes heal,
        # and a sweep that aborts on the first bad file is a sweep that stops healing the moment it
        # is needed most.
        try:
            is_final = util.day_is_final(day, out_dir)
            existing = util.read_json(days_dir / f"{day}.json", None)
            premature_empty = bool(existing) and existing.get("daily_lines") is None \
                and not existing.get("top_synchronized")
            needs_record = (not is_final) and (existing is None or premature_empty)
            needs_board = not (board_dir / f"{day}.json").exists()
            if is_final and not build.day_record_keys() <= set(existing or {}):
                # Published, yet its record never got the deterministic half. This is the third thing
                # the old cursor cost: a day it skipped was never written by RUN A, so assemble's
                # read-modify-write started from a bare day stub and published a record carrying no
                # `legacy_unvalidated_metrics` at all. Eight published days have that shape. Guard 2
                # forbids repairing them here, so the sweep NAMES them every run rather than passing
                # over them in silence. There is no one-command repair: `run_assemble --day` restores
                # composites but never writes this key, and `scripts/regen_derived.py --force` writes
                # the key but blanks composites, so completing one of these days is a decision about
                # a published record and not a routine operator action (S73, open).
                held.append({"day": day, "reason": "published without its deterministic half"})
            if not (needs_record or needs_board):
                continue
            if needs_record:
                util.write_json(days_dir / f"{day}.json", build.day_record(ledger, discipline, day))
                records_written.append(day)
            if needs_board:
                from . import silence
                silence.build_day_board(day, day_stmts)
                boards_written.append(day)
        except Exception as e:  # pragma: no cover - exercised only by an unreadable artifact
            failed.append({"day": day, "error": str(e)})
            print(f"[sweep] {day} skipped (skip-and-log): {e}")
    return {"window": [window[0], window[-1]] if window else None,
            "records_written": records_written, "boards_written": boards_written,
            "held": held, "failed": failed}


def run(records, *, run_id: str, focus_day: str | None = None,
        source_freshness: dict | None = None, generated_at: str | None = None,
        product_day: str | None = None) -> dict:
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
    # The clock is injected so a caller under a reproducibility claim can freeze it (docs/37 rule 5);
    # production passes nothing and gets the real product day.
    product_day = product_day or util.product_day()
    cursor = readiness.resolve_focus_day(days_present, product_day, explicit=focus_day)
    focus_day = cursor["day"]
    if cursor["clamped"] or cursor["future"]:
        print(f"[focus] {focus_day}: {cursor['reason']}")

    discipline = engine.discipline_index()
    summary = build.build_derived(statements, ledger, discipline, config.DERIVED, focus_day=focus_day)

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

    # S73 backfill sweep. Placed AFTER the focus day's own artifacts, so a defect in the repair of an
    # older day can never cost today its record, and wrapped in the same streak safety belt as every
    # other optional builder: a hole that fails to heal is yesterday's problem, a crashed RUN A is
    # today's. See `_sweep_unwritten_days` for what it will and will not touch.
    sweep = {"skipped": True}
    try:
        sweep = _sweep_unwritten_days(statements, ledger, discipline, focus_day=focus_day,
                                      product_day=product_day, out_dir=config.DERIVED)
        if sweep["records_written"] or sweep["boards_written"]:
            print(f"[sweep] backfilled records={sweep['records_written']} "
                  f"boards={sweep['boards_written']}")
        for row in sweep["held"]:
            print(f"[sweep] {row['day']}: {row['reason']} (not repairable from here; see docs/26 "
                  f"S73, the repair is a decision about a published record)")
    except Exception as e:  # pragma: no cover - streak safety belt, exercised only on a real defect
        sweep = {"error": str(e)}
        print(f"[sweep] skipped (skip-and-log): {e}")

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
        # What the cursor decided and why, and what the sweep repaired behind it. Both are published
        # because a silent skip is exactly how 2026-09-08 was lost: every run that dropped it was
        # GREEN and its manifest recorded only the day it did measure (Article XVI, verified not
        # trusted). Additive; schema_version stays 1.
        "focus_cursor": cursor,
        "day_sweep": sweep,
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
