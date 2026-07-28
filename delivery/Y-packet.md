# Y work-order delivery packet

Branch: `opus/y-packages`

Base: `ecdb041ed530b853b5622006d6b39e7ab719d4fe` (main at the S55 ruling that carries the Y
work order). Current `main` is `6eaab13` (S56 docs/37, a docs-only commit that came after the
order); the branch is based on the commit the work order names. docs/37 and Constitution
Article XVII bind this session and were read from history; they contain no code, so the base
choice does not affect the implementation.

Validation command for every package:

```text
C:\ProgramData\miniconda3\python.exe tests\run_tests.py
```

The suite baseline was 702 passed and 0 failed. The final result is 771 passed and 0 failed.
No push, deployment, workflow dispatch, post, live API call, `POSTING_ENABLED` change, or
`FEATURES` value change occurred. The one ruled exception to leaving `data/` untouched is the
Y1 public correction appended to `data/reference/corrections.json`; no `site/public` or
`data/derived` artifact was regenerated.

Two mutation harnesses report every check load-bearing:

```text
C:\ProgramData\miniconda3\python.exe scripts\run_verifier_mutations.py
C:\ProgramData\miniconda3\python.exe scripts\run_registry_mutations.py
```

15/15 verifier checks and 15/15 registry invariants are load-bearing.

## Package record

### Y1. Fingerprint integrity (R-36.2)

Commit: `1aaf66f`

Suite: 702 passed and 0 failed before. 713 passed and 0 failed after.

Method and schema versions are read from their owning modules, never copied as strings.
`METHOD_VERSION_PROVIDERS` reads document_families, eligibility.CLASSIFIER, surges,
participation, denominators, goldset, distill.STRUCTURED_COMPOSITE_VERSION, shadow_replay,
and status_exports. `SCHEMA_VERSION_PROVIDERS` reads contracts and corrections. Code identity
becomes `code_tree_hash`, a content hash over the measurement tree (pipeline code, prompts,
taxonomy, schemas) with normalized line endings, excluding data and site output. The
fingerprint is stamped once at assembly; the post manifest inherits it and the exports inherit
the cycle fingerprint. A provider-discovery test fails when a production method module is
absent from the registry. The public correction (major, category wrong-method-attestation) is
appended to `data/reference/corrections.json` with the count checkpoint bumped 5 to 6.

Acceptance: `tests/test_y1_fingerprint_integrity.py` (11 tests). Bumping a live METHOD_VERSION
moves the fingerprint with no registry edit; code identity excludes data and site; day, post,
and API artifacts in one cycle carry one identical fingerprint; the committed 2026-07-25 day
record and post manifest carry different fingerprints (the confirmed defect) and the
inheritance path removes the drift; the wrong-method-attestation correction is published.

Files:

- `pipeline/instrument_fingerprint.py`
- `pipeline/distill.py`
- `pipeline/site.py`
- `pipeline/status_exports.py`
- `pipeline/post_bluesky.py`
- `pipeline/ops.py`
- `pipeline/run_assemble.py`
- `data/reference/corrections.json`
- `data/reference/corrections-count.json`
- `tests/test_x1_instrument_fingerprint.py`
- `tests/test_w3_publication.py`
- `tests/test_y1_fingerprint_integrity.py`

### Y2. Discipline withdrawal (R-36.3)

Commit: `c17555d`

Suite: 713 passed and 0 failed before. 718 passed and 0 failed after.

The per-party discipline index is withdrawn from newly generated day records. The build path
emits a `legacy_unvalidated_metrics` carrier with status withdrawn, a stated reason, and the
discipline values retained under it, instead of a top-level discipline field.
`withdrawn_discipline_view` returns the metric as withdrawn for both the historical top-level
shape and the new carrier shape. The separate `discipline.json` instrument-state artifact is
not touched. Historical committed records are not rewritten; the schema stays additive.

Acceptance: `tests/test_y2_discipline_withdrawal.py` (5 tests). A freshly built day record has
no top-level discipline and carries the withdrawn carrier with a nonblank reason; reading the
real committed 2026-07-24 record (index 0.7692 top level) and the 2026-07-25 record the review
cited returns withdrawn.

Files:

- `pipeline/build.py`
- `tests/test_y2_discipline_withdrawal.py`

### Y3. Temporal truthfulness (R-36.4)

Commit: `fd66e88`

Suite: 718 passed and 0 failed before. 725 passed and 0 failed after.

The homepage resolves one of five temporal states by comparing the shown day to the expected
latest complete day (`util.product_day`) and the assemble manifest's degraded, force-finalized,
and age state. It renders the ruled heading from a new `public_strings` authority and shows a
publication-lag line when the reading trails by more than one day. The homepage title no longer
hardcodes Today and no longer carries a U+2014 em dash. Social posts posted after their
measured date no longer say today: `build_thread` neutralizes the residual today in the
composite to the absolute measured date, applied identically to both parties, gated on the post
date differing from the measured day. Stored records are not rewritten.

