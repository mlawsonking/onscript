# Gold-set pilot record

The append-only record of the 200-item pilot: what was sealed, who read it, what each reading
said, and what may be claimed from any of it. Every number here carries its estimator, unit,
window, denominator, and a rerunnable command. Nothing here is a metric. The metrics run on
pass 2 and do not exist yet.

Authority: docs/35 as amended by Session 57 (single human rater, model triage), the Session 60
model-rater record, and the Session 63 pass-1 ruling recorded below.

## 1. What is sealed

| Field | Value |
|---|---|
| Sealed sample | pilot, 200 items, disjoint from the 1,400-item full sample |
| `seal_hash` | `7facc4d2323596a71153997fda33a924324634f1a096c5dee2df221ec86a00d3` |
| `universe_fingerprint` | `51d7ac25c4d70cbc09db8134eee159ffdb64d9330b2b72bbfc597f76af4e112e` |
| Seed | `onscript-goldset-v1` |
| Universe size | 591,412 candidates |
| Split boundaries | train through 2025-12-31, validation through 2026-03-31 |
| Sealing commit | `36527f6` (N1, pilot re-seal with the Y10 generic survivors) |
| Ledger source | `data/state/ledger.json`, 3,084,929,086 bytes, sha256 `32c25c95…` |
| Statements source | `data/state/statements.jsonl.gz`, 94,067,097 bytes, sha256 `506ddb0a…` |
| Unresolved anchors | 0 |

The sealing rule in docs/35 section 3 holds: no item has moved between the pilot, the full
sample, or any split since the manifest was committed.

## 2. The seal is intact, and the seal verifier is not

`scripts/goldset_seal.py verify` reports `seal_hash match: False` on the current tree. The
sample did not move. The verifier did.

`verify()` rebuilds the public-impact oversampling set from the live `data/derived/days` tree
and feeds it to `tag_impact()`, which changes which candidates are drawn. That tree grows with
every production data commit. Two days were published after the kit was sealed
(`2026-07-27.json` and `2026-07-29.json`), so the rebuilt draw differs from the sealed draw
and the hash differs with it.

Rebuilding with the days tree pinned to the sealing commit reproduces the seal exactly:

| Check | Result |
|---|---|
| Manifest seal | `7facc4d2323596a71153997fda33a924324634f1a096c5dee2df221ec86a00d3` |
| Rebuilt as of `36527f6` | `7facc4d2323596a71153997fda33a924324634f1a096c5dee2df221ec86a00d3` |
| Seal match | true |
| Universe fingerprint match | true |
| Pilot candidate ids identical | true, 200 of 200 |
| Public-surface phrases at seal time | 299 |

Reproduction:

```
C:\ProgramData\miniconda3\python.exe scripts\goldset_seal.py verify --as-of 36527f6
```

This is the fourth appearance of the docs/37 rule 3 shape, after X7 at Session 52, Y1 at
Session 59, and the r3 gate test at Session 61. It is the most consequential one, because the
seal verifier is the mechanism by which a reader confirms the sample was frozen before any
label existed. Under docs/35 section 3 a mismatch means the sample must be resealed and
re-examined. A verifier that reports a false mismatch every time production publishes a day
would force a re-seal after labels exist, which the sealing rule prohibits.

The default `verify` behavior is unchanged in this session. Whether `verify` should pin its
own impact input rather than accept a reference is a design change to the sealed-kit contract
and belongs to Fable.

## 3. The readings

Three readings of the same sealed 200 items exist. Two are recorded here. The third is the
pass-2 human pass, which is Michael's pending act.

### 3.1 Pass 1, the human rater, preserved as a calibration record

| Field | Value |
|---|---|
| File | `bundles/pilot/michael-pass1.answersheet.csv` |
| sha256 | `51e65e0fbd57b9b33518875e0bf2b4011576d0f37f1290bc0bda412e3ac1d7ea` |
| Coverage | 200 of 200, class and family filled on every row, no duplicates, no extras |
| Class distribution | message 155, nomenclature 27, procedural 14, biographical 3, private 1, unknown 0 |
| Provenance | recovered from the browser export; the tracked `michael.answersheet.csv` is the N5 blank template and stays blank |

