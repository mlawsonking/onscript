"""S65 P3 - the volume alert compares a focus day only after it has stopped landing.

Incident: the morning RUN A on 2026-08-08 counted 2 lane-1 statements for its focus day
against a trailing median of 138.5 and paged for anomalously low volume. The same day
assembled 192 statements once upstream finished delivering. The alert was measuring the
clock, not the corpus, and it did so every morning, which is how an alert stops being read.

The gate takes both of its arms from pipeline.readiness, so the alert and the publication
path agree on when a day has stopped filling: a day is mature once it clears the readiness
ratio, or once it is MAX_WAIT_DAYS old and the readiness gate has stopped waiting for it.

Both paths have fixtures below. An immature day is logged and not paged. A day that aged
out of the wait and is still thin pages, because that one is real.
"""
from __future__ import annotations

import inspect
import json
from datetime import date, timedelta
from pathlib import Path

from pipeline import config, ops, readiness, run_collect

ROOT = Path(__file__).resolve().parents[1]

WEEKDAY_BASELINE = 140      # a normal lane-1 weekday in the fixtures below


def _corpus(counts: dict[str, int]) -> list[dict]:
    """Lane-1 statements, `count` of them on each named day."""
    return [{"published_at": day, "lane": 1} for day, count in counts.items()
            for _ in range(count)]


def _trailing(through: str, days: int = 42, count: int = WEEKDAY_BASELINE) -> dict[str, int]:
    """`days` consecutive full days ending the day before `through`."""
    end = date.fromisoformat(through)
    return {(end - timedelta(days=k)).isoformat(): count for k in range(1, days + 1)}


# The focus day and two reference days: the morning of the focus day itself, and three days
# later, past the readiness wait. Both are Wednesdays' worth of ordinary weekday history.
FOCUS = "2026-08-07"
MORNING_AFTER = "2026-08-08"        # age 1 day, inside the readiness wait
PAST_THE_WAIT = "2026-08-10"        # age 3 days, past MAX_WAIT_DAYS


def test_the_readiness_wait_is_the_source_of_the_second_arm():
    assert readiness.MAX_WAIT_DAYS == 2
    focus = date.fromisoformat(FOCUS)
    assert (date.fromisoformat(MORNING_AFTER) - focus).days < readiness.MAX_WAIT_DAYS
    assert (date.fromisoformat(PAST_THE_WAIT) - focus).days >= readiness.MAX_WAIT_DAYS


def test_a_partly_landed_focus_day_is_immature_and_is_not_paged():
    """The 2026-08-08 incident: 2 statements so far against a trailing median of 140."""
    statements = _corpus({**_trailing(FOCUS), FOCUS: 2})
    maturity = ops.collection_maturity(statements, FOCUS, reference_day=MORNING_AFTER)
    assert maturity["mature"] is False
    assert maturity["ready"] is False
    assert maturity["age_days"] == 1
    assert "still landing" in maturity["reason"]

    volume = ops.volume_anomaly(statements, FOCUS, maturity=maturity)
    assert volume["anomalously_low"] is False           # no page
    assert volume["comparison"] == "withheld"
    assert volume["collection_mature"] is False
    # The measurement is still published, so a withheld comparison is not a healthy one.
    assert volume["today"] == 2
    assert volume["baseline"] == WEEKDAY_BASELINE
    assert volume["maturity_reason"] == maturity["reason"]

    # Ungated, this is exactly the false page the gate removes.
    assert ops.volume_anomaly(statements, FOCUS)["anomalously_low"] is True


def test_a_day_that_aged_out_of_the_wait_and_stayed_thin_is_still_paged():
    """The genuinely dead day. Upstream had three days and delivered two statements."""
    statements = _corpus({**_trailing(FOCUS), FOCUS: 2})
    maturity = ops.collection_maturity(statements, FOCUS, reference_day=PAST_THE_WAIT)
    assert maturity["mature"] is True
    assert maturity["ready"] is False
    assert maturity["age_days"] == 3
    assert "not still landing" in maturity["reason"]

    volume = ops.volume_anomaly(statements, FOCUS, maturity=maturity)
    assert volume["anomalously_low"] is True            # the page fires
    assert volume["comparison"] == "judged"
    assert volume["today"] == 2


def test_a_focus_day_that_finished_landing_is_judged_on_the_morning_run():
    """Maturity does not wait when the day is already in. A full day is judged at once."""
    statements = _corpus({**_trailing(FOCUS), FOCUS: WEEKDAY_BASELINE})
    maturity = ops.collection_maturity(statements, FOCUS, reference_day=MORNING_AFTER)
    assert maturity["mature"] is True
    assert maturity["ready"] is True
    assert maturity["reason"] == "the focus day cleared the readiness gate"
    volume = ops.volume_anomaly(statements, FOCUS, maturity=maturity)
    assert volume["anomalously_low"] is False
    assert volume["comparison"] == "judged"


