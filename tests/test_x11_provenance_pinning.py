"""X11 acceptance tests for source and runtime provenance."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline import fetch, run_collect, runtime_environment, util


ROOT = Path(__file__).resolve().parents[1]
REVISION = "1" * 40


def test_collect_manifest_names_commit_hash_etag_and_collection_time():
    old_derived = run_collect.config.DERIVED
    originals = {
        "freshness": fetch.upstream_freshness,
        "pull_range": fetch.pull_range,
        "load_mirror": fetch.load_mirror,
        "roster": run_collect.roster.load,
        "deterministic": run_collect.deterministic.run,
    }
    statement = {"id": "s1", "published_at": "2026-07-24", "lane": 1,
                 "member": {"bioguide": "B1", "party": "D"}}
    provenance = {
        "upstream_commit": REVISION,
        "months_missing": 0,
        "collected_at": "2026-07-27T12:00:00Z",
        "files": [{
            "path": "data/2026/2026-07.jsonl", "content_sha256": "a" * 64,
            "etag": '"etag-value"', "collected_at": "2026-07-27T12:00:00Z",
        }],
    }
    with TemporaryDirectory() as td:
        run_collect.config.DERIVED = Path(td)
        fetch.upstream_freshness = lambda: {"ok": True, "age_hours": 1}
        fetch.pull_range = lambda _start, _end: ([statement], provenance)
        fetch.load_mirror = lambda: [statement]
        run_collect.roster.load = lambda: {}
        run_collect.deterministic.run = lambda *args, **kwargs: {
            "statements": [statement], "focus_day": "2026-07-24", "ledger": {},
            "manifest": {"days_present": ["2026-07-24"], "normalize": {}, "phrase_engine": {}},
        }
        try:
            manifest = run_collect.collect(
                offline=False, start="2026-07-01", end="2026-07-24",
                focus_day="2026-07-24", do_extract=False,
            )["manifest"]
        finally:
            run_collect.config.DERIVED = old_derived
            fetch.upstream_freshness = originals["freshness"]
            fetch.pull_range = originals["pull_range"]
            fetch.load_mirror = originals["load_mirror"]
            run_collect.roster.load = originals["roster"]
            run_collect.deterministic.run = originals["deterministic"]
    assert manifest["upstream_provenance"] == provenance
    assert manifest["runtime_environment"]["timezone"] == "America/New_York"
    assert manifest["runtime_environment"]["locale"] == "C"


def test_pinned_fetch_hashes_the_exact_response_and_keeps_etag():
    old_mirror, old_get = fetch.MIRROR, util.http_get_metadata
    raw = b'{"id":"one"}\n'
    with TemporaryDirectory() as td:
        fetch.MIRROR = Path(td)
        util.http_get_metadata = lambda *_args, **_kwargs: (raw, {"etag": '"abc"'})
        try:
            rows, provenance = fetch._fetch_month(2026, 7, REVISION)
        finally:
            fetch.MIRROR, util.http_get_metadata = old_mirror, old_get
    assert rows == [{"id": "one"}]
    assert f"/{REVISION}/" in provenance["url"]
    assert provenance["content_sha256"] == hashlib.sha256(raw).hexdigest()
    assert provenance["etag"] == '"abc"'


def test_both_2026_dst_transition_days_use_the_pinned_day_boundary():
    assert util.product_day(datetime(2026, 3, 9, 5, tzinfo=timezone.utc)) == "2026-03-08"
    assert util.product_day(datetime(2026, 11, 2, 5, tzinfo=timezone.utc)) == "2026-11-01"
    environment = runtime_environment.disclosure()
    assert environment["timezone_file_sha256"] and len(environment["timezone_file_sha256"]) == 64
    assert environment["day_boundary"] == "prior America/New_York calendar day"


def test_real_committed_raw_shard_has_reproducible_offline_provenance():
    provenance = fetch.mirror_provenance()
    target = next(row for row in provenance["files"] if row["path"].endswith("2026-07.jsonl"))
    path = ROOT / target["path"]
    assert target["content_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert target["etag"] is None and target["collected_at"] is None


def test_sbom_and_native_attestation_are_committed_and_pinned():
    sbom = json.loads((ROOT / "sbom.spdx.json").read_text(encoding="utf-8"))
    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert {row["name"] for row in sbom["packages"]} == {
        "OnScript deterministic pipeline", "CPython"
    }
    site_source = (ROOT / "pipeline/site.py").read_text(encoding="utf-8")
    assert 'shutil.copyfile(SBOM_SOURCE, OUT / "sbom.spdx.json")' in site_source
    for name in ("collect.yml", "assemble.yml"):
        workflow = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
        assert "attestations: write" in workflow and "id-token: write" in workflow
        assert "actions/attest-build-provenance@e8998f949152b193b063cb0ec769d69d929409be" in workflow
