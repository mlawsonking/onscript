# ANNOT work-order delivery packet

Branch: `opus/annotation-kit`

Base: `3259b961457e99b8244011e8f6ca68cadbab31cf` (main)

The gold-set annotation kit. Everything here is deterministic and free: no Anthropic API
call, no GPU, no network beyond git. The house runner is `C:\ProgramData\miniconda3\python.exe`.

Validation command for the whole kit:

```text
C:\ProgramData\miniconda3\python.exe tests\run_tests.py
```

Suite baseline was 667 passed and 0 failed. The final result is 699 passed and 0 failed.
Every commit leaves the suite green. No push, deployment, workflow dispatch, post, live API
call, `POSTING_ENABLED` change, or existing `FEATURES` change occurred. `AGENTS.md` and
`tests/_tmp_watchdog/` stayed untracked. No `site/public` or `data/derived` artifact was
regenerated. The only committed data outside code and docs are the three sealed sample files
under `evaluation/goldset/`, which the protocol requires committed.

## Package record

### A1. Sealed pilot and full samples

Commit: `7bc4a1f`

Suite: 699 passed and 0 failed. Adds `tests/test_goldset_sample.py` (14 tests).

Files:

- `pipeline/goldset_sample.py`
- `scripts/goldset_seal.py`
- `tests/test_goldset_sample.py`
- `evaluation/goldset/MANIFEST.json`
- `evaluation/goldset/pilot.sample.json`
- `evaluation/goldset/full.sample.json`

Build and verify:

```text
C:\ProgramData\miniconda3\python.exe scripts\goldset_seal.py build
C:\ProgramData\miniconda3\python.exe scripts\goldset_seal.py verify
```

The candidate unit is one phrase (n-gram) as carried by one party on that party's peak
public day. The universe is drawn from the committed 45-day Stage-1 ledger, gated to the
public epoch `config.STAGE1_EPOCH` = 2025-01-03. Each candidate's predicted class comes from
`pipeline.eligibility.classify_phrase`. The seal draws a 200-item pilot and a disjoint
1,400-item full sample, oversampling public-impact cases and fully including the rare private
and biographical classes, and freezes the split by date.

Sealed identity, reproduced by `verify` from the committed corpus:

- `seal_hash` = `2c349e56b37e326950596b9acb3780b57c4cc6b37985a7709f219b3a25880ec1`
- `universe_fingerprint` = `51d7ac25c4d70cbc09db8134eee159ffdb64d9330b2b72bbfc597f76af4e112e`
- Ledger source `data/state/ledger.json`, SHA-256 `32c25c95...bf7593`, 3,084,929,086 bytes.
- Statements source `data/state/statements.jsonl.gz`, SHA-256 `506ddb0a...`, 94,067,097 bytes.
- `verify` reports seal_hash match True and universe_fingerprint match True.

Acceptance: the sample is sealed before any label exists. The manifest commits the sample IDs,
the split boundaries, the seed, and the seal hash. `verify` rebuilds the frame from the
committed corpus and confirms both hashes, so any later corpus or frame change is detected.
`tests/test_goldset_sample.py` proves peak-day selection, the epoch gate, exact pilot and full
sizes, disjointness, seal reproducibility, seal change on frame change, rare-class survival,
public-impact oversampling, date-based split assignment, anchoring, and the privacy redaction
of written phrases.

**Table A1-1. Class composition of the universe and the sealed selection.**
Estimator: `eligibility.classify_phrase` over the candidate universe. Unit: one candidate
(phrase, party, peak day). Window: public epoch 2025-01-03 onward. Denominators: 591,412
universe candidates, 1,600 selected.

| Predicted class | Universe available | Selected |
|---|---:|---:|
| message | 315,720 | 806 |
| procedural | 183,665 | 470 |
| unknown | 78,133 | 202 |
| nomenclature | 13,811 | 39 |
| biographical | 76 | 76 |
| private | 7 | 7 |
| total | 591,412 | 1,600 |

Private and biographical are fully included because their entire universe pool is small; this
is the rare-class-coverage rule that keeps the confusion matrix populated in every class.

**Table A1-2. Split and party distribution of the selection.**
Estimator: `goldset.date_split` by publication day; party from the ledger. Unit: one selected
candidate. Window: split boundaries train_end 2025-12-31, validation_end 2026-03-31.
Denominators: 200 pilot, 1,400 full.

| Sample | train | validation | test | party D | party R |
|---|---:|---:|---:|---:|---:|
| pilot | 136 | 27 | 37 | 139 | 61 |
| full | 955 | 177 | 268 | 966 | 434 |

