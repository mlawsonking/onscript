"""LANE ISOLATION for the press spine (docs/12 Law L1, Fable Session 13c — Michael-confirmed).

`dwillis/congress-press` is a UNION OF DATASETS keyed by the record-level `date_source` field. The
`legacy` lane is a ProPublica import that stops FOREVER on 2021-01-03 — the day the 117th was seated.
The "2021 coverage collapse" is not behaviour: it is the union losing a dataset. A comparison whose
halves sit either side of that date is not comparing two eras, it is comparing two instruments.

This module is the deep archive's GENRE ISOLATION law (`pipeline/deep/lanes.py`) applied to
provenance: `lane_of()` raises on any row set that mixes lanes, so a series can never silently
compare ProPublica to a scraper. The remedy is ISOLATION, NOT NORMALIZATION — a scale factor cannot
repair a changing roster or a lane-dependent party mix.

MEASURED GROUND TRUTH (all 688,839 records of the 303-file mirror, 2026-07-17):

    date_source   n         window                    scraper/source fields
    legacy        485,948   2001-01-03 -> 2021-01-03  scraper=null, source=null   (ProPublica import)
    scraper       200,033   2009-01-06 -> 2026-07-09  scraper=<office>, source=<url>
    page_html       2,839   2014-12-09 -> 2026-07-09  scraper=<office>, source=<url>
    <missing>          19   date=null                 scraper="himes"

`date_source=='legacy'` <=> `scraper is None` <=> `source is None`, EXACTLY — a perfect partition.
That is what makes the lane recoverable at all.

WHY `date_source` IS NOT THE SAME THING AS "WHICH DATASET":
`date_source` records HOW THE DATE WAS DETERMINED, not which collector ran. `page_html` records are
scraper-collected (they carry `scraper` and `source`) and were merely date-parsed out of the page
body. So the INSTRUMENT partition — the one the seam is actually about — is binary:

    propublica = {legacy}                 the import that dies on the seam
    scraped    = {scraper, page_html}     the collector that continues across it

Both partitions are offered. `by="instrument"` (the default) is the seam-relevant one. `by="source"`
is the strict 3-way for a caller that has a date-provenance reason to separate `page_html`.

THE FOLD IS A RULING WITH A NUMBER ATTACHED — it is recorded here, not hidden: folding `page_html`
into `scraped` moves the same-era (2013-2020) lane party-mix gap from +5.67pt to +4.71pt of D-share.
`page_html` is only 2,839 records but is wildly D-skewed (D:R 12.47 in half A, on 4 members), so
ISOLATING it as a third lane would make the post-2021 corpus permanently "mixed" and unusable, while
filtering `date_source=='scraper'` would silently drop it. Folding is the default because both lanes
are the same instrument; the estimator is stated wherever the number is published (docs/12 L4).

TWO TRAPS THE MEASUREMENT FOUND, WRITTEN DOWN SO THEY ARE NOT REDISCOVERED:
  * A `legacy` filter does NOT buy 2001-2021 coverage. 99.67% of the lane is 2013-2020; its pre-2013
    tail is 1,594 records that are 99.9% Democrat (D 1,592 / R 2) and would poison any pre-2013 party
    statistic far worse than the seam itself. The `scraper` pre-2013 tail is the mirror image (~100%
    Republican: 2009 = D 0 / R 174).
  * "the scraper lane starts ~2018 at 49 offices" (CLAUDE.md:63) is LOOSE. It starts 2009-01-06 and is
    merely tiny until ~2017. A lane filter trusting "starts ~2018" silently admits 727 hyper-partisan
    pre-2013 scraper records.

The 19 untagged records need no rule: they are himes date-parse failures with `date: null` and are
already dropped unconditionally by `harness.iter_statements` (`if len(date) != 10: continue`).
"""
from __future__ import annotations

# The day the ProPublica import stops forever — the 117th Congress's first day. Every lane-crossing
# defect in the program is this date wearing a costume.
SEAM = "2021-01-03"

# The lane registry. `window` is measured from the mirror, not asserted from canon.
DATE_SOURCES: dict[str, dict] = {
    "legacy":    {"instrument": "propublica", "window": "2001-01-03..2021-01-03", "n": 485_948,
                  "role": "import",  "note": "ProPublica import; scraper/source both null; dies on the seam"},
    "scraper":   {"instrument": "scraped",    "window": "2009-01-06..",           "n": 200_033,
                  "role": "spine",   "note": "office scraper; tiny until ~2017; crosses the seam"},
    "page_html": {"instrument": "scraped",    "window": "2014-12-09..",           "n": 2_839,
                  "role": "spine",   "note": "scraper-collected, date parsed from page body; D-skewed, 4 offices"},
}

