"""Tests for the v2 Build Program dark shelf (docs/11). Every feature: built + verified + registered
`built/verified/UNRELEASED` behind the FEATURES flag. These lock the render logic and the build-dark
gate (nothing renders publicly until Michael flips the flag)."""
import contextlib
import datetime as _dt
import json
import sys
import tempfile
import unittest.mock as _mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import brief, config, gdelt, ops, silence, site  # noqa: E402

REAL_DERIVED = Path(__file__).resolve().parent.parent / "data" / "derived"


@contextlib.contextmanager
def _released(flag: str):
    """Temporarily flip a dark feature ON, to test the behaviour BEHIND the release gate."""
    config.FEATURES[flag] = True
    try:
        yield
    finally:
        config.FEATURES[flag] = False


@contextlib.contextmanager
def _derived_fixture(**files):
    """Run against a SYNTHETIC derived tree, with ntfy stubbed.

    Tests must never write into the real data/derived: assemble.yml does `git add data/derived`, so a
    test artifact would be COMMITTED — and one claiming a dark feature is "released" would be a
    fabricated receipt in a repo whose entire thesis is honest receipts. Stubbing ntfy also stops the
    suite from pushing to Michael's live phone topic when NTFY_TOPIC happens to be exported."""
    real_derived, real_ntfy, sent = config.DERIVED, ops.ntfy, []
    with tempfile.TemporaryDirectory() as d:
        config.DERIVED = Path(d)
        ops.ntfy = lambda *a, **k: (sent.append((a, k)), {"sent": True})[1]
        try:
            for rel, obj in files.items():
                f = config.DERIVED / rel.replace("__", "/")
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(json.dumps(obj), encoding="utf-8")
            yield sent
        finally:
            config.DERIVED, ops.ntfy = real_derived, real_ntfy


# --- 1.1 The Archive -----------------------------------------------------------------------------
def test_archive_index_renders_both_parties_and_fingerprints():
    chapters = [
        {"kind": "era", "congress": 119, "party": "D", "label": "119th", "id": "era-119-D",
         "stats": {"statements": 100, "top_phrases": [
             {"phrase": "birthright citizenship", "peak_members": 30, "first_date": "2025-06-30"}]},
         "verifier": {"passed": True}},
        {"kind": "era", "congress": 119, "party": "R", "label": "119th", "id": "era-119-R",
         "stats": {"statements": 80, "top_phrases": [
             {"phrase": "the southern border", "peak_members": 25, "first_date": "2025-02-01"}]},
         "verifier": {"passed": True}},
    ]
    body = site.archive_index_body(chapters)
    assert "Era fingerprints" in body
    assert "birthright citizenship" in body and "the southern border" in body   # both parties
    assert "pill D" in body and "pill R" in body


def test_chapter_page_renders_essay_phrase_table_and_verifier_note():
    ch = {"kind": "era", "label": "110th", "party": "R", "id": "era-110-R", "generator": "g",
          "prompt_version": "era.v1", "text": "We spoke of energy.\nAnd of war.",
          "verifier": {"passed": True}, "stats": {"statements": 50, "top_phrases": [
              {"phrase": "energy independence", "peak_members": 14, "peak_day": "2007-08-03",
               "first_date": "2007-08-03", "first_sayer": "Sen. X"}]}}
    body = site.chapter_page_body(ch)
    assert "We spoke of energy." in body and "And of war." in body        # essay paragraphs
    assert "energy independence" in body and "Sen. X" in body             # phrase table + receipts
    assert "verifier: passed" in body                                     # the gate is disclosed


def test_archive_loader_is_the_verifier_gate():
    """The release gate is 'zero uncited fragments' -> _load_chapters returns ONLY verifier.passed."""
    chapters = site._load_chapters()
    assert chapters and all((c.get("verifier") or {}).get("passed") for c in chapters)


def test_archive_ships_dark():
    assert config.feature_on("archive") is False    # build-dark: nothing renders until the flag flips


# --- 1.2 Silence Detector + "Shouting Into the Void" ---------------------------------------------
def _tax():
    return {"topics": [{"id": "immigration", "label": "Immigration", "seeds": ["border", "migrant"]},
                       {"id": "china", "label": "China", "seeds": ["china"]},
                       {"id": "other", "label": "Other", "seeds": []}]}


def _stmts(n, party, text):
    return [{"member": {"party": party}, "title": "", "text": text} for _ in range(n)]


