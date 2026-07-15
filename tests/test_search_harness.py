"""Kill-fixtures for the Search streaming ledger reader (docs/12 §S0.2). The reader must reconstruct a
big `{ngram: entry}` object identically to json.load, even with a TINY chunk size that splits tokens —
including braces/quotes inside string values — across buffer refills."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.search import harness as H  # noqa: E402


def _roundtrip(obj, chunk):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(obj, f)
        path = f.name
    got = dict(H.iter_ledger_entries(path, chunk_size=chunk))
    Path(path).unlink()
    return got


def test_streaming_reader_matches_json_load_across_boundaries():
    """The adversarial content: braces, colons, commas, escaped quotes, and unicode INSIDE string
    values (which a naive brace-counter would miscount), plus nested objects/arrays."""
    obj = {
        "interface{}": {"ngram": "interface{}", "n": 2, "note": 'a }{: , "quote" inside',
                        "daily": {"2013-01-03": {"D": 1, "members_D": ["A001"]}}},
        "born in the united states": {"first_seen": {"date": "2013-06-30", "tie": []},
                                      "daily": {"2013-06-30": {"D": 36, "members_D": ["B", "C"]},
                                                "2013-07-01": {"R": 5}}},
        "café — señor {x}": {"n": 1, "daily": {"2014-02-02": {"R": 3}}, "unicode": "naïve ✓ 中文"},
        "escaped \\\" quote": {"daily": {}, "v": "back\\slash and \"q\""},
    }
    ref = json.loads(json.dumps(obj))
    for chunk in (7, 1, 64, 5_000_000):        # tiny chunks force mid-token refills; big = one read
        got = _roundtrip(obj, chunk)
        assert got == ref, f"mismatch at chunk={chunk}"


def test_streaming_reader_handles_empty_and_single():
    assert _roundtrip({}, 4) == {}
    assert _roundtrip({"solo": {"peak": 1}}, 3) == {"solo": {"peak": 1}}


def test_phrase_summary_computes_peak_and_span():
    entry = {"first_seen": {"date": "2013-06-01"},
             "daily": {"2013-06-01": {"D": 2, "members_D": ["a", "b"]},
                       "2013-06-30": {"D": 36, "members_D": ["x"]},          # peak here
                       "2013-07-15": {"R": 5}}}
    s = H.phrase_summary("born in the united states", entry)
    assert s["peak"] == 36 and s["peak_day"] == "2013-06-30" and s["peak_party"] == "D"
    assert s["first_date"] == "2013-06-01" and s["last_date"] == "2013-07-15" and s["n_days"] == 3
    assert H.phrase_summary("empty", {"daily": {}}) is None
