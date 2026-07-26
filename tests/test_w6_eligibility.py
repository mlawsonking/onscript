"""W6 phrase classes, code selection, provenance, and dark prompts."""
from __future__ import annotations

from pathlib import Path

from pipeline import build, config, distill, eligibility, llm, post_bluesky
from tests.test_privacy import PERSON_A, gate


ROOT = Path(__file__).resolve().parent.parent


def _claim(label: str, members: int, topic: str, index: int) -> dict:
    return {
        "id": f"claim-{index}",
        "day": "2026-07-24",
        "label": label,
        "member_count": members,
        "statements": [f"s-{index}-{offset}" for offset in range(members)],
        "fragments": [{"statement": f"s-{index}-0", "text": label}],
        "topics": [topic],
    }


def test_top_raw_procedural_phrase_yields_a_line_led_by_the_top_message():
    procedural = _claim("introduced legislation for committee markup", 12, "government", 1)
    message = _claim("protect voting rights now", 7, "elections", 2)
    stats = distill.build_stats(
        "D", "2026-07-24", 25, [procedural, message],
        {"text": procedural["label"], "members": 12},
    )
    assert [row["label"] for row in stats["talking_points"]] == [message["label"]]
    assert stats["top_phrase"] is None
    rendered = distill._compose_dry(stats)
    assert message["label"] in rendered
    assert procedural["label"] not in rendered


def test_code_selects_two_message_claims_with_topic_diversity():
    claims = [
        _claim("lower household costs now", 10, "economy", 1),
        _claim("reduce consumer prices now", 9, "economy", 2),
        _claim("protect rural hospitals now", 8, "health", 3),
        _claim("secure voting access now", 7, "elections", 4),
    ]
    selected, shared = eligibility.select_claims(claims, day="2026-07-24", limit=2)
    assert shared == []
    assert [row["label"] for row in selected] == [
        "lower household costs now", "protect rural hospitals now",
    ]


def test_all_five_classes_are_deterministic_and_surface_gated():
    assert eligibility.classify_phrase("protect voting rights now", day="2026-07-24")["surface_class"] == "message"
    assert eligibility.classify_phrase(
        "introduced legislation for committee markup", day="2026-07-24"
    )["surface_class"] == "procedural"
    assert eligibility.classify_phrase(
        "was born in rural county", day="2026-07-24"
    )["surface_class"] == "biographical"

    original = eligibility.nomenclature.is_nomenclature
    eligibility.nomenclature.is_nomenclature = lambda phrase, congress: (
        {"lane": "bill", "cite": "hr1"} if phrase == "official measure title" else None
    )
    try:
        named = eligibility.classify_phrase("official measure title", day="2026-07-24")
    finally:
        eligibility.nomenclature.is_nomenclature = original
    assert named["surface_class"] == "nomenclature"

    with gate():
        private = eligibility.classify_phrase(f"policy for {PERSON_A}", day="2026-07-24")
        assert private["surface_class"] == "private"

    for classification in (
        eligibility.classify_phrase("introduced legislation for committee markup", day="2026-07-24"),
        eligibility.classify_phrase("was born in rural county", day="2026-07-24"),
        named,
        private,
    ):
        for surface in ("daily_line", "social", "alert"):
            assert eligibility.eligible_for_surface(classification, surface) is False


def test_nomenclature_is_segregated_while_the_legacy_chip_flag_is_off():
    previous = config.FEATURES["nomenclature_tags"]
    config.FEATURES["nomenclature_tags"] = False
    try:
        claim = _claim("21st century road to housing act", 20, "housing", 1)
        stats = distill.build_stats("D", "2026-07-24", 30, [claim], {
            "text": "21st century road to housing act", "members": 20,
        })
    finally:
        config.FEATURES["nomenclature_tags"] = previous
    assert stats["selected_claims"] == [] and stats["talking_points"] == []
    assert stats["top_phrase"] is None
    assert stats["shared_nomenclature"][0]["label"] == "21st century road to housing act"


def test_topic_labels_carry_classifier_provenance_and_epistemic_label():
    stats = distill.build_stats(
        "R", "2026-07-24", 10, [_claim("secure the southern border", 5, "immigration", 1)], None
    )
    provenance = stats["talking_points"][0]["topic_provenance"]
    assert provenance == [{
        "topic_id": "immigration",
        "classifier": {"name": "taxonomy-seed-match-v1", "method": "deterministic"},
        "epistemic_label": "classifier output, not an observed fact",
    }]


def test_social_receipt_omits_a_procedural_top_phrase():
    day = {
        "daily_lines": {"D": {"composite": "Today we published a measured line."}},
        "top_synchronized": [{
            "party": "D",
            "ngram": "introduced legislation for committee markup",
            "day_peak": 12,
            "first_seen": {"date": "2026-07-24"},
        }],
    }
    thread = "\n".join(post_bluesky.build_thread("2026-07-24", "D", day))
    assert "Most synchronized" not in thread
    assert "introduced legislation" not in thread


def test_concordance_keeps_a_non_surface_class_in_its_measurement_input():
    phrase = "was born in rural county"
    statement = {
        "id": "bio-1",
        "lane": 1,
        "published_at": "2026-07-24",
        "url": "https://example.test/bio-1",
        "text": phrase,
        "member": {"bioguide": "B000001", "party": "D", "name": "Member One", "state": "TS"},
    }
    ledger = {phrase: {"peak_units": 3}}
    result = build.build_concordance(
        [statement], ledger, roster_map={"B000001": statement["member"]},
        min_statements=1, receipts_max=1, peak_floor=1,
    )
    assert result["members"][0]["on_script"] == 1


def test_cleaned_prompt_versions_are_committed_but_inactive():
    assert (ROOT / "pipeline/prompts/P2_daily_line.v1.4.txt").is_file()
    assert (ROOT / "pipeline/prompts/P3_quiet_day.v1.2.txt").is_file()
    assert llm._PROMPT_FILES["P2"] == "P2_daily_line.v1.3.txt"
    assert llm._PROMPT_FILES["P3"] == "P3_quiet_day.v1.1.txt"
