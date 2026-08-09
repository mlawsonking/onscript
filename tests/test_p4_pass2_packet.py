"""The pass-2 packet, checked against the real rendered bundle (docs/37 rule 2).

Pass 1 was ruled to have read the sentences rather than the phrases, so pass 2 re-issues the
same sealed 200 items under the amended guide and the app that gates the message class on task
B. These assertions run against the committed packet, not a synthetic item, because blinding
and coverage are integration properties.

Blinding is asserted on JSON keys, not substrings. A real bundle carries members' own prose,
and that prose contains ordinary words like "priority" and "surge"; a substring test over real
corpus text reports a leak that is not there.
"""
import csv
import io
import json
from pathlib import Path

from pipeline import config

BUNDLE = Path(config.REPO_ROOT) / "evaluation" / "goldset" / "bundles" / "pilot"
GOLDSET = Path(config.REPO_ROOT) / "evaluation" / "goldset"

MACHINE_FIELDS = ("predicted_class", "predicted_family_id", "predicted_family_revision",
                  "impact_tags", "priority", "classifier_rule", "seal_hash", "split",
                  "lane", "family_evidence_count", "member_count", "quoted_speaker_detected")


def _ids(path):
    return [r["candidate_id"] for r in
            csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
            if (r.get("candidate_id") or "").strip()]


def _sealed_ids():
    return [row["candidate_id"] for row in
            json.loads((GOLDSET / "pilot.sample.json").read_text(encoding="utf-8"))["candidates"]]


def _app():
    return (BUNDLE / "michael-pass2.app.html").read_text(encoding="utf-8")


def test_pass_two_covers_the_same_sealed_200_items():
    assert sorted(_ids(BUNDLE / "michael-pass2.answersheet.csv")) == sorted(_sealed_ids())


def test_pass_two_ships_a_blank_answer_sheet():
    rows = list(csv.DictReader(io.StringIO(
        (BUNDLE / "michael-pass2.answersheet.csv").read_text(encoding="utf-8"))))
    assert len(rows) == 200
    assert not any((r.get("gold_class") or "").strip() for r in rows)
    assert not any((r.get("gold_family_id") or "").strip() for r in rows)


def test_pass_two_presents_the_items_in_a_different_order_than_pass_one():
    """A fresh per-annotator order, so position carries nothing forward from pass 1."""
    first, second = _ids(BUNDLE / "michael-pass1.answersheet.csv"), \
        _ids(BUNDLE / "michael-pass2.answersheet.csv")
    assert sorted(first) == sorted(second)
    assert first != second
    assert sum(1 for a, b in zip(first, second) if a == b) == 0


def test_pass_two_resumes_under_its_own_storage_key():
    """The app autosaves per annotator id. A shared key would preload the pass-1 answers."""
    app = _app()
    assert "'onscript-goldset-' + DATA.sample + '-' + DATA.annotator" in app
    payload = json.loads(app.split('id="goldset-data" type="application/json">')[1]
                         .split("</script>")[0].replace("<\\/", "</"))
    assert payload["annotator"] == "michael-pass2"
    assert payload["sample"] == "pilot"
    assert len(payload["items"]) == 200


def test_pass_two_carries_no_machine_signal():
    """Blinding, on the real bundle, by field rather than by word."""
    app = _app()
    payload = json.loads(app.split('id="goldset-data" type="application/json">')[1]
                         .split("</script>")[0].replace("<\\/", "</"))
    for item in payload["items"]:
        for field in MACHINE_FIELDS:
            assert field not in item, field
        assert set(item) <= {"candidate_id", "phrase", "before", "sentence", "after",
                             "title", "office", "date", "support"}
    for field in MACHINE_FIELDS:
        assert f'"{field}":' not in app, field


def test_pass_two_is_self_contained_and_offline():
    app = _app()
    assert app.startswith("<!doctype html>")
    assert "http://" not in app and "https://" not in app
    assert "<link" not in app and " src=" not in app


def test_pass_two_carries_the_corrected_instructions():
    app = _app()
    assert "Unknown is the safe default" in app
    assert "Label the <b>phrase</b>, not the sentence" in app
    assert "B. phrase complete *" in app
    assert "messageBlockedBy" in app


def test_the_pass_one_bundle_is_untouched_by_the_re_issue():
    """docs/35 section 10.6 publishes the packet byte for byte as it was annotated."""
    sheet = list(csv.DictReader(io.StringIO(
        (BUNDLE / "michael.answersheet.csv").read_text(encoding="utf-8"))))
    assert len(sheet) == 200
    assert not any((r.get("gold_class") or "").strip() for r in sheet)
    for name in ("michael.app.html", "michael.packet.html"):
        assert (BUNDLE / name).is_file()


def test_the_publish_certificate_covers_every_published_file():
    """A partial re-render must not leave earlier bundle files published and uncertified."""
    cert = json.loads((BUNDLE / "PUBLISH-CHECK.json").read_text(encoding="utf-8"))
    assert cert["admitted_forms_found"] == 0
    certified = {row["path"] for row in cert["files"]}
    on_disk = {p.name for p in BUNDLE.iterdir()
               if p.is_file() and p.name != "PUBLISH-CHECK.json"}
    assert on_disk <= certified, on_disk - certified
    for required in ("michael.app.html", "michael.packet.html",
                     "michael-pass1.answersheet.csv", "michael-pass2.app.html",
                     "model-rater.answersheet.csv"):
        assert required in certified, required
