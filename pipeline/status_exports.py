"""Manifest-backed status, API exports, and filtered alert feeds."""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
from datetime import date, timedelta
from pathlib import Path

from . import config, corrections, eligibility, instrument_fingerprint, util


METHOD_VERSION = "status-exports-v1"
API_VERSION = "v1"
API_STATUS = "experimental"
DEPRECATION_POLICY = {
    "stability": "experimental",
    "supported_commitment": False,
    "field_removal_notice_days": 30,
    "additive_fields_may_appear": True,
    "breaking_changes_require_new_version": True,
}
FRESHNESS_SLO_HOURS = 36.0
VERIFIER_DROP_SLO = 0.25
EXPECTED_POSTING_PARTIES = len(config.COMPOSITE_PARTIES)
VERIFIER_DROP_WINDOW_DAYS = 30
# Three calendar windows publish together so a recent breach cannot hide behind a healthy
# long window (R-36.6). Each is (span in calendar days, model key).
VERIFIER_DROP_WINDOWS = ((1, "latest"), (7, "seven_day"), (30, "thirty_day"))
# The recent (seven-day) rate at this multiple of the long (thirty-day) rate is a red spike.
# Estimator: seven-day dropped/offered over thirty-day dropped/offered; unit: ratio.
VERIFIER_DROP_RECENT_MULTIPLE = 2.0
# A measured day trailing the expected latest complete day by more than this is a lag incident.
PUBLICATION_LAG_MAX_DAYS = 1
POSTING_STATES = frozenset({"disabled", "not_due", "ready", "held", "partial", "posted", "failed"})
# Absolute severity precedence: no lower severity ever overrides a higher one (R-36.6).
SEVERITY_ORDER = ("critical", "red", "amber", "green", "neutral", "unknown")


def _worst(statuses) -> str:
    """Return the highest-precedence status present, defaulting to unknown when empty."""
    present = {status for status in statuses if status}
    for level in SEVERITY_ORDER:
        if level in present:
            return level
    return "unknown"


def _manifest_day(name: str, manifest: dict) -> str | None:
    """Parse the calendar day of an assemble manifest from its content or filename."""
    day = manifest.get("day")
    if isinstance(day, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        return day
    stem = name[len("assemble-"):-len(".json")] if name.startswith("assemble-") and name.endswith(".json") else ""
    return stem if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stem) else None


def _publication_lag_days(measured_day: str | None, now: str | None = None) -> int | None:
    """Calendar days the measured day trails the expected latest complete day (prior day)."""
    if not measured_day:
        return None
    try:
        measured = date.fromisoformat(measured_day)
        reference = date.fromisoformat(now[:10]) if now else date.today()
    except (TypeError, ValueError):
        return None
    return max(0, ((reference - timedelta(days=1)) - measured).days)


def _source(manifest: str, field: str, value) -> dict:
    return {"manifest": manifest, "field": field, "value": value}


def _check(identifier: str, label: str, value, unit: str, status: str,
           sources: list[dict], derivation: str | None = None) -> dict:
    return {
        "id": identifier,
        "label": label,
        "value": value,
        "unit": unit,
        "status": status if value is not None else "unknown",
        "sources": sources,
        "derivation": derivation,
    }


def _streak(assemble_history: list[tuple[str, dict]], *, clean: bool) -> tuple[int | None, list[dict]]:
    if not assemble_history:
        return None, []
    value = 0
    sources = []
    for name, manifest in reversed(sorted(assemble_history)):
        fields = [
            _source(name, "unattended", manifest.get("unattended")),
            _source(name, "degraded", manifest.get("degraded")),
            _source(name, "forced_finalize", manifest.get("forced_finalize")),
        ]
        sources.extend(fields)
        published = (manifest.get("publication_state") in {"published", "corrected"}
                     or (manifest.get("readiness") or {}).get("ready") is True)
        if not published:
            break
        if clean and (manifest.get("unattended") is not True or manifest.get("degraded") is not False
                      or manifest.get("forced_finalize") is not False):
            break
        value += 1
    return value, sources


