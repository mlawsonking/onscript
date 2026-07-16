"""Ops: dead-man ntfy, budget governor, and the nightly public symmetry audit (§5.2, §6.4).

The symmetry report is the product's armor: it proves, every day, that both parties ran
through an identical instrument (same prompts_sha, same thresholds_sha, same pipeline), so an
asymmetric finding is reality's, not the instrument's.
"""
from __future__ import annotations

import json
import os

from . import config, llm, roster, util


def thresholds_sha() -> str:
    """Hash of every comparative threshold, so the site can prove both parties used the same ones."""
    knobs = {
        "SYNC_MIN_MEMBERS": config.SYNC_MIN_MEMBERS,
        "NGRAM_MIN": config.NGRAM_MIN, "NGRAM_MAX": config.NGRAM_MAX,
        "BOILERPLATE_DF_SHARE_MAX": config.BOILERPLATE_DF_SHARE_MAX,
        "NEAR_JOINT_JACCARD": config.NEAR_JOINT_JACCARD,
        "LEDGER_MIN_TOTAL_USES": config.LEDGER_MIN_TOTAL_USES,
        "QUIET_DAY_MAX_STATEMENTS": config.QUIET_DAY_MAX_STATEMENTS,
    }
    return util.sha256_hex(json.dumps(knobs, sort_keys=True))


def prompts_sha() -> dict:
    return {pid: llm.load_prompt(pid)["sha"] for pid in ("P1", "P2", "P3")}


def caucus_sizes(statements: list[dict]) -> dict:
    """Distinct members per party observed in the whole corpus — a self-contained caucus proxy
    (the corpus covers all current members with official sites, R2). No external roster needed."""
    seen = {p: set() for p in config.ALL_PARTIES}
    for s in statements:
        m = s.get("member") or {}
        p, bio = m.get("party"), m.get("bioguide")
        if p in seen and bio:
            seen[p].add(bio)
    return {p: len(v) for p, v in seen.items()}


def budget_governor(month_to_date_usd: float) -> str:
    """§6.4: >$8 warn, >$9.50 degrade (Sonnet->Haiku + trim), $10 Console hard cap is the backstop."""
    if month_to_date_usd > 9.5:
        return "degrade"
    if month_to_date_usd > 8.0:
        return "warn"
    return "nominal"


# ---------------------------------------------------------------------------
# Real LLM-spend ledger (strict budget). Per-month file, keyed by day so a re-run OVERWRITES that
# day's cost instead of double-counting. This is the code-side source of truth for month-to-date
# spend; the Anthropic Console is the authoritative backstop. Committed under data/derived/cost/.
# ---------------------------------------------------------------------------
def _cost_ledger_path(day: str):
    return config.DERIVED / "cost" / f"{day[:7]}.json"


def record_cost(day: str, usd: float, *, tokens_in: int = 0, tokens_out: int = 0, model: str = "") -> dict:
    """ACCUMULATE this run's real LLM spend into the day. Real re-runs (a manual re-dispatch, an
    overlapping cron) each bill fresh Anthropic money, so they ADD — overwriting would let the ledger
    keep only the last run and the $9 ceiling would under-count. A $0 deterministic re-run adds
    nothing and never clobbers a prior real cost. The Console cap is the hard backstop; a concurrent
    read-modify-write is still possible (documented) but the daily cadence makes it rare. Returns
    the updated month ledger. §voice-wiring (MEDIUM-4)."""
    path = _cost_ledger_path(day)
    ledger = util.read_json(path, {"month": day[:7], "days": {}})
    prev = ledger.setdefault("days", {}).get(day, {})
    ledger["days"][day] = {
        "usd": round(prev.get("usd", 0) + usd, 6),
        "tokens_in": prev.get("tokens_in", 0) + tokens_in,
        "tokens_out": prev.get("tokens_out", 0) + tokens_out,
        "calls": prev.get("calls", 0) + (1 if usd > 0 else 0),
        "model": model or prev.get("model", ""), "updated_at": util.now_utc_iso(),
    }
    ledger["total_usd"] = round(sum(d.get("usd", 0) for d in ledger["days"].values()), 6)
    util.write_json(path, ledger)
    return ledger


