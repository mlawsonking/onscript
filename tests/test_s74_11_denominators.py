"""S74-11 Package 1 (F1, F5): the caucus denominator cannot go wrong silently.

A roster snapshot speaks for a bounded window. Past its horizon the date-effective functions return
a refused state and no count; a count above its eligible set is a refused share; the real renderers
print bare counts in both cases. Numerators and denominators use one population.
"""
from __future__ import annotations

import collections
import importlib.util
import json
import re
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline import build, config, denominators, ops, site, util

ROOT = Path(__file__).resolve().parents[1]
FRACTION = re.compile(r"\d+ of \d+ \(\d+(?:\.\d+)?%\)|of \d+ \(\d+(?:\.\d+)?%\)")


def _committed_roster() -> dict:
    return denominators.load_roster()


def test_committed_roster_seats_a_full_house_from_the_epoch_to_its_horizon():
    table = _committed_roster()
    horizon = denominators.roster_horizon(table)
    assert horizon == "2027-01-02", horizon
    day = date.fromisoformat(config.STAGE1_EPOCH)
    checked = 0
    while day.isoformat() <= horizon:
        iso = day.isoformat()
        chambers = collections.Counter()
        for row in table["offices"].values():
            interval = denominators.active_interval(row, iso)
            if interval and interval.get("voting_status", "voting") == "voting":
                chambers[interval.get("chamber")] += 1
        assert 400 <= chambers["House"] <= 440, (iso, chambers)
        assert 90 <= chambers["Senate"] <= 100, (iso, chambers)
        for party in config.COMPOSITE_PARTIES:
            measured = denominators.eligible_count(iso, party, roster_table=table)
            assert measured["denominator_state"] == denominators.STATE_OK
            assert measured["eligible_caucus_offices"] > 200, (iso, party, measured)
        checked += 1
        day += timedelta(days=1)
    assert checked == (date.fromisoformat(horizon) - date.fromisoformat(config.STAGE1_EPOCH)).days + 1


def test_a_day_past_the_horizon_is_refused_never_a_small_number():
    table = _committed_roster()
    for iso in ("2027-01-03", "2027-01-04", "2027-02-01"):
        assert denominators.eligible_offices(iso, "D", roster_table=table) is None
        for party in config.COMPOSITE_PARTIES:
            measured = denominators.eligible_count(iso, party, roster_table=table)
            assert measured == {"denominator_state": denominators.STATE_HORIZON,
                                "eligible_caucus_offices": None, "roster_horizon": "2027-01-02"}
            daily = denominators.daily_measures(iso, party, [], roster_table=table,
                                                source_registry={"attestations": {}})
            assert daily["eligible_caucus_offices"] is None
            assert daily["denominator_state"] == denominators.STATE_HORIZON


def test_explicit_valid_through_narrows_the_horizon_and_an_empty_roster_speaks_for_no_day():
    table = json.loads(json.dumps(_committed_roster()))
    table["provenance"]["valid_through"] = "2026-12-01"
    assert denominators.roster_horizon(table) == "2026-12-01"
    assert denominators.eligible_offices("2026-12-02", "R", roster_table=table) is None
    assert denominators.eligible_offices("2026-12-01", "R", roster_table=table)
    assert denominators.roster_horizon({}) is None
    assert denominators.eligible_count("2026-11-01", "D", roster_table={})["eligible_caucus_offices"] is None


def _symmetry(day: str) -> dict:
    """ops.symmetry_report writes its report under config.DERIVED; keep that write in a temp dir."""
    old = ops.config.DERIVED
    with TemporaryDirectory() as td:
        ops.config.DERIVED = Path(td)
        try:
            return ops.symmetry_report(day, [], {"D": {}, "R": {}}, freshness={}, degraded=False,
                                       roster_table=_committed_roster(),
                                       source_registry={"attestations": {}})
        finally:
            ops.config.DERIVED = old


def _real_day(day: str) -> dict:
    data = util.read_json(ROOT / "data" / "derived" / "days" / f"{day}.json")
    assert isinstance(data, dict) and data.get("top_synchronized"), day
    return data


