"""S74-11 Package 2 (F2): the nomenclature gate survives a new Congress.

On 2027-01-03 util.congress_for_date returns 120 and no verdicts-120.json exists. The lookup falls
back to the highest committed table at or below the requested Congress, stamps the fallback, and
never reads a later table. Tested against the committed verdicts-119 table, not a fixture.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pipeline import config, eligibility, nomenclature, nomenclature_build, util

ROOT = Path(__file__).resolve().parents[1]
VERDICTS_119 = ROOT / "data" / "reference" / "nomenclature" / "verdicts-119.json"


def _tagged_119() -> list[str]:
    table = json.loads(VERDICTS_119.read_text(encoding="utf-8"))
    return [ngram for ngram, row in (table.get("verdicts") or {}).items()
            if row["ratio"] >= config.NOMENCLATURE_RATIO_MIN]


def test_every_phrase_tagged_in_119_keeps_its_class_on_2027_01_04():
    assert not (VERDICTS_119.parent / "verdicts-120.json").exists()  # the case under test
    tagged = _tagged_119()
    assert len(tagged) > 1000, len(tagged)
    assert util.congress_for_date("2027-01-04") == 120
    changed = []
    for ngram in tagged:
        before = eligibility.classify_phrase(ngram, day="2027-01-02", family_count=5)
        after = eligibility.classify_phrase(ngram, day="2027-01-04", family_count=5)
        if before["surface_class"] != after["surface_class"]:
            changed.append((ngram, before["surface_class"], after["surface_class"]))
    assert not changed, (len(changed), changed[:5])


def test_the_fallback_is_stamped_and_a_congress_with_its_own_table_is_unstamped():
    ngram = _tagged_119()[0]
    own = nomenclature.is_nomenclature(ngram, 119)
    assert own and "verdicts_congress" not in own and "verdicts_fallback_for" not in own
    fallback = nomenclature.is_nomenclature(ngram, 120)
    assert fallback["verdicts_congress"] == 119 and fallback["verdicts_fallback_for"] == 120
    assert {k: v for k, v in fallback.items() if not k.startswith("verdicts_")} == own
    classified = eligibility.classify_phrase(ngram, day="2027-01-04", family_count=5)
    assert classified["classifier"]["verdicts_congress"] == 119
    assert "verdicts_congress" not in eligibility.classify_phrase(
        ngram, day="2026-11-20", family_count=5)["classifier"]
    assert nomenclature.judging_congress(119) == 119
    assert nomenclature.judging_congress(125) == 119
    # The anachronism guard: an earlier Congress is never judged by a later table.
    assert nomenclature.judging_congress(118) is None
    assert nomenclature.is_nomenclature(ngram, 118) is None
    assert nomenclature.index_version(120) == nomenclature.index_version(119)


def test_a_window_straddling_january_3_applies_one_rule():
    days = ["2026-12-30", "2026-12-31", "2027-01-01", "2027-01-02", "2027-01-03", "2027-01-04",
            "2027-01-05"]
    assert {util.congress_for_date(d) for d in days} == {119, 120}
    for ngram in _tagged_119()[:300]:
        verdicts = {json.dumps({k: v for k, v in (nomenclature.is_nomenclature(
            ngram, util.congress_for_date(d)) or {}).items() if not k.startswith("verdicts_")},
            sort_keys=True) for d in days}
        assert len(verdicts) == 1, ngram
        classes = {eligibility.classify_phrase(ngram, day=d, family_count=5)["surface_class"]
                   for d in days}
        assert len(classes) == 1, (ngram, classes)


def test_the_builder_range_includes_the_seated_congress():
    today = util.congress_for_date(date.today().isoformat())
    assert nomenclature_build.CONGRESSES[0] == 113
    assert nomenclature_build.CONGRESSES[-1] == today
    assert today in nomenclature_build.CONGRESSES
    source = (ROOT / "pipeline" / "nomenclature_build.py").read_text(encoding="utf-8")
    assert "range(113, 120)" not in source
