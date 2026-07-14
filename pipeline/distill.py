"""B3/B4 — the Daily Line: P2 composite per party per day, then the blocking verifier (§6.2/§6.3).

Real mode calls Sonnet (batch, direct-call fallback for the timeout kill-test). Dry-run
composes a deterministic first-person-plural composite using ONLY the code-computed STATS
numbers and verbatim fragment quotes (<=10 words) — so it passes the digit-whitelist and
quote-grounding checks by construction. Either way the composite is run through the verifier;
any violation drops the line to the honest fallback (§7.2), never silence.
"""
from __future__ import annotations

import json

from . import config, llm, util, verify

_QUOTE_MAX_WORDS = 10


def _quote(fragment_text: str) -> str:
    return " ".join((fragment_text or "").split()[:_QUOTE_MAX_WORDS])


def build_stats(party: str, day: str, party_statement_count: int, talking_points: list[dict],
                top_phrase: dict | None) -> dict:
    """Code-computed STATS block — the ONLY source of numbers the composite may use (§6.2 P2 rule 3)."""
    tps = []
    for tp in talking_points[:4]:
        # The quote MUST be verbatim member speech: the blocking verifier grounds it against real
        # fragment text, NEVER against the code-computed label (a punctuation-stripped n-gram that is
        # often not a raw substring of any statement — quoting it would violate citation integrity).
        # Pick the SHORTEST fragment in the cluster: on-topic (all fragments share the label phrase),
        # complete, and clean — not a mid-truncated long one that dangles. The label rides along as
        # the UNQUOTED talking-point name. §Session-5 (HIGH-1 fix).
        frags = [f["text"] for f in (tp.get("fragments") or []) if f.get("text")]
        quote = _quote(min(frags, key=lambda t: len(t.split()))) if frags else ""
        tps.append({"label": tp["label"], "members": tp["member_count"], "quote": quote,
                    "topics": tp.get("topics", [])})
    return {"party": party, "day": day, "statements": party_statement_count,
            "talking_points": tps, "top_phrase": top_phrase,
            "sync_min": config.SYNC_MIN_MEMBERS}  # the coordination threshold (for the no-coordination line)


def _compose_dry(stats: dict) -> str:
    """Deterministic composite: numbers from STATS, quotes from fragments only, first-person plural."""
    parts = [f"Today {stats['statements']} of us released statements."]
    quoted = 0
    for tp in stats["talking_points"][:3]:
        if tp["quote"]:
            parts.append(f'{tp["members"]} of us said "{tp["quote"]}".')
            quoted += 1
    tp = stats.get("top_phrase")
    if quoted == 0 and not (tp and tp.get("text")):
        # Honest measured ABSENCE: statements went out, but no phrase cleared the coordination bar.
        # This turns an empty column into a finding (the silence story), not a missing feature.
        parts.append(f"No phrase was shared by {stats.get('sync_min', config.SYNC_MIN_MEMBERS)} "
                     f"or more of us today.")
    if tp and tp.get("text"):
        # No quotation marks: the top synchronized phrase is a code-computed ledger n-gram, not a
        # verbatim member quote — render it as the measured phrase it is (§Session-5 HIGH-1 fix).
        parts.append(f'Our most synchronized phrase, in {tp["members"]} of our statements: {tp["text"]}.')
    text = " ".join(parts)
    words = text.split()
    if len(words) > 120:
        text = " ".join(words[:120])
    return text


def _quiet_dry(stats: dict) -> str:
    # Thin/quiet days still carry the one code-computed fact worth stating: the day's top
    # synchronized phrase + how many converged on it (§Session-4(g)). No LLM claim needed — the
    # phrase is a real ledger fact and is verifier-grounded in daily_line's groundable set.
    parts = [f"We released {stats['statements']} statements today."]
    tp = stats.get("top_phrase")
    if tp and tp.get("text"):
        # No quotation marks — a code-computed ledger phrase, not a verbatim quote (§Session-5 HIGH-1).
        parts.append(f'Even so, {tp["members"]} of us converged on the same phrase: {tp["text"]}.')
    return " ".join(parts)


_PARTY_FULL = {"D": "Democratic", "R": "Republican"}


def _compose_llm(prompt: dict, stats: dict, party: str, day: str) -> tuple[str, int, int]:
    """Call the real Sonnet voice (synchronous direct call — 2/day, pennies). Returns
    (composite_text, tokens_in, tokens_out) from the API's own usage. Raises on transport error;
    the caller falls back to the deterministic voice, and the blocking verifier still gates whatever
    text is ultimately used, so an ungrounded LLM claim can never publish. §voice-wiring."""
    fills = {"{day}": day, "{party}": _PARTY_FULL.get(party, party),
             "{code_computed_stats_json}": json.dumps(stats, ensure_ascii=False),
             "{talking_points_json}": json.dumps(stats.get("talking_points", []), ensure_ascii=False)}
    system, user = prompt["system"], prompt["user_template"]
    for k, v in fills.items():
        system = system.replace(k, v)
        user = user.replace(k, v)
    res = llm.direct_call(llm.VOICE_MODEL, system, user, max_tokens=400)
    text = (res.get("text") or "").strip()
    # If the API omits usage, ESTIMATE (never record a billed call as free) — over-count is the safe
    # direction for a spend ledger. §voice-wiring (LOW-7a).
    tin = int(res.get("tokens_in") or 0) or (llm.approx_tokens(system) + llm.approx_tokens(user))
    tout = int(res.get("tokens_out") or 0) or max(1, llm.approx_tokens(text))
    return text, tin, tout


