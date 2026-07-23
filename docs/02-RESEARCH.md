# 02: PoliSpeak research and Phase 2 validation

> **Handoff for Fable, Phase 3.** Three findings change the plan.
>
> 1. Floor speech (R1) cannot support the daily product. The Congressional Record is heavy with
>    procedure and tributes. Congress is also in recess Aug 10–Sep 11 and Oct 5–Nov 6 2026,
>    including election day. Use member press releases from `dwillis/congress-press` (R2) as the
>    daily core and Bluesky (R3) as a supplement. Keep floor speech as a high-quality citation
>    source and for floor-vs-feed analysis.
> 2. X is **DEAD** as an automated channel (R4). Since Feb 2026, reads cost $400–1,200/mo and each
>    citation-linked post costs $0.20/URL-post at that tier. That is 40–120× the $10 budget. Ingest
>    open sources, publish through Bluesky and the dashboard, and allow manual X cross-posts.
> 3. “Party Lines” is **DEAD** as a name (R11). An active U.S.-politics podcast already uses it, and
>    the `.com` and `.org` domains are unavailable. The recommended name is **OnScript**;
>    `theonscript.com` and `onscript.news` were available during this research.
>
> Every other assumption is **VIABLE** or **VIABLE-WITH-CHANGES**. Because Bluesky was about 94%
> Democratic, press releases are the only symmetric two-party source. Mirror the
> volunteer-maintained scraper and treat its availability as a critical dependency. Section §3 has
> the feature verdicts, §5 has the remaining product decisions, and §6 has the cost model, endpoints,
> and measured values. These findings supersede the vision's §10 assumptions. The original
> scoreboard said 2 **VIABLE** before correcting the count to three. Press-release ingestion remains
> a cost-0 path.

**Method.** On 2026-07-10, each assumption R1–R11 was checked against primary sources: official API
documentation, pricing pages, policy text, repository history, and registrar results. A separate
reviewer reopened the sources and tried to disprove any finding that would change a decision. A final
review checked for missing implications. The corrected values appear below. Confidence is `high` for
all eleven assumptions.

---

## §1 Verdict summary

| ID | Assumption (abbreviated) | Verdict | Confidence | What changed vs. the vision |
|---|---|---|---|---|
| **R1** | Daily machine-readable floor-speech corpus | **VIABLE-WITH-CHANGES** | high | Source is **GovInfo**, not congress.gov; it's a *supplementary/citation* leg, **not the core source** (recess-dark October; attribution intermittently drops) |
| **R2** | Member press releases ingestible at scale | **VIABLE-WITH-CHANGES** | high | Don't scrape 535 sites. **consume `dwillis/congress-press`**; single-maintainer risk |
| **R3** | Bluesky is a usable leg | **VIABLE-WITH-CHANGES** | high | Great free ingestion, but **~94% Democratic** → supplementary source + secondary posting only |
| **R4** | X has a sane path | **DEAD** | high | Pay-per-use since Feb 2026; **40–120× over budget**; url-posts taxed $0.20 each |
| **R5** | Free daily news-agenda baseline | **VIABLE** | high | **GDELT 2.0** (keyless, free, redistributable); needs a topic-mapping layer |
| **R6** | Fits the $10/mo Anthropic ceiling | **VIABLE-WITH-CHANGES** | high | Only with **batch + cache + Haiku bulk + Sonnet voice**, and likely **only at in-session cadence** |
| **R7** | Fits the GitHub Actions free tier | **VIABLE-WITH-CHANGES** | high | Make the repo **public** (free unlimited compute); store corpus in **Release assets**, not lfs |
| **R8** | The lane is unoccupied | **VIABLE** | high | Confirmed empty; first-gen trackers dead; Dartmouth is closest but a *tone classifier*, not coordination |
| **R9** | Legal posture is boring | **VIABLE-WITH-CHANGES** | high | Not all public-domain, campaign/social content rides on **fair use**; TVEyes is a *cautionary* precedent |
| **R10** | Phrase-matching at scale is feasible | **VIABLE** | high | Corpus is 1–2 orders **smaller** than assumed; local trigrams + embeddings cost ~$0 |
| **R11** | Naming available, no collision | **VIABLE-WITH-CHANGES** | high | **"Party Lines" dies** (active podcast collision) → rename to **OnScript** |

**Summary:** 1 assumption is **DEAD** (R4), 3 are **VIABLE** (R5/R8/R10), and 7 are
**VIABLE-WITH-CHANGES**. No §3 product feature is dead. Automated X and the “Party Lines” name are
retired.

---

## §2 The assumption register, validated

### R1. Floor-speech corpus. VIABLE-WITH-CHANGES (as a citation leg, not the core source)

