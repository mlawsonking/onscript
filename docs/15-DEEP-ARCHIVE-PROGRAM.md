# 15-DEEP-ARCHIVE-PROGRAM — the Record track (v1, Fable, 2026-07-15)

> **What this is.** The execution program for the historical expansion that `docs/14` proved feasible:
> a **symmetric 2001–2026 Congressional Record instrument** (`source=crec`), an extraction probe for
> the LoC press-genre archive, and two audited cross-check lanes — built **in parallel** with the
> launch ladder, the daily streak, and the Search, under explicit non-interference rules. Fable owns
> this doc; Opus executes; the BUILDLOG records; releases remain Michael's act (Constitution VIII).
>
> **Why it earns a program** (not just a backlog row): Alexandria's public framing — "the 25-year
> ledger" — is, per Search amendment A1, only *symmetric* back to 2013. That is an integrity debt.
> The CREC track converts the 25-year claim from quietly-coverage-gated to **true by construction**,
> and it is the only path that does so (14 §ranked-options). Everything else here is supporting cast.

---

## §0 Objects and names

| Lane | Source | Window | Genre | Role |
|------|--------|--------|-------|------|
| `press` | dwillis/congress-press (existing) | 2013–2026 | press releases | **The spine. Untouched.** All current headline numbers. |
| `crec` | GovInfo Congressional Record | **2001–2026** | floor speech + **Extensions of Remarks** | The symmetric deep instrument. E-lane (Extensions) = press-release analogue; H/S-lane (floor debate) = secondary, attribution-flagged. |
| `dcinbox` | DCinbox e-newsletters | 2010–2012 (usable to 2021) | e-newsletters | Independent both-party **cross-check** (R-leaning — uncorrelated with the spine's D-lean). |
| `academic_archive` | Grimmer (Senate 2005–07) + Wang (≤2012) | 2005–2012 | press releases | Existence lookups + cross-checks. **Never census numbers** (survivor-biased). |
| `loc_webarchive` | LoC Congressional Web Archive | 2003–2012 | member websites (press pages) | **Conditional** — exists only if the D2 extraction probe passes its gate. |
| `wayback` | Internet Archive CDX | per-member | press pages | Single-member longitudinal color, coverage-gated. Never aggregated. **No build wave** — used ad hoc under the audit. |

**The two laws that make this safe to build at all** (from 14, now binding program-wide):

1. **GENRE ISOLATION (in code).** Cross-era comparisons live **within one lane only** (crec-2005 vs
   crec-2019 ✓; press-2013 vs press-2026 ✓; crec-2008 vs press-2015 ✗ — that is a genre confound in a
   trend costume). The finding-card writer and the site renderer refuse any series mixing `source`
   values. Kill-fixture required (D0).
2. **THE CALIBRATION LAW.** No CREC-only pre-2013 claim publishes until its metric has been computed on
   **both** instruments over the **2013–2026 overlap** and the directions agree. The overlap is the
   bridge that lets the deep past borrow the spine's credibility — without it, "coordination in 2005"
   is an assertion about an instrument nobody has validated. (The calibration study itself is a
   publishable methods piece — SD.8.)

---

## §1 The non-interference contract (checked at the top of every session)

The four workstreams and what each may touch:

| Workstream | Owns | May NOT touch |
|---|---|---|
| **Streak/launch (S2→S3)** | daily pipeline, site, posting, workflows | — (highest priority) |
| **Search (12/13)** | `pipeline/search/`, `data/derived/search/`, `data/derived/findings/`, docs 12/13 | daily pipeline paths |
| **Deep Archive (this)** | `pipeline/deep/` (new), `X:\onscript-data\crec|dcinbox|academic\` (new), docs 15 | daily pipeline paths, `pipeline/search/` internals (read-only reuse), anything in Actions |
| **Build Program (11)** | v2/v3 features behind FEATURES | — |

Rules:

1. **Zero shared code paths with the daily pipeline.** All Deep Archive code lives in `pipeline/deep/`
   (new modules only). The existing `PhraseEngine`, `boilerplate`, and the Search's streaming reader
   and metrics library are **reused read-only via imports — additive helper functions only, never
   edits** to `pipeline/phrases.py`, `normalize.py`, or any RUN A/RUN B module. The streak cannot be
   destabilized by construction, not by care.
2. **Zero GitHub Actions usage.** Ingest is one-time capex → the local box (§1.3 generator policy),
   run as **resumable background crawls** with manifest checkpoints, throttled (≤3 req/s, identified
   User-Agent). The daily cron never contends with this program for anything.
3. **Storage: X: only.** Raw mirrors are immutable append-only under `X:\onscript-data\<lane>\raw\`;
   derived under `X:\onscript-data\<lane>\state\`. Nothing bulk on C:. (X: has ~1.9 TB free; the whole
   program is ≤ ~25 GB.) In-repo: only small derived JSON + reference tables + docs, same as today.
4. **FEATURES-dark.** Any site-facing rendering of CREC/era material is a v2+ release behind the
   FEATURES registry — built dark, released by Michael's one commit. This program produces
   *instruments and findings*, not public pages.
5. **Session yield order:** streak incident > launch gate (unattended greens, dark-week jobs) > Search
   waves > Deep Archive waves > Build-Program shelf. Deep Archive is explicitly the yielding track:
   it slips without ceremony. Crawls, however, run **between** sessions (unattended, resumable), so
   calendar time is cheap even when session time is contested.
6. **Search coordination:** the Search continues exactly as pre-registered on the `press` spine —
   nothing in 12/13 changes. Deep-archive hypotheses are pre-registered HERE (§4, "SD" ids) under 12's
   §1 standards verbatim; verdicts land in the same `13-SEARCH-LEDGER.md` (one ledger, clearly
   lane-tagged) so the graveyard/tally stays unified. The Search's S1′ merged-substrate work and the
   D-waves share the streaming reader but write to different caches — no contention.
7. **Mirror-first doctrine.** The moment a lane is touched, its upstream is mirrored immutably to X:
   (DCinbox's dumps stopped 2021-09; Grimmer/Wang are single-repo academic artifacts; these can vanish).
   Mirror before measure, always.

---

## §2 Wave D0 — rails first (one session)

Everything later rides these; nothing later is trusted without them.

- **D0.1 `pipeline/deep/audit.py` — the 7-gate coverage audit as CODE** (from 14): both-party floor
  (≥5 attributed members/party in-window), symmetry ratio (min/max ≥ 0.33), attribution-completeness %
  per section, integrity rate (stub/boilerplate rejection reported), 100% provenance (URL + capture
  date + stable ID or it does not enter), genre-isolation guard, temporal-coverage gate (A1-style).
  **Kill-fixtures:** a synthetic 29 D / 0 R lane must be rejected; a mixed-lane series must raise; an
  audit pass must be reproducible from the emitted audit JSON.
- **D0.2 Lane plumbing:** `source` tag threaded through deep-lane statement dicts (the press spine's
  schema is untouched — its absence of a tag means `press`); per-lane storage layout on X:; the
  resumable-crawl manifest format (`fetched.jsonl` checkpoint + politeness config).
- **D0.3 Mirrors:** DCinbox 141 monthly CSVs + Grimmer/Wang repos → `X:\onscript-data\<lane>\raw\`,
  hash-manifested. (~1 GB total; one background pull.)
- **D0.4 CREC reference tables** under `data/reference/search/`: session calendar cross-check, the
  granule-class allowlist (HOUSE / SENATE / EXTENSIONS; DAILYDIGEST excluded), the CREC-specific
  boilerplate seed list ("Mr. Speaker", "I yield back", "unanimous consent", page headers `[[Page
  E1403]]`) — versioned, source-cited, extendable during D1 with dated amendments only.

**Acceptance:** audit module + kill-fixtures green in the suite; mirrors hashed; a dry-run audit of the
existing `press` lane reproduces A1's known numbers (the audit validates against ground truth we
already trust).

## §3 Wave D1 — the CREC track (the flagship; 2–3 sessions + background crawls)

Build order is Extensions-first: the E-lane is the press-analogue, the smallest high-value slice
(~58 granules/day), and ~98% single-author attributed — it alone justifies the program.

- **D1.a Enumerator + fetcher:** sitemap-driven day discovery (`CREC_{year}_sitemap.xml`) → per-day
  MODS pull → parse `granuleClass` + `congMember` (bioGuideId, party, chamber, role) → fetch granule
  HTML **only** for allowlisted classes with attribution. Resumable, throttled, immutable raw store
  (`X:\onscript-data\crec\raw\{year}\CREC-YYYY-MM-DD\`). **Crawl budget:** ~6,500 day-packages
  2001–2026; E-lane ≈ 350–400k granule fetches ≈ ~35–40h background at 3 req/s — run in year-sized
  resumable chunks between sessions. (Floor H/S adds ~2× later; only after E-lane proves out.)
  *Beware the scout's finding:* `/bulkdata` zips return masked HTML errors — use metadata/content/
  sitemap paths only.
- **D1.b Normalize into the deep schema:** strip Record page furniture, resolve member via bioGuideId
  (no name-parsing — the attribution is structured), emit statements tagged `source=crec`,
  `crec_section=E|H|S`, with granule URL + package date as provenance. Reuse `normalize`'s dedupe
  IDEAS but as new code in `pipeline/deep/` (no edits to the daily module). CREC-specific boilerplate
  suppression applied at n-gram time exactly as the spine does it (same PhraseEngine, imported).
- **D1.c Per-Congress CREC ledger shards** (`X:\onscript-data\crec\state\ledger-{107..119}.json`) via
  the existing tested engine — schema-identical to Alexandria's, so the Search's streaming reader and
  phrase-index builder work unchanged (pointed at the crec state dir).
- **D1.d The audit, published:** per-Congress audit JSON (D/R attributed members, symmetry ratio,
  attribution % by section, granule counts) → `data/derived/crec/audit/` (small, committed). This is
  the artifact that makes every future CREC claim checkable.

**Acceptance:** E-lane 2001–2026 ingested + audited with **every Congress passing the both-party floor
and symmetry gates** (expected — the scout measured 28 D / 21 R Extensions authors on a single 2001
day); ledger shards built; audit JSONs committed; a smoke query ("top Extensions phrases, congress
108, by party") returns sane, citable rows. **Known confounds carried on every artifact:** majority
floor-control (floor time ≠ E-lane, but stated), tribute/commemoration dominance in Extensions
(measured and reported, not hidden — it is itself SD.6's subject), recess darkness.

## §4 Wave D2 — the LoC extraction probe (one session; a GATE, not a commitment)

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
  press-genre 2003–2012) remains the honest, disclosed gap; the only revival path is LoC research/WARC
  access — which becomes a **Michael errand** (filed on the bus only if he wants the revival).
- **Rights posture:** LoC states educational/research use; we extract *measurements and short cited
  excerpts* (the same transformative posture as everything else, R9), and the lane ships only with the
  rights note reviewed in the attorney hour (#77's standing agenda).

## §5 Wave D3 — cross-check lanes online (one session)

DCinbox (2010–2012 window) + Grimmer/Wang (2005–2012): normalize from the D0 mirrors into their lanes,
run the audit, build small per-lane phrase ledgers. Their entire job: **triangulation** — when a CREC
pre-2013 finding also shows in an independent genre (newsletters, archived press releases), the card
carries a "cross-instrument corroboration" line; when they disagree, that disagreement is reported, not
resolved by picking the friendly number. DCinbox e-mail chrome stripped with its suppression rate
reported (14 §risks).

## §6 Wave D4 — the Deep Annex of the Search (1–2 sessions, AFTER D1 audit passes)

Pre-registered here under 12 §1's standards verbatim (split-halves on the CREC lane: **A = 107–112
(2001–2012), B = 113–119 (2013–2026)** — the deep lane is what makes a real A-half possible at last).
Protocol details frozen per-hypothesis in this doc via dated amendment **before** each runs; verdicts
land in 13-SEARCH-LEDGER tagged `lane=crec`.

**The calibration study (runs FIRST — the law demands it):**
- **SD.8 Instrument concordance.** For each already-verdicted press-spine hypothesis with a CREC
  analogue: compute the CREC version over 2013–2026; report directional agreement. Agreement ≥ a
  pre-set share (frozen at amendment time) → the CREC lane is calibrated for that metric family;
  disagreement → that family is press-only, stated. *Either outcome is a publishable methods card.*

**The deep bets (stubs; each gets a frozen protocol before running):**
- **SD.1 The full-span SOTU gravity well** — the one night both parties speak the same words,
  2001–2026 on one instrument. Does the shared-language window shrink across 25 years?
- **SD.2 Voldemort, four presidencies** — opposing-president naming vs euphemism on floor speech
  across Bush → Obama → Trump → Biden → Trump. The press spine only sees 1.5 presidencies clearly;
  CREC sees four+.
- **SD.3 What losing sounds like, five flips** — the power-position signature ("the American people",
  rhetorical questions) across 2006, 2010, 2014(S), 2018, 2022 chamber flips — both parties in both
  roles repeatedly, the strongest possible symmetric design.
- **SD.4 The crisis playbook, 25 years ⚠** — 9/11 → Katrina → 2008 → COVID response language:
  latency, unison, decay. Gravity protocol in full; 9/11 unison is likely the largest cross-party
  unison event in the archive (⚠ handled with the weight it deserves).
- **SD.5 The escalation clock** — party-to-party counter-phrase lag on one instrument, 2001→now.
- **SD.6 The tribute economy** — what share of Congress's inserted words honor constituents vs fight
  the other party, 2001→2026 (E-lane composition itself; measured, deadpan, neutral-by-construction).
- **SD.7 The era-anniversary engine** (product, FEATURES-dark) — deterministic "N years ago in the
  Record, with receipts" generator; the archive producing perpetual drip anchors ($0, verifier-clean).

**Yield honesty:** expect **+6–12 CONFIRMED cards** from the annex (the deep bets are fewer but
heavier than press-spine oddities), plus the "twice-confirmed" upgrade on several existing findings
via SD.8 — a defensibility tier no one else in this lane can print.

---

## §7 Timeline & the parallel weave (calendar-honest)

- **Now → S3 launch:** Deep Archive costs Michael **nothing** — no launch dependency, no new secrets,
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

## §8 Honest assessment — is this a meaningful expansion?

**Yes — second-order meaningful, and only under two conditions.** Plainly:

- **What it genuinely buys:** (1) It converts "the 25-year archive" from a quietly coverage-gated
  claim into a **true one** — that is an integrity repair to Alexandria's own branding, and integrity
  is this product's entire moat. (2) It puts 9/11, Iraq, Katrina, the 2008 crash, the Tea Party — the
  eras with the most resonant possible findings — inside a symmetric instrument for the first time.
  (3) The overlap-calibration design (SD.8) plus "twice-confirmed" findings is a defensibility tier
  that turns the deep past into evidence rather than color. (4) It makes the divergence-index /
  academic-co-publication ambitions (HORIZON H6) real: a 25-year one-instrument series is citable;
  a 13-year one is a footnote. (5) The anniversary engine gives the drip program evergreen anchors
  forever, at $0.
- **What it does NOT do:** it does not help the launch, the streak, or the November 2026 attention
  window in any material way — the drip pieces it feeds land months out. It does not fix the
  2001–2002 press-genre gap (and may never). Floor speech is a different behavioral register than
  press releases, and no amount of labeling makes the deep lane *the* product — the spine stays the
  spine.
- **The two conditions:** (1) it holds **last place** in the yield order — the moment it competes
  with a launch gate or a Search wave for a session, it loses, automatically; (2) the calibration law
  is never waived — a 2005 finding that skipped SD.8 is exactly the "fake-complete" failure this
  whole program exists to avoid.
- **Net:** roughly the **second-biggest lever after the Search itself** for what OnScript wants to
  *become* (the instrument of record), and close to irrelevant for what it must *do this quarter*
  (launch clean and survive). Sized and sequenced accordingly — that is what this program is.

## §9 Amendments

**D1-B (2026-07-16, Opus) — the 2001–2008 CREC instrument is COMPLETE (the unique-fill window).** The
Extensions crawl finished 2003–2008 (after a hang fix — day-done markers make resumes O(new-days), see
BUILDLOG), and congresses 108/109/110 are built + audited alongside 107. **Every congress, every year,
PASSES symmetric two-party:** 108 (2003 D=205/R=228; 2004 D=205/R=223), 109 (2005 D=201/R=224; 2006
D=199/R=224), 110 (2007 D=232/R=193; 2008 D=233/R=194) — ratios 0.83–0.92, hundreds of members per
party per year, in the exact window the press lane is 100% Democrat. ~57k Extensions statements,
2001–2008; audit JSONs at `data/derived/crec/audit/congress-{107..110}.json`. This is the honest 25-year
claim made real for its hardest segment. **Remaining CREC:** 2009–2026 (the SD.8 calibration overlap) +
the crec-coordination gate (nomenclature segregation) before any phrase-coordination card; the
speaker-attribution SD.* bets are unblocked now.

**D3-A (2026-07-16, Opus) — the academic cross-check lane is LIVE; DCinbox is access-blocked.**
- **`academic_archive` lane INGESTED + AUDITED** (`pipeline/deep/academic.py` + `tests/test_deep_academic.py`):
  Grimmer's Senate press releases parsed from the mirror (filename → ISO date + surname; senator →
  bioguide/party via congress-legislators, fetched keyless + mirrored). **72,635 statements, 112/114
  dirs mapped** (the 2 unmatched are utility dirs), and the coverage audit **PASSES symmetric every year
  2004–2008** (D=37.5k / R=33.4k statements; ratios 0.68–0.98; audit JSON at
  `data/derived/academic/audit.json`). This is the second symmetric both-party historical instrument on
  the shelf — an independent cross-check for **2005–2008**, exactly the window where the press lane is
  single-party. Cross-check only, never census (survivor-biased population), enforced by the lane role.
- **DCinbox BLOCKED (Michael errand #133):** the downloads page (lindseycormack.com) is now
  **password-gated**, not the keyless bulk the scout expected — Opus cannot enter credentials. Filed for
  Michael to request research access. Mirror-first flagged it at-risk (dumps stopped 2021-09); until
  access is obtained, the 2010–2012 e-newsletter cross-check stays dark. The academic lane already
  provides a 2005–2008 cross-check, so this is not blocking.

**D1-A (2026-07-15, Opus) — congress 107 ingested + verified; the "weak carrier" confirmed.** The
E-lane crawl + D1.c/d ran end-to-end on **congress 107 (2001–2002): 11,867 symmetric Extensions
statements**, a schema-identical ledger shard (Search-reader-queryable), and a per-year audit that
**PASSES symmetric** (2001 D=211/R=208 ratio 0.99; 2002 D=209/R=211 ratio 0.99) — two-party where the
press lane is 100% Democrat. The D1.d audit caught + forced the fix of a real bug (`published_at` was
the package id, not the ISO date). **BUT the ledger's top phrases are dominated by parliamentary
procedure (the Committee-of-the-Whole formula) + bill-title language ("to provide for … and for other
purposes")** — R1's "weak carrier" concern, confirmed on real data. Consequence, binding for the crec
lane:
- **CREC is a WEAK carrier for phrase-COORDINATION metrics** (S1-style adoption curves) without a heavy
  genre-specific boilerplate layer. A first cut of procedural + bill-title seeds is in
  `crec_boilerplate_seeds.json`; the **full CREC coordination-boilerplate suppressor (with its own
  kill-fixture) is a prerequisite for any crec-lane SD.* coordination finding** and is queued for D4 —
  not yet built. No crec coordination card publishes before it exists.
- **CREC's near-term strength is SPEAKER-ATTRIBUTION analysis** — who spoke, when, on which *named*
  entities — which is boilerplate-robust. So the ripe crec deep-annex bets are **SD.2 (Voldemort /
  name-avoidance), SD.6 (the tribute economy), SD.3 (what-losing-sounds-like markers), and floor-vs-
  press**, ahead of phrase-adoption curves. Re-sequence D4 accordingly.
- **Status:** 2003–2008 crawling (background); congresses 108–112 shards build as the crawl lands; then
  2009–2026 for the SD.8 calibration overlap. The instrument is real and audited; the coordination-
  signal-extraction layer is the honest remaining work.

**D4-pre (2026-07-16, Opus) — the CREC boilerplate suppressor is BUILT (the procedural half).**
`pipeline/deep/crec_boilerplate.py` + `tests/test_deep_crec_boilerplate.py` (kill-fixture, incl. the
§1.12 marquee: procedural convergence is NOT read as message coordination). Three precise rules — (1)
sub-run of a procedural formula unless whitelisted (SOTU protected); (2) contains a recognition/yielding/
committee seed; (3) contains high-precision bill-title language — validated on real congress-107: **all
Committee-of-the-Whole procedural furniture removed** (49 phrases suppressed at peak≥6), "state of the
union" correctly survives. **138 tests green.** This clears the *procedural* half of the weak-carrier
problem — enough to unlock the boilerplate-robust SD.* bets (SD.2/SD.6/floor-vs-press) that were already
the priority. **Two documented residuals before a phrase-COORDINATION card ships:** (a) **inserted
bill-text / full bill-title** suppression = the separate **nomenclature-segregation** item (a single
inserted bill purpose-clause still leaks mid-clause fragments; needs the congress.gov bill corpus); (b)
**sub-gram redundancy** = the near-dup collapse layer (already exists for the press lane). A crec
coordination view runs `suppress()` + collapse + nomenclature-tagging; the first is done.

---

*Fable, 2026-07-15. Build the past the way we built the present: mirrored, audited, labeled, and
never merged. The archive doesn't get to be 25 years old by assertion — it earns it one gate at a
time.*
