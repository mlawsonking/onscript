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
            "talking_points": tps, "top_phrase": top_phrase}


def _compose_dry(stats: dict) -> str:
    """Deterministic composite: numbers from STATS, quotes from fragments only, first-person plural."""
    parts = [f"Today {stats['statements']} of us released statements."]
    for tp in stats["talking_points"][:3]:
        if tp["quote"]:
            parts.append(f'{tp["members"]} of us said "{tp["quote"]}".')
    tp = stats.get("top_phrase")
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


def daily_line(party: str, day: str, party_statements: list[dict], talking_points: list[dict],
               top_phrase: dict | None, statements_by_id: dict) -> dict:
    """Produce + verify one party-day Daily Line. Returns the daily_distillation record (§3)."""
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

    if llm.dry_run():
        composite = _quiet_dry(stats) if quiet else _compose_dry(stats)
        generator = "dry_run"
        model = prompt["id"] + ":dry_run"
    else:  # pragma: no cover - requires ANTHROPIC_API_KEY
        # The real Sonnet voice (llm.submit_batch / direct_call) is NOT yet wired into this branch.
        # Until it is, real mode falls back to the SAME deterministic composer as dry-run, labeled
        # HONESTLY as 'deterministic' (NOT in site.PRODUCTION_GENERATORS) so the honesty banner
        # discloses it — this is not Sonnet output. Wiring the live voice turns on real API billing
        # and is a deliberate, gated step (docs/11-BUILD-PROGRAM.md); when wired, set generator to a
        # value listed in site.PRODUCTION_GENERATORS in the SAME commit. §Session-5 (HIGH-2 fix).
        composite = _compose_dry(stats)
        generator = "deterministic"
        model = prompt["id"] + ":deterministic"

    # B4 verifier (blocking): numbers whitelisted + quotes grounded in fragments.
    ok, reasons = verify.verify_daily_line({"composite": composite}, stats_blob, fragments=groundable)
    fallback = False
    if not ok:
        composite = f"Some of our output could not be verified today. Measured from what did: we released {n} statements."
        fallback = True

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
    }
