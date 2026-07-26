# OnScript W1 through W11 delivery packet

## Delivery state

- Repository: `github.com/mlawsonking/onscript`
- Working branch: `codex/w-packages`
- Required base: `f99a507`
- Baseline validation: 511 passed, 0 failed
- Final package validation: 572 passed, 0 failed
- Test runner: `C:\ProgramData\miniconda3\python.exe tests/run_tests.py`
- Pushes, deployments, workflow dispatches, posts, feature changes, and `POSTING_ENABLED` changes: none
- Generated `site/public` or `data/derived` changes: none
- Untracked operator files excluded from every commit: `AGENTS.md`, `tests/_tmp_watchdog/`

## Suite progression

| Package | Before | After | Commit |
|---|---:|---:|---|
| W1 | 511 passed, 0 failed | 516 passed, 0 failed | `5629b5c11a2add9a00f47252794186a6a63c1c11` |
| W2 | 516 passed, 0 failed | 520 passed, 0 failed | `2cf17eb48c6f7f06535621345e43e172605cb938` |
| W3 | 520 passed, 0 failed | 528 passed, 0 failed | `a647466c752c4a21f8574357dfac998147b5b217` |
| W4 | 528 passed, 0 failed | 532 passed, 0 failed | `de0bfc095d0c4538c802e0671879c96f0c6696b0` |
| W5 | 532 passed, 0 failed | 536 passed, 0 failed | `86b5254b7ddf601cb8f8157dbcd90cf958ed6e94` |
| W6 | 536 passed, 0 failed | 544 passed, 0 failed | `7663778818595f35b9a92defa729de8b650acf05` |
| W7 | 544 passed, 0 failed | 548 passed, 0 failed | `3366b6642ba8da34382c178dd2049e9e2687a2cc` |
| W8 | 548 passed, 0 failed | 554 passed, 0 failed | `219ac318d1945048ebd820877456b421cec2fedb` |
| W9 | 554 passed, 0 failed | 559 passed, 0 failed | `72f469643762dfefdf2433ca0b9c7a1bc492d106` |
| W10 | 559 passed, 0 failed | 565 passed, 0 failed | `2d5a7ad5e75ae0af8d5bb0248305ce9ef48c047e` |
| W11 | 565 passed, 0 failed | 572 passed, 0 failed | `0132be0a3e92b8076303d697daf83484476d41be` |

## W1. Terminology, denominators, and labels

Commit: `5629b5c11a2add9a00f47252794186a6a63c1c11`

Acceptance command:

```powershell
& 'C:\ProgramData\miniconda3\python.exe' -c "from tests import test_w1_public_language as t; [getattr(t,n)() for n in sorted(dir(t)) if n.startswith('test_')]; print('PASS')"
```

Evidence: canonical public promises come from `pipeline/public_strings.py`. The term ladder renders.
Observed publishing offices, eligible caucus offices, and source collection health are separate.
The legacy coverage field remains with a deprecation note.

Files:

- `pipeline/ops.py`
- `pipeline/post_bluesky.py`
- `pipeline/public_strings.py`
- `pipeline/site.py`
- `tests/test_w1_public_language.py`

## W2. Occurrence and claim contract

Commit: `2cf17eb48c6f7f06535621345e43e172605cb938`

Acceptance command:

```powershell
& 'C:\ProgramData\miniconda3\python.exe' -c "from tests.test_w2_claim_contract import test_each_of_six_claim_invariants_fails_closed_when_broken as t; t(); print('PASS')"
```

Evidence: all six isolated invariant mutations fail closed. Typed claims carry source offsets and
separate office, publication, and family counts. The docs/28 tests pass without modification.

Files:

- `pipeline/contracts.py`
- `pipeline/distill.py`
- `pipeline/run_assemble.py`
- `pipeline/site.py`
- `pipeline/verify.py`
- `tests/test_w2_claim_contract.py`

## W3. Publication immutability and corrections

Commit: `a647466c752c4a21f8574357dfac998147b5b217`

Acceptance command:

```powershell
& 'C:\ProgramData\miniconda3\python.exe' -c "from tests.test_w3_publication import test_stale_archive_conflict_fails_before_any_checkout_write as a, test_correction_count_checkpoint_rejects_a_removed_entry as b; a(); b(); print('PASS')"
```

Evidence: a stale tracked reference file blocks restore before any checkout write. The correction
ledger count cannot decrease without failing validation.

Files:

- `.github/workflows/assemble.yml`
- `.github/workflows/collect.yml`
- `.gitignore`
- `data/reference/corrections-count.json`
- `data/reference/corrections.json`
- `pipeline/archive_restore.py`
- `pipeline/corrections.py`
- `pipeline/run_assemble.py`
- `pipeline/site.py`
- `tests/test_w3_publication.py`

## W4. Span privacy

Commit: `de0bfc095d0c4538c802e0671879c96f0c6696b0`

Acceptance command:

```powershell
& 'C:\ProgramData\miniconda3\python.exe' -c "from tests.test_w4_span_privacy import test_both_historical_escape_shapes_require_span_suppression as a, test_every_ngram_occurrence_overlapping_a_synthetic_private_span_is_suppressed as b; a(); b(); print('PASS')"
```

Evidence: both historical escape shapes are blocked. Every synthetic n-gram occurrence that
intersects a private span is suppressed before phrase generation.

Files:

- `pipeline/build.py`
- `pipeline/nomenclature_build.py`
- `pipeline/phrases.py`
- `pipeline/privacy.py`
- `tests/test_w4_span_privacy.py`

## W5. Adversarial fixtures and mutation checks

Commit: `86b5254b7ddf601cb8f8157dbcd90cf958ed6e94`

Acceptance command:

```powershell
& 'C:\ProgramData\miniconda3\python.exe' scripts/run_verifier_mutations.py
```

Evidence: the command reports 15 of 15 verifier checks as load-bearing. Estimator: exact registry
enumeration. Unit: verifier checks. Window: the W5 production registry. Denominator: all 15 checks.

Files:

- `pipeline/verify.py`
- `scripts/run_verifier_mutations.py`
- `tests/test_w5_adversarial.py`
- `tests/verifier_mutations.py`

## W6. Phrase classification and rendering discipline

Commit: `7663778818595f35b9a92defa729de8b650acf05`

Acceptance command:

```powershell
& 'C:\ProgramData\miniconda3\python.exe' -c "from tests.test_w6_eligibility import test_top_raw_procedural_phrase_yields_a_line_led_by_the_top_message as a, test_nomenclature_is_segregated_while_the_legacy_chip_flag_is_off as b; a(); b(); print('PASS')"
```

Evidence: a procedural phrase supported by 40 offices is excluded while a message phrase supported
by 12 offices leads. Nomenclature is segregated even when the superseded chip flag is off. At most
two topic-diverse message claims render. Prompt candidates P2 v1.4 and P3 v1.2 remain inactive.

Measured fixture: 40 procedural offices and 12 message offices. Estimator: deterministic fixture
enumeration. Unit: distinct offices. Window: one 2026-07-24 party-day. Denominator: every fixture
office in the two candidate counts.

Files:

- `pipeline/contracts.py`
- `pipeline/distill.py`
- `pipeline/eligibility.py`
- `pipeline/post_bluesky.py`
- `pipeline/privacy.py`
- `pipeline/prompts/P2_daily_line.v1.4.txt`
- `pipeline/prompts/P3_quiet_day.v1.2.txt`
- `pipeline/prompts/README.md`
- `pipeline/run_assemble.py`
- `pipeline/site.py`
- `pipeline/verify.py`
- `tests/test_nomenclature_wiring.py`
- `tests/test_session8.py`
- `tests/test_w6_eligibility.py`
- `tests/test_wave0.py`

## W7. Document families

Commit: `3366b6642ba8da34382c178dd2049e9e2687a2cc`

Acceptance command:

```powershell
& 'C:\ProgramData\miniconda3\python.exe' -c "from tests import test_w7_document_families as t; t.test_one_joint_release_many_offices_is_one_family(); t.test_near_duplicates_with_local_edits_cluster(); t.test_similarity_chain_does_not_form_one_transitive_family(); print('PASS')"
```

Evidence: one joint release from five offices reports one family. Local edits cluster. An A-B-C
similarity chain does not become one unrestricted component. MinHash retrieves candidates. Exact
Jaccard decides membership. A valid medoid anchors each family.

Measured fixture: 5 publications from 5 offices form 1 family. Estimator: distinct-ID enumeration
after normalization. Unit: publications, offices, and families. Window: one 2026-07-24 party-day.
Denominator: all 5 fixture publications.

Files:

- `pipeline/config.py`
- `pipeline/contracts.py`
- `pipeline/document_families.py`
- `pipeline/normalize.py`
- `tests/test_w7_document_families.py`

## W8. Surge statistics and first-observed honesty

Commit: `219ac318d1945048ebd820877456b421cec2fedb`

Acceptance commands:

```powershell
$a = & 'C:\ProgramData\miniconda3\python.exe' scripts/rank_surges.py tests/fixtures/w8_rankings.json
$b = & 'C:\ProgramData\miniconda3\python.exe' scripts/rank_surges.py tests/fixtures/w8_rankings.json
if (-not ($a -ceq $b)) { throw 'ranking output drifted' }
$a
```

Evidence: outputs are byte-identical. `largest_surge` ranks `true surge phrase` above the stable
high-frequency phrase. First-observed records disclose lane, corpus start, precision, and ties. A
day-precision tie carries no originator attribution. Five rankings remain separate.

Measured fixture: 25 of 100 offices against baseline share 0.02119701 gives
`p=7.44176900059556e-20` and `q=2.976707600238224e-19`. Estimator: exact binomial upper tail with
Jeffreys smoothing and Benjamini-Hochberg adjustment. Unit: distinct offices. Window: 2026-07-24
against 4 available prior days in the 28-day window. Denominator: 100 eligible offices per day.

Files:

- `docs/30-SURGE-REPRODUCTION.md`
- `pipeline/phrases.py`
- `pipeline/site.py`
- `pipeline/surges.py`
- `scripts/rank_surges.py`
- `tests/fixtures/w8_rankings.json`
- `tests/test_w8_surges.py`

## W9. Status, exports, and feeds

Commit: `72f469643762dfefdf2433ca0b9c7a1bc492d106`

Acceptance command:

```powershell
& 'C:\ProgramData\miniconda3\python.exe' -c "from tests import test_w9_status_exports as t; t.test_every_status_number_names_manifest_fields(); t.test_unavailable_input_is_unknown_and_never_green(); t.test_api_checksums_reproduce_and_csv_is_present(); t.test_watchlist_filter_is_party_symmetric_and_excludes_procedure(); print('PASS')"
```

Evidence: all nine operational checks name manifest fields. Missing input is unknown. API envelope
checksums reproduce. The CSV and bulk snapshots are present. Watchlist filtering is party-symmetric
and uses W6 alert eligibility.

Measured fixture: 9 checks, 5 API or CSV artifacts, 1 eligible alert per party, and 0 procedural
alerts. Estimator: deterministic fixture enumeration. Unit: checks, artifacts, and Atom entries.
Window: one 2026-07-25 party-day. Denominator: 9 checks, 5 expected artifacts, and 4 phrase rows.

Files:

- `pipeline/run_assemble.py`
- `pipeline/site.py`
- `pipeline/status_exports.py`
- `pipeline/watchlists.json`
- `tests/test_w9_status_exports.py`

## W10. Gold-set harness

Commit: `2d5a7ad5e75ae0af8d5bb0248305ce9ef48c047e`

Acceptance command:

```powershell
& 'C:\ProgramData\miniconda3\python.exe' scripts/goldset.py metrics tests/fixtures/w10_synthetic_annotations.json
```

Evidence: the synthetic sample runs through date splits, dual annotation, explicit adjudication,
and the complete metric set. No corpus annotation was performed.

