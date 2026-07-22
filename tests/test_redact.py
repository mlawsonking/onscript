"""R-L — redacted-view release assets (pipeline/redact.py + privacy.redact).

NO TEST FILE IN THIS REPO MAY COMMIT A SUPPRESSED NAME. Like tests/test_privacy.py, everything here
runs against the test-salt gate with fruit for names.
"""
from __future__ import annotations

import gzip
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import privacy, redact  # noqa: E402
from tests.test_privacy import FORMS, PERSON_A, gate  # noqa: E402


# --- the core primitive -------------------------------------------------------------------------
def test_redact_replaces_the_span_and_leaves_everything_else_byte_identical():
    with gate(forms=["quincewood marrowbane"]):
        src = "the killing of quincewood marrowbane in a statement"
        out, n = privacy.redact(src)
        assert n == 1
        assert "quincewood" not in out and "marrowbane" not in out
        assert out.startswith("the killing of ") and out.endswith(" in a statement")
        assert privacy.is_suppressed(src) and not privacy._suppressed_spans(out)


def test_a_clean_string_is_returned_unchanged_and_untouched():
    """The archive's own bytes survive: an uncontaminated record is never re-serialized."""
    with gate():
        src = "border security and the appropriations process"
        out, n = privacy.redact(src)
        assert n == 0 and out is src


def test_redaction_is_idempotent():
    with gate(forms=["quincewood marrowbane"]):
        once, n1 = privacy.redact("the killing of quincewood marrowbane")
        twice, n2 = privacy.redact(once)
        assert n1 == 1 and n2 == 0 and twice == once


def test_a_redaction_label_is_itself_suppressed():
    """The invariant that keeps R-L a release-asset change and nothing else: every display path
    already routes through is_suppressed(), so a labeled row is dropped exactly as the name was."""
    with gate():
        labeled, _ = privacy.redact("the killing of quincewood marrowbane")
        assert privacy.is_suppressed(labeled)
        assert privacy.is_suppressed("<private-individual-A>")          # the history-rewrite label
        assert not privacy.is_suppressed("border security appropriations")


def test_a_labeled_row_is_dropped_by_the_REAL_display_filter():
    """The whole reason R-L is a release-asset change and nothing else. Redaction flows back into
    the cloud's state, so labeled n-grams reach the render — and must be filtered exactly as the
    named ones were. This walks the actual filter the site calls, not the predicate underneath it."""
    with gate(forms=["quincewood marrowbane"]):
        labeled, n = privacy.redact("the killing of quincewood marrowbane")
        assert n == 1
        rows = [{"ngram": "border security now", "day_peak": 9}, {"ngram": labeled, "day_peak": 5}]
        kept, dropped = privacy.filter_rows(rows)
        assert dropped == 1 and [r["ngram"] for r in kept] == ["border security now"]


def test_distinct_forms_get_distinct_labels_so_json_keys_cannot_collapse():
    with gate():
        a, _ = privacy.redact("the killing of quincewood")
        b, _ = privacy.redact("the killing of vorbeck")
        assert a != b


def test_the_possessive_folds_and_the_span_cut_survives_a_length_changing_fold():
    """U+2019 folds to an ASCII apostrophe and U+2026 folds to THREE characters, so folded offsets
    are not original offsets. 4 of the 16 real contaminated n-grams carry the possessive."""
    with gate(forms=["quincewood s"]):                     # the possessive folds to two tokens
        src = "accountability quincewood’s family"
        out, n = privacy.redact(src)
        assert n == 1 and "quincewood" not in out
        assert out.startswith("accountability ") and out.endswith(" family")

    with gate(forms=["quincewood marrowbane"]):
        src2 = "we mourn… quincewood marrowbane spoke"     # ellipsis (1 char -> 3) BEFORE the name
        out2, n2 = privacy.redact(src2)
        assert n2 == 1 and "quincewood" not in out2 and "marrowbane" not in out2
        assert out2.startswith("we mourn… ") and out2.endswith(" spoke")


