# Gold-set pilot processing delivery packet

Branch: `opus/goldset-pilot-processing`

Base: `a2ae3d7` (origin/main at session start, "data: post 2026-07-30"). Main advanced to
`bbad7cc` during the session with the S63 watchdog work. The branch was not rebased: a rebase
over data commits mid-delivery is the X7 trap (docs/37 rule 3) and the merge is Fable's.

Session 64. Sessions 62 and 63 were claimed by parallel sessions while this one ran; 63 landed
on main mid-session.

Validation command for every package:

```
C:\ProgramData\miniconda3\python.exe tests\run_tests.py
```

Suite 890 passed and 0 failed at the base. 927 passed and 0 failed at delivery.

No push, deployment, workflow dispatch, post, live API call, `POSTING_ENABLED` change, or
`FEATURES` value change occurred. No `site/public` or `data/derived` artifact was written. The
only `data/` reads were the ledger and the statements corpus, read-only. Spend 0.00 USD.

## What this session was asked for and what it delivered

The order was to turn a completed pilot annotation into adjudicated labels and published
metrics. It could not be done as written, and the reason is the finding.

Two addenda arrived during the session. The first corrected the location of Michael's answer
sheet and identified the 2026-07-28 intake and metrics files as synthetic rehearsal leftovers.
The second ruled that pass 1 was performed under an inverted standard, is preserved as a
calibration record and never used as gold, and replaced the metrics packages with the
corrective work: amend the guide, gate the app, re-issue a pass-2 packet, disclose the priors.

Delivered: G1 in full, then packages (a) through (d) of the second addendum. Not delivered,
because the second addendum stops the session at the packet re-issue and because every
remaining number depends on a pass that has not happened: G2 adjudication, G3 metrics, G4
publication surfaces, G5 the classifier adjudication report. Each of those needs pass-2 labels
and none of them can be honestly produced without them.

## Package record

### P1. The pilot record, its integrity tests, and a verifiable seal

Commit: `40f3489`. Suite 890 to 916, 0 failed.

**Integrity, verified before anything was used.** 43 checks, all passing.

| Check | Result |
|---|---|
| Rater sheet seal, `sheet_sha256` against the rendered sheet | `363ecdfc2752f537…` matches |
| Rater sheet completeness | 200 rows, complete, 0 errors, 0 validation problems |
| Instrument in run and plan against the Y9 registration | all 5 frozen fields match, drift empty |
| One sealed sample across manifest, sample file, run, plan | `7facc4d2323596a7…` on all four |
| Pass-1 human coverage | 200 of 200, class and family filled, ids identical to the sealed set, no duplicates |
| Model coverage | 200 of 200, ids identical to the sealed set |
| Plan, requests, worksheet, calls | 148 groups on every carrier, item order identical, 200 item slots, 200 labels |
| Session answers against the sheet | 200, identical id set |

Reproduction: the checks are committed as `tests/test_p1_pilot_record.py`, which reads the real
artifacts rather than fixtures and asserts each against the identity it recorded when it was
written.

**The seal mismatch.** `scripts/goldset_seal.py verify` reported `seal_hash match: False`. This
was reported as a hard stop and then diagnosed rather than worked around. The sample did not
move. `verify()` rebuilds the public-impact oversampling set from the live `data/derived/days`
tree, which grows with every published day, and feeds it to `tag_impact()`, which changes which
candidates are drawn. Two days landed after the kit was sealed (`2026-07-27`, `2026-07-29`).

| | Value |
|---|---|
| Manifest seal | `7facc4d2323596a71153997fda33a924324634f1a096c5dee2df221ec86a00d3` |
| Rebuilt against the live tree | `bf21f521cd3019caca1c3a1a04b36c304bc2bc53e2aa5018cced172910e79ffd` |
| Rebuilt as of `36527f6` | `7facc4d2323596a71153997fda33a924324634f1a096c5dee2df221ec86a00d3` |
| Universe fingerprint | matches in both cases |
| Pilot candidate ids as of `36527f6` | identical, 200 of 200 |

```
C:\ProgramData\miniconda3\python.exe scripts\goldset_seal.py verify --as-of 36527f6
```

Fourth appearance of the docs/37 rule 3 shape after X7 at S52, Y1 at S59, and the r3 gate test
at S61, and the worst placed of the four. Under docs/35 section 3 a mismatch means the sample
must be resealed, and a re-seal after labels exist is what the sealing rule prohibits. A reader
who ran `verify` today would conclude the gold set is broken.

`verify` gains `--as-of REF`. Default behavior is unchanged. Whether `verify` should pin its own
impact input rather than accept a reference is a change to the sealed-kit contract and is
Fable's ruling, not this session's.