def daily_line(party: str, day: str, party_statements: list[dict], talking_points: list[dict],
               top_phrase: dict | None, statements_by_id: dict, allow_llm_voice: bool = False) -> dict:
    """Produce + verify one party-day Daily Line. Returns the daily_distillation record (§3).

    Voice selection: the real Sonnet voice fires ONLY when allow_llm_voice (run_assemble computes it
    from config.llm_voice_enabled() AND the budget governor) AND a key is present. Otherwise — gate
    off, budget halt, no key, or an API error — it is the honest deterministic voice. Either way the
    blocking verifier gates the output; a failure drops to the honest fallback, never silence."""
    n = len(party_statements)
    quiet = n < config.QUIET_DAY_MAX_STATEMENTS
    prompt = llm.load_prompt("P3" if quiet else "P2")

    # The blocking verifier grounds every quoted span ONLY against real, verbatim member speech
    # (fragment texts). Code-computed strings (cluster labels, the top synchronized phrase) are NEVER
    # added here — grounding a quote against a code-computed string would let it match itself and make
    # the check vacuous. Those facts are rendered WITHOUT quotation marks (as measured phrases), so the
    # verbatim-quote guarantee holds by construction. §Session-5 (HIGH-1 fix).
    all_fragment_texts = [f["text"] for tp in talking_points for f in tp["fragments"]]
    groundable = list(all_fragment_texts)

    stats = build_stats(party, day, n, talking_points, top_phrase)
    stats_blob = json.dumps(stats, ensure_ascii=False)

    tokens_in = tokens_out = 0
    if allow_llm_voice and not llm.dry_run():
        try:  # pragma: no cover - requires ANTHROPIC_API_KEY + LLM_VOICE_ENABLED
            composite, tokens_in, tokens_out = _compose_llm(prompt, stats, party, day)
            if not composite.strip():
                raise ValueError("empty composite from voice")   # never publish a blank line (HIGH-2)
            generator = "sonnet_direct"     # a real production voice (site.PRODUCTION_GENERATORS)
            model = llm.VOICE_MODEL
        except Exception as e:  # transport/API error/empty -> deterministic; a voice failure never crashes
            print(f"[voice:{party}] LLM voice failed ({e}); deterministic fallback")
            composite = _quiet_dry(stats) if quiet else _compose_dry(stats)
            generator = "deterministic"
            model = prompt["id"] + ":deterministic"
    elif llm.dry_run():
        composite = _quiet_dry(stats) if quiet else _compose_dry(stats)
        generator = "dry_run"
        model = prompt["id"] + ":dry_run"
    else:
        # Key present but the voice is gated OFF (LLM_VOICE_ENABLED) or the budget halted it:
        # the honest deterministic voice, $0. §voice-wiring.
        composite = _quiet_dry(stats) if quiet else _compose_dry(stats)
        generator = "deterministic"
        model = prompt["id"] + ":deterministic"

    # B4 verifier (blocking): every UNQUOTED number must be a code-computed count (the strict `stats`
    # whitelist — a digit inside a member quote can never become a fabricated aggregate), and every
    # quoted span must be verbatim, in-context member text. Failure -> honest fallback, never silence.
    ok, reasons = verify.verify_daily_line({"composite": composite}, stats_blob, fragments=groundable,
                                           stats=stats)
    fallback = False
    if not ok:
        composite = f"Some of our output could not be verified today. Measured from what did: we released {n} statements."
        fallback = True
        # The published text is now the deterministic fallback — attribute it honestly, never as the
        # model (the honesty banner + _voice_flags must not claim Sonnet wrote this). §LOW-6.
        generator = "deterministic"
        model = prompt["id"] + ":fallback"

    # sentence -> talking-point receipts mapping (which clusters back each sentence)
    receipts = [{"sentence_idx": i, "talking_points": [tp["id"] for tp in talking_points[:3]]}
                for i, _ in enumerate(composite.split(". "))]

    return {
        "schema_version": 1, "day": day, "party": party, "composite": composite,
        "quiet": quiet, "fallback": fallback,
        "sentence_receipts": receipts,
        "model": model, "generator": generator,
        "prompt_version": prompt["version"], "prompt_sha": prompt["sha"],
        "stats": stats,
        "verifier": {"checked": True, "passed": ok, "reasons": reasons,
                     "talking_points_published": len(talking_points)},
        # Real token usage for the spend ledger (0 unless the Sonnet voice actually fired). Tokens
        # are charged even if the verifier later dropped the line to fallback — record them honestly.
        "usage": {"tokens_in": tokens_in, "tokens_out": tokens_out, "model": model},
    }
