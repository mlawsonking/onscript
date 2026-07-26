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

from . import boilerplate, contracts

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
        # Every published talking point has one support phrase. An empty label carries no support;
        # it never degrades to counting the transitive component.
        if not label or not boilerplate.contains_gram(s.get("text", ""), label):
            continue
        unit = s.get("joint_group") or (s.get("member") or {}).get("bioguide")
        if unit:
            units.add(unit)
    return units


def claim_invariant_failures(tp: dict, statements_by_id: dict[str, dict], *,
                             require_citations: bool = False) -> list[str]:
    """Return failures for the six schema-2 claim invariants."""
    failures: list[str] = []
    claim_id = tp.get("claim_id")
    if (tp.get("schema_version") != contracts.SCHEMA_VERSION
            or tp.get("object_type") != contracts.CLAIM_TYPE
            or not claim_id or claim_id != tp.get("id")):
        failures.append("identity")

    support = tp.get("support_phrase") or {}
    phrase = tp.get("label") or ""
    if (not phrase or support.get("normalized") != phrase or not support.get("text")
            or not support.get("occurrence_id")):
        failures.append("support_phrase")

    occurrences = [row for row in (tp.get("occurrences") or []) if isinstance(row, dict)]
    occurrences_by_id = {row.get("occurrence_id"): row for row in occurrences
                         if row.get("occurrence_id")}
    offsets_ok = bool(occurrences)
    for row in occurrences:
        statement = statements_by_id.get(row.get("statement_id")) or {}
        source = statement.get("text") or ""
        start, end = row.get("start_char"), row.get("end_char")
        if (not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start
                or end > len(source) or source[start:end] != row.get("surface_text")
                or row.get("normalized_phrase") != phrase
                or not boilerplate.contains_gram(row.get("surface_text") or "", phrase)):
            offsets_ok = False
            break
    if not offsets_ok:
        failures.append("occurrence_offsets")

    occurrence_statements = {row.get("statement_id") for row in occurrences if row.get("statement_id")}
    if occurrence_statements != set(tp.get("statements") or []):
        failures.append("support_set")

    expected_counts = {
        "offices": len({row.get("office_id") for row in occurrences if row.get("office_id")}),
        "publications": len({row.get("publication_id") for row in occurrences if row.get("publication_id")}),
        "families": len({row.get("family_id") for row in occurrences if row.get("family_id")}),
        "support_units": len({row.get("support_unit_id") for row in occurrences
                              if row.get("support_unit_id")}),
    }
    counts = tp.get("counts") or {}
    ids_ok = (
        set(tp.get("office_ids") or [])
        == {row.get("office_id") for row in occurrences if row.get("office_id")}
        and set(tp.get("publication_ids") or [])
        == {row.get("publication_id") for row in occurrences if row.get("publication_id")}
        and set(tp.get("family_ids") or [])
        == {row.get("family_id") for row in occurrences if row.get("family_id")}
        and set(tp.get("support_unit_ids") or [])
        == {row.get("support_unit_id") for row in occurrences if row.get("support_unit_id")}
    )
    if counts != expected_counts or tp.get("member_count") != expected_counts["support_units"] or not ids_ok:
        failures.append("unit_counts")

    quote_occurrence = occurrences_by_id.get(support.get("occurrence_id"))
    render_ok = bool(
        quote_occurrence
        and support.get("text") == quote_occurrence.get("surface_text")
        and tp.get("display_quote") == support.get("text")
    )
    if require_citations:
        citations = [row for row in (tp.get("citations") or []) if isinstance(row, dict)]
        citation_ids = tp.get("citation_occurrence_ids") or []
        render_ok = render_ok and len(citations) >= 3 and citation_ids == [
            row.get("occurrence_id") for row in citations
        ]
        for citation in citations:
            occurrence = occurrences_by_id.get(citation.get("occurrence_id"))
            if (not occurrence or citation.get("publication_id") != occurrence.get("publication_id")
                    or not boilerplate.contains_gram(citation.get("quote") or "", phrase)):
                render_ok = False
                break
    if not render_ok:
        failures.append("render_binding")
    return failures


