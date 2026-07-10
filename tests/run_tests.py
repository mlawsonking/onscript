"""Minimal test runner so the suite works without pytest installed.

  python tests/run_tests.py        # runs every test_* function in tests/test_*.py
(pytest also discovers these files normally.)
"""
import importlib.util
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))


def main() -> int:
    passed = failed = 0
    failures = []
    for f in sorted(HERE.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(f.stem, f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        for name in dir(mod):
            if name.startswith("test_"):
                fn = getattr(mod, name)
                if callable(fn):
                    try:
                        fn()
                        passed += 1
                        print(f"  PASS {f.stem}::{name}")
                    except Exception as e:  # noqa: BLE001
                        failed += 1
                        failures.append((f.stem, name, e, traceback.format_exc()))
                        print(f"  FAIL {f.stem}::{name}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    for stem, name, e, tb in failures:
        print(f"\n--- {stem}::{name} ---\n{tb}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
