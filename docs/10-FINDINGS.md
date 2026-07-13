# 10-FINDINGS — first analysis pass over the 25-year corpus

Session 3 (2026-07-12). Results of running the [08 menu](08-ANALYSIS-MENU.md) analyses on data in
hand. **All numbers are internal/exploratory** — every cross-party or cross-member claim needs the
Constitution's neutrality-review gate + the "press-release voice specifically" framing before it
ships. Verdict legend: ✅ clean · ◐ partial (needs refinement) · ⚠ confounded (needs methodology).

## Meta-finding (the important one)

**Descriptive time-series analyses work cleanly; single-threshold classifiers and per-member
rankings hit confounds and need armor.** The discipline floor/ceiling, election clock, obituaries,
and tick-tock all produced clean, defensible signal. Every attempt to *rank members* or *classify
phrases with one threshold* (on-script leaderboard, naive origination, memo archetypes,
forbidden-lexicon) collapsed to a confound — tenure, volume, corpus-density, or the 2013 coverage
boundary — until controlled. This is the corpus telling us where it's honest by construction and
where publishing requires methodology. It also independently confirms design-review #8: member
rankings are fragile and must ship as raw counts + receipts, never a composite score.

## ✅ Clean findings

**On-script index (party level).** Republicans score higher every one of the 14 dense years
(0.667 vs 0.632 pooled); D leads in zero. Modest, perfectly consistent, holds even in D-House years.
Press-release-specific — inverts the 2022 Twitter-era result. `discipline.json`. NEUTRALITY-GATED.

**Biggest single-day unison events (15 yr).** R "american health care act" 184 (2017-05-04, AHCA
passage); R "tax cuts and jobs act" 166 (2017-11-16); D "deferred action for childhood arrivals" 153
(2017-09-05, DACA rescission); D "the heroes act" 151 (2020-05-15). Event-driven, symmetric.

**Intraday Tick-Tock.** R: 113 offices on "one big beautiful bill" 2025-07-03 (OBBB passage);
D: 90 offices on "state of the union" 2026-02-24 — every row a live `.gov` URL, verifier-ready.
*Caveat/TODO:* normalized corpus kept `published_at` at DATE resolution → same-day cohort, not a
minute-by-minute waterfall. **Pipeline fix: preserve publish time in normalization** unlocks true
intraday.

**Election Clock.** A symmetric pre-election tightening: on-script index rises +0.047 (D) / +0.039
(R) from ~12-20 weeks out to the final 0-3 weeks; both parties hit exactly **0.773 at election week**.
`discipline.json` aligned across the 2014-2024 cycles.

**Anatomy of the Ratchet — CORRECTED (Session 3): the "off-message day is vanishing" claim is
RETRACTED.** I originally reported the floor (p10) rising toward the ceiling as a secular trend. Under
the tail-pass lesson (trend words die), it fails: the floor is **flat 2013→2020** (D p10 0.531 →
0.525; R 0.559 → 0.568) — the *entire* apparent rise is the single 2021 step (D p10 0.525 → 0.716),
the same volume-confounded 2021 regime shift that killed Vanishing Common Tongue. It is a one-time
level shift in a low-volume window, **not** a gradual behavioral ratchet. Still true and descriptive:
the ceiling (p90) was always high (~0.83), discipline is right-skewed. The "vanishing off-day"
narrative does not survive — do not use it.