**Ruling (Session 63): pass 1 is never gold.** It was performed under an inverted standard.
The class was inferred from the surrounding sentence, where the guide anchors the message
decision to the candidate phrase alone. Pass 1 is preserved because a record of how a careful
reader misread the guide is the evidence that fixes the guide. It is not deleted, not
corrected, and not used as an answer key.

Three measurements carry the ruling. Denominator is the 200 sealed items, or the 155 pass-1
message labels where stated.

| Measurement | Value | What it shows |
|---|---|---|
| `unknown` labels | 0 of 200 | The guide's stated safe default was never once chosen |
| message labels with task B blank | 141 of 155 | The completeness gate the message rule requires went unanswered |
| message labels with task B answered no | 3 of 155 | Message asserted against an explicit completeness failure |

The guide makes phrase completeness a necessary condition for message. On 144 of 155 message
labels that condition was either unanswered or answered against the label.

### 3.2 The model reader, frozen prompt, triage input only

| Field | Value |
|---|---|
| Sheet | `bundles/pilot/model-rater.answersheet.csv`, sha256 `363ecdfc2752f5371e4209b25736f8f65cd428b6ed9ccd7c80e9647138440c8e` |
| Rating instrument | `1aa8447702f2b163103a3f23fc7447ebece81395189e1a6c2bbae885144a8246` |
| Wrapper | `90e0661f52ad3f8c2943b0e07242ff6c6c03bba9fc7ef1ec11e767cf8b3402cc` |
| Guide at rating time | `2243cddef095cc30e5eb39fe1c7689cbe444e409593d1f4b020891b046e0daf2` |
| Registered reader | `claude-sonnet-5` |
| Actual reader | `claude-opus-5` (authorized session transport, Session 60) |
| Rater id | `model-rater-GS1-v1.0-claude-opus-5` |
| Coverage | 200 of 200 over 148 day-and-party groups, 0 errors |
| Spend | 0.00 USD, no Anthropic call |
| Class distribution | unknown 128, nomenclature 41, message 16, procedural 11, biographical 3, private 1 |

Under docs/35 section 10.2 these labels are triage input and never gold labels. Their
relationship to any human sheet is human-versus-model agreement and nothing else. It is not
inter-annotator agreement, not inter-rater reliability, and not kappa between annotators.

The full generation record, its authorized transport deviation, and its variances are in
`delivery/RATER-packet.md` (Session 60).

### 3.3 Pass 2, pending

Michael's second human pass over the same sealed 200 items, under the amended guide and the
app that gates the message class on task B. This is his act and it is not yet done.

| Field | Value |
|---|---|
| App | `bundles/pilot/michael-pass2.app.html` |
| Read-only packet | `bundles/pilot/michael-pass2.packet.html` |
| Answer sheet | `bundles/pilot/michael-pass2.answersheet.csv`, blank, 200 rows |
| Items | 200 of the sealed 200, 196 carrying a support set |
| Order | re-randomized on the annotator id, 0 of 200 positions shared with pass 1 |
| Storage key | `onscript-goldset-pilot-michael-pass2`, distinct from pass 1 so no pass-1 answer preloads |
| Blinding | no predicted class, family, impact tag, priority, lane, split, or seal in the payload |
| Publish check | 14 files scanned, 0 admitted forms, canary `privacy-production-canary-v1` |

Re-issue command:

```
C:\ProgramData\miniconda3\python.exe scripts\goldset_bundle.py pilot --annotators michael-pass2
```

The pass-1 bundle was not re-rendered. `michael.app.html`, `michael.packet.html`, and the
blank `michael.answersheet.csv` are byte-identical to their committed form, because docs/35
section 10.6 publishes the packet as it was annotated.

Intake, triage, and every metric run on pass 2 only. Nothing downstream of this row exists yet.

## 4. Disclosed priors

Under the Session 57 total-transparency rule, anything a reader knew before labeling that
could point the labels in a direction is disclosed rather than left for the reader to discover.

### 4.1 Carried forward from the Session 60 model-rater record, verbatim

> One exposure has to be disclosed rather than left for triage to discover. This session's
> harness loaded a stored memory line from an earlier session stating that a pilot LLM and the
> deterministic classifier agreed only about 28 percent of the time and that the classifier
> likely over-labels message and procedural. That is an aggregate observation, not an
> item-level one, and no item's context came with it, but it was in context before the first
> label and it points in the same direction as this sheet's distribution. It is named here so
> triage can weigh it rather than assume the reading was clean of any prior signal.

