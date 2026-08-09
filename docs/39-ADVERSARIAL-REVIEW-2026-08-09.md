# 39: Adversarial review, 2026-08-09

Authority: Fable, adversarial review session, 2026-08-09, requested by Michael in session.
Method: five parallel read-only audit lanes (market and strategy; CI and security; pipeline code
and the full suite; data integrity with live citation fetches; docs, governance, and schedule)
plus direct inspection of the live site, origin/main at 7784628, the workflows, the task bus, and
the Bluesky and GitHub APIs. Nothing in the repository was modified by the review. This document
claims no session number: the docs/26 tail is forked (two Session 61s, two Session 62s across
refs), and renumbering belongs to the consolidation merge.

## 1. Verdict

Not pointless. The instrument is real, novel, honest, and cheap, and the niche is genuinely
unoccupied: nobody else publishes daily, symmetric, citation-forced measurement of coordinated
congressional language. The closest neighbor, Dartmouth PRL's America's Political Pulse,
classifies the tone of individual statements and does not measure phrase coordination, composite
voices, or silence. But after three weeks public the audience is approximately zero (about two
genuine human followers across the three accounts, zero stars, zero repo views in fourteen days,
zero third-party mentions, one dataset download, no analytics, no contact address), and since the
stack deployed on Jul 24 the recorded work has run roughly seven parts process to one part product
to zero parts distribution. The binding constraint is no longer instrument quality. It is that
nobody has been shown the instrument, and the features that would make it quotable are dark and
behind their own calendar. The project is a cheap option that appreciates daily; options only
expire worthless when never exercised, and the exercise window is the nine weeks to Oct 12.

## 2. Scorecard

| Lane | Grade | One line |
|---|---|---|
| Code quality | A minus | Verifier, privacy, posting are defense in depth; stdlib-only daily path; 903 of 904 green |
| Data integrity | B, one P0 | Fresh, continuous, privacy-clean, honest status; the core 3-unit claim breached on 3 live pages |
| CI and reliability | B | SHA-pinned, least privilege, layered dead man; collect growth curve and unprotected main are the risks |
| Governance value | B, trending negative | Symmetry, privacy, evidence mechanically enforced; the apparatus now consumes the calendar |
| Schedule execution | D | 0 of 3 flips, 0 essays, 0 human pushes since Jul 31 |
| Distribution | F | 2 human followers, 0 stars, 0 views, 0 mentions, no analytics, no contact |

## 3. Findings

### P0, integrity

**C1. The citation quorum is satisfied by a double-counted joint release on three live pages.**
Phrase pages 007eacff261c652d, 2dc5adb851e6e29d, and e0b16e162cdabc40 each claim grounded_units 3,
the exact floor, and two of the three receipts are the same near-duplicate joint announcement
(the Cortez Masto and Rosen offices rendering one 2026-07-09 Nevada airports release, name order
swapped). Root cause: pipeline/phrases.py and phrase_evidence.py key units on joint_group or
bioguide, but normalize.py assigns joint_group only for byte-identical text; near-duplicates form
document families that never reach the unit key (2,851 near_joint_groups in the 2026-08-09 collect
manifest). Exposure: 89 of 540 evidence entries carry an uncollapsed same-day cross-named pair
(about 16 percent); the other 86 stay above quorum after collapse. This violates the standing rule
that joint and cosigned releases count once through the project unit key, on the exact claim the
product's brand rests on. Fix: fold the family identity into the unit key, rebuild evidence,
append corrections for the three pages. Task #259.

### High

**H1. Distribution is zero and the funnel is uninstrumented.** Numbers above. No analytics of any
kind, no contact email, feeds exposed only as link headers, the API self-labeled experimental and
unlinked, bot accounts that never engage and have DMs off, and a SERP owned by an unrelated
call-center SaaS (OnScript AI). Even a real audience would be invisible today. Task #260 plus the
data-page work below.

