# 09: External candidate evaluation against the actual build

External design review (metric candidates + killed ideas + constraints) evaluated against this
codebase, 2026-07-12 (Session 3), grounded in file-cited inventory. **Verdict: the review was
written blind to a build that independently arrived at most of its Tier-1 conclusions and
pre-emptively killed its own KILLED list.** 7 of 9 candidates are already-covered / conflicts /
reject. Its value is three sharpenings, below.

## Verdict table

| # | candidate | verdict | why (grounded) |
|---|-----------|---------|----------------|
| 1 | Credit-claim audit (touts vs roll-call vote) | **adopt-later (v2)** | Genuinely absent, no roll-call join in `pipeline/`. Already on the menu as Whip-Count Proxy ([08](08-ANALYSIS-MENU.md)). Rides on a congress.gov vote corpus + the URL back-join. |
| 2 | Cited-statistic audit (numbers vs BLS/CBO) | **conflicts → reject** | The build deliberately does NOT adjudicate truth, `verify.py:37-41` whitelists numbers as verbatim copies of code-computed STATS, never checks if they're *right*. Fact-checking = the PolitiFact attack surface the review itself kills in #9. |
| 3 | Language provenance (origination vs echo) | **already-covered** | This IS the core source: first-appearance ledger (`phrases.py:129`), adoption curves (`build.py:18`), the in-flight Authors-vs-Vessels. |
| 4 | Falsifiability ratio by claim type | **reject** | Needs a per-statement claim-type classifier the build has no basis for; subjective taxonomy + high extraction error violates precision-over-recall; per-member → #8 hazard. |
| 5 | Silence map (rule-generated event list) | **adopt-later (v2)** | Already S3 Silence Detector (v2, pending GDELT). The reviewer's *ex-ante rule-generated event list* is a real sharpening, more defensible than news-volume-diff alone. |
| 6 | Consistency/contradiction scoring (public) | **already-covered** | Already killed as a public score; preserved only as human-reviewed, ship-late H7 Position-Drift (reports change, never motive). |
| 7 | Prediction scoring / Brier leaderboards | **already-covered** | Absent by design. The only forecasting is phrase-breakout backtest ([08](08-ANALYSIS-MENU.md) #8), not member forecasting, the "rewards silence" critique doesn't apply. |
| 8 | Per-member behavioral/predictive models, published | **conflicts** | The review says never-publish; the build intends to publish per-member origination (Authors-vs-Vessels) + H3 Drift. Open method + public corpus = rebuildable as targeting infra. **The strongest point; the build under-weights it.** See conflicts. |
| 9 | Composite scores / letter grades / credit-bureau | **already-covered** | Explicitly killed: no composite member score, no colors (only D/R), neutral headers, raw counts + distributions. Constitution Art. VII + deadpan rule. |

## Reciprocal audit, the build's own metrics vs the two screens

- **On-script member leaderboard (naive S4)**, FAILS Goodhart: saturates ~99.7% ("used *any* synced phrase" is ~universal), can't rank; cheapest "improvement" is silence. Self-caught + discarded this session, but **must be formally retired** in the vision (S4 as-specified, `01-VISION.md`).
- **Authors-vs-Vessels (in-flight)**, FAILS three-variable 3(b): a public open-method per-member origination score's cheapest adversarial use is a **targeting list** ("these members are movable vessels"). Neutral thresholds + both-party lists fix *naming/symmetry* but not *rebuild-as-targeting*. Also inherits day-granularity-before-2025 (precedence can misattribute).
- **Phrase velocity (peak/14-day-mean, `build.py:18`)**, partial Goodhart gap: the cheapest evasion is **staggering a memo across offices over several days** to suppress the ratio, currently *silent*, not surfaced. Per trap-rule, cadence-smoothing is itself a finding.
- **Per-party per-day discipline index (`phrases.py:196`)**, PASSES both. Per-PARTY not per-member, bounded 0-1 with denominator shown, no color/verdict. (The review conflates it with a member score; it isn't one.)
- **Daily Line + digit-whitelist verifier (`verify.py`)**, PASSES both. Numbers only from STATS, quotes verbatim, quorum ≥3 units (joint=1), failure → accurate fallback never silence.

## Conflicts (which should win)

1. **Cited-statistic fact-checking (#2) vs Article I (compression, not verdict).** *Codebase wins.* Adjudicating a statistic's truth turns a symmetric instrument into a truth-arbiter, the exact PolitiFact surface #9 kills. Defensible middle: flag *divergence* from a primary source without asserting who's right, research-corpus only, neutrality-gated, never a public verdict.
2. **Published per-member scores (build intends) vs #8 (never publish).** *Reviewer wins, partially, tighten, don't proceed as-is.* Resolution: ship origination as **raw per-member first-sayer/echo COUNTS with receipts** (a one-click-verifiable ledger fact = the legitimate Individuality family), and **refuse the composite "Vessel Score"** that compresses them into a target. Keep H3 Drift research-only until its backtest clears.

## Accepted additions to the feature list

| add | tier | rides on |
|-----|------|----------|
| **Published precision/recall eval table** on a frozen hand-labeled holdout | **now** | extraction/cluster is a classifier with an error rate the symmetry audit doesn't measure; renders on the methodology page. Pure protection, closes the "deterministic verification of AI-extracted claims" honesty gap. |
| **Live corrections/dispute ledger surface** | **now** | Constitution mandates corrections-as-posts; methodology page *promises* it "ships with v2" (future tense). Pull forward, corrections-rate-as-statistic is free neutrality protection from a `corrections.json`. |
| **Rule-generated ex-ante event list** for the Silence Detector | v2 | S3/GDELT + floor-voted bills + in-district FEMA declarations + member indictments. Makes "said nothing about X" a fact about X's rule-set membership, not an editor's pick. |
| **Memo-cadence evasion flag** (4th burst archetype: STAGGERED/SMOOTHED) | v2 | adoption-curve daily counts + the Memo Detector taxonomy ([08](08-ANALYSIS-MENU.md) #1). Turns the velocity blind spot into signal. |
| **Credit-claim ledger**, touts joined to roll-call votes, RAW (two receipts, no score) | v2 | congress.gov roll-calls + URL back-join + bill-reference extractor; same neutrality gate as all member-naming. |

## Bottom line

- (1) The review confirmed the #8 critique. Two member-ranking attempts, on-script rate and naive
   origination, both collapsed under confounds. Publish raw member counts with receipts and do not
   create a composite score.
- (2) Two promised constraint items remain inexpensive: the precision/recall evaluation table and the
   live corrections ledger.
- (3) A rule-generated silence event list would strengthen the neutrality controls for the feature with
   the highest legal risk.

Reject cited-statistic fact-checking because it would put the project in the role of deciding what is
true.
