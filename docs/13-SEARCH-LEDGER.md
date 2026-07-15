# 13-SEARCH-LEDGER — verdicts from the Search (append-only; Opus maintains)

> One row per pre-registered hypothesis in `docs/12-SEARCH-PROGRAM.md`. Every hypothesis ends in
> exactly one verdict: CONFIRMED · REFUTED · UNDERPOWERED · ARTIFACT (confound named) · BLOCKED.
> Confirmed findings get a card in `data/derived/findings/`. Numbers, not adjectives.

## Tally

| tested | confirmed | refuted | underpowered | artifact | blocked |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 0 |

## S0 data-inventory findings (S0.1 complete, 2026-07-15)

**Sources audited:**
- `raw/congress-press` — **303 monthly JSONL, 2001-01 → 2026-07** (the confirmed-complete ground
  truth). Schema `{url,title,date,member{bioguide_id,name,party,state,chamber},text}`; party spelled
  out ("Democrat"/"Republican"). **This is the Search substrate.**
- `state/ledger.json` (3 GB monolith) — recent-heavy, earliest first_seen **2011**, no 2001–2010.
  **Not a reliable 25-year source; not used as authoritative.**
- `state/alexandria/ledger-{107..119}.json` — **107–111 EMPTY**, 112 partial (49 KB), 113–119
  populated (243 MB–1 GB). Schema `ngram → {first_seen, daily{date:{D,members_D,R,members_R}},
  df_weight, peak_units}`. Populated shards are reusable; missing eras rebuildable via
  `alexandria.run_shard(n)` (but pre-2013 data is near-empty — see amendment A1).
- `state/alexandria/discipline-{n}.json` — per-party `{date:{statements,on_message_units,index}}`,
  ALL eras (coverage denominators + the density control source). `coverage-{n}.json` — per-year
  per-party statement counts, all eras.
- `statements.jsonl.gz` — congress 119 only (2025–26, ~76k). `member.leadership_role` present but
  **null throughout** → S1.12/S3-leadership need the `leadership.json` reference join, not the field.
- `data/derived/chapters/*.json` — 353 chapters; each carries `stats.top_phrases`
  `[{phrase,peak_members,peak_day,first_date,first_sayer}]` (top-N per era — a cross-check, not the
  full population).

**Load-bearing conclusion → Amendment A1 (see 12 §6):** the analyzable *symmetric* span is
**congresses 113–119 (2013–2026)**, not 2001–2026; pre-2013 is single-party/descriptive only. Split
revised to A=113–116 / B=117–119. The coverage confound is real and now sized.

**S0.3 metrics library:** built + kill-fixture-tested (`pipeline/search/metrics.py`,
`tests/test_search_metrics.py`, 9 tests — incl. the coverage-artifact refusal). rate_per_1k,
spearman, split_direction, confirms_in_both_halves, density_matched_subsample, power_ok,
symmetry_table, did, weekday_excess. **107 suite tests green.**

**S0 remaining (next session):** S0.2 streaming ledger reader + statement-metadata builder over
`raw/congress-press`; rebuild the buildable-but-thin early shards into the Search cache where a
hypothesis needs pre-2013 single-party data; S0.4 reference tables; S0.5 card schema. Then S1.

## Verdicts

| ID | Name | Verdict | Headline number | Date | Notes |
|----|------|---------|-----------------|------|-------|
| — | *(none yet)* | | | | |

## Graveyard notes

*(what died and why — published alongside what survived; the tally is itself a headline)*
