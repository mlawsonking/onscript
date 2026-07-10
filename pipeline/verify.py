"""B4 — the deterministic citation verifier (§6.3). Blocking; code, never a model.

Three checks, all mechanical (the hallucination surface for statistics is zero by
construction, §11.5):
  1. substring   — every quoted fragment is a verbatim substring of its cited statement
                   (whitespace-normalized, case-insensitive: robust to rendering, but any
                   invented or paraphrased word fails).
  2. quorum      — every published claim traces to >= 3 DISTINCT members (§1.4.2).
  3. digit-whitelist — every number that appears in a composite Daily Line also appears in
                   the code-computed STATS block; the model may copy numbers, never invent
                   or compute them (§6.2 P2 rule 3).

A violation drops the claim (logged, never hand-patched, §4 B4). If a party's Daily Line
loses all claims, the honest fallback line publishes (§7.2) — never silence.
"""
from __future__ import annotations

import re

_WS = re.compile(r"\s+")
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _norm(text: str) -> str:
    return _WS.sub(" ", (text or "")).strip().lower()


def is_verbatim(fragment: str, source_text: str) -> bool:
    frag = _norm(fragment)
    return bool(frag) and frag in _norm(source_text)


def _numbers(text: str) -> set[str]:
    return {m.group(0).replace(",", "") for m in _NUM.finditer(text or "")}


def numbers_whitelisted(composite_text: str, stats_blob: str) -> tuple[bool, set[str]]:
    allowed = _numbers(stats_blob)
    used = _numbers(composite_text)
    offending = used - allowed
    return (len(offending) == 0, offending)


def verify_talking_point(tp: dict, statements_by_id: dict[str, dict]) -> tuple[bool, list[str]]:
    """Return (ok, reasons). A talking point is publishable iff >=3 distinct members and
    every fragment is verbatim in its cited statement."""
    reasons: list[str] = []
    members: set[str] = set()
    for sid in tp.get("statements", []):
        s = statements_by_id.get(sid)
        if s:
            bio = (s.get("member") or {}).get("bioguide")
            if bio:
                members.add(bio)
    if len(members) < 3:
        reasons.append(f"quorum: {len(members)} distinct members (<3)")
    for frag in tp.get("fragments", []):
        sid = frag.get("statement")
        src = statements_by_id.get(sid, {})
        if not is_verbatim(frag.get("text", ""), src.get("text", "")):
            reasons.append(f"non-verbatim fragment: {frag.get('text','')!r}")
    return (len(reasons) == 0, reasons)


def verify_daily_line(distillation: dict, stats_blob: str) -> tuple[bool, list[str]]:
    ok_nums, offending = numbers_whitelisted(distillation.get("composite", ""), stats_blob)
    reasons: list[str] = []
    if not ok_nums:
        reasons.append(f"un-whitelisted numbers in composite: {sorted(offending)}")
    return (len(reasons) == 0, reasons)


def verify_day(distillation: dict, talking_points: list[dict], statements_by_id: dict[str, dict],
               stats_blob: str) -> dict:
    """Full B4 report for one party-day. Drops failing claims; reports counts."""
    published_tps: list[dict] = []
    dropped: list[dict] = []
    fragments_checked = 0
    for tp in talking_points:
        fragments_checked += len(tp.get("fragments", []))
        ok, reasons = verify_talking_point(tp, statements_by_id)
        (published_tps if ok else dropped).append({"id": tp.get("id"), "reasons": reasons} if not ok else tp)
    line_ok, line_reasons = verify_daily_line(distillation, stats_blob)
    return {
        "fragments_checked": fragments_checked,
        "claims_in": len(talking_points),
        "claims_published": len(published_tps),
        "claims_dropped": len(dropped),
        "dropped": dropped,
        "daily_line_ok": line_ok,
        "daily_line_reasons": line_reasons,
        "failed": (0 if line_ok else 1),  # published-fragment failures are 0 by construction
    }
