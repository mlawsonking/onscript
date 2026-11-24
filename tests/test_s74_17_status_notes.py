"""S74-17 P0: informational notes do not open an incident.

The status page read "Overall status: red" on 2026-11-23 for a non-incident: RUN A recorded two
healthy, informational lines (the cursor held at the product day; a volume comparison withheld on a
thin Sunday) in the same `alerts` list the incident check reads. Collect now keeps `alerts` (faults
and paged conditions) and `notes` apart; manifests written before the split are classified by the
writer's own prefixes (pipeline.collect_notes, docs/37 rule 1).
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

from pipeline import collect_notes, run_collect, status_exports

ROOT = Path(__file__).resolve().parents[1]

# The relevant fields of the real committed manifests of 2026-11-23, pinned as literals (docs/37 rule
# 3): collect-2026-11-23.json, assemble-2026-11-22.json and post-2026-11-22.json at main 2426aedc.
REAL_COLLECT_ALERTS = [
    "focus held at 2026-11-22: the corpus already holds 2026-11-23, a day that is not over yet; "
    "measuring the product day 2026-11-22 instead",
    "volume comparison withheld on 2026-11-22: the baseline cannot carry a ratio (recent 3-week "
    "same-weekday median, 5, against a floor of 20) (3 statements)",
]
DAY = "2026-11-22"


def _manifests(*, collect_alerts=None, notes=None, assemble_alerts=(), asymmetric=False, held=False,
               low=False, stale=False):
    collect = {"volume": {"today": 3, "anomalously_low": low},
               "source_freshness": {"age_hours": 40.0 if stale else 5.89, "ok": True},
               "days_present": ["2026-11-21", DAY, "2026-11-23"], "focus_day": DAY,
               "alerts": list(REAL_COLLECT_ALERTS if collect_alerts is None else collect_alerts)}
    if notes is not None:
        collect["notes"] = notes
    assemble = {"day": DAY, "generated_at": f"{DAY}T18:00:00Z",
                "readiness": {"ready": True, "count": 3, "share": 1.0},
                "publication_state": "published", "unattended": True, "degraded": False,
                "forced_finalize": False, "corrections_count": 12, "alerts": list(assemble_alerts),
                "per_party_llm": {"D": {"claims_published": 1, "claims_dropped": 0},
                                  "R": {"claims_published": 0, "claims_dropped": 0}}}
    post = {"day": DAY, "posting_enabled": True, "asymmetric": asymmetric, "atomic_hold": held,
            "results": [{"party": "D", "posted": True}, {"party": "R", "posted": True}]}
    return {"collect": collect, "assemble": assemble, "post": post}


def _incident(model):
    return next(c for c in model["checks"] if c["id"] == "incident")


def test_the_real_2026_11_23_notes_do_not_open_an_incident():
    model = status_exports.build_status(_manifests(), [("assemble-2026-11-22.json", _manifests()["assemble"])],
                                        [], now="2026-11-23T20:00:00Z")
    assert _incident(model)["value"] == "clear" and _incident(model)["status"] == "green"
    assert model["overall_status"] != "red"
    # The same lines written by the new collector, as notes, are equally clear.
    split = _manifests(collect_alerts=[], notes=REAL_COLLECT_ALERTS)
    assert _incident(status_exports.build_status(split, [], [], now="2026-11-23T20:00:00Z"))["value"] == "clear"


def test_every_real_alert_still_opens_the_incident():
    cases = {
        "stale upstream": _manifests(collect_alerts=REAL_COLLECT_ALERTS + ["upstream stale 52.27h"]),
        "months missing": _manifests(collect_alerts=["2 months missing"]),
        "low volume": _manifests(collect_alerts=["volume 3 < 40% of same-weekday median 141"]),
        "future focus day": _manifests(collect_alerts=["focus day 2026-11-24 is dated after the "
                                                       "product day 2026-11-23: the day cursor is "
                                                       "ahead of the calendar"]),
        "forced finalize": _manifests(assemble_alerts=["forced-finalize: upstream silent"]),
        "degraded": _manifests(assemble_alerts=["degraded"]),
        "asymmetric post": _manifests(asymmetric=True),
        "atomic hold": _manifests(held=True),
    }
    for name, manifests in cases.items():
        incident = _incident(status_exports.build_status(manifests, [], [], now="2026-11-23T20:00:00Z"))
        assert incident["value"] == "open" and incident["status"] == "red", name


def test_the_classifier_is_tested_against_the_live_writer():
    """docs/37 rule 1: every note run_collect writes is composed by collect_notes and classified as a
    note; nothing it appends to `alerts` is."""
    src = inspect.getsource(run_collect.collect)
    tree = ast.parse(src.lstrip())
    appended = {"alerts": [], "notes": []}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "append" and isinstance(node.func.value, ast.Name)
                and node.func.value.id in appended):
            appended[node.func.value.id].append(ast.unparse(node.args[0]))
    assert len(appended["notes"]) == 3
    assert all(a.startswith("collect_notes.") for a in appended["notes"]), appended["notes"]
    assert not any("collect_notes" in a for a in appended["alerts"]), appended["alerts"]
    for line in (collect_notes.focus_held(DAY, "why"), collect_notes.backfilled(2, 1),
                 collect_notes.volume_withheld(DAY, "why", 3)):
        assert collect_notes.is_note(line), line
    for line in REAL_COLLECT_ALERTS:
        assert collect_notes.is_note(line)
    for real in ("upstream stale 52.27h", "2 months missing", "volume 3 < 40% of x 9",
                 "focus day 2026-11-24 is dated after the product day 2026-11-23: x"):
        assert not collect_notes.is_note(real)
    assert collect_notes.real_alerts({}) is None
