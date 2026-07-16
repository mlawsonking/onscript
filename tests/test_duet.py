"""1.7a The Duet — symmetry, attribution integrity, and the quote gates. All $0, no network.

The load-bearing test here is test_never_attributes_a_colleagues_quote: it is a REAL failure found on
REAL data (2026-06-30), and one the deterministic verifier cannot catch by design.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, duet, site, verify  # noqa: E402


_DAY_FIXTURE = {"duets": [{"ngram": "rule of law", "counts": {"D": 9, "R": 5}, "both": 5, "sides": {
    "D": [{"member": "Dana Adams", "party": "D", "state": "CA", "date": "2026-06-30",
           "url": "https://adams.house.gov/x", "quote": "That is a victory for the rule of law."}],
    "R": [{"member": "Rhea Rivera", "party": "R", "state": "TX", "date": "2026-06-30",
           "url": "https://rivera.house.gov/y", "quote": "They undermine the rule of law."}]}}]}


def _with_duet_flag(on: bool):
    config.FEATURES["duet"] = on


# --- fixtures ---------------------------------------------------------------------------------
def _stmt(sid, bio, party, text, state="CA", joint=None):
    return {"id": sid, "member": {"bioguide": bio, "party": party, "state": state},
            "published_at": "2026-06-30", "url": f"https://{bio}.house.gov/{sid}",
            "text": text, "joint_group": joint, "lane": 1}


def _ledger(ngram, day, d_members, r_members):
    return {ngram: {"ngram": ngram, "n": len(ngram.split()), "df_weight": 0.9,
                    "first_seen": {"date": "2025-01-06", "bioguide": "X000001"},
                    "daily": {day: {"D": len(d_members), "members_D": list(d_members),
                                    "R": len(r_members), "members_R": list(r_members)}}}}


# Surnames, not "Alpha1": an attribution marker carries a NAME and the speaker gate matches name
# TOKENS, so a digit-bearing fixture name exercises a shape the roster can never produce.
_D_NAMES = {"D1": "Dana Adams", "D2": "Drew Baker", "D3": "Dale Carter", "D4": "Dora Diaz"}
_R_NAMES = {"R1": "Rhea Rivera", "R2": "Ross Stone", "R3": "Ruby Turner", "R4": "Rex Vance"}
_RMAP = {b: {"name": n, "party": "D", "state": "CA"} for b, n in _D_NAMES.items()}
_RMAP.update({b: {"name": n, "party": "R", "state": "TX"} for b, n in _R_NAMES.items()})


# --- the attribution kill-test (a real 2026-06-30 failure) -------------------------------------
def test_never_attributes_a_colleagues_quote():
    """A press release is a MULTI-speaker document. Cisneros's sentence appeared verbatim inside the
    releases published by BOTH Castro's and Houlahan's offices, and the Duet credited it to each of
    them as their own words.

    The deterministic verifier passes this text — is_verbatim() only asks whether the string occurs in
    the cited statement, which it truly does. Verbatim is not the same as attributable, so the gate
    lives here. Both directions are asserted: the colleague's line is refused, and the member's OWN
    line in the same document is still returned (the gate must not simply mute multi-speaker releases).
    """
    text = ('WASHINGTON — Rep. Castro released the following statement. '
            '"Our servicemembers deserve better," said Rep. Castro. '
            '"I know firsthand why we kept up with these vaccine requirements. '
            'I\'m proud to support my colleagues, Congressman Castro and Congresswoman Houlahan, '
            'in urging the DoD to act," said Rep. Cisneros.')
    # The colleague's sentence is verbatim in Castro's release...
    assert verify.is_verbatim("i'm proud to support my colleagues", text)
    # ...and is still refused as Castro's words, because Cisneros is the speaker of that block.
    assert duet.quote_for("i'm proud to support", text, speaker="castro") is None
    # Castro's own quoted line, in that same release, is returned.
    got = duet.quote_for("our servicemembers deserve", text, speaker="castro")
    assert got == "Our servicemembers deserve better"


def test_attribution_gate_allows_lead_and_unmarked_text():
    """No attribution marker before the sentence => it is the release's lead / the member's own voice.
    Conservative in the safe direction: we do not drop a member's real speech for lack of a marker."""
    text = 'The rule of law prevailed today. "We will keep fighting," said Rep. Adams.'
    assert duet.quote_for("rule of law", text, speaker="adams") == "The rule of law prevailed today."


