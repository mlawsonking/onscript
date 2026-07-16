# 13-SEARCH-LEDGER — verdicts from the Search (append-only; Opus maintains)

> One row per pre-registered hypothesis in `docs/12-SEARCH-PROGRAM.md`. Every hypothesis ends in
> exactly one verdict: CONFIRMED · REFUTED · UNDERPOWERED · ARTIFACT (confound named) · BLOCKED.
> Confirmed findings get a card in `data/derived/findings/`. Numbers, not adjectives.

## Tally

| tested | confirmed | refuted | underpowered | artifact | blocked | descriptive |
|---|---|---|---|---|---|---|
| 26 | **2** | 16 | 0 | 4 | 0 | 4 |

**Second CONFIRMED: S2.9 (The Boogeyman) — the out-party names the sitting president ~2× more, 14/14
years, both halves, self-verified (Opus re-ran it, not on the subagent's word).** Finding pipeline is
now populated: 8 drip-ready cards in `data/derived/findings/` (2 confirmed + 6 reversal/descriptive).

**Wave S1 complete** (1 CONFIRMED — S1.9; + 2 redefinitions; S1.12 blocked). **Wave S2 7/12 run**
(0 confirmed, 6 refuted, 1 descriptive; 3 reversal candidates banked). The confirmation rate is low
and honest; the drip value is carried by CONFIRMED S1.9 + the emergent narratives/reversals.

*(S1.4 measured on a proxy only → not counted as a verdict; proper metric queued. See notes.)*
**First CONFIRMED: S1.9 — the 2022 Self-Audit replicates (and survived the joint-release control).**

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
| S1.4 | The Copy-Paste Caucus | **REFUTED** (asymmetric, density-controlled) | **near-identical share (pre-registered metric): D rises both halves and SURVIVES the density control (matched D_A +1, D_B +1); R rises then falls (R_B −1).** D level 6–12% raw / 3–5% density-matched vs R 2–6% / 1–3% | 2026-07-15 | Not both-parties-rising → REFUTED, but the **density control did its job**: it stripped ~2/3 of the raw level (full D 0.12→matched 0.039 at 2019–20 = coverage) yet the **Democratic upward trend is real, not a density artifact.** Republicans flat/declining. Robust ⚠ power-position candidate (D's rise concentrates in the 2023–25 House-minority years) that reinforces S1.9. `s1_4_proper` (18-min re-normalize ×14) is the real metric; the verbatim one-pass floor agreed. Reframe check required before publishing. |
| **S1.9** | **The 2022 Self-Audit** | **CONFIRMED ✅** | **D weekly 5-gram overlap 0.00176 vs R 0.00095 (~85% higher), D>R in 75/105 weeks (71%)** | 2026-07-15 | **The founder's 2022 finding REPLICATES** on press releases (not Twitter), matched member counts. **Adversarial control passed:** excluding verbatim joint/co-signed releases *widened* the gap, and R actually co-signs more (48 vs 37) — so it's independent coordination, not co-signing. Congress 117 (2021–22, the pre-registered window). Card: `findings/S1.9.json`. **T1.** |
| S1.11 | Delegation Echo | **REFUTED** | same-state co-use ratio 1.01 (A) / 1.09 (B) vs the 1.5× gate | 2026-07-15 | Same-state delegations do **not** share phrases beyond a size-preserving permutation null — coordination is **national/party-driven, not regional.** Clean null (50-permutation test), an informative structural finding. |
| S1.10 | Bipartisanship Has a Season | **ARTIFACT** (a CONFIRMED overturned by the placebo — the marquee integrity catch) | pre-election bipartisan-signal trough in **6/6** cycles → looked CONFIRMED; **but the placebo (fake Nov-4 elections in odd years) shows 7/7 troughs too** | 2026-07-15 | The Aug–Oct dip / Nov–Jan rebound happens **every year, election or not** — it's **seasonal** (recess + campaign season vs winter legislating), NOT electoral. §4.5 adversarial verification caught and reversed a clean 6/6 CONFIRM before it shipped as "bipartisanship flees elections." Real reframe candidate: *bipartisan language has an autumn-vs-winter rhythm* (needs its own pre-registration). The single best demonstration of why the discipline exists. |
| S1.8 | The SOTU Gravity Well | **ARTIFACT** | annual "peak unison" days aren't SOTU (2013 peak = Oct 29, 2019 = Apr 2); counts up to 3,073 shared phrases; half-life a degenerate 1d every year | 2026-07-15 | The naive cross-party unison count is **boilerplate- and volume-contaminated** — the raw shard stream skipped the boilerplate filter `top_synchronized` applies, so procedural phrases both parties use routinely dominate, and the annual peaks are the highest-VOLUME days, not SOTU. Redefinition needed: boilerplate-filtered + daily-volume-normalized cross-party sharing RATE. **Deferred (S1.8′).** The discipline's 3rd caught artifact. |
| S1.6 | The 90-Day Snap | **REFUTED** (near-miss) | snap in 2022 & 2024 both parties, but not 2016/2020-R; tally A-R 2/4 fails the all-cells-majority gate | 2026-07-15 | Pre-election discipline tightening is **real and consistent in recent cycles** (2022/2024) but not across 2013–2026 — fails the strict gate by one cell. Reversal/refinement candidate (the effect may be a recent-era phenomenon). 2026 uncomputable (election is post-data-cutoff). |
| S1.1′ | Industrialization of the Memo (REDEFINED) | **REFUTED** (redefinition vindicated) | burst-ignition width **34d (2013) → 3–4d (2019–20)** then plateaus 2–15d (2021–26); dir_A −1, dir_B +1, ratio 4.86, density-survives | 2026-07-15 | The A2 fix works — **artifact gone (`artifact_guard=False`, no sawtooth)** via burst-local event detection on the merged cross-era series. Real finding underneath: **the memo DID industrialize ~8× through the 2010s, then hit a floor ~2019–20.** Fails the strict both-halves-monotone gate (it's industrialized-then-plateaued, not ever-accelerating). Strong reversal candidate. Kill-fixture-tested event detector. |
| S1.3′ | Phrase Lifespan Collapse (REDEFINED) | **REFUTED** (redefinition vindicated) | burst duration **92d (2013) → 12–15d (2019–20)** then plateaus/rises 12–52d (2021–26); dir_A −1, dir_B +1, drop 24%, density-survives, artifact gone | 2026-07-15 | Same A2 fix (burst duration on the merged series, censoring-safe). **Coherent with S1.1′: BOTH ignition speed and flare duration collapsed hard through the 2010s, then plateaued ~2019–20.** Fails the strict gate (not both-halves-monotone; 24% < 30%). The two together = a real T1/T2 narrative (below). Kill-fixture-tested (shortening + censoring guard). |

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

## Wave S2 — full-text language evolution (2026-07-15, 7 of 12 run)

| ID | Name | Verdict | Number |
|----|------|---------|--------|
| S2.1 | The Voldemort Index | **REFUTED → REVERSED** | opp-minus-own euphemism avoidance is **negative** (A −0.033, B −0.058) across Obama/Trump/Biden — the out-party NAMES the president (villain); the **in-party euphemizes its own** ("the administration"). Reversal candidate. |
| S2.2 | Adjective Inflation | **REFUTED** (partial) | only 0/1 words tripled (need ≥3 both parties) — but "extreme" ×2.7 (D), "radical" ×3.0 / "existential" ×2.6 (R): real partial inflation, party-asymmetric word choice. |
| S2.4 | Punctuation Archaeology | **DESCRIPTIVE** | **exclamations/statement +50% (0.032→0.048)**; first in-window emoji 2013-10-16. Shareable artifacts. |
| S2.5 | Death of the Semicolon | **REFUTED** | stable ~20–25 / 1k sentences (−12%, not −50%). Clean null. |
| S2.7 | Pronoun Economics | **REFUTED** | I/(I+we) stable ~0.33–0.40, dip ~2020; R slightly more "I" than D (small stable party gap). |
| S2.10 | The Concern Ladder | **REFUTED** | concerned 39k > deeply 5.8k > gravely 650, but "alarmed" 2.1k breaks the ordering. Grammar isn't a clean ladder. |
| S2.12 | The Apology Corpus | **REFUTED** | 1,226 total apologies, rate flat/noisy (73–309/100k), no era trend. T3 null footnote. |
| S2.3 | What Losing Sounds Like | **REFUTED** (a CONFIRMED overturned by both-halves) | pooled: minority higher on "the American people" + rhetorical questions, both parties → looked CONFIRMED; **but Half A fails (Dems-in-MAJORITY 2013–20 asked MORE questions).** The minority signature is a **recent-era (2021–26) effect, not a stable law** (self-honest gate now returns REFUTED). 2nd pooled-CONFIRMED reversed by §4.5 (after S1.10). Reversal candidate; partially explains the S1.9/S1.4 asymmetry as recent + power-linked. |
| S2.6 | Reading Level Drift | **REFUTED** | words/sentence stable; **Democrats consistently longer sentences (18–20) than Republicans (16–17)** — a stable party-style difference, not a trend. No recess-vs-DC effect (18.2 vs 17.9). |

**S2.9 The Boogeyman** | **CONFIRMED ✅** | out-party names sitting president ~2× more, **14/14 years, Half A 8/8, Half B 6/6** | 2026-07-16 | The confirmed inverse of the Voldemort hypothesis. Power-position RESOLVED to White-House control (2013–14 R House-majority still named Obama 2.6× as WH out-party). Symmetric, both-halves-passed (unlike S2.3). Fan-out measured it; **Opus re-verified independently** + fixed a chambers-control potus bug (118=D). Card: findings/S2.9.json. Label: mention≠hostility.
**S2.11 Euphemism Genealogies** | **DESCRIPTIVE** | 12 famous pairs; e.g. "climate change" D 34,581 / R 3,964; "death tax" D 32 / R 2,348; "obamacare" D 2,095 / R 36,808 | 2026-07-16 | Per-pair party split is the artifact (each pair its own mini-card). Verify agent reproduced counts EXACTLY, 24/24 label-sides hold in both halves. (Prose caveat: don't say Luntz "coined" climate change — he recommended an existing IPCC-1988 term.)
**S4.1 One Court, Two Languages** | **DESCRIPTIVE** (per-case) / aggregate **UNDERPOWERED** | 20 landmark SCOTUS rulings; loser-party louder 14/14; same-day response 19/20 | 2026-07-16 | Per-case series survives (each ruling = a drip card; birthright 06-30 is the live pilot). Verify agent caught a `_collect` count bug (cases counted per-day → 5–8× inflation); **fixed (dedup)**; corrected aggregate has only 5 half-B cases → UNDERPOWERED for the cross-case gate. All 20 decision dates verified (supremecourt.gov).
**S4.2 The Shutdown Blame Grammar** | **DESCRIPTIVE** | 7 shutdowns; self-blame D 4 / R 6; every window denominator + top-frame count reproduced to the digit | 2026-07-16 | Small-N event study. Dates verified vs Wikipedia/NPR (recent 2025/2026 shutdowns rely on the agent's WebSearch — re-check before publish). Who-shut-it-down framing by party.

**Remaining S2 (need reference tables):** S2.3 done; S2.6 done; S2.8 Seniority (tenure — needs historical roster).
**Reversal candidates banked:** S2.1 (Voldemort-reversed), S2.4 (exclamation inflation), S2.2 (partial).
Substrate: `text_features.jsonl` (675k statements, all lexicon/punctuation/pronoun/president features).

## The "Great Intensification" narrative (emergent, 2026-07-15)
Four verdicts point the same way and compose into one strong, re-pre-registrable story: **the
congressional message machine intensified relentlessly through the 2010s, then hit a ceiling around
2019–2020 and stopped.** Evidence: ignition speed collapsed 34→~4 days (S1.1′), talking-point flare
duration collapsed 92→~13 days (S1.3′), single-day synchronization peaked in 2017 (S1.2) — all three
then plateaued/reversed in the 2020s; and pre-election discipline tightening is now a *recent-cycle*
phenomenon (S1.6). Each was a "REFUTED" against a naive monotone guess, but together they are a T1
feature: *"The machine sped up until it couldn't, around 2019–20."* Publish as a pre-registered
inversion with all four series shown. (This is why the graveyard is not waste — it composed a headline.)

## Running note (after 7 verdicts — FIRST CONFIRMED)
**S1.9 is the first CONFIRMED finding — and it's the flagship** (the founder's own 2022 result
replicates on press releases, matched controls, joint-release confound defeated). It landed *because*
the machine had already refused 3 false positives (S1.1/S1.3/S1.4) and 2 more refutes (S1.11
delegation, and the reversal-candidate nulls S1.2/S1.5/S1.7) — the discipline is what makes this one
trustworthy. Substrate now built: streaming reader, phrase index (3.09M), statement-meta (686k),
member-augmented index (37k high-peak phrases + member unions), bioguide→state, elections/presidents
reference tables. **Remaining S1:** S1.12 Leadership Ignites (needs a leadership roster — sourcing),
S1.6 / S1.8 / S1.10 (need sessions/SOTU tables — accurate sourcing), and the redefinitions S1.1′/S1.3′
(event-detection on a merged cross-era series) + S1.4-proper (statements-in-groups + density control).
Reversal candidates S1.2/S1.5/S1.7 are a parallel content stream (re-pre-register in the found
direction). Next best CONFIRM shots: S1.12 (leadership origination) and the S1.4-proper rebuild.

## Wave S3 — roster joins / member lifecycle (2026-07-16, 7 of 7 adjudicated; 1 measured)

| ID | Name | Verdict | Headline number | Date | Notes |
|----|------|---------|-----------------|------|-------|
| S3.1 | The Freshman Assimilation Speedrun | **BLOCKED** (source, not power) | **0 of the 2001 cohort clears the spec's own ≥20-statement entry floor**; cohorts 107–112 yield 0/0/0/0/1/3 qualifying freshmen; press lane holds **2,000 statements total for 2001–2012 = 0.3% of the corpus**, single-party before 2009 | 2026-07-16 | The pre-registered "≥25% decline 2001→2026" cannot be computed: the 2001 end of the comparison is empty. **7 usable cohorts (113–119), not 13** — i.e. Amendment A1's 2013 cliff bites the *entry* variable, which is the hypothesis's anchor. Any respec must also survive the member-coverage collapse (191–253 distinct members/month in 2021–22 vs ~500 in 2018–20). Re-home to the CREC lane (docs/15) or retire. **T1 downgraded to unbuildable-in-lane.** |
| S3.2 | Lame-Duck Honesty | **BLOCKED** (twice: no IV, and the class is silent) | (a) `elections.json` = **7 dates, zero results** → general-election losers are not identifiable at all, and the roster records no departure reason; (b) departing members' lame-duck median output is **0–1 statements in all 6 cycles** (2%/2%/22%/28%/0%/0% publish ≥5) vs returning-member medians 8/9/10/11/2/4; only 2 of 6 cycles have a usable pre-period | 2026-07-16 | The "≥30 losers per half" floor is unreachable. **The emptiness is scraper mechanics** (offices wind down; upstream follows current-member sites) — so it is a *selection artifact* and must not be published as behavior either ("defeat silences the script" would be a lie about the crawler). Re-home to the CREC floor lane, where a departing member still speaks on the record. |
| S3.3 | The Retirement Drift (H3 retrospective) | **BLOCKED** (reference table does not exist) | The required curated table of **announced-retirement dates has zero rows** — `data/reference/search/` holds 6 files, none of them retirements; the roster carries term start/end but **no `end_reason`, no intent signal**. Only the 2018 (67) and 2020 (47) cycles have members with ≥40 statements in the prior 12 months | 2026-07-16 | Billed in §12 as **"the flagship backtest — the machine's first firing"**; it is currently the least-supported hypothesis in the wave. Even if the table were built, the "≥40 retirements" floor is reachable only by pooling to one cycle per half — **exactly the pooling that killed S2.3**. Unblock = one acquisition (announced-retirement dates, offline-parse-and-commit) **plus** an honest restatement of the halves. HORIZON H3 error-bar rules still apply. |
| **S3.4** | **The Party-Switch Fingerprint** | **REFUTED** (DESCRIPTIVE → REFUTED; killed by 2 of 3 skeptics) | Published headline was "**N=1 of 14 switches; Van Drew +0.0258 identity-controlled, 92.9th pctile**". Both figures fall: the enumerator missed ≥3 switches (**≥17 dated changes, not 14**) and **3 events clear the declared floor, not 1** — Sablan 2015-01-06 D→I is **240 pre / 322 post, more data than the one case built**. The identity control deleted **8,286 tokens incl. `trump`, `house`, `white`, `justice`** (roster-surname collisions over the impeachment window); correct target-scoped control gives **+0.0206 / 33-of-452 / 92.7th**, and the length-robust estimator gives **+0.0039 / 84.4th (70 of ~450 non-switchers drifted further)** | 2026-07-16 | **The graveyard row was the product and the graveyard row was wrong.** Root cause: `load_switches()` reads only each term's `party_affiliations` array and skips `i==0`, but congress-legislators encodes most switches as a **whole-term `party` field change with no affiliations array** — term-boundary switches are structurally invisible. It caught the one Sablan event with zero corpus and filed him as a "pre-2013 press-lane cliff" casualty; he is one of the best-covered members in the mirror (**2,318 statements**). Second kill: `controls_survived` is void — split-halves "all 4 pairings" is **one test restated four times** (algebraically max(pre)<min(post); verified 200,000/200,000; null pass rate exactly 1/6; **110/450 non-switching peers pass it**), and the "clean nulls" are **within-frame** (same idf, same centroid) compared against a cross-frame delta — near-zero by construction. Peer-calibrated, the p95 of *pure within-window drift* (+0.0267/+0.0330) **exceeds** the headline effect. **What survives (and is worth keeping):** D↔R switches since 2001 = **5, measurable = 1**; the LEVELS story (Van Drew at the **89.8th pctile of R-leaning-ness among Democrats *before* switching**, the 26.3rd among Republicans after — he never left the middle); the density bootstrap (**0/300 draws ≤ 0**); and the deflation (**Pelosi out-drifted the man who changed parties, +0.0367 raw, no switch**). Three attacks *failed* and two placebos say the author under-claimed. **Do not publish. Fix the enumerator, decide whether the tilt instrument admits Independents, re-run the graveyard.** |
| S3.5 | Committee Vocabulary Infection | **BLOCKED** (by its own pre-registered gate) | The 🔬-lite audit ran: `committees-{current,historical}.yaml` are mirrored and contain **ZERO bioguide references** — they are name/metadata tables for the nomenclature lane. Upstream membership is `committee-membership-current.yaml`, **current-Congress only**; historical membership **does not exist upstream**. **Committee assignment dates — the metric's anchor — exist in no mirrored source** | 2026-07-16 | The spec said "BLOCKED if historical membership incomplete." It is not incomplete; it is absent. **Recommend retirement of the hypothesis** rather than a reconstruction program — rebuilding 25 years of committee rosters is a capex line item, not a wave step. The gate worked exactly as written: audited before measuring, cost ~nothing. |
| S3.6 | Adoption Speed vs. Cohort Age | **UNDERPOWERED** | Inherits S3.1's **7 cohorts** (36–92 members each). "CONFIRM: monotone by cohort" over 7 points splits into halves of **3 and 4** — **a random ordering of 3 points is monotone 1 time in 3**, so the pre-registered halves-agree clause **cannot be satisfied under any future data in this lane**. Cohort 117 is a non-random **52% sample** of its class sitting mid-trend-line | 2026-07-16 | Publishes **DESCRIPTIVE at best**, with per-member cadence normalization mandatory. The gate is not merely unmet — it is unmeetable, which is a spec defect (a T3 ride-along inherited a T1's power requirement). |
| S3.7 | The Safe-Seat Vessel Test | **BLOCKED** (source; **cheapest unblock in the wave**) | `elections.json` has **no margin of victory** (it is 7 computed election dates); **no MoV table is mirrored anywhere** in `data/**` or `X:\onscript-data\**`. **The independent variable has zero rows** | 2026-07-16 | **One acquisition turns this into a real GO:** MIT Election Lab / FEC results → `bioguide × cycle → margin` JSON, same offline-parse-and-commit pattern as `committee-names.json`. Yields **~90–100 members per quintile** — genuine power, and the spec is honest either way ("either direction confirms something; flat REFUTES both folk theories"). **This is the wave's one recoverable hypothesis and the highest-value item to unblock.** |

### Wave S3 graveyard note (2026-07-16)

**S3 is the first wave whose dominant failure mode is source absence, not confounding.** Five of seven
were blocked *before measurement* — and four of those five (S3.2, S3.3, S3.5, S3.7) were blocked on
**reference tables docs/12 assumed into existence at pre-registration**: election results, announced
retirement dates, historical committee membership, margin of victory. The corpus is not the problem;
**the joins are unbuilt.** That is a planning defect and it is cheap to name: the S3 specs were written
as if `elections.json` were an election-results table (it is 7 dates), and as if the roster carried
departure reasons (it does not).

**The one hypothesis that ran (S3.4) died of a code bug in the very artifact it nominated as
publishable** — the enumerator that builds the graveyard couldn't see the encoding congress-legislators
actually uses for term-boundary switches, so the graveyard's flagship line ("only one switch in
twenty-five years left a paper trail") was false in both figures. **The adversarial pass caught it. The
subagent did not.** This is the fourth §4.5 reversal of the program (after S1.10, S2.3, and the
S1.1/S1.3 artifacts) and the first one caused by an *enumeration* error rather than a confound — a new
failure class worth a protocol line: **verdicts that rest on "we looked and found nothing" must show
that the looking instrument can see a positive control.** S3.4's enumerator was never asked to find a
switch it was known to have.

**Reusable-code hazard, flagged for every future wave:** the S3.4 `identity_drop_set()` pattern (drop
every ≥3-char token appearing in any name in `legislators-HISTORICAL.json`) deletes **`trump`, `house`,
`white`, `wall`, `justice`, `green`, `washington`, `virginia`, `jordan`** and ~110 more political
content words via 250-year surname collisions (Philadelph Van Trump, John House, Jim Justice, Garret
Wall). **It will silently gut any Trump-era vocabulary analysis.** Identity controls must be
target-scoped (that member's own name + state + titles), never roster-wide.

**Process note (kept on the record):** the S3.4 author's first fast-path reimplementation of the
speaker-attribution gate silently diverged from the tested `pipeline.duet` implementation
(`re.finditer` is non-overlapping, so a fresh-slice scan finds markers a full-text scan misses); the
selftest caught it at 1/7,383 sentences and it was reverted to an exact reimplementation, then
re-verified at **0 mismatches over 62,990 real sentences**. The selftest existed because the protocol
requires it. Also: a broad `Stop-Process` matched on the miniconda path rather than the author's own
command line while parallel sessions were running — careless; PID-by-command-line targeting after.

### Wave S3 — what it cost and what it bought

| tested | confirmed | refuted | underpowered | artifact | blocked | descriptive |
|---|---|---|---|---|---|---|
| 33 | **2** | 17 | 1 | 4 | 5 | 4 |

**Wave S3: 0 confirmed, 1 refuted, 1 underpowered, 5 blocked — the first wave with no measurement to
speak of.** Six of seven never reached a number; the seventh (S3.4) reached numbers that two of three
skeptics broke. Cumulative confirmation rate: **2 of 33 = 6.1%.** New finding cards from S3: **zero.**
Standing card inventory unchanged at 8 (`data/derived/findings/`: 2 confirmed + 6 reversal/descriptive).

Failure-mode split across S3's five blocks: **four are missing reference tables** (election results,
retirement dates, historical committee membership, margin of victory) and **one is the 2013 press-lane
cliff** (S3.1). One of the four is a one-acquisition fix (**S3.7 — MoV**); one is retirement-recommended
(**S3.5 — the data does not exist upstream**); two re-home to the CREC floor lane (**S3.2, S3.3**).

## What S3 says about the program's premise

**The projection is arithmetically dead. Say so plainly.**

docs/12 §0 projects **~22–28 CONFIRMED from 47** hypotheses (corpus-only families ~60% survival,
joined families ~40%). After 33 tested: **2 CONFIRMED.** Hitting even the low end would require **20 of
the remaining 14** hypotheses to confirm. There is no recovery path — this is not "behind pace," it is
**an impossible remainder.** At the observed 6.1% rate the 47-hypothesis catalog terminates around
**3 CONFIRMED**; at a generous 15% for the un-run remainder, **4–5**. The honest ceiling is **4–6, not
22–28.** The §0 survival assumptions were off by roughly **5×**, and the error is now large enough that
leaving the number in the doc is itself a small dishonesty.

**But S3 does not refute the premise the way the number implies — and the distinction is load-bearing.**

The 40% joined-family survival estimate was never *tested* in S3. **The joins do not exist.** Five of
seven blocked before measurement, four of those on reference tables docs/12 assumed into existence at
pre-registration (`elections.json` is 7 dates, not election results; the roster has no departure reason;
historical committee membership is absent upstream; no MoV table is mirrored anywhere). That is a
**planning defect, not an instrument verdict.** S3 says the joined families were *specced against
imagined substrate* — which also means the 40% figure remains **unfalsified**, and S3.7 (~90–100 members
per quintile after one acquisition) is evidence the joins can be genuinely well-powered once built.

Two structural facts the earlier waves had already established, now confirmed at the roster level:
1. **The 2013 cliff is not a caveat, it is the boundary of the instrument.** Amendment A1 said the
   symmetric span is 113–119. S3.1 shows it bites the *entry* variable too: **0/0/0/0/1/3** qualifying
   freshmen for congresses 107–112. Every "25-year" lifecycle hypothesis in the catalog is really a
   12-year hypothesis until CREC lands.
2. **The gates are calibrated for a corpus we don't have.** S3.6 is the proof: "monotone by cohort,
   halves agree" over 7 points with halves of 3 and 4 **cannot pass under any future data** — a random
   3-point ordering is monotone 1 time in 3. A T3 ride-along inherited a T1's power requirement. Several
   surviving gates are probably in the same condition, and nobody has audited them.

**Is the projection recoverable? No. Is the program? Yes — but only if the yield unit changes.**

The program has been counting the wrong thing. **CONFIRMED-hypothesis is a scientific unit; the drip
needs a publishable unit,** and by that measure the inventory is not thin — it is already oversubscribed:
**S4.1 alone is 20 SCOTUS cases** (loser-party louder 14/14, same-day response 19/20, per-case series
survives), **S2.11 is 12 euphemism pairs** (24/24 label-sides hold in both halves, counts reproduced
exactly), **S4.2 is 7 shutdowns**, plus **2 CONFIRMED** (S1.9, S2.9), **the Great Intensification**
four-series narrative, and ~8 banked reversal candidates. That is **~45+ drip-ready artifacts** against a
target of 1–2/month for 12–24 months. **The drip is not at risk. The scoreboard is.**

And the §3.S6 reserve is no longer a reserve — **it is the wave's actual product.** "We tested N folk
theories about congressional speech; K are false" was pre-registered as a fallback; at 6.1% it is the
main line, and it is *stronger* for the low rate, not weaker. The graveyard now contains four caught
reversals (S1.10's placebo, S2.3's halves, S1.1/S1.3's boundary artifact, S3.4's enumerator) — that is
the proof-of-instrument, and it is the most defensible asset the program has against the first bias
accusation. **A shop that publishes its own overturned CONFIRMEDs is a shop whose CONFIRMEDs mean
something.**

### The honest goal (recommend replacing docs/12 §0)

> **~4–6 CONFIRMED across the 47** (2 in hand), **~45+ publishable cards** (per-case series + reversals
> + the graveyard), and **a published null rate as a headline asset, not an apology.** The CONFIRMED
> tier is the rare tier — that is what makes S1.9 and S2.9 worth the banner. Yield is counted in cards.

### Three concrete consequences

1. **Amend §0 now, before Wave S4/S5 pre-registration inherits the same fantasy.** This is Fable's call
   (§0 is a program doc), but Opus should file the arithmetic. **The number to strike: 22–28.**
2. **Audit the un-run gates for reachability before running them** — S3.6's gate was unmeetable, and it
   cost a wave slot to discover that at execution time rather than at spec time. A one-pass "can this
   gate pass at the available N?" sweep over the remaining 14 is cheap and will likely reclassify
   several to DESCRIPTIVE-by-design *before* they burn a session.
3. **The acquisitions are now the highest-leverage work in the Search, not the analyses.** Ranked:
   **(a) MoV table → unblocks S3.7** (cheapest, real power, publishable either direction); **(b)
   election-results join → unblocks S3.2's IV** (though the lame-duck class is silent in *this* lane
   regardless, so it re-homes to CREC); **(c) announced-retirement dates → S3.3**, the self-described
   flagship backtest, currently zero rows. And **(d) retire S3.5** — its data does not exist upstream and
   reconstructing 25 years of committee rosters is capex, not a wave step.

**One line for the record:** Wave S3 spent its slot discovering that its substrate was imaginary, and
its single measurement died of a bug in the enumerator that was supposed to prove the negative. Both are
findings about *us*. The correct response is to fix the ledger's arithmetic and the doc's projection —
not to soften either.
