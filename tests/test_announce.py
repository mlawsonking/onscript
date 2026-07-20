"""The launch announce (docs/23 §7.3) — gates, verbatim integrity, idempotency.

This is a path that posts PUBLICLY from the house account, so the tests that matter are the ones
that prove it does NOT post: no --confirm, POSTING_ENABLED off, and missing credentials each have to
hold independently. `_authenticate` and `_post_thread` are replaced with exploding stubs so that any
run which reaches the network fails loudly here rather than on launch night.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import announce, config, post_bluesky  # noqa: E402

TEXT = ("OnScript reads what every member of Congress publishes and compresses each party's day into "
        "one voice, with receipts. Same pipeline, same prompts, same thresholds for both parties, "
        "audited in public every night. It starts today.")


class _Exploded(AssertionError):
    pass


def _no_network():
    def boom(*a, **k):
        raise _Exploded("network was touched by a gated announce run")
    return boom


def _run(argv, *, env=None, allow_network=False):
    """Run announce.main() with argv/env, with the AT-Proto primitives stubbed to explode."""
    saved_argv, saved_env = sys.argv, dict(os.environ)
    saved_auth, saved_post = post_bluesky._authenticate, post_bluesky._post_thread
    saved_manifest = announce.MANIFEST
    tmp = Path(tempfile.mkdtemp(prefix="onscript-announce-"))
    try:
        sys.argv = ["announce.py"] + argv
        for k in ("POSTING_ENABLED", "BSKY_BRAND_HANDLE", "BSKY_BRAND_PASSWORD", "ANNOUNCE_TEXT"):
            os.environ.pop(k, None)
        os.environ["ANNOUNCE_TEXT"] = TEXT
        os.environ.update(env or {})
        announce.MANIFEST = tmp / "announce.json"
        if not allow_network:
            post_bluesky._authenticate = _no_network()
            post_bluesky._post_thread = _no_network()
        return announce.main(), announce.MANIFEST
    finally:
        sys.argv = saved_argv
        os.environ.clear(); os.environ.update(saved_env)
        post_bluesky._authenticate, post_bluesky._post_thread = saved_auth, saved_post
        announce.MANIFEST = saved_manifest


# --- the three gates, each holding ALONE ---------------------------------------------------
def test_without_confirm_it_is_a_dry_run_even_with_everything_else_live():
    rc, _ = _run([], env={"POSTING_ENABLED": "true", "BSKY_BRAND_HANDLE": "onscript.news",
                          "BSKY_BRAND_PASSWORD": "app-pass"})
    assert rc == 0          # the exploding stubs would have raised if it reached the network


def test_posting_enabled_off_holds_even_with_confirm_and_real_creds():
    """The master S3 switch outranks --confirm. Same kill-test shape as the daily posting path."""
    rc, _ = _run(["--confirm"], env={"POSTING_ENABLED": "false", "BSKY_BRAND_HANDLE": "onscript.news",
                                     "BSKY_BRAND_PASSWORD": "app-pass"})
    assert rc == 0


def test_missing_credentials_hold_even_with_confirm_and_posting_enabled():
    rc, _ = _run(["--confirm"], env={"POSTING_ENABLED": "true"})
    assert rc == 0


def test_an_absent_posting_enabled_variable_is_off_not_on():
    """Default-off: an unset repo variable must never read as enabled."""
    rc, _ = _run(["--confirm"], env={"BSKY_BRAND_HANDLE": "onscript.news",
                                     "BSKY_BRAND_PASSWORD": "app-pass"})
    assert rc == 0


# --- verbatim integrity --------------------------------------------------------------------
def test_the_thread_reconstructs_the_approved_text_word_for_word():
    thread = announce.build_thread(TEXT)
    assert announce.verbatim_ok(TEXT, thread)
    assert all(len(p) <= announce.LIMIT for p in thread)
    assert all(p.strip() for p in thread)


def test_verbatim_ok_rejects_a_thread_that_dropped_or_changed_a_word():
    thread = announce.build_thread(TEXT)
    assert not announce.verbatim_ok(TEXT, thread[:-1])                      # dropped tail
    assert not announce.verbatim_ok(TEXT, thread[:-1] + [thread[-1] + " extra"])
    assert not announce.verbatim_ok(TEXT, [t.replace("both", "one") for t in thread])


def test_the_announce_carries_no_automated_composite_marker():
    """The marker labels the machine-distilled party voice. The announce is human-approved editorial
    copy, so stamping it would be a FALSE label — the inaccuracy, not the caution."""
    thread = announce.build_thread(TEXT)
    assert not any(post_bluesky._POST_MARK in p for p in thread)
    assert not any("🤖" in p for p in thread)


def test_author_chosen_post_boundaries_are_honored_exactly():
    """`---` lines are the author's break points. Mechanical packing would cut a launch announce
    mid-thought; the author gets to decide, and the text stays verbatim either way."""
    text = "First post body.\n---\nSecond post body.\n---\nThird post body."
    thread = announce.build_thread(text)
    assert thread == ["First post body.", "Second post body.", "Third post body."]
    assert announce.verbatim_ok(text, thread)


def test_an_over_length_author_post_is_refused_not_silently_repacked():
    """Refusing is the point: silently re-splitting would hand the boundaries back to the machine
    exactly where the author was most explicit about wanting them."""
    text = "ok post\n---\n" + ("x" * (announce.LIMIT + 1))
    try:
        announce.build_thread(text)
        raise AssertionError("an over-length author post was accepted")
    except ValueError as e:
        assert "exceed" in str(e) and "post 2" in str(e)


def test_a_long_announce_splits_into_a_thread_and_stays_verbatim():
    long_text = " ".join(f"word{i}" for i in range(400))
    thread = announce.build_thread(long_text)
    assert len(thread) > 1
    assert announce.verbatim_ok(long_text, thread)


# --- refusals -------------------------------------------------------------------------------
def test_empty_or_whitespace_text_is_refused_not_posted_as_an_empty_post():
    for bad in ("", "   \n\t "):
        saved = dict(os.environ)
        try:
            os.environ["ANNOUNCE_TEXT"] = bad
            announce.load_text()
            raise AssertionError("empty announce text was accepted")
        except ValueError:
            pass
        finally:
            os.environ.clear(); os.environ.update(saved)


def test_it_is_manual_dispatch_only_no_schedule_trigger():
    """Locked: an announce that can fire on a cron is the accident the posting gate exists to stop."""
    wf = (Path(__file__).resolve().parent.parent / ".github" / "workflows" / "announce.yml").read_text(encoding="utf-8")
    # Comments in that file discuss cron accidents on purpose, so assert on the YAML, not the prose:
    # strip comment lines, then require a dispatch trigger and no schedule trigger at all.
    body = "\n".join(l for l in wf.splitlines() if not l.lstrip().startswith("#"))
    assert "workflow_dispatch:" in body
    assert "schedule:" not in body and "cron:" not in body


# --- idempotency ----------------------------------------------------------------------------
def test_a_recorded_prior_announce_is_never_reposted():
    import json
    saved_manifest = announce.MANIFEST
    tmp = Path(tempfile.mkdtemp(prefix="onscript-announce-prior-"))
    try:
        announce.MANIFEST = tmp / "announce.json"
        announce.MANIFEST.write_text(json.dumps(
            {"posted": True, "root_uri": "at://did:plc:x/app.bsky.feed.post/abc",
             "announced_at": "2026-07-20T14:00:00Z"}), encoding="utf-8")
        assert announce.already_announced() is not None
    finally:
        announce.MANIFEST = saved_manifest


def test_a_failed_prior_attempt_with_no_root_uri_is_retryable():
    """The mirror of the above: a clean failure left no post, so it must NOT be treated as done."""
    import json
    saved_manifest = announce.MANIFEST
    tmp = Path(tempfile.mkdtemp(prefix="onscript-announce-fail-"))
    try:
        announce.MANIFEST = tmp / "announce.json"
        announce.MANIFEST.write_text(json.dumps({"posted": False}), encoding="utf-8")
        assert announce.already_announced() is None
    finally:
        announce.MANIFEST = saved_manifest


def test_the_root_rkey_is_deterministic_so_a_retry_cannot_double_post():
    a = post_bluesky._root_rkey("2026-07-20", "ANNOUNCE")
    b = post_bluesky._root_rkey("2026-07-20", "ANNOUNCE")
    assert a == b and len(a) == 13
