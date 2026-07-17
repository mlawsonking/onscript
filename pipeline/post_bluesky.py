"""B7 — post the Daily Line thread to both composite accounts (§7.2/§7.3).

blue.onscript.news = D, red.onscript.news = R. Posting is GATED, in order:
  1. POSTING_ENABLED (repo variable) — the S3 launch switch. Off (default) => dry-run print, NO
     network, regardless of creds (kill-tested). The first brand post is Michael's act, never a cron
     accident.
  2. Creds present for every due party — else dry-run (pre-launch).
  3. ATOMIC PRE-FLIGHT auth — a real createSession is established for EVERY due party BEFORE any post.
     If any fails (wrong/expired app-password), NEITHER posts (atomic hold) — an asymmetric post
     (one account up, one erroring) reads as bias. §Session-8.
  4. Post each thread, persisting the root URI the instant the root post is live (before the replies)
     so a mid-thread failure can never be re-posted as a DUPLICATE on a re-run. §Session-8.

The day comes from the day ASSEMBLE built (manifest/assemble-latest.json). Outcomes (incl. the full
thread text, for the on-domain signed archive) are written to manifest/post-<day>.json, flushed after
every root so a crash leaves a durable, non-duplicating record. Bluesky posting is free and never
touches the Anthropic API. Skip-and-log: a failure never crashes the run.
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

from pipeline import config, ops, privacy, util  # noqa: E402

SITE = "https://onscript.news"
_ACCOUNTS = {
    "D": {"handle_env": "BSKY_BLUE_HANDLE", "pw_env": "BSKY_BLUE_PASSWORD", "label": "blue"},
    "R": {"handle_env": "BSKY_RED_HANDLE", "pw_env": "BSKY_RED_PASSWORD", "label": "red"},
}


def _split(text: str, limit: int = 300) -> list[str]:
    """Pack words into <=limit-char posts. Invariant: never emit an EMPTY post and never emit an
    OVER-length one — a lone token longer than the limit (a URL, a pathological run) is hard-sliced.
    An empty leading post or an uncut oversize word would fail createRecord for that party alone,
    reading as bias (adversarial-review finding). §Session-8b."""
    out, cur = [], ""
    for w in text.split():
        if len(w) > limit:                          # lone oversize token: flush, then hard-slice it
            if cur.strip():
                out.append(cur.strip())
            cur = ""
            while len(w) > limit:
                out.append(w[:limit]); w = w[limit:]
        if cur.strip() and len(cur) + len(w) + 1 > limit:
            out.append(cur.strip()); cur = ""
        cur += " " + w
    if cur.strip():
        out.append(cur.strip())
    return out or [""]


def _has_composite(party: str, day_json: dict) -> bool:
    """True iff this party has a non-empty Daily Line composite for the day. A missing/empty composite
    would post a near-empty root; and if only ONE party's is missing, BOTH still post (asymmetric is
    False — both are technically 'posted'), a SILENT neutrality failure that slips past the asymmetric
    guard. So a due party with no composite holds ALL posting. §Session-8b (adversarial-review)."""
    dl = (day_json.get("daily_lines") or {}).get(party) or {}
    return bool((dl.get("composite") or "").strip())


def _privacy_trips(party: str, day_json: dict) -> bool:
    """True iff anything this party would POST names a private individual (Art. XIII) — the composite
    or the 'most synchronized' phrase build_thread appends to the receipts post. Total-failure-proof
    like _has_composite: a malformed day must never raise here."""
    dl = (day_json.get("daily_lines") or {}).get(party) or {}
    if privacy.is_suppressed(dl.get("composite") or ""):
        return True
    for r in day_json.get("top_synchronized") or []:
        if isinstance(r, dict) and r.get("party") == party and privacy.is_suppressed(r.get("ngram") or ""):
            return True
    return False


def build_thread(day: str, party: str, day_json: dict) -> list[str]:
    # Total-failure-proof: a malformed day entry (null composite, a top-phrase row missing keys) must
    # never raise here — a raise would crash the run. All accesses are guarded.
    dl = (day_json.get("daily_lines") or {}).get(party) or {}
    posts = _split(dl.get("composite") or "")
    top = next((r for r in (day_json.get("top_synchronized") or []) if r.get("party") == party), None)
    receipts = f"Receipts: {SITE}/day/{day}.html"
    if top and top.get("ngram"):
        fs = top.get("first_seen") or {}
        receipts += (f'\nMost synchronized: "{top.get("ngram")}" — {top.get("day_peak")} of us'
                     f' (first recorded {fs.get("date")}).')
    posts.append(receipts)
    if dl.get("generator") == "dry_run":
        posts.append(f"[Automated composite — methodology + symmetry audit: {SITE}/methodology.html]")
    return posts


def _print_thread(label: str, party: str, thread: list[str], reason: str) -> None:
    print(f"\n[dry-run bluesky:{label} ({party})] {reason} — would post {len(thread)} posts:")
    for i, p in enumerate(thread, 1):
        print(f"  --- post {i} ---\n  " + p.replace("\n", "\n  "))


def can_post(party: str) -> bool:
    """True iff this party's account creds are PRESENT. Presence is necessary but not sufficient — the
    atomic pre-flight (_authenticate) proves they actually work before anything posts."""
    a = _ACCOUNTS[party]
    return bool(os.environ.get(a["handle_env"]) and os.environ.get(a["pw_env"]))


def _dry_result(day: str, party: str, day_json: dict, reason: str, creds_present=None) -> dict:
    """A non-posting result (dry-run / gated / atomic-hold). Prints the would-be thread; NO network."""
    thread = build_thread(day, party, day_json)
    _print_thread(_ACCOUNTS[party]["label"], party, thread, reason=reason)
    return {"party": party, "thread": thread, "posts": len(thread), "posted": False,
            "reason": reason, "creds_present": can_post(party) if creds_present is None else creds_present}


# --- real AT-Protocol path (pragma: no cover — requires live app-password creds) -----------
def _http(url, jwt=None):  # pragma: no cover
    import json
    import urllib.request
    headers = {"authorization": f"Bearer {jwt}"} if jwt else {}
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


def _authenticate(handle: str, pw: str) -> dict:  # pragma: no cover - requires creds
    """Establish an authenticated session (createSession). Raises on a wrong/expired app-password —
    the caller uses that to hold ALL posting atomically, so a bad credential can never let the paired
    account post alone. §Session-8 (auth-real atomic pre-flight)."""
    base = "https://bsky.social/xrpc"
    sess = _call(f"{base}/com.atproto.server.createSession", {"identifier": handle, "password": pw})
    return {"base": base, "jwt": sess["accessJwt"], "did": sess["did"]}


def _ensure_bot_label(session: dict):  # pragma: no cover - requires creds
    """Idempotently declare the {val:'bot'} self-label (§7.3) WITHOUT clobbering the display name/bio/
    avatar. If the profile can't be read or is empty, do nothing. Never blocks posting."""
    base, jwt, did = session["base"], session["jwt"], session["did"]
    try:
        got = _http(f"{base}/com.atproto.repo.getRecord?repo={did}"
                    f"&collection=app.bsky.actor.profile&rkey=self", jwt)
        rec = (got or {}).get("value") or {}
    except Exception as e:
        print(f"[bot-label:{did[:12]}] profile unreadable, skipping self-label: {e}")
        return
    if not (rec.get("displayName") or rec.get("description")):
        print(f"[bot-label:{did[:12]}] profile has no display name/bio yet, skipping self-label")
        return
    values = list((rec.get("labels") or {}).get("values") or [])
    if any((v or {}).get("val") == "bot" for v in values):
        return
    values.append({"val": "bot"})
    rec["labels"] = {"$type": "com.atproto.label.defs#selfLabels", "values": values}
    rec.setdefault("$type", "app.bsky.actor.profile")
    _call(f"{base}/com.atproto.repo.putRecord", token=jwt,
          body={"repo": did, "collection": "app.bsky.actor.profile", "rkey": "self", "record": rec})
    print(f"[bot-label:{did[:12]}] declared self-label val=bot")


