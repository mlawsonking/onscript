"""Kill-fixtures for the CREC boilerplate suppressor (docs/15 §D4 gate). The Record is a WEAK CARRIER —
its loudest 'coordination' is parliamentary furniture every member uses. The suppressor must strip that
furniture AND leave substantive talking points standing. Both directions are tested; the marquee proves
procedural convergence is not read as message coordination (§1.12)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.deep import crec_boilerplate as B  # noqa: E402


def test_suppresses_committee_of_the_whole_procedure():
    for ng in ["whole house on the state", "the committee of the whole house",
               "under consideration the bill", "the house in committee of the whole",
               "had under consideration"]:
        assert B.is_crec_boilerplate(ng), ng


def test_suppresses_recognition_and_yielding():
    for ng in ["mr speaker today i rise", "i yield back the balance",
               "the gentleman from missouri", "reform in the house of representatives"]:
        assert B.is_crec_boilerplate(ng), ng


def test_suppresses_bill_title_language():
    for ng in ["to provide for security and diversity", "and for other purposes",
               "to amend the internal revenue code", "to authorize the secretary"]:
        assert B.is_crec_boilerplate(ng), ng


def test_substantive_talking_points_survive():
    for ng in ["birthright citizenship", "the notch baby act", "born in the united states",
               "the death tax", "affordable health care", "our men and women in uniform"]:
        assert not B.is_crec_boilerplate(ng), ng


def test_precision_a_phrase_sharing_formula_words_survives():
    """The anchor guard: 'state of the union' is a fragment of the Committee-of-the-Whole formula but
    carries no procedural anchor -> it SURVIVES (it's the SOTU, real). Only fragments with a procedural
    anchor ('whole', 'committee', 'consideration') are suppressed."""
    assert not B.is_crec_boilerplate("state of the union")             # SOTU survives
    assert not B.is_crec_boilerplate("the state of our schools")       # shares 'the state of', survives
    assert B.is_crec_boilerplate("whole house on the state")           # anchor 'whole' -> suppressed


def test_killfixture_procedural_convergence_is_not_message_coordination():
    """THE marquee (§1.12): a synthetic ledger whose loudest 'coordination' is procedural + bill-title
    furniture (universal — every member uses it), plus ONE real talking point. The suppressor must
    strip the furniture and leave the real message as the only surviving signal."""
    rows = [
        {"ng": "the committee of the whole house", "peak": 30},        # procedure — everyone
        {"ng": "under consideration the bill", "peak": 28},            # procedure
        {"ng": "i yield back the balance", "peak": 25},                # yielding
        {"ng": "to provide for security and diversity", "peak": 20},   # bill title
        {"ng": "and for other purposes", "peak": 19},                  # bill-title tail
        {"ng": "the notch baby act", "peak": 12},                      # REAL coordination
    ]
    kept = B.suppress(rows)
    assert [r["ng"] for r in kept] == ["the notch baby act"]           # only the real message survives
    assert B.suppress(["mr speaker", "birthright citizenship"]) == ["birthright citizenship"]  # bare strings too


def test_empty_and_case_insensitive():
    assert B.is_crec_boilerplate("") is False
    assert B.is_crec_boilerplate("MR SPEAKER Today") is True           # case-insensitive
