"""Golden-set tone regression (§Session-8). The deterministic composer's output on a frozen set of
representative inputs must not drift; if it does, a prompt/composer change altered the voice and the
change must be conscious. If this fails after an INTENTIONAL voice change, re-freeze:

  python scripts/golden_render.py --freeze
"""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

from pipeline import distill  # noqa: E402
import golden_render  # noqa: E402

GOLDEN = _ROOT / "tests" / "golden" / "deterministic.json"


def test_deterministic_voice_matches_golden_and_stays_in_register():
    g = json.loads(GOLDEN.read_text(encoding="utf-8"))
    for name, expected in g["deterministic"].items():
        got = golden_render.render(golden_render.FIXTURES[name])
        assert got == expected, (
            f"golden drift on {name!r} — if this voice change is intentional, re-run "
            f"`python scripts/golden_render.py --freeze`.\n  expected: {expected!r}\n  got:      {got!r}")
        assert distill.register_violations(got) == [], (name, distill.register_violations(got))


def test_register_guard_catches_out_of_voice_drift():
    assert any("exclamation" in v for v in distill.register_violations("We won today!"))
    assert distill.register_violations("Big news 🎉 #OnScript")                      # emoji + hashtag
    assert any("schema" in v for v in distill.register_violations("the top phrase is null"))
    assert distill.register_violations("Today 51 of us released statements.") == []  # clean deadpan
