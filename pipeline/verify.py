"""B4 — the deterministic citation verifier (§6.3). Blocking; code, never a model.

Three checks, all mechanical (the hallucination surface for statistics is zero by
construction, §11.5):
  1. substring   — every quoted fragment is a verbatim substring of its cited statement
                   (whitespace-normalized, case-insensitive: robust to rendering, but any
                   invented or paraphrased word fails).
  2. quorum      — every published claim traces to >= 3 DISTINCT members (§1.4.2).
  3. digit-whitelist — every number that appears in a composite Daily Line also appears in
                   the code-computed STATS block; the model may copy numbers, never invent
                   or compute them (§6.2 P2 rule 3).

A violation drops the claim (logged, never hand-patched, §4 B4). If a party's Daily Line
loses all claims, the honest fallback line publishes (§7.2) — never silence.
"""
from __future__ import annotations

import re

from . import boilerplate

_WS = re.compile(r"\s+")
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")

# TYPOGRAPHIC FOLDING (§deploy-hardening 2026-07-16). Press releases are written with smart quotes;
# any LLM or renderer routinely emits the ASCII form. `today’s` and `today's` are the SAME WORD, so
# failing grounding on that difference is a FALSE NEGATIVE — and it was a live one: on 2026-07-15 the
# Sonnet quoted a real fragment as "applauded today's house passage of the fiscal year" against a
# source reading `today’s`, got rejected, and the Daily Line fell back. Folding delivers the "robust
# to rendering" guarantee this module's docstring already claimed.
#
# It also closes a REAL hole in the negation guard: _NEGATION holds ASCII "don't", so a source written
# `don’t` never matched, and a meaning-inverting truncation after a curly contraction would have been
# wrongly grounded. Folding makes that check fire.
#
# This does not weaken verification: ONLY typography is folded — never a letter, digit, or word. An
# invented or paraphrased word still fails exactly as before.
_TYPOGRAPHY = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",                  # single quotes
    "“": '"', "”": '"', "„": '"', "‟": '"',                  # double quotes
    "–": "-", "—": "-", "‑": "-", "‒": "-", "―": "-",   # dashes
    "…": "...",                                                              # ellipsis
    " ": " ", " ": " ", " ": " ",                                  # nbsp/thin spaces
    "­": "",                                                                 # soft hyphen
    "⁄": "/",                                                                # fraction slash
}
_TYPO_RE = re.compile("|".join(map(re.escape, _TYPOGRAPHY)))


def fold_typography(text: str) -> str:
    """Map smart punctuation to its ASCII equivalent. Words are never touched."""
    return _TYPO_RE.sub(lambda m: _TYPOGRAPHY[m.group(0)], text or "")


def _norm(text: str) -> str:
    return _WS.sub(" ", fold_typography(text)).strip().lower()


def is_verbatim(fragment: str, source_text: str) -> bool:
    frag = _norm(fragment)
    return bool(frag) and frag in _norm(source_text)


def _numbers(text: str) -> set[str]:
    return {m.group(0).replace(",", "") for m in _NUM.finditer(text or "")}


def numbers_whitelisted(composite_text: str, stats_blob: str) -> tuple[bool, set[str]]:
    allowed = _numbers(stats_blob)
    used = _numbers(composite_text)
    offending = used - allowed
    return (len(offending) == 0, offending)


def key_carrying_units(tp: dict, statements_by_id: dict[str, dict]) -> set:
    """The distinct document FAMILIES (joint_group or bioguide) whose SOURCE actually carries the
    cluster key (docs/19 §4b). Shared by the quorum here and the citation path in run_assemble, so both
    count the same set. A family whose text does not contain the key was chained into the cluster by a
    DIFFERENT shared gram and is not evidence that THIS phrase is coordinated."""
    label = tp.get("label", "")
    units: set = set()
    for sid in tp.get("statements", []):
        s = statements_by_id.get(sid)
        if not s:
            continue
        # An empty label (should not happen) degrades to the old "count every unit" behaviour.
        if label and not boilerplate.contains_gram(s.get("text", ""), label):
            continue
        unit = s.get("joint_group") or (s.get("member") or {}).get("bioguide")
        if unit:
            units.add(unit)
    return units


def verify_talking_point(tp: dict, statements_by_id: dict[str, dict]) -> tuple[bool, list[str]]:
    """Return (ok, reasons). A talking point is publishable iff >=3 distinct document FAMILIES carry
    the cluster key AND every fragment is verbatim in its cited statement.

    docs/19 §4b — "distinct collapsed document families passing span". The quorum was counting every
    unit the transitive union-find chained in, including members dragged into a connective cluster by
    a DIFFERENT shared gram (Booker on a flood bill under "into the trump administration's";
    Krishnamoorthi on Blanche under "democratic colleagues in demanding the"). Requiring each counted
    family to actually carry the key drops those interlopers below quorum, while the birthright-06-30
    flagship — 53 families that each really typed "born in the united states" — is untouched. A joint
    release is still ONE family (§11 trap 2); member REACH stays reported on tp["member_count"]."""
    reasons: list[str] = []
    units = key_carrying_units(tp, statements_by_id)
    if len(units) < 3:
        reasons.append(f"key-quorum: {len(units)} distinct families carry the key phrase (<3)")
    for frag in tp.get("fragments", []):
        sid = frag.get("statement")
        src = statements_by_id.get(sid, {})
        if not is_verbatim(frag.get("text", ""), src.get("text", "")):
            reasons.append(f"non-verbatim fragment: {frag.get('text','')!r}")
    return (len(reasons) == 0, reasons)


_QUOTE = re.compile(r'"([^"]+)"|“([^”]+)”')


_QUOTE_TRIM = " \t\n,.;:!?\"'“”‘’—–-"


