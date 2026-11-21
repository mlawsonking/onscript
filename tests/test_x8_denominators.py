"""X8 acceptance tests for dated denominators and explicit source coverage."""
from __future__ import annotations

import re
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline import denominators, ops, site, util


ROOT = Path(__file__).resolve().parents[1]


def _roster_fixture() -> dict:
    return {
        "offices": {
            "D1": {"intervals": [
                {"start": "2026-01-01", "end_exclusive": "2026-02-01", "party": "D",
                 "chamber": "House", "voting_status": "voting"},
                {"start": "2026-02-10", "end_exclusive": "2027-01-01", "party": "D",
                 "chamber": "House", "voting_status": "voting"},
            ]},
            "S1": {"intervals": [
                {"start": "2026-01-01", "end_exclusive": "2026-03-01", "party": "D",
                 "chamber": "House", "voting_status": "voting"},
                {"start": "2026-03-01", "end_exclusive": "2027-01-01", "party": "R",
                 "chamber": "House", "voting_status": "voting"},
            ]},
            "NV": {"intervals": [
                {"start": "2026-01-01", "end_exclusive": "2027-01-01", "party": "D",
                 "chamber": "House", "voting_status": "nonvoting"},
            ]},
        }
    }


def test_vacancy_and_party_switch_change_the_correct_daily_denominators():
    roster = _roster_fixture()
    # S74-11 (F5): the nonvoting office NV is inside the population the numerators count, so it is
    # inside the eligible set; voting_only keeps the X8 voting-office view available.
    def voting(day, party):
        return set(denominators.eligible_offices(day, party, roster_table=roster, voting_only=True))
    assert voting("2026-01-15", "D") == {"D1", "S1"}
    assert voting("2026-02-05", "D") == {"S1"}
    assert voting("2026-02-15", "D") == {"D1", "S1"}
    assert voting("2026-03-01", "D") == {"D1"}
    assert voting("2026-03-01", "R") == {"S1"}
    assert set(denominators.eligible_offices("2026-01-15", "D", roster_table=roster)) == {"D1", "S1", "NV"}


def test_corpus_presence_never_becomes_source_support_without_attestation():
    roster = _roster_fixture()
    rows = [{
        "id": "publication-1", "published_at": "2026-01-15", "lane": 1,
        "member": {"bioguide": "D1", "party": "D"},
        "document_family": {"family_id": "family-1"},
    }]
    measured = denominators.daily_measures(
        "2026-01-15", "D", rows, roster_table=roster,
        source_registry={"attestations": {}},
    )
    assert measured["eligible_caucus_offices"] == 3  # D1, S1 and the nonvoting NV (S74-11 F5)
    assert measured["voting_caucus_offices"] == 2
    assert measured["source_supported_offices"] == 0
    assert measured["observed_publishing_offices"] == 1
    assert measured["publications"] == 1
    assert measured["document_families"] == 1
    assert measured["office_source_states"]["unattestable"] == 3


def test_explicit_interval_attestation_is_the_only_supported_path():
    registry = {"attestations": {"D1": [{
        "start": "2026-01-01", "end_exclusive": "2026-02-01", "state": "source_supported"
    }]}}
    assert denominators.source_state("D1", "2026-01-15", registry=registry) == "source_supported"
    assert denominators.source_state("D1", "2026-02-01", registry=registry) == "unattestable"


def test_committed_roster_has_pinned_open_provenance_and_intervals():
    payload = util.read_json(ROOT / "data/reference/date-effective-roster.json")
    provenance = payload["provenance"]
    # S74-11: a provenance-shape check, not a pin (docs/37 rule 3). A refresh to a new pinned
    # revision through scripts/build_date_effective_roster.py must not break this test.
    assert re.fullmatch(r"[0-9a-f]{40}", provenance["revision"])
    assert all(provenance["revision"] in row["url"] for row in provenance["files"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*", provenance["retrieved_at"])
    assert provenance["source"] == "unitedstates/congress-legislators"
    assert provenance["license"] == "CC0-1.0"
    assert len(provenance["files"]) == 2
    assert all(len(row["sha256"]) == 64 for row in provenance["files"])
    assert len(payload["offices"]) > 500
    assert all("intervals" in row for row in payload["offices"].values())


def test_symmetry_and_surface_keep_all_five_measures_distinct():
    old = ops.config.DERIVED
    with TemporaryDirectory() as td:
        ops.config.DERIVED = Path(td)
        try:
            report = ops.symmetry_report(
                "2026-01-15", [], {"D": {}, "R": {}}, freshness={}, degraded=False,
                roster_table=_roster_fixture(), source_registry={"attestations": {}},
            )
        finally:
            ops.config.DERIVED = old
    row = report["parties"]["D"]
    for key in ("date_effective_eligible_caucus_offices", "source_supported_offices",
                "observed_publishing_offices", "publications", "document_families"):
        assert key in row
    rendered = site.symmetry_table(report)
    assert "Eligible caucus offices (date-effective)" in rendered
    assert "Source-supported offices (explicitly attested)" in rendered
    assert "corpus proxy" not in rendered
