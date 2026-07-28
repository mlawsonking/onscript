"""E2: the silence board (1.2 The absence map) is WIRED into the daily deterministic leg.

The silence module, its render, and its guards are already tested in test_v2_build.py. What was
missing (docs/27: "module exists; no caller; data/derived/silence/ has never been built") is the
DATA-BUILD wiring: deterministic.run now calls silence.build_day_board so the boards accumulate dark,
exactly like build_concordance / build_awards ("build dark / release by gate"). These lock that wiring
and the two lane boundaries it must honor (Article III):
  * the per-party corpus counts are LANE 1 only (a Lane-2 record never enters a party denominator);
  * the GDELT news baseline is LANE 2 and only GATES topic salience, never a party count.

Every test runs against a SYNTHETIC state/derived tree; nothing touches the real data/derived (which
assemble.yml git-adds), so a dark feature can never leave a committed receipt.
"""
import contextlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, deterministic, silence  # noqa: E402

DAY = "2026-07-24"


def _rec(bio, party, body):
    # every record carries an immigration seed so corpus_topics has a topic to count; distinct bodies
    # keep them out of one joint/near-dup family.
    return {"url": f"https://{bio}.house.gov/{bio}-{len(body)}", "title": "Statement",
            "text": f"On immigration and the border, {body}", "date": DAY,
            "member": {"bioguide_id": bio, "party": party, "state": "CA", "chamber": "House"}}


_RECORDS = ([_rec(f"D{i}", "Democrat", f"the House must act now number {i} without delay") for i in range(1, 4)]
            + [_rec(f"R{i}", "Republican", f"the Senate should respond firmly number {i} this week") for i in range(1, 4)])


@contextlib.contextmanager
def _temp_state_derived():
    """Patch config.STATE and config.DERIVED to a throwaway tree (both are referenced at call time in
    the deterministic path). Never write into the real data/derived."""
    old_state, old_derived = config.STATE, config.DERIVED
    with tempfile.TemporaryDirectory(prefix="onscript-e2-silence-") as d:
        root = Path(d)
        config.STATE = root / "state"
        config.DERIVED = root / "derived"
        config.STATE.mkdir(parents=True, exist_ok=True)
        config.DERIVED.mkdir(parents=True, exist_ok=True)
        try:
            yield root
        finally:
            config.STATE, config.DERIVED = old_state, old_derived


@contextlib.contextmanager
def _flag(name, value):
    prev = config.FEATURES[name]
    config.FEATURES[name] = value
    try:
        yield
    finally:
        config.FEATURES[name] = prev


# --- the wiring: the deterministic leg builds the board ------------------------------------------
def test_deterministic_leg_builds_the_silence_board():
    """The E2 gap. After a deterministic run, data/derived/silence/{focus_day}.json exists and is a
    valid board (unscored here: no GDELT baseline in the synthetic tree, and a gap is never a silence)."""
    with _temp_state_derived():
        deterministic.run(_RECORDS, run_id="e2-silence-wiring")
        board_path = config.DERIVED / "silence" / f"{DAY}.json"
        assert board_path.exists(), "the deterministic leg must build the day's silence board"
        board = json.loads(board_path.read_text(encoding="utf-8"))
        assert board["kind"] == "silence-board" and board["day"] == DAY
        # no GDELT baseline present -> unscored, never fabricated from a missing baseline
        assert board["scored"] is False


def test_silence_board_accumulates_dark():
    """Build dark / release by gate: the board is built regardless of FEATURES['silence_board'] (only
    the site render is gated). So boards accumulate under data/derived/silence/ while the surface stays
    dark, which is exactly what the 08-03 digest needs."""
    with _temp_state_derived(), _flag("silence_board", False):
        deterministic.run(_RECORDS, run_id="e2-silence-dark")
        assert (config.DERIVED / "silence" / f"{DAY}.json").exists()
    assert config.FEATURES["silence_board"] is False, "the silence surface must ship OFF"


