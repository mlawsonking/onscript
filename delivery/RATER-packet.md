# Model-rater generation delivery packet

Branch: `opus/model-rater-run`

Base: `ac58742` (main at the S59 validation).

Validation command for every package:

```text
C:\ProgramData\miniconda3\python.exe tests\run_tests.py
```

The suite baseline was 883 passed and 0 failed. The final result is 892 passed and 0 failed.
No push, deployment, workflow dispatch, post, live API call, `POSTING_ENABLED` change, or
`FEATURES` value change occurred. No `site/public` or `data/derived` artifact was touched. The
only `data/` read was the statements corpus, read-only. Spend for the whole session is
0.00 USD.

## The one sentence Michael needs

The model rater's answer sheet is sealed and committed for P4 triage. Do not open it before
your own answer sheet is locked, because reading it first would make your labels a reaction to
its labels, and the sheet exists precisely to disagree with a label you reached on your own.

## Package record

### M1. A session transport for the model rater

Commit: `985f2d3`

Suite: 883 passed and 0 failed before. 892 passed and 0 failed after.

`pipeline/goldset_rater.py` gains a second transport carrying the same frozen instrument to a
different reader. The API path is untouched. What the deviation is allowed to move, and what it
may not, is enforced rather than asserted:

- `instrument_drift()` and `assert_instrument_registered()` gate on the frozen prompt alone:
  `prompt_id`, `prompt_version`, `wrapper_sha256`, `guide_sha256`, and the combined
  `rating_prompt_sha256`. The `model` field is a transport fact and is the only field the
  session path may differ on. A test holds both halves of that boundary: a registration whose
  model was changed drifts on exactly `model` and passes the instrument check, and a guide edit
  refuses a session run with the same `re-freeze` message a live run gives.
- `build_request()` now keeps the rendered item blocks beside the message it built them into, so
  `item_request_sha256()` can address one item's request over the instrument address, the group
  key, the candidate id, and the exact block sent. Both transports hash identically, so either
  sheet is re-derivable from the sealed bundle without the run that produced it. Moving the
  block or the guide moves the address; a test proves both.
- Session answers are validated against `evaluation/annotation.schema.json`, read from its owner
  rather than restated. The API parser normalizes an out-of-range value to blank, which is right
  for text a remote model wrote; an answer emitted by a transport this repository controls is
  refused instead, so a typo cannot become a silently blanked column. A test bumps the schema
  and watches the validator's verdict follow it (docs/37 rule 1).
- `run_session()` feeds those answers through the same `parse_response()` the API path uses, so
  one code path produces the sheet whatever read the items. What differs is stated, not implied:
  `reader_model` beside `registered_model`, absent token accounting rather than a fabricated
  zero, and `cost_usd` 0.0.
- `scripts/goldset_rate.py --transport session` runs in two steps because the reader works
  between them. `--emit` writes the worksheet; `--collect` re-derives every per-item hash from
  the live bundle and refuses if any moved since emit, refuses to write a sheet that is
  incomplete or fails `goldset_metrics.validate_rows`, and writes the manifest naming every
  problem either way. The flag combination is guarded: session mode requires exactly one of
  `--emit`/`--collect`, requires `--reader-model` so the reader is never recorded as the
  registered API model, and rejects `--allow-api-spend`.

Acceptance: `tests/test_n4_model_rater.py` grows from 11 tests to 20.

Files: `pipeline/goldset_rater.py`, `scripts/goldset_rate.py`, `tests/test_n4_model_rater.py`.

### M2. The sealed answer sheet, 200 of 200

Commit: `7bc7e17`

Suite: 892 passed and 0 failed before and after (M2 adds no code).

