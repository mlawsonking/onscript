# 07-OPERATIONS — the state ladder, health numbers, rituals, and playbooks (v1, 2026-07-11)

> **What this is.** The navigation system, written to Michael. At any moment over the next
> year, this doc answers three questions in under a minute: **Where am I? Is it healthy? What
> do I do about the thing that just happened?** Every work session (any model) ends by updating
> the **"You are here"** line in `CLAUDE.md` to the current state on the ladder below. The
> constitution (`06-CONSTITUTION.md`) governs *what's allowed*; this governs *what's next.*

---

## §1 The state ladder — "where am I?"

One state at a time; advance only through the exit gate. If you're ever lost: find your state,
do your job, ignore everything else.

| State | Name | You are here if… | Your job this state | Exit gate |
|---|---|---|---|---|
| **S0** | Built, dark | Machine verified in dry-run; no remote/keys **(← current, 2026-07-11)** | The 90-min errand batch: public repo + push, domains, Bluesky accounts, secrets, Console $10 cap | First cloud **dry-run** RUN A+B green |
| **S1** | Cloud-proven | Workflows green in the cloud, still $0 | Watch 3 consecutive dry-run days; fix YAML friction (Opus session if needed) | 3 green days + Release assets populating |
| **S2** | Live voice, dark | `ANTHROPIC_API_KEY` set; real Daily Lines; accounts unannounced | The dark week: hand-audit 5 receipts/day, tune P2 taste (free now, public diffs later), attorney hour | §1.4.1 gate (3 consecutive unattended real runs) + audits clean |
| **S3** | Launched | Accounts public, launch artifact out | The §9 circuit; then *let the streak work* — your only daily job is the 15-min ritual (§3) | 30 unbroken days AND (first external citation/embed OR 1k combined followers) |
| **S4** | v2 — the insight release | Building silence detector, leaderboard, floor leg, The Archive/Alexandria | Opus sessions against gameplan §10 v2; chapters via `claude -p` (before Sep 1) | v2 acceptance (gameplan §10) |
| **S5** | v3 — the coordination release | Building alerts, Memory Hole, upstream graph, bill-brands, API | Opus sessions against §10 v3 | v3 acceptance, by Oct 5 |
| **S6** | Election mode | Oct 15 – Nov 10, 2026 | **Freeze** (Constitution VIII); daily receipt spot-checks; capacity watch; prep the retrospective | Retrospective artifact ships ≤7 days post-election |
| **S7** | Season 2 | Jan 2027: new Congress | Assimilation curves live; State of the Script #1; Mirror Test | Annual report shipped |
| **S∞** | Steward | Ongoing | Quarterly HORIZON pick (05 §3 rules); the machine compounds | — (this is the destination) |

Skipping states is prohibited. Regressing (e.g., streak broken in S3) means: run the relevant
playbook (§4), file the postmortem, resume the same state — the ladder position doesn't reset.

## §2 The five health numbers — "is it healthy?"

