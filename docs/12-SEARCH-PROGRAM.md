# 12-SEARCH-PROGRAM — The Search (v1, Fable, 2026-07-15)

> **What this is.** The pre-registered hypothesis sweep of the 25-year archive. Fable authored it;
> **Opus executes it mechanically** — every hypothesis below carries a protocol precise enough to
> CONFIRM or REFUTE without judgment calls. Findings land in `docs/13-SEARCH-LEDGER.md` (the running
> verdict ledger) + `data/derived/findings/*.json` (one card per confirmed finding). The goal is a
> **shelf of dozens of verified, drip-able insight pieces** — 1–2 published per month for years —
> each labeled, receipted, and split-era validated before anyone sees it.
>
> **This document is the pre-registration.** Metrics, denominators, splits, and thresholds are fixed
> here before any measurement runs. Changing a protocol after seeing data requires a dated entry in
> §6 (Amendments) — silent tuning is p-hacking and is forbidden. The graveyard (what we tested and
> killed) is published alongside what survived; the tally is itself a headline.
>
> Relationship to canon: this operationalizes HORIZON §2.5 under its Appendix rules and does not
> preempt the BUILD-PROGRAM queue (it runs beside it as the *content* program). Constitution gates
> apply in full: citation-or-silence, symmetric instrument, correlation-not-cause, aggregate-only
> for behavioral oddities, trend-language gate, releases are Michael's act.

---

## §0 Ambition math (why this is sized the way it is)

