# 01-VISION — PoliSpeak (working name; naming candidates in §8)

> **HANDOFF NOTE — for Opus, Phase 2.** This document assumes generously on purpose; your job is to make it survive contact with reality by shrinking it, not by wishful thinking. Everything external-world in here — API coverage, platform rules, costs, prior art — is an *assumption*, enumerated in the register at §10 with the features that die if it's false. Validate each register item with evidence and links, then mark every feature in §3 **VIABLE / VIABLE-WITH-CHANGES / DEAD** in `docs/02-RESEARCH.md`. Kill without sentiment. Priorities in order: R1–R3 (does the daily corpus even exist in machine-readable form?), R5 (the silence detector lives or dies on a news baseline), R4 (X posting rules), R6–R7 (does it fit in $10/month and the GitHub Actions free tier?). For Anthropic cost modeling, read current published pricing — do not trust any number from memory. Nothing in this doc is precious except the constraints inherited from CLAUDE.md: citations, neutrality-by-construction, raw-first storage, and the weekend-sized v1.

---

## §0 The one-sentence product

Every day, the system reads everything elected officials said out loud, compresses each party into a single composite voice with receipts, and publishes the coordination machinery of American political speech — the talking points, the silences, and the members who are just reading the script.

The tone doctrine, stated once and inherited by everything below: **the system never jokes. The data is the joke.**

---

## §1 End goals — what winning looks like

### Capabilities at end-state
1. **Answer "what did each party say today?"** in one composite, cited voice — every day, unattended, forever. The composite accounts have never missed a day.
2. **Detect a coordinated talking point within ~24h of first synchronized use** and render the adoption curve: phrase, first-sayer, roster, timeline.
3. **Show what is being avoided, quantitatively** — a weekly absence map diffing the national news agenda against each party's corpus.
4. **Score every member continuously** on script-following vs. original language, with receipts behind every score.
5. **Render every insight above as a self-contained shareable artifact automatically** — image cards, threads, short video — with zero human hands in the loop.

### Success metrics by midterms (Nov 2026)
- An adoption-curve chart or silence map is embedded/cited in at least one mainstream outlet's story.
- "On-script index" (or whatever we name it) appears in political-media vocabulary unprompted.
- Journalists ask for the data; the answer is a public download link, not a DM negotiation.
- Zero successful bias takedowns: every accusation is answered by the methodology page, in public, once.
- The unbroken daily time-series has never broken.
- **The win condition:** a sitting member of Congress publicly complains about their on-script score — thereby going off-script, thereby becoming a citable event in the system that scored them.

### Success metrics at month 6 (≈ Jan 2027, new Congress)
- **Freshman assimilation curves ship** — watch new members' language converge to the party centroid week by week. This artifact is impossible without the time-series moat; it is proof the moat exists.
- Dataset cited in an academic preprint; the API has external users we didn't recruit.
- The system survived the post-election attention crash because the new Congress learning to speak *is* the season-two plot.

---

## §2 The insight taxonomy — five families

Every feature in §3 belongs to one of these. The taxonomy is the site's information architecture and the accounts' content calendar.

| Family | Core question | Flagship artifact |
|---|---|---|
| **1. Coordination** | Who is moving together, and when did the memo drop? | The adoption curve |
| **2. Absence** | What won't they say? | The silence map |
| **3. Individuality** | Who is a person and who is a vessel? | The on-script leaderboard |
| **4. Framing** | How do words fight? ("estate tax" vs. "death tax") | The frame-war tracker |
| **5. Lifecycle** | How do messages get born, spread, mutate, and die? | The phrase lifecycle card |

---

## §3 The feature universe, ranked

