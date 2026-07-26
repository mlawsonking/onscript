"""X4 fail-closed phrase classification and surface controls."""
from __future__ import annotations

import json
from pathlib import Path

from pipeline import build, distill, eligibility, phrases, post_bluesky, site, status_exports


ROOT = Path(__file__).resolve().parent.parent
DAY = "2026-07-24"
RECLASSIFIED = {
    "the house of representatives",
    "member of the house",
    "in sending a letter",
    "letter is available",
}


def _committed_day() -> dict:
    return json.loads((ROOT / "data" / "derived" / "days" / f"{DAY}.json").read_text(
        encoding="utf-8"
    ))


def test_committed_2026_07_24_failures_reclassify_away_from_message():
    payload = _committed_day()
    labels = {
        row.get("label")
        for rows in (payload.get("talking_points") or {}).values()
        for row in rows
    }
    labels |= {row.get("ngram") for row in payload.get("top_synchronized") or []}
    assert RECLASSIFIED <= labels
    for phrase in sorted(RECLASSIFIED):
        classified = eligibility.classify_phrase(phrase, day=DAY, family_count=3)
        assert classified["surface_class"] != "message", phrase
        assert classified["surface_eligible"] is False

    panel = site.daily_line_panel("D", payload)
    assert "the house of representatives" not in panel
    assert "member of the house" not in panel
    assert "letter is available" not in panel
    assert "No measured phrase met the message-eligibility standard today." in panel


def test_new_measurement_requires_three_distinct_families():
    low = eligibility.classify_phrase(
        "protect voting rights now", day=DAY, family_count=2,
    )
    enough = eligibility.classify_phrase(
        "protect voting rights now", day=DAY, family_count=3,
    )
    assert low["surface_class"] == "unknown"
    assert low["classifier"]["rule"] == "family-quorum-unmet"
    assert enough["surface_class"] == "message"


def test_phrase_ledger_carries_distinct_family_evidence():
    text = "We will protect voting rights now for every citizen."
    statements = []
    for index, family in enumerate(("family-a", "family-a", "family-b")):
        statements.append({
            "id": f"s{index}", "lane": 1, "published_at": DAY, "congress": 119,
            "text": text, "document_family": {"family_id": family},
            "member": {"bioguide": f"B{index}", "party": "D"},
        })
    for index in range(60):
        statements.append({
            "id": f"filler-{index}", "lane": 1, "published_at": DAY, "congress": 119,
            "text": f"alpha{index} beta{index} gamma{index} delta{index}",
            "document_family": {"family_id": f"filler-family-{index}"},
            "member": {"bioguide": f"F{index}", "party": "D"},
        })
    ledger = phrases.PhraseEngine().build(statements)
    evidence = ledger["protect voting rights now"]["daily"][DAY]
    assert evidence["families_D"] == 2
    assert evidence["family_ids_D"] == ["family-a", "family-b"]


def test_no_affirmative_message_yields_the_meaningful_null():
    claim = {
        "id": "claim-low-family",
        "day": DAY,
        "label": "protect voting rights now",
        "member_count": 4,
        "counts": {"offices": 4, "publications": 4, "families": 2, "support_units": 4},
        "fragments": [{"text": "protect voting rights now"}],
        "topics": ["elections"],
    }
    stats = distill.build_stats(
        "D", DAY, 12, [claim],
        {"text": "letter is available", "members": 8, "family_count": 8},
    )
    rendered = distill._compose_dry(stats)
    assert stats["selected_claims"] == []
    assert stats["top_phrase"] is None
    assert rendered.endswith("No measured phrase met the message-eligibility standard today.")
    assert claim["label"] not in rendered


def test_unknown_is_excluded_from_public_surfaces_but_retained_in_exports_and_concordance():
    phrase = "protect voting rights now"
    row = {
        "ngram": phrase, "party": "D", "day_peak": 4,
        "counts": {"D": 4, "R": 0}, "family_count": 2,
        "family_counts": {"D": 2, "R": 0},
        "first_seen": {"date": DAY},
    }
    day = {
        "day": DAY,
        "daily_lines": {"D": {"composite": "Measured output."}},
        "top_synchronized": [row],
    }
    assert phrase not in site.sync_table(day, set(), depth=1)
    assert phrase not in "\n".join(post_bluesky.build_thread(DAY, "D", day))
    assert phrase not in status_exports.watchlist_atom([(DAY, day)], ["voting"])

    files = status_exports.static_exports({}, [(DAY, day)], {"by_peak": [row], "by_velocity": []})
    assert phrase in files["api/v1/phrases.json"].decode("utf-8")

    statement = {
        "id": "s1", "lane": 1, "published_at": DAY,
        "url": "https://example.test/s1", "text": phrase,
        "member": {"bioguide": "B000001", "party": "D", "name": "Member", "state": "TS"},
    }
    concordance = build.build_concordance(
        [statement], {phrase: {"peak_units": 4}},
        roster_map={"B000001": statement["member"]},
        min_statements=1, receipts_max=1, peak_floor=1,
    )
    assert concordance["members"][0]["on_script"] == 1
