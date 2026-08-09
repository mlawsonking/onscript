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

## Build history

Phases 1 to 3 completed 2026-07-10 and their documents are the record: `docs/01-VISION.md`
(insight families, the ranked feature set, assumptions R1-R11), `docs/02-RESEARCH.md`
(R1-R11 tested; X is DEAD as an automated channel; the name OnScript replaced Party Lines;
press releases plus Bluesky as the symmetric source; GDELT as the news baseline), and
`docs/03-GAMEPLAN.md` with its amendments (cadence, budget governor, two-lane neutrality,
the Alexandria 2001 corpus and 25-year ledger, the `congress` key, era chapters in v2).
Phase 4 began 2026-07-10 and is recorded in `docs/04-BUILDLOG.md`; completion is defined
by §1.4 passing in full, and §13 decisions remain locked. Longer-term bets are in
`docs/05-HORIZON.md`; governance is `docs/06-CONSTITUTION.md` (17 articles, v1.2) and
`docs/07-OPERATIONS.md` (states, health measures, playbooks). Launch history through
public S3 is in `docs/26-SESSION-HISTORY.md`.

Decisions from the Phase 3 amendments that still steer work: recurring work uses Actions
plus the API; one-time chapters use the cheapest capable option, including
subscription-scripted `claude -p` at $0 marginal cost; Michael's 4080 handles Alexandria
embeddings and historical topic tagging; local models never write the chapter voice;
daily publication stays api-keyed.

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
- Blinded rating or annotation sessions do not recall label-space memory. Anything recalled
  before the first label is disclosed in the delivery packet as a prior (Session 60).

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
- The harness enforces the mechanical rules inside Claude Code sessions: `.claude/settings.json`
  carries deny and ask permission rules plus the `.claude/hooks/governance_guard.py` PreToolUse
  hook covering `git add -A`, bare `python`, release acts, the generated trees, prompt and config
  edits, and the freeze window. Bypass-permissions mode is disabled for this project; ask rules
  survive bypass in any case, deny rules do not, and deny beats ask beats allow across all
  settings files. The prose rules still bind where the harness cannot see.

### Engineering discipline (every implementation session)

`docs/37-ENGINEERING-DISCIPLINE.md` is binding and codifies the recurring failure patterns from
the W/X/Deep/S1/Y rounds, each rule with its incident. Constitution Article XVII (v1.2) makes
self-description integrity constitutional. The headline traps:

- Registries are tested against their live owning modules, never against their own copy.
- Production paths get at least one test built from real committed artifacts, not fixtures alone.
- Committed evidence files are pinned history; never assert them equal to a fresh live-tree build.
- A fail-closed gate ships with its transition path for existing production state, or it is an
  authored outage.
- Identity facts (fingerprints, versions) are stamped once at the owning stage and inherited;
  code identity hashes the measurement tree, never repository HEAD.
- Runs over 10 minutes go through the harness detached mechanism; never a manual nohup, never a
  polling loop.
- Session numbers are claimed from the docs/26 tail at session start; parallel sessions collide.
- An external worker's active branch and checkout are never touched by another session; parallel
  sessions run in isolated worktrees.
- A liveness probe runs outside the process it watches; fail-closed gates establish at first use,
  never at import time.

## Current status

OnScript reached public S3 on 2026-07-22. The site, party posting, announcement, repository, public
prompts, nightly symmetry audit, corrections log, and `data-latest` release are live. The Deep
Archive shards (Congresses 111/112 and 117-119), the three-lane substrate, the silence-board
wiring (dark, flip pending), the Alexandria Stage 2 embeddings, and the gold-set pilot
instrumentation are complete and recorded in `docs/26-SESSION-HISTORY.md`. Operating work follows
the `docs/27` calendar: Monday flips under the docs/23 health gate, the first editorial
publication around 08-05, and the October registration wave. Open operator items ride the task
bus.

The active documentation task is governed by `docs/25-DOCUMENTATION-VOICE-BRIEF.md`. Release and
rollout through the election freeze are governed by `docs/27-RELEASE-AND-ROLLOUT-ORDER.md`: the
local stack pushes in the R0-R8 sequence, one flip per Monday under the docs/23 health gate, last
flip Monday Oct 5, quiet from Oct 12, constitutional freeze Oct 15 through Nov 10. Dated work is
recorded in `docs/26-SESSION-HISTORY.md`. Future sessions append there and keep this section short.