Ranking rubric: **Insight** (1–5: does it tell you something true you couldn't see before?), **Share** (1–5: does a screenshot of it carry its own proof and travel?), **Cost** (S = rides on the spine ~day, M = ~week, L = weeks, XL = month+). Tier = judgment on the product Insight × Share ÷ Cost.

Tiers are not a schedule. **S** is the spine (v1 candidates), **A** is compounding escalation, **B** is end-state differentiators, **C** is the parking lot. Opus kills across all tiers; Fable Phase 3 re-picks v1 from the survivors.

### Tier S — the spine

| # | Feature | What it is | Insight | Share | Cost |
|---|---|---|---|---|---|
| S1 | **Daily Party Voice** | One composite statement per party per day, assembled from real quotes, every claim cited. The product. | 4 | 4 | M |
| S2 | **Adoption Curves (the Memo Detector)** | First-appearance tracking + adoption curve per phrase: 2 members → 90 members in 26 hours, annotated with the first-sayer. | 5 | 5 | M |
| S3 | **The Silence Detector** | Daily news baseline vs. each party's corpus → the topics nobody will touch, ranked by news volume × speech absence. | 5 | 5 | M |
| S4 | **On-Script Index + Leaderboard** | Per-member: % of output matching party language vs. own words. Top 10 vessels, top 10 mavericks. | 4 | 5 | M |
| S5 | **Receipts pages** | The citation UI under every artifact: member, quote, date, source URL. Not a feature — armor. Every share links here. | 3 | 2 | S |
| S6 | **Phrase Explorer** | Search any phrase → its curve, roster, first-sayer, mutations. The dashboard's core loop. | 4 | 3 | M |
| S7 | **Share-card renderer** | Every insight auto-renders as a self-contained image artifact (chart + claim + receipts pointer + date). The distribution multiplier for everything else. | 2 | 5 | M |

### Tier A — the escalation (months 1–3)

| # | Feature | What it is | Insight | Share | Cost |
|---|---|---|---|---|---|
| A1 | **The Script** | The daily reconstructed memo: "based on today's synchronized language, the memo said…" — formatted like a leaked one-pager, every bullet footnoted. | 5 | 5 | S* |
| A2 | **Phrase lifecycle cards + Obituaries** | Genealogy card per phrase: born (date, first-sayer), peaked, spread map, descendants, died. Obituary variant when a phrase goes 14 days silent after peak. | 4 | 5 | M |
| A3 | **Who-Said-It-First races** | Attribution leaderboard: originators vs. parrots. "Fastest Parrot" = shortest median lag from first-sayer to repetition. | 4 | 4 | S* |
| A4 | **Off-Script alerts** | Anomaly feed: member deviates hard from party centroid; phrase spikes with no news event (memo, not news); a loud member goes suddenly silent on a topic. | 5 | 4 | M |
| A5 | **The Duet** | Same phrase, both parties, same day, opposite intent → automatic side-by-side. | 4 | 5 | S* |
| A6 | **Frame-pair tracker** | Paired-term war charts over time: "estate tax"/"death tax", "undocumented"/"illegal", per-party usage share. The frame wars, quantified. | 5 | 4 | M |
| A7 | **Topic ownership map** | Which party owns which topics (50:1 speech ratios), which are contested, plus the asymmetric-silence chart. | 4 | 3 | S* |
| A8 | **Response latency** | News event → hours until each party's first coordinated response. The message-machine OODA clock, incl. per-member "hours to first statement." | 4 | 3 | M |
| A9 | **Weekly Awards** | Sunday ritual: the Ventriloquism Award (most on-script), Loudest Silence, Best Original Line, Fastest Parrot. Same rules both parties, winners picked by the data. | 3 | 5 | S* |
| A10 | **Member pages** | Per-member: signature phrases (stylometric fingerprint), on-script history, personal silence map, first-sayer credits. | 4 | 3 | M |
| A11 | **Party discipline index** | The 2022 trigram finding, upgraded: message-alignment index per party over time + does discipline tighten as the election approaches? | 4 | 3 | S* |
| A12 | **The Upstream Graph** | Who consistently says things first that others repeat → the influence topology. Detects the messaging operation's actual mouthpieces. | 5 | 3 | L |

\* S-cost because it rides on the Tier-S spine (S2/S4/S7) once that exists.

### Tier B — the end-state weird (defensible)

| # | Feature | What it is | Insight | Share | Cost |
|---|---|---|---|---|---|
| B1 | **The Séance** | "Ask the party" chatbot that can ONLY answer in real quotes, citation per sentence, in the composite voice. When the corpus is silent: "We have said nothing about this. That is itself an answer." | 4 | 5 | L |
| B2 | **Auto time-lapse videos** | 20–30s adoption-curve animations rendered nightly for short-form platforms. | 3 | 5 | L |
| B3 | **Memetic weather map** | Phrases as weather systems crossing member states: "a high-pressure system of 'affordability' moving through the Rust Belt." Daily phrase forecast. | 3 | 5 | L |
| B4 | **The Two Audiences** | Per-member divergence between local voice (press releases) and national voice (social): "At home: 'I secured $14M for our county.' Online: [culture war]." Promote to Tier A if both corpora land in v1. | 5 | 5 | M |
| B5 | **Floor vs. feed** | Congressional Record voice vs. social voice divergence — formal self vs. performing self. | 4 | 3 | M |
| B6 | **The Mirror Test** | Guess-the-party game on anonymized statements; the running distinguishability score doubles as a longitudinal polarization metric. Publishable. | 5 | 4 | M |
| B7 | **Phrase theft detection** | Cross-party frame capture events: one party adopts the other's language (to mock, to co-opt, to neutralize), auto-detected at the boundary crossing. | 4 | 4 | M |
| B8 | **Assimilation curves** | Jan 2027: freshman language converging to the party centroid, week by week. Borg-watch. The time-series moat made visible. | 5 | 4 | S* |
| B9 | **Emotional temperature index** | Outrage/fear/hope levels per party per day — same instrument, same rubric, both parties, rubric published. Neutrality-sensitive; ship with care. | 3 | 3 | M |
| B10 | **Embeds + public API + bulk downloads** | Journalists embed charts; researchers pull data. Second-order distribution that also builds the credibility layer. | 2 | 3 | M |
| B11 | **Historic replay scrubber** | The time machine: scrub any date range, watch phrases ignite. The 2022 Flourish viz, native and better. | 3 | 4 | M |
| B12 | **Half-life analytics** | Decay constants per phrase/party/topic: "'commonsense solutions' has a half-life of 6 days." | 3 | 3 | S* |

### Tier C — the parking lot

| # | Feature | One-liner |
|---|---|---|
| C1 | **Phrase futures** | Users predict tomorrow's spiking phrase; scoreboard. Retention toy. |
| C2 | **Congressional Mad Libs** | Real quote, signature phrases blanked, guess the blanks. |
| C3 | **Per-state digests** | "What your delegation said this week," localized email. |
| C4 | **Browser extension** | Hover any phrase in a news article → its adoption curve. |
| C5 | **Money × message overlay** | FEC donations vs. phrase adoption timing. Heavy, unique, v3+. |
| C6 | **Merch** | Phrase obituary posters. Lifecycle trading cards. (Only half a joke — artifacts that good should be printable.) |

**Constitutional, unranked:** methodology page, neutrality-by-construction documentation, corrections policy, "how distillation works" explainer, public immutable raw archive. These aren't features; they're the license to operate.

---

## §4 The top-5 "oh that's cool" artifacts

The five things the system must be able to produce that make someone grab their phone. All examples below are **illustrative — the numbers are invented for this vision doc; the real system never invents a number.**

### 1. The Adoption Curve (S2) — the holy-shit chart
One phrase, one chart: a flat line at 2 mentions, then a cliff — 87 members in 31 hours. Annotated: first-sayer (name, timestamp), the 10 AM leadership-hour surge, the roster below. Caption, clinical: *"'border czar's failed record' — first said by Rep. X, 8:02 AM Tuesday. 87 members by Wednesday afternoon."* Why it detonates: it is surveillance of coordination made visible — everyone suspects the memo exists; this is the memo's shadow on the wall, with receipts. And it's symmetric: both parties produce these weekly, so both sides share them to dunk on the other. The system doesn't care who's embarrassed. That's the brand.

### 2. The Script (A1) — the reconstructed memo
A one-page artifact styled like the thing everyone imagines: TODAY'S MESSAGE — [PARTY], three bullets, recommended vocabulary, do-not-say list (from the silence data). Every line footnoted to real statements. Header disclaimer, deadpan: *"Reconstructed from public statements. No memo was leaked. None needed to be."* It's the single most screenshot-native object the system can produce — the artifact of the conspiracy, assembled entirely from public data.

### 3. The Silence Map (S3) — what nobody would say this week
A heat grid: rows = the week's top news topics by baseline volume, columns = parties; cells = speech volume. The holes glow. Caption: *"Topic #1 in American news this week. Combined statements from 535 members of Congress: 3."* Nobody has shipped the absence map. Absence is unfalsifiable-feeling until you quantify it — then it's a chart, and charts get embedded.

### 4. The On-Script Leaderboard (S4) — the Ventriloquism Award
Top 10 vessels, top 10 mavericks, updated daily, receipts behind every score. The weekly award post: *"This week's Ventriloquism Award goes to Sen. Y, 96% of whose public output matched party language. Sen. Y's most original sentence this week was a birthday message."* Names beat aggregates; leaderboards are engagement machines; and the metric is inherently bipartisan — every week burns one of each.

### 5. The Phrase Lifecycle Card (A2) — genealogy + obituary
A collectible-card artifact per phrase: BORN 3/14, Rep. Z · PEAKED 3/19, 112 members/day · SPREAD [mini-map] · DESCENDANTS: two mutations · DIED 4/2. Obituary variant: *"In memoriam: 'commonsense solutions.' Survived by 'kitchen-table issues.'"* It makes language feel like what it is — an organism with a lifespan and a bloodline — and it's funny with zero editorializing.

---

## §5 Virality theory — viral vs. merely interesting

1. **A share is a screenshot that carries its own proof.** Self-contained artifact: claim + chart + names + date + receipts pointer in one image. If understanding it requires the thread above it, it dies.
2. **Names beat aggregates.** "Party discipline rose 12%" is interesting. "These ten people said the same four words within six hours of each other" is viral. Individuals are the story; indices are the footnote.
3. **Specificity is the punchline.** "87 members, 31 hours, 4 words." Precision reads as authority *and* as comedy. Round numbers read as opinion.
4. **Symmetry is the distribution hack.** Each party's partisans share the *other* party's charts. Neutrality doesn't halve the audience — it doubles it, because both tribes get ammunition on alternating days. Forced balance would break this; *instrument* symmetry with findings-as-they-fall keeps it.
5. **Deadpan wins.** No jokes, no adjectives, no 🚨 unless it's load-bearing. The register of a seismograph. Editorializing converts "devastating data" into "partisan account" instantly.
6. **Rhythm builds habit; anomaly builds urgency.** Daily line = habit. Weekly awards = appointment viewing. Off-script alerts = "turn on notifications."
7. **A novel measurement is newsworthy in itself.** The first instrument to measure a thing gets cited every time the thing matters. "On-script index" should be a term we coin and own.
8. **The interesting-but-not-viral layer is not waste — it's the armor.** Indices, methodology, downloads, time-series: journalists and academics convert those into citations, citations convert into credibility, and credibility is what makes the viral layer unkillable. Two audiences, one corpus.

---

## §6 The composite accounts — voice guide

**The signature move: first-person-plural self-surveillance.** The composite voice speaks sincerely as the party while clinically reporting its own coordination. It never mocks; it *confesses, proudly*. All examples illustrative:

> *"We began saying 'affordability agenda' at 9:14 AM. By 4 PM, 71 of us had said it. We are very excited about the affordability agenda."*

> *"Today we are focused on protecting your healthcare. We said 'gut Medicaid' in 63 separate statements, our highest single-day usage since March. We have not mentioned the debt ceiling in 11 days."*

> *"The #1 news story in America today concerns [topic]. We have no statement at this time. (Day 4.)"*

**Voice rules (constitutional):**
- Content words may come ONLY from the distilled corpus — the voice assembles, never invents. Counts, dates, and receipts links are the only permitted additions.
- No editorializing adjectives that don't appear in source statements. The caption register is clinical even when the content is absurd — *especially* when the content is absurd.
- Every post carries a receipts link. Every number is reproducible from the public archive.
- Never @-mention members (no harassment vector). Names appear in artifacts, not in tags.
- Accounts are clearly labeled automated/composite in bio + platform-native automation labels; bio links the methodology page. (Exact labeling requirements per platform: R3/R4.)

**Post types & cadence:** the Daily Line (each morning, post-distillation) · Unison Alerts (event-driven, phrase spikes) · Silence Notes (when the detector triggers) · The Duet (when it happens) · Weekly Awards (Sunday). Two accounts, one per party, identical logic. Platform: Bluesky assumed primary (R3); X if research shows a sane path (R4). The dashboard is home; the accounts are antennae.

---

## §7 The dashboard, October 27, 2026 (eight days before the midterms)

Front page, morning of a hot news day. Top: **two composite statements side by side** — this is the fold, and it reads like a split-screen presidential address written by a seismograph. Under each: receipts strips (member · quote · timestamp · source favicon). Between them: the **phrase ticker** — every talking point currently accelerating, sparklines twitching, sorted by velocity. Below the fold: **the chart of the day** (auto-picked: today it's an adoption curve that went vertical at 9:40 AM), the **silence of the day** (*"Topic #2 in national news. Neither party has issued a statement. Day 3."*), and the **leaderboard delta** (two members swapped places; one freshman is climbing the on-script rankings at a rate the tooltip calls "notable").

Nav: **Explore** (phrase search → curve, roster, first-sayer, mutations), **Topics** (ownership maps, frame-pair war charts), **Members** (fingerprints, histories, personal silence maps), **Awards** (the hall: every Ventriloquism Award since launch), **Time Machine** (scrub since launch day; watch the summer's three phrase-ignitions replay), **The Archive** (methodology, corrections log, raw downloads, API docs — the boring wing that makes the loud wing bulletproof).

Month 6, mid-January 2027, same site: election's over, attention crashed, and the front page doesn't care — the new Congress is being sworn in and the **assimilation curves** go live: ninety-some freshmen, each a thin line drifting week by week toward their party's centroid. Some snap to it in a fortnight. One or two never converge, and the Off-Script feed has already found them. Season two writes itself because the corpus never stops.

---

## §8 Naming

Criteria: says what it is · symmetric/neutral (no side implied) · memeable, sayable, ownable · account-family coherent · domain + Bluesky/X handles plausibly available (**R11 — Opus checks; do not fall in love before availability**).

| Candidate | Why | Family (site / accounts / alerts) |
|---|---|---|
| **Party Lines** ⭐ | Triple meaning: talking points, toeing the line, the old shared phone line everyone talks over. Neutral, obvious, sticky. | partylines.* / @PartyLinesBlue + @PartyLinesRed / "Off Script" |
| **The Chorus** | The composite-voice metaphor made literal; accounts basically name themselves. | thechorus.* / @BlueChorus + @RedChorus / "Solo" (off-script feed) |
| **On Script / Off Script** | Ties the brand to the flagship metric; "Off Script" is a perfect alert-feed name either way. | onscript.* / @OnScriptBlue + @OnScriptRed / "Off Script" |
| **The Daily Readout** | "Readout" is native political vocabulary for post-meeting talking points; deadpan-official flavor. | readout.* / @BlueReadout + @RedReadout / "No Readout" (silence feed) |
| **In Unison** | The coordination poetry; slightly softer. | inunison.* / @BlueInUnison + @RedInUnison / "Solo" |
| PoliSpeak | Working name only. Reads like a language-learning app. Retire at launch. | — |

**Recommendation: Party Lines**, with **Off Script** as the alerts feed and "The Ventriloquism Award" kept as-is regardless of brand. The Chorus is the runner-up and donates its account-naming scheme if handles collide.

---

## §9 Design tenets — failure-mode armor

1. **Symmetric instrument, asymmetric findings.** Identical pipeline, prompts, thresholds, and award rules for both parties — published. If the findings skew one way for a week, that's reality, not a bug; if the *instrument* skews, that's an incident. The methodology page explains exactly this distinction, because it is the answer to the first, tenth, and thousandth accusation.
2. **Citation or it doesn't ship.** Distillation is quote-assembly, not authorship: every content phrase in any output must match (exact or near-exact) a source statement, verified mechanically post-generation. An output that fails the match check is discarded and logged, never patched by hand. This is also the hallucination firewall.
3. **Raw-first, append-only, rebuildable.** Every ingested statement stored immutably with source URL, fetch timestamp, and content hash before any processing touches it. Every derived layer (distillations, curves, scores) is a pure function of the raw archive — rebuildable from zero. Schema changes are versioned, never breaking.
4. **Skip-and-log survivability.** Any source can vanish on any day (2022's lesson: the platform *itself* can vanish). A run with missing sources completes and says so. Dead-man switch: ntfy on failed runs or anomalously small output. Secrets (ntfy topic, API keys) live in GitHub Actions secrets, never in the repo.
5. **Platform-agnostic distribution.** The site is home; accounts are antennae. Any platform can ban, rug, or die without touching the product. Multi-platform posting from day one if costs allow.
6. **The unbroken series is the moat.** A missed day is an incident with a postmortem, not a shrug. Month-6 features (assimilation curves, half-lives, the time machine) exist only if weekend-1 storage decisions respected this.
7. **The boring wing is load-bearing.** Methodology, corrections policy, downloads, API get maintained with the same seriousness as the viral layer. Credibility is the moat's mortar.
8. **No editorializing anywhere in the pipeline.** Not in prompts, not in captions, not in alt text. The register of a seismograph, everywhere, forever. The data is the joke.

---

## §10 Assumption register — what Phase 2 must validate

Every load-bearing external-world assumption, with the features that die if it's false. Opus: evidence + links per item; verdicts flow into per-feature VIABLE / VIABLE-WITH-CHANGES / DEAD calls in `02-RESEARCH.md`.

| ID | Assumption to validate | Kills if false |
|---|---|---|
| **R1** | A daily machine-readable corpus of member speech exists: congress.gov API (and/or GPO) exposes Congressional Record floor speech with tolerable lag; coverage, endpoints, rate limits, actual per-day volume. | Everything. This is the foundation. |
| **R2** | Member press releases are ingestible at scale: sample ≥20 real member sites across both parties/chambers; RSS availability, structure variance, scraping effort/fragility; prior-art scrapers (e.g., unitedstates project) still maintained. | S1 quality, B4, A10 depth |
| **R3** | Bluesky is a usable leg: how many sitting members actively post (real count, both parties — check skew); API/AppView terms for bulk read; bot/automation posting rules and labeling requirements for composite accounts. | Bluesky ingestion leg; primary posting surface |
| **R4** | X: current API pricing tiers for read (sane path or not — 2022's lesson makes this a *question*, never an assumption); automation-label rules; parody/composite-account policy; realistic ban risk for the accounts. | X ingestion; X posting; a chunk of distribution reach |
| **R5** | A free/cheap daily news-agenda baseline with reuse rights exists (GDELT? RSS aggregation of major outlets? something better?) that yields defensible "top topics of the day" rankings. | S3, A7 (asymmetric silence), A8 — the entire Absence family |
| **R6** | The daily pipeline fits the $10/month Anthropic ceiling at realistic corpus size (estimate statements/day × tokens; Haiku-class + batch/caching options **at current published pricing — read the docs, trust no remembered number**). | Distillation depth; S1 cadence; margin for B-tier |
| **R7** | GitHub Actions free tier fits the daily job: scrape N-hundred sources + distill + render cards + commit, within minutes/storage/artifact limits; repo-growth strategy for an append-only corpus (LFS? release assets? split data repo?). | The zero-server constraint; B2 video rendering |
| **R8** | The lane is actually unoccupied: audit prior art — polititweet.org, Politwoops, GovTrack, ProPublica Congress API (alive?), university message-discipline research, any existing talking-point tracker. Map who's adjacent, who's dead, what's genuinely open. | Positioning; possibly nothing technical |
| **R9** | Legal posture is boring: quoting officials' public statements at scale (public record — confirm), platform impersonation/parody rules for clearly-labeled composite accounts, defamation surface of leaderboards built strictly from measured public speech, FEC data reuse terms (C5 only). | Composite accounts as a format; A9 awards framing |
| **R10** | Phrase-matching at this scale is desk-check feasible: n-gram/fingerprint + embedding hybrid over ~10⁵–10⁶ statements/year within the Actions compute budget (bound the approach, don't design it — design is Phase 3). | S2 fidelity, A3, A12, B7, B12 |
| **R11** | Naming availability: domains + Bluesky/X handles for §8 candidates, trademark collisions (esp. "Party Lines" in media/podcast space). | §8 recommendation only |

**Also carry into 02-RESEARCH.md:** for each Tier S/A feature, an explicit verdict line; for each DEAD verdict, one sentence on what (if anything) could replace it. Tier B/C can be batch-verdicted by their controlling R-items.

---

*Phase 1 closed 2026-07-10. Next: Opus, Phase 2, `docs/02-RESEARCH.md`. The handoff note at the top of this file is the brief.*
