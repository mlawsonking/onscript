"""Date-effective caucus denominators and office-source coverage states.

S74-11 (F1, F5). A roster snapshot is a record of one retrieval and can only speak for the days its
intervals were written to cover. Past that horizon every open House term "ends" at once, and a reader
that treats the scheduled term end as a vacancy turns a 430-office House into zero, so a caucus of 257
becomes 32 overnight and a count of 40 reads "40 of 32 (125.0%)". The quantity is impossible, so it is
made unreachable here, where it is computed (docs/37 rule 17): a day past the horizon gets a refused
state and no count, and a count larger than its eligible set gets a refused share and no fraction.
Renderers print the bare count in both cases and never substitute another denominator.

One population (F5): the numerators the site divides by this denominator count every D or R office
that published, delegates and the resident commissioner included, so the eligible set includes the
seated nonvoting offices too. The voting count is kept beside it as its own field.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from . import config, util


ROSTER_PATH = config.REFERENCE / "date-effective-roster.json"
SOURCE_REGISTRY_PATH = config.REFERENCE / "office-source-coverage.json"
METHOD_VERSION = "date-effective-denominators-v2"
SOURCE_STATES = frozenset({"source_supported", "source_unsupported", "unattestable"})

# Denominator states. Only STATE_OK carries a count a renderer may divide by.
STATE_OK = "date_effective"
STATE_HORIZON = "roster_horizon_exceeded"
STATE_EXCEEDS = "count_exceeds_roster"
STATE_UNAVAILABLE = "denominator_unavailable"
DENOMINATOR_STATES = frozenset({STATE_OK, STATE_HORIZON, STATE_EXCEEDS, STATE_UNAVAILABLE})


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


def _reference_day(table: dict) -> str | None:
    """The day the snapshot was taken: provenance retrieved_at, else the latest interval start."""
    retrieved = str(((table.get("provenance") or {}).get("retrieved_at")) or "")[:10]
    if len(retrieved) == 10:
        return retrieved
    starts = [interval.get("start") for row in (table.get("offices") or {}).values()
              for interval in (row.get("intervals") or []) if interval.get("start")]
    return max(starts) if starts else None


def derived_horizon(table: dict) -> str | None:
    """The last day the intervals can speak for, derived from the snapshot itself.

    The House intervals open on the reference day share one scheduled end (the Congress boundary;
    a pre-announced resignation is a singleton and does not set it). The day before that shared end
    is the last day on which the snapshot still describes a seated House."""
    day = _reference_day(table)
    if not day:
        return None
    ends: Counter = Counter()
    for row in (table.get("offices") or {}).values():
        for interval in row.get("intervals") or []:
            if interval.get("chamber") == "House" and interval.get("end_exclusive") and _contains(interval, day):
                ends[interval["end_exclusive"]] += 1
    if not ends:
        return None
    end = sorted(ends.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return (date.fromisoformat(end) - timedelta(days=1)).isoformat()


def roster_horizon(table: dict | None = None) -> str | None:
    """The latest date the snapshot can speak for: the earlier of an explicit provenance
    `valid_through` and the derived horizon. None means the snapshot speaks for no day at all."""
    table = table if table is not None else load_roster()
    explicit = (table.get("provenance") or {}).get("valid_through")
    candidates = [value for value in (explicit, derived_horizon(table)) if value]
    return min(candidates) if candidates else None


def within_horizon(day: str, table: dict | None = None) -> bool:
    horizon = roster_horizon(table)
    return bool(horizon) and day <= horizon


def eligible_offices(day: str, party: str, *, roster_table: dict | None = None,
                     voting_only: bool = False) -> dict[str, dict] | None:
    """Seated offices in the named party on the day, or None when the day is past the roster horizon.

    None is the refused state: there is no count to give, and an empty dict would be a count of zero.
    An office is absent during a vacancy because no service interval contains that day.
    Separate intervals make a party switch effective on its recorded date. Nonvoting offices
    (delegates, the resident commissioner) are included unless `voting_only`, because the numerators
    divided by this set count them (F5, one population).
    """
    date.fromisoformat(day)
    table = roster_table if roster_table is not None else load_roster()
    if not within_horizon(day, table):
        return None
    rows = table.get("offices") or {}
    out = {}
    for bioguide, row in rows.items():
        interval = active_interval(row, day)
        if not interval or _party(interval.get("party")) != party:
            continue
        if voting_only and interval.get("voting_status", "voting") != "voting":
            continue
        out[bioguide] = {**row, "active_interval": interval}
    return out


def eligible_count(day: str, party: str, *, roster_table: dict | None = None) -> dict:
    """{denominator_state, eligible_caucus_offices, roster_horizon}: the only denominator form a
    publishing caller should read. The count is None unless the state is STATE_OK."""
    table = roster_table if roster_table is not None else load_roster()
    offices = eligible_offices(day, party, roster_table=table)
    if offices is None:
        return {"denominator_state": STATE_HORIZON, "eligible_caucus_offices": None,
                "roster_horizon": roster_horizon(table)}
    return {"denominator_state": STATE_OK, "eligible_caucus_offices": len(offices),
            "roster_horizon": roster_horizon(table)}


def office_share(count, eligible, *, state: str | None = None) -> dict:
    """The one place a count-of-eligible share is computed.

    Returns {denominator_state, count, eligible, share}. `eligible` and `share` are None unless the
    state is STATE_OK, and a renderer prints a fraction only then. A count above its eligible set is
    an impossible share, refused here (STATE_EXCEEDS) rather than printed as 125 percent."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        return {"denominator_state": STATE_UNAVAILABLE, "count": count, "eligible": None, "share": None}
    if state not in (None, STATE_OK):
        return {"denominator_state": state if state in DENOMINATOR_STATES else STATE_UNAVAILABLE,
                "count": count, "eligible": None, "share": None}
    if isinstance(eligible, bool) or not isinstance(eligible, int) or eligible <= 0:
        return {"denominator_state": STATE_UNAVAILABLE, "count": count, "eligible": None, "share": None}
    if count > eligible:
        return {"denominator_state": STATE_EXCEEDS, "count": count, "eligible": None, "share": None}
    return {"denominator_state": STATE_OK, "count": count, "eligible": eligible, "share": count / eligible}


