"""E1: the eleven S1 re-validations migrated to the R-S50.1 ISOLATED three-lane substrate.

These lock the FROZEN registration (data/reference/search/e1-isolated-registration.json) and the
additive lane maps that let scripts/search/revalidate_s1_isolated.py read the isolated source lanes
(legacy/scraper/page_html) instead of the Session-19 instrument-folded pair (propublica/scraped).

Every test is synthetic or pure: no per-lane shard on X: is read, so the suite stays CI-safe. The
substrate-identity facts (legacy shards == propublica shards; scraper + page_html == scraped) are
verified live in the measurement run and recorded there (Art. XVI), not asserted against X: here.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "search"))

from pipeline import alexandria as A  # noqa: E402
from pipeline import fetch  # noqa: E402
from pipeline.search import harness as H  # noqa: E402
from pipeline.search import provenance as P  # noqa: E402
from pipeline.search import wave_s1 as S1  # noqa: E402
import revalidate_s1_shards as R  # noqa: E402

ISOLATED = ("legacy", "scraper", "page_html")
ELEVEN = ("S1.1", "S1.3", "S1.1'", "S1.3'", "S1.2", "S1.5", "S1.6", "S1.7", "S1.8", "S1.11", "S1.4")
REG = json.loads((Path(__file__).resolve().parent.parent / "data" / "reference" / "search"
                  / "e1-isolated-registration.json").read_text(encoding="utf-8"))


# --- the frozen lane maps ------------------------------------------------------------------------
def test_isolated_lanes_are_the_alexandria_source_lanes():
    """The three isolated lanes E1 runs are exactly alexandria.SOURCE_LANES (R-S50.1 primary)."""
    assert A.SOURCE_LANES == ISOLATED
    assert set(ISOLATED).issubset(set(A.ALL_LANES))


def test_wave_s1_maps_carry_every_isolated_lane():
    for lane in ISOLATED:
        assert lane in S1.LANE_YEAR_HALVES, f"{lane} missing from LANE_YEAR_HALVES"
        assert lane in S1.LANE_CONGRESS_HALVES, f"{lane} missing from LANE_CONGRESS_HALVES"
        assert lane in S1.LANE_CONGRESSES, f"{lane} missing from LANE_CONGRESSES"
        # the driver resolves halves through these accessors
        assert S1.year_halves_for(lane) == S1.LANE_YEAR_HALVES[lane]
        assert S1.congress_halves_for(lane) == S1.LANE_CONGRESS_HALVES[lane]


def test_legacy_equals_propublica_and_scraper_equals_scraped_halves():
    """The isolated lanes inherit the halves of the folded lane they refine, so an isolated verdict
    is directly comparable to its Session-19 folded verdict."""
    assert S1.LANE_YEAR_HALVES["legacy"] == S1.LANE_YEAR_HALVES["propublica"]
    assert S1.LANE_CONGRESS_HALVES["legacy"] == S1.LANE_CONGRESS_HALVES["propublica"]
    assert list(S1.LANE_CONGRESSES["legacy"]) == list(S1.LANE_CONGRESSES["propublica"])
    assert S1.LANE_YEAR_HALVES["scraper"] == S1.LANE_YEAR_HALVES["scraped"]
    assert S1.LANE_CONGRESS_HALVES["scraper"] == S1.LANE_CONGRESS_HALVES["scraped"]
    assert list(S1.LANE_CONGRESSES["scraper"]) == list(S1.LANE_CONGRESSES["scraped"])


def test_page_html_standalone_window_is_post_seam_only():
    """page_html runs on 117-119 only; its pre-2021 records are the docs/18 §2 supplementary tail,
    never pooled, so they are out of the standalone window."""
    assert list(S1.LANE_CONGRESSES["page_html"]) == [117, 118, 119]
    assert S1.LANE_CONGRESS_HALVES["page_html"] == {"A": {117}, "B": {118, 119}}


def test_lane_cutoff_registered_for_isolated_lanes():
    """s1_3_prime_lifespan's right-censor guard needs the lane edge: legacy ends at the seam,
    scraper/page_html run to the corpus cutoff."""
    assert R.LANE_CUTOFF["legacy"] == "2021-01-03" == R.LANE_CUTOFF["propublica"]
    assert R.LANE_CUTOFF["scraper"] == "2026-07-09"
    assert R.LANE_CUTOFF["page_html"] == "2026-07-09"


# --- the pre-2013 guard still fires for the isolated lanes ---------------------------------------
def test_shard_path_resolves_for_isolated_lanes_and_guards_pre_2013():
    for lane in ISOLATED:
        assert A.lane_shard_path("ledger", 117, lane) == A.LANES_DIR / f"ledger-117.{lane}.json"
        for combined_only in (110, 112):
            try:
                A.lane_shard_path("ledger", combined_only, lane)
                raise AssertionError(f"expected LaneIsolationError for {lane} congress {combined_only}")
            except P.LaneIsolationError:
                pass


# --- the isolation partition E1 depends on (synthetic mirror, no X:) -----------------------------
def _row(date, ds, party="D", bio="A000001"):
    scraper = None if ds == "legacy" else "office"
    return {"date": date, "date_source": ds, "domain": "x.house.gov",
            "scraper": scraper, "source": None,
            "member": {"bioguide_id": bio, "name": "X", "party": party, "state": "CA", "chamber": "house"},
            "text": "word " * 30, "title": "t", "url": "u"}


def _with_mirror(rows, fn):
    tmp = Path(__file__).resolve().parent / "_tmp_isolated"
    tmp.mkdir(parents=True, exist_ok=True)
    with open(tmp / "2022-03.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    old = fetch.MIRROR
    fetch.MIRROR = tmp
    try:
        return fn()
    finally:
        fetch.MIRROR = old
        for p in tmp.glob("*.jsonl"):
            p.unlink()
        tmp.rmdir()


def test_scraper_excludes_page_html_and_scraped_folds_it():
    """scraper + page_html partitions scraped: the isolated scraper lane never sees a page_html
    record, and the folded scraped lane sees both. This is the record-level fact E1 measures the
    consequences of."""
    rows = [_row("2022-03-01", "scraper"), _row("2022-03-02", "scraper"),
            _row("2022-03-03", "page_html"), _row("2022-03-04", "legacy")]
    scraper = _with_mirror(rows, lambda: list(H.iter_statements(lane="scraper")))
    page_html = _with_mirror(rows, lambda: list(H.iter_statements(lane="page_html")))
    scraped = _with_mirror(rows, lambda: list(H.iter_statements(lane="scraped")))
    assert {r["date_source"] for r in scraper} == {"scraper"}
    assert {r["date_source"] for r in page_html} == {"page_html"}
    assert {r["date_source"] for r in scraped} == {"scraper", "page_html"}
    # partition: scraper + page_html == scraped, exactly (the fold is their union)
    assert len(scraper) + len(page_html) == len(scraped)


# --- the frozen registration is complete ---------------------------------------------------------
def test_registration_freezes_every_hypothesis_for_every_lane():
    pv = REG["predicted_verdicts"]
    for lane in ISOLATED:
        assert lane in pv, f"{lane} missing predicted verdicts"
        assert set(pv[lane]) == set(ELEVEN), f"{lane} predictions do not cover the eleven"
    base = REG["folded_baseline_session19"]
    for lane in ("propublica", "scraped"):
        assert set(base[lane]) == set(ELEVEN)
    # legacy prediction must equal the propublica baseline (identity by construction)
    assert pv["legacy"] == base["propublica"]
    # page_html standalone predicted UNDERPOWERED across the board (empty member index)
    assert set(pv["page_html"].values()) == {"UNDERPOWERED"}


def test_registration_halves_match_the_wave_s1_maps():
    """The frozen registration and the code cannot drift: the halves in the registration are the
    halves the driver will actually use."""
    hw = REG["halves_and_window"]
    for lane in ISOLATED:
        assert list(S1.LANE_CONGRESSES[lane]) == hw[lane]["congresses"]
        assert S1.LANE_CONGRESS_HALVES[lane] == {k: set(v) for k, v in hw[lane]["congress_halves"].items()}
        assert R.LANE_CUTOFF[lane] == hw[lane]["cutoff"]