def test_a_saturday_holding_a_normal_saturday_volume_is_not_paged():
    """S70 replaces the arm this fixture used to prove.

    Until S70 this same fixture asserted a PAGE, because the alert compared 15 statements with a
    trailing ALL-DAYS median of 140 while the maturity arm compared them with a Saturday median of
    20. A Saturday holding three quarters of its own Saturday norm is not an incident; measuring it
    against Tuesdays is what made it look like one. Both arms now read one baseline, so the day is
    mature AND quiet.
    """
    saturdays = {"2026-07-04": 20, "2026-07-11": 20, "2026-07-18": 20, "2026-07-25": 20}
    statements = _corpus({**_trailing("2026-08-01"), **saturdays, "2026-08-01": 15})
    maturity = ops.collection_maturity(statements, "2026-08-01", reference_day="2026-08-02")
    assert maturity["ready"] is True
    assert maturity["mature"] is True
    volume = ops.volume_anomaly(statements, "2026-08-01", maturity=maturity)
    assert volume["baseline"] == 20                     # Saturdays, not the 140 weekday median
    assert volume["today"] >= config.NULL_SERVICE_VOLUME_RATIO * volume["baseline"]
    assert volume["anomalously_low"] is False
    assert volume["comparison"] == "judged"


def test_a_saturday_that_collapsed_against_its_OWN_saturdays_is_paged_and_held():
    """The quiet arm is not a mute button. Same fixture, same weekday, a real collapse.

    On the morning after, S65 still withholds: 2 statements at age 1 is a day that may yet land.
    Once it has aged past the readiness wait, the same two arms agree from the same baseline that
    the day is dead: the alert pages and the gate refuses to call it ready.
    """
    saturdays = {"2026-07-04": 20, "2026-07-11": 20, "2026-07-18": 20, "2026-07-25": 20}
    statements = _corpus({**_trailing("2026-08-01"), **saturdays, "2026-08-01": 2})
    morning = ops.collection_maturity(statements, "2026-08-01", reference_day="2026-08-02")
    assert ops.volume_anomaly(statements, "2026-08-01",
                              maturity=morning)["comparison"] == "withheld"

    aged = ops.collection_maturity(statements, "2026-08-01", reference_day="2026-08-04")
    assert aged["mature"] is True and aged["ready"] is False
    volume = ops.volume_anomaly(statements, "2026-08-01", maturity=aged)
    assert volume["baseline"] == 20                     # Saturdays, not the 140 weekday median
    assert volume["today"] < config.NULL_SERVICE_VOLUME_RATIO * volume["baseline"]
    assert volume["anomalously_low"] is True            # the page fires
    assert volume["comparison"] == "judged"


def test_without_a_reference_day_only_the_ready_arm_can_be_evaluated():
    statements = _corpus({**_trailing(FOCUS), FOCUS: 2})
    maturity = ops.collection_maturity(statements, FOCUS)
    assert maturity["age_days"] is None
    assert maturity["mature"] is False
    assert ops.collection_maturity(
        _corpus({**_trailing(FOCUS), FOCUS: WEEKDAY_BASELINE}), FOCUS)["mature"] is True


def test_a_day_with_no_same_weekday_history_is_mature_and_never_blocks():
    """readiness treats absent history as ready rather than blocking. The alert inherits
    that, so a new corpus or a new era keeps its dead-man rather than going quiet.

    S70 moved which arm carries that dead-man. There is no ratio to apply without a same-weekday
    baseline, so the ratio is withheld and the ABSOLUTE arm answers instead: a matured day holding
    nothing pages whatever the baseline says. The old fixture used one statement and relied on the
    all-days median that no longer exists.
    """
    statements = _corpus({"2026-08-05": 100, "2026-08-06": 100, FOCUS: 1})
    maturity = ops.collection_maturity(statements, FOCUS, reference_day=MORNING_AFTER)
    assert maturity["same_weekday_baseline"] == 0.0
    assert maturity["ready"] is True
    assert maturity["mature"] is True
    withheld = ops.volume_anomaly(statements, FOCUS, maturity=maturity)
    assert withheld["judgeable"] is False and withheld["comparison"] == "withheld"
    assert withheld["anomalously_low"] is False

    dead = _corpus({"2026-08-05": 100, "2026-08-06": 100})           # FOCUS holds nothing at all
    dead_maturity = ops.collection_maturity(dead, FOCUS, reference_day=MORNING_AFTER)
    assert dead_maturity["mature"] is True
    assert ops.volume_anomaly(dead, FOCUS, maturity=dead_maturity)["anomalously_low"] is True


