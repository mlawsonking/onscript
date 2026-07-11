"""A2 — Bluesky Lane 2 ingest (§1.2, R3). Enrichment/citations only, never a cross-party number.

Reads member post history from the FREE public AppView (public.api.bsky.app), unauthenticated —
no key, no Anthropic spend. Normalizes to the statement schema with lane=2 + copyright_basis
"fair_use"; the phrase engine machine-excludes Lane 2 from every comparative metric (§5.1).

This is cut-line item #1 (§1.2): shipped with a SEED handle set. The full ~130-member
handle->DID map (keyed by resolved DID for time-series stability) is a v1.1 task; Bluesky is a
Democratic-skewed supplement (R3), never a symmetric source.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import config, util  # noqa: E402

APPVIEW = "https://public.api.bsky.app/xrpc"
_SEED_FILE = config.REFERENCE / "bluesky_seed.json"

# A small verified-live seed (R3). party = caucus; bioguide filled where known. Extend via the
# seed file (data/reference/bluesky_seed.json) which overrides/augments this.
DEFAULT_SEED = {
    "schiff.senate.gov": {"party": "D", "chamber": "senate", "bioguide": "S001150"},
    "booker.senate.gov": {"party": "D", "chamber": "senate", "bioguide": "B001288"},
    "warren.senate.gov": {"party": "D", "chamber": "senate", "bioguide": "W000817"},
    "aoc.bsky.social": {"party": "D", "chamber": "house", "bioguide": "O000172"},
}


def load_seed() -> dict:
    seed = dict(DEFAULT_SEED)
    seed.update(util.read_json(_SEED_FILE, {}) or {})
    return seed


def _resolve_did(handle: str) -> str | None:
    try:
        d = json.loads(util.http_get(f"{APPVIEW}/com.atproto.identity.resolveHandle?handle={handle}", timeout=20))
        return d.get("did")
    except Exception:
        return None


def poll_author(handle: str, hours: int = config.BLUESKY_POLL_HOURS) -> list[dict]:
    """Original posts (no reposts/replies) from the last `hours`. Skip-and-log on failure."""
    try:
        raw = util.http_get(f"{APPVIEW}/app.bsky.feed.getAuthorFeed?actor={handle}&limit=50&filter=posts_no_replies", timeout=25)
        feed = json.loads(raw).get("feed", [])
    except Exception as e:
        print(f"[bluesky-skip] {handle}: {e}")
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = []
    for item in feed:
        if item.get("reason"):  # repost
            continue
        post = item.get("post", {})
        rec = post.get("record", {})
        created = rec.get("createdAt", "")
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except Exception:
            continue
        if dt < cutoff:
            continue
        out.append({"uri": post.get("uri"), "text": rec.get("text", ""), "createdAt": created})
    return out


def to_statements(handle: str, meta: dict, posts: list[dict], run_id: str) -> list[dict]:
    out = []
    for p in posts:
        if not p.get("text", "").strip():
            continue
        url = f"https://bsky.app/profile/{handle}/post/{(p.get('uri') or '').rsplit('/', 1)[-1]}"
        out.append({
            "schema_version": 1, "id": util.statement_id(url, p["text"]),
            "source": "bluesky", "lane": config.LANE_BY_SOURCE["bluesky"],
            "url": url, "title": "", "text": p["text"],
            "published_at": (p.get("createdAt") or "")[:10], "precision": "second",
            "observed_at": util.now_utc_iso(),
            "member": {"bioguide": meta.get("bioguide"), "name": None, "party": meta.get("party"),
                       "state": None, "chamber": meta.get("chamber"), "leadership_role": None},
            "congress": util.congress_for_date((p.get("createdAt") or util.now_utc_iso())[:10]),
            "joint_group": None, "syndicated": False, "copyright_basis": config.COPYRIGHT_BY_SOURCE["bluesky"],
            "bsky_handle": handle, "run_id": run_id,
        })
    return out


def ingest(run_id: str = "bluesky") -> list[dict]:
    seed = load_seed()
    statements: list[dict] = []
    for handle, meta in seed.items():
        posts = poll_author(handle)
        statements += to_statements(handle, meta, posts, run_id)
        print(f"[bluesky] {handle}: {len(posts)} recent posts")
    if statements:
        config.RAW.joinpath("bluesky").mkdir(parents=True, exist_ok=True)
        util.write_jsonl(config.RAW / "bluesky" / "lane2.jsonl", statements)
    return statements


def main() -> int:
    stmts = ingest()
    print(f"\n[bluesky] ingested {len(stmts)} Lane-2 statements from {len(load_seed())} seed accounts "
          f"(enrichment only — excluded from every cross-party metric).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
