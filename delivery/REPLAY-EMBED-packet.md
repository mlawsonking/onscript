# Replay and embedding work-order delivery packet

Branch: `opus/replay-embed`

Base: `b70b27c` (main at the S58 ruling that carries this work order).

Session 59 (Opus), 2026-07-28, claimed from the docs/26 tail (S58 was the last entry).

Validation command for every package:

```text
C:\ProgramData\miniconda3\python.exe tests\run_tests.py
```

The suite baseline was 814 passed and 0 failed. The final result is 883 passed and 0 failed.

**Exact spend this session: 0.00 USD.** No live API call was made. The reason is recorded in
full under R2 and is not budget: the preflight cleared on money and blocked on the key.

No push, deployment, workflow dispatch, post, `POSTING_ENABLED` change, or `FEATURES` value
change occurred. No `site/public` artifact was touched. The only `data/derived` writes are the
four R-track evidence artifacts under `data/derived/replay/`, which R-33.6 requires committed.
`AGENTS.md` and `tests/_tmp_watchdog/` remain untracked. Nothing was staged with `git add -A`.

Both mutation harnesses report every check load-bearing:

```text
C:\ProgramData\miniconda3\python.exe scripts\run_verifier_mutations.py
C:\ProgramData\miniconda3\python.exe scripts\run_registry_mutations.py
```

15/15 verifier checks and 30/30 registry invariants are load-bearing. The registry count rose
from 20 to 30 with the ten new shadow-replay invariants (R2).

**GPU wall time: 347.888 seconds** across 19 completed shards, on the RTX 4080 SUPER. The press
lane is deliberately left partial and resumable; see G2.

## Commit order

The two tracks are interleaved in history because G2 is a detached GPU run that had to start
early to have wall time. The order is G1, G1 followup, R1, R2, R3, R4, H1, G3, G2.

