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
import zlib
from collections import defaultdict

from . import config, util

_WS = re.compile(r"\s+")
_WORD = re.compile(r"[a-z0-9']+")


def _shingles(text: str, k: int) -> frozenset:
    # crc32 (not builtin hash()) so shingle sets are identical across runs/machines ->
    # near-dup clustering is deterministic, which rebuild.py (§1.4.8) depends on.
    toks = _WORD.findall(_norm_ws(text).lower())
    if len(toks) < k:
        return frozenset()
    return frozenset(
        zlib.crc32((" ".join(toks[i : i + k])).encode("utf-8")) for i in range(len(toks) - k + 1)
    )


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)
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
    """Assign a shared joint_group to same-day near-identical multi-member statements.
    Length-sorted windowed comparison bounds cost to ~O(n*window). Returns #groups formed."""
    by_day: dict[str, list[dict]] = defaultdict(list)
    for s in statements:
        if s["joint_group"] is None and (s.get("member") or {}).get("bioguide"):
            by_day[s["published_at"]].append(s)

    formed = 0
    for day, group in by_day.items():
        cand = []
        for s in group:
            sh = _shingles(s.get("text", ""), config.NEAR_JOINT_SHINGLE_K)
            if len(sh) >= config.NEAR_JOINT_MIN_TOKENS - config.NEAR_JOINT_SHINGLE_K + 1:
                cand.append((s, sh))
        if len(cand) < 2:
            continue
        cand.sort(key=lambda x: len(x[1]))
        parent = list(range(len(cand)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        w = config.NEAR_JOINT_WINDOW
        for i in range(len(cand)):
            for j in range(i + 1, min(i + 1 + w, len(cand))):
                if _jaccard(cand[i][1], cand[j][1]) >= config.NEAR_JOINT_JACCARD:
                    parent[find(i)] = find(j)

        clusters: dict[int, list[dict]] = defaultdict(list)
        for idx, (s, _sh) in enumerate(cand):
            clusters[find(idx)].append(s)
        for root, members in clusters.items():
            bios = {(m.get("member") or {}).get("bioguide") for m in members}
            if len(members) > 1 and len(bios) > 1:
                gid = "njoint:" + util.sha256_hex(day + members[0]["id"])[:20]
                formed += 1
                for m in members:
                    m["joint_group"] = gid
    return formed
