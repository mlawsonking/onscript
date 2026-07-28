"""X10 acceptance tests for correction lifecycle and operational status."""
from __future__ import annotations

from pathlib import Path

from pipeline import corrections, site, status_exports


ROOT = Path(__file__).resolve().parents[1]


def _assemble(day: str, *, degraded: bool) -> tuple[str, dict]:
    return f"assemble-{day}.json", {
        "day": day,
        "generated_at": f"{day}T12:00:00Z",
        "readiness": {"ready": True, "count": 100},
        "publication_state": "published",
        "unattended": True,
        "degraded": degraded,
        "forced_finalize": False,
        "per_party_llm": {
            "D": {"claims_published": 3, "claims_dropped": 1},
            "R": {"claims_published": 4, "claims_dropped": 0},
        },
    }


def _manifests(post: dict | None = None) -> dict:
    return {
        "collect": {
            "volume": {"today": 100, "anomalously_low": False},
            "source_freshness": {"age_hours": 4}, "alerts": [],
        },
        "assemble": _assemble("2026-07-25", degraded=True)[1] | {
            "corrections_count": 1, "alerts": [],
        },
        "post": post or {
            "asymmetric": False, "atomic_hold": False,
            "results": [{"party": "D", "posted": True}, {"party": "R", "posted": True}],
        },
    }


def _open_major() -> dict:
    return {
        "schema_version": 3,
        "correction_id": "corr-2026-07-27-open-major",
        "severity": "major", "status": "open",
        "affected_days": ["2026-07-25"], "logged": "2026-07-27", "day": "2026-07-25",
        "description": "A measured value requires correction.",
        "resolution": "Investigation remains open.",
        "detected_at": "2026-07-27T08:00:00Z",
        "acknowledged_at": "2026-07-27T09:00:00Z",
        "contained_at": None, "corrected_at": None, "closed_at": None,
        "original_url": "https://onscript.news/revisions/original/example.html",
        "corrected_url": "https://onscript.news/revisions/corrected/example.html",
        "detection_method": "operator report", "root_cause": "under investigation",
    }


def test_open_major_correction_plus_a_red_check_yields_red():
    # R-36.6: severity precedence is absolute. An open major (amber) plus a degraded (red)
    # check yields red overall; amber never short-circuits red (this is the third-review defect).
    history = [_assemble("2026-07-24", degraded=False), _assemble("2026-07-25", degraded=True)]
    model = status_exports.build_status(_manifests(), history, [_open_major()])
    assert model["overall_status"] == "red"
    check = next(row for row in model["checks"] if row["id"] == "corrections")
    assert check["status"] == "amber" and check["value"] == 1
    assert next(row for row in model["checks"] if row["id"] == "degraded")["status"] == "red"
    assert "Overall status:</strong> red" in site.status_body(model)


def test_degraded_day_breaks_clean_run_but_not_publication_streak():
    history = [_assemble("2026-07-24", degraded=False), _assemble("2026-07-25", degraded=True)]
    model = status_exports.build_status(_manifests(), history, [])
    assert model["streaks"]["publication"]["value"] == 2
    assert model["streaks"]["clean_run"]["value"] == 0


def test_disabled_posting_is_a_neutral_enumerated_state():
    post = {"posting_enabled": False, "asymmetric": False, "atomic_hold": False, "results": []}
    model = status_exports.build_status(_manifests(post), [_assemble("2026-07-25", degraded=False)], [])
    assert len(model["posting_states"]) == 7
    assert model["posting_state"] == "disabled"
    check = next(row for row in model["checks"] if row["id"] == "posting")
    assert check["status"] == "neutral"
    assert "Posting state:</strong> disabled" in site.status_body(model)


def test_verifier_drop_rate_names_window_numerator_and_denominator():
    history = [_assemble("2026-07-24", degraded=False), _assemble("2026-07-25", degraded=False)]
    measured = status_exports.build_status(_manifests(), history, [])["verifier_drop_window"]
    assert measured == {
        **measured,
        "days": 2, "window_days": 30, "dropped": 2, "offered": 16, "rate": 0.125,
        "unit": "claims dropped over claims offered",
    }


def test_schema_three_requires_lifecycle_and_renders_both_revision_links():
    row = _open_major()
    assert corrections.validate([row]) == [row]
    rendered = site.correction_permalink_body(row)
    assert "Original rendering" in rendered and "Corrected rendering" in rendered
    assert corrections.response_target("major") == {
        "acknowledge_hours": 24, "correct_hours": 72, "status": "provisional"
    }


def test_real_committed_corrections_and_manifests_build_status_read_only():
    rows = corrections.load()
    manifests, history = status_exports.load_manifest_inputs(ROOT / "data/derived/manifest")
    model = status_exports.build_status(manifests, history, rows)
    assert rows and all(corrections.lifecycle(row)["detected_at"] for row in rows)
    assert model["posting_state"] in status_exports.POSTING_STATES
    assert model["verifier_drop_window"]["window_days"] == 30
