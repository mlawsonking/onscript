"""Y2 acceptance: discipline withdrawal (R-36.3).

The discipline index leaves the top level of newly generated day records and moves
to a labeled legacy_unvalidated_metrics carrier with status withdrawn and a reason.
Historical committed records are not rewritten; a read-time helper renders the
metric withdrawn for both shapes.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from pipeline import build, config, util


def _fresh_day_record() -> dict:
    """Build one non-final day record through the production build path."""
    day = "2026-05-15"
    ledger = {
        "border security is broken": {
            "ngram": "border security is broken", "n": 4, "df_weight": 1.0,
            "first_seen": {"date": day, "party": "D", "member": "X"},
            "daily": {day: {"D": 2, "R": 4, "members_D": ["A", "B"], "members_R": ["C", "D", "E", "F"]}},
        },
    }
    discipline = {
        "D": {day: {"statements": 5, "on_message_units": 4, "index": 0.8}},
        "R": {day: {"statements": 6, "on_message_units": 6, "index": 1.0}},
    }
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        (out / "days").mkdir(parents=True, exist_ok=True)
        (out / "phrases").mkdir(parents=True, exist_ok=True)
        build.build_derived([], ledger, discipline, out, focus_day=day, coverage={})
        return util.read_json(out / "days" / f"{day}.json", {})


def test_a_freshly_built_day_record_has_no_top_level_discipline():
    record = _fresh_day_record()
    assert "discipline" not in record


def test_a_freshly_built_day_record_carries_the_withdrawn_legacy_metric():
    record = _fresh_day_record()
    carrier = record["legacy_unvalidated_metrics"]
    assert carrier["status"] == "withdrawn"
    assert carrier["reason"].strip()
    # The withdrawn values are retained under the labeled carrier, not deleted.
    discipline = carrier["metrics"]["discipline"]
    assert discipline["D"]["index"] == 0.8
    assert discipline["R"]["index"] == 1.0


def test_the_withdrawn_view_reads_a_new_record_as_withdrawn():
    view = build.withdrawn_discipline_view(_fresh_day_record())
    assert view["status"] == "withdrawn"
    assert view["reason"].strip()
    assert view["metrics"]["discipline"]["D"]["index"] == 0.8


def test_reading_a_real_historical_record_renders_the_metric_withdrawn():
    # The committed 2026-07-24 record stores discipline top level (index 0.7692 / 0.8358)
    # and must not be rewritten. The read-time helper still returns it as withdrawn.
    committed = util.read_json(config.DERIVED / "days" / "2026-07-24.json", {})
    assert committed.get("day") == "2026-07-24"
    assert isinstance(committed.get("discipline"), dict), "historical record keeps its top-level field"
    view = build.withdrawn_discipline_view(committed)
    assert view["status"] == "withdrawn"
    assert view["reason"].strip()
    assert view["metrics"]["discipline"]["D"]["index"] == 0.7692


def test_the_committed_2026_07_25_record_the_review_cited_reads_withdrawn():
    committed = util.read_json(config.DERIVED / "days" / "2026-07-25.json", {})
    assert committed.get("day") == "2026-07-25"
    view = build.withdrawn_discipline_view(committed)
    assert view["status"] == "withdrawn"
    # index 1.0 both parties beside participation of 0/3 and 0/2 (the reviewer's example)
    assert view["metrics"]["discipline"]["D"]["index"] == 1.0
    assert view["metrics"]["discipline"]["R"]["index"] == 1.0
