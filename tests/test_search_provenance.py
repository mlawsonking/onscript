"""L1 LANE ISOLATION (docs/12 Law L1) — the guard, and the proof that it fires.

The seam is not a subtle statistical worry. `dwillis/congress-press` is a union of datasets; the
`legacy`/ProPublica lane stops forever on 2021-01-03, and the program's pre-registered halves sit on
that date. So "replicates in both halves" has meant "reproduces on two different instruments".

Every test here is a kill-fixture in the §1.12 sense: it first demonstrates that the PRE-EXISTING
check passes the bad input — that is the whole point, the trend really is rising in both halves —
and only then asserts the lane guard refuses it.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import fetch  # noqa: E402
from pipeline.search import harness as H  # noqa: E402
from pipeline.search import metrics as M  # noqa: E402
from pipeline.search import provenance as P  # noqa: E402


# --- fixtures ------------------------------------------------------------------------------------
def _row(date, ds, party="D", bio="A000001", scraper=None, source=None):
    """A mirror record shaped like the real thing: `legacy` <=> scraper/source both null, exactly."""
    return {"date": date, "date_source": ds, "domain": "x.house.gov",
            "scraper": scraper, "source": source,
            "member": {"bioguide_id": bio, "name": "X", "party": party, "state": "CA", "chamber": "house"},
            "text": "word " * 30, "title": "t", "url": "u"}


def _mirror(tmp: Path, rows):
    tmp.mkdir(parents=True, exist_ok=True)
    with open(tmp / "2020-01.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return tmp


def _with_mirror(rows, fn):
    """Hand-rolled monkeypatch + try/finally restore, per tests/test_killtests.py:25-43."""
    tmp = _mirror(Path(__file__).resolve().parent / "_tmp_provenance", rows)
    old = fetch.MIRROR
    fetch.MIRROR = tmp
    try:
        return fn()
    finally:
        fetch.MIRROR = old
        for p in tmp.glob("*.jsonl"):
            p.unlink()
        tmp.rmdir()


# --- the root fix: the field survives iter_statements ---------------------------------------------
def test_iter_statements_exposes_date_source_and_instrument():
    """THE L1 ROOT. `date_source` was dropped by omission from the `rec` literal (harness.py:422-424),
    destroying the one field that says whether a comparison is valid."""
    rows = [_row("2020-05-01", "legacy"),
            _row("2020-05-02", "scraper", scraper="himes", source="u"),
            _row("2020-05-03", "page_html", scraper="himes", source="u")]
    out = _with_mirror(rows, lambda: list(H.iter_statements()))
    assert len(out) == 3
    assert [r["date_source"] for r in out] == ["legacy", "scraper", "page_html"]
    # the seam-relevant partition: page_html is scraper-COLLECTED, so it is the same instrument
    assert [r["instrument"] for r in out] == ["propublica", "scraped", "scraped"]


def test_iter_statements_lane_filter_isolates_one_lane():
    rows = [_row("2020-05-01", "legacy"),
            _row("2020-05-02", "scraper", scraper="s", source="u"),
            _row("2020-05-03", "page_html", scraper="s", source="u")]
    pro = _with_mirror(rows, lambda: list(H.iter_statements(lane="propublica")))
    scr = _with_mirror(rows, lambda: list(H.iter_statements(lane="scraped")))
    raw = _with_mirror(rows, lambda: list(H.iter_statements(lane="page_html")))
    assert [r["date_source"] for r in pro] == ["legacy"]
    assert [r["date_source"] for r in scr] == ["scraper", "page_html"]   # folded: same instrument
    assert [r["date_source"] for r in raw] == ["page_html"]              # strict 3-way still available


def test_untagged_rows_are_dropped_by_the_date_guard_not_defaulted_into_a_lane():
    """The 19 real untagged records are himes date-parse failures with `date: null`; they are already
    dropped by the len(date)!=10 guard. What must NEVER happen is defaulting them into a lane."""
    rows = [_row(None, None, scraper="himes", source="u"), _row("2020-05-01", "legacy")]
    out = _with_mirror(rows, lambda: list(H.iter_statements()))
    assert [r["date_source"] for r in out] == ["legacy"]


# --- THE KILL TEST: the CONFIRM gate refuses a cross-seam split -----------------------------------
def test_killtest_confirms_in_both_halves_refuses_a_split_across_the_seam():
    """THE KILL TEST. A trend that rises in BOTH halves — the program's strongest evidence — where
    half A is the ProPublica lane and half B is the scraper. The old gate returns True. It must not.

    This is S4.7's mechanism in miniature: the raw cross-seam number said "muted congressional
    response to January 6" (-69.9%, maximally quotable, false); lane-isolated it is +75.5%."""
    rising_a = [(2013, 1.0), (2014, 2.0), (2015, 3.0), (2016, 4.0)]   # legacy era
    rising_b = [(2022, 1.0), (2023, 2.0), (2024, 3.0), (2025, 4.0)]   # scraper era

    # The pre-existing check passes it. That is the point: the trend really does rise in both halves,
    # so split_direction is right and still not enough.
    assert M.split_direction(rising_a) == 1
    assert M.split_direction(rising_b) == 1

    try:
        M.confirms_in_both_halves(rising_a, rising_b, expected_sign=1,
                                  lane_a="propublica", lane_b="scraped")
    except P.LaneIsolationError as e:
        assert "two INSTRUMENTS, not two eras" in str(e)
    else:
        raise AssertionError("certified a finding across the provenance seam — two instruments "
                             "compared as two eras (docs/12 L1)")


