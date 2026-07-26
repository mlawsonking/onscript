"""The launch announce — a MANUAL, one-off post from the house account (@onscript.news).

docs/23 §7.3 (the release schedule) makes the announce the last step of the Monday launch sequence:
POSTING_ENABLED on -> repo public -> announce. This module is that step, and it is deliberately the
narrowest possible thing:

  * It is MANUAL-DISPATCH ONLY. There is no cron, no schedule trigger, and nothing in the daily
    pipeline imports it. `.github/workflows/announce.yml` is workflow_dispatch-only. If a future
    session is tempted to wire this into a schedule: don't — the first (and only) brand announce is
    Michael's act, and an automated announce is exactly the "cron accident" the whole posting gate
    exists to prevent.
  * It posts APPROVED TEXT VERBATIM and composes nothing. The text never lives in this repo (it is
    drafted to X:\\onscript-data\\drafts\\ and approved by Michael); it arrives at runtime as the
    workflow_dispatch input, so the act of pasting the approved text IS the approval.
  * It carries NO automated-composite marker. `post_bluesky._POST_MARK` ("automated composite")
    labels the machine-distilled party voice; the announce is human-approved editorial text, so
    stamping it would be a FALSE label, not a cautious one. The account-level disclosure and the
    site's About page carry the standing "what this is" statement.

Gates, in order (mirroring post_bluesky's, plus one):
  1. --confirm  — absent (the default) => DRY RUN. Prints the thread, touches no network.
  2. POSTING_ENABLED (repo variable) — the same master S3 switch the daily posting path obeys.
  3. Credentials present (BSKY_BRAND_HANDLE + BSKY_BRAND_PASSWORD).
  4. Idempotency — a recorded prior announce is never re-posted, belt (manifest) and braces
     (deterministic root rkey, which collides server-side instead of creating a second post).

Reuses the Session-8d live-smoke-tested AT-Proto primitives from post_bluesky rather than
re-implementing them: `_authenticate` (the real createSession), `_post_thread` (deterministic-rkey
root + collision recovery), `_split`, `_root_rkey`. Those were verified against a live PDS with 13/13
checks; a second implementation would be a second thing that can be wrong on launch night.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from pipeline import config, instrument_fingerprint, ops, post_bluesky, privacy, util  # noqa: E402

HANDLE_ENV = "BSKY_BRAND_HANDLE"
PW_ENV = "BSKY_BRAND_PASSWORD"
MANIFEST = config.DERIVED / "manifest" / "announce.json"
LIMIT = 300


def load_text(path: str | None = None) -> str:
    """The approved announce text, from --text-file or the ANNOUNCE_TEXT env var. Never from a
    committed file: the text is Michael's approved editorial copy and lives outside the repo."""
    raw = ""
    if path:
        raw = Path(path).read_text(encoding="utf-8")
    elif os.environ.get("ANNOUNCE_TEXT"):
        raw = os.environ["ANNOUNCE_TEXT"]
    text = raw.strip()
    if not text:
        raise ValueError(
            "no announce text supplied — pass --text-file <path> or set ANNOUNCE_TEXT. "
            "The text is never stored in this repo; it comes from the approved draft.")
    return text


POST_SEPARATOR = "---"


def build_thread(text: str) -> list[str]:
    """Split the approved text into <=300-char posts. VERBATIM: this only chooses where the breaks
    fall — it never adds, trims, or rewords. `verbatim_ok` locks that.

    If the text contains `---` on its own line, THOSE are the post boundaries: the author decides
    where a thread breaks, because mechanical word-packing would otherwise cut a launch announce
    mid-thought. An author-chosen post that exceeds the limit is a REFUSAL (raised here), not a
    silent re-split — quietly re-packing would hand the boundaries back to the machine at exactly
    the moment the author was most explicit about wanting them.

    With no separators, packing is mechanical (fine for a single-post announce)."""
    blocks = [b.strip() for b in text.split(f"\n{POST_SEPARATOR}\n")]
    blocks = [b for b in blocks if b]
    if len(blocks) > 1:
        too_long = [(i + 1, len(b)) for i, b in enumerate(blocks) if len(b) > LIMIT]
        if too_long:
            raise ValueError(
                "author-separated post(s) exceed the "
                f"{LIMIT}-char limit: " + ", ".join(f"post {i} is {n} chars" for i, n in too_long))
        return blocks
    return post_bluesky._split(text, limit=LIMIT)


def verbatim_ok(text: str, thread: list[str]) -> bool:
    """True iff the thread reconstructs the approved text exactly, word for word. Splitting is
    allowed to change WHITESPACE (that is what packing into posts means) and nothing else. The
    `---` boundary markers are structure, not content, so they are not expected in the output."""
    expected = [w for w in text.split() if w != POST_SEPARATOR]
    return expected == " ".join(thread).split()


