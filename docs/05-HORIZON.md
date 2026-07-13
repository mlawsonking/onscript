# 05-HORIZON — the long game (idea reservoir)

> **What this is.** The banked long-horizon ideation for OnScript, written by Fable (2026-07-11)
> while Fable access exists. **Not a phase gate, not commitments** — a reservoir future planning
> sessions draw from instead of re-ideating. If Fable is unavailable for later planning phases,
> this doc + `01-VISION.md` are the Fable stand-in: pick from here, don't improvise scope.
> Selection rules unchanged: insight × shareability ÷ cost, plus two gates added since v1 —
> **neutrality-risk review** for anything marked ⚠, and **Phase-2-style source validation** for
> anything marked 🔬 (new external corpus = new assumption register before build).
> Nothing here overrides the locked decisions (gameplan §13) or the citation/lane constitution.

---

## §0 The thesis: the archive is a backtest machine

Everything below rests on one property the project acquires with age and already partially has
via the 2001 backfill: **we hold both the language and the ground truth.** Twenty-five years of
who retired, who switched parties, who lost primaries, what passed, who won, what got walked
back. Any hypothesis of the form *"language change X precedes event Y"* can be validated against
history — quietly, cheaply, locally — before a single live prediction is published. The
discipline this imposes is the brand: **OnScript never publishes a predictor it hasn't
backtested, and publishes the backtest with the predictor.** Speculation is what everyone else
sells. We sell receipts, forward and backward in time.

Corollary: every feature below states what it rides on (the ledger, the distillations, the
mirror, a new corpus) so future sessions can cost it honestly.

---

## §1 Flagship horizon bets (the eight worth building the future around)

### H1. Memetic epidemiology — the R₀ of a talking point
Fit contagion models (SIR-family) to the adoption curves the ledger already produces: every
phrase gets a reproduction number, an incubation profile, a susceptible-population estimate
(which members are ever infectable by leadership language vs. immune). "This phrase has an R₀
of 3.2" is instantly graspable, deadpan-compatible, and — fit across 25 years — a publishable
methods contribution. Rides on: ledger only. Cost: local math + one paper-grade writeup.
The epidemiological vocabulary (patient zero, outbreak, immunity) is the product voice waiting
to happen; it is also *neutral by construction* because disease metaphors apply identically to
both parties. **This is the signature science bet.**

### H2. Coordination-mechanism fingerprinting — *how* the memo travels, from shape alone
Adoption-lag distributions have mechanism signatures: a synchronized cliff (all members within
hours, business-day aligned) = memo/leadership push; a broadcast-decay curve anchored to a
cable-news timestamp = TV-driven; a slow S-curve = organic spread; a two-hump curve = memo then
media pickup. Classify every ignition in the ledger by shape. Result: a *mechanism census* of
American political coordination — what share of each party's message is memo-driven vs.
media-driven vs. organic, per era, without a single leak. Rides on: ledger (+ H8/TV corpus
sharpens it). This is the deepest answer to the project's founding question — it detects not
just the private memo but the *distribution system*.

