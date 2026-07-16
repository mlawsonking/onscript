"""1.7a — The Duet: the same phrase, both parties, the same day (VISION A5, BUILD-PROGRAM 1.7).

Built dark behind FEATURES["duet"]; the data lands in the day JSON either way, only the render is gated.

WHAT IT SHOWS, AND WHAT IT REFUSES TO SAY
-----------------------------------------
The vision line reads "same phrase, both parties, same day, **opposite intent** -> automatic
side-by-side". We build every word of that EXCEPT the intent claim. "Opposite intent" is a verdict
about what people MEANT, and this instrument does not read minds (Constitution: citation-or-silence,
no verdict). So the Duet places each party's OWN verbatim sentence side by side under the shared
phrase and stops talking. When the framing really is opposed, the reader sees it in the two sentences
without us asserting it; when it is not opposed (both parties touting the same bill), the exhibit is
honest anyway — that is a shared-vocabulary fact, not a failure.

This also keeps the Duet clear of the nomenclature problem (CLAUDE.md: bill titles are not
coordination). A duet on "water resources development act" is not a claim that anybody coordinated —
it is two parties using one name. We never call a duet coordination.

SYMMETRY BY CONSTRUCTION (Article III)
--------------------------------------
ONE threshold (config.SYNC_MIN_MEMBERS) is applied to BOTH parties, and the ranking metric is
min(D, R) — a party-invariant function. Swap the party labels in the input and the output is
identical but for the labels; `tests/test_duet.py` proves it by actually swapping them. Nothing here
is rate-normalized: an asymmetric corpus is allowed to produce asymmetric findings, and a party that
simply never joins a phrase never appears — that is a real fact about the day, not a bug.

QUOTES ARE NEVER TRUNCATED MID-SENTENCE
---------------------------------------
Each side's quote is a COMPLETE sentence from a member's own statement, verbatim. We never clip a
sentence to fit: the verifier already carries a negation guard because a clipped span inverts meaning
("...a bill I will never support" -> "...a bill I will"), and a trailing clip is exactly that failure
in display clothing. A too-long sentence loses to a shorter one from another member; it is never cut.
The phrase itself is a CODE-COMPUTED ledger n-gram, so it is rendered UNQUOTED — quoting it would
misattribute a computed string to a member (HIGH-1; the same rule P2 v1.2 carries).
"""
from __future__ import annotations

import re

from . import boilerplate, build, config, verify

# The duet bar: BOTH parties must independently clear the SAME synchronization threshold that a
# single-party phrase must clear to be called synchronized at all. Not a new knob (§13) — the
# existing one, applied twice.
DUET_MIN_MEMBERS = config.SYNC_MIN_MEMBERS

# Duets are rare and event-driven ("when it happens", VISION §post types): real days range from 0
# (2026-07-08) to a few (2026-06-30, a SCOTUS decision day). A small cap keeps the exhibit an exhibit.
DUET_MAX_PER_DAY = 5

# Per-side citation target: the >=3-unit quorum the rest of the instrument uses (§1.4.2).
DUET_CITES_PER_SIDE = 3

# A quote longer than this is a paragraph, not a pull-quote. We SKIP such a candidate and try another
# member rather than truncate it (see module docstring). If no member has a shorter sentence, the
# full sentence still publishes — complete and verbatim beats short and inverted.
QUOTE_MAX_CHARS = 320

# Split on sentence ends OR paragraph breaks. Press releases put the dateline/header and the member's
# actual words in separate blocks with no terminal punctuation between them ("...decision:\n\n\"The
# ..."), so splitting on [.!?] alone runs the header into the quote. Splitting MORE finely is always
# safe here: every candidate is still a contiguous substring of the source, and each one is
# re-checked against the verifier before it can be displayed.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

# Release MECHANICS — the wrapper a press office puts around the message ("WASHINGTON — Rep. X
# released the following statement..."). A sentence that is furniture is not that member's message,
# so it loses to a real one.
#
# Deliberately NARROW, and deliberately NOT boilerplate._NGRAM_BOILERPLATE_RE: that list is tuned for
# suppressing n-grams on the engine's hot path, where it can afford to be blunt (it rejects any n-gram
# containing "washington", a year, or "senator"). Applied to whole SENTENCES it would reject most real
# political speech — "The 2026 budget guts Medicaid" mentions a year; "Senator Smith is wrong" names a
# senator. So the Duet keeps its own list, scoped to release plumbing only. §1.7.
_FURNITURE = re.compile(
    r"\b(issued|released|made|delivered) the following\b"
    r"|\bfollowing statement\b|\bstatement below\b"
    r"|\bfor immediate release\b"
    r"|\breleased? (a|the) (following )?statement\b"
    r"|\b(read|watch|view) (the )?(full|more)\b",
    re.IGNORECASE,
)

