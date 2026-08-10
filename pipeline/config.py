"""Configuration constants and paths.

Thresholds come from gameplan §13 "Open knobs (defaults)". Deviating from a default
is a sanctioned §13 move ONLY if the default fails on contact with reality — record any
deviation in docs/04-BUILDLOG.md with rationale.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths. Raw + state are gitignored (destined for GitHub Release assets, §2/§7);
# derived is committed and read by the site.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
RAW = DATA / "raw"               # immutable mirror of upstream (Release asset)
STATE = DATA / "state"           # phrase ledger + first-appearance (Release asset)
DERIVED = DATA / "derived"       # small JSON the site reads (committed)
RELEASES = DATA / "releases"     # staging dir for what gets uploaded to Release assets
REFERENCE = DATA / "reference"   # roster snapshots (congress-legislators), committed

for _p in (RAW, STATE, DERIVED, RELEASES, REFERENCE):
    _p.mkdir(parents=True, exist_ok=True)

TAXONOMY_FILE = REPO_ROOT / "taxonomy_v1.json"

# ---------------------------------------------------------------------------
# Upstream sources (research §6; live-verified 2026-07-10)
# ---------------------------------------------------------------------------
CONGRESS_PRESS_RAW = "https://raw.githubusercontent.com/dwillis/congress-press/main"
CONGRESS_PRESS_API = "https://api.github.com/repos/dwillis/congress-press"
# The append-only press-release corpus. Monthly files at data/YYYY/YYYY-MM.jsonl.
CONGRESS_PRESS_MONTH_URL = CONGRESS_PRESS_RAW + "/data/{year}/{year}-{month:02d}.jsonl"

LEGISLATORS_CURRENT = (
    "https://raw.githubusercontent.com/unitedstates/congress-legislators/main/legislators-current.yaml"
)
LEGISLATORS_HISTORICAL = (
    "https://raw.githubusercontent.com/unitedstates/congress-legislators/main/legislators-historical.yaml"
)

USER_AGENT = "onscript-pipeline (+https://onscript.news)"

# The public origin, used to build ABSOLUTE urls — og:/canonical meta in the rendered site, and the
# receipts links in posted threads. Absolute is not a style choice: a link card unfurled by Bluesky
# is fetched by THEIR crawler, so every og: value has to resolve without a page context.
# (post_bluesky.py keeps its own identical SITE constant; the posting path is frozen for launch and
# is not worth a refactor tonight. Consolidate post-launch.)
SITE_URL = "https://onscript.news"
# Derived from this checkout's `origin` remote (2026-07-22). Public call sites build repository and
# rolling-release links from one authority so a future repository move cannot leave split pointers.
REPO_URL = "https://github.com/mlawsonking/onscript"
OG_IMAGE = "og.png"          # committed at site/public/og.png — 1200x630, the link-card image
OG_IMAGE_W, OG_IMAGE_H = 1200, 630
# Per-page share cards (S67-3) live under this prefix. A page's card is optional by construction:
# when the file is absent the page falls back to OG_IMAGE, so a skipped card build costs a generic
# link preview and nothing else.
OG_CARD_DIR = "cards"

# docs/39 H1. The instrument had no way to be reached: no address anywhere on the site, bot accounts
# with DMs off, and a corrections process that assumed the reader already had a GitHub account. This
# is a PLAIN CONSTANT, not a feature flag. About renders a contact line only while it is non-empty,
# so emptying the string is the whole off switch and there is no second place to look.
CONTACT_EMAIL = "hello@onscript.news"

# ---------------------------------------------------------------------------
# Backfill epoch (gameplan §1.3). Stage 1 gates the weekend; 119th Congress seated.
# ---------------------------------------------------------------------------
STAGE1_EPOCH = "2025-01-03"      # 119th Congress seated
ALEXANDRIA_EPOCH = "2001-01-01"  # full-history Stage 2 (dark week, non-blocking)

# ---------------------------------------------------------------------------
# Phrase engine knobs (§13 defaults)
# ---------------------------------------------------------------------------
NGRAM_MIN = 3
NGRAM_MAX = 6
# Boilerplate: suppress the top DF percentile of n-grams within a (congress, party)
# corpus, plus a regex list. Per-Congress so 2005's template soup != 2025's (§11.9).
BOILERPLATE_DF_TOP_PERCENTILE = 0.005        # (legacy percentile knob; superseded by share below)
BOILERPLATE_DF_MIN_DOCS = 40                 # don't DF-suppress until a stratum has volume
# A candidate phrase is template boilerplate if it appears in > this share of a
# (congress, party) stratum's statements. Memory-bounded reformulation of the §13
# "top 0.5% DF percentile" knob (the percentile-over-ALL-ngrams cannot be computed in the
# two-pass streaming engine); same goal — suppress ubiquitous template soup, keep spiky
# talking points (which concentrate on few days -> low overall share). Recorded in BUILDLOG.
BOILERPLATE_DF_SHARE_MAX = 0.05
# Ledger compaction (§13): prune n-grams with < this many total uses or only ever one
# member/unit, evaluated per era so a rare-but-real historical phrase survives.
LEDGER_MIN_TOTAL_USES = 3
# "Synchronized phrase" = used by >= this many independent units (members/joint-groups)
# by one party on one day. Feeds adoption curves + discipline index.
SYNC_MIN_MEMBERS = 3

# The Concordance (1.4 / R4) — per-member on-script index. Disclosed knobs, movable without a rebuild.
# A member is NAMED only with >= this many SOLO (non-joint) statements in the window — enough for a
# stable share and to cite, so we never reproduce R2's "318 tied-at-zero vessels" swarm. Members below
# the floor are disclosed in aggregate, never scored. (Confirm this default at the release-flip review.)
CONCORDANCE_MIN_STATEMENTS = 10
CONCORDANCE_RECEIPTS_MAX = 3   # >=3 dated citations per named member (member-naming gate, docs/11 §0.5)
# A phrase counts as "the party script" for the on-script index ONLY if it genuinely coordinated at
# scale — peak >= this many members in one day. Same #143 confound control as ORIGINATION_PEAK_FLOOR.
# Without it the index saturates: over a real 45-day window the raw kept set is ~41k phrases, so ~91% of
# members read >=0.99 on-script (every release shares SOME 3-member-co-used gram — names, agency titles,
# generic language) — a misleading Art. IV artifact. MEASURED (BUILDLOG Session 23) — floor vs the named
# members' index distribution: 0 -> mean .99 (91% saturated); 10 -> .63; 15 -> .32 (IQR .18-.43, best
# spread); 20 -> .20 (14% zero); 30 -> .04 (64% zero, 10 phrases, starved). 15 discriminates without
# starving and matches the origination floor. Movable knob; confirm at the release-flip review.
CONCORDANCE_PEAK_FLOOR = 15

# The Unison + The Void (1.5 / R2) — symmetric weekly awards. Disclosed knobs, movable without a rebuild.
# R2 killed the Ventriloquism Award (most on-script MEMBER): 318/538 members tie at zero solo count and
# naming a "vessel" is a chamber/tenure/nomenclature confound (#143) and an Article X member-shaming
# construct. It is replaced, symmetric by construction, by two PHRASE-/TOPIC-level awards.
#   THE UNISON — each party's largest single-day "office-share" phrase over a trailing window: of the
#   party offices that published a SOLO release that day, the share that used one exact phrase. The
#   numerator IS the coordination magnitude, so no separate peak floor is needed — a winning share
#   already requires many offices (share 0.7 at 40 active offices means 28 said the same thing).
UNISON_WINDOW_DAYS = 7          # the "week": trailing window (inclusive) ending at the focus day
# A (party, day) is eligible only with >= this many active SOLO offices, so a thin weekend/holiday day
# can't take the award on a 2-of-3 share. MEASURED on the real corpus (BUILDLOG Session 24, week
# 2026-07-03..09): active SOLO offices/day is bimodal — normal weekdays 40-112 (D) / 24-77 (R), median
# 47/36, versus a thin-day cluster <=17 (July 4th D=17/R=10, the 5th D=1/R=3, weekends). 20 sits in the
# gap for BOTH parties (no day lands in 18-23), so it excludes holidays without touching normal days and
# keeps the award symmetric (at floor 15 the D winner was July-4th commemoration on 17 offices while R's
# 4-of-10 July-4th day fell below the bar — an asymmetric artifact). The office-share numerator IS the
# coordination magnitude, so no phrase-peak floor is needed on top. On a high-salience day a substantive
# phrase reaches ~50%+ (2026-06-30 "born in the united states": 53/102 D = 52%); a quiet week surfaces
# generic/commemorative language, which is honest, not a defect. Movable; confirm at the release-flip review.
UNISON_MIN_ACTIVE = 20
UNISON_TOP_N = 5                # ranked office-share list per party; the #1 row IS "The Unison" award
UNISON_MEMBERS_SAMPLE = 8       # offices named on a card before "+N more" (>= SYNC_MIN are always present)
# THE VOID — the window's loudest silence, BOTH directions, rolled up from the 1.2 absence-map boards
# (data/derived/silence/*.json, built only when FEATURES["silence_board"] is wired). Degrades to
# "unavailable" when no scored board exists for the window: 1.2's law that a gap is never rendered as a
# silence carries through unchanged, so The Void never fabricates an award from missing data.
VOID_TOP_N = 3

# Near-identical (delegation) collapse (§11 trap 2). Byte-identical text is caught exactly;
# near-identical delegation letters must ALSO collapse to one unit or they masquerade as
# independent coordination and the flagship chart is debunkable on day one.
NEAR_JOINT_JACCARD = 0.7          # shingle Jaccard >= this -> same coordinated document
NEAR_JOINT_MIN_TOKENS = 40        # skip short statements (unstable shingles)
NEAR_JOINT_SHINGLE_K = 8          # word-shingle size
NEAR_JOINT_WINDOW = 80            # length-sorted comparison window (bounds cost to ~O(n*w))

# Document-family retrieval and medoid anchoring. These thresholds are PROVISIONAL pending the W10
# gold set. One set applies to both parties. Exact Jaccard makes the final decision after MinHash
# retrieves candidates.
DOCUMENT_FAMILY_JACCARD = 0.72
DOCUMENT_FAMILY_MIN_TOKENS = 24
DOCUMENT_FAMILY_SHINGLE_K = 5
DOCUMENT_FAMILY_MINHASHES = 64
DOCUMENT_FAMILY_MINHASH_BANDS = 32
DOCUMENT_FAMILY_WINDOW_HOURS = 36
DOCUMENT_FAMILY_RECALL_TARGET = 0.995

# Phrase-screening significance gates. These are provisional and frozen until the
# gold-set review validates them. They are descriptive filters, not causal tests.
SURGE_MIN_ABSOLUTE_CHANGE = 0.03
SURGE_MIN_RATIO = 2.0
SURGE_MAX_Q_VALUE = 0.05

# ---------------------------------------------------------------------------
# Nomenclature segregation (docs/16). Official names (bill titles, committee names) are not
# messages; the tagger cites an external party-blind record for every tag. A DISCLOSED KNOB, not
# a validated constant: docs/16 §8.4 measured 'transportation and infrastructure' at 0.802 — one
# thousandth above the threshold — which falsifies the "nothing lands in the dead zone" claim.
# ---------------------------------------------------------------------------
NOMENCLATURE_RATIO_MIN = 0.80             # tag iff the doc-level nomenclature ratio >= this
NOMENCLATURE_INDEX_CONGRESS_MIN = 108     # BILLSTATUS bulkdata floor (107 -> 404, verified)
NOMENCLATURE_MIN_NAME_CONTENT_TOKENS = 2  # a name thinner than this is not indexable
# Generic-subcommittee hazard (measured on the real roster): 43 of the 181 current subcommittee
# names are < 3 tokens and 65 are < 3 CONTENT tokens ('Defense', 'Readiness', 'Aviation'). Indexed
# bare they would tag ordinary English, so they enter ONLY qualified ('subcommittee on aviation').
COMMITTEE_UNQUALIFIED_MIN_TOKENS = 3

# Cadence / quiet-day (§6.2 P3, §13)
QUIET_DAY_MAX_STATEMENTS = 15                # < this many new Lane-1 statements -> quiet line

# Bluesky (Lane 2) poll depth (§13)
BLUESKY_POLL_HOURS = 48

# ---------------------------------------------------------------------------
# Parties. The two composite accounts are D and R. Independents are kept as their own
# bucket: they enter the ledger but are NOT folded into either composite in v1
# (caucus-aware bucketing is a v2 refinement — logged in BUILDLOG). Comparative
# metrics are computed for D and R only.
# ---------------------------------------------------------------------------
COMPOSITE_PARTIES = ("D", "R")
ALL_PARTIES = ("D", "R", "I")

PARTY_NORMALIZE = {
    "d": "D", "democrat": "D", "democratic": "D", "democrat party": "D",
    "r": "R", "republican": "R", "gop": "R",
    "i": "I", "independent": "I", "id": "I", "il": "I",
}

CHAMBER_NORMALIZE = {
    "house": "house", "h": "house", "rep": "house", "representative": "house",
    "senate": "senate", "s": "senate", "sen": "senate", "senator": "senate",
}

# Lane assignment is by SOURCE, never by content (§5.1, machine-enforced).
LANE_BY_SOURCE = {"press_release": 1, "bluesky": 2, "floor": 2}
COPYRIGHT_BY_SOURCE = {"press_release": "usc105", "bluesky": "fair_use", "floor": "usc105"}

TIMEZONE = "America/New_York"    # product day = prior NY calendar day (§2)

# Env-overridable (Actions sets these; safe defaults for local dev)
def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# ---------------------------------------------------------------------------
# Release-switch architecture (docs/11-BUILD-PROGRAM.md §1). "Build dark, release by gate":
# every backlog feature builds its artifacts and lands verified, but does NOT render/link
# publicly until its flag flips True in a commit — that flip is the release act (dated, public,
# diffable; Constitution VIII spirit). Keys mirror the Build-Program queue. All False = dark.
# ---------------------------------------------------------------------------
FEATURES = {
    # Wave 1 (v2)
    # `concordance` is the 1.4 slot (docs/11 §1.4 "The Script"), which R4 (docs/21 §3.2) redefined to
    # THE CONCORDANCE — the per-member on-script index (denominators on every line, no predictive claim,
    # SPAN-gated). The old `the_script` (reconstructed-memo) key was unused; renamed here to match R4.
    "archive": False, "silence_board": False, "authors_vessels": False, "concordance": False,
    "awards": False, "floor": False, "duet": False, "phrase_search": True,
    "owners_brief": True, "credit_claim": False, "memo_cadence_flag": False,
    # Wave 2 (v3)
    "memory_hole": False, "off_script_alerts": False, "upstream_graph": False,
    "bill_brand": False, "public_api": False, "eval_table": False,
    # Cross-cutting instrument fix (docs/16, wired per docs/19) — prerequisite for
    # authors_vessels/awards/concordance and for ANY coordination headline claim. Tags only; wiring
    # tag->suppress is forbidden (§7). Name is `nomenclature_tags` (plural) per the docs/19 wiring
    # brief §2/§7 and CLAUDE.md; gates SITE display-time + daily pre-distill annotation. The MEASURE
    # wiring (nomenclature_rate in the nightly audit) is unconditional and does NOT read this flag.
    "nomenclature_tags": False,
    # R3 / #146 — per-party side-by-side columns for the day table (each party its own top-k with
    # N-of-caucus), fixing the pooled rank-and-truncate that makes the flagship 88% D. Data
    # (sync_by_party) is built every day; this gates only the RENDER, so the flip is a pure release act.
    "party_columns": True,
    # Serves the sealed gold-set annotation packet at an unlisted path so the rater can work the
    # pass from any device. docs/35 §10.6 publishes the bundle openly in any case and the packet
    # already clears the publication privacy floor, so this is a convenience flag, not a
    # disclosure decision. Unlisted means absent from the nav, absent from the sitemap,
    # disallowed in robots.txt, and noindex in the page itself. It does NOT mean private: the
    # path is derived in committed code, so anyone reading this public repository can compute it.
    # Off by default, and meant to be turned off again when the pass is finished.
    "annotation_packet": False,
}


def feature_on(name: str) -> bool:
    """True iff the named dark feature has been released (its FEATURES flag flipped)."""
    return bool(FEATURES.get(name, False))


# ---------------------------------------------------------------------------
# POSTING_ENABLED — the S3 launch switch (gameplan §9). A GitHub Actions repo VARIABLE
# (not a commit, not a secret): Michael flips it in the UI at launch. Default OFF (dark).
# When off, the Bluesky posting leg is a deterministic dry-run print — NO path posts,
# regardless of whether the app-password secrets are present (kill-tested). This is what
# turns the first-ever brand post from a cron accident into a deliberate act.
# ---------------------------------------------------------------------------
def posting_enabled() -> bool:
    return env("POSTING_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# LLM_VOICE_ENABLED — the billing switch for the real Sonnet Daily-Line voice. Same pattern as
# POSTING_ENABLED: a GitHub Actions repo VARIABLE, default OFF. When off, the daily voice is the
# deterministic template ($0), EVEN IF ANTHROPIC_API_KEY is present — so wiring the voice can be
# committed dark and bills nothing until Michael flips this. Flipping it off instantly reverts to
# $0. The hard ceiling below is the code-side budget backstop (the $10 Console cap is the last line).
# ---------------------------------------------------------------------------
def llm_voice_enabled() -> bool:
    return env("LLM_VOICE_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# NULL_SERVICE (R-36.5). The four-condition no-post rule. When a day is force-finalized
# AND its volume is anomalously low AND both parties have zero eligible claims AND the
# instrument status is red, the party accounts do not post the near-empty composites; the
# day page and the status incident still publish, and one neutral service-status note may
# post instead. The four conditions are named here so the rule is frozen, not inferred.
# These are rule names, not tunable measurement thresholds, so they are not part of the
# instrument fingerprint (instrument_fingerprint.LIVE_THRESHOLD_NAMES).
# ---------------------------------------------------------------------------
NULL_SERVICE_RULE = "R-36.5"
NULL_SERVICE_CONDITIONS = (
    "force_finalized",
    "anomalously_low_volume",
    "zero_eligible_claims_both_parties",
    "red_instrument_status",
)
# Lane-1 daily volume below this share of the trailing-14-day median is anomalously low.
NULL_SERVICE_VOLUME_RATIO = 0.4


def null_service_note_enabled() -> bool:
    """Deployment gate for the one neutral service-status note. Dark by default.

    The note has no dedicated account yet, so the decision (no party posts) is validated
    while the note itself stays dark, mirroring POSTING_ENABLED.
    """
    return env("NULL_SERVICE_NOTE_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


LLM_MONTHLY_CEILING_USD = 9.0   # pre-flight HARD stop (< the $10 Console cap); halts the LLM voice
SHADOW_FALLBACK_RATE_CEILING = 0.05  # frozen prompt-activation ceiling, fallback party-days / offered party-days
LLM_MONTHLY_WARN_USD = 8.0      # ntfy warn threshold (month-to-date)