```text
sealed bundle       pilot, seal 7facc4d2323596a71153997fda33a924324634f1a096c5dee2df221ec86a00d3
rating instrument   1aa8447702f2b163103a3f23fc7447ebece81395189e1a6c2bbae885144a8246
wrapper             90e0661f52ad3f8c2943b0e07242ff6c6c03bba9fc7ef1ec11e767cf8b3402cc
guide               2243cddef095cc30e5eb39fe1c7689cbe444e409593d1f4b020891b046e0daf2
registered reader   claude-sonnet-5
actual reader       claude-opus-5
rater id            model-rater-GS1-v1.0-claude-opus-5
sheet sha256        363ecdfc2752f5371e4209b25736f8f65cd428b6ed9ccd7c80e9647138440c8e
items               200 of 200 over 148 day-and-party groups
errors              0 parse errors, 0 schema problems, 0 sheet validation problems
wall time           1317 s
spend               0.00 USD, no Anthropic call made
```

The rating instrument matches the Y9 registration on all five frozen fields. The per-item
request hashes for all 200 items are in `model-rater.run.json`, and the collect step re-derived
them from the live bundle before accepting the answers.

**How the pass was run.** In bundle order, group by group: frozen prompt plus that group's
items, answer, next. No earlier answer was revisited after a later item, so each item stands
alone the way an API call would leave it. Within a group the family task was applied across the
group's items, which is what a single API call does, because a group is one call. Answers were
appended through a validator that refused any batch out of worksheet order, any duplicate
candidate id, and any answer failing the committed schema.

Files, all under `evaluation/goldset/bundles/pilot/`:

- `model-rater.answersheet.csv`, the sheet, in the exact shape `goldset_intake.py --model`
  ingests. Pass `--model-rater model-rater-GS1-v1.0-claude-opus-5` so the intake record names
  the reader that actually answered.
- `model-rater.run.json`, the generation manifest.
- `model-rater.session-answers.jsonl`, the raw reading, committed so the sheet is reproducible
  from it.

The worksheet, the requests, the system prompt copy, and the plan are deterministic outputs of
`scripts/goldset_rate.py` and stay uncommitted rather than duplicating identity facts in a
second carrier.

## The deviation and its authorization

The N4 contract routes the model rater through the Anthropic API and reserves that call to
Michael because it spends money. The work order for this session, on Fable's authority in the
S59 lineage, permits the transport to be a subscription session instead, under the docs/03
precedent for one-time subscription-scripted work at zero marginal cost. Everything else in N4
holds and was verified rather than assumed:

- The FROZEN prompt only. `rating_prompt_sha256` is `1aa84477...`, matching the Y9 registration
  and the committed `rater-registration.json`.
- Drift refusal. Both session steps call `assert_instrument_registered()` and exit non-zero on
  drift.
- Request hashing. Per-item, over the instrument address plus the exact block sent, recorded for
  all 200 items and re-derived at collect.
- Registration intact. `evaluation/goldset/rater-registration.json` was not edited. It still
  names `claude-sonnet-5`, which is now a statement about the registered reader rather than the
  one that read. The manifest carries both `registered_model` and `reader_model` so the
  difference is on the record instead of being papered over.

The rater identity is recorded truthfully as this session's model, `claude-opus-5`, in the
manifest and in the `rater_id` the sheet is ingested under. The frozen-prompt id
`model-rater-GS1-v1.0` is carried alongside as `frozen_prompt_rater_id`.

**What this changes about the sheet's standing.** Nothing about docs/35 section 10.2: these
labels are triage input, never gold labels, and their agreement with Michael's is
human-versus-model agreement and nothing else. One thing is worth stating plainly for anyone
replicating: a replication that runs the API path gets Sonnet reading the same frozen prompt,
not this reader. The instrument is reproducible; this particular reading is reproducible only
from the committed answers file.

## Contamination discipline, and one exposure to weigh

The rating used the frozen prompt and each item's bundle context and nothing else. The
classifier source, `eligibility.py`, committed day records, the review adjudications in
docs/29, docs/33, and docs/36, and prior sessions' discussion of specific phrases were not
opened. Where a label was genuinely uncertain, the answer is whatever the frozen prompt alone
supports, which is why `unknown` carries most of the sheet.

