# X work-order delivery packet

Branch: `codex/x-packages`

Base: `085184e38c09d3d6166159633fffd1e911f84eb1`

Validation command for every package:

```text
C:\ProgramData\miniconda3\python.exe tests\run_tests.py
```

The baseline was 572 passed and 0 failed. The final package result was 647 passed and 0 failed. No push, deployment, workflow dispatch, post, live API call, `POSTING_ENABLED` change, or existing `FEATURES` value change occurred.

## Package record

### X1. Instrument fingerprint

Commit: `6ce618cb9c11410a65e1b8c6d061f9c159e0ca61`

Suite: 572 passed and 0 failed before. 577 passed and 0 failed after.

Acceptance: `tests/test_x1_instrument_fingerprint.py` exhaustively mutates the registered live parameters and compares two clean builds at one commit. It also uses the committed 2026-07-24 day artifact. At X1, 24 of 24 registered live thresholds moved the authoritative hash. The estimator was exhaustive parameter mutation. The unit was a parameter. The window was the X1 `instrument-v1` registry. The denominator was all 24 registered parameters. Two of two clean builds agreed.

Files:

- `pipeline/announce.py`
- `pipeline/corrections.py`
- `pipeline/deterministic.py`
- `pipeline/instrument_fingerprint.py`
- `pipeline/ops.py`
- `pipeline/post_bluesky.py`
- `pipeline/run_assemble.py`
- `pipeline/status_exports.py`
- `tests/test_x1_instrument_fingerprint.py`

### X2. Surge correction

Commit: `fb043852fe14df882f23163e9f1491f4eba35220`

Suite: 577 passed and 0 failed before. 582 passed and 0 failed after.

Acceptance: `tests/test_x2_surge_correction.py` proves the two-of-28-day risk set, the superseded selection difference, complete disclosure, deterministic ranking, weekday mode, and calibration output. The fixture measured 4 prior successes over 2,800 office-trials across 28 eligible days. The superseded selector used 4 successes over 200 office-trials across 2 occurrence days. The estimator was an exact sum from the denominator series. The units were office-trials and calendar days. The window was the 28 days before 2026-07-24. The denominator was all 28 eligible days.

Files:

- `pipeline/config.py`
- `pipeline/instrument_fingerprint.py`
- `pipeline/surges.py`
- `scripts/calibrate_surges.py`
- `tests/test_x2_surge_correction.py`

### X3. Index removal and participation measures

Commit: `f4d23c7caff9345f10f81c09225472f8867c769d`

Suite: 582 passed and 0 failed before. 585 passed and 0 failed after.

Acceptance: `tests/test_x3_participation.py` proves that no public surface renders the old index and that all three replacements name both units, the party-day window, and the method. Three of three measures preserved one unit. The estimator was exact distinct-ID set intersection. The units were offices, publications, and document families. The window was Democratic party-day 2026-07-24. The denominators were 5 offices, 5 publications, and 4 families.

Files:

- `pipeline/instrument_fingerprint.py`
- `pipeline/participation.py`
- `pipeline/run_assemble.py`
- `pipeline/site.py`
- `tests/test_x3_participation.py`

### X4. Fail-closed classification

Commit: `6c77b2f2d62e9e74e5005f403a6da60a5f95877e`

Suite: 585 passed and 0 failed before. 590 passed and 0 failed after.

Acceptance: `tests/test_x4_fail_closed.py` reclassifies all four named committed 2026-07-24 phrases away from message, proves the three-family floor, produces the meaningful null, excludes unknowns from public surfaces, and retains them in concordance and exports.

Files:

- `pipeline/build.py`
- `pipeline/distill.py`
- `pipeline/duet.py`
- `pipeline/eligibility.py`
- `pipeline/instrument_fingerprint.py`
- `pipeline/phrases.py`
- `pipeline/post_bluesky.py`
- `pipeline/run_assemble.py`
- `pipeline/site.py`
- `pipeline/status_exports.py`
- `tests/test_x4_fail_closed.py`

### X5. Composite discipline

Commit: `ddd3d6ed22116d2bfe2075a26f4a0df1a27ce54e`

Suite: 590 passed and 0 failed before. 595 passed and 0 failed after.

Acceptance: `tests/test_x5_composite_discipline.py` proves a neutral lead and explicit state on committed day panels and threads, structured request and response hashes, meaningful null states, and verifier rejection for every banned style token. The live prompt pins remain P2 v1.3 and P3 v1.1. The new prompts remain dark.

Files:

- `pipeline/distill.py`
- `pipeline/instrument_fingerprint.py`
- `pipeline/post_bluesky.py`
- `pipeline/prompts/P2_daily_line.v1.4.txt`
- `pipeline/prompts/P3_quiet_day.v1.2.txt`
- `pipeline/site.py`
- `pipeline/verify.py`
- `tests/test_x5_composite_discipline.py`

### X6. Shadow replay harness

Commit: `2854749374434ab1cfc6adf6a7e916d391a613fd`

Suite: 595 passed and 0 failed before. 601 passed and 0 failed after.

Acceptance command:

```text
C:\ProgramData\miniconda3\python.exe scripts\shadow_replay.py --days-dir data\derived\days
```

The dry report processed 15 complete days from 16 committed day files and 30 party-days. The estimator counted files with non-empty Democratic and Republican composites. The units were complete days and party-days. The window was 2026-06-30 through 2026-07-24. The denominators were 16 committed files and 30 offered party-days. The dry fallback rate was 0 of 30, or 0.0. The live gate remained closed because the minimums are 60 complete days and 200 party-days. Live calls require both `--live` and `--allow-api-spend`.

Files:

- `pipeline/config.py`
- `pipeline/instrument_fingerprint.py`
- `pipeline/shadow_replay.py`
- `scripts/shadow_replay.py`
- `tests/test_x6_shadow_replay.py`

### X7. Migration and drill evidence

Commit: `40d64c9e732c33938155306db7f03c7ca2ff8a71`

Suite: 601 passed and 0 failed before. 608 passed and 0 failed after the timestamp repair.

Migration acceptance command:

```text
C:\ProgramData\miniconda3\python.exe -m pipeline.migration_evidence --check data\reference\x7-migration-manifest.json
```

Clean-clone drill command after downloading the rolling assets and sidecars into `release-assets`:

```text
C:\ProgramData\miniconda3\python.exe scripts\quarterly_restore_drill.py release-assets --report x7-drill-report.json
```

The recorded production cycle was 2026-07-24. Three of three required stages passed. The post evidence recorded 2 of 2 party lanes posted and 7 posts written. The estimator was the three-stage manifest gate over one production day. The unit was a stage. The denominator was all 3 required stages.

The repaired clean-clone drill passed. It verified both asset sidecars, restored 25 files, and reported byte identity. Both rebuild hashes were `2328858400cb6f5609c17a91dc0433833e9ae057467e8b363477ec0365d95026`. The estimator was SHA-256 over each relative deterministic derived JSON path and its bytes. The raw asset contained 94,188,780 bytes with SHA-256 `d6f0a966b48e2939b214a45a6de192b7547370ecfc108a938aa2bd1df2323df6`. The state asset contained 135,607,565 bytes with SHA-256 `0cd058de5241495cd52ac309272729030d7de34494652bc6b482d71760b28429`. The denominator was every byte in both verified assets.

Completed drill report:

```json
{"assets":{"raw.tar.gz":{"bytes":94188780,"sha256":"d6f0a966b48e2939b214a45a6de192b7547370ecfc108a938aa2bd1df2323df6","sidecar_verified":true},"state.tar.gz":{"bytes":135607565,"sha256":"0cd058de5241495cd52ac309272729030d7de34494652bc6b482d71760b28429","sidecar_verified":true}},"checkout_commit":"5fbfcee464342432dc1902c52844e256c3a160ea","clean_clone_verified":true,"generated_at":"2026-07-27T08:17:03Z","passed":true,"quarter":"2026-Q3","rebuild":{"byte_identical":true,"estimator":"SHA-256 over relative path and bytes for deterministic derived JSON","first_sha256":"2328858400cb6f5609c17a91dc0433833e9ae057467e8b363477ec0365d95026","second_sha256":"2328858400cb6f5609c17a91dc0433833e9ae057467e8b363477ec0365d95026"},"report_kind":"quarterly_restore_drill","restore":{"files_restored":25,"repository_authority_notices":[]},"schema_version":1}
```

The report checkout SHA is the pre-message-normalization X7 commit. Final X7 retains that drill implementation and result. It also makes canonical migration evidence follow the checkout platform's newline convention so clean Windows CRLF and Linux LF checkouts validate the same committed evidence.

Files:

- `data/reference/x7-migration-manifest.json`
- `pipeline/build.py`
- `pipeline/deterministic.py`
- `pipeline/migration_evidence.py`
- `pipeline/rebuild.py`
- `pipeline/restore_drill.py`
- `scripts/quarterly_restore_drill.py`
- `tests/test_x7_migration_drill.py`

### X8. Date-effective denominators and source coverage

