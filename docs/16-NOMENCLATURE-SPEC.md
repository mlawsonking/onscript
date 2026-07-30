# 16. Nomenclature Segregation: the build spec (measured)

> Editorial note (2026-07-30): the absolute operator paths naming repository files were shortened
  to repo-relative paths under docs/37 rule 16. Findings, decisions, and chronology are unchanged.
  The scratchpad path recording the verification probes is left as written, because it points
  outside the repository and is the provenance of the "I edited no repo files" statement.

> **Status: specification only; not built.** Authored 2026-07-16 by an Opus design review (3 mappers
  ->
> 3 competing designs -> 3 adversarial judges -> synthesis; 10 agents, ~1.4M tokens). Every
> critical claim was verified against the 75,989-statement corpus rather than reasoned
> about. It is CLAUDE.md queue item **(d)**, and it is the common prerequisite for v2 **1.3**
> (Authors-vs-Vessels), **1.5** (Awards), any **coordination headline claim**, and the **CREC lane**
> (docs/15 §9 amendment D1-A).
>
> **Why it exists.** The live site's "top synchronized phrases" are substantially bill titles,
> committee names, and person names, not messaging. The measured trigger: v2 1.3 would have
> published *"Chip Roy authored the save Act"*, where what actually happened is that he was the
> first member in our press corpus to type the name of a bill he sponsored.
>
> **Core finding.** *Nomenclature is a property of the
> occurrence, not of the phrase.* The span `the save act` is nomenclature in "reintroduced the save
> Act" and messaging in "the save Act would gut Medicaid". No test applied to a phrase in isolation
> separates them, which kills the dictionary/blacklist approach outright.
>
> **Why capitalization lost.** The rejected design read Title-Case in the source. It is defeated by
> a press secretary holding shift, and worse, it is *party-correlated*: R press shops shout 54%
> more, so the shouting-skip rule silently under-tags one party for stylebook reasons. That is an
> asymmetric **instrument**, which Article IV forbids (asymmetric *findings* are always allowed).
> Its truncation rule (B) is grafted into the winner, where it is safe precisely because span's
> spans are official records rather than typography.
>
> **Rulings this spec explicitly refuses to make** (its §9; filed as Vikunja tasks): the Article
> xiii privacy question, the aca call, the rank-and-truncate skew, the quiet-day floor, and the
> launch bar. An implementer must not self-authorize these.

---

# Build spec. Nomenclature Segregation (`pipeline/nomenclature.py`)

## 0. Winner and justification (3 sentences)

**SPAN wins with CAP Rule B for truncation.** Every SPAN tag cites a party-blind official record. On
the separating cases, `child tax credit` scores **0.003 under SPAN** and **0.683 under CAP**, where
CAP
produces a false positive. `the big ugly bill` remains untagged at **0.000 under SPAN**, while CAP
tags
the Democratic counter-brand at 0.908. CAP is unsuitable as the primary method because Republican
press shops use all caps 54% more often, which makes its capitalization signal party-correlated. CAP
Rule B remains useful because it raises the straddling-window example `bipartisan 21st century road
to housing` from 0.000 to **0.986** with zero regressions across all 10 protected phrases.

## 1. Two corrections to the inputs, both critical, both measured by me

(a) The buildability judge's headline finding is a misdiagnosis. span's 07-15 failure is a one-line
regex bug, not an architectural defect.

span's spec says *"Strip a trailing `of YYYY` from every name at index time"* with
`\s+of\s+(19|20)\d{2}\s*$`. But appropriations titles are **comma-year**, not "of"-year: `"National
Security, Department of State, and Related Programs Appropriations Act, 2026"` tokenizes to `...
appropriations act 2026`. The spec's regex does not match a bare trailing year, so **the entire
appropriations family is absent from the index** and the bill lane scores the live #1/#2 at 0.000.
Measured:

```
COV: --- --- --- --- --- --- --- --- --- ---     (SPAN's spec regex)
```

With `_YEAR_TAIL = re.compile(r"(\s+of)?\s+(19|20)\d{2}\s*$", re.I)`:

```
TITLE: national security department of state and related programs appropriations act 2026
COV  : COV COV COV COV COV COV COV COV COV COV ---
  anchor_covered('national security department')                  = True
  anchor_covered('state and related programs appropriations act')  = True
```