def test_the_default_call_judges_the_day_so_assemble_is_unchanged():
    """The assemble caller passes no maturity: a day it publishes has cleared the readiness
    gate or been force-finalized past it. Gating there would flip anomalously_low_volume to
    False on exactly the thin force-finalized days the no-post rule holds for."""
    statements = _corpus({**_trailing(FOCUS), FOCUS: 2})
    assert ops.volume_anomaly(statements, FOCUS) == {
        "today": 2, "baseline": float(WEEKDAY_BASELINE),
        "baseline_method": f"trailing {readiness.BASELINE_WEEKS}-week same-weekday median",
        "judgeable": True, "anomalously_low": True,
    }
    assert "anomalously_low_volume" in config.NULL_SERVICE_CONDITIONS
    # The contract that makes the assemble call site ungated: maturity is keyword-only and
    # defaults to None, so a positional two-argument call cannot accidentally acquire a gate.
    parameter = inspect.signature(ops.volume_anomaly).parameters["maturity"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is None


def _committed_day_counts() -> dict[str, int]:
    """Statements per day from the committed day records, D plus R.

    A proxy for the ledger's lane-1 count per day, and a real one: these are the counts the
    days actually assembled from. Used as production-shaped input, never asserted equal to a
    fresh build (docs/37 rules 2 and 3).
    """
    counts = {}
    for path in sorted((ROOT / "data" / "derived" / "days").glob("*.json")):
        day = json.loads(path.read_text(encoding="utf-8"))
        total = 0
        for line in (day.get("daily_lines") or {}).values():
            statements = ((line or {}).get("stats") or {}).get("statements")
            if isinstance(statements, int):
                total += statements
        counts[day["day"]] = total
    return counts


def test_the_real_2026_08_06_incident_withholds_while_partial_and_judges_when_full():
    """Both arms against real committed artifacts.

    collect-2026-08-06.json recorded volume.today 2 against a trailing median of 138.5 and
    paged. The committed day record for the same day holds the count it actually assembled.
    The partial count is a frozen literal so a re-collect cannot erase the incident; the full
    count is read live, because that is the healed side.
    """
    counts = _committed_day_counts()
    incident_day = "2026-08-06"
    assert incident_day in counts, "the committed day corpus should still hold the incident day"
    full = counts[incident_day]
    assert full > 100, f"expected an ordinary weekday, found {full}"

    partial = 2                      # frozen: what RUN A saw that morning
    morning = "2026-08-07"
    partial_corpus = _corpus({**counts, incident_day: partial})
    partial_maturity = ops.collection_maturity(partial_corpus, incident_day,
                                               reference_day=morning)
    assert partial_maturity["mature"] is False
    partial_volume = ops.volume_anomaly(partial_corpus, incident_day,
                                        maturity=partial_maturity)
    assert partial_volume["today"] == partial
    assert partial_volume["anomalously_low"] is False       # the page that should not have fired
    assert partial_volume["comparison"] == "withheld"
    # Ungated on the same real corpus, this is the alert the operator actually received.
    assert ops.volume_anomaly(partial_corpus, incident_day)["anomalously_low"] is True

    full_corpus = _corpus(counts)
    full_maturity = ops.collection_maturity(full_corpus, incident_day, reference_day=morning)
    assert full_maturity["ready"] is True
    assert full_maturity["mature"] is True
    full_volume = ops.volume_anomaly(full_corpus, incident_day, maturity=full_maturity)
    assert full_volume["today"] == full
    assert full_volume["anomalously_low"] is False          # an ordinary day, correctly quiet


def test_a_focus_day_ahead_of_the_reference_day_is_never_waited_out():
    """RUN A can meet a focus day that is still in progress, so age can be zero or negative.
    Neither is past the readiness wait."""
    counts = _committed_day_counts()
    today = max(counts)
    corpus = _corpus({**counts, today: 2})
    maturity = ops.collection_maturity(corpus, today, reference_day=FOCUS)
    assert maturity["age_days"] is not None and maturity["age_days"] < readiness.MAX_WAIT_DAYS
    assert maturity["mature"] is (maturity["ready"] is True)


def test_collect_and_ops_stay_one_definition():
    """docs/37 rule 12 and the Y4 contract: the two callers cannot diverge."""
    statements = _corpus({**_trailing(FOCUS), FOCUS: 2})
    maturity = ops.collection_maturity(statements, FOCUS, reference_day=MORNING_AFTER)
    assert (run_collect._volume_anomaly(statements, FOCUS, maturity=maturity)
            == ops.volume_anomaly(statements, FOCUS, maturity=maturity))
    assert run_collect._volume_anomaly(statements, FOCUS) == ops.volume_anomaly(statements, FOCUS)