Three method facts from the same record, each a place a reasonable rater lands elsewhere and
each disclosed as triage material rather than presented as a finding:

1. The message test's completeness gate was applied literally against n-gram windows that stop
   mid-construction, which is what makes the model sheet unknown-heavy.
2. Task F counts one template or cosigned letter as one supporting document.
3. One fragment-shape boundary was settled mid-pass without revising the earlier answer.
   `cand:33dc597f7685204e` (group 24) reads `unknown` and `cand:8c7f699e6cbd2d72` (group 67)
   reads `nomenclature` on the same shape. Both readings are defensible under the guide.

### 4.2 What the rater learned between pass 1 and pass 2

Before pass 2 begins, Michael has seen the pass-1 ruling and its evidence. Specifically he
knows:

- That pass 1 was ruled to have inferred class from surrounding context rather than from the
  phrase alone, and that `unknown` was chosen zero times in 200 items.
- The model reader's aggregate label distribution: unknown 128, nomenclature 41, message 16,
  procedural 11, biographical 3, private 1.
- The dominant disagreement cell between pass 1 and the model reader: pass-1 message against
  model unknown, 121 items.

He has not seen, and the pass-2 packet does not carry, any item-level model label. The
disagreement is disclosed as an aggregate, in the same form as the section 4.1 prior.

This exposure is real and it is one-directional: a rater who knows the dominant disagreement
is message-versus-unknown and that he never used unknown has been told which way to move. Pass
2 is therefore a corrected pass, not an independent one, and no number from it may be
described as independent replication. Gate B remains unclaimed and independent replication
still means labels from someone who is not the author, on the published bundles.

### 4.3 Two pilot items are answered in the guide itself

Found while amending the guide, and disclosed rather than fixed, because changing a worked
example's label decides an item that is under adjudication.

The guide's task A worked examples name two phrases that are sealed pilot items and state
their class:

| Phrase | Guide's stated class | In sample |
|---|---|---|
| `letter is available` | unknown | pilot |
| `was elected to serve` | biographical | pilot |

Any rater who reads the guide, which every rater is instructed to do, is handed the answer for
2 of the 200 pilot items. This affected pass 1 and the model reading equally and it affects
pass 2. It is 1 percent of the sample and it is disclosed so a reader can discount it rather
than discover it.

A third example phrase, `after the supreme court`, appears in the task C and task F worked
examples with its answers stated. It is a sealed item in the full sample, not the pilot, so it
does not touch pass 2. It did shape the model reading, which read the same guide.

The Session 63 amendment removed `after the supreme court` from the task A worked examples,
because the pass-1 ruling makes its stated class wrong and leaving it would teach the error the
amendment exists to correct. It was removed rather than re-labeled: removing an example leaves
the item undecided, which is the neutral act, while re-labeling it would decide a sealed
full-sample item from inside the guide. Whether the remaining task C and F examples and the two
pilot-item examples should be replaced with phrases drawn from outside both samples is a
sampling question for Fable, not a defect this session fixes.

## 5. Pass 1 against the model reader

A calibration read of two readings of the same 200 items. Not a metric. Not agreement in any
reportable sense: one side is a record ruled not gold, and the other never writes gold labels.

Class agreement: 45 of 200, observed 0.2250. Estimator: observed exact-match rate on the
surface class. Unit: items. Window: the sealed pilot. Denominator: 200 items rated by both.

Rows are pass 1, columns are the model reader.

| | message | unknown | nomencl. | procedur. | biograph. | private | sum |
|---|---|---|---|---|---|---|---|
| message | 16 | 121 | 9 | 8 | 1 | 0 | 155 |
| unknown | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| nomenclature | 0 | 3 | 24 | 0 | 0 | 0 | 27 |
| procedural | 0 | 4 | 6 | 3 | 1 | 0 | 14 |
| biographical | 0 | 0 | 2 | 0 | 1 | 0 | 3 |
| private | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| sum | 16 | 128 | 41 | 11 | 3 | 1 | 200 |

The 121-item message-versus-unknown cell is the whole disagreement. Every other off-diagonal
cell together is 34 items.

