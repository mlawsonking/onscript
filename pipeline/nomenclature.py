"""Nomenclature segregation by official-name span containment. Tag, don't delete (docs/16).

Nomenclature is a property of the OCCURRENCE, not of the phrase: the span `the save act`
is nomenclature in "reintroduced the SAVE Act" and messaging in "the SAVE Act would gut
Medicaid". No test applied to the phrase in isolation separates them — which is why this
module never asks "does this phrase look like a name?" and instead asks, of every occurrence
in the real corpus, "does an official record's name span cover it?".

Spine-level, not pipeline/deep/: it reads official records (BILLSTATUS titles, the committee
roster), not genre formulas, so both the press and crec lanes import it without a genre-isolation
violation. Article IV: nothing here can see party — the sources do not carry it and the signatures
refuse it.

Two stages, split so the daily path stays offline and $0:
  build (offline, pipeline/nomenclature_build.py) — the index tables + the per-congress verdicts,
    which need the whole corpus because the ratio is a doc-level measurement.
  read (here) — a committed-JSON lookup. No network, no key, no model: streak risk is zero.
"""
from __future__ import annotations

import functools
import json
import re

from . import boilerplate, config

_REF = config.REFERENCE / "nomenclature"

# Runtime year absorption. The index is already year-stripped (nomenclature_build._YEAR_TAIL), so a
# name run in a document stops one token short of the year the member actually typed; absorbing it
# keeps "Water Resources Development Act of 2024" and "...Appropriations Act, 2026" one run.
_YEAR = re.compile(r"(19|20)\d{2}")

# Lanes are read off the cite prefix the reference tables already carry ('cmte:HSAP'/'subcmte:HSAP04'
# vs the bill designator 'hr22') — so name_spans keeps the docs/16 §3 signature and nothing has to
# thread a parallel lane channel through the walk.
_CLASS = {"bill": "official_name", "committee": "institution"}


def _toks(s: str) -> list[str]:
    """Tokenize with the SAME tokenizer that produced the ledger n-grams (non-negotiable: an index
    built by any other tokenizer cannot align with the phrases it must cover. boilerplate.sentences()
    strips commas, which is why 'National Security, Department of State' is windowable as the live
    phrase 'national security department')."""
    out: list[str] = []
    for sent in boilerplate.sentences(s):
        out.extend(sent)
    return out


def _lane(cite: str) -> str:
    return "committee" if cite.startswith(("cmte:", "subcmte:")) else "bill"


@functools.lru_cache(maxsize=16)
def load_index(congress: int) -> dict[str, tuple[tuple[tuple[str, ...], str], ...]]:
    """Cumulative era-scoped index: union of congresses 108..congress (ANACHRONISM GUARD — a 2015
    phrase is never suppressed by a 2025 bill). Keyed by first token, longest-first; each entry is
    (name tokens, cite).

    Tables are read ascending so the EARLIEST congress to name a thing keeps the cite. The committee
    roster is era-blind (congress-legislators ships current+historical in one file with no congress
    key), so that lane is cumulative-only — a narrower guard than the bill lane's, and disclosed
    rather than faked.
    """
    names: dict[str, str] = {}
    for c in range(config.NOMENCLATURE_INDEX_CONGRESS_MIN, congress + 1):
        path = _REF / f"bill-titles-{c}.json"
        if path.exists():
            for name, cite in json.loads(path.read_text(encoding="utf-8"))["names"].items():
                names.setdefault(name, cite)
    cpath = _REF / "committee-names.json"
    if cpath.exists():
        for name, cite in json.loads(cpath.read_text(encoding="utf-8"))["names"].items():
            names.setdefault(name, cite)

    idx: dict[str, list[tuple[tuple[str, ...], str]]] = {}
    for name, cite in names.items():
        toks = tuple(name.split())
        idx.setdefault(toks[0], []).append((toks, cite))
    # Longest-first per bucket so the greedy walk below can take the first match it finds.
    return {k: tuple(sorted(v, key=lambda e: -len(e[0]))) for k, v in idx.items()}


def name_spans(toks: list[str], idx) -> list[tuple[int, int, str]]:
    """Greedy longest-match walk. Returns INCLUSIVE runs (r0, r1, cite), non-overlapping, in order.
    Absorbs an optional trailing 'of YYYY' or bare 'YYYY' after a matched name.

    MUST NOT accept a `party` argument (Article IV).
    """
    t = tuple(toks)
    L = len(t)
    runs: list[tuple[int, int, str]] = []
    i = 0
    while i < L:
        hit = None
        for name, cite in idx.get(t[i], ()):
            n = len(name)
            if t[i:i + n] == name:
                hit = (i + n - 1, cite)
                break               # entries are longest-first, so the first match IS the longest
        if hit is None:
            i += 1
            continue
        r1, cite = hit
        j = r1 + 1
        if j + 1 < L and t[j] == "of" and _YEAR.fullmatch(t[j + 1]):
            r1 = j + 1
        elif j < L and _YEAR.fullmatch(t[j]):
            r1 = j
        runs.append((i, r1, cite))
        i = r1 + 1
    return runs


