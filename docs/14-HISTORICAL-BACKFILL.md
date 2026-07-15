# 14-HISTORICAL-BACKFILL — can we fill the 2001–2012 gap rigorously? (feasibility, 2026-07-15)

> **The question (Michael):** the press spine collapses before ~2013 and is single-party (congress 107
> = 94 releases, 100% D, 0 R). Can the 2001–2012 gap be filled **reliably + transparently + accurately**?
> **The bar (non-negotiable):** a source that *looks* complete but is asymmetrically covered is WORSE
> than an honest gap — it hides selection bias behind apparent completeness. So for every source the
> decisive test is: **both parties, at comparable + measurable + documentable coverage, from a
> primary/archival origin, with clean member+date attribution.**
>
> **Method:** a 6-way parallel feasibility scout + adversarial completeness critic (Opus, 2026-07-15),
> each hitting real keyless endpoints and pulling a small live sample. Verdicts are evidence-backed
> (real URLs + real counts), Phase-2 style. Full run: workflow `historical-data-scout`.

## The verdict

**The gap IS fillable — rigorously — but ONLY as separate, explicitly-labeled, coverage-audited
instruments, never as one merged symmetric press series.** One source (CREC) fills the full window
symmetrically *by construction*; three more provide real both-party signal for bounded sub-windows as
cross-checks; the naive "just scrape more press releases" routes either reproduce our exact bias or
fail aggregate symmetry. The 2001–2002 press *genre* stays an honest gap unless one unprobed lead (LoC)
clears — but 2001–2012 **floor-speech** symmetry is fully recoverable today.

## Ranked recovery options (strict symmetric-coverage bar)

| # | Source | Window | Both-party symmetry (measured live) | Verdict | Role |
|---|--------|--------|-------------------------------------|---------|------|
| **1** | **CREC — Congressional Record (floor + Extensions of Remarks)** via GovInfo | **2001–2012 + →2026** | Both parties *every sampled day*: 2001-07-24 = 96 D / 78 R speaking; Extensions 28 D / 21 R; 2002-03-13 = 80 D / 58 R. Structured MODS `congMember` (bioGuideId+party) attribution. | **VIABLE** | **The backbone.** Only source that is *both* full-window AND symmetric-by-construction. Separate `source=crec` track. **Extensions of Remarks = the press-release analogue** (single-author, ~98% attributed, both parties). |
| **2** | **DCinbox — congressional e-newsletters** (Cormack) | **2010–2012** | Jan'10 112 D / 110 R (0.98); Jun'11 121 D / 206 R (0.59); Nov'12 107 D / 175 R (0.61); **0 unmapped bioguides.** | **VIABLE-WITH-CHANGES** | Independent both-party **cross-check**; its R-lean is *uncorrelated* with the spine's D-lean → a genuine validation instrument for 2011–12, not filler. Keyless bulk CSVs (141 monthly; dumps end 2021-09 → mirror on first ingest). |
| **3** | **Academic — Grimmer (Senate press releases) + Wang** | **2005–2012** | Grimmer Senate ~50/50; Wang ~40 R / 60 D over 142 members — but per-year balance NOT uniform (span = tenure). | **VIABLE-WITH-CHANGES** | Real both-party *press releases* for a bounded window. **Cross-checks + "did this phrase exist in 2008?" lookups only — never headline census** (survivor-biased population). Keyless GitHub/Dataverse. |
| **4** | **Wayback/CDX — members' own press pages** | per-member sub-windows | **Fails aggregate symmetry:** 100×+ per-member yield variance (Leahy ~2,384 vs Grassley pre-2008 ~0); soft-404 stubs inflate raw counts; dynamic-CMS members unrecoverable. | **VIABLE-WITH-CHANGES** | Right genre (merge-compatible press text) but no aggregate two-party density. **Single-member longitudinal color only, coverage-gated.** |
| **5** | **LoC "United States Congressional Web Archive"** ⭐ | **Dec 2002 →** | *Curated, all-member by design* (targets every member incl. departed ones — symmetric on the axis that kills generic Wayback). Not yet sampled. | **NEEDS-DEEPER-PROBE** | **The #1 lead** — could be the symmetric **press-genre** backfill for **2003–2012** that nothing else provides. Keyless, catalogued (coverage measurable pre-ingest). **Probe before accepting any press-genre gap for 2003+.** |

