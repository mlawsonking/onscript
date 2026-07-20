"""A PUBLISHED day is immutable to RUN A (docs/23 §7.5 R-C).

THE DEFECT THESE LOCK. `build.build_derived` wrote days/{day}.json as a full-object overwrite
carrying `daily_lines: None`. RUN A focuses whatever day is newest in the corpus, so a collect that
landed on an already-published day silently DELETED that day's composites, talking_points, duets and
rejected_keys. It destroyed two published days in production — `collect 2026-07-14` nulled day
2026-07-12, and `collect 2026-07-19` (0a66cea) nulled day 2026-07-18 — and it went unnoticed for a
week because the run exits 0 and the site keeps rendering.

The invariant: RUN A never rewrites a published day. The only sanctioned write path to a published
day is `run_assemble --day <day>` (the repair), which does its own read-modify-write.

Four of these tests lock things that LOOK like details and are not:
  * a manifest with NO `final` key still protects the day (5 of 10 published days are that shape);
  * the guard is scoped to days/ only, so the instrument's living state keeps refreshing;
  * the repair path does not route through the guard (a guard that blocks its own repair is worse
    than the bug);
  * the repair preserves trigger-provenance, so repairing the streak head cannot fail §1.4.1.
"""
import inspect
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import alexandria, build, deterministic, ops, run_assemble, util  # noqa: E402


def _tree(manifests: dict | None = None) -> Path:
    """A derived tree with an optional {day: assemble_manifest} set already published."""
    root = Path(tempfile.mkdtemp(prefix="onscript-immutable-"))
    (root / "days").mkdir(parents=True)
    (root / "manifest").mkdir(parents=True)
    (root / "phrases").mkdir(parents=True)
    for day, man in (manifests or {}).items():
        (root / "manifest" / f"assemble-{day}.json").write_text(json.dumps(man), encoding="utf-8")
    return root


def _ledger(day: str) -> dict:
    return {"border security funding": {
        "ngram": "border security funding", "n": 3, "df_weight": 1.0,
        "first_seen": {"date": day, "party": "D", "member": "X"},
        "daily": {day: {"D": 7, "R": 0, "members_D": ["A", "B", "C"], "members_R": []}}}}


def _published_day(day: str) -> dict:
    """What a day looks like AFTER assemble merged the composites in — the thing at risk."""
    return {"day": day, "top_synchronized": [{"ngram": "border security funding", "party": "D"}],
            "discipline": {"D": 0.4, "R": 0.2},
            "daily_lines": {"D": {"composite": "D said this.", "verifier": {"passed": True}},
                            "R": {"composite": "R said this.", "verifier": {"passed": True}}},
            "talking_points": {"D": [{"label": "border security funding"}], "R": []},
            "duets": [], "rejected_keys": {"D": [], "R": []}}


def _run(root: Path, day: str, **kw) -> dict:
    return build.build_derived([], _ledger(day), {"D": {day: 0.4}, "R": {day: 0.2}}, root,
                               focus_day=day, coverage={"2026": {}}, **kw)


# --- the core invariant -------------------------------------------------------------------------

def test_published_day_is_byte_identical_after_a_run_a_pass():
    """RUN A over a published day must not change one byte of it."""
    day = "2026-07-18"
    root = _tree({day: {"final": True, "event": "schedule", "unattended": True}})
    dayfile = root / "days" / f"{day}.json"
    dayfile.write_text(json.dumps(_published_day(day)), encoding="utf-8")
    before = dayfile.read_bytes()

    summary = _run(root, day)

    assert dayfile.read_bytes() == before, "RUN A rewrote a PUBLISHED day — the P0 has regressed"
    assert summary["focus_day_write"] == "skipped-final", summary
    # honest about work not done: never report a row count it did not write
    assert summary["focus_day_top_phrases"] is None, summary


def test_composites_survive_the_exact_production_sequence():
    """The literal 0a66cea scenario: assemble publishes, then a later collect re-focuses the day."""
    day = "2026-07-18"
    root = _tree({day: {"final": True, "event": "schedule", "unattended": True}})
    (root / "days" / f"{day}.json").write_text(json.dumps(_published_day(day)), encoding="utf-8")

    _run(root, day)   # the collect pass that used to null it

    after = json.loads((root / "days" / f"{day}.json").read_text(encoding="utf-8"))
    assert after["daily_lines"] is not None, "daily_lines was nulled — this is the exact P0"
    assert after["daily_lines"]["D"]["composite"] == "D said this."
    for k in ("talking_points", "duets", "rejected_keys"):
        assert k in after, f"{k} was dropped from a published day"


