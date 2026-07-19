"""Kill-fixtures for the connective-cluster defect (docs/19 §4b). Both directions, real strings.

An external review of the live 2026-07-17 day found Democratic talking points whose receipts do not
support the apparent message. Fable reproduced two from data/derived/days/2026-07-17.json:

  key "into the trump administration's"        — Padilla + Goldman (two different investigation
                                                 letters) + Booker (an unrelated flood bill, chained in
                                                 by the "army corps of engineers" gram);
  key "democratic colleagues in demanding the" — Kelly (a FEMA joint letter) + Rosen (the SAME letter,
                                                 different wrapper — "senate colleagues in urging") +
                                                 Krishnamoorthi (Blanche/Epstein, unrelated).

Every citation is string-valid: each source contains its cluster key verbatim — that is WHY they
clustered, and the verifier honestly verified it. The defect is that the admitted keys are connective
frames / attribution boilerplate, not messages, so a semantically incoherent cluster sails through a
verifier that checks verbatim-ness, quorum, and attribution — everything except whether the shared span
is a message. Two complementary fixes, kill-tested here:

  req 1  is_scaffold_key — a deterministic, party-blind key-admission gate. Both keys die; a real
         coordinated message ("born in the united states", the 06-30 flagship) survives.
  req 2  verify.verify_talking_point key-quorum — count only distinct document FAMILIES whose source
         actually carries the key. The transitively-chained interlopers (Booker, Rosen, Krishnamoorthi)
         drop out, so both clusters fall below the >=3 floor, while the 53-family flagship is untouched.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import boilerplate as B, verify as V  # noqa: E402


def _stmt(sid, bio, party, text, joint=None):
    return {"id": sid, "text": text, "published_at": "2026-07-17",
            "member": {"bioguide": bio, "party": party, "state": "CA"}, "joint_group": joint}


# --- the render interaction: prose must never survive its receipts (docs/19 §4b P1) --------------
def test_render_recomposes_when_the_scaffold_filter_empties_the_talking_points():
    """The 07-17 D flagship shape: every talking point is a scaffold key, so the render filter drops
    them ALL. The composite prose must NOT survive verbatim (it narrated exactly the interlopers), and
    the panel must NOT print the FALSE 'nothing cleared the threshold' line — that is an Art. II
    fabricated silence. Instead the composite is re-derived deterministically from the surviving stats,
    and the panel carries the scaffold-specific honest message."""
    from pipeline import site
    day = {
        "day": "2026-07-17",
        "top_synchronized": [{"ngram": "immigration enforcement", "party": "D", "day_peak": 9,
                              "counts": {"D": 9, "R": 0}, "n": 2, "df_weight": 1.0,
                              "first_seen": {"date": "2026-07-17"}, "series": [3, 9]}],
        "daily_lines": {"D": {
            "composite": "We take up \"into the trump administration's investigation\" and we join "
                         "colleagues in demanding the review.",
            "generator": "sonnet_direct", "model": "claude-sonnet-5",
            "verifier": {"checked": True, "passed": True},
            "stats": {"party": "D", "day": "2026-07-17", "statements": 82, "sync_min": 3,
                      "top_phrase": {"text": "immigration enforcement", "members": 9},
                      "talking_points": [{"label": "into the trump administration's", "members": 3,
                                          "quote": "into the trump administration's investigation", "topics": []}]}}},
        "talking_points": {"D": [
            {"label": "into the trump administration's", "member_count": 3,
             "fragments": [{"text": "into the trump administration's investigation"}], "citations": []}]},
    }
    panel = site.daily_line_panel("D", day, caucus=263)
    assert "into the trump administration" not in panel, "the stale composite narrated a dropped phrase"
    assert "colleagues in demanding" not in panel
    assert "cleared the" not in panel or "threshold" not in panel, "printed a FALSE 'nothing cleared' line"
    assert "connective or attribution phrasing" in panel, "missing the honest scaffold message"
    assert "deterministic template" in panel, "re-composed prose must be labelled deterministic"
    assert "immigration enforcement" in panel                      # the surviving measured fact remains


# --- req 1: the deterministic key-admission gate --------------------------------------------------
def test_scaffold_key_rejects_the_two_live_connective_keys_both_directions():
    # KILL — the two live 2026-07-17 defect keys, straight AND curly apostrophe (the day JSON is curly).
    assert B.is_scaffold_key("into the trump administration's")       # trailing possessive
    assert B.is_scaffold_key("into the trump administration’s")   # curly apostrophe, real data
    assert B.is_scaffold_key("democratic colleagues in demanding the")  # trailing 'the' + attribution
    assert B.is_scaffold_key("led senate colleagues in urging")        # attribution frame (no 'the')
    assert B.is_scaffold_key("joined his colleagues in sending")       # attribution frame
    assert B.is_scaffold_key("an investigation into the")              # terminates before the object
    assert B.is_scaffold_key("the war in iran and")                    # trailing conjunction
    # PROTECT — real coordinated messages, incl. the 06-30 flagship, survive.
    assert not B.is_scaffold_key("born in the united states")
    assert not B.is_scaffold_key("to release the epstein files")
    assert not B.is_scaffold_key("the save act would gut medicaid")
    assert not B.is_scaffold_key("attack on birthright citizenship")
    assert not B.is_scaffold_key("cuts to our medicaid program")
    assert not B.is_scaffold_key("no kings in america")


def test_scaffold_key_reads_only_the_phrase_never_party():
    import inspect
    assert "party" not in inspect.signature(B.is_scaffold_key).parameters
    # symmetry: the same grammar in either mouth gets the same verdict.
    assert B.is_scaffold_key("republican colleagues in demanding the") \
        == B.is_scaffold_key("democratic colleagues in demanding the")


# --- contains_gram: match on the tokenizer, not a raw substring -----------------------------------
def test_contains_gram_matches_on_the_tokenizer():
    # a comma between tokens in the source must NOT hide a gram the member used ...
    assert B.contains_gram("investigation into the Trump administration's efforts", "into the trump administration's")
    assert B.contains_gram("Everyone born in the United States is a citizen.", "born in the united states")
    # ... and a SENTENCE BOUNDARY (period) legitimately breaks the run — consistent with how cluster.py
    # built the gram per-sentence, so this is not a false negative, it is the same rule.
    assert not B.contains_gram("We defend border security. Now is the moment.", "border security now")
    assert not B.contains_gram("a statement about flood protection", "into the trump administration's")


# --- req 2: the key-carrying family quorum --------------------------------------------------------
def test_key_quorum_kills_cluster_d01_into_the_trump_administrations():
    tp = {"label": "into the trump administration's", "member_count": 3,
          "statements": ["p", "g", "b"], "fragments": []}
    by_id = {
        "p": _stmt("p", "P000145", "D", "Padilla is launching an investigation into the Trump "
                                         "administration's efforts to kill offshore wind projects."),
        "g": _stmt("g", "G000123", "D", "Goldman is demanding an investigation into the Trump "
                                         "administration's decision to move the Army Corps."),
        "b": _stmt("b", "B001288", "D", "Booker introduced legislation authorizing Army Corps of "
                                         "Engineers flood protection projects for New Jersey."),
    }
    # only Padilla + Goldman carry the key; Booker was chained in by "army corps of engineers".
    assert V.key_carrying_units(tp, by_id) == {"P000145", "G000123"}
    ok, reasons = V.verify_talking_point(tp, by_id)
    assert not ok and any("key-quorum" in r for r in reasons)


def test_key_quorum_kills_cluster_d02_democratic_colleagues_in_demanding_the():
    tp = {"label": "democratic colleagues in demanding the", "member_count": 3,
          "statements": ["k", "r", "m"], "fragments": []}
    by_id = {
        "k": _stmt("k", "K000377", "D", "Kelly joined other democratic colleagues in demanding the "
                                        "Federal Emergency Management Agency restore wildfire aid."),
        "r": _stmt("r", "R000608", "D", "Rosen led senate colleagues in urging the Federal Emergency "
                                        "Management Agency to act — the SAME letter, different wrapper."),
        "m": _stmt("m", "K000391", "D", "Krishnamoorthi called for the Senate to reject Todd Blanche's "
                                        "nomination over the Epstein files."),
    }
    # only Kelly carries the exact key; Rosen said "senate colleagues in urging", Krishnamoorthi is
    # unrelated — so the honest count is 1, far below quorum.
    assert V.key_carrying_units(tp, by_id) == {"K000377"}
    ok, reasons = V.verify_talking_point(tp, by_id)
    assert not ok and any("key-quorum" in r for r in reasons)


def test_key_quorum_admits_the_birthright_flagship():
    key = "born in the united states"
    by_id = {f"m{i}": _stmt(f"m{i}", f"BIO{i:03d}", "D",
                            f"Everyone born in the United States is a citizen, member {i} said.")
             for i in range(6)}
    tp = {"label": key, "member_count": 6, "statements": list(by_id), "fragments": []}
    assert len(V.key_carrying_units(tp, by_id)) == 6
    ok, reasons = V.verify_talking_point(tp, by_id)
    assert ok, reasons


def test_a_joint_letter_is_one_family_but_member_reach_is_reported():
    # three signatories of ONE letter (shared joint_group) + two independent members. The joint letter
    # is ONE publication unit toward the quorum (§11 trap 2), so this cluster has 3 families, not 5.
    key = "protect our public lands"
    sentence = "We must protect our public lands from this administration."
    by_id = {
        "a": _stmt("a", "A", "D", sentence, joint="joint:letter1"),
        "b": _stmt("b", "B", "D", sentence, joint="joint:letter1"),
        "c": _stmt("c", "C", "D", sentence, joint="joint:letter1"),
        "d": _stmt("d", "D", "D", "I will protect our public lands, said one member."),
        "e": _stmt("e", "E", "D", "Congress should protect our public lands this year."),
    }
    tp = {"label": key, "member_count": 3, "statements": list(by_id), "fragments": []}
    units = V.key_carrying_units(tp, by_id)
    assert units == {"joint:letter1", "D", "E"}          # 3 families, not 5 raw signatories
    assert V.verify_talking_point(tp, by_id)[0]          # 3 families >= quorum


def test_a_two_family_joint_plus_interloper_still_fails():
    # the D-02 shape generalized: one joint letter (2 signatories) + one unrelated member who does NOT
    # carry the key => 1 family carries it => fail. A joint letter cannot manufacture a quorum by itself.
    key = "restore the wildfire aid now"
    letter = "We are demanding you restore the wildfire aid now."
    by_id = {
        "k": _stmt("k", "K", "D", letter, joint="njoint:femaletter"),
        "r": _stmt("r", "R", "D", letter, joint="njoint:femaletter"),
        "m": _stmt("m", "M", "D", "An unrelated statement about the Blanche nomination."),
    }
    tp = {"label": key, "member_count": 2, "statements": list(by_id), "fragments": []}
    assert V.key_carrying_units(tp, by_id) == {"njoint:femaletter"}   # one family carries the key
    assert not V.verify_talking_point(tp, by_id)[0]
