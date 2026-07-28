# 35: Gold-set annotation protocol

Authority: this document governs how the OnScript gold set is annotated, adjudicated, and
measured. It serves the docs/33 rulings R-33.1 (the on-script index returns only after the
gold-set metrics publish) and R-33.2 (fail-closed classification with the unknown class). It
is the operating manual for the annotation kit built under the ANNOT work order. Human
annotation execution, recruiting, and all release acts are Michael's, per docs/33 section 4.

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