| Commit | Package |
|---|---|
| `cb3e894` | G1. The Alexandria Stage 2 GPU scripts |
| `fe9ba4e` | G1 followup. Dtype honesty and the determinism spot-check |
| `cf75067` | R1. Replay economics and the honest gate population |
| `d206ce4` | R2. Frozen instrument, budget preflight, refusal |
| `f9970e4` | R3. Incremental accumulation |
| `7d47b7b` | R4. The comparison report |
| `157d023` | H1. External heartbeat (Vikunja #203) |
| `690871a` | H1 followup. Remove the em dashes this session added |
| `dd336cf` | G3. The topic-tag pass, prepared and stopped |
| `a4df531` | R3 followup. A one-lane replay is not a whole day of gate progress |
| `a9ad869` | G1 followup 2. Read only the mirror files a Congress can hold |
| `df22fbb` | G2. The embedding pass and its verification manifest |

Four of these are followups rather than packages, and each names the defect it repairs in its
own message. Three were found by re-reading the work, not by a failing test, which is why each
one ships with the test that would have caught it.

## The finding that should be read first

The R-33.6 gate is at **1 of 60 complete days and 2 of 200 party-days**, not the 15 and 30 the
X6 delivery reported.

The X6 harness counted a committed day file as gate evidence whenever both parties carried a
composite. That is not the same question. A day is evidence about P2 v1.3 or P3 v1.1 only if
its record was written BY that prompt. Against the real corpus the committed days fail that on
three independent grounds, counted over 32 party-days (a party-day can fail more than one):

| Exclusion | Party-days |
|---|---|
| `stats_schema_mismatch` (pre-docs/28 stats cannot feed the v1.4 candidate prompt) | 30 |
| `prompt_lineage_mismatch` (written by P2 v1.0, v1.1 or v1.2, not v1.3) | 18 |
| `not_model_generated` (dry-run or deterministic voice, so no prompt ran) | 10 |

Comparing across that seam is what docs/37 rule 13 forbids, and the harness was doing it by
construction. Estimator: committed party-days whose production record was written by the live
prompt of its pair. Unit: party-day. Window: 2026-06-30 through 2026-07-26. Denominator: 60
complete days and 200 party-days, both required. Reproduce:

```text
C:\ProgramData\miniconda3\python.exe scripts\shadow_replay.py --plan --days-dir data\derived\days
```

The gate did not get smaller. It was never as full as the count implied. The flip stays blocked
and this session made the distance measurable.

## Package record

### R1. Replay economics

Commit: `cf75067`

Suite: 822 passed and 0 failed before. 835 passed and 0 failed after.

Two changes. The live side of the comparison is now read from the committed production record
rather than regenerated, which is both more honest (it is what OnScript published) and half the
cost. And `classify_record` states the eligibility ladder per party-day with a reason for every
exclusion, so the gate population is the one R-33.6 actually asks for.

The full ladder, from the committed corpus:

| Stage | Count |
|---|---|
| Committed day files | 18 |
| Days carrying a composite for both parties | 16 |
| Party-days carrying a composite | 32 |
| Gate-eligible days | 1 |
| Gate-eligible party-days | 2 |

Every artifact carries gate progress with its estimator, unit, window, and denominator. The
plan is deterministic and carries no clock. Cost projection: 2 calls, 0.008908 USD, priced only
on the generated side.

Committed artifact: `data/derived/replay/run-plan.json`.

The one design judgement worth naming: eligibility requires the docs/28 claim-binding stats
schema. The v1.4 and v1.2 prompts consume `selected_claims` typed claim objects, and a
pre-docs/28 record has none. Synthesising them with today's builder would render the candidate
against a stats block production never produced, while the record side used the builder of its
own day, and any difference would then be attributed to the prompt. That is the rule 13 seam in
miniature, so those days are excluded and labelled rather than patched.

### R2. The live run

Commit: `d206ce4`

Suite: 835 passed and 0 failed before. 848 passed and 0 failed after.

**The live run did not happen. Spend: 0.00 USD.** The budget cleared; the key did not exist.

Recorded verbatim in `data/derived/replay/live-run-refusal.json`:

```text
month-to-date            0.11552 USD
monthly code ceiling     9.00 USD
headroom                 8.88448 USD
authorized bound         3.00 USD
required headroom (2x)   6.00 USD
projection               0.008908 USD
governor state           nominal
blocking_reasons         ["no_api_key"]
spend                    0.00 USD
```

`ANTHROPIC_API_KEY` lives only in GitHub Actions secrets, which is the charter constraint, so an
operator box has no key by design. The workflow that does have one could not be dispatched: that
is outside this session's push scope, stated once in the work order. This is a stop with the
blocker named, not an improvisation around it.

The preflight now names that condition as `no_api_key` rather than letting `_headers` raise a
`KeyError` mid-run, after the instrument has been asserted and an operator believes a run
started. The CLI exits 2 with a readable refusal instead of a traceback.

Everything else in R2 shipped and is exercised:

- The replay instrument is content-addressed across all four prompt texts and frozen into
  `data/reference/replay-registration.json`. A live run asserts against it and refuses on drift,
  so an edited candidate prompt cannot spend under the identity of the registered one. This is
  the `goldset_rater` pattern from docs/35 section 10.2, applied to a second offline instrument.
- Ten new invariants enter the Y9 registry mutation harness: four prompt hashes, the combined
  replay address, the method version, the model, the fallback ceiling, and both R-33.6 minimums.
  The combined address is checked against an independent reimplementation of the composition
  rather than against the function that computes it, so a reordering of the formula fails.
- The preflight is two independent conditions, both required: the projection fits the authorized
  bound, and headroom under the code ceiling is at least twice that bound, so a replay can never
  be the spend that starves the daily voice.
- The evidence file admits live rows only. `append_evidence` raises on any non-live row. A dry
  row is a deterministic-voice composite, not an answer from the candidate prompt, and a gate
  counting those would count the harness's own template as evidence about a model.
- The candidate side is scored with the full verifier plus all four R-33.6 zero-tolerance checks
  and the fallback rate against the preregistered 0.05 ceiling. The live path is exercised in
  tests through an injected caller, so the scoring, hashing, and cost arithmetic are proven
  without fabricating a model response into the evidence file.

Order enforced and tested: freeze, then clear the budget, then call.

**Open item for Michael.** The two eligible party-days remain unreplayed. They need either a key
in the operator environment or a dispatch of a workflow carrying the Actions secret. Both are
his acts. The command is under R3 and is idempotent, so running it twice costs nothing extra.

### R3. Incremental accumulation

Commit: `f9970e4`

Suite: 848 passed and 0 failed before. 857 passed and 0 failed after.

`scripts/replay_accumulate.py` replays only the gate-eligible party-days with no evidence yet
under the current candidate prompt, and appends them to `data/derived/replay/evidence.jsonl`.
This is how the gate fills: production publishes one day at a time, so 60 complete days is
reached by re-running one command for weeks, not by one replay.

Append-only is held by test, not by intent: a second run appends nothing and the file is
byte-identical afterward; appending a later day leaves every earlier line verbatim; a moved
candidate prompt sha replays the day again rather than reusing evidence from a different
instrument. Each row stores its request hash beside the stored response and the response hash,
so any answer can be audited back to the exact rendered prompt. Rows are deterministic given the
model responses and carry no clock.

Gate progress here is measured on the **evidence**, not on eligibility: an eligible day with no
replayed candidate is a day the gate has not seen. Both numbers appear under separate names.

Current state, dry and free: 2 pending party-days (2026-07-25 D and R), 0 in evidence.

```text
C:\ProgramData\miniconda3\python.exe scripts\replay_accumulate.py
```

Committed artifact: `data/derived/replay/accumulation-status.json`.

### R4. The comparison report

Commit: `7d47b7b`

Suite: 857 passed and 0 failed before. 867 passed and 0 failed after.

`data/derived/replay/comparison-report.md`, rendered by `pipeline/replay_report.py`. Every
measured number carries its estimator, unit, window, and denominator.

On 2 scored party-days from 2026-07-25: gate progress 1 of 60 days (0.016667) and 2 of 200
party-days (0.01); the full eligibility ladder with every exclusion counted; per-check results
for the verifier and all five guards on both sides; fallback rate 0.0 on both against the 0.05
ceiling; and verifier drift on the record side at 0 of 2 party-days, reported rather than
smoothed.

The side-by-side is honest about its own weakness. Both party-days tie at 7 of 7 on the stated
quality score, so the report says in those words that a sample this small cannot separate the
prompts on quality, and labels the two shown as first and last in the reproducible order rather
than as a spread.

Two refusals are built in and tested. The report makes no flip recommendation, and the tests
assert the absence of advocacy phrasing. A dry report says on its own face that it is a
determinism check on the harness which says nothing about the candidate prompt.

The committed report is validated as pinned history (parses, complete, internally consistent),
deliberately **not** asserted byte-equal to a fresh render: it is built over `data/derived/days`,
so an equality test would turn the next published day into a suite failure. That is the docs/37
rule 3 incident exactly, and it was caught in this session by writing the equality test first
and then removing it.

```text
C:\ProgramData\miniconda3\python.exe scripts\replay_report.py
```

### H1. The external heartbeat

Commit: `157d023`

Suite: 867 passed and 0 failed before. 872 passed and 0 failed after.

Every alerting layer OnScript has runs inside GitHub Actions, so none can report Actions being
down or the watchdog schedule silently ceasing to fire. In both cases the probe never runs,
never fails, never pages, and every surface stays green. The heartbeat inverts the signal: an
external monitor alarms on the ping's absence.

`if: always()` rather than `success()`, to keep one alert per failure mode:

```text
the watchdog never ran   -> ping missing  -> the external monitor pages, and only it
the watchdog ran, broke  -> ping sent     -> the in-workflow dead-man pages, and only it
the watchdog ran, alarms -> ping sent     -> the probe itself paged, and only it
```

The curl swallows its own failure so an unreachable endpoint cannot redden the job it is
attached to.

This is workflow behaviour and it is inert on merge. It activates on two acts, both Michael's:
this file reaching the default branch (a scheduled workflow only ever runs from there, so that
push is the release act) and the `HEALTHCHECK_PING_URL` secret being created. The workflow
comment says so, next to the code it governs, and names Vikunja #203.

### G1. The Alexandria Stage 2 GPU scripts

Commits: `cb3e894`, `fe9ba4e`

Suite: 814 passed and 0 failed before. 822 passed and 0 failed after.

`scripts/deep/alexandria_embed.py` and `scripts/deep/alexandria_topic_tag.py`, both specified
in docs/34 and both previously left uncommitted because they pull a GPU stack.

The stack lives outside the repository:

```text
C:\ProgramData\miniconda3\python.exe -m venv --system-site-packages C:/Users/bobdo/venvs/onscript-embed
C:/Users/bobdo/venvs/onscript-embed/Scripts/python.exe -m pip install sentence-transformers==3.4.1
```

`--system-site-packages` is deliberate: the conda base already carries a working
`torch 2.6.0+cu124` against driver 591.86, so the environment adds only the encoder layer rather
than a second multi-gigabyte CUDA build. Documented in docs/34 section 3.

`requirements.lock` stays empty of runtime dependencies and the suite asserts the boundary: a
fresh interpreter importing both scripts pulls no third-party module, the missing-stack path
names where the environment lives instead of raising an ImportError traceback, and vector paths
are asserted never to resolve inside the repository working tree.

The followup commit corrects two things the smoke run exposed. docs/34 says "fp16 on the GPU"
and names an `f16.npy` output; those are two claims and one word was standing for both. Storage
is fp16 as specified; compute stays fp32, because the corpus encodes in minutes either way and
half-precision matmul would buy speed nobody needs at the cost of a numerical difference in the
artifact every later exhibit reads. The manifest records `dtype` and `compute_dtype` separately.
And the docs/34 section 6.2 determinism spot-check now runs inside the pass and lands in the
shard manifest, rather than depending on an operator remembering it afterward.

The frozen tagger config shipped here rather than in G3, because a fail-closed script without
its config cannot run at all.

### G3. The topic-tag pass, prepared and stopped

Commit: `dd336cf`

Suite: 872 passed and 0 failed, unchanged (documentation).

docs/34 section 4a states the run command, the two unmet prerequisites, and why the pass is not
run. The frozen config names `qwen2.5-14b-instruct` on LM Studio's default endpoint; LM Studio
is installed at `X:\LLAMA\LM Studio` and its library holds no model as of 2026-07-28, so the
endpoint would not answer. A changed model or endpoint requires re-freezing
`data/reference/alexandria-topic-tag.json`; the script fails closed against it.

The deeper reason for stopping is not the missing model. docs/03 section 1.4 draws the line that
a local model may compute but never write voice, and how far a run sits from that line depends
on what its output can be mistaken for. A 384-dimensional vector cannot be mistaken for prose. A
14B model's free text can. The tagger stays an operator decision with a named owner.

### G2. The embedding pass

Commit: `df22fbb`

Suite: 875 passed and 0 failed before. 883 passed and 0 failed after.

Run on the RTX 4080 SUPER through the venv outside the repository, detached per docs/37 rule 10.
The vectors stay on X: and never enter the repository. What lands here is the verification
manifest at `data/reference/alexandria-embeddings-manifest.json`.

State at delivery:

| Lane | Shards | Rows | Delta | Status |
|---|---|---|---|---|
| crec | 13/13 | 152,172 | 0 | complete |
| press | 6/13 | 2,371 | congresses 113-119 outstanding | partial, resumable |
| total | 19/26 | 154,543 | | GPU wall time 347.888 s |

Model identity, carried on every shard manifest and reconciled in the verification manifest:

```text
model      sentence-transformers/all-MiniLM-L6-v2
revision   1110a243fdf4706b3f48f1d95db1a4f5529b4d41
dimension  384, storage float16, compute float32, normalized, max_seq_length 256
```

Determinism, checked inside the pass per docs/34 section 6.2 by re-encoding one batch per shard:
worst `max_abs_delta` across 19 shards is 1.43e-07, and 0.0 exactly on most.

Independently spot-checked on written shards: vectors load at (rows, 384) float16, row counts
equal their manifests, and L2 norms sit at 1.0000 to 1.0001, which is unit length within fp16.
Every id row carries the provenance lane docs/34 section 2 requires: `date_source` for press
(legacy, scraper, page_html, with the 2021-01-03 instrument seam), `source=crec` plus
`crec_section` for CREC, alongside congress and the join keys an exhibit needs.

**The CREC delta reads 0 rather than -15 because the manifest names what it excludes.** docs/34
section 1 gates 152,187 CREC E-statements, 15 of which are dated to congress 106 and sit outside
a pass covering 107 through 119. An unexplained shortfall of 15 rows and a documented exclusion
of exactly 15 rows are indistinguishable in a row count, and only one of them is fine. The
manifest carries the gate total, the out-of-scope rows by name, and the in-scope expectation as
three separate fields.

**Why the press lane is partial.** Its cost is `normalize_records` over 95k to 160k full-text
records per Congress, not the GPU, which held near 40 percent throughout. Two rounds of
measurement went into this rather than one guess: the first pass was disk-bound, reading all 303
mirror shards per Congress across a 2.38 GB mirror on X:, roughly 31 GB of reads for the corpus
(fixed in `a9ad869`, and the identical fix applied to the CREC year files in this commit). What
remains is genuine normalize cost on the large Congresses. The work order names a healthy
partial as success, and this one is healthy: resume is per (lane, congress) and proven, since the
restarted run skipped all six completed shards by manifest and rebuilt none of them.

Continue it with the same two commands; the manifest reflects exact progress each rebuild:

```text
C:/Users/bobdo/venvs/onscript-embed/Scripts/python.exe scripts/deep/alexandria_embed.py
C:\ProgramData\miniconda3\python.exe scripts\deep\alexandria_embed_manifest.py
```

The precondition gate was re-run at session start and reported READY with delta 0 across every
Congress, matching docs/34 section 1 exactly: 684,853 press statements and 152,187 CREC
E-statements, 837,040 embeddable units.

## Deviations from the work order

1. **The R2 live run did not happen.** Spend 0.00 USD. The blocker is the absent
   `ANTHROPIC_API_KEY`, not the budget, which cleared with 8.88448 USD of headroom against a
   6.00 USD requirement. The key lives only in Actions secrets by charter, and dispatching the
   workflow that holds it is outside the stated push scope. Dated deferral note: 2026-07-28.
   The mechanism, the freeze, the preflight, and the scoring all shipped and are tested; only
   the call is outstanding, and R3's command performs it idempotently when a key exists.

2. **The frozen tagger config shipped in G1 rather than G3.** G1 was specified as "the embed and
   tag scripts" and G3 as "its script and frozen config", which overlap. A fail-closed script
   without its config is not shippable, so the config went with the script and G3 carries the
   run command and the prepared-not-run record.

3. **Commit order interleaves the tracks.** G1 landed before R1 so the detached GPU run could
   start early and have wall time. The packages are otherwise one commit each with the suite
   green before and after.

4. **`.gitignore` gained two allowlist entries.** `data/reference/*` is ignored with explicit
   re-includes; the two new frozen instruments (`alexandria-topic-tag.json`,
   `replay-registration.json`) follow that existing pattern, each with a comment naming why it
   must be committed.

5. **The production cost ledger was not written.** No spend occurred, so there is nothing to
   record. Had the live run happened, the exact cost would have been reported here for
   reconciliation rather than committed from a branch, because `data/derived/cost/2026-07.json`
   is production state written by the cloud run and a local write would conflict with it.

6. **`vtask add` could not be run.** The errand for the live replay (below) was refused twice by
   this session's permission layer, so it is not in Vikunja. It is recorded here instead and
   needs filing by hand. Nothing else in the standing task list was touched; #203 stays open,
   correctly, because H1 is inert until Michael merges and creates the secret.

## Incomplete items and blockers

- **The R-33.6 live replay of the 2 eligible party-days.** Blocked on `ANTHROPIC_API_KEY`, which
  is Michael's to supply locally or to reach by dispatching a workflow that holds the Actions
  secret. Not a defect in the delivery: the harness, the freeze, the preflight, and the scoring
  are all built and tested, and the command is idempotent.

  ```text
  C:\ProgramData\miniconda3\python.exe scripts\replay_accumulate.py --live --allow-api-spend
  ```

  Budget state as measured: month-to-date 0.11552 USD, headroom 8.88448 USD against a 6.00 USD
  requirement, projection 0.008908 USD, hard bound 3.00 USD. This is the first evidence toward
  the gate, not the flip decision.

- **The press embedding lane, congresses 113 through 119.** Partial by design and resumable;
  see G2 for the command and why it is not a blocker.

- **The topic-tag pass.** Prepared and deliberately unrun; see G3.
