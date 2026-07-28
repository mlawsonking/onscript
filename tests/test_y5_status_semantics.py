"""Y5 acceptance: status semantics (R-36.6).

Three calendar-based verifier windows, absolute severity precedence, and the five-way
freshness split. A recent (seven-day) breach reads red even when the long window is green.
"""
from __future__ import annotations

from pathlib import Path

from pipeline import corrections, site, status_exports

ROOT = Path(__file__).resolve().parents[1]


def _assemble(day, per_party):
    return f"assemble-{day}.json", {
        "day": day, "generated_at": f"{day}T12:00:00Z",
        "readiness": {"ready": True, "count": 100, "share": 1.0},
        "publication_state": "published", "unattended": True,
        "degraded": False, "forced_finalize": False,
        "corrections_count": 0, "alerts": [], "per_party_llm": per_party,
    }


def _healthy_manifests(assemble_body, day="2026-07-25"):
    return {
        "collect": {"volume": {"today": 100, "anomalously_low": False},
                    "source_freshness": {"age_hours": 4, "ok": True},
                    "days_present": ["2026-07-24", day], "focus_day": day, "alerts": []},
        "assemble": assemble_body,
        "post": {"posting_enabled": True, "asymmetric": False, "atomic_hold": False,
                 "results": [{"party": "D", "posted": True}, {"party": "R", "posted": True}]},
    }


def test_severity_precedence_is_absolute():
    worst = status_exports._worst
    assert worst(["green", "amber", "red"]) == "red"
    assert worst(["red", "critical", "amber"]) == "critical"
    assert worst(["green", "green", "green"]) == "green"
    assert worst(["neutral", "unknown"]) == "neutral"
    assert worst([]) == "unknown"


def test_a_seven_day_breach_is_red_while_the_thirty_day_window_alone_is_green():
    # 20 dropped over 41 offered in the seven-day window is 48.78 percent (>= the 0.25 SLO).
    # Diluted across thirty days by a high-volume clean old day, the long rate is under the SLO.
    history = [
        _assemble("2026-07-05", {"D": {"claims_published": 200, "claims_dropped": 1},
                                 "R": {"claims_published": 0, "claims_dropped": 0}}),
        _assemble("2026-07-25", {"D": {"claims_published": 21, "claims_dropped": 20},
                                 "R": {"claims_published": 0, "claims_dropped": 0}}),
    ]
    assemble_body = history[1][1]
    model = status_exports.build_status(_healthy_manifests(assemble_body), history, [],
                                        now="2026-07-26T00:00:00Z")
    windows = model["verifier_drop_windows"]
    assert windows["seven_day"]["rate"] == round(20 / 41, 6)
    assert windows["seven_day"]["rate"] >= status_exports.VERIFIER_DROP_SLO
    assert windows["thirty_day"]["rate"] < status_exports.VERIFIER_DROP_SLO
    verifier = next(check for check in model["checks"] if check["id"] == "verifier_drop")
    assert verifier["status"] == "red"
    assert model["overall_status"] == "red"


def test_windows_are_calendar_based_not_manifests_available():
    history = [
        _assemble("2026-07-05", {"D": {"claims_published": 5, "claims_dropped": 0},
                                 "R": {"claims_published": 0, "claims_dropped": 0}}),
        _assemble("2026-07-25", {"D": {"claims_published": 5, "claims_dropped": 0},
                                 "R": {"claims_published": 0, "claims_dropped": 0}}),
    ]
    model = status_exports.build_status(_healthy_manifests(history[1][1]), history, [],
                                        now="2026-07-26T00:00:00Z")
    windows = model["verifier_drop_windows"]
    assert windows["seven_day"]["days"] == 1     # only 2026-07-25 is within seven calendar days
    assert windows["thirty_day"]["days"] == 2     # both fall inside thirty calendar days


def test_unmeasured_days_are_counted_per_window():
    history = [
        _assemble("2026-07-24", {"D": {}, "R": {}}),  # present but offered nothing
        _assemble("2026-07-25", {"D": {"claims_published": 3, "claims_dropped": 0},
                                 "R": {"claims_published": 0, "claims_dropped": 0}}),
    ]
    model = status_exports.build_status(_healthy_manifests(history[1][1]), history, [],
                                        now="2026-07-26T00:00:00Z")
    assert model["verifier_drop_windows"]["seven_day"]["unmeasured_days"] == 1


def test_an_open_major_correction_plus_a_red_check_yields_red():
    open_major = {
        "schema_version": 3, "correction_id": "corr-2026-07-27-open", "severity": "major",
        "status": "open", "affected_days": ["2026-07-25"], "logged": "2026-07-27",
        "day": "2026-07-25", "description": "x", "resolution": "x",
        "detected_at": "2026-07-27", "acknowledged_at": None, "contained_at": None,
        "corrected_at": None, "closed_at": None, "original_url": None, "corrected_url": None,
        "detection_method": "review", "root_cause": "under investigation",
    }
    assemble_body = _assemble("2026-07-25", {"D": {"claims_published": 3, "claims_dropped": 0},
                                             "R": {"claims_published": 3, "claims_dropped": 0}})[1]
    assemble_body["degraded"] = True  # a red check
    model = status_exports.build_status(_healthy_manifests(assemble_body), [("assemble-2026-07-25.json", assemble_body)],
                                        [open_major], now="2026-07-26T00:00:00Z")
    corrections_check = next(c for c in model["checks"] if c["id"] == "corrections")
    assert corrections_check["status"] == "amber"
    assert model["overall_status"] == "red"


def test_freshness_splits_into_five_labeled_checks():
    history = [_assemble("2026-07-25", {"D": {"claims_published": 3, "claims_dropped": 0},
                                        "R": {"claims_published": 3, "claims_dropped": 0}})]
    model = status_exports.build_status(_healthy_manifests(history[0][1]), history, [],
                                        now="2026-07-26T00:00:00Z")
    ids = {c["id"] for c in model["checks"]}
    assert {"source_fetch", "content_watermark", "expected_day", "publication_lag",
            "endpoint_health"} <= ids
    assert "freshness" not in ids  # the transport-only mislabel is gone
    fetch = next(c for c in model["checks"] if c["id"] == "source_fetch")
    assert fetch["label"] == "Last successful source fetch"


def test_real_committed_manifests_publish_three_windows():
    manifests, history = status_exports.load_manifest_inputs(ROOT / "data/derived/manifest")
    model = status_exports.build_status(manifests, history, corrections.load())
    assert set(model["verifier_drop_windows"]) == {"latest", "seven_day", "thirty_day"}
    assert model["overall_status"] in status_exports.SEVERITY_ORDER
    assert model["verifier_drop_window"]["window_days"] == 30
    assert "Verifier drop, by window" in site.status_body(model)
