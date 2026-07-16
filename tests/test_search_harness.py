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


def test_bursts_split_on_gaps_and_measure_local_width():
    """Kill-fixture for the S1.1' event detector: bursts are gap-defined, so ignition width is the
    LOCAL rise (days), never the congress- or calendar-spanning artifact that killed S1.1."""
    from pipeline.search import wave_s1 as S1
    # two bursts: a fast one (3-day rise to 20) and, 60 days later, a slow one (12-day rise to 18)
    series = [["2019-03-01", 2], ["2019-03-02", 8], ["2019-03-04", 20],           # burst 1: width 3
              ["2019-05-10", 3], ["2019-05-16", 9], ["2019-05-22", 18]]            # burst 2 (gap>14): width 12
    bursts = S1._bursts(series, gap=14)
    assert len(bursts) == 2
    assert (bursts[0][-1][0].isoformat(), max(c for _, c in bursts[0])) == ("2019-03-04", 20)
    # a synthetic speedup (contiguous bursts narrowing over years) confirms; flat refutes
    from datetime import date as _d, timedelta

    def contiguous_burst(y, w):   # active days every 10d (gap<=14) rising to peak 18 at day w
        s = _d(y, 2, 1)
        days = [[(s + timedelta(days=t)).isoformat(), 5] for t in range(0, w, 10)]
        days.append([(s + timedelta(days=w)).isoformat(), 18])
        return {"series": days}

    rows = []
    for y, w in [(2013, 30), (2015, 25), (2017, 20), (2019, 12), (2021, 10), (2023, 6), (2025, 3)]:
        rows += [contiguous_burst(y, w) for _ in range(10)]   # >=min_cell per year
    res = S1.s1_1_prime_ignition(rows)
    assert res["dir_a"] == -1 and res["dir_b"] == -1 and res["verdict"] == "CONFIRMED"
    assert res["artifact_guard"] is False   # the redefined metric shows NO year-position sawtooth


def test_s1_3_prime_lifespan_detects_shortening_and_drops_censored_bursts():
    """S1.3' burst-duration: a synthetic shortening confirms; and a burst still active near the data
    cutoff is DROPPED (right-censoring guard), never counted as a short life."""
    from datetime import date as _d, timedelta
    from pipeline.search import wave_s1 as S1

    def burst(y, dur):   # a contiguous flare of `dur` days, peak 18
        s = _d(y, 2, 1)
        days = [[(s + timedelta(days=t)).isoformat(), 5] for t in range(0, dur, 10)]
        days.append([(s + timedelta(days=dur)).isoformat(), 18])
        return {"series": days}

    rows = []
    for y, dur in [(2013, 80), (2015, 60), (2017, 40), (2019, 30), (2021, 20), (2023, 12), (2025, 6)]:
        rows += [burst(y, dur) for _ in range(10)]
    res = S1.s1_3_prime_lifespan(rows, cutoff="2027-01-01")   # far cutoff -> nothing censored
    assert res["dir_a"] == -1 and res["dir_b"] == -1 and res["verdict"] == "CONFIRMED"
    # a contiguous burst still running near the cutoff is censored out (would else look artificially short)
    near = {"series": [["2026-06-20", 16], ["2026-06-30", 17], ["2026-07-05", 18]]}   # contiguous, ends 4d pre-cutoff
    r2 = S1.s1_3_prime_lifespan([near] * 20, cutoff="2026-07-09", censor_days=30)
    assert r2["cells"] == {}   # the still-active burst was dropped, not counted as a short life


def test_phrase_summary_computes_peak_and_span():
    entry = {"first_seen": {"date": "2013-06-01"},
             "daily": {"2013-06-01": {"D": 2, "members_D": ["a", "b"]},
                       "2013-06-30": {"D": 36, "members_D": ["x"]},          # peak here
                       "2013-07-15": {"R": 5}}}
    s = H.phrase_summary("born in the united states", entry)
    assert s["peak"] == 36 and s["peak_day"] == "2013-06-30" and s["peak_party"] == "D"
    assert s["first_date"] == "2013-06-01" and s["last_date"] == "2013-07-15" and s["n_days"] == 3
    assert H.phrase_summary("empty", {"daily": {}}) is None
