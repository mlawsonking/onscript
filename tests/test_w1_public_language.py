"""W1 public language, coverage units, and automated-measurement labels."""
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline import ops, public_strings, site


ROOT = Path(__file__).resolve().parents[1]


def _statement(party: str, bioguide: str, day: str = "2026-07-24") -> dict:
    return {
        "id": f"{party}-{bioguide}",
        "lane": 1,
        "published_at": day,
        "member": {"party": party, "bioguide": bioguide},
    }


def test_public_promises_come_from_one_module():
    rendered = site.page("OnScript", "<h1>Test</h1>")
    assert public_strings.TAGLINE in rendered
    assert public_strings.AUTOMATED_MEASUREMENT_LABEL in rendered
    assert public_strings.SYMMETRY_PROMISE in rendered
    assert public_strings.CITATION_PROMISE in rendered
    assert "This is what each party said today, compressed to one voice, with receipts." not in rendered


def test_term_ladder_is_complete_and_ordered():
    assert [label for label, _ in public_strings.TERM_LADDER] == [
        "Repeated phrase",
        "Convergence",
        "Shared-document reuse",
        "Propagation",
        "Probable upstream origin",
        "Observable language coordination",
    ]
    body = site.methodology_body()
    for label, meaning in public_strings.TERM_LADDER:
        assert label in body and meaning in body


def test_symmetry_report_separates_observation_eligibility_and_source_health():
    old = ops.config.DERIVED
    with TemporaryDirectory() as td:
        ops.config.DERIVED = Path(td)
        statements = [
            _statement("D", "D1"), _statement("D", "D2"),
            _statement("R", "R1"), _statement("R", "R2", day="2026-07-23"),
        ]
        try:
            report = ops.symmetry_report(
                "2026-07-24",
                statements,
                {"D": {}, "R": {}},
                freshness={"note": "assemble cannot attest endpoint health"},
                degraded=False,
            )
        finally:
            ops.config.DERIVED = old
    assert report["parties"]["D"]["observed_publishing_offices"] == 2
    assert report["parties"]["D"]["eligible_caucus_offices"] == 2
    assert report["parties"]["R"]["observed_publishing_offices"] == 1
    assert report["parties"]["R"]["eligible_caucus_offices"] == 2
    assert report["parties"]["R"]["source_collection_health"] == "not_attested"


def test_legacy_coverage_stays_with_a_deprecation_note():
    old = ops.config.DERIVED
    with TemporaryDirectory() as td:
        ops.config.DERIVED = Path(td)
        try:
            report = ops.symmetry_report(
                "2026-07-24",
                [_statement("D", "D1"), _statement("R", "R1")],
                {"D": {}, "R": {}},
                freshness={},
                degraded=False,
            )
        finally:
            ops.config.DERIVED = old
    assert report["parties"]["D"]["coverage_pct"] == 100.0
    assert "parties.*.coverage_pct" in report["deprecated_fields"]
    rendered = site.symmetry_table(report)
    assert "Legacy coverage estimate (deprecated)" in rendered
    assert public_strings.COVERAGE_DEPRECATION_NOTE in rendered


def test_public_renderers_do_not_embed_the_legacy_promise():
    legacy = "what each party said today, compressed to one voice, with receipts"
    for relative in ("pipeline/site.py", "pipeline/post_bluesky.py"):
        assert legacy not in (ROOT / relative).read_text(encoding="utf-8").lower()
