"""The outermost liveness probe (pipeline/watchdog.py, Art. XVI).

The anchor test replays the REAL 2026-07-25 incident: RUN B's 11:30 UTC pass concluded
`startup_failure` at 12:31 with zero jobs, so the in-job dead-man never existed and the missed day
was silent. Every fixture below uses that day's actual timestamps and manifest values, so a
regression is measured against what happened rather than against an invented scenario.

The second test is the one that justifies the whole run-level signal class: on that morning the
data-level checks alone were CLEAN, because a 1-day lag before the morning pass lands is normal.
A probe built only on advancing data would have stayed quiet through the outage.

Every test is offline and $0: no network, no ntfy, no Actions API.
"""
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import ops, watchdog  # noqa: E402

# The incident. 13:00 UTC is the first watchdog tick after the failed 11:30 pass.
INCIDENT_NOW = datetime(2026, 7, 25, 13, 0, tzinfo=timezone.utc)
INCIDENT_PRODUCT_DAY = "2026-07-24"


def _run(conclusion, created, *, status="completed", camel=False):
    if camel:
        return {"status": status, "conclusion": conclusion, "createdAt": created}
    return {"status": status, "conclusion": conclusion, "created_at": created,
            "html_url": "https://github.com/mlawsonking/onscript/actions/runs/1"}


def _incident_assemble_runs():
    """RUN B history as the API actually reported it on 2026-07-25."""
    return [_run("startup_failure", "2026-07-25T12:31:15Z"),
            _run("success", "2026-07-24T22:35:21Z"),
            _run("success", "2026-07-24T13:00:21Z")]


def _incident_collect_runs():
    """RUN A was green throughout; the failure was one-sided."""
    return [_run("success", "2026-07-25T10:50:37Z"),
            _run("success", "2026-07-24T20:44:44Z")]


def _derived(tmp: Path, *, collect_at="2026-07-25T11:39:43Z", final_day="2026-07-23",
             post_manifest=True) -> Path:
    """A derived tree carrying the committed record. Defaults are the real 2026-07-25 values."""
    mdir = tmp / "manifest"
    mdir.mkdir(parents=True, exist_ok=True)
    (mdir / "collect-latest.json").write_text(
        json.dumps({"run_id": "collect-2026-07-25", "generated_at": collect_at}), encoding="utf-8")
    (mdir / "assemble-latest.json").write_text(
        json.dumps({"day": final_day, "generated_at": "2026-07-24T13:01:51Z"}), encoding="utf-8")
    if post_manifest:
        (mdir / f"post-{final_day}.json").write_text("{}", encoding="utf-8")
    return tmp


def _alarms(result):
    return {f["check"] for f in result["alarms"]}


def _tmp(name):
    return Path(tempfile.mkdtemp(prefix=f"onscript-watchdog-{name}-"))


# ---------------------------------------------------------------------------
# The incident
# ---------------------------------------------------------------------------
def test_the_2026_07_25_startup_failure_pages():
    """THE ANCHOR. A run that never created a job must page. This is the failure that was silent."""
    r = watchdog.evaluate(derived=_derived(_tmp("incident")), now=INCIDENT_NOW,
                          product_day=INCIDENT_PRODUCT_DAY,
                          collect_runs=_incident_collect_runs(),
                          assemble_runs=_incident_assemble_runs())
    assert not r["ok"], "the startup_failure must not read as health"
    assert "assemble_conclusion" in _alarms(r)
    detail = [f for f in r["alarms"] if f["check"] == "assemble_conclusion"][0]
    assert detail["evidence"]["conclusion"] == "startup_failure"
    # RUN A was green that morning; the probe must not smear the failure across both pipelines.
    assert not any(a.startswith("collect") for a in _alarms(r))


def test_data_checks_alone_would_not_have_caught_2026_07_25():
    """Why the run-level class exists. With the same committed record and NO run history, the probe
    is clean: last finalized day 2026-07-23 against product day 2026-07-24 is a lag of 1, which is
    normal before the morning pass lands, and the collect manifest was 1.3h old."""
    r = watchdog.evaluate(derived=_derived(_tmp("data_only")), now=INCIDENT_NOW,
                          product_day=INCIDENT_PRODUCT_DAY,
                          collect_runs=None, assemble_runs=None)
    assert r["ok"], "the data-level checks were genuinely clean that morning"
    assert {f["level"] for f in r["findings"] if f["check"].endswith("_runs")} == {"note"}


