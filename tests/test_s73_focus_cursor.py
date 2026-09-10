"""S73: the day cursor is monotonic, never runs ahead of the calendar, and heals its own holes.

THE INCIDENT. RUN A focused `days_present[-1]`, the newest day in the corpus. The congress-press
mirror pushes each morning, so by the evening collect a few statements dated the RUN's own day had
usually landed and the cursor followed them. That skipped whatever day sat between: 2026-09-08,
Congress's first day back from recess, was never written and no later run would ever have written
it, because collect only ever wrote its one focus day. Every workflow run was GREEN throughout. The
same cursor also produced the tell nobody could act on, a collection-maturity line reading
"upstream is still landing the focus day, -1 days old".

WHAT THESE LOCK, in the order the fix applies:
  1. the resolver (`readiness.resolve_focus_day`) never points at a day that is not over, replayed
     against every collect manifest the repository actually holds;
  2. the sweep (`deterministic._sweep_unwritten_days`) writes every judgeable day in the lookback
     window, so a day whose data lands between two runs is still written, and so 2026-09-08 heals
     on the first run after deploy with no operator step;
  3. the sweep's four guards, because a repair that overwrites a published day is worse than the
     hole it fills;
  4. a negative age is unreachable, on the derived path by construction and on every other path by
     flooring.

docs/37 rule 2: the replay in section 1 runs on the real committed manifests, not on fixtures. It
asserts the HEALED invariant against them rather than asserting they stay defective (rule 3), so it
keeps passing as production advances and new manifests land.
"""
import contextlib
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import build, config, deterministic, ops, readiness, util  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
MANIFEST_DIR = REPO / "data" / "derived" / "manifest"
DAYS_DIR = REPO / "data" / "derived" / "days"

# The day the incident orphaned, and the run that stepped over it.
ORPHANED_DAY = "2026-09-08"
ORPHANING_RUN = "collect-2026-09-09"

# Five consecutive days, which is what it takes for a shared phrase carried by four members to sit
# under the boilerplate document-frequency cut. A shorter corpus builds an EMPTY ledger, and a test
# written against one would pass whether or not late data ever reached the page.
_SEED = ["2026-09-04", "2026-09-05", "2026-09-06", "2026-09-07", "2026-09-08"]


# --- helpers -------------------------------------------------------------------------------------
def _real_collect_manifests() -> list[dict]:
    """Every committed collect manifest that carries the two fields the replay needs."""
    out = []
    for p in sorted(MANIFEST_DIR.glob("collect-2*.json")):
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if m.get("generated_at") and m.get("days_present") and m.get("focus_day"):
            out.append({"run": p.stem, **m})
    return out


