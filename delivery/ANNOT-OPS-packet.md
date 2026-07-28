# Annotation-operations work-order delivery packet

Branch: `opus/annotation-ops`

Base: `e87e110` (main at the S57 ruling that carries this work order).

Validation command for every package:

```text
C:\ProgramData\miniconda3\python.exe tests\run_tests.py
```

The suite baseline was 774 passed and 0 failed. The final result is 814 passed and 0 failed.
No push, deployment, workflow dispatch, post, live API call, `POSTING_ENABLED` change, or
`FEATURES` value change occurred. No `site/public` or `data/derived` artifact was touched. The
only `data/` read was the ledger and the statements corpus, both read-only.

Both mutation harnesses report every check load-bearing:

```text
C:\ProgramData\miniconda3\python.exe scripts\run_verifier_mutations.py
C:\ProgramData\miniconda3\python.exe scripts\run_registry_mutations.py
```

15/15 verifier checks and 20/20 registry invariants are load-bearing. The registry count rose
from 15 to 20 with the five N4 gold-set rater invariants.

## Package record

### N1. The pilot re-seal with survivors

Commit: `36527f6`

Suite: 774 passed and 0 failed before. 781 passed and 0 failed after.

The seal was re-run over the committed corpus, harness-detached per docs/37 rule 10 (the
ledger is 3,084,929,086 bytes; the build ran about forty minutes end to end).

```text
old seal 2c349e56b37e326950596b9acb3780b57c4cc6b37985a7709f219b3a25880ec1
new seal 7facc4d2323596a71153997fda33a924324634f1a096c5dee2df221ec86a00d3
```

The new kit supersedes the prior sealed kit. `MANIFEST.json` now carries a `supersedes` block
with the prior `seal_hash`, `universe_fingerprint`, and method version. The record is
idempotent: rebuilding an unchanged kit records nothing, so a later rebuild cannot make the
kit appear to supersede itself. The universe is unchanged at 591,412 candidates and the
universe fingerprint is unchanged at `51d7ac25c4d70cbc...`; what moved is the impact tagging
and therefore the ranking inside each stratum.

Confirmed from the committed corpus, in a second detached run:

```text
seal_hash match: True
universe_fingerprint match: True
```

**Two build-versus-verify defects, fixed in the same commit.** `verify()` built its
public-impact set from the committed day surfaces alone, while `build()` unioned the Y10
survivors into it. The rebuilt frame would have carried different impact tags, a different
ranking, and a different seal hash, so the re-sealed kit would have been unverifiable from the
committed corpus, which is the property docs/35 section 3 promises to any reader. Both paths
now call one `public_phrase_set()`, and a test asserts both function bodies call it, so a
future edit to one path cannot silently diverge again (docs/37 rule 1).

**The survivor outcome, stated plainly.** The order expected the survivor fixture set to enter
the pilot. It did not. What actually happened:

| Survivor phrase | In the ledger | In the frame |
|---|---|---|
| `billions of dollars` | yes, 2,957 days | full sample, D and R rows |
| `communities across the country` | yes, 2,301 days | full sample, D and R rows |
| `families across the country` | yes, 1,553 days | full sample, D and R rows |
| `across the country` | **absent** | nowhere, and can never be sampled |
| `working families everywhere` | **absent** | nowhere, and can never be sampled |

Three of the five are now in the sealed frame with the `public_surface` tag and a priority of
at least 8, which is the weighting working. All six of their candidate rows landed in the full
sample and none in the pilot, because `split_pilot_full` strides evenly across each stratum's
ranked slice and a stratum's top-priority row is not necessarily on the stride. The Y10 test
`test_a_public_tagged_survivor_is_drawn_into_the_pilot` holds at fixture scale, where a
stratum is small enough that its first row is always on the stride; at production scale, with
591,412 candidates across 21 strata, it does not follow.

Two of the five are absent from the phrase ledger entirely, so no seal can ever draw them.
They document classifier behavior on phrases the corpus does not contain. That is worth
recording against the Y10 fixture, which describes itself as documenting current behavior.

I did not tune the sampler to force the named phrases into the pilot. That would make the
pilot a hand-picked set for exactly the phrases under adjudication, which is the property the
survivors fixture explicitly disclaims ("not a hand-tuned blocklist; the gold set decides").
The decision of whether to order a pilot-stride change, or to let the survivors be adjudicated
where they landed in the full sample, belongs to the orchestrating session. Nothing is blocked
either way: the pilot runs today on the kit as sealed.

