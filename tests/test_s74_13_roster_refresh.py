"""S74-13 Package 1 (R-74.15): the refreshed date-effective roster, and the party-switch split.

The roster was refreshed from unitedstates/congress-legislators at a pinned revision with
`--split-party-affiliations`. These tests hold the committed file to invariants that any refresh must
keep, whatever revision it pins, and hold the split to the rule that a party switch is effective on the
date its new affiliation starts, with the office seated on every day of the term.
"""
from __future__ import annotations

import collections
import importlib.util
from datetime import date, timedelta
from pathlib import Path

from pipeline import config, denominators

ROOT = Path(__file__).resolve().parents[1]


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_date_effective_roster", ROOT / "scripts" / "build_date_effective_roster.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _days(first: str, last: str):
    day = date.fromisoformat(first)
    while day.isoformat() <= last:
        yield day.isoformat()
        day += timedelta(days=1)


def test_every_day_from_the_epoch_to_the_horizon_seats_a_full_congress():
    table = denominators.load_roster()
    horizon = denominators.roster_horizon(table)
    assert horizon and horizon >= config.STAGE1_EPOCH, horizon
    checked = 0
    for iso in _days(config.STAGE1_EPOCH, horizon):
        chambers = collections.Counter()
        for row in table["offices"].values():
            interval = denominators.active_interval(row, iso)
            if interval and interval.get("voting_status", "voting") == "voting":
                chambers[interval.get("chamber")] += 1
        assert 425 <= chambers["House"] <= 435, (iso, chambers)
        assert 96 <= chambers["Senate"] <= 100, (iso, chambers)
        checked += 1
    assert checked == (date.fromisoformat(horizon) - date.fromisoformat(config.STAGE1_EPOCH)).days + 1


def test_no_interval_is_empty_and_no_office_has_overlapping_intervals():
    table = denominators.load_roster()
    empty, overlaps = [], []
    for bioguide, row in table["offices"].items():
        intervals = sorted(row["intervals"], key=lambda interval: interval.get("start") or "")
        for interval in intervals:
            start, end = interval.get("start"), interval.get("end_exclusive")
            if not start or not end or start >= end:
                empty.append((bioguide, start, end))
        for left, right in zip(intervals, intervals[1:]):
            if right["start"] < left["end_exclusive"]:
                overlaps.append((bioguide, left["start"], left["end_exclusive"], right["start"]))
    assert not empty, empty[:5]
    assert not overlaps, overlaps[:5]


def test_the_committed_snapshot_states_the_horizon_its_own_intervals_derive():
    table = denominators.load_roster()
    provenance = table["provenance"]
    assert provenance.get("valid_through") == denominators.derived_horizon(table)
    assert denominators.roster_horizon(table) == provenance["valid_through"]


def test_kiley_switch_is_effective_on_its_recorded_date_with_no_unseated_day():
    """K000401: upstream records Republican 2025-01-03..2026-03-08 and Independent from 2026-03-09.
    The first version of the flag copied the inclusive end 2026-03-08 into an exclusive bound and
    seated the office in neither party on that day."""
    table = denominators.load_roster()
    row = table["offices"]["K000401"]
    assert denominators.active_interval(row, "2026-03-08")["party"] == "Republican"
    assert denominators.active_interval(row, "2026-03-09")["party"] == "Independent"
    assert "K000401" in denominators.eligible_offices("2026-03-08", "R", roster_table=table)
    assert "K000401" not in denominators.eligible_offices("2026-03-09", "R", roster_table=table)
    for iso in _days("2025-01-03", "2027-01-02"):
        assert denominators.active_interval(row, iso), iso


def _term(**affiliations) -> bytes:
    rows = "".join(f"    - {{start: '{s}', end: '{e}', party: {p}}}\n" for s, e, p in affiliations["rows"])
    return (b"- id: {bioguide: A000001}\n  name: {first: Ann, last: Cole}\n  terms:\n"
            b"  - type: rep\n    start: '2025-01-03'\n    end: '2027-01-03'\n    state: CA\n"
            b"    district: 1\n    party: Independent\n    party_affiliations:\n" + rows.encode())


def _build(current: bytes, *, split: bool = True) -> dict:
    builder = _builder()
    sources = {"legislators-current.yaml": current, "legislators-historical.yaml": b"[]\n"}
    return builder.build(sources, revision="0" * 40, retrieved_at="2026-11-22T00:00:00Z",
                         valid_through=None, split_affiliations=split)


def test_split_handles_both_upstream_end_conventions_as_one_contiguous_partition():
    for first_end in ("2026-03-08", "2026-03-09"):  # inclusive last day, or equal to the next start
        table = _build(_term(rows=[("2025-01-03", first_end, "Republican"),
                                   ("2026-03-09", "2027-01-03", "Independent")]))
        intervals = table["offices"]["A000001"]["intervals"]
        assert [(i["start"], i["end_exclusive"], i["party"]) for i in intervals] == [
            ("2025-01-03", "2026-03-09", "Republican"), ("2026-03-09", "2027-01-03", "Independent")]
    unsplit = _build(_term(rows=[("2025-01-03", "2026-03-08", "Republican"),
                                 ("2026-03-09", "2027-01-03", "Independent")]), split=False)
    assert [(i["start"], i["end_exclusive"], i["party"])
            for i in unsplit["offices"]["A000001"]["intervals"]] == [
        ("2025-01-03", "2027-01-03", "Independent")]


def test_the_refresh_diff_names_the_office_behind_every_changed_run():
    spec = importlib.util.spec_from_file_location(
        "diff_date_effective_roster", ROOT / "scripts" / "diff_date_effective_roster.py")
    diff = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(diff)  # type: ignore[union-attr]
    table = denominators.load_roster()
    same = diff.day_runs(table, table, "2026-11-01", "2026-11-30")
    assert len(same) == 1 and all(not k[2] and not k[3] for k in same[0]["key"].values())
    assert diff.office_changes(table, table) == []
    import copy
    edited = copy.deepcopy(table)
    edited["offices"]["M001244"]["intervals"] = edited["offices"]["M001244"]["intervals"][:-1]
    runs = [run for run in diff.day_runs(edited, table, "2026-11-01", "2026-11-30") if run["key"]["R"][2]]
    assert [(r["first"], r["last"], r["key"]["R"][2]) for r in runs] == [
        ("2026-11-04", "2026-11-30", ("M001244",))]
    assert runs[0]["totals"]["R"][1] - runs[0]["totals"]["R"][0] == 1
    assert [row[0] for row in diff.office_changes(edited, table)] == ["M001244"]


def test_split_stops_on_an_affiliation_shape_it_cannot_read():
    bad = (
        [("2025-01-05", "2026-03-08", "Republican"), ("2026-03-09", "2027-01-03", "Independent")],
        [("2025-01-03", "2026-03-01", "Republican"), ("2026-03-09", "2027-01-03", "Independent")],
        [("2025-01-03", "2026-03-08", "Republican"), ("2026-03-09", "2026-12-01", "Independent")],
    )
    for rows in bad:
        try:
            _build(_term(rows=rows))
        except ValueError:
            continue
        raise AssertionError(f"accepted {rows}")