Measured synthetic fixture: 6 of 6 candidates resolve. Family pairs contain 1 true positive,
2 false positives, and 1 false negative. Precision is 0.333333. Recall is 0.5. Estimator:
exhaustive pair enumeration within party-day scopes. Unit: candidate pairs. Window: synthetic dates
2026-03-01 through 2026-07-01. Denominator: all comparable pairs in each fixture party-day group.

Files:

- `docs/31-GOLD-SET-HARNESS.md`
- `evaluation/ANNOTATION-GUIDE.md`
- `evaluation/annotation.schema.json`
- `pipeline/goldset.py`
- `scripts/goldset.py`
- `tests/fixtures/w10_synthetic_annotations.json`
- `tests/test_w10_goldset.py`

## W11. Hardening and provenance

Commit: `0132be0a3e92b8076303d697daf83484476d41be`

Acceptance commands:

```powershell
& 'C:\ProgramData\miniconda3\python.exe' -c "from tests.test_w11_hardening import test_traversal_archive_is_rejected_before_checkout_write as t; t(); print('PASS')"
& 'C:\ProgramData\miniconda3\python.exe' scripts/reproduce_subset.py
```

Evidence: parent traversal is rejected before checkout writes. All non-local Action references use
full commit SHAs. Release assets receive SHA-256 sidecars. RUN C owns posting credentials and posting
side effects after RUN B succeeds. The clean-clone subset is byte-identical across two runs.

Measured workflow tree: 10 of 10 third-party Action references across 5 workflows use 40-character
commit SHAs. Estimator: exhaustive scan of every `uses` field. Unit: Action references. Window: the
W11 workflow tree. Denominator: all 10 non-local references. The subset hash is
`35a30ea7b2055e787b33225c9063a45fe22ae0427417744e7790a78f485dfbf7` on both runs.

Files:

- `.github/workflows/announce.yml`
- `.github/workflows/assemble.yml`
- `.github/workflows/collect.yml`
- `.github/workflows/post.yml`
- `.github/workflows/watchdog.yml`
- `.python-version`
- `CITATION.cff`
- `LICENSE-CODE`
- `LICENSE-CONTENT`
- `LICENSE-DATA`
- `README.md`
- `SECURITY.md`
- `docs/32-RELEASE-PROVENANCE.md`
- `pipeline/release_provenance.py`
- `requirements.lock`
- `scripts/reproduce_subset.py`
- `tests/test_public_archive.py`
- `tests/test_w11_hardening.py`

## Deviations and adjudicated compatibility changes

1. The user instruction selected `f99a507` as the base. Docs/29 contains an older embedded baseline
   SHA. The explicit work order controls, so this branch starts at `f99a507`.
2. W6 updates three older fixtures and one older nomenclature test. Their inputs or assertions encoded
   the superseded assumption that nomenclature stayed message-eligible while the chip feature was
   dark. Docs/29 W6 explicitly replaces that assumption. The docs/28 tests remain unmodified.
3. W11 updates `tests/test_public_archive.py`. Its old assertion required posting inside RUN B.
   Docs/29 W11 explicitly requires posting-job separation. The revised test proves RUN B commits
   before RUN C posts, rerenders, and commits the signed archive.
4. The required operator interpreter path reports Python 3.13.13 on this machine, although the work
   order describes it as the Python 3.12 interpreter. All package suite evidence used that required
   path. Production is pinned to CPython 3.12.10 by W11.
5. Existing manifests do not yet contain W9 `corrections_count`. The status page reports that value as
   unknown until the first future RUN B writes the additive field. Unknown is never green.

No other deviation from docs/29 is known.

## Incomplete items and blockers

No W1 through W11 implementation item is incomplete. No package stopped on a blocker.

The license files are the attorney-pending placeholders required by W11. Final license selection is
an operator and attorney act already covered by open project task `#110`; no duplicate task was filed.

## Final validation

Run:

```powershell
& 'C:\ProgramData\miniconda3\python.exe' tests/run_tests.py
```

Expected result: `572 passed, 0 failed`.