def party_denominator(party_row: dict | None) -> tuple[int | None, str]:
    """(eligible count or None, state) from one party row of a symmetry report. A report written
    before S74-11 has no state field; its integer count was computed inside the horizon."""
    row = party_row if isinstance(party_row, dict) else {}
    value = row.get("date_effective_eligible_caucus_offices")
    state = row.get("denominator_state")
    if state is None:
        state = STATE_OK if isinstance(value, int) and not isinstance(value, bool) and value > 0 \
            else STATE_UNAVAILABLE
    if state != STATE_OK:
        return None, state
    return value, state


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
    """Return five distinct party-day measures without inferring source coverage.

    The observed office count is restricted to the eligible set (F5): an office the roster does not
    seat that day is reported as `observed_offices_outside_roster`, never added to a numerator whose
    denominator cannot contain it. Past the horizon there is no eligible set; the observed count is
    the bare count and every roster-derived field is None."""
    table = roster_table if roster_table is not None else load_roster()
    eligible = eligible_offices(day, party, roster_table=table)
    rows = [row for row in statements
            if row.get("published_at") == day and row.get("lane") == 1
            and _party((row.get("member") or {}).get("party")) == party]
    observed = {(row.get("member") or {}).get("bioguide") for row in rows
                if (row.get("member") or {}).get("bioguide")}
    families = {_family_id(row) for row in rows if _family_id(row)}
    base = {
        "method_version": METHOD_VERSION,
        "window": f"party-day {day}",
        "roster_horizon": roster_horizon(table),
        "publications": len({row.get("id") for row in rows if row.get("id")}),
        "document_families": len(families),
    }
    if eligible is None:
        return {**base, "denominator_state": STATE_HORIZON, "eligible_caucus_offices": None,
                "voting_caucus_offices": None, "source_supported_offices": None,
                "observed_publishing_offices": len(observed), "observed_offices_outside_roster": None,
                "office_source_states": None}
    states = {bioguide: source_state(bioguide, day, registry=source_registry)
              for bioguide in eligible}
    state_counts = {state: sum(value == state for value in states.values())
                    for state in sorted(SOURCE_STATES)}
    inside = observed & set(eligible)
    voting = sum(1 for row in eligible.values()
                 if row["active_interval"].get("voting_status", "voting") == "voting")
    return {
        **base,
        "denominator_state": STATE_OK,
        "eligible_caucus_offices": len(eligible),
        "voting_caucus_offices": voting,
        "source_supported_offices": state_counts["source_supported"],
        "observed_publishing_offices": len(inside),
        "observed_offices_outside_roster": len(observed - inside),
        "office_source_states": state_counts,
    }