# A dateline-headed segment ("WASHINGTON, D.C. — ...") is a header, not speech.
_DATELINE_HEAD = re.compile(r"^\s*[A-Z][A-Za-z.\s]{2,30},?\s*(D\.?C\.?)?\s*[–—-]\s")

_POSSESSIVE = re.compile(r"['’]s$")

# --- speaker attribution ------------------------------------------------------------------------
# A press release is a MULTI-SPEAKER document: a release from Castro's office carries quotes from
# Castro, Houlahan AND Cisneros. "Verbatim in the document" therefore does NOT mean "this member said
# it" — and the deterministic verifier only checks the former (is_verbatim finds the string in the
# cited statement's text; it has no notion of who was speaking). Without this gate the Duet published
# Rep. Cisneros's sentence ("I'm proud to support my colleagues, Congressman Castro and Congresswoman
# Houlahan...") as BOTH Castro's and Houlahan's own words — a real misattribution found on real data
# (2026-06-30), and precisely the failure the citation promise exists to prevent (Article XII).
#
# So: a sentence is attributable to the release's member only if the nearest attribution marker BEFORE
# it names that member (or there is no marker before it — the lead/their own quote). Anything inside
# another member's quoted block is rejected.
_TITLE = r"(?:Rep\.|Sen\.|Reps\.|Sens\.|Representative|Senator|Congressman|Congresswoman|Dr\.|Mr\.|Ms\.|Mrs\.|Leader|Whip|Chairman|Chairwoman|Chair)"
_NAME = r"[A-Z][A-Za-z.'’\-]+(?:\s+[A-Z][A-Za-z.'’\-]+){0,3}"
_SAY = r"(?:said|says|stated|added|continued|concluded|noted|wrote)"
_ATTRIB = re.compile(
    rf"\b{_SAY}\s+(?:{_TITLE}\s+)?({_NAME})"      # "said Rep. Cisneros"
    rf"|\b(?:{_TITLE}\s+)({_NAME})\s+{_SAY}\b",   # "Rep. Cisneros said"
)


def _surname(name: str) -> str:
    """Last alphabetic token of a roster name ("J. Correa" -> "correa"). Roster names are
    "First Last"; the surname is the token an attribution marker will carry."""
    toks = [t for t in re.split(r"[\s.]+", (name or "").strip()) if t.isalpha()]
    return toks[-1].lower() if toks else ""


def _marker_name(m: re.Match) -> str:
    return (m.group(1) or m.group(2) or "").lower()


def _names_in(marker: str) -> set[str]:
    """The marker's name TOKENS. Token equality, never substring: 'Smith' must not be considered the
    speaker of a block attributed to 'Smithson'."""
    return {t.strip(".,'’-") for t in marker.split() if t.strip(".,'’-")}


def attributed_to_other(text: str, start: int, end: int, speaker: str) -> bool:
    """True iff this span belongs to a member other than `speaker`.

    Attribution binds to a quote from EITHER side, and both forms are everywhere in this corpus:
        trailing — `"I'm proud to support...," said Rep. Cisneros.`   (marker INSIDE the span)
        leading  — `said Rep. Cisneros. "I know firsthand..."`         (marker BEFORE the span)
    So both are checked. Reading only backwards (the first cut of this gate) passed the real
    2026-06-30 text — which happens to use the leading form — while silently accepting every
    trailing-attributed quote in the corpus.

    Precedence: a marker INSIDE the span is that span's own attribution and wins. Otherwise the
    nearest marker before it governs. No marker at all => the release's lead or the member's own
    voice => accepted (we do not drop a member's real speech merely for lack of a marker)."""
    if not speaker:
        return False                      # unknown speaker -> nothing to check against
    inside = list(_ATTRIB.finditer(text[start:end] or ""))
    if inside:
        return not any(speaker in _names_in(_marker_name(m)) for m in inside)
    last = None
    for m in _ATTRIB.finditer(text or ""):
        if m.start() >= start:
            break
        last = m
    return last is not None and speaker not in _names_in(_marker_name(last))


