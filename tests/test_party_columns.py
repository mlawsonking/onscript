"""R3 / #146 — per-party side-by-side columns for the day table. DARK until FEATURES["party_columns"].

The pooled `collapse_and_rank(rows, k=20)` ranks by raw peak and truncates, so the larger caucus
structurally fills the flagship table (measured 88% D, 100% D on two days) — a display artifact, not a
finding, and a live Art. IV instrument asymmetry. R3's fix goes in the VIEW, never the threshold: each
party gets its OWN top-k, ranked within the party, every count carrying its N-of-caucus denominator.
SYNC_MIN is untouched.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import build, config, site  # noqa: E402

FLAG = "party_columns"


class _flag:
    def __init__(self, on): self.on = on
    def __enter__(self): self.prev = config.FEATURES[FLAG]; config.FEATURES[FLAG] = self.on
    def __exit__(self, *a): config.FEATURES[FLAG] = self.prev


def _row(ngram, d, r, slug="s"):
    return {"ngram": ngram, "slug": slug, "counts": {"D": d, "R": r, "I": 0},
            "day_peak": max(d, r), "party": "D" if d >= r else "R", "series": [1, max(d, r)],
            "df_weight": 1.0, "velocity": 1.0, "first_seen": {"date": "2026-07-15"}}


# --- the #146 fix: each party gets its own column, ranked within the party ----------------------
def test_the_larger_caucus_cannot_fill_the_table_the_minority_gets_its_own_column():
    # A D-dominated pooled table: 5 D phrases with high counts + 1 R phrase. In the pooled top-k the R
    # phrase is buried/last; in per-party columns it is R's #1 — visible, not crowded out.
    day = {"day": "2026-07-15", "top_synchronized": [
        _row("democrats protect health care", 40, 0, "d1"), _row("republicans gut medicaid", 35, 0, "d2"),
        _row("save our democracy now", 30, 0, "d3"), _row("defend the affordable care act", 25, 0, "d4"),
        _row("stand up for workers", 20, 0, "d5"), _row("secure the southern border", 0, 12, "r1")]}
    html = site.party_columns_table(day, {"d1", "r1"}, 1, {"D": 263, "R": 220})
    assert "secure the southern border" in html                    # R's phrase is shown ...
    assert html.count('class="pcol"') == 2                          # ... in its OWN column
    assert "of 263" in html and "of 220" in html                   # N-of-caucus denominators, both parties


def test_a_party_with_no_qualifying_phrase_says_so_never_borrows_the_others():
    day = {"day": "2026-07-15", "top_synchronized": [_row("only the democrats spoke today", 10, 0, "d1")]}
    html = site.party_columns_table(day, set(), 1, {"D": 263, "R": 220})
    assert "No phrase reached the threshold for this party today" in html   # the R column, honest
    assert "only the democrats spoke today" in html                          # the D column


def test_sync_by_party_when_present_is_used_verbatim():
    day = {"day": "2026-07-15", "sync_by_party": {
        "D": [_row("born in the united states", 20, 0, "d1")],
        "R": [_row("the little v hospital ruling", 0, 12, "r1")]}}
    html = site.party_columns_table(day, set(), 1, {"D": 263, "R": 220})
    assert "born in the united states" in html and "the little v hospital ruling" in html


# --- the build-time per-party selection (ledger -> {party: rows}) --------------------------------
def test_top_synchronized_by_party_ranks_within_each_party():
    day = "2026-07-15"
    ledger = {
        "affordable health care for all": {"n": 5, "df_weight": 1.0, "first_seen": {"date": day, "bioguide": "X"},
                                            "daily": {day: {"D": 20, "R": 0}}},
        "secure the southern border now": {"n": 5, "df_weight": 1.0, "first_seen": {"date": day, "bioguide": "Y"},
                                           "daily": {day: {"D": 0, "R": 12}}},
    }
    by_party = build.top_synchronized_by_party(ledger, day, k_per_party=10)
    assert [r["ngram"] for r in by_party["D"]] == ["affordable health care for all"]
    assert [r["ngram"] for r in by_party["R"]] == ["secure the southern border now"]  # R present despite lower count


# --- the release gate: DARK by default ----------------------------------------------------------
def test_feature_ships_dark():
    assert config.FEATURES["party_columns"] is False
