"""X8 acceptance tests for dated denominators and explicit source coverage."""
from __future__ import annotations

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
    assert set(denominators.eligible_offices("2026-01-15", "D", roster_table=roster)) == {"D1", "S1"}
    assert set(denominators.eligible_offices("2026-02-05", "D", roster_table=roster)) == {"S1"}
    assert set(denominators.eligible_offices("2026-02-15", "D", roster_table=roster)) == {"D1", "S1"}
    assert set(denominators.eligible_offices("2026-03-01", "D", roster_table=roster)) == {"D1"}
    assert set(denominators.eligible_offices("2026-03-01", "R", roster_table=roster)) == {"S1"}


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
    assert measured["eligible_caucus_offices"] == 2
    assert measured["source_supported_offices"] == 0
    assert measured["observed_publishing_offices"] == 1
    assert measured["publications"] == 1
    assert measured["document_families"] == 1
    assert measured["office_source_states"]["unattestable"] == 2


def test_explicit_interval_attestation_is_the_only_supported_path():
    registry = {"attestations": {"D1": [{
        "start": "2026-01-01", "end_exclusive": "2026-02-01", "state": "source_supported"
    }]}}
    assert denominators.source_state("D1", "2026-01-15", registry=registry) == "source_supported"
    assert denominators.source_state("D1", "2026-02-01", registry=registry) == "unattestable"


def test_committed_roster_has_pinned_open_provenance_and_intervals():
    payload = util.read_json(ROOT / "data/reference/date-effective-roster.json")
    provenance = payload["provenance"]
    assert provenance["revision"] == "4458244308621d0570a15008f46888b7a87645eb"
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
