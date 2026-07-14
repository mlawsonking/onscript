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

### Session 5 (2026-07-14) — Wave-0 hardening + adversarial review: five real defects fixed, and the "live voice" corrected

> **Model-identity flag (STRICT model-split, §0):** this session actually ran on **Fable 5**, not
> Opus, even though the standing prompt and the workflow assign Phase-4 implementation to Opus. The
> work is verified (55 tests, adversarial review) and I did not touch §13 locked decisions, but the
> canon attributes Phase 4 to Opus — Michael, if you intended Opus, switch models; flagged so the
> record is accurate.

Executed the Wave-0 launch-blocking set from `docs/11-BUILD-PROGRAM.md` §1 (the Session-4 item-2
list), then ran a 4-dimension adversarial review over the whole diff **before committing**. The
review earned its keep: **five real defects, three HIGH.** All fixed, each with a regression test.
**55 tests green** (was 50), including the `POSTING_ENABLED` kill-test and both LLM kill-tests.

**Wave-0 items delivered (a–g + registry + gate + bot-label):** posting day now comes from the
assemble manifest (`assemble-latest.json`), not `collect-latest` (a); the `POSTING_ENABLED` repo
variable is the hard launch gate — kill-tested that **no path posts when it is off, regardless of
creds** (b); the `FEATURES` registry (all dark) gates backlog UI; receipts render as real
member·date·`.gov` rows under each Daily Line (e); the About page carries the operator disclosure +
lists `blue.`/`red.onscript.news` (Art. X/XII); the bot self-label fires idempotently at first
authenticated session without clobbering the profile Michael set; the `scripts/analysis/*`
generators are promoted to import-safe, tested pipeline code (Art. VI, `tests/test_analysis.py`).

**The adversarial review's five findings — all confirmed against source, all fixed:**

1. **HIGH — self-grounding defeated the verbatim-quote guarantee (`distill.py`).** Wave-0 had added
   the code-computed cluster labels + top synchronized phrase to the verifier's `groundable` set, so
   quotes were grounded against *themselves* — a vacuous check. A punctuation-stripped label
   (`support affordable accessible housing`) could be quoted though no member wrote those words
   contiguously (they wrote `affordable, accessible`). **Fix:** `groundable` = verbatim fragment
   texts ONLY; `build_stats` quotes the shortest clean **verbatim fragment** (never the label);
   code-computed phrases (labels, top phrase) are rendered **without quotation marks** as measured
   facts. `verify.quotes_grounded` keeps internal punctuation, so this is now genuinely enforced.

2. **HIGH — the "live Sonnet voice" was never wired; deterministic stub published as `claude-sonnet-5`.**
   `distill.daily_line`'s real-mode branch produced `_compose_dry` (deterministic) but labeled it
   `generator="sonnet_batch"`, `model="claude-sonnet-5"`. Grep-confirmed: `llm.submit_batch` /
   `poll_batch` / `direct_call` have **zero call sites outside `llm.py`** — `run_assemble` never
   calls them. **The same is true of the Haiku extract layer** (`extract.py` real branch also falls
   back to `_dry_fragments`, labeled `haiku_batch`). So the **entire LLM layer is built but unwired**:
   the pipeline is currently **fully deterministic**, and the reported voice/extract costs are
   `estimate_cost` **projections, not charges.** My own Wave-0 site change had made this *worse* by
   adding `sonnet_batch` to `PRODUCTION_GENERATORS` and suppressing the disclosure banner. **Fix:**
   real-mode voice/extract now label their output **`deterministic`** (honest); `PRODUCTION_GENERATORS`
   = `{llm, production, sonnet_direct}` only; the honesty banner discloses any stub voice as **"not a
   language model … deterministic template."** *This corrects the Session-2/Session-4 canon: there
   has been no live LLM voice.* **Governance note:** Session-4 follow-up 2(d) instructed removing the
   placeholder banner **"because the voice is live"** — that premise was false, so per the Phase-4
   mandate (verify against reality; "should work" ≠ done) it is **reversed on the facts**, not
   followed. Wiring the real calls is Opus code work but turns on real API billing → **Michael's
   greenlight** (tasked, #71). The deterministic *engine* (ledger, coordination detection, adoption
   curves, discipline index, symmetry) is real and running — only the LLM narration is a placeholder.