One exposure has to be disclosed rather than left for triage to discover. This session's
harness loaded a stored memory line from an earlier session stating that a pilot LLM and the
deterministic classifier agreed only about 28 percent of the time and that the classifier
likely over-labels message and procedural. That is an aggregate observation, not an item-level
one, and no item's context came with it, but it was in context before the first label and it
points in the same direction as this sheet's distribution. It is named here so triage can weigh
it rather than assume the reading was clean of any prior signal.

## What the sheet looks like

Distributions, not conclusions. The denominator is 200 items.

```text
gold_class      unknown 128  nomenclature 41  message 16  procedural 11  biographical 3  private 1
phrase_complete false 139  true 61
stance          affirmative 196  negated 3  mixed 1
claim_supported false 169  true 27  not decidable 4
proposition     true 151  false 45  not decidable 4
distinct families 176
```

Three method facts drive most of that shape, and each is a place where a reasonable rater could
land elsewhere. Triage is the right venue for all three.

1. **The message test's completeness gate was applied literally.** Guide section 3 says a phrase
   is a message only when all three conditions hold, one of which is task B completeness. Many
   pilot candidates are n-gram windows that stop on a preposition, a conjunction, an auxiliary,
   a possessive, or mid-name. Under a literal reading those cannot be messages however
   substantive their words, so they fall to `unknown`, the guide's stated safe default. A rater
   who treats completeness as a soft signal rather than a gate would move a visible share of
   those 128 into `message`.
2. **Task F counts documents, not carriers.** Where a support set is one template, one cosigned
   letter, or one quotation reproduced by several offices, it was counted as one supporting
   document, so `claim_supported` is false. That follows the guide's stated trap about joint
   documents, extended to template reuse, which the guide addresses under task E but not
   explicitly under task F.
3. **Name-bearing fragments went to nomenclature.** A phrase built around an official name, an
   office, a committee, an act, or a public official's name was labeled nomenclature even when
   it carried scaffolding, which is what puts 41 items there.

## Variances and deviations

1. **The transport itself**, recorded in full above with its authorization.

2. **The instrument check is narrower than the API check, on purpose.** `assert_registered()`
   still covers all six fields and still guards the API path. The session path uses
   `assert_instrument_registered()`, which covers the five prompt fields. Widening it would
   refuse the authorized deviation; narrowing it further would let a guide edit through. The
   split is the smallest one that lets the reader change and nothing else.

3. **The rater id carries the reader.** `session_rater_id()` returns
   `model-rater-GS1-v1.0-claude-opus-5` rather than the bare frozen-prompt id, because the sheet
   itself has no annotator column and the id is the only identity that travels with it into
   intake. The frozen-prompt id is preserved in the manifest.

4. **One boundary was settled mid-pass and earlier answers were not revised.** For fragments
   consisting of a preposition plus an official name plus a trailing possessive, the first such
   item (`cand:33dc597f7685204e`, group 24) was answered `unknown` on the completeness gate; a
   later item of the same shape (`cand:8c7f699e6cbd2d72`, group 67) was answered `nomenclature`
   on the reasoning that the phrase is built around an official name. Both readings are
   defensible under the guide and the notes on each row say which was applied. They were left
   as answered because revisiting an earlier item after seeing a later one is exactly the global
   smoothing the work order forbids, and an API run would have the same seam. Triage should
   expect this pair to disagree with each other.

5. **Token accounting is absent rather than zero.** A session transport cannot measure the
   tokens an API call would have billed, so the manifest says so in words instead of writing a
   0 that would read as a measurement. The API-equivalent estimate from the same requests
   ($2.325938 upper bound on Sonnet) is carried under `api_equivalent_estimate` for the record.

## What was not done

- No push. The branch `opus/model-rater-run` is local and is the only branch touched.
- No intake, no metrics, no triage. Steps 6 through 8 of the docs/35 section 10.7 checklist wait
  on Michael's own answer sheet.
- Task #216, Michael's pilot annotation, is untouched and still his. This session produced the
  second reading that his triage queue will be built against.
