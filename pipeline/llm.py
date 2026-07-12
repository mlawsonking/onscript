"""LLM layer: prompt loading, pricing/budget, and the model client (§6).

TWO MODES, chosen automatically:
  * REAL — used ONLY when ANTHROPIC_API_KEY is set. Submits the Anthropic Message Batches
    API (Haiku for extraction, Sonnet for the 2 Daily Lines), with a direct-call fallback for
    the batch-timeout kill-test. Implemented and ready; NEVER invoked without the key.
  * DRY-RUN — the default whenever the key is absent (or ONSCRIPT_DRY_RUN=1). Produces
    deterministic, schema-valid, verifier-passing output from the real corpus, so the whole
    streak machine runs end-to-end for $0. Dry-run outputs are tagged generator="dry_run" and
    the site/methodology disclose it.

The verifier (verify.py) is generator-agnostic — it checks the OUTPUT TEXT regardless of who
produced it. The generator is a commodity; the verifier is the product (§1.3).
"""
from __future__ import annotations

import json
import os
import re

from . import config, util

PROMPTS_DIR = config.REPO_ROOT / "pipeline" / "prompts"

# Pinned price table (USD per 1M tokens), re-pin each build (research §6, live 2026-07-10).
# Sonnet 5 introductory pricing ends Sep 1 2026 -> re-verify before then (gameplan handoff).
PRICING = {
    "claude-haiku-4-5":  {"in": 1.0, "out": 5.0, "batch_in": 0.50, "batch_out": 2.50, "cache_read": 0.10},
    "claude-sonnet-5":   {"in": 2.0, "out": 10.0, "batch_in": 1.0, "batch_out": 5.0, "cache_read": 0.20,
                          "note": "introductory through 2026-08-31; then 3/15 (batch 1.5/7.5)"},
}
EXTRACT_MODEL = "claude-haiku-4-5"
VOICE_MODEL = "claude-sonnet-5"


def dry_run() -> bool:
    if os.environ.get("ONSCRIPT_DRY_RUN") == "1":
        return True
    return not os.environ.get("ANTHROPIC_API_KEY")


def estimate_cost(model: str, tokens_in: int, tokens_out: int, *, batched: bool = True,
                  cached_in: int = 0) -> float:
    p = PRICING[model]
    ki, ko = ("batch_in", "batch_out") if batched else ("in", "out")
    billable_in = max(0, tokens_in - cached_in)
    cost = (billable_in * p[ki] + cached_in * p["cache_read"] + tokens_out * p[ko]) / 1_000_000
    return round(cost, 6)


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # ~4 chars/token (Haiku tokenizer; Sonnet 5 budgeted +30% at call sites)


# ---------------------------------------------------------------------------
# Prompts (the instrument — versioned, public; §5.3)
# ---------------------------------------------------------------------------
_PROMPT_FILES = {
    "P1": "P1_extraction.v1.0.txt",
    "P2": "P2_daily_line.v1.0.txt",
    "P3": "P3_quiet_day.v1.0.txt",
    "P4": "P4_era_chapter.v1.0.txt",  # Alexandria era chapters (subscription-generated, §1.3)
}
_VERSION_RE = re.compile(r"\.v(\d+\.\d+)\.txt$")


def load_prompt(pid: str) -> dict:
    fname = _PROMPT_FILES[pid]
    raw = (PROMPTS_DIR / fname).read_text(encoding="utf-8").strip()
    version = (_VERSION_RE.search(fname) or [None, "0.0"])[1]
    system, _, user = raw.partition("\n---USER---\n")
    system = system.split("SYSTEM:", 1)[-1].strip()
    return {"id": pid, "file": fname, "version": version, "sha": util.sha256_hex(raw),
            "system": system, "user_template": user.strip()}


# ---------------------------------------------------------------------------
# REAL Anthropic Message Batches client (gated on the key; never runs in dry-run).
# Implemented per the public Batches API; UNTESTED here by design (no key = no spend).
# ---------------------------------------------------------------------------
_API = "https://api.anthropic.com/v1/messages/batches"


def _headers() -> dict:
    return {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
            "content-type": "application/json"}


def submit_batch(requests: list[dict]) -> str:  # pragma: no cover - requires key
    import urllib.request
    body = json.dumps({"requests": requests}).encode()
    req = urllib.request.Request(_API, data=body, headers=_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["id"]


def poll_batch(batch_id: str) -> dict:  # pragma: no cover - requires key
    import urllib.request
    req = urllib.request.Request(f"{_API}/{batch_id}", headers=_headers())
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def direct_call(model: str, system: str, user: str, *, max_tokens: int = 400) -> str:  # pragma: no cover
    """Non-batch fallback for the batch-timeout kill-test (§4 B3). Pennies; protects the streak."""
    import urllib.request
    body = json.dumps({"model": model, "max_tokens": max_tokens, "system": system,
                       "messages": [{"role": "user", "content": user}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                                 headers=_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    return "".join(b.get("text", "") for b in data.get("content", []))
