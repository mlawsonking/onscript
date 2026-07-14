"""B7 — post the Daily Line thread to both composite accounts (§7.2/§7.3).

blue.onscript.news = D, red.onscript.news = R. Posting is GATED three ways, in order:
  1. POSTING_ENABLED (config, from the GitHub Actions repo variable) — the S3 launch switch.
     Off (default) => deterministic dry-run print, NO network, regardless of creds. This is the
     deliberate-launch gate: the first brand post is Michael's act, never a cron accident.
  2. app-password secrets present — absent => dry-run print (the pre-launch/no-creds path).
  3. only then the real AT-Protocol path (createSession + app.bsky.feed.post, threaded).

The day comes from the day ASSEMBLE built (manifest/assemble-latest.json), not from collect —
decoupling the two fixes the Session-4 no-op bug. Post outcomes are written to
manifest/post-<day>.json, and an expected-but-absent post fires the dead-man (ntfy). Bluesky
posting is free and never touches the Anthropic API. Skip-and-log: a failure never crashes the run.
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

from pipeline import config, ops, util  # noqa: E402

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


def _print_thread(label: str, party: str, thread: list[str], reason: str) -> None:
    print(f"\n[dry-run bluesky:{label} ({party})] {reason} — would post {len(thread)} posts:")
    for i, p in enumerate(thread, 1):
        print(f"  --- post {i} ---\n  " + p.replace("\n", "\n  "))


def post_party(day: str, party: str, day_json: dict) -> dict:
    """Post (or dry-run) one party's thread. Returns a structured result the caller records."""
    acct = _ACCOUNTS[party]
    handle = os.environ.get(acct["handle_env"])
    pw = os.environ.get(acct["pw_env"])
    thread = build_thread(day, party, day_json)

    # Gate 1 — the launch switch. Off => never post, regardless of creds (kill-tested).
    if not config.posting_enabled():
        _print_thread(acct["label"], party, thread, reason="POSTING_ENABLED off (hold)")
        return {"party": party, "posted": False, "reason": "posting disabled", "posts": len(thread),
                "creds_present": bool(handle and pw)}

    # Gate 2 — creds. Absent => dry-run print (pre-launch / secrets not set).
    if not handle or not pw:
        _print_thread(acct["label"], party, thread, reason="no creds (dry-run)")
        return {"party": party, "posted": False, "reason": "no creds (dry-run)", "posts": len(thread),
                "creds_present": False}

    # Gate 3 — the real path.
    res = _post_real(handle, pw, thread, party)  # pragma: no cover - requires creds
    res["creds_present"] = True
    return res


# --- real AT-Protocol path (pragma: no cover — requires live app-password creds) -----------
def _http(url, jwt=None):  # pragma: no cover
    import json
    import urllib.request
    headers = {}
    if jwt:
        headers["authorization"] = f"Bearer {jwt}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _call(url, body, token=None):  # pragma: no cover
    import json
    import urllib.request
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _ensure_bot_label(base, jwt, did):  # pragma: no cover - requires creds
    """Idempotently declare the {val:'bot'} self-label on the account profile (§7.3), WITHOUT
    clobbering the display name / bio / avatar Michael set. Fetches the existing profile record,
    adds the label only if absent, and re-puts the FULL record. If the profile can't be read (or
    is empty), it does nothing — never risks creating a bare profile. Never breaks posting."""
    try:
        got = _http(f"{base}/com.atproto.repo.getRecord?repo={did}"
                    f"&collection=app.bsky.actor.profile&rkey=self", jwt)
        rec = (got or {}).get("value") or {}
    except Exception as e:
        print(f"[bot-label:{did[:12]}] profile unreadable, skipping self-label: {e}")
        return
    # Only touch a profile that actually exists with content (protects Michael's display name/bio).
    if not (rec.get("displayName") or rec.get("description")):
        print(f"[bot-label:{did[:12]}] profile has no display name/bio yet, skipping self-label")
        return
    labels = rec.get("labels") or {}
    values = list(labels.get("values") or [])
    if any((v or {}).get("val") == "bot" for v in values):
        return  # already labeled — idempotent no-op
    values.append({"val": "bot"})
    rec["labels"] = {"$type": "com.atproto.label.defs#selfLabels", "values": values}
    rec.setdefault("$type", "app.bsky.actor.profile")
    _call(f"{base}/com.atproto.repo.putRecord", token=jwt,
          body={"repo": did, "collection": "app.bsky.actor.profile", "rkey": "self", "record": rec})
    print(f"[bot-label:{did[:12]}] declared self-label val=bot")


