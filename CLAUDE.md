# OnScript project instructions

> Editorial note (2026-07-23): this file was restructured under
  `docs/25-DOCUMENTATION-VOICE-BRIEF.md`.
> The dated session record moved to `docs/26-SESSION-HISTORY.md`. Findings, decisions, and
  chronology
> are unchanged. The original wording is available at commit `68ef5ce`.

OnScript is the public name. The repository codename is `polispeak`; the name was locked in Phase 3
under `docs/03-GAMEPLAN.md` §0. The system reads public statements from elected U.S. officials,
summarizes each party's shared language in a cited composite voice, and measures coordinated speech.
The two party accounts introduce the product. The dashboard and its growing time series are the
product itself. The November 2026 midterms are the first major attention window.

## Product summary

OnScript compresses public source material without inventing jokes or claims. Every published claim
links to at least 3 source statements with a member, date, and URL. The corpus supports three main
analyses:

1. **Talking-point propagation:** first appearances and adoption curves over 24–72h. A phrase that
   moves from 2 accounts to 90 in a day is evidence of coordinated public language.
2. **Silence detection:** comparison of the national news baseline with subjects that neither party
   addresses.
3. **The on-script index:** each member's use of shared party language compared with their own
   language.

The predecessor was `github.com/mlawsonking/PoliticianTweeting` (2022, twint + trigrams + Flourish).
It found higher phrase alignment among Democratic tweets and showed that national events produce
phrase spikes. It stopped working when twint and the Twitter API stopped providing a usable source.
OnScript is the 2026 rebuild using LLM distillation and open data.

## Model-split workflow

Check the current phase before starting work.

| Phase | Model | Responsibility | Output | Status |
|---|---|---|---|---|
| 1 | **Fable** | Explore the feature set, distribution ideas, and strongest artifacts. No code or feasibility research. | `docs/01-VISION.md` | Complete, 2026-07-10 |
| 2 | **Opus** | Test the important assumptions against APIs, ToS, costs, and prior art. Mark each feature VIABLE, viable-with-changes, or DEAD with evidence and links. | `docs/02-RESEARCH.md` | Complete, 2026-07-10 |
| 3 | **Fable** | Set the v1 scope, architecture, schemas, pipeline, prompts, voice, launch sequence, roadmap, and acceptance criteria. The v1 plan had to fit one weekend. | `docs/03-GAMEPLAN.md` | Complete, 2026-07-10 |
| 4 | **Opus** | Implement the gameplan with live-source verification, targeted tests, and a current runbook. | pipeline and site | In progress; see `docs/04-BUILDLOG.md` |

Phase ownership is binding:

- The documents present under `docs/` identify the phase.
- Each phase ends with its document committed, a handoff note at the top, and updated status here.
- Opus stops if `docs/01-VISION.md` does not exist.
- Fable works in Phase 3 once `docs/02-RESEARCH.md` is complete.
- If Fable is unavailable, `docs/21-CONTINUITY.md` governs. Opus may draft decision memos and DRAFT
  briefs. Michael retains the reserved decisions. `docs/01-VISION.md` and `docs/05-HORIZON.md`
remain
  the planning sources.

## Hard constraints

- **Runtime:** GitHub Actions supplies cron and compute. The recurring model is a Haiku-class
  Anthropic API model. The v1 cost ceiling is $10/month. Output is JSON and a static Vercel site.
  There is no server to maintain and no local Node dependency for deployment. GitHub deploys to
  Vercel, as in PlainSpeak.
- **Sources:** use official and open sources first: congress.gov, member press releases, and
  Bluesky.
  X ingestion requires a separately validated path. Automated X posting was a research question,
  including price and labeling rules.
- **Citations:** every distilled talking point needs at least 3 public source statements. Failed
  verification drops the claim.
- **Reliability:** source outages use skip-and-log. They do not end the daily run. Failed runs and
  anomalously small outputs trigger the dead-man notification through Michael's existing ntfy topic.
  `ANTHROPIC_API_KEY` and `NTFY_TOPIC` are stored only in GitHub Actions secrets. Raw ingestion is
  immutable and rebuildable.
- **Neutrality:** both parties use the same pipeline, prompts, thresholds, and public symmetry
  audit.
  The method is symmetric even when the findings differ.
- **Storage:** schemas remain compatible. Raw records are append-only and date-stamped. The time
  series is the long-term asset.

## Current build state

The Phase 4 implementation record began on 2026-07-10. Completion is defined by §1.4 passing in
full. The presence of code alone is insufficient. Section §13 decisions remain locked, including the
open implementation choices recorded there.

