"""Watchdog: the OUTERMOST liveness probe (Art. XVI, §deploy-hardening 2026-07-25).

THE HOLE THIS CLOSES. Both pipeline workflows end with a `if: failure()` dead-man step. That step
lives INSIDE the job, so it can only fire if a job was created. On 2026-07-25 the 11:30 UTC RUN B
concluded `startup_failure` at 12:31 with ZERO jobs: GitHub never created the job, the dead-man step
therefore never existed, and the day's two Bluesky threads, site render, and symmetry audit were
skipped in COMPLETE SILENCE. Michael found it by asking, not by being paged. It was the first
startup_failure in the repo's run history, so this failure mode had never been exercised — the
recovery path we thought we had, we did not have.

Art. XVI already required this: "Failure notifications belong at the outermost layer so a scheduled
workflow reports failures that occur before main()" and "A liveness probe observes advancing data
rather than its own process." The in-job dead-man satisfied neither for a run that never started.
This module is that outermost layer, and it runs in a SEPARATE workflow so its own liveness does not
depend on the workflow it is watching.

TWO INDEPENDENT SIGNAL CLASSES, because either one alone is blind:

  RUN-LEVEL (did the machine run?) — reads the Actions API run history. Catches startup_failure,
  cancellation, a disabled workflow, and GitHub silently dropping the cron (it does this to repos
  after 60 days of inactivity). This is the check that would have caught 2026-07-25.

  DATA-LEVEL (did the output advance?) — reads the COMMITTED manifests. Catches a run that is green
  but produced nothing, which no exit code can report. Art. XVI's "observes advancing data".

On 2026-07-25 the data-level checks alone would NOT have paged: `assemble-latest.json` still read
day 2026-07-23 and product_day was 2026-07-24, a lag of 1, which is normal before the morning pass
lands. Only the run-level check saw it. Both classes are load-bearing; neither is decoration.

TWO EDGE PROBES (Session 63), because both classes above stop at the repository's edge. On
2026-07-29 the registrar suspended onscript.news over registrant-email verification and swapped its
nameservers to failed-whois-verification.namecheap.com. Every run stayed green and every manifest
advanced, because the DOMAIN sits downstream of everything those classes observe: the site built
perfectly, and the domain simply no longer pointed at it. Nothing paged (#220 was filed by hand).

  DOMAIN HEALTH (does the public edge serve OUR site?) fetches the site over the public domain and
  requires HTTP 200 plus the built site's marker. A registrar parking page also answers 200, so
  status alone cannot tell the site from its impostor.

  REGISTRAR STATE (is the registration itself sound?) reads the domain's RDAP record for hold and
  deletion statuses and for time-to-expiry, so the next suspension pages before the nameservers
  move, and an autorenew failure pages a month before it becomes an outage.

Both probes confirm before they page: a bad state must survive every retry, and transient network
trouble is skipped and logged, never alarmed (a probe that pages falsely erodes the pager). Network
use is read-only GETs; still no commits, no pushes, no API spend. Live fetching runs only under
--probe-domain / --probe-rdap, which the watchdog workflow passes; local runs stay offline.

ACTIVATION. Scheduled workflows execute the default branch's copy of this module, so these probes,
and any future change here, go live when the commit lands on the default branch. The push is the
release act (docs/37 rule 14).

WHAT THIS MODULE DOES NOT DO. It cannot detect the platform failing to schedule the WATCHDOG. That
residual risk needs a probe outside GitHub (an external heartbeat that pages when OnScript stops
checking in). Documented in docs/07-OPERATIONS.md P11; it needs an external account, so it is
Michael's to set up.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, ops, util

# --- Thresholds. Each one states its estimator, unit, window, and derivation (Art. XVI). ---

# Age of the newest COMPLETED run, in hours, before we call the scheduler dead.
# Derivation: both pipelines run two passes/day. The widest healthy gap is RUN A's 19:30 -> 09:30
# UTC = 14h. Observed GitHub schedule delay reached 61 min on 2026-07-25 (11:30 cron dispatched
# 12:31), and the jobs themselves run up to their 60-min timeout. 14 + 1 + 1 = 16h worst healthy
# case; 26h leaves a 10h margin and still fires well inside the day after BOTH passes of a workflow
# produce nothing. Tighter than 26 risks paging on a slow Saturday; looser loses a full day.
RUN_MAX_AGE_HOURS = 26.0

# Age of collect-latest.json, in hours, before the ingest side is called stale. Same derivation:
# RUN A rewrites this manifest on EVERY successful pass (unlike assemble-latest, below).
COLLECT_MANIFEST_MAX_AGE_HOURS = 26.0

# How far the last finalized day may legitimately trail product_day, in days.
# Derivation: readiness.MAX_WAIT_DAYS = 2, so the gate may HOLD a not-yet-ready day for two days
# before force-finalizing it. Add 1 for the pass that finalizes day D-1 during day D. A lag of 3 is
# therefore reachable without anything being wrong; 4 means the gate stopped advancing.
FINAL_DAY_MAX_LAG_DAYS = 3

# Attempts per edge probe and their spacing, in seconds. Derivation: a false page erodes the pager
# (docs/37 rule 14, one alert per failure mode), so a bad state must survive EVERY attempt before
# it alarms. Three attempts 20s apart span about a minute, which outlives a transient DNS or edge
# blip; the states these probes exist to catch (a registrar hold, a nameserver swap, an expired
# registration) persist for hours to days, so confirmation costs a minute and loses nothing.
# The 30s timeout is observed: rdap.org answered a first query at >20s on 2026-07-31.
PROBE_ATTEMPTS = 3
PROBE_RETRY_SLEEP_SECONDS = 20.0
PROBE_TIMEOUT_SECONDS = 30.0
_PROBE_MAX_BYTES = 2_000_000  # index.html is ~100KB; the cap only bounds a hostile impostor.

# The marker the built site emits in the <head> of EVERY page, from the single head template in
# pipeline/site.py. Chosen because it is static across days (titles change daily) and absent from
# any page this pipeline did not build. The suite pins it against the owning template AND the
# committed site (docs/37 rules 1 and 2), so it cannot drift from what production emits without a
# test failing, which would silently blind this probe.
SITE_MARKER = '<meta property="og:site_name" content="OnScript">'

DOMAIN_URL = f"{config.SITE_URL}/"
_DOMAIN_HOST = urllib.parse.urlsplit(config.SITE_URL).hostname or "onscript.news"
_PROBE_UA = f"onscript-watchdog/1 (+{config.SITE_URL})"

# rdap.org is the IANA bootstrap redirector: it 302s to the registry's own RDAP service (Identity
# Digital for .news, observed 2026-07-31). Queried instead of the registry URL directly so a
# registry-side RDAP migration cannot silently blind the probe.
RDAP_URL = f"https://rdap.org/domain/{_DOMAIN_HOST}"

# Days of registration remaining below which the probe alarms. Derivation: renewal is one
# registrar action with no external dependency; 30 days spans two of Michael's monthly ops checks,
# so an autorenew failure surfaces twice before it can become an outage.
RDAP_EXPIRY_MIN_DAYS = 30

# EPP status tokens meaning the registry or registrar has taken the domain out of service or is
# about to: client/server hold (the 2026-07-29 suspension class), redemption period and pending
# delete (the post-expiry death spiral). Matched against lowercased, space-stripped status strings
# so both RDAP spellings ("client hold" and "clientHold") hit. The only RFC 8056 statuses
# containing these substrings are exactly the out-of-service ones; "client transfer prohibited",
# the normal locked state, does not match.
RDAP_BAD_STATUS_TOKENS = ("hold", "redemption", "pendingdelete")

_OK, _ALARM = "ok", "alarm"


def _get(run: dict, *names):
    """Read a field across the two shapes the Actions API is consumed in: `gh api` returns
    snake_case (created_at), `gh run list --json` returns camelCase (createdAt). Accepting both
    means a future change of call site cannot silently blind the probe."""
    for n in names:
        if run.get(n) is not None:
            return run[n]
    return None


def _parse_iso(s: str | None) -> datetime | None:
    """Parse to an AWARE UTC instant. A naive input is read as UTC rather than left naive, because
    a naive/aware subtraction raises TypeError and would take the probe down instead of paging."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _finding(check: str, level: str, detail: str, **evidence) -> dict:
    return {"check": check, "level": level, "detail": detail, "evidence": evidence}