def _posting_state(post: dict) -> str:
    if post.get("posting_enabled") is False:
        return "disabled"
    if post.get("due") is False:
        return "not_due"
    if post.get("atomic_hold") is True:
        return "held"
    results = post.get("results") if isinstance(post.get("results"), list) else []
    posted = sum(row.get("posted") is True for row in results)
    if posted == EXPECTED_POSTING_PARTIES:
        return "posted"
    if posted:
        return "partial"
    if post.get("ready") is True and not results:
        return "ready"
    return "failed"


def _windowed_drop(history: list[tuple[str, dict]], anchor_day: str | None,
                   span_days: int) -> dict:
    """Verifier drop over a CALENDAR window ending at anchor_day, not a manifest count.

    Returns dropped over offered plus an unmeasured-day count (days present with no offered
    claims), so a recent window cannot be diluted by counting old files as recent days.
    """
    low = None
    if anchor_day:
        try:
            low = (date.fromisoformat(anchor_day) - timedelta(days=span_days - 1)).isoformat()
        except (TypeError, ValueError):
            low = None
    offered = dropped = measured_days = unmeasured_days = 0
    sources = []
    for name, manifest in sorted(history):
        day = _manifest_day(name, manifest)
        if not day or (low is not None and not (low <= day <= anchor_day)):
            continue
        measured_days += 1
        row_offered = 0
        for party in config.COMPOSITE_PARTIES:
            party_row = (manifest.get("per_party_llm") or {}).get(party) or {}
            published = party_row.get("claims_published")
            rejected = party_row.get("claims_dropped")
            sources.extend([
                _source(name, f"per_party_llm.{party}.claims_published", published),
                _source(name, f"per_party_llm.{party}.claims_dropped", rejected),
            ])
            if isinstance(published, int) and isinstance(rejected, int):
                row_offered += published + rejected
                offered += published + rejected
                dropped += rejected
        if row_offered == 0:
            unmeasured_days += 1
    return {
        "days": measured_days, "window_days": span_days,
        "dropped": dropped, "offered": offered,
        "rate": round(dropped / offered, 6) if offered else None,
        "unmeasured_days": unmeasured_days,
        "sources": sources,
        "unit": "claims dropped over claims offered",
    }


