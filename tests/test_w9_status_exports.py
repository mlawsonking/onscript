"""W9 acceptance tests for manifest-backed status, exports, and alert feeds."""
from __future__ import annotations

import json

from pipeline import site, status_exports


def _manifests() -> tuple[dict, list[tuple[str, dict]]]:
    collect = {
        "generated_at": "2026-07-25T20:00:00Z",
        "volume": {"today": 158, "anomalously_low": False},
        "source_freshness": {"age_hours": 12.5},
        "alerts": [],
    }
    assemble = {
        "generated_at": "2026-07-25T21:00:00Z",
        "readiness": {"ready": True, "count": 158},
        "per_party_llm": {
            "D": {"claims_published": 3, "claims_dropped": 1},
            "R": {"claims_published": 3, "claims_dropped": 1},
        },
        "degraded": False,
        "forced_finalize": False,
        "unattended": True,
        "alerts": [],
        "corrections_count": 5,
    }
    post = {
        "asymmetric": False,
        "atomic_hold": False,
        "results": [{"party": "D", "posted": True}, {"party": "R", "posted": True}],
    }
    history = [
        ("assemble-2026-07-24.json", {**assemble, "day": "2026-07-24"}),
        ("assemble-2026-07-25.json", {**assemble, "day": "2026-07-25"}),
    ]
    return {"collect": collect, "assemble": assemble, "post": post}, history


def _days() -> list[tuple[str, dict]]:
    return [
        ("2026-07-25", {
            "day": "2026-07-25",
            "degraded": False,
            "daily_lines": {"D": {}, "R": {}},
            "top_synchronized": [
                {"party": "D", "ngram": "protect medicare now", "day_peak": 4},
                {"party": "R", "ngram": "protect medicare now", "day_peak": 4},
                {"party": "D", "ngram": "yield back the balance", "day_peak": 8},
                {"party": "R", "ngram": "yield back the balance", "day_peak": 8},
            ],
        }),
    ]


def test_unavailable_input_is_unknown_and_never_green():
    model = status_exports.build_status({}, [])
    assert model["checks"]
    assert all(row["value"] is None and row["status"] == "unknown" for row in model["checks"])


def test_every_status_number_names_manifest_fields():
    manifests, history = _manifests()
    model = status_exports.build_status(manifests, history)
    for row in model["checks"]:
        if isinstance(row["value"], (int, float)) and not isinstance(row["value"], bool):
            assert row["sources"], row["id"]
            assert all(source["manifest"] and source["field"] for source in row["sources"])
    html = site.status_body(model)
    assert "Source:" in html and "158 statements" in html and "12.5 hours" in html


def test_api_checksums_reproduce_and_csv_is_present():
    manifests, history = _manifests()
    model = status_exports.build_status(manifests, history)
    files = status_exports.static_exports(model, _days(), {"by_peak": [], "by_velocity": []})
    expected = {
        "api/v1/status.json", "api/v1/days.json", "api/v1/phrases.json",
        "api/v1/bulk.json", "api/v1/days.csv",
    }
    assert set(files) == expected
    for name in expected - {"api/v1/days.csv"}:
        value = json.loads(files[name])
        assert status_exports.verify_envelope(value)
    assert files["api/v1/days.csv"].startswith(b"day,degraded,daily_line_parties,top_phrase_rows\n")


def test_watchlist_filter_is_party_symmetric_and_excludes_procedure():
    feed = status_exports.watchlist_atom(_days(), ["medicare", "yield back"], site_url="https://example.test")
    assert feed.count("D: protect medicare now") == 1
    assert feed.count("R: protect medicare now") == 1
    assert "yield back the balance" not in feed


def test_status_covers_the_ruled_operational_checks():
    manifests, history = _manifests()
    identifiers = {row["id"] for row in status_exports.build_status(manifests, history)["checks"]}
    assert identifiers == {
        "collection", "assembly", "streak", "verifier_drop", "degraded", "posting",
        "corrections", "incident",
        # R-36.6: freshness split into five separately labeled checks
        "source_fetch", "content_watermark", "expected_day", "publication_lag", "endpoint_health",
    }