def test_the_real_day_page_past_the_horizon_prints_no_fraction():
    """Build a real page: the 2026-11-18 committed day record, re-dated past the horizon, with the
    symmetry report ops writes for that day from the committed roster."""
    target = "2027-01-04"
    day_data = {**_real_day("2026-11-18"), "day": target}
    report = _symmetry(target)
    for party in config.COMPOSITE_PARTIES:
        row = report["parties"][party]
        assert row["date_effective_eligible_caucus_offices"] is None
        assert row["denominator_state"] == denominators.STATE_HORIZON
    old_derived, old_flags = site.DERIVED, dict(config.FEATURES)
    with TemporaryDirectory() as td:
        (Path(td) / "symmetry").mkdir()
        util.write_json(Path(td) / "symmetry" / f"{target}.json", report)
        site.DERIVED = Path(td)
        config.FEATURES["party_columns"] = True
        try:
            html = site.day_view_body(target, day_data, set(), 1)
            inside = {**_real_day("2026-11-18")}
            (Path(td) / "symmetry" / "2026-11-18.json").write_text(
                json.dumps(_symmetry("2026-11-18")), encoding="utf-8")
            control = site.day_view_body("2026-11-18", inside, set(), 1)
        finally:
            site.DERIVED = old_derived
            config.FEATURES.clear()
            config.FEATURES.update(old_flags)
    assert "repeated phrases" in html  # the party columns rendered
    assert not FRACTION.search(html), FRACTION.search(html).group(0)
    # The same page inside the horizon does carry fractions, so the assertion above is not vacuous.
    assert FRACTION.search(control)
    # S74-13: read from the committed roster, not pinned (D 260 / R 272 on the July snapshot,
    # D 262 / R 274 after the refresh to a263880).
    inside_counts = [denominators.eligible_count("2026-11-18", p)["eligible_caucus_offices"]
                     for p in config.COMPOSITE_PARTIES]
    assert any(f"of {n} (" in control for n in inside_counts), inside_counts
    table = site.symmetry_table(report)
    assert "past the last date the committed roster snapshot covers" in table


def test_a_count_above_the_caucus_renders_no_fraction():
    assert denominators.office_share(40, 32)["denominator_state"] == denominators.STATE_EXCEEDS
    assert denominators.office_share(40, 32)["share"] is None
    assert denominators.office_share(32, 32)["share"] == 1.0
    assert denominators.office_share(3, None)["denominator_state"] == denominators.STATE_UNAVAILABLE
    tp = {"member_count": 40, "label": "lower costs for families", "topics": [],
          "counts": {"offices": 40, "publications": 44, "families": 41}}
    strip = site.receipts_strip("D", [tp], caucus=32)
    assert "40 offices" in strip and not FRACTION.search(strip) and "125.0%" not in strip
    assert FRACTION.search(site.receipts_strip("D", [tp], caucus=260))
    column = site._party_column("R", [{"ngram": "secure the border", "counts": {"R": 45},
                                       "slug": "x"}], set(), 0, 31)
    assert ">45<" in column and not FRACTION.search(column) and "145.2%" not in column
    unison = site._unison_denoms({"offices_using": 40, "offices_active": 50, "office_share": 0.8,
                                  "day": "2026-11-18"}, 32)[1]
    assert "in the caucus" not in unison
    record = {"grounded_units": 3, "peak_day": "2026-11-18", "counts": {"D": 40},
              "receipts": [{"member": "Member", "party": "D", "state": "CA", "date": "2026-11-18",
                            "url": f"https://example.house.gov/{i}"} for i in range(3)]}
    old = site.DERIVED
    with TemporaryDirectory() as td:
        (Path(td) / "symmetry").mkdir()
        util.write_json(Path(td) / "symmetry" / "2026-11-18.json",
                        {"parties": {"D": {"date_effective_eligible_caucus_offices": 32}}})
        site.DERIVED = Path(td)
        try:
            evidence = site.phrase_evidence_body({"ngram": "lower costs", "slug": "lower-costs"},
                                                 {"phrases": {"lower-costs": record}})
        finally:
            site.DERIVED = old
    assert "D: 40" in evidence and "40 of 32" not in evidence


def test_no_caller_substitutes_the_corpus_proxy_for_a_refused_denominator():
    statements = [{"id": f"s{i}", "published_at": "2027-01-04", "lane": 1, "text": "",
                   "member": {"party": "D", "bioguide": f"X{i:06d}"}} for i in range(500)]
    with TemporaryDirectory() as td:
        result = build.build_awards(statements, {}, focus_day="2027-01-04", roster_map={},
                                    silence_dir=Path(td), generated_at="2027-01-05T00:00:00Z")
    assert result["caucus"]["D"] == 500  # the proxy is still written, under its own key
    assert result["date_effective_caucus"] == {"D": None, "R": None}
    assert result["date_effective_caucus_state"]["D"] == denominators.STATE_HORIZON
    html = site.awards_body({"caucus": {"D": 500, "R": 500}, "date_effective_caucus": {"D": None, "R": None},
                             "unison": {"D": [{"offices_using": 40, "offices_active": 50,
                                               "office_share": 0.8, "day": "2027-01-04",
                                               "ngram": "lower costs"}]}})
    assert "of 500 in the caucus" not in html


