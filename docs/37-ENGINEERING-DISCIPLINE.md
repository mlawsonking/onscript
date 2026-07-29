# 37: Engineering discipline (binding for every implementation session)

Authority: Fable, Session 56, 2026-07-28. This document codifies the failure patterns
found across the W, X, Deep, S1, ANNOT, and Y engineering rounds so that every future
session inherits them as rules instead of rediscovering them as incidents. Every work
order cites this document in its read list. Each rule names the incident that created
it, because a rule whose reason is lost gets argued with.

## 1. Registries are tested against their owners

Every central registry (method versions, schema versions, public strings, feature
flags, API field emitters, threshold readers, privacy canaries, correction
checkpoints) must have a test comparing it against the live owning module, not
against its own copy. A registry tested against itself goes stale silently the first
time a later package moves the authority.
Incident: the instrument fingerprint shipped attesting document-families-v1 and
surface-eligibility-v2 while the live modules said v2 and v3 (docs/36 R-36.1). The
same shape appeared in all three external review rounds.

## 2. Production-shaped tests for production paths

Any package touching restore, collect, assemble, post, publication, or rendering
must include at least one test built from real committed artifacts, not synthetic
fixtures alone. Fixtures prove logic; only production-shaped data proves the
integration.
Incident: the W3 restore check passed every fixture and then killed both production
runs on the first real archive, because every pre-W3 archive carried a tree no
fixture modeled (2026-07-26 outage).

## 3. Committed evidence is pinned history, never compared to the live tree

A committed evidence file records the moment it captured. Tests validate it as a
canonical pinned record (parses, canonical bytes, internal consistency). Asserting
it byte-equals a fresh build from the live tree makes every future production commit
a suite failure.
Incident: the X7 migration-evidence test broke on the first rebase over data commits
and would have broken again daily (S52 validation).
The mirror form is equally binding: a live artifact is never asserted to REMAIN
defective. A test documenting a defect against mutable production files breaks the
moment the fix heals them in production; document defects in fixtures or literals,
and assert the healed invariant against the live tree.
Incident: the Y1 drift-documentation test asserted the 2026-07-25 day and post
fingerprints differ, and failed the day RUN C re-rendered the manifest under the
inheritance fix it documented (S59 validation).

## 4. Fail-closed gates ship with their transition path

A new fail-closed check must enumerate what existing production state looks like on
day one and either tolerate it explicitly or migrate it. Protection belongs in the
narrow mechanism (an allowlist, a merge filter); detection reports loudly and skips.
A gate that dies on expected legacy state is an operator-created outage, and a gate
whose failure blocks the process that would repair its input is a deadlock.
Incident: the W3 restore conflict check raised on every pre-W3 archive, and the
archive could only be rebuilt by a run that got past the check (2026-07-26).

## 5. Timestamps and randomness never enter determinism claims

Anything asserted byte-identical across runs must take its clock as a parameter.
Production callers pass real time; comparison and rebuild paths freeze one value.
No argument-free now() inside any artifact covered by a reproducibility claim.
Incident: the X7 clean-clone drill failed byte identity on exactly two of 809 files
because generated_at was sampled per pass.

## 6. Stamp once, inherit everywhere

An identity computed about a measurement (fingerprint, method version, content
address) is computed once at the stage that owns it and carried byte-identical into
every downstream artifact of that cycle. Downstream stages never recompute identity
against a possibly moved checkout.
Incident: one measured day carried different fingerprints on its day record and its
post manifest because posting rebuilt the fingerprint at a later HEAD (docs/36).

## 7. Identity hashes cover the measurement tree, not the repository

Code identity in any public attestation hashes pipeline code, prompts, configuration,
and schemas. Never repository HEAD: data commits move HEAD without changing the
instrument.
Incident: same as rule 6; a data-only commit changed the alleged instrument identity.

## 8. Time is stated, never implied

