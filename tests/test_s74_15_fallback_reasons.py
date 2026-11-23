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
    _line, _tps, state, cause = site.corrected_line("R", day)
    assert state == "withheld" and cause["cause"] == "verifier"
    banner = _text(site.banner_html(day, {}))
    panel = _text(site.daily_line_panel("R", day))
    for html in (banner, panel):
        assert "withheld under the privacy floor" not in html
        assert "Republicans' line is withheld because the model text failed a publication check and " \
               "then the deterministic composite failed one too" in html
        assert site.REJECTION_CATEGORY_TEXT["unbound-quote"] in html
    assert "Composite state:  withheld_verifier_failure" in panel
    assert "corrected" not in panel.split("Composite state:")[1].split()[0]


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


# --- 4d: the reproduction, expected to fail until the defect is fixed --------------------------

def _curly_apostrophe_binds_to_its_own_label() -> None:
    """The correct behaviour: a deterministic composite quoting a label verbatim is bound to it."""
    label = "to the president’s desk"
    ok, off = verify.quotes_bound_to_talking_points(
        f'7 of us carried "{label}".', {"talking_points": [{"label": label, "quote": label, "members": 7}]})
    assert ok, off


def test_EXPECTED_FAIL_curly_apostrophe_unbinds_a_label_from_its_own_quote():
    """REPRODUCTION of 2026-09-16 R (S74-15 P4d), expected-fail. quotes_bound_to_talking_points folds
    the quote's typography (_norm turns U+2019 into ') and then asks boilerplate.contains_gram whether
    the folded quote carries the UNFOLDED label; the tokens "president's" and "president’s"
    differ, so a deterministic composite quoting its own label verbatim fails binding. This test
    passes while the defect stands and fails once it is fixed: then delete it and keep the helper as
    a real test. No verifier check is changed here."""
    try:
        _curly_apostrophe_binds_to_its_own_label()
    except AssertionError:
        return
    raise AssertionError("the curly-apostrophe defect is fixed: convert this expected-fail test")