# --- symmetry (Article III): swap the labels, get the same instrument --------------------------
def test_duet_is_symmetric_under_party_swap():
    day = "2026-06-30"
    ledger = _ledger("rule of law", day, ["D1", "D2", "D3"], ["R1", "R2", "R3"])
    focus = [_stmt(f"d{i}", f"D{i}", "D", f"The rule of law matters to us, number {i}.") for i in (1, 2, 3)]
    focus += [_stmt(f"r{i}", f"R{i}", "R", f"They undermine the rule of law, number {i}.") for i in (1, 2, 3)]
    got = duet.find_duets(day, ledger, focus, _RMAP, k=5)

    swapped_ledger = _ledger("rule of law", day, ["R1", "R2", "R3"], ["D1", "D2", "D3"])
    swapped_focus = [{**s, "member": {**s["member"],
                                      "party": ("R" if s["member"]["party"] == "D" else "D")}}
                     for s in focus]
    got2 = duet.find_duets(day, swapped_ledger, swapped_focus, _RMAP, k=5)

    assert len(got) == len(got2) == 1
    assert got[0]["ngram"] == got2[0]["ngram"]
    assert got[0]["both"] == got2[0]["both"]
    # the same magnitude on each side, with the labels exchanged
    assert got[0]["counts"]["D"] == got2[0]["counts"]["R"]
    assert len(got[0]["sides"]["D"]) == len(got2[0]["sides"]["R"])


def test_one_threshold_applies_to_both_parties():
    """DUET_MIN_MEMBERS is not a new knob: it IS the sync threshold, applied twice. A side one member
    short is not a duet, whichever side it is — asserted in both directions so a future edit cannot
    quietly make one party easier to publish."""
    assert duet.DUET_MIN_MEMBERS == config.SYNC_MIN_MEMBERS
    day = "2026-06-30"
    for short_party in ("D", "R"):
        d_m = ["D1", "D2"] if short_party == "D" else ["D1", "D2", "D3"]
        r_m = ["R1", "R2"] if short_party == "R" else ["R1", "R2", "R3"]
        ledger = _ledger("rule of law", day, d_m, r_m)
        assert duet.candidate_rows(ledger, day) == [], short_party


# --- the citation gate ------------------------------------------------------------------------
def test_uncitable_side_publishes_nothing():
    """Ledger says both parties said it, but the R statements do not contain the phrase in any
    sentence -> no receipts -> no duet. Citation-or-silence (Article XII)."""
    day = "2026-06-30"
    ledger = _ledger("rule of law", day, ["D1", "D2", "D3"], ["R1", "R2", "R3"])
    focus = [_stmt(f"d{i}", f"D{i}", "D", f"The rule of law matters, {i}.") for i in (1, 2, 3)]
    focus += [_stmt(f"r{i}", f"R{i}", "R", f"Unrelated remarks about trade, {i}.") for i in (1, 2, 3)]
    assert duet.find_duets(day, ledger, focus, _RMAP, k=5) == []


def test_joint_release_counts_once_toward_the_quorum():
    """A joint/delegation document is ONE act of agreement, not three (§11 trap 2)."""
    day = "2026-06-30"
    ledger = _ledger("rule of law", day, ["D1", "D2", "D3"], ["R1", "R2", "R3"])
    focus = [_stmt(f"d{i}", f"D{i}", "D", f"The rule of law matters, {i}.", joint="j1") for i in (1, 2, 3)]
    focus += [_stmt(f"r{i}", f"R{i}", "R", f"They undermine the rule of law, {i}.") for i in (1, 2, 3)]
    assert duet.find_duets(day, ledger, focus, _RMAP, k=5) == []   # D collapses to 1 unit -> < 3


def test_every_published_quote_is_verbatim_in_its_own_source():
    day = "2026-06-30"
    ledger = _ledger("rule of law", day, ["D1", "D2", "D3"], ["R1", "R2", "R3"])
    # Each release quotes ITS OWN member — anything else is correctly refused by the speaker gate.
    focus = [_stmt(f"d{i}", f"D{i}", "D", f'"The rule of law matters," said {_D_NAMES[f"D{i}"].split()[-1]}.')
             for i in (1, 2, 3)]
    focus += [_stmt(f"r{i}", f"R{i}", "R", f"They undermine the rule of law, number {i}.") for i in (1, 2, 3)]
    by_id = {s["id"]: s for s in focus}
    duets = duet.find_duets(day, ledger, focus, _RMAP, k=5)
    assert duets, "expected a duet"
    for d in duets:
        for party in ("D", "R"):
            assert len(d["sides"][party]) >= duet.DUET_MIN_MEMBERS
            for c in d["sides"][party]:
                src = next(s for s in by_id.values() if s["url"] == c["url"])
                assert verify.is_verbatim(c["quote"], src["text"]), c


