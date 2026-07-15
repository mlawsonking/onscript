"""Kill-fixtures for The Search metrics library (docs/12 §1.12). Every metric must REFUSE a synthetic
pure-coverage-growth confound before it is trusted on real data. No real data here — pure synthetic."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.search import metrics as M  # noqa: E402


def test_rate_per_1k_is_none_on_empty_denominator_never_zero():
    assert M.rate_per_1k(5, 1000) == 5.0
    assert M.rate_per_1k(3, 0) is None          # an honest gap, never a fabricated 0
    assert M.per_member_rate(10, 0) is None


def test_spearman_direction_and_ties():
    assert abs(M.spearman([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) < 1e-9    # perfect monotone up
    assert abs(M.spearman([1, 2, 3, 4], [4, 3, 2, 1]) + 1.0) < 1e-9    # perfect monotone down
    assert M.spearman([1, 1, 1, 1], [1, 2, 3, 4]) is None       # constant -> undefined, not 0
    assert M.spearman([1, 2], [1, 2]) is None                   # <3 pairs -> None
    r = M.spearman([1, 2, 2, 3], [1, 2, 3, 4])                  # ties handled (avg ranks)
    assert r is not None and 0.9 < r <= 1.0


def test_confirms_in_both_halves_rejects_a_one_half_only_trend():
    """The CONFIRM gate: a trend present only when the halves are pooled must FAIL — that's the
    split-leakage the program forbids."""
    rising_a = [(2013, 1.0), (2014, 2.0), (2015, 3.0), (2016, 4.0)]
    rising_b = [(2021, 1.0), (2022, 2.0), (2023, 3.0), (2024, 4.0)]
    flat_b = [(2021, 2.0), (2022, 2.0), (2023, 2.0), (2024, 2.0)]
    assert M.confirms_in_both_halves(rising_a, rising_b, expected_sign=1) is True
    assert M.confirms_in_both_halves(rising_a, flat_b, expected_sign=1) is False   # half B doesn't hold
    # a trend in the WRONG direction in one half also fails
    falling_b = [(2021, 4.0), (2022, 3.0), (2023, 2.0), (2024, 1.0)]
    assert M.confirms_in_both_halves(rising_a, falling_b, expected_sign=1) is False


def test_median_style_metric_is_coverage_invariant_no_false_trend():
    """KILL-FIXTURE: later years have the SAME true width distribution but MANY more phrases (pure
    coverage growth, no real behavioral change). A median-per-year metric must show NO trend."""
    dist = [1, 1, 3, 3, 3, 5, 7]        # fixed true distribution; median = 3, invariant to sample size
    def median(v):
        s = sorted(v); n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    # years grow 1x, 3x, 10x, 30x in volume, identical distribution repeated
    series = [(yr, median(dist * mult)) for yr, mult in [(2013, 1), (2015, 3), (2018, 10), (2022, 30)]]
    assert M.split_direction(series) == 0        # coverage growth alone produces NO false trend
    # and a genuinely shrinking series is still caught
    real = [(2013, 8.0), (2015, 6.0), (2018, 4.0), (2022, 2.0)]
    assert M.split_direction(real) == -1


def test_density_matched_subsample_kills_a_coverage_inflated_count():
    """KILL-FIXTURE: a coverage-SENSITIVE metric (count of narrow ignitions) rises with the corpus.
    Density-matching the late era to the early era's volume must collapse the inflation back to the
    early scale — the difference between a real finding and a coverage artifact (§1.3)."""
    early = [1 if i % 5 < 2 else 9 for i in range(100)]        # 40% are "narrow" (<2)
    late = [1 if i % 5 < 2 else 9 for i in range(1000)]        # SAME 40% narrow, 10x the volume
    narrow = lambda xs: sum(1 for x in xs if x < 2)
    m_early, m_raw_late = narrow(early), narrow(late)
    assert m_raw_late >= m_early * 5                            # raw metric IS coverage-inflated (~400 vs ~40)
    sub = M.density_matched_subsample(late, target_n=len(early), seed_key="killfix")
    assert len(sub) == len(early)
    m_sub_late = narrow(sub)
    assert m_sub_late <= m_early * 2                            # matched -> collapses to the early scale
    # determinism: same seed -> identical sample
    assert M.density_matched_subsample(late, len(early), "killfix") == sub
    assert M.density_matched_subsample(late, len(early), "other") != sub  # different seed -> different draw


def test_power_ok_underpowered_is_not_refuted():
    assert M.power_ok(200, 200) is True
    assert M.power_ok(199, 200) is False       # a thin cell reads UNDERPOWERED, never as evidence of absence
    assert M.power_ok(None, 200) is False


def test_symmetry_table_flags_the_power_position_reframe():
    t = M.symmetry_table({"D": 5.0, "R": 5.0})
    assert t["gap"] == 0.0 and t["reframe_flag"] is False
    t2 = M.symmetry_table({"D": 8.0, "R": 3.0})
    assert t2["gap"] == 5.0 and t2["reframe_flag"] is True      # asymmetry -> reframe check before publish
    assert M.symmetry_table({"D": 5.0})["gap"] is None          # missing party -> honest None


def test_did_is_plain_arithmetic():
    # losers drop 0.4; returning members drop 0.05 same weeks -> DiD = -0.35
    assert abs(M.did(0.8, 0.4, 0.8, 0.75) - (-0.35)) < 1e-9


def test_weekday_excess_detects_business_day_fingerprint():
    baseline = Counter({0: 100, 1: 100, 2: 100, 3: 100, 4: 100, 5: 100, 6: 100})  # flat
    observed = Counter({0: 40, 1: 40, 2: 40, 3: 40, 4: 40, 5: 0, 6: 0})           # weekday-only
    ex = M.weekday_excess(observed, baseline)
    assert ex[2] > 1.0 and ex[5] == 0.0 and ex[6] == 0.0        # weekdays over-, weekends absent