_S32 = "234567abcdefghijklmnopqrstuvwxyz"  # base32-sortable alphabet (AT-Proto TID encoding)


def _root_rkey(day: str, party: str) -> str:
    """A DETERMINISTIC record key for the root post, unique per day+party. Because it's fixed, a retried
    root (after a lost createRecord response or a failed manifest write) COLLIDES server-side instead of
    creating a second post — closing the duplicate-head-post window the local manifest alone can't.

    `app.bsky.feed.post` REJECTS an arbitrary rkey ("Invalid TID string", verified live #108) — the
    rkey MUST be a valid 13-char TID. So we build a real TID deterministically: timestamp = midnight
    UTC of `day`, clock-id = the party index. That is valid, unique per (day, party), and roughly
    chronological. §Session-8c (fixes the launch-blocking 400 the smoke test caught)."""
    import calendar
    from datetime import datetime, timezone
    try:
        dt = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        ts_us = int(calendar.timegm(dt.timetuple())) * 1_000_000
    except Exception:
        ts_us = int(calendar.timegm(datetime.now(timezone.utc).timetuple())) * 1_000_000
    clock = 0 if str(party).upper() == "D" else 1  # two composite parties -> two clock ids
    n = (ts_us << 10) | clock
    return "".join(_S32[(n >> (5 * (12 - i))) & 0x1F] for i in range(13))