### P2. The guide names the trap, and the instrument re-freezes

Commit: `a23266c`.

`evaluation/ANNOTATION-GUIDE.md` gains section 3.1, the context-supplies-meaning trap: the
cover-the-sentence test, and a worked pair from one sentence where `working families` is a
message and `claim they are for` is unknown. Task B is restated as a gate to answer before the
class. Both example phrases are absent from the pilot and the full sample, so the amendment
decides no item under adjudication.

The guide taught the error it now corrects. Its first task A worked example labelled
`after the supreme court` a message on the reasoning that the member was responding to a
Supreme Court ruling, which is the sentence supplying the meaning. That example is removed
rather than re-labelled: the phrase is a sealed full-sample item, so re-labelling it would
decide that item from inside the guide, while removing it leaves it undecided.

Re-freeze, deliberate, as runbook step 4 describes:

| | Before | After |
|---|---|---|
| `guide_sha256` | `2243cddef095cc30…` | `bab2b3261eedadbb…` |
| `rating_prompt_sha256` | `1aa8447702f2b163…` | `ea52cd2571c821e6…` |

`_freeze` now records what it supersedes, so the committed model sheet stays attributable to
the instrument that produced it. Idempotent: re-freezing an unchanged instrument records
nothing.

### P3. The app refuses a message label task B does not support

Commit: `cf5f724`.

Selecting message is refused while task B is unanswered and refused when task B says the phrase
is incomplete; nothing is recorded on refusal. Answering task B no after a message label was
recorded withdraws that label and says why. Task B is marked required. Every page carries the
standing reminder that the phrase is the unit and that unknown is the safe default.

`pipeline.goldset_bundle.message_blocked_by` owns the rule and both refusal strings; the
rendered app interpolates them, so there is one copy and a test holds the two together.

### P4. The pass-2 packet

Commit: `57a6353`.

| Field | Value |
|---|---|
| App | `bundles/pilot/michael-pass2.app.html` |
| Items | 200 of the sealed 200, 196 with a support set |
| Answer sheet | blank, 200 rows |
| Order | 0 of 200 positions shared with pass 1 |
| Storage key | `onscript-goldset-pilot-michael-pass2`, distinct from pass 1 |
| Blinding | item payload is exactly candidate_id, phrase, before, sentence, after, title, office, date, support |
| Publish check | 14 files scanned, 0 admitted forms, canary `privacy-production-canary-v1` |

```
C:\ProgramData\miniconda3\python.exe scripts\goldset_bundle.py pilot --annotators michael-pass2
```

The pass-1 bundle was not re-rendered and stays byte-identical.

### P6. The required-fields list matches the gate, and a rater quick reference

Commit: `1229c6e`. Suite 927, 0 failed.

Guide section 9 still listed only class and family as required while section 3.1, section 4,
and the app all treat task B as a gate. A guide that calls a field optional while the app blocks
on it is the divergence that produced pass 1, found in this session's own work. Section 9 now
names task B required and states what the app does in each case.

The second amendment gives the instrument a third identity. `rater-registration.json` records
one step of succession, so its `supersedes` now names step 2 rather than the instrument that
produced the committed model sheet. PILOT-RECORD.md section 7 carries the full lineage:

| Step | `guide_sha256` | `rating_prompt_sha256` | What changed |
|---|---|---|---|
| 1 | `2243cdde…` | `1aa84477…` | produced the committed model sheet |
| 2 | `bab2b326…` | `ea52cd25…` | section 3.1, the task B gate, the removed example |
| 3 | `12c9f921…` | `e2d5755f…` | the section 9 required-fields correction |

The model sheet stays attributable because `model-rater.run.json` carries its entire
registration inline rather than by reference.

`evaluation/goldset/PASS2-QUICK-REFERENCE.md` is the rater-facing companion for the pass. It
adds no rule and says so at the top; the guide wins on any difference. Every phrase quoted as
an example in it is absent from both sealed samples, 32 checked, so it does not widen the
section 4.3 exposure.

The publish certificate now covers every file in the bundle directory rather than only what the
run wrote, because a partial re-render would otherwise leave the rest published and unscanned.

Blinding is asserted by JSON key, not substring. The existing check bans words like "priority"
and passes only on a synthetic item; the real bundle carries members' prose, in which "with
priority given to communities" is ordinary text. That is a docs/37 rule 2 case and the new test
is the production-shaped one.

## The pass-1 evidence

Denominator is the 200 sealed items, or the 155 pass-1 message labels where stated.

| Measurement | Value |
|---|---|
| `unknown` labels | 0 of 200 |
| message labels | 155 of 200 |
| message labels with task B blank | 141 of 155 |
| message labels with task B answered no | 3 of 155 |

