"""A3 — normalize the congress-press corpus into the statement schema (§3).

Responsibilities (gameplan §4 A3):
  * map upstream record -> statement (schema_version 1)
  * dedupe by id (never process the same statement twice)
  * drop/flag syndicated reprints (they are not the member's own coordinated voice, R2)
  * collapse joint releases: same-day byte-identical text by N members -> one joint_group,
    all members credited, EXCLUDED from independent-adoption counts (§11 trap 2)

Everything here is deterministic; malformed records are quarantined, not fatal (§4 A3).
"""
from __future__ import annotations

import re
from collections import defaultdict

from . import config, document_families, util

_WS = re.compile(r"\s+")
_WORD = re.compile(r"[a-z0-9']+")


_SYNDICATION = re.compile(
    r"^\W{0,40}(originally (published|appeared)|first appeared|as (published|seen) in|"
    r"this (op-?ed|column|piece) (originally|first))",
    re.IGNORECASE,
)


def _norm_ws(text: str) -> str:
    return _WS.sub(" ", (text or "").strip())


def _party(raw: str | None) -> str | None:
    return config.PARTY_NORMALIZE.get((raw or "").strip().lower(), None)


def _chamber(raw: str | None) -> str | None:
    return config.CHAMBER_NORMALIZE.get((raw or "").strip().lower(), None)


def is_syndicated(text: str) -> bool:
    head = _norm_ws(text)[:240]
    return bool(_SYNDICATION.search(head))


def _joint_signature(day: str, text: str) -> str:
    """Signature for joint-release detection: same day + case/space-normalized full text."""
    return util.sha256_hex(day + "\x00" + _norm_ws(text).lower())


def normalize_records(records, *, run_id: str, roster: dict | None = None):
    """Yield normalized statement dicts from raw congress-press records.

    Two passes: (1) build statements + detect exact-duplicate ids; (2) assign joint_group
    for same-day identical text released by >1 distinct member.
    """
    roster = roster or {}
    seen_ids: set[str] = set()
    statements: list[dict] = []
    rejects = 0
    sig_members: dict[str, set[str]] = defaultdict(set)
    sig_to_stmts: dict[str, list[dict]] = defaultdict(list)

    for rec in records:
        try:
            url = (rec.get("url") or "").strip()
            text = rec.get("text") or ""
            if not url or not text.strip():
                rejects += 1
                continue
            sid = util.statement_id(url, text)
            if sid in seen_ids:
                continue  # exact dup -> never process twice
            seen_ids.add(sid)

            m = rec.get("member") or {}
            bio = (m.get("bioguide_id") or m.get("bioguide") or "").strip() or None
            party = _party(m.get("party"))
            chamber = _chamber(m.get("chamber"))
            state = (m.get("state") or "").strip() or None
            # Roster canonicalization (non-blocking enrichment): fill gaps, trust corpus otherwise.
            r = roster.get(bio or "", {})
            party = party or r.get("party")
            chamber = chamber or r.get("chamber")
            state = state or r.get("state")

            day = (rec.get("date") or "")[:10]
            if len(day) != 10:
                rejects += 1
                continue

            stmt = {
                "schema_version": config.__dict__.get("SCHEMA_VERSION", 1) or 1,
                "id": sid,
                "source": "press_release",
                "lane": config.LANE_BY_SOURCE["press_release"],
                "url": url,
                "title": (rec.get("title") or "").strip(),
                "text": text,
                "published_at": day,
                "precision": "day",
                "observed_at": rec.get("collected_at") or util.now_utc_iso(),
                "member": {
                    "bioguide": bio,
                    "name": (m.get("name") or "").strip() or (r.get("name") if bio else None),
                    "party": party,
                    "state": state,
                    "chamber": chamber,
                    "leadership_role": None,  # v3 (§11.4)
                },
                "congress": util.congress_for_date(day),
                "joint_group": None,
                "syndicated": is_syndicated(text),
                "copyright_basis": config.COPYRIGHT_BY_SOURCE["press_release"],
                "run_id": run_id,
            }
            statements.append(stmt)
            if bio:
                sig = _joint_signature(day, text)
                sig_members[sig].add(bio)
                sig_to_stmts[sig].append(stmt)
        except Exception:
            rejects += 1
            continue

    # Pass 2a: exact joint-collapse. A signature shared by >1 distinct member is a joint release.
    joint_groups = 0
    for sig, members in sig_members.items():
        if len(members) > 1:
            gid = "joint:" + sig[:24]
            joint_groups += 1
            for s in sig_to_stmts[sig]:
                s["joint_group"] = gid

    # Pass 2b: near-identical (delegation) collapse (§11 trap 2). Within a day, cluster
    # not-yet-grouped statements whose shingle Jaccard >= threshold; a multi-member cluster
    # is one coordinated document, not independent adoption.
    near_joint_groups = _near_dup_collapse(statements)
    document_families.annotate_all_families(statements)

    normalize_records.last_stats = {  # type: ignore[attr-defined]
        "in": len(statements) + rejects,
        "kept": len(statements),
        "rejects": rejects,
        "joint_groups": joint_groups,
        "near_joint_groups": near_joint_groups,
        "syndicated": sum(1 for s in statements if s["syndicated"]),
    }
    return statements


def _near_dup_collapse(statements: list[dict]) -> int:
    """Compatibility wrapper for the W7 document-family implementation."""
    return document_families.apply_families(statements)
