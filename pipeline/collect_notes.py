"""The informational notes RUN A records in its manifest, owned beside the writer (S74-17 P0).

`run_collect.collect` keeps two lists. `alerts` holds faults and paged conditions (upstream stale,
months missing, a focus day after the product day, anomalously low volume); the status page opens an
incident on them. `notes` holds three healthy, informational facts that used to share the `alerts`
list and so opened an incident on most days since S73: the cursor holding at the last complete day,
a sweep that backfilled earlier days, and a volume comparison withheld on an immature day.

The writer composes each note with the functions below, so the prefixes that classify a manifest
written before this change (whose notes sit inside `alerts`) cannot drift from what the writer emits
(docs/37 rule 1). Stdlib only, so the status renderer can import it without pulling in the collector.
"""
from __future__ import annotations

FOCUS_HELD = "focus held at "
BACKFILLED = "backfilled day records "
VOLUME_WITHHELD = "volume comparison withheld on "
NOTE_PREFIXES = (FOCUS_HELD, BACKFILLED, VOLUME_WITHHELD)


def focus_held(focus_day: str, reason: str) -> str:
    return f"{FOCUS_HELD}{focus_day}: {reason}"


def backfilled(records_written, boards_written) -> str:
    return (f"{BACKFILLED}{records_written} and silence boards {boards_written} that earlier runs left "
            f"unwritten")


def volume_withheld(focus_day: str, why: str, today) -> str:
    return f"{VOLUME_WITHHELD}{focus_day}: {why} ({today} statements)"


def is_note(line) -> bool:
    return isinstance(line, str) and line.startswith(NOTE_PREFIXES)


def real_alerts(collect_manifest: dict) -> list | None:
    """The fault alerts of a collect manifest, whichever schema wrote it. None when the manifest
    carries no `alerts` field at all (unavailable, never a clean reading)."""
    alerts = (collect_manifest or {}).get("alerts")
    if alerts is None:
        return None
    return [a for a in alerts if not is_note(a)]
