# 35: Gold-set annotation protocol

Authority: this document governs how the OnScript gold set is annotated, adjudicated, and
measured. It serves the docs/33 rulings R-33.1 (the on-script index returns only after the
gold-set metrics publish) and R-33.2 (fail-closed classification with the unknown class). It
is the operating manual for the annotation kit built under the ANNOT work order. Human
annotation execution, recruiting, and all release acts are Michael's, per docs/33 section 4.

**Amendment, Session 57, 2026-07-28.** The pilot no longer waits on hiring. Under the ruling
recorded in docs/26 Session 57, Michael annotates the pilot himself as the single human rater,
a frozen-prompt model acts as a second reader for disagreement triage only, and every number
that comes out carries the label in section 10.3. Sections 1 through 9 describe the
two-annotator study, which remains the design and the path to Gate B; section 10 states
exactly what the ruled pilot mode changes and what it may not claim. Where the two conflict
for the pilot, section 10 governs. The full sample still runs the two-annotator flow.

The kit is deterministic and free to run. Building a sample, rendering packets, intake, and
metrics make no network call and spend no API budget. The house runner is
`C:\ProgramData\miniconda3\python.exe`.

## 1. What the gold set is for

The deterministic classifier in `pipeline/eligibility.py` decides, by rule, whether each
phrase is a message, unknown, nomenclature, procedural, biographical, or private surface
class. The gold set is the human answer key that measures whether those decisions are
correct. Until the gold-set metrics exist, the composite on-script index stays off every
public surface (R-33.1) and the classifier ships only its deterministic floor (R-33.2). The
metrics this protocol produces are the evidence that gates those surfaces.

## 2. Roles and blinding

Section 10 replaces the annotator and adjudicator roles for the ruled pilot mode. The blinding
rules below hold in both modes, because blinding is a property of the kit rather than of who
holds the pen.

- **Annotator.** Two annotators label every item independently. Neither sees the other's
  answers, the machine's predicted class, rankings, surge scores, publication decisions, or
  corrections. Each works from the packet and the guide only.
- **Adjudicator.** A third person resolves every class or family disagreement and records
  their own ID with each decision. The adjudicator sees the same blinded context, never the
  machine's prediction.
- **Operator (Michael).** Recruits and pays the annotators, runs the commands, and holds all
  release authority. The operator does not label items.

Blinding is enforced by the kit. Packets are generated from the sealed sample with the
predicted class and every downstream signal removed. Item order is randomized per annotator
with a recorded seed so the two annotators do not move in lockstep.

## 3. The sealed sample

The sample is frozen before any label exists. `scripts/goldset_seal.py build` draws a
200-item pilot and a disjoint 1,400-item full sample from the committed corpus, stratified by
party, predicted class, lane, and year, oversampling public-impact cases, and assigns each
item a train, validation, or test split by date. The sealed identity is written to
`evaluation/goldset/MANIFEST.json` as `seal_hash`, over the sorted candidate IDs, the split
boundaries, the seed, and a fingerprint of the frame.

Sealing rule: once the manifest is committed, no item moves between the pilot, the full
sample, or any split. Moving an item after its label is examined is prohibited. The split
boundaries in the manifest are the only boundaries. Anyone can confirm the seal from the
committed corpus:

```bash
C:\ProgramData\miniconda3\python.exe scripts\goldset_seal.py verify
```

`verify` rebuilds the frame and the seal from the committed ledger and reports whether the
`seal_hash` and the frame fingerprint match the manifest. A mismatch means the corpus or the
frame changed and the sample must be resealed and re-examined, not silently accepted.

## 4. Pilot, calibrate, full

The pilot exists to prove the guide is usable before the expensive full pass. The flow is:

1. **Render pilot packets.** `scripts/goldset_bundle.py pilot` writes, per annotator under
   `evaluation/goldset/bundles/pilot/`, an interactive annotation app (`<annotator>.app.html`)
   and a read-only packet plus a blank CSV answer sheet. The app is a single offline HTML file:
   the annotator clicks the class, assigns a family, sets the optional tasks, and exports the
   CSV, which autosaves and resumes in the browser. `--format app` or `--format packet` selects
   one output.