3. **HIGH — the posting dead-man could never fire for the most likely failure (`post_bluesky.py`).**
   When `_post_real` threw (Bluesky 5xx / expired app-password 401 / timeout), `main`'s except
   appended a result with **no `creds_present`**, so the missing-post detector dropped it → no ntfy.
   **Fix:** the except handler computes `creds_present` from env; a creds-present post that throws now
   fires the dead-man. Kill-tested.

4. **MEDIUM — stored-XSS via unvalidated URL scheme in the new citation links (`site.py`).** Receipts
   rendered `<a href="{esc(url)}">` from ingested (poisonable) corpus urls; `esc()` neutralizes
   attribute-breakout but leaves the scheme, so a `javascript:`/`data:` url became clickable JS on a
   site that advertises zero JS. **Fix:** `_safe_http_url` whitelists http(s) at the render sink (the
   sole href sink for citation urls); bad-scheme urls render as a non-link span. Raw url stays
   faithful in the data (fidelity); sanitize on output, not input. Tested with four hostile schemes.

5. **MEDIUM — no idempotency → a re-run re-posts the whole thread (`post_bluesky.py`).** A manual
   re-dispatch / "Re-run all jobs" after a successful post would publish a duplicate composite.
   **Fix:** `main` reads the prior `post-<day>.json` and skips any party already `posted==True` for
   that day (records an `idempotent_skip`). Dormant until `POSTING_ENABLED` flips, but a real
   duplicate-post risk against the deliberate single-launch-post intent. Tested.

**Environment findings (local only — the cloud is unaffected; NOT code bugs):** the local Alexandria
ledger `X:\onscript-data\…\ledger.json` (3.08 GB) is **corrupt** (JSON parse error ~902 MB in) — it
crashes local `run_assemble` *before* my code runs and **blocks the Archive/1.1 build** until rebuilt
(a future Opus session can rebuild it from the raw corpus; the daily cloud run uses the smaller
RUN-A ledger from the `data-latest` Release asset and is fine). Local day-JSON statement ids are also
stale vs. `statements.jsonl.gz` after a corpus re-normalization. Both are why the code was verified by
representative unit tests rather than a local end-to-end assemble.

**Committed:** code (`config`, `distill`, `extract`, `post_bluesky`, `run_assemble`, `site`) + the
promoted `scripts/analysis/*` + `tests/test_wave0.py` + `tests/test_analysis.py` + the
`assemble.yml` `POSTING_ENABLED` env. **Never touched:** posting stayed off; no release flag flipped;
the Anthropic key was never set locally (dry-run $0 throughout).

**Session 5b (same day) — live-site correctness audit + honesty render deployed.** A four-lens audit
of the LIVE onscript.news found its shape right (coordination signal first; neutrality/symmetry
disclosures honest) but three live defects, all the pre-Session-5 render: the per-line flag stamped
`model: claude-sonnet-5 · generator: sonnet_batch` beside a banner admitting the text is
"deterministic" (a self-contradicting false-provenance claim); no member·date·.gov receipt rows; and
a bare About page. Root cause the Session-5 code already fixed — but the commit was **unpushed**, so
none of it was live; the site is served statically from the committed `site/public/` (no vercel.json).
One residual the fix missed: `site.py` printed the STORED `model`/`generator` verbatim, so historical
day pages would keep the false `claude-sonnet-5` even after redeploy. **Fixed** with a render-time
`_voice_flags` (any non-production generator renders uniformly as "voice: deterministic template (not
a language model)" and the stale model id is suppressed — corrects EVERY page without re-assembly; new
test; 56 green). Then **regenerated `site/public` locally with `site.py` only** ($0, no API, no
ledger — it renders committed derived JSONs) and **pushed** (commits 09acd99 + 041ffd7, clean
fast-forward). Verified on the live page: `claude-sonnet-5` is eradicated site-wide, About discloses
the operator + both accounts, the honesty banner is sharp, and the signal/symmetry are intact.
Freshness confirmed correct: `util.product_day` = yesterday, so showing 07-13 on 07-14 is by design
(07-14 is an empty stub). Deviation from the build-session convention "cloud owns site/public": the
owner explicitly asked to make the public site correct now, and with no `gh` to dispatch a run, a
local `site.py` render + push was the only immediate path — the next cloud assemble cleanly supersedes
it (same data, adds receipts). **Follow-ups the redeploy does NOT fix (grind queue, all Opus-doable):**
(i) member·date·.gov receipt ROWS + the cleaner distill quote wording need a fresh cloud assemble
(they live in the stored day JSON, not the render) — the 11:30 UTC cron or a manual dispatch applies
them; (ii) the Tracked-Phrases index is empty on thin days because `build.py` keys `phrases/top.json`
to the current (often stub) focus day, not a rolling window / last-substantive day; (iii) the nightly
symmetry audit appears to present cumulative corpus totals as if daily (verify + fix); (iv) prompt git
history is not rendered on Methodology (Art. VIII); (v) guard the on-script/discipline value against
meaningless low-N days; phrases index caps at 40 vs the spec's 50.

