"""Build the committed verification manifest for the Alexandria embedding store.

The vectors themselves never enter the repository: they are 837,040 rows of append-only store on
X:, and docs/34 section 5 keeps them there. What the repository carries is this manifest, which
is what makes a claim about the vectors checkable by someone who cannot see them: per-shard row
counts, the id-list content address, the model identity that produced them, the wall time, and
the command that resumes or reproduces the pass.

It also reconciles against the precondition gate. docs/34 section 1 fixes the embeddable unit
counts at 684,853 press statements and 152,187 CREC E-statements. A shard total that disagrees
means the vector store and the ledger describe different corpora, which is the one failure this
manifest exists to make loud rather than silent.

Read-only, CPU-only, $0. It starts no GPU and writes no vector.

  python scripts/deep/alexandria_embed_manifest.py --out data/reference/alexandria-embeddings-manifest.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import config, util  # noqa: E402
from scripts.deep import alexandria_embed as embed  # noqa: E402

MANIFEST_SCHEMA = 1
METHOD_VERSION = "alexandria-embed-manifest-v1"

# docs/34 section 1, verified READY on 2026-07-27 and again on 2026-07-28 by
# scripts/deep/alexandria_stage2_verify.py.
GATE_UNITS = {"press": 684853, "crec": 152187}

# What is actually in scope for the pass, which covers congresses 107 through 119. The CREC lane
# carries 15 rows dated to congress 106, a pre-2001 boundary sliver docs/34 section 1 says to
# ignore, so the in-scope CREC total is 15 below the gate total. Naming the difference here is
# the point: an unexplained delta of -15 and a documented exclusion of exactly 15 rows look
# identical in a row count, and only one of them is fine.
OUT_OF_SCOPE = {"press": {}, "crec": {"congress_106_boundary_sliver": 15}}
EXPECTED_UNITS = {lane: GATE_UNITS[lane] - sum(OUT_OF_SCOPE[lane].values())
                  for lane in GATE_UNITS}

# The interpreter is named as a placeholder, not an operator path: the GPU venv lives outside the
# repository (docs/34 section 3.1) and its location differs per machine. docs/37 rule 16 keeps
# operator machine identifiers out of committed artifacts, and this string is committed.
RESUME_COMMAND = (
    r"<embed-venv>/Scripts/python.exe scripts/deep/alexandria_embed.py"
)


def collect(out_root: Path | None = None) -> dict:
    """Read every shard manifest in the store and reconcile it against the precondition gate."""
    lanes = {}
    total_rows = 0
    total_wall = 0.0
    model_ids, revisions, dimensions, dtypes = set(), set(), set(), set()
    determinism = []

    for lane in embed.LANES:
        shards, missing = [], []
        lane_rows = 0
        for congress in embed.CONGRESSES:
            paths = embed.shard_paths(lane, congress, out_root)
            if not embed.shard_complete(lane, congress, out_root):
                missing.append(congress)
                continue
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            shards.append({
                "congress": congress,
                "rows": manifest["rows"],
                "id_list_sha256": manifest["id_list_sha256"],
                "dimension": manifest["dimension"],
                "wall_seconds": manifest.get("wall_seconds"),
                "vectors_bytes": paths["vectors"].stat().st_size,
                "ids_bytes": paths["ids"].stat().st_size,
            })
            lane_rows += manifest["rows"]
            total_wall += float(manifest.get("wall_seconds") or 0.0)
            model_ids.add(manifest.get("model_id"))
            revisions.add(manifest.get("model_revision"))
            dimensions.add(manifest.get("dimension"))
            dtypes.add(manifest.get("dtype"))
            spot = manifest.get("determinism_spot_check")
            if spot:
                determinism.append({"lane": lane, "congress": congress, **spot})
        expected = EXPECTED_UNITS[lane]
        lanes[lane] = {
            "shards_complete": len(shards),
            "shards_expected": len(list(embed.CONGRESSES)),
            "congresses_missing": missing,
            "rows": lane_rows,
            "gate_units": GATE_UNITS[lane],
            "out_of_scope_units": OUT_OF_SCOPE[lane],
            "expected_units": expected,
            "delta": lane_rows - expected,
            "complete": not missing and lane_rows == expected,
            "shards": shards,
        }
        total_rows += lane_rows

    worst = max((row["max_abs_delta"] for row in determinism), default=None)
    return {
        "schema_version": MANIFEST_SCHEMA,
        "method_version": METHOD_VERSION,
        "embed_method_version": embed.METHOD_VERSION,
        "store_root": util.artifact_path(embed.store_root(out_root)),
        "model": {
            "id": sorted(value for value in model_ids if value),
            "revision": sorted(value for value in revisions if value),
            "dimension": sorted(value for value in dimensions if value is not None),
            "storage_dtype": sorted(value for value in dtypes if value),
            "compute_dtype": embed.COMPUTE_DTYPE,
            "normalized": True,
        },
        "lanes": lanes,
        "rows_total": total_rows,
        "gate_total": sum(GATE_UNITS.values()),
        "expected_total": sum(EXPECTED_UNITS.values()),
        "delta_total": total_rows - sum(EXPECTED_UNITS.values()),
        "out_of_scope_total": {lane: OUT_OF_SCOPE[lane] for lane in OUT_OF_SCOPE
                               if OUT_OF_SCOPE[lane]},
        "wall_seconds_total": round(total_wall, 3),
        "determinism_spot_checks": determinism,
        "determinism_worst_max_abs_delta": worst,
        "complete": all(lane["complete"] for lane in lanes.values()),
        "resume_command": RESUME_COMMAND,
        "reconciliation_command": "python scripts/deep/alexandria_stage2_verify.py",
        "reconciliation_basis": "docs/34 section 1 gates 684,853 press statements and 152,187 "
                                "CREC E-statements. The pass covers congresses 107 through 119, "
                                "so the 15 CREC rows dated to congress 106 are out of scope and "
                                "named in out_of_scope_units. A non-zero delta against "
                                "expected_units means the vector store and the ledger describe "
                                "different corpora.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", type=Path, default=None)
    parser.add_argument("--out", type=Path,
                        default=config.REPO_ROOT / "data" / "reference"
                        / "alexandria-embeddings-manifest.json")
    args = parser.parse_args()
    manifest = collect(args.out_root)
    util.write_json(args.out, manifest)
    print(json.dumps({key: value for key, value in manifest.items() if key != "lanes"},
                     ensure_ascii=False, sort_keys=True, indent=2))
    for lane, summary in manifest["lanes"].items():
        print(f"{lane}: {summary['shards_complete']}/{summary['shards_expected']} shards, "
              f"{summary['rows']} rows, delta {summary['delta']}, "
              f"missing {summary['congresses_missing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