Files:

- `scripts/goldset_seal.py`
- `evaluation/goldset/MANIFEST.json`
- `evaluation/goldset/pilot.sample.json`
- `evaluation/goldset/full.sample.json`
- `tests/test_n1_reseal.py` (7 tests)

### N2. docs/35 amendment implementing the S57 ruling

Commit: `54cf9fc`

Suite: 781 passed and 0 failed before and after (documentation only).

Sections 1 through 9 keep the two-annotator study, which the full sample still runs and which
remains the path to Gate B. A new section 10 states the ruled pilot mode and governs the pilot
where the two conflict. Sections 2, 5, and 8 gain pointers so the document does not contradict
itself, and the amendment is announced at the top where a reader starts.

Section 10 states, with a subsection each: who rates and that the author is not an independent
rater (10.1); what the model rater may and may not do (10.2); the mandatory label (10.3); the
flow, including that the section 5 gates are not evaluated (10.4); what the mode may not claim
(10.5); publication and the standing re-annotation invitation (10.6); the operator checklist
(10.7); and Michael's reserved acts (10.8).

The acts named as Michael's: annotating the pilot and every triage decision; authorizing the
one paid step, the live model-rater run; choosing and freezing the classifier threshold on
train and validation; deciding when the test result is run; publishing the bundle, the labels,
and the metrics and issuing the invitation; and declaring any gate transition, including the
Gate B this mode does not release.

Gate B is refused explicitly and by name: a single-human-rater author-annotated pilot does not
release the docs/33 R-33.11 validated-instrument gate, and independent replication, meaning
labels from people who are not the author, is what does.

Files:

- `docs/35-ANNOTATION-PROTOCOL.md`

### N3. Intake tooling for the ruled mode

Commit: `0226668`

Suite: 781 passed and 0 failed before. 794 passed and 0 failed after.

`pipeline/goldset_single.py` owns the mode: it accepts one human answer sheet and one model
answer sheet, computes agreement under the name `human_versus_model_agreement`, emits the
triage queue, applies the human's post-triage decisions, and stamps the provenance label onto
every artifact it returns.

Three properties are enforced rather than documented:

1. **The model never writes a gold label.** `apply_triage` takes the human's original label or
   the human's own revision. A `keep` resolution leaves his label standing whatever the model
   said. The merged records carry `adjudicator_id: null` and the human as the only annotator.
2. **No inter-annotator claim can ship.** `assert_no_inter_annotator_claim` walks every payload
   before it is returned and refuses a field name containing any inter-annotator or inter-rater
   token. It scans keys only, deliberately: the interpretation and omission notes say those
   words in order to deny the claim, and a value scan would suppress the denial. Cohen's kappa
   and Krippendorff's alpha are not reported in this mode at all, and the omission says why.
3. **The gates are not claimed.** `pilot_gates` reports `evaluated: false` with the reason,
   instead of a pass or a fail.

The label is owned by the code as `goldset_single.PROVENANCE_LABEL`; docs/35 quotes it, and a
test holds the two together so the document cannot drift from the string the code stamps.

Both operator commands gain the mode without changing existing behavior. `goldset_intake.py`
takes `--human` and `--model`; `goldset_metrics.py` takes `--human` and `--triage`; each
refuses a mixed invocation and each keeps its two-annotator path byte-identical.
`goldset_single` is registered as a non-instrument method module, since it is offline
evaluation rather than a daily published surface.

Acceptance: `tests/test_n3_single_rater_intake.py` (13 tests), including the whole flow over
the committed sealed pilot rather than fixtures alone (docs/37 rule 2).

Files:

- `pipeline/goldset_single.py`
- `pipeline/instrument_fingerprint.py`
- `scripts/goldset_intake.py`
- `scripts/goldset_metrics.py`
- `tests/test_n3_single_rater_intake.py`

### N4. The model-rater runner

Commit: `b6ab379`

Suite: 794 passed and 0 failed before. 805 passed and 0 failed after.

`pipeline/goldset_rater.py` builds the rating prompt from the annotation guide itself, so the
model reads the same authority the human reads, and rates the sealed bundle in day-and-party
groups, which is the unit the document-family task compares over. The request carries exactly
the blinded fields the human packet carries and no machine-decided value; a test probes for
the field names and for each candidate's own classifier rule, family id, and anchor id.