**H2. The governance and session record has forked across four unmerged local branches.**
origin/main tail is S63; fable/s61-consolidation carries a second Session 61 plus the S60 rater
work and the only copy of the mechanized governance guard (origin/main has no .claude tree at
all); opus/collect-perf claims a second Session 62 and holds the durable collect-timeout fix while
production rides a doubled 240-minute bridge; opus/goldset-pilot-processing (13 commits) holds the
classifier floor audit (docs/38) and pilot salvage; opus/s65-voice-status (worked 2026-08-08)
holds the deterministic-composite digit whitelist and the recalibrated status alarms. Roughly 19
commits exist only on one disk, unpushed.

**H3. The classifier floor is not a floor, and it tops the front page.** docs/38 (Session 64,
unmerged): the message class admits 59.5 percent of published claims and 68.2 percent of the
synchronization table; six or seven of the twelve most-shared claims are misclassified ("after the
supreme court" counted as a 53-member message; bill titles as messages); about a fifth of
published claims are broken fragments. Live 2026-08-09: the top Democratic "message" is the press
boilerplate "statement after voting against", plus "1 8 billion" (a shredded dollar figure). The
fix path is the gold-set pilot (#216, pass 2 in flight) feeding the R-33.2 ruling; no ad hoc
threshold edits.

**H4. Stored XSS in the dark concordance render.** site.py _concordance_column interpolates the
citation URL with a scheme whitelist but no esc(); every sibling live path escapes. Reproduced
attribute breakout. Latent until FEATURES["concordance"] flips, which is the flip this review
recommends protecting. One-line fix plus poisoned-URL tests. Task #259, before the flip.

**H5. main is unprotected while three workflows push to it daily with contents: write and Vercel
autodeploys.** Secret scanning, push protection, and dependabot are all disabled (free on public
repos). A leaked token is an unreviewed write to the published record and the live site. Task #260.

**H6. Collect wall time is on a monotonic growth curve.** 35 minutes on 07-12, 101 on 07-27,
127 to 136 sustained since 07-30; two runs died at the old 120-minute ceiling on 07-28 and 07-29;
the bridge raise to 240 is explicit in collect.yml. The durable fix sits unmerged on
opus/collect-perf. Assemble already queues behind collect through the shared concurrency group,
drifting the daily schedule later.

### Medium

**M1. First-carrier attribution is dead on 88 percent of phrase pages** (553 of 627 say "member
name unavailable"; zero name an office). roster.json is not reaching the RUN B render; site.py
falls back silently. Truthful wording, dead feature. **M2. Methodology describes Lane 2 in the
present tense while it is empty in production**; the corpus is 100 percent Lane 1 press releases,
which is the good outcome for symmetry and deserves saying plainly. **M3. The homepage honesty
note contradicts the page it sits on** (says the model voice is "not wired in" while the other
party's line shows generator sonnet_direct, generated_verified; LLM_VOICE_ENABLED has been true
since 07-14), an Article XVII class defect. **M4. The governance guard leaks on alternate
spellings** (verified by running decide()): shell writes to protected files pass, git -C defeats
the git rules, gh variable set POSTING_ENABLED is ungated outside the freeze window, refspec force
push only asks. **M5. The status page has been red on alarms the s65 branch shows are
miscalibrated** (drop-rate verdicts over tiny denominators; the volume alert reading a day that is
still landing), pausing the Monday flip gate. **M6. Aging operator-only items:** external
heartbeat #203 unregistered eleven days after the outage that argued for it; #218 blocking the
prompt upgrades; attorney #110/#105 three weeks past waiver; #198 stale-open with its acceptance
criterion met; the GitHub server-side history purge tracked nowhere.

### Low

discipline.json ships floorless 1.0 indices from 3-statement days in the public repo artifact
while its withdrawal is recorded in a different file, and its window starts two days before
STAGE1_EPOCH. assemble.yml interpolates a dispatch input into a run block (write-access only). A
congressional staffer's work email is committed in the sealed goldset bundle HTML (from a public
press release; the seal complicates scrubbing, see exclusions). post.yml keys on the assemble
display name, so a rename silently stops posting. tests/_tmp_watchdog is a dead relic. Two
operator-path files remain on main. The composite voice generated and verified on only 2 of 16
sampled party-days (Jul 26 to Aug 8), an August-recess eligibility effect, honestly labeled.

## 4. What is genuinely strong

The verifier survived adversarial pressure (typography folding, token-aware contiguous-run
containment, joint-aware dedupe, mutation battery), and an independent live spot-check matched 6
of 6 phrases exactly against their cited sources. Posting is atomic with bilateral holds and
refuses to splice re-authored threads. The privacy floor is fail-closed, HMAC-salted, and leaked
zero bioguide tokens across 673 rendered files; it has failed closed in production twice, which is
the gate working. Reliability genuinely defends against "green but empty". The daily path is
stdlib-only with SHA-pinned actions, least-privilege tokens, and no fork-PR secret exposure. The
epoch rule, denominator labeling, corrections culture, and the honest red status page all check
out. Actual model spend is around fifty cents a month against the ten-dollar ceiling. The niche is
confirmed unoccupied. The system survived a registrar suspension, a privacy-gate outage, and
timeout kills without losing a day of data or posting.

## 5. The pattern to break

Since Jul 24: three external review rounds in four days, 36 remediation packages, and four
production incidents caused by the hardening waves themselves, against zero flips, zero essays,
zero distribution, and a P1 draft untouched since Jul 19. The apparatus is load-bearing where it
touches the daily instrument and net-negative where it touches the calendar. The instrument
already clears the bar that matters (it survives scrutiny). The scarce resource is the operator's
Mondays, roughly nine of them, against seven dark flips, six essays, an Aug 31 lock, and the Oct
12 quiet wall.

## 6. Recommendations

This week: (1) one consolidation merge (collect-perf, s65-voice-status, s61-consolidation, goldset
riding along; renumber sessions in one commit; single-headed docs/26); (2) the S66 integrity order
(#259: joint-collapse fix, concordance escape, roster fix, self-description copy, discipline.json
honesty); (3) the thirty-minute hardening errand (#260: ruleset, secret scanning, push protection,
analytics, contact email). Before September: flip triage that protects concordance above archive,
awards, and authors_vessels combined, and flips nomenclature_tags early because it gates every
coordination headline claim; a linked data page, a five-line codebook, a Zenodo DOI, one Data Is
Plural submission; ship P1 and P2. Before Oct 12: pre-pitch a Nov 12 post-election retrospective
to about five named recipients; the freeze is the pitch (thresholds locked Oct 15, untouched
through election day). Framing rule: never headline account-level propagation without the roughly
94 percent Democratic Bluesky disclosure; cross-party numbers stay Lane 1.

Explicitly not now: v3 features, new governance documents, further external review rounds,
Alexandria expansion, X or Truth Social ingestion research, engagement features.

## 7. Kill criteria, revisited around Dec 15

Park the build hours (never delete; the pipeline keeps accruing at about ten dollars a month) if
all of: five real pitches produce zero pickups and zero inbound; analytics, once installed, show
under roughly 500 organic uniques Oct 1 to Dec 1; third-party mentions remain zero; concordance
missed Oct 5 and Republican sub-threshold days stayed the norm. The only pointless version of this
project is the one where the instrument keeps being perfected and never shown.

## 8. Method notes and limits

Release asset contents were not downloaded (metadata only). The Bluesky search endpoint is
auth-gated, so mention-scanning there relied on follower and engagement data. Vercel analytics are
not installed, so no visitor data exists to audit. Two subagent claims were corrected against
origin/main before this record: collect.yml carries timeout-minutes 240 (not 120, a stale-branch
read), and post.yml was created in W11, so no posting outage preceded it. The in-flight blind
annotation (#216) was respected: no sealed or in-progress label file was opened; classifier
statements above cite only committed public measurements (docs/38 and the live surface), which the
pilot record already discloses as priors.