def test_corpus_topics_matches_deterministically_by_committed_seeds():
    stmts = _stmts(3, "D", "the border crisis") + _stmts(2, "R", "trade with china")
    c = silence.corpus_topics(stmts, _tax())
    assert c["immigration"] == {"D": 3, "R": 0} and c["china"] == {"D": 0, "R": 2}


def test_silence_requires_news_AND_both_parties_quiet():
    """Silence = the news is loud and BOTH parties are quiet. One party talking = not a silence."""
    corpus = {"immigration": {"D": 0, "R": 0}, "china": {"D": 40, "R": 40}}
    board = silence.silence_board({"immigration": 0.9, "china": 0.9}, corpus, _tax())
    assert board["scored"] is True
    assert [r["topic"] for r in board["silent"]] == ["immigration"]   # china is loud -> not silent


def test_a_failed_news_pull_is_excluded_not_called_silence():
    """THE guard: a gap is not a silence. A failed GDELT pull (None) must never produce a claim."""
    corpus = {"immigration": {"D": 0, "R": 0}, "china": {"D": 40, "R": 40}}
    board = silence.silence_board({"immigration": None, "china": 0.9}, corpus, _tax())
    assert board["silent"] == []                                     # no claim from a failed pull
    assert board["excluded"] and board["excluded"][0]["topic"] == "immigration"


def test_a_thin_or_one_party_day_is_not_scored():
    """A corpus hole must never masquerade as avoidance — thin days score nothing, both directions."""
    corpus = {"immigration": {"D": 0, "R": 0}, "china": {"D": 3, "R": 0}}
    board = silence.silence_board({"immigration": 0.9, "china": 0.9}, corpus, _tax())
    assert board["scored"] is False and board["silent"] == [] and board["void"] == []
    assert "thin" in board["gates"]["note"]


def test_void_is_the_mirror_twin_and_ships_with_silence():
    """Both directions ship together: the same call returns silent[] and void[]."""
    corpus = {"immigration": {"D": 0, "R": 0}, "china": {"D": 40, "R": 40}}
    board = silence.silence_board({"immigration": 0.9, "china": 0.0}, corpus, _tax())
    assert [r["topic"] for r in board["silent"]] == ["immigration"]
    assert [r["topic"] for r in board["void"]] == ["china"]          # loud for us, absent from news
    assert "silent" in board and "void" in board


def test_theme_map_is_committed_and_shares_the_taxonomy_seeds():
    """The published topic definition is ONE list: the same seeds drive the news query and our match —
    that's what makes a silence claim reproducible from published data."""
    m = gdelt.load_theme_map()
    tax = {t["id"]: t for t in silence.load_taxonomy()["topics"]}
    assert m["topics"] and "other" not in m["topics"]                # a catch-all has no baseline
    for tid, spec in m["topics"].items():
        assert spec["seeds"] == tax[tid]["seeds"]                    # one definition, both sides
        assert "sourcecountry:unitedstates" in spec["query"]


def test_silence_board_ships_dark():
    assert config.feature_on("silence_board") is False


def test_silence_render_ships_both_directions_together():
    """The release gate: silence and its mirror twin render on the SAME page, or not at all."""
    board = {"day": "2026-07-16", "scored": True,
             "silent": [{"topic": "immigration", "label": "Immigration", "news_volume": 0.9,
                         "D": 0, "R": 0}],
             "void": [{"topic": "china", "label": "China", "news_volume": 0.0, "D": 40, "R": 40}],
             "excluded": [], "gates": {"news_floor": 0.05, "quiet_max": 2, "void_min": 5,
                                       "void_news_max": 0.01}}
    body = site.silence_board_body(board)
    assert "Nobody will say it" in body and "Shouting into the void" in body   # both, one page
    assert "Immigration" in body and "China" in body
    assert "A gap is not a silence" in body                                    # guard disclosed


def test_silence_render_refuses_to_score_without_a_baseline():
    """An unscored board must say so plainly — never render an empty silence list as 'nobody spoke'."""
    body = site.silence_board_body({"day": "2026-07-16", "scored": False,
                                    "gates": {"note": "no news baseline for this day"}})
    assert "Not scored for this day" in body and "no news baseline" in body
    assert "Nobody will say it" not in body                                   # no claim rendered


def test_build_day_board_without_baseline_is_unscored_not_fabricated():
    with _derived_fixture():
        board = silence.build_day_board("1999-01-01",
                                        _stmts(50, "D", "the border") + _stmts(50, "R", "china"))
    assert board["scored"] is False and board["silent"] == [] and board["void"] == []


