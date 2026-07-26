"""Unit-safe party-day participation measures for published message claims."""
from __future__ import annotations


METHOD_VERSION = "participation-measures-v1"


def _family_id(statement: dict) -> str | None:
    return ((statement.get("document_family") or {}).get("family_id")
            or statement.get("joint_group") or statement.get("id"))


def _measure(label: str, numerator_ids: set[str], denominator_ids: set[str], unit: str,
             day: str) -> dict:
    denominator = len(denominator_ids)
    numerator = len(numerator_ids & denominator_ids)
    return {
        "label": label,
        "numerator": numerator,
        "numerator_unit": unit,
        "denominator": denominator,
        "denominator_unit": unit,
        "share": round(numerator / denominator, 6) if denominator else None,
        "window": f"party-day {day}",
        "method_version": METHOD_VERSION,
    }


def build(party: str, day: str, statements: list[dict], claims: list[dict]) -> dict:
    """Measure distinct support participation with no unit mixing."""
    eligible = [row for row in statements
                if row.get("published_at") == day
                and (row.get("member") or {}).get("party") == party]
    office_denominator = {
        (row.get("member") or {}).get("bioguide") for row in eligible
        if (row.get("member") or {}).get("bioguide")
    }
    publication_denominator = {row.get("id") for row in eligible if row.get("id")}
    family_denominator = {_family_id(row) for row in eligible if _family_id(row)}

    office_numerator = {value for claim in claims for value in (claim.get("office_ids") or [])}
    publication_numerator = {
        value for claim in claims for value in (claim.get("publication_ids") or [])
    }
    family_numerator = {value for claim in claims for value in (claim.get("family_ids") or [])}
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "party": party,
        "day": day,
        "measures": {
            "office_participation": _measure(
                "Office participation", office_numerator, office_denominator, "offices", day
            ),
            "publication_participation": _measure(
                "Publication participation", publication_numerator, publication_denominator,
                "publications", day
            ),
            "family_participation": _measure(
                "Document-family participation", family_numerator, family_denominator,
                "document families", day
            ),
        },
    }