def test_a_manifest_with_no_final_key_still_protects_the_day():
    """BACK-COMPAT IS THE WHOLE BALLGAME. Only 4 of 9 published manifests carry `final`; the rest
    pre-date the readiness gate. 2026-07-12 — the day that proves the bug — is one of the bare ones.
    A guard written as `m.get("final") is True` leaves 5 of 10 published days clobberable."""
    day = "2026-07-12"
    root = _tree({day: {"run_id": "assemble-2026-07-13", "day": day}})   # NO `final` key at all
    dayfile = root / "days" / f"{day}.json"
    dayfile.write_text(json.dumps(_published_day(day)), encoding="utf-8")
    before = dayfile.read_bytes()

    assert util.day_is_final(day, root) is True, "a bare manifest must still mean PUBLISHED"
    assert _run(root, day)["focus_day_write"] == "skipped-final"
    assert dayfile.read_bytes() == before


def test_an_unpublished_day_is_still_written():
    """The guard must not freeze the streak: a day with no assemble manifest is written normally."""
    day = "2026-07-20"
    root = _tree()
    assert util.day_is_final(day, root) is False
    summary = _run(root, day)
    assert summary["focus_day_write"] == "written", summary
    assert summary["focus_day_top_phrases"] == 1, summary
    assert (root / "days" / f"{day}.json").exists()


def test_an_explicitly_non_final_manifest_fails_open():
    """`final: False` means not-yet-published — writing is correct, and it is the safe direction."""
    day = "2026-07-20"
    root = _tree({day: {"final": False}})
    assert util.day_is_final(day, root) is False
    assert _run(root, day)["focus_day_write"] == "written"


# --- scope: the guard must not freeze the instrument --------------------------------------------

def test_the_instrument_keeps_refreshing_when_the_day_is_skipped():
    """discipline/coverage/phrases are CURRENT STATE, not the record of a date. The per-phrase pages
    are living adoption curves — freezing them strands each phrase at the day it first surfaced."""
    day = "2026-07-18"
    root = _tree({day: {"final": True}})
    (root / "days" / f"{day}.json").write_text(json.dumps(_published_day(day)), encoding="utf-8")

    _run(root, day)

    assert (root / "discipline.json").exists(), "discipline.json must keep refreshing"
    assert (root / "coverage.json").exists(), "coverage.json must keep refreshing"
    assert (root / "phrases" / "top.json").exists(), "phrases/top.json must keep refreshing"
    slug = build.phrase_slug("border security funding")
    assert (root / "phrases" / f"{slug}.json").exists(), "per-phrase curves must keep refreshing"


def test_the_escape_hatch_overwrites_a_published_day():
    """An operator may deliberately rebuild a published day's deterministic half in place."""
    day = "2026-07-18"
    root = _tree({day: {"final": True}})
    dayfile = root / "days" / f"{day}.json"
    dayfile.write_text(json.dumps(_published_day(day)), encoding="utf-8")

    summary = _run(root, day, allow_final_overwrite=True)

    assert summary["focus_day_write"] == "written", summary
    assert json.loads(dayfile.read_text(encoding="utf-8"))["daily_lines"] is None


# --- the guard must not be reachable-around, nor block its own repair ---------------------------

def test_run_a_never_passes_the_escape_hatch():
    """RUN A's two routes into build_derived must never opt out of immutability."""
    for fn in (deterministic.run, alexandria.merge):
        src = inspect.getsource(fn)
        assert "allow_final_overwrite" not in src, (
            f"{fn.__qualname__} opts out of the published-day guard — RUN A must never do this")


def test_the_repair_path_does_not_route_through_the_guard():
    """A guard that blocks its own repair path is worse than the bug. run_assemble does its own
    read-modify-write and must never call build_derived."""
    assert "build_derived" not in inspect.getsource(run_assemble), (
        "run_assemble now calls build_derived — the repair path would blank the day it is repairing")


# --- the repair must not destroy the launch gate -------------------------------------------------

def _fresh_manifest(**kw) -> dict:
    """What assemble() computes for THIS run, before provenance is merged. A repair is never a cron,
    so `event`/`unattended` here are always the repair's own trigger."""
    m = {"day": "2026-07-18", "final": True, "event": "local", "unattended": False,
         "run_id": "assemble-2026-07-20", "degraded": False, "forced_finalize": False,
         "readiness": None}
    m.update(kw)
    return m


def _repair(prior: dict, **kw):
    return run_assemble.repair_safe_manifest(
        _fresh_manifest(**kw), prior, now="2026-07-20T12:00:00Z",
        repair_run_id="assemble-2026-07-20", repair_event="local")