def _norm(text: str) -> str:
    """Fold typography + case + whitespace for MATCHING only (never for display). Mirrors the
    verifier's own normalization so a quote we accept here is a quote it accepts there."""
    return verify._norm(text)


# A "." that ends an abbreviation is not a sentence end. Without this, real quotes are guillotined at
# their most-cited moment: "Goodlander previously filed an amicus brief in this case, Trump v." and
# "Senator Capito joined an amicus brief with U.S." are both real output from 2026-06-30. Case names
# ("Trump v. CASA") and "U.S." are everywhere in this corpus, so this is the common path, not an edge.
_ABBREV_END = re.compile(
    r"(?:\b[A-Za-z]|\b(?:v|vs|etc|no|art|sec|fig|st|mt|ft|dr|mr|mrs|ms|jr|sr|rep|reps|sen|sens"
    r"|gov|col|gen|lt|adm|capt|hon|prof|inc|corp|co|ltd|dept|univ"
    r"|jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec))\.$",
    re.IGNORECASE,
)


def _sentence_spans(text: str) -> list[tuple[str, int]]:
    """(sentence, start_offset) over the ORIGINAL text.

    Returns offsets rather than bare strings for two reasons: the speaker gate must know WHERE this
    sentence sits (str.find would return the first identical occurrence, which may be a different
    speaker's block), and a merged abbreviation span must be sliced from the source so the result is
    still an exact substring — not a re-joined approximation."""
    t = text or ""
    spans: list[tuple[str, int]] = []
    start = 0
    for m in _SENT_SPLIT.finditer(t):
        if t[start:m.start()].strip():
            spans.append((t[start:m.start()], start))
        start = m.end()
    if t[start:].strip():
        spans.append((t[start:], start))

    merged: list[tuple[str, int]] = []
    for seg, st in spans:
        if merged and _ABBREV_END.search(merged[-1][0].rstrip()):
            _, prev_start = merged.pop()                 # spurious split: re-slice the WHOLE span
            merged.append((t[prev_start:st + len(seg)], prev_start))
        else:
            merged.append((seg, st))

    out: list[tuple[str, int]] = []
    for seg, st in merged:
        lead = len(seg) - len(seg.lstrip())
        out.append((seg.strip(), st + lead))
    return out


_WRAPPING_QUOTES = " \t\"'“”‘’"


# The release's own attribution tail: `..., " said Congresswoman Goodlander.` Requires a closing quote
# mark before the verb, so an ordinary mid-sentence "said" ("He said the bill is bad") is untouched.
_ATTRIB_TAIL = re.compile(r"[,.]?\s*[\"”’']\s*(?:said|says|stated|added|continued|concluded)\b.*$",
                          re.IGNORECASE)


def _unwrap(sentence: str) -> str:
    """Drop the release's own wrapping quotation marks and trailing attribution tail. A release prints
    the member's words as `"Title IX was established..."` — carrying those delimiters into a quoted UI
    renders `""Title IX...` — and often closes with `," said Rep. X.`, which is the PAPER talking, not
    the member.

    Both edits only ever REMOVE from the ends, so the result stays a substring of the source: the quote
    remains verbatim and the verifier still grounds it. The tail is stripped only when the speaker has
    already been confirmed as this member (quote_for's speaker gate), so nothing is re-attributed."""
    s = _ATTRIB_TAIL.sub("", (sentence or "").strip(_WRAPPING_QUOTES))
    return s.strip(_WRAPPING_QUOTES)


def is_furniture(sentence: str) -> bool:
    """True for release plumbing (dateline headers, 'released the following statement')."""
    return bool(_FURNITURE.search(sentence or "")) or bool(_DATELINE_HEAD.match(sentence or ""))


def quote_for(phrase: str, text: str, speaker: str = "") -> str | None:
    """The member's own COMPLETE sentence containing `phrase`, returned with its ORIGINAL case and
    typography (so it is verbatim to a reader, not just to the matcher). Returns None when the phrase
    never surfaces in a usable sentence — the caller then tries the next member rather than inventing
    one (citation-or-silence).

    Preference order: real speech over furniture, then shortest. The furniture demotion is what stops
    the exhibit from quoting "WASHINGTON — Rep. X released the following statement following the
    Supreme Court's decision" — technically verbatim, and technically not a thing anyone SAID."""
    target = _norm(phrase)
    if not target:
        return None
    # Furniture is REJECTED, never used as a fallback. If a member's release says the phrase only in
    # its own header ("Rep. X released the following statement on the Supreme Court's decision"), that
    # member simply did not say it — we take the next member instead. There is no shortage of members
    # on a real duet day, and a quote nobody uttered is worse than one fewer receipt.
    #
    # `speaker` gates misattribution: a sentence sitting inside a COLLEAGUE's quoted block is that
    # colleague's, however verbatim it is in this member's release.
    pool = []
    for s, at in _sentence_spans(text):
        if target not in _norm(s) or is_furniture(s):
            continue
        if attributed_to_other(text, at, at + len(s), speaker):
            continue
        pool.append(s)
    if not pool:
        return None
    pool.sort(key=len)
    short = [s for s in pool if len(s) <= QUOTE_MAX_CHARS]
    return _unwrap(short[0] if short else pool[0])