**Table A1-3. Public-impact capture in the selection.**
Estimator: impact tagging (public-surface membership from the 18 committed day artifacts,
quorum boundary at support-unit count 2 or 3, rare class, joint-family collapse). Unit: one
selected candidate, which may carry several tags. Denominator: 1,600 selected.

| Impact tag | Selected carrying it |
|---|---:|
| boundary_quorum | 1,213 |
| public_surface | 446 |
| rare_class | 122 |
| private | 7 |

Privacy: all 1,600 selected candidates anchored to a source statement (0 unresolved). Seven
private-class phrases were passed through the hardened label path before writing; a scan of
both committed sample files finds 0 admitted private-person forms.

### A2. Annotation guide and schema

Commit: `d3da9b3`

Suite: 699 passed and 0 failed.

Files:

- `evaluation/ANNOTATION-GUIDE.md`
- `evaluation/annotation.schema.json`

Acceptance: the guide covers tasks A through F (surface class, phrase completeness,
cross-receipt proposition consistency, stance consistency, document family, public claim
support) with plain decision rules and at least three worked examples per task drawn from
real published statements in the corpus. Every worked example names the office, date, and the
real sentence. The edge-case appendix covers the privacy name shapes and the
nomenclature-versus-message boundary, including two real cases where the deterministic
classifier and the correct human label differ: `committee on ways and means`, which the
classifier calls message but which is a committee name, and `born in the united states` in the
birthright-citizenship context, which the classifier calls biographical but which states a
principle. The schema adds the `unknown` class to the `gold_class` enum, reconciling it with
`eligibility.SURFACE_CLASSES` and R-33.2, and adds optional fields for tasks B, C, D, and F.
The change is additive; the existing W10 fixture stays valid and the suite stays green.

### A3. Annotator packet generator

Commit: `0ef6018`

Suite: 699 passed and 0 failed. Adds `tests/test_goldset_bundle.py` (8 tests).

Files:

- `pipeline/goldset_bundle.py`
- `scripts/goldset_bundle.py`
- `tests/test_goldset_bundle.py`

Commands:

```text
C:\ProgramData\miniconda3\python.exe scripts\goldset_bundle.py pilot
C:\ProgramData\miniconda3\python.exe scripts\goldset_bundle.py pilot --format app
```

Acceptance: the generator renders each annotator two shared-context outputs. The read-only
packet is a self-contained HTML page (inline CSS, no external asset reference, works offline)
paired with a CSV answer sheet keyed by candidate ID. The interactive app (`--format app`) is a
single offline HTML file where the annotator clicks the surface class, assigns a document
family, and sets the four optional tasks, with autosave and resume in the browser and one-click
export to the same CSV the intake tool ingests. Both show the candidate phrase, the full
sentence, one sentence before and after, the release title, the office, the date, and, for
items with a support set, the offices carrying the same phrase. Both hide the predicted class,
rankings, surge scores, publication decisions, and correction history. Item order is randomized
per annotator with a recorded seed.

Verified on the sealed pilot: two annotators, 200 items each, 196 with support sets, valid
UTF-8, no external URL, no admitted private-person form, none of the machine-signal fields
present. The interactive app was exercised in a browser: 200 cards render from the embedded
data, class selection and the toggle-off behavior work, the family input and stance and boolean
tasks persist to localStorage and resume on reload, the progress counter reflects fully labeled
items, and the export produces the exact answer-sheet header and rows.
`tests/test_goldset_bundle.py` proves neighbor extraction, context masking, family-deduplicated
support sets, the redacted-phrase skip, per-annotator order determinism, self-containment of
both the packet and the app, the app's embedded-data round trip and closing-tag escape, the
answer-sheet columns, and HTML escaping.

### A4. Intake and metrics tooling

Commit: `ac7d814`

Suite: 699 passed and 0 failed. Adds `tests/test_goldset_metrics.py` (10 tests).

Files:

- `pipeline/goldset_metrics.py`
- `scripts/goldset_intake.py`
- `scripts/goldset_metrics.py`
- `tests/test_goldset_metrics.py`

The two operator commands:

```text
C:\ProgramData\miniconda3\python.exe scripts\goldset_intake.py pilot --a A.csv --b B.csv
C:\ProgramData\miniconda3\python.exe scripts\goldset_metrics.py pilot --a A.csv --b B.csv --decisions decisions.csv
```

