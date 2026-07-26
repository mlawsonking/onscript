"""W11 acceptance tests for workflow, archive, and release hardening."""
from __future__ import annotations

import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

from pipeline import archive_restore, release_provenance


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"


def test_every_third_party_action_is_pinned_to_a_full_sha():
    references = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "uses:" not in line:
                continue
            reference = line.split("uses:", 1)[1].split("#", 1)[0].strip()
            if reference.startswith("./"):
                continue
            references.append((path.name, reference))
    assert references
    assert all(re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", reference)
               for _path, reference in references), references


def test_workflows_declare_minimum_permissions_and_posting_is_separate():
    assemble = (WORKFLOWS / "assemble.yml").read_text(encoding="utf-8")
    posting = (WORKFLOWS / "post.yml").read_text(encoding="utf-8")
    assert "pipeline/post_bluesky.py" not in assemble
    assert "pipeline/post_bluesky.py" in posting
    assert 'workflows: ["RUN B assemble"]' in posting
    assert "contents: write" in posting
    for name in ("announce.yml", "assemble.yml", "collect.yml", "post.yml", "watchdog.yml"):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert re.search(r"(?m)^permissions:\s*$", text), name


def test_traversal_archive_is_rejected_before_checkout_write():
    with tempfile.TemporaryDirectory(prefix="onscript-w11-") as name:
        root = Path(name)
        archive = root / "state.tar.gz"
        payload = b"escape"
        with tarfile.open(archive, "w:gz") as bundle:
            member = tarfile.TarInfo("data/state/../../escape.txt")
            member.size = len(payload)
            bundle.addfile(member, io.BytesIO(payload))
        checkout = root / "checkout"
        try:
            archive_restore.restore_archive(archive, checkout)
        except ValueError as error:
            assert "unsafe archive member" in str(error)
        else:
            raise AssertionError("traversal archive was accepted")
        assert not (root / "escape.txt").exists()


def test_release_sidecar_detects_tampering():
    with tempfile.TemporaryDirectory(prefix="onscript-w11-") as name:
        asset = Path(name) / "state.tar.gz"
        asset.write_bytes(b"release payload")
        sidecar = release_provenance.write_sidecar(asset)
        assert sidecar.name == "state.tar.gz.sha256"
        assert release_provenance.verify_sidecar(asset)
        asset.write_bytes(b"changed payload")
        assert not release_provenance.verify_sidecar(asset)


def test_clean_clone_subset_is_byte_reproducible():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/reproduce_subset.py")],
        cwd=ROOT, check=True, capture_output=True,
    )
    result = json.loads(completed.stdout)
    assert result["byte_identical"] is True
    assert result["first_sha256"] == result["second_sha256"]


def test_environment_and_legal_placeholders_are_present():
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12.10"
    assert "no third-party" in (ROOT / "requirements.lock").read_text(encoding="utf-8").lower()
    provenance = (ROOT / "docs/32-RELEASE-PROVENANCE.md").read_text(encoding="utf-8")
    assert "Unicode Character Database 15.0.0" in provenance
    for name in ("LICENSE-CODE", "LICENSE-DATA", "LICENSE-CONTENT"):
        assert "ATTORNEY REVIEW PENDING" in (ROOT / name).read_text(encoding="utf-8")
    assert (ROOT / "SECURITY.md").is_file() and (ROOT / "CITATION.cff").is_file()


def test_workflows_publish_checksum_sidecars():
    collect = (WORKFLOWS / "collect.yml").read_text(encoding="utf-8")
    assemble = (WORKFLOWS / "assemble.yml").read_text(encoding="utf-8")
    assert "pipeline.release_provenance write state.tar.gz raw.tar.gz" in collect
    assert "state.tar.gz.sha256 raw.tar.gz raw.tar.gz.sha256" in collect
    assert "pipeline.release_provenance write state.tar.gz" in assemble
    assert "state.tar.gz.sha256" in assemble
