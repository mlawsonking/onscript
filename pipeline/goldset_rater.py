"""The model rater: a frozen-prompt second reading of the sealed gold-set bundle.

docs/35 section 10.2. The model reads the same annotation guide and the same blinded item
context the human rater sees, and produces an answer sheet in the same shape. Its labels are
triage input. They never become gold labels.

The rating instrument is content-addressed before any live call: the prompt wrapper and the
annotation guide are hashed together into ``rating_prompt_sha256`` and frozen into
``evaluation/goldset/rater-registration.json``. A live run compares the live hash with the
registration and refuses on drift, so an edited guide cannot silently change the instrument
that produced a published sheet (docs/37 rules 6 and 7 applied to an offline instrument).

Everything except the network call is deterministic and free. Building requests, estimating
cost, and parsing responses spend nothing.
"""
from __future__ import annotations

from collections import defaultdict
import json

from . import config, goldset_bundle, llm, util


METHOD_VERSION = "gold-set-model-rater-v1"
PROMPT_ID = "GS1"
PROMPT_VERSION = "v1.0"
PROMPT_FILE = "GS1_gold_rater.v1.0.txt"
GUIDE_PATH = config.REPO_ROOT / "evaluation" / "ANNOTATION-GUIDE.md"
REGISTRATION_PATH = config.REPO_ROOT / "evaluation" / "goldset" / "rater-registration.json"

# Sonnet reads a long guide and a nuanced boundary; a weaker reader produces noisier
# disagreements, which costs the human rater time rather than money. The whole pilot is a
# one-time offline run of a few hundred short calls.
MODEL = "claude-sonnet-5"
MAX_TOKENS_PER_ITEM = 220
MAX_TOKENS_FLOOR = 400

ANSWER_COLUMNS = tuple(goldset_bundle.ANSWER_COLUMNS)
CLASSES = tuple(goldset_bundle.GOLD_CLASSES)
STANCES = tuple(goldset_bundle.STANCE_CHOICES)
BOOL_FIELDS = ("phrase_complete", "proposition_consistent", "claim_supported")

# The module holds the prompt wrapper and the guide as live module state so the registry
# mutation harness can bump either one and watch the registered hash follow (R-36.1).
_WRAPPER_TEXT = (llm.PROMPTS_DIR / PROMPT_FILE).read_text(encoding="utf-8").strip()
_GUIDE_TEXT = GUIDE_PATH.read_text(encoding="utf-8").strip()


def wrapper_text() -> str:
    return _WRAPPER_TEXT


def guide_text() -> str:
    return _GUIDE_TEXT


def rating_prompt_sha256() -> str:
    """Content address of the whole rating instrument: the wrapper plus the guide it carries."""
    return util.sha256_hex(f"{PROMPT_ID}\n{PROMPT_VERSION}\n{wrapper_text()}\n{guide_text()}")


def registration() -> dict:
    """The live identity of the rating instrument, read from its owners, never copied."""
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "prompt_id": PROMPT_ID,
        "prompt_version": PROMPT_VERSION,
        "prompt_file": f"pipeline/prompts/{PROMPT_FILE}",
        "guide_file": "evaluation/ANNOTATION-GUIDE.md",
        "wrapper_sha256": util.sha256_hex(wrapper_text()),
        "guide_sha256": util.sha256_hex(guide_text()),
        "rating_prompt_sha256": rating_prompt_sha256(),
        "model": MODEL,
    }


def rater_id() -> str:
    """The annotator id the model's sheet carries, pinned to the frozen prompt."""
    return f"model-rater-{PROMPT_ID}-{PROMPT_VERSION}"


class RegistrationError(RuntimeError):
    """The live rating instrument does not match the frozen registration."""


def load_registration() -> dict:
    if not REGISTRATION_PATH.is_file():
        raise RegistrationError(
            f"no frozen registration at {REGISTRATION_PATH}; freeze the prompt before spending")
    return json.loads(REGISTRATION_PATH.read_text(encoding="utf-8"))


def registration_drift(frozen: dict | None = None) -> list[str]:
    """Return the fields where the live instrument differs from the frozen registration."""
    frozen = frozen if frozen is not None else load_registration()
    live = registration()
    return sorted(key for key in ("prompt_id", "prompt_version", "wrapper_sha256",
                                  "guide_sha256", "rating_prompt_sha256", "model")
                  if frozen.get(key) != live.get(key))


def assert_registered(frozen: dict | None = None) -> dict:
    """Fail closed before any spend: the live prompt must be the registered prompt."""
    frozen = frozen if frozen is not None else load_registration()
    drift = registration_drift(frozen)
    if drift:
        raise RegistrationError(
            "the rating prompt is not the frozen one; re-freeze the registration before a live "
            f"run. Drifted: {', '.join(drift)}")
    return frozen


# --- request construction ----------------------------------------------------

def group_key(candidate: dict) -> tuple[str, str]:
    """Items are rated in day-and-party groups, the unit the family task compares over."""
    return (str(candidate.get("day") or ""), str(candidate.get("party") or ""))


def render_item(item: dict, position: int) -> str:
    """One item block, carrying exactly the blinded fields the human packet shows."""
    lines = [
        f"ITEM {position}",
        f"candidate_id: {item['candidate_id']}",
        f"phrase: {item['phrase']}",
        f"office: {item['office']}",
        f"date: {item['date']}",
        f"title: {item['title']}",
    ]
    if item.get("before"):
        lines.append(f"sentence before: {item['before']}")
    lines.append(f"sentence: {item['sentence']}")
    if item.get("after"):
        lines.append(f"sentence after: {item['after']}")
    for support in item.get("support") or []:
        lines.append(f"support: {support['office']} {support['date']} {support['sentence']}")
    return "\n".join(lines)


