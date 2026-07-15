"""Session-8 pre-posting hardening: post atomicity (both-or-neither), the signed post archive, and
the receipts denominators. All $0 — posting I/O stubbed, no network, no key."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import post_bluesky, site  # noqa: E402


def _env(**kv):
    prev = {k: os.environ.get(k) for k in kv}
    for k, v in kv.items():
        os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def restore():
        for k, v in prev.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    return restore


_DAY = {"day": "2026-06-30", "daily_lines": {"D": {"composite": "d"}, "R": {"composite": "r"}},
        "top_synchronized": []}


def _run_main(day, day_json, prior, post_real, ntfy_sink):
    writes = {}

    def fake_read(p, default=None):
        n = Path(str(p)).name
        if n == "assemble-latest.json":
            return {"day": day}
        if n == f"{day}.json":
            return day_json
        if n == f"post-{day}.json":
            return prior
        return {} if default is None else default

    saved = (post_bluesky.util.read_json, post_bluesky.util.write_json,
             post_bluesky._post_real, post_bluesky.ops.ntfy, sys.argv)
    post_bluesky.util.read_json = fake_read
    post_bluesky.util.write_json = lambda p, o: writes.__setitem__(Path(str(p)).name, o)
    post_bluesky._post_real = post_real
    post_bluesky.ops.ntfy = lambda *a, **k: ntfy_sink.append((a, k))
    sys.argv = ["post", "--day", day]
    try:
        rc = post_bluesky.main()
    finally:
        (post_bluesky.util.read_json, post_bluesky.util.write_json,
         post_bluesky._post_real, post_bluesky.ops.ntfy, sys.argv) = saved
    return rc, writes.get(f"post-{day}.json", {})


# --- atomicity: both composites or neither -------------------------------------------------
def test_atomic_hold_posts_neither_when_one_party_lacks_creds():
    """Posting ON, D has creds but R doesn't -> post NEITHER (never one account up, one silent), and
    the dead-man fires so a human fixes it."""
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="blue.onscript.news", BSKY_BLUE_PASSWORD="x",
                   BSKY_RED_HANDLE=None, BSKY_RED_PASSWORD=None)
    real, ntfy = [], []
    try:
        rc, man = _run_main("2026-06-30", _DAY, {},
                            post_real=lambda *a, **k: real.append(a) or {"party": "?", "posted": True, "posts": 2},
                            ntfy_sink=ntfy)
        assert rc == 0
        assert real == []                       # NOTHING posted for real — the atomic hold held
        assert man["atomic_hold"] is True
        res = {r["party"]: r for r in man["results"]}
        assert res["D"]["posted"] is False and "atomic hold" in res["D"]["reason"]
        assert ntfy, "dead-man must fire on an atomic hold"
    finally:
        restore()


def test_asymmetric_outcome_is_flagged_and_alerts():
    """Both have creds, D posts, R throws mid-post -> exactly one account up -> asymmetric flag + alert."""
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x",
                   BSKY_RED_HANDLE="r", BSKY_RED_PASSWORD="y")
    ntfy = []

    def real(handle, pw, thread, party):
        if party == "R":
            raise RuntimeError("bsky 500")
        return {"party": party, "posted": True, "posts": len(thread),
                "root_uri": "at://did:plc:abc/app.bsky.feed.post/xyz"}
    try:
        rc, man = _run_main("2026-06-30", _DAY, {}, post_real=real, ntfy_sink=ntfy)
        assert man["asymmetric"] is True and ntfy
    finally:
        restore()


def test_post_result_carries_thread_for_the_archive():
    restore = _env(POSTING_ENABLED=None, BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x")
    try:
        r = post_bluesky.post_party("2026-06-30", "D", _DAY)  # posting off -> dry-run, still records thread
        assert isinstance(r.get("thread"), list) and len(r["thread"]) >= 1
    finally:
        restore()


# --- signed post archive -------------------------------------------------------------------
def test_posts_archive_renders_and_maps_at_uri_to_web():
    threads = [{"day": "2026-07-13", "generated_at": "2026-07-13T12:00:00Z", "party": "D",
                "thread": ["We speak today of housing.", "Receipts: https://onscript.news/day/2026-07-13.html"],
                "root_uri": "at://did:plc:abc/app.bsky.feed.post/xyz"}]
    html = site.posts_log_body(threads)
    assert "We speak today of housing." in html
    assert "not ours" in html                                        # the forgery-defense line
    assert "bsky.app/profile/did:plc:abc/post/xyz" in html           # at:// -> web url
    assert "No posts yet" in site.posts_log_body([])                 # empty state


# --- denominators in view ------------------------------------------------------------------
def test_receipts_denominator_travels_with_count_and_said_is_gone():
    tps = [{"member_count": 10, "topics": ["housing"],
            "citations": [{"member": "Jane Doe", "party": "D", "state": "CA", "date": "2026-07-13",
                           "url": "https://x.house.gov/y", "quote": "the housing act"}]}]
    html = site.receipts_strip("D", tps, caucus=263)
    assert "carried" in html and "members</span> said" not in html   # said -> carried
    assert "10 of 263" in html and "3.8%" in html                    # denominator + % in view
