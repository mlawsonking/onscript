"""W3 publication immutability, safe restore, and structured corrections."""
from __future__ import annotations

import io
import json
import tarfile
import tempfile
from pathlib import Path

from pipeline import archive_restore, config, corrections, site


ROOT = Path(__file__).resolve().parent.parent


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _archive(path: Path, rows: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:gz") as bundle:
        for name, payload in rows.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            bundle.addfile(info, io.BytesIO(payload))


def test_stale_archive_conflict_fails_before_any_checkout_write():
    with tempfile.TemporaryDirectory(prefix="onscript-w3-") as name:
        root = Path(name)
        checkout = root / "checkout"
        authority = checkout / "data/reference/corrections.json"
        runtime = checkout / "data/state/ledger.json"
        _write(authority, b"new repository corrections")
        _write(runtime, b"current runtime state")
        archive = root / "state.tar.gz"
        _archive(archive, {
            "data/state/ledger.json": b"stale runtime state",
            "data/reference/corrections.json": b"stale corrections",
        })

        try:
            archive_restore.restore_archive(archive, checkout)
        except ValueError as error:
            assert "repository authority" in str(error)
        else:
            raise AssertionError("stale tracked reference data was accepted")
        assert authority.read_bytes() == b"new repository corrections"
        assert runtime.read_bytes() == b"current runtime state"


def test_valid_archive_merges_only_runtime_allowlist():
    with tempfile.TemporaryDirectory(prefix="onscript-w3-") as name:
        root = Path(name)
        checkout = root / "checkout"
        authority = checkout / "data/reference/corrections.json"
        _write(authority, b"same corrections")
        archive = root / "state.tar.gz"
        _archive(archive, {
            "data/state/ledger.json": b"restored ledger",
            "data/reference/roster.json": b"restored roster",
            "data/reference/corrections.json": b"same corrections",
        })
        merged = archive_restore.restore_archive(archive, checkout)
        assert merged == ["data/reference/roster.json", "data/state/ledger.json"]
        assert authority.read_bytes() == b"same corrections"
        assert (checkout / "data/state/ledger.json").read_bytes() == b"restored ledger"


def test_archive_member_outside_allowlist_is_rejected():
    with tempfile.TemporaryDirectory(prefix="onscript-w3-") as name:
        root = Path(name)
        archive = root / "state.tar.gz"
        _archive(archive, {"../checkout/data/reference/corrections.json": b"rollback"})
        try:
            archive_restore.restore_archive(archive, root / "checkout")
        except ValueError as error:
            assert "unsafe archive member" in str(error)
        else:
            raise AssertionError("path traversal member was accepted")


def test_publication_content_address_and_revision_chain_are_monotonic():
    first_payload = {"day": "2026-07-24", "value": 1}
    first = corrections.publication_fields(first_payload, {}, [])
    assert first["publication_state"] == "published"
    assert first["revision"] == 1
    assert first["revision_chain"][-1]["content_address"] == first["content_address"]

    unchanged = corrections.publication_fields(first_payload, first, [])
    assert unchanged["revision"] == 1
    assert unchanged["revision_chain"] == first["revision_chain"]

    correction = [{"correction_id": "corr-test"}]
    revised = corrections.publication_fields(
        {"day": "2026-07-24", "value": 2}, unchanged, correction
    )
    assert revised["publication_state"] == "corrected"
    assert revised["revision"] == 2
    assert revised["revision_chain"][1]["supersedes"] == first["content_address"]


def test_correction_count_checkpoint_rejects_a_removed_entry():
    rows = corrections.load()
    checkpoint = json.loads(
        (config.REFERENCE / "corrections-count.json").read_text(encoding="utf-8")
    )
    assert checkpoint["count"] == len(rows) == 5
    try:
        corrections.validate(rows[:-1], expected_count=checkpoint["count"])
    except ValueError as error:
        assert "corrections count changed" in str(error)
    else:
        raise AssertionError("a decreased correction count was accepted")


def test_correction_pages_feed_and_affected_day_link_use_stable_ids():
    rows = corrections.load()
    row = rows[-1]
    body = site.correction_permalink_body(row)
    index = site.corrections_index_body(rows)
    feed = site.corrections_feed(rows)
    day = site.day_corrections("2026-07-22", 1)
    for rendered in (body, index, feed, day):
        assert row["correction_id"] in rendered
    assert "Severity:" in body and "Status:" in body
    assert "Page URL:" in index and "Exact sentence or figure:" in index


def test_correction_reply_matches_p4_and_has_no_posting_path():
    text = corrections.correction_reply(
        "2026-07-25", "five offices carried the phrase", "three offices carried the phrase",
        "https://onscript.news/corrections/corr-example.html",
    )
    assert text == (
        "Correction (2026-07-25): we said five offices carried the phrase; the receipts supported "
        "three offices carried the phrase. The claim is retracted and the log updated: "
        "https://onscript.news/corrections/corr-example.html."
    )


def test_workflows_restore_through_the_validator_not_over_the_checkout():
    for name in ("collect.yml", "assemble.yml"):
        source = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
        assert source.count("python -m pipeline.archive_restore data/_restore --checkout .") == 1
        assert "tar -xzf data/_restore" not in source
        assert "git checkout -- data/reference" not in source