def _hours_since(then: datetime | None, now: datetime) -> float | None:
    if then is None:
        return None
    return round((now - then).total_seconds() / 3600.0, 2)


# ---------------------------------------------------------------------------
# RUN-LEVEL: did the machine actually run, and did it end green?
# ---------------------------------------------------------------------------
def check_runs(label: str, runs: list[dict] | None, now: datetime,
               *, max_age_hours: float = RUN_MAX_AGE_HOURS) -> list[dict]:
    """Judge one workflow's recent run history. `runs` is newest-first or any order; we sort.

    `None` means the caller did not supply history (local invocation without a token). That is
    reported as a NOTE, never as OK: a probe that cannot see must not claim health.
    """
    if runs is None:
        return [_finding(f"{label}_runs", "note", "no run history supplied — run-level checks skipped")]
    if not runs:
        return [_finding(f"{label}_runs", _ALARM,
                         f"{label}: the Actions API returned NO runs at all — workflow deleted, "
                         f"renamed, or Actions disabled for this repo")]

    completed = [r for r in runs if _get(r, "status") == "completed"]
    if not completed:
        # Everything in the window is still queued/in_progress. Not health, but not yet failure:
        # a long RUN A (63 min observed) legitimately looks like this. Report, do not page.
        return [_finding(f"{label}_runs", "note",
                         f"{label}: {len(runs)} run(s) in flight, none completed in the window")]

    latest = max(completed, key=lambda r: str(_get(r, "created_at", "createdAt") or ""))
    conclusion = _get(latest, "conclusion")
    created = _parse_iso(_get(latest, "created_at", "createdAt"))
    age = _hours_since(created, now)
    url = _get(latest, "html_url", "url") or ""
    out: list[dict] = []

    if conclusion != "success":
        # THE 2026-07-25 CHECK. `startup_failure` lands here, and so does cancelled/timed_out/
        # failure. Anything that is not success is a day at risk, and it self-clears the moment a
        # later run succeeds, so no state file is needed to stop repeat pages.
        out.append(_finding(f"{label}_conclusion", _ALARM,
                            f"{label}: last completed run concluded '{conclusion}', not success",
                            conclusion=conclusion, run_url=url, age_hours=age))
    if age is None:
        # The API always carries created_at. If it does not, staleness is UNKNOWABLE, and a probe
        # that cannot judge must not report health (same rule as absent history, above).
        out.append(_finding(f"{label}_scheduler", _ALARM,
                            f"{label}: newest completed run has no readable created_at, so its age "
                            f"cannot be judged", raw=_get(latest, "created_at", "createdAt")))
    elif age > max_age_hours:
        # No successful dispatch in a full cadence window. GitHub disables cron on repos after 60
        # days without activity; a schedule that silently stops looks exactly like this.
        out.append(_finding(f"{label}_scheduler", _ALARM,
                            f"{label}: newest completed run is {age}h old (>{max_age_hours}h) — "
                            f"the schedule appears to have stopped firing",
                            age_hours=age, threshold_hours=max_age_hours, run_url=url))
    if not out:
        out.append(_finding(f"{label}_runs", _OK,
                            f"{label}: last completed run succeeded {age}h ago", age_hours=age))
    return out


