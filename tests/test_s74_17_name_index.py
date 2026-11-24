"""S74-17 Package A: the refreshed bill-and-committee name index (committed reference tables).

Real committed artifacts, validated as a pinned record (docs/37 rule 3): the tables carry their fetch
date and provenance, the verdicts were measured on the production corpus, and the verdict domain
covers bill-title phrases the claim clusterer offers. The last point is the regression this refresh
found: a domain counted through the person-span gate kept 726 tagged phrases of 9,418 and lost
titles published as talking points.
"""
from __future__ import annotations

import json

from pipeline import config, nomenclature

REF = config.REFERENCE / "nomenclature"


def _load(name):
    return json.loads((REF / name).read_text(encoding="utf-8"))


def test_the_tables_are_the_2026_11_23_refresh_on_the_production_corpus():
    bills, verdicts, committees = (_load("bill-titles-119.json"), _load("verdicts-119.json"),
                                   _load("committee-names.json"))
    assert bills["fetch_date"] == committees["fetch_date"] == verdicts["fetch_date"] == "2026-11-23"
    assert verdicts["index_version"] == "2026-11-23" == nomenclature.index_version()
    assert verdicts["counts"]["corpus_statements"] == 91200
    assert bills["bills_parsed"] >= 20000 and len(bills["names"]) >= 15000
    assert "WITHOUT the person-span gate" in verdicts["domain"]
    assert any(a["date"] == "2026-11-23" for a in verdicts["amendments"])


def test_published_bill_title_talking_points_carry_a_verdict():
    """The phrases the July table could not judge, and the one the gated domain dropped."""
    for phrase in ("the bipartisan american affordability", "of the lindsey o",
                   "graham sanctioning russia and iran", "care of america’s veterans act"):
        verdict = nomenclature.is_nomenclature(phrase, 119)
        assert verdict and verdict["lane"] == "bill", phrase
    # The ACA ruling still holds on the refreshed table (docs/23 7.2.1).
    assert nomenclature.is_nomenclature("affordable care act", 119) is None