Acceptance: `tests/test_y3_temporal.py` (7 tests). The resolver returns each of the five states;
the live force-finalized stale scenario resolves to publication delayed, not today; each state
renders its ruled heading; a delayed-day social post carries the absolute date and not today,
both parties; a same-day post keeps today; the title carries no em dash.

Files:

- `pipeline/public_strings.py`
- `pipeline/site.py`
- `pipeline/post_bluesky.py`
- `tests/test_y3_temporal.py`

### Y4. Deterministic nulls and state-aware posting (R-36.5)

Commit: `cb64812`

Suite: 725 passed and 0 failed before. 732 passed and 0 failed after.

A day with zero code-selected claims and no top phrase makes no model call. The voice gate
reads one predicate, `distill._has_voiceable_content`, which the withheld state also reads. The
four-condition no-post rule is frozen in config with all four names
(`force_finalized`, `anomalously_low_volume`, `zero_eligible_claims_both_parties`,
`red_instrument_status`). Assembly persists the three assemble-observable conditions on the day
record, computing the volume anomaly for the target day through one shared `ops.volume_anomaly`
definition. Posting evaluates the fourth condition (red instrument status) at post time, only
when the three already hold, fail-soft; when all four hold, both party threads are held
symmetrically and one neutral service note may post (build-dark, no dedicated account). The
dead-man treats this as an intended hold.

Acceptance: `tests/test_y4_null_service.py` (7 tests). A zero-claim day makes no model call
(`direct_call` raises if invoked) and records the deterministic generator with zero usage;
`ops.volume_anomaly` is one shared definition; `null_service_hold` requires all four
conditions; a normal day short-circuits the status query and never holds; a four-flag day holds
both parties and prepares exactly one neutral note (dark by default, no today); the real
committed 2026-07-25 record meets the assemble-side conditions.

Files:

- `pipeline/config.py`
- `pipeline/distill.py`
- `pipeline/ops.py`
- `pipeline/run_collect.py`
- `pipeline/run_assemble.py`
- `pipeline/post_bluesky.py`
- `pipeline/public_strings.py`
- `tests/test_y4_null_service.py`

### Y5. Status semantics (R-36.6)

Commit: `601e8d0`

Suite: 732 passed and 0 failed before. 739 passed and 0 failed after.

Severity precedence is absolute: `overall_status` is the worst any check reports over
critical, red, amber, green, neutral, unknown, so an open major correction plus a degraded
check yields red (the amber short-circuit is removed). Verifier drop publishes three calendar
windows (latest, seven calendar days, thirty calendar days), each as dropped over offered with
an unmeasured-day count; the window filters by parsed calendar day, not the last N manifest
files. The red gate fires when the seven-day rate breaches the SLO or materially exceeds the
thirty-day rate (a named multiple). The single freshness check splits into five labeled checks:
last successful source fetch, content watermark, expected-day completeness, publication lag,
endpoint health. `build_status` takes an injectable clock. Schema stays additive
(`verifier_drop_window` keeps its thirty-day meaning; `verifier_drop_windows` is new).

Acceptance: `tests/test_y5_status_semantics.py` (7 tests). Severity precedence is absolute over
all six levels; a 48.78 percent seven-day case is red while the thirty-day window alone is
green; windows are calendar-based, not manifests-available; unmeasured days are counted; an
open major plus a red check yields red (also flipped in test_x10); freshness splits into five
labeled checks and the transport check is renamed; the real committed manifests publish three
windows and render them.

Files:

- `pipeline/status_exports.py`
- `pipeline/site.py`
- `tests/test_w9_status_exports.py`
- `tests/test_x10_corrections_status.py`
- `tests/test_y5_status_semantics.py`

### Y6. Surge scope and ranking split (R-36.7)

Commit: `fba6d42`

Suite: 739 passed and 0 failed before. 743 passed and 0 failed after.

The surge baseline is computed per party inside the second party loop from each party's own
denominator history; the leaked `prior_days` from the first loop is removed. Rankings split
into `qualified_surges` (rows that passed the practical gate) and
`largest_statistical_deviations` (screening only); the `largest_surge` key is removed so no
surface calls a screening result a surge. No committed data or reference artifact carries a
rankings object, so nothing historical is rewritten. The method version moves to
`phrase-statistics-v3` and the rankings schema to 2; Y1's imported registry propagates the bump
to the fingerprint with no registry edit.

Acceptance: `tests/test_y6_surge_scope.py` (4 tests). Per-party baselines use each party's own
denominator history (D and R differ on a divergent-history fixture); qualified_surges exclude
gate-failing rows that appear in largest_statistical_deviations; no ranking key calls a
screening result a surge; the method version moved and the fingerprint inherits it.