def _ends_mid_construction(ngram: str) -> bool:
    """True for a phrase whose LAST token is a function word ("united states and", "court's decision
    in", "united states to") — a span cut out of the middle of a sentence, not a thing anyone would
    say as a unit. On a real duet day these fragments crowd out the actual duets: "united states and"
    scored both=4 by pairing Democrats on birthright citizenship against Republicans on battlefield
    innovation — two parties saying the country's name, presented as a shared phrase.

    Only the TAIL is tested, never the head: n-grams start at NGRAM_MIN=3 tokens, so the shortest real
    form of many phrases legitimately carries a leading article ("the supreme court" — there is no
    2-gram "supreme court" in the ledger to prefer). Rejecting leading stopwords would delete the best
    duet on the board.

    Duet-display-local by design: the sync table's own suppression is deliberately left alone here —
    changing shared thresholds would move published coordination numbers, which is not this feature's
    business (§13)."""
    toks = (ngram or "").split()
    return bool(toks) and toks[-1] in boilerplate.STOPWORDS


def family_key(ngram: str) -> frozenset:
    """The phrase's CONTENT tokens, possessive-normalized ("court's" -> "court"). Two duet rows about
    the same event share these ("the supreme court", "the supreme court's", "supreme court ruled")."""
    return frozenset(_POSSESSIVE.sub("", t) for t in (ngram or "").split()
                     if t not in boilerplate.STOPWORDS)


def topic_disjoint(rows: list[dict], k: int) -> list[dict]:
    """Keep the strongest row per topic: a row is shown only if it shares NO content word with an
    already-kept (higher-ranked) row.

    Why so blunt: on a real SCOTUS day the candidate list is five spellings of one event ("the supreme
    court", "the supreme court's", "supreme court's decision", "today the supreme court", "supreme
    court ruled"). Containment-based merging (what the sync table uses) catches only some of those —
    "statement after the supreme" contains nothing and is contained by nothing, yet it is plainly the
    same event. For a 5-row exhibit, "each duet is about a different word" is a rule a reader can hold
    in their head, and it degrades safely: the LOSER of a merge is always the WEAKER row of a shared
    topic, never a hidden finding — the strongest row of every topic still shows.

    This is display selection, NOT the sync table's collapse: it never relabels or re-attributes a
    phrase, and the ledger keeps every variant. The known cost is that two genuinely different duets
    sharing one content word ("border security" / "national security") show only the stronger; that is
    an acceptable trade for a top-k exhibit and is why this is not used anywhere a claim is counted."""
    kept: list[dict] = []
    used: set = set()
    for r in rows:                       # rows arrive ranked (both, then content-richness)
        key = family_key(r["ngram"])
        if key & used:
            continue
        kept.append(r)
        used |= key
        if len(kept) >= k:
            break
    return kept


def _unit(statement: dict) -> str | None:
    """The citation unit: a joint/delegation release is ONE coordinated document, so it counts once
    toward the quorum (§11 trap 2) — never three members' worth of agreement."""
    m = statement.get("member") or {}
    return statement.get("joint_group") or m.get("bioguide")


