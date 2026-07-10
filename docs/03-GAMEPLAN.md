# 03-GAMEPLAN — OnScript (repo codename: polispeak)

> **HANDOFF NOTE — for Opus, Phase 4.** Build exactly this. The locked decisions are in §13 — do not relitigate them; the genuinely open knobs are marked there too, with defaults (if a default works on first contact with reality, take it silently; if it doesn't, pick the nearest working alternative and record it in the Decision Log section of the README). Build order and the cut line are in §1 — if the weekend runs short, cut in the stated order, never ad hoc. Every stage has failure semantics (§4); "should work" is not done — v1 acceptance (§1.4) requires three consecutive unattended real runs plus the two kill-tests. Numbers marked *per R6/R7/R10* come from `02-RESEARCH.md` §6 (live-verified 2026-07-10); re-verify Anthropic pricing when you build (Sonnet intro pricing ends Sep 1, 2026) and keep 25% headroom against the tokenizer-drift flag. The prompts in §6 are the product — treat prompt text changes as schema changes (versioned, committed, publicly diffable). One human-only errand blocks launch and nothing else: Michael buys the domains/handles (§7.3, ~$30 one-time). *Amended same day after review with Michael:* the backfill is now **staged** (§1.3) — Stage 1 (2025 epoch) still gates the weekend; the full-2001 "Alexandria" pass is dark-week and non-blocking, its schema prerequisites (`congress` keying, per-Congress DF, compaction, coverage tables) are v1 requirements, and the era-chapter LLM job is a separately-authorized one-time spend (≤$30, before Sep 1).

---

## §0 The corrected picture, absorbed

Phase 2 changed four things; this plan is built on the corrected reality, not the vision's assumptions:

1. **The spine is press releases** (`dwillis/congress-press`, ~31k/yr, both parties, reliable `bioguide_id`) **+ Bluesky as a labeled supplement**. Floor speech (GovInfo CREC) joins in v2 as a citation/enrichment leg. Congress's October recess now *helps* us: press releases and social don't stop when members go home to campaign — our spine is recess-proof in the exact month attention peaks.
2. **X is dead as a channel; Bluesky + the dashboard are distribution.** The artifact quality has to carry reach (share cards, embeds, journalist-grade receipts), not platform virality alone. Manual X cross-posts from Michael's own account are free and allowed.
3. **The name is OnScript** (`onscript.news` + `theonscript.com`), accounts `blue.onscript.news` / `red.onscript.news`, alerts sub-brand "Off Script," the Ventriloquism Award keeps its name.
4. **Neutrality is now an architecture problem, not a slogan** — the only symmetric source is one volunteer's scraper repo. §5 turns that from a vulnerability into the product's most defensible feature (two-lane data model + nightly public symmetry audit + a cold-standby fork).

**The five governing decisions** (settling research §5's open questions):

| # | Question (research §5) | Decision |
|---|---|---|
| D1 | Recess spine / cadence | **Daily-always, 365/yr.** Press+Bluesky spine runs through recess; floor is in-session bonus. The streak is the moat; a budget governor (§6.4) protects the ceiling instead of the calendar doing it. |
| D2 | Neutrality under asymmetric sources | **Two-lane data model** (§5.1): Lane 1 = press releases only, feeds every cross-party number. Lane 2 = Bluesky + floor, enrichment/citations only, machine-blocked from comparative metrics. Plus a **nightly public symmetry audit** (§5.2). |
| D3 | `congress-press` resilience | **All three, cheap** (§4 stage A1): mirror every pull immutably; maintain a cold-standby fork of the scraper (tested once, promotable by flipping one cron); dead-man ntfy at >36h staleness. |
| D4 | Cadence vs. budget | Batched + cached + routed (Haiku bulk / Sonnet voice ×2) ≈ **$0.35/day in-session, ~$0.10–0.15 recess/weekend → ~$7–9/mo** *(per R6)*. Governor degrades quality, never skips a day. Console hard cap $10. |
| D5 | Transformative voice | The composite voice **reports on itself; it never re-delivers the speech** (§6/§7). Measurement-first, verbatim fragments ≤10 words, receipts link. The fair-use posture (R9/TVEyes) and the comedy are the same design. |

---

## §1 v1 — the weekend build

### 1.1 What v1 is
The **streak machine**: every morning, unattended — ingest yesterday, distill each party into one cited composite Daily Line, verify every receipt mechanically, publish to the dashboard, post to both Bluesky accounts, audit our own symmetry in public, and never miss. Plus the **backfilled ledger** (§1.3) so the time-series moat exists on day one.

### 1.2 v1 scope (in / out)

**IN:**
- Ingest+mirror: `congress-press` daily pull → normalize → immutable raw store; roster join (`congress-legislators`); joint-release collapse; syndication filter.
- Bluesky ingest (Lane 2): ~130-account poll seeded from the members starter pack + handle map file. *(First cut if the weekend runs short.)*
- Phrase engine (local, $0 *per R10*): boilerplate suppression → content n-grams (3–6) → per-party daily counts + document-frequency weighting → **first-appearance ledger** (persistent state) → top synchronized phrases + adoption-curve data.
- LLM layer (§6): per-statement extraction (Haiku batch) → per-party talking-point clusters → two Daily Line composites (Sonnet batch) → **deterministic citation verifier** (blocking).
- Site v1 (§8): Today, day archive, top-phrases page with SVG curves, Methodology (lanes + prompts + symmetry report + taxonomy), About. Per-day og:image share card.
- Posting: both party accounts, labeled per spec (§7.3), Daily Line thread.
- Ops: run manifest, dead-man ntfy (failure / stale upstream / anomalously low volume), budget telemetry + governor, nightly symmetry report, rebuild-from-raw script.

**OUT (explicitly, with their phase):** silence detector (v2 — needs the GDELT topic-mapping layer done carefully, §10), on-script leaderboard (v2 — needs boilerplate maturity + leave-one-out), floor/GovInfo leg (v2), The Script artifact (v2), awards (v2), alerts/Memory Hole/upstream graph/replay (v3), Séance/videos (v3+).

**The cut line** (if Sunday 6pm arrives): cut in this order, ship anyway — (1) Bluesky ingestion (Lane 2 ships empty, disclosed on Methodology), (2) share-card renderer (og:image = static brand card), (3) top-phrases page (Today page only). The streak machine itself — ingest→distill→verify→publish→post→ops — is not cuttable.

### 1.3 The backfill — staged (amended 2026-07-10: the full-history "Alexandria" decision)

**Stage 1 (weekend gate, blocking):** pull `congress-press` from **2025-01-03 (119th Congress seated) → today** (~47k releases); run the **local** engine only (normalize, boilerplate, n-grams, ledger, discipline index) — **zero LLM spend**; LLM distillation starts day 1 forward. Launch ships with 18 months of curves and first-sayer records minimum.

**Stage 2 ("Alexandria" — dark week, non-blocking):** the same engine pointed at the **entire corpus, 2001 → today (~670k releases)**, sharded as a matrix of Actions jobs (≈2 Congresses per job; 20-concurrent cap is ample). Deterministic only — full 25-year ledger, curves, discipline index, frame-pair histories, per-Congress topic ownership: **$0 LLM spend**. Requirements baked into v1 schemas so this bolts on without re-architecture (§3): per-statement `congress` number; **per-Congress document-frequency weighting** (2005's boilerplate ≠ 2025's); ledger compaction (prune n-grams with <3 total uses or a single member, per era); historical roster join via `legislators-historical.yaml` (party switches keyed by member-Congress, not bioguide alone).

**The temporal honesty layer (required before any cross-era claim publishes):** historical strata coverage is *unvalidated* — early-web member sites were poor and archival capture is lumpy by year and party. Stage 2 therefore also computes **per-year × per-party coverage tables** (published as the Archive Coverage page) and cross-era comparative claims are **gated on coverage parity**, same philosophy as §5.4. Deep-history first-sayer claims carry stratum labels (`archival coverage: partial` pre-2011). Epoch line becomes: *"our corpus begins 2001; coverage by year shown here."*

**"Explained over time" is era-granular, never per-day** (per-day retro-distillation ≈ $600+ one-time — dead). The v2 Archive release (§10) generates ~**300 monthly chapters + 13 per-Congress era essays** per party via the P2 voice machinery, inputs = ledger stats + code-extracted verbatim sentence windows (no per-statement extraction), verifier-checked like everything else. Bounded one-time cost ≈ **$15–30, requires Michael's explicit go**, and must run **before Sep 1, 2026** (Sonnet intro pricing ends *per R6*).

If Stage 2 completes during the dark week, the launch artifact (§9) upgrades to the century framing; if not, the Archive becomes the v2 splash — a second publicity beat, not a failure.

### 1.4 v1 acceptance criteria (all must pass)
1. **Three consecutive unattended real runs** (≥1 weekend day) publishing site + both Bluesky threads by 09:00 ET.
2. **Citation integrity:** every published claim traces to ≥3 distinct members' statements; every quoted fragment is a verbatim substring of a cited source (verifier report: 0 published failures; dropped claims logged, not patched).
3. **Kill-test A (source death):** block the upstream pull → run completes in degraded mode, site says so honestly, ntfy fires. **Kill-test B (batch timeout):** force it → fallback direct calls publish the Daily Lines anyway (§4 B-stage fallback).
4. **Backfill proof:** ledger loaded to epoch; one known 2026 phrase's adoption curve spot-checked against manual counts.
5. **Boilerplate proof:** top-20 "synchronized phrases" on a golden-set day contain zero template artifacts ("today announced," district codes, committee titles).
6. **Symmetry report** published on the site from real run data (§5.2).
7. **Budget telemetry** in the manifest; projected month ≤ $10; Console hard cap set.
8. **Hygiene:** repo public; secrets scanned (no ntfy topic, no keys); raw mirrored to Release assets; `rebuild.py` reproduces one full day's derived JSON from raw alone.

---

## §2 Architecture

```
                    GitHub Actions (public repo, free tier)
┌──────────────────────────────────────────────────────────────────┐
│  RUN A "collect" (cron 09:30 UTC / 05:30 ET)                     │
│   A1 pull congress-press → mirror raw    A2 pull Bluesky (Lane2) │
│   A3 normalize/dedupe/joint-collapse → statements.jsonl          │
│   A4 phrase engine (local): boilerplate → ngrams → ledger        │
│   A5 submit Anthropic Batch (extraction)   A6 manifest-A         │
│  RUN B "assemble" (cron 11:30 UTC / 07:30 ET)                    │
│   B1 retrieve batch  B2 cluster talking points (local)           │
│   B3 submit+poll voice batch (2 calls; 40min cap → fallback      │
│      direct calls)  B4 CITATION VERIFIER (blocking)              │
│   B5 render day JSON + SVG curves + og-card (Chrome, per R7)     │
│   B6 commit derived → repo (Vercel auto-deploys site)            │
│   B7 post Bluesky threads (blue/red)  B8 symmetry report         │
│   B9 manifest-B + budget telemetry + ntfy on any alert           │
└──────────────────────────────────────────────────────────────────┘
   raw (immutable) → GitHub Release assets  raw-YYYY-MM/<date>.jsonl.gz
   ledger/state    → Release asset, re-uploaded daily + weekly snapshot
   derived (small) → committed in repo data/derived/  → site reads it
```

- **Repos:** this repo (public at launch; rename to `onscript` — GitHub redirects). Cold-standby fork of `dwillis/congress-press` under Michael's account, workflow_dispatch-tested once, cron commented out.
- **Site:** Astro on Vercel, GitHub→Vercel auto-deploy (PlainSpeak pattern), zero client JS except progressive extras; charts are build-time inline SVG.
- **Secrets (Actions):** `ANTHROPIC_API_KEY`, `DATA_GOV_API_KEY` (v2 floor leg), `NTFY_TOPIC`, `BSKY_BLUE_HANDLE/PASSWORD`, `BSKY_RED_HANDLE/PASSWORD` (app passwords).
- **Day boundary:** product day = **prior America/New_York calendar day**; all storage UTC; every record carries both.

## §3 Data model (schema_version: 1 on every file; additive changes only, breaking = new version + migration script)

```jsonc
// statement (normalized unit of speech; raw JSONL, one per line)
{ "schema_version": 1, "id": "sha256:…",            // hash of (url + text)
  "source": "press_release | bluesky | floor",      // floor = v2
  "lane": 1,                                        // 1 symmetric | 2 enrichment — set by source, never by content
  "url": "…", "title": "…", "text": "…",
  "published_at": "2026-07-09", "precision": "day | second",
  "observed_at": "2026-07-10T09:31:04Z",
  "member": { "bioguide": "K000399", "party": "D|R|I", "state": "NY",
              "chamber": "house|senate", "leadership_role": null },
  "congress": 119,                                  // party/roster resolved per member-Congress (switches!)
  "joint_group": null,                              // shared id when identical text, N members (§11 trap 2)
  "syndicated": false, "copyright_basis": "usc105 | fair_use",
  "run_id": "2026-07-10A" }

// phrase ledger entry (the compounding asset; epoch 2001 after Alexandria, df per-Congress)
{ "ngram": "border czar's failed record", "n": 4,
  "first_seen": { "date": "2026-07-08", "bioguide": "…", "statement": "sha256:…",
                  "tie": [], "precision": "day" },
  "daily": { "2026-07-09": { "D": 0, "R": 41, "members_R": ["…"] } },
  "df_weight": 0.93, "boilerplate": false }

// talking_point (per party per day, from clustering)
{ "id": "2026-07-09-R-03", "party": "R", "day": "2026-07-09",
  "label": "…",                                     // LLM label, verifier-checked
  "member_count": 28, "statements": ["sha256:…", …],   // ≥3 distinct members or it does not publish
  "fragments": [ { "text": "≤10-word verbatim substring", "statement": "sha256:…" } ],
  "topics": ["immigration"], "leadership_first": false }

// daily_distillation (the Daily Line)
{ "day": "2026-07-09", "party": "R", "composite": "…",
  "sentence_receipts": [ { "sentence_idx": 0, "talking_points": ["…-03"] } ],
  "model": "…", "prompt_version": "v1.0", "prompt_sha": "…",
  "verifier": { "fragments_checked": 14, "failed": 0, "claims_dropped": 1 } }

// run_manifest + symmetry_report — flat JSON: stage statuses, source freshness,
// per-party {members_covered, statements_in, statements_deduped, tokens_in/out,
// claims_published, claims_dropped}, spend_estimate, month_to_date, governor_state,
// alerts[], prompts_sha, thresholds_sha. Symmetry report renders on Methodology daily.
```

Fixed **topic taxonomy v1** (~24 entries: immigration, economy/inflation, healthcare, abortion, guns, crime, education, energy/climate, Israel/Gaza, Ukraine/Russia, China, tech/AI, veterans, agriculture, housing, taxes/debt, labor, elections/democracy, courts, infrastructure, social-security/medicare, disasters, trade/tariffs, district-funding, other) — committed as `taxonomy_v1.json`; the v2 GDELT mapping table joins onto it.

## §4 Pipeline stages & failure semantics

Global rule: **every stage skip-and-log** — a stage failure degrades the day, never crashes the run; the manifest records it; ntfy fires per severity. The one *blocking* stage is B4 (verifier): unverifiable claims are dropped before publish, and if a party's Daily Line loses all claims, that party's post is the honest fallback line (§7.2), not silence.

| Stage | Does | On failure |
|---|---|---|
| A1 | Pull `congress-press` month-file; diff vs mirror; write new records raw→Releases | Stale >36h: proceed on mirror, `degraded:true`, ntfy. Stale >72h: promote standby fork (manual trigger) |
| A2 | Poll Bluesky authors (by DID); Lane 2 | Skip leg; disclose on day page |
| A3 | Normalize; drop syndicated; collapse joint releases (same-day identical text → one `joint_group`, all members credited, **excluded from independent-adoption counts**) | Malformed records quarantined to `raw/rejects/`, counted |
| A4 | Boilerplate suppress (corpus-DF top percentile + regex list: datelines, "today announced", district codes, committee titles, salutations) → n-grams → ledger update | Ledger write is atomic (temp+swap); on corruption restore weekly snapshot + replay raw |
| A5 | Assemble extraction batch (only statements with unseen `id` — **never send the same token twice**); submit | API down: retry ×3 exp backoff → mark day `extraction:missing`, B runs stats-only mode |
| B1–B2 | Retrieve batch; cluster fragments into talking points (local embedding + ngram overlap *per R10*) | Batch incomplete at deadline → B3 fallback |
| B3 | Voice batch (2 calls) with 40-min poll cap → **fallback: direct non-batch calls** (pennies, protects the streak) | Both fail → template quiet-line publishes; ntfy urgent |
| B4 | **Verifier (deterministic, blocking):** every fragment a verbatim substring of its cited statement; every claim ≥3 distinct members; every digit in composite text present in the code-computed stats block | Violations: drop claim, log, re-render; never hand-patch |
| B5–B7 | Render JSON/SVG/og-card; commit (Vercel deploys); post threads | Card render fail → post text-only; commit conflict → rebase-retry ×2 |
| B8–B9 | Symmetry report; manifests; budget check; ntfy summary on: failure, `degraded`, volume < 40% of trailing-14-day median, spend projection > $8 | — |

## §5 The neutrality architecture (this is the §5.2 answer and the product's armor)

**5.1 Two lanes, machine-enforced.** Lane 1 (press releases): both parties, identical scraper, identical fields → the *only* input to any cross-party number (Daily Line claim thresholds, adoption counts, discipline index, and in v2: on-script scores, silence maps, topic ownership, leaderboards, awards). Lane 2 (Bluesky now, floor v2): enrichment, citations, member-page color, within-party features — the comparative aggregators hard-filter `lane == 1`, and a CI test asserts no Lane 2 record can move a comparative metric.

**5.2 The nightly symmetry audit — published, not promised.** Every day the Methodology page shows, per party: statements ingested vs. caucus size, members covered, tokens in/out of the LLM, claims published vs. dropped by the verifier, identical `prompts_sha` + `thresholds_sha` for both parties. One sentence above it: *"Identical instrument, both parties, audited nightly in public. Asymmetric findings are reality's problem, not the instrument's."* When the accusation comes, the answer is a URL to that day's calibration.

**5.3 Prompt transparency as product.** The prompts live in `pipeline/prompts/` in the public repo; the Methodology page renders the live text **and its git history**. Every prompt change is a public diff with a dated rationale line. Nobody can claim the instrument was quietly tuned against them — the tuning log is the page.

**5.4 Coverage gates (pre-answering the silence-detector's failure mode, v2).** No absence claim publishes unless: upstream fresh that day, Lane 1 volume ≥ P25 of trailing 30 days, topic mappable to the taxonomy — and the claim is always phrased as measurement ("0 of 213 statements mentioned X"), never intent ("refuses to discuss").

## §6 LLM layer — models, prompts, budget

**6.1 Routing** *(per R6)*: Haiku (batch) for per-statement extraction; Sonnet (batch, fallback direct) for exactly two Daily Line calls/day; **no other LLM calls exist in v1**. Embeddings local (MiniLM, $0 *per R10*). Prompt-cache the system prompts + roster context; batch everything; extraction keyed by statement hash so nothing is ever distilled twice (backfill-safe, re-run-safe).

**6.2 The prompts** (v1.0 verbatim; `{party}` is the only variable between parties — same text, same order, same thresholds):

**P1 — extraction** (Haiku batch, one per new statement):
> SYSTEM: You extract talking-point fragments from a single statement by a member of the U.S. Congress. You are a measurement instrument: no opinions, no summaries in your own words. Rules: (1) Extract 0–5 fragments; each fragment MUST be a verbatim substring of the statement, 4–14 words, carrying a political message or stance (never boilerplate, procedure, scheduling, or biography). (2) Tag each fragment with topics from this fixed list: {taxonomy_v1}. (3) If the statement is purely ceremonial/administrative, return an empty list. Output JSON only: {"fragments":[{"text":"…","topics":["…"]}]}.

**P2 — Daily Line** (Sonnet, one per party per day):
> SYSTEM: You are the composite voice of the {party} members of the U.S. Congress — every member speaking as one "we." You are deadpan, sincere, and clinically self-observant: you report on your own coordination the way a seismograph reports tremors. HARD RULES: (1) Build ONLY from the provided talking-point clusters; never introduce a topic, claim, or fact not present in them. (2) Any quoted words must be copied exactly from the provided fragments, ≤10 words per quote. (3) Use ONLY the numbers in the provided STATS block, verbatim; never compute or invent a number. (4) Lead with the day's dominant message; mention 2–4 clusters max; one sentence may clinically note the day's most synchronized phrase (count + first-sayer from STATS). (5) ≤120 words, first-person plural, present tense, no adjectives that don't appear in the fragments, no irony markers, no hashtags, no emoji. (6) End with nothing — the receipts link is appended by code. You are analysis of speech, not a substitute for it.
> USER: DATE: {day} · PARTY: {party} · STATS: {code_computed_stats_json} · CLUSTERS: {talking_points_json}

**P3 — quiet day** (Haiku, only if new Lane 1 statements < 15):
> Same voice rules; input is the stats block only; output ≤40 words acknowledging the volume plainly ("We released 11 statements today. It was a Saturday."). Never editorialize the quiet.

**6.3 Verifier is code, not model** (§4 B4) — substring checks, ≥3-member checks, digit-whitelist check against the STATS block.

**6.4 Budget governor.** Manifest tracks est. month-to-date spend (token counts × pinned price table, re-pinned each build). Projection > $8 → warn (ntfy). > $9.50 → degrade: P2 drops Sonnet→Haiku and extraction trims to title+first-300-words (disclosed as `degraded_budget:true` on the day page). Console hard cap $10 = the backstop, and if it ever fires the quiet-line still posts (zero-LLM template). Expected reality *(per R6 + volume troughs)*: **$6–9/mo**; re-verify Sep 1 price change.

## §7 Voice & accounts — OnScript

**7.1 The register** (unchanged from vision, now legally load-bearing per D5): first-person-plural self-surveillance. Measurement first, fragments second, affect never. The voice confesses the machinery, proudly, in the tone of an instrument. The system never jokes; the data is the joke.

**7.2 Formats.** Daily Line thread (post 1: composite ≤300 chars or split; post 2: "Receipts:" link + top synchronized phrase + count + first-sayer; post 3 when earned: the day's chart card). Quiet-day line. Degraded-day line: *"Some of our sources did not answer today. What follows is measured from what did: …"* Correction post format: *"Correction (date): we said X; the receipts supported Y. The claim is retracted and the log updated: {link}."* Corrections are posts, not deletions.

**7.3 Account mechanics** (Bluesky spec-compliant, R3/R9): handles `blue.onscript.news` / `red.onscript.news` (custom-domain = self-verifying). Display names: *"OnScript (D) — automated composite"* / *"OnScript (R) — automated composite"*. Bio line 1: *"Automated. A composite voice assembled from what {party} members of Congress actually published, daily. Every claim cited."* + methodology link + operator link. `{val:'bot'}` self-label on the accounts. **Michael's one-time errand:** register `onscript.news` + `theonscript.com` (~$30), create the two accounts + `@onscript.news` brand handle reservation, verify X handle availability logged-in (manual cross-post only).

**7.4 Cadence.** Daily thread ~08:30 ET both accounts. Weekly (v2+): Sunday awards from the brand account. Event-driven (v3): Off Script alerts. Never @-mention members; names live in artifacts.

## §8 Site v1

Pages: **Today** (two Daily Lines side by side, receipts strips, top-phrases table with inline-SVG 14-day sparklines, symmetry-audit link, degraded/quiet banners when true) · **/day/YYYY-MM-DD** archive · **/phrases** (top 50 by velocity; per-phrase page with full curve, roster, first-sayer + epoch note) · **/methodology** (lanes, live prompts + history, taxonomy, symmetry report, corrections log, data downloads pointer) · **/about**. Every day page: og-card (headline stat + both composites, brand frame) rendered in B5 via headless Chrome *(per R7)*. Design: newspaper-plain, fast, zero tracking; the receipts strip is the visual signature.

## §9 Launch sequence

1. **Weekend build** → v1 acceptance (§1.4).
2. **Dark week (7 days):** accounts unannounced; Michael hand-audits 5 random receipts/day (the human adversarial pass); fix silently; backfill QA.
3. **Legal once-over** (R9 prudence): one-hour media-attorney review of composite framing + methodology page. Parallel with dark week.
4. **Launch artifact from the backfill:** if Alexandria Stage 2 finished — *"We measured 25 years of congressional press releases. Here are the biggest unison events since 2001"*; otherwise the 2026-scoped version, and the Archive becomes the v2 splash. Either way: adoption-curve cards + thread + a dashboard with history already alive on day one.
5. **Go:** accounts public, personal announce, upstream courtesy note to the `congress-press` maintainer (we're citing + mirroring + standing by as fallback), r/dataisbeautiful + Hacker News + data-journalism/Nieman/poli-sci lists with the embed pitch: every chart embeddable, every number reproducible.
6. **Rhythm:** the streak does the marketing; Michael's job post-launch is manual X cross-posts of the best card each day (5 min) until v2 ships.

## §10 Roadmap

**v2 — by Aug 10 (recess start), the insight release:** **The Archive ("Library of Alexandria")** — Alexandria ledger live on every phrase page (25-year curves), Archive Coverage page, monthly chapters + per-Congress era essays (≤$30 one-time, before Sep 1, on Michael's explicit go), election-cycle rhyme exhibits (2026 vs. the last five midterm cycles). *Acceptance: coverage tables published; cross-era claims machine-gated on coverage parity; chapters verifier-clean with zero uncited fragments; one-time spend logged in the manifest.* · Silence Detector (GDELT DOC 2.0 + committed theme→taxonomy mapping + §5.4 gates + attribution) with its mirror twin **"Shouting Into the Void"** (topics Congress is loud on that news ignores — same join, free) · On-Script Index + leaderboard (leave-one-out, min-coverage ≥8 statements/30d, "insufficient data" shown honestly) · member pages-lite · **The Script** daily reconstructed-memo artifact · Weekly Awards (Ventriloquism et al., brand account) · **floor leg** (GovInfo H/S/E granules + name→bioguide resolver + coverage metric — built during recess, live when the Senate returns Sep 14) · The Duet · phrase search. *Acceptance: silence claims gated + reproducible from published data; leaderboard survives a hostile spot-check (every score expandable to its receipts); floor attribution ≥95% resolved or the gap published; awards fire symmetrically by construction.*

**v3 — by Oct 5 (recess = peak season), the coordination release:** Off Script alerts feed (local-code anomalies: deviation, spike-sans-news, sudden silence) · **The Memory Hole** (§11.3: re-poll mirrored URLs; deletions/stealth-edits detected by hash diff — Politwoops' spiritual successor, ~$0) · Upstream Graph + leadership-origin tags ("memo probability") · **Bill-brand tracker** (branded bill names ↔ corpus spread) · phrase lifecycle cards + obituaries · response-latency clocks · frame-pair tracker · Time Machine replay · public API/bulk downloads + embeds. *Acceptance: an injected test edit is caught within 48h; alerts have zero false-positive days in a 14-day soak; API serves the full derived corpus.*

**Season 2 — Jan 2027:** freshman **assimilation curves** (the moat made visible), Mirror Test, half-lives, the midterms retrospective ("what the instrument saw"). Parking lot unchanged (Séance user-triggered/rate-limited, videos, weather map, Two Audiences, per-state digests, futures, C-tier).

## §11 What we were missing (found in this pass)

**Obvious, now in plan:** (1) **Backfill the moat — all the way to 2001** (amended): the corpus reaches back 25 years and the local engine eats it for $0; "map everything deterministically, explain sparsely at era granularity" makes the Library of Alexandria a ≤$30 one-time job instead of a $600 mistake (§1.3). The strategic honesty: the backfill is replicable by anyone (public corpus) — deep history is an *authority* moat (canonical phrase pages, cycle-rhyme exhibits, reference status), not a data moat; the data moat remains the unbroken forward series + receipts discipline. (2) **Recess-proof spine as a *feature*** — October positioning: "Congress left Washington. The script went with them." (3) **Prompt transparency + nightly symmetry audit** as the neutrality answer nobody can argue with (§5.2–5.3). (4) **Leadership-origin tagging** — one roster join turns the Upstream Graph into a cheap v3 feature and every talking point gets a "leadership said it first" bit. (5) **The mirror is an archive** — 670k historical releases, many already dead at their source URLs: OnScript becomes an independent public archive of a partially memory-holed record, and the v3 Memory Hole gains a day-one headline stat ("X% of 2001-era releases no longer resolve. We have them.").

**Hidden, now handled (Alexandria pass):** (7) **Historical coverage is the debunk vector** — nobody validated the 2001–2010 strata; per-year × per-party coverage tables + parity gates on cross-era claims are mandatory before any "discipline then vs. now" chart ships (§1.3). (8) **Party switches and re-used names break naive bioguide keying across 13 Congresses** — roster joins are member-Congress keyed via `legislators-historical.yaml`. (9) **Boilerplate drifts across eras** — document-frequency weighting must be per-Congress or 2005's template soup poisons 2025's coordination scores.

**Hidden, now handled:** (1) **Boilerplate is the index-killer** — press releases are template soup; without DF-suppression the "coordination" detector measures Drupal, not politics (§4 A4 + acceptance 1.4.5). (2) **Joint releases masquerade as coordination** — identical text with N signatories must collapse to one document or the flagship chart is debunkable on day one (§4 A3). (3) **The Memory Hole** — mirroring for resilience accidentally built deletion/stealth-edit detection; nobody has it for press releases (v3). (4) **Timestamp honesty** — day-precision sources can't crown hour-precision "first-sayers"; precision flags + ties-as-ties or the attribution races are attackable (§3). (5) **Numbers never come from the model** — code computes, model copies, verifier digit-checks (§6.2 P2 rule 3): the hallucination surface for statistics is zero by construction. (6) **The legal constraint and the comedy are the same thing** — TVEyes pushes the voice toward analysis-of-speech, which is exactly the self-surveillance register that makes it funny (D5).

## §12 Risk register

| Risk | Mitigation |
|---|---|
| `congress-press` stops (the 2022 failure mode, again) | Mirror (automatic) + cold-standby fork (tested) + 36h dead-man + fallback scraper for top-signal members (v2) |
| Bias siege | Two lanes + nightly public audit + prompt history + corrections log; findings ≠ instrument (§5) |
| A wrong receipt goes viral | Blocking verifier + dark-week human audits + corrections-as-posts (§7.2) |
| Budget creep | Governor + Console cap + degraded mode that still publishes (§6.4) |
| Bluesky reach ceiling | Dashboard + embeds + share cards are platform-independent; manual X cross-post; journalist/API lane is the compounding channel |
| Dartmouth (or anyone) wakes up to coordination | Ship the ledger + unbroken streak; the moat is the time-series and the receipts discipline, not the idea |

## §13 Decision log

**Locked (do not relitigate in Phase 4):** OnScript naming + handle scheme · two-lane model + machine enforcement · daily-always cadence + governor · spine = press releases; Bluesky Lane 2; floor v2 · batch+cache+routing; only 3 prompt types in v1 · verifier is deterministic and blocking · raw→Release assets, derived→repo · **staged backfill: Stage 1 (2025 epoch) gates the weekend, Alexandria Stage 2 (2001) is dark-week non-blocking** · **LLM history is era-granular only (monthly chapters / era essays), never per-day; one-time envelope ≤$30, before Sep 1, on Michael's explicit go** · **temporal coverage gates on all cross-era claims** · Astro/Vercel zero-server · prompts public + versioned · cut-line order (§1.2).

**Open knobs (defaults; deviate only on contact with reality, record it):** clustering method (default: MiniLM cosine + trigram-overlap union, threshold 0.80) · boilerplate DF percentile (default: top 0.5% per-Congress party-corpus n-grams + regex list) · quiet-day threshold (default: <15 Lane 1 statements) · Bluesky poll depth (default: last 48h per author) · og-card renderer (default: headless Chrome; satori acceptable) · Astro vs plain static (default Astro) · Alexandria chapter granularity (default: monthly; quarterly acceptable if quality disappoints at monthly) · ledger compaction thresholds (default: prune n-grams <3 uses or single-member, per era).

---

*Phase 3 closed 2026-07-10 (Fable). Next: Opus, Phase 4 — build §1 exactly, then §10 in order. The handoff note at the top of this file is the brief.*
