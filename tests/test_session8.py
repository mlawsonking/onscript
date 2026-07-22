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


# --- sentence-aware thread packing (S35 Wednesday order, item 3) -----------------------------
def test_thread_packing_breaks_at_sentences_not_mid_clause():
    """The live launch thread read '...our 99 statements today do' / 'not converge on additional
    shared messages.' A word-packer fills to the last word that fits; the first post is the one that
    gets screenshotted, so it should end on a whole thought."""
    text = ("We speak today mainly on the tide act in the house of representatives, echoed by 4 of "
            "us. The most synchronized phrase across our statements is homeland security dhs, "
            "recorded 7 times, first recorded in our corpus from Ted Cruz. Beyond that, our 99 "
            "statements today do not converge on additional shared messages.")
    room = 300 - len("\n" + post_bluesky._POST_MARK)      # the width production actually packs to
    posts = post_bluesky._split(text, limit=room)
    assert len(posts) > 1
    for p in posts[:-1]:
        assert p.rstrip().endswith((".", "!", "?")), f"post cut mid-sentence: {p!r}"
    assert all(len(p) <= room for p in posts)


def test_packing_never_loses_or_reorders_a_word():
    """The load-bearing invariant. An ugly break is cosmetic; a dropped word is a fabricated quote."""
    cases = [
        "One sentence only.",
        "Short. " * 60,
        "We released 5 statements today. It was a Saturday.",
        "No trailing punctuation on this one",
        "   ragged\n\nwhitespace   everywhere\t ",
    ]
    for text in cases:
        posts = post_bluesky._split(text, limit=300)
        assert " ".join(posts).split() == text.split(), text[:40]
        assert all(p for p in posts) and all(len(p) <= 300 for p in posts)

    # A token longer than a whole post has to be cut INSIDE the word, so the word list necessarily
    # changes; what must still hold is that not one character is dropped, added or reordered.
    oversize = "A " + "verylongword" * 40 + " tail."
    posts = post_bluesky._split(oversize, limit=300)
    squash = lambda s: "".join(s.split())                                  # noqa: E731
    assert squash("".join(posts)) == squash(oversize)
    assert all(p for p in posts) and all(len(p) <= 300 for p in posts)


def test_a_sentence_ending_in_a_QUOTE_is_still_a_sentence_boundary():
    """Regression from the first live thread under the new packer (2026-07-21 D).

    Prompt rule 2 requires verbatim member quotes, so this voice ends sentences with `..."`
    routinely. The bare lookbehind sees the quote rather than the period, misses the boundary, merges
    two sentences into one run too long for a post, and the word-packer then cuts it mid-clause --
    the exact defect sentence packing exists to remove. The live thread read "...as a common" /
    "thread today."."""
    text = ('Among our statements, 5 of us echoed the phrase look forward to working, including one '
            'who put it as "and i look forward to seeing these improvements implemented." Across our '
            '130 statements, this was the only line shared widely enough to register as a common '
            'thread today. We note it plainly, without further elaboration.')
    sents = post_bluesky._sentences(text)
    assert len(sents) == 3, [len(s) for s in sents]
    assert all(len(s) <= 262 for s in sents), [len(s) for s in sents]   # each now fits one post

    room = 300 - len("\n" + post_bluesky._POST_MARK)
    posts = post_bluesky._split(text, limit=room)
    for p in posts[:-1]:
        assert p.rstrip().endswith((".", "!", "?", '."', '.”')), f"cut mid-sentence: {p!r}"
    assert " ".join(posts).split() == text.split()      # and still word-exact

    # Curly quotes and a quote-plus-paren close the same way.
    assert len(post_bluesky._sentences('He said “we will act.” Then we acted.')) == 2
    assert len(post_bluesky._sentences('It passed (barely.) We moved on.')) == 2


def test_packing_does_not_split_after_an_abbreviation():
    text = ("Rep. Smith and Sen. Jones of the U.S. House spoke today about No. 5 in the queue, and "
            "we carried that message across a very large number of separate statements this "
            "afternoon, which pushes this line onto a second post so the boundary actually matters.")
    posts = post_bluesky._split(text, limit=300)
    for p in posts:
        assert not p.rstrip().endswith(("Rep.", "Sen.", "U.S.", "No.")), f"split after abbrev: {p!r}"


