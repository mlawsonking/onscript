"""S74-15 Package 4b: a line states the real reason it was not model-written.

The Sonnet rejection reasons were overwritten in the day record (distill.py), so public pages
explained a fallback with a reason that was not the logged one: 2026-11-17 said the claims "cannot
support a model-written composite" over a line whose model text was rejected for a banned style
token; 2026-09-16 R said "withheld under the privacy floor" over a quote-binding failure; 2026-09-16 R
printed state "corrected" over a withheld line (Constitution Article XVII). Every explanation is now
rendered from the recorded state and category by site.composite_reasons. Day records are read at a
pinned commit (docs/37 rule 3).
"""
from __future__ import annotations

import re

from pipeline import distill, public_strings, site, verify
from tests._pinned import pinned_day


def _text(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html).replace("&#x27;", "'")


# --- the record keeps the category ------------------------------------------------------------

def test_every_reason_verify_daily_line_emits_has_a_category_and_a_public_label():
    """docs/37 rule 1: the categorizer is tested against the strings its owner emits."""
    import inspect
    emitted = re.findall(r'reasons\.append\(f?"([^"{]+)', inspect.getsource(verify.verify_daily_line))
    assert len(emitted) >= 7, emitted
    for prefix in emitted:
        [cat] = verify.daily_line_reason_categories([prefix])
        assert cat != "other", prefix
        assert cat in site.REJECTION_CATEGORY_TEXT
    assert verify.daily_line_reason_categories(["something new"]) == ["other"]
    for _prefix, cat in verify.DAILY_LINE_REASON_CATEGORIES:
        assert cat in site.REJECTION_CATEGORY_TEXT


def test_a_rejected_model_text_records_its_categories_and_never_its_prose():
    from tests.test_voice import _party_stmts, _swap, _tps
    bad = 'The dominant message centers on this, clinically: "a phrase nobody said" today.'
    restore = _swap(dry_run=lambda: False,
                    direct_call=lambda *a, **k: {"text": bad, "tokens_in": 100, "tokens_out": 20})
    try:
        out = distill.daily_line("D", "2026-07-13", _party_stmts(40), _tps(), None, {},
                                 allow_llm_voice=True)
        failing = _swap(dry_run=lambda: False, direct_call=lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("api 500")))
        try:
            errored = distill.daily_line("D", "2026-07-13", _party_stmts(40), _tps(), None, {},
                                         allow_llm_voice=True)
        finally:
            failing()
    finally:
        restore()
    assert out["composite_state"] == "deterministic_fallback"
    cats = out["rejection"]["model_text"]
    assert "banned-style" in cats and all(c in site.REJECTION_CATEGORY_TEXT for c in cats)
    assert "nobody said" not in repr(out["rejection"]) and "clinically" not in repr(out["rejection"])
    assert errored["rejection"] == {"model_text": ["voice-error"]}
    # A line nothing rejected carries no rejection field: additive, schema-compatible.
    clean = distill.daily_line("D", "2026-07-13", _party_stmts(40), _tps(), None, {}, allow_llm_voice=False)
    assert "rejection" not in clean


# --- the rendered reason matches the recorded state, on the real committed records -------------

def test_2026_11_17_no_longer_asserts_the_unsupported_claims_cause():
    day = pinned_day("2026-11-17")
    assert day["daily_lines"]["D"]["composite_state"] == "deterministic_fallback"
    assert day["daily_lines"]["D"]["usage"]["tokens_in"] > 0          # the model was called
    assert "rejection" not in day["daily_lines"]["D"]                  # a past day: no category
    banner = _text(site.banner_html(day, {}))
    assert "cannot support a model-written composite" not in banner
    assert "Democrats' line was composed deterministically after the model text failed a " \
           "publication check" in banner
    # R was never sent to the model, and the page says so rather than claiming a failed check.
    assert day["daily_lines"]["R"]["composite_state"] == "withheld_no_eligible_claim"
    assert "Republicans' line is a deterministic count" in banner
    assert "Republicans' line was composed deterministically after" not in banner


