"""Real Sonnet Daily-Line voice wiring + STRICT budget (voice-wiring).

The voice fires ONLY behind the LLM_VOICE_ENABLED gate AND a key AND budget room; the deterministic
verifier still gates the output; spend is tracked in a month-to-date ledger with a hard ceiling.

Every test runs $0: llm.dry_run / llm.direct_call are monkeypatched, NO key is ever set, and NO API
call is made. This proves the wiring end-to-end without spending a cent.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, distill, llm, ops  # noqa: E402


def _party_stmts(n, party="D"):
    return [{"id": f"s{i}", "text": "x", "member": {"bioguide": str(i), "party": party},
             "published_at": "2026-07-13", "lane": 1} for i in range(n)]


def _tps():
    return [{"id": "c1", "label": "border security now", "member_count": 3, "topics": ["immigration"],
             "fragments": [{"text": "we support border security now", "statement": "s1"}]}]


def _swap(**attrs):
    """Swap llm attributes; return restore()."""
    saved = {k: getattr(llm, k) for k in attrs}
    for k, v in attrs.items():
        setattr(llm, k, v)
    return lambda: [setattr(llm, k, v) for k, v in saved.items()]


# --- the gate -----------------------------------------------------------------------------
def test_llm_voice_enabled_gate_defaults_off():
    saved = os.environ.pop("LLM_VOICE_ENABLED", None)
    try:
        assert config.llm_voice_enabled() is False           # default OFF -> $0
        os.environ["LLM_VOICE_ENABLED"] = "true"
        assert config.llm_voice_enabled() is True
        os.environ["LLM_VOICE_ENABLED"] = "false"
        assert config.llm_voice_enabled() is False
    finally:
        os.environ.pop("LLM_VOICE_ENABLED", None)
        if saved is not None:
            os.environ["LLM_VOICE_ENABLED"] = saved


def test_voice_gated_off_uses_deterministic_even_with_key():
    """Gate OFF (allow_llm_voice=False) + key present => deterministic voice, NEVER an API call."""
    restore = _swap(dry_run=lambda: False,
                    direct_call=lambda *a, **k: (_ for _ in ()).throw(AssertionError("called with gate off!")))
    try:
        dl = distill.daily_line("D", "2026-07-13", _party_stmts(40), _tps(), None, {}, allow_llm_voice=False)
        assert dl["generator"] == "deterministic"
        assert dl["usage"]["tokens_in"] == 0 and dl["usage"]["tokens_out"] == 0
    finally:
        restore()


def test_dry_run_ignores_gate():
    """No key => llm.dry_run() True => always deterministic/dry_run even if allow_llm_voice=True."""
    dl = distill.daily_line("D", "2026-07-13", _party_stmts(40), _tps(), None, {}, allow_llm_voice=True)
    assert dl["generator"] == "dry_run" and dl["usage"]["tokens_in"] == 0


# --- the real voice path ------------------------------------------------------------------
def test_voice_on_calls_sonnet_and_records_real_usage():
    """Gate ON + key + budget ok => real voice; labeled sonnet_direct (a production generator);
    the API's own token usage is captured for the spend ledger."""
    restore = _swap(dry_run=lambda: False,
                    direct_call=lambda model, system, user, **k: {
                        "text": 'Today 40 of us released statements. 3 of us said "we support border security now".',
                        "tokens_in": 1400, "tokens_out": 180})
    try:
        dl = distill.daily_line("D", "2026-07-13", _party_stmts(40), _tps(), None, {}, allow_llm_voice=True)
        assert dl["generator"] == "sonnet_direct" and dl["model"] == llm.VOICE_MODEL
        assert dl["usage"]["tokens_in"] == 1400 and dl["usage"]["tokens_out"] == 180
        assert dl["verifier"]["passed"] is True and dl["fallback"] is False
    finally:
        restore()


def test_voice_output_failing_verifier_falls_back_but_records_tokens():
    """An ungrounded LLM quote / invented number fails the blocking verifier => the deterministic
    fallback text is published (never the hallucination), but the tokens we already paid ARE recorded."""
    restore = _swap(dry_run=lambda: False,
                    direct_call=lambda *a, **k: {
                        "text": 'We said "a phrase no member ever wrote" across 9999 statements.',
                        "tokens_in": 1400, "tokens_out": 200})
    try:
        dl = distill.daily_line("D", "2026-07-13", _party_stmts(40), _tps(), None, {}, allow_llm_voice=True)
        assert dl["verifier"]["passed"] is False and dl["fallback"] is True
        assert "a phrase no member ever wrote" not in dl["composite"]  # hallucination never published
        assert "9999" not in dl["composite"]
        assert dl["usage"]["tokens_in"] == 1400  # paid tokens are still recorded honestly
    finally:
        restore()