def test_longest_form_wins_so_a_shorter_tail_does_not_strand_a_token():
    with gate(forms=["quincewood marrowbane", "marrowbane tessilar"]):
        out, n = privacy.redact("quincewood marrowbane tessilar")
        assert n == 1 and "quincewood" not in out
        assert out.endswith(" tessilar")     # leftmost-longest: the first form claims its two tokens


def test_no_memoized_answer_survives_a_gate_reload():
    """A cached 'clean' computed under a different form list is not stale-but-close, it is wrong —
    and a wrong 'clean' here is a published name. Both memos key on the gate generation."""
    phrase = "the killing of quincewood marrowbane"
    with gate(forms=["vorbeck tessilar"]):        # a list that does NOT cover the phrase
        assert privacy.redact(phrase)[1] == 0     # ... so it caches a clean answer for it
    with gate(forms=["quincewood marrowbane"]):   # now it IS covered
        assert privacy.redact(phrase)[1] == 1     # the cached answer must not be reused


def test_the_scan_memo_is_bounded():
    """is_suppressed's memo is unbounded by design (a few hundred display rows a day). Pointing the
    same cache at 300 MB of corpus would grow one entry per distinct window until the runner died."""
    with gate():
        assert privacy._SCAN_MEMO_MAX <= 1_000_000
        privacy._SCAN_MEMO.clear()
        for i in range(2000):
            privacy.redact(f"statement number {i} about appropriations")
        assert len(privacy._SCAN_MEMO) <= privacy._SCAN_MEMO_MAX


# --- object + file walk -------------------------------------------------------------------------
def test_redact_obj_redacts_keys_not_only_values():
    """In ledger.json the n-gram IS the key — a value-only walk leaves the name as its own index."""
    with gate(forms=["quincewood marrowbane"]):
        obj = {"the killing of quincewood marrowbane": {"ngram": "the killing of quincewood marrowbane",
                                                        "n": 5, "members_D": ["A000360"]}}
        out, n = redact.redact_obj(obj)
        assert n == 2
        key = next(iter(out))
        assert "quincewood" not in key and "quincewood" not in json.dumps(out)
        assert out[key]["n"] == 5 and out[key]["members_D"] == ["A000360"]   # payload preserved


def test_clean_containers_are_returned_as_themselves_not_rebuilt():
    """A memory contract, not a style preference: ledger.json parses to ~3.3 GB of objects and all
    but a handful of entries are clean, so rebuilding every dict would hold two full copies at once
    on a 16 GB runner."""
    with gate(forms=["quincewood marrowbane"]):
        clean = {"a": {"b": ["border security", "appropriations"]}}
        out, n = redact.redact_obj(clean)
        assert n == 0 and out is clean and out["a"]["b"] is clean["a"]["b"]

        mixed = {"keep": {"deep": ["appropriations"]},
                 "hit": {"text": "the killing of quincewood marrowbane"}}
        out2, n2 = redact.redact_obj(mixed)
        assert n2 == 1
        assert out2 is not mixed                       # the contaminated branch is rebuilt...
        assert out2["keep"] is mixed["keep"]            # ...and the clean one is shared


def test_a_key_collision_is_a_hard_stop_never_a_silent_merge():
    with gate():
        obj = {"quincewood x": 1, "vorbeck x": 2}
        # Force the collision the per-form label exists to prevent, by making both forms hash-equal.
        real = privacy.label_for
        privacy.label_for = lambda h: "<private-individual-same>"
        try:
            raised = False
            try:
                redact.redact_obj(obj)
            except redact.RedactionError:
                raised = True
            assert raised, "two distinct keys collapsed into one without complaint"
        finally:
            privacy.label_for = real


def _tmpdir():
    return Path(tempfile.mkdtemp(prefix="onscript-redact-"))