# --- 1.8 The Owner's Brief -----------------------------------------------------------------------
def _sym(day, d=200, r=150, pub=10, drop=1):
    return {"day": day, "day_scoped": True, "parties": {
        "D": {"statements_ingested": d, "claims_published": pub, "claims_dropped": drop},
        "R": {"statements_ingested": r, "claims_published": pub, "claims_dropped": drop}}}


def _healthy(day="2026-07-20"):
    """A fully-green synthetic week: 8 published days, a real ledger, day-scoped symmetry, fresh
    upstream. Every honesty test below starts here and breaks exactly one thing."""
    f = {}
    for i in range(1, 9):
        d = brief._iso(brief._parse(day) - _dt.timedelta(days=i))
        f[f"manifest__assemble-{d}.json"] = {"kind": "assemble", "day": d}
        f[f"symmetry__{d}.json"] = _sym(d)
    f["cost__2026-07.json"] = {"month": "2026-07", "total_usd": 0.1,
                               "days": {"2026-07-15": {"usd": 0.1}}}
    f[f"manifest__collect-{day}.json"] = {"source_freshness": {"ok": True, "age_hours": 3.0}}
    return f


def test_brief_ships_dark_and_never_fires_while_the_flag_is_off():
    with _derived_fixture(**_healthy()) as sent:
        r = brief.send_brief("2026-07-20")                        # a Monday, everything green
        assert r["sent"] is False and r["reason"] == "feature dark" and sent == []
    assert config.feature_on("owners_brief") is False


def test_force_cadence_can_skip_monday_but_never_the_dark_gate():
    """The FEATURES flip is THE release act — dated, public, diffable. No kwarg may become a second,
    undated release path, so force_cadence bypasses the cadence gate only."""
    with _derived_fixture(**_healthy()) as sent:
        assert brief.send_brief("2026-07-22", force_cadence=True)["reason"] == "feature dark"
        assert sent == []                                          # dark + forced sends nothing
        with _released("owners_brief"):
            assert brief.send_brief("2026-07-22")["reason"] == "not Monday"       # a Wednesday
            assert brief.send_brief("2026-07-22", force_cadence=True)["sent"] is True
            assert brief.send_brief("2026-07-20")["sent"] is True                 # the Monday
        assert len(sent) == 2


def test_ALL_GREEN_is_impossible_while_anything_is_unmeasured():
    """THE regression test — the adversarial review's exact reproduction. This fixture rendered a
    confident ALL GREEN with FOUR things simultaneously broken: newest manifest zero-byte, ledger
    present but carrying no days, symmetry 12 days dead, and claims_dropped never written. Every one
    reported healthy, because `or 0` turns "never measured" into "measured zero" — and zero is green.
    Real state at the time: last real publish 2 days prior, $9.40 spent, audit dead, drop unmeasured."""
    f = _healthy()
    f["cost__2026-07.json"] = {"month": "2026-07", "days": {}}
    for i in range(1, 9):
        f.pop(f"symmetry__{brief._iso(brief._parse('2026-07-20') - _dt.timedelta(days=i))}.json")
    f["symmetry__2026-07-08.json"] = _sym("2026-07-08")            # stale by 12 days
    with _derived_fixture(**f):
        (config.DERIVED / "manifest" / "assemble-2026-07-19.json").write_text("", encoding="utf-8")
        b = brief.build_brief("2026-07-20")
        assert b["headline"] != "ALL GREEN"
        assert b["reds"] == ["streak"]                              # the zero-byte newest manifest
        assert set(b["unknowns"]) == {"spend", "coverage", "verifier_drop"}
        assert not any(n["status"] == "green" for n in b["numbers"])


def test_a_missing_field_is_unmeasured_not_a_healthy_zero():
    """`claims_dropped` absent must read UNKNOWN. Reporting 0-dropped would be a green verdict on a
    verifier that never spoke — and ops writes exactly this shape when a party's LLM leg dies."""
    f = _healthy()
    for i in range(1, 9):
        d = brief._iso(brief._parse("2026-07-20") - _dt.timedelta(days=i))
        row = {"statements_ingested": 200, "claims_published": 10}          # no claims_dropped
        f[f"symmetry__{d}.json"] = {"day": d, "day_scoped": True, "parties": {"D": row, "R": row}}
    with _derived_fixture(**f):
        vd = brief.verifier_drop("2026-07-20")
        assert vd["status"] == "unknown" and vd["value"] is None


