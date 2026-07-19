"""1.3 origination (R2 / docs/21 §3.2) — the SPAN-gated, coordination-floored, born-coordinated
replacement for the retired author leaderboard (#143). DARK until FEATURES["authors_vessels"].

The construct the leaderboard would have published — "Chip Roy authored the SAVE Act" — was three
confounds at once: tenure (veterans author everything), chamber (at a low floor every "author" is a
senator), and nomenclature (a member typing a bill's name first is not its author). What survives is a
per-phrase origination claim made ONLY when all three are controlled: the phrase is not an official
name, it actually coordinated (peak >= the floor), and it had a single day-0 first-sayer.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, site  # noqa: E402

FLAG = "authors_vessels"


class _flag:
    def __init__(self, on): self.on = on
    def __enter__(self): self.prev = config.FEATURES[FLAG]; config.FEATURES[FLAG] = self.on
    def __exit__(self, *a): config.FEATURES[FLAG] = self.prev


def _pd(ngram, peak, bio="B000001", tie=None, date="2026-07-11", congress=119):
    return {"ngram": ngram, "peak_units": peak, "congress": congress,
            "first_seen": {"date": date, "bioguide": bio, "tie": tie or []},
            "df_weight": 1.0, "series": [{"day": date, "D": 1}]}


# --- the three controls, on the origination string --------------------------------------------
def test_span_gate_a_bill_title_gets_no_authorship_claim():
    line = site._origination_line(_pd("21st century road to housing act", 20))
    assert "official name" in line and "not an authored phrase" in line
    assert " by " not in line and "born coordinated" not in line     # nobody is credited as author


def test_below_the_coordination_floor_is_not_origination():
    line = site._origination_line(_pd("cuts to our medicaid program", 5))   # substantive but peak < 15
    assert "coordination floor" in line
    assert " by " not in line and "born coordinated" not in line


def test_a_single_day0_sayer_of_a_coordinated_substantive_phrase_is_the_origin():
    line = site._origination_line(_pd("born in the united states", 53))     # not nomenclature, peak >= 15, no tie
    assert " by " in line and "official name" not in line and "born coordinated" not in line


def test_multiple_day0_sayers_is_born_coordinated_no_single_author():
    line = site._origination_line(_pd("border security now", 20, tie=["B000002"]))
    assert "born coordinated" in line and "no single author" in line


# --- the release gate: DARK by default --------------------------------------------------------
def test_the_first_said_row_is_byte_identical_with_the_flag_off():
    pd = _pd("21st century road to housing act", 20)
    with _flag(False):
        off = site.phrase_page_body(pd)
    # Flag OFF: the current unchanged line, NO origination redesign leaks onto the live page.
    assert "official name, not an authored phrase" not in off
    assert "First said" in off and " by " in off
    with _flag(True):
        on = site.phrase_page_body(pd)
    assert "official name, not an authored phrase" in on                 # ON: the SPAN gate renders


def test_feature_ships_dark():
    assert config.FEATURES["authors_vessels"] is False
