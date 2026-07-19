"""Kill-fixtures for nomenclature segregation (docs/16 §5). Real strings, both directions.

The live site's "top synchronized phrases" are substantially bill titles and committee names — not
messaging. The trigger was v2 1.3 nearly publishing "Chip Roy authored the SAVE Act", where what
actually happened is that he was the first member in our press corpus to type the name of a bill he
sponsored. This fixture is the proof that the tagger separates the two, in BOTH directions:

  KILL    — the statute's/institution's own name, and every straddling window of it, is tagged.
  PROTECT — a MESSAGE about the bill survives, including the D counter-brand ("the big ugly bill")
            and the generic policy English that happens to sit inside a title ("child tax credit").

Runs offline against the committed reference tables + verdicts (data/reference/nomenclature/), so a
third party reproduces every number from committed data alone. Follows tests/test_deep_crec_boilerplate.py.
"""
import inspect
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import boilerplate, config, nomenclature as N  # noqa: E402

C = 119

# A hand-built index for the pure rule tests: (name tokens, cite) keyed by first token, longest-first.
# Synthetic on purpose — the three rules are geometry and must be provable without a 94 MB corpus.
_IDX = {
    "save": ((("save", "act"), "hr22"),),
    "21st": ((("21st", "century", "road", "to", "housing", "act"), "hr6644"),),
    "water": ((("water", "resources", "development", "act"), "s601"),),
}


# --- the three rules, proven as geometry ---------------------------------------------------
def test_rule_a_containment_tags_the_name_and_a_clean_window():
    toks = "reintroduced the save act this week".split()
    runs = N.name_spans(toks, _IDX)
    assert runs == [(2, 3, "hr22")]
    assert N.classify_occ(toks, 1, 3, runs) == "A"      # "the save act" — leading article is outside


def test_rule_b_truncation_tags_a_phrase_whose_edge_cuts_inside_the_run():
    toks = "the bipartisan 21st century road to housing act which passed".split()
    runs = N.name_spans(toks, _IDX)
    assert runs == [(2, 7, "hr6644")]
    assert N.classify_occ(toks, 1, 6, runs) == "B"      # "bipartisan 21st…housing": left edge outside
    assert N.classify_occ(toks, 3, 6, runs) == "B"      # "century…act which": right edge outside


def test_a_run_strictly_inside_the_phrase_is_predication_and_never_tags():
    """THE heart of the design: the message is the part of the phrase the name does not cover."""
    toks = "the save act would gut medicaid".split()
    runs = N.name_spans(toks, _IDX)
    assert runs == [(1, 2, "hr22")]
    assert N.classify_occ(toks, 0, 4, runs) is None     # "the save act would" -> PREDICATION
    assert N.classify_occ(toks, 0, 6, runs) is None     # "…would gut medicaid" -> PREDICATION


def test_the_stopword_trap_anchor_is_the_first_content_token():
    """REGRESSION (docs/16 §3): 'would' IS in boilerplate.STOPWORDS. A rule that ignored ALL stopwords
    would trim the trailing modal too and score 'the save act would' at 1.00 — a false-positive TAG on
    this item's own acceptance case. A LEADING article may fall outside a span; a TRAILING modal starts
    a predicate, so only the left edge moves."""
    assert "would" in boilerplate.STOPWORDS and "the" in boilerplate.STOPWORDS
    assert N._anchor(["the", "save", "act", "would"], 10) == 11      # skips 'the', keeps 'would' inside
    assert N._anchor(["save", "act"], 10) == 10
    assert N._anchor(["the", "of", "and"], 10) == 10                 # all-stopword phrase -> the start


def test_name_spans_absorbs_a_trailing_year():
    """The index is year-stripped, so a run must re-absorb the year the member actually typed —
    'Act of 2024' and 'Act, 2026' (which tokenizes to a BARE trailing year) are ONE name."""
    of_year = "the water resources development act of 2024 passed".split()
    assert N.name_spans(of_year, _IDX) == [(1, 6, "s601")]
    bare_year = "the water resources development act 2026 passed".split()
    assert N.name_spans(bare_year, _IDX) == [(1, 5, "s601")]
    no_year = "the water resources development act passed".split()
    assert N.name_spans(no_year, _IDX) == [(1, 4, "s601")]


