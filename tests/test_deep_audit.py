"""Kill-fixtures for the Deep Archive coverage audit (docs/15 §D0.1). The audit does not get trusted
until it provably REJECTS each failure case: the single-party lane, the sub-ratio split, missing
provenance, thin attribution, a mixed-lane series, and a cross-era claim resting on a non-symmetric
era. No real data — pure synthetic. Also: the audit must be reproducible from its own output."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.deep import audit as A  # noqa: E402
from pipeline.deep import lanes as L  # noqa: E402


def _unit(source, party, mid, i):
    return {"source": source, "party": party, "member_id": mid,
            "url": f"https://x/{i}", "unit_date": "2005-06-01", "stable_id": f"{source}-{i}"}


def _units(source, nD, nR, dmembers=None, rmembers=None):
    """nD/nR statements; distinct members default = statement count (one per statement) unless capped."""
    dm = dmembers if dmembers is not None else nD
    rm = rmembers if rmembers is not None else nR
    out = []
    for i in range(nD):
        out.append(_unit(source, "D", f"D{i % dm}" if dm else None, f"d{i}"))
    for i in range(nR):
        out.append(_unit(source, "R", f"R{i % rm}" if rm else None, f"r{i}"))
    return out


def test_single_party_lane_is_rejected():
    """THE textbook failure (dwillis legacy 29 D / 0 R): must fail both the floor and symmetry gates."""
    res = A.audit_units(_units("crec", 29, 0), "2009-06")
    assert res["members"] == {"D": 29, "R": 0}
    assert res["gates"]["both_party_floor"] is False
    assert res["gates"]["symmetry_ratio"] is False        # never passes symmetry by vacuous ratio
    assert res["PASS"] is False


def test_symmetric_lane_passes():
    res = A.audit_units(_units("crec", 40, 36), "2001")
    assert res["gates"]["both_party_floor"] is True and res["gates"]["symmetry_ratio"] is True
    assert res["symmetry_ratio"] >= 0.33 and res["PASS"] is True


def test_sub_ratio_split_fails_symmetry_even_with_floor():
    """20 D members / 5 R members: both clear the >=5 floor, but ratio 0.25 < 0.33 -> symmetry FAILS."""
    res = A.audit_units(_units("crec", 20, 5), "2004")
    assert res["gates"]["both_party_floor"] is True
    assert res["symmetry_ratio"] == 0.25 and res["gates"]["symmetry_ratio"] is False
    assert res["PASS"] is False


def test_missing_provenance_fails_the_window():
    units = _units("crec", 20, 18)
    del units[0]["url"]                                    # one unit loses its provenance
    res = A.audit_units(units, "2001")
    assert res["gates"]["provenance_complete"] is False and res["PASS"] is False


def test_thin_attribution_fails():
    """Half the units carry no member id (CREC House-debate under-attribution) -> below the 0.40 floor
    when severe. Here 30% attributed."""
    units = _units("crec", 10, 10)                         # 20 attributed
    units += [{"source": "crec", "party": None, "member_id": None,
               "url": "u", "unit_date": "2001", "stable_id": f"x{i}"} for i in range(40)]  # 40 unattributed
    res = A.audit_units(units, "2001")
    assert res["attribution_rate"] < 0.40 and res["gates"]["attribution_completeness"] is False
    assert res["PASS"] is False


def test_genre_isolation_raises_on_mixed_lane():
    """Law 1 in code: a set mixing crec + press (untagged) must RAISE, never silently audit."""
    mixed = _units("crec", 10, 10) + [{"party": "D", "member_id": "P1", "url": "u",
                                       "unit_date": "2015", "stable_id": "p1"}]  # untagged = press
    try:
        A.audit_units(mixed, "x")
        assert False, "expected GenreIsolationError"
    except L.GenreIsolationError as e:
        assert "cross-lane" in str(e)


def test_cross_era_blocked_when_one_era_is_asymmetric():
    good = A.audit_units(_units("crec", 40, 36), "2019")
    bad = A.audit_units(_units("crec", 29, 0), "2005")
    assert A.audit_cross_era(good, good)["allowed"] is True
    blocked = A.audit_cross_era(good, bad)
    assert blocked["allowed"] is False and "era B" in blocked["reason"]


def test_audit_is_reproducible_and_json_serializable():
    units = _units("crec", 22, 19)
    r1 = A.audit_units(units, "2001")
    r2 = A.audit_units(units, "2001")
    assert r1 == r2                                        # deterministic
    assert json.loads(json.dumps(r1)) == r1               # pure-JSON, round-trips


def test_integrity_rate_reported_from_raw_count():
    units = _units("crec", 20, 18)                         # 38 accepted
    res = A.audit_units(units, "2001", n_raw=50)           # 12 rejected as stubs/boilerplate
    assert abs(res["integrity_rate"] - (1 - 38 / 50)) < 1e-9


# --- adversarial-review fixes (2026-07-15) -------------------------------------------------------
def test_cross_era_raises_across_different_lanes():
    """BLOCKER fix: gate 7 is where the genre confound hides — two lane-clean halves of DIFFERENT
    genres (crec-2005 vs press-2015) must RAISE, never trend freely."""
    crec = A.audit_units(_units("crec", 40, 36), "2005")
    press = A.audit_units([{"party": "D", "member_id": f"P{i}", "url": "u",
                            "unit_date": "2015", "stable_id": f"p{i}"} for i in range(40)]
                          + [{"party": "R", "member_id": f"Q{i}", "url": "u",
                              "unit_date": "2015", "stable_id": f"q{i}"} for i in range(36)], "2015")
    assert crec["lane"] == "crec" and press["lane"] == "press"
    try:
        A.audit_cross_era(crec, press)
        assert False, "expected GenreIsolationError across lanes"
    except L.GenreIsolationError as e:
        assert "WITHIN ONE lane" in str(e)


def test_unregistered_lane_is_rejected():
    """A typo'd lane ('crecc') must not sail through as a valid PASS (audit_units + audit_coverage)."""
    try:
        A.audit_units(_units("crecc", 40, 36), "2001")
        assert False, "expected ValueError for unregistered lane"
    except ValueError as e:
        assert "unregistered lane" in str(e)
    try:
        A.audit_coverage({"2005": {"D": {"members": 6}, "R": {"members": 6}}}, "not_a_lane")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_audit_coverage_is_fail_closed_on_provenance_and_attribution():
    """The summary path must FAIL a window that omits provenance/attribution evidence — a lane that
    'looks complete' cannot pass without affirmatively proving it."""
    cov = {"2005": {"D": {"members": 6, "statements": 50}, "R": {"members": 6, "statements": 40}}}
    silent = A.audit_coverage(cov, "loc_webarchive")["windows"]["2005"]
    assert silent["gates"]["provenance_complete"] is False and silent["PASS"] is False
    cov["2005"].update({"provenance_complete": True, "attribution_rate": 1.0})
    asserted = A.audit_coverage(cov, "loc_webarchive")["windows"]["2005"]
    assert asserted["PASS"] is True                        # passes only once provenance is asserted


def test_symmetry_boundary_is_exactly_one_third_not_0_33():
    """100 D / 33 R members = 3.03:1 must FAIL (0.33 < 1/3); 100 / 34 = 2.94:1 passes. Matches the
    documented 'no worse than 3:1' law, not the looser 0.33 constant."""
    fail = A.audit_units(_units("crec", 100, 33), "2001")
    assert fail["symmetry_ratio"] == 0.33 and fail["gates"]["symmetry_ratio"] is False
    ok = A.audit_units(_units("crec", 100, 34), "2001")
    assert ok["gates"]["symmetry_ratio"] is True


def test_expect_lane_catches_an_untagged_deep_set():
    """A wholly-untagged set (which lane_of reads as 'press') is caught when the caller declares it
    should be a deep lane."""
    untagged = [{"party": "D", "member_id": f"D{i}", "url": "u", "unit_date": "2005",
                 "stable_id": f"x{i}"} for i in range(10)]
    try:
        A.audit_units(untagged, "2005", expect_lane="crec")
        assert False, "expected GenreIsolationError"
    except L.GenreIsolationError:
        pass
