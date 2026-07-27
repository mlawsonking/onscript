# OnScript Deep Archive completion delivery packet (Opus, Session 51)

## Headline for the orchestrating session

- **D1 crawl state:** confirmed. 111, 112, 117, 118, 119 all buildable; 119's 2026 tail finished (+87
  statements) so it built COMPLETE, not partial.
- **D2 CREC shards:** all five built + audited (111, 112, 117, 118, 119). Every window passes symmetric
  two-party. The CREC E-lane now spans 107-119 (2001-2026).
- **D3 R-S50.1 3-lane substrate:** code complete and suite-green; page_html ISOLATED for all 113-119;
  scraper-lane rebuild finishing in the background (resumable). Daily pipeline unaffected.
- **D4 SD.8 instrument concordance: VERDICT = HELD.** The press-core president-naming direction (S2.9)
  reproduces on the CREC Extensions instrument in only 8/14 years, era-split (2013-2020 6/8, 2021-2026
  2/6). The CREC lane is NOT calibrated for the naming family, so **pre-2013 (107-112) CREC naming
  claims do NOT advance to publication.** No publication act performed.
- **Branch:** `opus/deep-archive` (pushed). Nothing on main touched.

**Decision Michael carries back:** SD.8 = HELD. Pre-2013 CREC president-naming publication stays gated
(press-only, stated). A within-CREC design, not a cross-instrument concordance, is the only path to power
a pre-2013 naming claim on its own lane. This is a legitimate publishable methods card either way.

## Delivery state

- Repository: `github.com/mlawsonking/onscript`
- Working branch: `opus/deep-archive` (base `origin/main` = `14e483e`)
- Freeze commit (registration, pre-measurement): `412308b`
- Measurement + records commit: this packet's commit (see `git log opus/deep-archive`)
- Baseline validation: **572 passed, 0 failed** (at `14e483e`)
- Final validation: **578 passed, 0 failed** (+2 R-S50.1 fixtures, +4 SD.8 kill fixtures)
- Test runner: `C:\ProgramData\miniconda3\python.exe tests/run_tests.py`
- Interpreter: `C:\ProgramData\miniconda3\python.exe` (bare `python` is a 0-byte stub)
- Pushes of main, deployments, workflow dispatches, posts, feature/flag/`POSTING_ENABLED` changes: **none**
- `site/public` changes: **none**
- `data/derived` changes: ONLY the intended work-order outputs, the five D2 CREC audit JSONs
  (`data/derived/crec/audit/congress-{111,112,117,118,119}.json`) and the D4 result
  (`data/derived/crec/sd8_concordance.json`). No daily-pipeline `data/derived` regeneration.
- Bulk shard data (CREC ledger/discipline/coverage; alexandria per-lane shards) written to
  `X:\onscript-data` only, outside the repository.
- Cost: $0, deterministic compute, zero Anthropic calls.

## Isolation and X-branch collision avoidance

Ran entirely in the isolated worktree `C:\Users\bobdo\projects\polispeak-deep` on `opus/deep-archive`,
created off `origin/main`. The operator checkout `C:\Users\bobdo\projects\polispeak` was owned by an
ACTIVE Codex worker on `codex/x-packages` throughout; its branch, index, and working tree were never
touched. Before editing any repository file, checked `git log origin/main..codex/x-packages -- <file>`.

| File | Edited/created | X-branch divergent commits touching it |
|---|---|---|
| `pipeline/alexandria.py` | edited | none (clean) |
| `pipeline/search/wave_s4.py` | edited | none (clean) |
| `tests/test_search_provenance.py` | edited | none (clean) |
| `scripts/deep/sd8_concordance.py` | created | n/a (new) |
| `scripts/search/build_source_lane_shards.py` | created | n/a (new) |
| `tests/test_deep_sd8.py` | created | n/a (new) |
| `docs/13-SEARCH-LEDGER.md` | edited | none (clean) |
| `docs/15-DEEP-ARCHIVE-PROGRAM.md` | edited | none (clean) |
| `docs/04-BUILDLOG.md` | edited | none (clean) |
| `docs/26-SESSION-HISTORY.md` | edited | none (clean) |

codex/x-packages and origin/main share merge-base `085184e` and each have 7 divergent commits on
disjoint file sets (the X1-X15 surface vs the deep/search surface). No collision occurred; none had to be
recorded as a blocker. Repository text is CRLF (`core.autocrlf=true` normalizes on commit); no em dash
(U+2014) in any authored line (verified by diff scan).

