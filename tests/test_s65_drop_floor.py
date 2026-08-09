"""S65 P2 - a verifier drop rate is read as a verdict only over enough offered claims.

On 2026-08-08 the seven-day window held 12 dropped over 22 offered and the instrument
status page read red at 54.5 percent. One claim moves that rate by more than four
percentage points, so the colour reported precision the denominator does not support.
Below VERIFIER_DROP_MIN_OFFERED the check now reports state unknown and the sentence
"insufficient volume (N offered)", and carries its raw dropped and offered counts and its
computed rate on its own face. The verdict is withheld, the measurement is not.

Each window is tested against the floor separately. Windows nest, so a seven-day window
that clears the floor guarantees a thirty-day window that clears it too; the thirty-day
window is only ever under the floor on days when the seven-day check is already unknown.

docs/37 rule 11: severity precedence is untouched. Unknown sits below green, so a thin
week neither colours the page nor masks another check's red.
"""
from __future__ import annotations

from pathlib import Path

from pipeline import corrections, site, status_exports

ROOT = Path(__file__).resolve().parents[1]
FLOOR = status_exports.VERIFIER_DROP_MIN_OFFERED


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


def _model(history, now="2026-07-26T00:00:00Z"):
    return status_exports.build_status(
        _healthy_manifests(history[-1][1]), history, [], now=now
    )


def _drop_check(model):
    return next(check for check in model["checks"] if check["id"] == "verifier_drop")


def _week(dropped, offered, day="2026-07-25"):
    """One in-window day offering `offered` claims of which `dropped` failed the verifier."""
    assert offered >= dropped
    return _assemble(day, {"D": {"claims_published": offered - dropped, "claims_dropped": dropped},
                           "R": {"claims_published": 0, "claims_dropped": 0}})


def test_the_thin_current_week_reports_unknown_and_keeps_its_counts():
    """Reproduces the 2026-08-08 reading: 12 dropped over 22 offered."""
    model = _model([_week(12, 22)])
    check = _drop_check(model)
    assert check["status"] == "unknown"
    assert check["value"] == "insufficient volume (22 offered)"
    # The measurement stays on the face of the same check.
    assert check["dropped"] == 12
    assert check["offered"] == 22
    assert check["rate"] == round(12 / 22, 6)
    assert check["minimum_offered"] == FLOOR
    assert str(FLOOR) in check["derivation"]


def test_a_forty_offered_half_dropped_week_is_red():
    model = _model([_week(20, 40)])
    check = _drop_check(model)
    assert check["status"] == "red"
    assert check["value"] == 0.5
    assert check["dropped"] == 20
    assert check["offered"] == 40
    assert model["overall_status"] == "red"


def test_the_floor_is_exact():
    """One claim either side of the floor, at a rate that would be red if it were read."""
    below = _drop_check(_model([_week(FLOOR - 1, FLOOR - 1)]))
    assert below["status"] == "unknown"
    assert below["value"] == f"insufficient volume ({FLOOR - 1} offered)"

    at = _drop_check(_model([_week(FLOOR, FLOOR)]))
    assert at["status"] == "red"
    assert at["value"] == 1.0


def test_a_clean_week_over_the_floor_is_still_green():
    check = _drop_check(_model([_week(0, 60)]))
    assert check["status"] == "green"
    assert check["value"] == 0.0
    assert check["offered"] == 60


def test_a_thin_week_does_not_disturb_the_thirty_day_window():
    """The floor is per window. A thin recent week leaves the long window measurable."""
    history = [
        _assemble("2026-07-05", {"D": {"claims_published": 180, "claims_dropped": 20},
                                 "R": {"claims_published": 0, "claims_dropped": 0}}),
        _week(4, 10, day="2026-07-25"),
    ]
    model = _model(history)
    windows = model["verifier_drop_windows"]
    assert windows["seven_day"]["offered"] == 10
    assert windows["seven_day"]["sufficient_volume"] is False
    assert windows["thirty_day"]["offered"] == 210
    assert windows["thirty_day"]["sufficient_volume"] is True
    assert windows["thirty_day"]["rate"] == round(24 / 210, 6)
    assert _drop_check(model)["status"] == "unknown"


