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
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import (config, distill, eligibility, instrument_fingerprint, ops, privacy, public_strings,
                      util)  # noqa: E402

SITE = config.SITE_URL      # one source of truth: a receipts link that disagrees with the site is a 404
_ACCOUNTS = {
    "D": {"handle_env": "BSKY_BLUE_HANDLE", "pw_env": "BSKY_BLUE_PASSWORD", "label": "blue"},
    "R": {"handle_env": "BSKY_RED_HANDLE", "pw_env": "BSKY_RED_PASSWORD", "label": "red"},
}


def _pack_words(text: str, limit: int = 300) -> list[str]:
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


# A sentence ends at .!? — optionally followed by a CLOSING QUOTE — then whitespace and something
# that can start a sentence. The abbreviation guard is the whole reason this is a function and not a
# one-line regex: the composite voice writes "Rep." / "U.S." / "No. 5" constantly, and splitting there
# would cut a post after "the U.S." — a worse break than the mid-sentence one this is fixing.
#
# THE CLOSING-QUOTE ALTERNATIVE IS NOT DEFENSIVE, it is the common case, and the first live thread
# proved it: prompt rule 2 REQUIRES verbatim member quotes, so this voice ends sentences with
# `...implemented."` routinely. With only the bare lookbehind, the character before the space is the
# quote rather than the period, the boundary is missed, two sentences merge into one 272-char run
# that no longer fits a post, and the word-packer cuts it mid-clause — reintroducing exactly the
# defect this function exists to remove (live D thread, 2026-07-21: "...as a common" / "thread today.").
_SENT_BOUNDARY = re.compile(r'(?:(?<=[.!?])|(?<=[.!?]["\'”’»)\]]))\s+(?=[A-Z0-9"“‘\'(])')
_ABBREV = {
    "u.s.", "u.s.a.", "d.c.", "mr.", "mrs.", "ms.", "dr.", "sen.", "rep.", "gov.", "st.", "jr.",
    "sr.", "no.", "vs.", "etc.", "inc.", "e.g.", "i.e.", "fig.", "art.", "sec.", "dept.",
}


def _sentences(text: str) -> list[str]:
    """Split into sentences, re-joining a false break after a known abbreviation or a lone initial."""
    parts = _SENT_BOUNDARY.split(text)
    out: list[str] = []
    for part in parts:
        if out:
            tail = out[-1].rsplit(" ", 1)[-1].lower()
            if tail in _ABBREV or re.fullmatch(r"[a-z]\.", tail):
                out[-1] = out[-1] + " " + part
                continue
        out.append(part)
    return [s for s in out if s.strip()]


def _split(text: str, limit: int = 300) -> list[str]:
    """Pack text into <=limit-char posts, breaking at SENTENCE boundaries wherever they fit.

    The live launch threads read "...our 99 statements today do" / "not converge on additional shared
    messages." — a word-packer fills each post to the last word that fits, so a thread that spans two
    posts almost always snaps mid-clause. Sentences are the natural unit of a composite line, and a
    reader who sees only the first post (the one that gets screenshotted) should get a whole thought.

    A sentence longer than one post still gets word-packed: the break has to happen somewhere, and a
    dropped or reordered word would be far worse than an ugly one. That is the load-bearing invariant
    here — the concatenation of the returned posts is always exactly the input's words, in order."""
    text = " ".join((text or "").split())           # normalize whitespace (was implicit in .split())
    if not text:
        return [""]
    out: list[str] = []
    cur = ""
    for sent in _sentences(text):
        joined = f"{cur} {sent}" if cur else sent
        if len(joined) <= limit:
            cur = joined
            continue
        if cur:
            out.append(cur)
            cur = ""
        if len(sent) <= limit:
            cur = sent
        else:
            chunks = _pack_words(sent, limit)       # unavoidable mid-sentence break
            out.extend(chunks[:-1])
            cur = chunks[-1]
    if cur:
        out.append(cur)
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