Read weekly (or from the Owner's Brief, §3). Green/red thresholds are deliberately crude —
they exist so you never have to *interpret* on a tired Monday.

1. **Streak** — days since last missed publish. Green: unbroken. Red: any miss → Playbook P1.
2. **Spend (MTD, projected)** — manifest `est_cost_usd` sum. Green: ≤ $8 projected. Red: governor already degraded twice this month → decide: raise cap or ride degraded (your call, one line in BUILDLOG).
3. **Coverage** — Lane-1 statements vs. trailing median, per party, + upstream freshness. Green: both parties ≥ 60% of trailing 14-day median and upstream < 36h stale. Red → Playbook P2.
4. **Verifier drop rate** — claims dropped ÷ claims published, 7-day. Green: < 25%. Red (sustained rise): upstream text quality shifted or prompt drift → Opus session, don't hand-tune.
5. **Reach** — followers + site sessions + citations/embeds (count monthly, not daily; vanity is a monthly vitamin, not a daily meal).

Numbers 1–4 are machine-readable today (manifests + symmetry reports). **The Owner's Brief**
(small v2 item, spec below) turns them into a push notification so "understanding where I'm
at" costs zero clicks.

## §3 Rituals — the entire human cost of stewardship

- **Weekly (Monday, 15 min):** read the five numbers · skim both Daily Lines with your editor
  hat (true is guaranteed; you're checking *funny/fair*) · glance at the best chart · anything
  odd → one line in `04-BUILDLOG.md`. That's it. **This ritual is the minimum viable
  stewardship: if life gets loud, do this and nothing else — the machine runs without you.**
- **Monthly (1st weekend, 1 hr):** spend vs. cap · coverage trend · prompt-diff review (should
  be empty or justified) · ladder check: still in the right state? · pick/adjust next state work.
- **Quarterly (2 hr):** re-verify Anthropic pricing + model IDs (model swap = regression-test
  day, never a silent change) · `congress-press` commit cadence check · Internet Archive
  snapshot (Constitution XIV) · constitution read-through · HORIZON pick session (05 §3 rules).
- **The Owner's Brief (v2-small, spec):** RUN B appends a Monday ntfy/email: the five numbers,
  streak count, top phrase of the week, any degraded days, any pending decision flagged by the
  governor. The system reports to its owner; the owner never has to remember to ask.

## §4 Playbooks — "the thing just happened"

- **P1 — Missed day.** Read manifests → identify stage → fix or file Opus session → **public
  postmortem post from the brand account** (clinical, 2 sentences) + BUILDLOG entry. The
  postmortem *is* the brand: instruments that admit failure get believed.
- **P2 — Upstream stale/dead.** <36h: nothing (dead-man already logged it). 36–72h: verify
  their repo/Actions manually. >72h: promote the cold-standby fork (one cron flip, tested),
  courtesy-note the maintainer, disclose on methodology until healthy.
- **P3 — Bias siege.** Reply once, with links: methodology + that day's symmetry audit + the
  prompt history. **Never argue past the first reply** (Constitution X). Sustained bad-faith
  campaigns get silence and a standing FAQ entry, not engagement. If they found a real
  instrument bug: P4, thank them publicly, fix publicly — converting an attacker into a citation
  is a win condition.
- **P4 — Wrong receipt shipped.** Within 24h: correction post (format in gameplan §7.2),
  corrections-log entry, BUILDLOG root-cause line, regression test added. Never delete the
  original; strike-through + link forward.
- **P5 — Viral moment.** Do nothing differently. The instrument does not celebrate, thank, or
  capitalize; it publishes tomorrow's line on schedule (that discipline *is* the story
  journalists write). Your only actions: capacity glance (Vercel/Actions fine at any read
  scale) and screenshot-spoof watch (Constitution XII reply if needed).
- **P6 — A member responds/complains.** It is a citable event; the system will measure it
  tomorrow like any other statement. Brand account: at most one reply, receipts link only.
  You personally: do not gloat (Constitution X). This is the win condition — treat it boring.
- **P7 — Platform death/ban (Bluesky policy shift, Vercel change, etc.).** Pre-decided:
  dashboard is home, accounts are antennae (gameplan §12). Re-point distribution; the archive
  and site never had a platform dependency.
- **P8 — Takedown/legal demand.** Public statements of public officials, transformative
  analysis, disclosed methodology (research R9). Don't panic-delete; consult the attorney from
  the S2 review; respond in writing; document in BUILDLOG. Corrections yes, silent removals no.
- **P9 — Model/pricing shift (e.g., Sep 1 Sonnet change).** Quarterly ritual catches it;
  pinned `llm.PRICING` updated in a commit; if a model is deprecated, swap + run the prompt
  regression suite + one dark day comparing outputs before the swap goes live.
- **P10 — Motivation dip (it will come, likely post-election).** The design already answered
  this: the weekly 15 minutes is the *whole* job (§3); the archive compounds whether or not
  you're inspired; S∞ has no deadline. Do not make product decisions in November. If you ever
  truly stop: Constitution XIV means stopping is graceful — the repo, data, and runbook are the
  legacy, and they keep working.

## §5 Doc map — who's who (so nothing gets lost)

| Doc | Role | Changes |
|---|---|---|
| `CLAUDE.md` | Session orientation + **"You are here"** line | Every session |
| `06-CONSTITUTION.md` | What's allowed — check decisions against it | Almost never (Art. XV) |
| `07-OPERATIONS.md` (this) | Where you are, what's next, what to do | Rarely; ladder states tick |
| `03-GAMEPLAN.md` | What v1–v3 *are* (specs, §13 locked decisions) | Frozen; deviations → BUILDLOG |
| `04-BUILDLOG.md` | What happened (sessions, deviations, postmortems) | Every work session |
| `05-HORIZON.md` | What could be next (the Fable reservoir + picking rules) | Quarterly picks |
| `01/02` | History: the vision and the validated reality | Never (reference) |

---

*The machine measures discipline. This doc is ours. — ratified 2026-07-11*
