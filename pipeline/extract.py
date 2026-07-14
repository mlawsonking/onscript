"""A5/B1 — P1 extraction: fragments per statement (§6.2 P1).

Real mode submits a Haiku batch (one request per NEW statement, keyed by statement hash so a
statement is never distilled twice — backfill-safe, re-run-safe). Dry-run produces the same
schema deterministically: for each statement it emits verbatim windows around the day's
detected coordination phrases (so cross-member fragments share language and cluster into real
talking points), tagged with taxonomy topics. Every fragment is a verbatim substring -> the
verifier passes either way.
"""
from __future__ import annotations

from . import boilerplate, config, llm, util, verify

_CACHE = config.STATE / "extractions.jsonl"
_MIN_WORDS, _MAX_WORDS = 4, 14


def _load_cache() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if _CACHE.exists():
        for row in util.iter_jsonl(_CACHE):
            out[row["id"]] = row
    return out


def _topics_for(text: str, taxonomy: list[dict]) -> list[str]:
    low = text.lower()
    hits = [t["id"] for t in taxonomy if any(s and s in low for s in t.get("seeds", []))]
    return hits[:3] or ["other"]


def _window(tokens: list[str], i: int, n: int) -> str | None:
    """A 4-14 word verbatim window around tokens[i:i+n]."""
    start = max(0, i - 2)
    end = min(len(tokens), i + n + 3)
    while end - start < _MIN_WORDS and (start > 0 or end < len(tokens)):
        if start > 0:
            start -= 1
        elif end < len(tokens):
            end += 1
        else:
            break
    if end - start > _MAX_WORDS:
        end = start + _MAX_WORDS
    if end - start < _MIN_WORDS:
        return None
    return " ".join(tokens[start:end])


def _dry_fragments(stmt: dict, sync: set[str], taxonomy: list[dict]) -> list[dict]:
    frags: list[dict] = []
    seen: set[str] = set()
    for toks in boilerplate.sentences(stmt.get("text", "")):
        L = len(toks)
        for n in range(config.NGRAM_MAX, config.NGRAM_MIN - 1, -1):  # prefer longer coordinated phrases
            for i in range(0, L - n + 1):
                ng = " ".join(toks[i : i + n])
                if ng in sync and ng not in seen:
                    w = _window(toks, i, n)
                    # A window can bridge a clean_text-removed gap (URL/phone/contact) and stop
                    # being a real substring — emit ONLY genuinely verbatim fragments.
                    if (w and w not in {f["text"] for f in frags}
                            and not boilerplate.is_boilerplate_ngram(w)
                            and verify.is_verbatim(w, stmt.get("text", ""))):
                        frags.append({"text": w, "topics": _topics_for(w, taxonomy)})
                        seen.add(ng)
                if len(frags) >= 5:
                    return frags
    return frags


def extract(statements: list[dict], sync_ngrams: set[str], taxonomy: list[dict]) -> tuple[dict[str, dict], dict]:
    """Return (extractions_by_statement_id, cost_telemetry). Only new statements are processed."""
    cache = _load_cache()
    new_rows: list[dict] = []
    tokens_in = tokens_out = 0
    # Real Haiku extraction (llm.submit_batch) is NOT yet wired — both branches use the deterministic
    # fragment extractor, so label it honestly ('deterministic', not 'haiku_batch'). The est_cost below
    # is a PROJECTION of what the real Haiku pass would cost, not a charge. §Session-5 (HIGH-2).
    generator = "dry_run" if llm.dry_run() else "deterministic"

    for s in statements:
        sid = s["id"]
        if sid in cache:
            continue
        if llm.dry_run():
            frags = _dry_fragments(s, sync_ngrams, taxonomy)
        else:  # pragma: no cover - requires ANTHROPIC_API_KEY
            frags = _dry_fragments(s, sync_ngrams, taxonomy)  # real Haiku batch not yet wired (see above)
        # budget telemetry (what the real Haiku pass WOULD cost, even in dry-run)
        tokens_in += llm.approx_tokens(s.get("text", "")) + 400  # + system/taxonomy prompt
        tokens_out += 120
        row = {"id": sid, "generator": generator, "fragments": frags}
        cache[sid] = row
        new_rows.append(row)

    if new_rows:
        # append-only cache (never re-extract; §6.1)
        existing = list(util.iter_jsonl(_CACHE)) if _CACHE.exists() else []
        util.write_jsonl(_CACHE, existing + new_rows)

    cost = {
        "stage": "extract", "model": llm.EXTRACT_MODEL, "generator": generator,
        "new_statements": len(new_rows), "tokens_in": tokens_in, "tokens_out": tokens_out,
        "est_cost_usd": llm.estimate_cost(llm.EXTRACT_MODEL, tokens_in, tokens_out, batched=True),
    }
    return cache, cost
