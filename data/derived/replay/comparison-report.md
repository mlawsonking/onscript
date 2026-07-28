# R-33.6 shadow replay: P2 v1.4 and P3 v1.2 against the published record

Method version shadow-replay-v2, report replay-report-v1. Replay instrument `19304d43ffc77b14`.

## What this compares

The live side is not generated. P2 v1.3 and P3 v1.1 ran in production on real days and their composites are committed in `data/derived/days`, so the live side of every party-day is what OnScript actually published, read back and rescored. Only the v1.4 and v1.2 side is generated. That is why the cost projection prices one call per party-day rather than two.

Mode: **dry_run**. A dry run is a determinism check on the harness. It says nothing about the candidate prompt, because the composite it scores comes from the deterministic voice, not from v1.4 or v1.2. No dry row is admitted to the evidence file.

## Gate progress

| Minimum | Observed | Required | Fraction | Remaining |
| --- | --- | --- | --- | --- |
| Complete days | 1 | 60 | 0.016667 | 59 |
| Party-days | 2 | 200 | 0.01 | 198 |

Estimator: committed party-days whose production record was written by the live prompt of its pair, over the R-33.6 minimums. Unit: party-day (one party lane on one measured day). Window: 2026-07-25 through 2026-07-25. Denominator: 60 complete days and 200 party-days, both required.

Minimum sample passed: **False**.

## Why the population is smaller than the file count

A committed day file is not automatically evidence about the live prompt. It counts only if its record was written BY the live prompt of its pair: the same prompt sha, a real model generator rather than the dry-run or deterministic voice, and a stats block of the schema the candidate prompt consumes. Mixing lineages in one comparison is what docs/37 rule 13 forbids.

| Stage | Count |
| --- | --- |
| Committed day files | 18 |
| Days carrying a composite for both parties | 16 |
| Party-days carrying a composite | 32 |
| Gate-eligible days | 1 |
| Gate-eligible party-days | 2 |

Exclusions, counted over 32 party-days (a party-day can fail more than one condition):

| Reason | Party-days |
| --- | --- |
| not_model_generated | 10 |
| prompt_lineage_mismatch | 18 |
| stats_schema_mismatch | 30 |

## Per-check results

Window: 2026-07-25 through 2026-07-25. Denominator for every row: 2 scored party-days.

| Check | Live (record) | Candidate | Estimator | Unit |
| --- | --- | --- | --- | --- |
| Full verifier pass | 2 of 2 | 2 of 2 | party-days whose composite passes verify_daily_line | party-day |
| Unit mixing | 0 of 2 | 0 of 2 | party-days where a sentence states one unit's count without labelling all three | party-day |
| Quote extension | 0 of 2 | 0 of 2 | party-days rendering a quote that is not a selected claim's display_quote | party-day |
| Topic-label assertion | 0 of 2 | 0 of 2 | party-days asserting a classifier topic label outside quotation marks | party-day |
| Multi-claim sentence | 0 of 2 | 0 of 2 | party-days with a sentence mapping to more than one claim id | party-day |
| Sentence mapping mismatch | 0 of 2 | 0 of 2 | party-days whose supplied sentence_claims differ from the computed mapping | party-day |

### Fallback rate against the preregistered ceiling

| Side | Fallback party-days | Denominator | Rate | Ceiling | Within ceiling |
| --- | --- | --- | --- | --- | --- |
| Live (record) | 0 | 2 | 0.0 | 0.05 | True |
| Candidate | 0 | 2 | 0.0 | 0.05 | True |

Estimator: fallback party-days / offered party-days. Unit: party-day share. Window: 2026-07-25 through 2026-07-25.

## Verifier drift on the record side

Party-days where today's verifier disagrees with the verdict stored on the day: **0 of 2**. A non-zero count is a verifier-version finding about the record, not about either prompt, and it is reported rather than smoothed.

## Composite quality, side by side

Ranked by a stated score: one point for the verifier, one for each of the five clean guards, one for not falling back. Maximum 7. Ties break on day then party, so the selection is reproducible.

Every scored party-day ties at 7 of 7, so the two shown below are the first and last in the reproducible order, not a spread. A sample this small cannot separate the prompts on quality.

### Strongest day for the candidate: 2026-07-25 D (P3)

|  | Live (committed record) | Candidate (generated) |
| --- | --- | --- |
| Quality score (max 7) | 7 | 7 |
| Verifier | pass | pass |
| Fallback | False | False |
| Guard violations | none | none |
| Generator | sonnet_direct | generated_dry |

Live composite:

> We released 3 statements today.

Candidate composite:

> We released 3 statements today.

### Weakest day for the candidate: 2026-07-25 R (P3)

|  | Live (committed record) | Candidate (generated) |
| --- | --- | --- |
| Quality score (max 7) | 7 | 7 |
| Verifier | pass | pass |
| Fallback | False | False |
| Guard violations | none | none |
| Generator | sonnet_direct | generated_dry |

Live composite:

> We released 2 statements today.

Candidate composite:

> We released 2 statements today.

## Accumulated evidence

`data/derived/replay/evidence.jsonl` holds 0 party-days across 0 days, append-only, each row carrying its request hash beside the stored response.

## Activation status

| Condition | Result |
| --- | --- |
| Minimum sample (60 days, 200 party-days) | False |
| Zero-tolerance checks clean | True |
| Fallback rate within 0.05 | True |
| Ready to activate | False |

This report makes no flip recommendation. R-33.6 states the conditions and the gate decides. Until every condition above reads true on live evidence, P2 v1.4 and P3 v1.2 stay dark.

## Reproduce

```text
C:\ProgramData\miniconda3\python.exe scripts\shadow_replay.py --plan
C:\ProgramData\miniconda3\python.exe scripts\shadow_replay.py
C:\ProgramData\miniconda3\python.exe scripts\replay_accumulate.py
```