**Phrase Obituaries (the STOP memo).** Big sustained phrases that died and never returned:
R "american health care act" (peak 184) died **2018-12-20** — GOP stopped saying it right after
losing the House; the COVID-relief phrases (moving forward act, PPP, "coronavirus aid relief and
economic security" = CARES, lower drug costs now act) died 2020-2022 with their bills; R
"with pre-existing conditions" died 2024-10-09. *Needs light curation* to separate political deaths
(AHCA post-midterm) from natural legislative-cycle deaths (a bill's phrase dies when the bill
resolves) and seasonal-phrase artifacts (NDAA).

**Era Fingerprints (the Archive front page).** Log-odds-distinctive phrases per Congress per party
render each era's defining vocabulary — and the **partisan frame-fight is visible in the same bill**:
119th R "one big beautiful bill" / "working families tax cuts" vs D "big **ugly** bill"; 117th D
"build back better" / "american rescue plan" vs R "$3.5 trillion" (the cost attack); 118th R "secure
the border act" / "fiscal responsibility act" vs D "national security supplemental" / "alliance for
hippocratic medicine"; 115th both AHCA, but R adds Gorsuch/Kavanaugh/"corporate tax rate", D adds
"attorney general sessions" / "the trump administration". *One fix needed:* generic procedural
boilerplate ("of the united states", "a member of the senate") leaks to the top — needs a stoplist
on the fingerprint output; the real signal sits just below it. ✅ (compelling; the public Archive's
natural landing page.)

**Distribution List (memo recipient cells).** Member-pair co-launch **lift** (co-appearances vs
volume-predicted) surfaces genuine coordination cells invisible to raw counts: a tight freshman-GOP
House cohort (Kennedy, Onder, Fine, Biggs, Knott, Jack — 30-66× expected, many in the exact same 66
events) and a rural-Senate cluster (Rounds + Sullivan 40×, + Hyde-Smith, Cramer). Raw co-occurrence
just re-finds the high-volume Senate Democrats (lift ~3-4×). ✅ (lift can inflate for low-volume
members — mitigated by a ≥40-event floor). NEUTRALITY-GATED.

**Backtest the Detector — a clean NO-GO (the null is the finding).** Across 1.9M candidate phrases
(day-2 breadth ≥3, 2013-2026), only **0.3% break out** to ≥20 members within 30 days. Day-2 breadth
"predicts" breakout only at the trivial extreme (K=20 → precision 1.0, but that phrase has *already*
broken out); the operating point doesn't transfer across time (fit precision 0.77 → holdout 0.50).
Decisive: **median lead time −1 day; 65% of breakouts had already peaked by day 2** — coordinated
phrases are born at scale, not ramped. Per backtest-before-predict, this **retires the proposed v3
"memo warning / breakout watch" alert feature**: you cannot see the memo coming from public output,
because the memo *is* the simultaneous drop, not an organic pre-phase. The negative result is a strong
finding about the coordination's nature — pre-scheduled, not emergent. ✅ (as a null).

## ◐ Partial — real signal, needs refinement

**Authors vs. Vessels.** Naive origination-by-first-use is **tenure-confounded** (prolific veterans
"author" everything; freshmen forced to "vessel") — RETIRED. Tenure-controlled to the 119th: Chip Roy
(31 caucus-wide phrases solo-launched), Ted Cruz (30), John Thune (18) as authors; Padilla, Welch,
Murray, Tom Cole as pure vessels (500-700 echoed, zero authored); **38% of caucus-wide phrases are
born-coordinated** (multiple day-0 first-sayers = no single author). Per design-review #8: ship as
raw per-member first-sayer/echo COUNTS with receipts, **refuse the composite "Vessel Score."**
NEUTRALITY-GATED.

**Forbidden Lexicon.** Exclusive high-convergence phrases genuinely exist. v3 added a sustained-days
filter: the R side is now clean and revealing — persistent framings with a days-active column
("by an illegal immigrant" sustained **144 days**, peak 33; "penalties for deported felons" 21 days;
"is not a security threat" 21 days; "the keystone xl pipeline approval act"). The D side stays
gravity-locked to the 2020 CARES/HEROES bill text (fragments used across ~2 weeks, so ≥5-days doesn't
drop them); a ≥30-day cross-bill filter is needed. **Hypothesis surfaced:** Democrats quote bill text
verbatim; Republicans coin rhetorical framings — the exclusive-phrase asymmetry may be behavioral,
not just corpus-size. NEUTRALITY-GATED.

## ⚠ Confounded — needs methodology before any claim

**Memo Detector.** The SCHEDULED/CASCADE/SLOW-BURN archetype classification runs. After density
control (restricted to peak 15-30 mid-size phrases, 2013 excluded): **the "getting faster over time"
trend does NOT survive** — year-to-year %scheduled bounces 0-65% with no monotonic acceleration. BUT
a clean, symmetric **election-year effect DOES survive**: phrases launched in election years are
markedly more likely to be born pre-coordinated (SCHEDULED) — **R 33% (election) vs 21% (off-year);
D 25% vs 13%**. Coordination intensifies on the electoral calendar, both parties. → moved from
⚠ confounded to ◐ partial: the election-cycle finding is publishable (neutrality-gated); the secular
acceleration claim is retired. Caveat: driven partly by specific cycles (2020, 2022) — a per-cycle
breakdown should accompany it.

**On-script member leaderboard (naive S4).** Saturates ~99.7% ("used any synced phrase" is
universal). Formally retire the S4-as-specified metric in `01-VISION.md`; replaced by Authors-vs-
Vessels raw counts.

## Tail pass — adversarially verified (Session 3)

Nine more analyses were run, then put through a hostile-skeptic verification workflow (one refuter per
finding + adjudicator) **before** recording. The skeptics killed the headline claim on every one; the
record below is the *survivors only*, reframed to what actually holds.

**The lesson (load-bearing): trend words are where these findings die.** Every finding framed as a
secular trend — "narrowing," "vanishing," "half-life shrinking" — turned out to be an artifact of the
2021 volume regime or birth-date censoring, and each betrayed itself by **rebounding/reversing when the
confound reversed** (a real secular change does not un-happen). Everything that survived did so only
after conversion to a **volume-invariant / fixed-observation-window / marginal-preserving-null**
instrument and downgrade to a **stable-level, sign, or cyclical** claim.

**✅ Reportable (reframed):**
- **Discipline gap is STABLE, not narrowing.** The R-over-D on-script gap holds across all 14 dense
  years (odds ratio ~1.15-1.20; R leads every year *as a sign*, not a magnitude). My "gap is
  narrowing" was **killed** — the erosion was carried entirely by 2023-24 (the 118th House-GOP
  fracture: McCarthy ouster, 3-week speakerless stretch) and fully reversed by 2025-26 with *equal
  endpoints*. The **lockstep** finding survives (YoY co-movement corr 0.68 after removing the 2021
  jump; 11/13 transitions same-direction) and **"does losing make you louder" is a robust null** (the
  2022→23 winner R got *quieter*). Caveats: press-release voice specifically (2022 Twitter gave the
  opposite sign); sign-not-magnitude; neutrality gate.