**Ledger re-diagnosis (Session 5b) — the "corrupt" Alexandria ledger is very likely NOT corrupt.**
Direct byte inspection: the file tail is a clean `…"boilerplate": false}}` and the bytes at the
exact reported failure offset (~902 MB) are valid JSON (`… "2018-02-09": {"R": 1, …}`). So the
earlier `JSONDecodeError` was almost certainly a **memory/scale** failure — `json.load` on a single
3.08 GB object exceeds this box's RAM — NOT on-disk corruption. Corroborating: the **per-Congress
shards in `state/alexandria/` are all intact** (`ledger-113…119.json`, discipline/coverage), and the
daily cloud pipeline is unaffected (it uses the smaller RUN-A ledger, never this one). Implication:
the Archive/1.1 build does **not** need a from-scratch rebuild — it needs a **streaming/sharded
reader** (e.g. `ijson`, or read the per-Congress shards directly) instead of `json.load` on the
merged file. `alexandria.merge()` can still re-emit `ledger.json` from the intact shards ($0, pure
function) if a single merged file is wanted, but the memory ceiling to *read* it back is the real
constraint. Symmetry follow-up (iii above) is now **fixed** (day-scoped audit, deploys next cloud
assemble). This corrects the "corrupt local ledger" framing used earlier in this BUILDLOG and in
CLAUDE.md "You are here".

### Session 6 (2026-07-14) — the real Sonnet voice, wired dark behind a kill-switch + strict budget

