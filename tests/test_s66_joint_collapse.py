"""S66-1 acceptance: a cosigned release is one project unit, so it cannot carry a quorum.

docs/39 C1. Three live phrase pages held grounded_units 3, the exact citation floor, while two
of the three receipts were one 2026-07-09 Nevada airports announcement published by the Cortez
Masto and Rosen offices under swapped name order. The near-duplicate family bar did not reach
that pair (measured Jaccard 0.647 against a 0.72 bar), so the standing rule that joint AND
COSIGNED releases count once through the project unit key was enforced for the joint half only.

The tests below are built from the committed production artifacts (docs/37 rule 2): the receipt
rows, peak day, and n-grams come from data/derived/phrase-evidence.json and data/derived/phrases,
not from invented fixtures. Nothing here asserts that a live artifact REMAINS defective (rule 3
mirror form): the pinned receipt rows are literals, and every assertion is the healed verdict
that the builder now returns for them, which stays true after production rebuilds the artifact.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from pipeline import config, document_families, phrase_evidence, site, util
from pipeline.phrases import _unit_key


DAY = "2026-07-09"
DEFECTIVE_SLUGS = ("007eacff261c652d", "2dc5adb851e6e29d", "e0b16e162cdabc40")

# The two real headlines. One announcement, two letterheads, name order swapped: this is the
# evidence each office declares that the other co-announced.
NEVADA_TITLES = {
    "https://www.cortezmasto.senate.gov/news/press-releases/cortez-masto-rosen-announce-nearly-30-million-for-airports-across-nevada/":
        "Cortez Masto, Rosen Announce Nearly $30 Million for Airports Across Nevada",
    "https://www.rosen.senate.gov/2026/07/09/rosen-cortez-masto-announce-nearly-30-million-in-federal-funding-for-airports-across-nevada/":
        "Rosen, Cortez Masto Announce Nearly $30 million in Federal Funding for Airports Across Nevada",
}

# Pinned history: the three defective records as published on 2026-08-09. Used only when the
# live artifact no longer carries them, so a production rebuild that heals the pages does not
# turn this file red.
PINNED_RECEIPTS = {
    "007eacff261c652d": [
        {"member": "Catherine Cortez Masto", "party": "D", "state": "NV", "date": DAY,
         "url": list(NEVADA_TITLES)[0]},
        {"member": "Emilia Strong Sykes", "party": "D", "state": "OH", "date": DAY,
         "url": "https://sykes.house.gov/media/press-releases/rep-sykes-secures-3-million-federal-grant"},
        {"member": "Jacky Rosen", "party": "D", "state": "NV", "date": DAY,
         "url": list(NEVADA_TITLES)[1]},
    ],
}

_SHARED = (
    "today the delegation announced a federal investment into airports across the state "
    "from the federal aviation administration ensuring that these airports will continue "
    "to serve communities throughout the region for many years to come and that every "
    "traveler benefits from a modern safe and reliable terminal building and runway "
    "surface as the department completes each phase of the awarded grant program "
).split()
_OWN = {
    "a": ("the senior senator said in a statement that this award reflects years of work "
          "with local officials and that the state will keep pressing for further "
          "investment in regional transportation infrastructure now and later ").split(),
    "b": ("the junior senator noted separately that community leaders had requested this "
          "funding repeatedly and that the delegation intends to seek additional "
          "appropriations during the coming budget negotiation season ahead ").split(),
}


def _body(ngram: str, variant: str) -> str:
    """One announcement in two letterheads: a shared body plus each office's own block."""
    return " ".join([*_SHARED, ngram, *_OWN[variant], ngram, "."])


def _statement(sid: str, bioguide: str, url: str, title: str, text: str, *, state="NV") -> dict:
    return {
        "id": sid, "lane": 1, "published_at": DAY, "syndicated": False, "joint_group": None,
        "url": url, "title": title, "text": text,
        "member": {"bioguide": bioguide, "party": "D", "state": state},
    }


def _live_evidence() -> dict:
    return util.read_json(config.DERIVED / "phrase-evidence.json", {}) or {}


def _receipts_for(slug: str) -> list[dict]:
    record = (_live_evidence().get("phrases") or {}).get(slug) or {}
    return list(record.get("receipts") or PINNED_RECEIPTS.get(slug) or PINNED_RECEIPTS[DEFECTIVE_SLUGS[0]])


