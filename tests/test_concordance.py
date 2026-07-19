"""1.4 The Concordance (R4 / docs/21 §3.2) — the per-member on-script index. DARK until
FEATURES["concordance"].

The discipline index is per-party-per-day; the Concordance is per-MEMBER: of a member's SOLO releases,
the share that used party-synchronized language that is NOT an official name. R4's three guarantees are
tested as invariants, not decoration — a denominator on every line, the SPAN gate (a bill title never
counts as on-script), and no predictive/motive claim — plus the R2 protections it inherits (joint
releases excluded; no swarm of tied-at-zero members below the naming floor).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import build, config, nomenclature, site  # noqa: E402

FLAG = "concordance"


class _flag:
    def __init__(self, on): self.on = on
    def __enter__(self): self.prev = config.FEATURES[FLAG]; config.FEATURES[FLAG] = self.on
    def __exit__(self, *a): config.FEATURES[FLAG] = self.prev


def _stmt(bio, party, text, *, day="2026-06-15", url=None, joint=None, congress=119,
          state="TX", chamber="house", syndicated=False, lane=1, name=None):
    return {"id": f"{bio}-{day}-{len(text)}", "lane": lane, "syndicated": syndicated,
            "joint_group": joint, "published_at": day, "congress": congress,
            "url": url or f"https://{bio.lower()}.house.gov/{day}", "text": text,
            "member": {"bioguide": bio, "party": party, "state": state, "chamber": chamber,
                       "name": name or f"Rep. {bio}"}}


def _led(*ngrams, peak=20):
    # build_concordance reads KEY membership + peak_units (the #143 coordination floor); nothing else.
    # peak 20 clears the default CONCORDANCE_PEAK_FLOOR (15), so these count as "the party script".
    return {ng: {"peak_units": peak} for ng in ngrams}


def _member(res, bio):
    return next(m for m in res["members"] if m["bioguide"] == bio)


# --- the core metric: solo on-script share, with denominators -----------------------------------
def test_solo_on_script_share_has_raw_counts_and_span_flag():
    led = _led("protect social security benefits")
    stmts = ([_stmt("A", "D", "we must protect social security benefits", day=f"2026-06-1{i}") for i in range(4)]
             + [_stmt("A", "D", "an unrelated statement about roads", day="2026-06-15")])  # not on-script
    res = build.build_concordance(stmts, led, min_statements=1)
    a = _member(res, "A")
    assert a["statements"] == 5 and a["on_script"] == 4          # 4 of 5 used the synchronized phrase
    assert a["index"] == round(4 / 5, 4)                          # the share, with its denominator visible
    assert res["span_gated"] is True


# --- the coordination floor: generic co-used language is not "the party script" (#143 / saturation) -
def test_a_phrase_below_the_coordination_floor_is_not_party_script():
    # peak_units 5 < the default floor (15): coordinated too narrowly to count. Without this control the
    # index saturates near 1.0 (every release shares SOME 3-member-co-used gram) — a measurement artifact.
    led = {"protect social security benefits": {"peak_units": 5}}
    stmts = [_stmt("A", "D", "we protect social security benefits", day=f"2026-06-0{i+1}") for i in range(3)]
    a = _member(build.build_concordance(stmts, led, min_statements=1), "A")
    assert a["statements"] == 3 and a["on_script"] == 0


# --- SPAN gate: an official name is never counted as being on-script (the #143 confound) ----------
def test_span_gate_excludes_official_names_denominator_unchanged():
    led = _led("secure american families act")
    stmts = [_stmt("A", "D", "today i reintroduced the secure american families act", day=f"2026-06-0{i+1}")
             for i in range(3)]
    # baseline: the tagger says NOT a name -> the phrase counts (this also proves the phrase is matchable)
    base = build.build_concordance(stmts, led, min_statements=1)
    assert _member(base, "A")["on_script"] == 3

    # now make that exact span an official name; the numerator must drop it, the denominator must not.
    orig = nomenclature.is_nomenclature
    nomenclature.is_nomenclature = lambda ng, c: {"ratio": 1.0} if ng == "secure american families act" else None
    try:
        gated = build.build_concordance(stmts, led, min_statements=1)
    finally:
        nomenclature.is_nomenclature = orig
    a = _member(gated, "A")
    assert a["on_script"] == 0 and a["statements"] == 3          # SPAN-gated numerator, honest denominator


# --- joint / co-signed releases are the coordination surface, not the member's solo voice ---------
def test_joint_releases_are_excluded_from_the_member_index():
    led = _led("defend affordable health care")
    stmts = ([_stmt("A", "D", "we defend affordable health care", day=f"2026-06-0{i+1}") for i in range(2)]
             + [_stmt("A", "D", "we defend affordable health care", day="2026-06-09", joint="joint:abcd")])
    a = _member(build.build_concordance(stmts, led, min_statements=1), "A")
    assert a["statements"] == 2                                   # the joint release counts for neither part


# --- the naming floor: no swarm of tied-at-zero "vessels" (R2) ------------------------------------
def test_below_floor_member_is_not_named_but_is_counted_in_aggregate():
    led = _led("protect social security benefits")
    stmts = [_stmt("A", "D", "we protect social security benefits", day=f"2026-06-0{i+1}") for i in range(2)]
    res = build.build_concordance(stmts, led, min_statements=3)
    assert res["members"] == []                                  # 2 < 3 -> not named
    assert res["counts"] == {"named": 0, "excluded_below_floor": 1, "members_seen": 1}


# --- symmetry: both parties scored by one rule; Independents are not in the composites ------------
def test_both_parties_scored_and_independents_excluded():
    led = _led("stand up for workers")
    stmts = []
    for bio, party in (("D1", "D"), ("R1", "R"), ("I1", "I")):
        stmts += [_stmt(bio, party, "we stand up for workers", day=f"2026-06-0{i+1}") for i in range(3)]
    res = build.build_concordance(stmts, led, min_statements=1)
    assert {m["party"] for m in res["members"]} == {"D", "R"}
    assert res["counts"]["members_seen"] == 2                    # the Independent is not counted at all


# --- receipts: >=3 dated citations per named member, capped, distinct, with member/date/url -------
def test_receipts_are_capped_distinct_and_carry_date_and_url():
    phrases = ["protect social security benefits", "defend affordable health care",
               "expand rural broadband access", "reform student loan debt"]
    led = _led(*phrases)
    stmts = [_stmt("A", "D", f"today we will {p}", day=f"2026-06-0{i+1}", url=f"https://a.house.gov/{i}")
             for i, p in enumerate(phrases)]
    a = _member(build.build_concordance(stmts, led, min_statements=1, receipts_max=3), "A")
    assert a["on_script"] == 4 and len(a["receipts"]) == 3       # all 4 on-script, receipts capped at 3
    assert len({r["phrase"] for r in a["receipts"]}) == 3        # distinct phrases
    assert all(r.get("date") and r.get("url") for r in a["receipts"])


# --- the render: R4 guarantees are visible on the page -------------------------------------------
def _cdata_one(on=4, st=10, excl=5):
    return {"members": [{"bioguide": "A", "name": "Rep. Alice", "party": "D", "state": "CA",
                         "chamber": "house", "statements": st, "on_script": on,
                         "index": round(on / st, 4),
                         "receipts": [{"phrase": "protect social security benefits",
                                       "date": "2026-06-01", "url": "https://a.house.gov/x"}]}],
            "window": {"start": "2026-06-01", "end": "2026-06-30"}, "min_statements": 10,
            "counts": {"named": 1, "excluded_below_floor": excl, "members_seen": excl + 1},
            "peak_floor": 15,
            "nomenclature_index_version": "idx-119-abc", "span_gated": True}


def test_render_shows_a_denominator_on_every_line():
    html = site.concordance_body(_cdata_one(on=4, st=10))
    assert "4 of 10 statements" in html and "40.0%" in html      # R4: denominators on every line


def test_render_states_the_no_motive_no_prediction_caveat():
    html = site.concordance_body(_cdata_one())
    assert "not a claim about motive" in html and "overlap" in html.lower()


def test_render_discloses_the_name_index_the_floor_and_renders_receipts():
    html = site.concordance_body(_cdata_one(excl=5))
    assert "idx-119-abc" in html                                 # which official-name table excluded names
    assert "at least 15 members" in html                         # the coordination floor is disclosed
    assert "5 members had fewer than 10" in html                 # below-floor disclosed in aggregate
    assert "protect social security benefits" in html and "source" in html  # the receipt + its link


def test_render_empty_column_is_honest_for_each_party():
    html = site.concordance_body({"members": [], "window": {}, "min_statements": 10, "counts": {}})
    assert html.count("No member reached the statement floor") == 2  # both columns, never borrowed


# --- the release gate: DARK by default -----------------------------------------------------------
def test_nav_link_is_absent_when_dark_and_present_when_released():
    with _flag(False):
        assert 'concordance.html">Concordance</a>' not in site.page("t", "<p>b</p>")
    with _flag(True):
        assert 'concordance.html">Concordance</a>' in site.page("t", "<p>b</p>")


def test_methodology_section_is_byte_identical_when_dark():
    # The Methodology page (where the page's "How this is measured" link points) carries ZERO of the
    # Concordance's text while the flag is off — the redesign ships dark; the flip adds the only byte.
    marker = "The Concordance (per-member on-script index)"
    with _flag(False):
        assert marker not in site.methodology_body()
    with _flag(True):
        assert marker in site.methodology_body()


def test_feature_ships_dark():
    assert config.FEATURES["concordance"] is False
