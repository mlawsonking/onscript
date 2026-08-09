"""H2: no operator machine identifier reaches the public tree.

The repository and the site are public. A user-home path in a tracked file discloses the
operator's account name and the layout of a private machine, and in a generated manifest it is
also a false claim: the artifact does not belong to that directory, it belongs to the repository.

This guard scans every tracked text file rather than a curated list, because the leak has never
arrived where anyone was looking. The H1 survey found it in two committed manifests, four
generators, two runbook command blocks, and a spec's file list.

Two details the H1 survey turned up the hard way, both encoded in PATTERN below:

- JSON escapes the separator, so a manifest carries ``C:\\\\Users\\\\name`` on disk. A pattern
  written for the single-backslash form silently misses every committed JSON manifest, which is
  exactly the class of file most likely to be machine-stamped by a generator.
- The same tree mixes separators. ``C:/Users/name`` appears in command strings next to
  ``C:\\Users\\name`` in prose.

The allowlist is deliberately small and each entry states why the line is not a defect. It keys
on the file and the number of hits in it, so an allowlisted file that gains a NEW identifier
still fails. Stale entries fail too: an allowlist nobody has to maintain is an allowlist that
stops describing the tree.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# A user-home root in any of the forms this tree actually produces: either separator, and the
# doubled backslash that JSON encoding leaves behind.
PATTERN = re.compile(r"(?i)[a-z]:[\\/]{1,2}Users[\\/]{1,2}|/home/|/Users/")

# path -> (expected hits, why this line is not a defect)
ALLOWLIST: dict[str, tuple[int, str]] = {
    "pipeline/util.py": (
        1,
        "Defines the home-prefix regex that artifact_path() scrubs. The string is the detector.",
    ),
    "tests/test_h2_path_hygiene.py": (
        10,
        "Defines this guard's own pattern, the shapes it documents, and the fixtures that prove "
        "it catches them. Every account name in them is the literal 'someone'. Adding a fixture "
        "moves this count and fails the guard on purpose: the number is the thing that keeps the "
        "exemption from widening quietly.",
    ),
    "delivery/DEEP-packet.md": (
        2,
        "Pinned history (docs/37 rule 3). The two paths are the evidence for the isolation claim: "
        "the delivery ran in one checkout while an active worker owned the other. Replacing them "
        "with a placeholder would delete the fact the section exists to record.",
    ),
    # docs/16-NOMENCLATURE-SPEC.md was allowlisted here as pinned provenance until S66-7. The
    # exemption did not survive reading it: the path pointed at a throwaway scratchpad, and
    # "synth1.py through synth5.py, written to that session's scratchpad outside the repository"
    # records the same fact without publishing an account name and a private directory layout.
    # An exemption is worth keeping only when the identifier is the evidence, as it is for the
    # DEEP packet's two checkouts, whose whole claim is that they were two different checkouts.
}


def tracked_text_files() -> list[Path]:
    """Every tracked file that decodes as text. Tracked, so the scan matches what is published."""
    listing = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True,
                             capture_output=True)
    files = []
    for name in listing.stdout.decode("utf-8").split("\0"):
        if not name:
            continue
        path = ROOT / name
        if not path.is_file():  # a submodule or a path removed from the working tree
            continue
        try:
            path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary asset; a home path in one is not a disclosure anyone can read
        files.append(path)
    return files


def scan() -> dict[str, list[tuple[int, str]]]:
    """Every tracked text file's home-path hits, keyed by repo-relative posix path."""
    hits: dict[str, list[tuple[int, str]]] = {}
    for path in tracked_text_files():
        found = []
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if PATTERN.search(line):
                found.append((number, line.strip()))
        if found:
            hits[path.relative_to(ROOT).as_posix()] = found
    return hits


def test_no_tracked_file_carries_an_unallowlisted_operator_path():
    unexpected = []
    for name, found in sorted(scan().items()):
        allowed = ALLOWLIST.get(name)
        if allowed is None:
            unexpected.append(f"{name}: {len(found)} hit(s), first at line {found[0][0]}: "
                              f"{found[0][1][:100]}")
        elif len(found) != allowed[0]:
            unexpected.append(f"{name}: {len(found)} hit(s), allowlist expects {allowed[0]}; "
                              f"lines {[number for number, _ in found]}")
    assert not unexpected, (
        "operator machine identifiers in the public tree (docs/37 rule 16). Store a repo-relative "
        "path or a neutral placeholder in the generator, or add a reasoned allowlist entry:\n  "
        + "\n  ".join(unexpected))


def test_the_allowlist_has_no_stale_entries():
    """A registry is only load bearing while it matches its subject (docs/37 rule 1)."""
    found = scan()
    stale = [name for name in ALLOWLIST if name not in found]
    assert not stale, (
        f"allowlist entries whose file no longer carries the identifier: {stale}. "
        "Remove them; a permanent exemption for a healed line hides the next real one.")


def test_every_allowlist_entry_states_a_reason():
    for name, (count, reason) in ALLOWLIST.items():
        assert count > 0, f"{name}: an allowlist entry for zero hits exempts nothing"
        assert len(reason.split()) >= 8, (
            f"{name}: the reason must say why the line is not a defect, not merely that it exists")


def test_the_pattern_catches_every_shape_the_tree_produces():
    """The negative controls are the shapes that already slipped past a narrower pattern."""
    must_match = [
        r"CLAUDE = r'C:\Users\someone\.local\bin\claude.exe'",       # Windows, backslash
        r'"path": "C:\\Users\\someone\\projects\\onscript"',          # the JSON-escaped form
        "venv at C:/Users/someone/venvs/onscript-embed",              # Windows, forward slash
        "the store lives in /home/someone/onscript",                  # Linux
        "the store lives in /Users/someone/onscript",                 # macOS
        "D:\\Users\\someone\\onscript",                               # a drive letter that is not C
    ]
    for case in must_match:
        assert PATTERN.search(case), f"pattern missed a real shape: {case}"

    must_not_match = [
        "C:\\ProgramData\\miniconda3\\python.exe",   # the sanctioned interpreter, not a home path
        "X:\\onscript-data\\alexandria\\embeddings",  # the data volume, deliberately outside
        "data/derived/replay/evidence.jsonl",         # what artifact_path() now writes
        "<embed-venv>/Scripts/python.exe",            # the neutral placeholder
        "the user's home directory",                  # prose about homes is not a path
    ]
    for case in must_not_match:
        assert not PATTERN.search(case), f"pattern fired on a clean string: {case}"


def test_the_generator_helper_neutralizes_both_inside_and_outside_the_repository():
    """artifact_path() is what keeps new manifests clean; H1 fixed the tree, this keeps it fixed."""
    from pipeline import config, util

    inside = util.artifact_path(config.DERIVED / "replay" / "evidence.jsonl")
    assert inside == "data/derived/replay/evidence.jsonl", inside
    assert not PATTERN.search(inside)

    outside = util.artifact_path(Path("C:/Users/someone/venvs/onscript-embed/pyvenv.cfg"))
    assert not PATTERN.search(outside), outside
    assert outside.endswith("venvs/onscript-embed/pyvenv.cfg"), outside