# --- quote hygiene ----------------------------------------------------------------------------
def test_furniture_is_never_quoted():
    text = ("WASHINGTON — Congressman Adams (CA-21) released the following statement following "
            "the Supreme Court's decision on birthright citizenship:")
    assert duet.is_furniture(text.split(":")[0] + ":")
    # the phrase appears ONLY in the header -> no quote at all, rather than a quote nobody said
    assert duet.quote_for("the supreme court", text, speaker="adams") is None


def test_abbreviations_do_not_guillotine_a_quote():
    """Case names and U.S. must not be read as sentence ends — both are real 2026-06-30 output that
    came back guillotined at 'Trump v.' and at 'with U.S.'"""
    text = "Goodlander filed an amicus brief in this case, Trump v. Barbara, before the U.S. Court of Appeals."
    got = duet.quote_for("an amicus brief", text, speaker="goodlander")
    assert got == text            # whole and unguillotined, terminal period included


def test_wrapping_quotes_and_attribution_tail_are_stripped_but_stay_verbatim():
    text = '“Americans deserve better,” said Congresswoman Adams.'
    got = duet.quote_for("americans deserve better", text, speaker="adams")
    assert got == "Americans deserve better"
    assert verify.is_verbatim(got, text)      # still grounded in the source


def test_quote_is_never_truncated_mid_sentence():
    """A clipped span inverts meaning ("...a bill I will never support" -> "...a bill I will"); the
    verifier carries a negation guard for exactly this. A long sentence publishes WHOLE."""
    long_tail = " and we will not stop until every family is protected from this cruelty" * 6
    text = f"The rule of law prevailed today{long_tail}."
    got = duet.quote_for("rule of law", text, speaker="adams")
    assert len(text) > duet.QUOTE_MAX_CHARS     # the fixture really does exceed the limit...
    assert got == text                          # ...and publishes WHOLE rather than clipped to fit
    assert verify.is_verbatim(got, text)


# --- display selection ------------------------------------------------------------------------
def test_ends_mid_construction_rejects_fragments_keeps_real_phrases():
    for frag in ("united states and", "court's decision in", "united states to", "birthright citizenship and"):
        assert duet._ends_mid_construction(frag) is True, frag
    # a leading article is NOT a fragment: n-grams start at 3 tokens, so "the supreme court" is the
    # shortest real form of that phrase and must survive.
    for good in ("the supreme court", "rule of law", "an amicus brief", "born in the united states"):
        assert duet._ends_mid_construction(good) is False, good


def test_topic_disjoint_keeps_the_strongest_row_per_topic():
    rows = [{"ngram": "the supreme court", "both": 15}, {"ngram": "the supreme court's", "both": 6},
            {"ngram": "supreme court's decision", "both": 5}, {"ngram": "statement after the supreme", "both": 5},
            {"ngram": "rule of law", "both": 5}]
    kept = [r["ngram"] for r in duet.topic_disjoint(rows, k=5)]
    assert kept == ["the supreme court", "rule of law"]   # one SCOTUS row, not five


def test_topic_disjointness_is_applied_after_the_citation_gate():
    """If the strongest row of a topic cannot be cited, a citable VARIANT of that same topic must
    still publish — filtering topics before the quote gate would drop it silently."""
    day = "2026-06-30"
    ledger = _ledger("the supreme court", day, ["D1", "D2", "D3", "D4"], ["R1", "R2", "R3", "R4"])
    ledger.update(_ledger("supreme court ruled", day, ["D1", "D2", "D3"], ["R1", "R2", "R3"]))
    # No statement carries the literal span "the supreme court", so the STRONGER row (both=4) is
    # uncitable; the weaker same-topic row is citable and must still publish.
    focus = [_stmt(f"d{i}", f"D{i}", "D", f"In a ruling, supreme court ruled for families, {i}.") for i in (1, 2, 3)]
    focus += [_stmt(f"r{i}", f"R{i}", "R", f"In a ruling, supreme court ruled for states, {i}.") for i in (1, 2, 3)]
    got = duet.find_duets(day, ledger, focus, _RMAP, k=5)
    assert [d["ngram"] for d in got] == ["supreme court ruled"]