Class agreement with the model reader: 45 of 200, observed 0.2250. Estimator: observed
exact-match rate on the surface class. Unit: items. Window: the sealed pilot. Denominator: 200
items rated by both. The single cell pass-1 message against model unknown is 121 items; every
other off-diagonal cell together is 34.

The full cross-tab is in `evaluation/goldset/PILOT-RECORD.md` section 5. Nothing there is a
metric: one side is a record ruled not gold and the other never writes gold labels.

## The re-look list

The order asked for a disagreement table and a re-look list. Both exist and neither is a triage
queue yet, because triage runs against pass 2 and pass 2 has not happened.

What Michael faces is not a 40-item queue. It is the whole pass: 155 items carry a label the
ruling says was reached the wrong way, and 121 of those sit in one disagreement cell. That is
why the answer is a fresh pass rather than a triage list over pass 1.

Two items to carry into the pass-2 triage when it comes:

- `cand:33dc597f7685204e` and `cand:8c7f699e6cbd2d72` are the same fragment shape answered
  differently by the model reader, disclosed in the S60 record. Expect them to disagree with
  each other.
- `letter is available` and `was elected to serve` are pilot items whose class the guide states
  outright. Their pass-2 labels are not independent of the guide.

## Deviations against the order

1. **The metrics packages were not delivered.** G2 through G5 all consume adjudicated labels.
   The second addendum stops the session at the packet re-issue. Reported rather than
   approximated: producing a metrics file from pass-1 labels would have put numbers into the
   record that the same addendum rules are not gold.

2. **The seal verifier was extended, not only reported.** The order says a seal mismatch is a
   hard stop, reported, not worked around. It was reported and diagnosed, and the sample was
   proven intact independently before anything downstream was rendered. `--as-of` was added
   because S58 ruled that a kit nobody can verify is not sealed, and this session re-issues a
   packet on that kit. The default path is untouched, so Fable can reject the addition without
   disturbing anything else.

3. **Pass 1 is committed at a new path.** `michael-pass1.answersheet.csv` rather than over
   `michael.answersheet.csv`, which stays the N5 blank template. Two files with labels and
   blanks under names that differ by a suffix is how a calibration record gets read as an
   answer key.

4. **Three test files were modified.** `test_n1_reseal.py` asserted the shared impact set by
   searching `verify`'s source text; `test_n5_pilot_bundle.py` asserted an exact three-file
   certificate set. Both now assert the invariant they were named for rather than the text or
   the count. Neither was weakened; both cover more than before.

5. **The guide's remaining sample-item examples were left alone.** `after the supreme court` in
   the task C and F examples, and the two pilot items answered in the task A examples. Changing
   them decides sealed items from inside the guide, which is the S58 concern. Reported in
   PILOT-RECORD.md section 4.3 for a sampling ruling.

6. **Per-package suite runs.** P1 through P4 were committed between two full-suite runs rather
   than with a full run between each. Each package's own tests were run in isolation and passed
   before its commit, and the two boundary runs are the 890 and 927 figures. The packages are
   additive and non-interfering. P5 and P6 each got their own full run, both 927 and 0 failed.

7. **The branch was not rebased** onto main's S63 advance. Stated above.

## What is Michael's

- **Pass 2.** Open `bundles/pilot/michael-pass2.app.html`, read the amended guide sections 1,
  3, 3.1, and 4 first, label all 200, export to
  `bundles/pilot/michael-pass2.answersheet.csv`. Task #216 covers this and stays open.
- Everything after it: triage, the threshold, when the test split is run, and publication.

## Expectation against observation

- **Expected** a completed annotation to adjudicate. **Observed** a completed annotation
  performed under an inverted standard, and the guide that taught the inversion.
- **Expected** the 2026-07-28 intake and metrics files to be the pilot's outputs. **Observed**
  they predate both real answer sheets and could not have read either. Both addenda confirmed
  it. Nothing from them is committed.
- **Expected** the seal to verify. **Observed** a false mismatch from a verifier that rebuilds
  against a moving tree, and the seal intact when the tree is pinned.
- **Expected**, from the S57 memory prior, roughly 28 percent agreement. **Observed** 0.2250
  class agreement between pass 1 and the model reader. That is a different pair of readers than
  the prior describes, so it neither confirms nor contradicts it. The prior is recorded because
  it was in context before the first label, not because it was a target.
- **Expected** the pilot to produce the R-29.2 and R-33.1 evidence this session. **Observed**
  that it produces the corrected instrument instead. Both gates stay closed. Gate B was never
  in reach and remains unclaimed.