def test_windows_nest_so_the_long_window_is_never_the_thinner_one():
    """Why the thirty-day arm of the spike rule cannot be reached under the floor.

    The thirty-day window ends at the same anchor and spans the seven-day window, so its
    offered count is never smaller. The guard stays in build_status so a future window pair
    that does not nest cannot silently use an under-floor baseline.
    """
    history = [
        _assemble("2026-07-02", {"D": {"claims_published": 7, "claims_dropped": 1},
                                 "R": {"claims_published": 0, "claims_dropped": 0}}),
        _week(12, 22, day="2026-07-25"),
    ]
    windows = _model(history)["verifier_drop_windows"]
    assert windows["thirty_day"]["offered"] >= windows["seven_day"]["offered"]
    assert windows["seven_day"]["offered"] >= windows["latest"]["offered"]

    manifests, real_history = status_exports.load_manifest_inputs(ROOT / "data/derived/manifest")
    live = status_exports.build_status(manifests, real_history, corrections.load())
    live_windows = live["verifier_drop_windows"]
    assert live_windows["thirty_day"]["offered"] >= live_windows["seven_day"]["offered"]


def test_a_seven_day_spike_over_a_measurable_long_window_is_still_red():
    """The pre-existing spike rule survives the floor when both windows clear it."""
    history = [
        _assemble("2026-07-05", {"D": {"claims_published": 396, "claims_dropped": 4},
                                 "R": {"claims_published": 0, "claims_dropped": 0}}),
        _assemble("2026-07-25", {"D": {"claims_published": 36, "claims_dropped": 4},
                                 "R": {"claims_published": 0, "claims_dropped": 0}}),
    ]
    model = _model(history)
    windows = model["verifier_drop_windows"]
    seven, thirty = windows["seven_day"]["rate"], windows["thirty_day"]["rate"]
    assert seven < status_exports.VERIFIER_DROP_SLO          # not an SLO breach on its own
    assert seven >= thirty * status_exports.VERIFIER_DROP_RECENT_MULTIPLE
    assert windows["seven_day"]["sufficient_volume"] is True
    assert _drop_check(model)["status"] == "red"


def test_an_unknown_drop_check_neither_colours_the_page_nor_masks_a_red():
    worst = status_exports._worst
    assert worst(["green", "unknown"]) == "green"
    assert worst(["red", "unknown"]) == "red"
    assert worst(["critical", "unknown"]) == "critical"

    healthy = _model([_week(2, 12)])
    assert _drop_check(healthy)["status"] == "unknown"
    assert healthy["overall_status"] == "green"


def test_an_empty_window_stays_unavailable_rather_than_insufficient():
    """No offered claims is no reading. That is a different statement from a thin reading,
    and the volume floor must not relabel it."""
    empty = status_exports.build_status({}, [])
    check = _drop_check(empty)
    assert check["value"] is None
    assert check["status"] == "unknown"
    assert check["offered"] == 0
    assert check["rate"] is None
    assert "unavailable" in site.status_body(empty)


def test_the_status_page_shows_the_sentence_without_a_unit():
    body = site.status_body(_model([_week(12, 22)]))
    assert "insufficient volume (22 offered)" in body
    assert "insufficient volume (22 offered) share" not in body
    # The by-window table keeps publishing the raw counts and the computed rate.
    assert ">12</td><td>22</td>" in body
    assert str(round(12 / 22, 6)) in body


def test_real_committed_manifests_report_the_floor_on_every_window():
    """docs/37 rule 2 and rule 3: real artifacts, and only the healed invariant is asserted.

    Whatever volume the live manifests hold, every window states the floor it was tested
    against, and the seven-day check either reports a numeric rate coloured red or green or
    reports unknown with the sentence and its counts. A rebuild cannot break either arm.
    """
    manifests, history = status_exports.load_manifest_inputs(ROOT / "data/derived/manifest")
    model = status_exports.build_status(manifests, history, corrections.load())
    for key, window in model["verifier_drop_windows"].items():
        assert window["minimum_offered"] == FLOOR, key
        assert window["sufficient_volume"] is (window["offered"] >= FLOOR), key

    check = _drop_check(model)
    assert check["dropped"] == model["verifier_drop_windows"]["seven_day"]["dropped"]
    assert check["offered"] == model["verifier_drop_windows"]["seven_day"]["offered"]
    if check["offered"] >= FLOOR:
        assert check["status"] in {"red", "green"}
        assert isinstance(check["value"], float)
    else:
        assert check["status"] == "unknown"
        assert check["value"] == f"insufficient volume ({check['offered']} offered)"
    assert "Verifier drop, by window" in site.status_body(model)