def test_killtest_an_undeclared_lane_is_refused_rather_than_defaulted():
    """A default would let an un-migrated call keep sliding through — which is how this travelled for
    34 verdicts. Omitting the lane must fail loudly, not silently pass."""
    a = [(2013, 1.0), (2014, 2.0), (2015, 3.0)]
    b = [(2022, 1.0), (2023, 2.0), (2024, 3.0)]
    try:
        M.confirms_in_both_halves(a, b, expected_sign=1)
    except P.LaneIsolationError as e:
        assert "requires lane_a= and lane_b=" in str(e)
    else:
        raise AssertionError("an undeclared comparison was certified")


def test_the_gate_is_not_a_blanket_refusal_within_one_lane():
    """NO-OP PROOF: isolation must still permit the measurement it is protecting. Same lane, same
    verdict as before the guard existed."""
    a = [(2022, 1.0), (2023, 2.0), (2024, 3.0), (2025, 4.0)]
    b = [(2022, 1.0), (2023, 2.0), (2024, 3.0), (2025, 4.0)]
    flat = [(2022, 2.0), (2023, 2.0), (2024, 2.0), (2025, 2.0)]
    assert M.confirms_in_both_halves(a, b, 1, lane_a="scraped", lane_b="scraped") is True
    assert M.confirms_in_both_halves(a, flat, 1, lane_a="scraped", lane_b="scraped") is False


# --- lane_of / the seam ---------------------------------------------------------------------------
def test_lane_of_raises_on_a_mixed_set_and_returns_the_single_lane_otherwise():
    legacy = [{"date_source": "legacy"}, {"date_source": "legacy"}]
    scraped = [{"date_source": "scraper"}, {"date_source": "page_html"}]
    assert P.lane_of(legacy) == "propublica"
    assert P.lane_of(scraped) == "scraped"          # folded by instrument
    assert P.lane_of([]) is None
    try:
        P.lane_of(legacy + scraped)
    except P.LaneIsolationError as e:
        assert "cross-lane series forbidden" in str(e)
    else:
        raise AssertionError("a cross-lane series was permitted")


def test_lane_of_refuses_an_untagged_row_rather_than_guessing():
    try:
        P.lane_of([{"date_source": "scraper"}, {"no_tag": 1}])
    except P.LaneIsolationError as e:
        assert "untagged row" in str(e)
    else:
        raise AssertionError("an untagged row was silently given a lane")


def test_strict_source_isolation_still_separates_page_html_when_asked():
    scraped = [{"date_source": "scraper"}, {"date_source": "page_html"}]
    assert P.lane_of(scraped, by="instrument") == "scraped"
    try:
        P.lane_of(scraped, by="source")
    except P.LaneIsolationError:
        pass
    else:
        raise AssertionError("by='source' must be the strict 3-way partition")


def test_spans_seam_boundaries_are_exact():
    """SEAM (2021-01-03) is the legacy lane's LAST day, so a window ending on it is all-legacy and
    clean, while one starting on it reaches into scraper-only territory."""
    assert P.spans_seam(["2020-11-04", "2021-02-01"]) is True     # the real s1_10 2020 post-window
    assert P.spans_seam(["2020-01-01", "2020-12-31"]) is False    # legacy only
    assert P.spans_seam(["2021-01-04", "2021-06-01"]) is False    # scraper only
    assert P.spans_seam(["2020-01-01", "2021-01-03"]) is False    # ends ON the seam -> all legacy
    assert P.spans_seam(["2021-01-03", "2021-06-01"]) is True     # starts ON the seam -> crosses
    assert P.spans_seam([]) is False