def month_to_date_usd(day: str, *, include_day: bool = False) -> float:
    """Total real LLM spend for day's month. Pre-flight checks exclude `day` (the run not yet made);
    displays/governor after record_cost pass include_day=True."""
    ledger = util.read_json(_cost_ledger_path(day), {})
    days = ledger.get("days") or {}
    return round(sum(v.get("usd", 0) for k, v in days.items() if include_day or k != day), 6)


def voice_budget_state(day: str, projected_usd: float = 0.0) -> str:
    """Pre-flight budget decision for the real LLM voice. 'halt' => use the deterministic voice
    (this run would cross the code ceiling); 'warn' => call but alert; 'nominal' => call. The $10
    Console cap is the last-line backstop below this. Includes today's ALREADY-recorded spend so a
    same-day re-dispatch still counts toward the ceiling. §voice-wiring (MEDIUM-4)."""
    mtd = month_to_date_usd(day, include_day=True)
    if mtd + max(0.0, projected_usd) >= config.LLM_MONTHLY_CEILING_USD:
        return "halt"
    if mtd >= config.LLM_MONTHLY_WARN_USD:
        return "warn"
    return "nominal"


def ntfy(title: str, message: str, *, priority: str = "default") -> dict:
    """Dead-man switch. Posts to ntfy.sh/<NTFY_TOPIC> if the secret is set; else logs (the topic
    is a secret and NEVER lives in the repo — CLAUDE.md constraint)."""
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print(f"[ntfy:{priority}] {title} — {message}")
        return {"sent": False, "reason": "no NTFY_TOPIC set (dev)"}
    try:  # pragma: no cover - requires the secret + network
        import urllib.request
        req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=message.encode(),
                                     headers={"Title": title, "Priority": priority}, method="POST")
        urllib.request.urlopen(req, timeout=15)
        return {"sent": True}
    except Exception as e:
        print(f"[ntfy-failed] {title}: {e}")
        return {"sent": False, "reason": str(e)}


def symmetry_report(day: str, statements: list[dict], per_party_llm: dict, *, freshness: dict,
                    degraded: bool) -> dict:
    """The §5.2 audit, per party, published on the Methodology page every day."""
    caucus = caucus_sizes(statements)  # full corpus caucus proxy (all members with official sites)
    parties: dict[str, dict] = {}
    for p in config.COMPOSITE_PARTIES:
        # DAY-SCOPED: every per-party row is THIS DAY's Lane-1 ingestion, consistent with the per-day
        # token/claim rows below — never the cumulative corpus total mislabeled under the day
        # (which read as "44,767 statements ingested today / 100% coverage"). §Session-5 fix.
        stmts = [s for s in statements
                 if (s.get("member") or {}).get("party") == p and s.get("lane") == 1
                 and s.get("published_at") == day]
        members = {(s.get("member") or {}).get("bioguide") for s in stmts if (s.get("member") or {}).get("bioguide")}
        llm_p = per_party_llm.get(p, {})
        parties[p] = {
            "statements_ingested": len(stmts),
            "members_covered": len(members),
            "caucus_size": caucus.get(p),
            "coverage_pct": round(100 * len(members) / caucus[p], 1) if caucus.get(p) else None,
            "tokens_in": llm_p.get("tokens_in", 0),
            "tokens_out": llm_p.get("tokens_out", 0),
            "claims_published": llm_p.get("claims_published", 0),
            "claims_dropped": llm_p.get("claims_dropped", 0),
        }
    report = {
        # `day_scoped` marks `statements_ingested` as THIS DAY's ingest. It changed meaning once
        # (Session 5: it used to be the cumulative corpus total under a per-day label), and a reader
        # medianing across that boundary reads a healthy day as a 99.6% collapse. Reports now say
        # which semantics they carry instead of leaving readers to infer it from a date.
        "schema_version": 1, "day": day, "day_scoped": True,
        "statement": "Identical instrument, both parties, audited nightly in public. "
                     "Asymmetric findings are reality's problem, not the instrument's.",
        "prompts_sha": prompts_sha(),
        "thresholds_sha": thresholds_sha(),
        "lane1_only": True,
        "degraded": degraded,
        "source_freshness": freshness,
        "parties": parties,
    }
    util.write_json(config.DERIVED / "symmetry" / f"{day}.json", report)
    util.write_json(config.DERIVED / "symmetry" / "latest.json", report)
    return report
