"""Alexandria Stage 2, the 4080 layer: sentence embeddings for the whole corpus.

This is the runbook procedure in docs/34 section 3, built as specified there. It is one-time
capital work on Michael's machine, $0 marginal (local GPU), and it never runs in the daily
cloud pipeline. It produces vectors only; it writes no prose and publishes nothing.

What it does, per docs/34:

- Streams two lanes. `press` is the Lane-1 congress-press corpus, embedded at the NORMALIZED
  statement unit (the same unit the alexandria ledger counts, 684,853 units). `crec` is the
  CREC Extensions deep instrument (152,187 E-statements), a SEPARATE lane that enriches and
  never enters a cross-party denominator with press.
- Encodes with sentence-transformers/all-MiniLM-L6-v2, 384 dimensions, normalized vectors,
  fp16 on the GPU.
- Writes one shard per (lane, congress) to the append-only store on X:, never into the
  repository working tree and never into site/public or data/derived.
- Records a manifest per shard (model id, model revision sha, dimension, dtype, row count,
  sha256 of the id list, max sequence length, wall time) so a reader can prove which model
  produced which vectors.

Every vector carries its provenance lane with it, because the comparison an exhibit later runs
is only valid within one lane (docs/34 section 2). For press that lane is `date_source`
(legacy | scraper | page_html, with the 2021-01-03 instrument seam); for CREC it is
`source=crec` plus `crec_section`.

Resume is per (lane, congress): a shard whose manifest is complete is skipped, so an
interrupted run is restarted with the same command and loses only the shard in flight.

torch and sentence-transformers live in a dedicated venv OUTSIDE this repository (docs/34
section 3.1). This module imports them lazily so the repository suite imports it with no GPU
stack installed at all.

  X:\\...\\onscript-embed\\Scripts\\python.exe scripts/deep/alexandria_embed.py --out-root X:/onscript-data
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import fetch, normalize, util  # noqa: E402
from pipeline.deep import lanes  # noqa: E402
from pipeline.search import provenance  # noqa: E402

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
DIMENSION = 384
DTYPE = "float16"
CONGRESSES = range(107, 120)
LANES = ("press", "crec")
MANIFEST_SCHEMA = 1
METHOD_VERSION = "alexandria-embed-v1"

# 12 GB class card; docs/34 section 3.2 says 256-512. 256 keeps headroom for a long press
# statement batch, where every row is padded to the model's max sequence length.
DEFAULT_BATCH = 256


class GpuStackMissing(RuntimeError):
    """The embedding stack is not importable. Named so the message can say where it lives."""


def _load_encoder(device: str):
    """Import the GPU stack only when a run actually encodes. Import-safe without torch."""
    try:
        import torch  # noqa: F401
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - the suite runs without the GPU stack
        raise GpuStackMissing(
            "torch and sentence-transformers are not importable. They live in a dedicated venv "
            "outside this repository and are never a pipeline dependency (docs/34 section 3.1, "
            "requirements.lock). Create it with:\n"
            "  C:\\ProgramData\\miniconda3\\python.exe -m venv --system-site-packages "
            "C:/Users/bobdo/venvs/onscript-embed\n"
            "  C:/Users/bobdo/venvs/onscript-embed/Scripts/python.exe -m pip install "
            "sentence-transformers==3.4.1\n"
            "then run this script with that interpreter."
        ) from exc
    return SentenceTransformer(MODEL_ID, device=device)


def model_revision() -> str | None:
    """The pinned model commit sha, so the manifest names the exact weights (docs/34 section 3.4)."""
    try:  # pragma: no cover - requires the GPU stack and a warm cache
        from huggingface_hub import HfApi
        return HfApi().model_info(MODEL_ID).sha
    except Exception:
        return None


# --- output layout ------------------------------------------------------------------

def store_root(out_root: Path | None = None) -> Path:
    """The append-only vector store on X:. Never the repository working tree."""
    return (Path(out_root) if out_root else lanes.DEEP_ROOT) / "alexandria" / "embeddings"


def shard_paths(lane: str, congress: int, out_root: Path | None = None) -> dict:
    base = store_root(out_root) / lane
    return {
        "vectors": base / f"emb-{congress}.f16.npy",
        "ids": base / f"ids-{congress}.jsonl",
        "manifest": base / f"manifest-{congress}.json",
    }


def shard_complete(lane: str, congress: int, out_root: Path | None = None) -> bool:
    """A shard counts as done only when its manifest says so and both artifacts exist."""
    paths = shard_paths(lane, congress, out_root)
    if not all(paths[key].is_file() for key in ("vectors", "ids", "manifest")):
        return False
    try:
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return manifest.get("complete") is True and isinstance(manifest.get("rows"), int)


def id_list_sha256(rows: list[dict]) -> str:
    """Content address of the id list, in row order. The row order IS the matrix row order."""
    digest = hashlib.sha256()
    for row in rows:
        digest.update(f"{row['stable_id']}\n".encode("utf-8"))
    return digest.hexdigest()


# --- lane readers -------------------------------------------------------------------

def _congress_of(day: str):
    return util.congress_for_date(day) if len(day or "") == 10 else None


def press_units(congress: int):
    """Normalized press statements for one Congress, each carrying its date_source lane.

    The embeddable unit is the normalized statement (docs/34 section 3.1), which is why this
    runs normalize_records rather than counting raw records: 688,820 records normalize to
    684,853 units, and the ledger counts the units.
    """
    raw = []
    source_by_id = {}
    for path in sorted(fetch.MIRROR.glob("*.jsonl")):
        for record in util.iter_jsonl(path):
            day = (record.get("date") or "")[:10]
            if _congress_of(day) != congress:
                continue
            raw.append(record)
            url, text = (record.get("url") or "").strip(), record.get("text") or ""
            if url and text.strip():
                source_by_id[util.statement_id(url, text)] = provenance.date_source_of(record)
    for statement in normalize.normalize_records(raw, run_id=f"embed-press-{congress}"):
        member = statement.get("member") or {}
        yield {
            "stable_id": statement["id"],
            "congress": statement.get("congress"),
            "lane": "press",
            "date_source": source_by_id.get(statement["id"]),
            "published_at": statement.get("published_at"),
            "bioguide": member.get("bioguide"),
            "party": member.get("party"),
            "text": statement.get("text") or "",
        }


def crec_units(congress: int):
    """CREC Extensions E-statements for one Congress, from the deep lane state on X:."""
    e_dir = lanes.lane_state("crec") / "E"
    if not e_dir.exists():
        return
    for path in sorted(e_dir.glob("statements-*.jsonl")):
        for row in util.iter_jsonl(path):
            found = row.get("congress") or _congress_of(
                (row.get("unit_date") or row.get("published_at") or "")[:10])
            if found is None or int(found) != congress:
                continue
            member = row.get("member") or {}
            yield {
                "stable_id": row.get("stable_id") or row.get("id"),
                "congress": int(found),
                "lane": "crec",
                "source": "crec",
                "crec_section": row.get("crec_section"),
                "published_at": row.get("published_at") or row.get("unit_date"),
                "bioguide": member.get("bioguide"),
                "party": member.get("party"),
                "text": row.get("text") or "",
            }


READERS = {"press": press_units, "crec": crec_units}


# --- the pass -----------------------------------------------------------------------

def encode_shard(lane: str, congress: int, *, out_root: Path | None, batch_size: int,
                 device: str, encoder=None, revision: str | None = None,
                 clock=time.monotonic) -> dict:
    """Encode one (lane, congress) shard and write it with its manifest. Returns the manifest."""
    import numpy  # local: numpy rides with the GPU venv, not with the pipeline

    started = clock()
    units = [unit for unit in READERS[lane](congress) if (unit.get("text") or "").strip()]
    paths = shard_paths(lane, congress, out_root)
    paths["vectors"].parent.mkdir(parents=True, exist_ok=True)

    if units:
        vectors = encoder.encode(
            [unit["text"] for unit in units],
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).astype(numpy.float16)
    else:
        vectors = numpy.zeros((0, DIMENSION), dtype=numpy.float16)

    rows = [{key: value for key, value in unit.items() if key != "text"} for unit in units]
    numpy.save(paths["vectors"], vectors)
    with paths["ids"].open("w", encoding="utf-8", newline="\n") as handle:
        for index, row in enumerate(rows):
            handle.write(json.dumps({"row": index, **row}, ensure_ascii=False,
                                    sort_keys=True) + "\n")

    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "method_version": METHOD_VERSION,
        "lane": lane,
        "congress": congress,
        "model_id": MODEL_ID,
        "model_revision": revision,
        "max_seq_length": getattr(encoder, "max_seq_length", None),
        "dimension": int(vectors.shape[1]) if vectors.size else DIMENSION,
        "dtype": DTYPE,
        "normalized": True,
        "device": device,
        "batch_size": batch_size,
        "rows": len(rows),
        "id_list_sha256": id_list_sha256(rows),
        "wall_seconds": round(clock() - started, 3),
        "complete": True,
    }
    util.write_json(paths["manifest"], manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lanes", nargs="*", default=list(LANES), choices=list(LANES))
    parser.add_argument("--congresses", nargs="*", type=int, default=list(CONGRESSES))
    parser.add_argument("--out-root", type=Path, default=None,
                        help="Store root. Defaults to the deep lane root on X:.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--report", type=Path, help="Write the run manifest here.")
    args = parser.parse_args()

    encoder = _load_encoder(args.device)
    revision = model_revision()
    print(f"model {MODEL_ID} revision {revision} on {args.device}, "
          f"max_seq_length {getattr(encoder, 'max_seq_length', None)}", flush=True)

    started = time.monotonic()
    shards, skipped = [], []
    for lane in args.lanes:
        for congress in args.congresses:
            if shard_complete(lane, congress, args.out_root):
                skipped.append(f"{lane}/{congress}")
                print(f"skip {lane} c{congress}: already complete", flush=True)
                continue
            manifest = encode_shard(lane, congress, out_root=args.out_root,
                                    batch_size=args.batch_size, device=args.device,
                                    encoder=encoder, revision=revision)
            shards.append(manifest)
            print(f"done {lane} c{congress}: {manifest['rows']} rows in "
                  f"{manifest['wall_seconds']}s", flush=True)

    report = {
        "schema_version": MANIFEST_SCHEMA,
        "method_version": METHOD_VERSION,
        "model_id": MODEL_ID,
        "model_revision": revision,
        "dimension": DIMENSION,
        "dtype": DTYPE,
        "store_root": str(store_root(args.out_root)),
        "lanes": list(args.lanes),
        "congresses": list(args.congresses),
        "shards_written": len(shards),
        "shards_skipped": skipped,
        "rows_written": sum(shard["rows"] for shard in shards),
        "wall_seconds": round(time.monotonic() - started, 3),
    }
    if args.report:
        util.write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