- **Phase 1, completed 2026-07-10:** `docs/01-VISION.md` defines 5 insight families, a ranked
  37-feature set, the top-5
  artifacts, distribution ideas, voice, names, design rules, and assumptions R1–R11.
- **Phase 2, completed 2026-07-10:** `docs/02-RESEARCH.md` tests R1–R11 against primary sources. The
  source design uses
  press releases from `dwillis/congress-press` plus Bluesky. X is DEAD as an automated channel.
  “Party Lines” is DEAD as the name; **OnScript** replaced it. GDELT 2.0 supplies the news baseline.
  Batched, cached, routed model work fits about $6–9/mo. Press releases are the symmetric two-party
  source, and the scraper is mirrored. No feature was eliminated.
- **Phase 3, completed 2026-07-10:** `docs/03-GAMEPLAN.md` defines the daily cadence, budget governor,
  two-lane neutrality
  design, nightly public audit, scraper mirror and cold-standby fork, dead-man path, and public
P1–P3
  prompts. The ledger starts at 2025-01-03. Stages A1–B9 have explicit failure behavior. Account
  specifications use `blue.onscript.news` and `red.onscript.news`. The roadmap set v2 work for Aug
10,
  v3 work for Oct 5, and assimilation curves for Jan 2027.
- **Phase 3 amendments, completed 2026-07-10:** the Library of Alexandria covers the full 2001 corpus
  with a deterministic
  25-year ledger. Era chapters belong to v2. Cross-era claims have temporal coverage gates, and v1
  schemas use a `congress` key. Recurring work uses Actions plus the API. One-time chapters use the
  cheapest capable option: subscription-scripted `claude -p` at $0 marginal cost, or API batch up to
  $30 before Sep 1. Michael's 4080 handles Alexandria embeddings and free historical topic tagging.
  Local models never write the chapter voice. Daily publication remains api-keyed.
- **Phase 4, Session 1:** the standard-library pipeline was verified against live `congress-press`
  data. It implements ingestion, mirroring, deduplication, syndication handling, joint-family
  collapse, boilerplate and date suppression, content n-grams, first appearances, adoption curves,
  the discipline index, coverage tables, and deterministic citation checks. P1–P3,
  `taxonomy_v1.json`, and `rebuild.py` were committed. The first suite had 17 tests. The §1.4.5
  boilerplate proof and §1.4.4 full-epoch backfill passed. The 8-Democrat “birthright citizenship”
  convergence on 2026-06-30 is recorded in `docs/04-BUILDLOG.md`.
- **Phase 4, Session 2:** the remaining v1 publication path was verified end to end in dry-run mode.
  Without `ANTHROPIC_API_KEY`, the pipeline spends $0 and makes no Anthropic call. The LLM layer,
  cached P1 fragments, 4-gram clustering, P2/P3 Daily Lines, Batch API path, direct fallback,
  verifier, two-lane enforcement (§5.1), symmetry audit (§6.4), RUN A, RUN B, workflows, Lane-2
  Bluesky ingest,
  at-Proto posting, and static site were added. The 2026-06-30 render showed 53 D members on “born
in
  the united states” and 12 R members on “supreme court's decision in little v,” with 100% coverage.
  The suite then held 25 tests. The static generator replaced Astro because the development machine
  had no Node installation; both use the same derived contract.
- **Launch snapshot from the original Phase 4 handoff:** the remaining §7.3/§9 work was assigned to
  Michael: create and push the public repository, register the domains and the
  `blue.onscript.news`/`red.onscript.news` accounts, set the Actions secrets, and set the $10 Console
  cap. The cloud gate required 3 consecutive unattended runs. The nonblocking list held the
  ~130-member Bluesky map, incremental ledger merge, and Alexandria Stage 2. This snapshot is
  historical; the current status below records that those launch steps later completed.
- **Idea document, completed 2026-07-11:** `docs/05-HORIZON.md` holds 8 longer-term bets, the §2.5
  Appendix, and publication gates.
- **Governance documents, completed 2026-07-11:** `docs/06-CONSTITUTION.md` defines 15 original
  invariants; Article XVI was added later. `docs/07-OPERATIONS.md` defines states S0–S∞, 5 weekly
  health measures, the 15-min, monthly, and quarterly checks, the Owner's Brief, and playbooks
  P1–P10.

## Standing rules and traps

These rules were extracted from the dated session record. Detailed evidence remains in
`docs/26-SESSION-HISTORY.md` and the canonical documents linked below.

### Evidence and analysis

- A green workflow badge is insufficient evidence. Read manifests and advancing data as required by
  Constitution Article xvi.
- Every number entering the record needs its estimator, unit, window, denominator, and a rerunnable
  reproduction path.