def _print_thread(thread: list[str], reason: str) -> None:
    print(f"\n[dry-run announce:house] {reason} — would post {len(thread)} post(s):")
    for i, p in enumerate(thread, 1):
        print(f"  --- post {i} ({len(p)} chars) ---\n  " + p.replace("\n", "\n  "))


def already_announced() -> dict | None:
    """A prior successful announce, if any. The announce is a ONE-OFF: if this returns a record, the
    house account has already announced and this run must do nothing."""
    prior = util.read_json(MANIFEST, {}) or {}
    return prior if prior.get("posted") and prior.get("root_uri") else None


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Post the approved launch announce (manual, one-off).")
    ap.add_argument("--text-file", default=None, help="path to the approved announce text")
    ap.add_argument("--confirm", action="store_true",
                    help="actually post. Without this flag the run is a dry run (no network).")
    ap.add_argument("--day", default=None, help="date stamp for the deterministic rkey (default: today)")
    args = ap.parse_args()

    day = args.day or util.product_day()
    text = load_text(args.text_file)
    try:
        thread = build_thread(text)
    except ValueError as e:
        print(f"[announce] ABORT — {e}")
        return 1

    # Verbatim is a hard invariant, not a preference: a mangled announce is a public first impression
    # that cannot be un-seen. Refuse rather than post something the approver did not approve.
    if not verbatim_ok(text, thread):
        print("[announce] ABORT — the split thread does not reconstruct the approved text verbatim.")
        return 1

    # Art. XIII belt. The announce is human-approved, but the privacy floor is unamendable and applies
    # to every published surface without exception — including copy a human wrote.
    if privacy.is_suppressed(text):
        print("[announce] ABORT — the announce text trips the privacy floor (names a private individual).")
        return 1

    prior = already_announced()
    if prior:
        print(f"[announce] already announced at {prior.get('root_uri')} ({prior.get('announced_at')}) "
              f"— idempotent skip, nothing posted.")
        return 0

    posting_enabled = config.posting_enabled()
    creds = bool(os.environ.get(HANDLE_ENV) and os.environ.get(PW_ENV))

    if not args.confirm:
        _print_thread(thread, "no --confirm (default)")
        print(f"\n[announce] DRY RUN. posting_enabled={posting_enabled} creds_present={creds}. "
              f"No network was touched. Re-run with --confirm to post.")
        return 0
    if not posting_enabled:
        _print_thread(thread, "POSTING_ENABLED is off")
        print("\n[announce] HELD — POSTING_ENABLED is off. That gate is the launch switch; flip it "
              "first (it is the step before the announce in the docs/23 §7.3 sequence).")
        return 0
    if not creds:
        _print_thread(thread, f"missing {HANDLE_ENV}/{PW_ENV}")
        print(f"\n[announce] HELD — house-account credentials are not present.")
        return 0

    handle = os.environ[HANDLE_ENV]
    print(f"[announce] posting {len(thread)} post(s) as {handle} …")
    try:
        session = post_bluesky._authenticate(handle, os.environ[PW_ENV])
    except Exception as e:
        print(f"[announce] FAILED — could not authenticate as {handle}: {e}")
        ops.ntfy("OnScript announce FAILED",
                 f"house-account auth error ({e.__class__.__name__}) — nothing posted", priority="high")
        return 1

    def _record(uri, posts=0, recovered=False):
        try:
            util.write_json(MANIFEST, {
                "schema_version": 1, "kind": "announce", "day": day,
                "instrument_fingerprint": instrument_fingerprint.build(),
                "announced_at": util.now_utc_iso(), "handle": handle, "posted": True,
                "root_uri": uri, "posts": posts, "recovered": recovered, "thread": thread,
            })
        except Exception as e:
            print(f"[announce] manifest write failed (non-fatal): {e}")

    try:
        out = post_bluesky._post_thread(
            session, thread,
            on_root=lambda uri: _record(uri, posts=1),          # durable BEFORE any reply
            # _root_rkey maps anything that isn't "D" to clock-id 1, the same id the R composite
            # uses — which is harmless here because rkeys are scoped to a REPO and this posts to the
            # house account's DID, not red's. Same key, different repo, no collision.
            root_rkey=post_bluesky._root_rkey(day, "ANNOUNCE"),
        )
    except Exception as e:
        print(f"[announce] FAILED mid-thread: {e}")
        ops.ntfy("OnScript announce FAILED",
                 f"mid-thread failure ({e.__class__.__name__}) — check the account before retrying; "
                 f"the root rkey is deterministic so a retry recovers rather than duplicates",
                 priority="high")
        return 1

    _record(out.get("root_uri"), posts=out.get("posts_written", 0), recovered=out.get("recovered", False))
    if out.get("recovered"):
        print(f"[announce] root already existed (rkey collision) — recovered {out['root_uri']}, "
              f"nothing duplicated.")
    else:
        print(f"[announce] posted {out.get('posts_written')} post(s). Root: {out.get('root_uri')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