def build_status(manifests: dict[str, dict], assemble_history: list[tuple[str, dict]] | None = None,
                 correction_rows: list[dict] | None = None, now: str | None = None) -> dict:
    """Build a status model. Templates receive this model and perform no measurements.

    `now` is injectable so publication-lag and window anchoring are deterministic in tests.
    """
    collect_name, collect = "collect-latest.json", manifests.get("collect") or {}
    assemble_name, assemble = "assemble-latest-day.json", manifests.get("assemble") or {}
    post_name, post = "post-latest-day.json", manifests.get("post") or {}
    checks = []

    volume = (collect.get("volume") or {}).get("today")
    anomalous = (collect.get("volume") or {}).get("anomalously_low")
    checks.append(_check(
        "collection", "Collection volume", volume, "statements",
        "green" if volume is not None and anomalous is False else "red",
        [_source(collect_name, "volume.today", volume),
         _source(collect_name, "volume.anomalously_low", anomalous)],
    ))

    ready = (assemble.get("readiness") or {}).get("ready")
    count = (assemble.get("readiness") or {}).get("count")
    checks.append(_check(
        "assembly", "Assembly input", count, "statements",
        "green" if count is not None and ready is True else "red",
        [_source(assemble_name, "readiness.count", count),
         _source(assemble_name, "readiness.ready", ready)],
    ))

    # R-36.6: freshness splits into five separately labeled checks so transport freshness
    # never reads as product freshness. Each is unknown when its input is absent.
    age = (collect.get("source_freshness") or {}).get("age_hours")
    checks.append(_check(
        "source_fetch", "Last successful source fetch", age, "hours",
        "green" if age is not None and age <= FRESHNESS_SLO_HOURS else "red",
        [_source(collect_name, "source_freshness.age_hours", age)],
        "hours since the upstream mirror last pushed (transport only)",
    ))

    days_present = collect.get("days_present")
    watermark = max(days_present) if isinstance(days_present, list) and days_present else None
    focus = collect.get("focus_day") or assemble.get("day")
    checks.append(_check(
        "content_watermark", "Content watermark", watermark, "day",
        "green" if watermark is not None and focus is not None and watermark >= focus
        else ("red" if watermark is not None else "unknown"),
        [_source(collect_name, "days_present", days_present),
         _source(assemble_name, "day", assemble.get("day"))],
        "newest ingested source day compared with the focus day",
    ))

    anomalous_volume = (collect.get("volume") or {}).get("anomalously_low")
    checks.append(_check(
        "expected_day", "Expected-day completeness", ready, "boolean",
        "green" if ready is True and anomalous_volume is not True else "red",
        [_source(assemble_name, "readiness.ready", ready),
         _source(collect_name, "volume.anomalously_low", anomalous_volume)],
        "the expected latest complete day assembled without a low-volume anomaly",
    ))

    lag = _publication_lag_days(assemble.get("day"), now)
    checks.append(_check(
        "publication_lag", "Publication lag", lag, "days",
        "green" if lag is not None and lag <= PUBLICATION_LAG_MAX_DAYS
        else ("red" if lag is not None else "unknown"),
        [_source(assemble_name, "day", assemble.get("day"))],
        "calendar days the measured day trails the expected latest complete day",
    ))

    endpoint_ok = (collect.get("source_freshness") or {}).get("ok")
    checks.append(_check(
        "endpoint_health", "Endpoint health", endpoint_ok, "boolean",
        "green" if endpoint_ok is True else ("red" if endpoint_ok is False else "unknown"),
        [_source(collect_name, "source_freshness.ok", endpoint_ok)],
        "whether the upstream fetch reported ok; endpoint completeness is not claimed",
    ))

    history = assemble_history or []
    clean_streak, streak_sources = _streak(history, clean=True)
    publication_streak, publication_sources = _streak(history, clean=False)
    checks.append(_check(
        "streak", "Clean-run streak", clean_streak, "days",
        "green" if clean_streak is not None and clean_streak > 0 else "red", streak_sources,
        "count consecutive manifests whose unattended is true and whose degraded and forced_finalize are false",
    ))

    # R-36.6: three calendar windows publish together. The red gate fires when the seven-day
    # rate breaches the SLO or the seven-day rate materially exceeds the thirty-day rate, so a
    # recent breach is never hidden by a healthy long window.
    anchor = max((_manifest_day(name, manifest) for name, manifest in history
                  if _manifest_day(name, manifest)), default=None) or assemble.get("day")
    drop_windows = {key: _windowed_drop(history, anchor, span) for span, key in VERIFIER_DROP_WINDOWS}
    seven, thirty = drop_windows["seven_day"], drop_windows["thirty_day"]
    seven_rate, thirty_rate = seven["rate"], thirty["rate"]
    verifier_red = (
        (seven_rate is not None and seven_rate >= VERIFIER_DROP_SLO)
        or (seven_rate is not None and thirty_rate not in (None, 0)
            and seven_rate >= thirty_rate * VERIFIER_DROP_RECENT_MULTIPLE)
    )
    checks.append(_check(
        "verifier_drop", "Verifier drop rate (seven day)", seven_rate, "share",
        "red" if verifier_red else "green", seven["sources"],
        "seven-day claims dropped over offered; red on an SLO breach or a spike over the long window",
    ))
    drop_window = thirty  # existing key keeps its thirty-day meaning (additive)

    degraded = assemble.get("degraded")
    checks.append(_check(
        "degraded", "Degraded publication", degraded, "boolean",
        "green" if degraded is False else "red", [_source(assemble_name, "degraded", degraded)],
    ))

    results = post.get("results") if isinstance(post.get("results"), list) else None
    posted = sum(1 for row in (results or []) if row.get("posted") is True) if results is not None else None
    posting_sources = [
        _source(post_name, f"results.{index}.posted", row.get("posted"))
        for index, row in enumerate(results or [])
    ]
    posting_state = _posting_state(post)
    posting_status = ("neutral" if posting_state in {"disabled", "not_due"}
                      else "green" if posting_state == "posted" else "red")
    checks.append(_check(
        "posting", "Parties posted", posted, "parties",
        posting_status, posting_sources,
        "count manifest result rows whose posted field is true",
    ))

    correction_count = assemble.get("corrections_count")
    supplied_corrections = correction_rows if correction_rows is not None else []
    open_rows = [row for row in supplied_corrections if row.get("status") == "open"]
    # An open critical correction surfaces at the top of the ladder; an open major is amber.
    if any(row.get("severity") == "critical" for row in open_rows):
        correction_status = "critical"
    elif any(row.get("severity") == "major" for row in open_rows):
        correction_status = "amber"
    elif correction_rows is not None or isinstance(correction_count, int):
        correction_status = "green"
    else:
        correction_status = "red"
    checks.append(_check(
        "corrections", "Open corrections", len(open_rows) if correction_rows is not None else correction_count,
        "corrections", correction_status,
        [_source(assemble_name, "corrections_count", correction_count)],
    ))

    alert_sources = [
        _source(collect_name, "alerts", collect.get("alerts")),
        _source(assemble_name, "alerts", assemble.get("alerts")),
        _source(post_name, "asymmetric", post.get("asymmetric")),
        _source(post_name, "atomic_hold", post.get("atomic_hold")),
    ]
    incident_available = all(source["value"] is not None for source in alert_sources)
    incident_open = bool((collect.get("alerts") or []) or (assemble.get("alerts") or [])
                         or post.get("asymmetric") or post.get("atomic_hold")) if incident_available else None
    checks.append(_check(
        "incident", "Incident state", "open" if incident_open else "clear" if incident_open is False else None,
        "state", "green" if incident_open is False else "red", alert_sources,
        "open when either manifest has alerts or the post manifest is asymmetric or held",
    ))

    generated_at = assemble.get("generated_at") or collect.get("generated_at") or post.get("generated_at")
    # Absolute severity precedence: the overall status is the worst any check reports, so a lower
    # severity never overrides a higher one (R-36.6). No check is special-cased.
    overall_status = _worst(row["status"] for row in checks)
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "generated_at": generated_at,
        "overall_status": overall_status,
        "streaks": {
            "publication": {"value": publication_streak, "unit": "days", "sources": publication_sources},
            "clean_run": {"value": clean_streak, "unit": "days", "sources": streak_sources},
        },
        "verifier_drop_window": drop_window,
        "verifier_drop_windows": drop_windows,
        "posting_state": posting_state,
        "posting_states": sorted(POSTING_STATES),
        "checks": checks,
        "slos": [
            {"check": "source_fetch", "target": FRESHNESS_SLO_HOURS, "unit": "hours maximum",
             "status": "provisional"},
            {"check": "verifier_drop", "target": VERIFIER_DROP_SLO, "unit": "share maximum",
             "status": "provisional"},
            {"check": "posting", "target": EXPECTED_POSTING_PARTIES, "unit": "parties",
             "status": "provisional"},
            *[{"check": f"correction_{severity}", "target": policy["correct_hours"],
               "unit": "hours to correction", "status": "provisional"}
              for severity, policy in corrections.SEVERITY_POLICY.items()],
        ],
    }


