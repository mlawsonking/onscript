"""R4: the comparison report is checkable, honest about its mode, and recommends nothing.

The failure this guards against is a readable report that quietly reads as a green light while
the sample sits at one percent of the minimum. So the tests hold three things: every measured
number carries its denominator, a dry report says on its face that it is not evidence about the
candidate prompt, and no sentence in the document recommends the flip.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

from pipeline import replay_report, shadow_replay


ROOT = Path(__file__).resolve().parent.parent
DAYS = ROOT / "data" / "derived" / "days"
COMMITTED = ROOT / "data" / "derived" / "replay" / "comparison-report.md"


def _render():
    built = replay_report.build(DAYS)
    return replay_report.render(built["report"], evidence_rows=built["evidence_rows"])


def test_the_report_never_recommends_the_flip():
    text = _render().casefold()
    for phrase in ("we recommend", "recommendation:", "should activate", "ready to flip",
                   "safe to flip", "proceed with the flip"):
        assert phrase not in text, f"the report drifted into advocacy: {phrase!r}"
    assert "this report makes no flip recommendation" in text
    assert "the gate decides" in text


def test_every_measured_number_carries_its_denominators():
    text = _render()
    report = replay_report.build(DAYS)["report"]
    denominator = report["candidate"]["offered_party_days"]
    assert f"Denominator for every row: {denominator} scored party-days" in text
    for _, label, estimator, unit in replay_report.CHECKS:
        assert label in text and estimator in text
        assert f"| {unit} |" in text
    assert report["gate_progress"]["estimator"] in text
    assert report["gate_progress"]["unit"] in text
    assert report["candidate"]["fallback_rate_estimator"] in text


def test_the_gate_fraction_is_on_the_face_of_the_report():
    text = _render()
    progress = replay_report.build(DAYS)["report"]["gate_progress"]
    assert str(progress["complete_days"]["fraction"]) in text
    assert str(progress["party_days"]["fraction"]) in text
    assert "| Complete days | " in text and "| 60 |" in text
    assert "| Party-days | " in text and "| 200 |" in text
    assert "Ready to activate | False" in text


def test_a_dry_report_says_it_is_not_evidence_about_the_candidate_prompt():
    text = _render()
    assert "Mode: **dry_run**" in text
    assert "says nothing about the candidate prompt" in text
    assert "No dry row is admitted to the evidence file." in text


def test_the_eligibility_ladder_and_its_exclusions_are_published():
    text = _render()
    ladder = replay_report.build(DAYS)["report"]["ladder"]
    assert f"| Committed day files | {ladder['committed_day_files']} |" in text
    assert f"| Gate-eligible party-days | {ladder['gate_eligible_party_days']} |" in text
    for reason, count in ladder["exclusion_reasons"].items():
        assert f"| {reason} | {count} |" in text
    assert "docs/37 rule 13" in text


def test_the_quality_ranking_is_stated_and_reproducible():
    perfect = {"verifier_passed": True, "fallback": False,
               "guards": {name: [] for name in shadow_replay.GUARD_NAMES}}
    assert replay_report.quality_score(perfect) == 7
    broken = {"verifier_passed": False, "fallback": True,
              "guards": dict({name: [] for name in shadow_replay.GUARD_NAMES},
                             quote_extension=["x"])}
    assert replay_report.quality_score(broken) == 4
    text = _render()
    assert "Ranked by a stated score" in text
    assert "Ties break on day then party" in text


def test_a_tied_sample_says_it_cannot_separate_the_prompts():
    built = replay_report.build(DAYS)
    rows = built["report"]["party_day_results"]
    if len(rows) > 1 and len({replay_report.quality_score(row["candidate"])
                              for row in rows}) == 1:
        assert "cannot separate the prompts on quality" in _render()


def test_the_report_is_deterministic_and_carries_no_clock():
    first, second = _render(), _render()
    assert first == second
    for token in ("generated_at", "Generated on", "updated_at"):
        assert token not in first


def test_the_committed_report_is_a_valid_pinned_record():
    """The committed report is pinned history, validated as itself.

    Deliberately NOT asserted byte-equal to a fresh render: this report is built over
    data/derived/days, which production advances every day, so an equality test would turn the
    next published day into a suite failure. That is the exact shape docs/37 rule 3 names.
    Validate it as a canonical record instead: it parses, it is complete, and its own numbers
    agree with each other.
    """
    assert COMMITTED.is_file()
    text = COMMITTED.read_text(encoding="utf-8")
    assert text.startswith("# R-33.6 shadow replay")
    for heading in ("## Gate progress", "## Per-check results", "## Activation status",
                    "## Composite quality, side by side", "## Reproduce"):
        assert heading in text, f"the pinned report is missing {heading}"
    assert "this report makes no flip recommendation" in text.casefold()
    assert "| Ready to activate | False |" in text
    observed, required = None, None
    for line in text.splitlines():
        if line.startswith("| Complete days | "):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            observed, required = int(cells[1]), int(cells[2])
    assert required == 60 and observed is not None and observed < required, (
        "a pinned report claiming the sample minimum is met needs a much harder look")


def test_the_report_cli_writes_where_it_says_it_did():
    with tempfile.TemporaryDirectory() as raw:
        out = Path(raw) / "report.md"
        completed = subprocess.run(
            [sys.executable, "scripts/replay_report.py", "--days-dir", str(DAYS),
             "--evidence-root", raw, "--out", str(out)],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        assert completed.stdout.strip() == str(out)
        assert out.read_text(encoding="utf-8").startswith("# R-33.6 shadow replay")