Acceptance: intake validates both answer sheets against the schema, merges the two annotators
double-blind, computes per-task Cohen's kappa and Krippendorff nominal alpha, reports the
docs/35 pilot gates, and emits the adjudication queue with blinded context and a decisions
template. Metrics ingests the adjudicated decisions and reports message precision, document
family pairwise precision and recall, the party error gap, and the full confusion matrix, each
with numerator, denominator, and a 95% Wilson interval, plus a Newcombe interval on the party
gap. It refuses to report while any item is unresolved and accepts `--split test` for the
run-once evaluation. Verified end to end on the sealed pilot: intake reported per-task kappa
and alpha over 200 dual-annotated items and the three pilot gates; metrics reported message
precision with its Wilson interval, family pairwise precision and recall, and the party gap
with its Newcombe interval, all from numerator over denominator.
`tests/test_goldset_metrics.py` proves CSV coercion, schema validation including the
reconciled unknown class, kappa and alpha on known inputs, the Wilson interval, the pilot-gate
report, the adjudication queue, and the interval metrics with correct numerators and
denominators.

### A5. Annotation protocol

Commit: `d4d163a`

Suite: 699 passed and 0 failed.

Files:

- `docs/35-ANNOTATION-PROTOCOL.md`

Acceptance: docs/35 states the roles and blinding, the pilot-calibrate-full flow, the pilot
pass gates (overall agreement at least 0.80, message versus non-message at least 0.90, privacy
near 1.00), the failed-pilot response (guide revision and a fresh pilot sample, never touching
the sealed test split), which thresholds may be tuned on train and validation, the run-once
rule for the test split, and the operator checklist from annotators hired to metrics
published. It marks every reserved act as Michael's. It serves R-33.1 and R-33.2.

## Sample composition, method note

The predicted class for a candidate uses the ledger support-unit count as the family-evidence
count for the message quorum. The ledger unit key already collapses joint groups, so this is
the support-unit count that R-33.8 defines as one family per support unit. The separate
document-family identity used by the family task (task E) and the family-pairwise metric is
computed by the document-family clustering (`pipeline.document_families`) at anchor time within
each item's day-and-party group, which is the unit the family-pairwise metric compares. Both
are recorded in the sealed sample and never recomputed downstream.

## Variances and deviations

1. Lane dimension. The W10 sampler stratifies by lane, and lane is recorded on every candidate.
   The committed comparative corpus (`statements.jsonl.gz`) is 100% lane 1, so at this commit
   every candidate is lane 1. The stratum is retained for forward compatibility; when lane-2
   normalization lands, the frame will populate it. Cross-party metrics use lane 1 regardless,
   per the standing rule.
2. Family-evidence count for classification uses the ledger support-unit count rather than a
   separately recomputed near-duplicate family count. See the method note above. The document
   family used for the family task is computed properly at anchor time.
3. Schema reconciliation. `annotation.schema.json` gained the `unknown` enum value and optional
   task fields. This is additive and aligns the schema with `eligibility.SURFACE_CLASSES` and
   R-33.2. The harness code already accepted `unknown`.
4. Private-class scarcity. The corpus holds only 7 private-class candidates because the privacy
   layer suppresses private material upstream. All 7 are included and their phrases are redacted
   in the sample files. The confusion matrix's private row is therefore small by nature, not by
   sampling choice; the guide teaches the name shapes so annotators still label private
   material they encounter.
5. Candidate unit. One phrase per party at its peak public day, not every occurrence, to bound
   the universe. Each selected candidate is anchored to a deterministic representative statement
   for its shown context.
6. Suite attribution. All new test files live in the working tree, so every commit's suite run
   reports 699. The 667 figure is the pre-session baseline. The per-package test counts above
   name which file each package adds.
7. Build performance only. `scripts/goldset_seal.py build` frees the ledger before anchoring so
   the garbage collector does not thrash on the 3 GB ledger. This changes runtime only, not
   output; `verify` reproduces the seal.

No other deviation from the work order is known.

## Incomplete items and blockers

None in the kit. The kit is ready for annotation to start the moment annotators are recruited.

Reserved for Michael, per docs/33 section 4 and docs/35 section 9: recruiting and paying the
two annotators and the adjudicator, sending packets and collecting answer sheets, choosing and
freezing the classifier threshold on train and validation, running the test split once, and
publishing the metrics that release the R-33.1 and R-33.2 surfaces.

## Repository state

The branch `opus/annotation-kit` starts at exact base
`3259b961457e99b8244011e8f6ca68cadbab31cf` and adds five package commits plus this packet.
`AGENTS.md` and `tests/_tmp_watchdog/` remain untracked. No generated `site/public` or
`data/derived` artifact was regenerated. Nothing was pushed; integration is the orchestrating
session's call.