# --- release gate + render rules ---------------------------------------------------------------
def test_duet_is_dark_until_its_flag_flips():
    """Build dark / release by gate (BUILD-PROGRAM §1): the data lands in the day JSON every day, but
    NOTHING renders until FEATURES["duet"] is flipped in a commit. Restores the flag either way so a
    failure here cannot leak a released flag into the rest of the suite."""
    before = config.FEATURES.get("duet")
    try:
        _with_duet_flag(False)
        assert site.duet_panel(_DAY_FIXTURE) == ""
        _with_duet_flag(True)
        assert "rule of law" in site.duet_panel(_DAY_FIXTURE)
    finally:
        config.FEATURES["duet"] = before
    assert config.FEATURES["duet"] is False, "the duet flag must ship OFF"


def test_render_never_quotes_the_code_computed_phrase():
    """The phrase is a ledger n-gram, not anybody's words. Quotation marks around it would attribute a
    computed string to a member — the exact failure P2 v1.2 and HIGH-1 exist to prevent. Member quotes
    DO get quote marks (via CSS on .quote), the phrase does not."""
    before = config.FEATURES.get("duet")
    try:
        _with_duet_flag(True)
        html = site.duet_panel(_DAY_FIXTURE)
        assert '<span class="duet-phrase">rule of law</span>' in html
        assert '"rule of law"' not in html and "&ldquo;rule of law&rdquo;" not in html
        # both sides' receipts, each bound to its own member + source link
        assert "Dana Adams" in html and "Rhea Rivera" in html
        assert "adams.house.gov" in html and "rivera.house.gov" in html
    finally:
        config.FEATURES["duet"] = before


def test_render_is_empty_on_a_day_with_no_duets():
    """0 duets is the common case (2026-07-08 had none) — the section must vanish, not render an
    empty shell that implies we found something."""
    before = config.FEATURES.get("duet")
    try:
        _with_duet_flag(True)
        assert site.duet_panel({"duets": []}) == ""
        assert site.duet_panel({}) == ""
    finally:
        config.FEATURES["duet"] = before


# --- §5.1 two-lane machine enforcement ----------------------------------------------------------
def test_lane2_record_cannot_move_a_duet():
    """A duet is a CROSS-PARTY number, so Lane 1 is its only admissible input (§5.1). Bluesky (Lane 2
    today) is ~94% Democratic and the v2 floor leg lands as Lane 2 as well, so a single Lane-2 record
    reaching a cross-party claim would import an asymmetric source into it.

    Enforced in find_duets itself rather than trusted to the caller: assemble() does pass a lane-1
    focus, but "machine-enforced" means the aggregator refuses, not that the caller remembers."""
    day = "2026-06-30"
    ledger = _ledger("rule of law", day, ["D1", "D2", "D3"], ["R1", "R2", "R3"])
    focus = [_stmt(f"d{i}", f"D{i}", "D", f"The rule of law matters, {i}.") for i in (1, 2, 3)]
    focus += [_stmt(f"r{i}", f"R{i}", "R", f"They undermine the rule of law, {i}.") for i in (1, 2, 3)]
    assert duet.find_duets(day, ledger, focus, _RMAP, k=5), "baseline: lane-1 duet publishes"

    # Drop one R to lane 2 -> that side can no longer field its quorum -> no duet at all.
    demoted = [dict(s, lane=2) if s["member"]["bioguide"] == "R3" else s for s in focus]
    assert duet.find_duets(day, ledger, demoted, _RMAP, k=5) == []

    # And a lane-2 record can never ADD a receipt: an extra Bluesky-style R post does not resurrect it.
    padded = demoted + [_stmt("x1", "R4", "R", "They undermine the rule of law online.", state="TX")]
    padded = [dict(s, lane=2) if s["id"] == "x1" else s for s in padded]
    assert duet.find_duets(day, ledger, padded, _RMAP, k=5) == []


def test_lane_none_is_also_excluded_from_duets():
    """Fail closed: an untagged record is not assumed to be Lane 1 (the engine's own gate treats
    lane=None as ineligible — tests/test_pipeline.py::test_two_lane_enforcement...)."""
    day = "2026-06-30"
    ledger = _ledger("rule of law", day, ["D1", "D2", "D3"], ["R1", "R2", "R3"])
    focus = [_stmt(f"d{i}", f"D{i}", "D", f"The rule of law matters, {i}.") for i in (1, 2, 3)]
    focus += [_stmt(f"r{i}", f"R{i}", "R", f"They undermine the rule of law, {i}.") for i in (1, 2, 3)]
    untagged = [{k: v for k, v in s.items() if k != "lane"} for s in focus]
    assert duet.find_duets(day, ledger, untagged, _RMAP, k=5) == []