def load_manifest_inputs(manifest_dir: Path) -> tuple[dict, list[tuple[str, dict]]]:
    collect = util.read_json(manifest_dir / "collect-latest.json", {}) or {}
    pointer = util.read_json(manifest_dir / "assemble-latest.json", {}) or {}
    day = pointer.get("day")
    assemble = util.read_json(manifest_dir / f"assemble-{day}.json", {}) if day else {}
    post = util.read_json(manifest_dir / f"post-{day}.json", {}) if day else {}
    history = []
    for path in sorted(manifest_dir.glob("assemble-*.json")):
        if path.stem == "assemble-latest":
            continue
        history.append((path.name, util.read_json(path, {}) or {}))
    return {"collect": collect, "assemble": assemble or {}, "post": post or {}}, history


def _canonical(payload) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def envelope(payload, generated_at: str | None, *, resource: str = "legacy",
             fingerprint: dict | None = None) -> dict:
    raw = _canonical(payload)
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "api_version": API_VERSION,
        "api_status": API_STATUS,
        "resource": resource,
        "generated_at": generated_at,
        "payload_fields": sorted(payload) if isinstance(payload, dict) else [],
        "deprecation_policy": DEPRECATION_POLICY,
        "checksums": {"payload_sha256": hashlib.sha256(raw).hexdigest()},
        # Inherit the cycle fingerprint when the caller stamped one, so an export
        # carries the same identity as the day it describes (docs/36 Y1).
        "instrument_fingerprint": fingerprint or instrument_fingerprint.build(),
        "payload": payload,
    }


