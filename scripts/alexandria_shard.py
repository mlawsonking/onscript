"""Run ONE Alexandria per-Congress shard in a fresh process (memory released on exit).

  python scripts/alexandria_shard.py 118
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import alexandria  # noqa: E402

n = int(sys.argv[1])
s, e = alexandria.congress_range(n)
print(f"[alexandria] shard {n} ({s} -> {e}) …", flush=True)
res = alexandria.run_shard(n)
print(f"[alexandria] shard {n}: {res}", flush=True)