def test_killtest_the_2020_post_election_window_is_refused():
    """s1_10_bipartisan_season's 2020 post-election window is 2020-11-04..2021-02-01: 60 days
    two-lane, then 29 days scraper-only. Its placebo runs on ODD years only, so the mandatory control
    is structurally blind to the artifact sitting next to it. The window itself must be refused."""
    window = ["2020-11-04", "2020-12-15", "2021-01-02", "2021-02-01"]
    try:
        P.assert_no_seam_span(window, what="2020 post-election 90d window")
    except P.LaneIsolationError as e:
        assert "spans the provenance seam" in str(e)
    else:
        raise AssertionError("a window containing 2021-01-03 was permitted")
    P.assert_no_seam_span(["2022-11-09", "2023-02-06"])   # a post-seam cycle is fine


def test_assert_same_lane_names_the_lane_it_isolated():
    a = [{"date_source": "scraper"}, {"date_source": "page_html"}]
    b = [{"date_source": "scraper"}]
    assert P.assert_same_lane(a, b) == "scraped"
    try:
        P.assert_same_lane([{"date_source": "legacy"}], b)
    except P.LaneIsolationError as e:
        assert "two INSTRUMENTS" in str(e)
    else:
        raise AssertionError("halves from two lanes were accepted")


# --- Wave S2 within-lane loader (docs/17 §4.3) ----------------------------------------------------
def _tf_row(ds, inst, y="2021", p="D", b="A000001", c=117):
    """A text_features row shaped like harness.build_text_features emits post-L1."""
    return {"y": y, "p": p, "b": b, "d": f"{y}-05-01", "c": c, "ds": ds, "inst": inst,
            "nw": 40, "ns": 3, "excl": 0, "semic": 0, "quest": 0, "isg": 0, "wpl": 0,
            "adj": {}, "concern": {}, "apol": 0, "ampeople": 0, "pres": {}, "euph": 0,
            "emoji": 0, "caps": 0}


def _with_text_features(rows, fn):
    from pipeline.search import wave_s2 as S2
    old = H.iter_text_features
    H.iter_text_features = lambda: iter(rows)
    try:
        return fn()
    finally:
        H.iter_text_features = old


def test_s2_load_rows_isolates_by_instrument_and_folds_page_html():
    from pipeline.search import wave_s2 as S2
    rows = [_tf_row("legacy", "propublica", y="2015", c=114),
            _tf_row("scraper", "scraped"),
            _tf_row("page_html", "scraped")]
    pro = _with_text_features(rows, lambda: S2.load_rows("propublica"))
    scr = _with_text_features(rows, lambda: S2.load_rows("scraped"))
    assert [r["ds"] for r in pro] == ["legacy"]
    assert sorted(r["ds"] for r in scr) == ["page_html", "scraper"]   # folded: same instrument
    strict = _with_text_features(rows, lambda: S2.load_rows("scraper", by="source"))
    assert [r["ds"] for r in strict] == ["scraper"]                    # page_html excluded


def test_s2_load_rows_refuses_a_pre_L1_cache():
    """A text_features.jsonl built before L1 has no `inst` field, so every lane filter would silently
    select NOTHING and read as an empty lane. That staleness must fail loudly."""
    from pipeline.search import wave_s2 as S2
    stale = [{"y": "2015", "p": "D", "nw": 40}]   # no ds/inst
    try:
        _with_text_features(stale, lambda: S2.load_rows("propublica"))
    except P.LaneIsolationError as e:
        assert "predates lane isolation" in str(e)
    else:
        raise AssertionError("a pre-L1 lane-blind cache was accepted as an isolated lane")


def test_s2_half_requires_named_halves():
    """`_half` has no default halves — a default is exactly what let the seam-spanning A=2013-2020 /
    B=2021-2026 split travel for 34 verdicts."""
    from pipeline.search import wave_s2 as S2
    h = S2.halves_for("propublica")
    assert S2._half(2015, h) == "A" and S2._half(2019, h) == "B" and S2._half(2022, h) is None
    try:
        S2._half(2015)   # missing halves
    except TypeError:
        pass
    else:
        raise AssertionError("_half accepted no halves — the seam split can travel again")


# --- per-lane alexandria shards (docs/18 §2-§3.4) ------------------------------------------------
def test_lane_shard_path_combined_is_unchanged_and_lane_is_subdirectory():
    """lane=None must return the SAME combined path merge()/the site read (in ALEX/, not lanes/), so
    the combined shards stay byte-untouched; a lane goes to the lanes/ subdirectory that merge()'s
    non-recursive glob never descends into."""
    from pipeline import alexandria as A
    assert A.lane_shard_path("ledger", 117, None) == A.ALEX / "ledger-117.json"
    assert A.lane_shard_path("ledger", 117, "propublica") == A.LANES_DIR / "ledger-117.propublica.json"
    assert A.LANES_DIR.parent == A.ALEX and A.LANES_DIR.name == "lanes"


