"""S74-15 Package 3: the Duet, made safe to show (the flag stays off).

(a) Every member label goes through the hardened label path, so the raw bioguides stored on
2026-09-24 and 2026-09-30 never render. (b) R-74.19: a quote carrying a private or quarantined person
span is withheld, and a duet left with an empty side does not render. (c) A quote attributed to
another speaker is withheld by a one-sentence rule. All at render time; day records are read at a
pinned commit (docs/37 rule 3) and never rewritten. The flag is patched on in-process only.
"""
from __future__ import annotations

import copy
import re

from pipeline import config, site
from tests._pinned import pinned_day

_BIO = re.compile(r"[A-Z]\d{6}")


def _flag_on(fn):
    prev = config.FEATURES.get("duet")
    config.FEATURES["duet"] = True
    try:
        return fn()
    finally:
        config.FEATURES["duet"] = prev


def _stored_bioguide_cites(day: dict) -> list[dict]:
    return [c for d in day.get("duets") or [] for p in ("D", "R")
            for c in (d.get("sides") or {}).get(p) or [] if _BIO.fullmatch(str(c.get("member") or ""))]


def test_the_committed_raw_bioguide_labels_never_render():
    for day_id in ("2026-09-24", "2026-09-30"):
        day = pinned_day(day_id)
        cites = _stored_bioguide_cites(day)
        assert cites, f"{day_id}: the pinned record no longer carries the defect this test covers"
        for c in cites:
            assert not _BIO.search(site.duet_member_label(c)), c["member"]
        # The whole panel, every quote shown (screens off), carries no raw bioguide either.
        unscreened = copy.deepcopy(day)
        saved = site.duet_quote_withheld
        site.duet_quote_withheld = lambda c: None
        try:
            panel = _flag_on(lambda: site.duet_panel(unscreened))
        finally:
            site.duet_quote_withheld = saved
        assert panel and not _BIO.search(re.sub(r"<[^>]+>", " ", panel)), day_id
        assert not _BIO.search(re.sub(r"<[^>]+>", " ", _flag_on(lambda: site.duet_panel(day))))


def test_a_quote_with_a_quarantined_person_span_is_withheld_and_an_empty_side_drops_the_duet():
    day = {"duets": [{"ngram": "rule of law", "counts": {"D": 9, "R": 5}, "sides": {
        "D": [{"member": "Dana Adams", "party": "D", "state": "CA", "url": "https://a.house.gov/x",
               "quote": "I thanked Joan Smithers of Springfield for the rule of law."}],
        "R": [{"member": "Rhea Rivera", "party": "R", "state": "TX", "url": "https://r.house.gov/y",
               "quote": "They undermine the rule of law."}]}}]}
    assert site.duet_quote_withheld(day["duets"][0]["sides"]["D"][0]) == "person_span"
    assert site.duet_quote_withheld(day["duets"][0]["sides"]["R"][0]) is None
    assert _flag_on(lambda: site.duet_panel(day)) == ""            # D side empty: no duet
    day["duets"][0]["sides"]["D"].append({"member": "Dana Adams", "party": "D", "state": "CA",
                                          "url": "https://a.house.gov/z",
                                          "quote": "We defend the rule of law."})
    panel = _flag_on(lambda: site.duet_panel(day))
    assert "We defend the rule of law." in panel and "Smithers" not in panel
    assert day["duets"][0]["sides"]["D"][0]["quote"].startswith("I thanked")   # record untouched


def test_the_other_speaker_rule_on_the_committed_grassley_quote_and_its_near_misses():
    """The rule, stated once in site.duet_quote_is_other_speaker. 2026-11-19: Grassley's release
    quotes Joe Murphy of the Iowa Business Council; that is not Grassley's sentence."""
    day = pinned_day("2026-11-19")
    [grassley] = [c for d in day["duets"] for p in ("D", "R") for c in d["sides"][p]
                  if "Iowa Business Council" in (c.get("quote") or "")]
    assert site.duet_quote_is_other_speaker(grassley["quote"], grassley)
    keep = [
        ("Chuck Grassley", "This matters, ” Grassley said."),
        ("Katie Boyd Britt", "Senator Britt said, “One of the many pillars of public service."),
        ("Michael F. Bennet", "He concluded by saying, “I think we should be having a debate."),
        ("Jim Banks", "The order said the country must “prepare the next generation.”"),
        ("Glenn Thompson", "to meet increasing demand,\" Rep. Thompson said."),
        ("Andrew R. Garbarino", "can keep pace,” Chairman Garbarino said."),
    ]
    for member, quote in keep:
        assert not site.duet_quote_is_other_speaker(quote, member), (member, quote)
    assert site.duet_quote_is_other_speaker("the bill is good,” President Trump said.", "Tim Moore")
    assert not site.duet_quote_is_other_speaker("Murphy said so.", "")      # no surname: not judged


def test_flag_off_renders_nothing_on_a_real_duet_day():
    day = pinned_day("2026-09-24")
    prev = config.FEATURES.get("duet")
    config.FEATURES["duet"] = False
    try:
        assert site.duet_panel(day) == ""
    finally:
        config.FEATURES["duet"] = prev