def test_absent_run_history_is_a_note_never_a_pass():
    """A probe that cannot see must not report health. `None` history is a note, not an OK."""
    r = watchdog.check_runs("assemble", None, INCIDENT_NOW)
    assert [f["level"] for f in r] == ["note"]


# ---------------------------------------------------------------------------
# Run-level checks
# ---------------------------------------------------------------------------
def test_healthy_history_and_fresh_data_stay_silent():
    """No false pages on a normal morning: both pipelines green, data current."""
    now = datetime(2026, 7, 25, 13, 0, tzinfo=timezone.utc)
    r = watchdog.evaluate(
        derived=_derived(_tmp("healthy"), collect_at="2026-07-25T11:39:43Z", final_day="2026-07-24"),
        now=now, product_day="2026-07-24",
        collect_runs=[_run("success", "2026-07-25T10:50:37Z")],
        assemble_runs=[_run("success", "2026-07-25T11:31:00Z")])
    assert r["ok"], f"unexpected alarms: {_alarms(r)}"


def test_a_silently_dropped_schedule_pages():
    """GitHub disables cron on inactive repos. All-green history that simply STOPPED must page."""
    now = datetime(2026, 7, 27, 13, 0, tzinfo=timezone.utc)
    r = watchdog.check_runs("assemble", [_run("success", "2026-07-25T11:31:00Z")], now)
    checks = {f["check"] for f in r if f["level"] == "alarm"}
    assert "assemble_scheduler" in checks
    assert not any(f["check"] == "assemble_conclusion" for f in r), \
        "the run succeeded; only its age is wrong"


def test_no_runs_at_all_pages():
    """An empty list means the workflow was deleted, renamed, or Actions was disabled."""
    r = watchdog.check_runs("collect", [], INCIDENT_NOW)
    assert [f["level"] for f in r] == ["alarm"]


def test_runs_still_in_flight_do_not_page():
    """RUN A has been observed taking 63 min. Mid-run is not failure."""
    r = watchdog.check_runs("collect", [_run(None, "2026-07-25T12:55:00Z", status="in_progress")],
                            INCIDENT_NOW)
    assert [f["level"] for f in r] == ["note"]


def test_both_api_field_shapes_parse():
    """`gh api` gives created_at, `gh run list --json` gives createdAt. A future change of call
    site must not silently blind the probe, so both are read."""
    snake = watchdog.check_runs("assemble", [_run("startup_failure", "2026-07-25T12:31:15Z")],
                                INCIDENT_NOW)
    camel = watchdog.check_runs("assemble", [_run("startup_failure", "2026-07-25T12:31:15Z",
                                                  camel=True)], INCIDENT_NOW)
    assert [f["level"] for f in snake] == [f["level"] for f in camel] == ["alarm"]


def test_an_unreadable_timestamp_pages_rather_than_reads_as_health():
    """If created_at is missing, staleness is unknowable. A probe that cannot judge must not pass."""
    r = watchdog.check_runs("assemble", [{"status": "completed", "conclusion": "success"}],
                            INCIDENT_NOW)
    assert [f["level"] for f in r] == ["alarm"]


def test_a_naive_now_does_not_crash_the_probe():
    """A naive instant is read as UTC. Left naive it would raise on subtraction and take the probe
    down, which is the one outcome a dead-man may never have."""
    r = watchdog.check_runs("assemble", [_run("success", "2026-07-25T11:31:00Z")],
                            watchdog._parse_iso("2026-07-25T13:00:00"))
    assert [f["level"] for f in r] == ["ok"]


def test_the_newest_completed_run_decides_not_the_first_in_the_list():
    """Order of the API response must not change the verdict; a later success clears an alarm."""
    unordered = [_run("startup_failure", "2026-07-24T12:31:15Z"),
                 _run("success", "2026-07-25T11:31:00Z")]
    r = watchdog.check_runs("assemble", unordered, INCIDENT_NOW)
    assert [f["level"] for f in r] == ["ok"], "a newer success means the incident is over"


# ---------------------------------------------------------------------------
# Data-level checks
# ---------------------------------------------------------------------------
def test_stale_ingest_pages():
    """Both RUN A passes produced nothing for a full day."""
    now = INCIDENT_NOW + timedelta(hours=30)
    r = watchdog.check_manifests(_derived(_tmp("stale")), now, "2026-07-25")
    assert "collect_freshness" in {f["check"] for f in r if f["level"] == "alarm"}