# ---------------------------------------------------------------------------
# DATA-LEVEL: did the committed output advance? (Art. XVI liveness)
# ---------------------------------------------------------------------------
def check_manifests(derived: Path, now: datetime, product_day: str) -> list[dict]:
    """Read the committed record, not the process. A green run that wrote nothing fails here."""
    out: list[dict] = []
    mdir = Path(derived) / "manifest"

    collect = util.read_json(mdir / "collect-latest.json", None)
    if not collect:
        out.append(_finding("collect_manifest", _ALARM,
                            "collect-latest.json is missing — RUN A has never committed here"))
    else:
        age = _hours_since(_parse_iso(collect.get("generated_at")), now)
        if age is None:
            out.append(_finding("collect_manifest", _ALARM,
                                "collect-latest.json has no readable generated_at",
                                generated_at=collect.get("generated_at")))
        elif age > COLLECT_MANIFEST_MAX_AGE_HOURS:
            out.append(_finding("collect_freshness", _ALARM,
                                f"ingest is stale: collect-latest.json is {age}h old "
                                f"(>{COLLECT_MANIFEST_MAX_AGE_HOURS}h)",
                                age_hours=age, run_id=collect.get("run_id")))
        else:
            out.append(_finding("collect_freshness", _OK, f"ingest fresh ({age}h)", age_hours=age))

    assemble = util.read_json(mdir / "assemble-latest.json", None)
    if not assemble or not assemble.get("day"):
        out.append(_finding("assemble_manifest", _ALARM,
                            "assemble-latest.json is missing or has no day — nothing was ever "
                            "finalized"))
        return out

    final_day = assemble["day"]
    try:
        lag = (datetime.fromisoformat(product_day).date()
               - datetime.fromisoformat(final_day).date()).days
    except ValueError:
        out.append(_finding("publication_advance", _ALARM,
                            f"assemble-latest.json day is unparseable: {final_day!r}"))
        return out

    if lag > FINAL_DAY_MAX_LAG_DAYS:
        out.append(_finding("publication_advance", _ALARM,
                            f"the series has stopped advancing: last finalized day {final_day} "
                            f"trails product day {product_day} by {lag}d "
                            f"(>{FINAL_DAY_MAX_LAG_DAYS}d, the readiness gate's own hold ceiling)",
                            final_day=final_day, product_day=product_day, lag_days=lag))
    else:
        out.append(_finding("publication_advance", _OK,
                            f"last finalized day {final_day}, {lag}d behind product day",
                            final_day=final_day, lag_days=lag))

    # A finalized day always leaves a post manifest, in dry-run as well as live (the manifests
    # from 2026-07-13 predate POSTING_ENABLED going true on 2026-07-21). A finalized day with no
    # post manifest means assemble finished the data leg and lost the publication leg silently.
    post = mdir / f"post-{final_day}.json"
    if not post.exists():
        out.append(_finding("post_manifest", _ALARM,
                            f"day {final_day} was finalized but {post.name} does not exist — the "
                            f"posting leg did not complete", final_day=final_day))
    else:
        out.append(_finding("post_manifest", _OK, f"{post.name} present", final_day=final_day))
    return out