def _post_real(handle: str, pw: str, thread: list[str], party: str) -> dict:  # pragma: no cover
    base = "https://bsky.social/xrpc"
    sess = _call(f"{base}/com.atproto.server.createSession", {"identifier": handle, "password": pw})
    jwt, did = sess["accessJwt"], sess["did"]
    try:
        _ensure_bot_label(base, jwt, did)  # disclosure hygiene; never blocks posting
    except Exception as e:
        print(f"[bot-label] non-fatal: {e}")
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
    return {"party": party, "posted": True, "posts": len(thread), "root_uri": (root or {}).get("uri")}


def resolve_day(arg: str | None) -> str:
    """The day to post = the day ASSEMBLE built (assemble-latest.json), NOT collect's focus_day.
    Explicit --day wins; falls back to the assemble manifest, then product_day (§2)."""
    if arg:
        return arg
    latest = util.read_json(config.DERIVED / "manifest" / "assemble-latest.json", {})
    return latest.get("day") or util.product_day()


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=None)
    args = ap.parse_args()
    day = resolve_day(args.day)
    day_json = util.read_json(config.DERIVED / "days" / f"{day}.json", None)

    # Idempotency: never re-post a party that a prior run already posted for THIS day. A manual
    # re-dispatch / "Re-run all jobs" after a successful post would otherwise publish a duplicate
    # composite thread. The prior post manifest is the source of truth. §Session-5 (MEDIUM-2).
    prior = util.read_json(config.DERIVED / "manifest" / f"post-{day}.json", {})
    already_posted = {r.get("party") for r in (prior.get("results") or []) if r.get("posted")}

    results: list[dict] = []
    if not day_json or not day_json.get("daily_lines"):
        print(f"no Daily Lines for {day} — nothing to post")
    else:
        for party in config.COMPOSITE_PARTIES:
            if party in already_posted:
                print(f"[post:{party}] already posted for {day} — idempotent skip")
                results.append({"party": party, "posted": True, "reason": "already posted (idempotent)",
                                "posts": 0, "creds_present": True, "idempotent_skip": True})
                continue
            try:
                results.append(post_party(day, party, day_json))
            except Exception as e:  # skip-and-log — a posting failure never crashes the run
                print(f"[post-failed:{party}] {e}")
                # Record creds presence so the dead-man below can fire: a creds-present party whose
                # real post THREW (network/401/timeout) is exactly the silent outage to alert on.
                acct = _ACCOUNTS[party]
                creds = bool(os.environ.get(acct["handle_env"]) and os.environ.get(acct["pw_env"]))
                results.append({"party": party, "posted": False, "reason": f"error: {e}",
                                "posts": 0, "creds_present": creds})

    posting_enabled = config.posting_enabled()
    manifest = {
        "schema_version": 1, "kind": "post", "day": day,
        "generated_at": util.now_utc_iso(),
        "posting_enabled": posting_enabled, "results": results,
    }
    util.write_json(config.DERIVED / "manifest" / f"post-{day}.json", manifest)

    # Dead-man: when posting is ON and creds are present, an expected post that didn't happen is
    # a silent marketing outage — alert. (When posting is OFF, absence is the intended hold.)
    if posting_enabled:
        missing = [r["party"] for r in results if r.get("creds_present") and not r.get("posted")]
        if missing:
            ops.ntfy("OnScript posting", f"day={day} expected-but-absent posts: {missing}",
                     priority="high")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