def _product_day_of(generated_at: str) -> str:
    """The product day a run generated at this instant would have computed."""
    ts = datetime.strptime(generated_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return util.product_day(ts)


def _between(a: str, b: str) -> list[str]:
    """Calendar days strictly between two ISO dates."""
    d0, d1 = datetime.fromisoformat(a).date(), datetime.fromisoformat(b).date()
    return [(d0 + timedelta(days=i)).isoformat() for i in range(1, (d1 - d0).days)]


def _skipped_by_production() -> set:
    """Days the production cursor vaulted over, read off the committed collect manifests.

    Derived rather than listed, so it stays correct as manifests accumulate and so no test here
    carries a hand-maintained allowlist of dates.
    """
    skipped, high = set(), None
    for m in _real_collect_manifests():
        focus = m["focus_day"]
        if high and focus > high:
            skipped.update(_between(high, focus))
        high = focus if (high is None or focus > high) else high
    return skipped


# A corpus that behaves like the real one rather than like a fixture, because the phrase engine's
# boilerplate cut is a DOCUMENT-FREQUENCY share within (congress, party): a phrase carried by four
# members of a six-document corpus is 67 percent of that party and is discarded as a template. Only a
# corpus wide enough to put four carriers under BOILERPLATE_DF_SHARE_MAX produces a ledger at all, so
# these tests would have asserted "the day was written empty" against every day, including the ones
# that work. Twenty non-carrying members per party per day put each shared phrase near 3 percent.
_WORDS = ("alder birch cedar dogwood elm fir ginkgo hawthorn ironwood juniper laurel maple nutmeg "
          "oak poplar quince redwood spruce teak vine walnut yew zelkova basalt").split()

# One phrase per party per day, so a phrase's document frequency does not accumulate across the
# window and quietly cross the boilerplate cut as the fixture grows.
_SHARED = {
    "2026-09-04": ("hold drug makers to their promises", "audit every federal grant program"),
    "2026-09-05": ("cap insulin at thirty five dollars", "repeal the estate tax on family farms"),
    "2026-09-06": ("restore the monthly child care credit", "fund the new border patrol academy"),
    "2026-09-07": ("protect rural hospital emergency rooms", "cut permitting delays for new pipelines"),
    "2026-09-08": ("lower prescription drug costs for seniors", "stop the war on domestic energy"),
    "2026-09-09": ("expand rural broadband to every county", "end the catch and release policy"),
}


def _body(i, j):
    """A sentence unlike every other one, so the near-duplicate collapse keeps these as four units."""
    w = _WORDS
    return (f"The {w[i % 24]} subcommittee toured a {w[(i * 3 + j) % 24]} facility and asked the "
            f"{w[(i * 5 + j * 2) % 24]} office for a {w[(i * 7 + j * 3) % 24]} briefing before "
            f"{w[(i * 11 + j) % 24]} season.")


def _rec(bio, party, day, body, tail=""):
    return {"url": f"https://{bio}.house.gov/{day}/{abs(hash(body)) % 999999}", "title": "Statement",
            "text": f"{body} {tail}".strip(), "date": day,
            "member": {"bioguide_id": bio, "party": party, "state": "CA", "chamber": "House"}}


def _records_for(days) -> list:
    """Four members per party carrying that day's shared phrase, against a realistic corpus."""
    rows = []
    for di, day in enumerate(days):
        dp, rp = _SHARED[day]
        for i in range(1, 5):
            rows.append(_rec(f"D{i}", "Democrat", day, _body(di * 80 + i, 1),
                             f"That is why we must {dp} this year."))
            rows.append(_rec(f"R{i}", "Republican", day, _body(di * 80 + i + 20, 2),
                             f"That is why we must {rp} this year."))
        for i in range(1, 21):
            rows.append(_rec(f"D{i + 10}", "Democrat", day, _body(di * 80 + i + 40, 3)))
            rows.append(_rec(f"R{i + 10}", "Republican", day, _body(di * 80 + i + 60, 4)))
    return rows


@contextlib.contextmanager
def _temp_tree():
    """A throwaway state/derived tree. Nothing here may touch the real data/derived."""
    old_state, old_derived = config.STATE, config.DERIVED
    with tempfile.TemporaryDirectory(prefix="onscript-s73-") as d:
        root = Path(d)
        config.STATE, config.DERIVED = root / "state", root / "derived"
        config.STATE.mkdir(parents=True, exist_ok=True)
        config.DERIVED.mkdir(parents=True, exist_ok=True)
        try:
            yield root
        finally:
            config.STATE, config.DERIVED = old_state, old_derived


def _run(days, product_day, run_id="s73"):
    return deterministic.run(_records_for(days), run_id=run_id, product_day=product_day)


def _day_file(day):
    return config.DERIVED / "days" / f"{day}.json"


def _board(day):
    return config.DERIVED / "silence" / f"{day}.json"


def _publish(day):
    """Mark a day published the way assemble does, so `util.day_is_final` sees it."""
    util.write_json(config.DERIVED / "manifest" / f"assemble-{day}.json",
                    {"day": day, "kind": "assemble", "final": True})


# --- 1. the resolver, replayed against the real committed manifests -------------------------------
def test_the_resolver_never_points_past_the_product_day_on_any_real_run():
    """Replay every committed collect manifest. Not one resolves to a day that was not over yet.

    The manifests carry what the resolver needs: the newest day the corpus held (`days_present[-1]`)
    and the instant the run happened (`generated_at`), which is the product day. Production resolved
    same-day focus on 30 of these runs; the fixed resolver resolves none.
    """
    manifests = _real_collect_manifests()
    assert len(manifests) > 20, f"expected the committed manifest history, found {len(manifests)}"
    for m in manifests:
        pd = _product_day_of(m["generated_at"])
        r = readiness.resolve_focus_day([m["days_present"][-1]], pd)
        assert r["day"] <= pd, f"{m['run']} resolved {r['day']}, past the product day {pd}"
        assert not r["future"], f"{m['run']} resolved a future day"


def test_the_run_that_orphaned_2026_09_08_now_resolves_to_it():
    """The single most important line of this file: the run that stepped over the day now lands on it.

    `collect-2026-09-09` recorded focus_day 2026-09-09 while the corpus already held 2026-09-08, and
    2026-09-08 was never written by anything. Replayed through the resolver, the same inputs give
    2026-09-08.
    """
    m = next((x for x in _real_collect_manifests() if x["run"] == ORPHANING_RUN), None)
    assert m is not None, f"{ORPHANING_RUN}.json is the pinned record of the incident"
    assert m["focus_day"] > _product_day_of(m["generated_at"]), \
        "this manifest is only interesting because production focused a day that was not over"
    r = readiness.resolve_focus_day([m["days_present"][-1]], _product_day_of(m["generated_at"]))
    assert r["day"] == ORPHANED_DAY, f"expected the orphaned day back, got {r['day']}"
    assert r["clamped"] is True
    assert r["requested"] == m["focus_day"]


def test_every_day_production_skipped_is_reachable_again():
    """No day in the real history escapes both the resolver and the sweep window.

    Production's focus sequence has gaps: thirteen days were vaulted over between 2026-07-12 and
    2026-09-09, and all nine that fell after the silence board was wired lost their board. For each
    such day the fixed pipeline must either focus it outright or reach it from a later run's sweep
    window. This is the whole invariant, stated over real production dates rather than invented ones.
    """
    manifests = _real_collect_manifests()
    resolved = [readiness.resolve_focus_day([m["days_present"][-1]],
                                            _product_day_of(m["generated_at"]))["day"]
                for m in manifests]
    focused = set(resolved)
    skipped = _skipped_by_production()
    assert ORPHANED_DAY in skipped, "the pinned incident must be in the skipped set"

    windows = [set(readiness.sweep_window(day)) for day in resolved]
    for day in sorted(skipped):
        assert day in focused or any(day in w for w in windows), \
            f"{day} was skipped by production and is still unreachable"


def test_a_corpus_behind_the_product_day_still_governs():
    """Clamping the future must never drag a backfill forward into days it does not hold."""
    r = readiness.resolve_focus_day(["2025-03-01", "2025-03-04"], "2026-09-09")
    assert r["day"] == "2025-03-04" and not r["clamped"]
    assert readiness.resolve_focus_day([], "2026-09-09")["day"] == "2026-09-09"


# --- 2. the sweep: a day whose data lands between two runs is still written ------------------------
def test_a_day_whose_data_lands_between_two_runs_is_still_written():
    """The incident, reconstructed end to end: two consecutive runs, day N landing between them.

    Run one sees the corpus through 2026-09-06. Between the runs the mirror delivers 09-07, 09-08 and
    a first statement for 09-09, exactly the shape `normalize.in` recorded moving 83,390 to 83,512.
    Run two focuses 09-09. Under the old cursor 09-07 and 09-08 were written by nothing; under the
    sweep both exist, with real content, and neither was ever a focus day.
    """
    with _temp_tree():
        _run(["2026-09-05", "2026-09-06"], product_day="2026-09-06", run_id="s73-run-1")
        assert _day_file("2026-09-06").exists(), "run one must write its own focus day"
        assert not _day_file("2026-09-08").exists(), "09-08 has not been delivered yet"

        _run(["2026-09-05", "2026-09-06", "2026-09-07", "2026-09-08", "2026-09-09"],
             product_day="2026-09-09", run_id="s73-run-2")
        for day in ("2026-09-07", "2026-09-08"):
            assert _day_file(day).exists(), f"{day} landed between runs and must still be written"
            rec = json.loads(_day_file(day).read_text(encoding="utf-8"))
            assert rec["day"] == day
            assert rec["top_synchronized"], f"{day} was written empty, which enshrines the hole"
            assert _board(day).exists(), f"{day} must get its silence board too"


def test_the_sweep_reports_what_it_repaired_in_the_manifest():
    """A silent repair is the same failure as a silent skip (Article XVI)."""
    with _temp_tree():
        _run(["2026-09-05", "2026-09-06"], product_day="2026-09-06", run_id="s73-m1")
        res = _run(["2026-09-05", "2026-09-06", "2026-09-07", "2026-09-08"],
                   product_day="2026-09-08", run_id="s73-m2")
        m = res["manifest"]
        assert "2026-09-07" in m["day_sweep"]["records_written"]
        assert m["focus_cursor"]["day"] == "2026-09-08"


# --- 3. the sweep's guards ------------------------------------------------------------------------
def test_a_premature_empty_day_is_refreshed_when_its_statements_arrive():
    """The 2026-09-09 shape: a day written from one statement must not be enshrined as a quiet day.

    The old cursor wrote a day record the moment a single statement dated that day appeared, with an
    empty `top_synchronized`, and nothing ever refreshed it. The sweep rewrites exactly this case:
    unpublished, no daily lines, no phrases, and data now present.
    """
    with _temp_tree():
        res = _run(_SEED, product_day="2026-09-08", run_id="s73-pe")
        statements, ledger = res["statements"], res["ledger"]
        discipline = res["engine"].discipline_index()

        util.write_json(_day_file("2026-09-06"),
                        {"day": "2026-09-06", "top_synchronized": [], "daily_lines": None})
        out = deterministic._sweep_unwritten_days(
            statements, ledger, discipline, focus_day="2026-09-07",
            product_day="2026-09-07", out_dir=config.DERIVED)
        assert "2026-09-06" in out["records_written"]
        refreshed = json.loads(_day_file("2026-09-06").read_text(encoding="utf-8"))
        assert refreshed["top_synchronized"], "late data must reach the page"

        # And the mirror: a record that already carries phrases is left alone.
        again = deterministic._sweep_unwritten_days(
            statements, ledger, discipline, focus_day="2026-09-07",
            product_day="2026-09-07", out_dir=config.DERIVED)
        assert "2026-09-06" not in again["records_written"]


def test_the_sweep_never_rewrites_a_published_day():
    """Guard 2. The sweep must not become a second route to the defect that nulled 2026-07-12."""
    with _temp_tree():
        res = _run(_SEED, product_day="2026-09-08", run_id="s73-final")
        statements, ledger = res["statements"], res["ledger"]
        discipline = res["engine"].discipline_index()

        published = {"day": "2026-09-06", "top_synchronized": [],
                     "daily_lines": {"D": {"composite": "published prose"}}}
        util.write_json(_day_file("2026-09-06"), published)
        _publish("2026-09-06")
        out = deterministic._sweep_unwritten_days(
            statements, ledger, discipline, focus_day="2026-09-07",
            product_day="2026-09-07", out_dir=config.DERIVED)
        assert "2026-09-06" not in out["records_written"]
        kept = json.loads(_day_file("2026-09-06").read_text(encoding="utf-8"))
        assert kept["daily_lines"] == published["daily_lines"], "a published day is permanent"


def test_the_sweep_never_writes_a_day_that_holds_nothing():
    """Guard 3. A dataless day is a gap, not a day, and `select_target_day` refuses to publish one.

    Writing it here would manufacture the empty "nothing today" page that guard exists to prevent,
    and would do it for every weekend forever.
    """
    with _temp_tree():
        res = _run(["2026-09-07"], product_day="2026-09-07", run_id="s73-gap")
        out = deterministic._sweep_unwritten_days(
            res["statements"], res["ledger"], res["engine"].discipline_index(),
            focus_day="2026-09-07", product_day="2026-09-07", out_dir=config.DERIVED)
        for day in readiness.sweep_window("2026-09-07"):
            if day != "2026-09-07":
                assert not _day_file(day).exists(), f"{day} holds no statements and must stay unwritten"
        assert out["records_written"] == []


def test_an_existing_silence_board_is_never_replaced():
    """Guard 4. A missing board is a hole worth filling; a present one belongs to its day."""
    with _temp_tree():
        res = _run(_SEED, product_day="2026-09-08", run_id="s73-board")
        _board("2026-09-06").parent.mkdir(parents=True, exist_ok=True)
        _board("2026-09-06").write_text('{"kind": "silence-board", "mine": true}', encoding="utf-8")
        out = deterministic._sweep_unwritten_days(
            res["statements"], res["ledger"], res["engine"].discipline_index(),
            focus_day="2026-09-07", product_day="2026-09-07", out_dir=config.DERIVED)
        assert "2026-09-06" not in out["boards_written"]
        assert json.loads(_board("2026-09-06").read_text(encoding="utf-8"))["mine"] is True


def test_the_sweep_reaches_exactly_as_far_back_as_the_publication_walk():
    """The stage that writes a day and the stage that publishes it must reach the same distance.

    A narrower write window hands assemble a day nobody built; a wider one rebuilds final days.
    """
    window = readiness.sweep_window("2026-09-09")
    assert window[-1] == "2026-09-09" and len(window) == readiness.LOOKBACK_DAYS + 1
    assert window == sorted(window), "the sweep walks oldest first, like every other walk"
    assert window[0] == "2026-09-04"


# --- 4. a negative age is unreachable -------------------------------------------------------------
def test_a_focus_day_in_the_future_can_never_report_a_negative_age():
    """The "-1 days old" line is unreachable, and the condition pages instead of printing nonsense."""
    statements = [{"published_at": "2026-09-09", "lane": 1}]
    m = ops.collection_maturity(statements, "2026-09-09", reference_day="2026-09-08")
    assert m["age_days"] == 0, "an age is floored at zero, never negative"
    assert m["future_focus_day"] is True
    assert "-1" not in m["reason"] and "-2" not in m["reason"]
    assert m["mature"] == m["ready"], "the waited-out arm must contribute nothing to a future day"


def test_flooring_a_future_age_cannot_manufacture_maturity():
    """The floor must not become a back door to force-finalizing a day that has not happened.

    Given a judgeable baseline the ready arm says no, so maturity can only come from the waited-out
    arm, and the floored age must not satisfy it. Six prior Wednesdays at the observed early-September
    level, against the single statement the 2026-09-09 run actually saw.
    """
    statements = ([{"published_at": "2026-09-09", "lane": 1}]
                  + [{"published_at": d, "lane": 1}
                     for d in ("2026-09-02", "2026-08-26", "2026-08-19",
                               "2026-08-12", "2026-08-05", "2026-07-29")
                     for _ in range(130)])
    m = ops.collection_maturity(statements, "2026-09-09", reference_day="2026-09-08")
    assert m["future_focus_day"] is True and m["age_days"] == 0
    assert m["ready"] is False, "one statement against a 130 baseline is not ready"
    assert m["mature"] is False, "a day that has not happened can never be mature"


def test_no_focus_and_reference_pair_can_produce_a_negative_age():
    """Property, over a grid that straddles the boundary in both directions."""
    days = [f"2026-09-{d:02d}" for d in range(4, 13)]
    for focus in days:
        for reference in days:
            m = ops.collection_maturity([{"published_at": focus, "lane": 1}], focus,
                                        reference_day=reference)
            assert m["age_days"] >= 0, f"{focus} against {reference} produced {m['age_days']}"
            assert m["future_focus_day"] is (focus > reference)
            assert " -" not in m["reason"], f"a negative day count reached the operator: {m['reason']}"


def test_a_healthy_age_is_untouched():
    """Flooring must not change any verdict on the path that was always correct."""
    m = ops.collection_maturity([{"published_at": "2026-09-07", "lane": 1}], "2026-09-07",
                                reference_day="2026-09-09")
    assert m["age_days"] == 2 and m["future_focus_day"] is False
    assert m["mature"] is True, "two product days old is past MAX_WAIT_DAYS and force-finalizes"


# --- 5. one owner for the day record --------------------------------------------------------------
def test_build_derived_writes_exactly_what_the_day_record_owner_produces():
    """docs/37 rule 1: the focus path and the sweep build the same object, from the same function."""
    with _temp_tree():
        res = _run(_SEED, product_day="2026-09-08", run_id="s73-owner")
        discipline = res["engine"].discipline_index()
        written = json.loads(_day_file("2026-09-07").read_text(encoding="utf-8"))
        assert written == build.day_record(res["ledger"], discipline, "2026-09-07")


def test_a_day_record_is_incomplete_only_where_the_cursor_skipped_it():
    """The third damage surface, measured on the live tree: skipped days lost their deterministic half.

    A day the cursor skipped was never written by RUN A at all, so when assemble later published it,
    assemble's read-modify-write started from a bare {"day": day} and the record went out WITHOUT
    `legacy_unvalidated_metrics`. In the era where that field exists, the days missing it are exactly
    the days production skipped: eight for eight, 2026-08-03 through 2026-09-06.

    Written as an implication rather than a list (docs/37 rule 3): every incomplete record must be
    explained by a skip. When a repair completes those days the implication still holds, and it
    catches any NEW incomplete day immediately, which is the regression worth guarding.
    """
    required = set(build.day_record({}, {}, "2026-01-01"))
    records = {p.stem: set(json.loads(p.read_text(encoding="utf-8")))
               for p in sorted(DAYS_DIR.glob("2026-*.json"))}
    assert records, "the committed day records are the production sample this rule asks for"
    complete = [d for d, k in records.items() if required <= k]
    assert complete, "no committed day record carries the deterministic half"
    era_start = min(complete)          # before this the field did not exist, so absence means nothing
    skipped = _skipped_by_production()
    for day in sorted(d for d in records if d >= era_start):
        if required <= records[day]:
            continue
        assert day in skipped, \
            f"{day} lost its deterministic half and no cursor skip explains it"


def test_a_published_day_missing_its_deterministic_half_is_reported_not_rewritten():
    """The backlog guard 2 refuses to repair must still be visible, or nobody learns it exists."""
    with _temp_tree():
        res = _run(_SEED, product_day="2026-09-08", run_id="s73-held")
        util.write_json(_day_file("2026-09-06"),
                        {"day": "2026-09-06", "top_synchronized": [],
                         "daily_lines": {"D": {"composite": "published prose"}}})
        _publish("2026-09-06")
        out = deterministic._sweep_unwritten_days(
            res["statements"], res["ledger"], res["engine"].discipline_index(),
            focus_day="2026-09-07", product_day="2026-09-07", out_dir=config.DERIVED)
        assert [r["day"] for r in out["held"]] == ["2026-09-06"]
        assert "2026-09-06" not in out["records_written"], "reporting is not permission to rewrite"


def test_the_day_record_key_set_comes_from_its_owner():
    """docs/37 rule 1: the sweep's notion of a complete record is the writer's, not a copy of it."""
    assert build.day_record_keys() == frozenset(build.day_record({}, {}, "2026-09-08"))
    assert "legacy_unvalidated_metrics" in build.day_record_keys()


def test_the_orphaned_day_is_the_one_hole_in_the_committed_record():
    """The damage this fix heals, measured on the live tree rather than asserted from the work order.

    Stated as a bound rather than an equality: when the deployed sweep fills 2026-09-08 the count
    goes to zero and this still passes, which is what rule 3 requires of a test that names a defect.
    """
    present = {p.stem for p in DAYS_DIR.glob("2026-09-*.json")}
    if not present:
        return
    span = _between(min(present), max(present))
    holes = [d for d in span if d not in present]
    assert len(holes) <= 1, f"the cursor left more holes than the incident accounts for: {holes}"
    assert all(h == ORPHANED_DAY for h in holes), f"an unexplained hole appeared: {holes}"