def test_fabricated_aggregate_from_a_quote_number_is_rejected():
    """HIGH-1: a number that appears only inside a member QUOTE (not a code-computed count) can never
    be published UNQUOTED as a fabricated aggregate."""
    tps = [{"id": "c1", "label": "cut wasteful programs", "member_count": 3, "topics": [],
            "fragments": [{"text": "we voted to cut all 87 wasteful programs", "statement": "s1"}]}]
    restore = _swap(dry_run=lambda: False,
                    direct_call=lambda *a, **k: {
                        "text": "Today 40 of us released statements. 87 of us stood firm.",  # 87 is fabricated
                        "tokens_in": 1400, "tokens_out": 120})
    try:
        dl = distill.daily_line("D", "2026-07-13", _party_stmts(40), tps, None, {}, allow_llm_voice=True)
        assert dl["verifier"]["passed"] is False and dl["fallback"] is True
        assert "87 of us" not in dl["composite"]
        assert dl["generator"] == "deterministic" and dl["model"].endswith(":fallback")  # LOW-6 relabel
    finally:
        restore()


def test_empty_voice_response_never_publishes_blank():
    """HIGH-2: an empty/whitespace Sonnet response drops to the deterministic voice — never a blank
    published line — and the billed tokens are still recorded."""
    restore = _swap(dry_run=lambda: False,
                    direct_call=lambda *a, **k: {"text": "   ", "tokens_in": 900, "tokens_out": 0})
    try:
        dl = distill.daily_line("D", "2026-07-13", _party_stmts(40), _tps(), None, {}, allow_llm_voice=True)
        assert dl["composite"].strip() and dl["generator"] == "deterministic"
        assert dl["usage"]["tokens_in"] == 900  # paid tokens recorded even though the text was empty
    finally:
        restore()


def test_quote_dropping_a_leading_negation_is_rejected():
    """MEDIUM-3: a verbatim span that drops a leading 'never' inverts meaning and is NOT grounded."""
    tps = [{"id": "c1", "label": "defund the police", "member_count": 3, "topics": [],
            "fragments": [{"text": "we will never vote to defund the police", "statement": "s1"}]}]
    restore = _swap(dry_run=lambda: False,
                    direct_call=lambda *a, **k: {
                        "text": 'Today 40 of us released statements. 3 of us said "vote to defund the police".',
                        "tokens_in": 1400, "tokens_out": 120})
    try:
        dl = distill.daily_line("D", "2026-07-13", _party_stmts(40), tps, None, {}, allow_llm_voice=True)
        assert dl["verifier"]["passed"] is False and dl["fallback"] is True
    finally:
        restore()


def test_no_coordination_line_states_the_absence_honestly():
    """A party with statements but zero cleared talking points reports the ABSENCE (the silence story)
    instead of a bare count — and the threshold number is whitelisted so it still verifies."""
    stmts = _party_stmts(51)
    dl = distill.daily_line("D", "2026-07-13", stmts, [], None, {s["id"]: s for s in stmts})
    assert "No phrase was shared" in dl["composite"]
    assert dl["verifier"]["passed"] is True and dl["fallback"] is False


def test_voice_transport_error_falls_back_no_crash():
    """An API/transport error never crashes the run — deterministic fallback, zero recorded tokens."""
    def boom(*a, **k):
        raise RuntimeError("api 500")
    restore = _swap(dry_run=lambda: False, direct_call=boom)
    try:
        dl = distill.daily_line("D", "2026-07-13", _party_stmts(40), _tps(), None, {}, allow_llm_voice=True)
        assert dl["generator"] == "deterministic" and dl["usage"]["tokens_in"] == 0
    finally:
        restore()


# --- the spend ledger (strict budget) -----------------------------------------------------
def test_cost_ledger_accumulates_real_spend_across_reruns():
    store = {}
    saved_w, saved_r = ops.util.write_json, ops.util.read_json
    ops.util.write_json = lambda p, o: store.__setitem__(str(p), o)
    ops.util.read_json = lambda p, default=None: store.get(str(p), default if default is not None else {})
    try:
        ops.record_cost("2026-07-10", 0.01, tokens_in=1000, tokens_out=100, model="claude-sonnet-5")
        ops.record_cost("2026-07-11", 0.02, tokens_in=2000, tokens_out=200)
        assert abs(ops.month_to_date_usd("2026-07-12") - 0.03) < 1e-9   # pre-flight sees both prior days
        # a REAL re-run of a day ADDS (each run bills real money) — never lost, never clobbered
        ops.record_cost("2026-07-11", 0.05)
        assert abs(ops.month_to_date_usd("2026-07-12") - 0.08) < 1e-9   # 0.01 + (0.02 + 0.05)
        # a $0 deterministic re-run adds nothing and does NOT clobber the accumulated real cost
        ops.record_cost("2026-07-11", 0.0)
        assert abs(ops.month_to_date_usd("2026-07-11", include_day=True) - 0.08) < 1e-9
    finally:
        ops.util.write_json, ops.util.read_json = saved_w, saved_r


def test_voice_budget_state_halts_before_the_ceiling():
    saved_r = ops.util.read_json
    try:
        ops.util.read_json = lambda p, default=None: {"days": {"2026-07-01": {"usd": 0.0}}}
        assert ops.voice_budget_state("2026-07-02", 0.02) == "nominal"
        ops.util.read_json = lambda p, default=None: {"days": {"2026-07-01": {"usd": 8.5}}}
        assert ops.voice_budget_state("2026-07-02", 0.02) == "warn"
        ops.util.read_json = lambda p, default=None: {"days": {"2026-07-01": {"usd": 8.99}}}
        assert ops.voice_budget_state("2026-07-02", 0.02) == "halt"  # 8.99 + 0.02 >= 9.0 ceiling
    finally:
        ops.util.read_json = saved_r
