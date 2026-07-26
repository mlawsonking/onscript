"""docs/19 §2/§3 acceptance — the nomenclature tagger is wired but DARK behind FEATURES["nomenclature_tags"].

Locks the four acceptance properties (docs/19 §3.4) plus the measure/pre-distill wiring:
  * flag OFF  => the tagger contributes ZERO bytes to any public surface (day table, prompt inputs,
                 the thresholds/prompts fingerprints) — byte-identical to a no-tagger world;
  * flag ON   => tags appear, nothing is deleted, and the audit fingerprint honestly reflects it;
  * the MEASURE wiring (nomenclature_rate in the nightly audit) is UNCONDITIONAL — it does not read the
    flag, so an asymmetric tagger can never be invisible to the instrument that exists to catch it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, distill, ops, site  # noqa: E402

FLAG = "nomenclature_tags"
# a real congress-119 nomenclature phrase (verdicts-119.json, ratio 1.0) and a real message that is not.
NOM = "21st century road to housing act"
MSG = "born in the united states"


class _flag:
    """Context manager: force FEATURES[nomenclature_tags] on/off and restore, so a test never leaks
    the release state into another (feature_on reads the FEATURES dict — no env override by design)."""
    def __init__(self, on): self.on = on
    def __enter__(self): self.prev = config.FEATURES[FLAG]; config.FEATURES[FLAG] = self.on
    def __exit__(self, *a): config.FEATURES[FLAG] = self.prev


def _day_data():
    row = {"ngram": NOM, "slug": "21st-century-road-to-housing-act", "party": "D", "day_peak": 10,
           "n": 6, "counts": {"D": 10, "R": 0}, "velocity": 1.0,
           "first_seen": {"date": "2026-07-13", "bioguide": "X"}, "df_weight": 1.0, "series": [3, 10]}
    return {"day": "2026-07-13", "top_synchronized": [row]}


# --- §3.4 the day table -------------------------------------------------------------------------
def test_sync_table_is_byte_identical_with_the_flag_off():
    dd = _day_data()
    with _flag(False):
        off = site.sync_table(dd, set(), depth=1)
    assert "nomtag" not in off, "the tagger rendered a chip while dark"
    # and the stored row is not mutated by a dark render (no nomenclature key leaks into the JSON path)
    assert "nomenclature" not in dd["top_synchronized"][0]


def test_sync_table_shows_the_tag_with_the_flag_on_and_deletes_nothing():
    dd = _day_data()
    with _flag(True):
        on = site.sync_table(dd, set(), depth=1)
    assert "nomtag" in on and "official name" in on          # the chip appears
    assert "hr6644" in on.lower() or "hr" in on.lower()       # cites the official record
    assert NOM.split()[0] in on                               # the row itself still renders (never deleted)


def test_flag_off_render_equals_a_no_tagger_render():
    # Belt-and-suspenders on "zero public bytes": the flag-off table equals the table produced when the
    # tagger's own contribution (the chip) is stripped, proving the ONLY difference the flag makes is the tag.
    dd = _day_data()
    with _flag(False):
        off = site.sync_table(dd, set(), depth=1)
    with _flag(True):
        on = site.sync_table(dd, set(), depth=1)
    import re as _re
    assert _re.sub(r' <span class="nomtag".*?</span>', "", on) == off


# --- §2a the MEASURE wiring (unconditional) -----------------------------------------------------
def test_symmetry_report_carries_the_nomenclature_rate_unconditionally():
    stmts = [{"member": {"party": "D", "bioguide": "A"}, "lane": 1, "published_at": "2026-07-13"}]
    measure = {"D": {"tagged": 4, "total": 10, "rate": 0.4}, "R": {"tagged": 1, "total": 20, "rate": 0.05}}
    saved = ops.util.write_json
    ops.util.write_json = lambda p, o: None                    # no data/derived side effects (test hygiene)
    try:
        with _flag(False):                                     # UNCONDITIONAL: present even when dark
            rep = ops.symmetry_report("2026-07-13", stmts, {}, freshness={}, degraded=False,
                                       nomen_measure=measure)
    finally:
        ops.util.write_json = saved
    assert rep["parties"]["D"]["nomenclature_rate"] == 0.4
    assert rep["parties"]["R"]["nomenclature_rate"] == 0.05
    assert rep["parties"]["D"]["nomenclature_tagged"] == 4


def test_thresholds_sha_is_stable_dark_and_moves_when_live():
    with _flag(False):
        dark = ops.thresholds_sha()
    with _flag(True):
        live = ops.thresholds_sha()
    assert dark != live, "a live tagger must fold its knob+index version into the instrument fingerprint"
    # dark must equal the pre-wiring fingerprint: the nomenclature knobs are simply absent from the hash.
    import json as _json
    from pipeline import util
    base = {"SYNC_MIN_MEMBERS": config.SYNC_MIN_MEMBERS, "NGRAM_MIN": config.NGRAM_MIN,
            "NGRAM_MAX": config.NGRAM_MAX, "BOILERPLATE_DF_SHARE_MAX": config.BOILERPLATE_DF_SHARE_MAX,
            "NEAR_JOINT_JACCARD": config.NEAR_JOINT_JACCARD,
            "LEDGER_MIN_TOTAL_USES": config.LEDGER_MIN_TOTAL_USES,
            "QUIET_DAY_MAX_STATEMENTS": config.QUIET_DAY_MAX_STATEMENTS}
    with _flag(False):
        assert ops.thresholds_sha() == util.sha256_hex(_json.dumps(base, sort_keys=True))


# --- §2c the pre-distill annotation -------------------------------------------------------------
def test_build_stats_always_segregates_nomenclature_from_message_claims():
    tp = {"label": NOM, "member_count": 5,
          "fragments": [{"text": "reintroduced the 21st century road to housing act today"}], "topics": []}
    with _flag(False):
        off = distill.build_stats("D", "2026-07-13", 12, [tp], None)
    assert off["talking_points"] == []
    assert off["shared_nomenclature"][0]["label"] == NOM
    with _flag(True):
        on = distill.build_stats("D", "2026-07-13", 12, [tp], None)
    assert on["talking_points"] == []
    assert on["shared_nomenclature"][0]["label"] == NOM


def test_prompts_sha_is_stable_dark_and_discloses_the_clause_live():
    with _flag(False):
        dark = ops.prompts_sha()
    with _flag(True):
        live = ops.prompts_sha()
    assert "P2P3_nomenclature_clause" not in dark               # dark: the committed prompt shas only
    assert "P2P3_nomenclature_clause" in live                   # live: the runtime clause is disclosed
    assert {"P1", "P2", "P3"} <= set(dark)