## D1. Confirm crawl state

```
C:\ProgramData\miniconda3\python.exe scripts/deep/crec_state.py
C:\ProgramData\miniconda3\python.exe scripts/deep/build_crec_shards.py --congresses 111,112,117,118,119 --dry-run
```

`crec_state.py` reported 111, 112, 117, 118, 119 all buildable. The strong per-year sitemap-completeness
check refused 119 because 2026 was truncated (114 crawled / 118 in sitemap; missing e.g. CREC-2026-06-11,
2026-07-21, 2026-07-22, 2026-07-23). Resolved by finishing the crawl (see below); 119 then verified
COMPLETE (2026: 118/118). 111/112/117/118 were COMPLETE on the first check (settled upstream `day-nomods`
gaps counted as settled, not pending).

## D2. Build the five CREC shards

Crawl the 2026 tail first (keyless GovInfo, $0), then build:

```
C:\ProgramData\miniconda3\python.exe scripts/deep/crawl_crec.py --years 2026
C:\ProgramData\miniconda3\python.exe scripts/deep/build_crec_shards.py --congresses 111,112,117,118,119
```

The 2026 crawl added the 4 missing days (+87 Extensions statements). The build used the §D1-C discipline
verbatim: online per-year sitemap completeness, settled-unavailable days counted as settled, no
`--allow-partial`, per-shard audit committed. Every window PASSES symmetric two-party:

| Congress | ledger entries | audit windows (D members / R members, ratio) |
|---|---:|---|
| 111 | 12,392 | 2009 259/175 r=0.676 PASS · 2010 259/178 r=0.693 PASS |
| 112 | 4,656 | 2011 198/226 r=0.876 PASS · 2012 197/222 r=0.887 PASS |
| 117 | 560 | 2021 208/192 r=0.923 PASS · 2022 207/189 r=0.913 PASS |
| 118 | 459 | 2023 202/187 r=0.926 PASS · 2024 202/195 r=0.965 PASS |
| 119 | 555 | 2025 192/188 r=0.979 PASS · 2026 170/142 r=0.835 PASS |