def test_a_silent_cost_ledger_is_unknown_never_zero_dollars_green():
    with _derived_fixture(**dict(_healthy(),
                                 **{"cost__2026-07.json": {"month": "2026-07", "days": {}}})):
        assert brief.spend("2026-07-20")["status"] == "unknown"
    with _derived_fixture(**dict(_healthy(), **{"cost__2026-07.json": {
            "month": "2026-07", "days": {"2026-07-15": {"tokens_in": 5}}}})):   # day row, no `usd`
        sp = brief.spend("2026-07-20")
        assert sp["status"] == "unknown" and sp["value"] is None


def test_spend_is_summed_from_the_days_not_the_cached_rollup():
    """`total_usd` is a cache; `days` is the ledger. A stale/absent rollup must not set the number."""
    with _derived_fixture(**dict(_healthy(), **{"cost__2026-07.json": {
            "month": "2026-07", "total_usd": 0.0,                               # a lying cache
            "days": {f"2026-07-{d:02d}": {"usd": 1.0} for d in range(14, 21)}}})):
        sp = brief.spend("2026-07-20")
        assert sp["value"] == 7.0                                   # from days, not total_usd
        assert sp["status"] == "red"


def test_spend_projects_over_days_the_ledger_covers_not_days_elapsed():
    """Dividing by days ELAPSED under-projects — in the GREEN direction — whenever spend starts
    mid-month, which is exactly when a new cost is being evaluated."""
    with _derived_fixture(**dict(_healthy(), **{"cost__2026-07.json": {
            "month": "2026-07",
            "days": {f"2026-07-{d:02d}": {"usd": 1.0} for d in range(16, 21)}}})):
        sp = brief.spend("2026-07-20")                              # $5 over 5 ledger days
        assert sp["value"] == 5.0
        assert sp["projected"] == 16.0 and sp["status"] == "red"    # $5 + $1/day * 11 remaining
        # the elapsed-days denominator would have said $5/20*31 = $7.75 -> a green $8 month


def test_coverage_refuses_a_stale_report_instead_of_reading_it_as_today():
    """A one-party break plus a corrupt newest report must not render green off a stale healthy day.
    Coverage names the day it measured and won't score one older than 2 days."""
    f = _healthy()
    for i in range(1, 4):
        f.pop(f"symmetry__{brief._iso(brief._parse('2026-07-20') - _dt.timedelta(days=i))}.json")
    with _derived_fixture(**f):
        cv = brief.coverage("2026-07-20")
        assert cv["status"] == "unknown" and "cannot describe current coverage" in cv["note"]


def test_coverage_excludes_the_pre_day_scoping_schema_visibly():
    """The real defect: medianing cumulative totals (44,546) against a day-scoped 186 produced a
    confident false RED -> the owner works Playbook P2 hunting an outage that never happened."""
    f = _healthy()
    for d, n in (("2026-07-11", 44635), ("2026-07-12", 44646)):
        f[f"symmetry__{d}.json"] = {"day": d, "parties": {                     # no day_scoped marker
            "D": {"statements_ingested": n, "claims_published": 5, "claims_dropped": 0},
            "R": {"statements_ingested": n, "claims_published": 5, "claims_dropped": 0}}}
    with _derived_fixture(**f):
        cv = brief.coverage("2026-07-20")
        assert cv["status"] == "green"                                          # not poisoned
        assert cv["excluded_reports"] == 2 and "cumulative-total schema" in cv["note"]


def test_coverage_gates_upstream_freshness_the_other_half_of_the_spec():
    """07-OPS §2.3 green = volume AND upstream < 36h. A stale upstream serving a healthy mirror
    replay must not read green, or P2's 72h cold-standby clock starts days late."""
    with _derived_fixture(**dict(_healthy(), **{
            "manifest__collect-2026-07-20.json": {"source_freshness": {"ok": True,
                                                                       "age_hours": 40.0}}})):
        cv = brief.coverage("2026-07-20")
        assert cv["freshness"]["status"] == "red" and cv["status"] == "red"
        assert all(p["status"] == "green" for p in cv["parties"].values())      # volume alone fine


def test_coverage_compares_each_party_to_its_own_median_never_pooled():
    """Pooling would hide a one-party ingest break — the exact failure this number exists to catch."""
    f = _healthy()
    f["symmetry__2026-07-19.json"] = _sym("2026-07-19", d=4, r=150)            # D collapses, R fine
    with _derived_fixture(**f):
        cv = brief.coverage("2026-07-20")
        assert cv["parties"]["D"]["status"] == "red" and cv["parties"]["R"]["status"] == "green"
        assert cv["status"] == "red"


