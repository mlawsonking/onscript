"""P1: collect phase timing instrumentation.

The 2026-07-28/29 collect timeouts had to be diagnosed from an outage because no stage published
its own cost: the run log carried a single total and the corpus walk hid inside it. These tests
hold the instrumentation to the two properties that make it worth having. It reports even when
the stage it times fails, and the restore hand-off across the workflow-step seam actually reads
back where the next process looks for it.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import archive_restore, deterministic, privacy, util  # noqa: E402
from tests.test_privacy import PERSON_A, gate  # noqa: E402


def _isolated_timings():
    util.reset_stage_timings()
    return util.stage_timings()


def test_stage_timer_records_a_stage_and_repeat_names_accumulate():
    """Two mirror reads cost the run both of them; reporting only the cheaper one would hide
    exactly the growth this instrumentation exists to surface."""
    _isolated_timings()
    with util.stage_timer("unit_stage"):
        pass
    first = util.stage_timings()["unit_stage"]
    with util.stage_timer("unit_stage"):
        pass
    second = util.stage_timings()["unit_stage"]
    assert first >= 0.0
    assert second >= first, "a repeated stage name must accumulate, never overwrite"
    util.reset_stage_timings()
    assert util.stage_timings() == {}


def test_stage_timer_still_reports_when_the_timed_stage_raises():
    """A stage that dies is the stage whose cost matters most. An instrument that only reports on
    success cannot describe the run that hit the ceiling."""
    _isolated_timings()

    class Boom(RuntimeError):
        pass

    try:
        with util.stage_timer("failing_stage"):
            raise Boom("stage died")
    except Boom:
        pass
    else:  # pragma: no cover - the timer must never swallow the exception
        raise AssertionError("stage_timer swallowed the exception from its body")
    assert "failing_stage" in util.stage_timings()
    util.reset_stage_timings()


def test_a_broken_detail_callback_never_breaks_the_stage_it_measures():
    """Instrumentation is not allowed to author an outage (docs/37 rule 4, in miniature)."""
    _isolated_timings()

    def explode():
        raise ValueError("no counters here")

    with util.stage_timer("detail_stage", detail_fn=explode):
        pass
    assert "detail_stage" in util.stage_timings()
    util.reset_stage_timings()


def test_the_restore_hand_off_is_written_where_the_collect_process_reads_it():
    """The restore runs in its own workflow step, so its cost crosses a process seam as a file.
    Two copies of a shape drift (docs/37 rule 1), so the contract is asserted across the seam
    rather than by trusting archive_restore and util to agree about a literal."""
    _isolated_timings()
    with tempfile.TemporaryDirectory() as raw:
        checkout = Path(raw)
        written = archive_restore.publish_restore_timing(checkout, 12.34)
        assert written is not None and written.is_file()
        assert written == checkout / archive_restore.STAGE_TIMING_RELPATH

        adopted = util.adopt_stage_timings(written)
        assert adopted == {"restore": 12.3}, adopted
        assert util.stage_timings()["restore"] == 12.3

        # The published document is ordinary JSON with no run-local structure beyond seconds.
        doc = json.loads(written.read_text(encoding="utf-8"))
        assert doc["schema_version"] == 1
        assert set(doc["stages"]) == {"restore"}
    util.reset_stage_timings()


def test_adopting_a_missing_or_malformed_hand_off_costs_a_log_line_not_the_run():
    _isolated_timings()
    with tempfile.TemporaryDirectory() as raw:
        assert util.adopt_stage_timings(Path(raw) / "absent.json") == {}
        bad = Path(raw) / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        assert util.adopt_stage_timings(bad) == {}
        wrong = Path(raw) / "wrong.json"
        wrong.write_text(json.dumps({"stages": {"restore": "not-a-number"}}), encoding="utf-8")
        assert util.adopt_stage_timings(wrong) == {}
    assert util.stage_timings() == {}


def test_the_span_scan_is_accounted_separately_from_the_rest_of_the_ledger_build():
    """The ledger build's total is what grew; the span scan is WHY. The two halves of the scan
    have separate remedies, so they are counted separately: the admitted-form sweep is a keyed
    hash over every token window, the capitalized-sequence walk is a regex pass."""
    with gate():
        privacy.reset_span_stats()
        assert privacy.span_stats()["person_spans_calls"] == 0

        privacy.person_spans(f"policy accountability after {PERSON_A} needs action",
                             roster_map={})
        stats = privacy.span_stats()
        assert stats["person_spans_calls"] == 1
        assert stats["person_spans_s"] >= 0.0
        assert stats["admitted_form_scans"] == 1, (
            "the admitted-form sweep must be counted on its own, not folded into the total")

        detail = deterministic._ledger_detail()
        for field in ("span_scan_s=", "span_scan_calls=", "admitted_form_s=",
                      "admitted_form_scans="):
            assert field in detail, detail
        privacy.reset_span_stats()


def test_the_accounting_wrapper_does_not_change_what_person_spans_returns():
    """Instrumentation that alters the verdict is worse than no instrumentation."""
    with gate():
        text = f"workers demand fair wages and {PERSON_A} deserves accountability now"
        counted = privacy.person_spans(text, roster_map={})
        uncounted = privacy._person_spans(text, None, {})
        assert counted == uncounted
        assert any(row["classification"] == "private" for row in counted)
