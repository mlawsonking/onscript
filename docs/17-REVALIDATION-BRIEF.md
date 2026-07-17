# 17 — THE RE-VALIDATION BRIEF (Fable, 2026-07-17 — binding)

**Who runs this: Opus, in the main tree, after reading CLAUDE.md.** This is build-order item (3):
the 34 pre-seam verdicts, re-validated within one provenance lane, under docs/12 Laws L1–L4 and
Constitution Art. XVI. Fable pre-registers here; the implementing session executes and does not
re-litigate. Michael's standing rulings (Session 13c R1–R6) apply throughout.

## §0 Session start (Art. XVI — expectation vs observation, before any work)

1. `git pull` (SHAs were rewritten 2026-07-17; if this clone predates that, RE-CLONE).
2. Read the streak from the RECORD: the assemble logs' `verifier_passed`/`fallback` (or `degraded`
   in the day manifests) for every run since 07-17 evening. Run statuses are inadmissible. File a
   discrepancy if the streak claim in CLAUDE.md doesn't match the logs.
3. `python tests/run_tests.py` — 255+ green before touching anything.
4. `vtask list` — surface open items to Michael; reuse, never re-file.

## §1 The lanes (measured 2026-07-17, Session 16 — the substrate for every floor)

| lane (instrument) | window | statements | exclusions (BINDING) |
|---|---|---|---|
| `propublica` (=`legacy`) | 2013-01-01 → 2020-12-31 | 484,125 | pre-2013 tail (1,594; 99.9% D) EXCLUDED; the 2021-01-01..03 stub (229) EXCLUDED from halves |
| `scraped` (=`scraper`+`page_html`) | 2021-01-04 → present | 174,641 | pre-2013 scraper (727; ~100% R) EXCLUDED everywhere; 2013–2020 scraped tail (25,997) = supplementary check ONLY, never pooled |

`page_html` runs FOLDED into `scraped` (same instrument — the default). Where folded-vs-strict
(`lane_of(by="source")`) moves a headline number by >0.5pt of D-share, report BOTH and flag the row
for Michael's open fold-vs-isolate ruling. Never decide it.

## §2 Pre-registered within-lane halves (the new CONFIRM splits)

- **propublica:** half A = **2013–2016** (196,681), half B = **2017–2020** (287,444).
  Congress-keyed form: **113–114 vs 115–116**. (117 is excluded: one day.)
- **scraped:** half A = **2021–2023** (67,032), half B = **2024–2026** (107,609).
  Congress-keyed form: **117 vs 118–119** (note 118 straddles the year-split; a congress-keyed
  hypothesis uses the congress form consistently, never mixed with the year form).
- **L4:** before measuring ANY hypothesis, derive its per-cell floors from these counts and write
  them as numerals in the ledger row. A floor written after the measurement is a violation.
- A CONFIRM now means: expected sign in both halves **within a lane**, `lane_a`/`lane_b` declared.
  Where both lanes are independently runnable, a both-lanes CONFIRM is the new twice-confirmed tier.

## §3 What is runnable NOW vs BLOCKED (do not discover this the hard way)

**Rebuild `text_features.jsonl` FIRST** (background it — tens of minutes; an early exit code from a
foreground tool is a TIMEOUT, not a crash): the cache predates L1, so its rows lack `ds`/`inst`.
Every S2 hypothesis reads it. Until rebuilt, every S2 re-run is lane-blind by substrate.

- **Runnable now** (direct `iter_statements(lane=...)` or rebuilt text_features): all S2 items;
  S1.4 (verbatim — ALSO fix its record-counted denominator vs member-counted numerator, which
  manufactures a rise landing on the seam); S1.10 (bipartisan season — drop the 2020 cycle via
  `assert_no_seam_span`, placebo per L3 on the same statistic); S1.9 (117-only, already lane-clean
  **by construction** — re-affirm and say so in its row); S4 items (fix `wave_s4._collect`'s
  `date_source` drop in passing — it reads the mirror directly).
- **BLOCKED-ON-SHARDS:** every S1 hypothesis that reads `phrase_index`/`daily_series`/
  `member_index`/`discipline` (S1.1, S1.1', S1.2, S1.3, S1.3', S1.5, S1.6, S1.7, S1.8, S1.11) —
  the alexandria ledger shards are lane-blind until the shard rebuild (its own session; ~3GB).
  Classify these BLOCKED in the ledger; do NOT re-run them on lane-blind substrate.
- Classify every one of the 34 as: RUNNABLE-WITHIN-LANE · NEEDS-RESCOPE (construct requires the
  cross-seam span; re-register within-lane or retire) · LANE-IMPOSSIBLE (retire, honest row) ·
  BLOCKED-ON-SHARDS. The classification table is itself a ledger artifact.

## §4 Order of execution

1. **S2.3** (what-losing-sounds-like) — the flagship reversal whose kill may be plumbing. Its own
   docstring already flags the minority signature as a "RECENT-era (2021-26) effect"; 2021–26 IS
   the scraped lane. This is the single highest-value re-validation in the program.
2. **S1.9** (self-audit) — quick re-affirm, lane-clean by construction; its CONFIRMED either
   survives with a stronger pedigree or the program's best card falls. Then **S2.9** (its ancestor
   tier for SD.2 on CREC).
3. The S2 remainder → S1.4/S1.10 rescopes → the S4 set.
4. Migrate wave call sites to `lane_a`/`lane_b`/`lane=` as each is re-run — never bulk-migrate
   code you aren't re-running (an un-migrated site fails loudly by design; that is the guard
   working, not a bug).

## §5 Ledger discipline (docs/13)

Rows are APPEND-ONLY. A re-validation appends a new row with `supersedes: <old-row>`; the old
verdict is never edited (the correction history is itself the credibility artifact). Every row
carries: lanes + halves used, floors (numerals), the estimator (units/window/denominator), and the
path of a re-runnable script (Art. XVI: an unreproducible number is prose). Only the session that
ran a measurement writes its row.

## §6 Out of scope for this session (queued after)

Alexandria shard lane-tag rebuild (unblocks the BLOCKED-ON-SHARDS set) → nomenclature wiring
(branch `wip/nomenclature`; wire `tag()` BEFORE distill; `nomenclature_rate` in the nightly audit;
adversarial review; merge) → rulings-shaped 1.3/1.4/1.5 (R2/R3/R4 — SPAN-gated, so they wait for
the nomenclature merge). Releases and flips remain Michael's acts only.

## §7 Session end (Art. XVI)

Full suite green · ledger rows pushed · BUILDLOG session entry · CLAUDE.md You-are-here updated ·
expectation-vs-observation check (site day, streak state, flags) with discrepancies FILED.
