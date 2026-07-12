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