def verify_envelope(value: dict) -> bool:
    expected = hashlib.sha256(_canonical(value.get("payload"))).hexdigest()
    return (value.get("checksums") or {}).get("payload_sha256") == expected


def days_csv(days: list[tuple[str, dict]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["day", "degraded", "daily_line_parties", "top_phrase_rows"])
    for day, payload in days:
        lines = payload.get("daily_lines") or {}
        writer.writerow([day, bool(payload.get("degraded")),
                         sum(1 for party in config.COMPOSITE_PARTIES if isinstance(lines.get(party), dict)),
                         len(payload.get("top_synchronized") or [])])
    return stream.getvalue().encode("utf-8")


def _classified_phrase_row(row: dict, day: str | None) -> dict:
    """Return the five ruled export fields for one phrase row, classified at emit time.

    Historical committed records predate these fields, so they are re-derived from the
    deterministic classifier rather than read from the row (R-36.7). Fail-closed: a
    nonprivate row must carry a class and a classifier version.
    """
    classification = eligibility.classify_phrase(
        row.get("ngram") or "", day=day, family_count=row.get("family_count"))
    classifier = classification.get("classifier") or {}
    fields = {
        "surface_class": classification.get("surface_class"),
        "surface_eligible": classification.get("surface_eligible"),
        "classification_rule": classifier.get("rule"),
        "classifier_version": classifier.get("name"),
        "family_count": row.get("family_count"),
    }
    if fields["surface_class"] != "private" and not (fields["surface_class"] and fields["classifier_version"]):
        raise ValueError("phrase export row is missing its surface class or classifier version")
    return fields


def phrases_csv(days: list[tuple[str, dict]]) -> bytes:
    """One observed phrase per row with no nested cells, each self-describing its class."""
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["day", "party", "phrase", "observed_offices", "surface_class",
                     "surface_eligible", "classification_rule", "classifier_version", "family_count"])
    for day, payload in days:
        for row in sorted(payload.get("top_synchronized") or [],
                          key=lambda value: (value.get("party") or "", value.get("ngram") or "")):
            fields = _classified_phrase_row(row, day)
            writer.writerow([day, row.get("party"), row.get("ngram"), row.get("day_peak"),
                             fields["surface_class"], fields["surface_eligible"],
                             fields["classification_rule"], fields["classifier_version"],
                             fields["family_count"]])
    return stream.getvalue().encode("utf-8")