# docs/19 §4c — the AI-composite marker must survive a CROPPED screenshot: it goes in EVERY post unit
# of the thread, never only the thread head or the account bio (a screenshot of a single reply would
# then omit it). The account also carries a profile-level {val:'bot'} self-label, but that is invisible
# in a cropped post — this per-post line is the belt that is not.
_POST_MARK = f"🤖 {public_strings.POST_MEASUREMENT_LABEL} | onscript.news"


def _with_mark(post: str, limit: int = 300) -> str:
    """Append the per-post AI-composite marker, guaranteeing the result never exceeds `limit` (a lone
    over-length post would fail createRecord for that party alone, reading as bias). Callers size the
    body to leave room; this truncation is the safety belt for a pathological case."""
    mark = "\n" + _POST_MARK
    if len(post) + len(mark) > limit:
        post = post[:max(0, limit - len(mark) - 1)].rstrip() + "…"
    return post + mark


_TODAY_WORD = re.compile(r"\btoday\b", re.IGNORECASE)


def _state_absolute_date(text: str, day: str) -> str:
    """Replace the word today with the absolute measured date for a delayed post."""
    return _TODAY_WORD.sub(lambda m: (f"On {day}" if m.group(0)[0].isupper() else f"on {day}"), text)


def build_thread(day: str, party: str, day_json: dict, post_date: str | None = None) -> list[str]:
    # Total-failure-proof: a malformed day entry (null composite, a top-phrase row missing keys) must
    # never raise here — a raise would crash the run. All accesses are guarded.
    dl = (day_json.get("daily_lines") or {}).get(party) or {}
    room = 300 - len("\n" + _POST_MARK)               # size posts so the per-post marker always fits
    structured = dl.get("structured_output") or {}
    composite = structured.get("composite") or dl.get("composite") or ""
    stats = dl.get("stats") or {}
    lead = dl.get("measurement_lead") or distill.measurement_lead(
        party, day, stats.get("statements")
    )
    state = distill.state_for_line(dl)
    body = f"{lead} Composite state: {state}. {composite}"
    # R-36.4: a reading posted after its measured date never says today. The absolute measured
    # date is already in the lead and receipts; neutralize any residual today in the composite.
    # Applied identically to both parties; the stored day record is never rewritten.
    if post_date and post_date != day:
        body = _state_absolute_date(body, day)
    posts = _split(body, limit=room)
    party_rows = [
        row for row in (day_json.get("top_synchronized") or [])
        if isinstance(row, dict) and row.get("party") == party
    ]
    top = next((
        row for row in party_rows
        if eligibility.eligible_for_surface(
            eligibility.classify_phrase(
                row.get("ngram") or "", day=day, family_count=row.get("family_count"),
            ),
            "social",
        )
    ), None)
    receipts = f"Receipts: {SITE}/day/{day}.html"
    if top and top.get("ngram"):
        # "in our corpus", always. First-appearance is measured against OUR record, which begins at
        # STAGE1_EPOCH — a phrase already in use before then dates to our first day, not to its own
        # first day. Unqualified "first recorded" reads as a claim about the phrase's origin in
        # American politics, which is not a claim this instrument can make. §S34 follow-up (3).
        fs = top.get("first_seen") or {}
        receipts += (f'\nMost synchronized: "{top.get("ngram")}" — {top.get("day_peak")} of us'
                     f' (first recorded in our corpus {fs.get("date")}).')
    posts.append(receipts)
    if dl.get("generator") == "dry_run":
        posts.append(f"Automated composite — methodology + symmetry audit: {SITE}/methodology.html")
    # EVERY post carries the marker (docs/19 §4c), so no crop can hide that this is machine-composed.
    return [_with_mark(p) for p in posts]


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
    thread = build_thread(day, party, day_json, post_date=date.today().isoformat())
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