def test_a_dark_feature_failure_never_breaks_the_run():
    """Skip-and-log (the streak invariant): if the silence build raises, the deterministic run must
    still complete. Forcing build_day_board to raise must not propagate."""
    orig = silence.build_day_board
    silence.build_day_board = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        with _temp_state_derived():
            out = deterministic.run(_RECORDS, run_id="e2-silence-safety")
            assert out["focus_day"] == DAY  # the run completed despite the silence failure
            assert not (config.DERIVED / "silence" / f"{DAY}.json").exists()
    finally:
        silence.build_day_board = orig


# --- Article III: the corpus counts are Lane 1 only ----------------------------------------------
def _stmt(bio, party, text, lane):
    return {"member": {"bioguide": bio, "party": party}, "published_at": DAY,
            "title": "t", "text": f"On immigration and the border, {text}", "lane": lane}


def test_silence_corpus_counts_are_lane1_only():
    """A Lane-2 record (Bluesky/floor) must never enter a per-party count: the board's D/R totals are a
    cross-party comparison (Article III). The deterministic wiring filters to lane == 1 before feeding
    corpus_topics; this test mirrors that filter and proves it is load-bearing."""
    press = [_stmt(f"D{i}", "D", f"press {i}", 1) for i in range(3)] + [_stmt(f"R{i}", "R", f"press {i}", 1) for i in range(3)]
    bluesky = [_stmt(f"B{i}", "D", f"bsky {i}", 2) for i in range(20)]   # 20 Lane-2 D posts
    mixed = press + bluesky
    lane1 = [s for s in mixed if s.get("lane") == config.LANE_BY_SOURCE["press_release"]]
    c_all = silence.corpus_topics(mixed)
    c_lane1 = silence.corpus_topics(lane1)
    imm = "immigration"
    # unfiltered, the 20 Lane-2 D posts would inflate D on the immigration topic...
    assert c_all[imm]["D"] == 23 and c_lane1[imm]["D"] == 3
    # ...the Lane-1 filter the wiring applies keeps the party count honest.
    assert c_lane1[imm]["R"] == 3


# --- the GDELT baseline is a Lane-2 gate, never a party denominator -------------------------------
def test_gdelt_news_volume_gates_topic_salience_but_is_not_a_party_count():
    """The news baseline (GDELT, Lane 2) only decides whether a topic is loud enough to be callable a
    silence; it never appears in a per-party number. On a properly-scored day (both parties active),
    the loud topic that both parties are quiet on is 'silent', and its row carries news_volume (the
    gate) separately from D/R (the Lane-1 party counts)."""
    tax = silence.load_taxonomy()
    topic_ids = [t["id"] for t in tax["topics"] if t["id"] != "other"]
    silent_topic = topic_ids[0]
    news = {tid: 0.9 for tid in topic_ids}                # every topic loud in the news
    # both parties active overall (so the day is not thin/one-party), but silent_topic is untouched by
    # both -> that is the silence. The party counts come ONLY from this corpus, never from `news`.
    corpus = {tid: ({"D": 0, "R": 0} if tid == silent_topic else {"D": 5, "R": 5}) for tid in topic_ids}
    board = silence.silence_board(news, corpus, tax)
    assert board["scored"] is True
    assert silent_topic in {r["topic"] for r in board["silent"]}
    for row in board["silent"]:
        assert set(row) >= {"news_volume", "D", "R"}
        assert row["news_volume"] == 0.9                  # the gate value, echoed as its own field
        assert isinstance(row["D"], int) and isinstance(row["R"], int)  # party counts are Lane-1 integers
    # the party totals are integers summed from the Lane-1 corpus; the fractional news volume is never in them
    totals = board["gates"]["party_totals"]
    assert totals["D"] > 0 and totals["R"] > 0 and totals["D"] == totals["R"]