def _ngram_for(slug: str) -> str:
    data = util.read_json(config.DERIVED / "phrases" / f"{slug}.json", {}) or {}
    return data.get("ngram") or "airport to rehabilitate"


def _nevada_pair(ngram: str) -> tuple[list[dict], dict]:
    urls = list(NEVADA_TITLES)
    statements = [
        _statement("s-cm", "C001113", urls[0], NEVADA_TITLES[urls[0]], _body(ngram, "a")),
        _statement("s-ro", "R000608", urls[1], NEVADA_TITLES[urls[1]], _body(ngram, "b")),
    ]
    roster_map = {"C001113": {"name": "Catherine Cortez Masto"},
                  "R000608": {"name": "Jacky Rosen"}}
    return statements, roster_map


# --- the identity itself -------------------------------------------------------------------

def test_the_nevada_pair_is_below_the_near_duplicate_bar_and_still_one_unit():
    """The similarity bar is untouched; the cosign decision is what collapses the pair."""
    ngram = _ngram_for(DEFECTIVE_SLUGS[0])
    statements, roster_map = _nevada_pair(ngram)
    left, right = (document_families.shingles(s["text"]) for s in statements)
    similarity = document_families.exact_similarity(left, right)
    assert similarity < config.DOCUMENT_FAMILY_JACCARD, similarity

    document_families.apply_families(statements, roster_map)
    assert _unit_key(statements[0]) == _unit_key(statements[1])
    assert str(statements[0]["joint_group"]).startswith("cosign:")
    assert statements[0]["document_family"]["duplicate_class"] == "cosigned"


def test_the_collapsed_group_is_a_group_prefix_and_never_reported_as_a_member():
    ngram = _ngram_for(DEFECTIVE_SLUGS[0])
    statements, roster_map = _nevada_pair(ngram)
    document_families.apply_families(statements, roster_map)
    key = str(_unit_key(statements[0]))
    assert key.startswith(document_families.UNIT_GROUP_PREFIXES)
    assert "cosign:" in document_families.UNIT_GROUP_PREFIXES


def test_two_offices_sharing_a_surname_are_not_a_cosigned_pair():
    """A shared surname is not evidence that either office named the other."""
    ngram = "shared surname phrase"
    statements, _ = _nevada_pair(ngram)
    statements[0]["title"] = "Smith, Smith Announce Funding"
    statements[1]["title"] = "Smith, Smith Announce Funding for the Region"
    roster_map = {"C001113": {"name": "Adrian Smith"}, "R000608": {"name": "Chris Smith"}}
    document_families.apply_families(statements, roster_map)
    assert _unit_key(statements[0]) != _unit_key(statements[1])


def test_an_unrelated_pair_that_names_each_other_is_not_collapsed():
    """Reciprocal naming decides only among documents retrieval already paired."""
    statements, roster_map = _nevada_pair("unrelated topic phrase")
    statements[0]["text"] = ("the senator applauded a new medicare coverage decision for "
                             "prescription treatments after a long review by the agency " * 4)
    statements[1]["text"] = ("the senator pressed the secretary on civilian protection "
                             "policy at the pentagon during an oversight hearing today " * 4)
    document_families.apply_families(statements, roster_map)
    assert _unit_key(statements[0]) != _unit_key(statements[1])


def test_a_missing_roster_leaves_every_unit_key_untouched():
    """apply_families without a roster is the pre-S66 behaviour, never a crash."""
    statements, _ = _nevada_pair(_ngram_for(DEFECTIVE_SLUGS[0]))
    document_families.apply_families(statements)
    assert _unit_key(statements[0]) != _unit_key(statements[1])


# --- production-shaped: the real receipts, the healed verdict ------------------------------

def test_each_defective_page_falls_below_quorum_on_its_real_receipts():
    for slug in DEFECTIVE_SLUGS:
        ngram = _ngram_for(slug)
        receipts = _receipts_for(slug)
        roster_map: dict[str, dict] = {}
        statements = []
        for index, receipt in enumerate(receipts):
            bioguide = f"Z{index:06d}"
            roster_map[bioguide] = {"name": receipt["member"]}
            title = NEVADA_TITLES.get(receipt["url"], f"{receipt['member']} Issues a Statement")
            variant = "a" if receipt["url"] == list(NEVADA_TITLES)[0] else "b"
            text = (_body(ngram, variant) if receipt["url"] in NEVADA_TITLES
                    else f"unrelated office language {ngram} in its own release " * 6)
            statements.append({
                "id": f"{slug}-{index}", "lane": 1, "published_at": receipt["date"],
                "syndicated": False, "joint_group": None, "url": receipt["url"],
                "title": title, "text": text,
                "member": {"bioguide": bioguide, "party": receipt["party"],
                           "state": receipt["state"]},
            })
        document_families.apply_families(statements, roster_map)
        record = phrase_evidence._build_one(ngram, DAY, statements, roster_map)
        assert record["grounded_units"] == 2, (slug, record)
        assert record["grounded_units"] < phrase_evidence.QUORUM