def _existing_replies(session: dict, root_uri: str, root_rkey: str) -> list[dict]:  # pragma: no cover
    """The replies to `root_uri` already in this account's repo, oldest first.

    Bounded by construction: a reply is created after its root, so its TID-rkey sorts ABOVE the
    root's. Walking the collection newest-first and stopping at the root's own rkey therefore reads
    only records from this thread's lifetime, not the account's whole history."""
    base, jwt, did = session["base"], session["jwt"], session["did"]
    found, cursor = [], None
    for _ in range(10):                                   # hard page cap; a thread is a handful of posts
        url = (f"{base}/com.atproto.repo.listRecords?repo={did}"
               f"&collection=app.bsky.feed.post&limit=100")
        if cursor:
            url += f"&cursor={cursor}"
        page = _http(url, jwt) or {}
        records = page.get("records") or []
        for r in records:
            rkey = str(r.get("uri", "")).rsplit("/", 1)[-1]
            if rkey <= root_rkey:                         # older than the root: cannot be its reply
                return sorted(found, key=lambda x: x["rkey"])
            reply = ((r.get("value") or {}).get("reply") or {})
            if ((reply.get("root") or {}).get("uri")) == root_uri:
                found.append({"rkey": rkey, "uri": r.get("uri"), "cid": r.get("cid"),
                              "text": (r.get("value") or {}).get("text") or ""})
        cursor = page.get("cursor")
        if not cursor or not records:
            break
    return sorted(found, key=lambda x: x["rkey"])


