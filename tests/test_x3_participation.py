"""X3 acceptance tests for unit-safe participation measures and index removal."""
from __future__ import annotations

from pipeline import config, participation, site, util


def _statement(index: int, family: str) -> dict:
    return {
        "id": f"s{index}",
        "published_at": "2026-07-24",
        "member": {"bioguide": f"D{index}", "party": "D"},
        "document_family": {"family_id": family},
    }


def test_three_measures_keep_units_and_name_the_party_day_window():
    statements = [
        _statement(1, "family-a"), _statement(2, "family-a"),
        _statement(3, "family-b"), _statement(4, "family-c"),
        _statement(5, "family-d"),
    ]
    claims = [{
        "office_ids": ["D1", "D2"],
        "publication_ids": ["s1", "s2"],
        "family_ids": ["family-a"],
    }]
    result = participation.build("D", "2026-07-24", statements, claims)
    measures = result["measures"]
    assert set(measures) == {
        "office_participation", "publication_participation", "family_participation"
    }
    expected = {
        "office_participation": (2, 5, "offices"),
        "publication_participation": (2, 5, "publications"),
        "family_participation": (1, 4, "document families"),
    }
    for key, (numerator, denominator, unit) in expected.items():
        row = measures[key]
        assert (row["numerator"], row["denominator"]) == (numerator, denominator)
        assert row["numerator_unit"] == row["denominator_unit"] == unit
        assert row["window"] == "party-day 2026-07-24"
        assert row["method_version"] == participation.METHOD_VERSION


def test_real_committed_day_with_legacy_discipline_renders_no_public_index():
    day = util.read_json(config.DERIVED / "days" / "2026-07-24.json", {})
    assert day.get("discipline", {}).get("D", {}).get("index") == 0.7692
    rendered = site.day_view_body("2026-07-24", day, set(), 0, is_today=True)
    assert "on-script index" not in rendered.casefold()
    assert "0.7692" not in rendered and "0.8358" not in rendered


def test_participation_render_names_both_units_window_and_method():
    statements = [_statement(1, "family-a"), _statement(2, "family-a")]
    claims = [{"office_ids": ["D1"], "publication_ids": ["s1"],
               "family_ids": ["family-a"]}]
    day = {"participation": {"D": participation.build(
        "D", "2026-07-24", statements, claims
    )}}
    rendered = site.participation_panel(day)
    assert "1 offices of 2 offices" in rendered
    assert "1 publications of 2 publications" in rendered
    assert "1 document families of 1 document families" in rendered
    assert "Window: party-day 2026-07-24" in rendered
    assert f"Method: {participation.METHOD_VERSION}" in rendered
