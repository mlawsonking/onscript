"""X15 acceptance tests for homepage lanes and the dark beta label."""
from __future__ import annotations

import os

from pipeline import config, eligibility, public_strings, site


def _day() -> dict:
    return {
        "day": "2026-07-27",
        "daily_lines": {
            "D": {"composite": "A measured Democratic composite.",
                  "composite_state": "generated_verified", "stats": {"talking_points": []}},
            "R": {"composite": "A measured Republican composite.",
                  "composite_state": "generated_verified", "stats": {"talking_points": []}},
        },
        "top_synchronized": [
            {"ngram": "message phrase", "party": "D", "day_peak": 4},
            {"ngram": "shared name", "party": "R", "day_peak": 4},
            {"ngram": "procedure phrase", "party": "D", "day_peak": 4},
            {"ngram": "unclassified fragment", "party": "R", "day_peak": 4},
        ],
    }


def _with_classifier(callback):
    original = eligibility.classify_phrase
    mapping = {
        "message phrase": "message",
        "shared name": "nomenclature",
        "procedure phrase": "procedural",
        "unclassified fragment": "unknown",
    }
    eligibility.classify_phrase = lambda phrase, **_kwargs: {
        "surface_class": mapping[phrase], "surface_eligible": mapping[phrase] == "message",
        "classifier": {"name": "fixture", "method": "deterministic", "rule": "fixture"},
    }
    try:
        return callback()
    finally:
        eligibility.classify_phrase = original


def test_four_lanes_render_from_the_classification_layer():
    rendered = _with_classifier(lambda: site.class_lanes_panel(_day()))
    assert rendered.count("data-class-lane=") == 4
    assert "Messages" in rendered and 'data-surface-class="message"' in rendered
    assert "Shared names" in rendered and 'data-surface-class="nomenclature"' in rendered
    assert "Procedure" in rendered and 'data-surface-class="procedural"' in rendered
    assert "Raw observations" in rendered and 'data-surface-class="unknown"' in rendered


def test_homepage_keeps_composites_before_lanes_and_links_corrections():
    old = os.environ.pop(public_strings.BETA_LABEL_ENV, None)
    try:
        rendered = _with_classifier(lambda: site.day_view_body(
            "2026-07-27", _day(), set(), depth=0, is_today=True
        ))
    finally:
        if old is not None:
            os.environ[public_strings.BETA_LABEL_ENV] = old
    assert rendered.index('class="lines"') < rendered.index("Classification lanes")
    assert "Instrument status." in rendered
    assert 'href="corrections/index.html"' in rendered
    assert public_strings.BETA_LABEL not in rendered


def test_beta_string_is_centralized_and_only_renders_behind_its_dark_flag():
    assert public_strings.beta_label_enabled({}) is False
    assert public_strings.beta_label_enabled({public_strings.BETA_LABEL_ENV: "true"}) is True
    assert public_strings.BETA_LABEL not in site.instrument_status_header(beta_enabled=False)
    assert public_strings.BETA_LABEL in site.instrument_status_header(beta_enabled=True)
    assert "beta_label" not in config.FEATURES


def test_beta_public_wording_has_one_code_owner():
    site_source = open(site.__file__, encoding="utf-8").read()
    assert "Public beta measurement instrument" not in site_source
    assert public_strings.BETA_LABEL == "Public beta measurement instrument"
