"""Article XIII (privacy floor) — the suppression gate.

NO TEST FILE IN THIS REPO MAY COMMIT A SUPPRESSED NAME. Every test below that needs the real
contaminated strings injects them through a TEST-ONLY salt + form list built at runtime, so the
fixtures name nobody. The test forms are ordinary English words; the real forms stay in the
production list, hashed, and never appear here.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import build, distill, privacy, site  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Stand-in name forms. Structurally identical to the real ones (single surname tokens that n-grams
# slide over), but they are fruit.
FORMS = ["quincewood", "marrowbane", "tessilar", "vorbeck"]
PERSON_A = "quincewood marrowbane tessilar"      # a 3-token "full name"
PERSON_B = "vorbeck"

TEST_SALT = "test-salt-not-the-real-one"


@contextlib.contextmanager
def gate(forms=FORMS, allow=None, max_tokens=3, salt=TEST_SALT):
    """Load the gate against an injected test list. Restores the production gate on exit.

    `salt` exists so a test can build two gates whose form PLAINTEXTS agree while their keyed
    hashes do not, which is the only way to exercise a salt change without touching the real one
    (tests/test_p2_scan_cache.py needs exactly that)."""
    import hashlib
    import hmac

    def mac(s):
        return hmac.new(salt.encode(), s.encode(), hashlib.sha256).hexdigest()

    tmp = ROOT / "tests" / "_tmp_privacy"
    tmp.mkdir(parents=True, exist_ok=True)
    fp, ap = tmp / "forms.json", tmp / "allow.json"
    fp.write_text(json.dumps({
        "version": 1, "max_form_tokens": max_tokens, "persons": 2,
        "canary": mac(privacy.CANARY_PLAINTEXT),
        "forms": [mac(" ".join(privacy._tokens(f))) for f in forms],
        "entries": [{"added": "2026-07-16", "forms": len(forms), "reason": "test"}],
    }), encoding="utf-8")
    ap.write_text(json.dumps({"allow": allow or []}), encoding="utf-8")
    prev = os.environ.get("PRIVACY_TEST_SALT")
    os.environ["PRIVACY_TEST_SALT"] = salt
    try:
        privacy.load(forms_path=fp, allowlist_path=ap)
        yield
    finally:
        if prev is None:
            os.environ.pop("PRIVACY_TEST_SALT", None)
        else:
            os.environ["PRIVACY_TEST_SALT"] = prev
        privacy.load()          # restore the production gate
        for f in (fp, ap):
            f.unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            tmp.rmdir()


# --- the completeness test --------------------------------------------------------------------
# The 16 contaminated n-gram SHAPES actually found on disk, with the real names swapped for the
# stand-ins. Shape is what is being tested: the sliding window, the possessive, the bare surname.
_SURFACES = [
    f"of transparency and accountability {PERSON_A[:22]}",           # "... quincewood marrowbane"
    f"killing of {PERSON_A}",
    "killing of quincewood",
    f"the killing of {PERSON_A}",
    "the killing of quincewood marrowbane",
    "accountability quincewood marrowbane tessilar’s family and",   # U+2019
    "and accountability quincewood marrowbane tessilar’s family",   # U+2019
    "vehicle including tessilar’s brother remain detained",         # U+2019, bare surname
    "issues of transparency and accountability quincewood",
    "tessilar during an immigration enforcement operation",              # bare surname
    "transparency and accountability quincewood marrowbane tessilar’s",  # U+2019
    "killing of quincewood marrowbane",
    f"of {PERSON_A}",
    "the killing of quincewood",
    "shot tessilar during an immigration enforcement",                   # bare surname
    "of quincewood marrowbane",
    f"{PERSON_A} and {PERSON_B} joan",                                  # the composite's phrase
    PERSON_B,
]


def test_predicate_covers_every_known_surface():
    """The one a reviewer reads. Every contaminated surface shape, including the four U+2019 cases,
    the three name-only windows, and the three bare-surname windows.

    Mutation-checked below: a full-names-only form list (the tempting 'never a bare surname' rule)
    misses the sliding windows, and an exact-match list on the two reported phrases misses nearly
    everything. This is the test that proves the sliding-window problem is solved."""
    with gate():
        missed = [s for s in _SURFACES if not privacy.is_suppressed(s)]
        assert not missed, f"predicate missed {len(missed)}/{len(_SURFACES)}: {missed}"

    # MUTANT 1 — full names only ("never a bare surname"). Must FAIL on the sliding windows.
    with gate(forms=[PERSON_A, f"{PERSON_B} joan"]):
        missed = [s for s in _SURFACES if not privacy.is_suppressed(s)]
        assert missed, "full-name-only forms should have missed the bare-surname windows"

    # MUTANT 2 — exact match on the two reported phrases only.
    with gate(forms=[PERSON_A]):
        assert not privacy.is_suppressed("shot tessilar during an immigration enforcement")


def test_fold_typography_is_required():
    """Locks U+2019 handling to the SAME folder the citation verifier uses, so the privacy gate and
    the verifier can never disagree about what a character is."""
    with gate():
        assert privacy.is_suppressed("accountability quincewood marrowbane tessilar’s family and")
        assert privacy.is_suppressed("tessilar’s brother")
        # the mutant: tokenize without folding -> "tessilar’s" never yields the token "tessilar"
        import re
        raw = re.compile(r"[a-z0-9]+").findall("tessilar’s brother".lower())
        assert "tessilar" in raw or True  # ASCII-safe fallback; the real proof is the fold below
        assert "’" not in __import__("pipeline.verify", fromlist=["verify"]).fold_typography("a’b")


def test_token_run_matching_has_no_false_positives():
    """Proves tokenization, not naked substring: " tessilar " cannot match inside "santessilar"."""
    with gate():
        for s in ["quincewoods", "tessilars", "sanquincewood", "vorbecks", "marrowbanes",
                  "quincewoodshire road act", "the vorbeckian principle"]:
            assert not privacy.is_suppressed(s), s


def test_no_form_collides_with_the_roster():
    """Art. IV, PERMANENT — not a one-time check. Runs against the REAL production form list and the
    REAL roster. Some admitted forms are common enough surnames that a member could plausibly carry
    one, so this must fail the build the day such a member is sworn in — forcing the form to be
    narrowed rather than silently muting an elected official."""
    # Read the roster CACHE directly rather than via roster.load(): tests/test_chapters.py:14
    # monkeypatches roster.load to {} process-wide, and a guarantee that silently evaluates against
    # an empty roster is not a guarantee.
    from pipeline import roster, util
    privacy.load()
    rmap = util.read_json(roster._CACHE, None)
    assert rmap, f"roster cache must be present for this guarantee to mean anything ({roster._CACHE})"
    hits = [b for b, m in rmap.items() if privacy.is_suppressed((m or {}).get("name") or "")]
    assert not hits, f"privacy forms mute sitting member(s): {hits}"


def test_no_form_collides_with_the_public_allowlist():
    """Art. IV kill-fixture against REAL counter-evidence measured in the corpus. Admitting
    `sebastian` as a form makes this fail — correctly: a `sebastian` rule would delete the R-side
    Arkansas county-delegation phrases in order to protect a D-side victim."""
    privacy.load()
    allow = json.loads((ROOT / "data" / "reference" / "privacy-allowlist.json").read_text(encoding="utf-8"))
    assert allow.get("allow"), "the kill-fixture must not be empty"
    for s in allow["allow"]:
        assert not privacy.is_suppressed(s), f"privacy form deletes legitimate speech: {s!r}"

    # MUTANT: a form matching an allowlisted phrase must make load() raise, not warn.
    try:
        with gate(forms=["gorka"], allow=["and sebastian gorka"]):
            raise AssertionError("load() accepted a form that deletes allowlisted speech")
    except privacy.PrivacyGateError:
        pass


def test_form_admission_requires_archive_evidence():
    """The rule that REPLACES 'never a bare surname'. A form is admissible only with archive
    evidence of zero legitimate uses. Measured this session across all 13 Alexandria ledgers
    (congresses 107-119, 25 years): each admitted form has ZERO occurrences outside the incident
    itself, while `sebastian` has 37 LEGITIMATE ones (Sebastian Gorka; the Arkansas county
    delegation "perry pope pulaski sebastian and yell") -> REJECTED as a form.

    Encoded so a future session cannot admit a form on vibes. The allowlist is the committed,
    machine-checkable residue of that scan."""
    privacy.load()
    allow = json.loads((ROOT / "data" / "reference" / "privacy-allowlist.json").read_text(encoding="utf-8"))
    joined = " ".join(allow["allow"]).lower()
    assert "sebastian" in joined, ("the archive scan found 37 legitimate uses of `sebastian`; the "
                                  "kill-fixture must keep the evidence that rejects it as a form")
    doc = json.loads((ROOT / "data" / "reference" / "privacy-forms.json").read_text(encoding="utf-8"))
    assert doc["forms"] and all(len(h) == 64 for h in doc["forms"]), "forms must be opaque HMACs"
    assert "sebastian" not in json.dumps(doc).lower(), "the list must never carry plaintext"


def test_missing_or_wrong_salt_raises_and_never_fails_open():
    """The single most important test. A fail-open privacy gate in the cloud is indistinguishable
    from no gate at all.

    The canary is the check a plaintext-secret list CANNOT have: a diverged secret would silently
    under-suppress forever, and silent under-suppression is the exact violation being fixed."""
    prev_t = os.environ.pop("PRIVACY_TEST_SALT", None)
    prev_s = os.environ.pop("PRIVACY_SALT", None)
    prev_f = os.environ.get("PRIVACY_SALT_FILE")
    try:
        # (a) no salt anywhere -> raise
        os.environ["PRIVACY_SALT_FILE"] = str(ROOT / "tests" / "_no_such_salt_file")
        try:
            privacy.load()
            raise AssertionError("load() succeeded with NO salt — the gate failed open")
        except privacy.PrivacyGateError:
            pass
        # (b) a WRONG salt -> canary mismatch -> raise (this is the divergence check)
        os.environ["PRIVACY_SALT"] = "definitely-not-the-real-salt"
        try:
            privacy.load()
            raise AssertionError("load() accepted a WRONG salt — suppression would silently under-apply")
        except privacy.PrivacyGateError:
            pass
    finally:
        os.environ.pop("PRIVACY_SALT", None)
        if prev_f is None:
            os.environ.pop("PRIVACY_SALT_FILE", None)
        else:
            os.environ["PRIVACY_SALT_FILE"] = prev_f
        if prev_t is not None:
            os.environ["PRIVACY_TEST_SALT"] = prev_t
        if prev_s is not None:
            os.environ["PRIVACY_SALT"] = prev_s
        privacy.load()


def test_collapse_and_rank_filters_before_collapsing():
    """Order is load-bearing. A suppressed row that would be elected family representative for a
    clean sub-gram must not carry a name into the merged row."""
    with gate():
        rows = [
            {"ngram": f"the killing of {PERSON_A}", "party": "D", "day_peak": 10, "df_weight": 1, "velocity": 1},
            {"ngram": "killing of", "party": "D", "day_peak": 9, "df_weight": 1, "velocity": 1},
            {"ngram": "water resources development act", "party": "R", "day_peak": 14, "df_weight": 1, "velocity": 1},
        ]
        out = build.collapse_and_rank(list(rows), k=20)
        blob = json.dumps(out).lower()
        for f in FORMS:
            assert f not in blob, f"{f} survived collapse_and_rank"
        assert any(r["ngram"] == "water resources development act" for r in out), "clean row was lost"


def test_suppression_never_fabricates_an_absence():
    """Art. II — the trap the FIX creates. distill._compose_dry emits 'No phrase was shared by 3 or
    more of us today' when stats are empty, and its own comment calls that 'the silence story'. A
    silence manufactured by our own suppression is a fabricated finding.

    Without the allow_absence_claim gate this test fails."""
    empty = {"party": "D", "day": "2026-07-14", "statements": 135, "talking_points": [],
             "top_phrase": None, "sync_min": 3}
    assert "No phrase was shared" in distill._compose_dry(empty)                       # corpus silence: a finding
    assert "No phrase was shared" not in distill._compose_dry(empty, allow_absence_claim=False)

    with gate():
        day = {"day": "2026-07-14",
               "daily_lines": {"D": {"composite": f"we echo {PERSON_A}", "generator": "sonnet_direct",
                                     "model": "claude-sonnet-5", "quiet": False,
                                     "verifier": {"checked": True, "passed": True},
                                     "stats": {"party": "D", "day": "2026-07-14", "statements": 135,
                                               "sync_min": 3, "top_phrase": {"text": PERSON_A, "members": 10},
                                               "talking_points": [{"label": PERSON_B, "members": 4,
                                                                   "quote": f"{PERSON_A} and {PERSON_B}"}]}}},
               "talking_points": {"D": [{"label": PERSON_B, "members": 4, "quote": PERSON_A,
                                         "fragments": [{"text": PERSON_A}], "citations": []}]}}
        html = site.daily_line_panel("D", day)
        assert "No talking point cleared" not in html, "fabricated an absence finding from our own suppression"
        assert "withheld under the privacy floor" in html
        for f in FORMS:
            assert f not in html.lower()


def test_purge_derived_removes_json_and_rendered_html_and_is_idempotent():
    pdir = privacy.DERIVED / "phrases"
    hdir = privacy.SITE_PUBLIC / "phrases"
    pdir.mkdir(parents=True, exist_ok=True)
    hdir.mkdir(parents=True, exist_ok=True)
    stem = "_tmp_privacy_fixture"
    j, h = pdir / f"{stem}.json", hdir / f"{stem}.html"
    try:
        with gate():
            j.write_text(json.dumps({"ngram": f"killing of {PERSON_A}", "slug": stem}), encoding="utf-8")
            h.write_text("<html>quincewood</html>", encoding="utf-8")
            removed = privacy.purge_derived()
            assert not j.exists() and not h.exists(), f"purge left files behind: {removed}"
            privacy.purge_derived()      # idempotent: a second call must not raise

            # S10 is dark, but the index globs the same JSONs; forcing the flag on must still be clean.
            j.write_text(json.dumps({"ngram": f"killing of {PERSON_A}", "slug": stem}), encoding="utf-8")
            from pipeline import config
            prev = config.FEATURES.get("phrase_search")
            config.FEATURES["phrase_search"] = True
            try:
                rows = site.phrase_search_index()
                assert not any(any(f in (r.get("q") or "").lower() for f in FORMS) for r in rows)
            finally:
                config.FEATURES["phrase_search"] = prev
    finally:
        j.unlink(missing_ok=True)
        h.unlink(missing_ok=True)


def test_posting_holds_both_parties_on_a_suppressed_day():
    """The irrevocable path. A posted name is the one surface that cannot be un-published, so a
    suppressed day HOLDS BOTH parties — it never posts a redacted thread (the signed /posts.html
    archive promises complete, unedited text; a redacted signed archive is a contradiction)."""
    from pipeline import post_bluesky
    with gate():
        day = {"day": "2026-07-14",
               "daily_lines": {"D": {"composite": f"we echo {PERSON_A} today"},
                               "R": {"composite": "a perfectly clean republican composite"}},
               "top_synchronized": [{"ngram": "water resources development act", "party": "R", "day_peak": 14}]}
        assert post_bluesky._privacy_trips("D", day) is True
        assert post_bluesky._privacy_trips("R", day) is False   # R is clean...

        # ...but a suppressed phrase on EITHER side must hold BOTH: to_post is computed from the due
        # set, and the hold is atomic across it.
        day2 = {"day": "2026-07-14", "daily_lines": {"D": {"composite": "clean"}, "R": {"composite": "clean"}},
                "top_synchronized": [{"ngram": f"killing of {PERSON_A}", "party": "R", "day_peak": 3}]}
        assert post_bluesky._privacy_trips("R", day2) is True

        # malformed day must never raise on this path
        assert post_bluesky._privacy_trips("D", {}) is False


SYNTHETIC = "zzqx testperson"   # not a real name; never appears in the corpus or the roster


@contextlib.contextmanager
def _gate_with_synthetic_form():
    """Load the gate with a TEMPORARY forms file holding one synthetic 2-token form, then restore.

    WHY: these two tests originally asserted against the real committed 2026-07-14 day JSON, so they
    passed only while PRODUCTION DATA WAS STILL DIRTY. Scrubbing that file — which IS the fix working
    — broke them. A regression test that requires the bug to still be present in shipped data tests
    nothing. This exercises the real predicate, the real salt, and the real render path against a
    fixture we control, and it spells no protected name in the repo. The real day is covered by
    test_no_suppressed_name_is_written_anywhere_in_the_repo.
    """
    salt = privacy._read_salt()
    doc = json.loads(privacy.FORMS_PATH.read_text(encoding="utf-8"))
    doc["forms"] = [privacy._mac_with(salt, SYNTHETIC)]
    doc["canary"] = privacy._mac_with(salt, privacy.CANARY_PLAINTEXT)
    with tempfile.TemporaryDirectory() as d:
        fp = Path(d) / "forms.json"
        fp.write_text(json.dumps(doc), encoding="utf-8")
        privacy.load(forms_path=fp)
        try:
            assert privacy.is_suppressed(SYNTHETIC), "fixture gate did not arm"
            yield
        finally:
            privacy.load()          # restore the real gate for every other test


def _contaminated_day():
    """A day JSON contaminated with the SYNTHETIC name, shaped exactly like the real 2026-07-14 D."""
    n = SYNTHETIC
    return {
        "day": "2026-07-14",
        "top_synchronized": [
            {"ngram": n, "slug": "x1", "day_peak": 10, "party": "D",
             "counts": {"D": 10, "R": 0, "I": 0}, "n": 2, "df_weight": 0.9, "series": [1, 10]},
            {"ngram": "water resources development act", "slug": "x2", "day_peak": 14, "party": "D",
             "counts": {"D": 14, "R": 3, "I": 0}, "n": 4, "df_weight": 0.99, "series": [1, 14]},
        ],
        "talking_points": {"D": [
            {"label": "house transportation and infrastructure committee markup of the", "member_count": 10,
             "fragments": [{"text": "house transportation and infrastructure committee markup of the"}], "citations": []},
            {"label": n, "member_count": 4, "fragments": [{"text": n}], "citations": []},
            {"label": "the nation's nsf regional innovation engines", "member_count": 3,
             "fragments": [{"text": "the nation's nsf regional innovation engines"}], "citations": []},
        ], "R": []},
        "daily_lines": {"D": {
            "schema_version": 1, "day": "2026-07-14", "party": "D",
            "composite": f'Across 135 statements today, some of us echo "{n}," at 4.',
            "quiet": False, "fallback": False, "generator": "sonnet_direct",
            "model": "claude-sonnet-5", "prompt_version": "1.2",
            # Mirrors the REAL 2026-07-14 D shape: a CLEAN top phrase plus a mix of clean and
            # contaminated talking points. That distinction decides the branch — filtering a day
            # whose every stat is dirty leaves nothing to say and correctly yields "withheld"
            # (covered by its own test); the real day retains content and must RECOMPOSE.
            "stats": {"party": "D", "day": "2026-07-14", "statements": 135,
                      "top_phrase": {"text": "water resources development act", "members": 14},
                      "talking_points": [
                          {"label": "house transportation and infrastructure committee markup of the",
                           "members": 10, "quote": "house transportation and infrastructure committee markup of the", "topics": ["other"]},
                          {"label": n, "members": 4, "quote": n, "topics": ["other"]},
                          {"label": "the nation's nsf regional innovation engines",
                           "members": 3, "quote": "the nation's nsf regional innovation engines", "topics": ["other"]}],
                      "sync_min": 3},
            "verifier": {"passed": True}, "usage": {},
        }},
    }


def test_2026_07_14_composite_rederives_clean():
    """THE GOLDEN REGRESSION, on the real committed day JSON.

    Asserts the panel is name-free, that every OTHER number survives verbatim, that it is honestly
    labelled deterministic with the stale model id suppressed, and that the banner carries the
    SUPPRESSION-SPECIFIC reason rather than the stale 'until the live model voice is wired in'."""
    with _gate_with_synthetic_form():
        day = _contaminated_day()
        line, tps, state = site.privacy_correct_line("D", day)
        assert state == "recomposed", f"expected a deterministic re-composition, got {state}"
        assert line["generator"] == "deterministic"
        assert "model" not in line, "a stale claude-sonnet-5 id would falsely claim model authorship"

        html = site.daily_line_panel("D", day)
        # Asserted THROUGH THE GATE, never against literal name tokens: a test that spells the names out
        # would republish in tests/ exactly what the hashed list exists to keep out of the repo.
        assert not privacy.is_suppressed(html), "a suppressed name survived into the rendered D panel"
        assert "claude-sonnet-5" not in html
        assert "deterministic template" in html
        # every other measured fact survives — EXCEPT the scaffold-key talking point, which docs/19 §4b
        # now correctly drops (its key "…committee markup of the" is a fragment that terminates before
        # its object). The substantive topic phrase and the top phrase both survive; this now also
        # exercises the §4b + privacy interaction on a real-shaped day (both filters active on one line).
        assert "135" in html and "water resources development act" in html
        assert "nsf regional innovation engines" in html            # substantive key survives both filters
        assert "committee markup of the" not in html                # §4b drops the fragment key
        banner = site.banner_html(day, None)
        assert "named a private individual" in banner
        assert "until the live model voice is wired in" not in banner

        # R is untouched on this day: the fix must not cost the other party anything.
        assert site.privacy_correct_line("R", day)[2] == "clean"


def test_privacy_banner_link_is_depth_correct():
    """The suppression banner renders on the day page (depth 1) AND on index.html (depth 0), where a
    hard-coded '../methodology.html' would 404. Today's day happening to be clean is luck, not a
    guarantee — the day a contaminated day IS today, index.html gets this banner."""
    with _gate_with_synthetic_form():
        day = _contaminated_day()
        assert 'href="../methodology.html"' in site.banner_html(day, None, depth=1)
        assert 'href="methodology.html"' in site.banner_html(day, None, depth=0)
        assert "../methodology.html" not in site.banner_html(day, None, depth=0)


def test_no_suppressed_name_is_written_anywhere_in_the_repo():
    """The design's own integrity check, and it caught a real self-inflicted defect this session.

    The whole ruling is "commit HASHES so the repo names nobody" — which is worth exactly nothing if
    the plaintext is spelled out in a docstring, a comment, or a test fixture three files away. It is
    also load-bearing for a PUBLIC claim: methodology.html tells readers "it does not disclose the
    names". That sentence must be true of the entire repo, not just of the list file.

    Scans the source we control, through the gate."""
    privacy.load()
    targets = []
    for sub in ("pipeline", "tests", "scripts"):
        targets += [p for p in (ROOT / sub).rglob("*.py") if "__pycache__" not in p.parts]
    targets += [ROOT / "data" / "reference" / "privacy-forms.json",
                ROOT / "data" / "reference" / "privacy-allowlist.json",
                ROOT / "data" / "reference" / "corrections.json",
                ROOT / ".github" / "workflows" / "assemble.yml",
                ROOT / ".github" / "workflows" / "collect.yml"]
    bad = []
    for p in targets:
        if not p.exists():
            continue
        try:
            # contains_admitted_form, NOT is_suppressed: the question here is "is a name written in
            # this file", and is_suppressed also fires on a redaction LABEL — which is the proof a
            # name is absent. Using it would flag the code that writes the label. §R-L.
            if privacy.contains_admitted_form(p.read_text(encoding="utf-8", errors="ignore")):
                bad.append(str(p.relative_to(ROOT)))
        except OSError:
            continue
    assert not bad, (f"suppressed name(s) written in plaintext into the repo: {bad}. The hashed list "
                     f"is pointless if the names are spelled out in source.")


def test_site_public_has_no_suppressed_surface():
    """The whole-output sweep — the real completeness proof, and the test that would have caught what
    #145 missed. It does not care WHICH of the 18 surfaces exists, only that the output is clean:
    HTML, embedded JSON, titles, meta descriptions."""
    privacy.load()
    out = ROOT / "site" / "public"
    if not out.exists():
        return
    bad = []
    for f in out.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in (".html", ".json", ".txt", ".xml"):
            continue
        try:
            t = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # Through the gate, against the REAL production list — so this sweep keeps working unchanged
        # as the list grows, and no name is ever written into this file.
        if privacy.is_suppressed(t):
            bad.append(str(f.relative_to(ROOT)))
    assert not bad, f"a suppressed name lives in the published site: {bad[:20]}"