- Cross-party metrics use Lane 1 only. Lane 2 can enrich sources but cannot enter comparative
  denominators.
- Historical analyses stay within one provenance lane unless a method explicitly handles the seam.
  Per-Congress shards cannot answer within-phrase genealogy questions without a merged substrate.
- Joint and cosigned releases count once through the project unit key. A member count and a source
  unit count use different denominators and must be labeled.
- The public epoch comes only from `config.STAGE1_EPOCH`. Earlier first carriers remain unattributed
  on public surfaces. Permanent phrase pages may remain while zero-in-window phrases leave search.
- Code computes numbers. Models may copy approved numbers but cannot derive them.

### Publication and privacy

- The verifier, privacy suppression, citation quorum, digit checks, and party symmetry rules apply
  before any public write.
- Public release archives are privacy-redacted views. Michael's append-only archive remains pristine.
  `pipeline.redact --check` must scan compressed carriers as well as ordinary JSON.
- A redaction label is itself suppressed on display paths. `contains_admitted_form()` answers the
  narrower question of whether an admitted name form is present.
- Every changed redaction carrier is scanned again. A key collision is a hard failure. The redaction
  cache includes the admitted-form fingerprint so a newly admitted form invalidates old clean
results.
- Raw bioguide identifiers never render as member names. All renderers use the hardened label path.
- Phrase evidence requires verifier-grade containment, at least 3 distinct source units, privacy
  checks before writing and rendering, and source metadata without statement text.
- Atom and social metadata use deterministic fields. They never include composite prose or source
  statement text.

### Daily reliability

- Source, evidence, favicon, and optional derived builders use skip-and-log where their failure must
  not cost the day's core artifact.
- The day summary is written before optional phrase evidence runs.
- Posting is atomic across parties. A partial manifest never authenticates the intended unwritten
  tail of a thread.
- The post archive is rendered again after posting in a fresh process. If that render fails, restore
  the first render, keep the day's data commit, and report the failure.
- Collision recovery resumes only when live replies are a prefix of the thread being posted. A
  mismatch refuses to splice two versions.
- Thread packing must preserve every input word in order. Sentence boundaries can end after closing
  quotation marks or brackets.
- Local `pipeline/post_bluesky.py` execution is preview-only when `GITHUB_ACTIONS` is absent. The
  `--allow-local-manifest-write` option is the explicit override. Any present `GITHUB_ACTIONS` value,
  including `false`, keeps the CI flush path.
- Do not dispatch a workflow while another run is pending unless replacement is intended. With
  `cancel-in-progress: false`, a newly queued run can displace an already pending run.
- Missing optional brand assets must log loudly and allow the site render to continue.

### Local development and release

- On the Windows operator machine, use `C:\ProgramData\miniconda3\python.exe`. Bare `python` is a
  0-byte stub in this environment. The authoritative suite is `tests/run_tests.py`; `pytest` is not
  installed and `unittest discover` finds 0 tests.
- Do not change prompts, thresholds, schemas, or feature flags during unrelated work. The election
  freeze in Constitution Article viii applies from Oct 15 through Nov 10.
- Never regenerate and commit `site/public` or `data/derived` as a side effect of local validation
  unless the work order explicitly requires those outputs.
- Never stage with `git add -A`. Preserve the untracked `AGENTS.md` file.
- Release belongs to Michael. External implementation work does not push, deploy, dispatch
  workflows,
  post, or change `POSTING_ENABLED` or any `FEATURES` value.
- The repository and site are public. The stabilization stack through `166b4de` and the binding
  voice
  brief `68ef5ce` are present locally. Voice-rewrite commits wait for Michael's review and the
release
  order in `docs/24-PUBLIC-SURFACE-STABILIZATION-BRIEF.md`.

## Current status

OnScript reached public S3 on 2026-07-22. The site, party posting, announcement, repository, public
prompts, nightly symmetry audit, corrections log, and `data-latest` release are live. The next
planned
operating work includes the 07-27 nomenclature flip, Archive and `silence_board` wiring by 08-03,
the
first editorial publication around 08-05 P1, Deep Archive work for Congresses 111/112 and 117–119,
SD.8, and the October registration wave.

The active documentation task is governed by `docs/25-DOCUMENTATION-VOICE-BRIEF.md`. Release and
rollout through the election freeze are governed by `docs/27-RELEASE-AND-ROLLOUT-ORDER.md`: the
local stack pushes in the R0-R8 sequence, one flip per Monday under the docs/23 health gate, last
flip Monday Oct 5, quiet from Oct 12, constitutional freeze Oct 15 through Nov 10. Dated work is
recorded in `docs/26-SESSION-HISTORY.md`. Future sessions append there and keep this section short.
