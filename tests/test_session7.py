"""Session-7 pre-launch punch list: cluster-label quality gate, quote-to-source binding, the daily
ranking's content weighting, and the P2/P3 v1.1 fourth-wall rules. All $0."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import boilerplate, build, llm, run_assemble, site  # noqa: E402


# --- C-i: the weak-label gate ------------------------------------------------------------
def test_is_weak_label_catches_connective_glue_keeps_real_phrases():
    # Glue = conjunction-led AND possessive-trailing (a mid-sentence fragment), or low-content.
    for weak in ("and the trump administration's", "but the president's", "of the"):
        assert boilerplate.is_weak_label(weak) is True, weak
    # Real conjunction-led phrases end in a content noun — must be KEPT (over-suppression guard).
    for good in ("21st century road to housing", "born in the united states",
                 "federal financial assistance", "and civil rights",
                 "and republicans in congress", "and transparent investigation into the killing"):
        assert boilerplate.is_weak_label(good) is False, good


# --- C-ii: each citation carries its own member's verbatim quote --------------------------
def test_citations_bind_each_quote_to_its_member():
    tp = {"statements": ["s1", "s2", "s3"],
          "fragments": [{"statement": "s1", "text": "we support border security now"},
                        {"statement": "s2", "text": "secure the border today"},
                        {"statement": "s3", "text": "protect our borders"}]}
    stmt_by_id = {
        "s1": {"member": {"bioguide": "B1", "party": "D", "state": "CA"}, "published_at": "2026-07-13", "url": "https://b1.house.gov/x"},
        "s2": {"member": {"bioguide": "B2", "party": "D", "state": "NY"}, "published_at": "2026-07-13", "url": "https://b2.house.gov/y"},
        "s3": {"member": {"bioguide": "B3", "party": "D", "state": "TX"}, "published_at": "2026-07-13", "url": "https://b3.house.gov/z"},
    }
    cites = run_assemble._citations(tp, stmt_by_id, {}, k=3)
    assert len(cites) == 3 and all(c.get("quote") for c in cites)
    by_url = {c["url"]: c["quote"] for c in cites}
    assert by_url["https://b1.house.gov/x"] == "we support border security now"   # each member's OWN quote
    assert by_url["https://b2.house.gov/y"] == "secure the border today"


def test_receipts_fall_back_to_fragments_when_no_citations():
    """#7: historical days have talking points with fragments but NO citations — receipts must still
    show the verbatim quotes rather than render empty (the site-wide citation promise must hold)."""
    tps = [{"member_count": 53, "topics": ["immigration"],
            "fragments": [{"text": "born in the united states"}, {"text": "birthright citizenship"}]}]
    html = site.receipts_strip("D", tps)
    assert "born in the united states" in html   # fragment quote shown even with no citations key
    assert "53 members" in html


def test_receipts_strip_shows_bound_quote_and_count_cue():
    tps = [{"member_count": 10, "topics": ["housing"],
            "citations": [{"member": "Jane Doe", "party": "D", "state": "CA", "date": "2026-07-13",
                           "url": "https://doe.house.gov/x", "quote": "support the housing act"}]}]
    html = site.receipts_strip("D", tps)
    assert "support the housing act" in html               # the quote is shown...
    assert 'href="https://doe.house.gov/x"' in html         # ...next to that member's link
    assert "Jane Doe" in html
    assert "showing 1 of 10 members" in html                # the "N of M" honesty cue


# --- C-iii: content-richness breaks peak ties (generic phrases sink) ----------------------
def test_daily_ranking_demotes_generic_phrase_of_equal_peak():
    def entry(peak):
        return {"daily": {"2026-07-13": {"D": peak, "members_D": [f"m{i}" for i in range(peak)]}},
                "n": 200, "first_seen": {"date": "2025-01-02", "bioguide": "X"}, "df_weight": 0.9}
    ledger = {"an important step": entry(5), "federal financial assistance": entry(5)}
    ngrams = [r["ngram"] for r in build.top_synchronized(ledger, "2026-07-13", k=10)]
    assert ngrams.index("federal financial assistance") < ngrams.index("an important step")
    # every row now carries its own 14-day series for a sparkline
    rows = build.top_synchronized(ledger, "2026-07-13", k=10)
    assert all("series" in r for r in rows)


# --- B: the P2/P3 v1.1 prompts forbid fourth-wall leaks -----------------------------------
def test_prompts_are_v1_1_with_fourth_wall_rules():
    for pid in ("P2", "P3"):
        p = llm.load_prompt(pid)
        assert p["version"] == "1.1", pid
        sysl = p["system"].lower()
        assert "null" in sysl and "cluster" in sysl  # they are NAMED as forbidden words
        assert "must not appear" in sysl             # the fourth-wall rule is present
    # P2 also carries the numerals-only rule (so no number escapes the digit whitelist) + the
    # party-tagged first-sayer rule
    p2 = llm.load_prompt("P2")["system"].lower()
    assert "every specific number as a numeral" in p2 and "party, and state" in p2