def test_name_spans_takes_the_longest_match_and_never_overlaps():
    idx = {"save": ((("save", "act", "of", "grace"), "hr99"), (("save", "act"), "hr22"))}
    assert N.name_spans("the save act of grace passed".split(), idx) == [(1, 4, "hr99")]
    assert N.name_spans("the save act passed".split(), idx) == [(1, 2, "hr22")]


# --- the corpus verdicts: KILL --------------------------------------------------------------
def test_the_name_is_tagged_but_a_message_about_the_bill_survives():
    assert N.is_nomenclature("safeguard american voter eligibility save act", C)   # 1.000 (see §DEVIATION)
    assert N.is_nomenclature("21st century road to housing act", C)                # 1.000
    assert N.is_nomenclature("the laken riley act", C)                             # 1.000
    assert N.is_nomenclature("state and related programs appropriations act", C)   # 1.000
    assert not N.is_nomenclature("the save act would", C)   # SENTINEL: 'would' IS a STOPWORD.
    assert not N.is_nomenclature("the save act is", C)      # A rule ignoring all stopwords
    assert not N.is_nomenclature("so-called save act", C)   # scores 'the save act would' 1.00.


def test_rule_b_truncation_kills_straddling_windows_of_a_long_title():
    # NGRAM_MAX=6 < the real title length, so windows straddle. Rule A alone returns None for these.
    assert N.is_nomenclature("bipartisan 21st century road to housing", C)["rule"] == "B"   # 0.986
    assert N.is_nomenclature("the bipartisan 21st century road to", C)["rule"] == "B"       # 0.985
    assert N.is_nomenclature("century road to housing act which", C)["rule"] == "B"         # 1.000


def test_committee_lane_is_load_bearing():
    """The bill lane ALONE scores the live 2026-07-15 #1 at 0.109 -> MISS. With the committee lane it
    is the House Appropriations subcommittee 'National Security, Department of State, and Related
    Programs' at 0.946 -> TAG."""
    v = N.is_nomenclature("national security department", C)
    assert v["lane"] == "committee" and v["class"] == "institution"
    assert v["cite"].startswith("subcmte:")


def test_year_variants_match_one_name():
    # Index-time _YEAR_TAIL MUST strip a BARE trailing year ("Act, 2026"), not just "of YYYY".
    assert N.is_nomenclature("water resources development act", C)                 # 1.000
    assert N.is_nomenclature("state and related programs appropriations act", C)   # comma-year


def test_acronym_gloss_is_recovered():
    """Members type the GLOSS ('the Safeguard American Voter Eligibility (SAVE) Act'), which matches
    NEITHER indexed short title. synthesize_acronym_glosses splices them; without it these are 0.000."""
    assert N.is_nomenclature("american voter eligibility save", C)     # 1.000
    assert N.is_nomenclature("safeguard american voter eligibility save", C)


# --- the corpus verdicts: PROTECT -----------------------------------------------------------
def test_generic_policy_english_inside_a_title_survives():
    """The case that separates SPAN from the rejected capitalization design: 'child tax credit' is
    0.003 here and 0.683 (a false-positive TAG) under CAP. Every one of these sits inside a real
    indexed title, and every one survives, because a title is only nomenclature where a member is
    NAMING it."""
    for ng in ["law enforcement officers",      # 0.121 (Law Enforcement Officers Safety Act)
               "child tax credit",              # 0.003 (No Child Tax Credit for Illegals Act)
               "the middle east",               # 0.038 (…Security in the Middle East Act)
               "birthright citizenship",        # 0.000 (Birthright Citizenship Act of 2025)
               "border patrol agents",
               "cuts to medicaid",
               "the west bank",
               "to release the epstein files"]:
        assert not N.is_nomenclature(ng, C), ng