def test_jsonl_only_contaminated_records_are_rewritten():
    with gate(forms=["quincewood marrowbane"]):
        d = _tmpdir()
        p = d / "raw.jsonl"
        clean = json.dumps({"member": "A000360", "text": "on appropriations"}, ensure_ascii=False,
                           separators=(",", ":"))
        dirty = json.dumps({"member": "B000575", "text": "the killing of quincewood marrowbane"},
                           ensure_ascii=False, separators=(",", ":"))
        odd = '{"member":"C000880", "text":   "spacing the archive chose"}'   # non-canonical spacing
        p.write_text("\n".join([clean, dirty, odd]) + "\n", encoding="utf-8")

        n = redact.redact_file(p)["count"]
        lines = p.read_text(encoding="utf-8").splitlines()
        assert n == 1
        assert lines[0] == clean            # untouched record keeps its exact bytes
        assert lines[2] == odd              # including bytes we would not have written ourselves
        assert "quincewood" not in lines[1] and json.loads(lines[1])["member"] == "B000575"


def test_a_clean_jsonl_file_is_left_byte_identical():
    with gate():
        d = _tmpdir()
        p = d / "clean.jsonl"
        body = '{"text":"appropriations"}\n{"text":"border security"}\n'
        p.write_text(body, encoding="utf-8")
        before = p.read_bytes()
        assert redact.redact_file(p)["count"] == 0
        assert p.read_bytes() == before


def test_gzipped_jsonl_is_scanned_not_skipped_as_binary():
    """statements.jsonl.gz ships inside state.tar.gz. A scanner that reads files as text sees gzip
    as noise and reports the file clean — a silent miss on ~100 MB of the payload."""
    with gate(forms=["quincewood marrowbane"]):
        d = _tmpdir()
        p = d / "statements.jsonl.gz"
        with gzip.open(p, "wt", encoding="utf-8") as fh:
            fh.write(json.dumps({"text": "the killing of quincewood marrowbane"}) + "\n")
            fh.write(json.dumps({"text": "on appropriations"}) + "\n")
        assert redact.redact_file(p)["count"] == 1
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            body = fh.read()
        assert "quincewood" not in body and "appropriations" in body


def test_json_escaped_unicode_is_caught_because_records_are_parsed_not_grepped():
    """With ensure_ascii=True the possessive is stored as the six characters \\u2019, whose tokens
    are nothing like the value's. Parsing per record is what makes the match possible."""
    with gate():
        d = _tmpdir()
        p = d / "escaped.jsonl"
        p.write_text(json.dumps({"text": "accountability quincewood’s family"},
                                ensure_ascii=True) + "\n", encoding="utf-8")
        assert "\\u2019" in p.read_text(encoding="utf-8")        # the trap is really in the file
        assert redact.redact_file(p)["count"] == 1
        assert "quincewood" not in p.read_text(encoding="utf-8")


def test_whole_document_json_keeps_its_one_line_shape():
    with gate():
        d = _tmpdir()
        p = d / "ledger.json"
        p.write_text(json.dumps({"the killing of quincewood": {"n": 4}}), encoding="utf-8")
        assert redact.redact_file(p)["count"] == 1      # the n-gram KEY, which a value-walk misses
        body = p.read_text(encoding="utf-8")
        assert "\n" not in body.strip() and "quincewood" not in body


def test_check_mode_reports_without_writing():
    with gate(forms=["quincewood marrowbane"]):
        d = _tmpdir()
        p = d / "raw.jsonl"
        p.write_text(json.dumps({"text": "the killing of quincewood marrowbane"}) + "\n",
                     encoding="utf-8")
        before = p.read_bytes()
        rep = redact.redact_tree([d], check=True, verbose=False)
        assert rep["occurrences"] == 1 and p.read_bytes() == before
        assert redact.main([str(d), "--check"]) == 1        # and it is a FAILING exit code
        assert redact.main([str(d)]) == 0                   # ... until it has been redacted
        assert redact.main([str(d), "--check"]) == 0


