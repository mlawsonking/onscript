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
    # Session 63: the scheduled tick runs the edge probes. Without these flags the code exists
    # and the domain goes unwatched, which is exactly the 2026-07-29 shape.
    assert "--probe-domain" in wf and "--probe-rdap" in wf


# ---------------------------------------------------------------------------
# Edge probes: domain health and registrar state (Session 63)
#
# The anchor incident: on 2026-07-29 the registrar suspended onscript.news over registrant-email
# verification and swapped its nameservers to failed-whois-verification.namecheap.com. Every run
# was green, every manifest advanced, and nothing paged, because the domain sits downstream of
# everything the older signal classes observe. All fixtures below are offline summaries in the
# exact shape fetch_domain/fetch_rdap produce; no test touches the network.
# ---------------------------------------------------------------------------
NOW_EDGE = datetime(2026, 7, 31, 4, 30, tzinfo=timezone.utc)

# The real RDAP record for onscript.news, captured live via rdap.org (302 to Identity Digital) on
# 2026-07-31, minutes after the suspension's resolution ("last changed" 2026-07-29 is the
# registrar restoring the domain). Production-shaped per docs/37 rule 2: this is the healthy state
# the probe must stay silent on, exactly as the registry serves it.
RDAP_REAL = {
    "ldhName": "onscript.news",
    "status": ["client transfer prohibited"],
    "events": [
        {"eventAction": "expiration", "eventDate": "2027-07-14T03:09:37.624Z"},
        {"eventAction": "registration", "eventDate": "2026-07-14T03:09:37.624Z"},
        {"eventAction": "last changed", "eventDate": "2026-07-29T14:16:49.042Z"},
    ],
}


def _domain_outcome(cls, attempts=None, **kw):
    out = {"class": cls, **kw}
    out["attempt_classes"] = attempts if attempts is not None else [cls] * 3
    return out


def _rdap_record(**overrides):
    rec = json.loads(json.dumps(RDAP_REAL))
    rec.update(overrides)
    return {"class": "record", "record": rec}


def _levels(findings):
    return [f["level"] for f in findings]


def test_the_2026_07_29_parking_page_pages():
    """THE ANCHOR. A parking page answers HTTP 200, so the alarm must key on the marker, not the
    status. This is the state the domain was in while every other signal class read green."""
    r = watchdog.check_domain(_domain_outcome(
        "no_marker", status=200, final_url="https://onscript.news/",
        resolved=["198.51.100.7"]))  # placeholder IP: the incident's parking address went unrecorded
    assert _levels(r) == ["alarm"]
    assert "marker" in r[0]["detail"].lower()
    assert r[0]["evidence"]["status"] == 200, "the alarm must show that 200 alone lied"


def test_a_healthy_domain_stays_silent():
    """Real values observed 2026-07-31: apex 301s to www, Vercel edge answers with the marker."""
    r = watchdog.check_domain(_domain_outcome(
        "ok", attempts=["ok"], status=200, final_url="https://www.onscript.news/"))
    assert _levels(r) == ["ok"]


def test_a_name_that_stops_resolving_pages():
    """serverHold pulls the delegation; from outside it is a name that no longer resolves. Every
    attempt agreed, so this is a confirmed state, not a blip."""
    r = watchdog.check_domain(_domain_outcome("dns_failure", error="[Errno 11001] getaddrinfo failed"))
    assert _levels(r) == ["alarm"]
    assert "resolve" in r[0]["detail"]


def test_a_consistent_connect_failure_pages_naming_the_state():
    r = watchdog.check_domain(_domain_outcome(
        "unreachable", error="timed out", resolved=["216.198.79.1"]))
    assert _levels(r) == ["alarm"]
    assert r[0]["evidence"]["resolved"] == ["216.198.79.1"], \
        "the alarm names the resolved state so the page is diagnosable from a phone"


def test_an_http_error_pages():
    """Something answered and it is not the site. A served status is a state, not noise."""
    r = watchdog.check_domain(_domain_outcome("http_error", status=503,
                                              final_url="https://onscript.news/"))
    assert _levels(r) == ["alarm"]


def test_mixed_failure_classes_skip_and_log_never_page():
    """A flaky egress path produces a different error each attempt; a real outage fails every
    attempt identically. Only the confirmed shape may page (skip-and-log, like source outages)."""
    r = watchdog.check_domain(_domain_outcome(
        "unreachable", attempts=["dns_failure", "unreachable", "unreachable"], error="timed out"))
    assert _levels(r) == ["note"], "inconsistent failures are transient, not a confirmed state"


def test_a_domain_probe_that_did_not_run_is_a_note_never_ok():
    assert _levels(watchdog.check_domain(None)) == ["note"]


def test_the_real_rdap_record_stays_silent():
    """The registry's actual answer for the healthy domain: one OK finding, no alarm. 348 days to
    expiry at the pinned instant; `client transfer prohibited` is the normal locked state and must
    never match the hold tokens."""
    r = watchdog.check_rdap(_rdap_record(), NOW_EDGE)
    assert _levels(r) == ["ok"], f"unexpected findings: {r}"
    assert r[0]["evidence"]["days_left"] > 300


