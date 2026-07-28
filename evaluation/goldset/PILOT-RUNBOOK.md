# Pilot runbook: annotate, triage, measure

For Michael, under the docs/35 section 10 single-human-rater mode. Everything here is one
page on purpose. The protocol is docs/35; the labeling rules are `ANNOTATION-GUIDE.md` in the
directory above this one. The house runner is `C:\ProgramData\miniconda3\python.exe`.

Two hundred items. Budget roughly one to two hours. Nothing here needs the network except
step 4, which is the only step that costs money.

## 1. Open the packet and annotate

Open `bundles/pilot/michael.app.html` in a browser. It is a single offline file: no server, no
network, nothing to install. Read the guide first, at least section 1 and section 3.

Click the surface class, type a family id, and set the optional tasks. Every change autosaves
in that browser, so you can close the tab and reopen the same file to resume. The header shows
how many items are labeled. Class and family are required on every item; the other tasks
follow the guide.

You are blind by construction: the packet carries the phrase, its sentence and neighbors, the
office, the date, the title, and the support set, and carries no predicted class, ranking, or
publication decision. Do not look at the live site while the pass is open.

When the counter reads 200 / 200, click **Export answer CSV**. Save it as
`evaluation/goldset/bundles/pilot/michael.answersheet.csv`.

## 2. Confirm the seal (10 seconds)

```
C:\ProgramData\miniconda3\python.exe scripts\goldset_seal.py verify
```

It must report a matching `seal_hash`. A mismatch means the corpus moved and the kit has to be
resealed before any number is reported.

## 3. Preview the model rater, for free

```
C:\ProgramData\miniconda3\python.exe scripts\goldset_rate.py pilot
```

This builds every request, checks the frozen rating prompt, prints an upper-bound cost, and
writes `bundles/pilot/model-rater.plan.json` and `model-rater.requests.jsonl`. It spends
nothing and makes no call. Read the plan, and read a request or two, before step 4.

## 4. Run the model rater live (your act, the only spend)

```
C:\ProgramData\miniconda3\python.exe scripts\goldset_rate.py pilot --allow-api-spend
```

Needs `ANTHROPIC_API_KEY` in the environment. It refuses if the prompt or the guide drifted
from `rater-registration.json`; if that happens, re-freeze with `--freeze` deliberately, then
rerun. It writes `model-rater.answersheet.csv` and a run record with the real billed cost.

The model is a second reading, not a second person. Its labels never become gold labels.

## 5. Intake and the triage queue

```
C:\ProgramData\miniconda3\python.exe scripts\goldset_intake.py pilot --human evaluation\goldset\bundles\pilot\michael.answersheet.csv --model evaluation\goldset\bundles\pilot\model-rater.answersheet.csv
```

Writes `intake/pilot/single/`: the human-versus-model agreement, the triage queue, a blank
triage template, and a blinded HTML page showing only the disputed items. The pilot gates are
reported as not evaluated, because they measure two humans and this mode has one.

## 6. Work the triage queue

Open `intake/pilot/single/triage-context.html` and, for each queued item, decide again. Fill
`triage-template.csv` and save it as `intake/pilot/single/triage.csv`:

- `resolution` is `keep` or `revise`.
- `keep` leaves your original label. The model gets no vote.
- `revise` needs a `gold_class` and a `gold_family_id`. Your revision is your own second
  decision, not the model's label.
- `notes` is optional and worth filling on close calls.

## 7. Metrics

```
C:\ProgramData\miniconda3\python.exe scripts\goldset_metrics.py pilot --human evaluation\goldset\bundles\pilot\michael.answersheet.csv --triage evaluation\goldset\intake\pilot\single\triage.csv
```

Writes `metrics/pilot/metrics-single-human.json`. Every output carries the mandatory label:

> author-annotated, single human rater, provisional

Add `--split train` or `--split validation` while tuning a threshold. The test split is run
once, with the threshold frozen (docs/35 section 7). That rule is unchanged in this mode.

## 8. Publish, and invite replication

Publish together: the bundle you annotated, your answer sheet, the model's answer sheet, the
triage record, the frozen prompt and its sha256, and the metrics with the label. State the
standing invitation: anyone may re-annotate the same bundle and publish their labels beside
yours. That openness is what replaces a second hired annotator, and it is the reason these
numbers may be published at all.

What you may not say on this evidence: that the instrument is validated, that Gate B is
reached, or that any number here is inter-annotator reliability. Gate B waits for labels from
someone who is not the author. Publication is your act and stays subject to the election
freeze in Constitution Article VIII.