def test_repairing_the_streak_head_preserves_unattended_provenance():
    """THE ONE THAT NEARLY SHIPPED. `run_assemble --day` recomputes event/unattended from
    GITHUB_EVENT_NAME, and a repair is never a `schedule` event. `ops.unattended_streak` breaks on
    the first falsy `unattended`, and the repair target (2026-07-18) is the streak HEAD — so the
    repair ordered to protect the launch would have taken §1.4.1 from passes:True to passes:False.
    Trigger-provenance is a fact about the ORIGINAL run; a repair restores content, not history.

    Behavioral, not source-inspecting: this drives the real streak function over real manifest files,
    so deleting the preservation loop fails it."""
    root = _tree()
    man = root / "manifest"
    published = {"final": True, "event": "schedule", "unattended": True, "degraded": False,
                 "forced_finalize": False}
    for day in ("2026-07-16", "2026-07-17", "2026-07-18"):
        (man / f"assemble-{day}.json").write_text(json.dumps(published), encoding="utf-8")
    assert ops.unattended_streak("2026-07-19", manifest_dir=man)["passes"] is True

    # the naive repair (no preservation) — proves the failure mode is real and still reachable
    (man / "assemble-2026-07-18.json").write_text(json.dumps(_fresh_manifest()), encoding="utf-8")
    assert ops.unattended_streak("2026-07-19", manifest_dir=man)["passes"] is False, (
        "the naive repair no longer breaks the streak — this test has stopped testing anything")

    # the real code path: provenance merged from the published manifest
    repaired, is_repair = _repair(published)
    assert is_repair is True
    assert repaired["event"] == "schedule" and repaired["unattended"] is True
    assert repaired["repaired_at"] == "2026-07-20T12:00:00Z"
    assert repaired["repair_event"] == "local"
    (man / "assemble-2026-07-18.json").write_text(json.dumps(repaired), encoding="utf-8")
    streak = ops.unattended_streak("2026-07-19", manifest_dir=man)
    assert streak["passes"] is True and streak["value"] == 3, streak


def test_a_repair_never_launders_a_force_finalized_day():
    """`forced_finalize` is trigger-provenance, not content: it records that the readiness gate waited
    out MAX_WAIT_DAYS and published anyway. The `--day` path hard-codes forced=False, so recomputing
    it would convert a force-finalized day into a streak-eligible one and drop its alert."""
    published = {"final": True, "event": "schedule", "unattended": True, "forced_finalize": True}
    repaired, _ = _repair(published)
    assert repaired["forced_finalize"] is True, "a repair laundered a force-finalized day"

    root = _tree()
    man = root / "manifest"
    (man / "assemble-2026-07-18.json").write_text(json.dumps(repaired), encoding="utf-8")
    assert ops.unattended_streak("2026-07-19", manifest_dir=man)["value"] == 0, (
        "a force-finalized day must not count toward §1.4.1")


def test_a_repair_does_not_invent_provenance_the_original_run_never_had():
    """07-14/07-15 pre-date the event/unattended instrumentation. An uninstrumented run must stay
    uninstrumented — inventing `unattended` would manufacture streak evidence."""
    repaired, is_repair = _repair({"final": True, "run_id": "assemble-2026-07-15"})
    assert is_repair is True
    assert "event" not in repaired and "unattended" not in repaired, repaired
    assert repaired["run_id"] == "assemble-2026-07-15"


def test_degraded_is_not_preserved_because_it_describes_content():
    """If a repair degrades a day, the streak SHOULD notice — `degraded` is what is published now."""
    repaired, _ = _repair({"final": True, "event": "schedule", "unattended": True,
                           "degraded": False}, degraded=True)
    assert repaired["degraded"] is True


def test_a_normal_run_is_untouched_by_the_repair_path():
    """INERTNESS. A fresh day has no prior manifest, so nothing is preserved and nothing is stamped —
    tonight's cron must behave exactly as it did before this change."""
    fresh = _fresh_manifest(event="schedule", unattended=True)
    out, is_repair = run_assemble.repair_safe_manifest(
        dict(fresh), {}, now="x", repair_run_id="y", repair_event="z")
    assert is_repair is False
    assert out == fresh, "a normal run's manifest was modified by the repair path"
    for k in ("repaired_at", "repair_run_id", "repair_event"):
        assert k not in out


def test_a_repair_does_not_repoint_the_posting_target():
    """assemble-latest.json chooses the day that POSTS. Repairing an old day must not aim the next
    post at it — repairing 2026-07-12 on launch eve would post a nine-day-stale day."""
    src = inspect.getsource(run_assemble.assemble)
    i_repair, i_latest = src.index("is_repair"), src.index("assemble-latest.json")
    assert "if not is_repair:" in src[i_repair:i_latest + 400], (
        "assemble-latest.json is repointed unconditionally — a repair would move the posting target")


def test_an_unreadable_manifest_never_crashes_run_a():
    """The guard is consulted from RUN A, which never read the manifest dir before. A corrupt
    manifest must not become a new way to break the streak — and ambiguity resolves toward NOT
    clobbering."""
    day = "2026-07-18"
    root = _tree()
    (root / "manifest" / f"assemble-{day}.json").write_text("{ truncated", encoding="utf-8")
    assert util.day_is_final(day, root) is True, "unreadable manifest must fail CLOSED"
    dayfile = root / "days" / f"{day}.json"
    dayfile.write_text(json.dumps(_published_day(day)), encoding="utf-8")
    before = dayfile.read_bytes()
    assert _run(root, day)["focus_day_write"] == "skipped-final"   # must not raise
    assert dayfile.read_bytes() == before
