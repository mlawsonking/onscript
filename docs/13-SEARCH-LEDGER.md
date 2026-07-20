# 13-SEARCH-LEDGER — verdicts from the Search (append-only; Opus maintains)

> One row per pre-registered hypothesis in `docs/12-SEARCH-PROGRAM.md`. Every hypothesis ends in
> exactly one verdict: CONFIRMED · REFUTED · UNDERPOWERED · ARTIFACT (confound named) · BLOCKED.
> Confirmed findings get a card in `data/derived/findings/`. Numbers, not adjectives.

## Tally

> **⚠ 2026-07-17 — every verdict below was validated on a split that sat on the provenance seam (see
> the WARNING section). ALL 34 have now been RE-VALIDATED within one lane — the runnable half (Session
> 18, "RE-VALIDATION — WITHIN-LANE") and the eleven BLOCKED-ON-SHARDS half (Session 19, "SHARD-LANES
> RE-VALIDATION"), both at the end of this file. Headline: the seam overturned ZERO verdicts toward a
> false positive, the two original CONFIRMEDs survive (S2.9 now twice-confirmed), AND lane isolation
> surfaced TWO NEW within-lane CONFIRMED — S1.1′/S1.3′, the "Great Intensification" (2013→2020, absent
> after the seam), pending Fable/neutrality review. Program CONFIRMED tally 2→4.**

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

## Wave S4 — event-anchored studies (2026-07-16, 3 of 8 run, 5 BLOCKED on absent reference tables)

> **Supersedes L111–L112.** The earlier S4.1/S4.2 rows were first-pass verdicts. Both are amended
> below: S4.1 gains its aggregate adjudication (no rebuild needed — `pipeline/search/wave_s4.py`
> already implements it), and **S4.2 is downgraded DESCRIPTIVE → REFUTED by 3/3 skeptics.**
> Do not read L112 ("7 shutdowns; self-blame D 4 / R 6") as live; it is a stale count from a
> different window set (the real table merges to 5 events per its own note fields).

| ID | Name | Verdict | Headline number | Date | Notes |
|----|------|---------|-----------------|------|-------|
| S4.1 | One Court, Two Languages (AMENDED) | **DESCRIPTIVE** (per-case) / **UNDERPOWERED → would fail anyway** (aggregate) | per-case: loser-party louder 14/14, same-day response 19/20. Aggregate: half B has **5** qualifying cases vs a floor of 8; `party_direction_gate=False` at **every** floor (5/8/10) and the dominant sign **REVERSES across halves (A=−1, B=+1)** | 2026-07-16 | Amends L111. Adjudicated from the existing `wave_s4.py::run(topk,min_cell)` — **nothing rebuilt.** The aggregate arm is not merely underpowered: it fails on direction at any power level, so more cases would not rescue it. The **top-phrases "two vocabularies" arm is DEAD on the nomenclature audit (~97% naming — the anchor is case names, so case names top the list; K2 fires)**, and its half-A median Jaccard of **0.60** shows *convergence*, not divergence — the opposite of the hypothesis. Per-case valence series remains shippable as **descriptive, per-case only**. |
| S4.2 | The Shutdown Blame Grammar (AMENDED) | **REFUTED** (DESCRIPTIVE downgraded — 3/3 skeptics) | claimed: agent-assignment ~95% outward, self-blame ~0 (D 291/301, R 196/208). **Killed: the headline statistic was never placebo-tested. On the agent's own 10 matched non-event windows it is D 74/74 = 100.0% / R 16/18 = 88.9% — the placebo D share EXCEEDS the event D share (96.7%).** | 2026-07-16 | Supersedes L112. **Four independent kills, all reproduced:** (1) **PLACEBO FAILS THE HEADLINE** — the placebo was run against the blame *rate* (topicality) and the *outward share* was headlined; run correctly, the "response" appears at 100% on random dates. S1.10 verbatim. (2) **The denominator is not a partition** — self-blame units are a near-subset of outward units (8/10 D, 6/12 R overlap; 4/4 in 2025), so 291/301 adds numerator units to the denominator; true distinct = D 291/293, R 196/202. (3) **The statistic is bounded at 1 by construction** — the agent's own hand-code says 12/12 self-blame hits are false positives (opponent's frame quoted to rebut), so true self-blame = 0 and the only attainable value is 100%. A constant is a definition, not a measurement; the split-halves "PASS" is vacuous. (4) **Appropriations seasonality** — fiscal years end Sep 30 annually; the grammar fires in 8/11 non-shutdown Sep–Nov windows, and **two non-shutdowns out-score two real shutdowns** (2023 = 0.256 and 2015 = 0.202 vs real 2026 = 0.105 and real 2018-19 = 0.066, the longest lapse then on record). Mann-Whitney AUC 0.909. The agent diagnosed this itself ("the grammar tracks the FIGHT, not the LAPSE") and filed it as a reference-table footnote under a PASS. Also: "who stops talking first" is a **degenerate estimator** (single-day unsmoothed peak; the identical rule returns stop_day ≤ 2 on 95% of 410 *in-event* fake end-days, median 0) with an off-by-one (`range(0,…)` indexes the event's final day) and no weekday control (2/5 events end Friday, cross Saturday). "Which party blames harder" correctly REFUTED (direction flips 3-2). **Nothing in S4.2 is publishable.** Two byproducts outlive it (below). |
| S4.4 | The Friday Night Dump | **REFUTED** (a clean, well-powered, instrument-validated null — the graveyard product) | Friday walk-back rate = **0.85× Mon–Thu in half A** [CI95 0.72–1.00], **0.96× in half B** [0.76–1.20]. Gate was **≥1.5× in BOTH halves.** Both CI upper bounds sit **below** the gate → equivalence, not failure-to-detect. **There is no Friday Night Dump.** | 2026-07-16 | **The load-bearing evidence is the POSITIVE CONTROL:** same machinery, same 1.5× gate, pre-registered week-ending vocabulary → **2.10× (A) / 1.75× (B), both clear the gate**, while a register-matched placebo lexicon is flat at 0.98×/0.96×. The instrument finds Friday effects where theory predicts them and not where it doesn't — that asymmetry converts "we didn't find it" into "it isn't there." **Pre-registration hashed before measurement** (sha256 `6cbee4a8…6b6d5`). Survived every control: rates-not-counts, density/length (no quartile reaches the gate), syndication collapse (7,870 dup rows), **leave-one-out across all 41 lexicon forms (A stays [0.83,0.88], B [0.93,1.01] — no single form drives it)**, office-day unit (0.82/0.99), day-block bootstrap ×2,000. **The holiday-eve arm's one suggestive number (1.31×) was KILLED by its own placebo** — 500 weekday-mix-matched random pseudo-eve sets put the real rate *inside* the null band [0.347%, 0.612%]; 6.0% of purely random date sets beat it. Sub-finding "did the Dump die with the 24/7 cycle?" = **NO, it was never alive** (ratio moves the wrong way, 0.85→0.96, CIs overlap). Honest caveats logged: core-B fails its own hit floor (139 < 200) so the verdict rests on half A (the gate is conjunctive); the tempting inverse ("Congress apologizes *less* on Fridays") is **not claimed** — within-quartile ratios (0.78–1.11) sit closer to 1.0 than the pooled 0.85, so the deficit is length composition, not behavior; and the pre-registration was written after the recon probe's answer (0.96/1.12) was known — mitigated, not eliminated. **0/34 nomenclature. K2 does not fire.** |
| S4.3 | (crisis-response volume decay) | **BLOCKED** | — | 2026-07-16 | `crisis-events.json` **does not exist.** docs/12 L109/L282 name it; disk has six reference files and grep finds zero code or data. Also booby-trapped when unblocked: its pre-registered monotone volume-decay CONFIRM would be satisfied by the **2021 coverage collapse alone.** → REVIEW-GATED. |
| S4.5 | (winner/loser-party language) | **BLOCKED** | — | 2026-07-16 | `elections.json` carries **seven dates and nothing else** — no winners, no losers, no margins. The spec's entire dependent variable is absent from its only join key. **This is the S3.7 failure verbatim.** Independently, the "13 cycles" gate is unreachable: 7 dates (2014–2026), 2026 is in the future (measured D=0/R=0) → 6 usable. Re-speccable as a 6-cycle DESCRIPTIVE using `chambers-control.json` as a coarse, disclosed winner proxy — **only as a new pre-registration, not a rescue.** |
| S4.6 | (post-disaster cross-party unison) | **BLOCKED** | — | 2026-07-16 | Same non-existent `crisis-events.json`. Most K2-exposed item in the wave: cross-party unison after a disaster will be dominated by **the storm's name and the place name** — "disasters have proper nouns," not "disasters produce unison." The ≥3× gate must run on a **naming-stripped** phrase set or it measures nothing. |
| S4.7 | (January 6 response) | **BLOCKED** (comparative arm) | within-event arm IS powered: D 324 stmts / 77 offices, R 341 / 94 (2021-01-06..01-20) | 2026-07-16 | Comparative arm needs `crisis-events.json`. **DO NOT RUN the volume comparison on raw counts:** Jan 6 sits at the exact bottom of the coverage collapse (2020: 177 stmts/office → 2021: 54), so raw volume would manufacture a false and **highly quotable** "muted response to January 6." → REVIEW-GATED, double gate. Recommend leaving unmeasured until the comparison table exists **and** coverage normalization is tested on a non-sensitive event first. |
| S4.8 | (war-authorization language evolution) | **BLOCKED** | AUMF 2002 = **ZERO statements** | 2026-07-16 | Two independent grounds: (1) the "curated votes list" does not exist anywhere in the repo; (2) Sept/Oct/Nov 2002 are **absent from the mirror entirely** — all 23 Iraq-mentioning statements in 2001–2003 belong to a single member (Barbara Lee). "Evolution" is unrecoverable from a baseline of zero. Syria 2013 (D 2,782/165 offices, R 2,637/188) and Ukraine 2022 (D 1,173/117, R 1,009/119) **are** powered → a two-event 2013–2022 descriptive is available as a **new, retitled** registration. The pre-2013 leg belongs to the CREC lane (docs/15), where congress 107 already yields 11,867 symmetric two-party statements — gated behind SD.8 calibration and genre isolation.

## Graveyard notes — Wave S4

- **S4.4 (2026-07-16) — the model entry.** A famous folk theory, pre-registered and hashed *before*
  measurement, well-powered (674,970 statements analyzed), killed cleanly at 0.85×/0.96× against a
  1.5× gate — **with a validated instrument standing behind the kill** (positive control 2.10×/1.75×,
  placebo lexicon 0.98×). Both CI upper bounds fall below the gate, so this is an **equivalence
  result**: the Dump is bounded away from its claimed size, not merely undetected. Three skeptics
  found nothing. This is what docs/05 §2.5 meant by the graveyard being the product.
- **S4.4's design lesson belongs in docs/12 before Wave S4 is specced further.** S4.4 needed **no
  reference table** and is **K2-immune for the same reason**: it measures a *pre-registered speech act
  within a time window* instead of measuring *which phrases are common in an event-anchored selection*.
  S4.1 is the mirror image — it anchors on case names, so ~97% of its emitted lines are case names.
  **Event-anchored phrase selection manufactures nomenclature convergence by construction.**
- **S4.2 (2026-07-16) — the fourth reversal, and the most instructive.** Its `honest_note` contained
  three separate concessions ("mostly definitional"; "outward_share is a FLOOR"; "the grammar tracks
  the FIGHT, not the LAPSE") and it filed all three **under a PASS**. The failure was not
  computational — the instrument is honest, reproducible, symmetric (D/R regex skeletons byte-identical
  after token substitution), and its multi-speaker gate was load-bearing (dropped 31 hits in 2018-19 D
  alone). The failure was **placebo-testing statistic A and headlining statistic B**, then letting a
  bounded-at-1 constant carry a card. Add to the protocol: *the placebo must be run against the exact
  statistic that appears in the headline.*
- **One correction the agent got backwards, worth keeping:** it claimed 95% is a "floor" because false
  positives land in the self bucket. Removing outward-bucket FPs gives (291−f)/(301−f), which
  **decreases**. It measured only the FP direction that helped its number.
- **Two byproducts outlive S4.2 and are worth more than the arm was:**
  1. **Corpus defect — bioguide `K000393` is a cross-chamber surname-collision roster mislabel.** 220
     statements from `kennedy.house.gov` (Tim Kennedy, D-NY-26) are labeled "John Kennedy / Republican
     / LA / Senate"; 50 more carry state "KY"; chamber contradicts domain in both directions. Dates
     2024-05-06..2026-04-01 — **inside the 2025 and 2026 windows.** Impact on S4.2 was negligible, but
     it is **~17% of the R self-blame bucket** (2 of 12 units), and a party-keyed denominator of 12 has
     no tolerance for it. **Cheap detector: domain-vs-chamber disagreement** (322 of 888 bioguides map
     to >1 domain; most benign — web.archive.org/bit.ly). Code fix, not a Michael action.
  2. **`shutdowns.json` defines "non-event" wrongly.** It means "no funding gap occurred," but the
     blame grammar tracks the **fight**, not the **lapse** — 2015-09/10 (Boehner CR) and 2023-09/11
     (McCarthy CR/ouster) are brinkmanship windows that score like events. **A near-miss/brinkmanship
     table would fix the placebo and is a better hypothesis than the cross-event trend arm the
     substrate cannot support anyway.**

## PROGRAM-LEVEL — two structural findings that outrank any new measurement

- **The substrate-assumption pattern is now confirmed twice and is structural, not bad luck.** Wave S3
  lost **5 of 7** to reference tables docs/12 assumed into existence. Wave S4 lost **4 of 8** (S4.3,
  S4.5, S4.6, S4.8) to the same cause, plus S4.7's comparative arm. `elections.json` (7 bare dates)
  failed S4.5 the *identical* way it failed S3.7. **Recommendation: a one-time inventory audit of every
  remaining wave's named tables against disk before any further speccing — roughly an hour, and the
  highest-yield hour available.**
- **The 2021 coverage collapse is undocumented and is gating the program's primary robustness test.**
  D statements 48,901 → 9,065; 177 → 54 statements per office; 276 → 167 offices; **symmetric across
  parties.** It gates S4.1's half B, S4.2's cross-event arm, S4.3's CONFIRM, and S4.7 entirely. It also
  sits **exactly on the A/B half boundary of BOTH `scotus-landmarks.json` and `shutdowns.json`** —
  meaning split-halves, the program's primary robustness test, is currently testing
  **high-coverage-vs-low-coverage as much as early-vs-late.** Whether this collapse is real or an
  upstream `congress-press` regression is a **factual question that gates four hypotheses** and
  deserves priority over any new measurement. (S4.4 handled it correctly — it chose the halves *at* the
  cliff deliberately, as a real regime boundary, and reported per-office-per-day.)

### Wave S4 — tally, review gates, and the re-baseline correction

**Wave S4 tally (honest):** 8 pre-registered · **3 run** (S4.1, S4.2, S4.4) · **5 BLOCKED** on reference substrate docs/12 assumed into existence (S4.3, S4.5, S4.6, S4.8 fully; S4.7's comparative arm) · **0 CONFIRMED** · 1 REFUTED-and-survived (S4.4) · 1 DESCRIPTIVE→**REFUTED by 3/3 skeptics** (S4.2) · 1 DESCRIPTIVE-per-case with a dead aggregate and a dead phrase arm (S4.1) · **3 REVIEW-GATED** (S4.3, S4.6, S4.7).

**Cumulative program tally: 34 tested / 2 CONFIRMED = 5.9%.** (33 before S4; S4.1 and S4.2 were already counted at L111–L112 and are amended here, not re-counted — S4.4 is the 34th and only new test.) The two CONFIRMEDs remain S1.9 (the 2022 Self-Audit) and S2.9 (the Boogeyman), both from Waves S1/S2. **Wave S3 added zero. Wave S4 added zero.**

Updated header table (replaces L9–L11):

| tested | confirmed | refuted | underpowered | artifact | blocked | descriptive |
|---|---|---|---|---|---|---|
| 34 | **2** | 24 | 1 | 4 | 5 | 3 |

**Blocked is not tested** — the 5 blocked S4 items are excluded from the denominator, which is why the honest read is worse than the table looks: the program is now failing to *reach* hypotheses as often as it fails to confirm them. Two consecutive waves (S3: 5/7 lost; S4: 4/8 lost + 1 partial) have lost the majority of their hypotheses to absent reference tables, not to reality.

**REVIEW-GATED (never auto-card; nothing publishes without Michael's explicit review):**

- S4.3 (crisis-response volume decay) — NEEDS-NEUTRALITY-REVIEW **and** BLOCKED. Double problem: `crisis-events.json` does not exist (docs/12 L109/L282 name it; disk has six reference files, grep finds zero code or data), AND the hypothesis is booby-trapped when unblocked — its pre-registered monotone volume-decay CONFIRM would be satisfied by the 2021 coverage collapse alone (177 -> 54 statements per office). Building the table without first resolving the collapse would manufacture a CONFIRM out of a data regression. Not shippable; not even safely runnable.
- S4.7 (January 6 response) — NEEDS-NEUTRALITY-REVIEW, DOUBLE GATE. The within-event arm IS powered (D 324 stmts / 77 offices, R 341 / 94, 2021-01-06..01-20) and the comparative arm is blocked on the same non-existent `crisis-events.json`. **DO NOT RUN the volume comparison on raw counts under any circumstances:** January 6 sits at the exact bottom of the 2021 coverage collapse, so raw volume would manufacture a false — and maximally quotable, maximally damaging — 'muted response to January 6' finding. RECOMMENDATION: leave unmeasured until (a) the comparison table exists, and (b) coverage normalization has been tested on a NON-SENSITIVE event first. This is the one item in the wave where a measurement error would be indistinguishable from a political accusation.
- S4.6 (post-disaster cross-party unison) — BLOCKED on the same non-existent `crisis-events.json`, and the most K2-exposed item in the wave. When unblocked, its >=3x unison gate must run on a NAMING-STRIPPED phrase set or it measures nothing: cross-party unison after a disaster will be dominated by the storm's name and the place name, i.e. 'disasters have proper nouns' rather than 'disasters produce unison'. Flagging under review-gated rather than merely blocked because the failure mode is a publishable-looking coordination claim built entirely from naming.

**S4 says the card-based re-baseline is right in principle and wrong on its inventory number — and that the binding constraint was never measurement supply.**

**1. CONFIRMED-counting is dead, and S4 is the proof rather than the cause.** 2 of 34 (5.9%) with zero from two consecutive waves. But the wave's single best artifact — S4.4 — is a **REFUTED**. A hashed pre-registration, 674,970 statements, a 1.5× gate missed at 0.85×, an equivalence result (both CI uppers below the gate), and a **positive control at 2.10×** proving the instrument could have found the effect. Under CONFIRMED-counting that is a zero. Under card-counting it is the wave's flagship. The metric change is not a lowered bar — it is the correct bar, and S4.4 is the worked example.

**2. The "~45+ cards in hand" number does not survive contact with disk.** `data/derived/findings/` contains **8 files**: GREAT-INTENSIFICATION, S1.4, S1.9, S1.10, S2.1, S2.3, S2.4, S2.9. The 45+ is a count of *candidates* claimed across sessions — per-case series, reversal candidates, per-pair mini-cards (S2.11's 12 euphemism pairs, S4.1's 20 rulings) — not written, verifier-passed, publishable cards. **Re-baselining onto a number that is 5.6× the on-disk reality would import exactly the failure mode S4.2 just died of: headlining a statistic other than the one that was actually validated.** The honest re-baseline needs the audit first: how many of the 45+ survive a nomenclature audit, a denominator check, and a placebo against *their own headline statistic*? S4 says the attrition is severe — S4.1 alone loses its entire 20-card top-phrases arm to a ~97% naming fraction, and S4.2 loses all of its.

**3. Even so, the re-baseline holds — because 8 real cards ÷ 1–2/month is 4–8 months of drip, and the constraint is upstream.** Wave S4 spent 5 of 8 hypotheses on tables that do not exist. Wave S3 lost 5 of 7 the same way. **The program is not short of findings; it is short of substrate and of publication throughput.** At 1–2 cards/month, the existing 8 cards plus S4.4 plus a de-phrased S4.1 per-case series already exceed the next two quarters of drip capacity. Measuring faster produces nothing. Concretely, in yield order:
   - **(a) The inventory audit — every remaining wave's named tables against disk. ~1 hour, the highest-yield hour available.** Two waves have now confirmed the pattern; `elections.json` (7 bare dates) failed S4.5 the *identical* way it failed S3.7. This is not bad luck, it is structural, and it will keep eating waves until someone reads the disk.
   - **(b) Resolve the 2021 coverage collapse** (48,901 → 9,065 D statements; 177 → 54 per office; 276 → 167 offices; symmetric). It is a **factual question** — real behavior change or upstream `congress-press` regression? — that gates S4.1's half B, S4.2's cross-event arm, S4.3's CONFIRM and S4.7 entirely, and that sits **exactly on the A/B boundary of both `scotus-landmarks.json` and `shutdowns.json`**, so split-halves is currently testing coverage as much as time. **The program's primary robustness test is compromised until this is answered.** It outranks every new measurement.
   - **(c) Audit the existing card inventory** against the S4.2 lesson before publishing any of it.
   - **(d) Only then spec more hypotheses**, using S4.4's template: pre-registered speech act + time window, no reference table, K2-immune by construction.

**4. The one protocol amendment S4 earns, and it is cheap:** *the placebo must be run against the exact statistic that appears in the headline.* S4.2 placeboed the blame rate, headlined the outward share, and passed itself. S4.4 placeboed the thing it claimed and killed its own best number (holiday-eve 1.31× → inside the null band; 6% of random date sets beat it). That one rule separates the wave's two event studies, and it is the whole difference between the graveyard being the product and the graveyard being the output.

---

## WARNING — INSTRUMENT DEFECT: THE PROVENANCE SEAM (2026-07-16). Read before trusting any verdict above.

**`dwillis/congress-press` is a UNION OF TWO DATASETS**, distinguished by the record-level
`date_source` field. The `legacy` lane (a ProPublica import; `scraper: null, source: null`) runs 2001
through **2021-01-03 and stops forever** — the exact day the 117th Congress was seated. The `scraper`
lane begins ~2018-01 with 49 offices and accretes. The "2021 coverage collapse" is not behavior: it is
the union losing the legacy lane and being left holding a then-immature scraper.

**VERDICT: UPSTREAM-REGRESSION.** A cliff, not a slide — legacy runs at full strength through 2020-12
(4,691 records / 405 offices), 229 records in the 3-day 2021-01 stub, then zero. Distinct offices:
2020-12 = 462 -> 2021-01 = 312 -> 2021-02 = 191. **Both adversarial skeptics CONFIRMED it (0 of 2
refuted)**; one re-derived every load-bearing number directly from the 303 mirror files, deliberately
bypassing `harness.iter_statements` so no harness quirk could propagate.

### What it does to SPLIT-HALVES — the program's primary robustness control

The A/B boundary of `scotus-landmarks.json` (A=2013-2020, B=2022-2026) and `shutdowns.json` sits
**directly on the provenance seam**. Half A is ~95% legacy lane; half B is ~100% scraper lane.

> **The halves are not two time periods. They are two different instruments.**
> Split-halves has not been comparing 2013-2020 to 2022-2026 — it has been comparing ProPublica to a
> scraper, across a ~2.6x change in office coverage, a ~2x change in statements-per-office, and a
> **7.7-point shift in party mix (legacy D:R = 1.538, scraper D:R = 1.12)**.

Every "replicates in both halves" PASS survived a weaker test than advertised. Every FAIL may be
plumbing — **including S2.3, the reversal this ledger holds up as proof the control works.**

Disappearance is party-SYMMETRIC (vanish rate D 0.634 / R 0.635), so no party is preferentially
deleted — but the two lanes carry materially different party mixes over identical months, so any
cross-party number spanning the seam is confounded regardless.

### CORRECTION (2026-07-16, same session, after independent re-measurement)

**The two numbers above are WRONG. The conclusion is right and was UNDERSTATED.** Both errors are
mine: I lifted `legacy D:R 1.538 vs scraper 1.12 / 7.7-point shift` from a workflow agent's output
and wrote it into canon WITHOUT reproducing it — the exact failure this ledger spends its length
catching in others. A parallel session flagged the discrepancy; I re-measured the 303 mirror files
directly and confirm their reading.

**1. The corpus has THREE lanes, not two.** `date_source` values, counted over the full mirror:

| lane | records |
|---|---|
| `legacy` | 485,948 |
| `scraper` | 200,033 |
| **`page_html`** | **2,839** |

`page_html` (2014→2026) is small and it is the **most party-skewed lane in the corpus**. A
two-valued enum built from the "union of two datasets" framing above would have silently
mis-bucketed it — the isolation fix must be built against the field's REAL domain, not this
paragraph's guess. Credit to the parallel L1 session for catching it before the enum was written.

**2. The party-mix numbers do not reproduce, because the original comparison confounded era with
lane** — it compared legacy-in-half-A against scraper-in-half-B, which is the very confound the
finding is about. With **era held constant (2013-2020, half A)**:

| lane | D | R | D:R |
|---|---|---|---|
| `legacy` | 257,401 | 218,817 | **1.176** |
| `scraper` | 12,577 | 13,420 | **0.937** |
| `page_html` | 536 | 43 | **12.465** |

and in half B (2022-2026): `scraper` 1.302, `page_html` 1.829, `legacy` **absent** (it dies
2021-01-03).

**The lane effect is ~24 points of D:R ratio with era fixed (1.176 vs 0.937) — larger than the
7.7-point cross-era figure originally published, and measured under the correct control.** The
seam finding stands and hardens: half A is ~all legacy, half B is ~all scraper, so split-halves has
been comparing LANES, not eras. Every conclusion above survives; only the arithmetic was wrong.

**The lesson is the one this ledger already teaches, turned on its author:** a number that arrives
from an agent is a number nobody reproduced. Canon is not a place to launder an unverified figure.

### The two near-misses this caught

- **S4.3** — its pre-registered CONFIRM ("monotone volume decay") is satisfied by **the legacy
  import's death alone**. It was one run from publishing a data seam as a finding about political
  speech.
- **S4.7 (January 6) — a SIGN INVERSION, not an exaggeration.** Raw: **-69.9%** -> *"muted
  congressional response to January 6"*: maximally quotable, publishable, and **false**. Lane-isolated:
  **+75.5%**. Fixed-cohort: January 2021 is a local **maximum**. The 70% "drop" is the ProPublica
  import ending three days before. This is the closest OnScript has come to publishing a damaging
  falsehood, and only the review gate stopped it.

### Verdicts needing revisit: ALL 34

Every verdict that used split-halves as its control was validated against a boundary sitting on the
seam. Highest priority: **S2.3** (the flagship reversal — the kill may be false), **S1.9 + S2.9** (the
program's only two CONFIRMED; their both-halves validation was weaker than advertised, and S2.9 is the
ancestor SD.2 would extend onto CREC as the "twice-confirmed" tier), **S4.1** (its UNDERPOWERED verdict
is plausibly the artifact itself — half B has ~1/4 the statements per month for pure instrument
reasons), **S4.4** (an equivalence claim measured across two instruments is not equivalence).

### The remedy — LANE ISOLATION IN CODE, not normalization

A scale factor cannot repair a changing roster or a lane-dependent party mix. `date_source` must
become a first-class field: `harness.iter_statements` currently **drops it** (harness.py:399-427
projects only date/year/party/bioguide/state/chamber/congress). The rule is the deep archive's
genre-isolation law applied to provenance: **comparisons live within ONE lane, enforced in code.**

### The inventory — the remainder is in BETTER shape than S3/S4 implied

Of 18 un-adjudicated items: **8 RUNNABLE NOW**, 2 need a trivial offline parse, 7 gate on a single
keyless CREC crawl (~11-13h unattended), 1 needs the `crisis-events.json` that never existed.

**Two FALSE BLOCKS — the substrate landed while the ledger recorded it as absent:**

- **S1.12** ("blocked, needs a leadership roster") — the roster is ON DISK. `legislators-{current,
  historical}.json` carry `leadership_roles`: 156 dated bioguide-keyed rows, 33 titles, all 9 core
  titles filled for every congress 113-119. Mirrored 2026-07-16 by the D3-A academic lane — **one day
  after S1 ran and found the field null.** No acquisition; a ~30-min offline parse.
- **S5** ("keyed joins; the key never comes local") — **that premise is obsolete.** GovInfo BILLSTATUS
  113-119 is keyless and already local (56 zips / 332 MB / 9,709 bills in 117-hr alone) with sponsor
  bioguideId, introducedDate, policyArea, subjects. **S5.2 is runnable now with no key and no
  Actions.** congress.gov API is needed for nothing in S5.

**The elections.json disease, 2nd and 3rd instance:** `presidents.json` starts at Obama 2009 — no Bush
term — while the CREC data on disk is exactly 2001-2008 (the presidency it omits), and
`chambers-control.json` covers only 113-119, so 2 of SD.3's 5 named flips have no control coding.
Both are trivial offline edits; both are load-bearing.

**A p-hacking hole, found by the gate-reachability audit docs/12 never got:** S5.2's floor is literally
">=Floor per cell" — no number was ever pre-registered.

---

## RE-VALIDATION — WITHIN-LANE (2026-07-17, Opus Session 18; docs/17 brief). Append-only; supersedes named.

**The headline: the seam did not overturn a single measured verdict, and it hardened the two that
matter.** The runnable half of the 34 was re-measured inside ONE provenance lane on the brief's
pre-registered within-lane halves (propublica A=2013-16/B=2017-20; scraped A=2021-23/B=2024-26). Both
CONFIRMED findings survive — S2.9 is now genuinely **twice-confirmed** (once per lane on that lane's
own split), and S1.9 replicates identically whether or not the 144 legacy 2021-01-03 records are
included. The flagship reversal S2.3 stays REFUTED **in both lanes independently and well-powered in
every cell** — its kill was not plumbing. No runnable verdict flipped direction. One new within-lane
wrinkle appeared (S2.7 confirms inside propublica only, does not replicate → not a card).

**Substrate rebuilt first (docs/17 §3):** `text_features.jsonl` was regenerated with the L1 lane
fields (`ds`/`inst`) — the on-disk cache dated 2026-07-16 01:58 predated L1 and every S2 re-run on it
would have been lane-blind. 674,905 rows: legacy 475,315 / scraper 196,753 / page_html 2,837. Its
lane split sums EXACTLY to the pre-seam totals (concern-ladder 39,249 / 5,808 / 650 / 2,084), which is
the migration's correctness proof.

### Classification of the 34 (docs/17 §3 — the required ledger artifact)

| ID | old verdict | class | this session |
|----|-------------|-------|--------------|
| S1.9 | CONFIRMED | RUNNABLE-WITHIN-LANE | re-affirmed CONFIRMED (both full-117 and scraped-only) |
| S2.9 | CONFIRMED | RUNNABLE-WITHIN-LANE | re-affirmed CONFIRMED in BOTH lanes = twice-confirmed |
| S2.3 | REFUTED | RUNNABLE-WITHIN-LANE | REFUTED in both lanes, well-powered — kill was NOT plumbing |
| S2.1 | REFUTED→REV | RUNNABLE-WITHIN-LANE | REFUTED both lanes (medA/medB negative both) |
| S2.2 | REFUTED | RUNNABLE-WITHIN-LANE | REFUTED both lanes (n_tripled < 3) |
| S2.4 | DESCRIPTIVE | RUNNABLE-WITHIN-LANE | DESCRIPTIVE both lanes; firsts now reported per-lane |
| S2.5 | REFUTED | RUNNABLE-WITHIN-LANE | REFUTED both lanes (no ≥50% decline) |
| S2.6 | REFUTED | RUNNABLE-WITHIN-LANE | REFUTED both lanes |
| S2.7 | REFUTED | RUNNABLE-WITHIN-LANE | **propublica CONFIRMED / scraped REFUTED** — single-lane, not robust |
| S2.10 | REFUTED | RUNNABLE-WITHIN-LANE | REFUTED both lanes ("alarmed" breaks ordering in both) |
| S2.12 | REFUTED | RUNNABLE-WITHIN-LANE | REFUTED both lanes (flat rate) |
| S1.4 (verbatim) | REFUTED | RUNNABLE-WITHIN-LANE | REFUTED both lanes; "D rises both halves" sub-claim does NOT survive |
| S1.4 (_proper, density) | REFUTED-asym | BLOCKED-ON-SHARDS | `load_congress_records` is lane-blind — not re-run |
| S1.10 | ARTIFACT | RUNNABLE-WITHIN-LANE | ARTIFACT holds (placebo 7/7) after dropping the seam-straddling 2020 cycle |
| S4.1 (per-case) | DESCRIPTIVE | RUNNABLE-WITHIN-LANE | DESCRIPTIVE stands; half-A cases are ~95% propublica + 5% scraped tail → needs half-A isolation |
| S4.1 (aggregate) | UNDERPOWERED | NEEDS-RESCOPE | the A(−1)/B(+1) direction reversal IS the seam (half A propublica, half B scraper); already dead |
| S4.2 | REFUTED | RUNNABLE (seam not the cause) | died on placebo methodology (3/3 skeptics), not the seam — stands |
| S4.4 | REFUTED | RUNNABLE (halves ARE the lanes) | half A=propublica, half B=scraper; equivalence holds WITHIN each lane → stands, arguably strengthened |
| S1.1, S1.1′, S1.2, S1.3, S1.3′, S1.5, S1.6, S1.7, S1.8, S1.11 | (various) | BLOCKED-ON-SHARDS | read phrase_index/daily_series/member_index/discipline; alexandria shards lane-blind until the ~3GB shard rebuild (its own session). NOT re-run on lane-blind substrate. |
| S3.1–S3.7 | 5 BLOCKED, S3.4 REFUTED, S3.6 UNDERPOWERED | BLOCKED-ON-SOURCE | never produced a seam-validated number (blocked on absent reference tables); seam-status moot |
| S4.3, S4.5, S4.6, S4.7, S4.8 | BLOCKED | BLOCKED-ON-SOURCE / REVIEW-GATED | absent `crisis-events.json`/`elections.json` results; S4.7 is the standing Jan-6 sign-inversion proof — unchanged |

### The runnable verdicts (append-only rows; `supersedes` = the pre-seam row)

| ID | new verdict | headline (within-lane) | lanes / halves | floors (numerals) | script | supersedes |
|----|-------------|------------------------|----------------|-------------------|--------|------------|
| S2.3 | **REFUTED (both lanes)** | propublica A: D 3/3 R 1/3, B: D 0/3 R 2/3. scraped A: D 2/3 R 1/3, B: D 3/3 R 1/3. Pooled-within-lane gate FALSE in both. Never ≥2 for BOTH parties in any half. | propublica 2013-16/2017-20; scraped 2021-23/2024-26 | ≥200 stmts per (half×party×status); smallest cell 5,520 | `scripts/search/revalidate_s2_3.py` | L106/L290 S2.3 |
| S1.9 | **CONFIRMED (re-affirmed)** | full-117: D 0.00176 vs R 0.00095, 75/105 wk (71%). scraped-only (144 legacy 2021-01-03 dropped): D 0.00200 vs R 0.00119, 75/105 (71%). Identical verdict. | scraped (congress 117 is 99.6% scraped; exclusion is a no-op) | ≥20 matched weeks each party; got 105 | `scripts/search/revalidate_s1_9_s2_9.py` | L69 S1.9 |
| S2.9 | **CONFIRMED (twice-confirmed)** | propublica half A 4/4 + half B 4/4; scraped half A 3/3 + half B 3/3. Reimpl reproduces the original 14/14 = propublica-8/8 + scraped-6/6 across the old seam split (faithfulness check). | propublica 2013-16/2017-20; scraped 2021-23/2024-26 | out>in every year in both halves | `scripts/search/revalidate_s1_9_s2_9.py` | L109 S2.9 |
| S2.1 | REFUTED (both lanes) | medA/medB opp-minus-own euphemism-avoidance: propublica −0.033/−0.012, scraped −0.081/+0.007 (need ≥0.10 both) | both lanes | — | `scripts/search/revalidate_s2_wave.py` | L99 S2.1 |
| S2.2 | REFUTED (both lanes) | tripled words: propublica D1/R0, scraped D0/R0 (need ≥3 both parties) | both lanes | — | `revalidate_s2_wave.py` | L100 S2.2 |
| S2.4 | DESCRIPTIVE (both lanes) | firsts + exclamation trend, per-lane | both lanes | — | `revalidate_s2_wave.py` | L101 S2.4 |
| S2.5 | REFUTED (both lanes) | propublica rose +26% (dir A+1 B+1), scraped dir A−1 B+1 drop 14% — no ≥50% decline either lane | both lanes | ≥2 yrs each half | `revalidate_s2_wave.py` | L102 S2.5 |
| S2.6 | REFUTED (both lanes) | words/sentence: no both-halves both-parties directional agreement in either lane | both lanes | — | `revalidate_s2_wave.py` | L107 S2.6 |
| S2.7 | **propublica CONFIRMED / scraped REFUTED** | I/(I+we) declines in both propublica halves for both parties (D −1/−1, R −1/−1); scraped disagrees (R +1 then... mixed). Single-lane confirm — does NOT replicate → **reversal candidate, needs re-pre-registration (parallel-session protocol), NOT a finding card.** | both lanes | ≥3 yrs each half | `revalidate_s2_wave.py` | L103 S2.7 |
| S2.10 | REFUTED (both lanes) | "alarmed" breaks the concern ladder in BOTH lanes (propublica 1,401 > gravely 434; scraped 683 > 216) | both lanes | — | `revalidate_s2_wave.py` | L104 S2.10 |
| S2.12 | REFUTED (both lanes) | apologies propublica 954 / scraped 244; rate flat, no era trend either lane | both lanes | ≥100 apologies (propublica passes, scraped 244 passes) | `revalidate_s2_wave.py` | L105 S2.12 |
| S1.4 (verbatim) | REFUTED (both lanes) | propublica D_A+1/D_B−1, R_A+1/R_B+1; scraped D_A+1/D_B−1, R_A−1/R_B−1. No lane has both parties rising in both halves. **The "D rose in both halves" claim was the seam.** | both lanes | ≥200 stmts/party/yr | `scripts/search/revalidate_s1_4_s1_10.py` | L68 S1.4 |
| S1.10 | ARTIFACT (robust) | real troughs 5/5, placebo troughs 7/7 → seasonal not electoral; 2020 real cycle dropped (window 2020-08-06..2021-02-02 straddles seam); no placebo cycle straddles | lane=None, per-cycle single-lane after drop | ≥4 real cycles (got 5) | `revalidate_s1_4_s1_10.py` | L71 S1.10 |
| S4.4 | REFUTED (stands; halves = lanes) | half A (2013-2020) = propublica, half B (2021-2026) = scraper; the 0.85×/0.96× equivalence is a within-lane null measured once per instrument, not a cross-instrument comparison | de-facto per-lane | as original | `pipeline/search/wave_s4.py` (Friday-dump path) | L292 S4.4 |
| S4.2 | REFUTED (stands; seam not the cause) | killed by placebo-run-against-the-headline (3/3 skeptics); the seam is not why it died | n/a | n/a | (unchanged) | L291 S4.2 |
| S4.1 | DESCRIPTIVE per-case / UNDERPOWERED aggregate (stands) | per-case survives; half-A cases carry a ~5% scraped tail (needs isolation), aggregate A/B reversal is the seam & already dead (half B 5<8) | per-case single-event | ≥8 qualifying/half (A=9, B=5) | `pipeline/search/wave_s4.py::run` (`_collect` now carries `ds`/`inst`) | L290 S4.1 |

### What changed in code (docs/17 §4.4 — migrate call sites as re-run)

- `pipeline/search/wave_s2.py`: module-level seam-spanning `HALF_A`/`HALF_B` removed; `LANE_HALVES` +
  `halves_for()` + `load_rows(lane)` (rejects a pre-L1 cache loudly); every S2 entry point takes
  `*, lane[, halves]`; `run_all()` returns `{lane: [...]}`. The lane-blind `_load()` is gone.
- `pipeline/search/wave_s1.py`: `s1_4_verbatim` and `s1_10_bipartisan_season` gained `lane=`;
  `s1_9_self_audit` gained `lane=` (144 legacy 2021-01-03 records confirmed non-load-bearing);
  `LANE_YEAR_HALVES` added; S1.10 now drops seam-straddling cycles via `provenance.spans_seam`.
- `pipeline/search/wave_s4.py`: `_collect` now carries `ds`/`inst` per matched statement (it reads the
  raw mirror directly, so it dropped `date_source` before) — future S4 event studies can isolate.
- `tests/test_search_provenance.py`: +5 tests (load_rows isolation/fold/pre-L1-refusal, `_half`
  requires halves, halves never span the seam). **259 suite tests green.**

### Two things the brief asserted that the measurement corrected (filed, docs/17 §7)

1. **"S1.9 is lane-clean by construction" is 99.6%, not 100%.** Congress 117 contains 144 ProPublica
   records dated exactly 2021-01-03 (the import's last day == the 117th's first day). The exclusion is
   a measured no-op (verdict, weeks-matched, and D>R count all identical), so the finding is unmoved —
   but "by construction" overstated it; it is "clean after excluding 144 records, which changes
   nothing."
2. **`confirms_in_both_halves` — the L1-guarded CONFIRM gate — is not reachable from any production
   code path.** Only tests call it; every wave module (S1 and S2) hand-rolls both-halves via
   `M.split_direction`, which has NO lane guard. So the Session-16 gate protects a function the
   measurement path never touches, and an un-migrated wave site fails **silently** (lane-blind
   numbers), not loudly as docs/17 §4.4 assumes. This session migrated the S2 + the runnable-S1 sites
   to `load_rows(lane)`/explicit halves so their isolation is real; the BLOCKED-ON-SHARDS sites remain
   un-migrated and must not be trusted until the shard rebuild reaches them.

---

## SHARD-LANES RE-VALIDATION — the eleven BLOCKED-ON-SHARDS items, WITHIN one lane (2026-07-17, Opus Session 19; docs/18 brief). Append-only; supersedes named.

Session 18 refused to run these eleven on the lane-blind alexandria shards. Per-lane shards now exist
(`ALEX/lanes/`, built by `scripts/search/build_lane_shards.py`, PYTHONHASHSEED-pinned), the harness is
lane-aware (lane-suffixed caches), and each hypothesis reads a lane-isolated substrate on that lane's
within-lane halves (docs/18 §5). Driver: `scripts/search/revalidate_s1_shards.py`. Floors are the
hypotheses' own pre-registered gates, applied per-lane (L4).

**Shard acceptance (docs/18 §3):** congress 117 raw partition EXACT (propublica 144 + scraped 36,773 =
36,917 combined; 0 statement delta; 0 cross-lane id-dups). `run_shard(n, lane=None)` is
content-deterministic and leaves the live combined shards untouched (§3.4, reframed — the on-disk
combined shards are a stale baseline: the ledger's key order is per-process randomized via
`_doc_ngrams`' set iteration, harmless to analysis because the Search readers stream all entries).
107-112 per-lane loaders RAISE.

### SCRAPED lane (congresses 117-119; year-halves 2021-23 / 2024-26; congress-halves {117}/{118,119})

| ID | new verdict | headline (within scraped lane) | vs Session-18/original | floors |
|----|-------------|--------------------------------|------------------------|--------|
| S1.1 | **ARTIFACT** (stands) | odd/even congress-boundary sawtooth INSIDE the lane: series 2021:60, 2022:0, 2023:60, 2024:15, 2025:60, 2026:1 (`artifact_guard=True`) | unchanged — proves the sawtooth is a per-shard artifact INDEPENDENT of the seam | min_cell 8; guard >5× odd/even |
| S1.3 | **ARTIFACT** (stands) | same sawtooth (2021:640, 2022:115, 2023:596, 2024:16, 2025:365, 2026:56; `artifact_guard=True`) | unchanged — seam-independent congress-boundary + censoring artifact | min_cell 8 |
| S1.1′ | **ARTIFACT** (coverage) | bursts shrink both halves (dir −1/−1, ratio 2.0) but **does NOT survive the density control** (`density_survives=False`) → coverage artifact | original REFUTED (industrialized-then-plateaued, 2013-26). WITHIN 2021-26 alone there is no clean ignition-speed trend — the "Great Intensification" was a **propublica-era (2013→2020) phenomenon** (to confirm when propublica runs) | min_cell 8; ≥2 powered yrs/half |
| S1.3′ | **ARTIFACT** (coverage) | bursts noisy (25,12,23,26,52,24), median_drop −0.13 (lifespan rose), dir −1/−1 but `density_survives=False` | original REFUTED. Same read: no within-scraped lifespan-collapse; it lived in the propublica era | min_cell 8 |
| S1.2 | **REFUTED** (stands) | normalized sync ceiling DECLINES both halves (dir −1/−1, ratio 0.457 — hypothesis wanted rising ≥1.5×) | consistent with original "peaked ~2017, declined"; within scraped it keeps falling | ≥2 yrs/half |
| S1.5 | **REFUTED** (stands) | Saturday avoided (excess 0.64/0.91) but **Sunday over-represented 7.1×/2.4×** → not weekend-avoidant | consistent — the Sunday spike, within lane | ≥30 ignitions/half |
| S1.6 | **UNDERPOWERED** (lane cost) | only 1 election cycle per half in the scraped lane (2022 in A, 2024 in B); tally 1/1 every cell (<2 floor) | the honest cost of isolation — the electoral-cycle gate needs cycles from both eras | ≥2 cycles/half/party |
| S1.7 | **REFUTED** (stands) | August ignition rate = **52% of session rate** (half A); half B has no August ignitions | consistent — coordination roughly halves in recess, within lane | ≥200 Aug stmts/half |
| S1.8 | **REFUTED** (stands) | SOTU-day unison half-life FLAT (dir 0/0, drop 0.0) | consistent — no half-life collapse within scraped | ≥2 yrs/half |
| S1.11 | **REFUTED** (stands) | same-state echo ratio A **1.68** / B **1.03** (needs ≥1.5 BOTH halves) — half A shows some regional echo, B none | original REFUTED (1.01/1.09); within scraped half A is higher but B kills it | ≥30 phrases/half |
| S1.4 (_proper) | **UNDERPOWERED** (gate unmeetable in-lane) | the congress-split both-halves gate needs ≥3 congresses/half; scraped has **1** (half A={117}) and 2 (half B={118,119}) → every direction None. Not a REFUTE — a false negative if reported so (cf. S3.6) | the year-keyed verbatim floor (S1.4-verbatim, Session 18) is the runnable within-lane form; REFUTED there | ≥3 congresses/half (unreachable) |

**Scraped-lane read:** 5 REFUTED-stands, 2 ARTIFACT-stands (S1.1/S1.3 — proving the sawtooth is NOT the seam), 2 ARTIFACT-coverage (S1.1′/S1.3′ — the intensification story is absent within 2021-26, so it was a propublica-era effect), 2 UNDERPOWERED (S1.6 electoral cycles, S1.4-proper congress-split — both honest lane-isolation costs, not failures). **Zero verdicts flipped toward a false positive.**

### PROPUBLICA lane (congresses 113-116; year-halves 2013-16 / 2017-20; congress-halves {113,114}/{115,116})

**THE HEADLINE: two new within-lane CONFIRMED — the "Great Intensification" is real, confirmed inside
the instrument that measured it, and it stopped at the seam.** S1.1′ and S1.3′ were REFUTED across the
2013-2026 seam split (the post-2021 plateau broke the monotone gate). Isolated to the propublica lane
(2013-2020) on the brief's pre-registered within-lane halves (docs/18 §5), the SAME hypotheses and the
SAME gate CONFIRM — and they are ARTIFACT/absent in the scraped lane. Lane isolation did not weaken
these findings; it is what made them confirmable.

| ID | new verdict | headline (within propublica lane) | vs original | floors |
|----|-------------|-----------------------------------|-------------|--------|
| S1.1 | **ARTIFACT** (stands) | odd/even congress-boundary sawtooth inside the lane (`artifact_guard=True`) | unchanged — same per-shard artifact, seam-independent | min_cell 8 |
| S1.3 | **ARTIFACT** (stands) | same sawtooth (`artifact_guard=True`) | unchanged | min_cell 8 |
| **S1.1′** | **CONFIRMED ✅** | ignition width **34d (2013) → 3d (2020)**, series 34,13,8,12 / 6,12,3,3; dir A −1, dir B −1; **ratio 11.33×** (≥1.5); **density_survives=True**; no sawtooth. Cells 928–12,548 bursts/yr | **original REFUTED (across seam) → CONFIRMED within propublica.** The memo industrialized ~11× through the 2010s | dir<0 both halves; ratio≥1.5; density-survives |
| **S1.3′** | **CONFIRMED ✅** | burst lifespan **55.5d (2013) → ~15d (2020)**, series 55.5,32,29,31 / 24.5,35,10,15; dir A −1, dir B −1; **drop 37.3%** (≥30%); **density_survives=True** | **original REFUTED → CONFIRMED within propublica.** Talking-point flare duration collapsed 37% | dir<0 both halves; drop≥30%; density-survives |
| S1.2 | **REFUTED** (stands, +peak) | normalized sync ceiling 0.228 (2013) → **0.330 (2017, peak)** → 0.250 (2020); dir A +1, dir B −1, ratio 1.09 | consistent — REFUTED against "monotone rising", and it **shows the 2017 peak-and-fall** within the lane | ≥2 yrs/half |
| S1.5 | **REFUTED** (stands) | weekend-avoidance not both days (Sunday over-represented) | consistent | ≥30 ignitions/half |
| S1.6 | **REFUTED** (powered now) | snap tally A-D 1/2, A-R 1/2, **B-D 2/2, B-R 2/2** — 2018/2020 snap, 2014/2016 don't; fails all-cells-majority (half A) | **now POWERED** (2 cycles/half, unlike scraped) — confirms the original "pre-election tightening is a RECENT-cycle phenomenon" | ≥2 cycles/half/party |
| S1.7 | **REFUTED** (stands) | August ignition rate craters vs session | consistent | ≥200 Aug stmts/half |
| S1.8 | **REFUTED** (stands) | SOTU half-life not declining | consistent | ≥2 yrs/half |
| S1.11 | **REFUTED** (stands) | same-state echo ratio A 0.94 / B 0.94 (<1.5) — no regional echo | consistent (original 1.01/1.09) | ≥30 phrases/half |
| S1.4 (_proper) | **UNDERPOWERED** (gate unmeetable) | congress-split gate needs ≥3 congresses/half; propublica has 2 ({113,114}/{115,116}) → directions None | the year-keyed verbatim floor (Session 18) is the runnable form | ≥3 congresses/half (unreachable) |

**Propublica-lane read:** **2 CONFIRMED** (S1.1′/S1.3′ — the intensification, real and within-lane), 6
REFUTED-stands (S1.2 also surfacing the 2017 sync peak; S1.6 now powered, confirming recent-cycle
tightening), 2 ARTIFACT-stands (S1.1/S1.3 sawtooth), 1 UNDERPOWERED (S1.4-proper). Zero false positives.

### The both-lanes picture — the eleven, re-validated

| ID | propublica | scraped | reading |
|----|-----------|---------|---------|
| S1.1 | ARTIFACT | ARTIFACT | congress-boundary sawtooth in BOTH lanes → proven seam-independent (a per-shard artifact) |
| S1.3 | ARTIFACT | ARTIFACT | same |
| **S1.1′** | **CONFIRMED** | ARTIFACT-coverage | **the intensification is a 2013→2020 phenomenon that STOPPED at the seam** |
| **S1.3′** | **CONFIRMED** | ARTIFACT-coverage | same — flare-duration collapse was a 2010s effect, absent 2021-26 |
| S1.2 | REFUTED (2017 peak) | REFUTED (declining) | sync ceiling peaked ~2017 and fell — consistent both lanes |
| S1.5 | REFUTED | REFUTED | Sunday spike, both lanes |
| S1.6 | REFUTED (powered) | UNDERPOWERED | pre-election tightening is recent-cycle; scraped has too few cycles to test |
| S1.7 | REFUTED | REFUTED | August coordination craters, both lanes |
| S1.8 | REFUTED | REFUTED | no SOTU half-life collapse, both lanes |
| S1.11 | REFUTED | REFUTED | no regional delegation echo, both lanes |
| S1.4 (_proper) | UNDERPOWERED | UNDERPOWERED | congress-split gate unmeetable in either lane (≥3 congresses/half); the verbatim floor (Session 18) is the runnable form, REFUTED both lanes |

**Publication gate (NOT a build-session act):** S1.1′/S1.3′ are REFUTED→CONFIRMED movements. Although
the within-lane halves were PRE-REGISTERED in docs/18 §5 (so this is not a p-hacked reversal — the
gate and hypothesis are unchanged, only the substrate is now lane-isolated), a REFUTED→CONFIRMED
finding must clear Fable + neutrality review before it becomes a published card/article, and the
density control's caveat (it matches burst COUNT, not within-day statement density — a denser day can
still peak a phrase faster) must be disclosed on any card. The `data/derived/findings/GREAT-INTENSIFICATION.json`
narrative card already exists as a banked reversal candidate; these two CONFIRMEDs are its within-lane
evidence, now on the correct (isolated) substrate.

### SHARD-LANES tally

| item | count |
|---|---|
| eleven re-validated in BOTH lanes | 11 |
| new within-lane CONFIRMED | **2 (S1.1′, S1.3′, propublica)** — pending publication review |
| ARTIFACT-stands (seam-independent) | 2 (S1.1, S1.3, both lanes) |
| REFUTED-stands | S1.2, S1.5, S1.7, S1.8, S1.11 (both lanes); S1.6 (propublica) |
| UNDERPOWERED (honest lane cost) | S1.6 (scraped), S1.4-proper (both lanes) |
| verdicts flipped toward a FALSE POSITIVE | **0** |

Reconciliation (docs/18 §3): all 7 congresses EXACT raw partition, 0 statement delta, 0 cross-lane
id-dups. Program CONFIRMED tally moves from 2 (S1.9, S2.9) to **4 pending review** (+S1.1′, +S1.3′).
Scripts: `scripts/search/{build_lane_shards,revalidate_s1_shards}.py`; results
`data/derived/search/revalidate_s1_shards.json`.

## NOMENCLATURE-ROBUSTNESS RIDER (docs/19 §4, Opus 2026-07-18) — all three exposed findings SURVIVE tag-stripping

The three nomenclature-exposed CONFIRMED findings count phrase / n-gram co-use, and docs/16's core
insight is that bill titles manufacture co-use. Per docs/19 §4 they were re-run on **tag-stripped
substrate** — the pre-registered gate and within-lane halves unchanged, only nomenclature spans
removed. **Every one holds; the bursts finding is if anything sharper without bill titles.** These
rows `supersede` nothing — they ADD a robustness dimension to the same verdicts (the CONFIRMEDs stand,
now also nomenclature-robust).

| id | metric | baseline | tag-stripped | expectation (pre-registered) | verdict |
|---|---|---|---|---|---|
| **S1.9** | weekly 5-gram overlap, c117 scraped; exclude 5-grams overlapping a name span | D 0.00200 vs R 0.00119, D>R 75/105 wk (71%) | D 0.00189 vs R 0.00117, D>R 72/105 wk (68%) | D>R AND ≥60% of matched weeks | **HOLDS** — CONFIRMED both |
| **S1.1′** | ignition width, propublica; drop nomenclature phrases (364/25188 = 1.4%) | dir −/−, ratio 11.33, density✓ | dir −/−, ratio **12.0**, density✓ | dir<0 both halves + density-survives | **HOLDS** — ratio rose |
| **S1.3′** | burst lifespan, propublica; same phrase drop | dir −/−, drop 0.373, density✓ | dir −/−, drop **0.381**, density✓ | dir<0 both halves + density-survives | **HOLDS** — drop rose |

S2.9 EXEMPT (a president's name is not bill nomenclature). Only 1.4% of propublica phrases were
nomenclature, and removing them did not weaken the intensification — the ratio/drop both rose slightly,
so the finding is NOT an artifact of two offices independently naming the same bill. Dropped examples
(correct): "authorization for use of military force", "keep your health plan act", "the central
intelligence agency", "federal law enforcement". Tag-strip mechanism: `_fivegrams(strip_idx=…)` (5-gram
overlap) + `nomenclature.name_spans`/`classify_occ` (phrase drop). Re-runnable:
`scripts/search/revalidate_nomenclature_rider.py`; results
`data/derived/search/revalidate_nomenclature_rider.json`. **This clears the docs/19 §4 gate on the
Aug/Sep drip pieces (docs/20); the S1.1′/S1.3′ publication still needs the standing Fable + neutrality
review for any REFUTED→CONFIRMED movement, with the density caveat disclosed.**

## NEW MEASUREMENTS (2026-07-19, Opus Session 26) — S1.12 run within-lane; S3.7 registered + blocked

Append-only. Two of the three false-blocks the substrate audit found (docs/13:504-513) are addressed:
**S1.12 is no longer blocked — it is REFUTED**; **S3.7 is registered and half-acquired but the House
data is guestbook-gated** (a block the earlier "keyless CC0" verification missed).

### S1.12 · Leadership Ignites, Backbenches Amplify — REFUTED (both lanes)

**The folk theory is false at the pre-registered gate.** Big talking points do NOT disproportionately
originate in leadership offices: core-leadership offices (Speaker/Leaders/Whips × chamber, the 9
titles) first-say major ignitions at **0.8–1.6× their share of press-release volume — never the ≥3×
the theory requires, and not stable across halves.**

| lane | half | ignitions (N≥20 peak) | leadership first-say | statement share | RATIO | powered (N≥50, μ₀≥3) |
|---|---|---|---|---|---|---|
| propublica (2013-20) | A 2013-16 | 2,460 | 2.76% | 3.37% | **0.82×** | ✓ (μ₀=83) |
| propublica (2013-20) | B 2017-20 | 12,702 | 4.09% | 4.62% | **0.89×** | ✓ (μ₀=587) |
| scraped (2021-26) | A 2021-23 | 1,510 | 6.42% | 3.99% | **1.61×** | ✓ (μ₀=60) |
| scraped (2021-26) | B 2024-26 | 844 | 3.79% | 4.01% | **0.95×** | ✓ (μ₀=34) |

**Verdict per lane: REFUTE** (well-powered in all four cells; ratio never ≥3.0, and the scraped lane's
halves disagree 1.61×→0.95× so not even "stable" in the pro-theory direction). **Robust across every
pre-registered variant:** 33-title leadership set (0.82/0.84/1.50/0.83), boilerplate-excluded
(0.82/0.89/1.61/0.95 ≈ identical). **One variant points differently and is the honest nuance:**
tie-inclusive first-sayer (leadership counted if it is ANY day-0 co-sayer, not only the designated
first) runs **2.22 / 2.67 / 2.36 / 1.92×** — leadership offices ARE over-represented among the earliest
co-signers, but **even this never reaches 3×.** So the defensible reading is *coordination looks like
simultaneous day-0 emergence with leadership over-present as a co-signer, NOT top-down broadcast where
leadership authors and backbenches parrot.* (The "leadership co-launches" angle is an OBSERVATION, not
a pre-registered claim — it would need its own registration and a day-precision-tie caveat before it
could be a card.) Publishable NULL, docs/20 graveyard/methods shelf; symmetric by construction (one
rule, both parties, both lanes).

**Substrate / false-block resolved:** `leadership_roles` from
`X:/onscript-data/academic_archive/raw/roster/legislators-{current,historical}.json` — 156 dated rows,
33 titles, 9 core filled every congress 113-119. S1 recorded the field null one day before this landed
(docs/13:506). **Pre-registration frozen in the script header BEFORE measuring** (F1 peak≥20; F2 the
9-core set; F3 power N≥50 ∧ μ₀≥3; F4 CONFIRM ratio≥3.0 both halves). The only post-first-run edit was a
plumbing fix (`iter_statements` returns `year` as a string → cast to int) that made the baseline
non-empty; **no floor was tuned after a ratio was visible** (the first run's baseline was 0/nan, so no
ratio existed to tune toward). Re-runnable: `PYTHONHASHSEED=0 python scripts/search/s1_12_leadership.py`;
results `scripts/search/evidence/s1_12_leadership.result.json`. **Supersedes the Wave-S1 "S1.12 blocked"
status.**

### S3.7 · The Safe-Seat Vessel Test — REGISTERED; BLOCKED on the House guestbook (Senate half local)

**The "keyless CC0 pure build act" premise (You-are-here #157 / brief §2.2, verified 2026-07-18 via
`fileAccessRequest:false`) is TRUE for the Senate file and FALSE for the House file.** The verification
checked the license + access-request flag but not the **guestbook**: the House returns file
(`doi:10.7910/DVN/IG0UN2`, `1976-2024-house.tab`) sits behind a **required Dataverse Guestbook
(guestbookID 458)**. `?gbrecs=true` does not bypass a *required* guestbook; the only API path POSTs a
guestbook response (name/email/institution = personal data), which a session must not fabricate. **This
is the elections.json disease inverted a THIRD time (cf. #157): last time the assumed blocker was
imaginary; this time an unnoticed blocker is real.** Errand **#177** filed (Michael downloads the House
`.tab` via the Dataverse UI — the guestbook wants an identity, his call). The **Senate** file
(`doi:10.7910/DVN/PEJ5QU`, `1976-2024-senate-state.tab`, CC0, ungated) is downloaded and local at
`X:/onscript-data/elections/raw/`.

**Pre-registration (frozen NOW, before any measurement — registration-before-data, docs/12 discipline):**
unit = member (bioguide); MoV = (winner − runner-up)/total votes per member per cycle (MEDSL →
bioguide via roster `terms` on state·district·year·party); **script participation** = the concordance
on-script index (`build.build_concordance`, `PEAK_FLOOR=15`, `MIN_STATEMENTS=10`). Test = **member-level
Spearman ρ(MoV, concordance) WITHIN chamber** (never pooled across chambers — the #143 chamber trap),
within-lane halves (docs/17). **CONFIRM iff |ρ|≥0.20 ∧ p<0.05 ∧ same sign in both halves** (either
direction: safety→more script = assimilation, safety→less = free voice); **REFUTE iff |ρ|<0.20 in a
well-powered cell** (the publishable null — "safety neither frees nor assimilates the voice"). **Power
floor: a chamber·lane·half cell reports a verdict only with ≥100 members carrying both a MoV and a
concordance score.** This floor is exactly why the Senate half is NOT run alone: ~100 senators total,
split by chamber·lane·half, cannot clear ≥100/cell — **the powered run genuinely needs the House**, so
no partial/underpowered verdict is forced. Aggregate quintile-mean plot is the artifact; **no
member-level "vessel" leaderboard** (the R2/#143 ruling). **Verdict: BLOCKED-ON-HOUSE-GUESTBOOK.**

### S3.7 · The Safe-Seat Vessel Test — **REFUTED** (both runnable lanes / House; Senate underpowered as pre-registered). *Supersedes the BLOCKED-ON-HOUSE-GUESTBOOK row above.*

**#177 closed → the House `.tab` is local; S3.7 ran EXACTLY as registered — no knob, floor, or rescope
added.** The publishable null: **a member's seat safety neither frees nor assimilates their party
voice.** Across all four well-powered House cells the on-script index is flat over the margin-of-
victory distribution (|ρ| ≤ 0.12, every one below the pre-registered 0.20 effect-size gate).

**Step 1 — the reference table** (`data/reference/search/mov-by-member.json`, committed; builder
`scripts/search/build_mov_table.py`). MEDSL House (comma-delimited) + Senate (tab-delimited, float vote
counts — a bare `int()` silently zeroed every Senate contest until caught) 1976–2024 → one winner/margin
per decided general contest: votes aggregated by candidate across party lines + modes (fusion-safe),
MoV = (winner − runner-up)/Σcandidatevotes, regular + deciding runoff, **specials split from regulars in
the contest key** (else OK-2014 Inhofe/Lankford merge into one fabricated margin). Joined to bioguide via
`congress-legislators terms` (type·state·district·party, term start = cycle+1; special also cycle),
**disambiguated by winner surname** (the incumbent-vs-successor tie the raw seat·year key can't resolve —
LA-5 Alexander→McAllister, MA-Sen Warren vs interim Cowan/Markey). **Join AUDITED before use: 3288/3290 =
99.9%** (House **100.0% every cycle 2012–2024**; Senate 90.9–100%; matched via 3244 unique / 39 surname /
5 surname+date / **0 party-relaxed** — independents King & Sanders matched exactly). The **2 unmatched are
the GA 2020/21 dual-runoff** (Perdue lost his runoff → no term; Ossoff's runoff is coded to an odd year) —
an honest ~1-senator gap, not a defect. MoV ∈ [0,1], median 0.272, 65 uncontested (=1.0). Full unmatched
detail: `X:/onscript-data/elections/derived/mov-audit-detail.json`.

**Step 2 — the test** (`scripts/search/s3_7_safe_seat.py`; evidence
`scripts/search/evidence/s3_7_safe_seat.result.json` + X: copy). Per lane-half the on-script index was
built with `build.build_concordance(PEAK_FLOOR=15, MIN_STATEMENTS=10)` over lazily-normalized per-congress
solo Lane-1 statements — **read-only, no production write** (`out_dir=None`; kept set = the committed
per-lane `phrase_index` peak≥15, `peak`≡`peak_units` verified in `pipeline/phrases.py`). MoV reduced per
member per window = **mean over the member's cycles whose seated term overlaps the window** (House 2-yr /
Senate 6-yr; rank-inert, disclosed — not a registered knob). Member-level Spearman ρ(MoV, index) WITHIN
chamber.

| chamber·lane·half | window | n | ρ | p | powered (≥100) | cell |
|---|---|---|---|---|---|---|
| House·propublica·A | 113–114 (2013–16) | 399 | **+0.004** | 0.94 | ✓ | null |
| House·propublica·B | 115–116 (2017–20) | 510 | **−0.041** | 0.36 | ✓ | null |
| House·scraped·A | 117 (2021–22) | 226 | **−0.107** | 0.11 | ✓ | null |
| House·scraped·B | 118–119 (2023–26) | 422 | **−0.122** | 0.012 | ✓ | null |
| Senate·scraped·A | 117 | 27 | −0.110 | 0.59 | ✗ | underpowered |
| Senate·scraped·B | 118–119 | 93 | −0.058 | 0.58 | ✗ | underpowered |
| Senate·propublica·A/B | — | 0 | — | — | ✗ | no cell (corpus carried **2** senators in the 2013–16 legacy lane) |

Floors (numerals, frozen): PEAK_FLOOR **15**, MIN_STATEMENTS **10**, effect gate |ρ|≥**0.20**, p<**0.05**,
power **100** members/cell. Halves: propublica 113–114/115–116, scraped 117/118–119 (docs/17 §2).
**Adjudication:** house.propublica REFUTE (+0.004/−0.041), house.scraped REFUTE (−0.107/−0.122),
senate.scraped UNDERPOWERED → **overall REFUTE.**

- **The registered quintile artifact is FLAT** in every powered cell (Q1 competitive → Q5 safest mean
  concordance, e.g. scraped·A 0.691/0.719/0.709/0.687/0.662; propublica·A 0.843/0.816/0.840/0.828/0.834).
  Concordance levels vary 0.66–0.94 across cells, so the metric **discriminates** — the null is real, not
  a saturation artifact. No member-level "vessel" leaderboard emitted (R2/#143).
- **The 0.20 effect-size gate earned its keep:** scraped·B is *statistically* significant (p=0.012 at
  n=422) but ρ=−0.12 is substantively trivial and below the pre-registered floor — a large sample finding
  a meaningless correlation is exactly what a p-only rule would have mis-sold as CONFIRM. Honest nuance,
  **not a card**: a weak, sub-threshold *negative* tendency in the scraped era (safer seat → marginally
  *less* on-script, the "free voice" direction), never reaching 0.20.
- **Senate is underpowered by CORPUS COVERAGE, not just seat count** (the registration's "the powered run
  needs the House" was righter than it knew): the ProPublica/legacy lane carried **2** Senate members in
  2013–16 (vs 494 House), rising to 245 (2017–20); scraped 28/99. No Senate cell reaches ≥100.
- **The within-chamber reduction actively protected the House correlation:** 83 senators whose 2013–16
  releases the corpus mislabeled `House` were caught by the MoV-row chamber filter (their margins are
  Senate) and dropped to None, never polluting the House ρ. The 88/113/8/15 "concordance-but-no-MoV"
  members per cell are these mislabels + delegates (Norton) + one special-seated member (LaHood) — 98.8%
  bioguide-format match confirms no join defect.

Re-runnable: `PYTHONHASHSEED=0 python scripts/search/build_mov_table.py` then
`… scripts/search/s3_7_safe_seat.py`. Supersedes L565 S3.7 (BLOCKED-ON-SOURCE) and the registration's
BLOCKED-ON-HOUSE-GUESTBOOK verdict.

### S5.2 · The Concern Conversion Rate — **REGISTERED** (frozen 2026-07-20, BEFORE any measurement). Companions committed: `data/reference/search/s5_2-registration.json`.

**The p-hacking hole docs/12:457 named — "`≥Floor per cell` is not a registration" — is closed by
freezing the four companions BEFORE touching confirmatory data** (docs/23 §4 + §7.2 item 5). Floor
300/cell + the comparative-claim gate are Michael's §4 confirm; the on-topic primary K=2 is his
2026-07-20 confirm. The committed JSON carries the exact lexicon + parameters; this row is the ledger
record of the freeze, and the **verdict follows in a SEPARATE later commit so the freeze precedes the
result in git history.** No post-hoc edits (a real design change is a new registration, never an edit).

- **Hypothesis:** what share of expressed concern is *never* followed by the same member sponsoring an
  on-topic bill within 180 days — the rate itself is the headline (docs/12 S5.2).
- **Concern statement:** a solo, non-syndicated Lane-1 release by a D/R member (bioguide present)
  containing ≥1 of **31 frozen DIRECTED concern phrases** (`concerned about/by/that/over/with`,
  `deeply/gravely/seriously/very/extremely/increasingly concerned`, `alarmed/troubled/disturbed/
  worried/outraged/dismayed/appalled by/at/that…`) — anchored on the pipeline's `build._CONCERN`,
  directed forms only so the topic-of-concern is extractable.
- **Topic of concern:** the content-token set of the **sentence(s) containing the concern phrase** (not
  the whole release — avoids coincidental matches); content = pipeline tokenizer − `STOPWORDS` − the
  concern tokens − a frozen ~40-word generic stoplist (`act/bill/federal/american/people/…`, declared
  in the artifact so the choice is auditable).
- **Sponsorship:** BILLSTATUS 113–119 local (keyless) — sponsor `bioguideId` + `introducedDate` +
  (short title + CRS `policyArea` + `legislativeSubjects`). **Cosponsorship excluded** (sponsoring =
  authoring = the strongest follow-through).
- **On-topic (K=2 PRIMARY):** ≥2 shared content tokens between the concern topic and the bill topic.
  K=1 (loose) and K=3 (strict) + a CRS-tags-only variant reported alongside every cell as disclosed
  bounds; the verdict uses K=2.
- **Conversion:** same bioguide sponsors an on-topic bill with `introducedDate` in (concern_date, +180d].
- **Right-censoring guard:** a concern statement is eligible only if `concern_date + 180d ≤` the latest
  `introducedDate` in the corpus; later statements are EXCLUDED (unobservable), count reported.
- **Cells + floor:** pooled / D / R + D/R × 4 era-halves (docs/17 lanes: propublica 113–114/115–116,
  scraped 117/118–119). ≥**300** eligible concern statements/cell or "insufficient"; comparative gate =
  both party cells ≥300 **and** the D−R gap > the summed 95% CI half-widths (~8pp at p=0.5). Denominators
  pre-verified clearing 300 in every cell (lower-bound: pooled D 22,000 / R 12,721; smallest 689).
- **Status:** REGISTERED — measurement next (this session), then a verdict row. Closes docs/12:520's
  named p-hacking hole for S5.2.

### S5.2 · The Concern Conversion Rate — **FINDING: ~92% of congressional concern is never followed by a bill** (the rate is the headline). *Supersedes the REGISTERED status above; measured against the frozen registration, no post-hoc edits.*

**At the pre-registered K=2 topical match, 92.0% of expressed concern is NOT followed by the same member
sponsoring an on-topic bill within 180 days** (pooled, n=**28,106** eligible concern statements, 95% CI
±0.3pp). The registration (commit `5cd27da`) precedes this measurement in git history — the p-hacking
hole docs/12:457 named is closed by the freeze, not by the result.

- **The rate is match-strictness sensitive, so the RANGE is the honest finding:** non-conversion is
  **63.2%** at K=1 (any one shared topic token), **92.0%** at K=2 (primary), **98.3%** at K=3, **99.3%**
  CRS-tags-only. Every published card must carry the range; the headline uses the frozen K=2.
- **Denominator:** 29,111 concern statements detected (31-phrase directed lexicon over solo, non-
  syndicated, D/R Lane-1 releases); 11 excluded (no extractable topic), 994 right-censored (180-day
  window past the latest BILLSTATUS `introducedDate` 2026-07-15) → **28,106 eligible**. Sponsorship index:
  **107,481 authored bills / 1,048 members** (BILLSTATUS 113–119, keyless, local).
- **All 11 cells powered** (n≥300, smallest 643): K=2 conversion 5.6–11.4% across party × era-half.
- **Party comparative gate (registered = gap > summed 95% CI half-widths):** overall **D 8.6% vs R 6.8%**
  conversion (gap +1.8pp > summed ±0.9pp) → **PASSES**; robust in propublica-B (+1.9pp) and scraped-B
  (+4.0pp); propublica-A no difference (−0.9pp); scraped-A directional (+2.5pp) but underpowered for the
  gap. A real-but-small asymmetry — **Democrats convert concern to authored on-topic legislation modestly
  more often than Republicans, both parties still ~92% non-converting** — an asymmetric FINDING from a
  SYMMETRIC instrument (identical lexicon/match/threshold, party-blind by construction; Art. IV protected).
- **Conservatism, all frozen + disclosed (each pushes non-conversion UP; K=1's 63% is the floor):**
  authored SPONSORSHIP only (cosponsorship excluded — the strongest follow-through); exact-token match
  (no stemming, so plural/tense near-misses undercount conversions); 180-day window.
- **Verdict:** a stark, well-powered rate-report **card** (docs/12 S5.2 "T1 if the number is stark").
  Enters the docs/20 shelf **pending Fable/neutrality review + Michael's editorial publication** (like
  S1.9/S2.9/Intensification — publication is his act, never a session's). **This is the program's first
  Wave-S5 card** and the CONFIRMED-tier count moves 4 → 5, pending that review.

Re-runnable: `PYTHONHASHSEED=0 python scripts/search/s5_2_concern_conversion.py` (reads the frozen
registration; BILLSTATUS parse cached to `X:/onscript-data/bills/derived/s5_2-sponsorships.jsonl`).
Evidence: `scripts/search/evidence/s5_2_concern_conversion.result.json` + X: copy.

## HX REGISTRATION WAVE (docs/05 §3) — substrate audit + HX.8 measured (launch-eve Search lane, 2026-07-20, Opus)

**The mandated first step — "substrate audited against disk BEFORE speccing" (docs/05 §3; the S3/S4
lesson that cost 9 of 15 hypotheses) — run for all 8 registration-wave candidates:**

| HX | claim | substrate on disk | status |
|----|-------|-------------------|--------|
| HX.1 | GDELT-anchored script-formation ("most big news days → no caucus script") | `gdelt.py`/`silence.py` + `gdelt_theme_map.json` exist; **no persisted GDELT baseline** | **BLOCKED-ON-NETWORK** (needs a live DOC 2.0 query) |
| HX.2 | per-topic script-proneness | `taxonomy_v1.json` ✓ (repo root) + ledger shards ✓ | **RUNNABLE** |
| HX.3 | chamber velocity | ledger + chamber ✓ | RUNNABLE ⚠ #143 chamber trap (per-member cadence norm mandatory) |
| HX.4 | phrase half-life × majority | ledger ✓ + `chambers-control.json` ✓ | **RUNNABLE** (within-lane only) |
| HX.5 | opposition vs celebration reuse | S4.1 valence lexicons (in `wave_s4.py`) ✓ + corpus | **RUNNABLE** (placebo on the headline stat) |
| HX.6 | event-conditioned regional micro-scripts | `bioguide_states` + ledger ✓ (event anchor = complex) | RUNNABLE (complex) |
| HX.7 | pre-floor-fight discipline | **no floor-calendar table on disk** | **BLOCKED-ON-SOURCE** (as flagged 🔬) |
| HX.8 | office concentration + intensity-vs-reach | `stmt_meta` ✓ + `member_index` ✓ | **RUNNABLE — MEASURED below** |

**6 of 8 are runnable now with local data** (HX.1 needs live GDELT; HX.7 needs a floor-calendar). This
is the runnable/blocked map for the October registration wave — no hypothesis is specced against an
imagined table.

### HX.8 · Prolific-office concentration + intensity-vs-reach — **MEASURED** (descriptive self-audit)

Floors PRE-DECLARED before measuring (L4): `MIN_STMTS=10`, `MIN_OFFICES=30`. Chambers NEVER pooled
(#143), lanes NEVER pooled (L1), denominators in the view (#146/R3). No CONFIRM/REFUTE gate — the
distribution IS the finding. `scripts/search/hx_8_office_concentration.py`. Two findings, both symmetric
across parties:

1. **Volume concentration is moderate, roughly party-symmetric, and FELL after the 2021 lane change.**
   propublica (2013–20) House: the top decile of offices produced **~36%** of statements (Gini ~**0.50**),
   near-identical D (share 0.359 / Gini 0.510) vs R (0.355 / 0.491). scraped (2021–26): top-decile share
   dropped to **0.17–0.25** (Gini 0.34–0.44) — volume spread more evenly across offices. (No Senate
   propublica cell: the ProPublica lane carried **1** Senate office — the same coverage gap S3.7 found,
   not a bug.)
2. **Intensity strongly predicts reach in EVERY powered cell (Spearman ρ 0.55–0.91, all p ≪ 1e-16): a
   prolific office is a coordination HUB, not a loud self-repeater.** The more an office publishes, the
   more distinct synchronized (peak≥15) phrases it rides. Robust across chamber × party × lane
   (House-R-propublica tightest at **0.858**, House-D-propublica loosest at **0.547**, still strong;
   scraped 0.79–0.91). The intensity-quintile mean-reach artifact is monotone up in every cell.

Both are methods/transparency-shelf descriptives (docs/20), symmetric by construction. Re-runnable:
`PYTHONHASHSEED=0 python scripts/search/hx_8_office_concentration.py`; evidence
`scripts/search/evidence/hx_8_office_concentration.result.json` + X:. **Next runnable HX (per the audit):
HX.2 / HX.4 / HX.5 (all local); HX.1 gated on live GDELT, HX.7 on a floor-calendar.**

### HX.4 · Phrase half-life × majority status — **REGISTERED** (frozen 2026-07-20, before measurement)

Design frozen before touching confirmatory data (docs/12 L4); no post-hoc edits (the verdict lands in a
separate later commit so the freeze precedes the result in git history).

- **Question:** does a party sustain its coordinated talking points LONGER when it holds institutional
  power (House majority) than when it does not? **Symmetric by construction** — House control flips
  between parties across congresses (chambers-control: 113–115 R, 116 D, 117 D, 118–119 R), so the
  comparison is majority-vs-minority POSITION pooled across whichever party held it — an institutional
  effect, not a partisan one. **Within-lane only** (docs/12 L1).
- **Unit:** a (phrase, congress) with `peak_units ≥ 15` (from `member_index[lane]`) — a synchronized
  phrase-in-a-congress. **Party** = `peak_party` (the party that coordinated on it that congress).
- **Persistence ("half-life"):** the count of distinct ACTIVE DAYS the phrase was used within that
  congress's date range (`daily_series[lane]` filtered to `[congress_start, congress_end)`). Primary
  metric. Robustness: calendar span (last − first active day).
- **Majority proxy:** the phrase's party held the **House** majority that congress. House chosen as the
  message-active, press-corpus-heavy chamber (disclosed; Senate-majority and unified-control reported as
  robustness variants, never as the primary).
- **Gate (frozen numerals):** per lane, Mann–Whitney U on persistence, majority-units vs minority-units.
  **CONFIRM iff |rank-biserial r| ≥ 0.10 ∧ p < 0.05 ∧ SAME direction in BOTH lanes.** **REFUTE iff
  |r| < 0.10 in a well-powered lane.** Floor: each cell (majority, minority) reports only with **≥ 200
  units.** (r > 0 ⇒ majority phrases persist longer.)
- **Status:** REGISTERED — measurement next (this session), then a verdict row.

### HX.4 · Phrase half-life × majority status — **CONFIRM: minority-party talking points persist ~3× longer than the majority's** (both lanes). *Supersedes the REGISTERED status; measured against the frozen registration `bc4d0d1`, no post-hoc edits.*

**A party's coordinated talking points persist for FEWER active days when that party holds the House
majority than when it sits in the minority — robust in both provenance lanes and both duration metrics.**
Symmetric by construction (House control flips between parties across congresses).

| lane | units (maj / min) | median active-days maj / min | rank-biserial r | p | span-robustness r |
|---|---|---|---|---|---|
| propublica | 23,392 / 3,869 | **14 / 41** | **−0.258** | 5e-146 | −0.347 |
| scraped | 3,903 / 1,686 | **15 / 51.5** | **−0.380** | 4e-113 | −0.209 |

Frozen gate: |r|≥0.10 ∧ p<0.05 ∧ same direction both lanes — all met, direction negative (majority
SHORTER) → **CONFIRM.**

- **The institutional reading:** the minority, lacking the floor and the agenda, leans on messaging — its
  coordinated phrases are sustained grievances that stay in circulation for weeks; the majority
  legislates and moves on, its coordinated phrases bill/moment-bound and short-lived. "The minority
  messages; the majority legislates."
- **⚠ Disclosed confound — propublica's majority is party-collinear.** House control was R for 3 of that
  lane's 4 congresses (113–115 R, 116 D), so there "majority" ≈ "R-ness" and the two cannot be fully
  separated. **The scraped lane is the load-bearing evidence:** its House control is genuinely mixed
  (117 D, 118–119 R), so majority spans BOTH parties, and it STILL shows the effect (r=−0.380) — the
  shorter-majority persistence is not merely a party effect. **A within-party decomposition** (does each
  party's own persistence drop in its majority congresses?) is the natural robustness follow-up and a
  precondition for publication — flagged, deliberately NOT run post-hoc on this same data in-session.
- **Verdict:** CONFIRM per the frozen gate → a candidate card, **pending Fable/neutrality review (which
  should include the within-party decomposition) + Michael's editorial publication**. Program cards
  5 → 6 pending that review. Re-runnable: `PYTHONHASHSEED=0 python
  scripts/search/hx_4_halflife_majority.py`; evidence
  `scripts/search/evidence/hx_4_halflife_majority.result.json` + X:.

### HX.2 · Per-topic script-proneness — **MEASURED** (descriptive; the clean signal is cross-party-within-topic)

Do some topics throw off more COORDINATION per unit of discussion than others? Index = coordinated
peak≥15 phrase-types (`member_index`, credited to `peak_party`) per 1,000 on-topic statements (seed-
substring tagged, `iter_statements` scan), per party, per lane. `scripts/search/hx_2_topic_scriptproneness.py`.

**Each party's coordination portfolio differs and SHIFTS across the 2021 lane change** (top topics by
index): propublica **D = crime (12.2) / energy_climate / healthcare**; **R = abortion (13.1) /
israel_gaza / taxes_debt**. scraped **D = guns (7.5) / taxes_debt / abortion**; **R = immigration (4.8) /
veterans / elections_democracy**. Symmetric instrument (identical seeds + method, both parties),
asymmetric portfolios (Art. IV protected).

- **⚠ The cross-TOPIC ranking is seed-breadth confounded** — a topic with narrow seeds mechanically
  scores a higher C/V index — so it is NOT a clean "topic X coordinates more than topic Y" claim. **The
  CLEAN signal is cross-PARTY within a topic** (the seed list cancels): e.g. propublica **healthcare D
  8.9 vs R 4.5**, **social-security/medicare D 6.5 vs R 4.8** — Democrats coordinated ~2×/1.4× more per
  unit of healthcare/entitlement discussion in that era; scraped **immigration R 4.8** leads its column.
- **The index is broadly higher in propublica than scraped** — consistent with HX.8 (coordination
  concentration fell after 2021).
- **Seed-proxy caveat:** seed-substring tagging misses topical text without the literal seed ("born in
  the united states" carries no seed), so C and V are lower bounds; the index is interpreted
  comparatively only, never as an absolute rate. Chambers mixed (a topic-level, not office-level,
  descriptive); lanes isolated (L1).
- **Verdict:** a methods/transparency-shelf descriptive (docs/20) — a map of what each party coordinates
  on, NOT a card. Re-runnable: `PYTHONHASHSEED=0 python scripts/search/hx_2_topic_scriptproneness.py`;
  evidence `scripts/search/evidence/hx_2_topic_scriptproneness.result.json` + X:.