Commit: `fee5ca75a5080b9e56a2de333d50ce547752a837`

Suite: 608 passed and 0 failed before. 613 passed and 0 failed after.

Acceptance: `tests/test_x8_denominators.py` spans a vacancy gap and a party switch. It also proves that corpus presence alone cannot create source support. The committed census contains 1,565 offices and 6,869 service intervals overlapping 2001 onward. The estimator was a direct deterministic count. The units were offices and intervals. The window was terms overlapping 2001-01-01 onward. The denominator was every record in both pinned CC0 source files at revision `4458244308621d0570a15008f46888b7a87645eb`.

Files:

- `data/reference/date-effective-roster.json`
- `data/reference/office-source-coverage.json`
- `pipeline/build.py`
- `pipeline/denominators.py`
- `pipeline/ops.py`
- `pipeline/site.py`
- `tests/test_x8_denominators.py`

### X9. Family hardening

Commit: `a31896ac97a1aca1f716694c284031ddfd0c1957`

Suite: 613 passed and 0 failed before. 618 passed and 0 failed after.

Acceptance: `tests/test_x9_family_hardening.py` proves stable identity after a late arrival, revision chaining, the bounded 36-hour window, diagnostics, and unit wording. The recall harness retrieved 6 of 6 exhaustive positive pairs, or 1.000, against the 0.995 target. The estimator was exhaustive exact Jaccard comparison. The unit was a positive document pair. The window was 36 hours over 5 bounded fixture documents. The denominator was all 6 exact-positive pairs.

Files:

- `pipeline/config.py`
- `pipeline/contracts.py`
- `pipeline/document_families.py`
- `pipeline/instrument_fingerprint.py`
- `pipeline/run_assemble.py`
- `pipeline/site.py`
- `tests/test_x9_family_hardening.py`

### X10. Corrections and status

Commit: `e560167553f2c2053542cd307af214b0fd124e58`

Suite: 618 passed and 0 failed before. 624 passed and 0 failed after.

Acceptance: `tests/test_x10_corrections_status.py` proves that an open major correction turns status amber, a degraded publication preserves the publication streak while resetting the clean-run streak, and disabled posting renders neutral. It reads the committed correction ledger and manifests. The verifier fixture measured 2 dropped claims over 16 offered claims, or 0.125. The estimator was direct manifest-field aggregation. The unit was a claim. The window was 2 observed days inside the declared trailing 30-day window. The denominator was all 16 offered claims across both parties.

Files:

- `pipeline/corrections.py`
- `pipeline/site.py`
- `pipeline/status_exports.py`
- `tests/test_x10_corrections_status.py`

### X11. Provenance pinning

Commit: `bbf7f072e8e3f17aed029b721b85db3973d6aaec`

Suite: 624 passed and 0 failed before. 629 passed and 0 failed after.

Acceptance: `tests/test_x11_provenance_pinning.py` proves exact upstream commit, content hash, ETag, collection time, timezone data fingerprint, locale, both 2026 DST transition days, the SPDX SBOM, and pinned native attestation steps. The real committed July 2026 raw shard measured 3,160,685 bytes and SHA-256 `e3664c64344d6c57beb3584f762ae5510dfc598242d6a1cfba3a52467f7896b7`. The estimator was bytewise SHA-256. The unit was a byte. The window was the committed July 2026 shard. The denominator was every byte in that shard.

Files:

- `.github/workflows/assemble.yml`
- `.github/workflows/collect.yml`
- `pipeline/fetch.py`
- `pipeline/run_collect.py`
- `pipeline/runtime_environment.py`
- `pipeline/site.py`
- `pipeline/util.py`
- `sbom.spdx.json`
- `tests/test_x11_provenance_pinning.py`

### X12. Privacy battery and canaries

Commit: `a5bf91b7c79fffaa8252949e1d721c22655b0f02`

Suite: 629 passed and 0 failed before. 634 passed and 0 failed after.

Acceptance: `tests/test_x12_privacy_canary.py` runs the name-shape battery and a seeded dry-run publication failure. Nine of nine name-shape fixtures entered the typed unresolved-person quarantine. The estimator was deterministic span classification. The unit was a name-shape case. The window was the committed X12 battery. The denominator was all 9 cases. Canary telemetry recorded 4 of 4 checks passed and 0 occurrence-level records.

Files:

- `.github/workflows/assemble.yml`
- `.github/workflows/post.yml`
- `pipeline/privacy.py`
- `pipeline/privacy_canary.py`
- `tests/test_x12_privacy_canary.py`

### X13. Experimental API and exports

