"""1.5 The Unison + The Void (R2 / docs/21 §3.2) — the symmetric weekly awards that replaced the killed
Ventriloquism Award. DARK until FEATURES["awards"].

THE UNISON: each party's largest single-day office-share phrase — of the party offices that published a
solo release that day, the share that used one exact phrase. R2's protections are tested as invariants:
the office-share carries its numerator AND denominator on every line; it is SPAN-gated (a bill title
never wins); joint releases are excluded from the office population; both parties are scored by one rule
and no individual member is named as a "vessel" (the unit is the PHRASE). THE VOID: the window's loudest
silence, both directions, rolled up from the 1.2 boards — degrading honestly to "unavailable" when no
scored board exists (a gap is never rendered as a silence).
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import boilerplate, build, config, nomenclature, site  # noqa: E402

FLAG = "awards"


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


def _entry(daily_bios: dict) -> dict:
    """A ledger entry from {day: {party: [bioguides who used the phrase in a solo release]}}. Mirrors what
    the phrase engine finalizes: per (day, party) a unit count + a members_{party} list (joints excluded
    upstream). build_awards reads only e['daily']; the office-share denominator comes from the statements."""
    daily, peak = {}, 0
    for day, parties in daily_bios.items():
        e = {}
        for p, bios in parties.items():
            e[p] = len(bios)
            e[f"members_{p}"] = sorted(bios)
            peak = max(peak, len(bios))
        daily[day] = e
    return {"ngram": "?", "n": 4, "daily": daily, "peak_units": peak,
            "first_seen": {"date": min(daily_bios), "bioguide": None, "tie": []}, "df_weight": 1.0}


def _users(ngram, day, party, n, *, congress=119):
    """`n` distinct party offices that used `ngram` in a solo release on `day`."""
    bios = [f"{party}-{day}-{i}" for i in range(n)]
    return bios, [_stmt(b, party, f"today we will {ngram} for the people", day=day, congress=congress) for b in bios]


def _silent(day, party, n, *, congress=119):
    """`n` distinct party offices that published a solo release on `day` but did NOT use the phrase."""
    bios = [f"{party}-{day}-s{i}" for i in range(n)]
    return bios, [_stmt(b, party, "a routine update about roads and bridges", day=day, congress=congress) for b in bios]


# --- THE UNISON: the core metric — office-share with its numerator AND denominator ----------------
def test_office_share_carries_numerator_and_denominator():
    ng = "protect social security benefits"
    users, us = _users(ng, "2026-06-15", "D", 30)
    _, sil = _silent("2026-06-15", "D", 15)                       # 15 more active offices didn't say it
    led = {ng: _entry({"2026-06-15": {"D": users}})}
    res = build.build_awards(us + sil, led, focus_day="2026-06-15", min_active=10, roster_map={})
    top = res["unison"]["D"][0]
    assert top["ngram"] == ng and top["day"] == "2026-06-15"
    assert top["offices_using"] == 30 and top["offices_active"] == 45  # denominator on its face
    assert top["office_share"] == round(30 / 45, 4)
    assert res["span_gated"] is True and res["caucus"]["D"] == 45


# --- the min-active floor: a thin day can't take the award on a two-of-three share ----------------
def test_min_active_floor_excludes_thin_days():
    ng = "stand with working families"
    users, us = _users(ng, "2026-06-15", "D", 3)                  # only 3 active offices all day
    led = {ng: _entry({"2026-06-15": {"D": users}})}
    assert build.build_awards(us, led, focus_day="2026-06-15", min_active=15, roster_map={})["unison"]["D"] == []
    lowered = build.build_awards(us, led, focus_day="2026-06-15", min_active=3, roster_map={})
    assert lowered["unison"]["D"][0]["office_share"] == 1.0        # eligible once the floor drops


# --- SPAN gate: an official name is never a unison (a bill title reaching high share is #143) ------
def test_span_gate_excludes_official_names():
    ng = "secure american families act"
    users, us = _users(ng, "2026-06-15", "D", 20)
    _, sil = _silent("2026-06-15", "D", 10)
    led = {ng: _entry({"2026-06-15": {"D": users}})}
    base = build.build_awards(us + sil, led, focus_day="2026-06-15", min_active=5, roster_map={})
    assert base["unison"]["D"][0]["ngram"] == ng                  # baseline: it wins when not a name

    orig = nomenclature.is_nomenclature
    nomenclature.is_nomenclature = lambda g, c: {"ratio": 1.0} if g == ng else None
    try:
        gated = build.build_awards(us + sil, led, focus_day="2026-06-15", min_active=5, roster_map={})
    finally:
        nomenclature.is_nomenclature = orig
    assert gated["unison"]["D"] == []                             # SPAN-gated out


# --- the office population: numerator is intersected with active offices, so share is always <= 1 --
def test_numerator_is_intersected_with_active_offices():
    ng = "expand rural broadband access"
    ledger_members = [f"D-2026-06-15-{i}" for i in range(30)]     # ledger claims 30 used it
    active = ledger_members[:22]                                  # ...but only 22 published solo that day
    us = [_stmt(b, "D", f"we {ng} today", day="2026-06-15") for b in active]
    led = {ng: _entry({"2026-06-15": {"D": ledger_members}})}
    top = build.build_awards(us, led, focus_day="2026-06-15", min_active=5, roster_map={})["unison"]["D"][0]
    assert top["offices_using"] == 22 and top["offices_active"] == 22 and top["office_share"] == 1.0


# --- joint / co-signed releases are coordination, not an office's own wording ---------------------
def test_joint_releases_are_excluded_from_the_office_population():
    ng = "defend affordable health care"
    users, us = _users(ng, "2026-06-15", "D", 20)
    joint = [_stmt(f"J{i}", "D", f"we {ng} together", day="2026-06-15", joint="joint:abcd") for i in range(5)]
    led = {ng: _entry({"2026-06-15": {"D": users}})}
    top = build.build_awards(us + joint, led, focus_day="2026-06-15", min_active=5, roster_map={})["unison"]["D"][0]
    assert top["offices_active"] == 20                           # the 5 joint offices are not active-solo


# --- symmetry: both parties scored by one rule; Independents are not in the composites ------------
def test_both_parties_scored_and_independents_excluded():
    ngd, ngr = "stand up for workers", "cut the red tape"
    du, ds = _users(ngd, "2026-06-15", "D", 20)
    ru, rs = _users(ngr, "2026-06-15", "R", 18)
    _, is_ = _users("we love this country", "2026-06-15", "I", 12)
    led = {ngd: _entry({"2026-06-15": {"D": du}}), ngr: _entry({"2026-06-15": {"R": ru}})}
    res = build.build_awards(ds + rs + is_, led, focus_day="2026-06-15", min_active=5, roster_map={})
    assert res["unison"]["D"][0]["ngram"] == ngd and res["unison"]["R"][0]["ngram"] == ngr
    assert set(res["unison"].keys()) == {"D", "R"} and "I" not in res["caucus"]


# --- the window: only single days inside the trailing week are eligible ---------------------------
def test_only_days_in_the_trailing_window_count():
    ng = "protect our democracy now"
    old_u, old_s = _users(ng, "2026-06-01", "D", 40)             # share 1.0 but outside a 7-day window
    new_u, new_s = _users(ng, "2026-06-14", "D", 20)
    _, sil = _silent("2026-06-14", "D", 20)                      # in-window share 0.5
    led = {ng: _entry({"2026-06-01": {"D": old_u}, "2026-06-14": {"D": new_u}})}
    top = build.build_awards(old_s + new_s + sil, led, focus_day="2026-06-15",
                             window_days=7, min_active=5, roster_map={})["unison"]["D"][0]
    assert top["day"] == "2026-06-14"                            # 2026-06-01 is out of window despite higher share


# --- a phrase shows once, at its single best day (no five near-identical rows for one week) --------
def test_a_phrase_appears_once_at_its_best_day():
    ng = "lower prescription drug prices"
    u1, s1 = _users(ng, "2026-06-13", "D", 30); _, x1 = _silent("2026-06-13", "D", 30)   # share .5
    u2, s2 = _users(ng, "2026-06-14", "D", 30); _, x2 = _silent("2026-06-14", "D", 10)   # share .75
    led = {ng: _entry({"2026-06-13": {"D": u1}, "2026-06-14": {"D": u2}})}
    rows = [r for r in build.build_awards(s1 + x1 + s2 + x2, led, focus_day="2026-06-15",
                                          min_active=5, roster_map={})["unison"]["D"] if r["ngram"] == ng]
    assert len(rows) == 1 and rows[0]["day"] == "2026-06-14"


# --- the display guards: a boilerplate / weak-label phrase never wins -----------------------------
def test_weak_label_phrases_do_not_win():
    ng = "in the united states of"
    users, us = _users(ng, "2026-06-15", "D", 30)
    _, sil = _silent("2026-06-15", "D", 10)
    led = {ng: _entry({"2026-06-15": {"D": users}})}
    orig = boilerplate.is_weak_label
    boilerplate.is_weak_label = lambda g: g == ng
    try:
        res = build.build_awards(us + sil, led, focus_day="2026-06-15", min_active=5, roster_map={})
    finally:
        boilerplate.is_weak_label = orig
    assert res["unison"]["D"] == []


# --- THE VOID: unavailable without boards (a gap is never rendered as a silence) ------------------
def test_void_is_unavailable_without_boards():
    ng = "reform the tax code fairly"
    users, us = _users(ng, "2026-06-15", "D", 20); _, sil = _silent("2026-06-15", "D", 10)
    led = {ng: _entry({"2026-06-15": {"D": users}})}
    res = build.build_awards(us + sil, led, focus_day="2026-06-15", min_active=5, roster_map={})
    assert res["void"]["available"] is False and res["void"]["loudest_silence"] is None


# --- THE VOID: rolls up the window's loudest silence, both directions; out-of-window/unscored out --
def test_void_rolls_up_loudest_silence_both_directions():
    d = Path(tempfile.mkdtemp())
    (d / "2026-06-14.json").write_text(json.dumps({"scored": True,
        "silent": [{"topic": "immigration", "label": "Immigration", "news_volume": 0.2, "D": 0, "R": 1},
                   {"topic": "guns", "label": "Guns", "news_volume": 0.4, "D": 1, "R": 0}],
        "void": [{"topic": "post_office", "label": "Post Office", "news_volume": 0.0, "D": 6, "R": 1}]}))
    (d / "2026-06-13.json").write_text(json.dumps({"scored": True,
        "silent": [{"topic": "climate", "label": "Climate", "news_volume": 0.5, "D": 2, "R": 0}], "void": []}))
    (d / "2026-06-13b-unscored.json").write_text(json.dumps({"scored": False, "silent": [], "void": []}))
    (d / "2026-06-01.json").write_text(json.dumps({"scored": True,                       # outside the window
        "silent": [{"topic": "z", "label": "Z", "news_volume": 0.99, "D": 0, "R": 0}], "void": []}))

    ng = "invest in american manufacturing"
    users, us = _users(ng, "2026-06-14", "D", 20); _, sil = _silent("2026-06-14", "D", 10)
    led = {ng: _entry({"2026-06-14": {"D": users}})}
    v = build.build_awards(us + sil, led, focus_day="2026-06-15", window_days=7,
                           min_active=5, roster_map={}, silence_dir=d)["void"]
    assert v["available"] is True and v["boards_scored"] == 2    # 06-01 out of window; unscored not counted
    assert v["loudest_silence"]["topic"] == "climate"            # 0.5 is the loudest in-window silence
    assert v["loudest_void"]["topic"] == "post_office"           # 7 combined statements, the loudest void


# --- the render: R2 guarantees are visible on the page -------------------------------------------
def _adata_one(du=30, da=40, caucus=200):
    return {"window": {"start": "2026-06-09", "end": "2026-06-15"}, "min_active": 15,
            "caucus": {"D": caucus, "R": caucus}, "nomenclature_index_version": "idx-119-abc",
            "span_gated": True,
            "unison": {"D": [{"ngram": "protect social security benefits", "slug": "abc123",
                              "day": "2026-06-15", "offices_using": du, "offices_active": da,
                              "office_share": round(du / da, 4),
                              "members": [{"bioguide": "D1", "name": "Rep. Alice", "state": "CA"}],
                              "members_more": du - 1}], "R": []},
            "void": {"available": False, "loudest_silence": None,
                     "note": "the absence map has not been built for this window"}}


def test_render_unison_shows_office_share_and_both_denominators():
    html = site.awards_body(_adata_one(du=30, da=40, caucus=200))
    assert "30 of 40 offices" in html and "75.0%" in html        # numerator / denominator on its face
    assert "of 200 in the caucus" in html                        # the secondary (caucus) denominator


def test_render_states_the_no_motive_caveat():
    html = site.awards_body(_adata_one())
    assert "not a claim about motive" in html and "overlap" in html.lower()


def test_render_empty_unison_column_is_honest_for_each_party():
    html = site.awards_body({"window": {}, "unison": {"D": [], "R": []}, "caucus": {},
                             "void": {"available": False}})
    assert html.count("No phrase reached the office-share threshold") == 2   # both columns, never borrowed


def test_render_void_unavailable_is_honest():
    html = site.awards_body(_adata_one())
    assert "Unavailable this week" in html


def test_render_void_shows_loudest_silence_when_scored():
    void = {"available": True, "boards_scored": 5, "note": "n",
            "loudest_silence": {"topic": "guns", "label": "Guns", "news_volume": 0.4, "D": 0, "R": 1,
                                "day": "2026-06-14"},
            "silence_top": [{"topic": "guns", "label": "Guns", "news_volume": 0.4, "D": 0, "R": 1,
                             "day": "2026-06-14"}],
            "loudest_void": None, "void_top": []}
    html = site.awards_body({"window": {}, "unison": {"D": [], "R": []}, "caucus": {}, "void": void})
    assert "loudest silence" in html.lower() and "Guns" in html


# --- the release gate: DARK by default -----------------------------------------------------------
def test_nav_link_is_absent_when_dark_and_present_when_released():
    with _flag(False):
        assert 'awards.html">Awards</a>' not in site.page("t", "<p>b</p>")
    with _flag(True):
        assert 'awards.html">Awards</a>' in site.page("t", "<p>b</p>")


def test_methodology_section_is_byte_identical_when_dark():
    marker = "The Unison &amp; The Void (weekly awards)"
    with _flag(False):
        assert marker not in site.methodology_body()
    with _flag(True):
        assert marker in site.methodology_body()


def test_feature_ships_dark():
    assert config.FEATURES["awards"] is False
