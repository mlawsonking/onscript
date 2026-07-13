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

**Anatomy of the Ratchet (the off-message day is vanishing).** The FLOOR rose more than the ceiling:
daily-index p10 climbed +0.105 (D) / +0.091 (R) since 2013 vs the p90 ceiling's +0.088 / +0.054. The
ceiling was always high (~0.83); the floor came up to meet it. *Flag:* a large 2021 discontinuity
(p50 D 0.61→0.83) coincides with a release-volume drop — **regime shift vs volume artifact, needs
density control** before claiming.

**Phrase Obituaries (the STOP memo).** Big sustained phrases that died and never returned:
R "american health care act" (peak 184) died **2018-12-20** — GOP stopped saying it right after
losing the House; the COVID-relief phrases (moving forward act, PPP, "coronavirus aid relief and
economic security" = CARES, lower drug costs now act) died 2020-2022 with their bills; R
"with pre-existing conditions" died 2024-10-09. *Needs light curation* to separate political deaths
(AHCA post-midterm) from natural legislative-cycle deaths (a bill's phrase dies when the bill
resolves) and seasonal-phrase artifacts (NDAA).

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

## Still queued (this menu)

Backtest the Detector (large; the go/no-go for live alerts). Distribution List, Asymmetric Silence
Board, Era Fingerprints, and the rest of [08](08-ANALYSIS-MENU.md)'s full ranking. Most historical
member examples remain blocked on the **pre-2025 URL back-join** (the one unblocker).
