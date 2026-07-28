"""Y7 acceptance: export semantic completeness (R-36.7).

Every nonprivate row in the phrase CSV and the API phrase resource carries a nonblank
surface class and classifier version, classified at emit time so historical committed
records that predate the fields are still self-describing.
"""
from __future__ import annotations

import csv
import io
import json

from pipeline import config, eligibility, status_exports, util


def _real_legacy_day():
    day = "2026-06-30"
    return [(day, util.read_json(config.DERIVED / "days" / f"{day}.json", {}))]


def test_the_legacy_record_rows_carry_no_class_so_the_exporter_must_derive_it():
    days = _real_legacy_day()
    rows = [row for _day, payload in days for row in payload.get("top_synchronized") or []]
    assert rows, "expected the real committed record to carry phrase rows"
    assert all("surface_class" not in row for row in rows)


def test_the_phrase_csv_carries_a_class_and_version_for_every_row():
    csv_bytes = status_exports.phrases_csv(_real_legacy_day())
    rows = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8"))))
    header, body = rows[0], rows[1:]
    class_at = header.index("surface_class")
    version_at = header.index("classifier_version")
    assert body, "expected exported phrase rows"
    for row in body:
        assert row[class_at], "blank surface class in the phrase CSV"
        assert row[version_at] == eligibility.CLASSIFIER


def test_the_api_phrase_resource_rows_carry_a_class_and_version():
    status = {"generated_at": "2026-07-27T12:00:00Z"}
    phrases = {"day": "2026-06-30",
               "by_peak": [{"ngram": "born in the united states", "party": "D", "day_peak": 8}]}
    exports = status_exports.experimental_exports(status, [], phrases, [])
    resource = json.loads(exports["api/v1/resources/phrases.json"])
    emitted = resource["payload"]["phrases"]
    assert emitted
    for row in emitted:
        assert row["surface_class"]
        assert row["classifier_version"] == eligibility.CLASSIFIER
        assert "classification_rule" in row and "surface_eligible" in row


def test_the_classifier_version_in_exports_is_the_live_authority():
    fields = status_exports._classified_phrase_row(
        {"ngram": "protect medicare now", "family_count": 4}, "2026-07-25")
    assert fields["classifier_version"] == eligibility.CLASSIFIER
    assert fields["surface_class"] and fields["classification_rule"]


def test_the_exporter_fails_closed_on_a_blank_class():
    saved = eligibility.classify_phrase
    try:
        eligibility.classify_phrase = lambda *a, **k: {
            "surface_class": "", "surface_eligible": False, "classifier": {"name": "", "rule": ""}}
        raised = False
        try:
            status_exports._classified_phrase_row({"ngram": "x"}, "2026-06-30")
        except ValueError:
            raised = True
        assert raised, "a blank nonprivate class must fail closed, never emit"
    finally:
        eligibility.classify_phrase = saved
