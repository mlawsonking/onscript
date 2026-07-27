"""Date-effective caucus denominators and office-source coverage states."""
from __future__ import annotations

from datetime import date

from . import config, util


ROSTER_PATH = config.REFERENCE / "date-effective-roster.json"
SOURCE_REGISTRY_PATH = config.REFERENCE / "office-source-coverage.json"
METHOD_VERSION = "date-effective-denominators-v1"
SOURCE_STATES = frozenset({"source_supported", "source_unsupported", "unattestable"})


def load_roster() -> dict:
    return util.read_json(ROSTER_PATH, {}) or {}


def load_source_registry() -> dict:
    return util.read_json(SOURCE_REGISTRY_PATH, {}) or {}


def _party(value: str | None) -> str | None:
    if value in config.ALL_PARTIES:
        return value
    return config.PARTY_NORMALIZE.get((value or "").strip().lower())


def _contains(interval: dict, day: str) -> bool:
    start = interval.get("start") or "0001-01-01"
    end = interval.get("end_exclusive") or "9999-12-31"
    return start <= day < end


def active_interval(row: dict, day: str) -> dict | None:
    """Return the latest-starting active interval for a day."""
    active = [interval for interval in (row.get("intervals") or []) if _contains(interval, day)]
    return max(active, key=lambda interval: interval.get("start") or "") if active else None


def eligible_offices(day: str, party: str, *, roster_table: dict | None = None) -> dict[str, dict]:
    """Voting offices in the named party on the day.

    An office is absent during a vacancy because no service interval contains that day.
    Separate intervals make a party switch effective on its recorded date.
    """
    date.fromisoformat(day)
    table = roster_table if roster_table is not None else load_roster()
    rows = table.get("offices") or {}
    out = {}
    for bioguide, row in rows.items():
        interval = active_interval(row, day)
        if not interval or _party(interval.get("party")) != party:
            continue
        if interval.get("voting_status", "voting") != "voting":
            continue
        out[bioguide] = {**row, "active_interval": interval}
    return out


def source_state(bioguide: str, day: str, *, registry: dict | None = None) -> str:
    """Read an explicit source attestation. Missing evidence is unattestable."""
    data = registry if registry is not None else load_source_registry()
    rows = (data.get("attestations") or {}).get(bioguide) or []
    active = [row for row in rows if _contains(row, day)]
    if not active:
        return "unattestable"
    state = max(active, key=lambda row: row.get("start") or "").get("state")
    return state if state in SOURCE_STATES else "unattestable"


def _family_id(statement: dict) -> str | None:
    return ((statement.get("document_family") or {}).get("family_id")
            or statement.get("joint_group") or statement.get("id"))


def daily_measures(day: str, party: str, statements: list[dict], *,
                   roster_table: dict | None = None, source_registry: dict | None = None) -> dict:
    """Return five distinct party-day measures without inferring source coverage."""
    eligible = eligible_offices(day, party, roster_table=roster_table)
    rows = [row for row in statements
            if row.get("published_at") == day and row.get("lane") == 1
            and _party((row.get("member") or {}).get("party")) == party]
    observed = {(row.get("member") or {}).get("bioguide") for row in rows
                if (row.get("member") or {}).get("bioguide")}
    states = {bioguide: source_state(bioguide, day, registry=source_registry)
              for bioguide in eligible}
    state_counts = {state: sum(value == state for value in states.values())
                    for state in sorted(SOURCE_STATES)}
    families = {_family_id(row) for row in rows if _family_id(row)}
    return {
        "method_version": METHOD_VERSION,
        "window": f"party-day {day}",
        "eligible_caucus_offices": len(eligible),
        "source_supported_offices": state_counts["source_supported"],
        "observed_publishing_offices": len(observed),
        "publications": len({row.get("id") for row in rows if row.get("id")}),
        "document_families": len(families),
        "office_source_states": state_counts,
    }