def _post_thread(session: dict, thread: list[str], on_root=None, root_rkey=None) -> dict:
    """Post a thread. The root uses a DETERMINISTIC rkey (idempotent server-side); on collision — the
    root already exists from a prior run whose response was lost — it is RECOVERED via getRecord and we
    STOP (never a duplicate head post, never re-posted replies). on_root(uri) fires the instant the root
    URI is known so the caller can persist it before any reply. Returns {root_uri, posts_written}."""
    base, jwt, did = session["base"], session["jwt"], session["did"]
    root = parent = None
    written = 0
    for text in thread:
        rec = {"$type": "app.bsky.feed.post", "text": text, "createdAt": util.now_utc_iso(), "langs": ["en"]}
        if root:
            rec["reply"] = {"root": root, "parent": parent}
        body = {"repo": did, "collection": "app.bsky.feed.post", "record": rec}
        if root is None and root_rkey:
            body["rkey"] = root_rkey
            try:
                res = _call(f"{base}/com.atproto.repo.createRecord", token=jwt, body=body)
            except Exception as create_err:
                # The create failed. Distinguish a rkey COLLISION (root already live from a prior run
                # whose response was lost) from a GENUINE failure (bad content, rate limit, network) by
                # PROBING existence — a collision surfaces as 400 OR 500 depending on the PDS (verified
                # live #108), so we can't match on the code/message. If the record now exists, recover
                # it and STOP (never a duplicate head, never re-posted replies). If it does NOT exist,
                # the create genuinely failed — re-raise so the caller skip-and-logs + the dead-man
                # fires (posted=False, no root_uri). §Session-8c.
                try:
                    got = _http(f"{base}/com.atproto.repo.getRecord?repo={did}"
                                f"&collection=app.bsky.feed.post&rkey={root_rkey}", jwt)
                except Exception:
                    raise create_err
                if on_root:
                    on_root(got["uri"])
                return {"root_uri": got["uri"], "posts_written": 0, "recovered": True}
        else:
            res = _call(f"{base}/com.atproto.repo.createRecord", token=jwt, body=body)
        ref = {"uri": res["uri"], "cid": res["cid"]}
        if root is None:
            root = ref
            if on_root:
                on_root(ref["uri"])   # durable checkpoint BEFORE any reply
        parent = ref
        written += 1
    return {"root_uri": (root or {}).get("uri"), "posts_written": written}


def resolve_day(arg: str | None) -> str:
    """The day to post = the day ASSEMBLE built (assemble-latest.json). Explicit --day wins."""
    if arg:
        return arg
    latest = util.read_json(config.DERIVED / "manifest" / "assemble-latest.json", {})
    return latest.get("day") or util.product_day()


def _deadman(posting_enabled: bool, results: list[dict], atomic_hold: bool) -> None:
    """Alert when posting is ON and something needs a human: an expected-but-absent post, an atomic
    hold (bad/missing creds — post neither), a partial thread (root up, replies failed), or an
    ASYMMETRIC outcome (exactly one account up — the bias-looking failure). §Session-8."""
    if not posting_enabled:
        return
    posted = [r["party"] for r in results if r.get("posted") and not r.get("idempotent_skip")]
    missing = [r["party"] for r in results if r.get("creds_present") and not r.get("posted")]
    partial = [r["party"] for r in results if r.get("partial")]
    live = [r["party"] for r in results if r.get("posted")]
    asymmetric = len(live) == 1
    if missing or atomic_hold or asymmetric or partial:
        ops.ntfy("OnScript posting",
                 f"posted={posted} missing={missing} partial={partial} "
                 f"atomic_hold={atomic_hold} asymmetric={asymmetric}", priority="high")


def _list_manifests() -> list:  # pragma: no cover - real FS listing (seam stubbed in tests)
    import glob
    return sorted(glob.glob(str(config.DERIVED / "manifest" / "post-*.json")))


