"""S74-11 Package 3 (F3): the fingerprinted minimum stratum size is real.

config.BOILERPLATE_DF_MIN_DOCS (40) was published in the instrument fingerprint and read by no
code, so a (congress, party) stratum of a handful of documents could delete a phrase from the
whole ledger. This is not a threshold change: the value and its fingerprint entry are unchanged;
the code now reads it.
"""
from __future__ import annotations

import ast
from pathlib import Path

from pipeline import config, instrument_fingerprint, phrases

ROOT = Path(__file__).resolve().parents[1]
PHRASE = "we will lower the cost of insulin for every family"


def _stmt(i, text, *, day, congress, party="D", bioguide=None):
    return {"id": f"sha256:{congress}-{i}", "text": text, "published_at": day, "lane": 1,
            "syndicated": False, "congress": congress,
            "member": {"bioguide": bioguide or f"M{congress}{i:04d}", "party": party}}


def _corpus() -> list[dict]:
    """A 200-document congress-119 stratum (the phrase in 3 of them, three offices, one day: 1.5
    percent, well under the 5 percent cap) and a 10-document congress-120 stratum where the phrase
    appears in 2 (20 percent), the shape of the first days of a new Congress."""
    rows = [_stmt(i, f"Today {PHRASE}.", day="2026-12-30", congress=119, bioguide=f"A{i}")
            for i in range(3)]
    rows += [_stmt(i, f"We support local road project number {i} in our district.", day="2026-12-30",
                   congress=119) for i in range(3, 200)]
    rows += [_stmt(i, f"Again {PHRASE}.", day="2027-01-04", congress=120, bioguide=f"A{i}")
             for i in range(2)]
    rows += [_stmt(i, f"The new session opens with project number {i} for our state.", day="2027-01-04",
                   congress=120) for i in range(2, 10)]
    return rows


def test_a_stratum_below_the_minimum_cannot_delete_a_phrase_ledger_wide():
    assert config.BOILERPLATE_DF_MIN_DOCS == 40  # the published value, unchanged
    engine = phrases.PhraseEngine()
    ledger = engine.build(_corpus())
    assert engine.docs_in_stratum[(119, "D")] == 200 and engine.docs_in_stratum[(120, "D")] == 10
    hits = [k for k in ledger if "cost of insulin" in k]
    assert hits, "the phrase must survive: only a 10-document stratum exceeds the share cap"
    row = ledger[max(hits, key=len)]
    assert row["daily"]["2026-12-30"]["D"] == 3
    assert row["df_weight"] == round(1 - 3 / 200, 3)  # the share comes from the stratum that votes


def test_a_stratum_at_the_minimum_still_suppresses():
    """The cap is unchanged where it applies: the same phrase in 2 of a 40-document stratum (5.0
    percent) survives, in 3 of 40 (7.5 percent) it is boilerplate."""
    for carriers, survives in ((2, True), (3, False)):
        rows = [_stmt(i, f"Today {PHRASE}.", day="2026-12-30", congress=119, bioguide=f"A{i}")
                for i in range(3)]
        rows += [_stmt(i, f"We support local road project number {i} in our district.", day="2026-12-30",
                       congress=119) for i in range(3, 200)]
        rows += [_stmt(i, f"Again {PHRASE}.", day="2027-01-04", congress=120, bioguide=f"B{i}")
                 for i in range(carriers)]
        rows += [_stmt(i, f"The new session opens with project number {i} for our state.",
                       day="2027-01-04", congress=120) for i in range(carriers, 40)]
        ledger = phrases.PhraseEngine().build(rows)
        assert bool([k for k in ledger if "cost of insulin" in k]) is survives, carriers


def test_the_phrase_ledger_method_version_is_registered_at_its_owner():
    versions = instrument_fingerprint.method_versions()
    assert versions["phrase_ledger"] == phrases.METHOD_VERSION == "phrase-ledger-v2"


def _config_reads(tree: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "config":
            names.add(node.attr)
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[-1] == "config":
            names.update(alias.name for alias in node.names)
    return names


def test_every_fingerprinted_setting_is_read_by_a_live_module():
    """docs/37 rule 1: the registry is tested against its owners. Every name in
    instrument_fingerprint.LIVE_THRESHOLD_NAMES must be read by at least one pipeline module
    other than config and the fingerprint itself, so the fingerprint can never again attest a
    setting no code reads. (LEGACY_THRESHOLD_NAMES is the declared compatibility list, kept only
    to reproduce the prior symmetry component, and is out of scope by its own comment.)"""
    reads: dict[str, set[str]] = {}
    for path in sorted((ROOT / "pipeline").rglob("*.py")):
        if path.name in ("config.py", "instrument_fingerprint.py"):
            continue
        for name in _config_reads(ast.parse(path.read_text(encoding="utf-8"))):
            reads.setdefault(name, set()).add(path.relative_to(ROOT).as_posix())
    unread = [name for name in instrument_fingerprint.LIVE_THRESHOLD_NAMES if not reads.get(name)]
    assert not unread, unread
    assert "pipeline/phrases.py" in reads["BOILERPLATE_DF_MIN_DOCS"]
    # Every fingerprinted name is a live config attribute, so a rename cannot leave a ghost entry.
    assert all(hasattr(config, name) for name in instrument_fingerprint.LIVE_THRESHOLD_NAMES)