2. **Annotate the pilot.** Both annotators fill their answer sheets independently.
3. **Intake the pilot.** The intake command validates the sheets, computes per-task agreement,
   and reports the pilot gates.
4. **Check the pilot gates (section 5).** If the gates pass, proceed to the full sample. If any
   gate fails, revise the guide and run a fresh pilot on a new pilot sample. The failed pilot's
   items are retired.
5. **Render and annotate the full sample** the same way, using `full` in place of `pilot`.
6. **Adjudicate and publish metrics** (section 6).

Intake command:

```bash
C:\ProgramData\miniconda3\python.exe scripts\goldset_intake.py pilot --a A.csv --b B.csv
```

It writes `evaluation/goldset/intake/pilot/agreement.json`, the adjudication queue, a blinded
`adjudication-context.html` for the disputed items, and a `decisions-template.csv` for the
adjudicator.

## 5. Pilot pass gates

These three gates measure two independent humans. The ruled pilot mode has one human, so under
section 10 they are not evaluated and cannot be reported as passed; section 10.4 states what is
reported in their place.

The pilot passes only when all three hold on the dual-annotated pilot items. The intake
command prints each with PASS or FAIL.

| Gate | Threshold | Meaning |
|---|---|---|
| Overall agreement | at least 0.80 | Observed agreement on the surface class across all items. |
| Message versus non-message | at least 0.90 | Agreement on the binary message-or-not decision, which is the load-bearing boundary. |
| Privacy agreement | near 1.00 (at least 0.99) | Agreement on the private class. Private-person material must almost never be missed. |

A failed pilot means the guide is not yet clear enough. The response is a guide revision and a
fresh pilot sample. A failed pilot never touches the sealed test split, and it never becomes
training data for a tuned threshold. Retire the failed pilot's items and reseal a new pilot
frame if the pilot pool is exhausted.

## 6. Adjudication and metrics

Every item where the two annotators disagree on class or family goes to the adjudicator. The
adjudicator fills the decisions template with their ID and the resolved class and family, then
the metrics command merges the two annotators with the decisions and reports the numbers.

```bash
C:\ProgramData\miniconda3\python.exe scripts\goldset_metrics.py full --a A.csv --b B.csv \
    --decisions decisions.csv
```

The metrics command refuses to report while any item is unresolved. When every item is either
an agreement or an adjudicated decision, it writes `evaluation/goldset/metrics/full/` and
prints, each with numerator, denominator, and a 95% Wilson confidence interval:

- Message precision: correct message labels over all predicted-message items.
- Document-family pairwise precision and recall, one family counted as one support unit.
- The party error gap: the absolute difference in error rate between the two parties, with a
  Newcombe interval on the difference.
- The full confusion matrix over the six classes.

## 7. Splits: what may be tuned and the run-once rule

The date-based splits exist so that any threshold the classifier learns is set on data the
final number never saw.

- **Train and validation.** The gold-set classifier threshold that R-33.2 adds to the
  affirmative message standard may be chosen and tuned on the train and validation splits.
  Iterate here as much as needed. Report interim numbers from these splits only.
- **Test.** The test split is measured once, with the threshold frozen, as the reported result.
  Run the metrics command on the test split one time. Do not tune anything against the test
  numbers and then rerun. The metrics command accepts `--split test` to restrict the report to
  the held-out split.

The run-once rule is a discipline, not a lock the tool enforces. If the test split is
inspected during tuning, it is burned, and a fresh test split must be sealed from later corpus
dates before a result can be reported.

## 8. Operator checklist, from hired to published

This is the two-annotator checklist, which the full sample follows. The ruled pilot runs the
shorter checklist in section 10.6.

Steps marked (Michael) are the operator's own acts. The rest are commands the operator runs.