### H3. The Drift Index — language as a leading indicator (backtested) ⚠
Members drift off-script before they announce: retirement, party switch, leadership bid,
primary-challenge posture, swing-seat repositioning. Build per-member centroid-distance
time-series; backtest against 25 years of known departures/switches/challenges; publish only
what survives (with the backtest: precision/recall on 2001–2024 history, in public). Live
product: a quiet weekly "drift watch" — clinically framed ("Sen. X's language is at its
greatest distance from the party centroid since 2019"), never predictive-sounding ("will
retire") unless the backtested model is disclosed and its error bars shown. ⚠ neutrality note:
identical thresholds both parties; drift is reported as measurement, motive is never asserted.
Rides on: ledger + roster history. **The first feature journalists will call "spooky."**

### H4. Upstream patient-zero — who wrote the memo 🔬⚠
Extend first-appearance tracking *upstream* beyond Congress: think-tank reports, advocacy
white papers, party-committee releases, administration statements (public domain), major
op-eds. When "commonsense permitting reform" appears in a foundation PDF in March and in 40
member releases in June, the genealogy now has a root outside the building. This converts the
Upstream Graph from *which member* said it first to *which institution* — the actual authorship
layer of American political language. 🔬 new corpora (each needs source validation: crawl
rights, fair-use excerpting, archive stability); ⚠ framing: provenance is reported as
first-observed-appearance, never as proven authorship. Rides on: ledger + new Lane-3
"upstream" corpus (asymmetric, disclosed, never comparative). **Highest ceiling in this doc.**

### H5. The Ghost Caucus — Congress re-mapped by language, not label
Cluster members in embedding space by what they actually say: the *de facto* caucuses. Which
informal blocs move together across party lines (populists? institutionalists? delegation
blocs?), who sits at cluster boundaries, whose cluster membership *changes* over a career.
Pure structure, no editorializing, deeply novel visualization (the real seating chart).
Longitudinal version: watch the cluster map deform across 25 years — realignment, watched
happening. Rides on: corpus embeddings (4080-friendly one-time + incremental). Neutral-safe:
geometry has no party.

### H6. The Divergence Index — the polarization series
The Mirror Test formalized into a continuous metric: how distinguishable are the parties'
vocabularies, per topic, per chamber, per year, 2001→now. One number with 25 years of history,
updated daily, methodology published — built to be *the* citable polarization index (the VIX
of political speech). Includes its own most interesting inversion: **national-unison events**
(both parties spiking the same phrase the same day) as the rarity log — the frequency of
shared language is itself the polarization story. Rides on: ledger + embeddings. Academic
co-publication is the distribution strategy.

### H7. The Position-Drift Engine (the Contradiction Engine, framed honestly) ⚠
Member's statement today vs. their own archive on the same topic: stance flips, silent
reversals, evolution. The most shareable accountability artifact the corpus can produce and
the most dangerous to neutrality if framed as "hypocrisy." Constitution: symmetrical triggers;
full-context links on both quotes; the artifact reports *change* ("2019: X. 2026: Y."), never
motive; changes-of-mind are legitimate and the framing must leave that possible; human review
lane before this ships, period. Rides on: corpus + embeddings + topic layer. Ship late,
ship careful — but ship: it is the archive's moral payload.

### H8. The Echo Chamber Atlas — Congress ↔ media direction-of-scripting 🔬
Join the phrase ledger to broadcast/caption corpora (TV news captions, transcript archives —
source validation required) with timestamps: for each ignition, did cable say it first or did
Congress? Per network, per party, per era: the *direction* of scripting, measured. Pairs with
H2 (mechanism shapes) to produce the full supply chain of a talking point: institution → memo
→ members → media → members (the echo of the echo). 🔬 caption-source terms/stability are the
gating research. **The feature most likely to be quoted in a media-studies syllabus.**

---

## §2 The families (compact — one line each, tagged)

### Forecasting (everything here obeys §0: backtest first, publish the backtest)
- **Whip-count proxy** — does pre-vote message coordination volume predict passage? Backtest on 25y of roll calls (public). [ledger + congress.gov votes]
- **Phrase survival odds** — lifecycle model predicts which of today's new phrases survives 30 days; the system bets on its own data, publicly, and keeps score. [ledger]
- **Swing-seat accent** — competitive-district members' measurable drift toward district language in election years; backtest vs. actual margins. [ledger + election results] ⚠
- **Cohort discipline forecast** — each freshman class's assimilation rate vs. prior classes; is the machine getting faster? [ledger, needs 2+ cohorts — starts Jan 2027]

### The scientific instrument
- **Half-life drift** — is political language dying faster decade over decade? The attention-economy measurement. [ledger]
- **Complexity/reading-level series** — 25-year trend, both parties, identical rubric, published. [corpus, local] ⚠ (framing: measurement, not mockery)
- **The Renaming Machine** — euphemism genealogies auto-detected: same referent, shifting label ("estate tax"→"death tax" as a *class*, mined not curated). [embeddings + topic layer]
- **Redistricting natural experiment** — members whose district lines changed: language before/after. Clean causal design academics will cite. [ledger + census/district data 🔬-lite]
- **Crisis playbook census** — post-event response templates (shooting, disaster, scandal): sequence, lag, vocabulary, per party per era; has the playbook changed since 2001? [corpus + event dates] ⚠

### External joins (each 🔬 — new source = new mini assumption register)
- **Executive echo** — White House/agency releases (public domain, easy source): does the party lead the President's language or follow it? Lag, per administration, 25 years. 🔬-easy
- **Lobbying overlay** — LDA quarterly filings (public API) vs. topic-spike timing: words per dollar, aggregate only. 🔬 ⚠
- **Polling followership** — message shifts vs. public-opinion series: who chases opinion, who moves first. 🔬 (poll licensing varies)
- **Fundraising-vocabulary creep** — archived campaign-email corpora vs. official releases: when donor language colonizes governing language, measured. 🔬 ⚠
- **Trading-attention join** — STOCK Act disclosures (public) vs. member topic-attention. Aggregate patterns only; explicit editorial policy before any per-member artifact. 🔬 ⚠⚠
- **Judicial echo** — SCOTUS opinion language entering party vocabulary (already observed live: the birthright ruling); formalize opinion→talking-point conversion rates. [ledger + opinions, public domain] 🔬-easy

### Expansion (the instrument is the export)
- **OnScript: Statehouse** — 50 governors first (press offices all publish), then legislatures; same schema, `jurisdiction` key. The 2030 cycle's product. 🔬
- **Candidate mode** — challengers' campaign releases in general elections; disclosed asymmetric lane (no incumbency parity). 🔬 ⚠
- **OnScript: Westminster / international franchises** — Hansard-class open parliamentary corpora; the methodology page is the franchise kit. 🔬
- **The researcher workbench** — hosted corpus + notebooks; academic citations are compounding distribution. [API layer]

### Memory & accountability (the archive as public record)
- **Promise ledger** — "we will pass/repeal X" statements tracked to outcomes across years. [corpus + bill outcomes] ⚠
- **The walk-back genre** — retractions/clarifications/Memory-Hole deletions as a measured corpus: who retreats, how fast, in what words. [Memory Hole + corpus]
- **Anniversary machine** — daily automated "N years ago, the same caucus said —" with receipts; the archive generating its own content forever. [corpus] ⚠ (symmetric triggers)
- **Speech-to-action gap** — statements-per-sponsored-bill ratio: who talks vs. who legislates; leaderboard-grade. [corpus + congress.gov, easy join]
- **Silence streak records** — longest-running bipartisan silences, tracked like records ("Day 400"). [silence detector]
- **The Unison Hall of Fame** — all-time fastest/widest adoptions; the daily machine feeds a permanent record book. [ledger]

### Products & institutions (what OnScript becomes)
- **The annual State of the Script report** — the yearly citable artifact (awards, indices, trends); institutional gravity like an NGO annual report. [everything]
- **Data licensing** — newsroom API tier; the indices as licensed series. Revenue without ads, neutrality-compatible. [API]
- **Election-night overlay** — live on-script-score × results crosswalk; the instrument's Super Bowl, prebuilt from backtests. [ledger + results]
- **Civics/curriculum kit** — the neutral-instrument positioning makes it classroom-safe; foundation-fundable. [derived data]

### Fable specials (weird, defensible, keep)
- **The Autocomplete Congress** — small per-party-per-era language models (4080-trainable, one-time capex per gameplan §1.3 generator policy): talk to the 2005 GOP or the 2013 Democrats; era-vs-era disagreement as interactive exhibit. Séance's time-traveling sibling — same quote-grounding rules apply to anything it *asserts*. ⚠
- **The seating chart that breathes** — H5's cluster map animated over 25 years; realignment as a 30-second film. [embeddings]
- **Phrase weather, long-range** — the memetic weather map (vision B3) upgraded with H1's epidemiology: fronts, pressure systems, *forecasts*. [ledger + H1]

---

## §2.5 The Appendix — the verified-oddity shelf (Freakonomics-class correlations)

> **The case for weird.** Verified oddities are the most shareable genre in data publishing,
> and OnScript holds the two things the genre always lacks: a 25-year corpus to validate
> against, and a voice that never over-claims. The discipline *is* the comedy: "correlation,
> cause unknown, receipts included" is funnier deadpan than any editorialized version. The
> governing insight: **the juiciest findings here are power-position effects, not party
> effects** — they attach to whoever is in/out of power, majority/minority, safe/swing — which
> makes them symmetric by construction (Constitution IV) *and* more interesting: this is what
> losing sounds like, whoever is losing.

**The Appendix rules (extends Constitution IX for correlation content):**
1. Every oddity ships labeled **"correlation, not cause"** — the artifact says so on its face.
2. **Split-era validation:** found on one half of the corpus, confirmed on the other, or it
   doesn't publish. The split is disclosed.
3. **Publish the graveyard:** each Appendix drop states how many hypotheses were tested and
   how many died (an annual "Correlation Graveyard" post lists the casualties). Forking-paths
   disclosure is the anti-p-hack flex *and* a better joke.
4. **Aggregate-only for behavioral claims** — party / chamber / cohort / delegation level;
   never a weird-correlation artifact about one named member (leaderboard-class metrics stay
   governed by their own rules).
5. External joins are 🔬 each (FRED, NOAA, FEC, sports schedules, congress.gov votes — public
   and license-clean candidates only), validated per the standing mini-register process.

**Product form:** *OnScript: The Appendix* — **monthly**, one verified oddity with methodology
+ the running tested/died tally; **annual Graveyard** post. Monthly, not weekly: the pool must
outlast the format, and rigor doesn't rush.

### Top shelf (the seven likeliest "holy shit"s)
- **The memo travels west with the sun** — adoption-curve lag by member time zone: if
  coordinated phrases land in eastern releases hours before Pacific ones, the private memo's
  morning distribution schedule is visible from public data alone. [ledger only — near-free]
- **The gas-price thermostat** — the exact price at which each party *starts* and *stops*
  saying "gas prices," by in-/out-of-power position. Hypothesis: the activation thresholds
  differ by who holds the White House, not by party. [FRED 🔬]
- **The Performance Gap** — every member's commemorative/birthday statements are their sincere
  linguistic baseline; distance between that voice and their political voice = how much of the
  job is performance, measurable per party/cohort/era. [corpus only]
- **The Voldemort Index** — how long before an opposing president stops being *named*
  ("Trump" → "the administration"; "Biden" → "the White House"): name-avoidance rate per
  president per party, 2001→now. [corpus only]
- **The Friday Night Dump + the Super Bowl burial window** — the folk theory of news-burying,
  finally measured across 25 years: walk-back vocabulary by day-of-week, holiday eves, and
  big-game weeks; which party buries harder; whether the Dump died with the 24/7 cycle.
  [corpus + calendar]
- **Adjective inflation** — the devaluation curve of "unprecedented," "radical," "extreme,"
  "historic": usage vs. era, the year each word lost its meaning, measured like currency
  collapse. [corpus only]
- **What losing sounds like** — the minority-party linguistic signature: "the American people"
  invocation rate, rhetorical-question rate, and exclamation density as a function of majority
  status — hypothesis: you cite the boss more when you're losing, in both parties, in every
  era. [corpus + control-of-chambers table]

### The rest of the shelf (one line each; all obey the Appendix rules)
- **Recess metabolism** — reading level drops when Congress goes home (DC voice vs. district voice, by calendar). [corpus]
- **The August effect** — message discipline by month: does coordination collapse or *tighten* when comms staff pre-schedule the beach weeks? [ledger]
- **The 90-day snap** — discipline as dose-response to days-until-election; the shape of the curve is the finding. [ledger + election calendar]
- **The half-life of "bipartisan"** — spikes N days before shutdown deadlines, vanishes after; measured across every fiscal cliff since 2001. [corpus + deadline table]
- **Daylight-saving typos** — error/correction rate the week after spring-forward (Memory Hole edit-detection as typo telemetry). [Memory Hole]
- **Heat-wave vocabulary** — district-level NOAA extremes vs. that delegation's topic/outrage mix that week; who gets loud and who goes quiet when it's 100°F at home. [NOAA 🔬 ⚠]
- **Disaster latency map** — hours-to-first-statement after FEMA declarations: own-district vs. other-party districts, 25 years. [FEMA 🔬 ⚠]
- **The mascot commodity** — each era's chosen inflation symbol (gas '08, eggs '24) vs. its actual CPI weight; Congress's grocery cart vs. yours. [FRED/BLS 🔬]
- **Congress as lagging indicator** — crypto/AI/housing mention curves peak N weeks after the underlying price/trend peaks; the measured lag of institutional attention. [FRED + trends 🔬]
- **The seniority vocabulary curse** — unique-vocabulary count vs. terms served; how many words a decade in office costs. [corpus + roster]
- **Adoption speed vs. age/cohort** — do younger members parrot faster (extremely online) or slower (less leadership-plugged)? Either answer surprises half the audience. [ledger + roster]
- **The safe-seat vessel hypothesis** — margin-of-victory vs. on-script score: does safety free a member's voice or complete the assimilation? [ledger + election results 🔬]
- **Committee vocabulary infection** — days from committee assignment to "family farms" (Ag), "readiness" (Armed Services) entering a member's active vocabulary. [corpus + committee rosters]
- **The lawyer hedge** — JD holders' hedged-language rate ("alleged," "pursuant") vs. everyone else; do lawyers dodge measurably more? [corpus + bios]
- **Pronoun economics** — the I/we ratio by party, tenure, chamber, and days-to-election ("I" season is primary season). [corpus]
- **Punctuation archaeology** — first exclamation point, first ALL-CAPS, first emoji in an official congressional press release (date, chamber, member-cohort); the exclamation divide by party/era. [corpus]
- **Thoughts-and-prayers half-life** — the decay curve of condolence vocabulary across repeated mass-casualty events, 2001→now; whether the playbook's timing has changed. [corpus + event dates ⚠ — handle with the gravity it deserves]
- **Bipartisan unison on nature** — eclipses, cicada years, and space landings as the only reliable cross-party unison events; the "we agree about the sky" baseline against which all other unison is measured. [ledger]
- **The pander-latency leaderboard** — hours from cultural moment (final, album drop, viral event) to first congressional invocation, by party/cohort. [corpus + events 🔬]
- **Home-team mood** — delegation-level Monday-release sentiment after the local NFL team wins/loses (there is real literature on game outcomes moving judicial and electoral behavior — cite it, then measure Congress). [schedules 🔬 ⚠ aggregate-only]
- **Fast-parrot fundraising** — do early talking-point adopters raise more small-dollar money than mavericks, or less? Committee-level FEC aggregates only; either answer is a headline. [FEC 🔬 ⚠]
- **The null-result banger** — "congressional messaging has zero predictive power for markets — we checked, here's how": publishing rigorous *absence* is on-brand, credible, and rarer than any positive finding. [FRED 🔬]



Nothing here preempts gameplan §10 (v2 silence/leaderboard/floor → v3 alerts/Memory
Hole/upstream → season-2 assimilation). The natural insertion points: **H1/H2/H6 ride the
existing ledger** and fit any post-v3 window as local-math features; **H3/H7 want the topic
layer + embeddings** (v2/v3 infrastructure) plus the neutrality review; **H4/H8 and all 🔬
items need a Phase-2-style validation pass first** — new sources get the same adversarial
treatment R1–R11 got, no exceptions; **expansion items are 2027+ decisions** made from a
position of authority, not ambition. When a future session plans v4+, it starts here, scores
against the standing rubric, and kills without sentiment — same as ever. **Appendix (§2.5)
items are post-v3 content features:** the corpus-only ones ride the existing ledger nearly
free and make ideal S∞ steward-state material (one validated oddity a month is a sustainable
solo cadence); every external join stays behind its 🔬 gate.

---

*Banked 2026-07-11 (Fable). The archive converts speculation into backtests; build accordingly.*