**DEAD (instructive):** *GovInfo/GPO-other* — no press releases exist in that window anywhere in the
collection; ProPublica's press corpus starts 2013. *Reachback/commercial* — the dwillis "legacy import"
**reproduces our exact asymmetry** (2001-01 = 8 D / 0 R; 2009-06 = 29 D / **0 R**, one member dominating)
= the textbook coverage-bias failure and the proof the gap is a source property, not a bug; congress.gov
has no press-release collection + is keyless-blocked; ProQuest/LexisNexis/C-SPAN are paywalled and/or
wrong-genre. **Keep the honest gap over any of these.** (Also considered + rejected: GovInfo CHRG
hearings (genre), congressional tweet archives (2017+, dead predecessor's lane), university member-papers
(asymmetric, non-machine).)

## The honest build — instrument-by-window (every lane labeled, schema-tagged, never silently merged)

- **Press spine — 2013–2026** (`source=press`, primary, merge-safe): the existing dwillis two-party
  corpus. **Untouched.** All headline discipline/coordination numbers live here.
- **CREC floor + Extensions track — 2001–2026** (`source=crec`, separate): the backfill backbone and the
  *only* symmetric 2001–2012 fill. **Extensions of Remarks** = primary press-release analogue; House/
  Senate floor debate = secondary lane carrying a published attribution-completeness flag.
- **DCinbox e-newsletter bridge — 2010–2012** (`source=dcinbox`, separate): independent both-party
  cross-check / validation instrument.
- **Academic archive lane — 2005–2012** (`source=academic_archive`, separate; Wang truncated ≤2012-12-31
  to not double-count the clean spine): cross-checks and existence lookups only, **never** census numbers.
- **Wayback per-member lane** (`source=wayback`, coverage-gated): opportunistic single-member color; never
  aggregated.
- **2001–2002 press-genre = honest, disclosed gap** — unless the **LoC** probe (Dec 2002+) clears text
  extraction + access terms, in which case a `source=loc_webarchive` lane for **2003–2012** could
  outrank Wayback and rival CREC for the press genre.

## The coverage audit — every new lane passes this before ANY finding rides on it

Default posture: *fill only where symmetry is proven; otherwise honest gap.* Enforced **in code**, not
just docs.

1. **Both-party floor:** ≥ **5 distinct attributed members per party** in the window (margin over the ≥3
   citation floor). Below floor for either party → metric suppressed, window labeled single-party/gap.
2. **Symmetry ratio:** `min(D,R) / max(D,R) ≥ 0.33` (no worse than 3:1) for any two-party claim.
   *Blocked example:* dwillis legacy 2009-06 = 29 D / 0 R → ratio 0 → hard reject.
3. **Attribution completeness:** report % of units with machine-verified member+party per section (CREC
   Extensions ~98% ✓; CREC House debate ~50% → flagged/excluded from discipline metrics; DCinbox 100%).
4. **Integrity rate:** Wayback — % of 200-status URLs that are soft-404 stubs, filtered by digest+length
   and reported; DCinbox — boilerplate/e-mail-chrome suppression rate reported.
5. **Provenance = 100%:** every unit carries source URL + capture/snapshot date + stable ID, or it does
   not enter the ledger.
6. **GENRE ISOLATION — the sharpest gate:** separate lanes are necessary but NOT sufficient. The real
   trap is a sentence like *"coordination rose from 2008 to 2015"* that silently compares CREC floor
   speech (2008) to the press spine (2015) — a genre confound wearing a temporal-trend costume.
   **Cross-era comparisons are permitted ONLY within a single instrument** (crec-2008 vs crec-2015;
   press-2013 vs press-2026), never across lanes. **Enforce in code.**
7. **Temporal-coverage gate (A1):** every cross-era claim gated on measured coverage in *both* eras.

## Recommendation

**Yes — build it, and it can be done to our standard.** Concretely, in priority order:

1. **Probe the LoC Congressional Web Archive next** (the one decisive open question). If it delivers
   symmetric, extractable, dated press-genre text for 2003–2012, it changes the whole picture — a
   merge-adjacent press backfill, not just a floor proxy. Cheap to probe, potentially the biggest unlock.
2. **Build the CREC track** (`source=crec`) — the flagship win, keyless, public domain, ~5–15 GB on X:,
   ~1–2 build sessions. This already overlaps BUILD-PROGRAM Wave-1 item 1.6 (the "floor leg"); this scout
   confirms it and extends it to the **full 25-year backfill + Extensions of Remarks as the press
   analogue**. It gives the Search a *genuinely 25-year symmetric* instrument (its own track), lifting
   amendment A1's 2013-only ceiling for every hypothesis that has a floor-speech version.
3. **Add DCinbox (2010–2012) + Grimmer/Wang (2005–2012) as cross-check lanes** behind the coverage audit.
4. **Keep 2001–2002 press-genre as an honest, disclosed gap** unless LoC clears it.

**Bottom line:** the "25-year symmetric archive" is real after all — but as a **Congressional Record
instrument**, clearly labeled and never merged into the press spine, with Extensions of Remarks as the
press-release analogue and three audited cross-check lanes around it. We don't get the gap for free, and
we don't get it by pretending — we get it by building the right instrument for each window and proving
symmetry before we publish a number.

---

*Feasibility groundwork, Opus 2026-07-15. Scout evidence + critic in the workflow transcript. Next: the
LoC probe, then the CREC ingest build.*
