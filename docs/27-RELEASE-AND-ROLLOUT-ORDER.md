# 27: Release and rollout order (binding)

Authority: Fable, Session 45, 2026-07-23. Requested by Michael through the implementation
agent. This order takes the project from its present local state to a deployed, publicly
verified release, then through the feature and editorial calendar to the election freeze.
It adjudicates; it does not implement. Release acts (push, deploy, flip, post, publish)
remain Michael's throughout. Where this order and an older document conflict, this order
states the conflict and rules on it. Settled rulings in docs/24 and docs/25 are not
reopened.

Baseline verified 2026-07-23 between 17:00 and 17:40 UTC by direct inspection: repository,
commit stack, configuration, workflows, live site fetches, scheduled-run history, release
assets, and the operator task list. The suite passed 479 of 479 at local HEAD on the house
runner.

## 1. Verified baseline

Live in production: the site, daily posting for both party accounts, party_columns,
owners_brief, phrase_search, four green scheduled runs per day, and the data-latest
release carrying raw.tar.gz and state.tar.gz.

Local only, nothing pushed: 17 commits on main. Three segments, in order: the
stabilization packet and its remediation (7 commits, "docs(fable): S43" through
"fix(site): protect core build from evidence failures", currently 4c16703); wave 2 and its
riders (5 commits through "fix(site): close wave two validation riders", currently
166b4de); the voice ruling and rewrite (5 commits through "docs(voice): finish subsystem
and corpus consistency", currently 6096ecf). The only untracked file is AGENTS.md.

Built dark, validated, awaiting flips: nomenclature_tags, archive, duet, awards,
authors_vessels, concordance. Partially ready: silence_board (module exists; no caller;
data/derived/silence/ has never been built). Not built: floor, credit_claim,
memo_cadence_flag, and every v3 flag.

Conflicts found between documentation and reality, ruled on below:

1. The remote moved. origin/main is at 6871440 (today's data commits); the local cache
   still points at f8b77e4. The stack must rebase before any push. The "17 ahead" count
   was measured against the stale cache.
2. The live site contradicts itself. About says the accounts "have not begun posting"
   while posts.html lists posts through 2026-07-22. Phrase pages still show pre-epoch
   dates and bare bioguide identifiers. The local stack fixes all of this; every day
   unpushed extends a false public posture. This makes the first push urgent.
3. Voice-rewrite compliance gaps. One U+2014 survives in plain prose (docs/06, the
   Article XIV title line) and the exception list required by docs/25 §5 gate 2 was never
   written. Twelve U+2014 survive corpus-wide; the other eleven sit inside code fences or
   inline code and are legitimate.
4. docs/23 §7.3 still lists phrase_search on 08-17. It shipped at launch under the §7.5
   amendment. The 08-17 row governs duet alone.
5. Freeze dates disagree. docs/06, docs/07, and docs/20 say Oct 15 through Nov 10.
   docs/23 says "~Mon 10-12". Ruled in §4.

## 2. Release sequence

Steps run in order. A step's failure stops the sequence at that step. No manual workflow
dispatch anywhere; scheduled runs are the only production exercise. Clean push window:
gh run list shows nothing queued or running, and the next cron slot (09:30, 11:30, 19:30,
21:30 UTC, all drifting up to two hours late) is not imminent. Waves are not combined to
recover time.

### R0. Voice compliance fix (implementation agent, may run first or parallel to R1)

Change: replace the docs/06 Article XIV title em dash with a colon (punctuation only,
allowed under docs/25 R-V2.1; title wording unchanged). Append the em-dash exception list
to docs/25 as a short appendix: file, line, and reason for each surviving U+2014 (eleven
after the fix, all in code contexts). One commit.
Validation: suite green; corpus U+2014 count outside code contexts is zero.
Stop: none. Evidence: the appendix itself plus before and after counts.
Proceed: R1 may run regardless; #197 review cannot close without R0.

### R1. Rebase onto the live remote (implementation agent)

Precondition: R0 committed or explicitly deferred by Michael.
Change: git fetch origin; git rebase origin/main. Expect a clean rebase: the local stack
touches no generated trees and the remote gained only data commits. All 17+ SHAs remap;
from here, commit subjects govern, not the SHAs quoted above.
Validation: rebase completes without conflicts; suite 479 of 479 on the house runner;
git status clean except AGENTS.md; record the new SHA map in the evidence.
Stop: any rebase conflict. Do not resolve conflicts inside data/ or site/public; stop and
report.
Rollback: git rebase --abort restores the pre-rebase stack.
Evidence: SHA map, suite output.
Proceed: R2 when green.

### R2. Push the stabilization prefix (Michael)

Precondition: R1 green; #195 review done; clean push window.
Act: push through the rebased "fix(site): protect core build from evidence failures"
commit. Nothing above it.
Validation: push is a fast-forward; Vercel deploys.
Stop: non-fast-forward (means the remote moved again; rerun R1).
Rollback: none needed; the push is the smallest reviewed unit.
Evidence: the pushed SHA, deploy confirmation.
Proceed: R3 begins with the next scheduled runs.

### R3. Production exercise of the stabilization stack (scheduled automation; Michael reads)

Precondition: R2 pushed before a collect+assemble pair.
Validation, collect run: green; the phrase-evidence bootstrap appears in the log; step
time within the ruled budget (bootstrap under 15 minutes once, steady state under 60
seconds after).
Validation, assemble run: green; two site renders in the log; the day's post manifest and
a posts.html carrying that same run's thread land in the same data commit.
Validation, live surface: About no longer claims the accounts have not posted; the three
account links resolve; the sampled phrase page shows no pre-epoch date and no bare
bioguide; phrase pages with quorum show the peak-day evidence section; the search index
carries no pre-epoch rows; the retired stale phrases return zero hits against production
HTML.
Stop: any red run, any dead-man fire, or any live-surface check failing.
Forward-fix rule: diagnose before touching anything; a red caused by the new code gets a
minimal fix commit reviewed like any packet; never revert the data commits of a green day.
Evidence: run URLs, log excerpts, live fetch results, one evidence table row per check.
Proceed: R4 after one fully green day (both runs) with all live checks passing.

### R4. Push wave 2 (Michael)

Precondition: R3 complete; clean window.
Act: push through the rebased "fix(site): close wave two validation riders" commit.
Validation next runs: green; feed.xml, sitemap.xml, robots.txt live and well-formed; feed
entries carry counts only; accessibility landmarks and 404 live; favicon present; posting
still flushes its manifest in CI (the W2-A inverse, proven by the day's manifest and
posts.html updating as in R3).
Stop and forward-fix: as R3.
Evidence: as R3 plus the feed and sitemap fetches.
Proceed: R5 anytime after R4 is pushed; R6 clock starts at R4's first green day.

### R5. Push the voice stack (Michael)

Precondition: #197 review done (stage evidence plus R0); R4 pushed; clean window.
Act: push through the rebased voice commits (documentation only; no runtime effect).
Validation: next run green (unchanged behavior expected); site unaffected.
Evidence: pushed SHA.
Proceed: immediately; R6 continues.

### R6. Green-day accumulation (scheduled automation)

Requirement: two consecutive fully green days (four runs) on the complete pushed stack,
live checks holding, before the first feature flip. Days already accumulated under R3 and
R4 count if nothing changed above them.
Proceed: R7 on the first Monday satisfying this and the docs/23 health gate.

### R7. First flip: nomenclature_tags (Michael, Monday, docs/23 §7.3 health gate)

Target Mon 07-27. Viable only if R2 through R4 land by Friday 07-24 evening and R6 is
satisfied Monday morning. Otherwise it slips per §4 rule 2. Flip validation: tags render
symmetric; flag-off regression tests stay green; the day after the flip is green.

### R8. Rollout continues per §4 and §5

One flip per Monday, each under the docs/23 health gate, silence_board under its own
auto-slip rule. No gate is weakened to hold a date.

## 3. Production acceptance gates

The current stack is "hardened and deployed" only when every row below has proof attached.
A green deployment alone is not acceptance; the public site must visibly show the fixes.

| Claim | Proof required |
|---|---|
| Suite floor | House runner (C:\ProgramData\miniconda3\python.exe tests\run_tests.py) 479+, zero failures, at the pushed SHA |
| Privacy and secrets | Privacy suite 15 of 15; secret-signature scan zero hits; pipeline.redact --check clean on fresh assets |
| Worktree hygiene | git status clean except AGENTS.md; no locally regenerated site/public or data/derived committed |
| Public posture | Live About, Methodology, posts pages carry the corrected copy; account and repository links resolve |
| Same-run archive | One production assemble whose data commit contains both the day's post manifest and a posts.html listing that thread |
| Temporal honesty | Live phrase pages and search index show no pre-epoch statistic, date, or bare bioguide |
| Receipts | A quorum phrase page shows at least three member receipts with working source and Wayback links; a below-quorum page shows no evidentiary claim |
| Phrase-evidence cost | Collect log: bootstrap once under 15 minutes; steady state under 60 seconds |
| Discovery surfaces | feed.xml validates and carries counts only; sitemap matches rendered pages; robots resolves |
| Accessibility | Landmarks, skip link, SVG titles, 404, favicon verified on the live site; no horizontal overflow at 390 px |
| Symmetry | Nightly symmetry audit clean; D and R rendered with equal weight on every checked page |
| Scheduled runs | Two consecutive fully green days on the final stack; run URLs retained |
| Release assets | data-latest assets rebuilt post-push and redaction-checked |

Michael retains the completed table with links as the release record, in docs/26.

## 4. Calendar reconciliation

Rulings, from the verified extracts of docs/06, 07, 20, 23:

1. Jul 27 nomenclature_tags: conditional go. Requires R2 through R4 pushed by Friday
   07-24 evening, two green days, and the Monday health gate. Miss any and it slips.
2. Slip rule for flips: a missed Monday flip moves to the next Monday and pushes every
   later flip back one week. Two flips never share a Monday. The Aug 31 editorial lock
   and the freeze dates do not move. If cumulative slips would push concordance past
   Mon Oct 5, concordance drops to post-freeze rather than compressing gates.
3. phrase_search: live since launch. The 08-17 row governs duet alone. docs/23 gets a
   one-line correction at its next edit; no separate commit needed for this.
4. Aug 3: archive flips (its coverage gate: era chapters verifier-clean, the 3,000
   statement floor per era, cross-era claims machine-gated). Silence-board wiring must
   also land by Aug 3 as dark accumulation; that is build work, not a flip (task #198).
5. Aug 10 silence_board: governed by the docs/23 auto-slip rule. Not accumulating by the
   08-03 digest means week-by-week slips until it is.
6. Aug 24 awards: ships whole or slips with silence_board. The Void must be live-fed at
   flip; a data-starved Void does not launch.
7. Aug 31 authors_vessels flips and all Sep and Oct editorial pieces lock. The lock is a
   commitment.
8. Sep 7 concordance: last scheduled flip. Requires confirmation that production emits
   concordance.json and awards.json in-process (read one production run's log or
   artifacts before the flip; noted open in docs/26).
9. Freeze dates: the constitution governs. Freeze is Oct 15 through Nov 10 (docs/06
   Article VIII; docs/07 agrees; docs/20 agrees). docs/23's "~Mon 10-12" survives as an
   operational buffer, not a competing freeze date: last possible flip Monday is Oct 5;
   from Mon Oct 12 the project is quiet (no flips, no new backward-looking claims, Oct
   pieces already published); the constitutional freeze begins Oct 15. Nothing in the
   buffer weakens Article VIII.
10. Commitments: freeze dates, the Aug 31 lock, the silence-board wiring deadline, one
    flip per Monday, every health gate. Targets: every individual flip and publication
    date.

## 5. Feature classification

Ready to flip under the standing health gate: nomenclature_tags (07-27, conditional per
§4.1); duet (08-17); authors_vessels (08-31).

Ready after a named validation: archive (coverage gate plus a post-flip check that
phrase-page temporal disclosures and archive pages tell one consistent story);
concordance and awards (production emission of concordance.json and awards.json confirmed
from a run log before their Mondays); awards additionally requires the silence substrate
(§4.6).

Requires implementation, scheduled: silence_board wiring. Internal Opus build session,
task #198, deadline Aug 3. Packet: call silence.silence_board()/build_day_board() from
the daily deterministic build; skip-and-log so a GDELT outage cannot cost the day's core
artifact; boards accumulate dark under data/derived/silence/; GDELT stays Lane 2
(enrichment, never a comparative denominator); flag-off means zero public bytes, locked
by a regression test; failure tests cover outage, malformed feed, and empty-day cases;
acceptance is boards building in production by the 08-03 digest.

Requires accumulated production data: silence_board (one week of boards before flip),
awards Void (three weeks).

Requires implementation, unscheduled (no date, needs its own ruling before work starts):
floor (needs render and coverage metric; the 95 percent attribution gate stands),
credit_claim, memo_cadence_flag.

Deferred to Season 2, after the freeze: memory_hole, off_script_alerts, upstream_graph,
bill_brand, public_api, eval_table, phrase lifecycle, response clocks, frame pairs, Time
Machine (all v3, zero code exists; the v3 acceptance gates in docs/03 §10 stand). P3
share cards stay deferred per docs/24. No recurring LLM cost may be added anywhere
without a separate ruling.

## 6. Editorial publication order

Standing gates apply to every piece: receipts, symmetric framing, correlation labels,
neutrality review before lock, Michael's byline and publication act. Lane rules per the
constitution: Lane 1 only for cross-party numbers. HELD and ARTIFACT results never become
headlines.

| Piece | Status | Remaining gates | Date |
|---|---|---|---|
| P1 Self-Audit (S1.9) | Confirmed, twice, nomenclature-robust | Editorial pass, neutrality review | ~Aug 5 |
| P2 Boogeyman (S2.9) | Confirmed, 14 of 14 years | Power-position reframe check, neutrality review | ~Aug 19 |
| P3 Friday Night Dump (S4.4) | Refuted with positive control; publishable null | Frame as null with the pre-registration hash shown | Sep |
| P4 Great Intensification (S1.1'/S1.3') | Confirmed within propublica lane only | Two-panel per-lane framing mandatory; Fable plus neutrality review of the draft (the refuted-to-confirmed rule); density caveat disclosed | Sep, locked by Aug 31 |
| P5 Autumn, not elections (S1.10) | Artifact, robust reframe | Its own pre-registration for the autumn framing before publication; neutrality review | Oct, locked by Aug 31, published by Oct 9 |
| P6 90-day snap (S1.6) | Refuted as timeless; confirmed recent-cycle, propublica lane | Within-lane framing; the underpowered scraped lane disclosed | Oct, locked by Aug 31, published by Oct 9 |
| Concern Conversion (S5.2) | Finding, review pending | Fable plus neutrality review; tier advance | Q1 2027, not before freeze |
| Minority persistence (HX.4/HX.4-D) | Parent confirmed; precondition HELD | Does not advance. No publication. The number stands unpublished | none |
| Leadership origin (S1.12) | Refuted, both lanes | Graveyard shelf entry, not a headline | Dec annual |
| Safe seat (S3.7) | Refuted, powered House cells | Graveyard shelf entry, not a headline | Dec annual |
| Artifacts (S1.1, S1.3, S1.8, S1.10, S4.2, HX.5) | Artifact or refuted-by-placebo | Graveyard and methods shelf only | Dec annual |
| P7 retrospective, P8 Provenance Seam, P9 graveyard annual | Planned | Drafted during freeze, published after Nov 10 | Dec |

## 7. Authority and task map

Implementation agent (Codex), all local, no release acts: R0 (voice fix commit), R1
(fetch, rebase, suite, SHA map). Nothing else is open to the implementation agent under
this order.

Michael only: R2, R4, R5 pushes; every flip; every publication; the acceptance table.
Existing tasks cover this: #195 (stabilization review and push, now including R3 and R4
reads), #197 (voice review and R5 push), #105 and #110 (attorney and operator-protection
work, unchanged). One new task was needed and filed: #198, starting the silence-board
wiring session, because #105/#110 are attorney acts and #195/#197 are release reviews;
none covers scheduling an implementation session with an Aug 3 deadline.

Scheduled automation: R3, R4 validation runs, R6 green days, and every daily run
thereafter.

Internal Opus sessions, not the implementation agent: silence-board wiring (#198), the
production-emission check before 09-07, floor and any unscheduled build work after its
own ruling.

## 8. Definition of done

Release stack complete: every §3 row proven, two green days on the final stack, evidence
table retained in docs/26.

First feature wave complete: nomenclature_tags live and green for a week; archive live
with its coverage gate proven; silence boards accumulating in production.

Pre-freeze product complete: every scheduled flip through concordance live or explicitly
slipped past freeze by rule; Sep and Oct pieces locked by Aug 31 and published by Oct 9;
no open P0; weekly health numbers green.

Freeze entered safely: last flip no later than Mon Oct 5; quiet from Mon Oct 12;
constitutional freeze Oct 15 through Nov 10 with daily runs, dead-man, and the weekly
ritual as the only activity; no prompt, threshold, schema, or flag changes.

Season 2 ready: freeze exited clean; December pieces published; the v3 queue and floor
work re-ruled with fresh priorities; the acceptance record archived in docs/26.

## 9. Work description for the implementation agent

You may: (1) make the R0 commit: fix the docs/06 Article XIV title em dash to a colon and
append the em-dash exception list to docs/25 (file, line, reason for each survivor);
(2) run R1: git fetch origin, git rebase origin/main, resolve nothing inside data/ or
site/public (stop and report instead), rerun the house runner expecting 479 plus any R0
delta with zero failures, and deliver the old-to-new SHA map plus a short evidence table.
Commit documentation and the R0 change only. Leave the tree clean except AGENTS.md.

You may not: push, deploy, dispatch any workflow, post, flip any flag, change any prompt,
threshold, schema, workflow, or generated file, or start feature work. Every push and
every flip in this order is Michael's, in a clean cron window, in the R2 through R8
sequence. Wiring silence_board is assigned to an internal session under task #198, not to
you.