Target: **≥24 CONFIRMED finding cards** = 1–2/month for 12–24 months of drip.
Catalog below: **47 pre-registered hypotheses.** Honest expected survival — corpus-only families
~60% (they're descriptive), joined families ~40% (more confounds) → **expected ~22–28 confirmed.**
If survival runs low, §3.S6 has the null-banger reserve: "we tested N folk theories about
congressional speech; K are false" is itself a T1 piece. Failure is convertible; only silence is
waste.

**Tiers** (score at confirmation, not at ideation):
- **T1 — holy shit.** Novel, counterintuitive or never-measured, one-chart visual, bulletproof.
- **T2 — interesting as fuck.** Strong curiosity + clean chart; carries a monthly Appendix slot.
- **T3 — mildly interesting.** Filler, ride-alongs, footnotes in bigger pieces.
Rubric: novelty (1–5) × visual (1–5) × defensibility (1–5); T1 ≥ 60, T2 ≥ 30. Drip priority favors
T1 > T2 > T3 within era-relevance (SCOTUS pieces near rulings, election pieces near cycles).

---

## §1 The Standards (the laws every hypothesis obeys)

1. **Pre-registration.** Protocols are fixed here. Amendments are dated (§6).
2. **Verdicts are exhaustive.** Every hypothesis ends in exactly one of:
   `CONFIRMED` · `REFUTED` · `UNDERPOWERED` (data too thin — not evidence of absence) ·
   `ARTIFACT` (killed by a confound — the confound is named) · `BLOCKED` (data/key unavailable).
   Every verdict is recorded in 13-SEARCH-LEDGER with its numbers. No hypothesis vanishes.
3. **The coverage confound is refutation attempt #1, always.** The corpus grows over 25 years
   (member-site adoption, scraper reach). Every trend metric MUST be computed as a **rate**
   (per-1k-statements or per-active-member), never a raw count; and every trend must survive the
   **density-matched control**: recompute on later-year data subsampled to earlier-year daily
   statement volumes. Raw and normalized series disagreeing on direction → `ARTIFACT`.
4. **Split-halves validation.** Default split: **Era A = congresses 107–113 (2001–2013), Era B =
   114–119 (2014–2026).** Election-cycle metrics split odd/even cycles instead. CONFIRMED requires:
   same direction in both halves AND pre-registered effect floor met on the full span.
5. **Symmetry by construction.** Every metric computed identically for both parties, both numbers
   always reported. A party-asymmetric finding triggers the **power-position reframe check** (does
   it attach to majority/minority or White-House-control rather than party identity?) and a ⚠
   neutrality review before any publication. Power-position findings must show the effect under
   BOTH parties' stints in each role where the calendar provides them.
6. **Power floors (else UNDERPOWERED).** Rate cells: ≥200 statements/cell. Event studies: ≥8 events
   per half. Cohort cells: ≥30 qualifying members. Single-artifact finds (a "first ever") need no
   floor — they need the receipt.
7. **Aggregate-only for behavioral oddities** (party/chamber/cohort/delegation), per Appendix rule 4.
   Leaderboard-shaped outputs obey the member-naming rules (raw counts + receipts, both-party lists
   together, ≥3 dated citations, no composite scores). Stylometry never identifies staff (XIII).
8. **Correlation-not-cause on every card's face.** The trend-language gate (08) applies to every
   rendered sentence. Motive is never asserted; "the pairing speaks."
9. **Gravity cases ⚠.** Mass-casualty, war, January 6: measurement permitted under this program;
   publication requires the gravity protocol (no jokes, no leaderboards, aggregate-only, Michael's
   explicit release) — ⚠⚠ items doubly so.
10. **$0 and local.** Deterministic stdlib-first compute on the local archive. `ANTHROPIC_API_KEY`
    never set locally. congress.gov-keyed joins run as a one-shot **workflow_dispatch Actions job**
    (the key already lives there) writing derived JSON back to the repo — never a local key.
11. **Data-resolution audit before measurement.** Each hypothesis names its resolution risk (e.g.
    date-only vs timestamp). If the audit fails, the hypothesis is `BLOCKED` or reframed by
    amendment — never quietly approximated.
12. **Kill-tested metrics.** Every metric function ships with unit tests INCLUDING a synthetic
    kill-fixture: a fake corpus with a known injected confound (e.g. pure coverage growth) that the
    metric must NOT flag as a finding. House pattern; no metric touches real data until its
    kill-fixture passes.

---

## §2 Wave S0 — infrastructure (build once, everything rides it)

**S0.1 Data inventory audit.** Enumerate what actually exists and at what resolution:
`X:\onscript-data\state\ledger.json` (3 GB unified — do NOT json.load), the per-congress Alexandria
shards (`state/alexandria/coverage-*.json` + whatever phrase/ledger shards exist — audit them),
`statements.jsonl.gz` (full text, ~670k releases), `data/derived/chapters/*.json` (353, with
per-era stats), the roster (`congress-legislators`, CC0). Record findings in the LEDGER preamble.
**Decision rule:** prefer shard-wise queries; build the streaming unified-ledger reader (the queued
Archive/1.1 item) only if a metric genuinely needs cross-congress single-pass state.

**S0.2 The query harness** (`pipeline/search/` or `scripts/search/` — Opus's call, registered in
FEATURES as dark): a statements streamer (gzip line-iterator with member/party/date filters), a
shard-wise ledger query API (phrase → first_seen, daily adoption, peak), and a memoized
intermediate store (`data/derived/search/cache/` — parquet-free, JSON/CSV, deterministic).

**S0.3 The metrics library** with kill-fixtures (§1.12): `rate_per_1k`, `per_member_rate`,
`split_halves`, `density_matched_subsample`, `power_check`, `symmetry_table`, `spearman` (stdlib
implementation), `did` (difference-in-differences, deterministic arithmetic).

**S0.4 Reference tables** — each committed under `data/reference/search/` with source URL, fetch
date, and license in the file header. All public-record, hand-curated once:
`sessions.json` (session/recess calendar 2001–2026), `chambers-control.json` (House/Senate/WH
control per congress), `elections.json` (election dates + general-election losers per cycle),
`leadership.json` (Speaker/Leaders/Whips per congress), `presidents.json` (terms + name tokens +
pre-registered euphemism list: "the administration", "the white house", "this president"),
`scotus-landmarks.json` (~15 cases, decision dates), `shutdowns.json`, `crisis-events.json`
(⚠ criteria in-file: US mass-casualty events ≥10 deaths, from public record), `sotu-dates.json`.

**S0.5 The findings ledger + card schema.** `docs/13-SEARCH-LEDGER.md`: one row per hypothesis
(ID · name · verdict · headline number · date · notes), plus the running tally
(tested/confirmed/refuted/underpowered/artifact/blocked). Cards: `data/derived/findings/<id>.json`
= `{id, claim, tier, numbers, chart_spec, receipts_sample, protocol_ref, labels
["correlation-not-cause", ...], split_result, confounds_tested, graveyard_context, drip_slot}`.

**S0 acceptance:** harness + metrics kill-tested; reference tables committed with sources; a smoke
query (top-10 phrases by peak, congress 111) returns in reasonable time; LEDGER initialized.

---

## §3 The catalog

Format per row: **ID · Name — hypothesis.** Protocol: metric | denominator | split | CONFIRM
threshold. Risk: the confound Opus attacks first. (Tier = pre-registration guess, re-scored at
verdict.)

### Wave S1 — pure ledger (coordination mechanics + the calendar). Cheapest, run first.

- **S1.1 · The Industrialization of the Memo — talking points reach full caucus saturation faster
  every cycle.** Protocol: for every phrase family with peak-day adopters ≥15, ignition width =
  days from first_seen to peak day (cap 60); median width per year | per-year phrase families |
  split-halves + density-matched subsample (§1.3) mandatory | CONFIRM: Spearman < 0 across years in
  both halves AND 2001–05 median ≥ 2× 2022–26 median. Risk: denser corpus mechanically narrows
  widths — the subsample control is decisive. **Tier guess: T1.** (If true: "In 2005 a talking
  point took a week to sweep the caucus. Today it takes a day.")
- **S1.2 · The Sync Ceiling — the loudest single-day unison keeps rising.** Max same-day same-phrase
  adopters per year ÷ active members that year | yearly | split-halves | CONFIRM: rising in both
  halves, 2026 ceiling ≥ 1.5× 2005. Risk: coverage. T2.
- **S1.3 · Phrase Lifespan Collapse — talking points die faster than they used to.** Median days
  first_seen→last_seen for phrases with peak ≥10 | per-year cohorts of phrases | halves + density
  control | CONFIRM: ≥30% median lifespan drop A→B, both halves' internal trend agreeing. T2.
- **S1.4 · The Copy-Paste Caucus — verbatim/near-identical multi-member releases are a growing share
  of all output.** Share of statements collapsed by the joint/near-identical machinery, per party
  per year | all statements | halves + coverage control | CONFIRM: share doubles A→B, both parties'
  direction agreeing. Risk: collapse-detector sensitivity is itself era-dependent — kill-fixture
  required. T1 if the curve is steep.
- **S1.5 · The Weekend Memo — coordinated ignitions almost never start on weekends, and the
  business-day fingerprint sharpened.** Ignition-day weekday distribution vs all-statement weekday
  baseline | ignitions (first_seen of eventual peak≥15 phrases) | halves | CONFIRM: weekday skew
  vs baseline χ²-style excess ≥ pre-set margin in both halves. (The distribution-schedule of the
  memo, visible from public data.) T2.
- **S1.6 · The 90-Day Snap — message discipline tightens as elections approach; the curve's shape
  is the finding.** Weekly party discipline index vs days-to-election | in-cycle weeks | odd/even
  cycle split | CONFIRM: monotone rise inside 90 days in ≥6 of 13 cycles per split half. T2.
- **S1.7 · The August Effect — coordination doesn't collapse in recess; it's pre-scheduled.**
  Discipline + ignition rate, session vs recess weeks | sessions.json | halves | CONFIRM: recess
  ignition rate ≥ 70% of session rate (the counterintuitive direction); REFUTE if it craters. T3
  either way; cheap.
- **S1.8 · The SOTU Gravity Well — the one night both parties speak the same words, and the shared
  window is shrinking.** Cross-party shared-phrase count on SOTU day + days until return to
  baseline ("shared-reality half-life"), per year | sotu-dates.json | halves | CONFIRM: half-life
  declining in both halves, ≥40% total. **T1 if confirmed** ("the shrinking shared calendar").
- **S1.9 · The 2022 Self-Audit — re-test the founder's own finding (Democrats coordinate tighter)
  on the symmetric corpus.** Mean pairwise weekly content-gram overlap per party, 2021–2022 press
  releases | matched member counts | n/a (targeted replication) | Pre-commitment: EITHER outcome
  publishes — replication ("it wasn't Twitter, it's the parties") or reversal ("it was a platform
  artifact — we checked our own headline"). Integrity flex. T1 either way.
- **S1.10 · Bipartisanship Has a Season — friendly cross-party co-mentions migrate on the election
  calendar.** Rate of "proud to join/partner with [other-party member]" (deterministic verb
  allowlist) vs days-to-election | per-week rates | odd/even cycles | CONFIRM: trough inside 90
  days, rebound after, in both splits. T2.
- **S1.11 · Delegation Echo — same-state delegations share phrases beyond party baseline.**
  Same-state cross-member phrase-share vs shuffled-state null (deterministic permutation, seeded) |
  aggregate by state size | halves | CONFIRM: observed ≥ 1.5× null in both halves. T3 (methods
  ride-along for S1.1). Aggregate-only.
- **S1.12 · Leadership Ignites, Backbenches Amplify — what share of big ignitions start in a
  leadership office?** First-sayer office class (leadership.json vs rest) for peak≥20 phrases |
  ignitions | halves | CONFIRM: leadership share ≥ 3× their statement share, stable in halves.
  Aggregate framing only ("N% of major talking points originate in leadership offices"). T2.

### Wave S2 — full text (language evolution). Streams `statements.jsonl.gz`.

- **S2.1 · The Voldemort Index — parties stop *naming* the opposing president.** Opposing-president
  name-token rate vs euphemism rate (presidents.json pre-registered lists) per party per year |
  per-1k statements | halves + all four presidencies with both-party data | CONFIRM: avoidance
  (euphemism share) higher for opposing than own president by ≥10pp, BOTH parties, both halves.
  **T1.** (Also yields per-presidency "days until the name disappears" — the chart.)
- **S2.2 · Adjective Inflation — "unprecedented" got precedented.** Rate of
  unprecedented/historic/radical/extreme/crisis per 1k statements, per party per year | halves +
  density control | CONFIRM: ≥3 of 5 words tripled A→B in both parties. Plus the derived artifact:
  the year each word crossed 2× its 2001–05 baseline ("the year it lost its meaning"). T2.
- **S2.3 · What Losing Sounds Like — the minority's linguistic signature.** "The American people"
  invocation rate + rhetorical-question rate + exclamation density as a function of
  majority/minority status (chambers-control.json) | per-1k, party-symmetric | power-position
  check (§1.5): effect must appear for BOTH parties when out of power | CONFIRM: out-of-power >
  in-power on ≥2 of 3 markers, both parties, both halves. **T1** ("you cite the boss more when
  you're losing — everyone does").
- **S2.4 · Punctuation Archaeology — the first exclamation point, first ALL-CAPS sentence, first
  emoji in an official congressional press release.** Single-artifact finds: earliest instance of
  each (unicode scan; manual receipt inspection) + the rate curves per party per year. No floor —
  the receipt is the finding. T2 (the emoji date is a guaranteed share).
- **S2.5 · The Death of the Semicolon** — semicolons per 1k sentences, 25-year slope, both parties |
  halves | CONFIRM: ≥50% decline. T3 ride-along with S2.4.
- **S2.6 · Reading-Level Drift** — identical rubric (deterministic readability formula, stdlib) per
  party per year; DC-voice vs recess-voice (sessions.json) as the sub-finding ("recess metabolism") |
  per-statement, length-controlled | halves | CONFIRM: any stable ≥1-grade-level shift. ⚠ framing:
  measurement, not mockery. T2.
- **S2.7 · Pronoun Economics — "I" season is primary season.** First-person-singular vs plural
  ratio vs days-to-election + tenure + chamber | per-1k tokens | odd/even cycles | CONFIRM: I/we
  rises inside primary windows in both splits, both parties. T2.
- **S2.8 · The Seniority Vocabulary Curse** — unique-vocabulary rate vs terms served (roster) |
  per-member-year, length-controlled, aggregate cohorts | halves | CONFIRM: monotone decline with
  tenure, both parties. T3.
- **S2.9 · The Boogeyman Rotation — each party's named villain, crowned and dethroned, 2001→now.**
  Mention share of named opposing-party figures (leadership + presidents lists) per party per year —
  pure mention-share, NO sentiment claim | per-1k | descriptive (no confirm gate — the chart is the
  artifact; publishes under correlation-not-cause with the "mention ≠ hostility" label). T2.
- **S2.10 · The Concern Ladder — "concerned → deeply concerned → gravely concerned → alarmed" is a
  real escalation grammar.** Frequency + within-topic escalation sequences of the concern ladder |
  per-1k | halves | CONFIRM: ladder ordering is consistent (deeper terms rarer, later in event
  windows) in both halves. T2; pairs with S4 events. (Sponsorship conversion = S5.2, keyed join.)
- **S2.11 · Euphemism Genealogies — paired-referent label shifts ("estate tax"→"death tax" as a
  class).** 20 curated seed pairs (committed reference file; curation disclosed) → measure each
  pair's party split + crossover dates | per-pair adoption curves | descriptive with per-pair
  receipts | publishes as a series ("the renaming machine"), each pair its own mini-card. T2.
- **S2.12 · The Apology Corpus — "I apologize / I regret / I misspoke," 25 years of it.** Rates +
  era trend + majority/minority split | per-100k (rare) | expect UNDERPOWERED per-party-year cells;
  aggregate to era | CONFIRM: any stable trend; else the null publishes as a T3 footnote ("Congress
  apologizes N times per year, unchanged"). T3.

### Wave S3 — roster joins (member lifecycle; congress-legislators CC0 + elections.json).

- **S3.1 · The Freshman Assimilation Speedrun — Washington absorbs a freshman faster every cycle.**
  Per cohort (13 classes): median days from a member's first statement to first participation in a
  party-peak phrase (peak≥20, within 7 days of peak); entry floor: member ≥20 statements in first
  year | cohort medians | Spearman across cohorts, halves agree | CONFIRM: ≥25% decline 2001→2026.
  Confound: early-era coverage thinness — per-member cadence normalization mandatory. **T1.**
  (Retrospective assimilation curves — 13 cohorts already in hand; Season-2's live version becomes
  the sequel, not the prerequisite.)
- **S3.2 · Lame-Duck Honesty — members who lose go measurably off-script, immediately.** For
  general-election losers (elections.json): on-script participation rate + I/we ratio, post-election
  lame-duck window vs their own prior 12 months, difference-in-differences vs returning members
  same weeks | ≥30 losers per half | halves (cycles) | CONFIRM: ≥20% relative drop in script
  participation, consistent sign in ≥3 cycles per half, both parties. **T1** ("defeat is the only
  known cure for the script"). Aggregate framing; no individual cards.
- **S3.3 · The Retirement Drift (H3 retrospective) — the backtest.** Per-member centroid-distance
  time-series (deterministic n-gram overlap distance, no embeddings needed for v1) for members with
  announced retirements (public dates, curated table) vs matched non-retirees | ≥40 retirements |
  halves | CONFIRM: pre-announcement drift detectable at pre-set lead time with precision/recall
  reported honestly; REFUTE publishes too ("we tested the spooky thing; it's not there"). This is
  the flagship backtest — the machine's first firing. T1 either way. ⚠ published with error bars,
  never as a live prediction (HORIZON H3 rules).
- **S3.4 · The Party-Switch Fingerprint** — the handful of switchers (public list): language
  distance to old vs new party centroid, before/after | descriptive per-case with receipts (n too
  small for gates — publishes as case studies, labeled as such). T2.
- **S3.5 · Committee Vocabulary Infection** — days from committee assignment to committee-vocab
  entering a member's output ("readiness," "family farms") | needs historical committee rosters —
  🔬-lite audit of `unitedstates` committee data first; BLOCKED if historical membership incomplete.
  Aggregate cohorts. T2.
- **S3.6 · Adoption Speed vs. Cohort Age** — do newer cohorts parrot faster? Per-member median
  lag-to-peak vs entry congress | aggregate | halves | CONFIRM: monotone by cohort. T3 (S3.1
  ride-along).
- **S3.7 · The Safe-Seat Vessel Test** — margin-of-victory (elections.json) vs script participation:
  does safety free the voice or complete the assimilation? | aggregate quintiles | halves |
  Either direction confirms something; flat REFUTES both folk theories (publishable null). T2.

### Wave S4 — event joins (curated public event tables; ⚠ gravity where marked).

- **S4.1 · One Court, Two Languages — every landmark SCOTUS decision, 2001–2026, produces two
  vocabularies within hours.** Per case (scotus-landmarks.json): response volume, latency, the two
  parties' top phrases, case-name vs outcome-language ratio | ≥12 cases | halves | Descriptive
  series + one aggregate CONFIRM: the case-name-vs-outcome framing split has a stable party
  direction across ≥8 cases. **T1 as a series** — each ruling is a drip piece; the birthright 06-30
  live data is the pilot card. 
- **S4.2 · The Shutdown Blame Grammar** — per shutdown: "shut down" agent-assignment phrasing
  ("Democrats shut down" vs "Republican shutdown"), volume curves, who stops talking first |
  shutdowns.json | descriptive per-event + cross-event pattern | T2.
- **S4.3 · Thoughts-and-Prayers Half-Life ⚠** — across successive mass-casualty events: response
  latency, condolence-vocabulary composition, response volume decay event-over-event |
  crisis-events.json, ≥8 events per half | halves | CONFIRM: monotone latency/volume trend.
  Gravity protocol in full (§1.9): aggregate only, no leaderboards, no levity, Michael's explicit
  release. The heaviest and possibly most-cited finding in the program.
- **S4.4 · The Friday Night Dump, Autopsied** — walk-back/correction vocabulary by day-of-week +
  holiday-eve windows, 25 years | per-1k | halves | CONFIRM: Friday excess ≥1.5× weekday mean in
  both halves; the sub-finding is whether the Dump *died* with the 24/7 cycle (B-half decay). T2.
- **S4.5 · Election-Morning Vocabulary — what winning and losing sound like, 13 cycles.** First
  post-election-day statements: winner-party vs loser-party markers (mandate/humility/unity/fight
  lexicons, pre-registered lists) | 13 cycles | odd/even split | CONFIRM: stable marker separation
  both splits, both parties when in each role. T2.
- **S4.6 · Crisis Convergence — disasters produce the only true bipartisan unison.** Cross-party
  same-phrase spikes: what share follow natural disasters vs political events | ledger + events |
  halves | CONFIRM: disaster-window unison rate ≥3× baseline. Pairs with the "we agree about the
  sky" HORIZON note. T2.
- **S4.7 · January 6 in 25-Year Context ⚠⚠** — response volume, latency, unison-then-divergence
  curve vs every other crisis in the archive | measurement permitted now; publication is its own
  deliberate decision (Michael + gravity + ⚠⚠ review). Pre-registered so the measurement is
  above reproach if/when used. Tier n/a until then.
- **S4.8 · The War Vocabulary Cycle** — AUMF 2002, Syria 2013, Ukraine 2022+: how force-authorization
  language evolved; "war powers resolution" already visible spiking in era-119 chapters | curated
  votes list | descriptive series. T2.

### Wave S5 — keyed joins (run as one-shot Actions workflow_dispatch; the key never comes local).

- **S5.1 · Vote No, Take the Dough — industrialized.** Roll-call No votes × same-member
  credit-claiming releases matched on program tokens + dollar figures | congress.gov roll calls |
  per-bill receipts, both-party lists together, context-honesty label (members vote no on packages
  for many reasons — the pairing speaks) | Publishes as raw pairings + rates. T1 as a genre.
- **S5.2 · The Concern Conversion Rate** — share of expressed-concern statements followed by the
  same member sponsoring anything on-topic within 180 days | congress.gov sponsorship | ≥Floor per
  cell | CONFIRM: the rate itself is the headline ("X% of congressional concern is never followed
  by a bill"). T1 if the number is stark.
- **S5.3 · The Credit-Claiming Multiplier** — identical grant announcements claimed by N members:
  the mean N | corpus-only actually (dollar+program token matching) — promoted to S5 only if
  grant-database validation is wanted; v1 runs corpus-only | CONFIRM: multiplier ≥2 with stable
  distribution. T2 ("the average federal dollar is announced 3.4 times").

### Wave S6 — synthesis.

- **S6.1** Re-score all confirmed cards against the rubric with real numbers; rank the shelf.
- **S6.2** The Graveyard tally (tested/died, by family) — drafted as its own publishable piece.
- **S6.3** The null-banger reserve: if any family swept ≥5 hypotheses with ≤1 confirmation, that
  family's nulls compose into "folk theories about Congress that aren't true."
- **S6.4** Handoff: 13-SEARCH-LEDGER complete; drip calendar proposal (which card, which month,
  freeze-window aware) for Michael's editorial pick. Publishing remains his act, always.

**Explicitly out of scope for this program** (parked, needs what it needs): embeddings-class work
(Ghost Caucus H5, Divergence Index H6 — want the 4080 pass), the topic layer (Escalation Clock),
external-corpus joins (H4 upstream, H8 media, FRED/NOAA/FEC 🔬 family), Memory-Hole-dependent
items. They stay in HORIZON; the quarterly-pick doctrine governs them.

---

## §4 Execution contract (Opus)

1. **Order:** S0 → S1 → S2 → S3 → S4 → (S5 when a dispatch window is convenient) → S6. Within a
   wave, cheapest-first is fine; never start a wave before the prior wave's verdicts are LEDGERed.
2. **Session shape:** pick up the next unfinished wave; build/extend harness + metrics with
   kill-fixtures FIRST; run; record every verdict with its numbers in 13-SEARCH-LEDGER; write
   finding cards for CONFIRMED only; BUILDLOG entry + You-are-here per the operating contract.
3. **No API keys locally, no LLM in the measurement path.** Narrative polish of finding cards, if
   any, happens later via the sanctioned generator policy — the numbers and claims are frozen by
   the deterministic pass first.
4. **Protocol integrity:** thresholds live in this doc. If a protocol proves ill-posed on contact
   with data, STOP that hypothesis, write a dated amendment in §6 with the reason, then rerun
   clean. Never tune-and-rerun silently.
5. **Adversarial pass per wave:** before LEDGERing a wave's confirmations, run the house
   adversarial review on the wave's metrics + top findings (the reviewer attacks: coverage
   artifact, collapse-detector drift, boilerplate contamination, denominator choice, split
   leakage). Findings that survive get `verified: true` on their card.
6. **Stopping rule:** the program is DONE when every catalog row has a verdict and S6 is written.
   Dry rounds don't extend it; new hypotheses go to HORIZON or a v2 of this doc — scope creep is
   how sweeps die.

## §5 Publication mapping (for the eventual drip — decisions are Michael's)

- T1 cards → standalone pieces (site + the Appendix slot; dataisbeautiful-shaped charts).
- T2 cards → monthly Appendix rotation; T3 → ride-alongs and footnotes.
- Series engines (S4.1 SCOTUS, S2.11 renamings) → recurring formats, one card per instance.
- Election freeze window (Constitution): no novel member-adjacent analytics released inside the
  frozen weeks; the calendar in S6.4 must show it.
- Every published piece links its protocol row here + its LEDGER line + the graveyard tally. The
  discipline is the brand.

## §6 Amendments

**A1 — 2026-07-15 (Opus, S0.1 data-inventory audit) — the analyzable symmetric span is ~2013–2026,
not 2001–2026.** The audit measured the mirror's actual coverage and it is far thinner and more
party-asymmetric before ~2011 than the "25-year archive" framing assumed:
- congress **107 (2001–02): 94 records, 100% Democrat, ZERO Republican**; **108: 289 (99% D)**;
  symmetric two-party balance is first reached at **112 (2011–12): 419 R / 428 D**.
- the per-congress ledger shards reflect this: **107–111 are empty** (near-zero qualifying data),
  112 partial (49 KB), **113–119 populated** (243 MB–1 GB). The 3 GB monolith is recent-heavy
  (earliest first_seen 2011) and is NOT a reliable 25-year source. Discipline/coverage shards span
  all eras but early-era cells are tiny (107 = 79 D-days, no R).

**Consequences (binding for the whole program):**
1. **Two-party / symmetric metrics run on congresses 113–119 (2013-01-03 → 2026).** The pre-2013
   corpus is retained ONLY for single-party and descriptive / "first-ever" artifacts (e.g. S2.4
   punctuation firsts), always with the coverage caveat on the card's face. No symmetric trend claim
   crosses 2013 backward.
2. **Split-halves default revised** (supersedes §1.4 for this program): **Era A = 113–116
   (2013–2020), Era B = 117–119 (2021–2026).** Election-cycle metrics split odd/even *within*
   2013–2026. This window still contains both parties in every power position (House control flips
   2019/2023; WH: Obama '13–'16, Trump '17–'20 & '25–, Biden '21–'24) — so the power-position reframe
   (§1.5) remains testable under both parties.
3. **Published language:** "since 2013" for symmetric trends; "since 2001" permitted only for
   single-party / first-ever artifacts carrying the explicit coverage-onset caveat. The
   "in 2005 a talking point took a week…" framing in S1.1's blurb is retired — the honest baseline is
   the 2013–2016 window.
4. Power floors (§1.6) unchanged; more early-window cells will correctly read UNDERPOWERED. This is
   the coverage confound (§1.3) confirmed empirically, not a surprise — the pre-registration
   anticipated it; the audit sized it.

*Nothing else in the catalog changes; the substrate (S0.2) is built from `raw/congress-press` (the
confirmed-complete ground truth, 2001–2026) with the analyzable window applied per metric.*

**A2 — 2026-07-15 (Opus, Wave S1 run) — S1.1 and S1.3 as-specified are ARTIFACT; the genealogy
metrics need a merged cross-era substrate + an event detector.** First S1 run produced a naive
CONFIRMED for both, but the adversarial look at the series (mandated by §4.5) revealed a structural
confound the gate missed:
- The per-Congress ledger shards seat each Congress in its ODD year, so any `first_seen → span` metric
  systematically differs between a Congress's **year 1 (a ~2-year runway → widths pin to the 60-day
  cap, median 60, n=23,117)** and **year 2 (no runway → median 3, n=13,872)** — a **20× sawtooth**,
  not a trend. By-Congress the medians are cap-dominated (`60,60,60,15,27,60,60`) with no direction.
- Root causes: (a) per-Congress `first_seen` ≠ global first appearance; (b) a 2-year peak-search
  window + 60-day cap; (c) recurring phrases conflate first-ever appearance with eventual biggest day;
  (d) shard-edge right-censoring of `last_date` (S1.3's identical sawtooth).

**Actions (per §4.4):** both **STOPPED as-specified → verdict ARTIFACT** (confound named). A
self-honesty guard `_year_position_artifact` is added to `wave_s1.py` so the as-specified metric can
never emit a false CONFIRMED on re-run. **Redefinition (deferred to S1.1′/S1.3′):** build a **merged
cross-era daily series** for the 113–119 window (S0.2b — the shards have disjoint date ranges, so a
per-ngram merge is clean), then measure **ignition as an EVENT** (a phrase-day where same-day adopters
rise from `<k` to `≥15` within a `≤14`-day lookback) and **lifespan with explicit right-censoring**
(survival-style, or only phrases whose death is observed inside the window). Each gets its own
kill-fixture before it runs.

**Wave lesson (binding):** genealogy / span hypotheses (S1.1, S1.3; S1.5's `first_seen` weekday is
weakly affected) require the merged substrate; **single-day-event** hypotheses (S1.2 sync ceiling —
one peak day, no span) are safe on the per-Congress substrate. Sequence S1 accordingly.

---

*Fable, 2026-07-15. Forty-seven pre-registered hypotheses, five compute waves, one graveyard.
The archive already knows which of these are true; Opus goes and asks it. Kill without sentiment,
publish the kills, and the survivors will be unimpeachable.*

---

## Amendment A3 + Laws L1-L4 (2026-07-16, Fable Session 13c — Michael-confirmed)

**A3 — the re-baseline.** §0's "~22-28 CONFIRMED from 47" is STRUCK. Measured: 34 tested / 2
CONFIRMED (5.9%); the low end of the old projection required 20 of the remaining 14. The program's
unit is now the **CARD** (publishable artifact: a confirmation, a reversal with teeth, a validated
null / graveyard flagship, or a descriptive series with denominators on its face). Goal: **sustain
1-2 published pieces/month through the midterms.** Inventory at enactment: 8 cards on disk; S4.4
(the Friday Night Dump refutation, positive control 2.10x) and S4.1's per-case valence series
approved as cards 9-10; 8 hypotheses runnable now; the deep annex unlocks behind the CREC
2009-2026 crawl.

**Laws — binding on every future wave; violations are verdict-invalidating:**

- **L1 (lane isolation).** `date_source` is a first-class field; no comparison, half-split, or
  baseline may span the 2021-01-03 provenance seam. All 34 pre-seam verdicts are PENDING
  within-lane re-validation before any publishes (order: S2.3, then S1.9/S2.9). The harness must
  expose the field (it is dropped today at pipeline/search/harness.py:399-427).
- **L2 (substrate before spec).** No hypothesis enters a wave without an on-disk check that every
  source it names exists AND carries the fields its CONFIRM criteria require. "elections.json
  exists" was true and worthless; existence is not the test. (Cost of learning this: 9 of 15
  hypotheses across two waves.)
- **L3 (the placebo targets the headline).** The placebo/null must be computed on the EXACT
  statistic the headline states — S4.2 placebo-tested the blame rate, headlined the outward share,
  and the share hits 100% on random non-shutdown dates.
- **L4 (floors are numbers).** Every power floor and cell minimum is a pre-registered NUMERAL
  before measurement. ">=Floor per cell" is not a registration (S5.2's hole).