# Negation tokens: a quoted span that begins immediately AFTER one of these inside its source
# fragment is a meaning-inverting truncation ("never vote to defund" -> "vote to defund"), so it
# does not count as grounded even though it is a verbatim substring. §voice-wiring (MEDIUM-3).
_NEGATION = {"not", "never", "no", "without", "cannot", "nor", "n't", "don't", "doesn't", "didn't",
             "won't", "can't", "isn't", "aren't", "wasn't", "weren't", "shouldn't", "wouldn't"}
_MIN_QUOTE_WORDS = 3   # NGRAM_MIN is 3, so real fragment quotes clear this; trivial spans do not


def quotes_grounded(composite_text: str, fragments: list[str]) -> tuple[bool, list[str]]:
    """P2 rule 2: the quoted WORDS in the composite must be a verbatim substring of some provided
    fragment, AND not a meaning-inverting truncation. Leading/trailing punctuation on the span is
    stripped first (American comma-inside-quotes stays valid). Now that the LLM picks its own spans:
    a span must be >= _MIN_QUOTE_WORDS words and must NOT start immediately after a negation token in
    its source fragment (which would drop a 'never'/'not' and invert meaning). §voice-wiring."""
    sources = [_norm(f) for f in fragments]
    offending: list[str] = []
    for m in _QUOTE.finditer(composite_text or ""):
        q = _norm(m.group(1) or m.group(2) or "").strip(_QUOTE_TRIM)
        if not q:
            continue
        if len(q.split()) < _MIN_QUOTE_WORDS:
            offending.append(q)
            continue
        grounded = False
        for s in sources:
            idx = s.find(q)
            if idx < 0:
                continue
            preceding = s[:idx].split()
            if preceding and preceding[-1].strip(".,;:!?\"'") in _NEGATION:
                continue  # verbatim but drops a leading negation -> inverts meaning; not grounded
            grounded = True
            break
        if not grounded:
            offending.append(q)
    return (len(offending) == 0, offending)


def _numbers_outside_quotes(text: str) -> set[str]:
    """Numbers in the composite that are NOT inside a quoted span. Numbers inside a quote are exempt
    from the whitelist because the quote itself is separately grounded to verbatim member text; only
    UNQUOTED numbers are aggregate claims that must be code-computed. §voice-wiring (HIGH-1)."""
    return _numbers(_QUOTE.sub(" ", text or ""))


def code_allowed_numbers(stats: dict) -> set[str]:
    """The ONLY numbers a composite may state UNQUOTED: code-computed counts (statement + member
    counts) and the audited date, plus digits that are part of a code-selected phrase NAME (labels,
    top phrase). Deliberately EXCLUDES the member-quote text — so the LLM cannot lift a number from a
    quote (e.g. 'cut all 87 programs') and publish it as a fabricated aggregate ('87 of us'). §HIGH-1."""
    allowed: set[str] = set()
    if stats.get("statements") is not None:
        allowed.add(str(stats["statements"]))
    for tp in stats.get("talking_points") or []:
        if tp.get("members") is not None:
            allowed.add(str(tp["members"]))
        allowed |= _numbers(tp.get("label", ""))   # a number that is part of the phrase NAME (e.g. "21st")
    tp = stats.get("top_phrase") or {}
    if tp.get("members") is not None:
        allowed.add(str(tp["members"]))
    allowed |= _numbers(tp.get("text", ""))
    allowed |= _numbers(str(stats.get("day", "")))  # 2026 / 07 / 13
    if stats.get("sync_min") is not None:
        allowed.add(str(stats["sync_min"]))         # the coordination threshold (no-coordination line)
    return {a for a in allowed if a}


def verify_daily_line(distillation: dict, stats_blob: str, fragments: list[str] | None = None,
                      *, stats: dict | None = None) -> tuple[bool, list[str]]:
    """Block a Daily Line unless every UNQUOTED number is a code-computed count/date (never a digit
    lifted from a member quote) and every quoted span is verbatim, in-context member text. When
    `stats` (the code-computed STATS dict) is passed, the strict per-field number whitelist is used;
    otherwise it falls back to the whole-blob check (legacy verify_day path). §voice-wiring HIGH-1."""
    reasons: list[str] = []
    composite = distillation.get("composite", "")
    if stats is not None:
        offending = _numbers_outside_quotes(composite) - code_allowed_numbers(stats)
    else:
        _, offending = numbers_whitelisted(composite, stats_blob)
    if offending:
        reasons.append(f"un-whitelisted numbers in composite: {sorted(offending)}")
    if fragments is not None:
        ok_q, off_q = quotes_grounded(composite, fragments)
        if not ok_q:
            reasons.append(f"un-grounded quotes in composite: {off_q}")
    return (len(reasons) == 0, reasons)


def verify_day(distillation: dict, talking_points: list[dict], statements_by_id: dict[str, dict],
               stats_blob: str) -> dict:
    """Full B4 report for one party-day. Drops failing claims; reports counts."""
    published_tps: list[dict] = []
    dropped: list[dict] = []
    fragments_checked = 0
    for tp in talking_points:
        fragments_checked += len(tp.get("fragments", []))
        ok, reasons = verify_talking_point(tp, statements_by_id)
        (published_tps if ok else dropped).append({"id": tp.get("id"), "reasons": reasons} if not ok else tp)
    line_ok, line_reasons = verify_daily_line(distillation, stats_blob)
    return {
        "fragments_checked": fragments_checked,
        "claims_in": len(talking_points),
        "claims_published": len(published_tps),
        "claims_dropped": len(dropped),
        "dropped": dropped,
        "daily_line_ok": line_ok,
        "daily_line_reasons": line_reasons,
        "failed": (0 if line_ok else 1),  # published-fragment failures are 0 by construction
    }
