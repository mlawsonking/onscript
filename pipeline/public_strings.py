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

# docs/39 M3, Constitution Article XVII. The homepage note used to say the composite phrasing was
# "a placeholder until the live model voice is wired in" while the same page showed the other
# party's line generated and verified by the model. The instrument may not misdescribe itself.
HOMEPAGE_HONESTY_NOTE = (
    "Honesty note: when a day's verified claims cannot support a model-written composite, that "
    "party's line is composed deterministically from the day's measured statistics. The numbers, "
    "quotes, and receipts are always real and verified; only the connective phrasing differs. "
    "Each line states its own generator, so the two parties can legitimately differ on the same day."
)

# docs/39 M2. The methodology described Lane 2 in the present tense while the corpus is entirely
# Lane 1. That is the good outcome for symmetry and it deserves saying plainly.
LANE_TWO_POPULATION_NOTE = (
    "Lane 2 is not currently populated: every citation on this site today is Lane 1, a press "
    "release from an official office."
)

# docs/39 §6, S67-1. THE FRONT DOOR. Everything else on the homepage assumes the reader already
# knows what this is; a stranger arriving from a shared link got a temporal-state banner and a
# participation table before any sentence told them what they were looking at. Plain words on
# purpose: no lane, no unit key, no composite, no denominator.
FRONT_DOOR = (
    "OnScript reads what members of Congress publish and counts the phrases they say together. "
    "Every claim below links to the press releases it came from."
)

# S67-1. The method blocks that used to sit above the composites now sit inside collapsed
# disclosures. Each summary says, in reader words, what opening it will show.
DISCLOSURE_PARTICIPATION = "How this is counted"
DISCLOSURE_CLASS_LANES = "How phrases are sorted"

# S67-1. Member counts and publication counts are different bases and sit next to each other on the
# day page. Saying so once, where they touch, is cheaper than a reader inferring that one is wrong.
DENOMINATOR_BASES_NOTE = (
    "These two bases differ. Office counts come from the day's eligible caucus offices in the "
    "nightly symmetry audit; publication counts come from the day's source publications. A joint "
    "release is one publication and can carry several offices, so the two never have to agree."
)

# S67-2b. The homepage exemplar charts pick themselves, and the rule is printed under them so a
# reader can check the pick rather than trust it. The office floor is interpolated from its owning
# constant at render time; this string carries the shape of the rule, never the number.
ADOPTION_SELECTION_RULE = (
    "How these two were chosen: for each party independently, code takes that party's phrase with "
    "the highest single-day office count in the trailing {window} days, counting only phrases that "
    "reached at least {floor} offices on some day in that window. Ties go to the earlier first "
    "appearance, then to the alphabetically first identifier. No model chooses, and neither party's "
    "pick constrains the other's."
)
ADOPTION_EMPTY_PANEL = (
    "No phrase reached the coordination floor in this window. The panel is left empty rather than "
    "lowering the bar to fill it."
)

# S67-4d. Vercel Web Analytics, enabled 2026-08-09. One same-origin script served by the host.
ANALYTICS_DISCLOSURE = (
    "Visit counting: the host counts page views in aggregate and without cookies. No identifier is "
    "set, nothing follows a reader to another site, and no data is sold or shared."
)

# S67-6. Velocity is a ranked column on the phrases index with no definition anywhere on the site.
# The wording follows pipeline/build._velocity's docstring, which owns the calculation.
VELOCITY_DEFINITION = (
    "Velocity is the day's office count for a phrase divided by the average of its office counts "
    "over the previous 14 days it appeared. A phrase used as much as usual sits near 1."
)

# S67-6. Repeated-phrase tables are per-party against each caucus's own denominator, so a reader
# comparing raw row counts across the two tables is reading caucus size, not coordination.
PARTY_IMBALANCE_NOTE = (
    "Each table is one party measured against that party's own caucus, so row counts are not "
    "comparable across the two. Differences in how much each party publishes are measured in the "
    "nightly symmetry audit, not here."
)

# S67-6. The measured identity is the normalized key ("1 8 billion"); the surface form is one real
# spelling from the sources, shown so the key reads as measurement output rather than a typo.
SURFACE_FORM_LABEL = "As published"
SURFACE_FORM_NOTE = (
    "The measured identity is the normalized key above. This is one spelling of it as it appeared "
    "in the sources, chosen by frequency."
)

# S67-7a. The standing labels an essay carries, from the docs/20 publication gates and the finding
# cards that already use these exact keys. The renderer shows the label with its meaning, so a
# reader meets the caveat rather than a tag they have to decode.
ESSAY_LABELS = {
    "correlation-not-cause": "A measured association. No causal claim is made.",
    "replication": "A re-run of an earlier finding on a different instrument or window.",
    "matched-controls": "Compared groups were matched before measuring.",
    "symmetric-instrument": "Both parties passed through the same pipeline and thresholds.",
    "party-asymmetric": "The result differs by party. The method that produced it does not.",
    "descriptive": "A description of the corpus, not a test of a hypothesis.",
    "pre-registered": "The direction was recorded before the measurement ran.",
}

ESSAY_STANDING_NOTE = (
    "Every number in this piece comes from the published record and can be recomputed from the "
    "sources it cites."
)

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
