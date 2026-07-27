"""Deterministic surface eligibility for measured phrase claims."""
from __future__ import annotations

import re

from . import boilerplate, nomenclature, privacy, util


CLASSIFIER = "surface-eligibility-v3"
SURFACE_CLASSES = (
    "message", "unknown", "nomenclature", "procedural", "biographical", "private",
)
MESSAGE_SURFACES = frozenset({"daily_line", "ranking", "social", "alert", "award"})
_PROCEDURAL = re.compile(
    r"\b(?:committee of the whole|yield back|recognized for|roll call vote|"
    r"introduced legislation|cosponsored legislation|joined a letter|letter to secretary|"
    r"hearing on|markup of|ordered to be printed)\b",
    re.IGNORECASE,
)
_BIOGRAPHICAL = re.compile(
    r"\b(?:was born|born in|graduated from|served as|was elected|native of|"
    r"married to|his children|her children|biography)\b",
    re.IGNORECASE,
)
_TITLE_REFERENCE = re.compile(
    r"^(?:a |the )?(?:house of representatives|member of the house)$|"
    r"\b(?:in )?(?:sending|sent|send|writing|wrote|signed|signing) (?:a |the )?letter\b|"
    r"\b(?:text of the )?letter is available\b",
    re.IGNORECASE,
)


def _family_count(claim: dict) -> int | None:
    """Return distinct-family evidence, preserving legacy fixtures that predate the field."""
    counts = claim.get("counts") or {}
    if isinstance(counts.get("families"), int):
        return counts["families"]
    if isinstance(claim.get("family_count"), int):
        return claim["family_count"]
    if isinstance(claim.get("family_ids"), list):
        return len(set(claim["family_ids"]))
    statements = claim.get("statements")
    if isinstance(statements, list):
        return len(set(statements))
    return None


def classify_phrase(phrase: str, *, day: str | None = None, congress: int | None = None,
                    surfaces: list[str] | None = None,
                    family_count: int | None = None) -> dict:
    """Return one ruled surface class with deterministic provenance."""
    value = phrase or ""
    if privacy.is_suppressed(value) or any(privacy.is_suppressed(surface) for surface in (surfaces or [])):
        cls, rule = "private", "article-xiii"
    else:
        era = congress or (util.congress_for_date(day) if day else None)
        verdict = nomenclature.is_nomenclature(value, era) if era else None
        if verdict:
            cls, rule = "nomenclature", f'{verdict.get("lane")}:{verdict.get("cite")}'
        elif _TITLE_REFERENCE.search(value):
            cls, rule = "unknown", "title-reference-only"
        elif boilerplate.is_scaffold_key(value) or _PROCEDURAL.search(value):
            cls, rule = "procedural", "procedural-formula"
        elif _BIOGRAPHICAL.search(value):
            cls, rule = "biographical", "biographical-formula"
        elif boilerplate.content_word_count(value) < boilerplate.MIN_CONTENT_WORDS:
            cls, rule = "unknown", "no-substantive-content"
        elif family_count is not None and family_count < 3:
            cls, rule = "unknown", "family-quorum-unmet"
        else:
            cls, rule = "message", "affirmative-deterministic-floor"
    return {
        "surface_class": cls,
        "surface_eligible": cls == "message",
        "classifier": {
            "name": CLASSIFIER,
            "method": "deterministic",
            "rule": rule,
        },
    }


def classify_claim(claim: dict, *, day: str | None = None) -> dict:
    """Copy one claim and attach its surface class and topic provenance."""
    out = dict(claim)
    surfaces = [
        out.get("label") or "",
        out.get("display_quote") or "",
    ]
    classification = classify_phrase(
        out.get("label") or "", day=day or out.get("day"), surfaces=surfaces,
        family_count=_family_count(out),
    )
    occurrences = [row for row in (out.get("occurrences") or []) if isinstance(row, dict)]
    stances = {row.get("stance") for row in occurrences if row.get("stance")}
    if "negated" in stances and "affirmative" in stances:
        classification = {
            "surface_class": "unknown", "surface_eligible": False,
            "classifier": {"name": CLASSIFIER, "method": "deterministic", "rule": "mixed-stance"},
        }
    elif stances == {"negated"}:
        classification = {
            "surface_class": "unknown", "surface_eligible": False,
            "classifier": {"name": CLASSIFIER, "method": "deterministic", "rule": "negated-claim"},
        }
    elif occurrences and all(row.get("is_quoted") and row.get("quoted_speaker_detected")
                             for row in occurrences):
        classification = {
            "surface_class": "unknown", "surface_eligible": False,
            "classifier": {"name": CLASSIFIER, "method": "deterministic",
                           "rule": "quoted-attribution-only"},
        }
    out.update(classification)
    topic_source = out.get("topic_classifier") or {
        "name": "taxonomy-seed-match-v1",
        "method": "deterministic",
    }
    out["topic_provenance"] = [
        {
            "topic_id": topic,
            "classifier": dict(topic_source),
            "epistemic_label": "classifier output, not an observed fact",
        }
        for topic in (out.get("topics") or [])
    ]
    return out


def select_claims(claims: list[dict], *, day: str | None = None,
                  limit: int = 2) -> tuple[list[dict], list[dict]]:
    """Select at most two message claims and return nomenclature in a separate lane."""
    classified = [classify_claim(row, day=day) for row in claims]
    ranked = sorted(
        (row for row in classified if row["surface_class"] == "message"),
        key=lambda row: (
            -int(row.get("member_count") or 0),
            -int((row.get("counts") or {}).get("publications") or len(row.get("statements") or [])),
            row.get("label") or "",
        ),
    )
    selected: list[dict] = []
    used_topics: set[str] = set()
    while ranked and len(selected) < max(0, limit):
        choice_index = next(
            (index for index, row in enumerate(ranked)
             if not used_topics or not (set(row.get("topics") or []) & used_topics)),
            0,
        )
        choice = ranked.pop(choice_index)
        selected.append(choice)
        used_topics.update(choice.get("topics") or [])
    shared_names = sorted(
        (row for row in classified if row["surface_class"] == "nomenclature"),
        key=lambda row: (-int(row.get("member_count") or 0), row.get("label") or ""),
    )
    return selected, shared_names


def eligible_for_surface(row: dict, surface: str) -> bool:
    if surface not in MESSAGE_SURFACES:
        raise ValueError(f"unknown ruled surface: {surface}")
    return row.get("surface_class") == "message" and row.get("surface_eligible") is True