def _post_thread(session: dict, thread: list[str], on_root=None, root_rkey=None) -> dict:
    """Post a thread. The root uses a DETERMINISTIC rkey (idempotent server-side); on collision — the
    root already exists from a prior run whose response was lost — it is RECOVERED via getRecord and
    the thread RESUMES after whatever replies are already live. on_root(uri) fires the instant the
    root URI is known so the caller can persist it before any reply.
    Returns {root_uri, posts_written, recovered, resumed_from}.

    RESUMING, not stopping, is the fix for a truncation the first cut shipped: recovery returned
    immediately with posts_written=0, so the run that lost its response left a bare head post with no
    receipts reply — the one post in the thread that carries the citation link — and no later run
    would ever add it, because the manifest then recorded the party as posted. §S30b follow-up."""
    base, jwt, did = session["base"], session["jwt"], session["did"]
    root = parent = None
    written = 0
    recovered = False
    start = 0

    if root_rkey and thread:
        rec = {"$type": "app.bsky.feed.post", "text": thread[0],
               "createdAt": util.now_utc_iso(), "langs": ["en"]}
        body = {"repo": did, "collection": "app.bsky.feed.post", "record": rec, "rkey": root_rkey}
        try:
            res = _call(f"{base}/com.atproto.repo.createRecord", token=jwt, body=body)
            root = parent = {"uri": res["uri"], "cid": res["cid"]}
            written, start = 1, 1
            if on_root:
                on_root(root["uri"])          # durable checkpoint BEFORE any reply
        except Exception as create_err:
            # The create failed. Distinguish a rkey COLLISION (root already live from a prior run
            # whose response was lost) from a GENUINE failure (bad content, rate limit, network) by
            # PROBING existence — a collision surfaces as 400 OR 500 depending on the PDS (verified
            # live #108), so we can't match on the code/message. If it does NOT exist, the create
            # genuinely failed — re-raise so the caller skip-and-logs + the dead-man fires.
            try:
                got = _http(f"{base}/com.atproto.repo.getRecord?repo={did}"
                            f"&collection=app.bsky.feed.post&rkey={root_rkey}", jwt)
            except Exception:
                raise create_err
            recovered = True
            root = parent = {"uri": got["uri"], "cid": got["cid"]}
            if on_root:
                on_root(root["uri"])
            live = _existing_replies(session, root["uri"], root_rkey)
            expected = thread[1:1 + len(live)]
            if [r["text"] for r in live] != expected:
                # The live thread is not a prefix of the one we are holding — the day was re-authored
                # between runs. Appending would splice two different threads together, so stop and
                # leave it to a human. on_root already recorded root_uri + partial=True, so the
                # dead-man fires and the reconcile backstop keeps flagging it until it is dealt with.
                raise RuntimeError(
                    f"recovered root {root['uri']} has {len(live)} live repl(ies) that do not match "
                    f"this thread — refusing to append (re-authored day?)")
            if live:
                parent = {"uri": live[-1]["uri"], "cid": live[-1]["cid"]}
            start = 1 + len(live)

    for text in thread[start:]:
        rec = {"$type": "app.bsky.feed.post", "text": text, "createdAt": util.now_utc_iso(), "langs": ["en"]}
        if root:
            rec["reply"] = {"root": root, "parent": parent}
        body = {"repo": did, "collection": "app.bsky.feed.post", "record": rec}
        res = _call(f"{base}/com.atproto.repo.createRecord", token=jwt, body=body)
        ref = {"uri": res["uri"], "cid": res["cid"]}
        if root is None:
            root = ref
            if on_root:
                on_root(ref["uri"])   # durable checkpoint BEFORE any reply
        parent = ref
        written += 1
    return {"root_uri": (root or {}).get("uri"), "posts_written": written,
            "recovered": recovered, "resumed_from": start}


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
    """Post manifests, as PATHS.

    The type is the whole point. This returned glob STRINGS, and util.read_json calls path.exists(),
    so every manifest raised AttributeError into the skip-and-log below and _reconcile_prior was a
    silent no-op for its entire life — through the launch, with posting live. The unit tests passed
    because they stubbed this seam AND read_json together, with strings on both sides; nothing ever
    ran the two against each other. tests/test_wave0.py now also exercises this on a real directory."""
    return sorted((config.DERIVED / "manifest").glob("post-*.json"))


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
    ap.add_argument("--allow-local-manifest-write", action="store_true",
                    help="deliberately enable the normal manifest-writing path outside GitHub Actions")
    args = ap.parse_args()
    day = resolve_day(args.day)
    day_json = util.read_json(config.DERIVED / "days" / f"{day}.json", None)
    manifest_path = config.DERIVED / "manifest" / f"post-{day}.json"

    # Local invocation is preview-only by default. S40 proved that even a fully gated dry run reached
    # _flush(), restamped the tracked launch manifest, flipped posting_enabled, and created a spurious
    # next-day manifest. GitHub Actions always sets GITHUB_ACTIONS, preserving the production path
    # byte-for-byte; an operator who genuinely needs local manifest writes must name that intent.
    if "GITHUB_ACTIONS" not in os.environ and not args.allow_local_manifest_write:
        if not (day_json and day_json.get("daily_lines")):
            print(f"no Daily Lines for {day} — nothing to preview")
            return 0
        for party in config.COMPOSITE_PARTIES:
            _dry_result(day, party, day_json, "local preview (manifest writes disabled)")
        return 0

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
            # Inherit the fingerprint assembly stamped on the day being posted, never a
            # fresh build, so the post manifest and the day record agree byte for byte
            # (docs/36 Y1, docs/37 rule 6). Older days without a stamp fall back to build.
            fingerprint = (instrument_fingerprint.inherit(day_json)
                           if isinstance(day_json, dict) and day_json.get("instrument_fingerprint")
                           else instrument_fingerprint.build())
            util.write_json(manifest_path, {
                "schema_version": 1, "kind": "post", "day": day, "generated_at": util.now_utc_iso(),
                "instrument_fingerprint": fingerprint,
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
        thread = build_thread(day, p, day_json, post_date=date.today().isoformat())
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
            # `posts` is the thread's LIVE length, not this run's write count: after a resume the run
            # writes only the missing tail, but the thread standing on the account is the whole one,
            # and that is what /posts.html mirrors. posts_written keeps the audit trail.
            result_by_party[p] = {"party": p, "thread": thread, "posts": len(thread),
                                  "posted": True, "root_uri": out["root_uri"], "creds_present": True,
                                  "posts_written": out["posts_written"]}
            if out.get("recovered"):
                result_by_party[p]["recovered"] = True
                print(f"[post:{p}] root already existed (rkey collision) — resumed at post "
                      f"{out.get('resumed_from', 0) + 1} of {len(thread)}")
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