def test_per_lane_shard_for_a_combined_only_congress_raises():
    """107-112 are combined-only (docs/18 §2): their pre-2013 tails are 99.9% single-party, so a
    per-lane shard there would be a poisoned statistic. The path, the record loader, and the builder
    must all refuse — the guard that stops it being built OR read."""
    from pipeline import alexandria as A
    for n in (107, 110, 112):
        try:
            A.lane_shard_path("ledger", n, "propublica")
        except P.LaneIsolationError:
            pass
        else:
            raise AssertionError(f"per-lane path for combined-only congress {n} was allowed")
        try:
            A.load_congress_records(n, lane="scraped")   # guard fires before any mirror read
        except P.LaneIsolationError:
            pass
        else:
            raise AssertionError(f"per-lane record load for combined-only congress {n} was allowed")


def test_per_lane_shard_unknown_lane_raises():
    from pipeline import alexandria as A
    try:
        A.lane_shard_path("ledger", 117, "bogus")
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown lane was accepted")


# --- R-S50.1: the isolated THREE-valued source-lane substrate (page_html its own lane) ------------
def test_load_congress_records_isolates_page_html_as_its_own_lane():
    """R-S50.1 (binding): the substrate lane domain is THREE-valued and `page_html` is ISOLATED -
    never folded into `scraper` in a primary number. `load_congress_records` must match
    harness.iter_statements: a source lane returns exactly that `date_source`, and the folded
    instrument names survive only as a labelled robustness view. Congress 116 (2019-2020), all three
    lanes co-present (page_html's window opens 2014-12; legacy runs to the 2021-01-03 seam)."""
    from pipeline import alexandria as A
    rows = [_row("2020-01-10", "legacy"),
            _row("2020-01-11", "scraper", scraper="s", source="u"),
            _row("2020-01-12", "page_html", scraper="s", source="u")]

    def ds(lane):
        return sorted(r["date_source"] for r in
                      _with_mirror(rows, lambda: A.load_congress_records(116, lane=lane)))

    assert ds("page_html") == ["page_html"]                  # isolated - its own lane
    assert ds("scraper") == ["scraper"]                      # scraper EXCLUDES page_html (isolated)
    assert ds("legacy") == ["legacy"]
    assert ds("scraped") == ["page_html", "scraper"]         # folded instrument: robustness view only
    assert ds("propublica") == ["legacy"]                    # folded instrument name (== legacy set)
    assert ds(None) == ["legacy", "page_html", "scraper"]    # combined carries every lane


def test_lane_shard_path_accepts_the_isolated_source_lanes():
    """Each of the three primary source lanes gets its own file under lanes/; the combined-only guard
    still fires for a source lane on a pre-2013 congress (107-112 stay combined-only, docs/18 §2)."""
    from pipeline import alexandria as A
    for lane in ("legacy", "scraper", "page_html"):
        assert A.lane_shard_path("ledger", 117, lane) == A.LANES_DIR / f"ledger-117.{lane}.json"
    for combined_only in (107, 110, 112):
        try:
            A.lane_shard_path("ledger", combined_only, "page_html")
        except P.LaneIsolationError:
            pass
        else:
            raise AssertionError(f"a per-lane source shard for combined-only congress {combined_only} was allowed")
        try:
            A.load_congress_records(combined_only, lane="page_html")
        except P.LaneIsolationError:
            pass
        else:
            raise AssertionError(f"a per-lane source load for combined-only congress {combined_only} was allowed")


def test_harness_cache_path_lane_suffixes_before_the_extension():
    assert H.cache_path("phrase_index.jsonl", None) == H.SEARCH_CACHE / "phrase_index.jsonl"
    assert H.cache_path("phrase_index.jsonl", "propublica") == H.SEARCH_CACHE / "phrase_index.propublica.jsonl"
    assert H.cache_path("cross_party_daily.json", "scraped") == H.SEARCH_CACHE / "cross_party_daily.scraped.json"


def test_s2_pre_registered_halves_never_span_the_seam():
    """Every lane's A and B windows must sit entirely on one side of 2021-01-03. The scraped lane's
    DATA starts 2021-01-04 (Jan 1-3 2021 is the excluded propublica stub), so its earliest real day is
    the day after the seam — the isolation is by instrument, and no instrument's data crosses the seam.
    Propublica ends 2020; scraped begins 2021-01-04."""
    from pipeline.search import wave_s2 as S2
    # true data-start per lane (not the nominal Jan-1 of the first half-A year)
    data_start = {"propublica": lambda y: f"{y}-01-01", "scraped": lambda y: ("2021-01-04" if y == 2021 else f"{y}-01-01")}
    for lane, halves in S2.LANE_HALVES.items():
        for h, years in halves.items():
            span = [data_start[lane](min(years)), f"{max(years)}-12-31"]
            P.assert_no_seam_span(span, what=f"{lane} half {h}")   # raises if it spans
        # and the two halves are disjoint and ordered
        assert max(halves["A"]) < min(halves["B"])