INSTRUMENTS = {src: meta["instrument"] for src, meta in DATE_SOURCES.items()}

# The lane that survives the seam. A cross-seam series is only ever legitimate within this one.
CROSSES_SEAM = "scraped"


class LaneIsolationError(RuntimeError):
    """Raised when a comparison would mix provenance lanes or span the seam. Never caught to
    'carry on with a warning' — a lane-crossing number is not a weaker finding, it is a different
    measurement wearing the finding's name (docs/13: the S4.7 sign inversion)."""


def date_source_of(row: dict) -> str | None:
    """A row's raw `date_source`. Deliberately NO default: `pipeline/deep/lanes.py` can default an
    untagged row to the press spine because there the spine is a known single lane, but here a
    missing tag means the lane is UNKNOWN, and silently defaulting an unknown into a lane is the
    exact class of error L1 exists to stop."""
    return row.get("date_source")


def instrument_of(row: dict) -> str | None:
    """The collector behind a row: 'propublica' | 'scraped' | None. This is the seam-relevant
    partition — the seam is where `propublica` ends."""
    src = date_source_of(row)
    return INSTRUMENTS.get(src) if src is not None else None


def _key(by: str):
    if by == "instrument":
        return instrument_of
    if by == "source":
        return date_source_of
    raise ValueError(f"by must be 'instrument' or 'source', got {by!r}")


def lane_of(rows, *, by: str = "instrument") -> str | None:
    """The single lane shared by every row, or raise. The in-code guard that forbids a cross-lane
    series (ProPublica-2015 next to scraper-2023 — an instrument change in a trend costume).

    Returns None for an empty set (nothing to isolate), mirroring `deep.lanes.lane_of`."""
    k = _key(by)
    lanes = {k(r) for r in rows}
    if not lanes:
        return None
    if None in lanes:
        raise LaneIsolationError(
            f"untagged row in a lane-isolated set (lanes seen: {sorted(x for x in lanes if x)}) — a row "
            f"without `date_source` has no known provenance and cannot be compared (docs/12 L1)")
    if len(lanes) > 1:
        raise LaneIsolationError(
            f"cross-lane series forbidden — mixes {sorted(lanes)}; comparisons live within ONE lane "
            f"(docs/12 L1). The remedy is isolation, not normalization: a scale factor cannot repair a "
            f"changing roster or a lane-dependent party mix.")
    return next(iter(lanes))


def spans_seam(dates) -> bool:
    """True if a window contains the seam — i.e. it has a date on or before 2021-01-03 AND one after.
    `SEAM` itself is a legacy day (the import's last), so the boundary is <= / >."""
    lo = hi = None
    for d in dates:
        d = (d or "")[:10]
        if len(d) != 10:
            continue
        lo = d if lo is None or d < lo else lo
        hi = d if hi is None or d > hi else hi
    if lo is None:
        return False
    return lo <= SEAM < hi


def assert_no_seam_span(dates, what: str = "window") -> None:
    """Raise if a computed window straddles the seam. For the sites where the defect is not a half
    split but a single window that happens to contain 2021-01-03 — e.g. the 2020 post-election
    90-day window (2020-11-04..2021-02-01), whose placebo runs on odd years only and is therefore
    structurally blind to the artifact sitting next to it."""
    if spans_seam(dates):
        raise LaneIsolationError(
            f"{what} spans the provenance seam {SEAM}: it is part ProPublica+scraper and part "
            f"scraper-only, so any count across it mixes two instruments (docs/12 L1)")


def assert_same_lane(rows_a, rows_b, *, by: str = "instrument", what: str = "halves") -> str:
    """Raise unless both sides of a comparison are the SAME single lane; return that lane.

    This is the guard for the program's primary control. The pre-registered splits — A=2013-2020 /
    B=2021-2026, and congress <=116 / >=117 — ARE the lane boundary (the 117th seats on the seam),
    so `confirms_in_both_halves` has been certifying findings using the confound as its validation
    split. Every such verdict is pending within-lane re-validation (docs/12 L1)."""
    la, lb = lane_of(rows_a, by=by), lane_of(rows_b, by=by)
    if la is None or lb is None:
        raise LaneIsolationError(f"{what}: an empty side has no lane to isolate")
    if la != lb:
        raise LaneIsolationError(
            f"{what} are two INSTRUMENTS, not two eras: {la!r} vs {lb!r}. Split-halves across the "
            f"{SEAM} seam compares ProPublica to a scraper (docs/12 L1) — re-validate within one lane.")
    return la
