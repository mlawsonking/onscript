"""The single public-window calculation shared by phrase rendering and evidence building."""
from __future__ import annotations

from . import config


def public_phrase_window(pdata: dict) -> dict:
    """Return a new Stage-1-only series plus its first day and max per-party peak.

    The retained input is never mutated. The peak follows the public D/R instrument, matching the
    two lines plotted on phrase pages and the parties for which caucus denominators are published.
    """
    rows = [dict(r) for r in (pdata.get("series") or [])
            if isinstance(r, dict) and isinstance(r.get("day"), str)
            and r.get("day") >= config.STAGE1_EPOCH]
    rows.sort(key=lambda r: r.get("day") or "")

    peak_units = None
    peak_day = ""
    for row in rows:
        counts = []
        for party in config.COMPOSITE_PARTIES:
            try:
                counts.append(max(0, int(row.get(party) or 0)))
            except (TypeError, ValueError):
                counts.append(0)
        row_peak = max(counts or [0])
        if peak_units is None or row_peak > peak_units:
            peak_units, peak_day = row_peak, row.get("day") or ""
    return {
        "series": rows,
        "first_day": (rows[0].get("day") or "") if rows else "",
        "peak_units": peak_units,
        "peak_day": peak_day,
    }
