"""X5 composite states, neutral leads, structured persistence, and style bans."""
from __future__ import annotations

import json
from pathlib import Path

from pipeline import distill, llm, post_bluesky, site, verify


ROOT = Path(__file__).resolve().parent.parent
DAY = "2026-07-24"


def _committed_day() -> dict:
    return json.loads((ROOT / "data" / "derived" / "days" / f"{DAY}.json").read_text(
        encoding="utf-8"
    ))


def _statements(count: int = 20) -> list[dict]:
    return [
        {
            "id": f"s-{index}", "lane": 1, "published_at": DAY, "text": "x",
            "member": {"bioguide": f"B{index}", "party": "D"},
        }
        for index in range(count)
    ]


def _claim() -> dict:
    return {
        "id": "claim-1", "day": DAY, "label": "protect voting rights now",
        "member_count": 3, "statements": ["s-0", "s-1", "s-2"],
        "fragments": [{"statement": "s-0", "text": "we protect voting rights now"}],
        "topics": ["elections"],
    }


def test_real_committed_day_panels_and_threads_carry_neutral_lead_and_state():
    payload = _committed_day()
    for party in ("D", "R"):
        panel = site.daily_line_panel(party, payload)
        thread = "\n".join(post_bluesky.build_thread(DAY, party, payload))
        assert "Measurement:" in panel and "Composite state:" in panel
        assert "Measurement:" in thread and "Composite state:" in thread
        assert any(state in panel for state in distill.COMPOSITE_STATES)
        assert any(state in thread for state in distill.COMPOSITE_STATES)


def test_daily_line_persists_self_verifying_structured_request_and_response():
    statements = _statements()
    line = distill.daily_line(
        "D", DAY, statements, [_claim()], None,
        {row["id"]: row for row in statements}, allow_llm_voice=False,
    )
    hashes = line["generation_hashes"]
    assert hashes["request_sha256"] == distill._record_hash(line["structured_request"])
    assert hashes["response_sha256"] == distill._record_hash(line["structured_output"])
    assert line["structured_output"]["composite"] == line["composite"]
    assert line["structured_output"]["sentence_claims"] == line["sentence_claims"]
    assert line["composite_state"] == "deterministic_fallback"
    assert line["measurement_lead"].startswith("Measurement: 20 publications")


def test_no_eligible_claim_and_verifier_failure_have_explicit_states():
    statements = _statements()
    empty = distill.daily_line(
        "D", DAY, statements, [], None,
        {row["id"]: row for row in statements}, allow_llm_voice=False,
    )
    assert empty["composite_state"] == "withheld_no_eligible_claim"
    assert "No phrase was shared" in empty["composite"]

    original = distill.verify.verify_daily_line
    distill.verify.verify_daily_line = lambda *args, **kwargs: (False, ["seeded failure"])
    try:
        failed = distill.daily_line(
            "D", DAY, statements, [_claim()], None,
            {row["id"]: row for row in statements}, allow_llm_voice=False,
        )
    finally:
        distill.verify.verify_daily_line = original
    assert failed["composite_state"] == "withheld_verifier_failure"


def test_every_banned_style_token_fails_the_blocking_verifier():
    stats = {"statements": 20, "talking_points": [], "day": DAY, "sync_min": 3}
    for token in verify.STYLE_LEAKAGE_BANS:
        ok, reasons = verify.verify_daily_line(
            {"composite": f"{token} measured output."}, json.dumps(stats), stats=stats,
        )
        assert ok is False, token
        assert any("banned style leakage" in reason for reason in reasons)


def test_style_bans_are_in_dark_prompts_and_live_pins_do_not_move():
    for filename in ("P2_daily_line.v1.4.txt", "P3_quiet_day.v1.2.txt"):
        text = (ROOT / "pipeline" / "prompts" / filename).read_text(encoding="utf-8").casefold()
        assert all(token in text for token in verify.STYLE_LEAKAGE_BANS)
    assert llm._PROMPT_FILES["P2"] == "P2_daily_line.v1.3.txt"
    assert llm._PROMPT_FILES["P3"] == "P3_quiet_day.v1.1.txt"