def test_a_series_that_stops_advancing_pages():
    """Green runs that finalize nothing. No exit code can report this; only the record can."""
    r = watchdog.check_manifests(_derived(_tmp("stalled"), final_day="2026-07-18"),
                                 INCIDENT_NOW, "2026-07-24")
    alarm = [f for f in r if f["check"] == "publication_advance" and f["level"] == "alarm"]
    assert alarm and alarm[0]["evidence"]["lag_days"] == 6


def test_a_legitimate_readiness_hold_does_not_page():
    """readiness.MAX_WAIT_DAYS is 2, plus one day for finalizing D-1 during D. A lag of exactly 3
    is reachable with nothing wrong, so 3 must stay quiet or the gate's own patience pages."""
    r = watchdog.check_manifests(_derived(_tmp("hold"), final_day="2026-07-21"),
                                 INCIDENT_NOW, "2026-07-24")
    assert not [f for f in r if f["level"] == "alarm"], "a 3-day lag is inside the gate's ceiling"


def test_a_finalized_day_with_no_post_manifest_pages():
    """The data leg finished and the publication leg vanished. Both parties post atomically, so a
    missing manifest means the day was never published at all."""
    r = watchdog.check_manifests(_derived(_tmp("nopost"), post_manifest=False),
                                 INCIDENT_NOW, INCIDENT_PRODUCT_DAY)
    assert "post_manifest" in {f["check"] for f in r if f["level"] == "alarm"}


def test_missing_manifests_page_rather_than_read_as_health():
    """An empty derived tree is not a clean bill; absence of a record is an alarm."""
    empty = _tmp("empty")
    (empty / "manifest").mkdir(parents=True, exist_ok=True)
    r = watchdog.check_manifests(empty, INCIDENT_NOW, INCIDENT_PRODUCT_DAY)
    assert {f["check"] for f in r if f["level"] == "alarm"} == {"collect_manifest",
                                                                "assemble_manifest"}


# ---------------------------------------------------------------------------
# CLI contract
# ---------------------------------------------------------------------------
def test_an_alarm_pages_exactly_once_and_exits_zero():
    """Exit 0 on a detected alarm is deliberate: the probe worked, and it has already paged. A
    non-zero exit would trip the workflow's own dead-man and page a second time for one incident."""
    tmp = _tmp("cli")
    _derived(tmp)
    runs = tmp / "assemble-runs.json"
    runs.write_text(json.dumps(_incident_assemble_runs()), encoding="utf-8")

    sent = []
    saved = ops.ntfy
    ops.ntfy = lambda title, message, **kw: sent.append((title, message, kw)) or {"sent": True}
    try:
        rc = watchdog.main(["--derived", str(tmp), "--assemble-runs", str(runs),
                            "--now", INCIDENT_NOW.isoformat(),
                            "--product-day", INCIDENT_PRODUCT_DAY])
    finally:
        ops.ntfy = saved

    assert rc == 0, "a detected alarm is a successful probe, not a failed one"
    assert len(sent) == 1, f"one page per incident, got {len(sent)}"
    assert sent[0][2].get("priority") == "high"
    assert "startup_failure" in sent[0][1]


def test_no_notify_suppresses_the_page():
    """Local and rehearsal runs must be able to inspect without paging Michael."""
    tmp = _tmp("cli_quiet")
    _derived(tmp)
    sent = []
    saved = ops.ntfy
    ops.ntfy = lambda *a, **k: sent.append(a) or {"sent": True}
    try:
        rc = watchdog.main(["--derived", str(tmp), "--now", INCIDENT_NOW.isoformat(),
                            "--product-day", "2026-08-01", "--no-notify"])
    finally:
        ops.ntfy = saved
    assert rc == 0 and sent == []


def test_the_workflow_file_wires_the_probe_and_is_not_in_the_pipeline_lane():
    """The probe must not share `onscript-pipeline`: queuing behind the 60-minute job it watches
    would silence it at the one moment it is needed."""
    wf = (Path(__file__).resolve().parent.parent / ".github/workflows/watchdog.yml"
          ).read_text(encoding="utf-8")
    assert "python -m pipeline.watchdog" in wf
    assert "group: onscript-watchdog" in wf
    # The directive, not the bare word: the file NAMES onscript-pipeline in a comment explaining
    # why it stays out of that lane, and a substring test would fail on the explanation itself.
    assert "group: onscript-pipeline" not in wf
    assert "schedule:" in wf and "if: failure()" in wf
    # Keyed by file path, because the display names are prose and can be rewritten.
    assert "workflows/${wf}.yml/runs" in wf
