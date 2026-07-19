"""Boilerplate suppression + tokenization (§4 A4, §11.1).

Press releases are template soup; without suppression the "coordination" detector
measures Drupal, not politics. Two layers:
  1. structural strip  — dateline prefixes, "For Immediate Release", contact blocks,
     "###" trailers, phone/email/URL tokens are removed before n-gramming.
  2. n-gram regex list — an n-gram is boilerplate if it matches a known template pattern
     ("today announced", committee titles, "th district", salutations, procedure).
A third, statistical layer (per-Congress document-frequency percentile) lives in phrases.py
because it needs the whole corpus.
"""
from __future__ import annotations

import re

# --- structural strip -------------------------------------------------------
_STRIP_PATTERNS = [
    re.compile(r"^\s*for immediate release\b.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*(press )?contact\s*:.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*media (inquiries|contact)\s*:.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\bhttps?://\S+", re.IGNORECASE),
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    re.compile(r"\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}"),          # phone numbers
    re.compile(r"#\s*#\s*#.*$", re.DOTALL),                     # ### and everything after
]
# Dateline prefix e.g. "WASHINGTON, D.C. —" / "WASHINGTON, DC –" / "WASHINGTON —"
_DATELINE = re.compile(
    r"^\s*[A-Z][A-Za-z.\s]{2,30},?\s*(D\.?C\.?)?\s*[–—-]\s*",
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_TOKEN = re.compile(r"[a-z0-9]+(?:['’-][a-z0-9]+)*")

# --- n-gram-level boilerplate regexes --------------------------------------
_NGRAM_BOILERPLATE = [
    re.compile(r"\btoday (announced|introduced|released|joined|voted|led|sent|urged|called|reintroduced)\b"),
    re.compile(r"\b(issued the following|released the following|made the following)\b"),
    re.compile(r"\bfollowing statement\b"),
    re.compile(r"\bis endorsed\b"),
    re.compile(r"\bis proud to\b"),
    re.compile(r"\bcommittee on\b"),
    re.compile(r"\b(ranking member|chairman|chairwoman|chair) of the\b"),
    re.compile(r"\bsubcommittee\b"),
    re.compile(r"\b\d{1,2}(st|nd|rd|th) (congressional )?district\b"),
    re.compile(r"\b(dear|sincerely|regards)\b"),
    re.compile(r"\bunanimous consent\b"),
    re.compile(r"\bi (rise|yield)\b"),
    re.compile(r"\b(u\.?s\.? )?(representative|senator|congressman|congresswoman)\b"),
    re.compile(r"\bwashington\b"),
    # temporal / scheduling artifacts (§1.4.5: dates are not political messages) --------
    re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"),
    re.compile(r"\b(19|20)\d{2}\b"),  # years
    re.compile(  # a month adjacent to a day number -> a date, not a stance ("may" alone survives)
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b"
    ),
    re.compile(
        r"\b\d{1,2}(st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b"
    ),
    re.compile(r"\b(a\.?m\.?|p\.?m\.?|est|edt|cst|cdt|pst|pdt)\b"),
    # institutional / process / courtesy language — recurring congressional plumbing, not a
    # partisan stance (keeps "trump administration"/"republicans" etc., which ARE stances) ---
    re.compile(r"\b(sent|send|wrote|write|read|signed|penned) (a |the )?letter\b"),
    re.compile(r"\bfull letter\b"),
    re.compile(r"\b(want|wish|would like|like) to thank\b"),
    re.compile(r"\bfollowing questions?\b"),
    re.compile(r"\banswers? to the\b"),
    re.compile(r"\bendorsed by\b"),
    re.compile(r"\bdepartment of\b"),
    re.compile(r"\boffice of\b"),
    re.compile(r"\bbureau of\b"),
    re.compile(r"\bexecutive director\b"),
    re.compile(r"\bfederal aviation\b"),
    re.compile(r"\bstate and local\b"),
]


# Function words: an n-gram needs >= MIN_CONTENT_WORDS tokens OUTSIDE this set to be a
# phrase, which drops generic filler ("at the same time", "this funding will") while keeping
# real talking points ("war in iran", "birthright citizenship"). Not a stance judgement —
# purely structural, applied identically to both parties.
STOPWORDS = frozenset("""
a an the and or but nor for so yet of to in on at by with from as into onto upon about over
under between through during before after above below off out up down this that these those
it its we us our ours you your yours i me my mine he him his she her hers they them their
theirs who whom whose which what is are was were be been being am do does did done have has
had having will would shall should can could may might must not no than then also just very
too more most much many some any all each every either neither both few several such same
other another one here there where when while because if unless until since about
""".split())
MIN_CONTENT_WORDS = 2


def content_word_count(ngram: str) -> int:
    return sum(1 for t in ngram.split() if t not in STOPWORDS)


def is_low_content(ngram: str) -> bool:
    return content_word_count(ngram) < MIN_CONTENT_WORDS


# A talking-point LABEL that is connective GLUE — begins with a coordinating conjunction AND trails
# off in a possessive ("and the trump administration's", which glued three unrelated statements —
# Cuba, USDA, immigration — by that span) — is a mid-sentence fragment, not a message. This pairing is
# high-precision: real conjunction-led phrases end in a content noun ("and civil rights", "and
# republicans in congress", "and transparent investigation into the killing") and are KEPT; only the
# possessive-trailing connective is dropped. Rejecting on the leading conjunction ALONE over-suppresses
# real coordinated phrases (adversarial-review finding), so we require both signals. §Session-7 (C-i).
_CONJUNCTION_START = frozenset("and but or nor yet so".split())


def is_weak_label(ngram: str) -> bool:
    """True if an n-gram is a poor talking-point NAME: low-content, or connective glue (begins with a
    coordinating conjunction AND ends in a possessive). Used to suppress clusters bound by grammar,
    not by a message — precisely, so coherent conjunction-led phrases survive."""
    toks = (ngram or "").split()
    if not toks or is_low_content(ngram):
        return True
    tail = (ngram or "").rstrip()
    return toks[0] in _CONJUNCTION_START and (tail.endswith("'s") or tail.endswith("s'"))


# docs/19 §4b — the cluster-key ADMISSION gate. is_weak_label caught ONE narrow scaffold shape
# (conjunction-led possessive, "and the trump administration's"). The live 2026-07-17 defects wore two
# others that it misses:
#   * "into the trump administration's"        — a connective frame that TERMINATES before the policy
#                                                 object (trailing possessive): it names a possessor,
#                                                 never the thing possessed;
#   * "democratic colleagues in demanding the" — an ATTRIBUTION frame (who joined/led), trailing off in
#                                                 a determiner: it is about the speakers, not a message.
# Both are string-valid and quorum-clean, so the verifier honestly verified a span that is not a
# message. This gate reads ONLY the phrase's own grammar (deterministic, party-blind — Art. IV) and is
# CONSERVATIVE by design (docs/19 §4b): a missed valid finding costs one line; an admitted scaffold key
# anchors unrelated claims on the flagship surface.
_ATTRIBUTION_TOKENS = frozenset(
    "colleagues cosponsors co-sponsors cosigners co-signers signatories".split())
_POSSESSIVE_TAILS = ("'s", "s'", "’s", "s’")   # straight + curly apostrophe

# docs/19 §4b (2nd pass) — STABLE rejection reason codes, so a conservative gate's false negatives are
# auditable: the all-days audit categorizes rejections by reason (not merely counts them) and logs each
# rejected candidate with its reason + would-have-been output — the only honest way to see what a
# precision-favouring gate is dropping before anyone tunes it. `is_weak_label` carries
# REJECT_LOW_INFORMATION_CONTENT; the family quorum (verify.py) carries REJECT_FAMILY_QUORUM.
REJECT_INCOMPLETE_SYNTACTIC_SPAN = "REJECT_INCOMPLETE_SYNTACTIC_SPAN"  # ends in a function word / possessive
REJECT_ATTRIBUTION_FRAME = "REJECT_ATTRIBUTION_FRAME"                  # names who joined/led, not the message
REJECT_LOW_INFORMATION_CONTENT = "REJECT_LOW_INFORMATION_CONTENT"      # is_weak_label (low-content / conj-possessive)
REJECT_FAMILY_QUORUM = "REJECT_FAMILY_QUORUM"                          # <quorum families carry the key (verify.py)


def scaffold_reason(ngram: str) -> str | None:
    """The stable reason code a cluster KEY is inadmissible as connective/attribution scaffolding
    (docs/19 §4b req 1), or None if admissible. Reject when the key (a) terminates before its object — a
    trailing function word ('...demanding the') or possessive ('...administration's') names a
    connector/possessor rather than the object — or (b) is an attribution frame naming WHO joined/led
    rather than WHAT was said. Party-blind (reads only the phrase's own grammar)."""
    toks = (ngram or "").split()
    if not toks:
        return REJECT_INCOMPLETE_SYNTACTIC_SPAN
    # Attribution is checked FIRST because it is the deeper, more informative reason: "democratic
    # colleagues in demanding the" is scaffolding because it names WHO joined, and only incidentally
    # also ends in a determiner. A pure fragment ("war powers resolution to") has no attribution token
    # and falls through to the syntactic-span reason.
    if any(t in _ATTRIBUTION_TOKENS for t in toks):             # (a) attribution frame — names who joined/led
        return REJECT_ATTRIBUTION_FRAME
    last = toks[-1]
    if last in STOPWORDS or last.endswith(_POSSESSIVE_TAILS):   # (b) terminates before the object
        return REJECT_INCOMPLETE_SYNTACTIC_SPAN
    return None


def is_scaffold_key(ngram: str) -> bool:
    """True if a cluster KEY is connective/attribution scaffolding, not a message (docs/19 §4b req 1).
    Thin wrapper over scaffold_reason so every existing call site stays boolean; the audit uses the
    reason code."""
    return scaffold_reason(ngram) is not None


def contains_gram(text: str, gram: str) -> bool:
    """True if the token sequence `gram` appears as a contiguous run in `text`'s tokenized sentences —
    the SAME notion of "this statement carries this phrase" that cluster.py used to build the cluster
    (docs/19 §4b). Matched on the tokenizer, NOT a raw substring, so a comma or period between tokens in
    the source can never hide a gram the member really used (nor admit one they did not)."""
    gt = gram.split()
    n = len(gt)
    if n == 0:
        return False
    for toks in sentences(text):
        for i in range(len(toks) - n + 1):
            if toks[i:i + n] == gt:
                return True
    return False


def clean_text(text: str) -> str:
    """Remove structural boilerplate before tokenization."""
    t = text or ""
    for pat in _STRIP_PATTERNS:
        t = pat.sub(" ", t)
    return t


def sentences(text: str):
    for seg in _SENTENCE_SPLIT.split(clean_text(text)):
        seg = _DATELINE.sub("", seg)
        toks = _TOKEN.findall(seg.lower())
        if toks:
            yield toks


# One combined alternation instead of ~20 separate .search() calls per n-gram — identical
# match semantics (matches iff any sub-pattern matches), ~20x faster on the engine's hot path.
_NGRAM_BOILERPLATE_RE = re.compile("|".join(f"(?:{p.pattern})" for p in _NGRAM_BOILERPLATE))


def is_boilerplate_ngram(ngram: str) -> bool:
    return _NGRAM_BOILERPLATE_RE.search(ngram) is not None