1. (Michael) Recruit and pay two annotators and one adjudicator.
2. Confirm the seal: `scripts\goldset_seal.py verify` reports a matching `seal_hash`.
3. Render pilot packets: `scripts\goldset_bundle.py pilot`.
4. (Michael) Send each annotator their HTML packet and CSV answer sheet. Send the guide.
5. Collect the two returned pilot answer sheets.
6. Intake the pilot: `scripts\goldset_intake.py pilot --a A.csv --b B.csv`. Read the gates.
7. If a gate fails: revise `evaluation/ANNOTATION-GUIDE.md`, reseal a fresh pilot, return to
   step 3. Never touch the test split.
8. When the pilot gates pass, render full packets: `scripts\goldset_bundle.py full`.
9. (Michael) Send full packets. Collect the two returned full answer sheets.
10. Intake the full sample and give the adjudicator the queue and the blinded context.
11. (Michael/adjudicator) Resolve every disagreement into `decisions.csv`.
12. Compute metrics on train and validation while tuning the classifier threshold.
13. Freeze the threshold. Run metrics once on the test split with `--split test`.
14. (Michael) Publish the metrics. This is the R-33.1 and R-33.2 evidence that releases the
    validated surfaces. The release itself is Michael's act.

## 9. Reserved acts

These belong to Michael and are not part of any command:

- Recruiting, paying, and instructing the annotators and adjudicator.
- Sending packets and collecting answer sheets.
- Choosing and freezing the classifier threshold on train and validation.
- Deciding when the test result is run, and publishing it.
- Every release act that follows: activating the validated surfaces and the composite index
  name under R-33.1, subject to the election freeze in Constitution Article VIII.

## 10. The ruled pilot mode: single human rater with model triage

Authority: docs/26 Session 57. The pilot was blocked on hiring two annotators and an
adjudicator, which is a cost and a calendar the project does not have before the midterms. The
ruling unblocks it by changing who annotates, not by relaxing what the numbers may claim. The
mechanism that replaces personnel independence is total disclosure: the sealed bundles, the
answer sheets, and the labels publish openly so anyone can redo the work.

### 10.1 Who rates

- **Human rater (Michael).** He annotates every pilot item himself, working from the same
  sealed bundle and the same guide any hired annotator would receive. He is the author of the
  system, so he is not an independent rater. That is the limitation the label in 10.3 names,
  and it is why 10.5 refuses Gate B.
- **Model rater.** A frozen-prompt model reads the same annotation guide and the same blinded
  item context and produces its own answer sheet. It exists to find the items worth a second
  look. It is a second reading, not a second person.
- **No adjudicator.** With one human there is nothing to adjudicate between two humans. The
  human rater resolves his own flagged items in triage (10.4) and his post-triage label is the
  gold label.

Blinding is unchanged and still enforced by the kit. The bundle carries the phrase, its
sentence and neighbors, the office, the date, the title, and the support set. It carries no
predicted class, ranking, surge score, publication decision, or correction. The model rater
receives exactly the same fields, so neither reader sees the machine's own answer.

### 10.2 What the model rater may and may not do

- It may disagree with the human, and that disagreement is the queue the human works through.
- It may never write a gold label. Every label in the measured record is the human's.
- Its agreement with the human is reported as **human-versus-model agreement** and never as
  inter-annotator agreement, inter-rater reliability, kappa between annotators, or any phrasing
  that implies two independent human readings. The intake tool names the field accordingly and
  refuses to emit an inter-annotator field in this mode.
- Its prompt is frozen and content-addressed before any live call. The registration records the
  prompt text and its sha256, so the exact instrument that produced the model sheet is
  reproducible and any later edit to the guide or the wrapper invalidates the freeze.
- The model rater is not independent evidence. It reads the same guide and can inherit the same
  blind spots. It raises the chance that a careless human label gets a second look. It does not
  raise the reliability of the study.

### 10.3 The mandatory label

Every metric produced under this mode carries this label, verbatim, in the artifact and on any
surface that cites it:

> author-annotated, single human rater, provisional

The label is owned by the code (`pipeline/goldset_single.PROVENANCE_LABEL`) and stamped into
every output the single-rater intake and metrics commands write. A number from this mode that
appears anywhere without the label is a defect, not a shortcut. "Provisional" means the number
stands until independent replication either confirms or moves it.