Ledger/discipline/coverage shards on `X:\onscript-data\crec\state\`; audits committed to
`data/derived/crec/audit/`.

## D3. Lane-aware substrate rebuild (R-S50.1)

**Premise correction (deviation, filed).** The work order cited "the lane-blind read recorded open in
Session 21" for `alexandria.load_congress_records` and `wave_s4._collect`. At the branch base those reads
were already 2-lane-aware (Session 19 gave them the propublica/scraped instrument fold). The genuine
remaining work under R-S50.1 was the 2->3-lane ISOLATION upgrade (page_html as its own lane), not a
from-scratch lane fix. Recorded in the docs/13 R-S50.1 row.

Code (all suite-green):
- `pipeline/alexandria.py`: `SOURCE_LANES = (legacy, scraper, page_html)` primary; `load_congress_records`
  / `lane_shard_path` accept the isolated source lanes (filtered by `date_source`, matching
  `harness.iter_statements`) alongside the folded instrument names (`propublica`/`scraped`), kept as a
  labelled robustness view only; `reconcile_source_lanes` asserts `legacy + scraper + page_html ==
  combined`.
- `pipeline/search/wave_s4.py`: `_collect` carries the isolated `date_source` as the primary lane key;
  `inst` folded, robustness only.
- `tests/test_search_provenance.py`: +2 fixtures (page_html isolated at the loader; source-lane shard
  paths; the 107-112 combined-only guard fires for a source lane).

Daily-pipeline isolation VERIFIED: `run_collect`/`run_assemble`/`distill`/`build`/`ops`/`verify`/
`post_bluesky` do not import alexandria; nothing in D3 reaches a public surface.

Substrate rebuild (`scripts/search/build_source_lane_shards.py`, `PYTHONHASHSEED=0`):

```
PYTHONHASHSEED=0 C:\ProgramData\miniconda3\python.exe scripts/search/build_source_lane_shards.py
```

- `page_html` built fresh and ISOLATED for all 113-119 (COMPLETE): records 6 / 108 / 62 / 403 / 454 /
  794 / 1012 for 113..119.
- `scraper` (page_html excluded) rebuilding in the BACKGROUND at delivery time (resumable; ~148 MB
  ledgers/congress; the long pole). Not a blocker: writes to X: only, and SD.8 does not depend on it.
- `legacy` == the existing `propublica` shards by identity (`instrument propublica = {legacy}`; copied,
  no recompute).

## D4. SD.8, frozen then run

Freeze-before-measure: the registration and thresholds were committed in `412308b` BEFORE measurement.

```
C:\ProgramData\miniconda3\python.exe scripts/deep/sd8_concordance.py
```

Frozen protocol (`scripts/deep/sd8_concordance.py`; docs/13 SD.8 registration row): family =
president-NAMING (the S2.9 Boogeyman family), the one unambiguous CREC analogue; metric identical to S2.9
(sitting-president `name_token` per 1000 words, out-party vs in-party, per year 2013-2026); floor 200
statements/party/year; CONFIRM iff >=8 scored years AND agreement>=0.75 AND both sub-eras majority out>in;
REFUTE iff contradiction>=0.75; else HELD.

Result on 68,527 CREC Extensions statements (113-119): out>in in **8/14** years (agreement 0.571),
era-split **2013-2020 6/8** but **2021-2026 2/6**, contradiction 0.429. **VERDICT: HELD.** The CREC lane
is not calibrated for the naming family; pre-2013 naming publication stays gated (press-only, stated).
Kill fixtures (`tests/test_deep_sd8.py`) prove the gate rejects a null (equal naming -> HELD, not a false
CONFIRM or REFUTE), confirms a positive control, and refutes an inverted control. Result at
`data/derived/crec/sd8_concordance.json`.

Family-selection is stated, not silent (docs/13 SD.8 rows): the S1 phrase-coordination family has no
admissible CREC analogue yet (CREC is a weak coordination carrier until the crec boilerplate layer is
built, docs/15 §9, 3 residuals open); S4 is BLOCKED; the S2 lexical-style family is register-confounded
with directionless nulls. The registration was frozen, not reinterpreted mid-run.

## D5. Records (all on the branch)

- `docs/13-SEARCH-LEDGER.md`: the R-S50.1 ruling record; the SD.8 REGISTERED row (frozen); the SD.8 HELD
  verdict row.
- `docs/15-DEEP-ARCHIVE-PROGRAM.md`: §9 amendment (crawl confirmed, five shards built, R-S50.1 substrate,
  SD.8 HELD).
- `docs/04-BUILDLOG.md`: Session 51 entry with full evidence and the Art. XVI expectation-vs-observation
  check.
- `docs/26-SESSION-HISTORY.md`: dated Session 51 entry.

## Files created or modified

Created: `scripts/deep/sd8_concordance.py`, `scripts/search/build_source_lane_shards.py`,
`tests/test_deep_sd8.py`, `data/derived/crec/audit/congress-{111,112,117,118,119}.json`,
`data/derived/crec/sd8_concordance.json`, `delivery/DEEP-packet.md`.
Modified: `pipeline/alexandria.py`, `pipeline/search/wave_s4.py`, `tests/test_search_provenance.py`,
`docs/13-SEARCH-LEDGER.md`, `docs/15-DEEP-ARCHIVE-PROGRAM.md`, `docs/04-BUILDLOG.md`,
`docs/26-SESSION-HISTORY.md`.

## Deviations, blockers, and carried work

- **Deviation (premise correction):** the D3 "lane-blind read" premise was stale; the reads were already
  2-lane (Session 19). R-S50.1 was implemented as the 2->3-lane isolation. Justified and filed above.
- **Deviation (initiative):** finished the 2026 crawl tail (4 days, +87 statements) so 119 built COMPLETE
  rather than being deferred or `--allow-partial`. Keyless, $0, within the Deep Archive mandate.
- **Not a blocker (long-running):** the scraper-lane substrate rebuild continues in the background at
  delivery time (resumable; ~hours). page_html isolation, the core of R-S50.1, is complete for all
  113-119. The rebuild writes to X: only and does not gate SD.8.
- **Carried (future session):** re-running the eleven S1 hypotheses on the isolated substrate (docs/18 §4:
  migrate each reader as it is re-run, never ahead of need). Out of scope for this session.
- **Out of scope (untouched):** silence_board wiring (#198); the X1-X15 order; any prompt/threshold/
  schema/flag change; any publication, posting, or recurring cost.