def test_a_control_phrase_with_three_distinct_units_keeps_its_evidentiary_section():
    ngram = "the program and"
    roster_map, statements = {}, []
    for index, name in enumerate(("Adam B. Schiff", "Christopher A. Coons", "Pete Aguilar")):
        bioguide = f"Y{index:06d}"
        roster_map[bioguide] = {"name": name}
        statements.append(_statement(
            f"control-{index}", bioguide, f"https://office{index}.senate.gov/news/release",
            f"{name.split()[-1]} Statement on the Program",
            f"each office wrote its own release about {ngram} the appropriation this week",
            state="CA"))
    document_families.apply_families(statements, roster_map)
    record = phrase_evidence._build_one(ngram, DAY, statements, roster_map)
    assert record["grounded_units"] == 3
    phrase = {"ngram": ngram, "slug": "control", "first_seen": {"date": DAY},
              "series": [{"day": DAY, "D": 3, "R": 0, "I": 0}]}
    body = site.phrase_page_body(phrase, evidence={"phrases": {"control": record}})
    assert "Peak-day evidence" in body


def test_the_defective_pages_lose_their_evidentiary_claim_when_below_quorum():
    for slug in DEFECTIVE_SLUGS:
        phrase = {"ngram": _ngram_for(slug), "slug": slug, "first_seen": {"date": DAY},
                  "series": [{"day": DAY, "D": 3, "R": 0, "I": 0}]}
        assert "Peak-day evidence" not in site.phrase_page_body(phrase, evidence={"phrases": {}})


# --- the identity is stamped once and inherited (docs/37 rules 1 and 6) --------------------

def _evidence_root(root: Path) -> Path:
    (root / "phrases").mkdir(parents=True)
    (root / "phrases" / "control.json").write_text(json.dumps({
        "ngram": "the program and", "slug": "control", "first_seen": {"date": DAY},
        "series": [{"day": DAY, "D": 3, "R": 0, "I": 0}]}), encoding="utf-8")
    return root


def test_the_evidence_artifact_inherits_the_live_unit_identity_version():
    with tempfile.TemporaryDirectory() as td:
        root = _evidence_root(Path(td) / "derived")
        artifact, _stats = phrase_evidence.build_phrase_evidence(
            [], root, cache_path=Path(td) / "cache.json", rmap={})
    assert artifact["unit_identity_method"] == document_families.METHOD_VERSION


def test_a_bumped_unit_identity_invalidates_every_cached_quorum():
    """A cached count measured under a superseded collapse is never served (rule 1)."""
    with tempfile.TemporaryDirectory() as td:
        root = _evidence_root(Path(td) / "derived")
        cache = Path(td) / "cache.json"
        _first, first_stats = phrase_evidence.build_phrase_evidence(
            [], root, cache_path=cache, rmap={})
        _warm, warm_stats = phrase_evidence.build_phrase_evidence(
            [], root, cache_path=cache, rmap={})
        original = document_families.METHOD_VERSION
        try:
            document_families.METHOD_VERSION = original + "-probe"
            _bumped, bumped_stats = phrase_evidence.build_phrase_evidence(
                [], root, cache_path=cache, rmap={})
        finally:
            document_families.METHOD_VERSION = original
    assert first_stats["cache_misses"] == 1
    assert warm_stats["cache_hits"] == 1
    assert bumped_stats["cache_hits"] == 0 and bumped_stats["cache_misses"] == 1


# --- the correction is on the public record ------------------------------------------------

def test_the_three_pages_are_disclosed_in_the_public_corrections_ledger():
    from pipeline import corrections
    rows = corrections.load()
    covering = [row for row in rows if all(slug in json.dumps(row) for slug in DEFECTIVE_SLUGS)]
    assert covering, "no correction discloses the three double-counted phrase pages"
    row = covering[0]
    assert DAY in row["affected_days"]
    assert row["severity"] in corrections.SEVERITY_CLASSES