### 10.4 The flow

1. Seal and render Michael's bundle (10.6 step 1 and 2).
2. Michael annotates every pilot item, blind, and exports his answer sheet.
3. The model rater runs against the same sealed bundle and writes its answer sheet.
4. Intake computes human-versus-model agreement, labeled as such, and emits the triage queue:
   every item where the two readings differ on class or family.
5. Michael works the triage queue. For each item he either keeps his label or revises it,
   recording which, and his post-triage label becomes the gold label. He may keep a label the
   model disagreed with; the model has no vote.
6. Metrics run on the post-triage labels and stamp the 10.3 label on every output.

The pilot gates in section 5 are not evaluated. The intake tool reports them as not applicable
in this mode rather than printing a pass, because a pass would assert a reliability measurement
that a single human rater cannot produce. What is reported instead is the agreement in step 4,
the triage volume, and how many labels the human revised after seeing the disagreement.

### 10.5 What this mode may not claim

- **Gate B stays unclaimed.** The docs/33 R-33.11 ladder places Gate B, the validated
  instrument, after the gold-set metrics. A single-rater author-annotated pilot does not
  release it and nothing may describe the instrument as validated on this evidence. Gate B
  waits for independent replication, which means labels produced by people who are not the
  author, on the published bundles, reported next to these numbers.
- **No inter-annotator reliability figure.** No kappa, alpha, or agreement number from this
  mode may be presented as inter-rater reliability.
- **No pilot-gate pass.** Section 5's gates measure two humans and are not evaluated here.
- The split discipline in section 7 is unchanged and still binding. The test split is measured
  once, with the threshold frozen, in either mode.

### 10.6 Publication and the standing re-annotation invitation

The point of publishing is that anyone can check the work and, if they disagree, replace it.
Published openly, alongside the metrics:

- The sealed sample manifests and the seal hash, already committed.
- Michael's blinded bundle, byte for byte the packet he annotated.
- His answer sheet, the model rater's answer sheet, and the triage record.
- The frozen rating prompt and its sha256.
- The metrics, each carrying the 10.3 label.

With those, a replication costs a reader nothing but their own time: open the same bundle,
label it, run the same two commands, and compare. The invitation is standing and is stated on
the surface that publishes the numbers. Replication labels sent back are published beside the
author's, whether they agree or not.

Nothing here weakens the privacy floor. The bundle is publication-grade only because it passes
the same gate every public artifact passes: no admitted private-person form reaches it, proven
by the production canary and a scan of the rendered bundle before it is published.

### 10.7 Operator checklist for this mode

Steps marked (Michael) are his own acts. The rest are commands he runs.

1. Confirm the seal: `scripts\goldset_seal.py verify` reports a matching `seal_hash`.
2. Render his bundle: `scripts\goldset_bundle.py pilot --annotators michael`.
3. (Michael) Open `michael.app.html`, annotate every item, export the answer sheet.
4. Preview the model rater at zero cost: `scripts\goldset_rate.py pilot`.
5. (Michael) Run the model rater live: `scripts\goldset_rate.py pilot --allow-api-spend`. This
   is the only step that spends money and it is his act alone.
6. Intake: `scripts\goldset_intake.py pilot --human <sheet> --model <sheet>`.
7. (Michael) Work the triage queue into the triage decisions CSV.
8. Metrics: `scripts\goldset_metrics.py pilot --human <sheet> --triage <decisions>`.
9. (Michael) Publish the bundle, both sheets, the triage record, and the metrics, with the
   10.3 label and the 10.6 invitation. Publication is his act, subject to the election freeze
   in Constitution Article VIII.

### 10.8 Michael's acts under this mode

Reserved to him, unchanged in kind from section 9 and shortened in list:

- Annotating the pilot, and every triage decision.
- Authorizing the one paid step, the live model-rater run.
- Choosing and freezing the classifier threshold on train and validation.
- Deciding when the test result is run.
- Publishing the bundle, the labels, and the metrics, and issuing the re-annotation invitation.
- Declaring any gate transition, including the Gate B that this mode does not release.
