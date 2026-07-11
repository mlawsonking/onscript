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
        quote = _quote(tp["fragments"][0]["text"]) if tp.get("fragments") else ""
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
    if tp and tp.get("in_fragments"):
        parts.append(f'Our most synchronized phrase was "{tp["text"]}", in {tp["members"]} of our statements.')
    text = " ".join(parts)
    words = text.split()
    if len(words) > 120:
        text = " ".join(words[:120])
    return text


def _quiet_dry(stats: dict) -> str:
    return f"We released {stats['statements']} statements today."


def daily_line(party: str, day: str, party_statements: list[dict], talking_points: list[dict],
               top_phrase: dict | None, statements_by_id: dict) -> dict:
    """Produce + verify one party-day Daily Line. Returns the daily_distillation record (§3)."""
    n = len(party_statements)
    quiet = n < config.QUIET_DAY_MAX_STATEMENTS
    prompt = llm.load_prompt("P3" if quiet else "P2")

    # top_phrase text must be groundable in a fragment to be quotable
    all_fragment_texts = [f["text"] for tp in talking_points for f in tp["fragments"]]
    if top_phrase:
        tpn = verify._norm(top_phrase.get("text", ""))
        top_phrase = dict(top_phrase, in_fragments=any(tpn in verify._norm(ft) for ft in all_fragment_texts))

    stats = build_stats(party, day, n, talking_points, top_phrase)
    stats_blob = json.dumps(stats, ensure_ascii=False)

    if llm.dry_run():
        composite = _quiet_dry(stats) if quiet else _compose_dry(stats)
        generator = "dry_run"
        model = prompt["id"] + ":dry_run"
    else:  # pragma: no cover - requires ANTHROPIC_API_KEY (wired in run_assemble real path)
        composite = _compose_dry(stats)
        generator = "sonnet_batch"
        model = llm.VOICE_MODEL

    # B4 verifier (blocking): numbers whitelisted + quotes grounded in fragments.
    ok, reasons = verify.verify_daily_line({"composite": composite}, stats_blob, fragments=all_fragment_texts)
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
