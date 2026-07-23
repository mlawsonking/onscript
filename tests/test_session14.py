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

The speaker gate still refuses borrowed words. Under the claim-binding contract, a demoted quote
also cannot serve as a receipt for P; the talking point publishes only if three other P-bound
receipts remain.
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


def _tp(frags, sids, label="diesel engine flexibility act"):
    return {"label": label, "statements": sids,
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

    assert cites == []


def test_a_demoted_quote_cannot_survive_as_a_phrase_receipt():
    """A receipt is now evidence for P itself, so a unit without an attributable P-carrying
    fragment drops from the receipt set instead of surviving as an unquoted row.

    docs/19 §4b — a published cluster's cited statements all CARRY the key (the key-quorum guaranteed
    it before _citations ran), so a realistic fixture has the bill name in every co-releasing office's
    statement; s2/s3 name the bill exactly as three offices introducing it together would."""
    cites = run_assemble._citations(
        _tp([("it's a practical solution that supports jobs", "s1"),
             ("Brooks introduced the Diesel Engine Flexibility Act for farmers", "s2"),
             ("The Diesel Engine Flexibility Act helps our truckers", "s3")],
            ["s1", "s2", "s3"]),
        {"s1": _stmt("s1", "F000900", _FEDORCHAK_RELEASE),
         "s2": _stmt("s2", "B000111", "Brooks introduced the Diesel Engine Flexibility Act for farmers."),
         "s3": _stmt("s3", "C000222", "The Diesel Engine Flexibility Act helps our truckers, said Chen.")},
        _RMAP)

    assert len(cites) == 2
    assert {c["url"] for c in cites} == {
        "https://B000111.house.gov/s2", "https://C000222.house.gov/s3"}


def test_the_members_own_words_in_a_multi_speaker_release_still_publish():
    """The gate must not simply mute every multi-speaker release — that would thin receipts for a
    stylistic property of press offices. Fedorchak's OWN quote, in the same document, publishes."""
    cites = run_assemble._citations(
        _tp([("our farmers and truckers deserve equipment", "s1")], ["s1"],
            label="our farmers and truckers"),
        {"s1": _stmt("s1", "F000900", _FEDORCHAK_RELEASE)},
        _RMAP)
    assert cites[0]["quote"] == "our farmers and truckers deserve equipment"


def test_prefers_a_self_attributed_fragment_over_a_colleagues():
    """When a statement contributed several fragments, take one the member actually said rather
    than demoting to no quote at all."""
    cites = run_assemble._citations(
        _tp([("it's a practical solution that supports jobs", "s1"),      # Davis's — refused
             ("our farmers and truckers deserve equipment", "s1")],       # Fedorchak's — taken
            ["s1"], label="our farmers and truckers"),
        {"s1": _stmt("s1", "F000900", _FEDORCHAK_RELEASE)},
        _RMAP)
    assert cites[0]["quote"] == "our farmers and truckers deserve equipment"


def test_unlocatable_fragment_cannot_become_a_phrase_receipt():
    """A fragment that does not carry P cannot become a receipt for P."""
    # The statement carries the key (docs/19 §4b — else it would not be cited), but the FRAGMENT under
    # test appears in no single sentence, so the speaker-check cannot locate it and fails open.
    stmt = _stmt("s1", "F000900", "The Diesel Engine Flexibility Act matters. Trucks matter too.")
    cites = run_assemble._citations(
        _tp([("nowhere in this document", "s1")], ["s1"]), {"s1": stmt}, _RMAP)
    assert cites == []


def test_unknown_speaker_fails_open():
    """No roster name to compare against => nothing to check => current behavior."""
    stmt = _stmt("s1", "ZZZ999", _FEDORCHAK_RELEASE)
    cites = run_assemble._citations(
        _tp([("it's a practical solution that supports jobs", "s1")], ["s1"],
            label="practical solution that supports"), {"s1": stmt}, _RMAP)
    assert cites[0]["quote"] == "it's a practical solution that supports jobs"
