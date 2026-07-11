"""B7 — post the Daily Line thread to both composite accounts (§7.2/§7.3).

blue.onscript.news = D, red.onscript.news = R. Dry-run (no BSKY_* creds) prints the exact
thread that WOULD post; the real AT-Protocol path (createSession + app.bsky.feed.post, threaded)
is gated on the app-password secrets Michael sets at launch. Bluesky posting is free and never
touches the Anthropic API. Skip-and-log: a posting failure never crashes the run.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import config, util  # noqa: E402

SITE = "https://onscript.news"
_ACCOUNTS = {
    "D": {"handle_env": "BSKY_BLUE_HANDLE", "pw_env": "BSKY_BLUE_PASSWORD", "label": "blue"},
    "R": {"handle_env": "BSKY_RED_HANDLE", "pw_env": "BSKY_RED_PASSWORD", "label": "red"},
}


def _split(text: str, limit: int = 300) -> list[str]:
    words, out, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > limit:
            out.append(cur.strip()); cur = ""
        cur += " " + w
    if cur.strip():
        out.append(cur.strip())
    return out or [""]


def build_thread(day: str, party: str, day_json: dict) -> list[str]:
    dl = (day_json.get("daily_lines") or {}).get(party) or {}
    composite = dl.get("composite", "")
    posts = _split(composite)
    # receipts post: link + the day's most synchronized phrase (count + first-sayer)
    top = next((r for r in day_json.get("top_synchronized", []) if r.get("party") == party), None)
    receipts = f"Receipts: {SITE}/day/{day}.html"
    if top:
        fs = top.get("first_seen", {})
        receipts += (f'\nMost synchronized: "{top["ngram"]}" — {top["day_peak"]} of us'
                     f' (first said {fs.get("date")}).')
    posts.append(receipts)
    if dl.get("generator") == "dry_run":
        posts.append(f"[Automated composite — methodology + symmetry audit: {SITE}/methodology.html]")
    return posts


def post_party(day: str, party: str, day_json: dict) -> dict:
    acct = _ACCOUNTS[party]
    handle = os.environ.get(acct["handle_env"])
    pw = os.environ.get(acct["pw_env"])
    thread = build_thread(day, party, day_json)
    if not handle or not pw:
        print(f"\n[dry-run bluesky:{acct['label']} ({party})] would post {len(thread)} posts:")
        for i, p in enumerate(thread, 1):
            print(f"  --- post {i} ---\n  " + p.replace("\n", "\n  "))
        return {"party": party, "posted": False, "reason": "no creds (dry-run)", "posts": len(thread)}
    return _post_real(handle, pw, thread, party)  # pragma: no cover - requires creds


def _post_real(handle: str, pw: str, thread: list[str], party: str) -> dict:  # pragma: no cover
    import json
    import urllib.request

    def _call(url, body, token=None):
        headers = {"content-type": "application/json"}
        if token:
            headers["authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

    base = "https://bsky.social/xrpc"
    sess = _call(f"{base}/com.atproto.server.createSession", {"identifier": handle, "password": pw})
    jwt, did = sess["accessJwt"], sess["did"]
    root = parent = None
    for text in thread:
        rec = {"$type": "app.bsky.feed.post", "text": text, "createdAt": util.now_utc_iso(),
               "langs": ["en"]}
        if root:
            rec["reply"] = {"root": root, "parent": parent}
        res = _call(f"{base}/com.atproto.repo.createRecord", token=jwt,
                    body={"repo": did, "collection": "app.bsky.feed.post", "record": rec})
        ref = {"uri": res["uri"], "cid": res["cid"]}
        root = root or ref
        parent = ref
    return {"party": party, "posted": True, "posts": len(thread)}


def main() -> int:
    latest = util.read_json(config.DERIVED / "manifest" / "collect-latest.json", {}) \
        or util.read_json(config.DERIVED / "manifest" / "latest.json", {})
    day = latest.get("focus_day") or util.product_day()
    day_json = util.read_json(config.DERIVED / "days" / f"{day}.json", None)
    if not day_json or not day_json.get("daily_lines"):
        print(f"no Daily Lines for {day} — nothing to post")
        return 0
    for party in config.COMPOSITE_PARTIES:
        try:
            post_party(day, party, day_json)
        except Exception as e:  # skip-and-log
            print(f"[post-failed:{party}] {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