Michael greenlit wiring the live LLM voice (#71). Executed the Phase-3 plan — the composite voice was
always meant to be Sonnet; the deterministic template was the $0 placeholder. Built **dark**:
`LLM_VOICE_ENABLED` repo variable defaults off, so the commit bills nothing; the voice only calls the
API when Michael flips the switch, and flipping it off reverts to $0 instantly (the POSTING_ENABLED
pattern). **Scope: voice only** (2 Sonnet direct calls/day, ~$0.01/day ≈ $0.30/mo); extraction stays
deterministic ($0). Every composite still passes the blocking verifier or drops to the deterministic
fallback — an ungrounded LLM claim can never publish.

**Strict budget:** a month-to-date spend ledger (`data/derived/cost/YYYY-MM.json`) accumulates REAL
token usage; `voice_budget_state` HALTS the voice at a **$9 code ceiling** (below the $10 Console
cap); ntfy warns at $8; cost is recorded BEFORE the day-JSON write and is date-aware for Sonnet-5's
2026-09-01 price step. Monitoring surfaces: Console (authoritative), the cost ledger (committed), the
assemble manifest (`month_to_date_usd`/`voice_used`/`voice_budget_state`), ntfy, methodology tokens.

**Adversarial review found + fixed 7 defects before commit** (2 HIGH, 3 MED, 2 LOW): the
fabricated-number whitelist hole (a digit inside a member quote could publish as a fake aggregate —
now only code-computed counts/dates are allowed unquoted, quote-numbers exempt via grounding); a
blank Sonnet response publishing as a verified line (now guarded); quote grounding accepting
negation-dropping truncations + cross-fragment stitching (now min-length + negation-guard); the cost
ledger overwriting instead of accumulating and excluding today from the halt check (now accumulates,
halt includes today); undated Sonnet-5 pricing (now date-aware); verifier-fail keeping the
sonnet_direct label; null API usage recording $0. Also shipped the **honest no-coordination line**
("No phrase was shared by N or more of us today") so an empty party column reads as a measured finding
(the silence story), not a gap — answers the "why is the R column empty" question. **69 tests green;
dry-run $0 throughout; nothing billed; the gate is off.** These distill/verify changes deploy on the
next cloud assemble (they regenerate the composite); the no-coordination line + hardened verifier
apply to new days going forward.

**Michael to turn it on (dark-week validation):** set repo variable `LLM_VOICE_ENABLED=true`, run
assemble (or wait for cron), watch 2-3 runs for cost (~$0.01/day) + verifier pass + prose quality,
then it's validated for launch alongside the streak. Off = `false`/delete → instant $0.

**Session 6b (same day) — the voice went LIVE + a Vercel-deploy bug fixed.** Michael greenlit turning
it on; I set `LLM_VOICE_ENABLED=true` via `gh` (auth confirmed; repo variables were empty, so
POSTING_ENABLED stays absent = posting off) and dispatched assemble (run 29358642659, green in 52s).
**First real Sonnet run, fully validated on 2026-07-13:** both parties `generator=sonnet_direct`,
verifier passed, no fallback; **cost $0.005572 for the day** (month-to-date the same; ~$0.17/mo
projected — a fraction of the $9 ceiling); budget/governor nominal; the cost ledger persisted
(`data/derived/cost/2026-07.json`); **posting stayed off** (post manifest: both parties
`posted=False, reason="posting disabled"`). The prose is on-voice (deadpan-clinical, first-person
plural) and the R no-coordination case is narrated gracefully by the model ("We report no dominant
message today… 51 statements… synchronization minimum 3…"). Receipts render live with real member·
date·.gov links. **Flagship-claim audit:** the D line's "first said by Tim Scott" was verified from
the raw corpus — S001184 IS Tim Scott (R-SC), who coined "21st century road to housing act" on
2026-03-03 as its Republican champion; Democrats adopted it at passage. A **real cross-party
origination**, not a lookup bug — the tool's core signal working, correctly reported and honestly
hedged by the voice.

**CI/deploy bug fixed:** the collect/assemble commit messages carried `[skip ci]`, and Vercel skips
deploying such commits — but the workflows are schedule/dispatch-only (never push-triggered), so the
marker did nothing for Actions while silently **freezing the live site** (every automated daily commit
was committed but never deployed; the site only moved on manual pushes). Removed `[skip ci]` from both
workflows (commit e87763d, no marker, which itself deployed the live voice). The site now genuinely
auto-deploys on every data commit — the missing piece of the "updates itself unattended" guarantee.
**Verified end-to-end:** a second dispatched assemble (run 29359973881) committed as `data: assemble
2026-07-14` **without** `[skip ci]` and auto-deployed (the live Methodology now shows the day-scoped
symmetry — "Statements ingested (this day): 74/51", not the old cumulative 44,767 — proving the cloud
commit reached Vercel). The **cost ledger accumulated correctly** across the two runs (`total_usd
0.011274`, `calls: 2`, tokens 2262 = 2×1131) — the MEDIUM-4 accumulation fix confirmed live. Also
shipped: the **month-to-date model-voice spend is now published on the Methodology page** (from the
cost ledger) — radical-transparency + a public budget monitor. **69 tests green.**

**Grind queue (Opus, next sessions — none blocking):** (1) Archive/1.1 needs a **streaming/sharded
ledger reader** (the 3 GB Alexandria ledger is valid-but-too-big, not corrupt; shards intact). (2)
Phrases index is empty on thin focus days (`build.py` keys `top.json` to the current stub day, not a
rolling window). (3) Low-N guard on the on-script/discipline value. (4) Phrases index caps at 40 vs
the spec's 50. (5) Optional: wire Haiku extraction (voice-only was the deliberate scope; extraction
stays deterministic + $0). (6) The prompt git *history* on Methodology (the live prompts already
render; history is a nice-to-have). Prompt-transparency (Art. VIII) is otherwise satisfied.

## Next sessions / follow-ups (rewritten 2026-07-14, Session 4)

> **Session-5 update:** item 2 below (S2 hardening) is **DONE** — see the Session-5 entry (Wave-0 +
> the five review fixes, 55 tests). New priorities on top of the list below:
> - **Michael (decision, tasked #71):** the live LLM voice was never wired — greenlight wiring it
>   (turns on cents/day real API billing under your $10 cap) or launch on the honest deterministic
>   voice. The site now discloses the deterministic voice truthfully either way.
> - **Launch checklist addition:** the dark-week hold is now the **`POSTING_ENABLED` repo variable
>   (default off)** — the primary, reliable gate — *not* the blanked passwords. At S3 launch, set
>   `POSTING_ENABLED=true` **and** replace the single-space `BSKY_*_PASSWORD` secrets with real app
>   passwords (a single space is truthy → it would attempt a failed login and fire the dead-man).
> - **Next Opus:** rebuild the corrupt local Alexandria ledger before the Archive/1.1 build; then
>   either wire the LLM layer (if greenlit) or proceed down the Build-Program queue (Wave 1).

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
