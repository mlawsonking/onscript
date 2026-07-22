"""D2 regression tests: the signed archive must only authenticate proven live content."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from pipeline import site


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "assemble.yml"


def _manifest_tree(tmp_path: Path, results: list[dict]) -> Path:
    derived = tmp_path / "derived"
    manifest_dir = derived / "manifest"
    manifest_dir.mkdir(parents=True)
    payload = {
        "day": "2026-07-21",
        "generated_at": "2026-07-22T13:01:00Z",
        "results": results,
    }
    (manifest_dir / "post-2026-07-21.json").write_text(json.dumps(payload), encoding="utf-8")
    return derived


def _load_threads(results: list[dict]) -> list[dict]:
    with tempfile.TemporaryDirectory() as td:
        derived = _manifest_tree(Path(td), results)
        old = site.DERIVED
        site.DERIVED = derived
        try:
            return site.posted_threads()
        finally:
            site.DERIVED = old


def test_partial_manifest_renders_only_proven_root_link():
    threads = _load_threads([{
        "party": "D", "posted": True, "partial": True,
        "root_uri": "at://did:plc:partial/app.bsky.feed.post/root",
        "thread": ["root text", "INTENDED REPLY THAT NEVER WENT LIVE"],
    }])

    html = site.posts_log_body(threads)
    assert "partial" in html.lower()
    assert "bsky.app/profile/did:plc:partial/post/root" in html
    assert "root text" not in html
    assert "INTENDED REPLY THAT NEVER WENT LIVE" not in html


def test_posted_manifest_without_root_is_explicitly_unverifiable():
    threads = _load_threads([{
        "party": "R", "posted": True,
        "thread": ["INTENDED TEXT WITH NO PROVABLE ROOT"],
    }])

    html = site.posts_log_body(threads)
    assert "unverifiable" in html.lower()
    assert "INTENDED TEXT WITH NO PROVABLE ROOT" not in html


def test_complete_manifest_with_root_renders_as_authenticated():
    threads = _load_threads([{
        "party": "D", "posted": True,
        "root_uri": "at://did:plc:complete/app.bsky.feed.post/root",
        "thread": ["PROVEN ROOT", "PROVEN REPLY"],
    }])

    html = site.posts_log_body(threads)
    assert "authenticated" in html.lower()
    assert "PROVEN ROOT" in html and "PROVEN REPLY" in html


def test_assemble_workflow_has_two_ordered_fresh_process_renders():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    render = "python pipeline/site.py"
    post = "python pipeline/post_bluesky.py"
    commit = "git add data/derived site/public"
    persist = "gh release upload data-latest state.tar.gz"
    redact = "python -m pipeline.redact data/state data/reference"

    assert workflow.count(render) == 2
    first, second = [i for i in range(len(workflow)) if workflow.startswith(render, i)]
    assert first < workflow.index(post) < second < workflow.index(commit)
    assert workflow.index(redact) < workflow.index(persist)
    assert "mktemp -d" in workflow
    assert "POST_ARCHIVE_REFRESH_FAILED" in workflow
    assert "cp -a site/public/." in workflow
    assert "cp -a \"$snapshot/.\" site/public/" in workflow
