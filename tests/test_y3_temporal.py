"""Y3 acceptance: temporal truthfulness (R-36.4).

The homepage names its measured state under the five-state ladder, and a reading
posted after its measured date never says today and carries the absolute date.
"""
from __future__ import annotations

import re

from pipeline import config, public_strings, site, util
from pipeline import post_bluesky as pb


_TODAY = re.compile(r"\btoday\b", re.IGNORECASE)


def test_the_resolver_returns_each_of_the_five_states():
    assert site.temporal_state("2026-07-27", "2026-07-27", age_hours=10) == "today"
    assert site.temporal_state("2026-07-27", "2026-07-27", age_hours=48) == "latest_complete"
    assert site.temporal_state("2026-07-27", "2026-07-27", age_hours=10, degraded=True) == "latest_available"
    assert site.temporal_state("2026-07-25", "2026-07-27", age_hours=10) == "publication_delayed"
    assert site.temporal_state("2026-07-27", "2026-07-27", source_ok=False) == "no_current_reading"


def test_a_force_finalized_stale_reading_is_not_labeled_today():
    # The exact live scenario the review confirmed: a force-finalized reading two days
    # behind the expected latest complete day.
    state = site.temporal_state("2026-07-25", "2026-07-27", age_hours=72,
                                degraded=True, forced_finalize=True)
    assert state == "publication_delayed"
    assert public_strings.temporal_heading(state) == "Publication delayed"


def test_each_state_renders_its_ruled_heading():
    day_data = util.read_json(config.DERIVED / "days" / "2026-07-25.json", {})
    for state, heading in public_strings.TEMPORAL_HEADINGS.items():
        body = site.day_view_body("2026-07-25", day_data, set(), 0,
                                  is_today=True, temporal_state=state, lag_days=2)
        head = body.split("</h1>", 1)[0]
        assert heading in head, f"{state} heading missing from the h1"


def test_publication_delayed_renders_the_lag_line_on_the_homepage():
    day_data = util.read_json(config.DERIVED / "days" / "2026-07-25.json", {})
    body = site.day_view_body("2026-07-25", day_data, set(), 0,
                              temporal_state="publication_delayed", lag_days=2)
    assert "publication is 2 days behind" in body
    assert "2026-07-25" in body


def test_a_delayed_day_social_post_carries_the_absolute_date_and_not_today():
    day_data = util.read_json(config.DERIVED / "days" / "2026-07-25.json", {})
    for party in ("D", "R"):
        thread = pb.build_thread("2026-07-25", party, day_data, post_date="2026-07-28")
        assert not any(_TODAY.search(post) for post in thread), f"{party} post still says today"
        assert any("2026-07-25" in post for post in thread), f"{party} post lacks the absolute date"


def test_a_same_day_social_post_keeps_today_as_a_true_statement():
    day_data = util.read_json(config.DERIVED / "days" / "2026-07-25.json", {})
    thread = pb.build_thread("2026-07-25", "D", day_data, post_date="2026-07-25")
    assert any(_TODAY.search(post) for post in thread)


def test_the_homepage_title_carries_no_em_dash():
    # The <title> literal previously used a U+2014 em dash; house style forbids it.
    source = (config.REPO_ROOT / "pipeline" / "site.py").read_text(encoding="utf-8")
    assert "OnScript — Today" not in source