**Bottom line. A daily, free, full-text, member-attributed floor-speech corpus exists, but it must
come from the GovInfo (gpo) API**, and it cannot be the daily *product* core source.

- **Use GovInfo, not congress.gov.** `api.congress.gov` v3 `daily-congressional-record` returns
  metadata + document *links* only (PDF / "Formatted Text" URLs), not embedded speech text. GovInfo
  exposes the Congressional Record (`CREC`) as **full-text granules** with a per-member attribution
  array. Endpoints: `/collections/CREC/{startDate}/{endDate}` → `/packages/{pkgId}/granules` →
  `/packages/{pkgId}/granules/{granuleId}/summary` (returns `members[]` with `bioGuideId, party,
  state, chamber, role` + `download.txtLink`). Rate limits: **GovInfo 36,000 req/hr** vs
  congress.gov 5,000, a 7.2× reason to prefer GovInfo. Both use one free `api.data.gov` key.
  ([usgpo/api](https://github.com/usgpo/api), [LibraryOfCongress/api.congress.gov](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/DailyCongressionalRecordEndpoint.md))
- **Same-day lag.** "The current year's Congressional Record database is usually updated daily by 11
  a.m." ([govinfo.gov/help/crec](https://www.govinfo.gov/help/crec))
- **The two disqualifiers from being the core source:**
  1. **Recess.** The Senate 2026 tentative schedule has state work periods **Aug 10–Sep 11** and
     **Oct 5–Nov 6**, the fall recess covers the Nov 3 election. Net ≈ **35–45 in-session publishing
     days** before the election, with **~all of October dark**. ([senate.gov 2026 schedule](https://www.senate.gov/legislative/2026_schedule.htm))
  2. **Content fit (plausible, not proven).** The Record is four sections. Daily Digest, House,
     Senate, Extensions of Remarks, and Extensions is tributes/commemoration; House/Senate sections
     mix spoken remarks with *inserted* (never-spoken) statements. The adversarial checker confirmed
     the *categories* but could **not** verify the vision's "dominated by tributes/procedure"
     magnitude, treat "weak carrier" as a real signal-dilution concern, not an established fact.
- **Attribution is not guaranteed (checker refutation, holds=false, verdict unchanged).**
  `members[]` (and specifically `bioGuideId`/`party`, the exact field the on-script index needs)
  appears only when the name parses *and* matches GovInfo's member authority; it **drops** for
  newly-sworn members (documented: [usgpo/api #149](https://github.com/usgpo/api/issues/149), "Mr. suozzi"). Full text + attribution live on
  **House/Senate/Extensions (H/S/E) granules, not Daily Digest (D)** granules, the pipeline must
  filter by granule class.

**Changes needed.** Ingest from GovInfo (H/S/E granules); store raw granule JSON + htm immutably;
add a `name → bioGuideId` fallback resolver (via the congress.gov member list) plus a coverage
metric; handle mods `429/Retry-After`; move the daily party-voice/adoption/on-script/silence core source
onto press releases (R2) + Bluesky (R3); use CREC for the floor-vs-feed features (B5, B4) and as the
citation backbone. **Do not schedule the flagship cadence to depend on floor activity in October
2026.**

### R2. Press releases at scale. VIABLE-WITH-CHANGES (consume a corpus, don't build a scraper)

**Bottom line.** Member press releases are the main source for message discipline and the **only
symmetric two-party source**. They can be ingested for ~$0 by using an existing corpus instead of
scraping 535 sites.

- **Don't build a 535-site scraper.** House sites share a Drupal template but expose only a noisy
  site-wide `/rss.xml`; Senate sites are a heterogeneous mix (WordPress, bespoke CMSes) with feeds
  variously present/404/410. **ProPublica's Congress API, the classic aggregator, is shut down**
  ("no longer available… historical reference"). ([projects.propublica.org](https://projects.propublica.org/api-docs/congress-api/))
- **The rescue: [`dwillis/congress-press`](https://github.com/dwillis/congress-press).** A **live, mit-licensed, daily-updated** (GitHub Actions ~5am UTC)
  jsonl corpus, verified commits on 2026-07-08/09/10. 670k+ releases (2001–present), both
  chambers/parties, every current member with an official site. Each record has `url, title, date,
  source, domain, member{bioguide_id, name, party, state, chamber}, text`, every field the
  ≥3-cited-source rule needs. Consume it via daily `raw.githubusercontent` pull / submodule;
  **ingestion LLM cost = $0**. ([raw 2026-07 JSONL](https://raw.githubusercontent.com/dwillis/congress-press/main/data/2026/2026-07.jsonl))
- **Roster:** [`unitedstates/congress-legislators`](https://github.com/unitedstates/congress-legislators) is current (last commit 2026-06-15), CC0, with
  party/chamber/website/social handles. **but no Bluesky field** (Bluesky handle discovery is a
  separate task).

**Changes needed.** Consume `congress-press` as primary; **mirror every pull into PoliSpeak's own
immutable append-only store** (upstream is one volunteer's repo, the single-maintainer dependency is
the #1 resilience risk, see §4); dead-man switch on stale-upstream (>36h) or anomalously low record
count; join to `congress-legislators` for canonical roster; filter syndicated reprints ("Originally
published in…") before distillation; keep a thin fallback scraper for a few high-signal members.

### R3. Bluesky. VIABLE-WITH-CHANGES (supplementary + Democratic-skewed)

**Bottom line.** A clean, free, terms-OK ingestion leg, but structurally Democratic, so it can
augment the corpus, never fill it.

- **Free unauthenticated reads.** `public.api.bsky.app` `getProfile`/`getAuthorFeed` return HTTP 200
  with no token; members use official `.senate.gov`/`.house.gov` handles; a curated 127-member
  "Members of Congress" starter pack exists; members are actively posting in 2026. ([docs.bsky.app](https://docs.bsky.app/docs/api/app-bsky-feed-get-author-feed))
  *Rate-limit correction:* the "3,000 req/5min per IP" figure is the **pds** limit, not the AppView,
  the public AppView limit is unpublished/"generous," ample for a ~150-account daily poll.
- **The disqualifier: ~94% Democratic.** Of the ~29% of the 119th Congress on Bluesky, active
  accounts are **~94% Democrat / ~5% Republican** ([Trilligent, Jan 2025](https://trilligent.com/the-fragmented-feed-reaching-policymakers-in-the-new-social-media-era/)). Bluesky **cannot** supply a
  symmetric two-party corpus.
- **Posting is allowed. Bots are "welcome"; clearly-labeled parody/composite accounts are permitted
  if they identify their nature in both display name and bio** (+ a `{val:'bot'}` self-label); no
  anti-scraping clause in ToS. ([bots doc](https://docs.bsky.app/docs/starter-templates/bots), [Community Guidelines](https://bsky.social/about/support/community-guidelines))

**Changes needed. Reclassify Bluesky as (1) a supplementary, D-leaning ingestion signal that never
sets party-comparative thresholds, keyed by resolved did** (not handle) for time-series stability;
(2) the natural posting home for the *Democratic* composite account and the *dashboard* is the
primary surface for both. The Republican corpus must come from press releases (R2).

### R4. X. DEAD

**Bottom line.** Economically impossible within $10/mo, by 1–2 orders of magnitude. It is the 2022
failure mode, priced in.

- **Pay-per-use since ~Feb 6 2026** (no free read tier for new devs): third-party post read
  **$0.005**, post-with-URL **$0.200**, plain post $0.015; 2M-read/month cap. Legacy Basic
  ($200)/Pro ($5,000) closed to new signups. ([docs.x.com pricing](https://docs.x.com/x-api/getting-started/pricing))
- **Ingestion math:** ~80k–240k reads/mo = **$400–$1,200/mo** (40–120× budget); even a 100-member
  watchlist ≈ $75/mo (7.5×).
- **Posting math:** every composite post is citation-linked → the **$0.20 url-post tier**, the
  single most expensive routine action X sells. The product's core output format is the thing X
  prices highest.
- Policy (pcf parody labeling, automation rules) is *survivable* but moot given the economics.

**Replacement.** Ingest from R1–R3 (congress.gov/GovInfo + `congress-press` + Bluesky); distribute
on Bluesky + the Vercel dashboard; treat X as an **optional manual cross-post only** ($0 API cost,
ToS-clean, no automation ban exposure).

### R5. News-agenda baseline. VIABLE

**Bottom line.** A free, license-clean, reproducible "top topics of the day" baseline exists:
**GDELT 2.0**.

- **GDELT doc 2.0 API:** keyless, free, coverage back to Jan 2017; `TimelineVol` returns normalized
  topic volume (matched ÷ total monitored articles); filters `theme:` and
  `sourcecountry:unitedstates`; gkg themes (~13k, flat but citable) give a defensible topic
  taxonomy. License: **"unlimited and unrestricted use… you may redistribute, rehost, republish"**
  with attribution, so the baseline is third-party-reproducible and the methodology page is
  publishable. ([about](https://www.gdeltproject.org/about.html), [DOC 2.0](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/))
- **Corroborators:** Wikipedia Current Events / Featured feed (CC by-sa JSON, but the `news` array
  is **current-day-only**, must be captured live daily); Media Cloud 2.0 (free, ~4,000 req/week,
  URLs/metadata only) as a cross-check.
- **Rejected:** NewsAPI.org (first paid tier **$449/mo**, free tier bans commercial use); raw
  AP/Reuters/NPR RSS aggregation (copyright/ToS risk. NPR is noncommercial-only; 11th Cir. found no
  implied RSS license); Google Trends/News (ToS forbids automated access/redistribution). Baseline
  cost: **$0/mo**.

**Changes needed.** A documented **topic-mapping layer** so GDELT topics and the party corpus score
on the *same* normalized topic list (It is the critical methodological piece, put it on the
methodology page); filter to US sources; rank "top topics" by day-over-day **delta/spike**, not raw
global-normalized volume; store the raw daily pull immutably; bake GDELT attribution into every
silence-map card.

### R6. $10/month Anthropic ceiling. VIABLE-WITH-CHANGES

**Bottom line.** It fits, but only with mandatory discipline, and probably only at in-session
cadence. The naive design (~$30/mo) is dead.

- **Live pricing** (fetched 2026-07-10, [platform.claude.com/…/pricing](https://platform.claude.com/docs/en/docs/about-claude/pricing)): **Haiku 4.5** $1 / $5 per MTok; **Batch
  API −50%** → $0.50 / $2.50; **prompt-cache read 0.1×** base input; batch + caching **stack**.
  **Sonnet 5** introductory $2 / $10 through Aug 31 2026, then **$3 / $15** from Sep 1 2026. Haiku
  3.5 is retired on the first-party API.
- **Model. ~360 statements/in-session day → ~180k input tokens/day. Batched + cached, Haiku for bulk
  + Sonnet 5 for the two daily composite-voice calls ≈ $0.40–0.50/day**. Monthly: **~$8–10 at ~20
  in-session days (fits)**; **~$12–15 at 30 days (breaches)**. (The per-day figure rests on token
  assumptions the checker flagged as plausible-not-independently-proven; note Sonnet 5's newer
  tokenizer produces ~30% more tokens.)

**Changes needed (critical).** (1) **Batch** the whole daily pipeline; (2) **cache** the party
centroid + system prompts; (3) **route**. Haiku for bulk, Sonnet only for the two voice calls, never
Opus; (4) **offload phrase-matching/scoring to local code (R10)** instead of LLM calls, the single
biggest lever for B-tier headroom; (5) **gate spend by in-session days** and/or accept a slightly
higher ceiling to honor "never miss a day"; (6) set a hard monthly spend cap in the Console as the
dead-man backstop.

### R7. GitHub Actions free tier. VIABLE-WITH-CHANGES

**Bottom line.** Comfortable fit; the daily job uses ~5–15 min of a 6-hour ceiling. Two required
changes.

- **Public repo → free unlimited compute** (private Free = only 2,000 Linux min/mo). Hard walls:
  6h/job, 35-day run, 20 concurrent jobs, none bind. Runner: 4 vCPU / 16 GB / 14 GB ssd.
  ([limits](https://docs.github.com/en/actions/reference/limits))
- **Corpus store: GitHub Release assets**, not Git lfs. Releases: ≤2 GiB/file, 1,000 assets/release,
  **no total-size or bandwidth limit**. lfs free quota is only 10 GiB storage + 10 GiB bandwidth/mo
  then metered (a public site pulling lfs blobs could trip $0.0875/GB overages and silently break
  the $10 ceiling). ([about-releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)) Corpus growth is only ~300 MB/yr (text).
- **Runner pre-installs** git/git-lfs/Python/Node/**Chrome+Chromium+ChromeDriver** (headless
  HTML→png share-cards work out of the box). **ffmpeg is not pre-installed** (apt-get for B2 video).

**Changes needed.** Public repo; Release assets (not the app repo's git history, daily-growing files
bloat `.git` unbounded) or a separate data repo; shallow-clone the data store; `apt-get ffmpeg` only
when B2 is built and make video a non-blocking (skip-and-log) step using x264.

### R8. The lane. VIABLE (genuinely unoccupied)

**Bottom line.** The specific combined lane, daily composite cited party voice + adoption curves +
silence detector + on-script leaderboard, has no live occupant.

- **First generation is dead**, all killed by the 2022–24 collapse of free Twitter API access:
  ProPublica Congress API (sunset 2024-07-10), Politwoops (dead), PolitiTweet.org (frozen
  2023-04-03), and the project's own twint predecessor. The emptying of the lane *is* the opening.
  ([Politwoops obituary](https://www.propublica.org/article/politwoops-deleted-tweets-twitter-politicians-musk))
- **Closest live tool:** Dartmouth's **America's Political Pulse**, same corpus, all 535 members,
  but a per-member **tone classifier** (attacks/policy/debate/accomplishments/bipartisanship), *not*
  coordination/adoption/silence/on-script. *(Checker correction: its "1.5M data points" is
  **cumulative since Aug 2022**, not per-day.)* Well-funded incumbent-risk: monitor their roadmap.
  ([Dartmouth](https://home.dartmouth.edu/news/2024/08/new-tool-tracks-what-members-congress-say-and-do))
- Academic prior art (Gentzkow-Shapiro-Taddy, *Econometrica* 2019) validates that the
  phrase-partisanship signal is real and citable, as retrospective research, never a live product.

### R9. Legal posture. VIABLE-WITH-CHANGES

**Bottom line.** Boring in the way the vision hoped, with one correction and one critical design
constraint.

- **Not uniformly public domain.** 17 U.S.C. 105 covers only federal-employee *official-duty* works
  (Congressional Record, official `.gov` press pages). **Campaign/personal social posts and campaign
  releases are copyrightable.** Their legal basis is **fair use**.
  ([17 U.S.C. 105](https://www.law.cornell.edu/uscode/text/17/105))
- **TVEyes is a *cautionary* precedent, not clean support.** The Second Circuit found *against*
  TVEyes on market-harm (factor 4) because it "essentially republishes content unaltered."
  **PoliSpeak survives only if outputs are genuinely transformative** (adoption curves, on-script
  scores, silence maps) and never function as a substitute republication of the source speech. This
  constrains the composite-voice design (see §4).
- **Leaderboards** from measured public speech have near-zero defamation surface (public figures +
  actual malice + truth + protected opinion), *if* the methodology is disclosed and scores are
  framed as the metric's output.
- **Platform risk centers on ToS/API compliance;** copyright/defamation is secondary here;
  platform enforcement ended Politwoops. Composite accounts must meet X pcf requirements (keyword
  leads display name plus non-identical avatar), Bluesky labeling requirements, and CA SB 1001 bot
  disclosure. The pipeline cannot depend on one platform API.

**Changes needed.** Tag each source by copyright basis; keep excerpts short + transformative +
attributed; build accounts to each platform's exact labeling spec; publish methodology + a
corrections mechanism; a one-time media/First-Amendment attorney review before scaled launch is
prudent.

### R10. Phrase-matching at scale. VIABLE (not a constraint)

**Bottom line.** Comfortably feasible and nearly free. The corpus is smaller than the vision feared.

- **Corpus is ~5×10⁴–10⁵ statements/year** (press ~31k/yr; *checker corrected up from ~19k*. + CREC
  ~5k/yr + Bluesky), 1–2 orders **below** the 10⁶ ceiling; daily delta is hundreds-to-low-thousands.
- **Local cpu embeddings** (`all-MiniLM-L6-v2`, ~220–315 sentences/sec on cpu) embed the annual
  corpus in minutes, the daily delta in seconds. **no per-call cost**. API fallback (OpenAI
  `text-embedding-3-small` $0.02/M) ≈ **$0.12/yr**. ([model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2))
- **Trigram/shingle matching alone carries the adoption-curve product** (the 2022 predecessor proved
  it); embeddings are a paraphrase enhancement, not critical.

**Watch-outs (modeling, not compute): boilerplate/procedural n-grams over-count as false
"coordination" → need stopword/boilerplate filtering + document-frequency weighting; the on-script
index needs a leave-one-out** baseline so a member isn't scored against their own text; cross-run
state (first-appearance timestamps, embeddings) must persist in the append-only store.

### R11. Naming. VIABLE-WITH-CHANGES (rename off "Party Lines")

**Bottom line.** The front-runner is disqualified; a clean coined alternative is available.

- **"Party Lines" collides in-vertical. Politicon's "Party Lines with Kurt & Erin" (a us-politics
  show, "One Democrat. One Republican. No Talking Points.") published an episode dated 2026-07-09,
  the day before this research**; cbc News also runs a "Party Lines." `partylines.com` and `.org`
  are gone; only weak TLDs remain (`.us` $7.99, `.news` $17.99). The clean `@PartyLines` handles are
  taken. ([Politicon](https://www.politicon.com/podcasts/party-lines/), [CBC](https://www.cbc.ca/listen/cbc-podcasts/381-radio-party-lines))
- Every other §8 candidate's flagship `.com` is taken
  (`thechorus`/`onscript`/`offscript`/`readout`/`inunison`).
- **Recommended: OnScript.** Ties the brand to the flagship on-script index; `theonscript.com`
  ($11.25) and `onscript.news` ($17.99) are available. Since `onscript.bsky.social` is taken, use
  Bluesky **custom-domain handles** (`blue.onscript.news` / `red.onscript.news`), which are
  confirmed supported. Keep "Off Script" as the alerts sub-brand.

**Changes needed.** Drop "Party Lines." Register `theonscript.com` (or `onscript.news`), the
`.bsky.social`/custom-domain handles, and both party handles simultaneously before launch. Verify X
handles logged-in (unauth HTTP 200 is not proof). If "Party Lines" is kept for memorability, it
requires real uspto clearance + an explicit decision to coexist with the podcasts, not recommended.

---

## §3 Per-feature verdicts

Verdicts flow from the controlling assumptions. **No feature is DEAD.** VIABLE-WITH-CHANGES means
the feature ships but a specific corrected condition applies (usually: source it from press
releases/Bluesky not floor; keep it transformative; keep per-member calls out of the daily LLM
budget).

### Tier S, the core source (explicit verdicts)

| # | Feature | Verdict | Condition |
|---|---|---|---|
| **S1** | Daily Party Voice | **VIABLE-WITH-CHANGES** | core source = press releases (R2) + Bluesky (R3), **not** floor. Output must be transformative/analytic, not a substitute digest (R9/TVEyes). |
| **S2** | Adoption Curves | **VIABLE-WITH-CHANGES** | Run on the press-release/social corpus (reliable `bioguide_id`), trigram-carried (R10). Not on floor text (attribution drops, R1). |
| **S3** | Silence Detector | **VIABLE-WITH-CHANGES** | GDELT baseline (R5) + a documented topic-mapping layer + **coverage gating** so "silence" isn't a corpus gap (recess/attribution). |
| **S4** | On-Script Index + Leaderboard | **VIABLE-WITH-CHANGES** | Leave-one-out baseline (R10); `name→bioGuide` fallback + min-coverage threshold (R1); frame as disclosed-metric output (R9). |
| **S5** | Receipts pages | **VIABLE** | *Strengthened*. CREC gives immutable member+date+URL+full-text citations. Core evidence. |
| **S6** | Phrase Explorer | **VIABLE-WITH-CHANGES** | Core loop fine; keep event-driven reactive queries sparse (non-batch = 2× cost, R6). |
| **S7** | Share-card renderer | **VIABLE** | Chrome pre-installed on the runner (R7); HTML→png works out of the box. |

### Tier A, the escalation (explicit verdicts)

| # | Feature | Verdict | Condition |
|---|---|---|---|
| **A1** | The Script (reconstructed memo) | **VIABLE** | Rides on S2/S4; keep framing transformative (R9). |
| **A2** | Phrase lifecycle cards + Obituaries | **VIABLE** | Trigram first-appearance/decay (R10). |
| **A3** | Who-Said-It-First races | **VIABLE** | n-gram first-appearance (R10); attribution-dependent. |
| **A4** | Off-Script alerts | **VIABLE-WITH-CHANGES** | Event-driven = non-batch LLM cost (R6); keep sparse or compute in local code. |
| **A5** | The Duet | **VIABLE** | Rides on the two-party core source. |
| **A6** | Frame-pair tracker | **VIABLE** | n-gram usage-share (R10). |
| **A7** | Topic ownership / asymmetric silence | **VIABLE-WITH-CHANGES** | Depends on R5 baseline + a *symmetric* corpus; guard neutrality (press releases, not Bluesky, for cross-party ratios). |
| **A8** | Response latency | **VIABLE-WITH-CHANGES** | Event timing from R5; degraded during recess when the floor is dark (R1). |
| **A9** | Weekly Awards | **VIABLE-WITH-CHANGES** | Frame superlatives as the disclosed metric's output + corrections policy (R9). |
| **A10** | Member pages | **VIABLE-WITH-CHANGES** | Handle attribution completeness + coverage denominator accurately (R1/R2). |
| **A11** | Party discipline index | **VIABLE** | Academically precedented; R10-feasible. |
| **A12** | The Upstream Graph | **VIABLE** | n-gram first-appearance topology (R10); higher build cost, no new dependency. |

### Tier B, batch-verdicted by controlling assumptions

All **VIABLE** except as noted. Controlling assumptions in brackets.
- **B1 The Séance**. **VIABLE-WITH-CHANGES** [R6]: per-query LLM must be user-triggered +
  rate-limited, *outside* the daily budget.
- **B2 Auto time-lapse videos**. **VIABLE-WITH-CHANGES** [R7]: `apt-get ffmpeg`, non-blocking step,
  x264.
- **B3 Memetic weather map**. VIABLE [presentation on the corpus].
- **B4 The Two Audiences**. **VIABLE-WITH-CHANGES** [R2+R3+R6]: needs "local" (press) and "national"
  (social) legs; Bluesky's D-skew limits the R side; per-member pass is headroom-gated.
- **B5 Floor vs. feed**. VIABLE [R1+R3]: *directly enabled* by CREC full text vs. social, promote
  it; it's the best use of the floor corpus.
- **B6 The Mirror Test**. VIABLE.
- **B7 Phrase theft detection**. VIABLE [R10].
- **B8 Assimilation curves**. VIABLE [R10 + the long-term time series]; the Jan-2027 season-two
  artifact.
- **B9 Emotional temperature index**. **VIABLE-WITH-CHANGES** [R6+R9]: per-party-per-day is cheap;
  per-member would blow the budget; neutrality-sensitive rubric must be published.
- **B10 Embeds + public API + bulk downloads**. VIABLE [R7 Release assets; R9 reuse OK].
- **B11 Historic replay scrubber**. VIABLE [time-series + R7 storage].
- **B12 Half-life analytics**. VIABLE [R10 decay].

### Tier C, parking lot (batch-verdicted)

All **VIABLE** except: **C5 Money × message overlay**. **VIABLE-WITH-CHANGES** [R9]: fec
individual-contributor names/addresses may not be used to solicit or commercially;
committee-level/aggregate analysis is fine. (C1 phrase futures, C2 Mad Libs, C3 per-state digests,
C4 browser extension, C6 merch, all VIABLE, all v2+.)

### Constitutional / unranked

Methodology page, neutrality documentation, corrections policy, distillation explainer, immutable
raw archive, all **VIABLE and now more critical**: R5 requires an attribution/topic-mapping
methodology; R9 makes disclosed methodology + corrections the defamation firewall; the neutrality
page is the answer to the source-asymmetry problem (§4).

### Retired channel and name decisions

- **X as an automated channel**. DEAD [R4]. *Replacement:* ingest from open sources; post on Bluesky
  + dashboard; manual X cross-post only.
- **The name "Party Lines"**. DEAD [R11]. *Replacement:* **OnScript**.

---

## §4 Cross-cutting implications (what the register does to the product)

1. **Neutrality now rests on press releases, and therefore on one repo.** X-dead (R4) +
   Bluesky-94%-Democratic (R3) mean **no social platform carries a symmetric two-party corpus**. The
   Republican corpus must come from press releases (R2/`dwillis/congress-press`). So "identical
   instrument, both parties" lives entirely in one volunteer-maintained scraper. **Mirror it,
   monitor its freshness with the dead-man switch, and keep a fallback fetcher**, It is the
   critical resilience decision, and it's the same class of single-point failure that killed the
   2022 predecessor.
2. **October goes dark when it matters. The floor recess (Oct 5–Nov 6, R1) collides with
   both the "never miss a day" promise and the midterm attention peak. Press releases + Bluesky must
   carry the product through recess, but those are the less-symmetric-verified and D-skewed sources,
   so recess degrades neutrality precisely when traffic peaks.**
3. **One data defect cross-cuts two of three engines.** Floor attribution-drop (R1) breaks both the
   on-script index *and* the adoption-curve propagation detector (both need member+party). The
   `name→bioGuide` fallback is a hard dependency for both, another reason to core source on press
   releases, whose `bioguide_id` is reliable.
4. **API tokens set the budget limit.** Public-repository Actions (R7) and local embeddings (R10)
   are
   approximately free. Anthropic distillation tokens (R6) are the scarce resource, so §5 must set
   the cadence/budget tradeoff against that limit.
5. **The composite voice must stay analytic, or it drifts into the TVEyes failure.** The more
   "here's what they said" the daily voice reads, the closer it gets to substitute-republication
   (R9). Citation integrity (≥3 sources) helps but doesn't itself establish transformation, the
   *analysis* (curves, scores, silence) is what makes it fair use.
6. **Ingestion architecture is constrained by R1 details.** GovInfo (36k/hr) primary, filter to
   H/S/E granule classes (not Daily Digest), congress.gov only for member-list resolution, never
   bulk. Phase 3 must bake this into the pipeline stages.

---

## §5 Open questions only Phase 3 can settle

1. **Recess core source.** What does the daily product show Oct 5–Nov 6 when floor speech is dark?
   Press+Bluesky only? Drop to in-session cadence? Redefine "never miss a day" as a recess-mode
   dashboard?
2. **Symmetric neutrality under asymmetric sources.** If the gop corpus is press-releases-only while
   Democrats add Bluesky, how is "identical instrument" defended? (Recommended framing: press
   releases are the symmetric backbone scored identically; Bluesky is a labeled D-side supplement
   that never sets cross-party thresholds, document this on the methodology page.)
3. **`congress-press` resilience.** Mirror/fork the scraper, build an independent fetcher, or accept
   the risk with a dead-man switch?
4. **Cadence vs. budget.** Daily-always, in-session-only, or tiered (cheap daily + full in-session
   runs)? This sets the distillation prompt count, batching, and model tier that keep it under
   $10/mo.
5. **On-script under attribution drop.** Specify the `name→bioGuide` resolver, the minimum-coverage
   threshold below which a member/day is excluded, and how coverage is shown accurately.
6. **Keeping the voice transformative.** Distillation prompts + voice guide must produce analysis,
   not a readable substitute for the source speeches (R9).
7. **Composite-account mechanics.** Exact Bluesky display-name label term, bio disclosure text,
   `{val:'bot'}` self-label, and handle (`blue.onscript.news`/`red.onscript.news`).
8. **Silence false-positives.** Gate "silence" claims on known-complete corpus coverage for that
   day, so recess/attribution gaps don't masquerade as party avoidance.

---

## §6 Reference, the hard numbers Phase 3 needs

**Corpus sources & endpoints**
- **Floor (R1):** GovInfo API. `GET /collections/CREC/{startYYYY-MM-DDT00:00:00Z}/{endZ}` →
  `/packages/{pkgId}/granules?offsetMark=*&pageSize=N` →
  `/packages/{pkgId}/granules/{granuleId}/summary` → `members[]` + `download.txtLink`. **Filter to
  granuleClass HOUSE/SENATE/EXTENSIONS (H/S/E); skip Daily Digest (D).** 36,000 req/hr. Free
  `api.data.gov` key (in Actions secrets). Same-day lag. ~109 granules on a light in-session day.
- **Press releases (R2):** `dwillis/congress-press`, daily jsonl at `data/YYYY/YYYY-MM.jsonl`; ~31k
  releases/yr recent; mit; record schema
  `{url,title,date,source,domain,member{bioguide_id,name,party,state,chamber},text}`. **Mirror into
  own store.**
- **Roster (R2):** `unitedstates/congress-legislators` (CC0; no Bluesky field, build a handle map).
- **Bluesky (R3):** `public.api.bsky.app` `getAuthorFeed`/`getProfile`, unauthenticated; key members
  by resolved did; ~127-member starter pack; ~94% D.
- **News baseline (R5):** GDELT doc 2.0 `https://api.gdeltproject.org/api/v2/doc/doc`, keyless,
  `mode=TimelineVol`, `sourcecountry:unitedstates`; rank by day-over-day delta. + Wikipedia Featured
  feed (capture `news` live daily). Attribution required.

**Cost model (R6).** Haiku 4.5 $1/$5 (batch $0.50/$2.50), cache-read 0.1×, stacks; Sonnet 5 $2/$10
intro→$3/$15 (Sep 1 2026). The batched and cached pipeline costs about $0.40–0.50/day, or
~$8–10/mo at ~20 in-session days. It breaches the limit at 30 days. Set a Console monthly cap and
offload matching/scoring to local code.

**Compute & storage (R7)**. Public repo → free unlimited Actions (6h/job). Store the compounding
corpus in **Release assets** (no size/bandwidth cap), not lfs. Corpus growth ~300 MB/yr. Chrome
pre-installed (share-cards); `apt-get ffmpeg` for B2.

**Phrase matching (R10)**. Corpus ~5×10⁴–10⁵/yr. Local `all-MiniLM-L6-v2` (~220–315 sent/sec cpu) or
trigrams alone; ~$0. Needs boilerplate filtering + leave-one-out on-script baseline.

**Legal (R9).** Tag sources: 17 U.S.C. 105 public domain (CREC, official `.gov`) vs. fair use
(campaign/social). Short transformative excerpts only. Platform PCF/parody labels + bot disclosure.
Methodology + corrections published.

---

## §7 Naming decision

**Retire "Party Lines" and "PoliSpeak." Recommended primary name: OnScript**. `theonscript.com` (or
`onscript.news`), Bluesky handles `blue.onscript.news` / `red.onscript.news` (custom-domain), alerts
sub-brand "Off Script," "The Ventriloquism Award" kept. Register domain + all handles simultaneously
before launch; verify X handles logged-in. It is the R11 recommendation, not a locked decision.
Phase 3 owns the final call, but it must be off "Party Lines."

---

*Phase 2 closed 2026-07-10 (Opus). Every assumption validated against live primary sources and
adversarially re-checked; every verdict held. Next: Fable, Phase 3, `docs/03-GAMEPLAN.md`, build the
weekend-sized v1 around the corrected core source (press releases + Bluesky), the OnScript name, the
batch-and-cache cost discipline, and the neutrality defense for asymmetric sources. The handoff note
at the top of this file is the brief.*