def build_request(items: list[dict], *, group: tuple[str, str]) -> dict:
    """Render one group's frozen system prompt and user message."""
    raw = wrapper_text()
    system_template, _, user_template = raw.partition("\n---USER---\n")
    system = system_template.split("SYSTEM:", 1)[-1].strip().replace("{guide}", guide_text())
    body = "\n\n".join(render_item(item, index + 1) for index, item in enumerate(items))
    user = (user_template.strip()
            .replace("{count}", str(len(items)))
            .replace("{items}", body))
    return {
        "group_day": group[0],
        "group_party": group[1],
        "candidate_ids": [item["candidate_id"] for item in items],
        "system": system,
        "user": user,
        "max_tokens": max(MAX_TOKENS_FLOOR, MAX_TOKENS_PER_ITEM * len(items)),
    }


def build_requests(candidates: list[dict], items_by_id: dict) -> list[dict]:
    """Every request for one sample, in a deterministic order."""
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for candidate in sorted(candidates, key=lambda row: row["candidate_id"]):
        item = items_by_id.get(candidate["candidate_id"])
        if item is not None:
            grouped[group_key(candidate)].append(item)
    return [build_request(grouped[key], group=key) for key in sorted(grouped)]


def estimate_run(requests: list[dict], *, model: str = MODEL, on_date: str | None = None) -> dict:
    """Token and dollar estimate for a live run. Direct calls, so no batch discount."""
    tokens_in = sum(llm.approx_tokens(request["system"]) + llm.approx_tokens(request["user"])
                    for request in requests)
    tokens_out = sum(request["max_tokens"] for request in requests)
    return {
        "requests": len(requests),
        "items": sum(len(request["candidate_ids"]) for request in requests),
        "model": model,
        "approx_tokens_in": tokens_in,
        "max_tokens_out": tokens_out,
        "estimated_cost_usd": llm.estimate_cost(model, tokens_in, tokens_out, batched=False,
                                                on_date=on_date),
        "estimate_basis": "approx 4 characters per token; output priced at the ceiling, so the "
                          "estimate is an upper bound",
    }


# --- response parsing --------------------------------------------------------

def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    return None


def parse_response(text: str, expected_ids: list[str]) -> tuple[list[dict], list[str]]:
    """Parse one group's JSON-lines reply into answer-sheet rows, reporting every problem."""
    rows: list[dict] = []
    errors: list[str] = []
    seen: set[str] = set()
    for line in (text or "").splitlines():
        line = line.strip().strip("`")
        if not line or not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"unparseable line: {line[:80]}")
            continue
        cid = str(payload.get("candidate_id") or "").strip()
        if cid not in expected_ids:
            errors.append(f"unexpected candidate_id {cid!r}")
            continue
        if cid in seen:
            errors.append(f"duplicate candidate_id {cid}")
            continue
        seen.add(cid)
        gold_class = str(payload.get("gold_class") or "").strip().lower()
        if gold_class not in CLASSES:
            errors.append(f"{cid}: invalid gold_class {payload.get('gold_class')!r}")
            continue
        row = {
            "candidate_id": cid,
            "gold_class": gold_class,
            "gold_family_id": str(payload.get("gold_family_id") or "").strip() or cid,
            "notes": str(payload.get("notes") or "").strip(),
        }
        for field in BOOL_FIELDS:
            value = _coerce_bool(payload.get(field))
            row[field] = "" if value is None else str(value).lower()
        stance = str(payload.get("stance") or "").strip().lower()
        row["stance"] = stance if stance in STANCES else ""
        rows.append(row)
    for cid in expected_ids:
        if cid not in seen:
            errors.append(f"{cid}: no label returned")
    return rows, errors


def render_answer_csv(rows: list[dict]) -> str:
    """The model's answer sheet, in the exact shape the intake tool ingests."""
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(ANSWER_COLUMNS)
    for row in sorted(rows, key=lambda item: item["candidate_id"]):
        writer.writerow([row.get(column, "") for column in ANSWER_COLUMNS])
    return buffer.getvalue()


def run_live(requests: list[dict], *, model: str = MODEL,
             call=None) -> dict:  # pragma: no cover - requires a key and real spend
    """Call the model once per group. Michael's act only, behind --allow-api-spend."""
    caller = call or llm.direct_call
    rows: list[dict] = []
    errors: list[str] = []
    calls: list[dict] = []
    tokens_in = tokens_out = 0
    for request in requests:
        result = caller(model, request["system"], request["user"],
                        max_tokens=request["max_tokens"])
        tokens_in += int(result.get("tokens_in") or 0)
        tokens_out += int(result.get("tokens_out") or 0)
        parsed, problems = parse_response(result.get("text") or "", request["candidate_ids"])
        rows.extend(parsed)
        errors.extend(f"[{request['group_day']} {request['group_party']}] {problem}"
                      for problem in problems)
        calls.append({
            "group_day": request["group_day"],
            "group_party": request["group_party"],
            "items": len(request["candidate_ids"]),
            "labels_returned": len(parsed),
            "tokens_in": int(result.get("tokens_in") or 0),
            "tokens_out": int(result.get("tokens_out") or 0),
        })
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "model": model,
        "registration": registration(),
        "rater_id": rater_id(),
        "calls": calls,
        "labels": len(rows),
        "errors": errors,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": llm.estimate_cost(model, tokens_in, tokens_out, batched=False),
        "rows": rows,
    }
