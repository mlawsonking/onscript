# 04: OnScript phase 4 build log (implementation, Opus)

> **Normalization note (2026-07-23).** Prose was normalized under `docs/25-DOCUMENTATION-VOICE-BRIEF.md`.
> Findings, decisions, and chronology are unchanged. The original wording is available at commit
> `cbf9f8c`.

> **SHA notice (2026-07-17).** A `git filter-repo` history rewrite (Article XIII: the two
> private-individual names replaced with their redaction labels in every historical blob)
> changed **every commit SHA in this repository**. Commit hashes cited below that predate
> 2026-07-17 are **pre-rewrite labels**, historical references, not live pointers. The
> content of every commit is otherwise intact (HEAD tree byte-identical; 164 commits
> preserved). Post-rewrite anchors: `fdcda1f` → `c44579c` (the #145 privacy deploy),
> `d816066` → `457f90e` (L1 lane isolation).

Running log of the multi-session build. Convention (per CLAUDE.md / gameplan §13): each
session records **progress against the §1.4 acceptance criteria** and any **sanctioned §13
deviations with rationale**, so a fresh session resumes without re-deriving state. The phase
is done when **§1.4 passes in full**, not when code exists.

> **RESUME POINTER (read first).** The **entire v1 streak machine is built and verified
> end-to-end on real `congress-press` data**, running for $0 in dry-run: ingest → normalize →
> phrase ledger → P1 extraction → clustering → P2 Daily Lines → **blocking verifier** →
> derived JSON → static site → Bluesky-thread text → nightly symmetry audit. Both GitHub
> Actions workflows (RUN A / RUN B) and both failure tests are done. **What remains is not code ,
> it is Michael's launch errands** (§7.3/§9): create the public GitHub repo + push; register
> `onscript.news`/`theonscript.com` + the two Bluesky accounts; set the Actions secrets
> (`ANTHROPIC_API_KEY`, `NTFY_TOPIC`, `BSKY_*`); set the $10 Console cap. The moment the API
> key is set, dry-run flips to the actual Haiku/Sonnet voice automatically (no code change), and
> the 3-consecutive-run acceptance gate (§1.4.1) can run in the cloud. **The pipeline never
> calls the Anthropic API until that key exists**, dry-run is the default and is enforced.
>
> Open follow-ups (small, non-blocking): Bluesky **ingest** (Lane 2) is the deliberate cut-line
> #1 (§1.2), a seed client exists conceptually but the ~130-member handle map is a v1.1 task;
> the daily ledger is currently a full-corpus rebuild (~30 min, fine on the 6 h runner) rather
> than an incremental merge; og-card PNG rasterization uses headless Chrome in RUN B (SVG card
> generated locally).

## Environment (this dev box)

- **Python:** `C:\ProgramData\miniconda3\python.exe` (3.13). The deterministic core is
  **stdlib-only** on purpose so it runs identically here and on `ubuntu-latest` (Python 3.12).
- **No Node / no npm** locally → the Astro site can't be previewed here; Vercel builds it in
  the cloud (charter: no local Node dependency for deploys). Site work is written, not locally run.
- **No git remote yet** → Actions can't be exercised until Michael creates the public repo and
  pushes. Workflow YAML will be written and cloud-verified after that (recorded accurately, not
  claimed as passing before it runs).
- Network egress works from Python (used for the actual-data backfill below).

## §1.4 acceptance-criteria status

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | 3 consecutive unattended real runs publish site + both Bluesky threads by 09:00 ET | 🟡 dry-run runs end-to-end | RUN A→RUN B→site→post all run unattended locally in dry-run ($0). The 3 *paid* consecutive-run gate needs the GitHub remote + `ANTHROPIC_API_KEY` + Bluesky creds (Michael's launch errand), the only thing between here and this criterion is turning the key on. |
| 2 | Citation integrity: every claim ≥3 members; every fragment a verbatim substring; 0 published failures | ✅ **passing** | verifier exercised on real 2026-06-30 output: 7→4 D / 3 R talking points, **0 published verifier failures**, drops logged; numbers-whitelist + quotes-grounded both enforced. `tests/`: verify + pipeline suites. |
| 3 | Failure tests A (source death) + Failure tests B (batch timeout) | ✅ **passing** | `tests/test_killtests.py`: A = stale upstream → degraded + dead-man ntfy logs without crashing; B = verify-fail → accurate fallback line, never silence. Real batch→direct fallback path implemented (`llm.direct_call`), key-gated. |
| 4 | Backfill proof: ledger loaded to epoch; a known 2026 phrase's curve spot-checked | ✅ **passing** | full epoch loaded **2025-01-01 → 2026-07-09** (76,023 records); flagship phrase `"born in the united states"` = **36 distinct D members on 2026-06-30, 22.9× baseline**, first-sayer tracked. Manual receipt count is a dark-week audit (§9). |
| 5 | Boilerplate proof: top-20 synchronized phrases contain zero template artifacts | ✅ **passing** | golden-set day 2026-06-30 top-20 is all substantive (birthright citizenship / 14th Amendment / SCOTUS), zero template/date/committee/district artifacts |
| 6 | Symmetry report published from real run data | ✅ **passing** | `data/derived/symmetry/<day>.json` generated from the actual 2026-06-30 run: per-party statements/members/caucus/coverage%, claims published vs dropped, **identical `prompts_sha` + `thresholds_sha` for both parties**; rendered on the Methodology page. |
| 7 | Budget telemetry in manifest; projected month ≤ $10; Console cap set | 🟡 telemetry done | manifests carry per-stage token counts + `est_cost_usd` (pinned price table `llm.PRICING`) + governor state (§6.4: $8 warn / $9.50 degrade). Projection ≤ $10 at in-session cadence. Console hard cap is Michael's one-time setup. |
| 8 | Hygiene: repo public; secrets scanned; raw→Release assets; `rebuild.py` reproduces a day from raw | 🟡 partial | `rebuild.py` determinism check built (crc32 shingles → deterministic); secret scan clean; `.gitignore` keeps raw/state/secrets out of git; workflows upload raw+state to Release assets. Repo-public + first Release + Console cap are Michael's launch errands. |

Legend: ✅ passing · 🟡 built, not fully proven end-to-end (usually gated on Michael's launch errands) · ⛔ not started.

## Session 1 (2026-07-10), the deterministic long-term value, verified on real data

**Built:** the full deterministic core (table in the README), the three versioned prompts
(`pipeline/prompts/*.v1.0.txt`, §6.2 verbatim), `taxonomy_v1.json` (24 topics), the verifier,
`rebuild.py`, and the test suite (`tests/`, 17 tests, all passing).

**Verified against real `congress-press` data** (June–July 2026 slice, 5,560 records):

- ingest+mirror works; upstream freshness read live (pushed 9.8h ago → fresh).
- normalize: 5,559 kept / 1 reject; **12 exact joint-collapses + 157 near-identical
  (delegation) collapses**; 6 syndicated flagged.
- phrase engine: first-appearance ledger with adoption curves + per-party discipline index.
  (The 2-month slice first ran single-pass; the engine was then rebuilt two-pass for memory ,
  see the full-epoch addendum below for the engine that ships and its final numbers.)
- bipartisan coverage: D 3,383 statements / 249 members; R 2,134 / 243 members.
- **Real coordination signal confirmed:** e.g. **8 Democrats on 2026-06-30** independently
  converged on "if you are born in the united states" / "birthright citizenship" / "by
  executive order" (first-sayer A000380); **8 Democrats on 2026-06-25** on "to end temporary
  protected status" for "haitians and syrians." First-sayer, roster, and curve all captured.

**Two data-quality traps surfaced by real data and fixed (it is why we run against reality):**

1. **§11.1 boilerplate / dates.** First pass surfaced `"tuesday july 7"`, `"july 9 2026"` and
   template soup in the top phrases. Fixed with temporal-suppression regexes (weekdays, years,
   month+day) + the existing template list. §1.4.5 now passes.
2. **§11 trap 2, joint releases masquerading as coordination.** A Houston-delegation letter
   (near-identical text, not byte-identical) inflated one event into ~18 "coordinated" phrases.
   Fixed by adding **near-identical (shingle-Jaccard) collapse** on top of exact collapse; the
   ledger shrank 99,883 → 30,290 (≈70% was near-dup inflation), and the flagship chart is no
   longer debunkable on day one.

## Session 1 addendum, full-epoch backfill (§1.4.4) + a scaling fix found by running it

Ran the full Stage-1 backfill (`2025-01-03` epoch → today). Findings:

- **Volume is larger than the gameplan estimate:** **76,023 records** across 19 months (the
  gameplan §1.3 said ~47k). Normalize: 75,989 kept / 34 rejects; **161 exact + 2,123
  near-joint collapses**; 62 syndicated. Coverage: **D 44,546 statements / 263 members; R
  30,980 / 272 members**, the full two-party Congress.
- **The single-pass engine OOM'd**, it held ~41 GB (tens of millions of rare long n-grams)
  before the late compaction, nearly exhausting the box. **Fixed with a two-pass,
  memory-bounded engine** (`pipeline/phrases.py`): pass 1 finds the small candidate set that
  reaches the ≥3-member bar on some day; pass 2 tracks only those. Full-epoch run now peaks at
  **~1.2 GB** and completes in a single process. Runtime ≈ 30 min in pure-Python on this box
  (2× n-gram generation), fine for a one-time job on the Actions runner (16 GB / 6 h), but a
  data point that **Stage-2 "Alexandria" (670k records) will need the sharded matrix already
  specified in §1.3**, and Stage 1 itself may benefit from it on the constrained runner.
- **The flagship works on real data:** on **2026-06-30** (the day SCOTUS ruled on birthright
  citizenship) **36 Democrats** converged on `"born in the united states"` (velocity 22.9×
  baseline), 20 on `"the 14th amendment"` (15.6×), plus `"in trump v"`, `"supreme court
  upheld"`, `"the fourteenth amendment"`, `"of birthright citizenship"`, first-sayer + curve
  captured. It is the high-signal chart, produced deterministically from Lane-1 press
  releases, $0 LLM.
- **Boilerplate/velocity tuning** to keep the top lists clean at full-corpus scale (see §13
  deviations below): DF-share cap, ≥2-content-word rule, institutional/process regexes, and a
  velocity (spike-vs-baseline) lens that separates real coordination from steady institutional
  language. A display-time boilerplate guard (`build.top_synchronized`) lets regex/knob updates
  take effect on an already-built ledger without a 30-min re-run (`scripts/query_ledger.py`).

## §13 deviations / knob settings recorded (all within "Open knobs", no locked decision touched)

- **Boilerplate regex list (open knob):** extended with (a) temporal patterns (weekdays,
  4-digit years, month-adjacent-to-day, am/pm/tz, dates are scheduling, not messages; `"may"`
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
  spiky talking points), computable in bounded memory. **It is the one knob whose *form*
  changed; recorded here per §13 rules.**
- **Velocity (spike) lens (new, presentation):** `build.top_by_velocity` ranks by day count ÷
  trailing-14-day baseline, so real coordination (spikes) surfaces above steady institutional
  language. It is the adoption-curve product behavior *and* a boilerplate defense.
- **Near-identical joint-collapse (implements §11 trap 2, not a knob relitigation):** added
  `NEAR_JOINT_JACCARD=0.70`, `NEAR_JOINT_SHINGLE_K=8`, `NEAR_JOINT_MIN_TOKENS=40`,
  `NEAR_JOINT_WINDOW=80` (length-sorted windowed comparison bounds cost). crc32 shingles (not
  builtin `hash()`) so clustering is deterministic across runs → `rebuild.py` reproducibility holds.
- **Independents (I):** kept as their own bucket; they enter the ledger but are **not** folded
  into either composite in v1, and comparative metrics are D/R only. Caucus-aware bucketing is a
  v2 refinement (logged here so it isn't silently lost).
- **DF boilerplate threshold:** default top 0.5% per-(congress,party), min 40 docs/stratum
  before DF-suppression engages (avoids nuking small strata). Unchanged from §13 default.

## Session 2 (2026-07-10), the LLM layer, orchestration, ops, and the site

Built the rest of the v1 streak machine, all verified end-to-end on real data in **dry-run
($0; never touches the Anthropic API; auto-dry-run whenever `ANTHROPIC_API_KEY` is unset)**:

- **LLM layer.** `llm.py` (prompt loading + version/sha, pinned pricing/cost, and the client:
  real Anthropic **Message Batches** + `direct_call` fallback, both key-gated and never run in
  dry-run). `extract.py` (P1: per-statement fragments, **cached by statement hash so nothing is
  distilled twice**; dry-run emits verbatim, boilerplate-free windows around detected
  coordination phrases). `cluster.py` (B2: union-find on shared **4-grams** → talking points,
  ≥3 distinct members). `distill.py` (P2/P3 Daily Line from **STATS numbers + fragment quotes
  only**, then B4 verifier → accurate fallback on failure).
- **Verifier hardened.** Added `quotes_grounded` (P2 rule 2: every quoted span in a composite
  must be verbatim from a provided fragment) alongside the number-whitelist and ≥3-member checks.
- **Ops.** `ops.py`: dead-man `ntfy` (logs when no topic secret; posts when set), budget
  governor (§6.4), and the **nightly public symmetry audit** (§5.2), identical `prompts_sha`
  and `thresholds_sha` for both parties, proving one instrument.
- **Two-run orchestration.** `run_collect.py` (RUN A: fetch→mirror→ledger→extract + freshness/
  volume dead-man) and `run_assemble.py` (RUN B: extract→cluster→distill→verify→merge derived→
  symmetry). `post_bluesky.py` (Daily Line thread; dry-run logs it, real AT-Proto gated on creds).
- **GitHub Actions.** `.github/workflows/collect.yml` + `assemble.yml` (cron RUN A/RUN B; state
  + raw mirror persisted as Release assets; derived committed → Vercel deploys). Authored to
  spec; cloud-verification pending the remote (Michael).
- **Site.** `pipeline/site.py` renders a plain, fast, self-contained static site (Today / day
  archive / phrases + per-phrase adoption curves / methodology / about) from the derived JSON ,
  inline SVG charts, zero JS/CDN/tracking, the receipts strip as the visual signature, the
  symmetry audit + live prompt text on Methodology, and an accuratey banner while composites are
  dry-run. Static output (no Node), a §13 open-knob choice ("Astro vs plain static") forced by
  the no-Node dev box and *better* for local verifiability; the derived JSON contract is
  unchanged, so an Astro front-end could swap in later.

**End-to-end proof (2026-06-30, dry-run):** RUN B produced verifier-clean Daily Lines, **53 D**
on `"if you are born in the united states of america"`, **12 R** on `"supreme court's decision
in little v"`, 0 published verifier failures, symmetry audit at 100% coverage with identical
instrument hashes. **24 tests pass** including both failure tests.

**Deviation recorded (§13 open knob):** site is **plain static (Python-generated)**, not Astro
, dev box has no Node; the choice is explicitly sanctioned by §13 and keeps the site locally
verifiable. Astro remains swappable against the same derived JSON.

### Session 2 addendum, adversarial self-review (6 dimensions, findings verified)

Ran a multi-agent adversarial review of the critical modules (dry-run billing safety,
verifier soundness, neutrality symmetry, coordination/joint-collapse, determinism, robustness).
**Dry-run billing safety: zero findings**, no path reaches the Anthropic API when
`ANTHROPIC_API_KEY` is unset. Two defects were adversarially CONFIRMED and **fixed**:

1. **HIGH, joint-collapse wasn't carried into the talking-point path** (`cluster.py`,
   `run_assemble.py`, `verify.py`). The phrase *ledger* collapsed a joint/delegation release to
   one unit, but the *Daily Line* cluster + verifier counted by raw bioguide, so N signatories
   of one identical letter could publish as an "N-member coordination" claim (the §11 trap-2
   false positive, on the marketing surface). Fix: carry `joint_group` through the fragment
   annotation and count the quorum by **unit** (`joint_group or bioguide`) in both cluster and
   verifier, mirroring `phrases._unit_key`. After the fix, 2026-06-30's D talking points dropped
   4→2 (a delegation-inflated cluster correctly removed) while the genuine 53-member birthright
   coordination survived. Test: `test_cluster_collapses_joint_release_to_one_unit`,
   `test_quorum_counts_joint_release_as_one_unit`.
2. **MEDIUM, `util.iter_jsonl` had no per-line guard**, so one truncated line in a mirror file
   would crash RUN A on the degraded-mode recovery path (violating skip-and-log). Fix: per-line
   `try/except JSONDecodeError: continue`, matching `fetch.fetch_month`. Test:
   `test_iter_jsonl_skips_malformed_lines`. 28 tests pass.

### Session 3 (2026-07-12), Alexandria Stage 2 complete: the 25-year deterministic long-term value + era/monthly chapters

**Goal:** finish the §1.3 "Library of Alexandria" backfill, merge the full 2001→2026 corpus into
one ledger, then run the models over it to produce the retrospective composite-voice **chapters**,
on the **Claude subscription** (`claude -p`), never the metered API key (§1.3 generator policy;
`ANTHROPIC_API_KEY` remains untouched, verified by the deny rules).

**Corpus + ledger (the deterministic layer).** Full `dwillis/congress-press` history downloaded
(688,839 releases) and run through the per-Congress **sharded** engine (memory-safe, §1.3), then
merged into one ledger on `X:\onscript-data`: **2,770,235 synchronized phrases**, epoch
**2011-01-25 → 2026-07-09**. Coverage is accurately **bimodal**, 2001–2012 is threadbare (dozens–
hundreds of releases/yr; R near-zero pre-2009), dense only from **2013 (113th Congress)** onward
(17k–48k per party per year). **674,956 dated releases** (D 366,802 / R 308,008) in the per-year×
party coverage table. The sync epoch and the coverage gate agree: our real record starts at the
113th, everything earlier is coverage-gated to accurate code stubs, never generated prose.

**Chapter layer (§1.3).** `build_chapter_inputs` → **352 inputs** (26 era = per Congress×party;
326 monthly from 2013), **339 sufficient**. Generated via `scripts/generate_chapters.py` (self-
contained, hang-proof: `claude -p`, no tools → no permission prompts, 12-concurrency, retries) and
gated by the **same deterministic verifier** (numbers whitelisted to STATS; quotes verbatim from
fragments). First pass: 252 published / 13 stubs / 87 verifier-refused. Hardened **P4 → v1.1**
(rules 2/3: never quote a name/paraphrase, never write a digit absent from STATS) and re-ran only
the failures (`scripts/regen_failed_chapters.py`, accepting a replacement **only if it now
verifies**, can never make the corpus worse). **Final: 327 published / 13 stubs / 12 failed** ,
**96.5% yield** on sufficient chapters. The 12 residual failures are all *quote* over-reaches
(`"trump's state of the union"`, `"the supreme court's"`) the gate correctly refused, citation-
or-silence holding on the flagship artifact.

**Headline (biggest 15-year unison events, peak members on one day):** R, "american health care
act" **184** (2017-05-04, AHCA House passage), "tax cuts and jobs act" **166** (2017-11-16, TCJA),
"national defense authorization act" **135**. D, "deferred action for childhood arrivals" **153**
(2017-09-05, DACA rescission day), "the heroes act" **151** (2020-05-15), "justice in policing act"
**122** (2020-06-25), "lower drug costs now act" **117**. The propagation thesis is visible in the
raw dates: "tax cuts and jobs act" first appeared 2017-11-02, hit 166 members by 2017-11-16, a
phrase crossing a whole caucus in two weeks. Symmetric instrument, event-driven asymmetric findings.

**Two bugs fixed (both in `pipeline/chapters.py`, committed with 7 new tests → 35/35 pass):**
1. **The ~80-minute hang.** `build_era_inputs`/`build_monthly_inputs` ran a full **O(n²)** members-
   aware nested-phrase collapse over 100k+ synchronized phrases per congress just to keep the top 8,
   and stored a member `frozenset` per entry (~18 GB, paging to disk). Rewrote to a **bounded** top-
   PRESELECT(60) collapse (`_collapse_top`, identical top-8 result) with `{peak, day}`-only buckets
   (members fetched lazily for the ~8 survivors) and memoized day→congress. **Input build: 82-min
   hang → 109 s.**
2. **Latent `KeyError`.** `finalize_chapters` read `inp["congress"]`, which crashes on every
   *monthly* input (no congress key), it would have failed generation even after the timing fix.
   → `inp.get("congress")`.

**Git reconciliation.** The cloud Actions (RUN A/B) had cron'd overnight and pushed the 2026-07-12
collect+assemble, a 2-and-2 divergence. Rebased the local Alexandria stack onto the cloud commits
(`-X theirs` for the regenerable `derived`), **preserving origin's immutable `data/raw` + new-day
files** (`days/2026-07-12.json`, symmetry, site HTML) while keeping Alexandria's 25-year aggregates.
Linear history, pushed clean (`dc24788..5f678bd`).

**Deviation / follow-up (documented, non-blocking):** the 12 verify-failed chapters retain
`verifier.passed=false` with their prior text; before the Archive goes public (v2) the chapter
renderer must show only `passed==true` (fall back to stub) so ungrounded prose never displays.
`generated_chapters.json` keeps the raw text for a future retry. Chapter `prompt_version` is stamped
uniformly at finalize (the 252 first-pass chapters were P4 v1.0 but are recorded v1.1), cosmetic;
the verifier guarantee is identical across versions.

### Session 4 (2026-07-14), Fable governance audit: first live run, S2 ruling, posting-leg finding

**The machine went on-air overnight, unattended.** First live run (cron, 2026-07-14): `generator:
sonnet_batch` / `claude-sonnet-5`, daily voice cost **$0.0072** (≈46× headroom under the $10 cap),
governor `nominal`, verifier clean, zero alerts, symmetry hashes published. Site live at
**onscript.news** (Vercel auto-deploy confirmed, it was already showing the next day's build).
Release assets (`data-latest` rolling: raw + state) populating. Ladder ruling: **S0 and S1 exit
gates passed (07-12, 07-14); current state = S2 "live voice, dark."** Ladder marker moved in
`07-OPERATIONS.md` §1; "You are here" updated.

**Material finding, the posting leg silently no-ops (day-selection coupling).** `post_bluesky.main`
resolves its day from `collect-latest.json:focus_day`, but assemble chooses its own build day; on
07-14 collect's focus moved 07-12→07-14 across two runs while assemble built 07-13 → the post step
found no `daily_lines` for its day and exited 0, for both parties. Post outcomes are not recorded in
the manifest, so the run stayed green with the marketing leg dark. **Governance read: this
accidentally enforced the S2 dark week (accounts have never posted, correct!), but it is luck, not
a hold**, the heuristics can agree any morning, which would make the first-ever brand post an
unattended cron accident rather than the deliberate §9 launch. Interim hold tasked to Michael
(blank both `BSKY_*_PASSWORD` secrets → posting path becomes a deterministic dry-run print). Also:
red's custom handle **did** eventually verify, `red.onscript.news` is now canonical and the
`BSKY_RED_HANDLE` secret (set to the `.bsky.social` fallback) is stale.

**Constitution audit (all 15 articles checked):** I–XIII healthy in the live run (II strengthened
this week by `citations.json`/`citations_era.json` + the live corrections ledger; V intact, site
published every day; VII/IV verified in the manifest hashes). Two dated gaps, both scheduled work,
no violations: **XIV** (repo still private, flips public at S3 launch) and **XII** (the site does
not yet list the brand accounts, small Opus item). One Article-VI observation: the committed
analysis artifacts (`citations*.json`, `era_fingerprints.json`) were produced by scratchpad scripts
, promote their generators into `scripts/` so every committed number is reproducible from committed
code.

**Fable-owned amendments made:** `01-VISION.md` S4 leaderboard amended (naive %-match retired ,
saturates ~99.7%; ships as Authors-vs-Vessels raw origination/echo counts with receipts, never a
composite score, per `09-DESIGN-REVIEW` #8 + `10-FINDINGS`); `08-ANALYSIS-MENU.md` gained the
**trend-language publication gate** (the Session-3 verified lesson, now rule); ladder + "You
are here" updated. The gameplan §10 v2 item "on-script leaderboard" is to be read through the S4
amendment (deviation recorded here per doc-map convention, the gameplan file stays frozen).

### Session 5 (2026-07-14), Wave-0 hardening + adversarial review: five real defects fixed, and the "live voice" corrected

> **Model-identity flag (STRICT model-split, §0):** this session actually ran on **Fable 5**, not
> Opus, even though the standing prompt and the workflow assign Phase-4 implementation to Opus. The
> work is verified (55 tests, adversarial review) and I did not touch §13 locked decisions, but the
> canon attributes Phase 4 to Opus, Michael, if you intended Opus, switch models; flagged so the
> record is accurate.

Executed the Wave-0 launch-blocking set from `docs/11-BUILD-PROGRAM.md` §1 (the Session-4 item-2
list), then ran a 4-dimension adversarial review over the whole diff **before committing**. The
review earned its keep: **five real defects, three HIGH.** All fixed, each with a regression test.
**55 tests green** (was 50), including the `POSTING_ENABLED` failure tests and both LLM failure tests.

**Wave-0 items delivered (a–g + registry + gate + bot-label):** posting day now comes from the
assemble manifest (`assemble-latest.json`), not `collect-latest` (a); the `POSTING_ENABLED` repo
variable is the hard launch gate. A failure test confirms that **no path posts when it is off, regardless of
creds** (b); the `FEATURES` registry (all dark) gates backlog UI; receipts render as real
member·date·`.gov` rows under each Daily Line (e); the About page carries the operator disclosure +
lists `blue.`/`red.onscript.news` (Art. X/XII); the bot self-label fires idempotently at first
authenticated session without clobbering the profile Michael set; the `scripts/analysis/*`
generators are promoted to import-safe, tested pipeline code (Art. VI, `tests/test_analysis.py`).

**The adversarial review's five findings, all confirmed against source, all fixed:**

1. **HIGH, self-grounding defeated the verbatim-quote guarantee (`distill.py`).** Wave-0 had added
   the code-computed cluster labels + top synchronized phrase to the verifier's `groundable` set, so
   quotes were grounded against *themselves*, a vacuous check. A punctuation-stripped label
   (`support affordable accessible housing`) could be quoted though no member wrote those words
   contiguously (they wrote `affordable, accessible`). **Fix:** `groundable` = verbatim fragment
   texts ONLY; `build_stats` quotes the shortest clean **verbatim fragment** (never the label);
   code-computed phrases (labels, top phrase) are rendered **without quotation marks** as measured
   facts. `verify.quotes_grounded` keeps internal punctuation, so it is now genuinely enforced.

2. **HIGH, the "live Sonnet voice" was never wired; deterministic stub published as `claude-sonnet-5`.**
   `distill.daily_line`'s real-mode branch produced `_compose_dry` (deterministic) but labeled it
   `generator="sonnet_batch"`, `model="claude-sonnet-5"`. Grep-confirmed: `llm.submit_batch` /
   `poll_batch` / `direct_call` have **zero call sites outside `llm.py`**, `run_assemble` never
   calls them. **The same is true of the Haiku extract layer** (`extract.py` real branch also falls
   back to `_dry_fragments`, labeled `haiku_batch`). So the **entire LLM layer is built but unwired**:
   the pipeline is currently **fully deterministic**, and the reported voice/extract costs are
   `estimate_cost` **projections, not charges.** My own Wave-0 site change had made this *worse* by
   adding `sonnet_batch` to `PRODUCTION_GENERATORS` and suppressing the disclosure banner. **Fix:**
   real-mode voice/extract now label their output **`deterministic`** (accurate); `PRODUCTION_GENERATORS`
   = `{llm, production, sonnet_direct}` only; the accuratey banner discloses any stub voice as **"not a
   language model … deterministic template."** *This corrects the Session-2/Session-4 canon: there
   has been no live LLM voice.* **Governance note:** Session-4 follow-up 2(d) instructed removing the
   placeholder banner **"because the voice is live"**, that premise was false, so per the Phase-4
   mandate (verify against reality; "should work" ≠ done) it is **reversed on the facts**, not
   followed. Wiring the actual calls is Opus code work but turns on real API billing → **Michael's
   greenlight** (tasked, #71). The deterministic *engine* (ledger, coordination detection, adoption
   curves, discipline index, symmetry) is real and running, only the LLM narration is a placeholder.

3. **HIGH, the posting dead-man could never fire for the most likely failure (`post_bluesky.py`).**
   When `_post_real` threw (Bluesky 5xx / expired app-password 401 / timeout), `main`'s except
   appended a result with **no `creds_present`**, so the missing-post detector dropped it → no ntfy.
   **Fix:** the except handler computes `creds_present` from env; a creds-present post that throws now
   fires the dead-man. Covered by a failure test.

4. **MEDIUM, stored-XSS via unvalidated URL scheme in the new citation links (`site.py`).** Receipts
   rendered `<a href="{esc(url)}">` from ingested (poisonable) corpus urls; `esc()` neutralizes
   attribute-breakout but leaves the scheme, so a `javascript:`/`data:` url became clickable JS on a
   site that advertises zero JS. **Fix:** `_safe_http_url` whitelists http(s) at the render sink (the
   sole href sink for citation urls); bad-scheme urls render as a non-link span. Raw url stays
   faithful in the data (fidelity); sanitize on output, not input. Tested with four hostile schemes.

5. **MEDIUM, no idempotency → a re-run re-posts the whole thread (`post_bluesky.py`).** A manual
   re-dispatch / "Re-run all jobs" after a successful post would publish a duplicate composite.
   **Fix:** `main` reads the prior `post-<day>.json` and skips any party already `posted==True` for
   that day (records an `idempotent_skip`). Dormant until `POSTING_ENABLED` flips, but a real
   duplicate-post risk against the deliberate single-launch-post intent. Tested.

**Environment findings (local only, the cloud is unaffected; NOT code bugs):** the local Alexandria
ledger `X:\onscript-data\…\ledger.json` (3.08 GB) is **corrupt** (JSON parse error ~902 MB in), it
crashes local `run_assemble` *before* my code runs and **blocks the Archive/1.1 build** until rebuilt
(a future Opus session can rebuild it from the raw corpus; the daily cloud run uses the smaller
RUN-A ledger from the `data-latest` Release asset and is fine). Local day-JSON statement ids are also
stale vs. `statements.jsonl.gz` after a corpus re-normalization. Both are why the code was verified by
representative unit tests rather than a local end-to-end assemble.

**Committed:** code (`config`, `distill`, `extract`, `post_bluesky`, `run_assemble`, `site`) + the
promoted `scripts/analysis/*` + `tests/test_wave0.py` + `tests/test_analysis.py` + the
`assemble.yml` `POSTING_ENABLED` env. **Never touched:** posting stayed off; no release flag flipped;
the Anthropic key was never set locally (dry-run $0 throughout).

**Session 5b (same day), live-site correctness audit + accuratey render deployed.** A four-lens audit
of the LIVE onscript.news found its shape right (coordination signal first; neutrality/symmetry
disclosures accurate) but three live defects, all the pre-Session-5 render: the per-line flag stamped
`model: claude-sonnet-5 · generator: sonnet_batch` beside a banner admitting the text is
"deterministic" (a self-contradicting false-provenance claim); no member·date·.gov receipt rows; and
a bare About page. Root cause the Session-5 code already fixed, but the commit was **unpushed**, so
none of it was live; the site is served statically from the committed `site/public/` (no vercel.json).
One residual the fix missed: `site.py` printed the STORED `model`/`generator` verbatim, so historical
day pages would keep the false `claude-sonnet-5` even after redeploy. **Fixed** with a render-time
`_voice_flags` (any non-production generator renders uniformly as "voice: deterministic template (not
a language model)" and the stale model id is suppressed, corrects EVERY page without re-assembly; new
test; 56 green). Then **regenerated `site/public` locally with `site.py` only** ($0, no API, no
ledger, it renders committed derived JSONs) and **pushed** (commits 09acd99 + 041ffd7, clean
fast-forward). Verified on the live page: `claude-sonnet-5` is eradicated site-wide, About discloses
the operator + both accounts, the accuratey banner is sharp, and the signal/symmetry are intact.
Freshness confirmed correct: `util.product_day` = yesterday, so showing 07-13 on 07-14 is by design
(07-14 is an empty stub). Deviation from the build-session convention "cloud owns site/public": the
owner explicitly asked to make the public site correct now, and with no `gh` to dispatch a run, a
local `site.py` render + push was the only immediate path, the next cloud assemble cleanly supersedes
it (same data, adds receipts). **Follow-ups the redeploy does NOT fix (grind queue, all Opus-doable):**
(i) member·date·.gov receipt ROWS + the cleaner distill quote wording need a fresh cloud assemble
(they live in the stored day JSON, not the render), the 11:30 UTC cron or a manual dispatch applies
them; (ii) the Tracked-Phrases index is empty on thin days because `build.py` keys `phrases/top.json`
to the current (often stub) focus day, not a rolling window / last-substantive day; (iii) the nightly
symmetry audit appears to present cumulative corpus totals as if daily (verify + fix); (iv) prompt git
history is not rendered on Methodology (Art. VIII); (v) guard the on-script/discipline value against
meaningless low-N days; phrases index caps at 40 vs the spec's 50.

**Ledger re-diagnosis (Session 5b), the "corrupt" Alexandria ledger is very likely NOT corrupt.**
Direct byte inspection: the file tail is a clean `…"boilerplate": false}}` and the bytes at the
exact reported failure offset (~902 MB) are valid JSON (`… "2018-02-09": {"R": 1, …}`). So the
earlier `JSONDecodeError` was almost certainly a **memory/scale** failure, `json.load` on a single
3.08 GB object exceeds this box's RAM, NOT on-disk corruption. Corroborating: the **per-Congress
shards in `state/alexandria/` are all intact** (`ledger-113…119.json`, discipline/coverage), and the
daily cloud pipeline is unaffected (it uses the smaller RUN-A ledger, never this one). Implication:
the Archive/1.1 build does **not** need a from-scratch rebuild, it needs a **streaming/sharded
reader** (e.g. `ijson`, or read the per-Congress shards directly) instead of `json.load` on the
merged file. `alexandria.merge()` can still re-emit `ledger.json` from the intact shards ($0, pure
function) if a single merged file is wanted, but the memory ceiling to *read* it back is the actual
constraint. Symmetry follow-up (iii above) is now **fixed** (day-scoped audit, deploys next cloud
assemble). This corrects the "corrupt local ledger" framing used earlier in this BUILDLOG and in
CLAUDE.md "You are here".

### Session 6 (2026-07-14), the actual Sonnet voice, wired dark behind a kill-switch + strict budget

Michael greenlit wiring the live LLM voice (#71). Executed the Phase-3 plan, the composite voice was
always meant to be Sonnet; the deterministic template was the $0 placeholder. Built **dark**:
`LLM_VOICE_ENABLED` repo variable defaults off, so the commit bills nothing; the voice only calls the
API when Michael flips the switch, and flipping it off reverts to $0 instantly (the POSTING_ENABLED
pattern). **Scope: voice only** (2 Sonnet direct calls/day, ~$0.01/day ≈ $0.30/mo); extraction stays
deterministic ($0). Every composite still passes the blocking verifier or drops to the deterministic
fallback, an ungrounded LLM claim can never publish.

**Strict budget:** a month-to-date spend ledger (`data/derived/cost/YYYY-MM.json`) accumulates REAL
token usage; `voice_budget_state` HALTS the voice at a **$9 code ceiling** (below the $10 Console
cap); ntfy warns at $8; cost is recorded BEFORE the day-JSON write and is date-aware for Sonnet-5's
2026-09-01 price step. Monitoring surfaces: Console (authoritative), the cost ledger (committed), the
assemble manifest (`month_to_date_usd`/`voice_used`/`voice_budget_state`), ntfy, methodology tokens.

**Adversarial review found + fixed 7 defects before commit** (2 HIGH, 3 MED, 2 LOW): the
fabricated-number whitelist hole (a digit inside a member quote could publish as a fake aggregate ,
now only code-computed counts/dates are allowed unquoted, quote-numbers exempt via grounding); a
blank Sonnet response publishing as a verified line (now guarded); quote grounding accepting
negation-dropping truncations + cross-fragment stitching (now min-length + negation-guard); the cost
ledger overwriting instead of accumulating and excluding today from the halt check (now accumulates,
halt includes today); undated Sonnet-5 pricing (now date-aware); verifier-fail keeping the
sonnet_direct label; null API usage recording $0. Also shipped the **accurate no-coordination line**
("No phrase was shared by N or more of us today") so an empty party column reads as a measured finding
(the silence story), not a gap, answers the "why is the R column empty" question. **69 tests green;
dry-run $0 throughout; nothing billed; the gate is off.** These distill/verify changes deploy on the
next cloud assemble (they regenerate the composite); the no-coordination line + hardened verifier
apply to new days going forward.

**Michael to turn it on (dark-week validation):** set repo variable `LLM_VOICE_ENABLED=true`, run
assemble (or wait for cron), watch 2-3 runs for cost (~$0.01/day) + verifier pass + prose quality,
then it's validated for launch alongside the streak. Off = `false`/delete → instant $0.

**Session 6b (same day), the voice went LIVE + a Vercel-deploy bug fixed.** Michael greenlit turning
it on; I set `LLM_VOICE_ENABLED=true` via `gh` (auth confirmed; repo variables were empty, so
POSTING_ENABLED stays absent = posting off) and dispatched assemble (run 29358642659, green in 52s).
**First real Sonnet run, fully validated on 2026-07-13:** both parties `generator=sonnet_direct`,
verifier passed, no fallback; **cost $0.005572 for the day** (month-to-date the same; ~$0.17/mo
projected, a fraction of the $9 ceiling); budget/governor nominal; the cost ledger persisted
(`data/derived/cost/2026-07.json`); **posting stayed off** (post manifest: both parties
`posted=False, reason="posting disabled"`). The prose is on-voice (deadpan-clinical, first-person
plural) and the R no-coordination case is narrated gracefully by the model ("We report no dominant
message today… 51 statements… synchronization minimum 3…"). Receipts render live with real member·
date·.gov links. **Flagship-claim audit:** the D line's "first said by Tim Scott" was verified from
the raw corpus, S001184 IS Tim Scott (R-SC), who coined "21st century road to housing act" on
2026-03-03 as its Republican champion; Democrats adopted it at passage. A **real cross-party
origination**, not a lookup bug, the tool's core signal working, correctly reported and accurately
hedged by the voice.

**CI/deploy bug fixed:** the collect/assemble commit messages carried `[skip ci]`, and Vercel skips
deploying such commits, but the workflows are schedule/dispatch-only (never push-triggered), so the
marker did nothing for Actions while silently **freezing the live site** (every automated daily commit
was committed but never deployed; the site only moved on manual pushes). Removed `[skip ci]` from both
workflows (commit e87763d, no marker, which itself deployed the live voice). The site now genuinely
auto-deploys on every data commit, the missing piece of the "updates itself unattended" guarantee.
**Verified end-to-end:** a second dispatched assemble (run 29359973881) committed as `data: assemble
2026-07-14` **without** `[skip ci]` and auto-deployed (the live Methodology now shows the day-scoped
symmetry, "Statements ingested (this day): 74/51", not the old cumulative 44,767, proving the cloud
commit reached Vercel). The **cost ledger accumulated correctly** across the two runs (`total_usd
0.011274`, `calls: 2`, tokens 2262 = 2×1131), the MEDIUM-4 accumulation fix confirmed live. Also
shipped: the **month-to-date model-voice spend is now published on the Methodology page** (from the
cost ledger), radical-transparency + a public budget monitor. **69 tests green.**

**Grind queue (Opus, next sessions, none blocking):** (1) Archive/1.1 needs a **streaming/sharded
ledger reader** (the 3 GB Alexandria ledger is valid-but-too-big, not corrupt; shards intact). (2)
Phrases index is empty on thin focus days (`build.py` keys `top.json` to the current stub day, not a
rolling window). (3) Low-N guard on the on-script/discipline value. (4) Phrases index caps at 40 vs
the spec's 50. (5) Optional: wire Haiku extraction (voice-only was the deliberate scope; extraction
stays deterministic + $0). (6) The prompt git *history* on Methodology (the live prompts already
render; history is a nice-to-have). Prompt-transparency (Art. VIII) is otherwise satisfied.

### Session 7 (2026-07-14, Fable), the bones review: editorial ruling + pre-launch punch list

Four-lens review (cold-read / editorial-voice / hostile-skeptic / fact-checker) of the live site with
the Sonnet voice on, plus a direct Fable read. **Ruling: the bones are strong.** The accuracy lens
found **zero numeric errors** (every figure on the homepage/day page reconciles with the day JSON;
all six receipts resolve to real members with correct party/state and own-domain .gov URLs; live
matches committed). The neutrality architecture survives a hostile read (R's null day reads as a
measured result; the 24%/14% coverage gap is disclosed with denominators; identical prompt SHAs).
And the attention thesis validated: the cold reader "got it" in ten seconds and named the R line
("We remain 51 statements wide and zero phrases deep") as the thing they'd screenshot. The failures
are all in the last inch, labeling, wording, and ONE machine-level defect, and they cluster precisely
where skeptics will look. **Pre-launch punch list (Opus, in order):**

**A. Wording/copy (cheap, high-value, next Opus session, deploys next assemble):**
1. Drop "directly" from the every-page tagline → "It is what each party said today, compressed to
   one voice, with receipts." ("directly" over an LLM composite is the pedantic rebuttal we can least
   afford, skeptic HIGH.)
2. Scope the citation promise to what's true as rendered: index/footer "Every claim above is
   citation-backed" → "Every distilled **talking point** above is citation-backed" (match About).
   On zero-cluster days add a card note: "No talking point cleared the 3-member bar today, nothing
   to cite." (The receipt-free R card directly under the universal claim is screenshot ammunition ,
   skeptic HIGH.)
3. In-card composite cue so a cropped screenshot carries its own disclaimer: a small caption under
   each Daily Line, "A composite voice, machine-written from the day's measured phrases. No member
   spoke these sentences; quoted spans are verbatim (see receipts)."
4. About present-tense fix: accounts "post one thread per day" → "will post one citation-backed
   thread per day (posting begins at public launch)", they have never posted; tense = accuracy on
   the disclosure page.
5. Cadence banner under the H1 (the .banner class already exists, unused): "Press releases for a day
   are complete the next morning, today's reading covers {day}."
6. Causal overclaim in About/Phrases marketing copy ("the public output of private coordination"/"a
   private memo") → measured co-usage language ("when dozens of members converge on identical
   phrasing in a day, the convergence is the story; we measure it, we don't assert its cause").
   The system pages already have this right; the marketing copy must match (Constitution:
   correlation-not-cause).

**B. Prompt bump P2/P3 → v1.1 (public, versioned):** (a) never name the input mechanics, "cluster(s),
talking point(s), STATS, null, sync minimum, provided" must not appear; the "we" is the party, not a
system describing its data (the live R line says "the top phrase is null", the JSON leaking into the
party's mouth; editorial HIGH). Zero-cluster days in plain speech: "Across 51 statements, no phrase
was shared by three or more of us." (b) one number style both parties (spell one–nine, numerals 10+).
(c) first-sayer named with party-state ("Tim Scott (R-SC)"), requires first_sayer_party in STATS.
Keep corpus-wide first-sayer (cross-party origination IS the product); just annotate it.

**C. Engine (the one machine-level defect, root of three findings):** cluster label quality. The
"and the trump administration's" cluster, a connective-glue n-gram, published, got receipts pointing
at Cuba trips and a USDA lawsuit, and the voice upgraded it to an "immigration… consistent
formulation." The one reader who clicks to verify the most charged quote on the page lands on
receipts that don't support it, receipts sowing doubt is the product's exact failure mode (3 lenses
flagged independently). Fix: (i) publish-time gate, a cluster whose label fails the low-content/
connective test is not published or narrated (the boilerplate machinery exists; apply it to labels);
(ii) bind each displayed fragment quote to its own member/source (data already links fragments →
statements); (iii) same root as the generic phrase-table tail Michael spotted, fold df_weight/
low-content into the daily table ranking.

**D. Wiring polish:** phrases hub must never render empty (fall back to all-time/last-substantive-day
top list, 292 phrase pages already exist); marquee phrases clickable with sparklines (wire detail
pages for highest-count rows first); prev/next links only to pages that exist (07-13 currently links
a 404 "next day"); lowercase verbatim quotes (usda, trump) get display-case restoration while keeping
the lowercase form for matching; sparkline color should follow the phrase's leading party.

**Noise, filtered (do not spend time):** sparkline window semantics (invisible without decoding the
SVG), CSS nitpicks, CDN cache lag, missing dark features (deliberate), re-runs rewriting the day's
line (recorded fact, manifest tracks it; single daily cron in practice).

**Session 7 execution (Opus, 2026-07-14), punch list DONE, deployed, verified.** All of A–D shipped
+ an adversarial review that found and fixed 6 defects before commit (commit 54aa81a; 75 tests green;
dry-run $0). Review catches worth recording: (#1) my first cluster-gate rule rejected ANY
conjunction-led label and would have erased real coordinated phrases ("and civil rights", "and
transparent investigation into the killing"), corrected to conjunction-led **AND** possessive-
trailing, which catches the "and the trump administration's" glue precisely while keeping real
phrases; (#7) the reworked receipts sourced quotes only from citations, which would have rendered
EMPTY receipts on historical days (the 53-member "born in the united states" flagship) that predate
citations, fixed with a fragment-quote fallback; (#8) the methodology "live prompt text" was
hardcoded to v1.0 while the published sha moved to v1.1 (an auditor hashing the shown text would get
a mismatch, falsifying the neutrality protection), now driven from `llm._PROMPT_FILES`; (#4) the
party-tagged first-sayer would fabricate on a roster-miss, now emitted only when name+party+state
fully resolve; plus the quote ≥3-word floor and the "sync" vs "synchronized" prompt fixes. The
numerals-only rule (my pre-emptive fix) closed a real hole: a spelled-out number would bypass the
digit whitelist. **Verified live on 2026-07-13 after a dispatch:** the D voice reads clean ,
"…first recorded from Tim Scott (R-SC)…", no schema words, one talking point (the glue cluster
suppressed); R says "Across 51 statements, no phrase was shared by more than a few of us today."; the
housing receipt shows three members' own quotes bound to their .gov links with a "showing 3 of 10
members" cue; the methodology prompt text matches the v1.1 sha. Cost nominal ($0.0163 MTD). The bones
are launch-strong.

### Session 8 (2026-07-15, Fable), external critique adjudicated against the code; unattended run #1 green

**Unattended gate progress:** the first fully-unattended cron cycle ran green (collect 11:06Z,
assemble 12:51Z, both `schedule`-triggered, auto-deployed, no `[skip ci]`). Fresh product-day
2026-07-14: both parties `sonnet_direct`, verifier clean, D 8 / R 3 talking points (the asymmetry cut
R-ward today, both-ways evidence), cost $0.0078 (MTD $0.024). **1 of ~3 unattended greens done.**

**An external ("stranger Fable") critique was adjudicated claim-by-claim against the code.** Verdict:
high-quality, ~70% valid, ~20% already-resolved-in-our-favor conditionals, ~10% wrong or
constitutionally confused. Rulings that matter, with ground truth:

**CONFIRMED, the big one (construct validity).** The top of the daily table is dominated by
**nomenclature, not messaging**: 07-13's top phrase was a bill title; 07-14's unattended run topped
with "water resources development act" (+ a committee name in the D composite). Convergence on a
statute's only name conflates coordination, nomenclature, and calendar. Mitigants already live (we
never assert cause; content ranking; weak-label gate) but the segregation is missing. **Queue (before
any "coordination" headline claim): bill-title/institution tagging**, official short titles via the
congress.gov API (`DATA_GOV_API_KEY` is set) + a committee/institution name list → "nomenclature"
chips in the table, optionally a split view; longer-term a null baseline (how often do independent
members writing about the same bill produce the same n-gram?) per the Appendix backtest rule.

**CONFIRMED, with a constitutional correction (base rates).** D out-publishes R (07-14: 135 vs 87
statements), so the absolute ≥3 bar is mechanically easier for D to clear. BUT the critique's remedy
("rate-normalized thresholds") would mean **different absolute bars per party, an Article-III
violation** (identical thresholds is the protection). The correct fix: **denominators in view**, render
"14 of 263 (5.3%)" beside every member count (caucus_size is already computed), and rate-normalize
any cross-party comparative CLAIM (the trend-language gate already requires this for eras). The
operational quorum stays absolute and symmetric: it is a citation floor, not a comparative statistic.

**CONFIRMED, real gaps, now queued (sequenced):**
- *Before posting flips on:* **post atomicity** (today a per-party try/except means one bot can post
  while the other errors, asymmetric failure reads as bias; build both threads, post both or
  neither, degraded-notice path + dead-man already exists); **signed post archive** (mirror every
  posted thread on the domain from the post manifests, doubles as forgery/compromise detection);
  **golden-set tone regression** (frozen STATS inputs re-rendered on any prompt/model change, diffed
  for register before deploy); **"said" → "carried"** (receipts header + composite verb: a release
  can quote third parties, presenters, bill text, so "N members said X" overclaims; "N members'
  statements carried X" is exact; the P1 no-quote-boundary gap is real, extraction takes any
  sentence, so also run the **100-fragment speaker-contamination sample** (Opus builds the sample
  sheet, Michael classifies during #77; >~2% → build deterministic quote-boundary detection));
  **copy fix:** About/methodology claim a "public source repository" while the repo is private until
  S3, soften now or link at flip.
- *Inscriptions (cheap now, expensive later):* the **verbatim-identity position** on Methodology
  ("OnScript measures verbatim coordination; a decline in verbatim sync under observation is itself
  a finding; any semantic instrument would ship separately with a weaker guarantee"), pre-writes
  the future "they just paraphrase now" gotcha as a predicted result; the **model-free measurement
  claim** ("no number on this site is produced by a model: the phrase ledger is deterministic code;
  the LLM renders prose it cannot add facts to"), verified true in code, currently under-claimed;
  **methodology-versioning rule** (any threshold change re-runs the full corpus; both series
  published side by side, determinism makes this cheap).
- *Standing:* per-member ingest-health flags ("silent >N days", volume-spike anomaly) published in
  the nightly audit, silent CMS-migration decay is invisible today and plausibly party-correlated;
  congress-press license audit + own-scraper-primary (mirror rule already stands); lookalike
  handles; Bluesky PLC rotation-key backup.

**RESOLVED IN OUR FAVOR (the critique hedged; the code answers):** the phrase ledger is **model-free**
(pure deterministic n-grams; extraction feeds only the composite layer, and extraction itself is
deterministic today); the verbatim/injection check lives in **code** (verify.is_verbatim), not the
prompt; posting runs on **GitHub Actions**, not the media server (no residential infra); the roster
is a **committed snapshot** (poisoning requires a repo commit); the tokenizer handles curly
apostrophes and the corpus is entity-clean (0/3000 sampled releases carry literal HTML entities) ,
the "normalization asymmetry" fear is largely closed by inspection; response posture ≈ playbooks
P3–P6 already. **Recommendation flowing from this:** retire the plan to wire Haiku extraction, a
permanently model-free measurement path is worth more than LLM fragments (a §13 knob change; needs
Michael's nod; extraction stays deterministic, voice stays the only LLM surface).

**WRONG or noise:** rate-normalized *thresholds* (Article III, above); the $1–4k backfill-extraction
cost (moot, nothing LLM-extracts the corpus); "0 corrections = unexamined" (that examination IS the
dark week, #77); member-level near-dup findings (already governed: Appendix aggregate-only rule ,
publish distributions, never names).

**Michael-only decisions filed to the bus:** the funding-pledge wording (the current absolute "takes
no outside funding" is un-amendable-later; decide "never" vs "no political money ever; disclosed
philanthropic infrastructure grants permitted" NOW, while nobody watches) and the operator-protection
bundle (WHOIS privacy, LLC decision, employer outside-activities policy, personal-account engagement
policy, PLC key custody) + attorney-hour agenda additions (state synthetic-political-content
statutes before midterm peak; vendor AUPs, Anthropic usage policy, Bluesky ToS, Vercel).

**Added to 07-OPERATIONS: P11, the sunset playbook** (accounts announce a clinical close, crons
disabled in one commit, site banner flips to "archive," data released, accounts stay up silent ,
never deleted), the critique's "a zombie political bot in 2029 is the worst available ending" is
correct, and improvised endings are how you get one.

**My own analogous misses (same blind spot, everything around the system):** GitHub account =
single point of failure (2FA/recovery/break-glass doc); a visible "generated at" timestamp + /status
so a stale site never reads as editorial silence; GDELT (v2 silence detector) needs the same
upstream-anomaly treatment as press releases the day it lands; DST shifts the cron's local-time
meaning in November (benign; noted).

### Session 8b (2026-07-15, Opus), pre-posting set built, reviewed, deployed

Executed the Session-8 pre-posting queue + Michael's two decisions, 5 commits (…f00e27a), 82 tests.
**Decisions applied:** funding pledge pivoted to "no political money, ever; grants disclosed" (#104
done); **no LLC** (Michael), operator protection is now the non-LLC bundle in #105 (WHOIS, employer
policy, personal-account policy, PLC keys, lookalike handles) + the site disclosure is already
personal-contact-free (routes through the repo/corrections, no email/address). **Built:** the three
methodology inscriptions (verbatim-identity, model-free, versioning); denominators-in-view ("N of
{caucus} (X%)"); "said"→"carried"; post **atomicity** (both-or-neither pre-flight, `asymmetric`/
`atomic_hold` flags, dead-man on both); the **signed post archive** at /posts.html (on-domain mirror
of posted threads, at://→bsky.app, forgery defense; nav-gated on HAS_POSTS); the **golden-set tone
regression** (frozen deterministic snapshots + `register_violations`; `scripts/golden_render.py
--freeze`); the **speaker-contamination sample** (`scripts/audit/speaker_sample.py` for #77).

**Adversarial review found + fixed 4 defects before push** (the review earned it again): (HIGH) the
versioning inscription was **present-tense for an unbuilt capability**, no old/new series retention
exists (the ledger overwrites in place), a false claim on the neutrality page; reworded to a
commitment. (MED) the deterministic composer **mislabeled a member count as a statement count** ("N
of our statements carried") contradicting the receipts on the same page; fixed to "N of us carried" +
golden re-frozen. (HIGH) **build_thread could crash the run** on a null composite / a top-phrase row
missing keys (post_party builds the thread before the gates), one account would post, the other skip
the manifest+dead-man; hardened all accesses (launch-critical, dormant behind POSTING_ENABLED=off).
(HIGH) the **committed site/public was stale**, regenerated + committed so the served copy matches
source (the live About had still read "takes no outside funding").

**Two posting-launch blockers deferred to a pre-flip Opus session (dormant now; fix BEFORE
`POSTING_ENABLED` flips):** (2) on a mid-thread `_post_real` failure the result has `posted=False` +
no `root_uri`, so a re-run **re-posts the already-live posts** (duplicates), capture partial
progress / persist the root uri once the root succeeds. (3) `can_post` pre-flight checks only env-var
presence, not auth, so a **wrong/expired app-password** on one account lets the other post fully
before it 401s, upgrade the atomic pre-flight to establish a `createSession` per to-post party and
`atomic_hold` if any fails. Both are AT-Proto-network paths (untestable locally; verify on a live
launch dry-run).

### Session 8c (2026-07-15, Opus), the two posting-launch blockers CLOSED + a third (silent-neutrality) fixed

Directive: "make sure when we're ready for go-live our bots don't fall on their face." Rewrote the
posting path (`pipeline/post_bluesky.py`) to close both Session-8b blockers, then ran a focused
adversarial review that found and closed a third. Commit `3d6bd60`, **88 tests**. Posting stays OFF
(POSTING_ENABLED default off), it is dormant hardening. A failure test confirms that no path posts when off.

**Blocker (3), atomic pre-flight auth, CLOSED.** `main()` now does an ATOMIC PRE-FLIGHT:
`_authenticate` (createSession) for **every** due party *before* any post; if any raises (wrong/
expired app-password), `atomic_hold` + dead-man and **neither** party posts. A bad credential can no
longer let the paired account post alone. Test: `test_atomic_hold_when_one_account_auth_fails`.

**Blocker (2), partial-post duplication, CLOSED, two layers.** (a) `_on_root(uri)` persists the
root URI to the manifest **before** any reply, and `already_posted` requires `posted AND root_uri`,
so a re-run after a mid-thread crash skips the head (no duplicate root). (b) The root now uses a
**deterministic rkey** `onscript-<day>-<party>`: a retried root **collides server-side** (createRecord
is create-not-put) and is RECOVERED via `getRecord`, returns `posts_written=0, recovered=True`,
never a duplicate head, never re-posted replies. Tests: `test_partial_post_records_root_and_a_rerun_
does_not_duplicate`, `test_post_thread_recovers_root_on_rkey_collision_without_duplicating`,
`test_root_rkey_is_deterministic_per_day_and_party`.

**New finding (adversarial review), silent-neutrality on an empty composite, FIXED.** If one
party's composite was missing/empty, BOTH still posted (a near-empty root) with `asymmetric=False` ,
it slipped past the asymmetric guard because both were technically "posted." Now a due party with no
composite → `atomic_hold` + dead-man (hold both). Also `_split` now provably never emits an empty or
over-length post (lone oversize token hard-sliced). Tests: `test_empty_composite_for_one_party_holds_
both_atomically`, `test_split_never_emits_empty_or_overlength_posts`.

**Also landed (deferred from 8b's review):** the near-dup phrase collapse now folds **only** stopword-
padding variants (`_padding_variant`) so a generic hub ("the trump administration", peak 20) can no
longer absorb the distinct coordinated messages that contain it (the over-merge the 8b review flagged);
least-padded form is the representative carrying the family max peak. Guard test:
`test_collapse_does_not_let_a_generic_hub_absorb_distinct_messages`. Receipts Wayback fallback +
denominators + methodology inscriptions regenerated into `site/public` and deployed.

**Two residual pre-flip items (NOT blockers; posting is off) from this review:**
- **(A) Live AT-Proto smoke test before flip**, the rkey-collision-recovery + getRecord + oversize/
  empty behavior are `# pragma: no cover` (never run against a real server). The create-not-put
  assumption is correct per spec but has never executed live. **Filed as a Michael pre-flip task**
  (throwaway accounts: create-with-rkey → retry-collision → recovery). Fold into the S3 launch dry-run.
- **(B) Asymmetric-post reconciliation**, the dead-man fires only at end of `main()`; a hard process
  kill (Actions timeout/OOM/SIGKILL) in the sub-second gap between the two parties' posts leaves a
  durably asymmetric manifest with no alert. **Opus build item** (a startup reconciliation that scans
  recent post manifests and alerts on unacknowledged asymmetric/partial), queued below, before flip.

### Session 8d (2026-07-15, Opus), #108 smoke test ran live and caught a launch-blocking 400

Michael created a throwaway Bluesky account and handed over its app-password, so item (A) above ran
**for real** this session (not deferred). `scratchpad/smoke_post.py` drives the **actual** `post_bluesky`
primitives against the throwaway. It immediately found a **launch-blocking bug**: `app.bsky.feed.post`
**rejects an arbitrary rkey**, `createRecord` returns `400 InvalidRequest: "Invalid record key for
app.bsky.feed.post: Invalid TID string (got \"onscript-…\")"`. The Session-8c deterministic rkey
`onscript-<day>-<party>` is **not a valid TID**, so real posting would have **400'd on the very first
post at launch**, and the over-broad recovery `except` would have masked it as a phantom "collision
recovery," then crashed on the follow-up getRecord (precisely the traceback the smoke test produced).

**Fixed (commit 9e387f7, pushed):** (1) `_root_rkey` now builds a **valid deterministic TID** ,
timestamp = midnight UTC of the day, clock-id = party index; a valid 13-char base32-sortable string,
unique per (day, party), roughly chronological. Verified live that **both past-dated (2001-01-20 →
`2vvcci3yk2222`) and present-dated TIDs create cleanly.** (2) Recovery is now **probe-existence based,
not error-code matching**, a rkey collision surfaces as **400 OR 500** depending on the PDS (500
observed live), so on any create error we `getRecord` by rkey and recover only if the record exists,
else **re-raise the original error** so the caller records `posted=False` + the dead-man fires. This
also closes the swallow-a-real-failure bug. **13/13 live checks pass** (valid TID · threaded root+reply
posted + verified · collision→recovery with no duplicate head · 401 raises on a wrong password · split
invariants + oversize thread posts, all ≤300) **+ 89 unit tests.** Item (A) / task #108 is **done**;
item (B) reconciliation still queued. (~10 test posts left on the throwaway, harmless.)

### Session 8e (2026-07-15, Opus), finding (B) built: the hard-kill reconciliation backstop

Closed the last Opus pre-flip item. `_reconcile_prior()` (in `post_bluesky.py`) runs at the **start**
of every posting run: it scans the post manifests and fires the dead-man **once** per unacknowledged
`asymmetric`/`partial` prior day (marking it `reconciled`), so a run **hard-killed** (Actions timeout/
OOM/SIGKILL, not a Python exception) *between* the two parties' posts can no longer leave a durable
silent one-sided post that alerts nobody. **Alert-only**, it never auto-posts or repairs (that stays
with the deterministic-rkey idempotency path); a human check+repair is the correct remediation. Gated
on `POSTING_ENABLED` (no-op in dark mode; dark manifests are `asymmetric=False`, so the first live run
never false-alarms, confirmed against a real on-disk dark manifest). **Adversarial review confirmed 6
invariants + found 3 fixes, all applied:** (1) scan **ALL** manifests, not a `[-14:]` window, the
operator-disables-posting-for-weeks reflex would otherwise age the bad day out unseen (the exact failure
this exists to catch); the `reconciled` marker keeps a full scan cheap + idempotent. (2) day derived
from the **filename** (authoritative), not a possibly-missing `"day"` field. (3) each manifest read is
**guarded**, a corrupt manifest is skip-and-logged, never crashes the run, never blocks reconciling
other days (honors the module's never-crash contract). Commit `be86eba`, **94 tests** (+5). Posting
stays OFF. **The Opus pre-flip queue is now empty**, nothing on the build side blocks the launch flip.

### Session 8f (2026-07-15, Opus), near-dup phrase collapse finished: safe sub-gram containment + historical rebuild

Michael flagged the top-synchronized table still showed near-duplicate rows. Diagnosed two residuals
beyond the Session-8b stopword-padding collapse: (1) overlapping **sub-grams of the same coordinated
message** ("statement after the supreme" next to "statement after the supreme court"; "children born
in" next to "children born in the united states"), and (2) the flagship page was **stale** (rendered
before any collapse). Built `_collapse_subgrams` (in `build.py`): folds a fragment into the fuller
phrase that CONTAINS it when peaks are comparable, keeping the longer, more-specific label at its OWN
accurate peak, **guarded by a peak RATIO (1.25)** so a generic HUB is never absorbed ("born in the
united states" (36) is NOT folded into "children born in the united states" (12); the "the trump
administration" entity hub is protected). It is the safe realization of the docstring's long-standing
"nested sub-grams → maximal phrase" without the over-merge trap a naive substring merge caused.
`collapse_and_rank` (collapse+rank+truncate) is now **shared** by build-time `top_synchronized` and
applied at **render time** in `site.py` (`sync_table` + the peak table), so **already-built historical
day pages** reflect the current merge rules without re-running the engine (the display-time refresh
pattern the boilerplate guard uses). Re-rendered `site/public` + verified live: the 06-30 flagship
**20 → 16 rows** (4 fragments/padding folded; flagship hub + every distinct message intact, checked
against the stored ledger snapshot; "statement after the supreme"/"children born in" now absent live,
"born in the united states" present). **98 tests** (+4: content-subrun, fragment-fold, HUB-guard,
flagship end-to-end). Commit `710e1ba`, deployed. **Known residual (queued):** the `14th`/`fourteenth`
numeral-vs-word synonym pair still shows twice, that's a normalization-map problem, not containment,
and is a separate small feature (not a launch blocker).

### Session 9 (2026-07-15, Fable), The Search authored: 47 pre-registered hypotheses over the 25-year archive

Michael asked what the archive is actually sitting on ("1–2 pieces a month of insight") and handed
Fable the gameplan. Written: **`docs/12-SEARCH-PROGRAM.md`**, the pre-registered hypothesis sweep.
**47 hypotheses in 5 compute waves** (S1 pure-ledger coordination mechanics · S2 full-text language
evolution · S3 roster/lifecycle joins · S4 event joins · S5 keyed joins via one-shot Actions
dispatch), each with a mechanical protocol (metric | denominator | split | CONFIRM threshold |
named confound) so **Opus can confirm/refute the entirety without judgment calls.** Standards
codified as law: pre-registration (silent tuning forbidden, amendments are dated), the coverage
confound as refutation-attempt-#1 with a mandatory density-matched control, split-halves
(107–113 vs 114–119), symmetry + power-position reframe, power floors (UNDERPOWERED ≠ REFUTED),
mutation-tested metrics, aggregate-only oddities, gravity ⚠ protocol (S4.3 thoughts-and-prayers,
S4.7 Jan-6 ⚠⚠ measured-not-published), $0/local ($NO key ever local; S5 runs where the key already
lives). Ambition math: expected ~22–28 CONFIRMED → 1–2 drip pieces/month for 12–24 months; the
graveyard tally and the grouped null result are also pre-committed publishable pieces. Lead T1 bets:
Industrialization of the Memo (S1.1), Freshman Assimilation Speedrun (S3.1, 13 cohorts already in
hand), Lame-Duck Accuratey (S3.2), the Voldemort Index (S2.1), What Losing Sounds Like (S2.3), the
SOTU Gravity Well (S1.8), the 2022 Self-Audit (S1.9, either outcome publishes), One Court Two
Languages (S4.1, birthright 06-30 is the live pilot card). **`docs/13-SEARCH-LEDGER.md`**
initialized (append-only verdicts + tally). Out of scope by design: embeddings/topic-layer/external
🔬 families (stay in HORIZON under the quarterly-pick rule). **Next Opus session: Wave S0**
(data-inventory audit incl. the Alexandria shards, the query harness, failure-test metrics library,
reference tables, card schema), then S1. The streak is untouched; the Search is a parallel content
program, releases remain Michael's act.

### Session 10 (2026-07-15, Fable), the Deep Archive program authored (docs/15)

Michael asked for the gameplan that turns the `docs/14` backfill feasibility into buildable work,
rolled into the existing programs without interference, and an accurate answer on whether it's
meaningful. Written: **`docs/15-DEEP-ARCHIVE-PROGRAM.md`.** Architecture: five labeled lanes
(`press` core source untouched · **`crec` 2001–2026** Extensions-first · `dcinbox` · `academic_archive` ·
`loc_webarchive` conditional on the D2 probe gate) under **two binding laws**, genre isolation
enforced in code (no cross-lane trend claims, failure fixture required) and **the calibration law** (no
CREC-only pre-2013 claim publishes until SD.8 shows directional concordance with the press core source on
the 2013–2026 overlap). Waves: D0 rails (audit-as-code + mirrors + reference tables) → D1 CREC track
(sitemap→MODS→granule ingest, resumable ≤3 req/s background crawls, E-lane ≈ 350–400k fetches ≈
~35–40h; per-Congress ledger shards via the existing engine; per-Congress audit JSON committed) → D2
LoC extraction probe (12-member stratified browser probe, **≥8/12 gate** else the lane is killed for
v1) → D3 cross-check lanes → D4 the Deep Annex (SD.1–SD.7 pre-registered stubs: full-span SOTU
gravity well, Voldemort across four presidencies, what-losing-sounds-like over five flips, the crisis
playbook ⚠, escalation clock, the tribute economy, the anniversary engine FEATURES-dark; protocols
freeze by dated amendment before each runs). **Non-interference contract:** zero Actions, zero
daily-pipeline code paths (`pipeline/deep/` only, read-only reuse of the Search's reader/metrics),
X:-only storage (~≤25 GB of 1.9 TB), FEATURES-dark, and **last place in the session-yield order** ,
crawls run between sessions so calendar time is cheap even when session time is contested. Synergy:
D1's ingest IS Build-Program item 1.6's floor-leg ingest (one build, two consumers). Accurate sizing
(15 §8, verbatim ruling): meaningful **second-order**, it repairs Alexandria's "25-year" integrity
debt, puts 9/11→Katrina→2008→Tea Party inside a symmetric instrument, and creates the twice-confirmed
defensibility tier; it does nothing for the launch or the November window, and it holds last priority
by design. Expected annex yield: +6–12 confirmed cards + calibration upgrades to existing findings.

### Session 11 (2026-07-15, Opus), Deep Archive Wave D0 (the rails) COMPLETE

Executed docs/15 §2. All new code in `pipeline/deep/` (zero edits to daily-pipeline or `pipeline/search/`
internals; read-only reuse of `config`), all data on X: (deep-lane dirs created), FEATURES-dark, no
Actions. **126 suite tests green.**

- **D0.2 lane plumbing (`pipeline/deep/lanes.py`):** the 6-lane registry (press core source untagged; crec /
  dcinbox / academic_archive / loc_webarchive / wayback tagged); `DEEP_ROOT` derived from the state
  junction (machine-portable, no hardcoded drive); `tag()` fail-closed provenance enforcement (url +
  unit_date + stable_id or it doesn't enter); **`lane_of()` = GENRE ISOLATION (Law 1) in code** (raises
  on any mixed-source set); `CrawlManifest` (append-only, hash-verified, resumable) + politeness config.
- **D0.1 the 7-gate coverage audit (`pipeline/deep/audit.py`):** both-party floor (≥5 members/party) ·
  symmetry ratio (min/max ≥ 1/3 on distinct MEMBERS) · attribution completeness (≥0.40) · integrity
  rate (reported) · provenance (100%) · genre isolation · cross-era temporal gate. Deterministic +
  JSON-reproducible. **Failure fixtures (`tests/test_deep_audit.py`):** the 29 D/0 R lane rejected, a
  mixed-lane series raises, sub-ratio/missing-provenance/thin-attribution all fail.
- **Adversarial review (4-lens workflow) found + fixed 1 BLOCKER + 3 should-fixes before commit:**
  (BLOCKER) `audit_cross_era` didn't check same-lane → a crec-2005→press-2015 trend would be
  authorized, the exact genre confound gate 7 exists to stop; now raises on differing lanes.
  (fix) `audit_coverage` was fail-OPEN on provenance/attribution → now fail-closed (omit = FAIL).
  (fix) unregistered/typo'd lane sailed through → now rejected in both audit paths + `expect_lane`
  guards an untagged deep set. (fix) `MIN_RATIO 0.33 → 1/3` (0.33 admitted 3.03:1). +5 tests.
- **D0.4 reference tables** (`data/reference/deep/`): CREC granule-class allowlist (EXTENSIONS/HOUSE/
  SENATE; DAILYDIGEST excluded) + CREC boilerplate seeds (procedural furniture). `elections.json`/
  `presidents.json` reused from the Search, not rebuilt.
- **D0.3 mirror-first (`pipeline/deep/mirror.py`):** the hash-manifested resumable fetcher; Grimmer
  Senate corpus mirrored to X: (72,817 files, manifested). DCinbox URL discovery deferred to D3 (the
  downloads page is JS-rendered, a page-structure detail, not a D0 blocker).
- **Acceptance validated + refined:** the audit dry-run on the actual press lane reproduces A1's structure
  AND sharpens it, the accurate single-party gap is **2001–2008** (not 2001–2012); 2009+ is already
  symmetric. So **CREC's unique symmetric-fill value is 2001–2008**; 2009–2012 it's a densifying
  cross-check. **The rails are down; D1 (the CREC Extensions crawl) is the next Deep-Archive slot.**

**D1.a/b built + verified end-to-end (same session):** `pipeline/deep/crec.py`, sitemap day
enumerator, MODS parser (structured `congMember` attribution: bioGuideId/party/chamber/role, NO
name-parsing), the Record-furniture stripper, the deep-schema normalizer (`source=crec`,
`crec_section=E`, granule URL + package date as provenance via `lanes.tag()`), and the resumable/polite/
immutable Extensions crawler (keyless GovInfo metadata+content+sitemap paths; `/bulkdata` zips avoided
per the scout). Parser locked with `tests/test_deep_crec.py` (4 tests; **130 suite green**). **Verified
on real data (CREC-2001-01-03): 41 Extensions granules, 97% attributed, and the day audit is D=10 / R=14
members, ratio 0.71, PASS, symmetric two-party coverage in a year the PRESS lane is 100% D / 0 R.** That
is the Deep-Archive thesis proven in one day. **The 2001–2008 Extensions crawl (the unique-fill window)
is LAUNCHED in the background** (resumable, ~3 req/s, ~4–5h; raw MODS immutable, statements →
`crec/state/E/statements-{year}.jsonl`). **Next: D1.c** (per-Congress CREC ledger shards via the existing
engine, once the crawl lands) **+ D1.d** (per-Congress audit JSON committed), then 2009–2026 to complete
the calibration overlap.

**D1.c/d VERIFIED on congress 107 (2001–2002):** the crawl landed 107 complete (11,867 symmetric
Extensions statements) before a DNS blip; `build_congress_shard(107)` produced a 6.9 MB ledger shard
(4,141 phrases, schema-identical → the Search's streaming reader queries it unchanged), and
`audit_congress(107)` is **per-year PASS + symmetric** (2001 D=211/R=208 ratio 0.99; 2002 D=209/R=211
ratio 0.99), two-party coverage where the press lane is 100% Democrat. **The D1.d audit caught a real
bug** (`to_statement` received the package id `CREC-2001-01-03` where the ISO date belonged, so
`published_at[:4]` read `'CREC'` and collapsed every year to one window), fixed (`pkg_date()`),
regression-tested, and the 11,867 already-written statements repaired in place; the shard rebuilt clean.
**131 tests green.** Audit artifact committed to `data/derived/crec/audit/congress-107.json`.
**Accurate finding, R1's "weak carrier" confirmed (docs/15 §9 amend D1-A):** the ledger's top phrases are
dominated by parliamentary procedure (Committee-of-the-Whole) + bill-title language ("to provide for …
and for other purposes"), so CREC needs a **heavy genre-boilerplate layer before phrase-COORDINATION
findings** (first seeds added; the full suppressor + failure fixture queued for D4). Its boilerplate-robust
near-term strength is **SPEAKER-attribution analysis** (SD.2 name-avoidance / SD.6 tributes / floor-vs-
press), which is re-sequenced ahead of adoption curves. 2003–2008 crawling; 108–112 shards as the crawl
lands; 2009–2026 for SD.8 calibration.

### Session 9 (2026-07-16, Opus), the live-site breakdown: three real defects, all fixed

Michael reported the live site showing *"Some of our output could not be verified today"* for BOTH
parties. Every Action was green, this was not a crash. Root-caused to **three separate defects**, all
now fixed, tested, and pushed.

**1. The fail-safe skipped the good voice** (`distill.py`, commit c3b7424). The Sonnet drifted two
quotes; the verifier correctly rejected them, but `daily_line()` then dropped STRAIGHT to the
apologetic stub, **skipping `_compose_dry()`**, the rich deterministic composite that is verifier-clean
because of the design. One drifted LLM quote nuked the whole Daily Line to an apology. Now: verify-fail →
rich deterministic composite → re-verify → publish; the stub is the last resort only. **Confirmed live**
on the 07-15 repair run: `verifier_passed=True fallback=False`, real line published.

**2. Typographic false negative** (`verify.py`, commit c9e2d7f), *the reason the Sonnet voice was
never shipping*. Press releases use smart quotes; the Sonnet emits ASCII. It quoted a REAL fragment as
`"applauded today's house passage…"` against a source reading `today’s` → "un-grounded". Same words.
`_norm` folded whitespace/case but not typography, despite the docstring promising "robust to
rendering". `fold_typography()` added. **Also closed a real hole**: `_NEGATION` holds ASCII `"don't"`, so
a source written `don’t` never matched and a meaning-inverting truncation after a curly contraction
would have been wrongly grounded. No bypass risk (the `_QUOTE` extractor already matched both quote
styles); verification not weakened (only typography folds, invented words still fail).

**3. The prompt invited the violation** (P2 **v1.2**, commit 97b112a). v1.1 told the voice it may "note
the day's most synchronized phrase" but never to leave it UNQUOTED, so the Sonnet quoted a
code-computed ledger n-gram, which the verifier refuses to ground (HIGH-1, by design). v1.2 says it
plainly, matching what the deterministic voice already did.

**Repair lever added** (c1b7edf): `assemble.yml` workflow_dispatch now takes an explicit `day` (the
readiness gate correctly refuses to re-assemble a final day, so a plain dispatch can't repair one).

**Also this session, the readiness gate** (`pipeline/readiness.py`, commit 097a000), from Michael's
design catch: *"I don't want to publish 'nothing today' just because it wasn't out in time."* He was
half right, the 1-day lag IS the designed cadence (`product_day()` = prior NY day), but the gap he
sensed was real and **worse than staleness**: a late mirror meant we ingested a thin day, published it,
and the next run ADVANCED `product_day()`, **skipping that day permanently**, a hole in the
time-series (the long-term value). The old `_volume_anomaly` only ALERTED. Now a run assembles the OLDEST
not-yet-final READY day (5-day lookback, oldest-first so the series fills chronologically); if none is
ready it **NO-OPS at $0** (no cluster/distill/API) and a later pass recovers it; a day that never fills
is force-finalized after MAX_WAIT so a quiet holiday can't livelock the streak. RUN A/B now run twice
daily (09:30+19:30 / 11:30+21:30) so a late day recovers same-day and a backlog drains (two passes, not
four, repo is still PRIVATE = metered minutes).

**Two traps encoded** (either would kill the streak): SAME-WEEKDAY baseline (an all-days median would
hold every Saturday forever) and no-history⇒READY. **Two bugs caught by dry-running the gate against
PRODUCTION state before shipping**: (a) pre-gate manifests lack `final`, so `_is_final` would have
called all history pending and re-assembled old days; (b) force-finalize would have **published a
zero-statement day** (the gate directly chose `day=2026-07-10, count=0, forced=True`), precisely what
Michael said must never happen. Zero-data days are now skipped (self-healing, no empty page); only
real-but-thin days are force-published. 8 readiness failure fixtures.

### Session 12 (2026-07-16, Opus), v2 Build Program: the dark shelf opens (1.1, 1.2, 1.8)

Directive: *"v2 Build, grind until complete or blocked by my tasks/decisions."* Three features now
sit **built / verified / UNRELEASED** behind their FEATURES flags. **188 tests green.** Nothing on
the build side is blocked on Michael; no public surface changed (every flag is still False).

- **1.1 The Archive** (`db877a2`), era + month chapters, era fingerprints, verifier-gated loader
  (only `verifier.passed` chapters render: 340 clean, 13 correctly excluded). Dark gate confirmed.
- **1.2 Silence Detector + "Shouting Into the Void"** (`6f5934c`, render `9d75f43`), the absence
  map. `data/reference/gdelt_theme_map.json` (24 topics) is built from the SAME taxonomy_v1 seeds
  that drive the corpus-side match, so both halves of a silence claim share one published
  definition and a third party can reproduce it. `pipeline/gdelt.py` (keyless DOC 2.0, 1 req/5.2s,
  raw stored immutably) + `pipeline/silence.py` + the board render.
  **The critical guard, a gap is not a silence:** a failed GDELT pull returns None (verified
  live: a real 429 -> None -> topic EXCLUDED -> zero claims), and a thin/one-party day scores
  nothing in either direction, because a corpus hole must never read as avoidance. A missing news
  baseline writes an UNSCORED board rather than one fabricated from absence. Both directions render
  on ONE page, that is the release gate, not a layout choice.
- **1.8 The Owner's Brief** (`2902c44`), the five health numbers (07-OPS §2) + streak + top phrase
  + degraded days + the dark shelf, pushed to ntfy Mondays. Wired into `run_assemble.main()` on
  **both** paths (including the NO-OP return, a Monday where nothing assembled is precisely the
  Monday the owner needs a brief), skip-and-log because that workflow step has no `|| true`: a
  report ABOUT the machine must never take the machine down.

**The Session-12 adversarial review earned its keep, it caught a brief that lied.** The first cut
held the accuratey rule at FILE level and lost it at FIELD level: `row.get("claims_dropped") or 0`
turns "the verifier never reported" into "the verifier dropped nothing", and zero is green. The
review REPRODUCED a confident **ALL GREEN** brief with four things simultaneously broken (newest
manifest zero-byte, ledger carrying no days, symmetry audit 12 days dead, claims_dropped never
written) against a reality of: last publish 2 days prior, $9.40 spent, audit dead, drop unmeasured.
That fixture is now the regression test. Every input reads through `_req()` (None for
absent/non-numeric), and every None propagates to `unknown`. **A green means measured-and-healthy,
never silent.**

Also fixed, each a real defect:
- **The false RED, on real data.** `statements_ingested` changed meaning in Session 5 (cumulative
  corpus totals -> day-scoped) with no schema bump. Medianing across that boundary read a healthy
  186-statement day as 0.4% of a 44,546 "median" -> a confident RED that would have sent Michael
  into **Playbook P2 hunting an outage that never happened**. Pre-boundary reports are now excluded
  *visibly* (`DAY_SCOPED_FROM`), and `ops.symmetry_report` emits **`day_scoped: true`** so no future
  reader infers semantics from a date. **Lesson for the schema discipline: the meaning of a field
  changed silently once. `schema_version` did not move. Assume it can happen again.**
- **§2.3 was half-implemented**, upstream freshness was passed through, never gated. The actual
  `age_hours` lives in the **collect** manifest (RUN A measures it); the assemble-side symmetry
  report carries only a placeholder note, which is why the gate was silently missing. A 40h-stale
  upstream serving a healthy mirror replay read GREEN, P2's 72h cold-standby clock would have
  started days late. Now gated.
- **spend** projects over days the LEDGER covers, not days elapsed (the old denominator
  under-projects in the GREEN direction precisely when spend starts mid-month: $5 over 5 ledger days
  -> $16 projected RED, where elapsed-days math said $7.75 green). MTD is summed from `days` (the
  ledger), not `total_usd` (a cache that can lie).
- **headline by inclusion**, by exclusion, any unrecognized status inherited green.
- **the render carries each number's MEASUREMENT, not just its method** ("[RED] coverage: each party
  vs its trailing median" named no day, no party, no share, nothing a tired owner can act on, which
  is the opposite of the zero-interpretation promise). Governor state now appears in the text.
- `force=` can no longer bypass the **dark** gate (cadence only): the FEATURES flip is the release
  act, dated, public, diffable, and a kwarg must not become a second, undated one.
- **Test pollution that would have shipped a lie.** The v2 tests had written REAL artifacts into
  `data/derived/brief/`, one recording `shelf.released: ["owners_brief"]` while the flag is False ,
  and `assemble.yml` does `git add data/derived`. A fabricated receipt claiming a dark feature was
  released, committed into the repo whose entire thesis is accurate receipts. Tests now run against a
  synthetic derived tree with ntfy stubbed (which also stops the suite pushing to Michael's live
  phone topic when `NTFY_TOPIC` is exported). A guard test fails loudly if the isolation ever lapses.

**Deviation logged (§13 knob):** `verifier_drop`'s denominator is dropped+published (claims
*offered*), where 07-OPS §2.4 says "dropped ÷ published". The code's is the rate the 25% line is
meaningful against; flagged here rather than silently diverging, 07-OPS §2.4's wording should be
reconciled to it at the next doc pass.

**Queue after this:** 1.3 Authors-vs-Vessels (its citation back-join dependency is already done),
then 1.4/1.5/1.6 (floor, CREC ingest already built in D1)/1.7/1.10; 1.9 stays gated on
`DATA_GOV_API_KEY` via Actions dispatch.

### Session 13 (2026-07-16, Opus, worktree `v2-lane-b`), v2 1.7 The Duet + phrase search; the misattribution gate

**Parallel-session note.** The `(fork)` session was live in the main tree the whole time (verified
running, same cwd). A worktree fixes FILE collisions, not DUPLICATE FEATURES, so this session took a
disjoint claim: the fork walks 1.3 -> 1.4 -> 1.5 (a dependency chain: awards need member pages), this
lane took the independent leaves. **1.10 was dropped from the claim on inspection**: no `archetype`
code exists anywhere yet, and the Memo-Detector it needs is shared substrate with the fork's 1.3/1.4
(08 §87), building it here would have duplicated precisely what 1.4 must build. Worktree at
`../polispeak-v2` with junctions re-pointed at the same X: storage (read-only use of `state`; no
ledger rebuild from this lane).

**1.7a The Duet (`b9bd3c5`), built/verified/dark. 1.7b phrase search (`8ed87a5`), built/verified/
dark. 210 tests green; every FEATURES flag still False.**

**The spec was wrong and the data said so.** VISION A5 promises "same phrase, both parties, same day,
**opposite intent**". Built on 2026-06-30 (the SCOTUS day), the strongest duet is both parties saying
*the supreme court* about **entirely different cases**, Democrats on birthright citizenship,
Republicans on Title IX. Not opposite intent: parallel universes. Asserting intent would have made
the first real exhibit factually wrong. So the Duet ships the whole line EXCEPT the verdict: the
phrase, then each side's own verbatim sentence, no adjective from us (Constitution: no verdict). When
the framing IS opposed it needs no help, *rule of law* is D-immigrant-families vs
R-sanctuary-cities, same three words, same day.

**THE FIND: verbatim != attributable, and the verifier cannot know the difference.** A press release
is a MULTI-SPEAKER document. Rep. Cisneros's sentence ("I'm proud to support my colleagues,
Congressman Castro and Congresswoman Houlahan...") appears verbatim inside the releases published by
BOTH Castro's and Houlahan's offices; the first cut published it as each of their own words.
`verify.is_verbatim()` PASSES it, by design it asks only whether the string occurs in the cited
statement, and it truly does. **It is a structural blind spot in the citation promise, not a bug in
verify.py.** The gate now lives in `duet.attributed_to_other()`: a sentence is attributable only if
the nearest attribution marker names that member, checking BOTH the leading form (`said Rep. X.
"quote"`) and the trailing form (`"quote," said Rep. X`), reading only backwards passed the actual
2026-06-30 text (which happens to be leading-form) while silently accepting every trailing-attributed
quote in the corpus. My synthetic fixture caught that; the actual data hid it. Name matching is
token-equality, never substring (Smith != Smithson).

**The live site was audited and is CLEAN, it is latent, not active.** All 103 published quotes
(2026-07-13/14/15) were joined to upstream source text (`congress-press` 2026-07.jsonl) and checked
with the same gate: 103/103 joined, **0 flagged**. `run_assemble._citations()` has no speaker check
and is in its structure exposed, but applying the gate there changes PUBLISHED output (a dropped citation
can push a talking point below the >=3-unit quorum and remove it from the product), so it is filed as
its own evaluated change rather than a side effect of a dark build. Same exposure applies to
`distill.py`'s `groundable` fragments.

Other gates, each earned on real output rather than imagined:
- **furniture is rejected, never a fallback**, "WASHINGTON, Rep. X released the following
  statement..." is verbatim and is not a thing anyone said; if the phrase appears only in a header,
  that member simply did not say it and the next member is used.
- **quotes are complete sentences, never clipped**, a trailing clip inverts meaning ("...a bill I
  will never support" -> "...a bill I will"), which is why the verifier carries a negation guard at
  all. A long sentence publishes whole.
- **abbreviations are not sentence ends**, real output came back guillotined at "Trump v." and "with
  U.S."; case names are the common path in this corpus, not an edge.
- **fragments ending mid-construction are dropped**, "united states and" scored a duet by pairing
  Democrats on birthright citizenship against Republicans on battlefield innovation: two parties
  saying the country's name. Only the TAIL is tested, n-grams start at 3 tokens, so "the supreme
  court" is the shortest real form of that phrase and a leading-article rule would delete the best
  duet on the board.
- **one duet per topic** (a SCOTUS day otherwise shows five spellings of one event), applied AFTER
  the citation gate so an uncitable strong row cannot consume its topic and silently drop a citable
  variant.
- Duets are rare and event-driven as designed: 57 candidates on 2026-06-30, **0 on 2026-07-08**.

**1.7b phrase search:** the site is STATIC and the ledger is 2.9GB / 2.8M n-grams, so search is a
prebuilt index (one row per phrase PAGE, 291 today, ~23KB inline) filtered client-side. Scoped to
real pages so a result can never 404, and the page discloses what it does NOT cover (a phrase absent
from the index never cleared the 3-member bar; that is not "nobody said it"). Both injection defenses
verified against a **live DOM**, not string asserts: a hostile phrase (`</script><img src=x
onerror=...>`) fired no handler, produced zero elements, rendered as a text node with 0 children.
Dark means ABSENT, search.html is not written at all while the flag is off, because an unlinked page
is still crawlable and shareable.

**Left for the fork / next:** 1.6 floor (buildable, CREC ingest exists from D1), 1.9 credit-claim
(gated on `DATA_GOV_API_KEY` via Actions dispatch), 1.10 memo-cadence (blocked on the Memo-Detector
substrate that 1.3/1.4 will build).

### Session 14 (2026-07-16, Opus, worktree `friendly-bardeen-a6aa2d`), the Session-13 gate on the LIVE citation path

**Scope:** evaluate + wire `duet.attributed_to_other` into `run_assemble._citations`. **228 tests
green** (222 on the rebased trunk + 6 new; composes cleanly with the parallel lane's streak fix
`20ea633`). No flag flipped, no posting touched, no published output changed. Files: only
`pipeline/run_assemble.py` + `tests/test_session14.py` (parallel lane's `duet.py` untouched).

**1. The live path is CLEAN, reproduced, and then widened.** All **103** published quotes
(2026-07-13/14/15, that is the entire live quote corpus; no other day carries citation quotes)
re-joined to upstream `congress-press` and re-checked: **103/103 joined, 0 flagged**. Session 13's
number confirmed precisely. Then the same check on the **whole `groundable` set** (item 4) by
recomputing `util.statement_id` from upstream so uncited statements join too: **142/142 fragments
clean, 0 unjoined, 0 cross-party**. Both exposures are latent. Not a live defect.

**2. The stated blocker was wrong, and that is what unblocked this.** The Session-13 note held that
"a dropped citation can push a talking point below the >=3-unit quorum". It cannot:
`verify.verify_talking_point` fixes the quorum from `tp["statements"]` **before** `_citations` is
ever called, and nothing in `_citations` feeds back. `_citations` is a pure receipt renderer. So the
gate cannot move a published number **because of the design**, the only thing at risk was the pull-quote.
And `quote=None` is **already a live published state** (2 of 105 citations today) that `site.py:608`
already renders gracefully (member/date/source/archived links, no quote block). Hence **demote,
never drop**: the citation always publishes; only an unattributable quote is withheld.

**3. "Prefer a self-attributed fragment" has no material, measured.** Each statement contributes
precisely **one** fragment per talking point (107/107 at index 0), so the preference loop degenerates
to a single check. It is still built that way (it is free, and it is the correct shape if extraction
ever emits more), but the actual choice is binary: the member's quote, or no quote.

**4. THE HAZARD IS REAL AND LARGE.** Across 6,503 releases: **27.4% carry a colleague's attributed
block**, and **21.8% of all sentences** sit inside one. Near-symmetric (D 27.6% / R 26.9%). The live
0/103 is not structural safety, it is a small sample of a big surface.

**5. THE GATE HAS A FALSE-POSITIVE MODE, and I did NOT "fix" it, the obvious fix is an Article IV
trap.** `_SAY` contains ordinary English verbs (`continued|added|noted|says`) and `_NAME` matches any
capitalized token, so **"protecting Dreamers from continued Republican attacks"** parses as *"Republican"
said*, and under the leading-form rule that one bogus marker then governs **every sentence after it**.
Real casualty: Whip Katherine Clark's release, where all 22 sentences of her own prepared remarks are
flagged as "Republican's". Same shape: "intentionally **added** PFAS", "said **Congress** has the
authority", "wrote **Monday** in a post", verb objects read as speakers.
- I prototyped the natural fix (require a closing quote before a leading marker) and **measured it into
  the bin**: Rep. Don Davis's quote is reprinted in **three** offices' releases, and the closing quote
  mark survives only in `dondavis.house.gov`, the `fedorchak` and `fischbach` scrapers dropped it. So
  the fix would stop flagging Davis's words in precisely the two releases where he is the *colleague*.
  **Quote marks are a per-office scraper artifact**, so any rule keyed on them makes the system's
  sensitivity vary by whose scraper ran, the same trap docs/16 rejected capitalization for
  (an asymmetric *instrument*). Rejected on measurement, not taste.
- Accurate precision: of flagged sentences, ~72% name a roster member outright, and most of the
  remainder are **real non-member speakers** (`rod lenz`, `dreisen heath`, `salvador g. sarmiento` ,
  advocates quoted in releases), whose quotes are *correctly* refused. Genuine noise (`congress`,
  `ways`, party labels) is ~1–4% of markers and **symmetric: D 4.22% / R 4.12%**, no Article IV
  problem in either direction.
- **So the current gate's over-flagging bias is the CORRECT bias here**, because demote-only fails
  safe: an over-flag costs a pull-quote, an under-flag publishes a colleague's words under this
  member's name. Wired as-is, deliberately.

**6. Verified no-op on live data.** The **shipped** `_attributable` (not a reimplementation) re-run
over all 103 published quotes with the actual roster: **103 still attributable, 0 demoted.**

**Failure tests is a real one, on real text** (`tests/test_session14.py`), and it is
**mutation-checked**: neutering the gate makes it fail with *"published a colleague's words as
Fedorchak's own"*. The fixture is the sharpest live shape found, **cross-party**: Rep. Julie
Fedorchak (R-ND) published Rep. Don Davis's (D-NC) quote, so ungated, a **Democrat's words would
publish under a Republican's name and .gov link**, verifier-clean. Both directions asserted (the
colleague's line refused, the member's own line in the same document still published), plus both
fail-open paths (unresolvable speaker, unlocatable fragment) pinned to today's behavior.

**Left, deliberately, for a session of its own:**
- **`distill.py` `groundable` (item 4), measured 142/142 clean, NOT wired.** Gating it removes
  fragments from the live Sonnet voice's grounding set, so an over-flag makes the voice fail verify
  and fall back to the deterministic template, i.e. it *changes published prose* and needs its own
  validated run. Measured need today: zero. Refusing to do it as a side effect of this change is the
  same call Session 13 made about `_citations`.
- **`site.py:618-622`** renders raw `tp["fragments"]` as quotes when a day has no citations
  (historical days, pre-citations-backfill). That path is **ungated**, it should be folded into the
  citations backfill item (e), not patched separately.
- The `_SAY`/`_NAME` noise (`congress`, `ways`, party labels) is worth a principled pass someday ,
  the discriminator that survives measurement is *"only a person can be attributed speech"* (roster
  + name-shape), **not** quote marks and **not** capitalization.

### Session 15 (2026-07-16, Opus), nomenclature tagger built + green (branch only); two self-inflicted errors worth keeping

**Not on main.** `wip/nomenclature` (worktree `../polispeak-nom`): the docs/16 SPAN tagger is **21/21
fixture, 233 suite**, but **unwired, unreviewed, unmerged**. Reference data done: govinfo BILLSTATUS
113–119 (keyless, ~347MB raw to X:), committee lane from congress-legislators, `verdicts-119.json`.
The corpus pass lands on the spec's own predictions, sync phrases **461,501 (exact)**, covered
**14,175** vs 14,178 predicted. Measured both directions: KILLS `21st century road to housing act`
1.000, `the one big beautiful bill act` 1.000, `state and related programs appropriations act` 1.000,
`bipartisan 21st century road to housing` 0.986 (Rule B), `national security department` 0.946
(committee lane), `safeguard american voter eligibility save act` 1.000; PROTECTS at 0.000 ,
**`the big ugly bill`** (the D counter-brand the rejected CAP design tagged at 0.908), `the save act
would`, `child tax credit`, `cuts to medicaid`, `birthright citizenship`, `law enforcement officers`,
`the west bank`, `border patrol agents`.

**ERROR 1, I misdiagnosed a timeout as a crash, then wrote the guess down as a finding.**
`build_verdicts` exited 127 after one line; I read OOM and committed a WIP message blaming "the span
arithmetic + the `_anchor` stopword trap". Both innocent. The actual cause: `is_nomenclature()` reads
`verdicts-{congress}.json` and **the table had never been generated**, an interrupted workflow
stopped between the index stage and the corpus pass. The code was **starved, not wrong**; feeding it
the table went 13/21 → 20/21 with **zero code change**. The 127 was my own tool timeout killing a
two-pass scan over 75,757 statements × 552 days, *tens of minutes* of offline capex that I kept
allowing ten. **Lesson, and it rhymes with the §1.4.1 one: an exit code is not a diagnosis. Measure
before you name a cause, and never write a hypothesis into a commit message in the voice of a
finding.** (The prior WIP commit is corrected in-place by 5603588.)

**ERROR 2, I nearly "fixed" a correct filter to satisfy a false test.**
`test_official_and_display_titles_never_enter_the_index` asserted `len(name) <= 20` as a proxy for
"no prose". The data falsifies the premise, verified against raw BILLSTATUS XML: congressional
**backronyms are real short titles** (`advancing critical connectivity expands service small business
resources opportunities...` IS the ACCESS BROADBAND Act; also ANTI-SOCIAL CCP, HOUTHI), and
**hres1225 registers "Original Resolution Commending the Islamic Republic of Pakistan..." under
titleTypeCode 101, "Short Title(s) as Introduced"**, a 22-token sentence by the clerk's own hand.
The allowlist was already right (checked against real 119 data: only Short Title codes; Official
6/7/259 and Display 45/81 excluded). The proxy is replaced by assertions on the **actual gate** plus
the cite invariant, with the evidence written into the test, changing a test until it passes is how
you fool yourself.

**THE ONE REAL DEFECT the proxy was covering: 3 indexed names whose cite was the empty string**
(incl. a 47-token appropriations omnibus). A name indexed under `cite=""` licenses a tag whose
receipt is *nothing*, a suppression the reader cannot check, which is the single thing the design
exists to forbid. `parse_titles` now applies the project's own rule to the reference table itself: **if
it can't be cited, it doesn't enter.** Empty cites **3 → 0**, and all **47 legitimate >20-token
statutes retained**, a length rule would have evicted real statutes *and* still admitted a short
official title.

**Also this session:** the Session-14 speaker gate was validated and merged to main, **mutation-checked**
(neutering `_attributable` to always-True makes 2 fixture tests fail, so the fixture is not vacuous).
Worth recording: my own independent re-check of its "no-op" claim came back **hollow**, it reported
"0 demoted" having actually checked **0 quotes**, because none of the 103 cited URLs exist in the
local corpus snapshot (the day files are built in Actions from the cloud's state). A vacuous pass is
not a pass; the mutation test is what actually validated it.

**Process correction:** this session had been squatting on the **shared main tree with an experimental
branch checked out**, with three workers live, precisely what the parallel-session protocol forbids.
Main is handed back on `main`, clean; the WIP runs in its own worktree with its own corpus junction.

**REMAINS for nomenclature:** wire `tag()` at display time (**before distill**), `nomenclature_rate`
per party in the nightly audit, adversarial review, merge. No flag flipped; nothing published changed.

### Session 13b (2026-07-16, Opus, worktree `v2-lane-b`), the provenance seam; two zero waves; the gate was 0/3

**The session's three headline outputs are all corrections to numbers WE wrote.** Recorded here because
the pattern is the finding: every one survived because nobody checked the thing the number rested on.

**1. THE PROVENANCE SEAM (docs/13, the big one).** `dwillis/congress-press` is a UNION OF TWO DATASETS
keyed by the record-level `date_source` field. The `legacy` lane (a ProPublica import) runs 2001 →
**2021-01-03 and stops forever**, the day the 117th Congress was seated. The `scraper` lane starts
~2018 at 49 offices and accretes. The "2021 coverage collapse" is not behavior; it is the union losing
a dataset. Both adversarial skeptics CONFIRMED (0/2 refuted); one re-derived every number straight from
the 303 mirror files, bypassing the harness so no harness quirk could propagate.
**Consequence: SPLIT-HALVES, the program's primary robustness control, has been comparing ProPublica
to a scraper, not 2013-2020 to 2022-2026.** Half A is ~95% legacy, half B ~100% scraper, across a 2.6×
coverage change and a 7.7-point party-mix shift (legacy D:R 1.538 vs scraper 1.12). Every both-halves
PASS survived a weaker test than advertised; every FAIL may be plumbing, including **S2.3**, the
reversal the ledger sells as proof the control works. All 34 verdicts need revisiting.
**S4.7 (January 6) is a SIGN INVERSION**: raw −69.9% ("muted congressional response to January 6" ,
maximally quotable, publishable, FALSE) vs lane-isolated **+75.5%**; fixed-cohort makes Jan 2021 a local
MAXIMUM. The 70% "drop" is the import ending three days earlier. Only the review gate stopped it.
**Remedy is isolation, not normalization**, `date_source` must become first-class (harness.py:399-427
drops it today), same shape as the deep archive's genre-isolation law.

**2. §1.4.1 WAS 0/3, NOT 2/3-about-to-pass.** Measured from the run LOGS, not the run status: 07-14 and
07-15 crons were genuinely clean, but the **07-16 12:59Z cron published the apology stub for BOTH
parties** (pre-fix code; the typography fix landed 14:53Z). The published day was repaired by dispatch,
so the site is correct, but the UNATTENDED streak reset to zero. **An Actions `success` is not a green:
all three runs exited 0, and `gh run list` cannot tell a product from an apology.** Now a code-owned
number (`ops.unattended_streak`, manifest `event`/`unattended`), failing closed. Earliest accurate pass:
07-19 (Sun), which also satisfies the weekend-day clause.

**3. THE MEMO BET IS REFUTED BY ~90×.** Michael's "90+% accuracy if a line or two persists per member",
tested directly (P(held-out member carries ≥2 of 3 memo lines built without them)): **1.01% same-party
vs 0.00% strongest null**, pre-registered bar +10pp. 11 agents, 8 nulls, all 3 skeptics refuted. The
earlier 94.3% was itself an artifact, **the system's own suppression layer removes −25.0pp of
apparent coordination, 4× more than the attribution gate (−5.9pp) built this session.** The publishability
skeptic found the reason The Script must ship as a CONCORDANCE, and it is better than the fabrication
argument: **the memo format destroys the denominator**, "rule of law (5/78)" and "born in the united
states (30/107)" both clear the ≥3 verifier floor and render as identical bullets. Article II is a FLOOR
check; it cannot see a denominator.

**WAVES S3 + S4: 15 hypotheses, 0 findings, and the cause is planning, not the system.** 9 of 15
BLOCKED before measurement on reference tables docs/12 assumed into existence: `elections.json` is 7 bare
dates (killed S3.2/S3.7/S4.5, one table, four hypotheses), `crisis-events.json` does not exist (S4.3/
S4.6), no retirement-date table (S3.3, billed as "the flagship backtest"), no historical committee
membership (S3.5). **S4.4 is the wave's best artifact and it is a REFUTATION**: the Friday Night Dump is
FALSE, 0.85×/0.96× against a ≥1.5× gate over 674,970 statements, with a positive control at 2.10×
proving the detector works. S4.2 died 3/3 and earned a protocol amendment: **the placebo must run against
the exact statistic in the headline** (it placebo-tested the blame RATE, headlined the outward SHARE, and
the share hits 100% on random non-shutdown dates). S4.1 is refuted by its own metric, ~97% nomenclature
because the case-name anchors ARE the selector, and median cross-party Jaccard 0.60 means the parties use
the SAME words.

**THE SUBSTRATE AUDIT, the remainder is in BETTER shape than two zero waves implied.** Of 18
un-adjudicated items: **8 RUNNABLE NOW**, 7 gated on one keyless CREC crawl, 2 on a trivial parse. **Two
FALSE BLOCKS**, the substrate landed while the ledger recorded it as absent: **S1.12**'s leadership
roster is ON DISK (156 dated bioguide-keyed rows, all 9 core titles for 113-119; mirrored 2026-07-16 by
the D3-A academic lane, **one day AFTER S1 ran and found the field null**), and **S5's "the key never
comes local" premise is obsolete**, GovInfo BILLSTATUS 113-119 is keyless and already local (332MB,
9,709 bills in 117-hr alone), so S5.2 runs with no key and no Actions. Also found: `presidents.json` has
no Bush term while the CREC data on disk is precisely 2001-2008, `chambers-control.json` covers only
113-119, and S5.2's floor is directly "≥Floor per cell", **a pre-registration that never registered a
number.**

**BUILT THIS SESSION (all dark, every flag False, 222 tests green at hand-off):**
- **1.7a The Duet** (`b9bd3c5`) + **1.7b phrase search** (`8ed87a5`), built/verified/UNRELEASED.
  The Duet's review produced **"verbatim != attributable"**: a press release is a MULTI-speaker document
  and `verify.is_verbatim` passes a colleague's quote BY DESIGN. Gate: `duet.attributed_to_other` checks
  the nearest attribution marker BOTH before and inside the span (reading only backwards passed the actual
  2026-06-30 text while silently accepting every trailing-attributed quote in the corpus).
- **§5.1 lane-1 enforcement moved INSIDE `find_duets`** (`32e99b8`), a comparative aggregator must not
  depend on its caller filtering. Bites in v2: the floor leg lands as Lane 2 and Bluesky is ~94% D.
- **The §1.4.1 gate as code** (`5dc963f`, `20ea633`), incl. an adjacency fix caught by simulating the
  next cron: without it a NO-OP day is hopped over and 07-13/07-15/07-16 reads as "three consecutive".
- A parallel session (Session 14) wired the same speaker gate into the LIVE citation path (`a1be954`),
  reusing `duet.py` rather than duplicating it, and improved on the brief: **demote the quote, never the
  citation**, so the gate in its structure cannot move a published number.

**RUNNING AT HAND-OFF: the CREC 2009-2026 Extensions crawl** (detached, keyless, $0, zero Anthropic
usage). Order is deliberate, **2013-2026 FIRST** because the calibration law makes the overlap the gate
for SD.1-SD.6; 2009-2012 follows. Pace is ~4h, not the estimated 11-13h (2013: 5,955 stmts; 2014: 5,780).
Log: `X:\onscript-data\crec\state\crawl-2009-2026.log`.
**Non-clobber note for whoever finds it:** `crec.py:217` OVERWRITES `crawl-stats.json` with only the
current run's stats, which would erase the parallel session's 2001-2008 record, so the driver snapshots
it to `crawl-stats-2001-2008.snapshot.json` first and writes a MERGED file at the end. A
`CRAWL-RUNNING.lock` names the PID/range/owner so a second crawler is a deliberate act. crec.py itself
was NOT modified (it is the other lane's file).

**Worktree note:** `../polispeak-v2` is left on disk ONLY because the running crawl imports from it. The
branch `v2-lane-b` is closed (fully merged, 0 ahead). Prune the directory once the crawl exits:
`git worktree remove ../polispeak-v2` (or `git worktree prune` after deleting it).

### Session 13c (2026-07-16, Fable), six rulings, all confirmed by Michael in-session

The three open construct rulings (#143, #146, #154) plus three earned by the day's measurements.
Recorded here verbatim; docs/12 carries A3+L1-L4; implementing sessions execute, never re-litigate.

- **R1 (#154, docs/12 A3 + L1-L4):** 22-28 CONFIRMED struck; the unit is CARDS (1-2/month through
  the midterms); lane isolation, substrate-before-spec, placebo-targets-the-headline, and
  numeric-floors are binding law. Nothing publishes from a pre-seam verdict until re-validated
  within-lane (S2.3 first, then S1.9/S2.9).
- **R2 (#143):** the "Author" CONSTRUCT is dead, measured as "first to type a bill's name" (Roy's
  31 = SAVE Act windows; top-12 flips to all-D-senators at low floors; 59% of members tie at zero).
  1.3 becomes **origination pages** (phrase -> first-seen-in-corpus member -> adoption curve,
  labeled as first-in-corpus, gated on the SPAN tagger). The member-level author score/leaderboard
  is DROPPED. **The Ventriloquism Award is KILLED, not repaired**, replaced by event-shaped,
  symmetric-by-construction weekly awards: **The Unison** (each party's largest single-day
  office-share phrase, denominator on its face) and **The Void** (the week's loudest silence, both
  directions, from 1.2). No member-shaming award survives Article X.
- **R3 (#146):** fix the VIEW, never the threshold. SYNC_MIN stays identical for both parties; the
  pooled top-20 becomes side-by-side per-party columns, every row carrying N-of-caucus (x%). The
  88%-D table was layout converting caucus size into rank.
- **R4 (The Script / 1.4):** ships as **THE CONCORDANCE**, every line "N of M offices" with
  receipts; no predictive/accuracy claim ever (the memo backtest refuted reconstruction ~90x and
  the memo format erases denominators: 5-of-78 renders identical to 30-of-107). Header amended:
  "Compiled from public statements. Every line counted, every count sourced. No memo was leaked.
  None needed to be." Gated on the SPAN tagger.
- **R5 (#145, Art. XIII):** IMMEDIATE manual suppression list at the display layer for the known
  private-citizen names, disclosed in the methodology corrections log; a principled person-name
  gate follows as its own reviewed build item. Execution = Opus lane, next session in the main
  tree. #145 stays open on the bus until deployed.
- **R6 (S4.7 posture, permanent):** no raw-volume comparative ever crosses the provenance seam ,
  January 6 above all (measured sign inversion: raw -69.9% vs lane-isolated +75.5%). Review-gate
  indefinite.
- **#119 (Michael's nod given):** Haiku extraction retired PERMANENTLY (§13 knob closed). The daily
  path has been deterministic in every live run; a model in the extraction path is cost plus a
  laundering surface for zero measured benefit. P1 stays in the repo as an archived, versioned
  artifact (prompts are public history, Art. VIII).
- **Launch-flip standard (confirmed):** the §1.4.1 evidence is `ops.unattended_streak()` reporting
  `passes: True`, never an Actions run status. The flip sequence (#131 -> #132) waits on that
  number.

## Next sessions / follow-ups (rewritten 2026-07-14, Session 4)

> **Session-5 update:** item 2 below (S2 hardening) is **DONE**, see the Session-5 entry (Wave-0 +
> the five review fixes, 55 tests). New priorities on top of the list below:
> - **Michael (decision, tasked #71):** the live LLM voice was never wired, greenlight wiring it
>   (turns on cents/day real API billing under your $10 cap) or launch on the accurate deterministic
>   voice. The site now discloses the deterministic voice truthfully either way.
> - **Launch checklist addition:** the dark-week hold is now the **`POSTING_ENABLED` repo variable
>   (default off)**, the primary, reliable gate, *not* the blanked passwords. At S3 launch, set
>   `POSTING_ENABLED=true` **and** replace the single-space `BSKY_*_PASSWORD` secrets with real app
>   passwords (a single space is truthy → it would attempt a failed login and fire the dead-man).
> - **Next Opus:** rebuild the corrupt local Alexandria ledger before the Archive/1.1 build; then
>   either wire the LLM layer (if greenlit) or proceed down the Build-Program queue (Wave 1).

1. **Michael, urgent (tasked on the bus):** blank `BSKY_BLUE_PASSWORD` + `BSKY_RED_PASSWORD`
   (deterministic dark week, prevents an accidental first post) and correct `BSKY_RED_HANDLE` →
   `red.onscript.news` while there. Then the S2 dark-week job: hand-audit 5 receipts/day across 3
   live runs + the attorney hour; first Monday 15-min ritual 2026-07-20.
2. **Next Opus session (S2 hardening, small):** (a) posting fix, assemble passes its own built
   `--day` to `post_bluesky` (kill the `collect-latest` coupling) + explicit `POSTING_ENABLED`
   gate (repo variable = the launch switch) + write post results into the assemble manifest with a
   dead-man alert on expected-but-absent posts; (b) promote the citation/era-fingerprint generators
   from scratchpad into `scripts/` (Art. VI); (c) About page lists the actual accounts (Art. XII)
   **and carries the operator-disclosure line (Art. X):** who operates it + a contact + "the
   operator's personal views appear nowhere on this instrument", Michael has no personal Bluesky,
   so both account bios point `Operator: onscript.news/about` and About is the disclosure of record.
   **Polish punch list (from the 2026-07-14 live-page editorial review):** (d) the index accuratey
   banner still renders the "not yet the production model / placeholder" copy while generators are
   `sonnet_batch`, condition that copy on dry-run generators only (the voice is live; the site
   under-claims); (e) **receipts are not visible on the public pages**, index and day page render
   zero member `.gov` citation links even though claims verify upstream; persist the Daily Lines'
   talking-point citations into the day JSON and render member·date·source rows under each line
   (wire in `citations*.json` where useful), Art. XII protection, S5 "receipts pages" spirit; (f) P2
   taste (the dark week's sanctioned tuning): composite quoted an ungrammatical sub-fragment
   ("who supports the … act's historic"), prefer maximal collapsed phrases for quotes; (g) the
   thin/quiet fallback line ("Today 51 of us released statements." full stop) should deterministically
   append the day's top synchronized phrase + count (code-computed, no LLM claim needed).
3. **S2→S3 launch (deliberate, gameplan §9):** after the §1.4.1 gate (3 unattended real runs) +
   Michael's audits: re-add passwords, flip `POSTING_ENABLED`, **flip repo public** (Art. XIV),
   announce. Launch is a decision, not a cron side effect.
4. **v2 (§10, by Aug 10):** silence detector (internal-baseline first, GDELT after), Authors-vs-
   Vessels raw-counts page (the amended S4), floor leg, The Script, awards, **Archive/Alexandria
   public release** (chapter renderer + coverage page + `passed==true` render filter). The
   credit-claim ledger (09 adopt-later) is now **unblocked**, `DATA_GOV_API_KEY` is set.
5. Deferred/non-blocking: Bluesky Lane-2 handle map (~130 members), incremental ledger merge,
   `theonscript.com` (decided: skip).

*(The pre-Session-4 follow-ups list is superseded by the rewrite above: launch errands done ,
domains, accounts, all 7 secrets, cap, and Alexandria done in Session 3; the Bluesky Lane-2 handle
map and incremental ledger merge carry forward as item 5.)*

## Session 16 (2026-07-17, Opus), L1 lane isolation: `date_source` is first-class, and the CONFIRM gate refuses the seam

Build order item (2) of the Session-13c rulings. Item (1), the #145 privacy deploy, landed in the
immediately-prior session (`fdcda1f`) which handed off on context and **left no BUILDLOG row**, this
is that gap noted, not filled; its commit is the record.

**Shipped.** `pipeline/search/provenance.py` (new), the deep archive's genre-isolation law
(`pipeline/deep/lanes.py`) applied to provenance: a measured lane registry, `SEAM = 2021-01-03`,
`LaneIsolationError`, `lane_of()` (raises on a mixed set), `spans_seam` / `assert_no_seam_span`
(for the single-window straddles), `assert_same_lane`. `harness.iter_statements` now emits
`date_source` + derived `instrument` and takes `lane=` to isolate at the source; `build_text_features`
carries the lane onto every feature row (**without this the fix dies again**, all seven S2
hypotheses read `text_features.jsonl` two layers below the harness and could not otherwise see their
own provenance). `metrics.confirms_in_both_halves` now takes **keyword-only `lane_a`/`lane_b` with no
usable default** and raises on an undeclared or cross-lane call.

**Verified on real data, not fixtures** (`scratchpad/l1_verify_real.py`): 688,820 records stream with
the lane attached, that is 688,839 minus precisely the 19 untagged records, which the pre-existing
`len(date)!=10` guard already drops, so no new rule was needed for them. Lane counts reproduce the
mirror precisely (legacy 485,948 / scraper 200,033 / page_html 2,839 → propublica 485,948 / scraped
202,872). The isolated `propublica` stream's last day **is** the seam, derived not asserted. The guard
accepts each isolated stream and refuses their union. **255 tests green** (was 243; +12, all
failure fixtures that first prove the pre-existing check passes the bad input, then prove the guard
fires). The daily pipeline is untouched and cannot be: `run_collect`/`run_assemble` do not import
`pipeline.search` at all, the §1.4.1 streak is not at risk from this change.

**Three findings that correct canon (evidence in `scratchpad/adv_partymix_pass1-5.py`, re-runnable):**

1. **Canon's party-mix numbers do not reproduce, and the sign is inverted.** `docs/13:413` (echoed at
   `CLAUDE.md:63` and `04-BUILDLOG.md:1284`) claims *"a 7.7-point shift in party mix (legacy D:R =
   1.538, scraper D:R = 1.12)"*. **1.538 is the legacy lane's TERMINAL YEAR** (116th 2nd session: D
   43,646 / R 28,378 = 1.5380, D-share 60.60%, matches canon's decode to 4 s.f.), mislabeled as the
   lane. The lane is **1.184**; half A is **1.176**. **1.12 is not reproducible under any nameable
   definition** (closest: 2023-only 1.135). Canon says half A is +7.7pt more D; the contrast it
   describes actually runs **half B +2.52pt more D, opposite sign**. **Canon's CONCLUSION survives
   and is well-supported**: over identical months (2013-2020) the lanes run **1.176 vs 0.937**
   (+5.67pt D-share), robust to office-matching (+5.32pt) and year-standardizing (+8.28pt). L1 stands;
   only the cited numbers are wrong. **Not corrected in `docs/13` by this session, that ledger row
   belongs to the `v2-lane-b` session (CLAUDE.md:59/61: only the session that ran a measurement writes
   its row). Reported to Michael for that session or Fable to enact.**
2. **The corpus is THREE lanes, not two.** Canon's "union of TWO datasets" omits `page_html` (2,839
   records, 2014-12-09→2026-07-09), scraper-collected but date-parsed from the page body, and **D:R
   12.47 in half A** (536 D / 43 R, 4 offices). A two-valued enum would have silently mis-bucketed the
   most party-skewed lane in the corpus. `date_source=='legacy'` ⟺ `scraper is null` ⟺ `source is
   null`, precisely, which is why the lane is recoverable at all.
3. **Canon names one drop; there are THREE.** `harness.iter_statements` (fixed) is one of three
   independent places `date_source` dies. **Still open:** `alexandria.load_congress_records`
   (`pipeline/alexandria.py:30-44`) → every `ledger-N/discipline-N/coverage-N` shard carries no lane
   tag, so every S1 phrase hypothesis reads lane-blind substrate (fixing it means a shard rebuild, ~3GB
  , its own session); and `wave_s4._collect` (`pipeline/search/wave_s4.py:53-96`), a direct mirror read.

**A RULING AN IMPLEMENTER must not SELF-AUTHORIZE (flagged, not taken):** fold-vs-isolate for
`page_html`. Folding it into `scraped` (this build's default, because it is the same instrument) moves
the same-era lane gap from **+5.67pt to +4.71pt**. Isolating it as a third lane makes the post-2021
corpus permanently "mixed"; filtering `date_source=='scraper'` silently drops it. The code supports
**both** (`lane_of(by="instrument"|"source")`) so the ruling changes which number is published, not the
architecture. **Fable/Michael to rule before any lane number is published.**

**Why the waves now raise, and why that is correct.** The pre-registered splits ARE the lane boundary ,
the 117th seats on 2021-01-03, so `A=2013-2020 / B=2021-2026` and `c<=116 / c>=117` are the same cut.
`confirms_in_both_halves` was therefore certifying findings **using the confound as its validation
split**; "replicates in both halves" meant "reproduces on two instruments", a weaker test than
advertised. Every un-migrated call site now fails loudly with a teaching error rather than returning a
confounded True. That IS the law ("MEASURE NOTHING NEW UNTIL IT LANDS"), and clearing it is item (3),
the 34 re-validations. `density_matched_subsample` matches **volume only** and cannot repair a lane-mix
change, it is false assurance for S1.1/S1.1'/S1.3'/S1.4.

**Triage inherited by item (3)** (full map in this session's recon): literal window straddles ,
`s1_10_bipartisan_season`'s 2020 post-window (2020-11-04→2021-02-01), **whose placebo is in its structure
blind to it** (odd years only); `s1_3_lifespan` (unbounded `min(first)`→`max(last)`); `s1_1_prime` /
`s1_3_prime` (the lane dropout injects a false >14d silence that severs a burst). Result-inverting ,
`s1_4_verbatim` (record-counted denominator vs member-counted numerator manufactures a "rise" landing
precisely on the seam, in the CONFIRM direction) and `s2_3_what_losing_sounds_like` (its own docstring
calls it a "RECENT-era (2021-26) effect", 2021-26 **is** the scraper-only lane; prime lane-artifact
suspect). Pooled A/B ratio as the headline, `s2_2_adjective_inflation`. **Lane-clean and safe:**
`s1_9_self_audit` (`congresses=(117,)`, scraper-only because of the design), which matters, because S1.9 is
one of the program's only two CONFIRMEDs. `_year_position_artifact` is **aliased with the seam**
(congresses seat in odd years; the legacy lane dies on an odd-year Jan 3), so each can mask the other.

**Traps written down so they are not rediscovered:** a `legacy` filter does **not** buy 2001-2021
coverage, 99.67% of the lane is 2013-2020 and its pre-2013 tail is 1,594 records that are **99.9%
Democrat** (D 1,592 / R 2); the `scraper` pre-2013 tail is the mirror image (~100% Republican). And
`CLAUDE.md:63`'s "the scraper lane starts ~2018 at 49 offices" is **loose**, it starts **2009-01-06**
and is merely tiny until ~2017; a filter trusting "~2018" silently admits 727 hyper-partisan records.

**Also this session (ops, not build):** the CREC 2009-2026 crawl was **dead**, not running. It died
with its parent session at ~22:25 local and left a stale `CRAWL-RUNNING.lock` naming a dead PID (9224)
, and the driver **aborts when a lock exists**, so the stale lock was itself the block. 2013-2019 raw
is complete (187/155/187/185/213/207/210 MODS files); it died inside 2020 at 18 of ~200 files.
Relaunched **detached under Windows Task Scheduler** (`OnScript-CREC-Crawl`, one-shot, no recurring
trigger) from `scratchpad/crec_crawl_2009_2026.py`, resuming at 2020; 2001-2008 record safe in the
snapshot (1,014 days / 38,325 granules). **The `v2-lane-b` watchdog cannot detect the crawler's death:**
its probe is a `python.exe` whose own command line contains the `*crec_crawl*` pattern it greps for, so
it always matches itself, which is the likely reason a prior session reported the crawl "alive and
healthy" while it was gone.

**Next:** (3) the 34 within-lane re-validations (order: S2.3, then S1.9/S2.9), now unblocked and
now *enforced*; the `alexandria` shard-tag rebuild; then (4) rulings-shaped 1.3/1.4/1.5.

## Session 17 (2026-07-17, Fable), consolidation: the outage, the history rewrite, Article XVI

Michael's directive: three parallel workers left him lost, consolidate, close strays, fix the
pipeline, fix the history, bake validation in so canon stops drifting. Fable's lane (governance +
repo surgery); the 34 re-validations and nomenclature wiring stay queued for Opus.

**THE OUTAGE (root cause, fixed).** Every scheduled run from 2026-07-16 22:29Z to 07-17 11:03Z
failed in 10-20 seconds: the #145 privacy gate (fail-closed, Art. XIII, correct) calls `load()` at
module import, and the `PRIVACY_SALT` secret it requires **was never set**, `fdcda1f` verified 243
tests locally, where the salt file exists, and never ran a cloud check. Worse, it failed **silently
for 14 hours**: the in-process dead-man (`ops.ntfy`) cannot see a crash that happens before any
pipeline code runs, and no workflow-level failure step existed. Fixed threefold: the salt set (piped
from the salt file, value never displayed; the canary self-verifies it), a **preflight step** in both
workflows that fails loudly when a required secret is absent, and an **`if: failure()` dead-man** at
the workflow level, which sees every failure mode including import-time death. Verification run
dispatched (29585706793), dispatch runs do not count toward §1.4.1; tonight's 19:30/21:30Z crons are
the first streak candidates, earliest accurate 3-green pass **Sat 07-19**, before the Monday ritual.

**THE HISTORY REWRITE (#161-as-described, executed).** Repo private, zero forks, the one moment
it is cheap. Method: extracted the two gated names from pre-`fdcda1f` blobs **by running the live
`privacy.is_suppressed` matcher over historical token n-grams** (the gate that suppresses them live
is the authority on what they are); a full object-database scan found 52 blobs carrying precisely 2
literal forms; `git filter-repo --replace-text` mapped each to its redaction label. **Proof:**
post-rewrite scan = **0 occurrences in 2,898 blobs**; **HEAD tree hash byte-identical**
(`84d1df16…` before and after, current content untouched); 164 commits preserved; 288 historical
revisions now carry the redaction label; 255 tests green. Force-pushed `main`, `wip/nomenclature`,
`data-latest`. The replacements file is deleted; the only place the names now exist is the
pre-rewrite mirror backup at `X:\onscript-data\backup\polispeak-pre-rewrite.git` (Michael deletes
after sign-off) and the raw corpus (see residual). Worktree cleanup rode along: `polispeak-v2`
removed (scratch evidence archived to `X:\onscript-data\evidence\polispeak-v2-scratch\`),
`polispeak-nom` worktree removed (**branch `wip/nomenclature` alive and pushed**), merged remote
branch `claude/friendly-bardeen-a6aa2d` deleted. **One tree, one writer is now literal: one tree.**

**RESIDUALS (filed on the bus, Michael's acts):** (a) GitHub retains unreachable pre-rewrite objects
server-side until GC, before the public flip, either a GitHub-support purge request or
delete-and-recreate the repo (old SHAs cited in this very buildlog would otherwise be fetchable
pointers to name-bearing blobs). (b) The release asset's raw mirror contains 11 member statements
that *mention* the names, members' own published .gov speech, so Art. XIII (privacy floor) and
Art. VI (raw immutable/rebuildable) pull opposite ways; queued for the attorney hour, leave raw
alone until ruled.

**ARTICLE XVI ratified (v1 → v1.1, per Art. XV).** The validation article, every lesson of the
last 48h made law: status codes inadmissible (the streak miscount), fail-closed ships with its key
(the salt outage), failure visibility at the outermost layer (the silent 14 hours), liveness is
data-not-process-match (the self-matching CREC watchdog), numbers enter canon with estimator +
reproduction script (1.538-as-the-lane; my own ratio-as-points error), session-end
expectation-vs-observation check (this consolidation exists because nobody ran one).

**Also:** BSKY_RED_HANDLE corrected to `red.onscript.news` (pre-flip list item, public string).
CREC crawl healthy under the Task Scheduler, past the seam (2020: 224 files, 2021: 223, 2022
running). BCAD/Assessment-Commons response filed on that project's bus (not OnScript work).

## Session 18 (2026-07-17, Opus), revalidation (docs/17): the runnable 34, re-measured within one lane

Build-order item (3) of the Session-13c rulings, governed by `docs/17-REVALIDATION-BRIEF.md`. Ran the
runnable half of the 34 pre-seam verdicts inside ONE provenance lane, on the brief's pre-registered
within-lane halves. **Nothing published changed** (the Search does not touch the daily pipeline); the
deliverable is corrected verdicts + a lane-clean measurement path.

**Headline: the seam overturned zero runnable verdicts, and hardened the two that matter.**
- **S2.9 (the Boogeyman) is now genuinely twice-confirmed**, CONFIRMED in the propublica lane on its
  own split (half A 4/4 + half B 4/4) AND in the scraped lane on its own split (3/3 + 3/3). My
  reimplementation (S2.9 had NO code in the repo, only the finding card survived a fan-out) reproduces
  the original 14/14 precisely as propublica-8/8 + scraped-6/6 across the old seam split, which is the
  faithfulness check before trusting the lane split.
- **S1.9 (the 2022 Self-Audit) re-affirmed**, CONFIRMED whether the 144 legacy 2021-01-03 records are
  in or out (D 0.00176 vs R 0.00095, 75/105 weeks, identical both ways). Corrected the brief: "lane-clean
  because of the design" is 99.6%, and the exclusion is a measured no-op.
- **S2.3 (the flagship reversal) stays REFUTED in BOTH lanes, well-powered in every cell** (smallest
  5,520 vs a 200 floor). Reproduced the original seam-spanning arms precisely first (pooled 2013-26 gate
  PASS → looked CONFIRMED; both-halves gate FAIL → REFUTED), then showed both lanes independently
  REFUTE. **The kill was not plumbing**, the ledger's proof-that-the-control-works survives, though the
  control was weaker than advertised.

**Full S2 wave re-run within lanes:** 7 of 8 verdicts identical across both lanes. The one move, **S2.7
Pronoun Economics CONFIRMS inside propublica only** (both parties I/(I+we) declining 2013-16 and 2017-20)
but REFUTES in scraped, is a single-lane result that does not replicate, so it is a reversal candidate
needing re-pre-registration, NOT a finding card. The lane split of `text_features` sums precisely to the
pre-seam totals (concern ladder 39,249/5,808/650/2,084), the migration's correctness proof.

**S1.4 (verbatim) REFUTED both lanes; the "D copy-paste rose in both halves" sub-claim does NOT survive
lane isolation** (within each lane D rises in half A then falls in half B, the apparent both-halves rise
was the 2013-2020→2021-2026 instrument change). Its density-controlled `_proper` arm is BLOCKED-ON-SHARDS
(`load_congress_records` is lane-blind). **S1.10 ARTIFACT holds**, after dropping the seam-straddling
2020 cycle, the placebo still troughs 7/7 → seasonal-not-electoral is robust, not a seam artifact.

**S4 set:** fixed `wave_s4._collect`'s `date_source` drop (it reads the raw mirror directly), every
matched statement now carries `ds`/`inst`. This surfaced that **S4.1's half-A SCOTUS cases are ~95%
propublica + a 5% scraped tail** (mixed-lane; half-B cases are clean scraper-only), so per-case
DESCRIPTIVE needs half-A isolation and the aggregate A/B reversal is the seam (already UNDERPOWERED,
half B 5<8). S4.2 stays REFUTED (died on placebo methodology, not the seam). **S4.4 stands and is
arguably strengthened**, its half A (2013-2020) IS the propublica lane and half B (2021-2026) IS the
scraper lane, so its 0.85×/0.96× equivalence is a within-lane null measured once per instrument.

**Code (migrate call sites as re-run, docs/17 §4.4).** `wave_s2.py`: removed module-level seam-spanning
`HALF_A/HALF_B`; added `LANE_HALVES`/`halves_for`/`load_rows(lane)` (rejects a pre-L1 cache loudly);
every entry point is `*, lane[, halves]`; `run_all()` returns `{lane: [...]}`. `wave_s1.py`: `lane=` on
`s1_4_verbatim`/`s1_9_self_audit`/`s1_10_bipartisan_season`, `LANE_YEAR_HALVES`, seam-cycle drop.
`wave_s4.py`: `_collect` carries `ds`/`inst`. Re-runnable scripts committed under **`scripts/search/`**
(NOT scratchpad, see below): `revalidate_s2_3.py`, `revalidate_s1_9_s2_9.py`, `revalidate_s2_wave.py`,
`revalidate_s1_4_s1_10.py`. Ledger rows appended (docs/13, `supersedes` named). **259 tests green** (+4
provenance).

**Two discrepancies filed against canon (docs/17 §7):**
1. **`confirms_in_both_halves` is unreachable from production.** The Session-16 L1 CONFIRM gate is
   called only by tests, every wave module (S1 and S2) hand-rolls both-halves via `M.split_direction`,
   which has no lane guard. So an un-migrated wave site fails **silently** (lane-blind numbers), not
   loudly as docs/17 §4.4 assumed. This session made the S2 + runnable-S1 sites' isolation real via
   `load_rows`/explicit halves; the BLOCKED-ON-SHARDS sites are still un-migrated and must not be
   trusted until the shard rebuild reaches them.
2. **The `scratchpad/adv_partymix_pass1-5.py` evidence cited in CLAUDE.md (Session 16) is UNTRACKED** ,
   the whole `scratchpad/` tree is gitignored, so those re-runnable scripts vanish on a re-clone, which
   Art. XVI calls prose. This session put its re-validation scripts in tracked `scripts/search/`.

**BLOCKED-ON-SHARDS (not re-run, per docs/17 §3):** S1.1, S1.1′, S1.2, S1.3, S1.3′, S1.5, S1.6, S1.7,
S1.8, S1.11, S1.4-proper, they read alexandria ledger/discipline/member/daily shards, which are
lane-blind until the ~3GB shard lane-tag rebuild (its own session, docs/17 §6). Classifying them BLOCKED
rather than re-running on lane-blind substrate is the discipline, not a gap.

## Session 19 (2026-07-17, Opus), the shard lanes (docs/18): the eleven unblocked and two new CONFIRMED

Build-order step (4), governed by `docs/18-SHARD-LANES-BRIEF.md`. Gave the alexandria shards a lane
dimension, made the harness lane-aware, and re-validated the eleven BLOCKED-ON-SHARDS S1 items within
one provenance lane. Nothing published changed (the daily pipeline does not import alexandria; merge()
and the combined shards are untouched).

**THE HEADLINE: two new within-lane CONFIRMED, and lane isolation is what MADE them confirmable.**
S1.1' (ignition width) and S1.3' (burst lifespan) were REFUTED across the 2013-2026 seam split, the
post-2021 plateau broke their monotone gate. Isolated to the propublica lane (2013-2020) on the
brief's pre-registered within-lane halves, the SAME hypotheses and the SAME gates CONFIRM:
- **S1.1' CONFIRMED**: ignition width 34d (2013) -> 3d (2020), an **11.3x speedup**, declining in both
  within-lane halves, **survives the density control**, no sawtooth. The memo industrialized ~11x.
- **S1.3' CONFIRMED**: burst lifespan 55.5d -> ~15d, **37% drop**, both halves declining, density-survives.
- Both are **ARTIFACT/absent in the scraped lane (2021-2026)**, so the "Great Intensification" is a
  real 2013->2020 phenomenon that **STOPPED at the seam**. The program's CONFIRMED tally moves from 2
  (S1.9, S2.9) to **4 pending publication review** (S1.1'/S1.3' are REFUTED->CONFIRMED movements; the
  within-lane halves were pre-registered in docs/18 §5, so it is not a p-hacked reversal, but a
  REFUTED->CONFIRMED card still needs Fable + neutrality review, and the density control's caveat ,
  count-matched, not statement-density-matched, must be disclosed).

**Zero verdicts flipped toward a false positive across all 22 (11 items x 2 lanes).** The rest: S1.1/S1.3
stay ARTIFACT in BOTH lanes (proving the odd/even congress-boundary sawtooth is a per-shard artifact
INDEPENDENT of the seam); S1.2/S1.5/S1.7/S1.8/S1.11 REFUTED-stand in both (S1.2 also surfacing the 2017
sync-ceiling peak within-lane; S1.6 REFUTED-powered in propublica confirming pre-election tightening is
a RECENT-cycle effect); S1.6-scraped and S1.4-proper (both lanes) accurately UNDERPOWERED, the
congress-split gate needs >=3 congresses/half, which no single lane has (cf. S3.6, an unmeetable T1 gate).

**Shipped.**
- `pipeline/alexandria.py`: `run_shard(n, lane=)`, `load_congress_records(n, lane=)` filter records by
  `provenance.instrument_of` BEFORE normalize (the 3rd and last place `date_source` died). Per-lane
  shards live in `ALEX/lanes/`, a subdirectory ON PURPOSE: a flat `ledger-113.propublica.json` matches
  merge()'s `ledger-*.json` glob and would double-count + choke its `int(stem.split("-")[1])` manifest
  parse; the non-recursive glob never descends into `lanes/`. `lane=None` is byte-identical.
  `reconcile_lane_shards()` for the §3 acceptance.
- `pipeline/search/harness.py`: every builder takes `lane=` and writes a lane-suffixed cache (so a
  scraper-only half can't be normalized against an era-pooled baseline, the S1.5 triage bug);
  `bioguide_states` stays pooled (identity map). Added `_iter_jsonl_rows`, the jsonl readers now skip a
  corrupt line with a loud warning instead of crashing all hypotheses (see the corruption note below).
- `pipeline/search/wave_s1.py`: all eleven items lane-migrated (`_half` requires halves; year-halves for
  phrase/series, congress-halves for S1.11/S1.4-proper; S1.3' takes the lane cutoff so a propublica
  burst alive at 2021-01-03 is censored, not counted short). `s1_4_proper` now reports UNDERPOWERED (not
  a false REFUTED) when its congress-split gate is unmeetable in-lane.
- `scripts/search/`: `validate_lane_shards` (fast pre-build correctness), `build_lane_shards`
  (resumable, PYTHONHASHSEED-pinned), `revalidate_s1_shards` (the analysis driver, cache-skipping,
  lane-merging). Evidence re-homed to `scripts/search/evidence/` + `scripts/ops/history-rewrite/` (all
  10 verified name-free against the live privacy gate; the rewrite tools print only hashes).

**Acceptance (docs/18 §3), all PASS.** All 7 congresses reconcile precisely: records(propublica) +
records(scraped) == records(combined), **0 statement delta, 0 cross-lane id-dups** (c113 92,895+1,681;
c116 145,026+15,863; c117 144+36,773; c118/c119 0+all, propublica is EMPTY post-seam, the seam on
record). `run_shard(n, lane=None)` is content-deterministic and leaves the live combined shards
untouched. 107-112 per-lane loaders RAISE. **263 tests green** (+8 shard/reader failure fixtures).

**Two things worth keeping on the record.**
1. **The §3.4 "byte-identical" acceptance was reframed.** The on-disk combined shards are a STALE
   baseline, the ledger's dict/daily key order is per-PROCESS randomized (via `_doc_ngrams` returning a
   set, iterated under PYTHONHASHSEED), so re-running produces different bytes from identical DATA
   (discipline/coverage are order-independent aggregations and DO match). It is harmless to analysis
   (the Search readers stream all entries, order-invariant) and pre-existing (not introduced here); the
   accurate test is determinism + combined-path-invariance + live-shards-untouched, all verified.
   PYTHONHASHSEED=0 pins the per-lane shards for reproducibility.
2. **A file-level cache corruption crashed the first both-lanes run and was hardened against.** A raw
   control byte appeared in `phrase_index.scraped.jsonl` at line 796,225 (an unescaped 0x11 inside a
   `first_date`) under concurrent X: I/O (the completion build + the analysis both hammering the
   junction). Proven NOT a data/code fault: `json.dumps` always escapes control chars, and the
   scraped-119 LEDGER has ZERO control-char dates, so a rebuild produces a clean file (it did). Fix:
   rebuilt the scraped caches clean AND hardened the jsonl readers to skip+warn on a bad line (one
   corrupt byte in an 800k-line rebuildable cache must degrade an analysis by one row, not kill it). The
   propublica caches were scanned clean (0 control chars across 2.09M phrase-index lines), so the
   CONFIRMED findings rest on good data.

**NEXT (build order 5):** nomenclature wiring (branch `wip/nomenclature`; wire `tag()` BEFORE distill;
`nomenclature_rate` in the nightly audit; adversarial review; merge), then rulings-shaped 1.3/1.4/1.5
(SPAN-gated, behind the nomenclature merge). The S1.1'/S1.3' CONFIRMEDs await Fable/neutrality review
before publication. The alexandria shard rebuild the re-validation needed is DONE, the
BLOCKED-ON-SHARDS half of the 34 is now re-validated.

## Session 21 (2026-07-18, Opus), nomenclature wiring, the connective-cluster P0 fix, and the §4 rider

Executed `docs/19-NOMENCLATURE-WIRING-BRIEF.md` (Fable, Session 20) in full. Rebased `wip/nomenclature`
onto main (one `.gitignore` conflict: kept both the privacy and nomenclature re-include blocks); the
21 tagger fixtures + full suite green on the rebased branch before any wiring. **304 tests green at
close (was 263 on main; +41).** Flag renamed to the brief's name: `FEATURES["nomenclature_tags"]`
(the branch's `nomenclature_tag` singular disagreed with docs/19 §2/§7 + CLAUDE.md, the binding docs win).

**§2 WIRING (all DARK behind `nomenclature_tags`, default off):**
- **§2a MEASURE, UNCONDITIONAL (does not read the flag).** `ops.symmetry_report` now carries
  `nomenclature_tagged/total/rate` per party (denominator = the day's FULL synchronized set, not the
  truncated top-20, so a 103-D/15-R display skew can't masquerade as an asymmetric tag rate).
  `thresholds_sha` folds `NOMENCLATURE_RATIO_MIN` + the index version ONLY when the flag is live (dark
  ⇒ every historical day's fingerprint is byte-unchanged). Measurement changes the audit JSON, never a
  rendered surface.
- **§2b SITE display-time (flag-gated).** `nomenclature.tag()` at RENDER time in `sync_table` (the
  flagship day table) and `phrase_page_body`, tagging COPIES so a dark render can never see a stale key
  from a live one; the `_nomenclature_chip` shows "official name · HR1" / "committee name" with a
  cite tooltip. Fixes every historical page with no ledger rebuild.
- **§2c DAILY pre-distill (flag-gated).** `distill.build_stats` annotates a talking-point key that is an
  official name; `_compose_llm` appends a runtime clause telling the voice not to present a bill title
  as coordination, runtime-appended so the committed P2/P3 files (and `prompts_sha` over them) stay
  byte-stable dark; `prompts_sha` discloses the clause hash when live.

**§3 ACCEPTANCE:** 21/21 fixtures + full suite green (§3.1); the verdicts re-derivation reproduced the
spec anchors precisely on the current corpus (sync 461,501, covered 14,175, histogram identical, the
local corpus is frozen at 75,757 so it is a determinism proof) (§3.2); KILL/PROTECT re-verified both
directions by the fixtures (§3.3); `test_nomenclature_wiring.py` locks flag-off = zero public bytes and
flag-on = tags appear + nothing deleted (§3.4).

**§4b THE CONNECTIVE-CLUSTER DEFECT (P0, the launch-flip blocker), FIXED, always-on (a correctness
fix, NOT the dark feature):**
- **req 1, `boilerplate.is_scaffold_key`**: a deterministic, party-blind key-admission gate. Rejects a
  key that terminates before its object (trailing function word or possessive, straight+curly) or is an
  attribution frame ("colleagues …"). Both live 07-17 defect keys die; the birthright-06-30 flagship and
  the R OBBBA flagship survive. Wired alongside `is_weak_label` at `run_assemble.py:166`.
- **req 2, key-span-gated family quorum**: `verify.key_carrying_units`/`verify_talking_point` now count
  only distinct `joint_group or bioguide` families whose SOURCE actually carries the cluster key (via
  the new `boilerplate.contains_gram`, matched on the tokenizer so punctuation never hides a real gram).
  This independently kills both live clusters (the transitively-chained interlopers, Booker's flood
  bill, Krishnamoorthi's Blanche, Rosen's different-wrapper, drop out) while the 53-family flagship is
  untouched. `_citations` filters to the SAME key-carrying set, so a published cluster's receipts all
  contain the phrase and never thin below 3.
- **req 3, receipt display**: `receipts_strip` highlights the exact key span in each quote
  (`_mark_key`, punctuation-tolerant) and shows a per-test chip row (message-key · N families · phrase
  shown x/y · sourced y/y) instead of one opaque badge.
- **req 4, audit + retroactive correction**: `scripts/audit_connective_keys.py` found **19 inadmissible
  talking points across 7 of 10 published days, both parties (D 15 / R 4, party-blind gate, the skew
  tracks the caucus)**, the defect is systemic, not a 07-17 event. `daily_line_panel` drops scaffold
  talking points at render (the display-time refresh idiom); a dated corrections-log entry discloses it.

**THE ADVERSARIAL REVIEW (docs/19 §5) confirmed the four hard invariants HOLD** (tag-never-deletes;
flag-off = zero public bytes on every rendered surface + both fingerprints; citations never mutated or
thinned below quorum; party-blind) and caught **one P1**, now fixed: the render filter dropped the
receipts but LEFT the stale Sonnet composite, so 07-17 D would have narrated the three interloper
phrases over "nothing cleared the threshold", an Art. II fabricated silence. FIX: the render-time
correction (`privacy_correct_line`) now ALSO drops scaffold keys and RE-DERIVES the composite from the
surviving stats via the deterministic composer (the exact trusted degradation path privacy uses), a
distinct "readmitted" state (never the privacy claim), an accurate scaffold-specific empty message, and a
banner note. Verified on the actual 07-17 D: interlopers gone, generator=deterministic, no false
threshold line. Also fixed: P3 (`_mark_key` now comma-tolerant), test hygiene (a symmetry test had
clobbered real derived data, monkeypatched `write_json`, restored the files), the 07-14 privacy golden
updated (its "…committee markup of the" is a fragment §4b correctly drops now). P2 (the gate rejects any
trailing stopword, broader than the brief's "possessive/preposition") KEPT as a conscious conservative
choice, a missed line is cheaper than an admitted scaffold key (docs/19 §4b); the refinement
(scaffold-aware key SELECTION, so a real cluster keeps a better key instead of dying) is a named
follow-up.

**§4 THE ROBUSTNESS RIDER, all three nomenclature-exposed CONFIRMEDs SURVIVE tag-stripping** (ledger
row in docs/13; results `data/derived/search/revalidate_nomenclature_rider.json`). S1.9 holds (D>R in
68% of weeks stripped, ≥60% gate); S1.1' ratio ROSE 11.33→12.0; S1.3' drop ROSE 0.373→0.381, removing
the 364/25188 (1.4%) nomenclature phrases SHARPENED the intensification, so it is not a bill-title
artifact. S2.9 exempt. This clears the §4 gate on the Aug/Sep drip pieces (docs/20). Mechanism:
`_fivegrams(strip_idx=…)` + `name_spans`/`classify_occ`; `scripts/search/revalidate_nomenclature_rider.py`.

**§4c riders:** per-post AI-composite marker now on EVERY post unit (was dry-run-tail-only, a LIVE post
carried no marker at all; `post_bluesky.build_thread`), sized so the marker never overflows 300 chars.
The clause-ablation test, the "observed publishing member" R3 denominator definition, and the
first/observed/earliest-in-lane timestamp distinction are QUEUED (named follow-ups; the first two are
pre-v2-Concordance requirements).

**MERGED DARK to main, flag off (the flip is Michael's).** Per-member ingest-health flags (§2a) and the
phrase-page/archive-fingerprint tag surfaces beyond the day table are minor follow-ups (the day table is
the flagship where the defect lives). Nothing published changed except the §4b always-on correctness fix
(the 19 inadmissible talking points drop + the receipts gain chips + affected composites re-derive
deterministically) and the corrections-log entry.

**SECOND-PASS REVIEW folded in (docs/19 amended by Michael/Fable mid-session as `df6e2d6`; my commit
sits on top of it):** (1) **stable rejection reason codes**, `boilerplate.scaffold_reason` returns
`REJECT_ATTRIBUTION_FRAME` / `REJECT_INCOMPLETE_SYNTACTIC_SPAN` (attribution checked first, the deeper
reason), `is_scaffold_key` a thin boolean wrapper; the audit now CATEGORIZES (18 incomplete-span, 1
attribution) not merely counts, and writes a **rejected-candidates log** (`data/derived/search/rejected_cluster_keys.json`:
reason + would-have-been reach, the accurate false-negative view for a conservative gate). Both
directions are covered: the audit is the BACKWARD view over published days, and `run_assemble` now
emits the FORWARD view, every generation-time drop is reason-coded (`_reject_reason`) and written to
`day_json["rejected_keys"]` per party, with an Art. XIII guard that never logs a private-name label.
(2) The
receipt **aggregate is a derived CONJUNCTION**, "publication verified" iff every check passes, else
"verification unavailable"; deliberately NO reduced-confidence middle. (3) **Support-graph validity**
(the hardened clause-ablation rider) QUEUED in docs/11 §4 as a pre-v2-Concordance requirement, the
free-text voice can't bind clauses to cluster ids cheaply; the Session-21 render-time re-composition
(drop the cluster AND re-derive the prose) is the interim "no proposition outlives its evidence"
guarantee. **Session-close evidence (Art. XVI):** the two named 07-17 clusters die for the correct
deterministic reason (possessive → incomplete-span; colleagues → attribution) · a known-good cluster
survives · family collapse runs before quorum on the publication path · spans highlighted on every
receipt · chips independently computed · the all-days audit ran over the local archive with failures
categorized · affected pages re-derive at render · the live page no longer shows the known-invalid
interpretations. The **human sample audit of admitted AND rejected clusters folds into the #129
dark-week ritual** (artifact: the rejected-candidates log), Michael's, not a build act; #129 not
re-filed.

Streak read from the record: **2/3** (07-16, 07-17
clean unattended), earliest §1.4.1 pass Sat 07-19, consistent with docs/19 §0.

## Session 22 (2026-07-19, Opus), build-order 6 begins: 1.3 origination (R2), SPAN-gated + floored, dark

First increment of the rulings-shaped 1.3/1.4/1.5 (docs/21 §3.2, Opus implements to R2/R3/R4, the
release flip stays Michael's). Built the **1.3 origination core**, DARK behind `FEATURES["authors_vessels"]`.
The retired author leaderboard (#143) was three confounds at once, tenure, chamber, and nomenclature
("Chip Roy authored the SAVE Act" = a member typing a bill's name first). The live phrase page still
made the raw claim ("First said {date} by {member}") for every phrase, bill titles included. R2's
redesign, now implemented as `site._origination_line`, makes a per-phrase origination claim ONLY under
three controls: (a) **SPAN**, a nomenclature phrase (via the committed `is_nomenclature` tables, usable
while the display tagger is dark) gets NO authorship claim, just "first recorded"; (b) the **#143
coordination floor** (`ORIGINATION_PEAK_FLOOR=15`), below it, first-use is a chamber artifact, not
origination; (c) **born-coordinated**, multiple day-0 first-sayers means no single author. Flag OFF ⇒
the phrase page is byte-identical (a locked test), so nothing on the live site changed and no re-render
was needed. 6 new tests (`tests/test_origination.py`), **310 green**. NOT built yet (future increments):
a dedicated origination surface / the phrases-index treatment, 1.4 The Concordance (R4), 1.5 The Unison
+ The Void (R2). The `authors_vessels` flag name is kept (the 1.3 slot) though the construct it once
named is dead, noted in the code. Streak unchanged (2/3; the 07-19 cron had not landed a day-07-18
manifest at session time).

**R3 / #146, per-party side-by-side columns (the second build-order-6 increment), DARK behind
`FEATURES["party_columns"]`.** The pooled `collapse_and_rank(rows, k=20)` ranks by raw peak and
truncates, so the larger caucus in its structure fills the flagship table, measured **20 D / 0 R on
2026-07-15** (100% D), a live Art. IV instrument asymmetry, not a finding. R3's fix goes in the VIEW,
never the threshold (SYNC_MIN untouched): `build.top_synchronized_by_party` gives each party its OWN
top-k ranked WITHIN the party, and `site.party_columns_table` renders two columns with an N-of-caucus
denominator on every row. `run_assemble` writes `day_json["sync_by_party"]` every day (build-dark), so
the flip is a pure release act; the render falls back to deriving per-party top-k from the stored pooled
top-20 for historical days written before the field existed (**bounded pre-flip limitation**: a minority
column can read empty if that party's phrases were truncated out of the pooled top-20, new days carry
the full per-party set). Flag OFF ⇒ the day view is the current pooled `sync_table`, byte-identical (a
locked test), so nothing live changed and no re-render was needed. 5 tests (`tests/test_party_columns.py`),
**315 green**. The full per-party columns need `sync_by_party`, which only new days accrue, so the fix
is complete going forward and degrades accurately on old days. NEXT: 1.4 The Concordance (R4, per-MEMBER
on-script index, a new data layer, the existing discipline index is per-party-per-day) and 1.5 The
Unison + The Void, each a substantial feature.

## Session 23 (2026-07-19, Opus), build-order 6 cont.: 1.4 The Concordance (R4), the per-member on-script index, dark

The third increment of the rulings-shaped 1.3/1.4/1.5. Built **The Concordance**, the per-MEMBER
on-script index, DARK behind `FEATURES["concordance"]` (the 1.4 slot; the unused pre-ruling `the_script`
key was renamed to match R4). The existing discipline index is per-party-per-day; it is its per-member
extension: of a member's SOLO (non-joint) Lane-1 releases, the share that used a phrase their party
genuinely converged on. `build.build_concordance(statements, ledger)` writes `derived/concordance.json`
EVERY run (from `deterministic.run`, wrapped skip-and-log so a dark feature can never crash RUN A), like
`day_json["sync_by_party"]`, so the flip is a pure release act. It reuses the engine's own tokenizer
(`phrases._doc_ngrams`) so the intersection with the ledger is exact, and is a pure function of
`(statements, ledger)`, rebuild reproduces it.

**R4's shape, enforced in its structure.** (a) **Denominators on every line**, every score carries its raw
`(on_script / statements)` counts, in the data and on the page. (b) **SPAN-gated** ,
`nomenclature.is_nomenclature()` drops official-name occurrences per the statement's congress (a member
typing a bill title is never "on-script"), degrading to a no-op where no verdicts table exists. (c) **No
predictive claim**, the page states, before any number, that it is descriptive OVERLAP, not
motive/direction/influence.

**Inherited R2/#143 controls.** Joint/co-signed releases are EXCLUDED (coordination, not solo voice). A
**naming floor** (`CONCORDANCE_MIN_STATEMENTS=10` solo statements) so there is no swarm of tied-at-zero
"vessels", below-floor members are disclosed in aggregate, never scored. The **Art. XIII privacy floor
+ the same display-time boilerplate/weak-label guards `top_synchronized()` uses** are applied to the
phrase set, so a suppressed private-name phrase can never count toward on-script nor surface as a receipt
(the raw ledger.json still holds it; suppression is a render-time act, #145). **≥3 dated receipts per
named member.** Party set = the two composites (D/R), matching every other cross-party metric.

**THE SATURATION FINDING + the coordination floor (`CONCORDANCE_PEAK_FLOOR`).** The first real-data run
exposed the metric saturating at ~1.00 for EVERY member: over a wide window the raw kept set is tens of
thousands of phrases, so nearly every release shares SOME 3-member-co-used 3-6gram (member names/titles
like "durbin d-il ranking member", agency names, generic language like "make life more affordable"), a
misleading Art. IV artifact (everyone reads as a total vessel), the same confound family #143 killed. Fix
= the same control Session 22's origination used: a phrase counts as "the party script" only if it
coordinated at scale (`peak_units >= floor`). **Measured** the named-member index distribution across
floors on a real 45-day window (6,143 statements, 41,032 raw phrases): `0 -> mean .99, 91% saturated at
>=.99` · `10 -> .63` · `15 -> .32, IQR .18-.43, 0.5% saturated / 5.5% zero` · `20 -> .20, 14% zero` ·
`30 -> .04, 64% zero (only 10 phrases, starved)`. **15 discriminates without starving and matches
`ORIGINATION_PEAK_FLOOR`**, default set there, disclosed/movable. At the default the distribution spreads
both parties across the range (Thanedar D 14/14 → Hernández D 0/40; Thune R 16/29 → Van Drew R 0/12);
names resolve via the roster (210/210); the span gate removes 52 on-script credits.

**Render** (`site.concordance_body`, dark): both parties side by side, ranked within party (a reference
INDEX, not the single-winner leaderboard / Ventriloquism Award that #143/R2 retired), every row its raw
counts + expandable receipts, with the no-motive caveat + window + name-index-version + coordination floor
+ joint-exclusion all disclosed on the page. Written to the site ONLY when the flag flips (built dark =
absent from output, the `phrases/search.html` rule); the Methodology gains a gated "How it is measured"
section; the nav link is gated. Flag OFF ⇒ zero public bytes change, locked tests: nav link absent,
`methodology_body()` byte-identical. **14 new tests (`tests/test_concordance.py`), 329 green.**

**RESERVED for Michael at the flip review (NOT self-authorized).** The flag flip itself; the
`CONCORDANCE_PEAK_FLOOR` (15) and `CONCORDANCE_MIN_STATEMENTS` (10) defaults; and the FRAMING, the dark
render is a neutral within-party-sorted reference table with heavy no-motive caveats; whether to promote a
"most on-script member" headline (the leaderboard framing R2 was cautious about) is a publication
decision, not a build one. Two measurement definitions were matched to the existing discipline index
rather than invented, and are flagged for review: "on-script" counts a phrase synchronized by EITHER party
(own-party-only is a possible tightening), and it counts a phrase used any time it is in the kept set (not
only on its synchronized day), both are precisely the existing discipline-index semantics the user asked to
extend. A further distinctiveness filter (df_weight) on the receipt phrases is a possible refinement (a
few floor-clearing phrases are generic-but-viral, e.g. "signed into law").

NOT built (future increment, its own session): **1.5 The Unison + The Void** (R2). Streak unchanged.

## Session 24 (2026-07-19, Opus), build-order 6 cont.: 1.5 The Unison + The Void (R2), the symmetric weekly awards, dark

The fourth and final increment of the rulings-shaped 1.3/1.4/1.5. Built **The Unison + The Void**, the
symmetric weekly awards that R2 substituted for the KILLED Ventriloquism Award (docs/04 R2 ruling:
"most on-script MEMBER" is dead, 318/538 tie at zero solo count, and naming a "vessel" is a
chamber/tenure/nomenclature confound and an Article X member-shaming construct). Both awards are
PHRASE-/TOPIC-level, never member-level, and symmetric because of the design. Behind `FEATURES["awards"]`
(the 1.5 slot / A9; default off, the flip is Michael's one commit). `build.build_awards(statements,
ledger)` writes `derived/awards.json` EVERY run (from `deterministic.run`, wrapped skip-and-log like
concordance so a dark feature can never crash RUN A); only `site.awards_body` is gated, so the flip is a
pure release act. Pure function of `(statements, ledger, [silence boards on disk])`; rebuild reproduces
it bar `generated_at`.

**THE UNISON, each party's largest single-day office-share phrase over a trailing 7-day window.**
office-share = a party's offices that used one exact phrase in a SOLO release that day ÷ its offices that
published ANY solo release that day (the denominator on its face). The numerator comes from the ledger's
`members_{party}` list (joint markers already excluded by the engine's unit key), INTERSECTED with the
day's active-solo-office set computed from `statements` with the exact same filter (`lane==1`, not
syndicated, not joint), so the numerator is a subset of the denominator because of the design and the share is
always in [0,1]. R2's controls are structural: **SPAN-gated** (`nomenclature.is_nomenclature` per the
day's congress, a bill title reaching high office-share is "everyone named the bill," not a message
unison, the #143 control; degrades to no-op with no verdicts table); **privacy + display-boilerplate /
weak-label filtered** precisely as the public sync table; **joint/co-signed releases excluded** from the
office population; **both parties scored by one rule**, Independents not in the composites. The numerator
IS the coordination magnitude, so, unlike the Concordance, **no phrase-peak floor is needed** (a winning
share already implies many offices). Ranked within party; the #1 row is the award, runners-up shown for
context.

**A real-data finding fixed before it shipped: near-duplicate fragment clutter.** The first real run
showed the D column as "united states of" AND "the united states of" as two separate top rows, the same
stopword-padding/sub-gram family the flagship table already collapses. The Unison now reuses the flagship
`collapse_and_rank` machinery (each phrase reduced to its single best day first, then padding/sub-gram
families folded, `day_peak = offices_using` driving the collapse magnitude) so it can't regress what the
public table fixed. Re-measured clean.

**THE `UNISON_MIN_ACTIVE` FLOOR, measured, not guessed.** A `(party, day)` is eligible only with ≥ this
many active solo offices, so a thin holiday can't take the award on a 2-of-3 share. **Measured** on the
real corpus (week 2026-07-03..09, 1,723 statements → windowed ledger 9,817 entries): active solo
offices/day is **bimodal**, normal weekdays **40–112 (D) / 24–77 (R)**, median 47/36, versus a thin-day
cluster **≤17** (July 4th D=17/R=10, the 5th D=1/R=3, weekends). **20 sits in the empty gap for BOTH
parties** (no day lands in 18–23), so it excludes holidays without touching normal days and keeps the
award symmetric, at floor 15 the D winner was July-4th commemoration ("more perfect union", "next 250
years") on 17 offices while R's 4-of-10 July-4th day fell below the bar, an asymmetric artifact.
**Default `UNISON_MIN_ACTIVE = 20`**; disclosed on the page, movable. Sensitivity table (D / R winner):
`15 → "next 250 years" 7/17 (July 4) / "of the working families tax cuts" 3/17` · `20 → "in federal
funding" 8/40 / "under the working families tax cuts" 4/24` · `25 → same D / "better utilizing
investments" 5/36`. **The metric's real signal shows on a news day**: on 2026-06-30 (birthright-
citizenship SCOTUS) a SUBSTANTIVE phrase, "born in the united states", hit **53/102 D = 52% office-share**.
A quiet week surfaces generic/commemorative language, which is accurate, not a defect (no blocklist, the
docs/16 anti-pattern); the floor keeps the denominator real and the "descriptive overlap, not motive"
banner carries the rest.

**THE VOID, the window's loudest silence, both directions, rolled up from the 1.2 absence-map boards.**
`_the_void` reads whatever scored `data/derived/silence/*.json` boards fall inside the window and surfaces
the loudest `silent` topic (max news volume that neither party touched) and the loudest `void` topic (max
party push the news ignored). It **degrades accurately to UNAVAILABLE** when no scored board exists for the
window, 1.2's law that a gap is never rendered as a silence carries through unchanged, so The Void never
fabricates an award from a missing baseline. It is the state on real data today (silence_board is dark,
no GDELT baselines local): `available=false`, and the page says so plainly. It lights up when 1.2 is
wired and its boards accrue, no code change.

**Render + gating.** `site.awards_body` (dark): both parties' Unison side by side (award card + runners-
up, every line carrying `offices_using / offices_active` AND the caucus size), then The Void section, with
the no-motive/overlap-only banner, the office-share definition, the floor, the SPAN + joint exclusions,
and the name-index version all disclosed. Written to the site ONLY when the flag flips (built dark =
absent from output, the `concordance.html` rule); the nav gains a gated "Awards" link; the Methodology
gains a gated section. **Flag OFF ⇒ zero public bytes change**, locked tests: nav link absent,
`methodology_body()` byte-identical. Validated end-to-end on real data: `awards.json` writes + round-trips
(no collapse scaffolding leaks into the persisted rows), `awards_body` renders (16 KB page, all R2
guarantees present), dark gating holds on the live functions. **19 new tests (`tests/test_awards.py`),
348 green.**

**RESERVED for Michael at the flip review (NOT self-authorized).** The flag flip itself; the
`UNISON_MIN_ACTIVE` (20), `UNISON_WINDOW_DAYS` (7), `UNISON_TOP_N` (5), and `VOID_TOP_N` (3) defaults; and
the FRAMING, whether a thin-day holiday commemoration or a ~20% normal-day fragment is worth headlining
as "The Unison", and whether The Void ships before the absence map is publicly live. Two definitions are
matched to the existing metrics and flagged: the office-share numerator counts a phrase used by ≥ SYNC_MIN
offices (the flagship bar), and the window is a fixed trailing 7 days rather than a calendar week. A
content/distinctiveness floor on the winning phrase (so a generic fragment like "in federal funding" can't
top a quiet week) is a possible refinement, deliberately NOT added here (a blocklist is the docs/16
anti-pattern; the "descriptive overlap" framing + the min-active floor are the accurate controls).

**Build order 6 (rulings-shaped 1.3/1.4/1.5) is COMPLETE**: 1.3 origination (Session 22) + R3 party
columns (Session 22) + 1.4 Concordance (Session 23) + 1.5 The Unison + The Void (this session), all dark,
all SPAN-gated, all behind their flags. Streak unchanged (the 3/3 §1.4.1 pass stands; the daily pipeline
does not import build_awards' render). Next dark-shelf items (docs/11): 1.6 floor render + coverage
metric, 1.10 memo-cadence, 1.9 (gated on `DATA_GOV_API_KEY`).

## Session 26 (2026-07-19, Opus), the flip packet (docs/23) + two runnable findings; no code, no flips

The constraint moved from build to DECISIONS (§1.4.1 has PASSED, `ops.unattended_streak('2026-07-19')`
= `passes:True`, 3/3, re-confirmed at session start AND close). Per docs/22 (the flip-packet brief) this
session assembled the decision packet, then spent the remainder on the runnable finding work. **No
production code changed; no flag flipped; nothing published.** Suite 348 green at open and close.

**THE FLIP PACKET, `docs/23-FLIP-PACKET.md` (DRAFT, Michael to ratify; committed `d31f447`, vtask
#176).** Every reserved decision from Sessions 12-24 in one document, swept exhaustively (grep
RESERVED/self-authoriz/flip across docs + BUILDLOG + the FEATURES registry + the 10 open vtasks; the
sweep's completeness is the doc). Three tiers, per docs/21 §2 (Opus drafts, Michael rules, memo style
imitates the #143/#146 adjudications):
- **Tier 1, LAUNCH ACTS (only these gate launch):** pre-flip gates (#129 dark-week receipts audit,
  #110 attorney, status reports, not my calls; #160 + #161 data-history ruling, the literal-name
  history purge is DONE, the residual is Michael's ruling + the GitHub server-side object purge)
  → the mechanical sequence (#131 real passwords → `POSTING_ENABLED` → repo public → #132 announce).
  **Disposition of the five docs/16 §9 rulings: 4 of 5 gate a FEATURE flip (nomenclature ACA / skew /
  quiet-floor / scope), only the privacy one has a live instance and it is already handled by the live
  display-suppression + the Tier-1 history residual.** So most §9 rulings are NOT launch blockers.
- **Tier 2, FEATURE FLIPS (all built-dark, none launch-blocking):** `party_columns` (rec: flip at
  launch, Art. IV correctness), `owners_brief` (rec: flip anytime, private ntfy, ~zero risk),
  `nomenclature_tags` (carries the 3 §9 riders, flip only once resolved), and `authors_vessels` /
  `concordance` / `awards` / `archive` / `silence_board` / `duet`+`phrase_search` (rec: schedule as
  docs/20 content moments, with each one's reserved knobs listed, PEAK_FLOOR 15, MIN_ACTIVE 20, etc.).
  Standing steer = launch MINIMAL.
- **Tier 3, PUBLICATION ACTS (calendar-paced):** S1.9 (P1), S2.9 (P2), the Intensification cards (P4,
  #174 met), plus the fold-vs-isolate `page_html` methodology ruling as a Tier-3 precondition on any
  published lane number.
The packet also carries **S5.2's floor pre-registration** (§4, the docs/13 p-hacking hole; drafted
with a binomial-power justification, min-cell 300, awaiting Michael's one-line confirm; NOT self-supplied
and NOT measured) and flags **#145/#159 as stale-open** (display-suppression live, salt set, Michael's
to close).

**RUNNABLE FINDINGS (docs/13 rows appended; committed `ffd52ea`).**
- **S1.12 Leadership Ignites, REFUTED, both lanes.** False block resolved (leadership_roles on disk:
  `X:/onscript-data/academic_archive/raw/roster/legislators-*.json`, 156 rows, 9 core titles). Core
  leadership offices first-say big ignitions (peak≥20) at **0.82/0.89× (propublica 2013-20) and
  1.61/0.95× (scraped 2021-26)** their statement share, never the ≥3× the folk theory needs, all four
  cells well-powered, robust to the 33-title and no-boilerplate variants. The accurate nuance: the
  tie-inclusive (day-0 co-sayer) variant runs 1.9-2.7×, leadership over-signs at ignition but doesn't
  solo-originate; even so, below 3×. Publishable NULL (docs/20 graveyard/methods). Floors F1-F4 frozen
  in the script header BEFORE measuring; the sole post-run edit was a `year` str→int plumbing fix that
  made the (previously empty) baseline non-empty, no floor tuned against a visible ratio. Script:
  `scripts/search/s1_12_leadership.py`.
- **S3.7 Safe-Seat Vessels, REGISTERED + BLOCKED on a guestbook the "keyless CC0" check missed.** The
  Senate MEDSL file is ungated CC0 and now local (`X:/onscript-data/elections/raw/`); the **House file
  (doi:10.7910/DVN/IG0UN2) sits behind a REQUIRED Dataverse guestbook (id 458)**, `gbrecs=true` does
  not bypass it, and the only API path submits personal data (not fabricated). Errand **#177** filed
  (Michael does the UI download). S3.7's floors pre-registered NOW (member-level Spearman ρ within
  chamber, within-lane halves; CONFIRM |ρ|≥0.20 ∧ p<0.05 ∧ stable-sign; ≥100-members/cell power floor ,
  which is precisely why Senate-alone is NOT run). It is the elections.json disease a third time,
  inverted: an assumed-absent blocker turned out real.

**Reserved (untouched, as required):** every flag, every flip, repo-public, posting, publication of any
card, the S5.2 floor, the docs/16 §9 rulings. **Next Opus session:** the packet is Michael's to rule;
build-side, the docs/11 dark shelf (1.6 floor render, 1.10 memo-cadence) and, when #177 lands, the
whole S3.7 run.

**Addendum, a task-bus TOOLING defect found while filing this packet (fixed).** `vtask list` and the
`vtask add` fuzzy-dedupe both call `get_open_tasks` → `GET /projects/N/tasks?per_page=200`, but Vikunja
CAPS `per_page` at 50 and vtask requested no explicit sort, so on any project with >50 total tasks
(polispeak has 55) both saw only page 1, the OLDEST 50, and silently missed the newest tasks. Real
consequences THIS session: the session-start `vtask list` showed **10 open when there are 13**, it hid
**#161** (a launch-blocking Art. XIII git-history task) plus the two I filed (#176/#177); and the
add-time dedupe could not see #176, so a re-file probe was NOT refused and created a true duplicate
#178 (closed). The bus's whole anti-duplicate guarantee (household CLAUDE.md) was defeated by pagination.
**Fixed** `~/.claude/vtask/vtask.py:get_open_tasks` to paginate every page (bounded 40); `vtask list` now
returns all 13 and the dedupe sees the full set. The fix is in Michael's global tooling, not this repo.
Canon correction: the pre-public privacy-history residual is tracked by bus tasks **#160 + #161**
(near-duplicates; #161 is the flip-blocker); "#166" is a BUILDLOG residual LABEL for the GitHub
server-side object purge, not a numbered bus task. **Discrepancy FILED** (Art. XVI): the docs/22 brief
and earlier canon assumed the session-start `vtask list` was complete; it was not, for any project with
>50 tasks, every prior session read a truncated bus.

---

## Session 28 (2026-07-19, Opus), the pre-launch duties (docs/23 §7.3); day nav + the announce path; 370 green

Ran the worker-session duties the ratified flip packet lists as due before Monday's launch.
**Nothing flipped, nothing posted, no feature released; all FEATURES dark, `POSTING_ENABLED` off,
`unattended_streak('2026-07-19').passes=True` re-confirmed from the record at close.** Commit
`fc8f80f`. **370 tests green** (348 inherited + 7 day-nav + 15 announce).

### 1. Day-navigation fix (§7.3, added 07-19): the day pages were permanent and unreachable

`index.html` linked to **zero** day pages: `day_view_body`'s `is_today` branch swapped the prev/next
nav for a lone "browse phrases" link, so the prev/next chain between day pages had **no entry point**
and a published day was reachable only by typing its URL. Ten days of published record, invisible.

* nav gains **Days**; new **`/day/index.html`** date archive, newest first, grouped by month,
  marking phrases-only days rather than dropping them (dropping would silently rewrite the record of
  what we published, and the archive is the compounding asset).
* the homepage now links **the previously published day** + the archive. `rendered` is hoisted above
  the index block so the homepage knows what preceded it; the lookup is guarded (the `today_day`
  fallback can select a day with no page, so it is `.index()`-with-fallback, never `[-2]`).
* built from the **same `rendered` list the pages come from**, so the index cannot list a 404 or omit
  a live page. `tests/test_day_nav.py` locks the correspondence **both directions**, plus the
  single-day case (no phantom "previous day" arrow) and **"no FEATURES flag"**, it is navigation
  to already-public pages; gating it would re-orphan every day page.
* the rebuild also flushed a **stale `.pcols` CSS block** the committed site predated (Session-22
  dark-feature CSS; no live class emits it).

### 2. Announce path (§7.3, added 07-19): `pipeline/announce.py` and a `workflow_dispatch`-only workflow

Reuses the **Session-8d live-smoke-tested** AT-Proto primitives (`_authenticate`, `_post_thread`
with its deterministic-rkey collision recovery, `_split`, `_root_rkey`) rather than a second
implementation that can be wrong on launch night.

* **Gates, each tested independently:** no `--confirm` => dry run; `POSTING_ENABLED` off **holds even
  with `--confirm` and real creds**; missing creds hold; an **absent repo variable reads OFF**.
* **The approved text never lives in this repo.** It arrives as the dispatch input, so pasting it IS
  the approval. **`---` lines are author-chosen post boundaries**; an over-length authored post is
  **REFUSED, never silently re-split** (silent re-packing would hand the boundaries back to the
  machine precisely where the author was most explicit). `verbatim_ok()` locks that the thread
  reconstructs the approved text word for word.
* **No automated-composite marker.** `_POST_MARK` labels the machine-distilled party voice; stamping
  human-approved editorial copy with it would be a **false label, not a cautious one**.
* Idempotent belt (manifest) and braces (deterministic root rkey, same clock id as R, but rkeys are
  **repo-scoped** and this posts to the house DID, so no collision). ntfy on failure. A locked test
  asserts **no schedule/cron trigger** ever appears in the workflow.

### 3. Flip-readiness audit: two schedule findings

Verified each §7.3 flip is genuinely a one-commit change. **Two are not:**

* **⚠ `nomenclature_tags` (Mon 07-27), §7.2.1's ACA rationale is FACTUALLY INVERTED.** The ruling
  reasons "'the affordable care act' IS an official short title… that D-vocabulary tags where R's
  'obamacare' does not is an asymmetric *finding* from a symmetric *instrument*." Measured against
  the committed cumulative index at the actual threshold (`NOMENCLATURE_RATIO_MIN=0.8`), via
  `nomenclature.tag()`: **`affordable care act` 0.0049 -> NOT tagged · `the affordable care act`
  0.0008 -> NOT tagged · `obamacare` -> NOT tagged · but `unaffordable care act` AND `the unaffordable
  care act` ratio 1.0 -> TAGGED (bill hr6300, a real introduced bill).** The asymmetry runs the
  **opposite** way from the one the ruling considered and accepted: neither party's ordinary framing
  tags, and the only ACA-family phrase that tags is a **Republican counter-brand**, which at display
  time gets a chip citing an official bill record while the Democratic framing renders unmarked.
  SPAN is arguably working precisely as designed (members using it often ARE referencing hr6300), so
  this may need **no code change at all**, but the ratified rationale is backwards and it is the
  thing authorizing the flip. **Not self-authorizable** (docs/16 §9 ruling + Art. IV). Filed **#179**.
  **Does NOT block launch**; blocks only the 07-27 flip.
* **⚠ `silence_board` (Mon 08-10) is NOT a one-commit flip, the board is never BUILT.**
  `pipeline/silence.py::silence_board()` has **no caller anywhere in the pipeline**; `config.py:113`
  says so in passing ("built only when FEATURES['silence_board'] is wired") and
  `data/derived/silence/` does not exist. Flipping the flag alone renders nothing. **This cascades:**
  The Void half of `awards` (Mon 08-24) rolls up from those boards and degrades to UNAVAILABLE
  without them, so 08-24 would ship half-dark. **Both need a build session before their dates**
  (a future Opus session's work, not a human errand, deliberately NOT filed to the bus).

Ready as pure one-line flips: **`party_columns`** (fallback verified on real days, 07-17 D10/R4,
06-30 D10/R7; `sync_by_party` is absent from all 10 historical days because `run_assemble.py:281`
landed in Session 22, so historical days use the documented fallback and days from the next cron
carry it natively), **`owners_brief`** (wired in `run_assemble` both paths; private, zero public
bytes), **`archive`** (chapters present), **`duet`/`phrase_search`/`authors_vessels`** (render-time).

`concordance.json`/`awards.json` are **absent from `data/derived`** because the local state
(`statements` 07-10, `ledger` 07-12) **predates the Session-23/24 code** (07-19); production builds
them in-process every run via `deterministic.run`. A direct re-verification was attempted and
**abandoned, not completed**: it re-parses the **3.08 GB** `ledger.json` from disk and did not finish.
Their own suites (14 + 19 tests) are green and Sessions 23/24 validated them end-to-end on real data.
**Definitive confirmation is the next cloud run producing the two files, check it before 08-24/09-07.**

### 4. Launch-timing observation (Michael's call, unchanged)

The newest published day, **2026-07-18 (Sat), ingested 5 D / 3 R statements**, vs 82/55 on 07-17 and
159/84 on 07-16, so it has **zero synchronized phrases** and both composites are the accurate quiet
line ("We released 5 statements today"). The quiet-day path worked as designed. The
`QUIET_DAY_MAX_STATEMENTS` guard fired, the run is correctly `degraded=False`, and both the pooled table and the post-flip
columns say so plainly. But it means **a Monday 07-20 announce lands on a homepage showing Sunday's
quiet weekend day**, since a day's releases are only complete the next morning. The flagship
demonstration (offices converging on one phrase) is a **weekday** phenomenon. The day-nav fix above
materially softens this, a reader can now reach a rich day in one click, which they could not do
before. **Launch timing is Michael's reserved act; nothing was changed.**

### 5. Bus hygiene

`vtask` pagination fix from Session 26 **verified present** (`get_open_tasks` paginates, bounded at
40 pages). **#176 closed** (the packet was ratified in Session 27). **#179 filed** (the ACA rider).
The announce draft landed at `X:\onscript-data\drafts\ANNOUNCE-launch.md`, **never in-repo**, with
a 4-post recommended thread, two alternatives, and every char count **measured through the actual
thread builder**. It flags that **canon's "53 D on 'born in the united states'" is a different
estimator** (the Unison office-share numerator); the page a reader lands on says **36**, so the copy
says 36. Announce copy must match the page it links to.

### 6. ⚠ Found at close (2026-07-20 ~00:45Z): Run A nulls `daily_lines` on already-published days

While pushing, the rebase pulled in the evening's crons (`collect 2026-07-19` 20:53Z, `assemble
2026-07-19` 22:27Z) and the regenerated site came back with **one fewer day than it had an hour
earlier**. Not a regression in the day-nav code, the archive was correctly reporting a change in the
data:

**`collect 2026-07-19` (commit `0a66cea`) rewrote `data/derived/days/2026-07-18.json` and set
`"daily_lines": null`** (−85 lines), deleting the composites of a day whose assemble manifest is
`final: True`, i.e. **PUBLISHED**. The subsequent assemble targeted 07-19 and did not restore them.

**It is systemic, not a one-off.** Three of ten published days now carry `daily_lines: null` while
still holding real phrase data:

| day | daily_lines | top_synchronized | nulled by |
|---|---|---|---|
| 2026-07-09 | **null** | 19 rows | an earlier collect |
| 2026-07-12 | **null** | 14 rows | `data: collect 2026-07-14` |
| 2026-07-18 | **null** | 0 rows | `data: collect 2026-07-19` (tonight) |

So a day's composites survive only until some later RUN A rebuilds that day and no RUN B re-assembles
it. The "phrases only" days the new archive marks are not a natural category, **they are the scar
tissue of this behavior.**

**Two consequences, both live right now:**

1. **A stale orphan page is public.** `site/public/day/2026-07-18.html` still renders "We released 5
   statements today" for both parties, text whose backing data no longer exists. `build_site` only
   ever WRITES; nothing unlinks, which the privacy code already says out loud
   (`purge_derived`: "a render-time SKIP is not enough… a skipped page stays live at its public
   URL"). It is the Session-21 principle *no proposition outlives its evidence* failing on the
   day-page surface.
2. **The homepage moved to 2026-07-17 (Fri)**, because "today" is the most recent day WITH
   daily_lines, and 07-18's were deleted. **This incidentally cancels the §4 launch-timing concern
   above**: the landing page is now a full weekday with 20 synchronized phrases, not a quiet
   Saturday. A defect improved the launch optics, which is not a reason to leave it.

**NOT fixed in this session, deliberately.** The tempting fix, have `build_site` unlink day pages
that fall out of `rendered`, treats the symptom and would *delete public pages the project treats as
permanent*, destroying the record instead of restoring it. The actual fix is upstream: RUN A must not
null `daily_lines` on a day whose manifest says `final: True`, and the three affected days should be
repaired by re-assembling them (`run_assemble.py --day <day>` bypasses the readiness gate, which is
precisely the documented REPAIR path). **That is a build session's work, not a bus errand.** Queued as
the next worker's first item, ahead of the docs/11 shelf.

**Launch impact: none mechanical, one editorial.** The site is internally coherent (homepage 07-17,
archive lists the 9 days that are genuinely published, no listed link 404s), and nothing about the
posting path is touched. But **the announce points at a site with one stale public day page and two
older days missing their composites**, and Michael should know that before he says go.

---

## Session 30 (2026-07-20, Opus), Monday repair (docs/23 §7.5 steps 1–3): P0 closed, {07-12, 07-18} restored, 386 green

Ran the Monday repair. **No launch acts**, `POSTING_ENABLED` untouched, repo still private, all 19
FEATURES flags dark, nothing posted, no flip. Commit `1543c0e`, pushed (the guard had to reach
production before the 19:30Z collect; §7.5's amendment note, "without it, a post-assemble collect
could null the very Monday reading the launch is waiting for", is the whole reason this was a
same-day push and not a tomorrow-morning one).

### 1. Guard: a published day is immutable to Run A

`build.build_derived` wrote `days/{day}.json` as a **full-object overwrite carrying
`daily_lines: None`**. RUN A focuses whatever day is newest in the corpus, so a collect that landed
on an already-published day deleted its composites, `talking_points`, `duets` and `rejected_keys`.
`util.day_is_final(day, derived_dir)` + one check at that write closes it; `run_assemble._is_final`
now delegates to the same function, so **the readiness gate and the write guard cannot disagree about
which days are published**, that disagreement is precisely how a day got clobbered.

Three design points that are not incidental:

* **Scope is `days/` only.** `discipline.json`, `coverage.json`, `phrases/top.json` and the
  per-phrase pages are *the current state of the system*, not *the record of a date*, and the
  per-phrase files are living adoption curves, so freezing them would strand every phrase at whatever
  day first surfaced it. They keep refreshing while the day is skipped (locked by test).
* **Back-compat is critical, not politeness.** Only 4 of the 9 published assemble manifests carry
  a `final` field; the rest pre-date the readiness gate. `bool(m) and bool(m.get("final", True))` is
  therefore correct and `m.get("final") is True` is a **bug that would leave 5 of 10 published days
  clobberable, including 07-12, the day that proves the defect.** Mutation-verified: that one-token
  change is caught only by the new test, by nothing in the prior 370.
* **Skip-and-log, never raise, and fail CLOSED on ambiguity.** RUN A hits this guard twice a day by
  design, so firing is the normal case. An adversarial pass found the guard had introduced a *new*
  crash surface, `read_json` raises on a truncated manifest, and RUN A had never read the manifest
  dir before, which contradicted the guard's own reason for existing. Wrapped: an unreadable
  manifest returns `True` (if we cannot tell whether a day was published, do not clobber it).

`scripts/regen_derived.py --force` is the deliberate operator escape hatch; `deterministic.run` and
`alexandria.merge` never pass it, locked by a source test. **`alexandria.merge` was a second, unfired
instance of the same defect**, it writes derived for the last day of a 25-year merge, routinely a
published day, and the guard closes it for free.

### 2. Repair: restored from published bytes, **deliberately not `run_assemble --day`**

§7.5 R-C names `run_assemble --day` as the repair path. **Executed directly it would have failed the
launch gate it is sequenced in front of.** Three measured reasons, all reproduced before deviating:

1. **It destroys the streak evidence.** `assemble()` rewrites `manifest/assemble-{day}.json`
   unconditionally, recomputing `event`/`unattended` from `GITHUB_EVENT_NAME`. A repair is never a
   `schedule` event. `ops.unattended_streak` breaks on the first falsy `unattended`, and **07-18 is
   the head of the 3/3 streak.** Simulated: `passes: True` → **`passes: False`**, unrecoverable until
   a third clean cron on Wed 07-22, i.e. *through launch morning*.
2. **It fabricates locally.** `data/state/statements.jsonl.gz` ends at **2026-07-09** (75,989
   statements). A local re-assemble of 07-12/07-18 sees zero statements for those days and writes
   *"We released 0 statements today."* over days that really released 11/12 and 5/3, Art. II.
3. **It re-authors under false provenance.** 07-12's published composite carries
   `generator: dry_run`, `model: P3:dry_run`, prompt 1.0. The cloud has the key and
   `LLM_VOICE_ENABLED`, so a re-assemble would restamp it `sonnet_direct` / `claude-sonnet-5` / 1.1 ,
   a Sonnet provenance claim over text that was published as a deterministic template.

So the composites were **restored from the exact published bytes** (`af36b2a` → 07-12,
`fb9e447` → 07-18) by surgical key merge. Whole-document canonical equality with the published blobs
verified for both days; the deterministic halves (`day`, `top_synchronized`, `discipline`) were
asserted byte-identical rather than rewritten, which is what makes the restore *verifiable* instead of
merely plausible. **The strongest evidence it is a restore and not a regeneration: 07-12's published
version carried no `duets` and no `rejected_keys`, and the restore does not synthesize them, while
07-18 gets both back, a regeneration would have produced schema-current keys on both.** Independent
confirmation: `site/public/day/2026-07-18.html` re-renders **byte-identical** to what was already
live. The "stale orphan" page had been showing the pre-null content all along; the data now matches
the page again, and the page was never unlinked.

**07-09 was NOT repaired, and that is the finding, not an omission.** No committed version of its file
ever carried `daily_lines` (verified across its full history); the composer never ran for it. It is an
accurate phrases-only backfill day and manufacturing a composite for it would **invent a record rather
than repair one** (Art. II). It remains listed and marked "phrases only", the archive now carries
that marker on precisely one day, where before the bug's scar tissue made it look like a category.

### 3. Amendment to the repair path: `repair_safe_manifest`

So the §7.5-named path is safe the next time anyone uses it. Trigger-provenance
(`event`, `unattended`, `run_id`, `forced_finalize`, `readiness`) is preserved from the published
manifest and the repair recorded **additively** (`repaired_at` / `repair_run_id` / `repair_event`).
Three lines that are judgement calls, all documented in code:

* **`degraded` is NOT preserved**, it describes what is published *now*, so a repair that degrades a
  day *should* break the streak.
* **`forced_finalize` IS preserved.** It looks like content and is not: it records that the readiness
  gate waited out `MAX_WAIT_DAYS`. The `--day` path hard-codes `forced=False`, so recomputing it would
  **launder a force-finalized day into a streak-eligible one** and silently drop its alert. Latent
  today (no manifest carries it), locked by test.
* **A field the original never carried is DROPPED, never invented**, 07-14/07-15 pre-date the
  instrumentation, and inventing `unattended` would *manufacture streak evidence*.

A repair also no longer repoints `assemble-latest.json`: that pointer chooses the day that POSTS, so
repairing 07-12 on launch eve would have aimed the first live Daily Line thread at a nine-day-stale
day.

The logic is a **pure function** specifically so it is testable. An adversarial pass proved the first
draft's tests were worthless here, deleting the preservation loop left the suite green, because they
asserted on `inspect.getsource` substrings. Now mutation-verified: emptying `REPAIR_PRESERVED_KEYS`
fails three tests, and the docstring's "THE ONE THAT NEARLY SHIPPED" is behavioral.

### 4. Article XVI record check (§7.5 step 2)

Read from the record, never from run status. Days 07-16/07-17/07-18 each `event=schedule ·
unattended=True · degraded=False · final=True · forced_finalize=False`, symmetry `degraded=false`
(which lives in `derived/symmetry/{day}.json`, **not** in the assemble manifest), governor nominal,
`voice_used=true`, zero alerts; verifier `passed=True` / `fallback=False` both parties every day.
`ops.unattended_streak('2026-07-20')` → **`passes: True, value: 3, days [07-16, 07-17, 07-18]`**,
re-confirmed after the repair, the restore touched no manifest (`git diff data/derived/manifest/`
empty).

**THE S28 OPEN CHECK IS RESOLVED, FAVOURABLY.** `concordance.json` (500,234 B) and `awards.json`
(12,864 B) were both added by **cloud bot commit `0a66cea`**, `git log --diff-filter=A` shows no
other commit, local or bot, has ever touched either path. **Production emits both every run** (from
`deterministic.run`, after `build_derived`, in their own skip-and-log belts), so confidence for the
`awards` (08-24) and `concordance` (09-07) flips now rests on production evidence rather than
inference. Verified the guard does not suppress them: neither builder references `day_is_final`, and
the guard's branch wraps only the `days_dir` write. *(The irony is worth recording: the same commit
that proved production emits them is the commit that nulled 07-18.)*

### 5. Unplanned finding: `scratchpad/` was never gitignored

Canon has asserted since Session 18 that "scratchpad is gitignored → gone on re-clone". **It was
not.** `git add -A --dry-run` staged 21 files, including the Article XIII name-extraction tooling and
the `adv_partymix` evidence scripts. On a repo that goes **public tomorrow**, one reflex `git add -A`
publishes precisely the material Art. XIII spent a history-rewrite removing. Now ignored. The existing
parallel-session rule ("stage only your own files") was the only thing standing between that and a
public leak, and it was holding by convention, not by mechanism.

### 6. Known-open, not in scope (with one canon correction)

* **`2026-07-09` is the one published day the invariant does not cover**, it has a live public page
  but no assemble manifest, so `day_is_final` is False and `regen_derived.py 2026-07-09` would rewrite
  its 19 `top_synchronized` rows with **no `--force` needed**. Nothing would be lost today (it has no
  composites) and RUN A never walks backward to it, so it is a follow-up, not a blocker. If the
  invariant is meant to read "a day with a public page is immutable", the predicate is one manifest
  short.
* **`sync_by_party` is absent from all 10 day JSONs**, so the `party_columns` flip falls back to the
  stored top-20 on every published day, and 07-18, now the homepage, has an *empty* synchronized set,
  so both columns would render empty. Bounded pre-flip limitation already in canon; flagged because
  the homepage moved.
* **CANON CORRECTION.** An adversarial pass reported `coverage.json` (2 year-keys) and
  `discipline.json` (561 D days) as clobber damage "live on methodology.html". **They are not damaged.**
  `config.STAGE1_EPOCH = "2025-01-03"`, so the daily lane's corpus *is* 2025–2026 and 561 days is
  precisely right; the 25-year tables belong to the separate Alexandria ledger. Recorded so a future
  session does not "fix" correct data.

### 7. ⚠ Reproduced directly: the workflows' push-recovery path could never have worked

Pushing the guard at 12:26Z landed mid-run: today's collect had started at **12:00:26Z**, delayed
~2.5h by the Actions scheduler (cron is 09:30Z; prior landings were 11:20–11:48Z). Its push was
rejected as non-fast-forward and the fallback ran, and **failed**:

```
! [rejected]  main -> main (fetch first)
error: cannot pull with rebase: You have unstaged changes.
##[error]Process completed with exit code 128
```

Both workflows carried `git push origin main || { git pull --rebase origin main && git push origin
main; }`. The run stages only `data/derived` (collect) / `data/derived site/public` (assemble) and
leaves other files modified, **so the tree is always dirty at that point and `git pull --rebase`
always refuses.** The recovery path was unreachable because of the design and had never once been
exercised, because nothing had ever pushed during a cron. Fixed in both workflows with
`--rebase --autostash`.

**It is not a cosmetic fix and the timing matters: tomorrow's launch morning commits
`party_columns` + `owners_brief`, and the 21:30Z assemble pass is live.** A launch-morning flip that
races a run would have hit precisely this, lost that run's output, and fired the dead-man in the middle
of the announce.

**Blast radius of today's failure: none permanent, and it self-heals.** The `RUN A collect` step
itself SUCCEEDED and `Persist state + raw mirror to the data Release` succeeded, the long-term value (raw
mirror + `statements.jsonl.gz` + `ledger.json`) is intact. Only the derived commit was lost; the
19:30Z pass restores state, re-pulls and rebuilds it. **The guard was not implicated:** the run's
focus day was `2026-07-20` (it created `days/2026-07-20.json`, a fresh unpublished day), so nothing
was nulled, and the run predated the guard anyway.

**Two operational notes for the record.** (a) The dead-man fired correctly, the workflow-level
`if: failure()` notify ran, so Michael received an ntfy alert at ~12:42Z that was **caused by this
session's push, not by a pipeline fault**. (b) **The 11:30Z assemble did not run at all today** ,
GitHub's scheduler is dropping/delaying heavily (the collect was 2.5h late); the 21:30Z pass is the
backstop, and RUN B's readiness gate no-ops at $0 if no day is ready. **Tuesday's launch morning
depends on the ~11:30Z assemble landing day 07-20; on today's evidence that timing is not
guaranteed, and the launch-morning order should verify the homepage from the record rather than
assume the assemble has landed.**

**Standing rule this earns: do not push to `main` while a cron run is in flight.** Check
`gh run list --json status` first. The `concurrency: onscript-pipeline` group serializes the two
workflows against each other, but nothing serializes a human against them.

---

## Session 30b (2026-07-20, Opus), launch-eve polish (docs/23 §7.5 amendment 2): og cards, two production defects, and a launch-blocking sequencing finding

Second half of the Monday session, after the repair. Commit `eca9153`. **No launch acts** ,
`POSTING_ENABLED` off, repo private, all 19 FEATURES dark, nothing posted, nothing flipped.
**396 tests green** (386 + 10 og), verified green in BOTH the dark state and with all three launch-window
flags flipped.

### 1. ⛔ Blocker: the natural Tuesday cron cannot publish day 2026-07-20. Amendment 2's premise is false as written.

Today's 13:26Z assemble NO-OPed:

```
RUN B assemble — NO-OP (no cluster, no distill, no API spend)
2026-07-19 not ready (only 1 vs same-weekday median 5.5 (18% < 55%)
  — upstream likely still landing) and only 0d old — HOLD, retry later
```

`readiness.select_target_day` walks the lookback window **oldest-first and returns on the first
non-final day**. `util.product_day()` is `2026-07-20` at **both** Tuesday passes (11:30Z and 21:30Z;
`config.TIMEZONE = America/New_York`), so 07-19 is age **1** all day Tuesday, under `MAX_WAIT_DAYS = 2`.
Simulated through the actual function across the whole count range:

| 07-19 final count | Tue 11:30Z result |
|---|---|
| 0, 1, 2, 3 | **NO-OP** (hold) |
| 4, 6, 10, 50 | target **2026-07-19** |

**2026-07-20 is unreachable in every branch**, it is in its structure impossible while an older non-final
day sits in the window. §7.5 amendment 2 says "after the ~11:30Z assemble lands day 07-20 and the
homepage shows Monday's reading"; **that will not happen on its own.** Worse, the count≥4 branch is the
*bad* one: it publishes a 4-statement Sunday and, since `today_day` is the newest day *with*
`daily_lines`, the launch-morning homepage becomes that quiet Sunday, thinner than today's.

**The remedy is already sanctioned and needs no new code**: `run_assemble.py --day` bypasses the gate
(`--day` skips the readiness call entirely) and `assemble.yml` wires the `day` dispatch input to it ,
the same documented repair path amendment 2(c) already uses for first-post timing. Verified
consequences of dispatching 07-20: no prior manifest ⇒ `is_repair=False` ⇒ **`assemble-latest.json`
DOES repoint to 07-20**, which is precisely what 2(c) needs for the composite threads to target the
Monday reading. No hole is created: 07-19 stays non-final and the gate keeps re-examining it
(force-finalized degraded on Wed if count ≥ 1; costlessly skipped at 0). Archive order is safe ,
`all_day_files()` sorts by filename, so publication order is irrelevant.

**One thing that will look alarming and is not:** a dispatch writes `unattended: False`, and
`ops.unattended_streak` breaks on the first falsy `unattended` walking back from the newest manifest ,
so **the streak reads `passes: False` immediately after the dispatch.** That is expected. §1.4.1 already
PASSED on the historical record (07-16/17/18) per Art. XVI; it is a gate on evidence already collected,
not a live health check. Do not let it read as a launch-gate failure mid-morning.

### 2. ⛔ Production silently reset the public corrections log from 3 to 0

`data/reference/corrections.json` held **3** entries at HEAD (including this morning's data-loss
correction). The committed `site/public/methodology.html` said **"Corrections to date: 0. No published
line has yet required a correction."** Production assemble `14af2f0` rendered it.

Root cause, verified in **both** workflows: `tar -xzf data/_restore/state.tar.gz -C .` extracts the
tarball's `data/reference/` **over the git checkout**. 21 files there are **tracked**, corrections.json,
the **Article XIII privacy form list and allowlist**, the nomenclature index, and git is their
authority. A stale tarball rolls them back; the commit step stages only `data/derived` + `site/public`,
so **the rollback never appears in a diff**, it renders wrong and then re-uploads itself, one
self-perpetuating loop.

On the eve of the announce this had the site **denying its own error record**, which is a direct hit on
the project's own rule that a correction is a dated public entry and never a silent edit. The
privacy-form case is the more serious latent one: a stale allowlist silently weakens Art. XIII
suppression with no visible symptom.

Fixed with `git checkout -- data/reference || true` after the extract in both workflows, it restores
tracked paths only, so the gitignored `roster.json` cache still comes from the tarball (the only reason
`data/reference` is in it at all). Re-rendered: **"Corrections to date: 3"**.

### 3. ⛔ The suite failed and would have failed again on Tuesday's flip

Two independent problems, both of which would have shown as a failing health gate on launch morning:

* **A calendrical time bomb.** `test_tests_never_write_into_the_real_derived_tree` asserted that a brief
  for the hardcoded day **"2026-07-20"** never reaches the actual derived tree. Production published that
  day *today*, so the canary went permanently red for a reason having nothing to do with what it
  guards. Re-pointed at **1999-01-04**, a day the corpus cannot produce (`STAGE1_EPOCH` is 2025-01-03).
  A canary whose whole job is "this file must not exist" must name a date reality cannot supply.
* **Six tests asserted the SHIPPED VALUE of feature flags, not the gating behaviour** (`all(v is False
  ...)`, `FEATURES["x"] is False`, "ships dark"). Every one fails the instant a flag is deliberately
  flipped, so **the launch commit itself would have reddened the suite**, and the fastest route back to
  green would have been deleting the very gate tests. Rewritten to force the flag and assert behaviour,
  plus an explicit **`DELIBERATELY_RELEASED` allowlist** in `test_wave0.py`: a release now adds its name
  in the same commit that flips it, which turns a one-character diff into a named, reviewable act and
  still catches an *accidental* flip. **Verified green in both states**, all dark, and with
  `party_columns` + `owners_brief` + `phrase_search` all live.

### 4. Link cards, duty (b), shipped

The site emitted **zero** og: tags across all 291 pages, so the announce, the receipts link carried in
every composite thread, and every share forever would unfurl as a bare imageless URL. Added
`og:type/site_name/title/description/url/image` + `og:image:width|height|alt`, `twitter:card`, and
`rel=canonical`, in `site.page()`, the single shell every page already passes through.

**The privacy rule is the design.** og values are built inside `page()` from its own `title`/
`description` arguments and from nothing else. They must never be sourced from composite prose:
composites pass `privacy_correct_line()`, which can **withhold** or **recompose** them under Art. XIII,
and a meta tag is a surface no audit scans and no reader sees, sourcing one from raw prose would
republish precisely the text the page body withheld. Locked by an **AST** test (not a substring grep,
which would fire on the comment explaining the rule) and mutation-verified.

Absolute URLs throughout, because the crawler that fetches them has no page context. `path=` is passed
by hand at 16 call sites, so the critical test checks **og:url against each file's actual location
on disk, for every rendered page**, the one assertion a typo cannot survive. All 291 pages carry the
full set.

`og.png` is 1200×630, generated from the existing house seismograph identity. `brand.py` no longer
writes to a **dead scratchpad path at import time** (it did, from a long-gone session), is now
`__main__`-guarded and repo-relative, and regeneration is byte-stable, verified: re-running did not
churn the avatar/banner assets that are **live on the three Bluesky profiles**.

### 5. `phrase_search`, duty (a), verified, flip NOT taken

Verified end-to-end: **275 index rows / 275 rendered pages, 0 broken links in both directions**, search
payload ~24 KB, no raw `<` in the JSON, `privacy.is_suppressed` applied in the index (and
`tests/test_privacy.py` already forces the flag ON and asserts the payload is name-free). No new derived
artifact, no network, no build step, the phrase JSONs are already tracked. **No reason not to flip.**

**The Tuesday flip is precisely two lines** (per amendment 2 the flip is Tuesday's act, not Monday's):

```
pipeline/config.py        "phrase_search": False  ->  True   (with party_columns, owners_brief)
tests/test_wave0.py       DELIBERATELY_RELEASED = {"party_columns", "owners_brief", "phrase_search"}
```

### 6. Follow-ups recorded, not done

* **`site.phrase_search_index()` crashes the whole build on a non-dict phrase JSON** (`site.py:1034`
  does `_load_json(p) or {}` then `.get()`); the page loop guards with `isinstance(pdata, dict)` but the
  index does not. One-word fix, matters more once the flag is live.
* **Thread-truncation on retry:** on deterministic-rkey collision `post_bluesky` returns
  `recovered=True` **before posting replies**, leaving a permanently 1-post thread with no receipts
  post. Reachable only if a real post lands and the manifest push then fails, and a push *did* fail
  today (the pre-`--autostash` collect). Operational mitigation for now.
* **`post_bluesky.SITE` duplicates the new `config.SITE_URL`.** Deliberately not refactored: the
  posting path is frozen for launch. Consolidate post-launch.

---

## Session 37 (2026-07-21, Opus), Deep Archive: CREC congresses 113–116, and the metadata-path masked error

Launch-day parallel lane. Zero daily-pipeline surfaces, zero Actions, X:-only bulk storage; the only
in-repo writes are `pipeline/deep/crec.py`, `tests/test_deep_crec.py`, `scripts/deep/*`, four audit
JSONs, and docs. **401 tests green.**

### 1. The crawl was dead, and the named deliverable was blocked before it started

`CRAWL-RUNNING.lock` named pid 17728, **not running**. Started 2026-07-17T04:11Z, dead by ~04:36Z.
Its year order was `[2013…2026, 2009…2012]` and it got as far as 2022, so **2009–2012 was never
crawled**. Congresses 111 and 112 are precisely 2009–2010 and 2011–2012: there was no data to build them
from, and no amount of session time would have changed that.

Restarted detached with the order inverted, `2009,2010,2011,2012` first, then `2022…2026`, so the
blocked deliverable unblocks soonest and the SD.8 overlap fills behind it.

### 2. GovInfo serves "Page Not Found" as HTTP 200, on the metadata path

Ten days across 2013–2022 had been logging `MODS parse … FAILED: mismatched tag: line 70, column 4` on
every single run. The payload is not malformed XML, it is a 44,165-byte **HTML error page**, served
with status 200 by `/metadata/pkg/{pkg}/mods.xml` for packages GovInfo's own sitemap lists. Re-fetched
live to confirm it is upstream and permanent, not transient.

`urlopen` raises nothing, so the payload is the only signal, and two things followed:

* the error page was **written into the append-only raw mirror and hash-manifested as evidence**;
* it was **cached**, and `man.seen(mods_key) and mods_file.exists()` reads the cache first, so every
  resume re-read the error page from disk. **Those days could never heal.** Six days of runs, ten days
  of coverage, permanently stuck, logging the same line every time.

Fix (`crec.looks_like_mods` + `crawl_extensions`): validate before mirroring; quarantine a poisoned
cache entry to `raw/mods/_rejected/` rather than delete it (what upstream served is part of the record)
and re-attempt once; record the day `day-nomods:`, **settled-unavailable, not pending**.

That last distinction is the critical one. A permanently unfetchable day counted as "pending" puts
100% out of reach because of the design, which makes "complete" unfalsifiable, and an unfalsifiable
completeness claim is worth less than an accurate gap. Settled-unavailable days are counted, named, and
carried into the audit JSON as `upstream_gaps`.

Four tests, mutation-verified 3/3 against the pre-fix behaviour (`looks_like_mods → True`).

### 3. Congresses 113–116, built and audited

| congress | years | statements | ledger | member symmetry | audit |
|---|---|---|---|---|---|
| 113 | 2013–14 | 11,735 | 3,185 | .935 / .925 | PASS both years |
| 114 | 2015–16 | 12,455 | 3,431 | .855 / .828 | PASS both years |
| 115 | 2017–18 | 11,999 | 1,371 | .859 / .874 | PASS both years |
| 116 | 2019–20 | 9,177 | 2,549 | .831 / .814 | PASS both years |

~180–230 attributed members **per party per year**. Ledger schema verified identical to the 107–110
shards, so the Search's streaming reader queries them unchanged.

Ratios are on **distinct members** (`audit.gate_result`), while the core source's published D:R numbers are
statement-shares. Those are different estimators (docs/12 L4) and the tempting one-line comparison ,
"the deep lane is more symmetric than the core source in the same years", is not licensed by these numbers.
Comparing the two instruments is SD.8's job.

**Congress 117 was refused.** 2021 is complete; 2022 stops at 87 of 200 sitemap days, because that is
where the old crawl died. A truncated year inside a shard is indistinguishable from a quiet one, it
just looks like less speech. The builder verifies each year's settled days against the published
sitemap and refuses; `--allow-partial` exists and stamps `"partial": true` into the audit so the
artifact would carry its own caveat.

### 4. The shard stays raw, suppression is a view, not a build step

`crec_boilerplate.suppress()` is applied in the acceptance smoke query, **not** at build time.
Congresses 107–110 were built raw by design (docs/15 §9 D4-pre: the ledger keeps every n-gram; the
suppressor filters what a coordination view may surface). Applying it here would have forked the
instrument mid-lane and quietly invalidated every within-lane cross-era comparison, the exact "genre
confound in a trend costume" failure, wearing the costume of a fix.

`lanes.lane_of()` is called explicitly on the loaded set before each build, so a stray press row in the
crec state dir raises instead of entering a deep shard.

### 5. What the smoke query says about the coordination layer

Rows are citable and sane, and they re-confirm both documented residuals on fresh data: **full bill
titles** dominate ("military construction and veterans affairs and related agencies appropriations
act"), and **sub-gram windows of one phrase fill five rows**. One residual is new: **missed-vote
explanations** ("i would have voted yea", "on roll call no") are a high-volume Extensions formula the
seed list does not cover, and they rank as top "R coordination" in congress 115.

All three must close before a crec phrase-coordination card. None of them touches the
speaker-attribution bets (SD.2/SD.3/SD.6), which remain the ripe ones.

### 6. SD.8 not started, precondition unmet

Calibration needs the CREC half of the full 2013–2026 overlap. 2013–2020 is now on the shelf; 117 needs
2022 and 118/119 need 2023–2026, all in the running crawl. Running a concordance on a partial overlap
is the "fake-complete" failure §8 names as the one thing this program exists to avoid, so it waits.

### 7. Drivers are tracked now

`scripts/deep/{crawl_crec,build_crec_shards,crec_state}.py`. Prior sessions ran these from
`scratchpad/`, gitignored, so they vanished on every re-clone and each session re-hand-rolled them
(the Session-18 untracked-evidence lesson). The crawl driver also neutralizes the known `crec.py:217`
trap (it overwrites `crawl-stats.json` with only the current run) by snapshotting before and merging
after; that trap had already destroyed the 2001–2002 record and the entire 2013–2021 campaign's stats.

`crec_state.py` recounts coverage from the statement files rather than trusting run bookkeeping, and is
the first thing the next Deep Archive session should run.

---

## Session 40 (2026-07-22, Opus), posting hygiene (S35 Wednesday order) + R-L redacted-view releases

Prep session, ~01:10–04:00 local, deliberately ahead of the morning cron. **Nothing was posted, no
workflow was dispatched, `POSTING_ENABLED` untouched, no FEATURES flag moved, the repo is still
private.** 433 tests green.

### 1. `_reconcile_prior`, reproduced first, then fixed

The S8e asymmetric-post backstop has been a silent no-op since it was written. Reproduced against a
real directory before touching it: `_list_manifests` returns glob **strings**, `util.read_json` calls
`path.exists()`, so every manifest raised `AttributeError` into the skip-and-log and the scan alerted
on nothing, `alerted=[]`, `ntfy calls=0`.

`_list_manifests` now returns `Path`s. The more important change is the test: **every existing
reconcile test stubs `_list_manifests` AND `read_json` together, with strings on both sides**, so the
two halves were never run against each other and the suite stayed green while the feature did nothing.
`test_reconcile_runs_against_a_REAL_directory_not_a_stubbed_one` stubs only the output (ntfy) and the
location (`config.DERIVED`); the filesystem, the path types and both JSON helpers are real. It fails on
the old code.

This one matters more than its size: posting went live on 07-21, and it is the guard that catches a
hard-kill between the two parties' posts, a durable one-sided thread, which is the worst neutrality
failure the system can have.

### 2. Collision recovery finished the job instead of truncating

`_post_thread` recovered a colliding root and returned `posts_written=0`, leaving a bare head post with
no receipts reply, the only post in the thread carrying the citation link, and no later run would add
it, because the manifest then recorded the party as posted. It now **resumes**: `_existing_replies`
lists the replies already hanging off the recovered root (bounded because of the design, a reply's TID-rkey
always sorts above its root's, so the walk stops at the root) and the run posts only the missing tail.

If the live replies are **not a prefix** of the thread in hand, the day was re-authored between runs;
appending would staple two threads together, so it raises. `on_root` has already fired by then, so the
manifest holds `root_uri` + `partial=True`, the dead-man fires and §1 keeps flagging it.

### 3. Sentence-aware packing, and the invariant that constrains it

The live launch thread read "…our 99 statements today do" / "not converge on additional shared
messages." `_split` now packs whole sentences where they fit and falls back to the old word-packer
(kept, renamed `_pack_words`) only for a sentence longer than one post. An abbreviation guard keeps it
from cutting after "Rep." / "U.S." / "No.".

The critical test is not the pretty one: **the concatenation of the posts is always precisely the
input's words, in order.** An ugly break is cosmetic; a dropped or reordered word is a fabricated
quote. (For a token longer than a whole post the word list must change, so that case asserts character
preservation instead.)

### 4. First-sayer wording, three surfaces, one claim

"first recorded" now says **"in our corpus"** in the composite (prompt **P2 v1.3**), in the receipts
post, and on the phrase page (`First said` → `First recorded in our corpus`). The launch threads were
factually correct and symmetric, the D voice credited a Republican, the R voice a Democrat, because
first-appearance is corpus-wide, but unqualified, it reads as a claim that the member coined the
phrase, and our record starts at `STAGE1_EPOCH`. The live receipts line said "first recorded
2025-01-03", which is the first day of the corpus: left-censoring rendered as discovery.

Also `post_bluesky.SITE` is now `config.SITE_URL` (it was a second hardcoded literal on the one post
that carries the citations).

### 5. R-L, the redacted-view release assets

`pipeline/redact.py` + `privacy.redact()`, wired into the state-persist step of **both** workflows,
before the tar, with no `|| true`: a failure stops the job **before** the upload. Redaction runs in
place on the runner, whose state was restored from the previous asset, so the cloud store converges on
the redacted view; the pristine archive on X: is untouched because no workflow writes there.

**The design decision that keeps R-L inside its scope: a redaction label is itself suppressed.**
`is_suppressed()` returns True for `<private-individual-…>`, so labeled rows are dropped, held and
purged by the display paths precisely as named ones were. Labels flow back into the cloud's state and
**no published site byte moves**. The narrower question, "is a name actually written here", is now
`contains_admitted_form()`, which is what the repo-scan guard uses; conflating the two made that guard
fire on the code that writes the label.

Per-record parsing, not text scanning, and the reason is measurable: with `ensure_ascii=True` a
possessive is stored as the six characters `’`, whose tokens are nothing like the value's, so a
grep-shaped scan misses precisely the possessive forms the gate exists to catch. Only contaminated
records are rewritten, an untouched record keeps its original bytes, which is what keeps a 300 MB
append-only mirror from churning every run. Distinct forms get distinct labels so two n-gram **keys**
can never collapse into one (a silent last-write-wins merge), and a collision is a hard stop. Every
file the pass changes is immediately re-scanned and must come back clean.

### 6. ⛔ Two findings about the R-L blocker itself

Full census of the actual `data-latest` assets, production gate, 48 files, 890 MB:

| file | ships in | occurrences |
|---|---|---|
| `data/raw/congress-press/2026-07.jsonl` | raw.tar.gz | 205 |
| `data/state/statements.jsonl.gz` | state.tar.gz | 205 |
| `data/state/ledger.json` | state.tar.gz | 156 |
| `data/state/extractions.jsonl` | state.tar.gz | 127 |
| **total** | | **693, in 4 of 48 files** |

`data/reference` measures **0 across 26 files**, so the redactor never modifies a tracked file and
cannot fight the `git checkout -- data/reference` restore. **Only the July 2026 raw shard is
contaminated, all 20 earlier monthly shards are clean**, which matches the rider's "1 monthly shard"
and confirms the incident is localized in time.

**(a) `statements.jsonl.gz` is a carrier nobody had measured, and it ties for the largest.** 96.6 MB of
gzip inside `state.tar.gz`. A scanner that reads files as text sees gzip as noise and reports it clean
, which is why S38's whole-worktree scan lists seven carriers and not this one. It holds 205, the same
count as the raw month it is normalized from. The redactor decompresses, scans and recompresses.

**(b) The assets carry ~8× what the R-L spec was written against, and the numbers reconcile precisely.**
S39's rider says "the name 44×/42×", 86. The measured total is **693**. The per-form breakdown
explains the gap to the unit: in `2026-07.jsonl` (205 occurrences across 52 of its 2,414 records),
**form `447bf804…` accounts for 42, which is S38's number precisely.** S38 measured the ONE form it was
scrubbing from git history; **all four admitted forms, both suppressed people, are present.**

It is not a defect in S38, whose job was the git scrub. It does mean the #132 gate spec's figures
describe one form, not the payload.

### 7. Cost, measured on the actual assets

The uncompressed payload is ~890 MB (state 593 + raw 300); a full bootstrap pass measured **861 s**
under contention from other probes. A whole-string memo, the ledger carries every n-gram twice and
`daily` is millions of bioguides from a vocabulary of a few thousand, took
`ledger.json` from **204 s to 52 s** at an identical 156 occurrences. Peak memory in the production
shape is **4.21 GB** against the runner's 16 GB, and `redact_obj` returns clean containers **as
themselves** rather than rebuilding them, without that, the ledger is held twice (measured ~7 GB).
Steady state per run is the files
that change every run (ledger, extractions, statements, the current month's raw); the file-level skip
cache, keyed on the **form list's fingerprint** as well as the file's, carries the rest. Admitting a
new name invalidates the whole cache, which is the one moment a stale "already clean" answer would be
wrong about the entire corpus.

A record-level clean-cache would cut the recurring cost further and is the named follow-up if the added
minutes prove annoying; it was deliberately not built tonight.

### 8. ⚠ Footgun found by walking into it: a local dry-run rewrites tracked post manifests

Previewing the new packing by running `pipeline/post_bluesky.py` locally, fully gated, no creds,
`POSTING_ENABLED` unset, zero network, still called `_flush()`, which rewrote
`data/derived/manifest/post-2026-07-20.json` with `generated_at` restamped and **`posting_enabled`
flipped `true` → `false`**, and created a spurious `post-2026-07-21.json`. That file is the launch
day's record and the source `/posts.html` renders as the signed archive; committing it would have
falsified the evidence that the launch posts went out under a live gate.

Caught by `git status` before staging, reverted, nothing pushed. The preview was re-done by calling
`build_thread()` directly, which is pure.

**A dry run should not be able to write a tracked artifact.** The fix is a preview path that never
flushes (or a `--preview` flag), and it is a named follow-up rather than a change made at 3 a.m. on
the posting path the morning cron is about to use. Until then: preview via `build_thread()`, never by
running the module.

### 9. ✅ R-L in production, and the #132 gate condition met

Later the same session. The 09:30Z collect ran scheduler-delayed at 11:23Z, after the push, so it
picked up the new code unprompted, and redacted **732 occurrences in 4 of 48 files in 1039.9 s**:
`raw/congress-press/2026-07.jsonl` 223, `statements.jsonl.gz` 223, `ledger.json` 158,
`extractions.jsonl` 128. Persist and commit both green, no dead-man; job 1h3m against a ~43m baseline.

**The deltas are the finding.** Against the previous day's assets, raw is **+18** and statements is
**+18**, identical, because statements are normalized from raw, which is a free consistency check on
the derivation. Those eighteen occurrences arrived in *this morning's ingest*: the person is still
being named in new press releases. A one-time edit of the eleven records the rider named would already
have re-leaked, on day one. That is the whole argument for a filter on the way out rather than a patch.

**Verification, as the ruling specifies it.** Downloaded both freshly-built assets from `data-latest`
(byte-sizes matching the live release precisely, raw 93,026,744, state 141,799,381, uploaded 12:27:20Z),
ran `python -m pipeline.redact --check` over all 48 files: **0 occurrences.**

A check that finds nothing and a check that is broken look the same, so the **positive control** was run
as well: the published assets carry **732 redaction labels, matching the run's own report file for file
(223 / 223 / 158 / 128)**. The same machinery found 732 things to replace, and all 732 are present, a
no-op scan is ruled out.

**Stated limit:** `--check` shares its matching engine with the redactor, so it is not an independent
audit; a shared blind spot would pass silently. What partially offsets it is that S38 measured 42 for
form `447bf804…` independently, in another session with another tool, and that number reproduced here
to the unit.

**One ops lesson worth carrying.** A manually dispatched collect was cancelled once the scheduled run
was seen mid-redact. With `cancel-in-progress: false`, a newly queued run displaces an **already-pending**
one, so dispatching anything while an assemble sits queued can cancel the day's post.

### 10. The morning ran, and the live thread found the defect the tests did not

RUN B fired at 13:00:36Z (scheduler ~90 min late, in line with the collect's ~113) and finished green
in 1m3s. Readiness picked **`target=2026-07-21 forced=False :: ready`**, precisely what the gate was
predicted to choose from the actual cloud state, both parties `verifier_passed=True fallback=False`,
`atomic_hold=False`, `asymmetric=False`, both threads live.

**The redact step cost 0.4 s**, "redacted 0 file(s), skipped 29 unchanged". Against the 1039.9 s
bootstrap in the collect, that is the file-level cache doing precisely its job, and it settles the
performance question: the recurring cost is nil, and the record-level cache named in §7 is not needed.

**P2 v1.3 is visibly live**: the R composite reads "first recorded **in our corpus** from Nick LaLota
(R-NY)", and both receipts posts carry the qualifier.

**And the D thread still cut mid-clause**, "...as a common" / "thread today.", which is the defect
sentence packing exists to remove. Cause, from the actual composite: `_sentences` returned 3 sentences,
the middle one 272 chars against a 262-char post. It was 272 because **two sentences had merged**. The
boundary sits after `implemented."`, where the terminal period is INSIDE the closing quote, so the
lookbehind `(?<=[.!?])` inspected the quote and found no boundary. Prompt rule 2 *requires* verbatim
member quotes, so `..."` at a sentence end is this voice's normal register, not an edge case.

Fixed by allowing an optional closing quote/bracket in the lookbehind. On the actual 07-21 composite the
thread goes from 3 body posts with a mid-clause cut to **2, each ending on a complete sentence, still
word-exact**. Mutation-verified against the version shipped this morning. 435 tests green.

The test gap was straightforward. The packing fixtures used prose without quotations. The live voice
uses quote-terminated sentences because the prompt requires them, and the fixture did not cover that
shape.

Receipts verified live: `/day/2026-07-21.html` 200, homepage on 07-21, and the methodology page
carrying both new R-L disclosures.

## Session 46 (2026-07-25, Opus), the first `startup_failure`: the outermost dead-man that was missing

Michael asked whether a post was due today. It was. Day 2026-07-24 never published, and nothing
told him.

**Observation.** RUN B's 11:30Z pass was dispatched at 12:31:15Z, 61 minutes late, and concluded
`startup_failure` at 12:33:55Z. Run 30158114594. GitHub created zero jobs for it. The jobs endpoint
returns an empty list, and the check suite for the head commit records the same conclusion.

**Evidence that the day was genuinely due, not a correct no-op.** RUN A had already succeeded that
morning, run 30155186265, committing 285301c at 11:53:49Z. Its manifest reports `focus_day`
2026-07-24, `focus_day_write: written`, `volume.today` 158 against `trailing_median` 174.5,
`anomalously_low: false`, `degraded: false`, `source_freshness.age_hours` 2.93, and an extract stage
that spent $0.174841 on 185 new statements. `assemble-latest.json` still read day 2026-07-23, so
2026-07-24 was the oldest not-yet-final day and was comfortably above the readiness gate's 55% share
of its same-weekday median. `POSTING_ENABLED` and `LLM_VOICE_ENABLED` were both `true`. No
`post-2026-07-24.json` exists. The 07-24 site render and symmetry audit are absent for the same
reason.

**Root cause of the silence, which is the finding that matters.** The dead-man in both pipeline
workflows is a job step guarded by `if: failure()`. A `startup_failure` means no job was created, so
the step never existed and could not run. The same structure sits in `collect.yml`. This was the
first `startup_failure` in the repository's entire run history, so the failure mode had never been
exercised. Article XVI already required the fix in two sentences: failure notifications belong at
the outermost layer so a scheduled workflow reports failures that occur before `main()`, and a
liveness probe observes advancing data rather than its own process. The in-job dead-man satisfied
neither for a run that never started. The gap was in the implementation, not in the rule.

The workflow file was not at fault. `assemble.yml` is unchanged since b297c06, parses under
`yaml.safe_load`, and ran green twice on 07-24 at 13:02Z and 22:35Z. The head commit 285301c touched
only `data/derived/**`. A valid file that ran hours earlier and then failed to start is a platform
dispatch fault.

**The fix.** `pipeline/watchdog.py` plus `.github/workflows/watchdog.yml`, scheduled at 13:00Z and
23:00Z, 90 minutes after each RUN B pass. It runs in its own concurrency group, `onscript-watchdog`,
because sharing `onscript-pipeline` would queue the probe behind the 60-minute job it exists to
watch. It is read-only: no commit, no push, no Anthropic call, $0.

Two signal classes, because either one alone is blind here:

- Run level, from the Actions API, keyed by workflow file path rather than display name because the
  display names are prose and can be rewritten. Alarms when the newest completed run concluded
  anything other than success, and when that run is older than 26h.
- Data level, from the committed manifests. Alarms when `collect-latest.json` is older than 26h,
  when the last finalized day trails product day by more than 3 days, and when a finalized day has
  no post manifest.

Thresholds and their derivations. `RUN_MAX_AGE_HOURS` is 26. The widest healthy gap between passes
is RUN A's 19:30Z to 09:30Z, 14 hours; add the 61-minute delay observed today and a job running to
its 60-minute timeout for 16 hours worst healthy case, leaving a 10-hour margin.
`FINAL_DAY_MAX_LAG_DAYS` is 3, taken from `readiness.MAX_WAIT_DAYS` of 2 plus one day for finalizing
D-1 during D, so the gate's own patience can never page.

**Why both classes ship.** Replaying today's committed record against the data-level checks alone
produces zero alarms. `assemble-latest.json` read 2026-07-23 against product day 2026-07-24, a lag
of 1, which is normal before the morning pass lands, and the collect manifest was 1.34h old. A probe
built only on advancing data would have stayed quiet through this outage. The run-level check is
what sees it. Test `test_data_checks_alone_would_not_have_caught_2026_07_25` pins that.

**Validation.** Suite 492/0 before, 511/0 after, 19 new tests, no existing test touched. The probe
was then replayed against real recorded state rather than fixtures. Reproduction:

```
for wf in collect assemble; do
  gh api "repos/mlawsonking/onscript/actions/workflows/${wf}.yml/runs?branch=main&per_page=20" \
    --jq '[.workflow_runs[] | {status, conclusion, created_at, updated_at, html_url, event}]' > ${wf}-runs.json
done
python -m pipeline.watchdog --derived <origin manifests> \
  --collect-runs collect-runs.json --assemble-runs assemble-runs.json \
  --now 2026-07-25T13:00:00+00:00 --product-day 2026-07-24 --no-notify
```

At the 13:00Z tick, against origin's manifests and the live run history, the probe returns one
alarm, `assemble_conclusion`, and holds `collect_runs`, `collect_freshness`, `publication_advance`,
and `post_manifest` at OK. Replaying the healthy 2026-07-24 23:00Z tick, with manifests read at
fe5147a and the run list filtered to runs created before that instant, returns zero alarms. It fires
on the incident and stays silent on the day before it.

**One page per failure mode.** The module pages and exits 0 when it finds an alarm, because the
probe did its job. A non-zero exit would trip the watchdog's own `if: failure()` dead-man and page
twice for one incident. The job goes red only when the watchdog itself breaks, which is what that
step is for, and it pages under a distinct title.

**Residual risk, stated rather than assumed away.** A probe inside GitHub Actions cannot detect
GitHub failing to schedule the probe. Closing that needs an external heartbeat that pages when
OnScript stops checking in. It requires an external account and a new secret, so it is Michael's
act, filed as a task. The watchdog runs twice daily and today's fault was the first of its kind in
the repository's history, so the compound probability is low, but it is not zero and it is not
covered.

**Detection latency, before and after.** Before: unbounded, ended by Michael happening to ask, about
7 hours after the failure. After: at most about 13 hours, and for a failure at the 11:30Z pass, 29
minutes.

**Not done, by standing rule.** Nothing was pushed, dispatched, deployed, or flipped. Local commit
only. The 21:30Z pass was left to recover 2026-07-24 on its own, which is what the readiness gate is
built to do, rather than racing it with a manual dispatch against a pending queued run.

## Session 50 (2026-07-26, Fable, emergency implementation): the restore deadlock, its hotfix, and the production proof

The first post-W3 cycle failed on both legs. RUN A died at 10:57Z and RUN B at 12:39Z,
identically: `ValueError: archive conflicts with repository authority:
data/reference/corrections.json` from `pipeline/archive_restore.py`. RUN C correctly
declined to fire behind the failed assemble. The 14:25Z watchdog tick raised 2 alarms
(`collect_conclusion`, `assemble_conclusion`) and paged. That is the probe built on
07-25 catching a real dual failure on 07-26, its first full day in production.

Mechanism. Every `data-latest` archive built before W3 carries `data/reference`, and W3
upgraded the tracked `corrections.json` in the repository, so the new conflict check saw
archive differing from checkout and raised. The raise deadlocks: the archive is only
rebuilt by a run that gets past restore, so no future run could clear the condition. The
merge allowlist below the check already refuses to write repository-authority paths, so
the raise added downtime without adding protection.

Fix, commit 9d3b73f, pushed 19:52Z, about 35 minutes before the evening dispatch. A
differing repository-authority file in an archive is logged loudly and skipped;
rollback stays impossible because the merge loop is unchanged. New archives stop
carrying tracked reference files: `data/reference/roster.json` is the only runtime-owned
path under reference and is now the only reference path in `state.tar.gz`. The renamed
regression test pins the outage shape:
`test_stale_repository_file_in_archive_is_ignored_and_the_day_survives`. Suite 572/0
before push, with an end-to-end proof against the legacy archive shape in the run log.

Production proof, same day. The 20:27Z RUN A restore step printed `[restore]
repository-authority file in archive differs and is IGNORED (repository wins):
data/reference/corrections.json` and `restored 25 runtime file(s) through the
allowlist`, then the run went green end to end. The 22:30Z RUN B went green and the
readiness gate HELD product day 2026-07-25 at 5 statements against a same-weekday
median of 11 (45% below the 55% floor, day 0d old): a Sunday hold, correct behavior,
not a failure. The 22:32Z RUN C was the first production firing of the posting split:
with no newly finalized day it posted nothing, authenticated the 2026-07-24 post
manifest in a fresh process, refreshed the phrase pages, and committed. Day 2026-07-25
publishes when the gate clears, at the 09:30Z pass or on force-finalize per
`readiness.MAX_WAIT_DAYS`.

Validation gap, owned. The W3 conflict check was validated against fixtures only. The
transition case that broke production, every existing archive necessarily predating W3,
was foreseeable from the packet's own file list and was not exercised against the real
`data-latest` asset during acceptance. Article XVI's live-run requirement existed for
exactly this; the S48 validation treated the first scheduled cycle as the live proof and
the cycle found the defect. Future workflow-touching packages get a restore rehearsal
against the production release assets before merge, recorded with the acceptance
evidence.

Numbers with their estimators: outage window 10:57Z to 20:27Z (first failed dispatch to
first green dispatch, Actions run history); detection latency 1h46m (12:39Z RUN B
failure to 14:25Z watchdog page, versus 7h silence on 07-25); fix latency 7h13m
(12:39Z to the 19:52Z push, including diagnosis from a cold start at 19:37Z).

## Session 51 (2026-07-27, Opus), Deep Archive completion: CREC 111/112/117-119, the R-S50.1 3-lane substrate, and SD.8 (HELD)

Deep Archive work order under docs/29-era governance, carrying Fable ruling R-S50.1. Ran in an ISOLATED
worktree `opus/deep-archive` off `origin/main` (14e483e); the operator checkout was owned by an ACTIVE
Codex worker on `codex/x-packages`, so every edited file was collision-checked
(`git log origin/main..codex/x-packages -- <file>`) and all D3/D5 targets came back clean (the worker's 7
x-commits touch a disjoint file set). $0, deterministic, zero Anthropic calls; no publication, flip,
dispatch, or push of main. Suite **572 green at base -> 578 green at close** (+2 R-S50.1 fixtures, +4 SD.8
kill fixtures).

**D1 crawl state confirmed** (`scripts/deep/crec_state.py`): 111, 112, 117, 118, 119 all buildable. The
strong per-year sitemap-completeness check (`build_crec_shards.py --dry-run`) found 119's 2026 truncated
(114 crawled / 118 in sitemap), so the 4 missing days were crawled first (`crawl_crec.py --years 2026`,
+87 Extensions statements, keyless $0) so 119 builds COMPLETE, not `--allow-partial`.

**D2 five CREC shards built** exactly as 113-116 (docs/15 §D1-C discipline verbatim: online per-year
sitemap completeness, settled-unavailable `day-nomods` days counted as SETTLED not pending, no
`--allow-partial`, per-shard audit committed). Every window PASSES symmetric two-party:
- 111 (2009 D=259/R=175 r=0.676 · 2010 259/178 r=0.693) 12,392 ledger entries
- 112 (2011 198/226 r=0.876 · 2012 197/222 r=0.887) 4,656
- 117 (2021 208/192 r=0.923 · 2022 207/189 r=0.913) 560
- 118 (2023 202/187 r=0.926 · 2024 202/195 r=0.965) 459
- 119 (2025 192/188 r=0.979 · 2026 170/142 r=0.835) 555

Audits at `data/derived/crec/audit/congress-{111,112,117,118,119}.json`. The CREC E-lane now spans
107-119 (2001-2026); the SD.8 A=107-112 / B=113-119 overlap is complete.

**D3 R-S50.1 3-lane substrate.** Premise correction: the Session-21-cited "lane-blind read" was already
2-lane-aware at this base (Session 19 gave `load_congress_records`/harness/`wave_s4` the propublica/scraped
instrument fold); R-S50.1 is the 2->3-lane ISOLATION upgrade, page_html its OWN lane, never folded (docs/13
R-S50.1 row is the ruling record). Executed:
- `alexandria.load_congress_records` / `lane_shard_path` accept the three isolated source lanes
  (legacy/scraper/page_html, filtered by `date_source`, matching `harness.iter_statements`) alongside the
  folded instrument names, retained as a labelled robustness view; `reconcile_source_lanes` asserts the
  exact partition legacy+scraper+page_html==combined.
- `wave_s4._collect` carries the isolated `date_source` as the primary lane key; `inst` folded, robustness.
- +2 fixtures in `test_search_provenance.py` (page_html isolated at the loader; source-lane paths; the
  107-112 combined-only guard fires for a source lane too).
- Daily pipeline verified NOT to import alexandria (run_collect/run_assemble/distill/build/ops/verify/
  post_bluesky all clean); nothing here reaches a public surface.
- Substrate rebuild (`scripts/search/build_source_lane_shards.py`, PYTHONHASHSEED=0) COMPLETED for all
  113-119 in ~2.8h (X: only, outside the repo; does not gate SD.8, which reads the CREC statement files):
  `page_html` and `scraper` (page_html excluded) built fresh; `legacy` == the propublica shards by identity
  (copied). `reconcile_source_lanes` PASSES the R-S50.1 acceptance, the EXACT partition legacy + scraper +
  page_html == combined for every congress (delta 0): c113 92895+1675+6=94576 · c114 103753+3124+108=106985
  · c115 142475+6673+62=149210 · c116 145026+15460+403=160889 · c117 144+36319+454=36917 · c118
  0+61123+794=61917 · c119 0+74925+1012=75937 (legacy=0 post-seam is the import's death on 2021-01-03, on
  record).

**D4 SD.8 frozen then run, verdict HELD.** The instrument-concordance calibration study (docs/15 §6) was
pre-registered with numeral thresholds in commit `412308b` BEFORE measurement (freeze-before-measure), then
measured in a separate commit. Family = president-NAMING (the S2.9 Boogeyman family), the one unambiguous
CREC analogue (S1 coordination is CREC-blocked until the boilerplate layer, S4 is BLOCKED, the S2
lexical-style family is register-confounded; naming is boilerplate-robust and docs/13 names S2.9 as the
SD.2 extension). CREC metric IDENTICAL to S2.9 (sitting-president `name_token` per 1k words, out-party vs
in-party, per year), on 68,527 CREC Extensions statements 2013-2026, floor 200/party/year (all 14 scored).
RESULT: out>in in **8/14 years** (agreement 0.571), era-split **2013-2020 6/8 but 2021-2026 2/6**,
contradiction 0.429. Frozen gate -> **HELD**: the parent S2.9 stands on press, the CREC Extensions lane is
NOT calibrated for the naming family, so pre-2013 (107-112) CREC naming claims do NOT advance (calibration
law working; HELD != REFUTED, no systematic contradiction). The instrument difference IS the finding, press
releases are attack-genre, Extensions carry more in-party tribute reference. Publishable methods card either
way; no publication act this session. Result `data/derived/crec/sd8_concordance.json`; re-runnable
`python scripts/deep/sd8_concordance.py`.

**Expectation vs observation (Art. XVI).** Expected all 5 congresses buildable -> observed same, plus the
119-2026 truncation, resolved by crawling. Expected R-S50.1 to be a from-scratch lane fix (work-order
premise) -> observed the reads were already 2-lane; the real work was the 3-lane isolation (premise
correction, filed). Expected SD.8 a clean concordance -> observed HELD with a real era-split, which the
frozen gate correctly did not launder into CONFIRM. No discrepancy left unfiled.

**Deferred / carried:** re-running the eleven S1 hypotheses on the now-isolated substrate is a future
session (docs/18 §4: migrate each reader as it is re-run, never ahead of need). silence_board wiring (#198)
and the X1-X15 order remain out of scope and untouched. Delivery packet: `delivery/DEEP-packet.md`.

## Session 53 (2026-07-27, Opus), the long-session build tranche: E1 (isolated-substrate S1 re-run), then E2/E3

Branch `opus/s1-tranche` from `6c9b0bd`. Baseline suite 653 passed, 0 failed. $0, deterministic, no
Anthropic call, no main push, no flip/dispatch/site-or-data-pipeline regeneration.

### E1: the eleven S1 hypotheses re-run on the R-S50.1 isolated three-lane substrate (docs/18 §4)

The Session-51 carry-forward. Freeze-before-measure: registration + machinery committed (`f0c96e9`)
before any measurement, predictions in `data/reference/search/e1-isolated-registration.json`. Migration
was additive and localized (the alexandria loader/harness were already isolated-lane capable and tested at
Session 51): `wave_s1` gained `legacy`/`scraper`/`page_html` in its lane maps, the reader gained their
cutoffs, and a new reader `scripts/search/revalidate_s1_isolated.py` runs them (reusing
`revalidate_s1_shards.run_lane`, the same estimator). +9 CI-safe fixtures.

Result (full table + evidence in docs/13, "E1" section; `data/derived/search/revalidate_s1_isolated.json`):
**isolation changes NO verdict.** `legacy` reproduces the Session-19 propublica column byte-for-byte
(shards SHA256-identical; S1.1' ratio 11.33, S1.3' drop 0.373, series identical) so the pre-seam isolation
is a verified no-op and the two propublica-era CONFIRMEDs are preserved. `scraper` matches Session-19
scraped on ten of eleven; the one move (S1.3' ARTIFACT -> REFUTED) is a **normalize-version rebuild
artifact, not page_html isolation**: the Session-51 scraper shards use the newer W7/X9 `document_families`
collapse (c117 ledger 164,179 -> 121,417) that the Session-19 scraped shards predate, and `page_html`
contributes ZERO coordination phrases (its ledger is 1 ngram/congress; its peak>=15 member index is empty),
so it is mathematically incapable of reshaping the burst series. Both S1.3' verdicts are non-findings
(density fails, drop negative) so the move is null-to-null. `page_html` standalone is UNDERPOWERED for all
eleven (empty member index), confirming it cannot be an independent comparative lane. Verdicts flipped
toward a false positive: 0.

Found and fixed in passing (`faebf7f`): `s1_4_proper` OOMed at congress scale because the post-Session-19
`document_families` clustering runs on the full-corpus normalize; since its congress-split gate is
structurally unmeetable in any single lane (verdict UNDERPOWERED regardless), the power check now runs
before the normalize. Verdict-preserving; lane=None unaffected.

**Substrate finding flagged to the orchestrating session / Fable (not self-authorized):** the R-S50.1
isolated substrate mixes normalize instruments (legacy is a byte copy of the OLD 2026-07-17 propublica
shards; scraper/page_html were built fresh 2026-07-27 on the NEW normalize). Within-lane verdicts are each
valid; a clean same-instrument page_html decomposition would rebuild `scraped` via `run_shard(lane=
"scraped")` but is unnecessary here because page_html provably contributes 0 coordination phrases.

**Art. XVI expectation vs observation:** predicted legacy == propublica (confirmed exact), scraper ==
scraped (confirmed 10/11; the S1.3' deviation diagnosed to the substrate rebuild, filed above, not left as
an anomaly), page_html UNDERPOWERED x11 (confirmed). Suite 653 -> 662 green across the freeze, the fix, and
the measurement. origin/main collision-checked clean before every edit; the daily crons commit to main, my
branch does not.