**The freeze.** `rating_prompt_sha256` covers the prompt wrapper and the guide together and is
frozen into `evaluation/goldset/rater-registration.json`:

```text
rating_prompt_sha256 1aa8447702f2b163103a3f23fc7447ebece81395189e1a6c2bbae885144a8246
prompt               pipeline/prompts/GS1_gold_rater.v1.0.txt
guide                evaluation/ANNOTATION-GUIDE.md
model                claude-sonnet-5
```

A live run compares live against frozen and refuses on drift, so an edit to the guide cannot
silently change the instrument that produced a published sheet. The registration is a pin, not
a captured record: a test asserts it equals the live instrument, and that test failing is the
intended alarm, since a live run would refuse in the same condition.

**Dry run is the default and costs nothing.** It builds every request, checks the freeze,
prints an upper-bound estimate, and writes the requests so they can be read before anyone pays
for them. It writes no answer sheet, because a fabricated sheet is indistinguishable from a
real one at a glance. Measured on the sealed pilot:

```text
requests: 148 over 200 items (pilot, seal 7facc4d2323596a7)
model: claude-sonnet-5  approx tokens in: 845769  estimated cost: $2.325938 (upper bound)
dry run: $0 spent, no Anthropic call made, no answer sheet written.
```

The live run needs `--allow-api-spend` and `ANTHROPIC_API_KEY`, and is Michael's act. It
refuses without either and refuses on registration drift. Sonnet is the default because a
weaker reader produces noisier disagreements, which costs the human rater time rather than
money; the whole run is a one-time offline cost of about two dollars against a $10 monthly
ceiling that governs the daily pipeline.

**Registered in the Y9 harness** as five invariants: prompt version, model, wrapper sha256,
guide sha256, and the combined rating-prompt sha256. The harness gains an optional `expect()`
so a derived value can be load-bearing: bump the guide text and the registered content address
must follow it to the exact expected hash, not merely change. Without that, a hash invariant
could only prove the value moved, which a hand-copied literal could also do by coincidence of
editing.

Acceptance: `tests/test_n4_model_rater.py` (11 tests). The network call is the only uncovered
code and is marked `# pragma: no cover`, as `pipeline/llm.py` marks its own.

Files:

- `pipeline/goldset_rater.py`
- `pipeline/prompts/GS1_gold_rater.v1.0.txt`
- `pipeline/instrument_fingerprint.py`
- `evaluation/goldset/rater-registration.json`
- `scripts/goldset_rate.py`
- `tests/registry_mutations.py`
- `tests/test_n4_model_rater.py`

### N5. Michael's pilot bundle

Commit: `5488077`

Suite: 805 passed and 0 failed before. 814 passed and 0 failed after.

Generated from the new seal, for annotator `michael`: the interactive offline app, the
read-only packet, and a blank answer sheet over all 200 sealed pilot items, 196 of them
carrying a support set.

```text
michael.app.html          428,066 bytes
michael.packet.html       515,174 bytes
michael.answersheet.csv     6,108 bytes
PUBLISH-CHECK.json          1,022 bytes
```

**Publish-ready, proven by the existing canary machinery.**
`goldset_bundle.certify_publishable` runs the production canary through the existing
`publication_rehearsal` entry point, then scans every rendered file with
`contains_admitted_form`. That is the narrower question and the correct one here: a redaction
label is expected in a packet and is the evidence that a name is absent, so `is_suppressed`
would fire on the very thing that proves the file is clean. The certificate ships as
`PUBLISH-CHECK.json`: 3 files scanned, 0 admitted forms found, canary
`privacy-production-canary-v1`, seal hash pinned. A seeded canary failure and a planted
admitted form each refuse, both tested.

`evaluation/goldset/PILOT-RUNBOOK.md` is the one page: open the packet, annotate, verify the
seal, preview the model rater for free, run it live (his act, the only spend), intake, work the
triage queue, run metrics, publish with the label and the invitation. It states what the mode
may not claim.

Acceptance: `tests/test_n5_pilot_bundle.py` (7 tests) plus the two privacy tests below.

Files:

- `pipeline/goldset_bundle.py`
- `pipeline/privacy.py`
- `scripts/goldset_bundle.py`
- `evaluation/goldset/PILOT-RUNBOOK.md`
- `evaluation/goldset/bundles/pilot/michael.app.html`
- `evaluation/goldset/bundles/pilot/michael.packet.html`
- `evaluation/goldset/bundles/pilot/michael.answersheet.csv`
- `evaluation/goldset/bundles/pilot/PUBLISH-CHECK.json`
- `tests/test_privacy_lazy_gate.py`
- `tests/test_n5_pilot_bundle.py`

## Variances and deviations

1. **N1 does not put the survivors in the pilot.** The order asked that the survivor fixture
   set enter the pilot sample per the existing `tag_impact` weighting. Under that weighting
   they enter the frame and land in the full sample. Forcing them into the pilot requires
   changing `split_pilot_full`, which is a sampling-method change made after seeing which
   items land where, so it is not mine to make silently. Recorded above with the evidence and
   left as a decision.

2. **N1 fixes `verify()` as well as running `build()`.** Re-sealing without that fix would have
   produced a kit whose seal hash could not be reproduced from the committed corpus, which
   would have converted the re-seal into an unverifiable artifact. The fix is in the same
   commit because the two are one deliverable.

3. **N4 registers the prompt hash through a new harness capability.** `tests/registry_mutations.py`
   gains an optional `expect()` transform. Every pre-existing invariant is unaffected (the
   default is identity) and all 15 still report load-bearing, alongside the 5 new ones.

4. **N5 carries a privacy fix.** `privacy.redact()` raised on the un-established gate instead
   of establishing it, so it was the one gate-touching call the 2026-07-28 lazy-gate fix
   missed. Any tool whose first privacy touch is a redaction died with a message naming no
   remedy, and the bundle renderer redacts first, so N5 could not run at all. It now takes the
   same `_require_gate()` path as every other consuming call, which is strictly fail-closed
   because `load()` still raises the full remedy message when the salt is genuinely absent.
   Two salt-less subprocess tests were added to the existing lazy-gate file, reproducing the
   CI runner exactly: one proves it still refuses without a salt with the remedy message
   intact, one proves a first-call redaction works when a salt is present. This is docs/37
   rule 4 again, in the same costume as S57: a fail-closed branch left behind by the fix that
   moved everything around it.

5. **The model rater defaults to Sonnet, not a Haiku-class model.** The $10 ceiling in
   CLAUDE.md governs the recurring daily pipeline. This is a one-time offline run estimated at
   $2.33 upper bound, and rating quality here converts directly into the human rater's time.
   `--model` overrides it and the dry run prints the estimate before anyone commits.

6. **Sonnet pricing note carried forward.** `llm.PRICING` records that Sonnet 5 introductory
   pricing ends 2026-08-31. `estimate_run` passes the run date through, so an estimate made
   after the cutover prices at the new rate without any edit here.

## Operator smoke test, and what it does not mean

The whole flow was exercised end to end with synthetic answer sheets to prove the commands
run: `goldset_rate.py pilot` (dry), `goldset_intake.py pilot --human --model` (200 rows each,
40 class disagreements queued, blinded triage context rendered), and
`goldset_metrics.py pilot --human --triage` (40 triage decisions, 10 revised, metrics written
and stamped). **Every number that run produced is meaningless**: the labels were generated by a
rotation over the class list, not by reading anything. No metrics artifact from that run is
committed, and none should ever be published. The real numbers do not exist until Michael
annotates.

## Incomplete items and blockers

No package was blocked. Two items are left for the operator or the orchestrating session:

1. The survivor-versus-pilot decision in variance 1.
2. The smoke-test outputs could not be deleted from the working tree: the deletion command was
   denied by the session's permission gate, twice. The following untracked paths remain in the
   working tree and are safe to remove; none is committed and none affects the branch.

```text
evaluation/goldset/intake/
evaluation/goldset/metrics/
evaluation/goldset/bundles/pilot/model-rater.plan.json
evaluation/goldset/bundles/pilot/model-rater.requests.jsonl
```

## Repository state

The branch starts at exact base `e87e110`. HEAD is `5488077`. Five commits, one per package.
`AGENTS.md` and the pre-existing `tests/_tmp_watchdog/` remain untracked. No `site/public` or
`data/derived` artifact was regenerated. No em dash was added to any authored file (the 24 in
`pipeline/privacy.py` are pre-existing and untouched). No push, deploy, workflow dispatch,
post, live API call, or gate or feature mutation occurred.