def side_citations(phrase: str, party_statements: list[dict], rmap: dict,
                   k: int = DUET_CITES_PER_SIDE) -> list[dict]:
    """Up to k citations for one side of a duet — one per DISTINCT unit, each carrying that member's
    own verbatim sentence. A statement whose text does not actually contain the phrase in a sentence
    contributes nothing (citation-or-silence: we would rather publish no duet than a quote that does
    not say the phrase)."""
    cites: list[dict] = []
    seen: set = set()
    # Deterministic order: shortest quote first would let text length pick the members, so we order by
    # unit id — stable, content-blind, and identical under a party swap.
    for s in sorted(party_statements, key=lambda x: (_unit(x) or "", x.get("id") or "")):
        unit = _unit(s)
        if not unit or unit in seen:
            continue
        m0 = s.get("member") or {}
        name = (rmap.get(m0.get("bioguide"), {}) or {}).get("name") or ""
        q = quote_for(phrase, s.get("text") or "", speaker=_surname(name))
        if not q:
            continue
        # Belt: the displayed quote must survive the SAME verifier the Daily Line answers to.
        if not verify.is_verbatim(q, s.get("text") or ""):
            continue
        seen.add(unit)
        m = s.get("member") or {}
        cites.append({"member": (rmap.get(m.get("bioguide"), {}) or {}).get("name") or m.get("bioguide"),
                      "party": m.get("party"), "state": m.get("state"),
                      "date": s.get("published_at"), "url": s.get("url"), "quote": q})
        if len(cites) >= k:
            break
    return cites


def candidate_rows(ledger: dict, day: str, k: int = 50) -> list[dict]:
    """Phrases that BOTH parties independently synchronized on `day`, collapsed and ranked.

    `day_peak` is deliberately set to min(D, R) — the DUET magnitude — so that build.collapse_and_rank
    (which dedupes stopword-padding variants and sub-grams by comparing day_peak, then breaks ties on
    content-richness) does its collapsing on the duet's own metric rather than on a single party's
    count. "the water resources development act" and "water resources development act" are one duet,
    not two."""
    rows = []
    for ngram, e in ledger.items():
        d = (e.get("daily") or {}).get(day)
        if not d:
            continue
        # Same display-time suppression the sync table applies: procedural furniture and connective
        # glue ("and the trump administration's") are not duets, they are grammar.
        if (boilerplate.is_boilerplate_ngram(ngram) or boilerplate.is_low_content(ngram)
                or boilerplate.is_weak_label(ngram)):
            continue
        if _ends_mid_construction(ngram):
            continue
        counts = {p: d.get(p, 0) for p in config.ALL_PARTIES}
        both = min(counts["D"], counts["R"])
        if both < DUET_MIN_MEMBERS:      # ONE bar, applied to BOTH parties
            continue
        rows.append({
            "ngram": ngram, "slug": build.phrase_slug(ngram), "n": e.get("n"),
            "both": both, "day_peak": both, "counts": counts,
            # Both collapse passes only merge rows of the SAME party (so one party's phrase family can
            # never absorb the other's). Every duet row is cross-party by definition, so there is no
            # party to key on: one constant sentinel puts all duets in a single family space, which is
            # the intended semantics ("the water resources development act" and "water resources
            # development act" are one duet). Stripped below — it never reaches the payload.
            "party": "*",
            "first_seen": e.get("first_seen"), "df_weight": e.get("df_weight", 0),
            "velocity": build._velocity(e.get("daily") or {}, day),
        })
    rows = build.collapse_and_rank(rows, k)
    for r in rows:
        r.pop("party", None)
    return rows


def find_duets(day: str, ledger: dict, focus: list[dict], rmap: dict, k: int = 5) -> list[dict]:
    """The day's duets, each with >=DUET_CITES_PER_SIDE cited verbatim quotes on BOTH sides.

    A candidate that cannot field a real quorum of real quotes on BOTH sides is DROPPED, not
    downgraded — an uncitable duet is silence (Article XII). Because the drop rule reads only
    per-side citation counts, it cannot prefer a party."""
    by_party: dict[str, list[dict]] = {p: [] for p in config.COMPOSITE_PARTIES}
    for s in focus:
        p = (s.get("member") or {}).get("party")
        if p in by_party:
            by_party[p].append(s)

    citable: list[dict] = []
    for row in candidate_rows(ledger, day, k=k * 6):   # headroom: many candidates fail the quote gate
        sides = {p: side_citations(row["ngram"], by_party[p], rmap) for p in config.COMPOSITE_PARTIES}
        if any(len(sides[p]) < DUET_MIN_MEMBERS for p in config.COMPOSITE_PARTIES):
            continue                                    # uncitable on a side -> not published, at all
        citable.append({**{kk: vv for kk, vv in row.items() if not kk.startswith("_")},
                        "sides": sides})
    # Topic-disjointness is applied AFTER the citation gate, never before: if the strongest row of a
    # topic cannot field real quotes on both sides, a weaker VARIANT of that same topic must still get
    # its chance. Filtering first would let a row that never published consume its whole topic and
    # silently drop a citable duet.
    return topic_disjoint(citable, k)
