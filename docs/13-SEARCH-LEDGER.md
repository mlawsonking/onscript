# 13-SEARCH-LEDGER — verdicts from the Search (append-only; Opus maintains)

> One row per pre-registered hypothesis in `docs/12-SEARCH-PROGRAM.md`. Every hypothesis ends in
> exactly one verdict: CONFIRMED · REFUTED · UNDERPOWERED · ARTIFACT (confound named) · BLOCKED.
> Confirmed findings get a card in `data/derived/findings/`. Numbers, not adjectives.

## Tally

| tested | confirmed | refuted | underpowered | artifact | blocked |
|---|---|---|---|---|---|
| 5 | 0 | 3 | 0 | 2 | 0 |

*(S1.4 measured on a proxy only → not counted as a verdict; proper metric queued. See notes.)*

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
| S1.1 | Industrialization of the Memo | **ARTIFACT** | year1 median 60 vs year2 median 3 (20× sawtooth); by-Congress 60,60,60,15,27,60,60 | 2026-07-15 | Congress-boundary/cap/recurrence confound (amendment A2). `first_seen→peak` ill-posed on per-Congress shards. Redefine as event-detection on a merged cross-era series → **S1.1′ deferred.** Guard added so it can't re-emit CONFIRMED. |
| S1.3 | Phrase Lifespan Collapse | **ARTIFACT** | same odd/even sawtooth (665 vs 106…); shard-edge right-censoring | 2026-07-15 | Same A2 confound + `last_date` censored at the Congress boundary. Redefine with survival/censoring on the merged series → **S1.3′ deferred.** |
| S1.2 | The Sync Ceiling | **REFUTED** | normalized ceiling: 2013 .23 → **2017 .35 (peak)** → 2026 .17; dir_A +1, dir_B −1, ratio 0.73 | 2026-07-15 | Not a monotone rise — synchronization **peaked ~2017 and declined.** Reversal candidate (needs its own pre-registration to publish "peaked-and-fell"). Boundary-safe (single-day peaks), coverage-normalized by active members. |
| S1.5 | The Weekend Memo | **REFUTED** | Saturday excess 0.74–0.89 (avoided) but **Sunday 4.4–6.4× over-represented** | 2026-07-15 | Ignitions don't avoid weekends — they *avoid Saturday but love Sunday*. Opposite of the folk theory. The Sunday spike needs a small-baseline artifact check before it becomes its own finding (Sunday is a tiny share of the baseline). |
| S1.7 | The August Effect | **REFUTED** | Aug ignition rate = **45–49% of session rate**, both halves | 2026-07-15 | Coordination does NOT persist through recess (<70% gate) — it roughly **halves in August**, consistently across both halves. Clean, both-half-agreeing null (a publishable finding in the un-predicted direction). Recess proxy = August, disclosed. |
| S1.4 | The Copy-Paste Caucus | *(no verdict — proxy only)* | group-rate rose 19.7→30.1/1k (ratio 1.53, both halves +1) BUT tracks corpus volume (116=41.6@160k stmts, 117=14.2@37k) | 2026-07-15 | **Group-count/statements is DENSITY-SENSITIVE** — a denser corpus yields more near-dup matches regardless of behavior (the kill-fixture concern the protocol flagged). Proper metric = statements-in-groups share + a density-controlled detector + per-party split. **Queued, no verdict rendered.** |

## Graveyard notes

- **S1.1 / S1.3 (2026-07-15):** the two flagship genealogy metrics returned a naive CONFIRMED that was
  a **congress-boundary artifact** — the machine's own adversarial pass (§4.5) + structural guard
  caught it before it became a false "the memo industrialized" headline. This is the discipline paying
  off on day one: *the first thing the sweep did was reject its own most-wanted result.* Both are
  redefinable (event-detection on a merged substrate, S1.1′/S1.3′) — not dead, deferred. The lesson
  (per-Congress shards can't answer within-phrase-genealogy questions) reshaped the S1 sequencing.
- **S1.2 / S1.5 / S1.7 (2026-07-15):** three trend-guesses refuted — but *into* real findings, not
  emptiness: message synchronization **peaked ~2017 and fell** (not ever-rising); ignitions **avoid
  Saturday but spike 6× on Sunday** (not weekend-avoidant); coordination **halves in the August
  recess** (not persistent). Each is a "reversal candidate" — publishable in its own right once
  pre-registered in the un-guessed direction (can't claim the reverse after seeing data). The
  graveyard is filling with *inversions*, which is exactly the Freakonomics genre the Appendix wanted.
- **S1.4 (2026-07-15):** the leading CONFIRM candidate (copy-paste rising 1.5×) failed the adversarial
  look — the group-rate is **density-confounded** (tracks corpus volume). No verdict rendered; proper
  metric queued. Second time this session the discipline refused a promising-but-artifactual signal.

## Running note (after 5 verdicts)
Zero CONFIRMED so far, and that is the *correct, honest* state — the ambitious trend-guesses are
refuting or artifacting, and the machine has refused every false positive it was handed (S1.1, S1.3,
S1.4). The structural hypotheses most likely to CONFIRM — **S1.11 Delegation Echo, S1.12 Leadership
Ignites, S1.9 2022 Self-Audit** — need member-level data (first-sayer bioguide + peak-day member sets,
dropped from the compact index) and the leadership roster; those are the next build + the best shot at
the first confirmed finding. Reversal candidates (S1.2/S1.5/S1.7) are a parallel content stream.
