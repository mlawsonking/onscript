"""G1: the Alexandria Stage 2 GPU scripts are import-safe and their deterministic parts hold.

The whole point of these two scripts is that they carry a GPU stack that must never enter the
pipeline. So the suite asserts the boundary itself: importing them pulls no third-party package,
requirements.lock stays empty of runtime dependencies, and everything that can be computed
without a GPU (store layout, resume detection, id-list addressing, taxonomy parsing, frozen
instrument identity) is exercised here.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from pipeline import config, util
from scripts.deep import alexandria_embed as embed
from scripts.deep import alexandria_topic_tag as tagger


ROOT = Path(__file__).resolve().parent.parent


def test_gpu_stack_is_never_a_pipeline_dependency():
    # S67-3 put the first package in requirements.lock: Pillow, optional and decorative, imported
    # only by pipeline/cards.py from a skip-and-log builder. So this no longer asserts the file is
    # empty; it asserts what it was always FOR, which is that the GPU stack never crosses into the
    # pipeline, plus that the pinned set is exactly the one package the project has sanctioned and
    # every pin carries artifact hashes.
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    requirements = [line.strip() for line in lock.splitlines()
                    if line.strip() and not line.lstrip().startswith(("#", "--hash"))]
    names = {re.split(r"[=<>~!\[ ]", line.strip(" \\"))[0].lower() for line in requirements}
    assert names <= {"pillow"}, f"requirements.lock gained an unsanctioned dependency: {sorted(names)}"
    assert not (names & {"torch", "sentence-transformers", "sentence_transformers",
                         "numpy", "transformers", "accelerate"}), (
        "the Alexandria GPU stack must never be a pipeline dependency")
    assert "pillow==12.2.0" in lock and lock.count("--hash=sha256:") >= 2, (
        "a pinned dependency needs an exact version and artifact hashes")
    # A fresh interpreter, so the check is about these two modules and not about whatever an
    # earlier test file happened to import.
    probe = (
        "import sys;"
        "from scripts.deep import alexandria_embed, alexandria_topic_tag;"
        "print([n for n in ('torch','sentence_transformers','numpy','transformers')"
        " if n in sys.modules])"
    )
    completed = subprocess.run([sys.executable, "-c", probe], cwd=ROOT, check=True,
                               capture_output=True, text=True)
    assert completed.stdout.strip() == "[]", (
        f"importing the Alexandria GPU scripts pulled {completed.stdout.strip()}")


def test_the_missing_gpu_stack_names_where_it_lives_instead_of_stack_tracing():
    try:
        embed._load_encoder("cpu")
    except embed.GpuStackMissing as error:
        message = str(error)
        assert "outside this repository" in message
        assert "sentence-transformers" in message
        assert "requirements.lock" in message
    except Exception as error:  # pragma: no cover - only when the stack IS importable here
        raise AssertionError(f"unexpected failure mode: {error!r}") from error


def test_the_vector_store_never_points_into_the_repository():
    for lane in embed.LANES:
        for path in embed.shard_paths(lane, 113).values():
            resolved = str(Path(path).resolve())
            assert not resolved.startswith(str(config.REPO_ROOT.resolve())), (
                f"{path} would write vectors into the repository working tree")
    assert "alexandria" in str(embed.store_root()).lower()


def test_resume_treats_a_shard_as_done_only_when_its_manifest_says_complete():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        assert embed.shard_complete("press", 113, root) is False
        paths = embed.shard_paths("press", 113, root)
        paths["vectors"].parent.mkdir(parents=True, exist_ok=True)
        paths["vectors"].write_bytes(b"")
        paths["ids"].write_text("", encoding="utf-8")
        util.write_json(paths["manifest"], {"rows": 5, "complete": False})
        assert embed.shard_complete("press", 113, root) is False, (
            "an interrupted shard must not be skipped on resume")
        util.write_json(paths["manifest"], {"rows": 5, "complete": True})
        assert embed.shard_complete("press", 113, root) is True


def test_the_mirror_window_covers_a_congress_with_room_at_both_boundaries():
    """The reader opens ~48 of 303 mirror files per Congress instead of all of them.

    Scanning the whole 2.38 GB mirror once per Congress meant about 31 GB of reads across the
    corpus, and that disk time, not the GPU, dominated the first run. The window is decided from
    file names alone. It must still contain every month a Congress can touch: a Congress seats
    Jan 3 of its start year and ends Jan 2 two years later, so December before and January after
    are both in play.
    """
    for congress in (107, 113, 119):
        names = {path.name for path in embed.mirror_files_for(congress)}
        start = 2001 + 2 * (congress - 107)
        for required in (f"{start - 1}-12.jsonl", f"{start}-01.jsonl", f"{start}-12.jsonl",
                         f"{start + 1}-01.jsonl", f"{start + 1}-12.jsonl",
                         f"{start + 2}-01.jsonl"):
            if (embed.fetch.MIRROR / required).is_file():
                assert required in names, f"congress {congress} window drops {required}"
        assert f"{start - 2}-06.jsonl" not in names, "the window is wider than it needs to be"


def test_the_windowed_reader_selects_the_same_records_as_a_full_scan():
    """Proven against a real Congress rather than a fixture, on the smallest one.

    Skipped when the raw mirror is absent, because it is a Release asset and not every checkout
    carries it. Where it exists this is the check that matters: the optimisation must not change
    which statements get embedded.
    """
    if not embed.fetch.MIRROR.is_dir() or not any(embed.fetch.MIRROR.glob("*.jsonl")):
        return
    congress = 107
    windowed = {unit["stable_id"] for unit in embed.press_units(congress)
                if (unit.get("text") or "").strip()}
    full = set()
    for path in sorted(embed.fetch.MIRROR.glob("*.jsonl")):
        for record in embed.util.iter_jsonl(path):
            day = (record.get("date") or "")[:10]
            if len(day) != 10 or embed.util.congress_for_date(day) != congress:
                continue
            url, text = (record.get("url") or "").strip(), record.get("text") or ""
            if url and text.strip():
                full.add(embed.util.statement_id(url, text))
    assert windowed == full, (
        f"the file window changed which statements are embedded: {len(windowed)} vs {len(full)}")


def test_the_crec_window_covers_a_congress_and_is_not_the_whole_lane():
    """The CREC E lane is one file per calendar year; a Congress spans at most three of 26."""
    from pipeline.deep import lanes

    e_dir = lanes.lane_state("crec") / "E"
    if not e_dir.is_dir() or not any(e_dir.glob("statements-*.jsonl")):
        return
    total = len(list(e_dir.glob("statements-*.jsonl")))
    for congress in (108, 113, 119):
        names = {path.name for path in embed.crec_files_for(congress, e_dir)}
        start = 2001 + 2 * (congress - 107)
        assert len(names) < total, "the window is the whole lane, so it saves nothing"
        for year in (start, start + 1):
            required = f"statements-{year}.jsonl"
            if (e_dir / required).is_file():
                assert required in names, f"congress {congress} window drops {required}"


def test_the_id_list_address_is_row_ordered_and_order_sensitive():
    rows = [{"stable_id": "a"}, {"stable_id": "b"}]
    assert embed.id_list_sha256(rows) == embed.id_list_sha256([{"stable_id": "a"},
                                                               {"stable_id": "b"}])
    assert embed.id_list_sha256(rows) != embed.id_list_sha256(list(reversed(rows)))


def test_the_tagger_speaks_only_the_committed_taxonomy():
    committed = json.loads(config.TAXONOMY_FILE.read_text(encoding="utf-8"))
    assert tagger.labels() == [topic["id"] for topic in committed["topics"]]
    assert len(tagger.labels()) == 25
    for label in tagger.labels():
        assert tagger.parse_label(f"  {label.title()}. ") == label
    assert tagger.parse_label("I am not going to answer that") == "other"
    assert tagger.parse_label("") == "other"


def test_the_frozen_tagger_config_matches_its_live_owners():
    frozen = tagger.load_frozen()
    assert tagger.config_drift(frozen) == []
    assert tagger.assert_frozen(frozen)["prompt_sha256"] == tagger.prompt_sha256()
    drifted = dict(frozen, prompt_sha256="0" * 64)
    assert tagger.config_drift(drifted) == ["prompt_sha256"]
    try:
        tagger.assert_frozen(drifted)
    except tagger.ConfigDrift as error:
        assert "re-freeze" in str(error)
    else:
        raise AssertionError("a drifted tagging instrument did not fail closed")


def test_the_tagger_cli_is_prepared_and_refuses_to_generate_without_the_flag():
    completed = subprocess.run(
        [sys.executable, "scripts/deep/alexandria_topic_tag.py"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    report = json.loads(completed.stdout)
    assert report["ran"] is False
    assert report["prepared"] is True
    assert report["frozen_config"]["prompt_sha256"] == tagger.prompt_sha256()
