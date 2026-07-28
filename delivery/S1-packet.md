# OnScript long-session build tranche delivery packet (Opus, Session 53)

## Headline for the orchestrating session

- **E1 (isolated-substrate S1 re-run): isolation changes NO S1 verdict.** `legacy` reproduces the
  Session-19 propublica column byte-for-byte (the two CONFIRMEDs, S1.1'/S1.3', preserved); `scraper`
  matches Session-19 scraped on 10 of 11; the one move (S1.3' ARTIFACT to REFUTED) is a normalize-version
  rebuild artifact, not page_html isolation, and it creates or destroys no CONFIRMED. `page_html`
  standalone is UNDERPOWERED for all eleven. Zero verdicts flipped toward a false positive.
- **E2 (silence_board wiring, task #198): wired dark.** `silence.build_day_board` now runs in the daily
  deterministic leg (build dark, skip-and-log, Lane-1 only, GDELT held to a Lane-2 salience gate), so
  boards accumulate under `data/derived/silence/` while the surface stays gated off. The archive surface
  was already wired dark and needed no change.
- **E3 (Alexandria Stage 2 dry prep): inputs verified READY, runbook written.** No GPU job started.
- **Branch:** `opus/s1-tranche` from `6c9b0bd` (never merged to main, never pushed to main). Integration
  is the orchestrating session's call.

**Decisions the orchestrating session / Fable carries back.**
1. The R-S50.1 isolated substrate mixes normalize instruments: `legacy` is a byte copy of the OLD
   (2026-07-17) propublica shards, while `scraper`/`page_html` were built fresh (2026-07-27) on the NEW
   normalize (post-W7/X9 document-family collapse). Within-lane E1 verdicts are each valid, but a direct
   isolated-vs-folded scraper comparison is instrument-confounded (this is what moved S1.3'). A clean
   same-instrument page_html decomposition would rebuild `scraped` via `run_shard(lane="scraped")`; it is
   unnecessary because page_html provably contributes 0 coordination phrases. Flagged, not self-authorized.
2. E2 is wired; the flip (`FEATURES["silence_board"]`) remains Michael's, gated on boards accumulating in
   production by the 08-03 digest (docs/27).
3. E3's embed/tag GPU scripts are specified in docs/34 but not committed (torch stack, untestable without
   the GPU). Starting the run is Michael's machine time and his call.

## Delivery state

- Repository: `github.com/mlawsonking/onscript`
- Working branch: `opus/s1-tranche` (base `origin/main` = `6c9b0bd`, unchanged for the session)
- Commits (in order): `f0c96e9` E1 freeze, `faebf7f` s1_4_proper power-gate fix, `a4a6612` E1 measurement,
  `782bac5` E2 silence wiring, plus this E3 commit (see `git log opus/s1-tranche`)
- Baseline validation: **653 passed, 0 failed** (at `6c9b0bd`)
- Final validation: **667 passed, 0 failed** (+9 E1 fixtures, +5 E2 fixtures)
- Test runner / interpreter: `C:\ProgramData\miniconda3\python.exe tests/run_tests.py` (bare `python` is a
  0-byte stub)
- Pushes of main, deployments, workflow dispatches, posts, feature/flag/`POSTING_ENABLED` changes,
  GPU jobs: **none**
- `site/public` changes: **none.** `data/derived` changes: ONLY the E1 evidence
  (`revalidate_s1_isolated.json` + the per-lane cache summaries). No daily-pipeline regeneration.
- Cost: $0, deterministic compute, zero Anthropic calls.
- CRLF throughout (`core.autocrlf=true`); no em dash (U+2014) in any authored line (diff-scanned).
- Discipline: `git add` was always explicit (never `-A`); AGENTS.md and tests/_tmp_watchdog/ stayed
  untracked; origin/main collision-checked before every edit.

## E1. The eleven S1 hypotheses on the R-S50.1 isolated substrate (docs/18 section 4)

Freeze-before-measure: registration + machinery committed (`f0c96e9`) before any measurement; predictions
in `data/reference/search/e1-isolated-registration.json`. The alexandria loader and harness were already
isolated-lane capable and tested at Session 51; the only new code is the additive `wave_s1` lane maps
(legacy/scraper/page_html) and the reader's cutoffs, plus the reader
`scripts/search/revalidate_s1_isolated.py` (reusing `revalidate_s1_shards.run_lane`, the same estimator).
Evidence: `data/derived/search/revalidate_s1_isolated.json`; full analysis in docs/13 "E1" section.

| ID | legacy | vs propublica | scraper | vs scraped | page_html |
|----|--------|---------------|---------|------------|-----------|
| S1.1  | ARTIFACT | same | ARTIFACT | same | UNDERPOWERED |
| S1.3  | ARTIFACT | same | ARTIFACT | same | UNDERPOWERED |
| S1.1' | CONFIRMED | same | ARTIFACT | same | UNDERPOWERED |
| S1.3' | CONFIRMED | same | REFUTED | ARTIFACT -> REFUTED | UNDERPOWERED |
| S1.2  | REFUTED | same | REFUTED | same | UNDERPOWERED |
| S1.5  | REFUTED | same | REFUTED | same | UNDERPOWERED |
| S1.6  | REFUTED | same | UNDERPOWERED | same | UNDERPOWERED |
| S1.7  | REFUTED | same | REFUTED | same | UNDERPOWERED |
| S1.8  | REFUTED | same | REFUTED | same | UNDERPOWERED |
| S1.11 | REFUTED | same | REFUTED | same | UNDERPOWERED |
| S1.4  | UNDERPOWERED | same | UNDERPOWERED | same | UNDERPOWERED |

- **legacy == propublica, exact** (SHA256-identical shards; S1.1' ratio 11.33, S1.3' drop 0.373, series
  identical). The pre-seam isolation is a verified no-op.
- **The single S1.3' move is not page_html.** The Session-51 scraper shards use the newer W7/X9 collapse
  (c117 ledger 164,179 to 121,417) the Session-19 scraped shards predate; page_html's standalone ledger is
  1 ngram/congress and its peak>=15 member index is empty, so it contributes zero coordination phrases.
  Both S1.3' verdicts are non-findings (density fails, drop negative). Proof of the instrument gap: the OLD
  combined shard and the Session-19 scraped shard have identical ledgers (c118 239,812; c119 461,198); the
  Session-51 scraper shard does not.
- **page_html standalone: UNDERPOWERED x11** (3 phrase rows, 0 member rows), the accurate cost of full
  isolation and the reason R-S50.1 isolates it rather than analysing it.

Fix landed in passing (`faebf7f`): `s1_4_proper` OOMed at congress scale (the post-Session-19
document-family clustering on the full-corpus normalize). Its congress-split gate is structurally
unmeetable in any single lane (verdict UNDERPOWERED regardless), so the power check now precedes the
normalize. Verdict-preserving; lane=None unaffected; no test depends on the discarded fields.

## E2. silence_board wiring (task #198, docs/27, due Aug 3)

The silence module, its render (`site.silence_board_body`, gated at `site.py:3214`), and its guards were
already built and tested; docs/27 named the gap ("module exists; no caller"). `deterministic.run` now calls
`silence.build_day_board(focus_day, lane1_day)` right before `build_awards` (so The Void is live-fed),
unconditionally (build dark / release by gate) inside the skip-and-log streak belt. Two lane boundaries are
enforced and tested (Article III): the per-party corpus counts are Lane-1 only, and the GDELT news baseline
stays Lane 2, gating topic salience only (a missing baseline writes an UNSCORED board). +5 tests
(`tests/test_silence_wiring.py`, on a synthetic state/derived tree). Archive surface confirmed already
wired dark (render gated at `site.py:3195`, ships off), no change needed. You wire; Michael flips.

## E3. Alexandria Stage 2 embedding-layer dry prep

Stage 2's deterministic pass is complete (Session 3); the remaining piece is the optional 4080 layer (local
all-MiniLM-L6-v2 embeddings + a local topic-tagger for Archive exhibits, dark until released). No embedding
code exists, so E3 verified the inputs and wrote the runbook, no GPU job.

`scripts/deep/alexandria_stage2_verify.py` (new, CPU-only, $0, rerunnable) reports READY: press mirror
688,820 records across 107-119, delta 0 against every alexandria shard's `records`, 684,853 embeddable units
(lane split legacy 485,948 / scraper 200,033 / page_html 2,839); CREC E-lane 152,187 statements (2001-2026)
with all 13 ledgers present, the pre-2013 spine (107-112 carry ~83,671 CREC vs ~2,389 in press). About
837,040 vectors. `docs/34-ALEXANDRIA-STAGE2-EMBEDDING-RUNBOOK.md` (new) operationalizes docs/03 section 1.4:
precondition gate, the input lane contract, the embedding and topic-tag passes, storage math, and
non-interference. The GPU embed/tag scripts are specified but not committed (torch stack, untestable here).

## Deviations, blockers, and carried work

- **Deviation (fix during measurement):** the `s1_4_proper` OOM was a post-Session-19 regression, not an E1
  bug. Fixed verdict-preservingly and committed separately (`faebf7f`), disclosed above and in docs/04.
- **Finding (flagged, not self-authorized):** the R-S50.1 isolated substrate mixes normalize instruments
  (legacy old copy, scraper/page_html fresh). Recorded in docs/13 "E1" for Fable / the orchestrating
  session; the clean same-instrument page_html decomposition is available (`run_shard(lane="scraped")`) but
  unnecessary given page_html contributes 0 coordination phrases.
- **Carried (Michael):** the `silence_board` flip (after boards accumulate in production); the 4080 GPU run
  and the two embed/tag scripts docs/34 specifies.
- **Out of scope (untouched):** any prompt/threshold/schema/flag change; any publication, posting, dispatch,
  or recurring cost; the X order; the daily pipeline (provably untouched, it does not import Search or
  alexandria).

## Files created or modified

Created: `scripts/search/revalidate_s1_isolated.py`, `data/reference/search/e1-isolated-registration.json`,
`tests/test_search_isolated_lanes.py`, `data/derived/search/revalidate_s1_isolated.json` (+ per-lane cache
summaries), `tests/test_silence_wiring.py`, `scripts/deep/alexandria_stage2_verify.py`,
`docs/34-ALEXANDRIA-STAGE2-EMBEDDING-RUNBOOK.md`, `delivery/S1-packet.md`.
Modified: `pipeline/search/wave_s1.py`, `scripts/search/revalidate_s1_shards.py`,
`pipeline/deterministic.py`, `docs/13-SEARCH-LEDGER.md`, `docs/04-BUILDLOG.md`, `docs/26-SESSION-HISTORY.md`.