def verify_talking_point(tp: dict, statements_by_id: dict[str, dict], *,
                         require_contract: bool = False,
                         require_citations: bool = False) -> tuple[bool, list[str]]:
    """Return (ok, reasons). A talking point is publishable iff >=3 distinct document FAMILIES carry
    the cluster key AND every fragment is verbatim in its cited statement.

    docs/28 overrules the old component-reach display. ``member_count`` is now exactly the number of
    joint-aware units that carry the support phrase; a mismatch is a blocking verification failure.
    A joint release remains one family (§11 trap 2)."""
    reasons: list[str] = []
    units = key_carrying_units(tp, statements_by_id)
    if len(units) < 3:
        reasons.append(f"key-quorum: {len(units)} distinct families carry the key phrase (<3)")
    if tp.get("member_count") != len(units):
        reasons.append(
            f"support-count: stored {tp.get('member_count')!r} != {len(units)} distinct families carrying the key"
        )
    for frag in tp.get("fragments", []):
        sid = frag.get("statement")
        src = statements_by_id.get(sid, {})
        if not is_verbatim(frag.get("text", ""), src.get("text", "")):
            reasons.append(f"non-verbatim fragment: {frag.get('text','')!r}")
    if require_contract:
        reasons.extend(
            f"claim-invariant:{name}"
            for name in claim_invariant_failures(tp, statements_by_id,
                                                 require_citations=require_citations)
        )
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


def quotes_bound_to_talking_points(composite_text: str, stats: dict) -> tuple[bool, list[str]]:
    """Bind every composite quote to one STATS talking point and that point's support phrase.

    A quote merely appearing somewhere in the day's combined fragment pool is not evidence for the
    count beside it. The quote must be a grounded span of that talking point's own supplied quote and
    must visibly carry its support phrase. When the sentence uses the deterministic ``N of us`` form,
    the nearest preceding N must equal the bound talking point's support-unit count.
    """
    offending: list[str] = []
    tps = [tp for tp in (stats.get("talking_points") or []) if isinstance(tp, dict)]
    text = composite_text or ""
    for match in _QUOTE.finditer(text):
        raw = match.group(1) or match.group(2) or ""
        q = _norm(raw).strip(_QUOTE_TRIM)
        if not q:
            continue
        bound: list[dict] = []
        for tp in tps:
            label = tp.get("label") or ""
            supplied = tp.get("quote") or ""
            if not label or not boilerplate.contains_gram(q, label):
                continue
            grounded, _ = quotes_grounded(f'"{raw}"', [supplied])
            if grounded:
                bound.append(tp)
        if not bound:
            offending.append(raw)
            continue

        sentence_start = max(text.rfind(".", 0, match.start()), text.rfind("?", 0, match.start()),
                             text.rfind("!", 0, match.start())) + 1
        prefix = text[sentence_start:match.start()]
        count_matches = list(re.finditer(r"(\d[\d,]*)\s+of\s+us\b", prefix, re.I))
        if count_matches:
            claimed = int(count_matches[-1].group(1).replace(",", ""))
            if all(tp.get("members") != claimed for tp in bound):
                offending.append(f"{raw} [count {claimed} is not its support count]")
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
    if stats is not None:
        ok_q, off_q = quotes_bound_to_talking_points(composite, stats)
        if not ok_q:
            reasons.append(f"unbound talking-point quotes: {off_q}")
        if stats.get("schema_version") == contracts.SCHEMA_VERSION:
            known_ids = set(stats.get("claim_ids") or [])
            typed = [tp for tp in (stats.get("talking_points") or []) if isinstance(tp, dict)]
            if (any(tp.get("claim_type") != contracts.CLAIM_TYPE
                    or tp.get("claim_id") not in known_ids for tp in typed)
                    or known_ids != {tp.get("claim_id") for tp in typed}):
                reasons.append("typed claim IDs are missing or inconsistent")
            mapping = contracts.sentence_claims(composite, stats)
            quoted_sentences = {
                index for index, sentence in enumerate(contracts.sentence_parts(composite))
                if _QUOTE.search(sentence)
            }
            mapped = {row["sentence_idx"] for row in mapping if len(row["claim_ids"]) == 1}
            if quoted_sentences != mapped or any(len(row["claim_ids"]) > 1 for row in mapping):
                reasons.append("each quoted sentence must map to exactly one typed claim")
            allowed_quotes = {_norm(tp.get("quote") or "") for tp in typed if tp.get("quote")}
            rendered_quotes = {
                _norm(match.group(1) or match.group(2) or "")
                for match in _QUOTE.finditer(composite)
            }
            if rendered_quotes - allowed_quotes:
                reasons.append("the counted phrase must be the only quoted phrase")
    elif fragments is not None:
        # Legacy verifier entry points without structured STATS retain ordinary verbatim grounding.
        # The production Daily Line always supplies STATS and therefore cannot use a combined pool.
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
