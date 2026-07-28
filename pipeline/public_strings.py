"""Canonical public product language.

Public promises and labels live here so a wording review has one code surface. Renderers may
add page-specific facts, but they do not restate or expand these promises.
"""
from __future__ import annotations

import os


PRODUCT_PROMISE = (
    "OnScript measures repeated language in the congressional press releases it observes. "
    "It renders each party's observed day as a cited automated composite."
)

TAGLINE = "Observed congressional language, rendered as two cited automated composites."

DEFAULT_DESCRIPTION = (
    "OnScript measures repeated language in observed congressional press releases and publishes "
    "cited automated composites."
)

OG_IMAGE_ALT = "OnScript automated measurement of observed congressional language."

AUTOMATED_MEASUREMENT_LABEL = (
    "Automated measurement. Composite prose is generated from claims selected and counted by code."
)

POST_MEASUREMENT_LABEL = "automated measurement and composite"

SYMMETRY_PROMISE = (
    "Both parties use the same pipeline, prompts, thresholds, and publication checks. "
    "The nightly audit publishes the shared fingerprints."
)

CITATION_PROMISE = (
    "Every distilled claim links to at least three source publications from distinct supporting units."
)

DAY_CITATION_NOTE = "Every distilled claim above is citation-backed."

ABOUT_DESCRIPTION = "A symmetric, citation-backed measurement of observed congressional language."

BETA_LABEL = "Public beta measurement instrument"
BETA_LABEL_ENV = "ONSCRIPT_BETA_LABEL_ENABLED"


def beta_label_enabled(environ: dict[str, str] | None = None) -> bool:
    """Deployment gate for the centralized beta label. Dark by default."""
    source = os.environ if environ is None else environ
    return source.get(BETA_LABEL_ENV, "").strip().lower() in {"1", "true", "yes", "on"}

OBSERVATION_SCOPE = (
    "Observed means present in the mirrored source corpus. It does not mean every eligible office "
    "published or that every office endpoint was collected successfully."
)

COVERAGE_DEPRECATION_NOTE = (
    "The legacy coverage percentage is retained for schema compatibility. Use observed publishing "
    "offices, eligible caucus offices, and source collection health as separate fields."
)

SOURCE_HEALTH_LIMIT = (
    "The mirror can attest to the files used by this run. It cannot attest to every eligible office "
    "endpoint, so endpoint completeness is not claimed."
)

TERM_LADDER = (
    ("Repeated phrase", "The same exact phrase appears in more than one publication."),
    ("Convergence", "Distinct offices use the same phrase within the measured window."),
    ("Shared-document reuse", "Multiple offices publish the same or near-identical document family."),
    ("Propagation", "A repeated phrase spreads across offices over time."),
    ("Probable upstream origin", "Evidence supports a likely first upstream source, with uncertainty shown."),
    (
        "Observable language coordination",
        "A thesis-level description for measured language patterns. It does not assert motive or a private process.",
    ),
)


LEXICAL_TABLE_DISCLAIMER = (
    "This table lists repeated phrase observations, ranked by how many members used the same "
    "exact phrase. It is not filtered to coordinated messages, so it can include official names, "
    "procedural formulas, and biographical phrasing, not only messages."
)


def day_tagline(day: str) -> str:
    """Public day-page scope with the measured date supplied by code."""
    return f"Observed congressional language on {day}, rendered as two cited automated composites."


# R-36.4 temporal state ladder. A published reading names its state so a stale or
# degraded reading is never labeled current. site.py renders the homepage heading
# from this authority (owning surface for the state strings).
TEMPORAL_HEADINGS = {
    "today": "Today on OnScript",
    "latest_complete": "Latest complete day",
    "latest_available": "Latest available reading",
    "publication_delayed": "Publication delayed",
    "no_current_reading": "No current reading",
}
TEMPORAL_STATES = tuple(TEMPORAL_HEADINGS)


def temporal_heading(state: str) -> str:
    """Return the ruled homepage heading for a temporal state."""
    return TEMPORAL_HEADINGS.get(state, TEMPORAL_HEADINGS["latest_available"])


def service_status_note(day: str, site: str) -> str:
    """Party-blind neutral note for an R-36.5 null-service day. Carries no composite prose."""
    return (f"Service status for {day}: this reading was force-finalized on low source volume "
            f"with no eligible claims, so the party composites are held. "
            f"Methodology and status: {site}/status/.")


def publication_lag_note(measured_day: str, lag_days: int) -> str:
    """Homepage note when the shown reading trails the expected latest complete day."""
    unit = "day" if lag_days == 1 else "days"
    return (f"This reading is for {measured_day}. The latest expected complete day has not "
            f"published, so publication is {lag_days} {unit} behind.")
