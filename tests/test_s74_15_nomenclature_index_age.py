"""S74-15 Package 1c/1d: the name index's age is visible and bounded.

The committed bill-and-committee name index went 128 days unrefreshed with nothing recording it, so
bill titles introduced after 2026-07-16 passed the name gate as messages. The symmetry audit now
carries the index's age beside `nomenclature_rate`, and the watchdog warns once the age exceeds
config.NOMENCLATURE_INDEX_MAX_AGE_DAYS, paging on the crossing day and weekly after (R-74.17's
pattern). Built on the committed verdicts table, so a refresh moves these expectations with it.
"""
from __future__ import annotations

import ast
import json
from datetime import date, timedelta
from pathlib import Path

from pipeline import config, instrument_fingerprint, nomenclature, watchdog

ROOT = Path(__file__).resolve().parents[1]


def _shift(day: str, days: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def _config_reads(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "config":
            names.add(node.attr)
    return names


def test_the_constant_is_owned_by_config_read_by_the_watchdog_and_not_a_threshold():
    """docs/37 rule 1: the registry is tested against its owner. The constant lives in config, the
    watchdog reads it from there (no local copy), and it is an operations constant, so it is not in
    the fingerprinted threshold registry and cannot move thresholds_sha."""
    assert isinstance(config.NOMENCLATURE_INDEX_MAX_AGE_DAYS, int)
    assert config.NOMENCLATURE_INDEX_MAX_AGE_DAYS > 0
    assert "NOMENCLATURE_INDEX_MAX_AGE_DAYS" in _config_reads(ROOT / "pipeline" / "watchdog.py")
    assert not hasattr(watchdog, "NOMENCLATURE_INDEX_MAX_AGE_DAYS")
    assert "NOMENCLATURE_INDEX_MAX_AGE_DAYS" not in instrument_fingerprint.LIVE_THRESHOLD_NAMES
    assert "NOMENCLATURE_INDEX_MAX_AGE_DAYS" not in instrument_fingerprint.LEGACY_THRESHOLD_NAMES


def test_the_committed_tables_fetch_date_parses_and_the_age_is_right():
    """Real artifact: the committed verdicts table's index_version is an ISO date that is no later
    than every bill-titles table it was built over, and the age is plain calendar arithmetic."""
    ref = config.REFERENCE / "nomenclature"
    newest = nomenclature.committed_verdict_congresses()[-1]
    table = json.loads((ref / f"verdicts-{newest}.json").read_text(encoding="utf-8"))
    version = table["index_version"]
    fetched = date.fromisoformat(version)
    assert date.fromisoformat(table["fetch_date"]) >= fetched
    assert nomenclature.index_version() == version
    for offset in (0, 1, 21, 128):
        day = (fetched + timedelta(days=offset)).isoformat()
        assert nomenclature.index_age(day) == {"index_version": version, "age_days": offset,
                                               "postdates_day": False}
    # docs/37 rule 17: a day older than the index never reads a negative age.
    before = nomenclature.index_age(_shift(version, -5))
    assert before["age_days"] == 0 and before["postdates_day"] is True


def test_the_watchdog_carries_the_age_and_pages_on_the_crossing_day_and_weekly_after():
    version = nomenclature.index_version()
    limit = config.NOMENCLATURE_INDEX_MAX_AGE_DAYS
    for age in range(0, limit + 30):
        [f] = watchdog.check_nomenclature_index(_shift(version, age))
        assert f["check"] == "nomenclature_index"
        assert f["evidence"]["age_days"] == age and f["evidence"]["index_version"] == version
        expected = "alarm" if age in {limit + 1, limit + 8, limit + 15, limit + 22, limit + 29} else "ok"
        assert f["level"] == expected, (age, f)
        if age > limit:
            assert "P14" in f["detail"]


def test_a_missing_index_alarms_rather_than_reporting_health():
    [f] = watchdog.check_nomenclature_index("2026-11-21", index_age={"index_version": None,
                                                                     "age_days": None})
    assert f["level"] == "alarm"


def test_the_symmetry_report_carries_the_age_beside_the_rate_for_both_parties():
    from pipeline import ops

    saved = ops.util.write_json
    ops.util.write_json = lambda p, o: None                  # no data/derived side effects
    try:
        rep = ops.symmetry_report("2026-11-19", [], {}, freshness={}, degraded=False,
                                  nomen_measure={"D": {"tagged": 1, "total": 10, "rate": 0.1},
                                                 "R": {"tagged": 0, "total": 5, "rate": 0.0}},
                                  fingerprint={"sha256": "x"})
    finally:
        ops.util.write_json = saved
    expected = nomenclature.index_age("2026-11-19")
    for p in config.COMPOSITE_PARTIES:
        row = rep["parties"][p]
        assert row["nomenclature_index_version"] == expected["index_version"]
        assert row["nomenclature_index_age_days"] == expected["age_days"]