def corrections_csv(rows: list[dict]) -> bytes:
    """One correction per row with affected days normalized into separate rows."""
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["correction_id", "affected_day", "severity", "status", "logged"])
    for row in sorted(rows, key=lambda value: value.get("correction_id") or ""):
        days = row.get("affected_days") or [""]
        for day in days:
            writer.writerow([row.get("correction_id"), day, row.get("severity"),
                             row.get("status"), row.get("logged")])
    return stream.getvalue().encode("utf-8")


RESOURCE_FIELDS = {
    "status": ("status",),
    "days": ("days",),
    "phrases": ("phrases",),
    "corrections": ("corrections",),
    "instrument": ("instrument_fingerprint",),
    "schema": ("api_status", "api_version", "deprecation_policy", "resources"),
}


RESOURCE_ENDPOINTS = {
    "status": "api/v1/resources/status.json",
    "days": "api/v1/resources/days.json",
    "phrases": "api/v1/resources/phrases.json",
    "corrections": "api/v1/resources/corrections.json",
    "instrument": "api/v1/resources/instrument.json",
    "schema": "api/v1/schema.json",
}


def _resource_envelope(resource: str, payload: dict, generated_at: str | None,
                       fingerprint: dict | None = None) -> dict:
    expected = list(RESOURCE_FIELDS[resource])
    if sorted(payload) != sorted(expected):
        raise ValueError(f"{resource} fields differ from the public API contract")
    value = envelope(payload, generated_at, resource=resource, fingerprint=fingerprint)
    value["payload_fields"] = expected
    return value


def experimental_exports(status: dict, days: list[tuple[str, dict]], phrases: dict,
                         correction_rows: list[dict],
                         fingerprint: dict | None = None) -> dict[str, bytes]:
    """Emit experimental resource endpoints and normalized CSV exports."""
    generated_at = status.get("generated_at")
    cycle_fingerprint = fingerprint or instrument_fingerprint.build()
    day_rows = [{
        "day": day,
        "degraded": payload.get("degraded"),
        "composite_states": {
            party: ((payload.get("daily_lines") or {}).get(party) or {}).get("composite_state")
            for party in config.COMPOSITE_PARTIES
        },
    } for day, payload in days]
    phrase_rows = [{**dict(row), **_classified_phrase_row(row, phrases.get("day"))}
                   for row in (phrases.get("by_peak") or [])]
    resources = {
        "status": {"status": status},
        "days": {"days": day_rows},
        "phrases": {"phrases": phrase_rows},
        "corrections": {"corrections": correction_rows},
        "instrument": {"instrument_fingerprint": cycle_fingerprint},
        "schema": {
            "api_status": API_STATUS,
            "api_version": API_VERSION,
            "deprecation_policy": DEPRECATION_POLICY,
            "resources": [
                {"name": name, "endpoint": RESOURCE_ENDPOINTS[name],
                 "payload_fields": list(RESOURCE_FIELDS[name])}
                for name in RESOURCE_ENDPOINTS if name != "schema"
            ],
        },
    }
    out = {
        RESOURCE_ENDPOINTS[name]: _canonical(
            _resource_envelope(name, payload, generated_at, cycle_fingerprint)) + b"\n"
        for name, payload in resources.items()
    }
    out["api/v1/exports/days.csv"] = days_csv(days)
    out["api/v1/exports/phrases.csv"] = phrases_csv(days)
    out["api/v1/exports/corrections.csv"] = corrections_csv(correction_rows)
    return out


def api_documentation() -> str:
    """Render field documentation from the emitter's contract constants."""
    rows = []
    for name, endpoint in RESOURCE_ENDPOINTS.items():
        fields = ", ".join(RESOURCE_FIELDS[name])
        rows.append(f"<tr><td><code>/{endpoint}</code></td><td>{name}</td><td>{fields}</td></tr>")
    return (
        "<h1>Experimental API</h1>"
        "<p class='subhead'>These static resources are experimental. They are not a supported API "
        "commitment before Gate B.</p>"
        "<p>Additive fields may appear. A field removal receives 30 days of notice. A breaking "
        "contract uses a new versioned path.</p>"
        "<table><thead><tr><th>Endpoint</th><th>Resource</th><th>Payload fields</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "<p>Normalized CSV exports: <code>/api/v1/exports/days.csv</code>, "
        "<code>/api/v1/exports/phrases.csv</code>, and "
        "<code>/api/v1/exports/corrections.csv</code>.</p>"
    )


