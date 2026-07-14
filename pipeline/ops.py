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
        "schema_version": 1, "day": day,
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
