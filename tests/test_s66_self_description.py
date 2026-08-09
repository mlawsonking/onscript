"""S66-4 acceptance: the instrument describes itself accurately (Constitution Article XVII).

docs/39 M3 and M2. Two public statements had drifted from the running system.

The homepage honesty note said a deterministic line was "a placeholder until the live model
voice is wired in" while the SAME page showed the other party's line carrying generator
sonnet_direct and generated_verified. LLM_VOICE_ENABLED has been true since 2026-07-14, so a
deterministic composite is now a per-day outcome of the verifier, not an unbuilt feature. The
old wording told a reader the instrument was less finished than it is, and it explained a real
asymmetry between the two parties' lines with a false cause.

The methodology described Lane 2 in the present tense while the corpus is 100 percent Lane 1.
That is the good outcome for symmetry and it deserves saying plainly.

Both strings live in public_strings and are read live by their renderers (docs/37 rule 1), so
a wording review has one surface and a stale copy cannot survive in a template.
"""
from __future__ import annotations

from pipeline import public_strings, site


HONESTY = (
    "Honesty note: when a day's verified claims cannot support a model-written composite, that "
    "party's line is composed deterministically from the day's measured statistics. The numbers, "
    "quotes, and receipts are always real and verified; only the connective phrasing differs. "
    "Each line states its own generator, so the two parties can legitimately differ on the same day."
)
LANE_TWO = (
    "Lane 2 is not currently populated: every citation on this site today is Lane 1, a press "
    "release from an official office."
)


def _stub_day() -> dict:
    """A day where one party's line is deterministic and the other's is a verified model line."""
    return {"daily_lines": {
        "D": {"generator": "deterministic", "text": "..."},
        "R": {"generator": "sonnet_direct", "model": "claude-sonnet-5",
              "verifier": {"checked": True, "passed": True}, "text": "..."},
    }}


# --- the strings themselves ------------------------------------------------------------------

def test_the_two_strings_are_verbatim_and_carry_no_em_dash():
    assert public_strings.HOMEPAGE_HONESTY_NOTE == HONESTY
    assert public_strings.LANE_TWO_POPULATION_NOTE == LANE_TWO
    for value in (HONESTY, LANE_TWO):
        # docs/25 forbids U+2014 in authored prose. Written as an escape so this detector is not
        # itself the one em dash in the delivery.
        assert chr(0x2014) not in value


def test_both_strings_stay_plain_text_because_their_renderers_emit_them_raw():
    """They render unescaped so the reviewed wording survives verbatim in the page source."""
    for value in (public_strings.HOMEPAGE_HONESTY_NOTE, public_strings.LANE_TWO_POPULATION_NOTE):
        assert "<" not in value and ">" not in value and "&" not in value


def test_the_retired_claim_is_gone_from_every_public_string_and_renderer():
    from pathlib import Path
    source = Path(site.__file__).read_text(encoding="utf-8")
    rendered_lines = [line for line in source.splitlines()
                      if "wired in" in line and not line.lstrip().startswith("#")]
    assert not rendered_lines, rendered_lines
    banner = site.banner_html(_stub_day(), {}, depth=0)
    assert "placeholder" not in banner
    assert "wired in" not in banner


# --- read live by their renderers -------------------------------------------------------------

def test_the_homepage_banner_reads_the_honesty_note_live():
    saved = public_strings.HOMEPAGE_HONESTY_NOTE
    try:
        assert HONESTY in site.banner_html(_stub_day(), {}, depth=0)
        public_strings.HOMEPAGE_HONESTY_NOTE = "PROBE-HONESTY-NOTE-ZZZ"
        assert "PROBE-HONESTY-NOTE-ZZZ" in site.banner_html(_stub_day(), {}, depth=0)
    finally:
        public_strings.HOMEPAGE_HONESTY_NOTE = saved


def test_the_methodology_reads_the_lane_two_note_live():
    saved = public_strings.LANE_TWO_POPULATION_NOTE
    try:
        assert LANE_TWO in site.methodology_body()
        public_strings.LANE_TWO_POPULATION_NOTE = "PROBE-LANE-TWO-ZZZ"
        assert "PROBE-LANE-TWO-ZZZ" in site.methodology_body()
    finally:
        public_strings.LANE_TWO_POPULATION_NOTE = saved


def test_the_lane_two_note_sits_with_the_lane_two_description():
    body = site.methodology_body()
    assert body.index("Bluesky") < body.index("Lane 2 is not currently populated")
    assert body.index("Lane 2 is not currently populated") < body.index("What OnScript measures")


def test_the_banner_still_discloses_the_days_own_flags():
    """The new wording replaces a false cause, never the per-day disclosure."""
    day = _stub_day()
    day["daily_lines"]["D"]["quiet"] = True
    banner = site.banner_html(day, {}, depth=0)
    assert HONESTY in banner
    assert "quiet-day" in banner
    assert "Democrats" in banner


def test_a_verified_model_day_with_a_flag_keeps_the_transparency_wording():
    day = {"daily_lines": {"D": {"generator": "sonnet_direct", "fallback": True},
                           "R": {"generator": "sonnet_direct"}}}
    banner = site.banner_html(day, {}, depth=0)
    assert "transparency flag" in banner
    assert HONESTY not in banner