def static_exports(status: dict, days: list[tuple[str, dict]], phrases: dict,
                   fingerprint: dict | None = None) -> dict[str, bytes]:
    generated_at = status.get("generated_at")
    cycle_fingerprint = fingerprint or instrument_fingerprint.build()
    day_payload = []
    for day, payload in days:
        lines = payload.get("daily_lines") or {}
        rows = payload.get("top_synchronized") or []
        day_payload.append({
            "day": day,
            "degraded": payload.get("degraded"),
            "daily_line_parties": [
                party for party in config.COMPOSITE_PARTIES if isinstance(lines.get(party), dict)
            ],
            "top_synchronized_counts": {
                party: sum(1 for row in rows if row.get("party") == party)
                for party in config.COMPOSITE_PARTIES
            },
        })
    # Each phrase row self-describes its class and classifier version (R-36.7).
    day_hint = phrases.get("day")
    enriched_phrases = dict(phrases)
    for key in ("by_peak", "by_velocity"):
        rows = phrases.get(key)
        if isinstance(rows, list):
            enriched_phrases[key] = [{**dict(row), **_classified_phrase_row(row, day_hint)}
                                     for row in rows]
    payloads = {
        "api/v1/status.json": status,
        "api/v1/days.json": day_payload,
        "api/v1/phrases.json": enriched_phrases,
        "api/v1/bulk.json": {"status": status, "days": day_payload, "phrases": enriched_phrases},
    }
    out = {
        name: _canonical(envelope(payload, generated_at, fingerprint=cycle_fingerprint)) + b"\n"
        for name, payload in payloads.items()
    }
    out["api/v1/days.csv"] = days_csv(days)
    return out


def watchlist_atom(days: list[tuple[str, dict]], terms: list[str], site_url: str | None = None) -> str:
    """Render one party-symmetric filtered feed from eligible measured phrases."""
    root = site_url or config.SITE_URL
    wanted = sorted({term.casefold().strip() for term in terms if term.strip()})
    entries = []
    for day, payload in reversed(days):
        for row in sorted(payload.get("top_synchronized") or [],
                          key=lambda value: (value.get("party") or "", value.get("ngram") or "")):
            phrase = row.get("ngram") or ""
            if not any(term in phrase.casefold() for term in wanted):
                continue
            classified = eligibility.classify_phrase(
                phrase, day=day, family_count=row.get("family_count")
            )
            if not eligibility.eligible_for_surface(classified, "alert"):
                continue
            party = row.get("party")
            if party not in config.COMPOSITE_PARTIES:
                continue
            url = f"{root}/day/{day}.html"
            identity = hashlib.sha256(f"{day}\n{party}\n{phrase}".encode("utf-8")).hexdigest()[:24]
            entries.append(
                "<entry>"
                f"<title>{html.escape(party)}: {html.escape(phrase)}</title>"
                f"<id>urn:onscript:watch:{identity}</id><link href=\"{html.escape(url)}\"/>"
                f"<updated>{html.escape(day)}T00:00:00Z</updated>"
                f"<summary>{html.escape(str(row.get('day_peak') or 0))} observed offices</summary>"
                "</entry>"
            )
    updated = f"{days[-1][0]}T00:00:00Z" if days else "1970-01-01T00:00:00Z"
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        '<title>OnScript watchlist alerts</title>'
        f'<id>{html.escape(root)}/alerts/feed.xml</id>'
        f'<updated>{updated}</updated>{"".join(entries)}</feed>\n'
    )
