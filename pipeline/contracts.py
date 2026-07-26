"""Canonical occurrence and phrase-claim contracts.

The legacy talking-point keys remain available to existing consumers. Schema version 2 adds exact
source spans, typed claim identifiers, and separately labeled count units.
"""
from __future__ import annotations

import re

from . import util


SCHEMA_VERSION = 2
CLAIM_TYPE = "phrase_claim"
_TOKEN = re.compile(r"[a-z0-9]+(?:['’-][a-z0-9]+)*", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _token_spans(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0).lower(), m.start(), m.end()) for m in _TOKEN.finditer(text or "")]


def phrase_occurrences(statement: dict, phrase: str, claim_id: str) -> list[dict]:
    """Return every exact token-run occurrence of ``phrase`` with source character offsets."""
    wanted = (phrase or "").split()
    if not wanted:
        return []
    text = statement.get("text") or ""
    spans = _token_spans(text)
    sid = statement.get("id") or ""
    member = statement.get("member") or {}
    office_id = member.get("bioguide")
    joint = statement.get("joint_group")
    out: list[dict] = []
    for index in range(len(spans) - len(wanted) + 1):
        window = spans[index:index + len(wanted)]
        if [token for token, _start, _end in window] != wanted:
            continue
        start, end = window[0][1], window[-1][2]
        occurrence_id = "occ:" + util.sha256_hex(f"{claim_id}\n{sid}\n{start}\n{end}")[:24]
        out.append({
            "schema_version": SCHEMA_VERSION,
            "object_type": "phrase_occurrence",
            "occurrence_id": occurrence_id,
            "claim_id": claim_id,
            "statement_id": sid,
            "publication_id": sid,
            "office_id": office_id,
            "family_id": joint or sid,
            "support_unit_id": joint or office_id,
            "party": member.get("party"),
            "start_char": start,
            "end_char": end,
            "surface_text": text[start:end],
            "normalized_phrase": phrase,
        })
    return out


def canonical_claim(tp: dict, statements_by_id: dict[str, dict]) -> dict:
    """Add the schema-2 claim contract without changing any legacy key or value."""
    claim_id = tp.get("claim_id") or tp.get("id")
    phrase = tp.get("label") or ""
    if not claim_id or not phrase:
        raise ValueError("claim identity and support phrase are required")
    occurrences: list[dict] = []
    for sid in tp.get("statements") or []:
        statement = statements_by_id.get(sid)
        if statement:
            occurrences.extend(phrase_occurrences(statement, phrase, claim_id))
    occurrences.sort(key=lambda row: (row["statement_id"], row["start_char"], row["end_char"]))
    if not occurrences:
        raise ValueError("support phrase has no exact source occurrence")

    offices = sorted({row["office_id"] for row in occurrences if row.get("office_id")})
    publications = sorted({row["publication_id"] for row in occurrences if row.get("publication_id")})
    families = sorted({row["family_id"] for row in occurrences if row.get("family_id")})
    support_units = sorted({row["support_unit_id"] for row in occurrences if row.get("support_unit_id")})
    quote_occurrence = min(
        occurrences,
        key=lambda row: (len(row["surface_text"]), row["surface_text"].casefold(),
                         row["statement_id"], row["start_char"]),
    )
    return {
        **tp,
        "schema_version": SCHEMA_VERSION,
        "object_type": CLAIM_TYPE,
        "claim_id": claim_id,
        "support_phrase": {
            "normalized": phrase,
            "text": quote_occurrence["surface_text"],
            "occurrence_id": quote_occurrence["occurrence_id"],
        },
        "display_quote": quote_occurrence["surface_text"],
        "occurrences": occurrences,
        "counts": {
            "offices": len(offices),
            "publications": len(publications),
            "families": len(families),
            "support_units": len(support_units),
        },
        "office_ids": offices,
        "publication_ids": publications,
        "family_ids": families,
        "support_unit_ids": support_units,
        "citation_occurrence_ids": [],
    }


def sentence_claims(composite: str, stats: dict) -> list[dict]:
    """Map each rendered sentence to the typed claims whose counted phrase it quotes."""
    source = (stats.get("selected_claims") if "selected_claims" in stats
              else stats.get("talking_points") or [])
    claims = [row for row in source if isinstance(row, dict)]
    sentences = sentence_parts(composite)
    out = []
    for index, sentence in enumerate(sentences):
        ids = []
        for claim in claims:
            claim_id = claim.get("claim_id")
            quote = claim.get("quote") or ""
            if claim_id and quote and (f'"{quote}"' in sentence or f'“{quote}”' in sentence):
                ids.append(claim_id)
        out.append({"sentence_idx": index, "claim_ids": sorted(set(ids))})
    return out


def sentence_parts(composite: str) -> list[str]:
    """Return non-empty rendered sentences using the claim-mapping boundary rule."""
    return [part.strip() for part in _SENTENCE.split(composite or "") if part.strip()]