The Session 60 prior in section 4.1 recorded an aggregate of roughly 28 percent agreement
between a pilot LLM and the deterministic classifier. That is a different pair of readers than
this table compares, so 0.2250 neither confirms nor contradicts it. The prior is recorded
because it was in context, not because it is a target.

## 6. What may not be claimed from anything in this record

- Not a metric. No precision, recall, error gap, or confusion matrix is reported here. Those
  run on pass 2.
- Not inter-annotator reliability. No kappa, alpha, or agreement figure from a human-model
  comparison may be presented as reliability between annotators.
- Not a pilot-gate pass. The docs/35 section 5 gates measure two independent humans.
- Not Gate B. Gate B waits for independent replication under docs/33 R-33.11.
- Not validation. Nothing here describes the instrument as validated.

## 7. What changed for pass 2

The pass-1 ruling is a finding about the instrument, not about the rater. Two changes follow
from it, both landed before the pass-2 packet was rendered.

**The guide.** `evaluation/ANNOTATION-GUIDE.md` gains section 3.1, the context-supplies-meaning
trap, with the cover-the-sentence test and a worked pair from one sentence: `working families`
is a message, `claim they are for` is unknown. Task B is restated as a gate to answer before
the class rather than an optional extra. The `after the supreme court` message example was
removed for the reason given in section 4.3.

**The app.** Selecting message is refused while task B is unanswered, and refused when task B
says the phrase is incomplete. Answering task B no after a message label was recorded withdraws
that label and says why. The standing reminder at the top of every page states that the phrase
is the unit and that unknown is the safe default. `pipeline.goldset_bundle.message_blocked_by`
owns the rule and the rendered app interpolates its strings, so there is one copy.

Amending the guide changed `guide_sha256` and with it `rating_prompt_sha256`, which invalidates
the model rater's freeze by design (docs/35 section 10.2). The registration was re-frozen
deliberately, as the runbook's step 4 describes, and now records what it supersedes:

| | Before | After |
|---|---|---|
| `guide_sha256` | `2243cddef095cc30…` | `bab2b3261eedadbb…` |
| `rating_prompt_sha256` | `1aa8447702f2b163…` | `ea52cd2571c821e6…` |

The committed model sheet stays attributable to the instrument that produced it: the prior
identity is carried in `rater-registration.json` under `supersedes`, and
`model-rater.run.json` carries the full prior registration inline. A model reading under the
amended guide has not been run and is not required for pass 2.

## 8. Reproduction

Every command is deterministic, spends nothing, and makes no network call.

```
C:\ProgramData\miniconda3\python.exe scripts\goldset_seal.py verify --as-of 36527f6
C:\ProgramData\miniconda3\python.exe scripts\goldset_bundle.py pilot --annotators michael-pass2
C:\ProgramData\miniconda3\python.exe tests\run_tests.py
```

The pilot record's own consistency is pinned by `tests/test_p1_pilot_record.py`, which reads
the committed artifacts rather than fixtures and asserts each against the identity it recorded
when it was written. `tests/test_p3_message_gate.py` holds the app gate to the guide rule it
enforces, and `tests/test_p4_pass2_packet.py` checks the rendered pass-2 packet for coverage,
blinding, and order.

## 9. Next

Pass 2 is Michael's act. After it lands as `bundles/pilot/michael-pass2.answersheet.csv`:

```
C:\ProgramData\miniconda3\python.exe scripts\goldset_intake.py pilot ^
    --human evaluation\goldset\bundles\pilot\michael-pass2.answersheet.csv ^
    --model evaluation\goldset\bundles\pilot\model-rater.answersheet.csv ^
    --model-rater model-rater-GS1-v1.0-claude-opus-5
```

That writes the triage queue. He works it into `intake/pilot/single/triage.csv`, then metrics
run on the post-triage labels. Two things to carry into that step:

- The model sheet was produced under the superseded guide. Its disagreements with pass 2 are
  still a usable second look, but a disagreement may now reflect the guide amendment rather
  than a mistake, and the triage record should say so where it applies.
- The 2026-07-28 files under `intake/pilot/single/` and `metrics/pilot/` in the operator
  checkout are synthetic rehearsal outputs from the annotation-ops build. They predate both
  real sheets, they are not committed here, and no number in them is a measurement of anything.
