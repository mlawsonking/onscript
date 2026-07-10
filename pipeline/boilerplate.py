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
    re.compile(r"\bthe following statement\b"),
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
]


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


def is_boilerplate_ngram(ngram: str) -> bool:
    return any(p.search(ngram) for p in _NGRAM_BOILERPLATE)