def _reconcile_prior(current_day: str, posting_enabled: bool) -> list:
    """Backstop for a HARD process-kill (Actions timeout/OOM/SIGKILL) BETWEEN the two parties' posts:
    the end-of-run dead-man never runs, so a durably ASYMMETRIC (one party live) or PARTIAL manifest
    from a prior run would otherwise alert nobody — a silent one-sided post, the worst neutrality
    failure. On the next posting run, scan recent post manifests and fire the dead-man ONCE per
    unacknowledged asymmetric/partial day (marking it `reconciled` so it never re-alerts). Excludes the
    current day — this run's own end-of-run dead-man owns that. Returns the days alerted. §Session-8d
    (adversarial-review finding B)."""
    if not posting_enabled:
        return []
    alerted = []
    for path in _list_manifests():   # ALL manifests, not a recent window: after a one-sided post the
        # operator may disable posting for weeks to investigate — a bounded window would age the bad day
        # out unseen. The `reconciled` marker keeps a full scan idempotent and cheap. §Session-8d review.
        base = os.path.basename(path)
        mday = base[len("post-"):-len(".json")] if base.startswith("post-") and base.endswith(".json") else base
        if mday == current_day:   # day from the FILENAME (authoritative) — never trust a missing "day" field
            continue
        try:
            m = util.read_json(path, {}) or {}   # a corrupt manifest never crashes the run (module contract)
        except Exception as e:
            print(f"[reconcile] unreadable manifest {base} (skipped): {e}")
            continue
        if m.get("reconciled"):
            continue
        partial = any((r or {}).get("partial") for r in (m.get("results") or []))
        if not (m.get("asymmetric") or partial):   # atomic_hold is the SAFE outcome — never re-alert it
            continue
        live = [r.get("party") for r in (m.get("results") or []) if r.get("posted")]
        ops.ntfy("OnScript posting",
                 f"UNRECONCILED prior run {mday}: a hard-kill left a one-sided/partial post "
                 f"(asymmetric={m.get('asymmetric')} partial={partial} live={live}) — check + repair by hand",
                 priority="high")
        m["reconciled"] = True
        try:
            util.write_json(path, m)   # mark once so the alert fires exactly once
        except Exception as e:
            print(f"[reconcile] mark-reconciled write failed (non-fatal): {e}")
        alerted.append(mday)
    return alerted


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=None)
    day = resolve_day(ap.parse_args().day)
    day_json = util.read_json(config.DERIVED / "days" / f"{day}.json", None)
    manifest_path = config.DERIVED / "manifest" / f"post-{day}.json"

    prior = util.read_json(manifest_path, {})
    prior_results = prior.get("results") or []
    # A party is "already posted" only if a prior run recorded a real root URI — so a partial thread
    # (root live) is NEVER re-posted (no duplicate), but a clean failure (no root) IS retried.
    already_posted = {r.get("party") for r in prior_results if r.get("posted") and r.get("root_uri")}
    posting_enabled = config.posting_enabled()
    have_day = bool(day_json and day_json.get("daily_lines"))

    # Backstop a prior run that was hard-killed mid-post (silent asymmetric/partial) before doing today.
    _reconcile_prior(day, posting_enabled)

    result_by_party: dict = {}
    atomic_hold = False

    def _ordered():
        return [result_by_party[p] for p in config.COMPOSITE_PARTIES if p in result_by_party]

    def _flush():
        # A manifest write failure must never crash the run (module contract) — and the deterministic
        # root rkey means the manifest is a fast-path record, not the sole idempotency guard.
        try:
            live = [r["party"] for r in _ordered() if r.get("posted")]
            util.write_json(manifest_path, {
                "schema_version": 1, "kind": "post", "day": day, "generated_at": util.now_utc_iso(),
                "posting_enabled": posting_enabled, "atomic_hold": atomic_hold,
                "asymmetric": len(live) == 1, "results": _ordered(),
            })
        except Exception as e:
            print(f"[post] manifest write failed (non-fatal): {e}")

    if not have_day:
        print(f"no Daily Lines for {day} — nothing to post")
        _flush()
        return 0

    # Carry prior successes forward (idempotent skip — never re-post; preserves thread + root_uri).
    for party in config.COMPOSITE_PARTIES:
        if party in already_posted:
            prev = next((r for r in prior_results if r.get("party") == party and r.get("root_uri")), {})
            print(f"[post:{party}] already posted for {day} — idempotent skip")
            result_by_party[party] = {**prev, "party": party, "posted": True,
                                      "reason": "already posted (idempotent)", "creds_present": True,
                                      "idempotent_skip": True}

    to_post = [p for p in config.COMPOSITE_PARTIES if p not in already_posted]

    # Gated / dry-run: posting off, or nothing due -> hold all as dry (no network).
    if not (posting_enabled and to_post):
        for p in to_post:
            result_by_party[p] = _dry_result(
                day, p, day_json, "posting disabled" if not posting_enabled else "no creds (dry-run)")
        _flush()
        _deadman(posting_enabled, _ordered(), atomic_hold)
        return 0

    # A due party missing creds -> hold ALL atomically (post neither).
    no_creds = [p for p in to_post if not can_post(p)]
    if no_creds:
        atomic_hold = True
        for p in to_post:
            result_by_party[p] = _dry_result(day, p, day_json, f"atomic hold (creds missing: {no_creds})")
        _flush()
        _deadman(posting_enabled, _ordered(), atomic_hold)
        return 0

    # A due party with an empty/missing composite -> hold ALL atomically. Posting a near-empty root for
    # one party while the other posts a real thread reads as bias yet slips past the asymmetric guard
    # (both are technically "posted"). Hold both + alert. §Session-8b (adversarial-review).
    no_content = [p for p in to_post if not _has_composite(p, day_json)]
    if no_content:
        atomic_hold = True
        for p in to_post:
            result_by_party[p] = _dry_result(day, p, day_json, f"atomic hold (no composite: {no_content})")
        _flush()
        _deadman(posting_enabled, _ordered(), atomic_hold)
        return 0

    # ART. XIII — a HOLD, never a filter. A posted name is the one surface that cannot be
    # un-published. We do NOT post a redacted thread: site.posts_log_body re-renders posted text from
    # manifest/post-<day>.json and its copy promises a complete, unedited archive ("Any post
    # attributed to these accounts that does not appear here is not ours"), so a redacted signed
    # archive is a contradiction. The only available cut is never emitting. Both parties hold, so a
    # suppressed day can never publish a one-sided thread.
    suppressed = [p for p in to_post if _privacy_trips(p, day_json)]
    if suppressed:
        atomic_hold = True
        for p in to_post:
            result_by_party[p] = _dry_result(day, p, day_json,
                                             f"atomic hold (privacy floor, Art. XIII: {suppressed})")
        _flush()
        _deadman(posting_enabled, _ordered(), atomic_hold)
        return 0

    # ATOMIC PRE-FLIGHT AUTH — a real session for EVERY due party before any post. A wrong/expired
    # password holds ALL posting, so a bad credential never lets the paired account post alone.
    sessions: dict = {}
    auth_fail: dict = {}
    for p in to_post:
        a = _ACCOUNTS[p]
        try:
            sessions[p] = _authenticate(os.environ[a["handle_env"]], os.environ[a["pw_env"]])
        except Exception as e:
            auth_fail[p] = str(e)
            print(f"[post-auth-failed:{p}] {e}")
    if auth_fail:
        atomic_hold = True
        for p in to_post:
            result_by_party[p] = _dry_result(
                day, p, day_json, f"atomic hold (auth failed: {sorted(auth_fail)})", creds_present=True)
        _flush()
        _deadman(posting_enabled, _ordered(), atomic_hold)
        return 0

    # POST each authed party, checkpointing the root URI the instant it is live.
    for p in to_post:
        thread = build_thread(day, p, day_json)
        try:
            try:
                _ensure_bot_label(sessions[p])
            except Exception as e:
                print(f"[bot-label:{p}] non-fatal: {e}")

            def _on_root(uri, p=p, thread=thread):
                result_by_party[p] = {"party": p, "thread": thread, "posts": len(thread),
                                      "posted": True, "root_uri": uri, "creds_present": True, "partial": True}
                _flush()  # durable BEFORE replies -> a re-run skips this party (no duplicate)

            out = _post_thread(sessions[p], thread, on_root=_on_root, root_rkey=_root_rkey(day, p))
            result_by_party[p] = {"party": p, "thread": thread, "posts": out["posts_written"],
                                  "posted": True, "root_uri": out["root_uri"], "creds_present": True}
        except Exception as e:  # skip-and-log — a posting failure never crashes the run
            print(f"[post-failed:{p}] {e}")
            if not (result_by_party.get(p) or {}).get("root_uri"):
                result_by_party[p] = {"party": p, "thread": thread, "posts": 0, "posted": False,
                                      "reason": f"error: {e}", "creds_present": True}
            # else: on_root already recorded posted=True + root_uri (a partial thread) -> leave it so a
            # re-run does NOT duplicate; the dead-man flags the partial/asymmetric state below.
        _flush()

    _flush()
    _deadman(posting_enabled, _ordered(), atomic_hold)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
