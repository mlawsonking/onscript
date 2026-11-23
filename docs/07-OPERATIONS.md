# 07: Operations, state ladder, health numbers, rituals, and playbooks (v1, 2026-07-11)

> Michael uses this document as the project's navigation system. It answers three questions in under a minute: Where is the
> project, is it healthy, and what should happen next? Every work session (any model) ends by updating
> the **"You are here"** line in `CLAUDE.md` to the current state on the ladder below. The
> constitution (`06-CONSTITUTION.md`) governs *what's allowed*; this governs *what's next.*

---

## §1 The state ladder

One state at a time; advance only through the exit gate. If you're ever lost: find your state,
do your job, ignore everything else.

| State | Name | You are here if… | Your job this state | Exit gate |
|---|---|---|---|---|
| **S0** | Built, dark | Machine verified in dry-run; no remote/keys | The 90-min errand batch: public repo + push, domains, Bluesky accounts, secrets, Console $10 cap | **First cloud dry-run** RUN A+B green *(passed 07-12)* |
| **S1** | Cloud-proven | Workflows green in the cloud, still $0 | Watch 3 consecutive dry-run days; fix yaml friction (Opus session if needed) | 3 green days + Release assets populating *(passed 07-14)* |
| **S2** | Live voice, dark | `ANTHROPIC_API_KEY` set; real Daily Lines; accounts unannounced *(first live run passed 2026-07-14; exited after the unattended streak and launch gates cleared)* | The dark week: hand-audit 5 receipts/day, tune P2 taste (free now, public diffs later), attorney hour | §1.4.1 gate (3 consecutive unattended real runs) + audits clean |
| **S3** | Launched | Accounts public, launch artifact out **(← current, 2026-07-22: site + posting + announce live; repo public)** | The §9 circuit; then *let the streak work*, your only daily job is the 15-min ritual (§3) | 30 unbroken days green on the published status SLOs and a first external citation or embed *(amended S69 per docs/29 item 57: the follower arm is retired; a no-engagement instrument's followers measure nothing)* |
| **S4** | v2, the insight release | Building silence detector, leaderboard, floor leg, The Archive/Alexandria | Opus sessions against gameplan §10 v2; chapters via `claude -p` (before Sep 1) | v2 acceptance (gameplan §10) |
| **S5** | v3, the coordination release | Building alerts, Memory Hole, upstream graph, bill-brands, API | Opus sessions against §10 v3 | v3 acceptance, by Oct 5 |
| **S6** | Election mode | Oct 15 – Nov 10, 2026 | **Freeze** (Constitution viii); daily receipt spot-checks; capacity watch; prep the retrospective | Retrospective artifact ships ≤7 days post-election |
| **S7** | Season 2 | Jan 2027: new Congress | Assimilation curves live; State of the Script #1; Mirror Test | Annual report shipped |
| **S∞** | Steward | Ongoing | Quarterly horizon pick (05 §3 rules); the machine compounds | Stewardship is the destination. |

Skipping states is prohibited. Regressing (e.g., streak broken in S3) means: run the relevant
playbook (§4), file the postmortem, resume the same state, the ladder position doesn't reset.

## §2 The five health numbers

Read weekly (or from the Owner's Brief, §3). Green/red thresholds are deliberately crude,
they exist so you never have to *interpret* on a tired Monday.

1. **Streak**, days since last missed publish. Green: the site is current under the docs/23 §7.3
   clause (`site.reading_state` is `today` or `latest_complete`: the newest published day trails
   the product day by at most 1 and is neither degraded nor force-finalized). Red: anything else →
   Playbook P1. The brief prints two labelled counts beside it: consecutive days with a published
   record (backfilled days count) and consecutive clean unattended runs (`ops.unattended_streak`,
   which a dispatched backfill breaks). S74-15.
2. **Spend (mtd, projected)**, manifest `est_cost_usd` sum. Green: ≤ $8 projected. Red: governor
   already degraded twice this month → decide: raise cap or ride degraded (your call, one line in
   buildlog).
3. **Coverage**. Lane-1 statements vs. trailing median, per party, + upstream freshness. Green: both
   parties ≥ 60% of their own trailing 6-week same-weekday median (S70-2; it was a trailing
   14-day all-days median) and upstream < 36h stale. Red → Playbook P2.
4. **Verifier drop rate**, claims dropped ÷ claims offered (dropped + published; the brief's
   logged deviation from the original "÷ published"), 7-day. Green: < 25%. Red (sustained
   rise): upstream text quality shifted or prompt drift → Opus session, don't hand-tune.
5. **Reach**, citations/embeds + site sessions (analytics live since 2026-08-10; count monthly,
   not daily; vanity is a monthly vitamin, not a daily meal). Follower counts are retired as a
   health input (S69, docs/29 item 57): the accounts solicit no engagement, so their followers
   measure the instrument's posture, not its reach.

Numbers 1–4 are machine-readable today (manifests + symmetry reports). **The Owner's Brief**
(small v2 item, spec below) turns them into a push notification so "understanding where I'm
at" costs zero clicks.

Number 1 no longer waits for a Monday read. Since 2026-07-25 the watchdog workflow checks the
streak twice a day from outside both pipelines and pushes when a run fails to start or the
committed record stops advancing. See P12 and docs/04-BUILDLOG.md, Session 46.

## §3 Rituals, the entire human cost of stewardship

- **Weekly (Monday, 15-20 min):** read the five numbers · run the structured review sample,
  `C:\ProgramData\miniconda3\python.exe scripts\reproduce_subset.py`, and spot-read the sampled
  claims with your editor hat (true is guaranteed; you're checking *funny/fair*; the
  deterministic sample replaces ad-hoc skimming, per docs/29 item 54, accepted S69) · glance at
  the best chart · anything odd → one line in `04-BUILDLOG.md`. That's it. **This ritual is the
  minimum viable stewardship: if life gets loud, do this and nothing else, the machine runs
  without you.**
- **Monthly (1st weekend, 1 hr):** spend vs. cap · coverage trend · prompt-diff review (should
  be empty or justified) · ladder check: still in the right state? · pick/adjust next state work.
- **Quarterly (2 hr):** re-verify Anthropic pricing + model IDs (model swap = regression-test
  day, never a silent change) · `congress-press` commit cadence check · Internet Archive
  snapshot (Constitution xiv) · constitution read-through · horizon pick session (05 §3 rules).
- **The Owner's Brief (v2-small, spec):** RUN B appends a Monday ntfy/email: the five numbers,
  streak count, top phrase of the week, any degraded days, any pending decision flagged by the
  governor. The system reports to its owner; the owner never has to remember to ask.

## §4 Playbooks

- **P1. Missed day.** Read manifests → identify stage → fix or file Opus session → **public
  postmortem post from the brand account** (clinical, 2 sentences) + buildlog entry. The
  postmortem *is* the brand: instruments that admit failure get believed.
- **P2. Upstream stale/dead.** <36h: nothing (dead-man already logged it). 36–72h: verify
  their repo/Actions manually. >72h: promote the cold-standby fork (one cron flip, tested),
  courtesy-note the maintainer, disclose on methodology until healthy.
- **P3. Bias siege.** Reply once, with links: methodology + that day's symmetry audit + the
  prompt history. **Never argue past the first reply** (Constitution X). Sustained bad-faith
  campaigns get silence and a standing faq entry, not engagement. If they found a real
  instrument bug: P4, thank them publicly, fix publicly, converting an attacker into a citation
  is a win condition.
- **P4. Wrong receipt shipped.** Within 24h: correction post (format in gameplan §7.2),
  corrections-log entry, buildlog root-cause line, regression test added. Never delete the
  original; strike-through + link forward.
- **P5. Viral moment.** Do nothing differently. The system does not celebrate, thank, or
  capitalize; it publishes tomorrow's line on schedule (that discipline *is* the story
  journalists write). Your only actions: capacity glance (Vercel/Actions fine at any read
  scale) and screenshot-spoof watch (Constitution xii reply if needed).
- **P6. A member responds/complains.** It is a citable event; the system will measure it
  tomorrow like any other statement. Brand account: at most one reply, receipts link only.
  You personally: do not gloat (Constitution X). That response is the win condition. Treat it as routine.
- **P7. Platform death/ban (Bluesky policy shift, Vercel change, etc.).** Pre-decided:
  dashboard is home, accounts are antennae (gameplan §12). Re-point distribution; the archive
  and site never had a platform dependency.
- **P8. Takedown/legal demand.** Public statements of public officials, transformative
  analysis, disclosed methodology (research R9). Don't panic-delete; consult the attorney from
  the S2 review; respond in writing; document in buildlog. Corrections yes, silent removals no.
- **P9. Model/pricing shift (e.g., Sep 1 Sonnet change).** Quarterly ritual catches it;
  pinned `llm.PRICING` updated in a commit; if a model is deprecated, swap + run the prompt
  regression suite + one dark day comparing outputs before the swap goes live.
- **P10. Motivation dip (it will come, likely post-election).** The design already answered
  this: the weekly 15 minutes is the *whole* job (§3); the archive compounds whether or not
  you're inspired; S∞ has no deadline. Do not make product decisions in November. If you ever
  truly stop: Constitution xiv means stopping is graceful, the repo, data, and runbook are the
  legacy, and they keep working.
- **P11. The sunset (pre-written so the ending is never improvised; Session-8 adjudication).**
  A zombie political bot posting from a half-broken pipeline is the worst available ending; this
  playbook exists so it can't happen. Trigger: Michael decides to stop, or the weekly health
  numbers have been red a full quarter with no session scheduled. Sequence, one sitting: (1) all
  three accounts post the same two-sentence clinical close ("This instrument stopped measuring on
  {date}. The archive, data, and methodology remain public and reproducible at onscript.news."),
  pinned; (2) both workflow crons disabled in the same commit, the site freezes accurately instead
  of rotting; (3) the site gets a dated banner: archive, not instrument; (4) raw + derived data +
  the final ledger released as a versioned archive (Constitution xiv); (5) accounts stay up,
  silent, self-labeled, never deleted (deletion reads as retraction). The corrections log stays
  open one year post-sunset. Nothing else. The ending is a dated public act, like every release
  before it.
- **P12. A scheduled run never started (added 2026-07-25 after the first `startup_failure`).**
  Symptom: an ntfy page titled "OnScript watchdog", or a run in the Actions tab whose conclusion is
  `startup_failure`, `cancelled`, or `timed_out`. In that state GitHub created no job, so the
  in-job dead-man in `collect.yml` and `assemble.yml` could not fire. The page comes from
  `.github/workflows/watchdog.yml`, which watches both pipelines from outside. Sequence: (1) read
  the run page to separate a platform fault from a repo fault. A valid workflow file that ran green
  hours earlier and then failed to start is a GitHub dispatch fault, not a code defect. (2) Do
  nothing if the next scheduled pass is close. The readiness gate takes the oldest not-yet-final
  day, so a missed pass is recovered rather than skipped and the series keeps no hole. (3) If the
  next pass is far off or also failed, dispatch the workflow manually. Check for a pending queued
  run first: with `cancel-in-progress: false` a new run can displace one already waiting. (4) A
  missed publication day is still P1. Log it either way, because a silent recovery still spent a
  day of the streak.
- **P13. Refresh the date-effective roster (added 2026-11-22, S74-13).** The party totals printed
  beside shares ("28 of 259") come from `data/reference/date-effective-roster.json`, a dated copy of
  `unitedstates/congress-legislators`. It goes stale when upstream records a special election, a
  resignation or a party switch, and it stops speaking at its horizon: the day before the scheduled
  end shared by the House terms open on its retrieval day. Past the horizon pages print bare counts
  with no total. Symptom: an ntfy page titled "OnScript watchdog" with a `roster_horizon` alarm
  (14 days or fewer left, or already past), or a seat change you know upstream has listed. A
  refresh changes published numbers going forward, so it is a release. Sequence: (1) take the
  upstream head, `git ls-remote https://github.com/unitedstates/congress-legislators HEAD`, and
  pin its full hash; never a branch name. (2) Build:
  `C:\ProgramData\miniconda3\python.exe scripts\build_date_effective_roster.py --revision <40-hex>
  --retrieved-at <UTC now> --split-party-affiliations --out data\reference\date-effective-roster.json`.
  Provenance records the revision, both source sha256 and `valid_through`; the builder prints the
  horizon. (3) Invariants, in `tests/test_s74_13_roster_refresh.py`, then the full suite: every
  day from `STAGE1_EPOCH` to the horizon seats 425 to 435 voting House offices and 96 to 100
  senators; no office has overlapping intervals; no interval starts on or after its end;
  `valid_through` equals the horizon the intervals derive. A test that pins a total from the old
  snapshot is updated only where the number legitimately changed. (4) Read the diff:
  `C:\ProgramData\miniconda3\python.exe scripts\diff_date_effective_roster.py --old HEAD` prints,
  per party, runs of days with old and new totals and the offices responsible, then every office
  whose intervals moved, including upstream's own historical corrections. Check each named
  office against upstream's term dates and its `how` and `end-type` fields; say only what
  upstream states. (5) Corrections: an entry is needed when any published day's page printed a
  total the refresh changes. The S74-13 measurement,
  `X:\onscript-data\drafts\staged\S74-13\stale.py`, lists those days (only days whose page prints a
  total belong in `affected_days`), compares like with like (audits written before 2026-11-21
  count voting members only; `--voting-only` gives the same population in the diff), and computes
  the largest effect on a printed share by rendering each committed day record against its
  committed audit. Published day records are never rewritten. A refresh that changes only days not yet published needs no entry. (6) Commit,
  then release under the docs/27 order. **The January step.** Upstream ends every open House term
  on the Congress boundary until it lists the new terms, so on the 2026-11-22 snapshot the horizon
  is 2027-01-02 and the watchdog alarms from product day 2026-12-19. From 2027-01-03 pages print
  bare counts. Those days keep bare counts after the refresh, because their audits are not
  rewritten; that is a loss of a total, not a wrong number, so it needs no corrections entry.
  Refresh once upstream lists the 120th Congress, with `--retrieved-at` on a day the new House is
  seated, and confirm the builder prints a horizon of 2029-01-02 before committing; a horizon
  derived while upstream has listed only part of the House is not a full Congress, and the seat
  invariants will fail on it.
- **P14. Refresh the bill-and-committee name index (added 2026-11-22, S74-15).** The name gate
  (`eligibility.classify_phrase`, which feeds Daily Line selection, posting, party columns and
  alerts) reads `data/reference/nomenclature/bill-titles-<congress>.json` and
  `verdicts-<congress>.json`, a dated snapshot. A bill introduced after the snapshot's fetch date
  cannot tag, so its title passes the gate as a message. Symptom: an ntfy page titled "OnScript
  watchdog" with a `nomenclature_index` alarm (the age first exceeds
  `config.NOMENCLATURE_INDEX_MAX_AGE_DAYS`, then weekly), or `nomenclature_index_age_days` in
  `symmetry/<day>.json` above it. A refresh changes selections going forward, so it is a release.
  Sequence: (1) the verdicts are a ratio over the WHOLE congress's statements corpus, so the build
  needs the production corpus (`statements.jsonl.gz` from the `data-latest` release's
  `state.tar.gz`); a local `data/state` is a July copy on the operator machine and must not be
  used (S74-15: 75,989 local rows ending 2026-07-09 against 91,500 in production). (2) The bill
  fetch resumes from its mirror, so point it at an empty root or it rebuilds the old snapshot:
  `$env:ONSCRIPT_DEEP_ROOT = '<empty dir>'`, then
  `C:\ProgramData\miniconda3\python.exe -m pipeline.nomenclature_build --congresses 119
  --skip-committees --corpus <restored>\data\state\statements.jsonl.gz`. (3) Diff old and new names
  and verdicts, measure which published selections the new table classes as official names, and
  draft a corrections entry if any published selection changes. (4) Commit both tables, then
  release under the docs/27 order. The index also moves `nomenclature_index_version` in the
  dark concordance and awards data.

## §5 Doc map, who's who (so nothing gets lost)

| Doc | Role | Changes |
|---|---|---|
| `CLAUDE.md` | Session orientation + **"You are here"** line | Every session |
| `06-CONSTITUTION.md` | What's allowed, check decisions against it | Almost never (Art. XV) |
| `07-OPERATIONS.md` (this) | Where you are, what's next, what to do | Rarely; ladder states tick |
| `03-GAMEPLAN.md` | What v1–v3 *are* (specs, §13 locked decisions) | Frozen; deviations → buildlog |
| `04-BUILDLOG.md` | What happened (sessions, deviations, postmortems) | Every work session |
| `05-HORIZON.md` | What could be next (the Fable reservoir + picking rules) | Quarterly picks |
| `01/02` | History: the vision and the validated reality | Never (reference) |

---

*The machine measures discipline. This doc is ours., ratified 2026-07-11*
