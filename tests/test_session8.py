"""Session-8 pre-posting hardening: post atomicity (both-or-neither), the signed post archive, and
the receipts denominators. All $0 — posting I/O stubbed, no network, no key."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import build, post_bluesky, site  # noqa: E402


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


# Full atomicity (both-or-neither, atomic auth pre-flight, partial-post idempotency, asymmetric
# dead-man) is covered against the new API in test_wave0.py. Here: the archive + denominators.
def test_post_result_records_thread_for_the_archive():
    """Even a non-posting (dry / held) result carries the full thread text, so the on-domain signed
    archive can mirror exactly what was — or would be — posted."""
    restore = _env(POSTING_ENABLED=None, BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x")
    try:
        r = post_bluesky._dry_result("2026-06-30", "D", _DAY, "posting disabled")
        assert isinstance(r.get("thread"), list) and len(r["thread"]) >= 1
    finally:
        restore()


def test_root_rkey_is_a_valid_deterministic_tid():
    """app.bsky.feed.post REJECTS a non-TID rkey ("Invalid TID string", verified live #108). The
    deterministic root key must therefore be a valid 13-char TID — unique per (day, party), stable
    across runs — not a human-readable string."""
    s32 = "234567abcdefghijklmnopqrstuvwxyz"
    a = post_bluesky._root_rkey("2026-07-14", "D")
    assert len(a) == 13 and all(c in s32 for c in a)             # valid TID shape (would 400 otherwise)
    assert a == post_bluesky._root_rkey("2026-07-14", "D")       # deterministic
    assert a != post_bluesky._root_rkey("2026-07-14", "R")       # party-unique
    assert a != post_bluesky._root_rkey("2026-07-15", "D")       # day-unique
    assert post_bluesky._root_rkey("garbage-not-a-date", "D")    # never raises (falls back)


def test_post_thread_reraises_a_genuine_failure_not_masked_as_recovery():
    """§Session-8c: the over-broad recovery `except` once swallowed a REAL create error (the launch-
    blocking 400) as a 'collision'. Now recovery is probe-based: if the record does NOT exist after a
    create error, the ORIGINAL error propagates so the caller records posted=False + the dead-man fires."""
    def fake_call(url, body, token=None):
        raise RuntimeError("400 bad content")

    def fake_http(url, jwt=None):
        raise RuntimeError("404 record does not exist")   # probe: the create genuinely failed

    saved = (post_bluesky._call, post_bluesky._http)
    post_bluesky._call, post_bluesky._http = fake_call, fake_http
    try:
        raised = ""
        try:
            post_bluesky._post_thread({"base": "b", "jwt": "j", "did": "did"}, ["head", "r1"],
                                      on_root=lambda u: None, root_rkey="3mqng2mws2223")
        except RuntimeError as e:
            raised = str(e)
        assert raised == "400 bad content"   # the create error, NOT the probe error, NOT swallowed
    finally:
        post_bluesky._call, post_bluesky._http = saved


def test_post_thread_recovers_root_on_rkey_collision_without_duplicating():
    """§Session-8: if the root create's response is lost, a re-run's root create collides on the
    deterministic rkey; we RECOVER the root via getRecord — never a duplicate head post, never
    re-posted replies (posts_written=0)."""
    def fake_call(url, body, token=None):
        raise RuntimeError("could not process request (record already exists)")

    def fake_http(url, jwt=None):
        return {"uri": "at://did/app.bsky.feed.post/onscript-2026-07-14-d", "cid": "cid1"}

    rooted = []
    saved = (post_bluesky._call, post_bluesky._http)
    post_bluesky._call, post_bluesky._http = fake_call, fake_http
    try:
        out = post_bluesky._post_thread({"base": "b", "jwt": "j", "did": "did"},
                                        ["head", "reply1", "reply2"],
                                        on_root=lambda u: rooted.append(u), root_rkey="onscript-2026-07-14-d")
        assert out["root_uri"].endswith("onscript-2026-07-14-d")
        assert out["posts_written"] == 0 and out.get("recovered") is True  # replies NOT re-posted
        assert rooted == [out["root_uri"]]                                 # root_uri persisted for idempotency
    finally:
        post_bluesky._call, post_bluesky._http = saved


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


# --- denominators + archival fallback in the receipts --------------------------------------
def test_receipts_denominator_travels_with_count_and_said_is_gone():
    tps = [{"member_count": 10, "topics": ["housing"],
            "citations": [{"member": "Jane Doe", "party": "D", "state": "CA", "date": "2026-07-13",
                           "url": "https://x.house.gov/y", "quote": "the housing act"}]}]
    html = site.receipts_strip("D", tps, caucus=263)
    assert "carried" in html and "members</span> said" not in html   # said -> carried
    assert "10 of 263" in html and "3.8%" in html                    # denominator + % in view
    # every source carries a Wayback archival fallback so a rotted .gov link never dead-ends
    assert ">source</a>" in html and ">archived</a>" in html
    assert "web.archive.org/web/20260713/https://x.house.gov/y" in html


# --- near-duplicate phrase collapse (stopword padding only) --------------------------------
def test_collapse_merges_stopword_padding_keeps_content_variants():
    """A stopword-only variant ("the …") folds into the clean phrase; a content difference (an
    acronym) stays its own row. The clean phrase is the representative, carrying the family max peak."""
    rows = [
        {"ngram": "water resources development act", "day_peak": 14, "party": "D"},
        {"ngram": "the water resources development act", "day_peak": 13, "party": "D"},   # 'the' -> merges
        {"ngram": "water resources development act wrda", "day_peak": 8, "party": "D"},   # 'wrda' -> stays
        {"ngram": "transportation and infrastructure", "day_peak": 13, "party": "D"},
    ]
    kept = {r["ngram"]: r for r in build._collapse_nested(rows)}
    assert "the water resources development act" not in kept          # stopword variant merged away
    assert kept["water resources development act"]["day_peak"] == 14  # clean rep, family max peak
    assert "water resources development act wrda" in kept             # acronym (content) kept separate
    assert "transportation and infrastructure" in kept


def test_collapse_does_not_let_a_generic_hub_absorb_distinct_messages():
    """The critical guard (adversarial-review finding): a generic entity phrase must NOT swallow the
    distinct coordinated messages that contain it — that would hide the real signal behind a label."""
    rows = [
        {"ngram": "the trump administration", "day_peak": 20, "party": "D"},
        {"ngram": "sue the trump administration", "day_peak": 6, "party": "D"},
        {"ngram": "hold the trump administration accountable", "day_peak": 5, "party": "D"},
    ]
    kept = {r["ngram"] for r in build._collapse_nested(rows)}
    assert kept == {"the trump administration", "sue the trump administration",
                    "hold the trump administration accountable"}  # all three survive
