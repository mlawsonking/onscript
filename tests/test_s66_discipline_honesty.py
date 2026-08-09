"""S66-5 acceptance: discipline.json says what it is, inside the file.

docs/39, the low findings. The artifact ships committed in a public repository. It carried
per-day indices with no interpretation floor (91 Democratic and 122 Republican days at exactly
1.0, every one of them from 19 statements or fewer, and 44 of those from three statements or
fewer), while its withdrawal under R-36.3 was recorded only in build.py and in the day records.
Nothing renders it, so nobody inside the project ever read it back; a reader who found the file
had no way to learn from the file that the metric is withdrawn or that a 1.0 on a
three-statement day means almost nothing. Its window also started 2025-01-01, two days before
config.STAGE1_EPOCH, against the standing rule that the public epoch has one authority.

The stamp is additive: the per-party series keep their place and their row shape, the floor is
recorded and NOT applied to any value, and only the pre-epoch rows leave.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from pipeline import build, config


DAY = "2026-07-18"


def _raw() -> dict:
    return {
        "D": {"2025-01-01": {"statements": 3, "on_message_units": 3, "index": 1.0},
              "2025-01-02": {"statements": 2, "on_message_units": 2, "index": 1.0},
              config.STAGE1_EPOCH: {"statements": 4, "on_message_units": 4, "index": 1.0},
              DAY: {"statements": 40, "on_message_units": 12, "index": 0.3}},
        "R": {"2025-01-02": {"statements": 1, "on_message_units": 1, "index": 1.0},
              DAY: {"statements": 30, "on_message_units": 6, "index": 0.2}},
    }


# --- the stamp -------------------------------------------------------------------------------

def test_the_artifact_declares_its_own_withdrawal():
    artifact = build.public_discipline_artifact(_raw())
    assert artifact["status"] == "withdrawn"
    assert artifact["reason"] == build.DISCIPLINE_WITHDRAWN_REASON
    assert "participation-measures-v1" in artifact["reason"]


def test_the_artifact_declares_the_floor_below_which_the_index_is_unreadable():
    artifact = build.public_discipline_artifact(_raw())
    assert artifact["min_statements"] == config.CONCORDANCE_MIN_STATEMENTS
    assert artifact["min_statements_note"] == build.DISCIPLINE_MIN_STATEMENTS_NOTE
    assert artifact["days_below_min_statements"] == {"D": 1, "R": 0}


def test_the_window_starts_at_the_one_epoch_authority():
    artifact = build.public_discipline_artifact(_raw())
    assert artifact["window"]["start"] == config.STAGE1_EPOCH
    assert artifact["window"]["epoch_authority"] == "config.STAGE1_EPOCH"
    assert artifact["window"]["end"] == DAY
    for party in ("D", "R"):
        assert all(day >= config.STAGE1_EPOCH for day in artifact[party])
    assert "2025-01-01" not in artifact["D"] and "2025-01-02" not in artifact["R"]


# --- additive and schema-compatible ------------------------------------------------------------

def test_the_series_keep_their_place_and_their_row_shape():
    artifact = build.public_discipline_artifact(_raw())
    assert set(artifact["D"][DAY]) == {"statements", "on_message_units", "index"}
    assert artifact["D"][DAY] == _raw()["D"][DAY]
    assert artifact["R"][DAY] == _raw()["R"][DAY]


def test_the_floor_is_stamped_and_never_applied_to_a_measurement():
    """A thin day keeps its raw values; the artifact says how to read them, it does not edit them."""
    artifact = build.public_discipline_artifact(_raw())
    thin = artifact["D"][config.STAGE1_EPOCH]
    assert thin["statements"] == 4 and thin["index"] == 1.0
    assert thin["statements"] < artifact["min_statements"]


def test_stamping_a_stamped_artifact_is_idempotent():
    """scripts/regen_derived.py reads this file and passes it straight back into the builder."""
    once = build.public_discipline_artifact(_raw())
    twice = build.public_discipline_artifact(once)
    assert once == twice
    assert set(twice) - set(build.DISCIPLINE_ARTIFACT_KEYS) == {"D", "R"}


def test_no_reserved_key_can_collide_with_a_party_code():
    for key in build.DISCIPLINE_ARTIFACT_KEYS:
        assert len(key) > 1
    for party in (*config.ALL_PARTIES, *config.COMPOSITE_PARTIES):
        assert party not in build.DISCIPLINE_ARTIFACT_KEYS


def test_an_empty_discipline_map_still_produces_a_readable_artifact():
    artifact = build.public_discipline_artifact({})
    assert artifact["status"] == "withdrawn"
    assert artifact["window"]["end"] is None
    assert artifact["days_below_min_statements"] == {}


# --- the production write path -----------------------------------------------------------------

def test_the_builder_writes_the_stamped_artifact_not_the_raw_map():
    ledger = {"border security funding": {
        "ngram": "border security funding", "n": 3, "df_weight": 1.0,
        "first_seen": {"date": DAY, "party": "D", "member": "B000001"},
        "daily": {DAY: {"D": 3, "R": 0, "members_D": ["B000001", "B000002", "B000003"],
                        "members_R": []}}}}
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "phrases").mkdir()
        (root / "days").mkdir()
        build.build_derived([], ledger, _raw(), root, focus_day=DAY, coverage={"2026": {}})
        written = json.loads((root / "discipline.json").read_text(encoding="utf-8"))
    assert written["status"] == "withdrawn"
    assert written["min_statements"] == config.CONCORDANCE_MIN_STATEMENTS
    assert written["window"]["start"] == config.STAGE1_EPOCH
    assert "2025-01-01" not in written["D"]
    assert written["D"][DAY]["index"] == 0.3