def test_the_message_about_a_statute_survives_across_its_whole_family():
    """'birthright citizenship' is a 2-gram — below NGRAM_MIN, so it can never reach a verdict and its
    protection above is structural, not measured. The MEASURED claim is this: 'Birthright Citizenship
    Act' IS an indexed name, and every in-range phrase the caucus built around it still survives."""
    assert any(n == ("birthright", "citizenship", "act") for n, _c in N.load_index(C).get("birthright", ()))
    for ng in ["attack on birthright citizenship", "birthright citizenship executive order",
               "14th amendment birthright citizenship", "birthright citizenship by executive"]:
        assert not N.is_nomenclature(ng, C), ng


def test_killfixture_the_statutes_name_is_tagged_but_the_counter_brand_is_the_finding():
    """THE marquee: the R flagship's official name is nomenclature; the D counter-brand for the same
    statute is a real, invented, coordinated MESSAGE — no such statute exists. Tagging one and not the
    other is the finding. Wiring tag->suppress would delete one of them, which is why it is forbidden."""
    rows = [{"ngram": "the one big beautiful bill act", "party": "R", "day_peak": 113},
            {"ngram": "the big ugly bill", "party": "D", "day_peak": 55}]
    out = N.tag(rows, congress=C)
    assert out[0]["nomenclature"]["class"] == "official_name"   # cites BILLSTATUS hr1
    assert out[0]["nomenclature"]["cite"] == "hr1"
    assert out[1].get("nomenclature") is None                   # 0.000 — no such statute exists
    assert len(out) == 2 and out is rows                        # TAG NEVER DELETES, both parties


def test_tag_never_drops_a_row_and_needs_no_party():
    rows = [{"ngram": "the one big beautiful bill act", "congress": C},
            {"ngram": "the big ugly bill", "congress": C},
            {"ngram": "border patrol agents"},                   # no congress -> untagged, still returned
            {"ngram": ""}, {"ngram": "the one big beautiful bill act", "congress": 42}]
    out = N.tag(rows)
    assert len(out) == 5
    assert out[0]["nomenclature"]["ratio"] >= config.NOMENCLATURE_RATIO_MIN
    assert all("nomenclature" not in r for r in out[1:])         # incl. a congress with no verdicts table
    assert "party" not in inspect.signature(N.tag).parameters


# --- the index's own rules ------------------------------------------------------------------
def test_generic_subcommittee_name_requires_qualification():
    """43 of the current subcommittee names are <3 tokens ('Defense', 'Africa', 'Readiness'). Indexed
    bare they would tag ordinary English on the authority of a subcommittee's existence, so they enter
    ONLY qualified. Asserted at the index, which is where the rule lives (§DEVIATION: the docs/16 §5
    form of this test asks is_nomenclature about 'the subcommittee on aviation' — boilerplate.py:43
    suppresses every n-gram containing 'subcommittee', so no such phrase can reach a verdict)."""
    idx = N.load_index(C)
    assert not any(name == ("aviation",) for name, _cite in idx.get("aviation", ()))
    assert any(name == ("subcommittee", "on", "aviation") for name, _cite in idx.get("subcommittee", ()))
    assert not N.is_nomenclature("aviation in this country", C)