def _anchor(ptoks: list[str], i: int) -> int:
    """Doc index of the phrase's FIRST CONTENT TOKEN, given the phrase's tokens and its start `i`.

    Leading STOPWORDS may fall outside a span (a leading article is a member referring to a name);
    a TRAILING modal starts a predicate, so only the LEFT edge moves.
    REGRESSION (docs/16 §3): 'would' IS in boilerplate.STOPWORDS — a rule that ignored all stopwords
    would score 'the save act would' at 1.00 TAG, a false positive on this item's own acceptance case.
    """
    for k, tok in enumerate(ptoks):
        if tok not in boilerplate.STOPWORDS:
            return i + k
    return i


def _classify(toks, i: int, n: int, runs) -> tuple[str | None, str | None]:
    """classify_occ + the cite of the run that licensed it (build_verdicts needs the receipt)."""
    a = _anchor(toks[i:i + n], i)
    b = i + n - 1
    fallback = None
    for r0, r1, cite in runs:
        if r1 < a or r0 > b:
            continue                                        # disjoint
        if r0 <= a and b <= r1:
            return "A", cite                                # containment wins outright
        if (r0 < a <= r1 < b) or (a < r0 <= b < r1):
            fallback = fallback or ("B", cite)              # an edge cuts INSIDE the run
        # run strictly inside the phrase (a < r0 and r1 < b) -> PREDICATION: keep looking, never tag
    return fallback or (None, None)


def classify_occ(toks, i, n, runs) -> str | None:
    """'A' containment | 'B' truncation | None.
    A: r0 <= a and b <= r1                       -> the phrase IS the name / a clean window
    B: (r0 < a <= r1 < b) or (a < r0 <= b < r1)  -> the phrase edge cuts INSIDE the run
    run strictly inside the phrase (a < r0 and r1 < b) -> None (PREDICATION: the message).

    That last line is the whole design: it is what lets "the SAVE Act would gut Medicaid" survive.
    """
    return _classify(toks, i, n, runs)[0]


@functools.lru_cache(maxsize=16)
def _verdicts(congress: int) -> dict:
    path = _REF / f"verdicts-{congress}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def index_version(congress: int | None = None) -> str | None:
    """The index_version stamped on the verdicts table (the reference-data snapshot the tagger reads).
    ops.thresholds_sha folds this in WHEN the tagger is live (docs/19 §2a), so the daily symmetry
    fingerprint reflects which name index shaped the output. Defaults to the highest congress that has
    a verdicts table. Returns None when no table is present (dark box / fresh checkout)."""
    if congress is None:
        cands = sorted(int(p.stem.split("-")[1]) for p in _REF.glob("verdicts-*.json")
                       if p.stem.split("-")[1].isdigit())
        if not cands:
            return None
        congress = cands[-1]
    return (_verdicts(congress) or {}).get("index_version")


def is_nomenclature(ngram: str, congress: int) -> dict | None:
    """verdicts-{congress}.json lookup. Returns {'ratio','lane','cite','class','docs','nom_docs',
    'rule','index_version'} or None. MUST NOT accept a `party` argument (Article IV).

    The verdict is a doc-level MEASUREMENT over the real corpus, never a property of the string:
    ratio = docs where EVERY occurrence is covered / docs containing the phrase. The threshold is
    applied here, not baked into the table, so NOMENCLATURE_RATIO_MIN stays the disclosed knob
    docs/16 §8.4 requires (it measured 'transportation and infrastructure' at 0.802 — one thousandth
    above it — so the threshold does delicate work and must stay movable without a rebuild).
    """
    table = _verdicts(congress)
    row = (table.get("verdicts") or {}).get(" ".join((ngram or "").split()))
    if not row or row["ratio"] < config.NOMENCLATURE_RATIO_MIN:
        return None
    return {**row, "class": _CLASS[row["lane"]], "index_version": table.get("index_version")}


def tag(rows: list, key: str = "ngram", congress: int | None = None) -> list:
    """Attach row['nomenclature'] in place; NEVER drops a row. Mirrors crec_boilerplate.suppress()'s
    display-time API shape, but tags instead of suppressing.

    TAG, NEVER DELETE is not a style preference (docs/16 §7): wiring tag->suppress is a live Article
    IV defect in BOTH directions — it would delete either the 113-R OBBBA flagship or the 55-D
    counter-brand. Every row comes back; the caller decides what a tagged row means.
    """
    for row in rows:
        c = congress if congress is not None else row.get("congress")
        if c is None:
            continue
        verdict = is_nomenclature(row.get(key) or "", int(c))
        if verdict:
            row["nomenclature"] = verdict
    return rows
