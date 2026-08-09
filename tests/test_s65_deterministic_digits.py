"""S65 P1 - the deterministic composite may only emit digits its own verifier whitelists.

Incident: on 2026-08-03 the Democratic composite was withheld with
``un-whitelisted numbers in composite: ['5']`` while four talking points published.
The deterministic template rendered the W2 claim contract's three unit counts
(offices, publications, families), but verify.code_allowed_numbers admits only the
support count, the day statement count, the coordination threshold, the audited date,
and digits inside a selected phrase name. Whenever the three counts disagreed, the
template emitted a digit its own verifier rejected and the day lost its composite.
Four committed party-days hit it: 2026-07-27, 07-29, 07-30, and 08-03, all Democratic.

The fix is in the template. The verifier is unchanged and still fails closed.

docs/37 rule 2: the sweep below runs against every committed day artifact.
docs/37 rule 3: the defect itself is documented in frozen literals here, never asserted
against the mutable day files, so a production rebuild that heals a day cannot fail
this suite. The live tree is only ever asserted to hold the healed invariant.
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline import config, distill, site, verify

ROOT = Path(__file__).resolve().parent.parent
DAYS = ROOT / "data" / "derived" / "days"

# Frozen 2026-08-03 Democratic shape: publications (5) disagrees with the support count (4),
# which is what the whitelist admits. Literal, so the incident stays reproducible after any
# rebuild of the day file.
INCIDENT_PHRASE = "the devastating wildfires sweeping"
INCIDENT_STATS = {
    "schema_version": 2,
    "party": "D",
    "day": "2026-08-03",
    "statements": 74,
    "talking_points": [{
        "label": INCIDENT_PHRASE,
        "members": 4,
        "quote": INCIDENT_PHRASE,
        "claim_id": "2026-08-03-D-00",
        "claim_type": "phrase_claim",
        "object_type": "phrase_claim",
        "surface_class": "message",
        "counts": {"offices": 4, "publications": 5, "families": 4, "support_units": 4},
    }],
    "selected_claims": [{
        "label": INCIDENT_PHRASE,
        "members": 4,
        "quote": INCIDENT_PHRASE,
        "claim_id": "2026-08-03-D-00",
        "claim_type": "phrase_claim",
        "object_type": "phrase_claim",
        "surface_class": "message",
        "counts": {"offices": 4, "publications": 5, "families": 4, "support_units": 4},
    }],
    "top_phrase": None,
    "claim_ids": ["2026-08-03-D-00"],
    "sync_min": 3,
}


def _verify(composite: str, stats: dict) -> tuple[bool, list[str]]:
    return verify.verify_daily_line(
        {"composite": composite}, json.dumps(stats, ensure_ascii=False), stats=stats
    )


def _unwhitelisted(composite: str, stats: dict) -> set[str]:
    return verify._numbers_outside_quotes(composite) - verify.code_allowed_numbers(stats)


def test_the_withdrawn_sentence_form_is_the_one_that_failed():
    """Teeth: the pre-fix sentence really is rejected on the incident shape."""
    claim = INCIDENT_STATS["selected_claims"][0]
    counts = claim["counts"]
    old_form = (
        f'Today {INCIDENT_STATS["statements"]} of us released statements. '
        f'{counts["offices"]} offices across {counts["publications"]} publications and '
        f'{counts["families"]} families carried "{claim["quote"]}".'
    )
    assert _unwhitelisted(old_form, INCIDENT_STATS) == {"5"}
    ok, reasons = _verify(old_form, INCIDENT_STATS)
    assert not ok
    assert any("un-whitelisted numbers" in reason and "'5'" in reason for reason in reasons)


def test_the_incident_day_now_composes_and_verifies():
    composite = distill._compose_dry(INCIDENT_STATS)
    assert _unwhitelisted(composite, INCIDENT_STATS) == set()
    ok, reasons = _verify(composite, INCIDENT_STATS)
    assert ok, reasons
    assert f'4 of us carried "{INCIDENT_PHRASE}".' in composite
    assert distill.register_violations(composite) == []


def test_no_count_combination_can_emit_an_unwhitelisted_digit():
    """The template is exercised across divergent unit counts, not just the ones seen."""
    checked = 0
    for offices in (1, 4, 17, 233):
        for publications in (1, 5, 18, 991):
            for families in (2, 4, 19):
                stats = json.loads(json.dumps(INCIDENT_STATS))
                counts = {"offices": offices, "publications": publications,
                          "families": families, "support_units": 4}
                stats["talking_points"][0]["counts"] = counts
                stats["selected_claims"][0]["counts"] = counts
                composite = distill._compose_dry(stats)
                assert _unwhitelisted(composite, stats) == set(), (counts, composite)
                ok, reasons = _verify(composite, stats)
                assert ok, (counts, reasons)
                checked += 1
    assert checked == 48


def test_legacy_stats_without_sync_min_state_the_absence_without_a_bare_threshold():
    """A STATS block with no sync_min does not whitelist the threshold.

    Six committed party-days (2026-06-30, 07-11, 07-12) carry such STATS and reach this
    template through the site recompose path, so the absence line must not print
    config.SYNC_MIN_MEMBERS as a bare digit.
    """
    legacy = {"party": "D", "day": "2026-07-11", "statements": 91,
              "talking_points": [], "top_phrase": None}
    assert "sync_min" not in legacy
    composite = distill._compose_dry(legacy)
    assert str(config.SYNC_MIN_MEMBERS) not in composite
    assert _unwhitelisted(composite, legacy) == set()
    ok, reasons = _verify(composite, legacy)
    assert ok, reasons
    assert "No phrase was shared" in composite          # still the measured-absence finding

    modern = dict(legacy, sync_min=config.SYNC_MIN_MEMBERS)
    modern_composite = distill._compose_dry(modern)
    assert f"shared by {config.SYNC_MIN_MEMBERS} or more of us" in modern_composite
    assert _verify(modern_composite, modern)[0]


def test_no_committed_day_makes_the_template_emit_an_unwhitelisted_digit():
    """docs/37 rule 2, run against real committed artifacts rather than fixtures alone.

    The assertion is the healed invariant (rule 3): whatever each day's STATS say, the
    deterministic template must not state a number its own verifier rejects. Nothing here
    pins a stored composite, so a rebuilt or re-rendered day cannot break it.

    Scope note. Twelve pre-docs/28 party-days still fail the separate quote-binding check
    when recomposed from their stored STATS, identically before and after this fix. That
    condition is not asserted away here, so this test stays specific to the digit rule.
    """
    day_files = sorted(DAYS.glob("*.json"))
    assert len(day_files) >= 20, f"expected the committed day corpus, found {len(day_files)}"
    checked = divergent = 0
    offenders = []
    for path in day_files:
        day = json.loads(path.read_text(encoding="utf-8"))
        for party, line in (day.get("daily_lines") or {}).items():
            stats = (line or {}).get("stats")
            if not isinstance(stats, dict) or stats.get("statements") is None:
                continue
            composite = (distill._quiet_dry(stats) if line.get("quiet")
                         else distill._compose_dry(stats))
            leaked = _unwhitelisted(composite, stats)
            _ok, reasons = _verify(composite, stats)
            number_reasons = [r for r in reasons if "un-whitelisted numbers" in r]
            if leaked or number_reasons:
                offenders.append((day.get("day"), party, sorted(leaked), number_reasons))
            for claim in (stats.get("selected_claims")
                          or stats.get("talking_points") or []):
                counts = (claim or {}).get("counts") or {}
                if any(counts.get(key) != claim.get("members")
                       for key in ("offices", "publications", "families")
                       if isinstance(counts.get(key), int)):
                    divergent += 1
            checked += 1
    assert not offenders, offenders
    assert checked >= 40, f"only {checked} party-days exercised"
    # Unit counts are measurement outputs, not template outputs, so the committed days that
    # made the incident possible keep their divergent counts across any re-render. If this
    # ever reads zero the sweep has lost its teeth and needs a new corpus, not a lower bar.
    assert divergent >= 1, "no committed claim has unit counts that disagree with its support count"


def test_the_three_labeled_unit_counts_stay_on_the_day_page():
    """The composite no longer states offices, publications, and families, so the day page
    receipts are now their only public carrier. Guard that carrier against a silent loss."""
    day = json.loads((DAYS / "2026-08-03.json").read_text(encoding="utf-8"))
    published = [row for row in (day.get("talking_points") or {}).get("D") or []
                 if isinstance((row or {}).get("counts"), dict)]
    assert published, "the 2026-08-03 Democratic claims should carry unit counts"
    html = site.receipts_strip("D", published)
    counts = published[0]["counts"]
    assert f'{counts["offices"]} offices' in html
    assert f'{counts["publications"]} publications' in html
    assert f'{counts["families"]} families' in html
