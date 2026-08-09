"""P3: the clean-statement scan cache is verdict preserving at production shape.

A performance change that alters a published number is not a performance change, it is a silent
instrument change. So the cache is held to byte identity of the LEDGER, not just of a span list:
cold cache, warm cache and no cache must produce the same bytes over the same corpus.

The real-artifact corpus is the published day files under data/derived/days (docs/37 rule 2:
fixtures prove the logic, only production-shaped data proves the integration). They are used as
INPUT, never as an expected output. Nothing here asserts that a committed file equals a fresh
build, which is the trap docs/37 rule 3 names, so a later data commit cannot turn this red.
"""
from __future__ import annotations

import glob
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import privacy, scan_cache  # noqa: E402
from pipeline.phrases import PhraseEngine  # noqa: E402
from tests.test_privacy import PERSON_A, PERSON_B, gate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def real_committed_prose(limit: int = 120) -> list[str]:
    """Real published prose from the committed derived tree: composites, quotes, phrase labels."""
    out: list[str] = []

    def walk(node):
        if isinstance(node, str):
            if len(node) > 60:
                out.append(node)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for path in sorted(glob.glob(str(ROOT / "data" / "derived" / "days" / "*.json"))):
        walk(json.loads(Path(path).read_text(encoding="utf-8")))
        if len(out) >= limit:
            break
    return out[:limit]


def corpus_from(texts: list[str], *, contaminate: bool = False) -> list[dict]:
    """Wrap prose as a Lane-1 statement corpus the engine will actually walk."""
    parties = ("D", "R")
    statements = []
    for index, text in enumerate(texts):
        body = text
        if contaminate and index % 7 == 3:
            body = f"{text} Accountability for {PERSON_A} and {PERSON_B} joan remains open."
        statements.append({
            "id": f"sha256:p3-{index:04d}",
            "text": body,
            "published_at": f"2026-06-{(index % 28) + 1:02d}",
            "lane": 1,
            "syndicated": False,
            "congress": 119,
            "member": {"bioguide": f"P{index % 11:03d}", "party": parties[index % 2]},
        })
    return statements


def _ledger_bytes(statements: list[dict]) -> bytes:
    ledger = PhraseEngine().build(statements)
    return json.dumps(ledger, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _build_cache_off(statements) -> bytes:
    scan_cache.deactivate()
    return _ledger_bytes(statements)


def _build_cache_on(statements, path: Path, *, warm: bool) -> tuple[bytes, dict]:
    privacy.activate_scan_cache(path=path)
    try:
        if warm:
            assert scan_cache.stats()["loaded"] > 0, "the warm build found no prior verdicts"
        out = _ledger_bytes(statements)
        privacy.flush_scan_cache(path=path)
        return out, scan_cache.stats()
    finally:
        scan_cache.deactivate()


def test_the_ledger_is_byte_identical_cache_on_and_off_over_a_fixture_corpus():
    """Cold cache, warm cache and no cache must all produce the same ledger bytes. The corpus is
    contaminated on purpose: a cache that only preserved verdicts for clean text would be a cache
    that changed the answer for exactly the statements Article XIII exists to protect."""
    filler = [f"our district deserves reliable transit funding in fiscal year {y} and beyond"
              for y in range(2026, 2126)]
    statements = corpus_from(filler, contaminate=True)
    with tempfile.TemporaryDirectory() as raw, gate():
        path = Path(raw) / scan_cache.CACHE_BASENAME
        off = _build_cache_off(statements)
        cold, cold_stats = _build_cache_on(statements, path, warm=False)
        warm, warm_stats = _build_cache_on(statements, path, warm=True)
        assert off == cold == warm
        assert cold_stats["misses"] > 0, "the cold build must have scanned"
        assert warm_stats["hits"] > 0, "the warm build must have served cached verdicts"


def test_the_ledger_is_byte_identical_cache_on_and_off_over_real_committed_prose():
    """docs/37 rule 2. This walks prose the pipeline actually published."""
    texts = real_committed_prose()
    assert len(texts) >= 40, f"expected real committed prose to walk, found {len(texts)}"
    statements = corpus_from(texts, contaminate=True)
    with tempfile.TemporaryDirectory() as raw, gate():
        path = Path(raw) / scan_cache.CACHE_BASENAME
        off = _build_cache_off(statements)
        cold, _ = _build_cache_on(statements, path, warm=False)
        warm, warm_stats = _build_cache_on(statements, path, warm=True)
        assert off == cold == warm
        assert warm_stats["hits"] > 0


def test_a_second_warm_run_over_an_append_only_corpus_serves_every_prior_verdict():
    """The shape the daily collect actually has: yesterday's corpus plus today's statements. The
    old statements must hit and the new ones must be scanned, or the cache is not doing the job
    the 2026-07-28/29 timeouts asked for."""
    yesterday = corpus_from(real_committed_prose(limit=60))
    today = corpus_from([f"a new statement about rural broadband access number {i}"
                         for i in range(12)])
    for index, statement in enumerate(today):
        statement["id"] = f"sha256:new-{index:04d}"

    with tempfile.TemporaryDirectory() as raw, gate():
        path = Path(raw) / scan_cache.CACHE_BASENAME
        _build_cache_on(yesterday, path, warm=False)
        _, stats = _build_cache_on(yesterday + today, path, warm=True)
        assert stats["hits"] > 0 and stats["misses"] > 0, stats
        # Every text carried forward was served; only the genuinely new ones were scanned.
        assert stats["hits"] >= len(yesterday), stats