- **Both parties coin durable exclusive framings** (Forbidden Lexicon v4, ≥30 active days) — this
  *falsifies the absolute* "only R coins framings, D just quotes bill text." **Killed:** the stronger
  "filter-artifact / framing-vs-bill-text refuted" claim — that rate distinction was never tested and
  "framing vs bill text" is subjective human coding (a neutrality-gate violation). A code-owned
  bill-text/CRS-overlap classifier is required before any per-party *rate* claim.
- **Election-year phrases decay far faster** (Phrase Survival, fixed 180-day window, volume-invariant)
  — **CONFIRMED: 19.7% (election-year) vs 71.1% (off-year) six-month survival = 3.6× faster decay**,
  every one of 5 cycles with *no overlap* (every even year below every odd year); volume-invariant
  (2020 had the most phrase births yet the lowest survival, 0.191); holds under the matched-timing
  H1-only control (25% vs 82%). Mechanism = the electoral/Congress transition resetting the agenda,
  not intrinsic election-year coordination. This *replaces* the killed "median half-life" metric
  (right-censoring). The secular "language dying faster over time" version is **rejected** — survival
  is flat within each cycle phase; only the cyclical structure is real. **The single clean new finding
  to survive the full adversarial gauntlet this pass.**

**⚠ Killed / needs a new run (not reported):**
- **Sub-Caucus "coordination cells" — KILLED.** Bare lift ranks *inverse-volume*, so it surfaced the
  party's most *passive echoers* as its "tightest cell" (a freshman pair in the exact same 66 events =
  offices whose entire output IS the party-wide pile-ons) — the opposite of an inner circle — and can
  only re-derive public rosters (freshman class, Senate GOP). Salvageable *only* as a marginal-
  preserving-permutation-null "co-timing graph **recovers** institutional structure (chamber, cohort)"
  — recovery, not discovery; per-chamber thresholds; a convergence-share column to separate followers
  from sources. Do not publish the lift version.
- **Vanishing Common Tongue — KILLED** (volume artifact; the share rebounds to 5.3% when volume
  returns in 2024). **Aisle-Jumpers — KILLED** (surfaces shared institutional vocabulary — NDAA, farm
  bill — peaking in different years, not ownership flips). **The Hush — weak/calendar-confounded**
  (0.87× pre-blast, 55% vs 50% chance). **Lazarus revivals — killed as computed** (measures external
  events' periodicity — appropriations, debt ceiling, two Netanyahu visits); a filtered ledger-only
  pass (periodicity exclusion + context-divergence) is exploratory-untested.

## Verified re-run queue (data in hand, outcome uncertain)
Permutation-null Sub-Caucus (recovery framing) · Lexicon per-party rate via a bill-text/CRS classifier
· Lazarus filtered pass (non-empty = finding, empty = publishable null) · Vanishing Common Tongue
fixed-N Jaccard (lowest priority — predicted to flatten to noise).

## Still queued (this menu)

Backtest the Detector (large; the go/no-go for live alerts). Distribution List, Asymmetric Silence
Board, Era Fingerprints, and the rest of [08](08-ANALYSIS-MENU.md)'s full ranking. Most historical
member examples remain blocked on the **pre-2025 URL back-join** (the one unblocker).
