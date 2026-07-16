"""Session 14 — the speaker-attribution gate on the LIVE citation path (run_assemble._citations).

A congressional press release is a MULTI-SPEAKER document, so "verbatim in the cited statement"
does not mean "this member said it" — and `verify.is_verbatim` cannot tell the difference BY
DESIGN. Session 13 found this while building the dark Duet (1.7a) and gated the Duet; the live
citation path was left structurally exposed pending this evaluation.

The fixture below is REAL text from a REAL release (2026-07, congress-press), not a synthetic
construction: Rep. Julie Fedorchak (R-ND) published a bipartisan-bill release carrying Rep. Don
Davis's (D-NC) quote. The audit that motivated this change found the same Davis quote reprinted
across THREE offices' releases. It is the sharpest shape of the bug — a CROSS-PARTY one, where a
Democrat's words would publish under a Republican's name and .gov link.

The gate DEMOTES the quote, never the citation: member/date/URL still publish, so no receipt is
lost and no published number can move (`verify.verify_talking_point` has already fixed the >=3-unit
quorum from tp["statements"] before _citations is reached).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import run_assemble  # noqa: E402

# Verbatim from https://fedorchak.house.gov/media/press-releases/fedorchak-and-colleagues-introduce-
# bipartisan-def-act-protect-farmers-truckers — Fedorchak's release, Davis's quote.
_FEDORCHAK_RELEASE = (
    "The Diesel Engine Flexibility Act would reduce unnecessary downtime caused by faulty "
    "emissions sensors while keeping every existing emissions standard in place, said Davis. "
    "“It's a practical solution that supports jobs, strengthens our rural economy, and helps "
    "keep America fed and our communities growing.”\n\n"
    "“Our farmers and truckers deserve equipment that works,” said Rep. Fedorchak."
)

_RMAP = {
    "F000900": {"name": "Julie Fedorchak", "party": "R", "state": "ND"},
    "D000230": {"name": "Don Davis", "party": "D", "state": "NC"},
    "B000111": {"name": "Bea Brooks", "party": "R", "state": "IA"},
    "C000222": {"name": "Cal Chen", "party": "R", "state": "OH"},
}


def _stmt(sid, bio, text, party="R", state="ND"):
    return {"id": sid, "member": {"bioguide": bio, "party": party, "state": state},
            "published_at": "2026-07-14", "url": f"https://{bio}.house.gov/{sid}",
            "text": text, "joint_group": None, "lane": 1}


def _tp(frags, sids):
    return {"label": "diesel engine flexibility act", "statements": sids,
            "fragments": [{"text": t, "statement": s} for t, s in frags]}


def test_kill_a_colleagues_quote_never_publishes_as_this_members_words():
    """THE KILL TEST. Davis's sentence is verbatim inside Fedorchak's release, and the verifier
    passes it. It must NOT publish as Fedorchak's quote."""
    frag = "it's a practical solution that supports jobs"
    stmt = _stmt("s1", "F000900", _FEDORCHAK_RELEASE)

    # The verifier — the only check that existed before this gate — passes it. That is the point:
    # the string really is in the document, so is_verbatim is right and still not enough.
    from pipeline import verify
    assert verify.is_verbatim(frag, _FEDORCHAK_RELEASE)

    cites = run_assemble._citations(
        _tp([(frag, "s1")], ["s1", "s2", "s3"]),
        {"s1": stmt,
         "s2": _stmt("s2", "B000111", "Farmers deserve better sensors."),
         "s3": _stmt("s3", "C000222", "This bill helps our truckers.")},
        _RMAP)

    assert cites[0]["member"] == "Julie Fedorchak"
    assert cites[0]["quote"] is None, (
        f"published a colleague's words as Fedorchak's own: {cites[0]['quote']!r}")


def test_the_citation_survives_the_demotion_receipts_never_thin_out():
    """Demote the QUOTE, never the CITATION: the row keeps member/date/URL, so the receipt still
    stands and the >=3-unit quorum (already fixed upstream by verify_talking_point) cannot move."""
    cites = run_assemble._citations(
        _tp([("it's a practical solution that supports jobs", "s1")], ["s1", "s2", "s3"]),
        {"s1": _stmt("s1", "F000900", _FEDORCHAK_RELEASE),
         "s2": _stmt("s2", "B000111", "Farmers deserve better sensors."),
         "s3": _stmt("s3", "C000222", "This bill helps our truckers.")},
        _RMAP)

    assert len(cites) == 3                        # still a full quorum of receipts
    assert cites[0]["url"] == "https://F000900.house.gov/s1"
    assert cites[0]["date"] == "2026-07-14"
    assert cites[0]["party"] == "R"


def test_the_members_own_words_in_a_multi_speaker_release_still_publish():
    """The gate must not simply mute every multi-speaker release — that would thin receipts for a
    stylistic property of press offices. Fedorchak's OWN quote, in the same document, publishes."""
    cites = run_assemble._citations(
        _tp([("our farmers and truckers deserve equipment", "s1")], ["s1"]),
        {"s1": _stmt("s1", "F000900", _FEDORCHAK_RELEASE)},
        _RMAP)
    assert cites[0]["quote"] == "our farmers and truckers deserve equipment"


def test_prefers_a_self_attributed_fragment_over_a_colleagues():
    """When a statement contributed several fragments, take one the member actually said rather
    than demoting to no quote at all."""
    cites = run_assemble._citations(
        _tp([("it's a practical solution that supports jobs", "s1"),      # Davis's — refused
             ("our farmers and truckers deserve equipment", "s1")],       # Fedorchak's — taken
            ["s1"]),
        {"s1": _stmt("s1", "F000900", _FEDORCHAK_RELEASE)},
        _RMAP)
    assert cites[0]["quote"] == "our farmers and truckers deserve equipment"


def test_unlocatable_fragment_fails_open_to_current_behavior():
    """A fragment no single sentence carries cannot be speaker-checked. Fail OPEN (publish it, as
    today) rather than invent silence — safe only because the verifier already grounded it and the
    caller demotes rather than drops."""
    stmt = _stmt("s1", "F000900", "Farmers rely on diesel equipment. Trucks matter too.")
    cites = run_assemble._citations(
        _tp([("nowhere in this document", "s1")], ["s1"]), {"s1": stmt}, _RMAP)
    assert cites[0]["quote"] == "nowhere in this document"


def test_unknown_speaker_fails_open():
    """No roster name to compare against => nothing to check => current behavior."""
    stmt = _stmt("s1", "ZZZ999", _FEDORCHAK_RELEASE)
    cites = run_assemble._citations(
        _tp([("it's a practical solution that supports jobs", "s1")], ["s1"]), {"s1": stmt}, _RMAP)
    assert cites[0]["quote"] == "it's a practical solution that supports jobs"
