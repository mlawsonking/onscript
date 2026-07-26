"""Manifest-backed status, API exports, and filtered alert feeds."""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
from pathlib import Path

from . import config, eligibility, util


METHOD_VERSION = "status-exports-v1"
FRESHNESS_SLO_HOURS = 36.0
VERIFIER_DROP_SLO = 0.25
EXPECTED_POSTING_PARTIES = len(config.COMPOSITE_PARTIES)


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


def _streak(assemble_history: list[tuple[str, dict]]) -> tuple[int | None, list[dict]]:
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
        if (manifest.get("unattended") is not True or manifest.get("degraded") is not False
                or manifest.get("forced_finalize") is not False):
            break
        value += 1
    return value, sources


def build_status(manifests: dict[str, dict], assemble_history: list[tuple[str, dict]] | None = None) -> dict:
    """Build a status model. Templates receive this model and perform no measurements."""
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

    age = (collect.get("source_freshness") or {}).get("age_hours")
    checks.append(_check(
        "freshness", "Source freshness", age, "hours",
        "green" if age is not None and age <= FRESHNESS_SLO_HOURS else "red",
        [_source(collect_name, "source_freshness.age_hours", age)],
    ))

    streak, streak_sources = _streak(assemble_history or [])
    checks.append(_check(
        "streak", "Clean unattended streak", streak, "days",
        "green" if streak is not None and streak > 0 else "red", streak_sources,
        "count consecutive manifests whose unattended is true and whose degraded and forced_finalize are false",
    ))

    party_rows = assemble.get("per_party_llm") or {}
    offered = dropped = 0
    verifier_sources = []
    verifier_measured = bool(party_rows)
    for party in config.COMPOSITE_PARTIES:
        row = party_rows.get(party) or {}
        published = row.get("claims_published")
        party_dropped = row.get("claims_dropped")
        verifier_sources.extend([
            _source(assemble_name, f"per_party_llm.{party}.claims_published", published),
            _source(assemble_name, f"per_party_llm.{party}.claims_dropped", party_dropped),
        ])
        if not isinstance(published, int) or not isinstance(party_dropped, int):
            verifier_measured = False
        else:
            offered += published + party_dropped
            dropped += party_dropped
    drop_rate = dropped / offered if verifier_measured and offered else None
    checks.append(_check(
        "verifier_drop", "Verifier drop rate", round(drop_rate, 6) if drop_rate is not None else None,
        "share", "green" if drop_rate is not None and drop_rate < VERIFIER_DROP_SLO else "red",
        verifier_sources, "sum claims_dropped divided by claims_published plus claims_dropped for both parties",
    ))

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
    checks.append(_check(
        "posting", "Parties posted", posted, "parties",
        "green" if posted == EXPECTED_POSTING_PARTIES else "red", posting_sources,
        "count manifest result rows whose posted field is true",
    ))

    correction_count = assemble.get("corrections_count")
    checks.append(_check(
        "corrections", "Corrections logged", correction_count, "corrections",
        "green" if isinstance(correction_count, int) else "red",
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
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "generated_at": generated_at,
        "checks": checks,
        "slos": [
            {"check": "freshness", "target": FRESHNESS_SLO_HOURS, "unit": "hours maximum",
             "status": "provisional"},
            {"check": "verifier_drop", "target": VERIFIER_DROP_SLO, "unit": "share maximum",
             "status": "provisional"},
            {"check": "posting", "target": EXPECTED_POSTING_PARTIES, "unit": "parties",
             "status": "provisional"},
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


def envelope(payload, generated_at: str | None) -> dict:
    raw = _canonical(payload)
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "generated_at": generated_at,
        "checksums": {"payload_sha256": hashlib.sha256(raw).hexdigest()},
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


def static_exports(status: dict, days: list[tuple[str, dict]], phrases: dict) -> dict[str, bytes]:
    generated_at = status.get("generated_at")
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
    payloads = {
        "api/v1/status.json": status,
        "api/v1/days.json": day_payload,
        "api/v1/phrases.json": phrases,
        "api/v1/bulk.json": {"status": status, "days": day_payload, "phrases": phrases},
    }
    out = {
        name: _canonical(envelope(payload, generated_at)) + b"\n"
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
            classified = eligibility.classify_phrase(phrase, day=day)
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