# ---------------------------------------------------------------------------
# EDGE-LEVEL: does the public domain serve OUR site, and is the registration sound?
# The network happens in fetch_domain/fetch_rdap (below); the judgment functions are pure so the
# suite can replay the 2026-07-29 suspension offline, at $0, forever.
# ---------------------------------------------------------------------------
def _resolve_host(host: str) -> list[str]:
    """Best-effort address lookup, for alarm evidence only ("naming the resolved state"). Returns
    [] on failure, never raises: evidence gathering may not take down the probe."""
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        return sorted({str(i[4][0]) for i in infos})
    except OSError:
        return []


def _http_get(url: str, timeout: float) -> tuple[int, str, bytes]:
    """One GET, redirects followed (the site 301s apex to www). Returns (status, final_url, body).
    Raises; classification belongs to the callers' retry loops."""
    req = urllib.request.Request(url, headers={"User-Agent": _PROBE_UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", None) or resp.getcode()
        return status, resp.geturl(), resp.read(_PROBE_MAX_BYTES)


def fetch_domain(url: str = DOMAIN_URL, *, marker: str = SITE_MARKER,
                 attempts: int = PROBE_ATTEMPTS, timeout: float = PROBE_TIMEOUT_SECONDS,
                 sleep=time.sleep) -> dict:
    """Live-fetch the public site and summarize for check_domain. Never raises: every failure is
    classified, because taking the probe down is the one outcome a dead-man may never have.

    Classes: `ok` (200 + marker), `no_marker` (200 without it: a parking page looks exactly like
    this), `http_error` (any non-200 answer), `dns_failure` (the name did not resolve), and
    `unreachable` (resolved but no HTTP conversation). A success ends the retry loop; otherwise
    every attempt's class is recorded so the judge can tell a confirmed state from a flaky path.
    """
    host = urllib.parse.urlsplit(url).hostname or url
    tried: list[str] = []
    outcome: dict = {"class": "unreachable", "error": "not attempted"}
    for i in range(max(1, attempts)):
        if i:
            sleep(PROBE_RETRY_SLEEP_SECONDS)
        try:
            status, final_url, body = _http_get(url, timeout)
            if status == 200 and marker in body.decode("utf-8", "replace"):
                outcome = {"class": "ok", "status": status, "final_url": final_url}
            elif status == 200:
                outcome = {"class": "no_marker", "status": status, "final_url": final_url,
                           "resolved": _resolve_host(host)}
            else:
                outcome = {"class": "http_error", "status": status, "final_url": final_url,
                           "resolved": _resolve_host(host)}
        except urllib.error.HTTPError as e:
            outcome = {"class": "http_error", "status": e.code, "final_url": e.geturl(),
                       "resolved": _resolve_host(host)}
        except urllib.error.URLError as e:
            if isinstance(getattr(e, "reason", None), socket.gaierror):
                outcome = {"class": "dns_failure", "error": str(e.reason)}
            else:
                outcome = {"class": "unreachable", "error": str(getattr(e, "reason", e)),
                           "resolved": _resolve_host(host)}
        except Exception as e:  # noqa: BLE001 - classify, never die
            outcome = {"class": "unreachable", "error": f"{type(e).__name__}: {e}",
                       "resolved": _resolve_host(host)}
        tried.append(outcome["class"])
        if outcome["class"] == "ok":
            break
    outcome["attempt_classes"] = tried
    return outcome


def fetch_rdap(url: str = RDAP_URL, *, attempts: int = PROBE_ATTEMPTS,
               timeout: float = PROBE_TIMEOUT_SECONDS, sleep=time.sleep) -> dict:
    """Live RDAP query via the bootstrap redirector, summarized for check_rdap. Never raises.

    A 404 is a definitive registry answer (the domain is not registered) and returns immediately.
    Everything else retries, and a final failure reports class `network_error`, which the judge
    logs and skips: rdap.org throttles by IP, and a throttled probe is not a broken domain.
    """
    outcome: dict = {"class": "network_error", "error": "not attempted"}
    for i in range(max(1, attempts)):
        if i:
            sleep(PROBE_RETRY_SLEEP_SECONDS)
        try:
            status, final_url, body = _http_get(url, timeout)
            record = json.loads(body.decode("utf-8", "replace"))
            return {"class": "record", "record": record, "final_url": final_url,
                    "status": status}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"class": "not_found", "status": 404}
            outcome = {"class": "network_error", "error": f"HTTP {e.code}"}
        except json.JSONDecodeError as e:
            outcome = {"class": "network_error", "error": f"unparseable RDAP payload: {e}"}
        except Exception as e:  # noqa: BLE001 - classify, never die
            outcome = {"class": "network_error", "error": f"{type(e).__name__}: {e}"}
    return outcome


def check_domain(outcome: dict | None, *, url: str = DOMAIN_URL) -> list[dict]:
    """Judge one summarized domain fetch. Pure: the network happened in fetch_domain.

    `None` means the probe was not run (local invocation without --probe-domain). That is a NOTE,
    never an OK: a probe that did not look must not claim health (same rule as absent run history).
    """
    if outcome is None:
        return [_finding("domain_health", "note",
                         "domain probe not run (enable with --probe-domain)")]
    cls = outcome.get("class")
    tried = outcome.get("attempt_classes") or ([cls] if cls else [])
    ev = {k: outcome[k] for k in ("status", "final_url", "resolved", "error") if outcome.get(k)}
    ev["attempt_classes"] = tried
    if cls == "ok":
        return [_finding("domain_health", _OK,
                         f"{url} answers HTTP 200 and serves the built site", **ev)]
    if cls == "no_marker":
        # THE 2026-07-29 CHECK. The registrar's parking nameservers serve a 200 of their own, so
        # the day the suspension happened this is what the domain looked like: green to a status
        # check, gone to every reader.
        return [_finding("domain_health", _ALARM,
                         f"{url} answers HTTP 200 WITHOUT the built-site marker: the domain is "
                         f"serving a page this pipeline did not build (registrar parking looks "
                         f"exactly like this; on 2026-07-29 the nameservers were swapped to "
                         f"failed-whois-verification.namecheap.com and nothing paged)", **ev)]
    if cls == "http_error":
        # A served status is a resolved state, not noise: something answered, and it is not the
        # site. It survived every retry (a success would have ended the loop).
        return [_finding("domain_health", _ALARM,
                         f"{url} answers HTTP {outcome.get('status')}, not the built site", **ev)]
    if cls in ("dns_failure", "unreachable") and tried and all(t == cls for t in tried):
        # No HTTP conversation at all, and every attempt failed the SAME way: confirmed, not
        # flaky. A registry hold pulls the zone, so from outside serverHold looks like a name
        # that stopped resolving.
        state = ("the name does not resolve (a registry hold removes the delegation; this is "
                 "what serverHold looks like from outside)" if cls == "dns_failure" else
                 f"the host is unreachable ({outcome.get('error')})")
        return [_finding("domain_health", _ALARM,
                         f"{url} failed all {len(tried)} attempts: {state}", **ev)]
    # Attempts disagreed about what is wrong. That is a flaky path, not a state; skip and log.
    return [_finding("domain_health", "note",
                     f"transient network trouble reaching {url}; skipping this tick rather than "
                     f"paging falsely (attempt classes: {', '.join(tried)}). A real outage fails "
                     f"every attempt identically and alarms.", **ev)]


def check_rdap(outcome: dict | None, now: datetime) -> list[dict]:
    """Judge one summarized RDAP query. Pure: the network happened in fetch_rdap."""
    if outcome is None:
        return [_finding("registrar", "note",
                         "registrar probe not run (enable with --probe-rdap)")]
    cls = outcome.get("class")
    if cls == "not_found":
        return [_finding("registrar", _ALARM,
                         f"RDAP answers 404 for {_DOMAIN_HOST}: the registry has NO record of the "
                         f"domain (deleted, or lost past redemption)")]
    if cls != "record":
        # Skip-and-log, per the same rule as source outages: rdap.org throttles by IP and had a
        # >20s first answer on 2026-07-31. A flaky third-party probe must not page.
        return [_finding("registrar", "note",
                         f"RDAP unreachable this tick ({outcome.get('error')}); skipping rather "
                         f"than paging falsely. A registry state persists and will be seen by the "
                         f"next tick.")]
    record = outcome.get("record") or {}
    out: list[dict] = []
    statuses = [str(s) for s in (record.get("status") or [])]
    bad = sorted({s for s in statuses
                  if any(t in s.lower().replace(" ", "") for t in RDAP_BAD_STATUS_TOKENS)})
    if bad:
        out.append(_finding("registrar_status", _ALARM,
                            f"the registry reports an out-of-service state on {_DOMAIN_HOST}: "
                            f"{', '.join(bad)} (the 2026-07-29 suspension class: the domain is, "
                            f"or is about to be, off the air regardless of what this repo does)",
                            status=statuses))
    expiry = None
    for e in record.get("events") or []:
        if e.get("eventAction") == "expiration":
            expiry = _parse_iso(e.get("eventDate"))
            break
    if expiry is None:
        out.append(_finding("registrar_expiry", _ALARM,
                            f"the RDAP record for {_DOMAIN_HOST} has no readable expiration "
                            f"event, so time-to-expiry cannot be judged; a probe that cannot "
                            f"judge must not report health", events=record.get("events")))
    else:
        days = round((expiry - now).total_seconds() / 86400.0, 1)
        if days < RDAP_EXPIRY_MIN_DAYS:
            out.append(_finding("registrar_expiry", _ALARM,
                                f"{_DOMAIN_HOST} expires in {days}d "
                                f"(<{RDAP_EXPIRY_MIN_DAYS}d): renew at the registrar NOW",
                                days_left=days, expires=expiry.strftime("%Y-%m-%dT%H:%M:%SZ")))
        elif not bad:
            out.append(_finding("registrar", _OK,
                                f"registration sound: {days}d to expiry, status {statuses}",
                                days_left=days))
    return out


def evaluate(*, derived: Path, now: datetime, product_day: str,
             collect_runs: list[dict] | None = None,
             assemble_runs: list[dict] | None = None,
             domain_outcome: dict | None = None,
             rdap_outcome: dict | None = None) -> dict:
    """Full probe. Returns {findings, alarms, ok}. Pure: no network, no writes, no clock reads.
    The edge outcomes are pre-fetched summaries (fetch_domain/fetch_rdap) or None for not-run."""
    findings = (check_runs("collect", collect_runs, now)
                + check_runs("assemble", assemble_runs, now)
                + check_manifests(derived, now, product_day)
                + check_domain(domain_outcome)
                + check_rdap(rdap_outcome, now))
    alarms = [f for f in findings if f["level"] == _ALARM]
    return {"findings": findings, "alarms": alarms, "ok": not alarms,
            "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "product_day": product_day}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _load_runs(path: str | None) -> list[dict] | None:
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("workflow_runs", data) if isinstance(data, dict) else data


def _report(result: dict) -> str:
    lines = [f"OnScript watchdog {result['checked_at']} (product day {result['product_day']})"]
    for f in result["findings"]:
        lines.append(f"  [{f['level'].upper():5}] {f['check']}: {f['detail']}")
    lines.append(f"  {len(result['alarms'])} alarm(s)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OnScript outermost liveness probe")
    ap.add_argument("--collect-runs", help="JSON file of collect.yml run history (gh api)")
    ap.add_argument("--assemble-runs", help="JSON file of assemble.yml run history (gh api)")
    ap.add_argument("--derived", default=str(config.DERIVED))
    ap.add_argument("--now", help="ISO instant to judge against (testing)")
    ap.add_argument("--product-day", help="override product day (testing)")
    ap.add_argument("--no-notify", action="store_true", help="print only, never page")
    ap.add_argument("--probe-domain", action="store_true",
                    help="live-fetch the public site (network; the workflow passes this)")
    ap.add_argument("--probe-rdap", action="store_true",
                    help="live-query RDAP for the domain (network; the workflow passes this)")
    args = ap.parse_args(argv)

    now = _parse_iso(args.now) or datetime.now(timezone.utc)
    result = evaluate(derived=Path(args.derived), now=now,
                      product_day=args.product_day or util.product_day(),
                      collect_runs=_load_runs(args.collect_runs),
                      assemble_runs=_load_runs(args.assemble_runs),
                      domain_outcome=fetch_domain() if args.probe_domain else None,
                      rdap_outcome=fetch_rdap() if args.probe_rdap else None)
    report = _report(result)
    print(report)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:  # pragma: no cover - Actions only
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### Watchdog\n\n```\n{report}\n```\n")

    for f in result["alarms"]:  # annotate so the run page carries the reason, not just ntfy
        print(f"::error::watchdog {f['check']}: {f['detail']}")

    if result["alarms"] and not args.no_notify:
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        body = "\n".join(f"- {f['detail']}" for f in result["alarms"])
        if repo:
            body += f"\n\nhttps://github.com/{repo}/actions"
        ops.ntfy(f"OnScript watchdog: {len(result['alarms'])} alarm(s)", body, priority="high")

    # Exit 0 even when alarms fire: the probe did its job, and the page has already been sent. A
    # non-zero exit here would trip the workflow's own `if: failure()` dead-man and page a SECOND
    # time for one incident. The job goes red only when the watchdog ITSELF breaks, which is the
    # one condition its in-job dead-man is there to report. One alert per failure mode.
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