def test_an_oversize_sentence_still_gets_packed_rather_than_dropped():
    long_sentence = "we say " + "the same words over and over " * 30 + "today."
    posts = post_bluesky._split(long_sentence, limit=300)
    assert len(posts) > 1 and " ".join(posts).split() == long_sentence.split()


def test_build_thread_says_first_recorded_IN_OUR_CORPUS():
    """First-appearance is measured against our record, which starts at STAGE1_EPOCH. Unqualified
    'first recorded' reads as a claim about the phrase's origin in American politics. §S34 (3)."""
    day_json = {"daily_lines": {"D": {"composite": "We spoke today."}},
                "top_synchronized": [{"party": "D", "ngram": "homeland security dhs", "day_peak": 7,
                                      "first_seen": {"date": "2025-01-03"}}]}
    thread = post_bluesky.build_thread("2026-07-20", "D", day_json)
    receipts = [p for p in thread if "Receipts:" in p][0]
    assert "first recorded in our corpus 2025-01-03" in receipts


def test_receipts_link_follows_the_configured_site_url():
    """One source of truth: a second hardcoded literal is a receipts link that 404s the day the
    domain moves, on the only post that carries the citations."""
    from pipeline import config as _config
    assert post_bluesky.SITE == _config.SITE_URL
    day_json = {"daily_lines": {"D": {"composite": "We spoke today."}}, "top_synchronized": []}
    thread = post_bluesky.build_thread("2026-07-20", "D", day_json)
    assert f"{_config.SITE_URL}/day/2026-07-20.html" in " ".join(thread)


_ROOT_RKEY = "3mqng2mws2223"
_ROOT_URI = f"at://did/app.bsky.feed.post/{_ROOT_RKEY}"


def _collision_fakes(live):
    """Fakes for an rkey COLLISION: the root create fails, getRecord finds the root, and listRecords
    reports `live` (rkey, text) replies already hanging off it. Returns (call, http, posted)."""
    posted = []

    def fake_call(url, body, token=None):
        if body.get("rkey"):                      # the deterministic ROOT create -> collides
            raise RuntimeError("could not process request (record already exists)")
        posted.append(body["record"]["text"])
        return {"uri": f"at://did/app.bsky.feed.post/new{len(posted)}", "cid": f"c{len(posted)}"}

    def fake_http(url, jwt=None):
        if "getRecord" in url:
            return {"uri": _ROOT_URI, "cid": "cid-root"}
        recs = [{"uri": f"at://did/app.bsky.feed.post/{k}", "cid": f"c-{k}",
                 "value": {"text": t, "reply": {"root": {"uri": _ROOT_URI}}}} for k, t in live]
        return {"records": list(reversed(recs))}  # listRecords reads newest-first

    return fake_call, fake_http, posted


def _run_collision(live, thread=("head", "reply1", "reply2")):
    rooted = []
    fake_call, fake_http, posted = _collision_fakes(live)
    saved = (post_bluesky._call, post_bluesky._http)
    post_bluesky._call, post_bluesky._http = fake_call, fake_http
    try:
        out = post_bluesky._post_thread({"base": "b", "jwt": "j", "did": "did"}, list(thread),
                                        on_root=lambda u: rooted.append(u), root_rkey=_ROOT_RKEY)
        return out, posted, rooted
    finally:
        post_bluesky._call, post_bluesky._http = saved


def test_post_thread_recovers_root_on_rkey_collision_and_finishes_the_thread():
    """§Session-8 recovers the root without duplicating it; §S30b follow-up finishes the job.

    The first cut returned at recovery with posts_written=0. That left exactly the state it was
    supposed to prevent: a bare head post, no receipts reply — the only post carrying the citation
    link — and no future run would add it, because the manifest now recorded the party as posted.
    The head is never re-posted; the MISSING replies are."""
    out, posted, rooted = _run_collision(live=[])
    assert out["root_uri"] == _ROOT_URI and out.get("recovered") is True
    assert rooted == [_ROOT_URI]                       # root_uri persisted before any reply
    assert posted == ["reply1", "reply2"]              # the truncated tail is completed
    assert out["posts_written"] == 2 and out["resumed_from"] == 1


def test_a_resumed_thread_never_re_posts_replies_that_are_already_live():
    out, posted, _ = _run_collision(live=[("3mqng2mws2224", "reply1")])
    assert posted == ["reply2"]                        # only the missing one
    assert out["posts_written"] == 1 and out["resumed_from"] == 2