def test_2026_09_16_r_states_the_quote_binding_failure_not_the_privacy_floor():
    day = pinned_day("2026-09-16")
    line = day["daily_lines"]["R"]
    assert line["composite_state"] == "withheld_verifier_failure"
    assert verify.daily_line_reason_categories(line["verifier"]["reasons"]) == ["unbound-quote"]
    # S74-17 C fixed the verifier defect that withheld it, so the render-time re-composition now
    # verifies: the page shows the re-composed line and says it was withheld when published.
    _line, _tps, state, cause = site.corrected_line("R", day)
    assert state == "reclassified" and cause is None
    banner = _text(site.banner_html(day, {}))
    assert "withheld under the privacy floor" not in banner
    assert "Republicans' line was withheld when published because the model text failed a " \
           "publication check and then the deterministic composite failed one too" in banner
    assert site.REJECTION_CATEGORY_TEXT["unbound-quote"] in banner
    # The verifier-withheld branch itself: forced through a failing re-verification.
    saved = site.verify.verify_daily_line
    site.verify.verify_daily_line = lambda *a, **k: (False, ["unbound talking-point quotes: ['x']"])
    try:
        _line, _tps, state, cause = site.corrected_line("R", day)
        panel = _text(site.daily_line_panel("R", day))
    finally:
        site.verify.verify_daily_line = saved
    assert state == "withheld" and cause == {"cause": "verifier", "categories": ["unbound-quote"]}
    assert "withheld under the privacy floor" not in panel
    assert "Republicans' line is withheld because" in panel
    assert "Composite state:  withheld_verifier_failure" in panel


def test_2026_11_19_states_both_the_fallback_and_the_correction():
    day = pinned_day("2026-11-19")
    for party in "DR":
        assert day["daily_lines"][party]["composite_state"] == "deterministic_fallback"
    banner = _text(site.banner_html(day, {}))
    assert "Democrats' line was composed deterministically after the model text failed" in banner
    assert "Republicans' line was composed deterministically after the model text failed" in banner
    reasons = site.composite_reasons("D", day)
    if site.privacy_states(day)["D"] == "reclassified":
        assert any("message-eligibility standard" in r for r in reasons)


def test_a_recorded_category_is_named_and_a_privacy_withholding_keeps_its_own_reason():
    day = pinned_day("2026-11-17")
    line = dict(day["daily_lines"]["D"])
    line["rejection"] = {"model_text": ["banned-style", "counted-phrase"]}
    probe = {**day, "daily_lines": {**day["daily_lines"], "D": line}}
    [reason] = [r for r in site.composite_reasons("D", probe) if r.startswith("Democrats")]
    assert "model-written text failed a publication check (a banned style word; a quoted phrase " \
           "other than the counted phrase)" in reason
    line["rejection"] = {"model_text": ["voice-error"]}
    assert "returned no usable text" in site.composite_reasons("D", probe)[0]


def test_the_honesty_note_asserts_no_single_cause():
    note = public_strings.HOMEPAGE_HONESTY_NOTE
    assert "cannot support" not in note
    assert "not called" in note and "fails a publication check" in note


# --- 4d / S74-17 C: the curly-apostrophe defect, fixed (R-74.26) --------------------------------

def test_a_curly_apostrophe_label_binds_to_its_own_verbatim_quote():
    """2026-09-16 R: quotes_bound_to_talking_points folded the quote's typography (U+2019 to ') and
    compared it with the UNFOLDED label, so a deterministic composite quoting its own label verbatim
    failed binding. Both sides are now folded (structured-composite-v2)."""
    for label in ("to the president’s desk", "to the president's desk"):
        for quoted in ("to the president’s desk", "to the president's desk"):
            ok, off = verify.quotes_bound_to_talking_points(
                f'7 of us carried "{quoted}".',
                {"talking_points": [{"label": label, "quote": label, "members": 7}]})
            assert ok, (label, quoted, off)
    # A different word still fails: only typography is folded.
    ok, _ = verify.quotes_bound_to_talking_points(
        '7 of us carried "to the governor’s desk".',
        {"talking_points": [{"label": "to the president’s desk",
                             "quote": "to the president’s desk", "members": 7}]})
    assert not ok


def test_the_2026_09_16_r_deterministic_composite_now_verifies_from_its_recorded_stats():
    import json as _json
    day = pinned_day("2026-09-16")
    stats = day["daily_lines"]["R"]["stats"]
    composite = distill._compose_dry(stats)
    ok, reasons = verify.verify_daily_line({"composite": composite},
                                           _json.dumps(stats, ensure_ascii=False), stats=stats)
    assert ok, reasons
    assert distill.STRUCTURED_COMPOSITE_VERSION == "structured-composite-v2"