Both live rows tag, **with no Rule B needed for this case**. The judge diagnosed the symptom
correctly and the cause wrongly; do not "fix" this with architecture.

**(b) Both designs misattribute the Constitution.** Symmetry is **Article IV** ("Symmetric
instrument, asymmetric findings", `docs/06-CONSTITUTION.md:25`). Article iii is the two-lanes rule.
The neutrality judge is right.

## 2. My measurements (full 75,989-statement corpus, 119/hr index, fixed year normalization)

| phrase | docs | ruleA | **A+B** | verdict |
|---|---|---|---|---|
| `21st century road to housing act` | 287 | 1.000 | **1.000** | kill |
| `the one big beautiful bill act` | 705 | 1.000 | **1.000** | kill |
| `state and related programs appropriations act` | 35 | 1.000 | **1.000** | kill |
| `bipartisan 21st century road to housing` | 69 | 0.000 | **0.986** | kill *(Rule B only)* |
| `the bipartisan 21st century road to` | 66 | 0.000 | **0.985** | kill *(Rule B only)* |
| `century road to housing act which` | 38 | 0.000 | **1.000** | kill *(Rule B only)* |
| `national security department` | 184 | 0.109 | **0.109** | needs committee lane |
| **`the big ugly bill`** | **196** | **0.000** | **0.000** | **protect ✓** |
| `the save act would` | 42 | 0.000 | **0.000** | protect ✓ |
| `so-called save act` | 22 | 0.000 | **0.000** | protect ✓ |
| `cuts to medicaid` | 866 | 0.000 | **0.000** | protect ✓ |
| `child tax credit` | 583 | 0.003 | **0.003** | protect ✓ *(CAP: 0.683 ✗)* |
| `law enforcement officers` | 1399 | 0.002 | **0.002** | protect ✓ |
| `the middle east` | 1462 | 0.000 | **0.000** | protect ✓ |
| `birthright citizenship` | 262 | 0.000 | **0.000** | protect ✓ |
| `the west bank` | 202 | 0.000 | **0.000** | protect ✓ |
| `border patrol agents` | 373 | 0.000 | **0.000** | protect ✓ |
| `to release the epstein files` | 126 | 0.000 | **0.000** | protect ✓ |

**Rule B costs nothing and buys the whole 07-13 residual.** Rule B is safe *here specifically
because span's spans are official records, not typography*, It is why the same rule is dangerous
in CAP and safe in SPAN. `national security department` at 0.109 with the bill lane alone
independently confirms **the committee lane is critical** (buildability measured 0.946 with it).

## 3. Required module layout

### `pipeline/nomenclature.py` (core-source-level, importable by press and crec; **not** `pipeline/deep/`, so no genre-isolation violation: it reads official records, not genre formulas)

```python
"""Nomenclature segregation by official-name span containment. Tag, don't delete.

Nomenclature is a property of the OCCURRENCE, not of the phrase: the span `the save act`
is nomenclature in "reintroduced the SAVE Act" and messaging in "the SAVE Act would gut
Medicaid". No test applied to the phrase in isolation separates them.
"""
from __future__ import annotations
import re, json, functools
from pipeline import boilerplate, config

# Index-time: strip BOTH "Act of 2026" and "Act, 2026" (the latter tokenizes to a BARE
# trailing year and is the form EVERY appropriations title uses — omitting the `(\s+of)?`
# branch silently drops the entire appropriations family. Measured, not theorized.)
_YEAR_TAIL = re.compile(r"(\s+of)?\s+(19|20)\d{2}\s*$", re.I)
_YEAR = re.compile(r"(19|20)\d{2}")
_MIN_NAME_CONTENT_TOKENS = 2
LEAD_DET = frozenset({"the", "a", "an"})

def _toks(s: str) -> list[str]:
    """Tokenize with the SAME tokenizer that produced the ledger n-grams (non-negotiable:
    boilerplate.sentences() strips commas, which is why 'National Security, Department of
    State' is windowable as 'national security department')."""
    out = []
    for sent in boilerplate.sentences(s):
        out.extend(sent)
    return out

@functools.lru_cache(maxsize=16)
def load_index(congress: int) -> dict[str, tuple[tuple[str, ...], ...]]:
    """Cumulative era-scoped index: union of congresses 108..congress (anachronism guard —
    a 2015 phrase is never suppressed by a 2025 bill). Keyed by first token, longest-first."""

def name_spans(toks: list[str], idx) -> list[tuple[int, int, str]]:
    """Greedy longest-match walk. Returns INCLUSIVE runs (r0, r1, cite).
    Absorbs an optional trailing 'of YYYY' or bare 'YYYY' after a matched name."""

def _anchor(ptoks: list[str], i: int) -> int:
    """Index of the phrase's FIRST CONTENT TOKEN. Leading STOPWORDS may fall outside a span
    (a leading article is a member referring to a name); a TRAILING modal starts a predicate.
    REGRESSION: 'would' IS in boilerplate.STOPWORDS — a rule that ignores ALL stopwords scores
    'the save act would' at 1.00 TAG, a false positive on the task's own acceptance case."""

def classify_occ(toks, i, n, runs) -> str | None:
    """'A' containment | 'B' truncation | None.
    A: r0 <= a and b <= r1                       -> the phrase IS the name / a clean window
    B: (r0 < a <= r1 < b) or (a < r0 <= b < r1)  -> the phrase edge cuts INSIDE the run
    run strictly inside the phrase (a < r0 and r1 < b) -> None (PREDICATION: the message)"""

def is_nomenclature(ngram: str, congress: int) -> dict | None:
    """verdicts-{congress}.json lookup. Returns {'ratio','lane','cite','class','docs',
    'nom_docs','rule','index_version'} or None. MUST NOT accept a `party` argument (Art. IV)."""

def tag(rows: list, key: str = "ngram", congress: int | None = None) -> list:
    """Attach row['nomenclature'] in place; NEVER drops a row. Mirrors
    crec_boilerplate.suppress()'s display-time API shape, but tags instead of suppressing."""
```

### `pipeline/nomenclature_build.py`, one-time/weekly capex, **never on the daily path**

```python
def fetch_billstatus(congress: int, bill_type: str, dest) -> Path   # masked-error guard
def parse_titles(zip_path) -> set[str]                              # titleTypeCode allowlist
def synthesize_acronym_glosses(shorts_per_bill) -> set[str]         # "Long (ACRO) Act"
def build_committee_names(yaml_paths) -> dict                       # PyYAML, local only
def build_verdicts(congress: int, corpus_path) -> dict              # full-corpus occurrence scan
def main()                                                          # writes data/reference/nomenclature/
```

### `pipeline/config.py` additions

```python
NOMENCLATURE_RATIO_MIN = 0.80          # tag iff ratio >= this
NOMENCLATURE_INDEX_CONGRESS_MIN = 108  # BILLSTATUS bulkdata floor (107 -> 404)
COMMITTEE_UNQUALIFIED_MIN_TOKENS = 3   # generic-subcommittee hazard: 43 names are <3 tokens
FEATURES["nomenclature_tag"] = False   # build-dark / release-by-gate
```

### `TITLE_TYPE_ALLOW` (in `nomenclature_build.py`)

```python
TITLE_TYPE_ALLOW = frozenset({"101","102","103","104","106","107","108","109",
                              "146","147","151","152","250","252","254","255","256","27","30"})
# BAN Official (6/7/10/259): prose, median 25 tokens vs 6 for short.
# BAN Display (45): prose whenever a bill has no short title — 856/9,712 bills (8.8%),
#   ~97% byte-identical to the Official prose title. Display leaks prose; short-only does not.
# Key on titleTypeCode (machine-stable int), NEVER a regex over the prose `titleType`.
```

## 4. Reference-data acquisition

**Keyless. No `DATA_GOV_API_KEY`.** `pipeline/deep/lanes.py:23` sets the press core source to `2013-2026`
= congresses 113–119; billstatus bulkdata covers 108–119. **The live contamination is entirely
fixable keyless, do not sequence it behind the key.**

```
https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/{type}/BILLSTATUS-{congress}-{type}.zip
types: hr,s,hjres,sjres,hconres,sconres,hres,sres
```
- Build **113–119** (347.5 MB, ~5 min). 108–112 is a **deferred** follow-up (see §7).
- Measured: 119/hr = 29.2 MB in 16.4s, `application/zip`, 9,712 bills parsed in 6.3s, 11,404 names.
- Congress 107 → **404** (not in bulkdata). Out of scope.

**masked-error guard, must be in code, It is a real trap:**
```python
r = urlopen(Request(url, headers={"Accept": "application/json"}))
ct = r.headers.get("Content-Type", "")
if "zip" not in ct and "json" not in ct:      # NOT status == 200
    raise RuntimeError(f"masked bulkdata error: Content-Type={ct!r}")
```
The bulkdata *directory* service returns **HTTP 200 with an HTML error page** when `Accept:
application/json` is absent. `pipeline/deep/crec.py::_get()` checks neither.

**Committees:**
`https://raw.githubusercontent.com/unitedstates/congress-legislators/main/committees-{current,historical}.yaml`
(63,336 + 214,181 bytes). Parse **once, locally** with PyYAML 6.0.3 (present in the conda python,
absent in Actions); commit JSON. Matches CLAUDE.md's generator policy and the
`crec_granule_classes.json` precedent. `theunitedstates.io` JSON exports are dead from this box (ssl
eof), that note at `pipeline/roster.py:4-5` should be narrowed to that host, not the project.

**Committee qualification rule (verified necessary. 43 of the current subcommittee names are <3
tokens: `Defense`, `Africa`, `Europe`, `Readiness`, `Western Hemisphere`):** a name enters
unqualified **only if ≥3 content tokens**; shorter names enter **only** as `committee on X` /
`subcommittee on X` / `X committee` / `X subcommittee`.

**Storage:**
- Zips → `X:\onscript-data\bills\raw\` via `lanes.lane_raw()` + `CrawlManifest` + sha256 (1.9 TB
  free).
- Committed → `data/reference/nomenclature/`: `bill-titles-{congress}.json` (0.62 MB/congress, ~4.3
  MB for 113–119), `committee-names.json`, `verdicts-{congress}.json`. Each carries the
  `schema_version`/`kind`/`source`/`fetch_date`/`rationale`/`amend_policy`/dated-`amendments` header
  from `crec_boilerplate_seeds.json`.

**gitignore trap (verified, it's line 20, not 19):** `.gitignore:20` is `data/reference/*` with
explicit `!` re-includes. New tables are invisible to git unless you add, mirroring lines 25–26:
```
!data/reference/nomenclature/
!data/reference/nomenclature/*.json
```

**Refresh:** a `workflow_dispatch` + weekly Actions job, **entirely separate** from the daily cron.
Between refreshes a brand-new bill title is untagged, bounded, disclosed lag. The daily pipeline
never touches the network for this.

## 5. Mutation fixture in `tests/test_nomenclature.py`

Runs offline against a committed fixture slice so a third party reproduces from committed data
alone. Follows `tests/test_deep_crec_boilerplate.py`.

```python
def test_the_name_is_tagged_but_a_message_about_the_bill_survives():
    assert N.is_nomenclature("the safeguard american voter eligibility save act", 119)  # 1.000
    assert N.is_nomenclature("21st century road to housing act", 119)                   # 1.000
    assert N.is_nomenclature("the laken riley act", 119)                                # 1.000
    assert N.is_nomenclature("state and related programs appropriations act", 119)      # 1.000
    assert not N.is_nomenclature("the save act would", 119)   # SENTINEL: 'would' IS a STOPWORD.
    assert not N.is_nomenclature("the save act is", 119)      # A rule ignoring all stopwords
    assert not N.is_nomenclature("so-called save act", 119)   # scores 'the save act would' 1.00.

def test_rule_b_truncation_kills_straddling_windows_of_a_long_title():
    # NGRAM_MAX=6 < real title length, so windows straddle. Rule A alone returns False here.
    assert N.is_nomenclature("bipartisan 21st century road to housing", 119)   # 0.000 -> 0.986
    assert N.is_nomenclature("the bipartisan 21st century road to", 119)       # 0.000 -> 0.985
    assert N.is_nomenclature("century road to housing act which", 119)         # 0.000 -> 1.000

def test_generic_policy_english_inside_a_title_survives():
    assert not N.is_nomenclature("law enforcement officers", 119)  # 0.002 (Law Enf. Officers Safety Act)
    assert not N.is_nomenclature("child tax credit", 119)          # 0.003 (No Child Tax Credit for Illegals Act)
    assert not N.is_nomenclature("the middle east", 119)           # 0.000 (...Security in the Middle East Act)
    assert not N.is_nomenclature("birthright citizenship", 119)    # 0.000 (Birthright Citizenship Act of 2025)
    assert not N.is_nomenclature("border patrol agents", 119)
    assert not N.is_nomenclature("cuts to medicaid", 119)
    assert not N.is_nomenclature("the west bank", 119)
    assert not N.is_nomenclature("to release the epstein files", 119)

def test_killfixture_the_statutes_name_is_tagged_but_the_counter_brand_is_the_finding():
    rows = [{"ngram": "the one big beautiful bill act", "party": "R", "day_peak": 113},
            {"ngram": "the big ugly bill",             "party": "D", "day_peak": 55}]
    out = N.tag(rows, congress=119)
    assert out[0]["nomenclature"]["class"] == "official_name"   # cites BILLSTATUS HR1
    assert out[1].get("nomenclature") is None                   # 0.000 — no such statute exists
    assert all(r in out for r in out)                           # TAG NEVER DELETES, both parties

def test_committee_lane_is_load_bearing():
    # bill lane ALONE scores the live #1 at 0.109 -> MISS. Committee lane -> 0.95 TAG.
    assert N.is_nomenclature("national security department", 119)["lane"] == "committee"

def test_generic_subcommittee_name_requires_qualification():
    assert not N.is_nomenclature("aviation in this country", 119)
    assert N.is_nomenclature("the subcommittee on aviation", 119)

def test_year_variants_match_one_name():
    # Index-time _YEAR_TAIL MUST strip a BARE trailing year ("Act, 2026"), not just "of YYYY".
    assert N.is_nomenclature("water resources development act", 119)                  # 1.000
    assert N.is_nomenclature("state and related programs appropriations act", 119)    # comma-year

def test_official_and_display_titles_never_enter_the_index():
    assert not N.is_nomenclature("to amend the national voter registration act of 1993", 119)

def test_acronym_gloss_is_recovered():
    assert N.is_nomenclature("american voter eligibility save", 119)  # needs the synth canonicalizer

def test_the_tagger_cannot_read_party():
    import inspect
    assert "party" not in inspect.signature(N.is_nomenclature).parameters   # Article IV
    assert "party" not in inspect.signature(N.name_spans).parameters

def test_bulkdata_masked_error_is_rejected():
    # HTTP 200 + text/html "Govinfo Bulkdata Service Error" must raise, not parse.
```

## 6. Where it plugs in, display-time first, ledger second

**Layer 1, display-time (ship this first; fixes the live site today, no rebuild).** The repo has
this pattern **twice already with the same stated rationale** (*"so regex/knob updates take effect
on an already-built ledger without re-running the engine"*): `pipeline/build.py:135-139`
(boilerplate guard re-applied inside `top_synchronized`) and `pipeline/site.py:684`
(`collapse_and_rank` re-applied at render). Call `nomenclature.tag()` at both sites. This
**retroactively corrects every historical page across all 25 years** without touching the
3,084,929,086-byte `data/state/ledger.json` (~30-min engine).

**Layer 2, ledger (permanent, at the next natural rebuild, not a launch blocker).** The entry write
at `pipeline/phrases.py:179-187` has a **dead field**, `"boilerplate": False` (line 186), a
hardcoded literal, written once, read nowhere. The nomenclature block sits beside it:
```python
"nomenclature": {"ratio": 0.95, "lane": "committee", "cite": "subcmte:HSAP",
                 "class": "institution", "rule": "A", "docs": 184, "nom_docs": 175,
                 "index_version": "2026-07-16"},
```
**Purely additive. `schema_version` stays 1**; every existing reader (`iter_ledger_entries`,
`phrase_summary`) ignores it. **Leave `"boilerplate": False` as-is**, the ledger is
append-only and removing it is a compat break for zero gain.

**Justification against the append-only rule:** the append-only law binds `data/raw/`.
`data/reference/` and the derived ledger are *derived indices*. Adding a field is additive, not a
mutation. The display-time layer touches neither, which is precisely why it re-runs over 25 years of
history for free.

**must tag before the LLM, not after.** `pipeline/distill.py` builds P2/P3 from stats+fragments;
with `LLM_VOICE_ENABLED=true` the Sonnet voice will otherwise launder nomenclature into fluent prose
**and the verifier will pass it** (32 Democrats really did type it). The existing citation
protection does not cover this failure mode.

**Aggregation rule.** `ratio = docs_where_every_occurrence_is_covered / docs_containing_phrase`,
doc-level, matching `_doc_ngrams`' existing set-dedupe semantics (`pipeline/phrases.py:30-41`). A
document counts as nomenclature only if *every* occurrence in it is covered: conservative,
precision-favoring.

**Wire into the nightly audit.** `pipeline/ops.py::symmetry_report` (lines 123–162) publishes
nothing about suppression, so an asymmetric tagger would be **invisible to it**. Add
`nomenclature_tagged` + `nomenclature_rate` per party to `parties[p]`, and fold the index version
into `thresholds_sha()`.

## 7. What it does not do, and what it defers

**Does not:**
- **Delete anything.** Tag-only, behind `FEATURES["nomenclature_tag"]`. Wiring tag→suppress is a
  **live Article IV defect in both directions** (it would delete either the 113-R obbba flagship or
  the 55-D counter-brand). Tag, chip, toggle. Never a blacklist.
- Fix **proc (18/83) or generic (4/83)**. 26.5% of the junk is a boilerplate problem, not a
  nomenclature one.
- Fix **person/place names**. `<private-individual-A>` (10 D) and `<private-individual-B>` (8 D) are
  untouched.
- Fix **sub-gram inflation as a merger.** Rule B tags straddling windows but does not *collapse*
  them into a canonical row. Inflation and contamination are orthogonal defects; a perfectly
  collapsed `21st century road to housing act, peak 12` is still a category error. **Ship SPAN as a
  tagger, not as a better merger.** (The name index *is* the canonical-title anchor
  `_content_subrun` structurally cannot produce, that's the follow-up, not this.)
- Fix **bill numbers.** `22 the safeguard american` (peak 14) survives; `h r 22` tokenizes to a bare
  `22` no name span covers.

**Defers:**
1. **Congresses 108–112** (222.6 MB). Press core source is 113–119; 108–112 serves Alexandria/CREC only.
   `titleTypeCode` vocabulary for 108–112 is **unmeasured**, verify before hardcoding the allowlist
   there.
2. **Congress 107**. billstatus 404s; api-only, ~11k calls at an unverified rate limit. Serves the
   CREC lane, last in session-yield order.
3. **The `first_seen` repair.** `data/derived/days/2026-07-15.json` has `first_seen.bioguide =
   E000246` = **Chuck Edwards (r-nc)** for the *Democratic* composite's top phrase, the first person
   to type a subcommittee's name is whoever announced their vice-chairmanship. Every propagation
   claim on a nomenclature first-sayer is wrong the same way. Separate session, separate commit,
   dated `data/reference/corrections.json` entry.
4. **The CAP/capitalization lane, deferred, not adopted.** Rejected as primary (party-correlated
   mechanism, uncitable, gameable, `child tax credit` FP). Reconsider **only** as a narrowly-gated
   `unattested_proper_name` class for congress 107/CREC where billstatus cannot reach.
5. Ledger-scale threshold histogram (§8).
6. **The `\bcommittee\b` one-liner.** `pipeline/boilerplate.py:41` is `\bcommittee on\b` while
   **line 43 is already a bare `\bsubcommittee\b`**, an outright inconsistency. A bare
   `\bcommittee\b` catches `house transportation and infrastructure committee` with zero measured
   collateral. **Land it separately; do not gate this item on it.**

## 8. Acceptance gate

1. **All 188 existing tests stay green** (`tests\run_tests.py`;
   `CLAUDE.md`'s "138" is stale) plus the new fixture.
2. 2026-07-15's #1 flips `national security department` → **`the west bank` (25 D)**.
3. 2026-07-13's top row is **not** a window of the road-to-housing title (Rule B must clear all
   four).
4. **Re-run the ratio histogram over all 1,370 congress-119 phrases at peak≥15, at ledger scale, not
   the 113 rendered rows, before locking `NOMENCLATURE_RATIO_MIN`.** Buildability measured
   `transportation and infrastructure` at **0.802**, one thousandth above the threshold, which
   falsifies span's "zero phrases in the 0.60–0.80 dead zone; the threshold does no delicate work"
   claim. **Do not publish the bimodality-as-validation argument.** Ship the threshold as a
   disclosed knob. Report the tag **rate**, not the count (the rendered table is 103 D / 15 R;
   `1/15` is meaningless).

## 9. Decisions reserved for a ruling

| # | Question | Who | Why |
|---|---|---|---|
| **1** | **Article XIII privacy, raise before this item ships.** `<private-individual-A>` (10 D) and `<private-individual-B>` (8 D) render as top synchronized phrases on the live site. `docs/06-CONSTITUTION.md:66-69` ("never private citizens… regardless of how interesting") is effectively unamendable. I did not verify whether these are private individuals or public figures in covered cases. Both designers and two judges independently flagged this as plausibly higher-severity than bill titles, and this spec does not fix it. | **Michael** | Constitutional, effectively unamendable, live now. |
| **2** | **The aca decision.** `the affordable care act` (2,061 occ, 40 D peak) scores 0.000 only under a 119-only index; under the cumulative 113–119 index it becomes **tag**. Consistent (it is the statute's name; `affordable care act tax credits` still survives at 0.000) but a **product decision, not a technical one**. Must be resolved *visibly in `verdicts-119.json`* before shipping, not silently at index-build time. | **Michael** | Product call on a marquee D phrase. |
| **3** | **The rank-and-truncate skew.** `build.collapse_and_rank(rows, k=20)` ranks a **pooled two-party list by raw `day_peak`** and truncates at 20, so the larger caucus structurally fills the table: **103 D / 15 R (87% D)**, and **100% D (20/0, 16/0)** on 2026-07-15 and 2026-06-30. **It is a pre-existing Article IV instrument asymmetry that dwarfs nomenclature**, and this item's neutrality metric is computed on top of it. File as its own item. | **Fable** | Article IV instrument design. |
| **4** | **The quiet-day floor.** After tagging, 2026-07-13 leads with `an important step` (6 D). The tagger converts “confidently wrong” into “accurately empty.” That is progress, but it is not a publishable post, and the pipeline posts every day. A floor rule can state that nothing cleared the bar. | **Fable** | Product/editorial; interacts with §13 daily-always cadence. |
| **5** | **Scope honesty.** The queue item's own gate is *"before any coordination headline claim."* **This spec does not satisfy that gate alone**, after tagging, 2026-07-14's #1 is still a person name. The defensible claim is *"the top of the table stops being bill titles on 4 of 7 days,"* not *"the table becomes good."* | **Michael** | Sets the launch bar. |

## 10. Cost

One-time: 113–119 = 347.5 MB, ~5 min, keyless. Daily path: **1.43 ms/statement** → ~0.43s for a
typical ~300-statement day; **$0 LLM** (no model in the path, immune to the `LLM_VOICE_ENABLED`
kill-switch, adds nothing to the $9 ceiling). **Streak risk: zero because of the design**, the daily
pipeline reads committed JSON; no network, no key, nothing to skip-and-log. Effort: ~1 session for
lanes 1+2 + display-time tagging + the fixture; the ledger field and the `first_seen` repair are
separate sessions.

**Process:** working tree has uncommitted edits to `pipeline/distill.py` and `tests/test_voice.py`,
per the parallel-session protocol, **stage only your own files; never `git add -A`**. Also correct
the stale comment at `pipeline/deep/crec.py:5-6` ("the /bulkdata zips are broken"), the operational
conclusion for CREC is right (CREC is not a bulkdata collection, 404), but the stated *reason*
generalizes wrongly and could cause a future session to skip billstatus and burn the rate-limited
key instead. The fix is **narrowing, not reversing**.

---

**Files:** spec target `pipeline\nomenclature.py`,
`pipeline\nomenclature_build.py`,
`tests\test_nomenclature.py`,
`data\reference\nomenclature\`. My verification probes:
`C:\Users\bobdo\AppData\Local\Temp\claude\C--Users-bobdo-projects-polispeak\b625d988-e876-421a-9ce3-b09a84e736e0\scratchpad\synth1.py`–`synth5.py`.
**I edited no repo files.**