def test_a_missing_publish_is_a_miss_not_a_pending_run():
    """Day D publishes on D+1, so yesterday MUST be there. A hole is RED -> Playbook P1."""
    with _derived_fixture(**_healthy()):
        assert brief.streak("2030-01-01")["status"] == "red"
        s = brief.streak("2026-07-20")
        assert s["status"] == "green" and s["value"] == 8


def test_streak_does_not_invent_a_miss_before_the_first_publish_ever():
    with _derived_fixture(**_healthy()):
        assert brief.streak("2026-07-20")["last_missed"] is None


def test_an_unreadable_manifest_is_not_a_publish():
    with _derived_fixture(**_healthy()):
        (config.DERIVED / "manifest" / "assemble-2026-07-19.json").write_text("{tru",
                                                                             encoding="utf-8")
        assert brief.streak("2026-07-20")["status"] == "red"       # a corrupt receipt is no receipt


def test_reach_is_reported_as_a_manual_count_not_fabricated():
    r = brief.reach()
    assert r["status"] == "manual" and r["value"] is None and "monthly" in r["note"]


def test_headline_is_computed_by_inclusion_so_no_status_inherits_green():
    """Computing it by exclusion ("not reds and not unknowns") hands a green headline to any status
    this function doesn't recognize — including a future typo."""
    with _derived_fixture(**_healthy()):
        assert brief.build_brief("2026-07-20")["headline"] == "ALL GREEN"   # reach() is "manual"
        with _mock.patch.object(brief, "streak", lambda d: {"name": "streak", "status": "wat",
                                                            "note": "?", "value": None}):
            assert brief.build_brief("2026-07-20")["headline"] == "CHECK: unrecognized status"


def test_degraded_days_are_weekly_and_never_in_the_future():
    """Month-scoping hid the entire prior week on the 1st — the exact Monday it matters most."""
    f = _healthy()
    f["manifest__assemble-2026-07-15.json"] = {"kind": "assemble", "day": "2026-07-15",
                                               "degraded": True}
    f["manifest__assemble-2026-07-21.json"] = {"kind": "assemble", "day": "2026-07-21",
                                               "degraded": True}              # tomorrow
    with _derived_fixture(**f):
        assert brief.degraded_days("2026-07-20") == ["2026-07-15"]
    f2 = _healthy("2026-08-03")
    f2["manifest__assemble-2026-07-30.json"] = {"kind": "assemble", "day": "2026-07-30",
                                                "degraded": True}             # prior month, but
    with _derived_fixture(**f2):                                              # inside the week
        assert "2026-07-30" in brief.degraded_days("2026-08-03")


def test_render_carries_every_measurement_not_just_the_method():
    """A bare "[RED] coverage: each party vs its trailing median" gives a tired owner nothing to act
    on. Every line carries its own numbers — that IS the zero-interpretation promise."""
    with _derived_fixture(**_healthy()):
        body = brief.render_brief(brief.build_brief("2026-07-20"))
    for n in ("streak", "spend", "coverage", "verifier_drop", "reach"):
        assert n in body
    assert "2026-07-19" in body                      # coverage names the day it measured
    assert "governor nominal" in body                # the pending-decision signal (07-OPS §3)
    assert "upstream 3.0h" in body                   # freshness is visible, not a sidecar
    assert "Dark shelf" in body and "Monday ritual" in body


def test_tests_never_write_into_the_real_derived_tree():
    """Guards the guard: if the fixture ever stops redirecting, this fails LOUDLY instead of
    silently committing fabricated receipts into the public repo."""
    with _derived_fixture(**_healthy()):
        brief.send_brief("2026-07-20")
        assert config.DERIVED != REAL_DERIVED
        assert (config.DERIVED / "brief" / "2026-07-20.json").exists()
    assert not (REAL_DERIVED / "brief" / "2026-07-20.json").exists()


def test_owners_brief_is_wired_into_run_b_on_both_paths():
    """docs/11 gate: "fires Mondays". A brief nothing calls fires never — and it must run on the
    NO-OP path too, because a Monday where nothing assembled is the Monday it matters most."""
    src = (Path(__file__).resolve().parent.parent / "pipeline" / "run_assemble.py").read_text(
        encoding="utf-8")
    calls = [ln for ln in src.splitlines()
             if "_owners_brief()" in ln and not ln.lstrip().startswith("def ")]
    assert len(calls) == 2                                  # the NO-OP return AND the normal end
    assert "brief.send_brief" in src and "skip-and-log" in src   # never crashes RUN B
