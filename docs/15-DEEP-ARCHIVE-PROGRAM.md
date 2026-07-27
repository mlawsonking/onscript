# 15: Deep Archive program, the Record track (v1, Fable, 2026-07-15)

> This document is the execution program for the historical expansion that `docs/14` proved feasible:
> a **symmetric 2001–2026 Congressional Record instrument** (`source=crec`), an extraction probe for
> the LoC press-genre archive, and two audited cross-check lanes, built **in parallel** with the
> launch ladder, the daily streak, and the Search, under explicit non-interference rules. Fable owns
> this doc; Opus executes; the BUILDLOG records; releases remain Michael's act (Constitution VIII).
>
> **Why it earns a program** (not just a backlog row): Alexandria's public framing, "the 25-year
> ledger", is, per Search amendment A1, only *symmetric* back to 2013. That is an integrity debt.
> The CREC track converts the 25-year claim from quietly-coverage-gated to **true because of the design**,
> and it is the only path that does so (14 §ranked-options). Everything else here is supporting cast.

---

## §0 Objects and names

| Lane | Source | Window | Genre | Role |
|------|--------|--------|-------|------|
| `press` | dwillis/congress-press (existing) | 2013–2026 | press releases | **The core source. Untouched.** All current headline numbers. |
| `crec` | GovInfo Congressional Record | **2001–2026** | floor speech + **Extensions of Remarks** | The symmetric deep instrument. E-lane (Extensions) = press-release analogue; H/S-lane (floor debate) = secondary, attribution-flagged. |
| `dcinbox` | DCinbox e-newsletters | 2010–2012 (usable to 2021) | e-newsletters | Independent both-party **cross-check** (R-leaning, uncorrelated with the core source's D-lean). |
| `academic_archive` | Grimmer (Senate 2005–07) + Wang (≤2012) | 2005–2012 | press releases | Existence lookups + cross-checks. **Never census numbers** (survivor-biased). |
| `loc_webarchive` | LoC Congressional Web Archive | 2003–2012 | member websites (press pages) | **Conditional**, exists only if the D2 extraction probe passes its gate. |
| `wayback` | Internet Archive CDX | per-member | press pages | Single-member longitudinal color, coverage-gated. Never aggregated. **No build wave**, used ad hoc under the audit. |

**The two laws that make this safe to build at all** (from 14, now binding program-wide):

1. **GENRE ISOLATION (in code).** Cross-era comparisons live **within one lane only** (crec-2005 vs
   crec-2019 ✓; press-2013 vs press-2026 ✓; crec-2008 vs press-2015 ✗, that is a genre confound in a
   trend costume). The finding-card writer and the site renderer refuse any series mixing `source`
   values. Failure fixture required (D0).
2. **THE CALIBRATION LAW.** No CREC-only pre-2013 claim publishes until its metric has been computed on
   **both** instruments over the **2013–2026 overlap** and the directions agree. The overlap is the
   bridge that lets the deep past borrow the core source's credibility, without it, "coordination in 2005"
   is an assertion about an instrument nobody has validated. (The calibration study itself is a
   publishable methods piece, SD.8.)

---

## §1 The non-interference contract (checked at the top of every session)

The four workstreams and what each may touch:

| Workstream | Owns | May NOT touch |
|---|---|---|
| **Streak/launch (S2→S3)** | daily pipeline, site, posting, workflows |, (highest priority) |
| **Search (12/13)** | `pipeline/search/`, `data/derived/search/`, `data/derived/findings/`, docs 12/13 | daily pipeline paths |
| **Deep Archive (this)** | `pipeline/deep/` (new), `X:\onscript-data\crec|dcinbox|academic\` (new), docs 15 | daily pipeline paths, `pipeline/search/` internals (read-only reuse), anything in Actions |
| **Build Program (11)** | v2/v3 features behind FEATURES |, |

Rules:

1. **Zero shared code paths with the daily pipeline.** All Deep Archive code lives in `pipeline/deep/`
   (new modules only). The existing `PhraseEngine`, `boilerplate`, and the Search's streaming reader
   and metrics library are **reused read-only via imports, additive helper functions only, never
   edits** to `pipeline/phrases.py`, `normalize.py`, or any RUN A/RUN B module. The streak cannot be
   destabilized because of the design, not by care.
2. **Zero GitHub Actions usage.** Ingest is one-time capex → the local box (§1.3 generator policy),
   run as **resumable background crawls** with manifest checkpoints, throttled (≤3 req/s, identified
   User-Agent). The daily cron never contends with this program for anything.
3. **Storage: X: only.** Raw mirrors are immutable append-only under `X:\onscript-data\<lane>\raw\`;
   derived under `X:\onscript-data\<lane>\state\`. Nothing bulk on C:. (X: has ~1.9 TB free; the whole
   program is ≤ ~25 GB.) In-repo: only small derived JSON + reference tables + docs, same as today.
4. **FEATURES-dark.** Any site-facing rendering of CREC/era material is a v2+ release behind the
   FEATURES registry, built dark, released by Michael's one commit. This program produces
   *instruments and findings*, not public pages.
5. **Session yield order:** streak incident > launch gate (unattended greens, dark-week jobs) > Search
   waves > Deep Archive waves > Build-Program shelf. Deep Archive is explicitly the yielding track:
   it slips without ceremony. Crawls, however, run **between** sessions (unattended, resumable), so
   calendar time is cheap even when session time is contested.
6. **Search coordination:** the Search continues precisely as pre-registered on the `press` core source ,
   nothing in 12/13 changes. Deep-archive hypotheses are pre-registered HERE (§4, "SD" ids) under 12's
   §1 standards verbatim; verdicts land in the same `13-SEARCH-LEDGER.md` (one ledger, clearly
   lane-tagged) so the graveyard/tally stays unified. The Search's S1′ merged-substrate work and the
   D-waves share the streaming reader but write to different caches, no contention.
7. **Mirror-first rule.** The moment a lane is touched, its upstream is mirrored immutably to X:
   (DCinbox's dumps stopped 2021-09; Grimmer/Wang are single-repo academic artifacts; these can vanish).
   Mirror before measure, always.

---

## §2 Wave D0, rails first (one session)

Everything later rides these; nothing later is trusted without them.

- **D0.1 `pipeline/deep/audit.py`, the 7-gate coverage audit as CODE** (from 14): both-party floor
  (≥5 attributed members/party in-window), symmetry ratio (min/max ≥ 0.33), attribution-completeness %
  per section, integrity rate (stub/boilerplate rejection reported), 100% provenance (URL + capture
  date + stable ID or it does not enter), genre-isolation guard, temporal-coverage gate (A1-style).
  **Failure fixtures:** a synthetic 29 D / 0 R lane must be rejected; a mixed-lane series must raise; an
  audit pass must be reproducible from the emitted audit JSON.
- **D0.2 Lane plumbing:** `source` tag threaded through deep-lane statement dicts (the press core source's
  schema is untouched, its absence of a tag means `press`); per-lane storage layout on X:; the
  resumable-crawl manifest format (`fetched.jsonl` checkpoint + politeness config).
- **D0.3 Mirrors:** DCinbox 141 monthly CSVs + Grimmer/Wang repos → `X:\onscript-data\<lane>\raw\`,
  hash-manifested. (~1 GB total; one background pull.)
- **D0.4 CREC reference tables** under `data/reference/search/`: session calendar cross-check, the
  granule-class allowlist (HOUSE / SENATE / EXTENSIONS; DAILYDIGEST excluded), the CREC-specific
  boilerplate seed list ("Mr. Speaker", "I yield back", "unanimous consent", page headers `[[Page
  E1403]]`), versioned, source-cited, extendable during D1 with dated amendments only.

**Acceptance:** audit module + failure fixtures green in the suite; mirrors hashed; a dry-run audit of the
existing `press` lane reproduces A1's known numbers (the audit validates against ground truth we
already trust).

## §3 Wave D1, the CREC track (the flagship; 2–3 sessions + background crawls)

Build order is Extensions-first: the E-lane is the press-analogue, the smallest high-value slice
(~58 granules/day), and ~98% single-author attributed, it alone justifies the program.

- **D1.a Enumerator + fetcher:** sitemap-driven day discovery (`CREC_{year}_sitemap.xml`) → per-day
  MODS pull → parse `granuleClass` + `congMember` (bioGuideId, party, chamber, role) → fetch granule
  HTML **only** for allowlisted classes with attribution. Resumable, throttled, immutable raw store
  (`X:\onscript-data\crec\raw\{year}\CREC-YYYY-MM-DD\`). **Crawl budget:** ~6,500 day-packages
  2001–2026; E-lane ≈ 350–400k granule fetches ≈ ~35–40h background at 3 req/s, run in year-sized
  resumable chunks between sessions. (Floor H/S adds ~2× later; only after E-lane proves out.)
  *Beware the scout's finding:* `/bulkdata` zips return masked HTML errors, use metadata/content/
  sitemap paths only.
- **D1.b Normalize into the deep schema:** strip Record page furniture, resolve member via bioGuideId
  (no name-parsing, the attribution is structured), emit statements tagged `source=crec`,
  `crec_section=E|H|S`, with granule URL + package date as provenance. Reuse `normalize`'s dedupe
  IDEAS but as new code in `pipeline/deep/` (no edits to the daily module). CREC-specific boilerplate
  suppression applied at n-gram time precisely as the core source does it (same PhraseEngine, imported).
- **D1.c Per-Congress CREC ledger shards** (`X:\onscript-data\crec\state\ledger-{107..119}.json`) via
  the existing tested engine, schema-identical to Alexandria's, so the Search's streaming reader and
  phrase-index builder work unchanged (pointed at the crec state dir).
- **D1.d The audit, published:** per-Congress audit JSON (D/R attributed members, symmetry ratio,
  attribution % by section, granule counts) → `data/derived/crec/audit/` (small, committed). It is
  the artifact that makes every future CREC claim checkable.

**Acceptance:** E-lane 2001–2026 ingested + audited with **every Congress passing the both-party floor
and symmetry gates** (expected, the scout measured 28 D / 21 R Extensions authors on a single 2001
day); ledger shards built; audit JSONs committed; a smoke query ("top Extensions phrases, congress
108, by party") returns sane, citable rows. **Known confounds carried on every artifact:** majority
floor-control (floor time ≠ E-lane, but stated), tribute/commemoration dominance in Extensions
(measured and reported, not hidden, it is itself SD.6's subject), recess darkness.

## §4 Wave D2, the LoC extraction probe (one session; a GATE, not a commitment)

The one open question from 14: LoC coverage is proven symmetric (1,247 member sites; 815 overlap
2003–2012) but playback is Cloudflare-gated → keyless curl cannot extract.

- **Protocol (pre-registered):** stratified sample of **12 members (6 D / 6 R, both chambers, mixed
  tenure)** from the LoC census × 2 capture dates each. Render via the in-app browser (executes JS,
  passes the challenge as a normal reader); attempt to reach each member's press-release listing and
  extract **≥5 dated, attributed releases** per member-capture. Log per-member yield + failure mode
  (challenge-block / dynamic-CMS / no-press-section).
- **Decision gate:** **≥8/12 members yield extractable dated releases → D2 PASSES** → scope a
  `loc_webarchive` lane build (browser-bound crawl; weeks of background calendar time; its own
  pre-registered plan as an amendment here). **<8/12 → the lane is KILLED for v1**; 2001–2002 (and
  press-genre 2003–2012) remains the accurate, disclosed gap; the only revival path is LoC research/WARC
  access, which becomes a **Michael errand** (filed on the bus only if he wants the revival).
- **Rights posture:** LoC states educational/research use; we extract *measurements and short cited
  excerpts* (the same transformative posture as everything else, R9), and the lane ships only with the
  rights note reviewed in the attorney hour (#77's standing agenda).

## §5 Wave D3, cross-check lanes online (one session)

DCinbox (2010–2012 window) + Grimmer/Wang (2005–2012): normalize from the D0 mirrors into their lanes,
run the audit, build small per-lane phrase ledgers. Their entire job: **triangulation**, when a CREC
pre-2013 finding also shows in an independent genre (newsletters, archived press releases), the card
carries a "cross-instrument corroboration" line; when they disagree, that disagreement is reported, not
resolved by picking the friendly number. DCinbox e-mail chrome stripped with its suppression rate
reported (14 §risks).

## §6 Wave D4, the Deep Annex of the Search (1–2 sessions, AFTER D1 audit passes)

Pre-registered here under 12 §1's standards verbatim (split-halves on the CREC lane: **A = 107–112
(2001–2012), B = 113–119 (2013–2026)**, the deep lane is what makes a real A-half possible at last).
Protocol details frozen per-hypothesis in this doc via dated amendment **before** each runs; verdicts
land in 13-SEARCH-LEDGER tagged `lane=crec`.

**The calibration study (runs FIRST, the law demands it):**
- **SD.8 Instrument concordance.** For each already-verdicted press-core source hypothesis with a CREC
  analogue: compute the CREC version over 2013–2026; report directional agreement. Agreement ≥ a
  pre-set share (frozen at amendment time) → the CREC lane is calibrated for that metric family;
  disagreement → that family is press-only, stated. *Either outcome is a publishable methods card.*

**The deep bets (stubs; each gets a frozen protocol before running):**
- **SD.1 The full-span SOTU gravity well**, the one night both parties speak the same words,
  2001–2026 on one instrument. Does the shared-language window shrink across 25 years?
- **SD.2 Voldemort, four presidencies**, opposing-president naming vs euphemism on floor speech
  across Bush → Obama → Trump → Biden → Trump. The press core source only sees 1.5 presidencies clearly;
  CREC sees four+.
- **SD.3 What losing sounds like, five flips**, the power-position signature ("the American people",
  rhetorical questions) across 2006, 2010, 2014(S), 2018, 2022 chamber flips, both parties in both
  roles repeatedly, the strongest possible symmetric design.
- **SD.4 The crisis playbook, 25 years **, 9/11 → Katrina → 2008 → COVID response language:
  latency, unison, decay. Gravity protocol in full; 9/11 unison is likely the largest cross-party
  unison event in the archive ( handled with the weight it deserves).
- **SD.5 The escalation clock**, party-to-party counter-phrase lag on one instrument, 2001→now.
- **SD.6 The tribute economy**, what share of Congress's inserted words honor constituents vs fight
  the other party, 2001→2026 (E-lane composition itself; measured, deadpan, neutral-by-construction).
- **SD.7 The era-anniversary engine** (product, FEATURES-dark), deterministic "N years ago in the
  Record, with receipts" generator; the archive producing perpetual drip anchors ($0, verifier-clean).

**Yield honesty:** expect **+6–12 CONFIRMED cards** from the annex (the deep bets are fewer but
heavier than press-core source oddities), plus the "twice-confirmed" upgrade on several existing findings
via SD.8, a defensibility tier no one else in this lane can print.

---

## §7 Timeline & the parallel weave (calendar-accurate)

- **Now → S3 launch:** Deep Archive costs Michael **nothing**, no launch dependency, no new secrets,
  no Actions, no site changes. D0 can land in the next free Opus slot; D1 crawls run in the background
  between whatever sessions the launch and the Search need. The only shared scarce resource is **Opus
  session time**, governed by §1.5's yield order.
- **Rough sequence (slippable by design):** D0 (1 session) → D1.a crawl starts (background, ~1–2
  weeks calendar in chunks) → Search waves continue in the foreground → D1.b–d as crawl chunks land
  (2 sessions) → D2 probe (1 session, decides LoC) → D3 (1) → D4 calibration + first deep bets (1–2).
  Realistic: **the CREC E-lane audited and queryable within ~3–4 weeks of calendar time** without
  displacing a single launch or Search milestone; floor H/S and any LoC build follow only after the
  E-lane proves out.
- **v2 synergy, not double-build:** D1's ingest **is** BUILD-PROGRAM Wave-1 item 1.6's floor-leg
  ingest (same endpoints, same parser). When v2 releases the floor leg, it consumes the already-built
  `crec` lane behind its own FEATURES gate. One build, two consumers.

## §8 Accurate assessment, is this a meaningful expansion?

It is a meaningful second-order expansion under two conditions.

- **What it provides:**
  - (1) It makes the "25-year archive" claim accurate instead of quietly coverage-gated.
  - (2) It brings 9/11, Iraq, Katrina, the 2008 crash, and the Tea Party into a symmetric system for the
     first time.
  - (3) The SD.8 overlap calibration lets the project mark findings as "twice-confirmed" and use the
     deep past as evidence.
  - (4) It supports the divergence-index and academic co-publication work in HORIZON H6 because a
     25-year, one-system series is citable where a 13-year series is only a footnote.
  - (5) The anniversary engine gives the drip program evergreen anchors at $0.
- **What it does not do:** it does not help the launch, the streak, or the November 2026 attention
  window in any material way, the drip pieces it feeds land months out. It does not fix the
  2001–2002 press-genre gap (and may never). Floor speech is a different behavioral register than
  press releases, and no amount of labeling makes the deep lane *the* product, the core source stays the
  core source.
- **The two conditions:** (1) it holds **last place** in the yield order, the moment it competes
  with a launch gate or a Search wave for a session, it loses, automatically; (2) the calibration law
  is never waived, a 2005 finding that skipped SD.8 is precisely the "fake-complete" failure this
  whole program exists to avoid.
- **Net:** roughly the **second-biggest lever after the Search itself** for what OnScript wants to
  *become* (the system of record), and close to irrelevant for what it must *do this quarter*
  (launch clean and survive). Sized and sequenced accordingly, that is what this program is.

## §9 Amendments

**D4-SD.8 REGISTERED + congresses 111/112/117-119 BUILT + the R-S50.1 isolated substrate rebuilt
(2026-07-27, Opus, Session 51). The overlap is whole; SD.8 is frozen.**

- *Crawl confirmed* (`scripts/deep/crec_state.py`): 111, 112, 117, 118, 119 all buildable. The 2026
  current-year tail was finished first (4 sitemap days uncrawled -> `crawl_crec.py --years 2026`, +87
  Extensions statements) so 119 builds COMPLETE, not `--allow-partial`. Built the five per-Congress CREC
  shards EXACTLY as 113-116 (the §D1-C discipline verbatim: online per-year sitemap completeness,
  settled-unavailable `day-nomods` days counted as SETTLED not pending, no `--allow-partial`, per-shard
  audit committed to `data/derived/crec/audit/congress-{111,112,117,118,119}.json`). Every window PASSES
  symmetric two-party. The CREC lane now spans 107-119 (2001-2026); the SD.8 A=107-112 / B=113-119
  overlap is complete.
- *R-S50.1 substrate* (docs/13 R-S50.1 row): the alexandria per-lane shards are being rebuilt on the
  ISOLATED three-valued `date_source` domain (`legacy` / `scraper` / `page_html`; page_html its OWN lane,
  never folded). `alexandria.load_congress_records` / `lane_shard_path` / `wave_s4._collect` are 3-lane
  (code complete, suite green); `page_html` is built and isolated for all 113-119; `scraper` (page_html
  excluded) is rebuilding in the background (resumable); `legacy` == the existing `propublica` shards by
  identity. The folded `propublica`/`scraped` view survives only as a labelled robustness check. Daily
  pipeline unaffected (does not import alexandria).
- *SD.8 frozen, then run* (docs/13 SD.8 registration + verdict rows): the president-naming
  instrument-concordance study was pre-registered with numeral thresholds BEFORE measurement (frozen
  commit `412308b`), then run on the 2013-2026 overlap. **Verdict: HELD.** The press-core S2.9 direction
  (out-party names the sitting president more) reproduces on the CREC Extensions instrument in only 8/14
  years and is era-split (2013-2020 6/8, but 2021-2026 2/6), below the 0.75 both-eras bar and not a
  systematic contradiction. The CREC lane is therefore NOT calibrated for the naming family, so pre-2013
  (107-112) CREC naming claims do NOT advance to publication (the calibration law working as designed).
  No publication act performed this session. Full evidence in docs/13 and the Session 51 BUILDLOG.

**D1-C (2026-07-21, Opus), congresses 113–116 built + audited; 111/112 are BLOCKED ON A CRAWL THAT
never RAN THEM; and the masked-HTML-error trap turns out to live on the METADATA path too.**

*Session found:* the 2009–2026 crawl was **dead, not running**, a stale lock (`pid 17728`, dead) from
2026-07-17T04:11Z, killed ~25 minutes in. Its year order was `[2013…2026, 2009…2012]`, so it reached
2022 and stopped: **2009–2012 was never crawled at all**, which is precisely the data congresses 111 and
112 are made of. The named deliverable was blocked before it began. Restarted with the order inverted
(`2009,2010,2011,2012` first, then `2022…2026`) so 111/112 unblock soonest; running detached, resumable,
keyless, $0.

- ** THE FINDING, GovInfo serves "Page Not Found" as HTTP 200 with an HTML body on
  `/metadata/pkg/{pkg}/mods.xml`.** It is the `/bulkdata` masked-error behavior §D1.a warns about,
  on a path we trusted. `urlopen` raises nothing; the status is 200; **the payload is the only signal.**
  Ten sitemap-listed days across 2013–2022 return an identical 44,165-byte error page (the Jan-3
  convening days of 2013/14/17/18/19/20/21/22, plus 2022-05-11 and 2022-05-19). The consequences were
  both real and self-perpetuating: the error page was **written into the append-only raw mirror and
  hash-manifested as archival evidence**, and, worse, it was **cached**, so `man.seen(mods_key) and
  mods_file.exists()` read it back off disk on every resume. The same ten days failed to parse on every
  run for six days and **could never heal.** Fixed in `crec.looks_like_mods()` + `crawl_extensions`:
  a non-MODS payload never enters the mirror, a poisoned cache entry is **quarantined to
  `raw/mods/_rejected/` rather than deleted** (what upstream actually served is part of the record), and
  the day is recorded `day-nomods:`, *settled-unavailable*, not pending. That distinction is what makes
  the word "complete" mean anything: counting permanently-unfetchable days as pending puts 100% out of
  reach because of the design. Failure fixture + heal test + happy-path regression in `tests/test_deep_crec.py`,
  mutation-verified 3/3.
- **Congresses 113–116 BUILT + AUDITED** (`ledger|discipline|coverage-{113..116}.json` on X:, audit JSONs
  committed to `data/derived/crec/audit/`). Ledger schema verified **identical** to the 107–110 shards,
  so the Search's streaming reader queries them unchanged. **Every window PASSES symmetric two-party:**
  113 (2013 D=200/R=214 · 2014 D=196/R=212), 114 (2015 D=189/R=221 · 2016 D=183/R=221), 115 (2017
  D=189/R=220 · 2018 D=187/R=214), 116 (2019 D=231/R=192 · 2020 D=220/R=179), member-symmetry ratios
  **0.81–0.93**, ~180–230 members per party per year. 45,366 Extensions statements. *(Ratios are on
  distinct MEMBERS, per `audit.gate_result`; the core source's published D:R figures are statement-shares ,
  different estimators, docs/12 L4. Comparing the two instruments is SD.8's job, not an aside.)*
- **Congress 117 REFUSED, deliberately.** 2021 is complete; **2022 is truncated at 87 of 200 days** (the
  year the old crawl died in). A half-crawled year is indistinguishable from a quiet one once it is
  inside a shard, it just looks like less speech. `build_crec_shards.py` verifies each year's
  days-settled against the **published GovInfo sitemap** and refuses; `--allow-partial` exists and
  stamps `"partial": true` into the audit JSON so the artifact would carry its own caveat.
- **Drivers are TRACKED now** (`scripts/deep/crawl_crec.py`, `build_crec_shards.py`, `crec_state.py`).
  Prior sessions ran these from `scratchpad/`, which is gitignored, so each session re-hand-rolled them ,
  the Session-18 untracked-evidence lesson, applied. The crawl driver also neutralizes the **known
  `crec.py:217` trap** (it overwrites `crawl-stats.json` with only the current run) by snapshotting
  before and merging after; that trap had already destroyed the 2001–2002 record and the whole 2013–2021
  campaign's stats.
- **Smoke query (the §3 acceptance criterion) passes and re-confirms both D4-pre residuals, plus one
  new one.** Top boilerplate-suppressed phrases are citable and sane, but are dominated by (a) **full
  bill titles** ("military construction and veterans affairs and related agencies appropriations act",
  "middle class health benefits tax repeal act of"), residual (a), the nomenclature-segregation item ,
  and (b) **sub-gram windows of one phrase filling five rows**, residual (b), the collapse layer.
  **NEW residual (c): missed-vote explanations** ("i would have voted yea", "on roll call no") are a
  high-volume Extensions genre formula the seed list does not cover, and they surface as top-ranked
  "R coordination" in congress 115. All three must be closed before any crec phrase-COORDINATION card;
  none of them affects the speaker-attribution bets (SD.2/SD.3/SD.6), which stay the ripe ones.
- **SD.8 is NOT started, its precondition is not met.** The calibration study needs the CREC half of
  the full **2013–2026** overlap; 113–116 (2013–2020) is now on the shelf, 117 needs 2022, and 118/119
  need 2023–2026, all in the running crawl. Starting a concordance on a partial overlap would be the
  "fake-complete" failure §8 names as the one thing this program exists to avoid.

**Next Deep Archive session:** confirm the crawl finished (`scripts/deep/crec_state.py`), build 111/112
and 117–119 the same way, then, and only then, freeze and run SD.8. Note the crawl now running
started under the *pre-fix* code, so it will re-poison any Jan-3 days it meets; the next crawl
invocation auto-quarantines them, and `build_crec_shards.py` reads the on-disk evidence directly, so no
build is ever misled in the meantime.

**D1-B (2026-07-16, Opus), the 2001–2008 CREC instrument is COMPLETE (the unique-fill window).** The
Extensions crawl finished 2003–2008 (after a hang fix, day-done markers make resumes O(new-days), see
BUILDLOG), and congresses 108/109/110 are built + audited alongside 107. **Every congress, every year,
PASSES symmetric two-party:** 108 (2003 D=205/R=228; 2004 D=205/R=223), 109 (2005 D=201/R=224; 2006
D=199/R=224), 110 (2007 D=232/R=193; 2008 D=233/R=194), ratios 0.83–0.92, hundreds of members per
party per year, in the exact window the press lane is 100% Democrat. ~57k Extensions statements,
2001–2008; audit JSONs at `data/derived/crec/audit/congress-{107..110}.json`. It is the accurate 25-year
claim made real for its hardest segment. **Remaining CREC:** 2009–2026 (the SD.8 calibration overlap) +
the crec-coordination gate (nomenclature segregation) before any phrase-coordination card; the
speaker-attribution SD.* bets are unblocked now.

**D3-A (2026-07-16, Opus), the academic cross-check lane is LIVE; DCinbox is access-blocked.**
- **`academic_archive` lane INGESTED + AUDITED** (`pipeline/deep/academic.py` + `tests/test_deep_academic.py`):
  Grimmer's Senate press releases parsed from the mirror (filename → ISO date + surname; senator →
  bioguide/party via congress-legislators, fetched keyless + mirrored). **72,635 statements, 112/114
  dirs mapped** (the 2 unmatched are utility dirs), and the coverage audit **PASSES symmetric every year
  2004–2008** (D=37.5k / R=33.4k statements; ratios 0.68–0.98; audit JSON at
  `data/derived/academic/audit.json`). It is the second symmetric both-party historical instrument on
  the shelf, an independent cross-check for **2005–2008**, precisely the window where the press lane is
  single-party. Cross-check only, never census (survivor-biased population), enforced by the lane role.
- **DCinbox BLOCKED (Michael errand #133):** the downloads page (lindseycormack.com) is now
  **password-gated**, not the keyless bulk the scout expected, Opus cannot enter credentials. Filed for
  Michael to request research access. Mirror-first flagged it at-risk (dumps stopped 2021-09); until
  access is obtained, the 2010–2012 e-newsletter cross-check stays dark. The academic lane already
  provides a 2005–2008 cross-check, so it is not blocking.

**D1-A (2026-07-15, Opus), congress 107 ingested + verified; the "weak carrier" confirmed.** The
E-lane crawl + D1.c/d ran end-to-end on **congress 107 (2001–2002): 11,867 symmetric Extensions
statements**, a schema-identical ledger shard (Search-reader-queryable), and a per-year audit that
**PASSES symmetric** (2001 D=211/R=208 ratio 0.99; 2002 D=209/R=211 ratio 0.99), two-party where the
press lane is 100% Democrat. The D1.d audit caught + forced the fix of a real bug (`published_at` was
the package id, not the ISO date). **BUT the ledger's top phrases are dominated by parliamentary
procedure (the Committee-of-the-Whole formula) + bill-title language ("to provide for … and for other
purposes")**, R1's "weak carrier" concern, confirmed on real data. Consequence, binding for the crec
lane:
- **CREC is a WEAK carrier for phrase-COORDINATION metrics** (S1-style adoption curves) without a heavy
  genre-specific boilerplate layer. A first cut of procedural + bill-title seeds is in
  `crec_boilerplate_seeds.json`; the **full CREC coordination-boilerplate suppressor (with its own
  failure fixture) is a prerequisite for any crec-lane SD.* coordination finding** and is queued for D4 ,
  not yet built. No crec coordination card publishes before it exists.
- **CREC's near-term strength is SPEAKER-ATTRIBUTION analysis**, who spoke, when, on which *named*
  entities, which is boilerplate-robust. So the ripe crec deep-annex bets are **SD.2 (Voldemort /
  name-avoidance), SD.6 (the tribute economy), SD.3 (what-losing-sounds-like markers), and floor-vs-
  press**, ahead of phrase-adoption curves. Re-sequence D4 accordingly.
- **Status:** 2003–2008 crawling (background); congresses 108–112 shards build as the crawl lands; then
  2009–2026 for the SD.8 calibration overlap. The system is real and audited; the coordination-
  signal-extraction layer is the accurate remaining work.

**D4-pre (2026-07-16, Opus), the CREC boilerplate suppressor is BUILT (the procedural half).**
`pipeline/deep/crec_boilerplate.py` + `tests/test_deep_crec_boilerplate.py` (failure fixture, incl. the
§1.12 marquee: procedural convergence is NOT read as message coordination). Three precise rules, (1)
sub-run of a procedural formula unless whitelisted (SOTU protected); (2) contains a recognition/yielding/
committee seed; (3) contains high-precision bill-title language, validated on real congress-107: **all
Committee-of-the-Whole procedural furniture removed** (49 phrases suppressed at peak≥6), "state of the
union" correctly survives. **138 tests green.** This clears the *procedural* half of the weak-carrier
problem, enough to unlock the boilerplate-robust SD.* bets (SD.2/SD.6/floor-vs-press) that were already
the priority. **Two documented residuals before a phrase-COORDINATION card ships:** (a) **inserted
bill-text / full bill-title** suppression = the separate **nomenclature-segregation** item (a single
inserted bill purpose-clause still leaks mid-clause fragments; needs the congress.gov bill corpus); (b)
**sub-gram redundancy** = the near-dup collapse layer (already exists for the press lane). A crec
coordination view runs `suppress()` + collapse + nomenclature-tagging; the first is done.

---

*Fable, 2026-07-15. Build the past the way we built the present: mirrored, audited, labeled, and
never merged. The archive doesn't get to be 25 years old by assertion, it earns it one gate at a
time.*