def test_a_registrar_hold_pages_in_both_rdap_spellings():
    """The 2026-07-29 suspension class. RFC 8056 writes `client hold`; some servers emit
    `clientHold`. Both must page, or the probe is blind to half the registries."""
    for spelling in ("client hold", "clientHold", "server hold", "serverHold"):
        r = watchdog.check_rdap(_rdap_record(status=[spelling, "client transfer prohibited"]),
                                NOW_EDGE)
        alarms = [f for f in r if f["level"] == "alarm"]
        assert [f["check"] for f in alarms] == ["registrar_status"], f"{spelling!r} must page"
        assert spelling in alarms[0]["detail"]


def test_expiry_inside_30_days_pages():
    rec = _rdap_record()
    rec["record"]["events"][0]["eventDate"] = "2026-08-20T03:09:37.624Z"  # 19.9d from NOW_EDGE
    r = watchdog.check_rdap(rec, NOW_EDGE)
    alarms = [f for f in r if f["level"] == "alarm"]
    assert [f["check"] for f in alarms] == ["registrar_expiry"]
    assert alarms[0]["evidence"]["days_left"] == 19.9


def test_an_rdap_record_with_no_expiration_event_pages_rather_than_reads_as_health():
    """Same rule as the unreadable run timestamp: a served record the probe cannot judge is an
    alarm, not a pass."""
    rec = _rdap_record(events=[{"eventAction": "registration",
                                "eventDate": "2026-07-14T03:09:37.624Z"}])
    r = watchdog.check_rdap(rec, NOW_EDGE)
    assert [f["check"] for f in r if f["level"] == "alarm"] == ["registrar_expiry"]


def test_rdap_404_pages():
    """404 is a definitive registry answer, not a network failure: the domain does not exist."""
    r = watchdog.check_rdap({"class": "not_found", "status": 404}, NOW_EDGE)
    assert _levels(r) == ["alarm"]


def test_rdap_network_trouble_skips_and_logs_never_pages():
    """rdap.org throttles by IP and was observed answering in >20s on 2026-07-31. A throttled
    probe is not a broken domain; only a served bad state may page."""
    r = watchdog.check_rdap({"class": "network_error", "error": "HTTP 429"}, NOW_EDGE)
    assert _levels(r) == ["note"]


def test_the_marker_matches_the_live_site_template():
    """docs/37 rule 1: the marker constant is a registry entry whose owner is pipeline/site.py's
    single head template. If the template drops or rewords the tag, this fails, because otherwise
    the first render after that change would page as a parking page (or worse, the probe would be
    silently blind if the marker were also updated nowhere)."""
    src = (Path(__file__).resolve().parent.parent / "pipeline" / "site.py").read_text(encoding="utf-8")
    assert watchdog.SITE_MARKER in src


def test_the_marker_is_in_the_committed_site():
    """docs/37 rule 2: production-shaped proof against the real committed artifact. The page the
    live domain actually serves must contain the exact bytes the probe requires."""
    idx = (Path(__file__).resolve().parent.parent / "site" / "public" / "index.html"
           ).read_text(encoding="utf-8")
    assert watchdog.SITE_MARKER in idx


def test_edge_probes_stay_offline_unless_flagged():
    """Local runs and the suite are $0 and networkless by contract (the module docstring's own
    claim). Without the flags, the fetchers must never be called."""
    tmp = _tmp("cli_offline")
    _derived(tmp)
    calls = []
    saved = watchdog.fetch_domain, watchdog.fetch_rdap
    watchdog.fetch_domain = lambda *a, **k: calls.append("domain")
    watchdog.fetch_rdap = lambda *a, **k: calls.append("rdap")
    try:
        rc = watchdog.main(["--derived", str(tmp), "--now", INCIDENT_NOW.isoformat(),
                            "--product-day", INCIDENT_PRODUCT_DAY, "--no-notify"])
    finally:
        watchdog.fetch_domain, watchdog.fetch_rdap = saved
    assert rc == 0 and calls == []


def test_flagged_edge_probes_feed_the_verdict_and_page_once():
    """The full 2026-07-29 shape end to end: parking page plus registrar hold, healthy manifests,
    one page, exit 0 (the probe worked; a second page would violate one-alert-per-failure-mode)."""
    tmp = _tmp("cli_edge")
    # Manifests fresh at NOW_EDGE, so the ONLY alarms are the edge probes': the assertion below on
    # the page body must not be diluted by an unrelated staleness alarm.
    _derived(tmp, collect_at="2026-07-31T03:39:43Z", final_day="2026-07-29")
    saved_fetch = watchdog.fetch_domain, watchdog.fetch_rdap
    watchdog.fetch_domain = lambda *a, **k: _domain_outcome(
        "no_marker", status=200, final_url="https://onscript.news/", resolved=["198.51.100.7"])
    watchdog.fetch_rdap = lambda *a, **k: _rdap_record(status=["client hold"])
    sent = []
    saved_ntfy = ops.ntfy
    ops.ntfy = lambda title, message, **kw: sent.append((title, message)) or {"sent": True}
    try:
        rc = watchdog.main(["--derived", str(tmp), "--now", NOW_EDGE.isoformat(),
                            "--product-day", "2026-07-30", "--probe-domain", "--probe-rdap"])
    finally:
        watchdog.fetch_domain, watchdog.fetch_rdap = saved_fetch
        ops.ntfy = saved_ntfy
    assert rc == 0, "a detected alarm is a successful probe"
    assert len(sent) == 1, f"one page per incident, got {len(sent)}"
    assert "marker" in sent[0][1] and "client hold" in sent[0][1]
