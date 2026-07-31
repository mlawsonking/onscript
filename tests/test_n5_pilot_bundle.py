"""N5 acceptance: Michael's pilot bundle is publication grade (docs/35 section 10.6).

The bundle publishes openly, so it clears the same privacy floor as any public artifact,
proven by the existing production canary rather than by a new bespoke check. The committed
bundle is validated as what it is: a pinned kit whose publish certificate, answer sheet, and
seal agree with each other and with the sealed pilot.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile

from pipeline import config, goldset_bundle, privacy, privacy_canary


GOLDSET = Path(config.REPO_ROOT) / "evaluation" / "goldset"
BUNDLE = GOLDSET / "bundles" / "pilot"
RUNBOOK = GOLDSET / "PILOT-RUNBOOK.md"
RATER = "michael"


def _temp_files(contents: list[str]) -> tuple[tempfile.TemporaryDirectory, list[Path]]:
    holder = tempfile.TemporaryDirectory()
    paths = []
    for index, text in enumerate(contents):
        path = Path(holder.name) / f"file{index}.html"
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return holder, paths


def test_a_clean_bundle_certifies_with_the_production_canary():
    holder, paths = _temp_files(["<p>public budget policy</p>", "candidate_id,gold_class\n"])
    try:
        certificate = goldset_bundle.certify_publishable(paths)
    finally:
        holder.cleanup()
    assert certificate["publishable"] is True
    assert certificate["files_scanned"] == 2
    assert certificate["admitted_forms_found"] == 0
    assert certificate["canary_version"] == privacy_canary.CANARY_VERSION
    assert all(len(row["sha256"]) == 64 and row["bytes"] > 0 for row in certificate["files"])


def test_a_failing_canary_refuses_before_any_file_is_called_clean():
    holder, paths = _temp_files(["<p>public budget policy</p>"])
    try:
        goldset_bundle.certify_publishable(paths, seed_failure=True)
    except privacy_canary.PrivacyCanaryError:
        pass
    else:
        raise AssertionError("a broken gate certified a bundle as publishable")
    finally:
        holder.cleanup()


def test_an_admitted_form_in_any_file_refuses_publication():
    holder, paths = _temp_files(["clean text", "text with a marked name"])
    original = privacy.contains_admitted_form
    try:
        privacy.contains_admitted_form = lambda text: "marked name" in text
        try:
            goldset_bundle.certify_publishable(paths)
        except privacy.PrivacyGateError as error:
            assert "file1.html" in str(error)
        else:
            raise AssertionError("a bundle carrying an admitted form was certified")
    finally:
        privacy.contains_admitted_form = original
        holder.cleanup()


def test_the_certificate_covers_every_file_the_bundle_ships():
    certificate = json.loads((BUNDLE / "PUBLISH-CHECK.json").read_text(encoding="utf-8"))
    manifest = json.loads((GOLDSET / "MANIFEST.json").read_text(encoding="utf-8"))
    assert certificate["publishable"] is True
    assert certificate["admitted_forms_found"] == 0
    assert certificate["seal_hash"] == manifest["seal_hash"]
    names = {row["path"] for row in certificate["files"]}
    # The pass-1 packet, which is what N5 sealed.
    assert {f"{RATER}.app.html", f"{RATER}.packet.html", f"{RATER}.answersheet.csv"} <= names
    # And every other file the bundle ships. The directory grew past N5's three when the model
    # rater's record and the pass-2 packet landed; a certificate naming only the original three
    # would leave the rest published and unscanned.
    shipped = {path.name for path in BUNDLE.iterdir()
               if path.is_file() and path.name != "PUBLISH-CHECK.json"}
    assert shipped <= names, shipped - names
    for row in certificate["files"]:
        assert (BUNDLE / row["path"]).is_file()


def test_the_answer_sheet_matches_the_sealed_pilot_exactly():
    sample = json.loads((GOLDSET / "pilot.sample.json").read_text(encoding="utf-8"))
    sealed = {row["candidate_id"] for row in sample["candidates"]}
    with (BUNDLE / f"{RATER}.answersheet.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [column for column in rows[0]] == goldset_bundle.ANSWER_COLUMNS
    assert {row["candidate_id"] for row in rows} == sealed
    assert len(rows) == sample["size"] == 200
    # A blank sheet: every answer column is empty and waiting for the human.
    assert all(row[column] == "" for row in rows for column in goldset_bundle.ANSWER_COLUMNS[1:])


def test_the_committed_packet_carries_no_machine_signal():
    # Field names and machine-minted identifiers only. Ordinary English words are not usable
    # as leak probes here: the packets quote real speech, which says "surge" and "priority".
    rendered = {
        "packet": (BUNDLE / f"{RATER}.packet.html").read_text(encoding="utf-8").lower(),
        "app": (BUNDLE / f"{RATER}.app.html").read_text(encoding="utf-8").lower(),
    }
    probes = ("predicted_class", "predicted_family_id", "classifier_rule", "impact_tags",
              "family_evidence_count", "member_headcount", "anchor_statement_id",
              "dfam:", "dfrev:", "sha256:")
    for name, text in rendered.items():
        for probe in probes:
            assert probe not in text, f"the {name} leaked {probe}"

    sample = json.loads((GOLDSET / "pilot.sample.json").read_text(encoding="utf-8"))
    for candidate in sample["candidates"]:
        for value in (candidate["classifier_rule"], candidate["predicted_family_id"],
                      candidate["anchor_statement_id"]):
            for name, text in rendered.items():
                assert str(value).lower() not in text, f"the {name} leaked {value}"


def test_the_runbook_states_the_label_and_refuses_the_claims_the_mode_cannot_make():
    from pipeline import goldset_single

    text = RUNBOOK.read_text(encoding="utf-8")
    assert goldset_single.PROVENANCE_LABEL in text
    for command in ("goldset_rate.py pilot", "goldset_intake.py pilot",
                    "goldset_metrics.py pilot"):
        assert command in text
    assert "--allow-api-spend" in text
    assert "Gate B" in text
    assert "inter-annotator reliability" in text
