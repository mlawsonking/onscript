"""P2: the clean-statement scan cache, and the invalidation that makes it safe.

The cache serves one bit per statement text, only in the affirmative: "no admitted form occurs
here". A stale affirmative is a published name, so most of this file is about the ways a prior
verdict must STOP being served. The cost side is proven too: a hit has to actually skip the scan,
or the cache is decoration.

No test here names a suppressed form. The gate is loaded against the runtime-built stand-in list
from tests/test_privacy.py, exactly like every other privacy test.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import phrases, privacy, scan_cache  # noqa: E402
from tests.test_privacy import FORMS, PERSON_A, PERSON_B, gate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

CLEAN_TEXT = "workers deserve fair wages and affordable housing in every district this year"
DIRTY_TEXT = f"policy accountability after the killing of {PERSON_A} needs action now"


def _cache_path(root: Path) -> Path:
    return Path(root) / scan_cache.CACHE_BASENAME


def _read_cache(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_a_clean_verdict_is_served_from_the_cache_and_skips_the_scan():
    """The cost claim. A hit must not reach the keyed-hash sweep, or nothing was saved."""
    with tempfile.TemporaryDirectory() as raw, gate():
        path = _cache_path(Path(raw))
        privacy.activate_scan_cache(path=path)
        assert privacy._suppressed_spans(CLEAN_TEXT) == []
        privacy.flush_scan_cache(path=path)
        scan_cache.deactivate()

        # Second run, cold process state, warm cache.
        privacy.activate_scan_cache(path=path)
        assert scan_cache.stats()["loaded"] == 1

        calls = []
        original = privacy._compute_suppressed_spans
        privacy._compute_suppressed_spans = lambda text: (calls.append(text), original(text))[1]
        try:
            assert privacy._suppressed_spans(CLEAN_TEXT) == []
            assert calls == [], "a cache hit still ran the full admitted-form sweep"
            assert scan_cache.stats()["hits"] == 1

            # A text the cache has never seen is scanned in full, every run.
            privacy._suppressed_spans(CLEAN_TEXT + " and one more clause")
            assert len(calls) == 1
            assert scan_cache.stats()["misses"] == 1
        finally:
            privacy._compute_suppressed_spans = original
            scan_cache.deactivate()


def test_a_dirty_statement_is_never_cached_and_is_rescanned_every_run():
    """Only the affirmative is stored. There are no negative entries to go stale."""
    with tempfile.TemporaryDirectory() as raw, gate():
        path = _cache_path(Path(raw))
        privacy.activate_scan_cache(path=path)
        spans = privacy._suppressed_spans(DIRTY_TEXT)
        assert spans, "the fixture must actually contain an admitted form"
        privacy.flush_scan_cache(path=path)
        scan_cache.deactivate()

        doc = _read_cache(path)
        assert doc["clean"] == [], "a statement containing an admitted form must not be recorded"

        privacy.activate_scan_cache(path=path)
        try:
            assert privacy._suppressed_spans(DIRTY_TEXT) == spans
            assert scan_cache.stats()["hits"] == 0
        finally:
            scan_cache.deactivate()


def test_a_newly_admitted_form_voids_every_prior_clean_verdict():
    """The one moment a stale clean answer is wrong about the whole corpus. The text below is
    clean under the base list and contains an admitted form under the widened one."""
    widened_text = f"the committee record notes {PERSON_B} joan and moves on"
    with tempfile.TemporaryDirectory() as raw:
        path = _cache_path(Path(raw))
        with gate(forms=[f for f in FORMS if f != PERSON_B]):
            privacy.activate_scan_cache(path=path)
            assert privacy._suppressed_spans(widened_text) == []
            privacy.flush_scan_cache(path=path)
            scan_cache.deactivate()
            assert len(_read_cache(path)["clean"]) == 1

        with gate(forms=FORMS):        # the same salt, one more admitted form
            status = privacy.activate_scan_cache(path=path)
            try:
                assert "invalidated by forms_fingerprint" in status, status
                assert scan_cache.stats()["loaded"] == 0
                assert privacy._suppressed_spans(widened_text), (
                    "the widened form list must find what the old cache called clean")
            finally:
                scan_cache.deactivate()


def test_a_salt_generation_change_voids_every_prior_clean_verdict():
    """Verdicts computed under a different salt are not stale-but-close, they are unrelated."""
    with tempfile.TemporaryDirectory() as raw:
        path = _cache_path(Path(raw))
        with gate():
            privacy.activate_scan_cache(path=path)
            assert privacy._suppressed_spans(CLEAN_TEXT) == []
            privacy.flush_scan_cache(path=path)
            scan_cache.deactivate()
            written = _read_cache(path)
            assert len(written["clean"]) == 1

        # Same form plaintexts, different salt: every hash in the file belongs to another gate.
        with gate(forms=FORMS, salt="a-different-test-salt"):
            status = privacy.activate_scan_cache(path=path)
            try:
                assert "invalidated by" in status, status
                assert scan_cache.stats()["loaded"] == 0
                assert privacy.salt_fingerprint() != written["salt_fingerprint"]
            finally:
                scan_cache.deactivate()


def test_an_entity_hierarchy_bump_voids_every_prior_clean_verdict():
    """The entity version is a module constant, so a bump need not reload the gate. The key has to
    notice anyway, or a warm process keeps answering under the version it started with."""
    with tempfile.TemporaryDirectory() as raw, gate():
        path = _cache_path(Path(raw))
        privacy.activate_scan_cache(path=path)
        key_before = privacy.clean_scan_key(CLEAN_TEXT)
        assert privacy._suppressed_spans(CLEAN_TEXT) == []
        privacy.flush_scan_cache(path=path)
        scan_cache.deactivate()

        original = privacy.ENTITY_HIERARCHY_VERSION
        privacy.ENTITY_HIERARCHY_VERSION = original + "-bumped"
        try:
            assert privacy.clean_scan_key(CLEAN_TEXT) != key_before, (
                "the key must commit to the entity-hierarchy version")
            status = privacy.activate_scan_cache(path=path)
            assert "invalidated by entity_hierarchy_version" in status, status
            assert scan_cache.stats()["loaded"] == 0
        finally:
            privacy.ENTITY_HIERARCHY_VERSION = original
            scan_cache.deactivate()


def test_the_cache_holds_no_offsets_no_counts_and_no_negative_entries():
    """R-29.3 is absolute: nothing persisted may let a reader locate a suppressed name. The file
    is a header plus opaque fixed-width keys, and the keys are not computable without the salt."""
    with tempfile.TemporaryDirectory() as raw, gate():
        path = _cache_path(Path(raw))
        privacy.activate_scan_cache(path=path)
        privacy._suppressed_spans(CLEAN_TEXT)
        privacy._suppressed_spans(DIRTY_TEXT)
        privacy.flush_scan_cache(path=path)
        scan_cache.deactivate()

        doc = _read_cache(path)
        assert set(doc) == {"schema_version", "kind", "cache_version", "forms_fingerprint",
                            "salt_fingerprint", "entity_hierarchy_version", "clean"}, sorted(doc)
        assert doc["clean"] == [privacy.clean_scan_key(CLEAN_TEXT)]
        for key in doc["clean"]:
            assert len(key) == scan_cache.KEY_HEX_CHARS
            assert all(c in "0123456789abcdef" for c in key)

        # An unkeyed digest would let anyone with the public mirror test membership. The key must
        # depend on the secret, not just on the text.
        import hashlib
        assert not any(hashlib.sha256(CLEAN_TEXT.encode()).hexdigest().startswith(k)
                       for k in doc["clean"])

        blob = path.read_bytes()
        assert b"start_char" not in blob and b"end_char" not in blob
        for form in FORMS:
            assert form.encode() not in blob


def test_the_cache_cannot_be_turned_on_without_the_gate():
    """A cached run is still a publishing run. The hit path never reaches _scan_window, which is
    where every other caller happens to arm the gate, so a cache that short-circuited before
    establishment would fail OPEN exactly when it is warm (docs/37 rule 4, the S57 shape).

    Run in a subprocess with a scrubbed environment, like tests/test_privacy_lazy_gate.py, so it
    reproduces the salt-less runner rather than poisoning this process's gate."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("PRIVACY_SALT", "PRIVACY_TEST_SALT", "PRIVACY_SALT_FILE")}
    env["PRIVACY_SALT_FILE"] = str(ROOT / "tests" / "_no_such_salt_file.txt")

    # Activation refuses: the header commits to the salt, so it cannot be built without one.
    activate = subprocess.run(
        [sys.executable, "-c",
         "import pipeline.privacy as p\n"
         "try:\n"
         "    p.activate_scan_cache()\n"
         "except p.PrivacyGateError as e:\n"
         "    print('GATE REFUSED'); print(str(e)[:80])\n"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert activate.returncode == 0, activate.stderr[-500:]
    assert "GATE REFUSED" in activate.stdout
    assert "PRIVACY_SALT" in activate.stdout

    # And the adversarial case: the store is handed a header directly and made active anyway. The
    # scan must still refuse rather than serve or record a verdict.
    forced = subprocess.run(
        [sys.executable, "-c",
         "import pipeline.privacy as p, pipeline.scan_cache as sc\n"
         "sc.activate({'schema_version': 1, 'kind': sc.KIND,\n"
         "             'cache_version': sc.CACHE_VERSION, 'forms_fingerprint': 'x',\n"
         "             'salt_fingerprint': 'x', 'entity_hierarchy_version': 'x'})\n"
         "assert sc.active()\n"
         "try:\n"
         "    p._suppressed_spans('any statement text at all')\n"
         "except p.PrivacyGateError as e:\n"
         "    print('GATE REFUSED'); print(str(e)[:80])\n"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert forced.returncode == 0, forced.stderr[-500:]
    assert "TypeError" not in forced.stderr, "the bare-TypeError outage shape must not return"
    assert "GATE REFUSED" in forced.stdout
    assert "PRIVACY_SALT" in forced.stdout


def test_every_failure_mode_resolves_to_rescanning_rather_than_to_clean():
    with tempfile.TemporaryDirectory() as raw, gate():
        root = Path(raw)
        header = privacy.scan_cache_header()

        # absent
        assert "cold" in scan_cache.activate(header, path=root / "absent.json.gz")
        assert scan_cache.stats()["loaded"] == 0

        # not JSON at all
        bad = root / "bad.json"
        bad.write_bytes(b"\x1f\x8b this is not json either")
        assert "unreadable" in scan_cache.activate(header, path=bad)
        assert scan_cache.stats()["loaded"] == 0

        # valid JSON, wrong shape
        wrong = root / "wrong.json"
        wrong.write_text(json.dumps({**header, "clean": "not-a-list"}), encoding="utf-8")
        assert "malformed entry list" in scan_cache.activate(header, path=wrong)

        # valid JSON, not even a mapping
        listy = root / "listy.json"
        listy.write_text(json.dumps(["nope"]), encoding="utf-8")
        assert "malformed" in scan_cache.activate(header, path=listy)

        # valid JSON, truncated key
        short = root / "short.json"
        short.write_text(json.dumps({**header, "clean": ["abc"]}), encoding="utf-8")
        assert "shape check" in scan_cache.activate(header, path=short)
        assert scan_cache.stats()["loaded"] == 0

        # a run with no cache active never serves a verdict
        scan_cache.deactivate()
        assert scan_cache.is_clean(privacy.clean_scan_key(CLEAN_TEXT)) is False
        assert scan_cache.flush(path=root / "unused.json") == "inactive, nothing written"
        assert not (root / "unused.json").exists()


def test_the_cache_carrier_stays_readable_by_the_article_xiii_redaction_gate():
    """THE DEFECT THIS PINS. The first cut wrote the cache gzipped as clean-scan-cache.json.gz.
    pipeline.redact handles gzip on its JSONL path but opens .json as text, so the redaction step
    raised "unparseable JSON, cannot prove it is clean" and failed CLOSED on every collect, before
    the release upload and after the day's work. A carrier the release gate cannot parse is an
    authored outage (docs/37 rule 4), so the shape is pinned here rather than in a comment.

    Compression bought nothing in any case: the file is tarred into a gzipped release asset."""
    from pipeline import redact
    with tempfile.TemporaryDirectory() as raw:
        path = _cache_path(Path(raw))
        with gate():
            privacy.activate_scan_cache(path=path)
            privacy._suppressed_spans(CLEAN_TEXT)
            privacy._suppressed_spans(DIRTY_TEXT)
            privacy.flush_scan_cache(path=path)
            scan_cache.deactivate()
        # Outside gate(): scanned against the PRODUCTION gate, which is what the workflow step runs.
        assert path.is_file()
        assert redact._mode_for(path) == "json", (
            "the redaction gate must recognise the carrier, not skip it as unsupported")
        result = redact.redact_file(path, check=True)
        assert result["count"] == 0, result
        report = redact.redact_tree([path.parent], check=True, verbose=False)
        assert report["occurrences"] == 0, report
        assert report["unsupported"] == [], report
        assert report["scanned"] == 1, report


def test_the_operator_kill_switch_disables_the_cache_without_a_code_change():
    import os
    with tempfile.TemporaryDirectory() as raw, gate():
        path = _cache_path(Path(raw))
        prev = os.environ.get("ONSCRIPT_SCAN_CACHE")
        os.environ["ONSCRIPT_SCAN_CACHE"] = "0"
        try:
            status = privacy.activate_scan_cache(path=path)
            assert "disabled" in status, status
            assert scan_cache.active() is False
            assert privacy._suppressed_spans(CLEAN_TEXT) == []
        finally:
            if prev is None:
                os.environ.pop("ONSCRIPT_SCAN_CACHE", None)
            else:
                os.environ["ONSCRIPT_SCAN_CACHE"] = prev
            scan_cache.deactivate()


def test_the_cache_is_verdict_preserving_over_a_fixture_corpus():
    """Cache-on and cache-off must produce identical n-gram sets, statement for statement, for
    clean and contaminated text alike."""
    corpus = [
        CLEAN_TEXT,
        DIRTY_TEXT,
        f"transparency and accountability {PERSON_A} family and community",
        "the committee advanced a bipartisan infrastructure package this morning",
        f"shot {PERSON_B} during an immigration enforcement operation downtown",
        "Cedar Vale families deserve safe housing and reliable public transit",
    ]
    with tempfile.TemporaryDirectory() as raw, gate():
        path = _cache_path(Path(raw))
        scan_cache.deactivate()
        cold = [phrases._doc_ngrams(text, None, {}) for text in corpus]

        privacy.activate_scan_cache(path=path)
        first = [phrases._doc_ngrams(text, None, {}) for text in corpus]
        privacy.flush_scan_cache(path=path)
        scan_cache.deactivate()

        privacy.activate_scan_cache(path=path)
        try:
            assert scan_cache.stats()["loaded"] > 0, "the second pass must find a warm cache"
            warm = [phrases._doc_ngrams(text, None, {}) for text in corpus]
            assert scan_cache.stats()["hits"] > 0, "the warm pass served no cached verdict"
        finally:
            scan_cache.deactivate()

        assert cold == first == warm
