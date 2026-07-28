"""Alexandria Stage 2, the 4080 layer: one taxonomy topic per statement, from a local model.

This is the runbook procedure in docs/34 section 4, built as specified there. It is PREPARED,
not run: committing the script and its frozen config is the deliverable, and starting the pass
is a separate operator act (docs/34 section 5, the charter posture in docs/03 section 1.4).

The constitutional line this script sits behind: a local model may compute, never write voice.
A topic tag is a classification over a committed 25-label taxonomy, parsed deterministically
from a temperature-0 generation. It never becomes published prose, it never bypasses the
verifier, and it never reaches a chapter. Chapter voice is Claude's, always.

Shape, per docs/34 section 4:

- For each statement, prompt the model with the text and the fixed taxonomy label list and
  require a single label from that list (or `other`).
- Write alexandria/topics/{lane}/topics-{congress}.jsonl (stable_id, topic, model_conf) to the
  append-only store on X:, resumable per (lane, congress).
- Manifest per shard: model id, revision, prompt sha, taxonomy version, row count.

The frozen config (data/reference/alexandria-topic-tag.json) pins the model id, the endpoint,
the decoding parameters, and the prompt sha, so the manifest a run writes can be checked against
the instrument that was frozen before it, exactly as the gold-set rater freezes its prompt
before spending (docs/35 section 10.2, docs/37 rules 6 and 7).

The local runtime is an OpenAI-compatible server (LM Studio or llama.cpp), imported lazily
through the standard library only. The suite imports this module with no server running and no
model on disk.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import config, util  # noqa: E402
from pipeline.deep import lanes  # noqa: E402
from scripts.deep import alexandria_embed as embed  # noqa: E402

METHOD_VERSION = "alexandria-topic-tag-v1"
MANIFEST_SCHEMA = 1
CONFIG_PATH = config.REPO_ROOT / "data" / "reference" / "alexandria-topic-tag.json"

PROMPT = (
    "Classify the political subject of one public statement by a member of the United States "
    "Congress.\n"
    "Answer with exactly one label from this list and nothing else:\n"
    "{labels}\n"
    "If no label fits, answer other.\n\n"
    "STATEMENT:\n{text}\n\nLABEL:"
)


def taxonomy() -> dict:
    return json.loads(config.TAXONOMY_FILE.read_text(encoding="utf-8"))


def labels() -> list[str]:
    """The committed 25-topic label set, the same vocabulary the daily pipeline uses."""
    return [topic["id"] for topic in taxonomy()["topics"]]


def prompt_text(text: str) -> str:
    return PROMPT.replace("{labels}", ", ".join(labels())).replace("{text}", text.strip())


def prompt_sha256() -> str:
    """Content address of the instrument: the template plus the label set it carries."""
    return util.sha256_hex(f"{METHOD_VERSION}\n{PROMPT}\n{','.join(labels())}")


def frozen_config() -> dict:
    """The live identity of the tagging instrument, read from its owners, never copied."""
    return {
        "schema_version": MANIFEST_SCHEMA,
        "method_version": METHOD_VERSION,
        "taxonomy_version": taxonomy()["taxonomy_version"],
        "taxonomy_file": "taxonomy_v1.json",
        "label_count": len(labels()),
        "prompt_sha256": prompt_sha256(),
        "temperature": 0.0,
        "max_tokens": 8,
        "endpoint": "http://localhost:1234/v1/chat/completions",
        "model_id": "qwen2.5-14b-instruct",
    }


class ConfigDrift(RuntimeError):
    """The live tagging instrument does not match the frozen config."""


def load_frozen() -> dict:
    if not CONFIG_PATH.is_file():
        raise ConfigDrift(f"no frozen config at {CONFIG_PATH}; freeze it before running the pass")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def config_drift(frozen: dict | None = None) -> list[str]:
    frozen = frozen if frozen is not None else load_frozen()
    live = frozen_config()
    return sorted(key for key in ("method_version", "taxonomy_version", "label_count",
                                  "prompt_sha256", "temperature", "max_tokens", "model_id")
                  if frozen.get(key) != live.get(key))


def assert_frozen(frozen: dict | None = None) -> dict:
    """Fail closed before any generation: the live prompt must be the frozen prompt."""
    frozen = frozen if frozen is not None else load_frozen()
    drift = config_drift(frozen)
    if drift:
        raise ConfigDrift(
            "the tagging instrument is not the frozen one; re-freeze before running. "
            f"Drifted: {', '.join(drift)}")
    return frozen


def parse_label(text: str) -> str:
    """Deterministic parse of one generation into one taxonomy label. Unparseable is `other`."""
    allowed = labels()
    cleaned = (text or "").strip().strip("`\"'.").casefold()
    if cleaned in allowed:
        return cleaned
    for label in allowed:
        if label in cleaned:
            return label
    return "other"


def shard_paths(lane: str, congress: int, out_root: Path | None = None) -> dict:
    base = (Path(out_root) if out_root else lanes.DEEP_ROOT) / "alexandria" / "topics" / lane
    return {
        "topics": base / f"topics-{congress}.jsonl",
        "manifest": base / f"manifest-{congress}.json",
    }


def shard_complete(lane: str, congress: int, out_root: Path | None = None) -> bool:
    paths = shard_paths(lane, congress, out_root)
    if not all(paths[key].is_file() for key in ("topics", "manifest")):
        return False
    try:
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return manifest.get("complete") is True


def call_local(prompt: str, *, endpoint: str, model_id: str, temperature: float,
               max_tokens: int) -> tuple[str, float | None]:  # pragma: no cover - needs a server
    """One temperature-0 completion from the local OpenAI-compatible server."""
    import urllib.request

    body = json.dumps({
        "model": model_id,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    request = urllib.request.Request(endpoint, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.load(response)
    choice = (payload.get("choices") or [{}])[0]
    return (choice.get("message") or {}).get("content") or "", choice.get("logprob")


def tag_shard(lane: str, congress: int, *, out_root: Path | None, frozen: dict,
              call=call_local, clock=time.monotonic) -> dict:
    """Tag one (lane, congress) shard and write it with its manifest."""
    started = clock()
    paths = shard_paths(lane, congress, out_root)
    paths["topics"].parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for unit in embed.READERS[lane](congress):
        text = (unit.get("text") or "").strip()
        if not text:
            continue
        raw, confidence = call(prompt_text(text), endpoint=frozen["endpoint"],
                               model_id=frozen["model_id"], temperature=frozen["temperature"],
                               max_tokens=frozen["max_tokens"])
        rows.append({"stable_id": unit["stable_id"], "topic": parse_label(raw),
                     "model_conf": confidence})
    with paths["topics"].open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "method_version": METHOD_VERSION,
        "lane": lane,
        "congress": congress,
        "model_id": frozen["model_id"],
        "model_revision": frozen.get("model_revision"),
        "prompt_sha256": frozen["prompt_sha256"],
        "taxonomy_version": frozen["taxonomy_version"],
        "rows": len(rows),
        "wall_seconds": round(clock() - started, 3),
        "complete": True,
    }
    util.write_json(paths["manifest"], manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lanes", nargs="*", default=list(embed.LANES), choices=list(embed.LANES))
    parser.add_argument("--congresses", nargs="*", type=int, default=list(embed.CONGRESSES))
    parser.add_argument("--out-root", type=Path, default=None)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--allow-local-generation", action="store_true",
        help="Required. Without it this script only prints the frozen instrument and exits, "
             "because the pass is prepared, not scheduled (docs/34 section 4).",
    )
    args = parser.parse_args()

    frozen = assert_frozen()
    if not args.allow_local_generation:
        print(json.dumps({"prepared": True, "ran": False, "frozen_config": frozen},
                         ensure_ascii=False, sort_keys=True, indent=2))
        return 0

    started = time.monotonic()
    shards, skipped = [], []
    for lane in args.lanes:
        for congress in args.congresses:
            if shard_complete(lane, congress, args.out_root):
                skipped.append(f"{lane}/{congress}")
                continue
            manifest = tag_shard(lane, congress, out_root=args.out_root, frozen=frozen)
            shards.append(manifest)
            print(f"done {lane} c{congress}: {manifest['rows']} rows", flush=True)

    report = {
        "schema_version": MANIFEST_SCHEMA,
        "method_version": METHOD_VERSION,
        "frozen_config": frozen,
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
