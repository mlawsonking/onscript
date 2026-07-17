# 18 — THE SHARD-LANES BRIEF (Fable, 2026-07-17 — binding)

**Who runs this: Opus, in the main tree, after reading CLAUDE.md.** Build-order step (4): give the
alexandria shards lanes, make the harness lane-aware, then finish the re-validation — the eleven
BLOCKED-ON-SHARDS items Session 18 correctly refused to run on lane-blind substrate. docs/12 Laws
L1–L4, docs/17 §1–§2 (lanes, exclusions, halves), and Constitution Art. XVI govern throughout.
Fable pre-registers here; the implementing session executes and does not re-litigate.

## §0 Session start (Art. XVI)

`git pull` first (data commits land on main from the 19:30/21:30Z crons — pull-rebase before every
push, and expect a mid-session data commit). Read the streak from the RECORD (`verifier_passed`/
`fallback` in tonight's assemble log — if it ran green, say so in the buildlog; if not, file it).
`python tests/run_tests.py` — 259+ green before touching anything. `vtask list` — reuse, never
re-file.

## §1 The job, in one paragraph

`alexandria.run_shard` builds per-congress ledger/discipline/coverage shards from ALL records —
`load_congress_records` is the third and last place `date_source` dies (Session 16 finding). Add a
lane dimension: per-lane shards alongside the combined ones, lane-aware harness builders on top,
then re-run the eleven blocked S1 items on the new substrate. The combined shards and `merge()` are
UNTOUCHED — they feed the site/Archive, their schema is a compatibility promise (Art. VI), and a
pooled index for lookup is legitimate; only COMPARISONS require a lane.

## §2 Shard design (pre-registered)

- `run_shard(n, lane=None)`: `lane` in `{"propublica","scraped"}` filters RECORDS by
  `provenance.instrument_of` BEFORE `normalize` (the lane is a property of the record; normalize and
  `PhraseEngine` stay untouched). Outputs `ledger-{n}.{lane}.json`, `discipline-{n}.{lane}.json`,
  `coverage-{n}.{lane}.json`, `shard-{n}.{lane}.json`. `lane=None` = today's combined behaviour,
  byte-identical.
- Build BOTH lanes for congresses **113–119 only**. 107–112 stay combined-only, and any per-lane
  loader asked for them RAISES `LaneIsolationError` — the pre-2013 tails are 99.9% single-party
  (docs/17 §1) and a per-lane shard for them would be an invitation to a poisoned statistic.
- Disk: ~3 GB additional on X: (1.8 TB free). Resumable per (congress, lane); run the long passes
  in the background — **a foreground tool timeout is a TIMEOUT, not a crash** (canon trap, twice
  now).

## §3 Acceptance (pre-registered numerals — write results in the shard summaries)

1. **Raw partition EXACT**: for every n in 113–119, `records(propublica) + records(scraped) ==
   records(combined)`. The 19 untagged records have null dates and never enter a congress load, so
   there is no tolerance here — any mismatch is a bug.
2. **Post-normalize tolerance ±0.5%** per congress: per-lane statement counts will NOT sum exactly
   to combined, because joint-collapse merges near-identical releases ACROSS records and a joint
   pair split across lanes cannot collapse within one. Measure the delta, attribute it (count the
   cross-lane collapse pairs), and record both numbers in `shard-{n}.{lane}.json`. A delta beyond
   ±0.5% is a stop-and-diagnose, not a note.
3. **Reader spot-check**: stream 5 named ngrams via `iter_ledger_entries` from both lane shards and
   the combined shard for one congress; daily counts must satisfy propublica + scraped ≤ combined,
   with every strict inequality explained by (2).
4. Suite green (259+), plus new kill-fixtures: per-lane loader for 107–112 raises; unknown lane
   raises; `run_shard(n, lane=None)` output byte-identical to a pre-change shard for one small
   congress.

## §4 Lane-aware harness (the substrate the eleven items actually read)

Every builder gains `lane=`, and **every cache file is lane-suffixed** (`phrase_index.{lane}.jsonl`
etc.) so lanes can never share a cache: `build_phrase_index`, `build_daily_series`,
`build_cross_party_daily`, `build_member_index`, `load_discipline_index`, and
`build_statement_meta` — whose `weekday_baseline` and `active_members_by_year` become per-lane
(S1.5's era-pooled baseline normalizing a scraper-only half was a Session-16 triage finding).
`bioguide_states` MAY stay pooled — it is an identity map, not a comparison; say so in its
docstring. Migrate each BLOCKED S1 site to the lane-aware path as it is re-run (Session 18's
convention), never ahead of need.

## §5 The eleven re-validations

S1.1, S1.1′, S1.2, S1.3, S1.3′, S1.5, S1.6, S1.7, S1.8, S1.11, and S1.4-proper (give
`load_congress_records` the same `lane=` so its density-matched control runs per-lane). Halves per
docs/17 §2 — propublica 113–114 vs 115–116 (years 2013–16 vs 2017–20), scraped 117 vs 118–119
(2021–23 vs 2024–26); congress-keyed and year-keyed forms never mixed within one hypothesis. L4
floors derived from the per-lane shard substrate and written as numerals BEFORE measuring. Ledger
rows append-only with `supersedes`, estimator, and a tracked script path under `scripts/search/`.

Two lane-edge rules for the burst/lifespan family (S1.1′, S1.3, S1.3′): the propublica lane ENDS at
2021-01-03, so the right-censor guard (`censor_days`) applies at the lane edge exactly as it does at
the 2026-07-09 cutoff — a burst alive at lane-end is censored, not "died." And within one lane the
seam's false `>14d` silence cannot occur; if a within-lane series still shows a wall at an era
boundary, that is a finding, not plumbing — measure it, don't patch it.

**Rider:** S4.1 half-A per-case isolation (drop the ~5% scraped tail Session 18 surfaced; the
aggregate stays UNDERPOWERED — half B has 5 qualifying cases against a floor of 8 — and the row
should say so).

## §6 Hygiene riders (cheap, do them while the shards build)

- Re-home the untracked evidence canon cites: `scratchpad/adv_partymix_pass1-5.py`,
  `l1_substrate.py`, `l1_partymix.py`, `l1_verify_real.py` → tracked `scripts/search/evidence/`;
  the two history-rewrite tools (`extract_names.py`, `scan_all_blobs.py` — they contain no names)
  → `scripts/ops/history-rewrite/`. Update the CLAUDE.md ⚠ block's script pointers to match.
- If tonight's assemble ran green, note the streak count in the buildlog entry (from the log, not
  the run status).

## §7 Out of scope

`merge()`, the site, the Archive, the daily pipeline (provably untouched — it does not import
Search). Nomenclature wiring (branch `wip/nomenclature`) is the step after this one and gets its
own brief; rulings-shaped 1.3/1.4/1.5 wait behind it (SPAN-gated). Releases and flips are Michael's
acts only.

## §8 Session end (Art. XVI)

Full suite green · shard summaries carry the acceptance numbers · ledger rows pushed · BUILDLOG
Session entry · CLAUDE.md You-are-here + build-order line updated (step 4 → done or honestly
partial, naming what remains) · expectation-vs-observation check (site day, streak, flags) with
discrepancies FILED · pull-rebase before the final push.
