"""CREC boilerplate suppressor (docs/15 §D4 gate). The Congressional Record is a WEAK CARRIER for
message coordination: its text is dense with parliamentary procedure, recognition/yielding formulas,
and bill-title language that a naive n-gram counter reads as 'coordination' (R1; confirmed on real
congress-107 data, docs/15 §9 amend D1-A — the loudest 'coordination' was the Committee-of-the-Whole
formula). This is the genre-specific suppression layer EVERY crec-lane coordination metric must pass an
n-gram through — the analogue of the press spine's boilerplate guard, but heavier. **No crec
coordination card publishes without it.**

Precision over recall by design: the seeds/formulas target UNAMBIGUOUS procedural + high-precision
bill-title furniture; substantive noun-phrase talking points ('birthright citizenship', a named act,
'the death tax') survive. Full bill-title coverage (all sub-grams of every enacted title) is the
SEPARATE nomenclature-segregation item (a congress.gov bill-title corpus); this layer handles the
procedural formulas + the recognition/yielding seeds + the high-precision bill-title markers. The seed
lists live in data/reference/deep/crec_boilerplate_seeds.json (versioned, dated-amendments-only).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_REF = Path(__file__).resolve().parents[2] / "data" / "reference" / "deep" / "crec_boilerplate_seeds.json"


@lru_cache(maxsize=1)
def _seeds():
    d = json.loads(_REF.read_text(encoding="utf-8"))
    return (tuple(tuple(f.lower().split()) for f in d.get("procedural_formulas", [])),
            tuple(tuple(s.lower().split()) for s in d.get("phrase_seeds", [])),
            tuple(tuple(s.lower().split()) for s in d.get("bill_title_seeds", [])),
            frozenset(p.lower() for p in d.get("protected_phrases", [])))


def _run_in(hay: tuple, needle: tuple) -> bool:
    """True iff `needle` is a contiguous token sub-run of `hay`. Token-level (not substring) so a seed
    never matches inside a word and a phrase merely SHARING words with a formula is not caught."""
    n, h = len(needle), len(hay)
    if n == 0 or n > h:
        return False
    return any(hay[i:i + n] == needle for i in range(h - n + 1))


def is_crec_boilerplate(ngram: str) -> bool:
    """True iff `ngram` is Congressional-Record procedural/bill-title furniture that must be excluded
    from a coordination metric. Three precise rules:
      1. the ngram is a contiguous sub-run of a procedural formula (Committee-of-the-Whole etc.);
      2. the ngram CONTAINS a recognition/yielding seed ('mr speaker', 'i yield back', 'the gentleman
         from', 'in the house of representatives' — the Extensions header furniture);
      3. the ngram CONTAINS high-precision bill-title language ('and for other purposes', 'to provide
         for', 'to amend the', …).
    A substantive noun-phrase talking point matches none of these and survives."""
    toks = tuple(ngram.lower().split())
    if not toks:
        return False
    formulas, phrase_seeds, bill_seeds, protected = _seeds()
    # rule 1: the ngram is a contiguous sub-run of a procedural formula (catches EVERY fragment of the
    # long Committee-of-the-Whole formula) UNLESS it is a protected real phrase. The only substantive
    # phrase embedded in the procedural formulas is "state of the union" (the SOTU) + its variants —
    # whitelisted so the SOTU survives while "the state of the union had" / "on the state of the union"
    # (procedural connective tissue) are suppressed.
    if " ".join(toks) not in protected and any(_run_in(f, toks) for f in formulas):
        return True
    if any(_run_in(toks, s) for s in phrase_seeds):    # rule 2: a recognition/yielding/committee seed ⊆ ngram
        return True
    if any(_run_in(toks, s) for s in bill_seeds):      # rule 3: bill-title language ⊆ ngram
        return True
    return False


def suppress(rows, key: str = "ng"):
    """Drop CREC boilerplate from a list of phrase rows (dicts keyed by `key`, or bare strings).
    Display/analysis-time, exactly like the press spine's boilerplate guard — the ledger keeps every
    n-gram; this filters what a coordination view is allowed to surface."""
    def ng(r):
        return r[key] if isinstance(r, dict) else r
    return [r for r in rows if not is_crec_boilerplate(ng(r))]
