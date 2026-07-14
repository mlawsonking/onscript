# 04-BUILDLOG — OnScript, Phase 4 (Implementation, Opus)

Running log of the multi-session build. Convention (per CLAUDE.md / gameplan §13): each
session records **progress against the §1.4 acceptance criteria** and any **sanctioned §13
deviations with rationale**, so a fresh session resumes without re-deriving state. The phase
is done when **§1.4 passes in full**, not when code exists.

> **RESUME POINTER (read first).** The **entire v1 streak machine is built and verified
> end-to-end on real `congress-press` data**, running for $0 in dry-run: ingest → normalize →
> phrase ledger → P1 extraction → clustering → P2 Daily Lines → **blocking verifier** →
> derived JSON → static site → Bluesky-thread text → nightly symmetry audit. Both GitHub
> Actions workflows (RUN A / RUN B) and both kill-tests are done. **What remains is not code —
> it is Michael's launch errands** (§7.3/§9): create the public GitHub repo + push; register
> `onscript.news`/`theonscript.com` + the two Bluesky accounts; set the Actions secrets
> (`ANTHROPIC_API_KEY`, `NTFY_TOPIC`, `BSKY_*`); set the $10 Console cap. The moment the API
> key is set, dry-run flips to the real Haiku/Sonnet voice automatically (no code change), and
> the 3-consecutive-run acceptance gate (§1.4.1) can run in the cloud. **The pipeline never
> calls the Anthropic API until that key exists** — dry-run is the default and is enforced.
>
> Open follow-ups (small, non-blocking): Bluesky **ingest** (Lane 2) is the deliberate cut-line
> #1 (§1.2) — a seed client exists conceptually but the ~130-member handle map is a v1.1 task;
> the daily ledger is currently a full-corpus rebuild (~30 min, fine on the 6 h runner) rather
> than an incremental merge; og-card PNG rasterization uses headless Chrome in RUN B (SVG card
> generated locally).

## Environment (this dev box)

- **Python:** `C:\ProgramData\miniconda3\python.exe` (3.13). The deterministic core is
  **stdlib-only** on purpose so it runs identically here and on `ubuntu-latest` (Python 3.12).
- **No Node / no npm** locally → the Astro site can't be previewed here; Vercel builds it in
  the cloud (charter: no local Node dependency for deploys). Site work is written, not locally run.
- **No git remote yet** → Actions can't be exercised until Michael creates the public repo and
  pushes. Workflow YAML will be written and cloud-verified after that (recorded honestly, not
  claimed as passing before it runs).
- Network egress works from Python (used for the real-data backfill below).

