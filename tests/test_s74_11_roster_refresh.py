"""S74-11 Package 5 (F7): names for new members.

roster.load used to return the cache whenever it existed, and CI restores it from the state asset,
so the cache never learned a member it had not seen when it was first built. On the local cache
(888 entries) three seated members were missing (A000383 Alan Armstrong, seated 2026-03-24;
G000607 James Gallagher, 2026-06-10; G000608 Darline Graham, 2026-07-14), and 77 senators seated on
2026-07-26 carried chamber "house". roster.refresh merges on every collect and corrects chamber
from the term data. Built here from committed artifacts only (the date-effective roster and the
day records), because the cache itself is gitignored.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pipeline import config, denominators, privacy, roster, site

ROOT = Path(__file__).resolve().parents[1]
BIO = re.compile(r"^[A-Z]\d{6}$")


def _stale_cache() -> dict:
    """The shape of the stale production cache: seated members, corpus-derived, with the corpus
    chamber field ("house" for some senators) and without the members seated after it was built."""
    table = denominators.load_roster()
    out = {}
    for bio, row in table["offices"].items():
        interval = denominators.active_interval(row, "2026-02-01")
        if not interval:
            continue
        out[bio] = {"name": row["name"], "party": None, "state": interval["state"], "chamber": "house"}
    return out


def test_merge_adds_unseen_members_and_never_drops_or_blanks():
    cache = {"X000001": {"name": "Kept Member", "party": "D", "chamber": "house", "state": "CA"},
             "X000002": {"name": None, "party": "R", "chamber": None, "state": None}}
    records = [
        {"member": {"bioguide_id": "X000002", "name": "Filled Name", "party": "Republican",
                    "chamber": "Senate", "state": "TX"}},
        {"member": {"bioguide_id": "X000001", "name": "", "party": "", "chamber": "", "state": ""}},
        {"member": {"bioguide_id": "X000003", "name": "New Member", "party": "Democrat",
                    "chamber": "House", "state": "NY"}},
    ]
    merged, stats = roster.merge(cache, records, roster_table={"offices": {}})
    assert merged["X000001"] == cache["X000001"]           # a blank never overwrites a present field
    assert merged["X000002"]["name"] == "Filled Name" and merged["X000002"]["state"] == "TX"
    assert merged["X000003"]["name"] == "New Member"
    assert set(cache) <= set(merged)                         # nothing is dropped
    assert stats["added"] == 1 and stats["before"] == 2 and stats["after"] == 3
    assert cache["X000002"]["name"] is None                  # pure: the input is untouched


def test_refresh_corrects_chamber_from_the_term_data_and_seats_the_missing_three():
    table = denominators.load_roster()
    cache = _stale_cache()
    for bio in ("A000383", "G000607", "G000608"):
        cache.pop(bio, None)
    merged, stats = roster.merge(cache, (), roster_table=table)
    for bio, name in (("A000383", "Alan Armstrong"), ("G000607", "James Gallagher"),
                      ("G000608", "Darline Graham")):
        assert merged[bio]["name"] == name, bio
    seated = set()
    for party in config.ALL_PARTIES:
        seated |= set(denominators.eligible_offices("2026-07-26", party, roster_table=table))
    wrong = [b for b in seated if merged[b]["chamber"] !=
             denominators.active_interval(table["offices"][b], "2026-07-26")["chamber"].lower()]
    assert not wrong, wrong[:5]
    senators = [b for b in seated if denominators.active_interval(
        table["offices"][b], "2026-07-26")["chamber"] == "Senate"]
    assert all(merged[b]["chamber"] == "senate" for b in senators) and len(senators) >= 99
    assert stats["chamber_corrected"] >= len(senators)
    # Offices that left before the epoch are not imported into the name cache.
    assert "A000014" not in merged  # Neil Abercrombie, left 2010


def test_every_author_in_the_last_seven_committed_days_resolves_to_a_name():
    days = sorted((ROOT / "data" / "derived" / "days").glob("*.json"))[-7:]
    authors = set()

    def walk(value):
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str) and BIO.match(value):
            authors.add(value)

    for path in days:
        walk(json.loads(path.read_text(encoding="utf-8")))
    assert len(authors) > 50, len(authors)
    merged, _ = roster.merge({}, (), roster_table=denominators.load_roster())
    unnamed = sorted(b for b in authors if not (merged.get(b) or {}).get("name"))
    assert not unnamed, unnamed
    old = site.ROSTER
    site.ROSTER = merged
    try:
        labels = {b: site.member_name(b) for b in authors}
    finally:
        site.ROSTER = old
    assert not [b for b, label in labels.items() if label == "member name unavailable" or BIO.search(label)]


def test_a_seated_member_in_the_refreshed_roster_is_not_quarantined():
    table = denominators.load_roster()
    stale = _stale_cache()
    stale.pop("A000383", None)
    text = "new funding announced by Alan Armstrong will reach rural hospitals in our state."
    statement = {"member": {"bioguide": "A000383", "party": "R"}}
    before = privacy.person_spans(text, statement, roster_map=stale)
    assert [row["classification"] for row in before] == ["quarantine"]
    merged, _ = roster.merge(stale, (), roster_table=table)
    after = privacy.person_spans(text, statement, roster_map=merged)
    assert [row["classification"] for row in after] == ["public_official"]
    old = site.ROSTER
    site.ROSTER = merged
    try:
        assert site.member_name("A000383") == "Alan Armstrong (R-OK)"
    finally:
        site.ROSTER = old


def test_refresh_persists_the_merge_and_leaves_an_unchanged_cache_alone():
    from tempfile import TemporaryDirectory
    old = roster._CACHE
    with TemporaryDirectory() as td:
        roster._CACHE = Path(td) / "roster.json"
        try:
            roster._CACHE.write_text(json.dumps({"A000383": {"name": None, "party": "R",
                                                             "chamber": "house", "state": "OK"}}),
                                     encoding="utf-8")
            merged = roster.refresh([], roster_table=denominators.load_roster())
            on_disk = json.loads(roster._CACHE.read_text(encoding="utf-8"))
            assert on_disk == merged
            assert on_disk["A000383"]["name"] == "Alan Armstrong"
            assert on_disk["A000383"]["chamber"] == "senate"
            before = roster._CACHE.stat().st_mtime_ns
            roster.refresh([], roster_table=denominators.load_roster())
            assert roster._CACHE.stat().st_mtime_ns == before
        finally:
            roster._CACHE = old


def test_collect_refreshes_the_cache_instead_of_only_ensuring_it_exists():
    import inspect
    from pipeline import run_collect
    source = inspect.getsource(run_collect.collect)
    assert "roster.refresh(records)" in source