def test_unsupported_files_are_reported_never_silently_skipped():
    with gate():
        d = _tmpdir()
        (d / "notes.txt").write_text("the killing of quincewood marrowbane", encoding="utf-8")
        rep = redact.redact_tree([d], check=True, verbose=False)
        assert [Path(p).name for p in rep["unsupported"]] == ["notes.txt"]


def test_the_cache_skips_unchanged_files_but_never_survives_a_new_admitted_form():
    """The one moment a stale 'already clean' answer is wrong about the entire corpus is the moment
    a new name is admitted."""
    with gate():
        d = _tmpdir()
        p = d / "a.jsonl"
        p.write_text(json.dumps({"text": "on appropriations"}) + "\n", encoding="utf-8")
        cache = d / redact.CACHE_NAME
        assert redact.redact_tree([d], cache_path=cache, verbose=False)["scanned"] == 1
        assert redact.redact_tree([d], cache_path=cache, verbose=False)["skipped"] == 1
        fp_before = privacy.forms_fingerprint()

    with gate(forms=FORMS + ["appropriations"]):
        assert privacy.forms_fingerprint() != fp_before
        rep = redact.redact_tree([d], cache_path=cache, verbose=False)
        assert rep["skipped"] == 0 and rep["occurrences"] == 1   # rescanned, and it found the new one


def test_a_redaction_that_did_not_take_is_a_hard_stop():
    """Every changed file is re-scanned before the run is allowed to continue. Without it, the whole
    guarantee rests on a return value from the code being checked."""
    with gate(forms=["quincewood marrowbane"]):
        d = _tmpdir()
        (d / "a.jsonl").write_text(json.dumps({"text": "the killing of quincewood marrowbane"}) + "\n",
                                   encoding="utf-8")
        real = privacy.redact
        privacy.redact = lambda s: (s, 1) if isinstance(s, str) and s else real(s)  # claims, does nothing
        try:
            raised = ""
            try:
                redact.redact_tree([d], verbose=False)
            except redact.RedactionError as e:
                raised = str(e)
            assert "survived redaction" in raised
        finally:
            privacy.redact = real


def test_a_partial_scan_does_not_evict_cache_entries_it_did_not_walk():
    """collect scans data/raw, assemble does not, and both share one cache. A plain overwrite would
    drop raw's entries every assemble and make the next collect rescan 300 MB it had cleared."""
    with gate():
        d = _tmpdir()
        (d / "state").mkdir()
        (d / "raw").mkdir()
        (d / "state" / "s.jsonl").write_text('{"text":"appropriations"}\n', encoding="utf-8")
        (d / "raw" / "r.jsonl").write_text('{"text":"border security"}\n', encoding="utf-8")
        cache = d / redact.CACHE_NAME

        both = redact.redact_tree([d / "state", d / "raw"], cache_path=cache, verbose=False)
        assert both["scanned"] == 2
        # assemble-shaped run: state only
        redact.redact_tree([d / "state"], cache_path=cache, verbose=False)
        # collect-shaped run again: raw must still be cached, not rescanned
        again = redact.redact_tree([d / "state", d / "raw"], cache_path=cache, verbose=False)
        assert again["scanned"] == 0 and again["skipped"] == 2


def test_tree_redaction_reaches_a_full_person_name_across_nested_directories():
    with gate():
        d = _tmpdir()
        (d / "state").mkdir()
        (d / "state" / "ledger.json").write_text(
            json.dumps({f"of transparency and accountability {PERSON_A}": {"n": 6}}), encoding="utf-8")
        rep = redact.redact_tree([d], verbose=False)
        assert rep["occurrences"] >= 1
        assert redact.redact_tree([d], check=True, verbose=False)["occurrences"] == 0
