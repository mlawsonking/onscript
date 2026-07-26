"""Deterministic surface eligibility for measured phrase claims."""
from __future__ import annotations

import re

from . import boilerplate, nomenclature, privacy, util


CLASSIFIER = "surface-eligibility-v1"
SURFACE_CLASSES = ("message", "nomenclature", "procedural", "biographical", "private")
MESSAGE_SURFACES = frozenset({"daily_line", "social", "alert"})
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


def classify_phrase(phrase: str, *, day: str | None = None, congress: int | None = None,
                    surfaces: list[str] | None = None) -> dict:
    """Return one ruled surface class with deterministic provenance."""
    value = phrase or ""
    if privacy.is_suppressed(value) or any(privacy.is_suppressed(surface) for surface in (surfaces or [])):
        cls, rule = "private", "article-xiii"
    else:
        era = congress or (util.congress_for_date(day) if day else None)
        verdict = nomenclature.is_nomenclature(value, era) if era else None
        if verdict:
            cls, rule = "nomenclature", f'{verdict.get("lane")}:{verdict.get("cite")}'
        elif boilerplate.is_scaffold_key(value) or _PROCEDURAL.search(value):
            cls, rule = "procedural", "procedural-formula"
        elif _BIOGRAPHICAL.search(value):
            cls, rule = "biographical", "biographical-formula"
        else:
            cls, rule = "message", "message-default"
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
        out.get("label") or "", day=day or out.get("day"), surfaces=surfaces
    )
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