Commit: `d07b1e5e41e9d048b5ceda83cab45ff559b5f557`

Suite: 634 passed and 0 failed before. 639 passed and 0 failed after.

Acceptance: `tests/test_x13_experimental_api.py` recomputes every payload hash and compares the documented field list with the emitted fields. Six of six JSON resource envelopes self-verified. Three of three normalized CSV resources carried exact headers. The estimator was deterministic enumeration and SHA-256 recomputation. The unit was a resource file. The window was one fixture day. The denominators were all 6 JSON resources and all 3 CSV resources.

Files:

- `pipeline/site.py`
- `pipeline/status_exports.py`
- `tests/test_x13_experimental_api.py`

### X14. Deterministic context guards

Commit: `99407706fbbeaa7ea080e16d5ae2c5709499436e`

Suite: 639 passed and 0 failed before. 643 passed and 0 failed after.

Acceptance: `tests/test_x14_context_guards.py` proves that `this is not a stock trading ban` cannot join affirmative support as a message claim. It also proves sentence and clause coordinates, adjacent tokens, quote attribution, affirmative eligibility, and attribution-only rejection. Three phrase occurrences across 3 publications and 3 families produced 2 stance classes and 1 mixed-stance rejection. The estimator was deterministic token-window context classification. The unit was a phrase occurrence. The window was one fixture party-day. The denominator was all 3 supporting occurrences.

Files:

- `pipeline/contracts.py`
- `pipeline/eligibility.py`
- `tests/test_x14_context_guards.py`

### X15. Homepage lanes and beta string

Commit: `d3b4e0097e70d200da0cc39c35916b4f1f0665eb`

Suite: 643 passed and 0 failed before. 647 passed and 0 failed after.

Acceptance: `tests/test_x15_homepage_lanes.py` proves that all four lanes come from the classification layer, that both composites precede the lanes, that the corrections link renders, and that the centralized beta string is dark by default. Four of four lanes rendered from 4 classified rows. The estimator was deterministic classifier-to-lane mapping. The units were lanes and rows. The window was one fixture homepage day. The denominator was all 4 specified lanes and all 4 fixture rows. The beta string rendered in 1 of 2 tested flag states, only the enabled state.

Files:

- `pipeline/public_strings.py`
- `pipeline/site.py`
- `tests/test_x15_homepage_lanes.py`

## Variances and deviations

1. The work-order authority directed X7 acceptance to complete asynchronously while X8 through X15 continued. The completed report passed. This was an explicit variance supplied during execution.
2. The first X7 drill found nondeterministic `generated_at` bytes in `awards.json` and `concordance.json`. X7 now samples one real rebuild-start timestamp and uses it for both comparison passes. Normal production timestamp behavior is unchanged. This repair was accepted in principle by the work-order authority.
3. X8 retains the old flat `eligible_caucus_offices` corpus-proxy field for one compatibility cycle because existing keys cannot change meaning. New `date_effective_eligible_caucus_offices` and `date_effective_denominators` fields carry the ruled measurement. Public surfaces use the date-effective field.
4. X10 accepts existing schema-version 2 correction records and requires all lifecycle fields on new schema-version 3 records. Existing public correction records were not silently rewritten.
5. X13 retains the existing W9 static export files and adds the experimental resource endpoints beside them. This preserves current consumers while adding the ruled contract.
6. An external workspace process rebased the branch onto three unrelated production-data commits during X1 through X6. The altered history was preserved as `codex/x-packages-external-rebase`. The working branch was reconstructed from exact base `085184e38c09d3d6166159633fffd1e911f84eb1` by replaying only the package commits. The final merge base and local `main` both equal the required base.
7. X7 through X15 commit metadata was rewritten to place the completed X7 drill evidence in the X7 commit body. That message-only rewrite was tree-identical. A later X7 repair made canonical migration evidence use the checkout platform's newline convention after a clean Windows checkout exposed an LF versus CRLF mismatch. The branch was then validated again at 647 passed and 0 failed. The preserved pre-reword branch is `codex/x-packages-pre-x7-reword`.

No other deviation from docs/33 is known.

## Incomplete items and blockers

None.

The X6 live shadow replay remains intentionally unrun. It requires real API spend and Michael's authorization. The dark prompt pins remain unchanged.

## Repository state

The required branch starts at exact base `085184e38c09d3d6166159633fffd1e911f84eb1`. `AGENTS.md` remains untracked. The pre-existing `tests/_tmp_watchdog/` directory remains untracked. No generated `site/public` or `data/derived` artifact was regenerated as an implementation side effect.