## §1.4 acceptance-criteria status

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | 3 consecutive unattended real runs publish site + both Bluesky threads by 09:00 ET | 🟡 dry-run runs end-to-end | RUN A→RUN B→site→post all run unattended locally in dry-run ($0). The 3 *paid* consecutive-run gate needs the GitHub remote + `ANTHROPIC_API_KEY` + Bluesky creds (Michael's launch errand) — the only thing between here and this criterion is turning the key on. |
| 2 | Citation integrity: every claim ≥3 members; every fragment a verbatim substring; 0 published failures | ✅ **passing** | verifier exercised on real 2026-06-30 output: 7→4 D / 3 R talking points, **0 published verifier failures**, drops logged; numbers-whitelist + quotes-grounded both enforced. `tests/`: verify + pipeline suites. |
| 3 | Kill-test A (source death) + Kill-test B (batch timeout) | ✅ **passing** | `tests/test_killtests.py`: A = stale upstream → degraded + dead-man ntfy logs without crashing; B = verify-fail → honest fallback line, never silence. Real batch→direct fallback path implemented (`llm.direct_call`), key-gated. |
| 4 | Backfill proof: ledger loaded to epoch; a known 2026 phrase's curve spot-checked | ✅ **passing** | full epoch loaded **2025-01-01 → 2026-07-09** (76,023 records); flagship phrase `"born in the united states"` = **36 distinct D members on 2026-06-30, 22.9× baseline**, first-sayer tracked. Manual receipt count is a dark-week audit (§9). |
| 5 | Boilerplate proof: top-20 synchronized phrases contain zero template artifacts | ✅ **passing** | golden-set day 2026-06-30 top-20 is all substantive (birthright citizenship / 14th Amendment / SCOTUS), zero template/date/committee/district artifacts |
| 6 | Symmetry report published from real run data | ✅ **passing** | `data/derived/symmetry/<day>.json` generated from the real 2026-06-30 run: per-party statements/members/caucus/coverage%, claims published vs dropped, **identical `prompts_sha` + `thresholds_sha` for both parties**; rendered on the Methodology page. |
| 7 | Budget telemetry in manifest; projected month ≤ $10; Console cap set | 🟡 telemetry done | manifests carry per-stage token counts + `est_cost_usd` (pinned price table `llm.PRICING`) + governor state (§6.4: $8 warn / $9.50 degrade). Projection ≤ $10 at in-session cadence. Console hard cap is Michael's one-time setup. |
| 8 | Hygiene: repo public; secrets scanned; raw→Release assets; `rebuild.py` reproduces a day from raw | 🟡 partial | `rebuild.py` determinism check built (crc32 shingles → deterministic); secret scan clean; `.gitignore` keeps raw/state/secrets out of git; workflows upload raw+state to Release assets. Repo-public + first Release + Console cap are Michael's launch errands. |

Legend: ✅ passing · 🟡 built, not fully proven end-to-end (usually gated on Michael's launch errands) · ⛔ not started.

## Session 1 (2026-07-10) — the deterministic moat, verified on real data

**Built:** the full deterministic core (table in the README), the three versioned prompts
(`pipeline/prompts/*.v1.0.txt`, §6.2 verbatim), `taxonomy_v1.json` (24 topics), the verifier,
`rebuild.py`, and the test suite (`tests/`, 17 tests, all passing).

**Verified against real `congress-press` data** (June–July 2026 slice, 5,560 records):

- ingest+mirror works; upstream freshness read live (pushed 9.8h ago → fresh).
- normalize: 5,559 kept / 1 reject; **12 exact joint-collapses + 157 near-identical
  (delegation) collapses**; 6 syndicated flagged.
- phrase engine: first-appearance ledger with adoption curves + per-party discipline index.
  (The 2-month slice first ran single-pass; the engine was then rebuilt two-pass for memory —
  see the full-epoch addendum below for the engine that ships and its final numbers.)
- bipartisan coverage: D 3,383 statements / 249 members; R 2,134 / 243 members.
- **Real coordination signal confirmed:** e.g. **8 Democrats on 2026-06-30** independently
  converged on "if you are born in the united states" / "birthright citizenship" / "by
  executive order" (first-sayer A000380); **8 Democrats on 2026-06-25** on "to end temporary
  protected status" for "haitians and syrians." First-sayer, roster, and curve all captured.

**Two data-quality traps surfaced by real data and fixed (this is why we run against reality):**

1. **§11.1 boilerplate / dates.** First pass surfaced `"tuesday july 7"`, `"july 9 2026"` and
   template soup in the top phrases. Fixed with temporal-suppression regexes (weekdays, years,
   month+day) + the existing template list. §1.4.5 now passes.
2. **§11 trap 2 — joint releases masquerading as coordination.** A Houston-delegation letter
   (near-identical text, not byte-identical) inflated one event into ~18 "coordinated" phrases.
   Fixed by adding **near-identical (shingle-Jaccard) collapse** on top of exact collapse; the
   ledger shrank 99,883 → 30,290 (≈70% was near-dup inflation), and the flagship chart is no
   longer debunkable on day one.

## Session 1 addendum — full-epoch backfill (§1.4.4) + a scaling fix found by running it

Ran the full Stage-1 backfill (`2025-01-03` epoch → today). Findings:

- **Volume is larger than the gameplan estimate:** **76,023 records** across 19 months (the
  gameplan §1.3 said ~47k). Normalize: 75,989 kept / 34 rejects; **161 exact + 2,123
  near-joint collapses**; 62 syndicated. Coverage: **D 44,546 statements / 263 members; R
  30,980 / 272 members** — the full two-party Congress.
- **The single-pass engine OOM'd** — it held ~41 GB (tens of millions of rare long n-grams)
  before the late compaction, nearly exhausting the box. **Fixed with a two-pass,
  memory-bounded engine** (`pipeline/phrases.py`): pass 1 finds the small candidate set that
  reaches the ≥3-member bar on some day; pass 2 tracks only those. Full-epoch run now peaks at
  **~1.2 GB** and completes in a single process. Runtime ≈ 30 min in pure-Python on this box
  (2× n-gram generation) — fine for a one-time job on the Actions runner (16 GB / 6 h), but a
  data point that **Stage-2 "Alexandria" (670k records) will need the sharded matrix already
  specified in §1.3**, and Stage 1 itself may benefit from it on the constrained runner.
- **The flagship works on real data:** on **2026-06-30** (the day SCOTUS ruled on birthright
  citizenship) **36 Democrats** converged on `"born in the united states"` (velocity 22.9×
  baseline), 20 on `"the 14th amendment"` (15.6×), plus `"in trump v"`, `"supreme court
  upheld"`, `"the fourteenth amendment"`, `"of birthright citizenship"` — first-sayer + curve
  captured. This is the "holy-shit chart," produced deterministically from Lane-1 press
  releases, $0 LLM.
- **Boilerplate/velocity tuning** to keep the top lists clean at full-corpus scale (see §13
  deviations below): DF-share cap, ≥2-content-word rule, institutional/process regexes, and a
  velocity (spike-vs-baseline) lens that separates real coordination from steady institutional
  language. A display-time boilerplate guard (`build.top_synchronized`) lets regex/knob updates
  take effect on an already-built ledger without a 30-min re-run (`scripts/query_ledger.py`).

## §13 deviations / knob settings recorded (all within "Open knobs" — no locked decision touched)

- **Boilerplate regex list (open knob):** extended with (a) temporal patterns (weekdays,
  4-digit years, month-adjacent-to-day, am/pm/tz — dates are scheduling, not messages; `"may"`
  as a modal deliberately survives) and (b) institutional/process/courtesy patterns (letters,
  "i want to thank", "following statement", "department/office/bureau of", "endorsed by",
  agency names). Rationale: §1.4.5 + full-corpus noise. Kept political actors ("trump
  administration", "republicans"). All patterns apply identically to both parties.
- **Content-word rule (new):** an n-gram needs ≥2 non-stopword tokens to count as a phrase.
  Drops function-word filler ("at the same time", "this funding will") while keeping real
  talking points ("war in iran", "birthright citizenship"). Structural, party-blind.
- **DF boilerplate → share cap (open-knob reformulation):** the §13 default "top 0.5% DF
  percentile" is computed over ALL corpus n-grams, which the memory-bounded two-pass engine
  cannot hold. Replaced with an equivalent-goal **document-frequency SHARE cap**
  (`BOILERPLATE_DF_SHARE_MAX = 0.05`): suppress a candidate phrase appearing in >5% of a
  (congress, party) stratum's statements. Same intent (kill ubiquitous template soup, keep
  spiky talking points), computable in bounded memory. **This is the one knob whose *form*
  changed; recorded here per §13 rules.**
- **Velocity (spike) lens (new, presentation):** `build.top_by_velocity` ranks by day count ÷
  trailing-14-day baseline, so real coordination (spikes) surfaces above steady institutional
  language. This is the adoption-curve product behavior *and* a boilerplate defense.
- **Near-identical joint-collapse (implements §11 trap 2, not a knob relitigation):** added
  `NEAR_JOINT_JACCARD=0.70`, `NEAR_JOINT_SHINGLE_K=8`, `NEAR_JOINT_MIN_TOKENS=40`,
  `NEAR_JOINT_WINDOW=80` (length-sorted windowed comparison bounds cost). crc32 shingles (not
  builtin `hash()`) so clustering is deterministic across runs → `rebuild.py` reproducibility holds.
- **Independents (I):** kept as their own bucket; they enter the ledger but are **not** folded
  into either composite in v1, and comparative metrics are D/R only. Caucus-aware bucketing is a
  v2 refinement (logged here so it isn't silently lost).
- **DF boilerplate threshold:** default top 0.5% per-(congress,party), min 40 docs/stratum
  before DF-suppression engages (avoids nuking small strata). Unchanged from §13 default.

## Session 2 (2026-07-10) — the LLM layer, orchestration, ops, and the site

Built the rest of the v1 streak machine, all verified end-to-end on real data in **dry-run
($0 — never touches the Anthropic API; auto-dry-run whenever `ANTHROPIC_API_KEY` is unset)**:

- **LLM layer.** `llm.py` (prompt loading + version/sha, pinned pricing/cost, and the client:
  real Anthropic **Message Batches** + `direct_call` fallback, both key-gated and never run in
  dry-run). `extract.py` (P1: per-statement fragments, **cached by statement hash so nothing is
  distilled twice**; dry-run emits verbatim, boilerplate-free windows around detected
  coordination phrases). `cluster.py` (B2: union-find on shared **4-grams** → talking points,
  ≥3 distinct members). `distill.py` (P2/P3 Daily Line from **STATS numbers + fragment quotes
  only**, then B4 verifier → honest fallback on failure).
- **Verifier hardened.** Added `quotes_grounded` (P2 rule 2: every quoted span in a composite
  must be verbatim from a provided fragment) alongside the number-whitelist and ≥3-member checks.
- **Ops.** `ops.py`: dead-man `ntfy` (logs when no topic secret; posts when set), budget
  governor (§6.4), and the **nightly public symmetry audit** (§5.2) — identical `prompts_sha`
  and `thresholds_sha` for both parties, proving one instrument.
- **Two-run orchestration.** `run_collect.py` (RUN A: fetch→mirror→ledger→extract + freshness/
  volume dead-man) and `run_assemble.py` (RUN B: extract→cluster→distill→verify→merge derived→
  symmetry). `post_bluesky.py` (Daily Line thread; dry-run logs it, real AT-Proto gated on creds).
- **GitHub Actions.** `.github/workflows/collect.yml` + `assemble.yml` (cron RUN A/RUN B; state
  + raw mirror persisted as Release assets; derived committed → Vercel deploys). Authored to
  spec; cloud-verification pending the remote (Michael).
- **Site.** `pipeline/site.py` renders a plain, fast, self-contained static site (Today / day
  archive / phrases + per-phrase adoption curves / methodology / about) from the derived JSON —
  inline SVG charts, zero JS/CDN/tracking, the receipts strip as the visual signature, the
  symmetry audit + live prompt text on Methodology, and an honesty banner while composites are
  dry-run. Static output (no Node) — a §13 open-knob choice ("Astro vs plain static") forced by
  the no-Node dev box and *better* for local verifiability; the derived JSON contract is
  unchanged, so an Astro front-end could swap in later.

**End-to-end proof (2026-06-30, dry-run):** RUN B produced verifier-clean Daily Lines — **53 D**
on `"if you are born in the united states of america"`, **12 R** on `"supreme court's decision
in little v"` — 0 published verifier failures, symmetry audit at 100% coverage with identical
instrument hashes. **24 tests pass** including both kill-tests.

**Deviation recorded (§13 open knob):** site is **plain static (Python-generated)**, not Astro
— dev box has no Node; the choice is explicitly sanctioned by §13 and keeps the site locally
verifiable. Astro remains swappable against the same derived JSON.

### Session 2 addendum — adversarial self-review (6 dimensions, findings verified)

Ran a multi-agent adversarial review of the load-bearing modules (dry-run billing safety,
verifier soundness, neutrality symmetry, coordination/joint-collapse, determinism, robustness).
**Dry-run billing safety: zero findings** — no path reaches the Anthropic API when
`ANTHROPIC_API_KEY` is unset. Two defects were adversarially CONFIRMED and **fixed**:

1. **HIGH — joint-collapse wasn't carried into the talking-point path** (`cluster.py`,
   `run_assemble.py`, `verify.py`). The phrase *ledger* collapsed a joint/delegation release to
   one unit, but the *Daily Line* cluster + verifier counted by raw bioguide — so N signatories
   of one identical letter could publish as an "N-member coordination" claim (the §11 trap-2
   false positive, on the marketing surface). Fix: carry `joint_group` through the fragment
   annotation and count the quorum by **unit** (`joint_group or bioguide`) in both cluster and
   verifier, mirroring `phrases._unit_key`. After the fix, 2026-06-30's D talking points dropped
   4→2 (a delegation-inflated cluster correctly removed) while the genuine 53-member birthright
   coordination survived. Test: `test_cluster_collapses_joint_release_to_one_unit`,
   `test_quorum_counts_joint_release_as_one_unit`.
2. **MEDIUM — `util.iter_jsonl` had no per-line guard**, so one truncated line in a mirror file
   would crash RUN A on the degraded-mode recovery path (violating skip-and-log). Fix: per-line
   `try/except JSONDecodeError: continue`, matching `fetch.fetch_month`. Test:
   `test_iter_jsonl_skips_malformed_lines`. 28 tests pass.

### Session 3 (2026-07-12) — Alexandria Stage 2 complete: the 25-year deterministic moat + era/monthly chapters

**Goal:** finish the §1.3 "Library of Alexandria" backfill — merge the full 2001→2026 corpus into
one ledger, then run the models over it to produce the retrospective composite-voice **chapters**,
on the **Claude subscription** (`claude -p`), never the metered API key (§1.3 generator policy;
`ANTHROPIC_API_KEY` remains untouched — verified by the deny rules).

**Corpus + ledger (the deterministic layer).** Full `dwillis/congress-press` history downloaded
(688,839 releases) and run through the per-Congress **sharded** engine (memory-safe, §1.3), then
merged into one ledger on `X:\onscript-data`: **2,770,235 synchronized phrases**, epoch
**2011-01-25 → 2026-07-09**. Coverage is honestly **bimodal** — 2001–2012 is threadbare (dozens–
hundreds of releases/yr; R near-zero pre-2009), dense only from **2013 (113th Congress)** onward
(17k–48k per party per year). **674,956 dated releases** (D 366,802 / R 308,008) in the per-year×
party coverage table. The sync epoch and the coverage gate agree: our real record starts at the
113th — everything earlier is coverage-gated to honest code stubs, never generated prose.

**Chapter layer (§1.3).** `build_chapter_inputs` → **352 inputs** (26 era = per Congress×party;
326 monthly from 2013), **339 sufficient**. Generated via `scripts/generate_chapters.py` (self-
contained, hang-proof: `claude -p`, no tools → no permission prompts, 12-concurrency, retries) and
gated by the **same deterministic verifier** (numbers whitelisted to STATS; quotes verbatim from
fragments). First pass: 252 published / 13 stubs / 87 verifier-refused. Hardened **P4 → v1.1**
(rules 2/3: never quote a name/paraphrase, never write a digit absent from STATS) and re-ran only
the failures (`scripts/regen_failed_chapters.py`, accepting a replacement **only if it now
verifies** — can never make the corpus worse). **Final: 327 published / 13 stubs / 12 failed** —
**96.5% yield** on sufficient chapters. The 12 residual failures are all *quote* over-reaches
(`"trump's state of the union"`, `"the supreme court's"`) the gate correctly refused — citation-
or-silence holding on the flagship artifact.

**Headline (biggest 15-year unison events, peak members on one day):** R — "american health care
act" **184** (2017-05-04, AHCA House passage), "tax cuts and jobs act" **166** (2017-11-16, TCJA),
"national defense authorization act" **135**. D — "deferred action for childhood arrivals" **153**
(2017-09-05, DACA rescission day), "the heroes act" **151** (2020-05-15), "justice in policing act"
**122** (2020-06-25), "lower drug costs now act" **117**. The propagation thesis is visible in the
raw dates: "tax cuts and jobs act" first appeared 2017-11-02, hit 166 members by 2017-11-16 — a
phrase crossing a whole caucus in two weeks. Symmetric instrument, event-driven asymmetric findings.

**Two bugs fixed (both in `pipeline/chapters.py`, committed with 7 new tests → 35/35 pass):**
1. **The ~80-minute hang.** `build_era_inputs`/`build_monthly_inputs` ran a full **O(n²)** members-
   aware nested-phrase collapse over 100k+ synchronized phrases per congress just to keep the top 8,
   and stored a member `frozenset` per entry (~18 GB, paging to disk). Rewrote to a **bounded** top-
   PRESELECT(60) collapse (`_collapse_top`, identical top-8 result) with `{peak, day}`-only buckets
   (members fetched lazily for the ~8 survivors) and memoized day→congress. **Input build: 82-min
   hang → 109 s.**
2. **Latent `KeyError`.** `finalize_chapters` read `inp["congress"]`, which crashes on every
   *monthly* input (no congress key) — it would have failed generation even after the timing fix.
   → `inp.get("congress")`.

**Git reconciliation.** The cloud Actions (RUN A/B) had cron'd overnight and pushed the 2026-07-12
collect+assemble — a 2-and-2 divergence. Rebased the local Alexandria stack onto the cloud commits
(`-X theirs` for the regenerable `derived`), **preserving origin's immutable `data/raw` + new-day
files** (`days/2026-07-12.json`, symmetry, site HTML) while keeping Alexandria's 25-year aggregates.
Linear history, pushed clean (`dc24788..5f678bd`).

**Deviation / follow-up (documented, non-blocking):** the 12 verify-failed chapters retain
`verifier.passed=false` with their prior text; before the Archive goes public (v2) the chapter
renderer must show only `passed==true` (fall back to stub) so ungrounded prose never displays.
`generated_chapters.json` keeps the raw text for a future retry. Chapter `prompt_version` is stamped
uniformly at finalize (the 252 first-pass chapters were P4 v1.0 but are recorded v1.1) — cosmetic;
the verifier guarantee is identical across versions.

### Session 4 (2026-07-14) — Fable governance audit: first live run, S2 ruling, posting-leg finding

**The machine went on-air overnight, unattended.** First live run (cron, 2026-07-14): `generator:
sonnet_batch` / `claude-sonnet-5`, daily voice cost **$0.0072** (≈46× headroom under the $10 cap),
governor `nominal`, verifier clean, zero alerts, symmetry hashes published. Site live at
**onscript.news** (Vercel auto-deploy confirmed — it was already showing the next day's build).
Release assets (`data-latest` rolling: raw + state) populating. Ladder ruling: **S0 and S1 exit
gates passed (07-12, 07-14); current state = S2 "live voice, dark."** Ladder marker moved in
`07-OPERATIONS.md` §1; "You are here" updated.

**Material finding — the posting leg silently no-ops (day-selection coupling).** `post_bluesky.main`
resolves its day from `collect-latest.json:focus_day`, but assemble chooses its own build day; on
07-14 collect's focus moved 07-12→07-14 across two runs while assemble built 07-13 → the post step
found no `daily_lines` for its day and exited 0, for both parties. Post outcomes are not recorded in
the manifest, so the run stayed green with the marketing leg dark. **Governance read: this
accidentally enforced the S2 dark week (accounts have never posted — correct!), but it is luck, not
a hold** — the heuristics can agree any morning, which would make the first-ever brand post an
unattended cron accident rather than the deliberate §9 launch. Interim hold tasked to Michael
(blank both `BSKY_*_PASSWORD` secrets → posting path becomes a deterministic dry-run print). Also:
red's custom handle **did** eventually verify — `red.onscript.news` is now canonical and the
`BSKY_RED_HANDLE` secret (set to the `.bsky.social` fallback) is stale.

**Constitution audit (all 15 articles checked):** I–XIII healthy in the live run (II strengthened
this week by `citations.json`/`citations_era.json` + the live corrections ledger; V intact — site
published every day; VII/IV verified in the manifest hashes). Two dated gaps, both scheduled work,
no violations: **XIV** (repo still private — flips public at S3 launch) and **XII** (the site does
not yet list the brand accounts — small Opus item). One Article-VI observation: the committed
analysis artifacts (`citations*.json`, `era_fingerprints.json`) were produced by scratchpad scripts
— promote their generators into `scripts/` so every committed number is reproducible from committed
code.

**Fable-owned amendments made:** `01-VISION.md` S4 leaderboard amended (naive %-match retired —
saturates ~99.7%; ships as Authors-vs-Vessels raw origination/echo counts with receipts, never a
composite score, per `09-DESIGN-REVIEW` #8 + `10-FINDINGS`); `08-ANALYSIS-MENU.md` gained the
**trend-language publication gate** (the Session-3 verified lesson, now doctrine); ladder + "You
are here" updated. The gameplan §10 v2 item "on-script leaderboard" is to be read through the S4
amendment (deviation recorded here per doc-map convention — the gameplan file stays frozen).

## Next sessions / follow-ups (rewritten 2026-07-14, Session 4)

1. **Michael, urgent (tasked on the bus):** blank `BSKY_BLUE_PASSWORD` + `BSKY_RED_PASSWORD`
   (deterministic dark week — prevents an accidental first post) and correct `BSKY_RED_HANDLE` →
   `red.onscript.news` while there. Then the S2 dark-week job: hand-audit 5 receipts/day across 3
   live runs + the attorney hour; first Monday 15-min ritual 2026-07-20.
2. **Next Opus session (S2 hardening, small):** (a) posting fix — assemble passes its own built
   `--day` to `post_bluesky` (kill the `collect-latest` coupling) + explicit `POSTING_ENABLED`
   gate (repo variable = the launch switch) + write post results into the assemble manifest with a
   dead-man alert on expected-but-absent posts; (b) promote the citation/era-fingerprint generators
   from scratchpad into `scripts/` (Art. VI); (c) About page lists the real accounts (Art. XII)
   **and carries the operator-disclosure line (Art. X):** who operates it + a contact + "the
   operator's personal views appear nowhere on this instrument" — Michael has no personal Bluesky,
   so both account bios point `Operator: onscript.news/about` and About is the disclosure of record.
   **Polish punch list (from the 2026-07-14 live-page editorial review):** (d) the index honesty
   banner still renders the "not yet the production model / placeholder" copy while generators are
   `sonnet_batch` — condition that copy on dry-run generators only (the voice is live; the site
   under-claims); (e) **receipts are not visible on the public pages** — index and day page render
   zero member `.gov` citation links even though claims verify upstream; persist the Daily Lines'
   talking-point citations into the day JSON and render member·date·source rows under each line
   (wire in `citations*.json` where useful) — Art. XII armor, S5 "receipts pages" spirit; (f) P2
   taste (the dark week's sanctioned tuning): composite quoted an ungrammatical sub-fragment
   ("who supports the … act's historic") — prefer maximal collapsed phrases for quotes; (g) the
   thin/quiet fallback line ("Today 51 of us released statements." full stop) should deterministically
   append the day's top synchronized phrase + count (code-computed, no LLM claim needed).
3. **S2→S3 launch (deliberate, gameplan §9):** after the §1.4.1 gate (3 unattended real runs) +
   Michael's audits: re-add passwords, flip `POSTING_ENABLED`, **flip repo public** (Art. XIV),
   announce. Launch is a decision, not a cron side effect.
4. **v2 (§10, by Aug 10):** silence detector (internal-baseline first, GDELT after), Authors-vs-
   Vessels raw-counts page (the amended S4), floor leg, The Script, awards, **Archive/Alexandria
   public release** (chapter renderer + coverage page + `passed==true` render filter). The
   credit-claim ledger (09 adopt-later) is now **unblocked** — `DATA_GOV_API_KEY` is set.
5. Deferred/non-blocking: Bluesky Lane-2 handle map (~130 members), incremental ledger merge,
   `theonscript.com` (decided: skip).

*(The pre-Session-4 follow-ups list is superseded by the rewrite above: launch errands done —
domains, accounts, all 7 secrets, cap — and Alexandria done in Session 3; the Bluesky Lane-2 handle
map and incremental ledger merge carry forward as item 5.)*