def test_official_and_display_titles_never_enter_the_index():
    """Official (6/7/10/259) and Display (45) titles are PROSE — median 25 tokens vs 6 for a short
    title. Letting either in would put 'to amend the national voter registration act of 1993' in the
    index, and the tagger would then tag ordinary policy English on the authority of a bill's
    boilerplate. Asserted at the index: no phrase of that shape survives long enough to reach a
    verdict, so is_nomenclature could not catch a leak here (§DEVIATION)."""
    idx = N.load_index(C)
    prose = [n for n, _c in idx.get("to", ()) if n[:2] in (("to", "amend"), ("to", "provide"))]
    assert prose == []
    assert not N.is_nomenclature("to amend the national voter registration act", C)
    # NOT a length bound. This assertion used to read `len(n) <= 20`, on the assumption that a short
    # title is short. Congress falsifies that: the 119 index legitimately carries 22-47 token SHORT
    # titles, verified against the raw BILLSTATUS XML. Two kinds, both real:
    #   * backronyms — "advancing critical connectivity expands service small business resources
    #     opportunities..." IS the ACCESS BROADBAND Act's short title (also ANTI-SOCIAL CCP, HOUTHI);
    #   * hres1225 registers "Original Resolution Commending the Islamic Republic of Pakistan..." under
    #     titleTypeCode 101, "Short Title(s) as Introduced" — a 22-token sentence, by the clerk's own
    #     hand.
    # Length was only ever a proxy for "no official/display-title prose". Assert the thing itself: the
    # gate is the code allowlist, and no Official (6/7/259) or Display (45/81) code may be in it. A
    # length rule would evict real statutes AND still admit a short official title.
    from pipeline import nomenclature_build as NB
    assert not ({"6", "7", "45", "81", "259"} & set(NB.TITLE_TYPE_ALLOW))
    assert all(t.startswith("short title") or t == "popular titles" for t in NB.TITLE_TYPE_PROSE_ALLOW)
    # CITATION-OR-SILENCE at the index: a name whose cite is "" would license a suppression the reader
    # cannot check. 3 such names reached the 119 index before parse_titles dropped uncitable bills.
    assert all(c for entries in idx.values() for _n, c in entries)


def test_anachronism_guard_index_is_era_scoped():
    """A 2015 phrase must never be suppressed by a 2025 bill: load_index(c) is the union of 108..c,
    so an index is a strict subset of every later one and can only ever grow forward in time."""
    early, late = N.load_index(114), N.load_index(C)
    assert 0 < len(early) < len(late)
    for tok, entries in early.items():
        assert {n for n, _ in entries} <= {n for n, _ in late[tok]}
    assert not any(n == ("one", "big", "beautiful", "bill", "act") for n, _ in early.get("one", ()))
    assert any(n == ("one", "big", "beautiful", "bill", "act") for n, _ in late.get("one", ()))


# --- Article IV + the acquisition guard -----------------------------------------------------
def test_the_tagger_cannot_read_party():
    """Article IV — symmetric instrument, asymmetric findings. The tag cites an external, party-blind
    official record; no function in the module may accept party, so an asymmetric tagger cannot be
    written here even by accident. (The rejected capitalization design failed exactly here: R press
    shops shout 54% more, so its SHOUTING-skip rule silently under-tagged one party.)"""
    assert "party" not in inspect.signature(N.is_nomenclature).parameters
    assert "party" not in inspect.signature(N.name_spans).parameters
    for name, fn in vars(N).items():
        if callable(fn) and getattr(fn, "__module__", None) == N.__name__:
            params = inspect.signature(fn).parameters
            assert not any("party" in p for p in params), f"{name} can read party"


def test_bulkdata_masked_error_is_rejected():
    """HTTP 200 + text/html 'Govinfo Bulkdata Service Error' must raise, not parse. Verified live
    2026-07-16: the directory endpoint returns 200 + text/html EVEN WITH `Accept: application/json`,
    so status is a useless signal and the Content-Type gate is the only defense."""
    from pipeline import nomenclature_build as B
    saved = B._get
    B._get = lambda url, timeout=180: (b"<html><title>Govinfo Bulkdata Service Error</title></html>",
                                       "text/html;charset=UTF-8")
    try:
        with tempfile.TemporaryDirectory() as d:
            try:
                B.fetch_billstatus(999, "hr", dest=d)
                raise AssertionError("an HTTP-200 HTML error page was accepted as bulk data")
            except RuntimeError as e:
                assert "masked bulkdata error" in str(e) and "text/html" in str(e)
            assert list(Path(d).iterdir()) == []      # nothing was written from the error page
    finally:
        B._get = saved


def test_feature_ships_dark():
    """Build dark / release by gate: the tagger is built, verified, and renders NOTHING until the flag
    flips in a commit. tag() itself must still work with the flag off — the gate is the call site."""
    assert config.FEATURES["nomenclature_tags"] is False
    assert config.feature_on("nomenclature_tags") is False