def test_the_numerator_office_set_is_a_subset_of_the_eligible_set():
    """F5: the observed office set counted against the denominator is inside the eligible set, on
    real committed shape: every seated office of each party publishes once, plus one off-roster
    author and every seated delegate."""
    table = _committed_roster()
    day = "2026-11-18"
    statements = []
    for party in config.COMPOSITE_PARTIES:
        for bioguide in denominators.eligible_offices(day, party, roster_table=table):
            statements.append({"id": f"{bioguide}-1", "published_at": day, "lane": 1,
                               "member": {"bioguide": bioguide, "party": party}})
    statements.append({"id": "ghost", "published_at": day, "lane": 1,
                       "member": {"bioguide": "Z999999", "party": "D"}})
    for party in config.COMPOSITE_PARTIES:
        eligible = denominators.eligible_offices(day, party, roster_table=table)
        nonvoting = [b for b, row in eligible.items()
                     if row["active_interval"].get("voting_status") == "nonvoting"]
        assert len(nonvoting) == 3, (party, nonvoting)  # the delegates are inside the population
        measured = denominators.daily_measures(day, party, statements, roster_table=table,
                                               source_registry={"attestations": {}})
        assert measured["observed_publishing_offices"] <= measured["eligible_caucus_offices"]
        assert measured["observed_publishing_offices"] == len(eligible)
        assert measured["voting_caucus_offices"] == len(eligible) - 3
    assert denominators.daily_measures(day, "D", statements, roster_table=table,
                                       source_registry={"attestations": {}})[
        "observed_offices_outside_roster"] == 1


def test_a_report_written_before_s74_11_keeps_its_integer_denominator():
    assert denominators.party_denominator({"date_effective_eligible_caucus_offices": 257}) == (
        257, denominators.STATE_OK)
    assert denominators.party_denominator({"date_effective_eligible_caucus_offices": None})[0] is None
    assert denominators.party_denominator({"date_effective_eligible_caucus_offices": 31,
                                           "denominator_state": denominators.STATE_HORIZON}) == (
        None, denominators.STATE_HORIZON)


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_date_effective_roster", ROOT / "scripts" / "build_date_effective_roster.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_roster_builder_is_deterministic_and_states_its_horizon():
    builder = _builder()
    current = (b"- id: {bioguide: A000001}\n  name: {first: Ann, middle: B., last: Cole}\n"
               b"  terms:\n  - {type: rep, start: '2025-01-03', end: '2027-01-03', state: CA, district: 1,"
               b" party: Democrat, url: 'https://cole.house.gov'}\n"
               b"- id: {bioguide: B000002}\n  name: {first: Dee, last: Ross, official_full: Dee Ross}\n"
               b"  terms:\n  - {type: rep, start: '2025-01-03', end: '2027-01-03', state: GU, district: 0,"
               b" party: Republican}\n"
               b"  - {type: sen, start: '1995-01-04', end: '2001-01-03', state: GU, party: Republican}\n")
    historical = (b"- id: {bioguide: C000003}\n  name: {first: Old, last: Timer}\n"
                  b"  terms:\n  - {type: rep, start: '1997-01-07', end: '1999-01-03', state: NY,"
                  b" district: 2, party: Democrat}\n")
    sources = {"legislators-current.yaml": current, "legislators-historical.yaml": historical}
    rev = "0" * 40
    one = builder.build(sources, revision=rev, retrieved_at="2026-07-27T00:00:00Z", valid_through=None)
    two = builder.build(sources, revision=rev, retrieved_at="2026-07-27T00:00:00Z", valid_through=None)
    assert builder.serialize(one) == builder.serialize(two)
    assert set(one["offices"]) == {"A000001", "B000002"}  # a term ending before 2001 is dropped
    assert one["offices"]["A000001"]["name"] == "Ann B. Cole"
    guam = one["offices"]["B000002"]["intervals"]
    assert guam[0]["voting_status"] == "nonvoting" and guam[0]["district"] == 0
    assert builder.default_valid_through(one, "2026-07-27T00:00:00Z") == "2027-01-02"
    assert denominators.roster_horizon(one) == "2027-01-02"
    provenance = one["provenance"]
    assert provenance["revision"] == rev and provenance["retrieved_at"] == "2026-07-27T00:00:00Z"
    assert all(row["url"].endswith(row["path"]) and rev in row["url"] for row in provenance["files"])
