"""S74-17 Package D (R-74.24): the duet person-span screen exempts only spans a public record
resolves (a roster member, or a bill or committee name the name index finds in the quote). Every
span read as a private individual in the S74-17 labelled set stays withheld. Flag stays off; the
quotes below are literals copied from the committed day records.
"""
from __future__ import annotations

from pipeline import site

DAY = "2026-11-19"


def test_roster_members_and_indexed_bill_names_are_resolved():
    assert site.duet_span_resolved("Senator Britt", "Senator Britt said, “One of the many pillars.", DAY)
    assert site.duet_span_resolved("Amy Klobuchar", "Senators Jacky Rosen (D-NV) and Amy Klobuchar (D-MN) "
                                   "also cosponsor the bill.", DAY)
    assert site.duet_span_resolved(
        "Ratepayer Protection Act",
        "Yesterday's passage of the Ratepayer Protection Act is a significant step forward.", DAY)


def test_private_individuals_from_the_labelled_set_stay_withheld():
    cases = [
        ("Joe Murphy", "including Joe Murphy of the Iowa Business Council who said, “This bill.”"),
        ("Edan Alexander", "the family of former hostage Edan Alexander on Edan Alexander Way in Tenafly"),
        ("Major Star", "In 2018, Major Star was diagnosed with stage 4 lung cancer linked to burn pits."),
        ("David McFerrin", "American Legion Post 47 of Filer nominated David McFerrin, who retired."),
        ("Mr. Smith", "Mr. Smith came before us, took the oath, and submitted himself to questions."),
        ("Le Huu Minh Tuan", "Representative Tran serves as the official sponsor of Le Huu Minh Tuan, a "
                             "Vietnamese journalist."),
    ]
    for span, quote in cases:
        assert not site.duet_span_resolved(span, quote, DAY), span
    # A whole quote with one resolvable and one unresolvable span is still withheld.
    cite = {"member": "Chuck Grassley", "party": "R", "date": DAY,
            "quote": "Senator Britt and Joe Murphy of the Iowa Business Council agree on the bill."}
    assert site.duet_quote_withheld(cite) == "person_span"


def test_a_quote_whose_only_held_span_is_a_member_is_shown():
    cite = {"member": "Katie Boyd Britt", "party": "R", "date": "2026-07-16",
            "quote": "We thank Senator Budd for his work on the rule of law."}
    assert site.duet_quote_withheld(cite) is None