Public surfaces name the measured date and its state (current, delayed, degraded,
force-finalized). The word today appears only when the reading is genuinely current
under the docs/36 R-36.4 ladder. Social posts about a delayed day carry the absolute
date.
Incident: the homepage said Today over a force-finalized three-day-old reading while
status was red (third review).

## 9. Models are never called to produce what a template can say

A day with zero code-selected claims renders a deterministic null. Model calls exist
for editorial connective prose over code-selected claims, nothing else. Posting is
state-aware: an empty, degraded, red day does not manufacture party threads.
Incident: two paid model calls produced "we released N statements" nulls that were
then posted as three-day-late threads titled today.

## 10. Long runs are detached, never polled

Any run expected to exceed 10 minutes goes through the harness's detached background
mechanism with output captured to a file. Never a manual nohup (reaped on teardown),
never a polling loop narrating the wait (burns the session's budget watching CPU
time advance).
Incidents: a manually backgrounded CREC build died silently on tool teardown (S51);
the X7 drill wait consumed hours of session loop in one-minute status messages.

## 11. Severity precedence is absolute

Status severities order critical, red, amber, green, neutral, unknown, and a lower
severity never overrides a higher one anywhere in aggregation. Windows for rates are
calendar-defined, and short-window deterioration is never masked by a healthy long
window: publish latest, seven-day, and thirty-day together.
Incident: an open major correction forced overall status amber while a check was
red, and a 48.78 percent seven-day verifier drop hid behind a green 30-manifest
window (third review).

## 12. Loop-local state stays loop-local

Any value computed per iteration (per party, per lane, per day) is bound to its key,
never left in a variable a later loop can silently reuse. When two parties or lanes
could diverge, the acceptance fixture gives them divergent inputs and asserts
divergent outputs.
Incident: the surge baseline's prior_days leaked across party loops (docs/36 Y6).

## 13. Instruments are compared only on one method version

Numbers produced by different normalize or builder versions never appear in one
comparison without the seam being stated. Rebuilding one side of a comparison on a
newer instrument invalidates the comparison, not the sides.
Incident: the E1 scraper-versus-scraped verdict moved because the isolated shards
were rebuilt on the W7/X9 collapse while the folded shards predated it; the move was
a normalize-version artifact, not a finding (S53, ruled S54).

## 14. Mechanical discipline that keeps recurring

- One commit per package; suite green before and after; a blocked package stops the
  sequence with the blocker named, never improvised around.
- Renaming or moving any test updates the W5 fixture registry in the same commit.
- Never git add -A. AGENTS.md and tests/_tmp_watchdog/ stay untracked.
- No em dash (U+2014) in authored prose, comments, or docs. CRLF is preserved;
  append to CRLF files with a CRLF-aware writer, not a bare LF echo.
- Session numbers are claimed by reading the docs/26 tail at session start; parallel
  sessions exist and numbers collide (S51 was taken while S51 was planned).
- Pushes happen in a clean window: nothing queued or in flight, next cron slot not
  imminent. Crons drift up to 90 minutes late; the drift is part of the window math.
- Every measured number carries estimator, unit, window, denominator, and a
  rerunnable command.
- One alert per failure mode: a probe that pages exits 0; its own death is the only
  thing that turns its job red.
- Workflow references key on file paths, never display names; display names are
  prose and get rewritten.
- New scheduled or event-triggered workflow behavior activates on push to the
  default branch: say so in a comment, and treat the push as the release act it is.
- A work order states its push scope exactly once, in one place. The Y session
  received "push only your own branch" in one section and "never push" in another
  and correctly stopped to ask; the ambiguity was the defect, not the question.

## 15. Maintenance of this document

A new incident class earns a rule here in the same delivery that fixes it; the rule
names its incident. A rule that stops being true is amended, not silently ignored.
Work orders cite this document instead of restating it, and the orchestrating
session's validation pass checks deliveries against it.
