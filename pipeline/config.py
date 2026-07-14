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

# Near-identical (delegation) collapse (§11 trap 2). Byte-identical text is caught exactly;
# near-identical delegation letters must ALSO collapse to one unit or they masquerade as
# independent coordination and the flagship chart is debunkable on day one.
NEAR_JOINT_JACCARD = 0.7          # shingle Jaccard >= this -> same coordinated document
NEAR_JOINT_MIN_TOKENS = 40        # skip short statements (unstable shingles)
NEAR_JOINT_SHINGLE_K = 8          # word-shingle size
NEAR_JOINT_WINDOW = 80            # length-sorted comparison window (bounds cost to ~O(n*w))

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
    "archive": False, "silence_board": False, "authors_vessels": False, "the_script": False,
    "awards": False, "floor": False, "duet": False, "phrase_search": False,
    "owners_brief": False, "credit_claim": False, "memo_cadence_flag": False,
    # Wave 2 (v3)
    "memory_hole": False, "off_script_alerts": False, "upstream_graph": False,
    "bill_brand": False, "public_api": False, "eval_table": False,
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


LLM_MONTHLY_CEILING_USD = 9.0   # pre-flight HARD stop (< the $10 Console cap); halts the LLM voice
LLM_MONTHLY_WARN_USD = 8.0      # ntfy warn threshold (month-to-date)