def test_a_resume_refuses_to_splice_a_thread_that_was_re_authored():
    """If the live replies are not a prefix of the thread in hand, the day was re-authored between
    runs. Appending would staple two different threads together, so it stops and leaves a partial
    for the dead-man + the reconcile backstop."""
    raised = ""
    try:
        _run_collision(live=[("3mqng2mws2224", "a reply from some other version of this day")])
    except RuntimeError as e:
        raised = str(e)
    assert "refusing to append" in raised


# --- signed post archive -------------------------------------------------------------------
def test_posts_archive_renders_and_maps_at_uri_to_web():
    threads = [{"day": "2026-07-13", "generated_at": "2026-07-13T12:00:00Z", "party": "D",
                "thread": ["We speak today of housing.", "Receipts: https://onscript.news/day/2026-07-13.html"],
                "root_uri": "at://did:plc:abc/app.bsky.feed.post/xyz"}]
    html = site.posts_log_body(threads)
    assert "We speak today of housing." in html
    assert "not ours" in html                                        # the forgery-defense line
    assert "bsky.app/profile/did:plc:abc/post/xyz" in html           # at:// -> web url
    assert "No posts recorded in this build" in site.posts_log_body([])  # environment-neutral empty state


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


# --- sub-gram containment collapse (fold a fragment into its fuller phrase; never absorb a hub) -----
def test_content_subrun_detects_contiguous_fragments_only():
    assert build._content_subrun("children born in", "children born in the united states")
    assert build._content_subrun("born in the united states", "children born in the united states")
    assert not build._content_subrun("children states", "children born in the united states")   # gap
    assert not build._content_subrun("children born in the united states", "children born in")   # not shorter


def test_subgram_folds_a_fragment_into_the_fuller_phrase():
    """A fragment used by ~the same members as the fuller phrase it sits inside folds into that fuller,
    more specific label — kept at its OWN honest peak, never inflated."""
    rows = [{"ngram": "children born in", "day_peak": 14, "party": "D"},
            {"ngram": "children born in the united states", "day_peak": 12, "party": "D"}]
    kept = {r["ngram"]: r for r in build._collapse_subgrams(rows)}
    assert "children born in" not in kept                                  # fragment folded away
    assert kept["children born in the united states"]["day_peak"] == 12    # fuller label, own peak


def test_subgram_guard_a_hub_is_never_absorbed():
    """The critical guard: a fragment whose peak GREATLY exceeds the fuller phrase's is a hub (used
    across many messages) and stays its own row — never absorbed, never absorbing."""
    rows = [{"ngram": "born in the united states", "day_peak": 36, "party": "D"},         # flagship hub
            {"ngram": "children born in the united states", "day_peak": 12, "party": "D"},
            {"ngram": "the trump administration", "day_peak": 20, "party": "D"},           # entity hub
            {"ngram": "sue the trump administration", "day_peak": 6, "party": "D"},
            {"ngram": "hold the trump administration accountable", "day_peak": 5, "party": "D"}]
    kept = {r["ngram"] for r in build._collapse_subgrams(rows)}
    assert {"born in the united states", "children born in the united states"} <= kept    # 36 !≈ 12
    assert {"the trump administration", "sue the trump administration",
            "hold the trump administration accountable"} <= kept                          # hub intact


def test_collapse_and_rank_dedups_flagship_without_over_merging():
    """End-to-end on real 06-30 flagship rows: redundant fragments fold (statement-after-the-supreme,
    children-born-in, the-supreme-court-upheld) while the flagship hub + distinct messages all survive,
    peak-ranked."""
    def P(ng, pk):
        return {"ngram": ng, "day_peak": pk, "party": "D"}
    rows = [P("born in the united states", 36), P("statement after the supreme", 20),
            P("statement after the supreme court", 18), P("children born in", 14),
            P("children born in the united states", 12), P("supreme court upheld", 11),
            P("the supreme court upheld", 9)]
    kept = [r["ngram"] for r in build.collapse_and_rank(rows, k=20)]
    assert "statement after the supreme" not in kept and "statement after the supreme court" in kept
    assert "children born in" not in kept and "children born in the united states" in kept
    assert "the supreme court upheld" not in kept and "supreme court upheld" in kept   # padding pass
    assert "born in the united states" in kept and kept[0] == "born in the united states"  # hub, peak-ranked