Files:

- `pipeline/surges.py`
- `tests/test_w8_surges.py`
- `tests/test_y6_surge_scope.py`

### Y7. Export semantic completeness (R-36.7)

Commit: `3eba09d`

Suite: 743 passed and 0 failed before. 748 passed and 0 failed after.

The phrase CSV and the API phrase resources classify each row at emit time and carry
surface_class, surface_eligible, classification_rule, classifier_version, and family_count.
`_classified_phrase_row` re-derives the deterministic classification from the ngram, day, and
family_count rather than reading a field the rows never carried; it fails closed when a
nonprivate row has no class or classifier version. Because historical committed records cannot
be rewritten, the fields are populated at emit time in the CSV, the experimental phrases
resource, and the static exports. family_count stays best-effort (legacy rows lack it), so the
nonblank guard targets class and classifier version.

Acceptance: `tests/test_y7_export_completeness.py` (5 tests). The real committed 2026-06-30
record carries phrase rows with no surface_class, so the exporter derives it; every phrase CSV
row and every API phrase resource row carries a nonblank class and classifier version equal to
the live `eligibility.CLASSIFIER`; the classifier version in exports is the live authority; the
exporter fails closed on a blank nonprivate class.

Files:

- `pipeline/status_exports.py`
- `tests/test_x13_experimental_api.py`
- `tests/test_y7_export_completeness.py`

### Y8. Lane discipline (R-36.8)

Commit: `ac036a4`

Suite: 748 passed and 0 failed before. 753 passed and 0 failed after.

Remedy B (rename plus disclaimer) was chosen over remedy A (filter to message) because
message-only filtering would drop the flagship 2026-06-30 birthright-citizenship convergence,
which the blunt biographical and procedural regexes over-label; remedy B preserves recall under
an honest heading. The shared day-page heading, the party-column sub-headings, and the phrases
index rename from synchronized to "Repeated phrase observations" and carry a canonical
`public_strings.LEXICAL_TABLE_DISCLAIMER`. One rule across the homepage, the party columns, and
the day pages. The change is render-time only; no committed record is rewritten.

Acceptance: `tests/test_y8_lane_discipline.py` (5 tests). The classifier tags the fixture rows
biographical and nomenclature; the day table heading is disclaimed in both the party-columns
and sync_table paths; a biographical and a procedural row still render under the disclaimed
heading and the old synchronized sub-heading is gone; a nomenclature row renders disclaimed;
the phrases index disclaims its repeated-phrase table.

Files:

- `pipeline/public_strings.py`
- `pipeline/site.py`
- `tests/test_y8_lane_discipline.py`

### Y9. Registry-versus-authority invariants (R-36.1)

Commit: `1d5e7d3`

Suite: 753 passed and 0 failed before. 763 passed and 0 failed after.

The enforcement package for the failure shape all three rounds share. Y1 already made the
fingerprint import method and schema versions from owning modules; Y9 adds the invariants and
the mutation harness that keep every central registry bound to its live owner.
`status_exports.ENVELOPE_SCHEMA_VERSION` becomes the owner for the published_artifact schema, so
no registry-local literal remains. `tests/registry_mutations.py` mirrors the verifier harness:
for each of the 15 invariants (nine method versions, three schema versions, api_version,
canary_version, entity_hierarchy_version) it bumps the owner and asserts the registry follows,
proving a live read rather than a stale copy. `scripts/run_registry_mutations.py` reports each
load-bearing.

Acceptance: `tests/test_y9_registry_authority.py` (10 tests). Every method and schema version
entry matches its live owner and every entry has an owning authority; a one-line bump of any
live authority moves the fingerprint with no registry edit; feature flags have no second copy;
public strings are read live by renderers; a resolved posting state is a member of the posting
registry; the API field emitters match the documented contract; the correction checkpoint binds
to the ledger; the mutation harness reports every one of the 15 invariants load-bearing.
Threshold readers are covered by the existing test_x1 parameter-mutation matrix.

Files:

- `pipeline/instrument_fingerprint.py`
- `pipeline/status_exports.py`
- `tests/registry_mutations.py`
- `tests/test_y9_registry_authority.py`
- `scripts/run_registry_mutations.py`

### Y10. Classifier floor hardening (R-36.7)

Commit: `99d5074`

Suite: 763 passed and 0 failed before. 771 passed and 0 failed after.

`classify_phrase` gains a `require_family_evidence` path: on a public surface a phrase with no
family evidence classifies unknown (family-evidence-absent) instead of falling through to the
message floor, and the distinct-statement fallback in `_family_count` survives only for legacy
fixtures. The capability is dark by default, so the deterministic floor and every production
surface are byte-identical. The generic survivors are a committed fixture set
(`evaluation/goldset/generic_survivors.json`) documenting current message-floor behavior for
the gold set to adjudicate, not a hand-tuned blocklist; the classifier never reads the fixture.
They are registered for public-surface oversampling (`goldset_sample.survivor_phrases`, unioned
into the seal build's public set) so the next seal draws them into the pilot.

Acceptance: `tests/test_y10_classifier_floor.py` (8 tests). Family-evidence-absent public claims
classify unknown; the message floor is unchanged by default; the statement-count fallback
survives only for legacy fixtures; classify_claim strict drops a statements-only claim; the
fixture documents current behavior and is not a blocklist the classifier reads; the survivors
are registered for public-surface sampling and a public-tagged survivor is drawn into the pilot.

Files:

- `pipeline/eligibility.py`
- `pipeline/goldset_sample.py`
- `scripts/goldset_seal.py`
- `evaluation/goldset/generic_survivors.json`
- `tests/test_y10_classifier_floor.py`

## Variances and deviations

1. Y1 renames the fingerprint code component from `code_commit` to `code_tree`, because the
   value became a measurement-tree content hash and is no longer a commit; naming a content
   hash a commit would violate Article XVII. `test_x1` was updated for the renamed component in
   the same commit. The fingerprint sha256 changes as a result, which is the disclosed subject
   of the Y1 correction.

2. Y1 corrects two schema and method version drifts beyond the two the review named: the
   corrections schema was stale at 2 while the owning module was 3, and the denominators method
   version was absent from the registry. Both are now imported from their owners.

3. Y1 appends one correction record to `data/reference/corrections.json` and bumps
   `data/reference/corrections-count.json`. This is the ruled exception to leaving data
   untouched. The five existing records are preserved byte for byte (the record was spliced
   before the closing bracket, not rewritten). `test_w3_publication` count and affected-day
   assertions were updated for the new record.

4. Y5 flips `test_x10::test_open_major_correction_turns_status_amber` to red and renames it,
   and updates the `test_w9` check-id set for the five-way freshness split. Both are the direct
   consequence of the ruled behavior change and land in the same commit.

5. Y6 removes the `largest_surge` ranking key, which is not additive, but is mandated by R-36.7
   ("no surface calls a screening result a surge"). No committed `data/derived` or
   `data/reference` artifact carries a rankings object (`build_rankings` is script and evidence
   only), so no historical record is rewritten. Y6 also bumps `surges.METHOD_VERSION` to v3 and
   the rankings schema to 2 because the numbers on divergent-history days and the output shape
   both change; the bump propagates to the fingerprint automatically through Y1's imported
   registry.

6. Y9 gives the `published_artifact` schema entry an owning authority
   (`status_exports.ENVELOPE_SCHEMA_VERSION`) so every registry entry is tested against an
   owner. The emitted value is unchanged (1), so the fingerprint does not move.

7. Y10 deliberately does not bump `eligibility.CLASSIFIER` and does not wire
   `require_family_evidence=True` into any production caller. Production talking points carry no
   real family evidence (the current families count is derived from member_count), so enforcing
   the strict rule now would silence every daily line. The ruling delegates the message-versus-
   unknown decision to the gold set, so the capability ships dark, production is byte-identical,
   and the classifier version stays v3. This matches the project's dark-until-validated pattern
   (R-33.2, R-29.2).

## Incomplete items and blockers

The Y10 acceptance also asks that the survivor fixture set be sampled into the pilot annotation
queue. The survivors are registered for public-surface oversampling and a test proves a
public-tagged survivor is drawn into a sealed pilot, but the committed pilot
(`evaluation/goldset/pilot.sample.json`) is not regenerated in this delivery. Regenerating it
runs `scripts/goldset_seal.py build`, which reads the multi-GB `data/state/ledger.json` (a run
over ten minutes, which docs/37 rule 10 requires to be harness-detached) and regenerates the
frozen sealed kit, changing `seal_hash` and `MANIFEST.json`. That kit is the just-sealed
deliverable the human annotation study runs on (docs/36 section 3), so re-sealing it is a
governance-sensitive operator act, not a Y-session side effect. The re-seal is deferred to the
annotation-study owner. After the re-seal the survivors will appear in the pilot because they
are now in the public-surface set (proven by `test_a_public_tagged_survivor_is_drawn_into_the_pilot`).

No other item is incomplete. No package was blocked.

## Repository state

The branch starts at exact base `ecdb041ed530b853b5622006d6b39e7ab719d4fe`. HEAD is
`99d507410413e33255a77f25699e8db70505d49f`. `AGENTS.md` and the pre-existing
`tests/_tmp_watchdog/` directory remain untracked. No `site/public` or `data/derived` artifact
was regenerated. No push, deploy, workflow dispatch, post, or gate or feature mutation
occurred.
