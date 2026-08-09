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

Two transports carry the same frozen instrument. ``api`` calls the model over the network and
is Michael's paid act. ``session`` records the answers of a subscription session that read the
same frozen prompt and the same item blocks, at no marginal cost, under the docs/03 precedent
for one-time subscription-scripted work. Both transports refuse on instrument drift, hash each
item's request, and produce the identical answer sheet; only the reader and the bill differ,
and the run record names which reader answered.
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
SCHEMA_PATH = config.REPO_ROOT / "evaluation" / "annotation.schema.json"

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

TRANSPORTS = ("api", "session")
# The instrument is the frozen prompt: the wrapper, the guide, and their combined address.
# The model field records which reader was registered, which is a transport fact, not part of
# the rating instrument. The session transport pins the instrument and states the reader.
INSTRUMENT_FIELDS = ("prompt_id", "prompt_version", "wrapper_sha256", "guide_sha256",
                     "rating_prompt_sha256")
REGISTRATION_FIELDS = INSTRUMENT_FIELDS + ("model",)
ANSWER_KEYS = tuple(ANSWER_COLUMNS)
OPTIONAL_ANSWER_FIELDS = ("phrase_complete", "proposition_consistent", "stance",
                          "claim_supported")
SESSION_DEVIATION = (
    "The reader is a subscription session rather than an API call. Authorized by Fable in the "
    "S59 lineage under the docs/03 precedent for one-time subscription-scripted work. The "
    "frozen prompt, the item context, the per-item request hashing, the drift refusal, and the "
    "answer schema are unchanged. Marginal cost is 0.00 USD.")

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


def _drift(frozen: dict, fields: tuple[str, ...]) -> list[str]:
    live = registration()
    return sorted(key for key in fields if frozen.get(key) != live.get(key))


def registration_drift(frozen: dict | None = None) -> list[str]:
    """Return the fields where the live instrument differs from the frozen registration."""
    frozen = frozen if frozen is not None else load_registration()
    return _drift(frozen, REGISTRATION_FIELDS)


def instrument_drift(frozen: dict | None = None) -> list[str]:
    """Drift in the frozen prompt alone, ignoring which reader was registered to read it.

    The session transport changes the reader and nothing else, so this is the check it fails
    closed on. It can never be laxer than ``registration_drift`` about the prompt itself.
    """
    frozen = frozen if frozen is not None else load_registration()
    return _drift(frozen, INSTRUMENT_FIELDS)


def assert_registered(frozen: dict | None = None) -> dict:
    """Fail closed before any spend: the live prompt must be the registered prompt."""
    frozen = frozen if frozen is not None else load_registration()
    drift = registration_drift(frozen)
    if drift:
        raise RegistrationError(
            "the rating prompt is not the frozen one; re-freeze the registration before a live "
            f"run. Drifted: {', '.join(drift)}")
    return frozen


def assert_instrument_registered(frozen: dict | None = None) -> dict:
    """Fail closed before a session run: the live prompt must be the frozen prompt."""
    frozen = frozen if frozen is not None else load_registration()
    drift = instrument_drift(frozen)
    if drift:
        raise RegistrationError(
            "the rating prompt is not the frozen one; re-freeze the registration before a "
            f"session run. Drifted: {', '.join(drift)}")
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
    blocks = [render_item(item, index + 1) for index, item in enumerate(items)]
    user = (user_template.strip()
            .replace("{count}", str(len(items)))
            .replace("{items}", "\n\n".join(blocks)))
    return {
        "group_day": group[0],
        "group_party": group[1],
        "candidate_ids": [item["candidate_id"] for item in items],
        # The blocks the user message is made of, kept alongside it so one item's request can be
        # content-addressed without re-splitting the rendered message.
        "item_blocks": blocks,
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


def item_request_sha256(request: dict, position: int) -> str:
    """Content address of one item's request: the frozen instrument plus the exact block sent.

    Both transports hash the same way, so a session-produced sheet and an API-produced sheet
    carry comparable per-item addresses, and either can be re-derived from the sealed bundle
    without the run that produced it.
    """
    return util.sha256_hex("\n".join([
        rating_prompt_sha256(),
        request["group_day"],
        request["group_party"],
        request["candidate_ids"][position],
        request["item_blocks"][position],
    ]))


def request_hashes(request: dict) -> dict[str, str]:
    """Per-item request hashes for one group, keyed by candidate_id."""
    return {cid: item_request_sha256(request, position)
            for position, cid in enumerate(request["candidate_ids"])}


def all_request_hashes(requests: list[dict]) -> dict[str, str]:
    """Per-item request hashes for a whole run, keyed by candidate_id."""
    hashes: dict[str, str] = {}
    for request in requests:
        hashes.update(request_hashes(request))
    return hashes


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


# --- answer schema -----------------------------------------------------------

def annotation_schema() -> dict:
    """The committed annotation schema, read from its owner rather than restated here."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def annotation_record(answer: dict, *, annotator_id: str) -> dict:
    """One answer as the schema's annotation object. A null optional field is absent, not null."""
    record = {
        "schema_version": 1,
        "candidate_id": answer.get("candidate_id"),
        "annotator_id": annotator_id,
        "gold_class": answer.get("gold_class"),
        "gold_family_id": answer.get("gold_family_id"),
    }
    for field in OPTIONAL_ANSWER_FIELDS:
        value = answer.get(field)
        if value is not None:
            record[field] = value
    notes = answer.get("notes")
    if notes is not None:
        record["notes"] = notes
    return record


def schema_problems(record: dict, schema: dict | None = None) -> list[str]:
    """Validate one annotation object against the committed schema.

    A deliberately small validator covering exactly the keywords the committed schema uses:
    object type, additionalProperties false, required, const, type, enum, and minLength. It
    reads the schema file rather than a copy of its rules, so a schema edit moves the check.
    """
    schema = schema if schema is not None else annotation_schema()
    problems: list[str] = []
    if not isinstance(record, dict):
        return ["not a JSON object"]
    properties = schema.get("properties") or {}
    for field in schema.get("required") or []:
        if field not in record:
            problems.append(f"missing required field {field}")
    if schema.get("additionalProperties") is False:
        for field in sorted(set(record) - set(properties)):
            problems.append(f"unknown field {field}")
    for field, rule in properties.items():
        if field not in record:
            continue
        value = record[field]
        if "const" in rule and value != rule["const"]:
            problems.append(f"{field}: expected {rule['const']!r}, got {value!r}")
        if "enum" in rule and value not in rule["enum"]:
            problems.append(f"{field}: {value!r} is not one of {rule['enum']}")
        expected = rule.get("type")
        if expected == "string" and not isinstance(value, str):
            problems.append(f"{field}: expected a string, got {type(value).__name__}")
        if expected == "boolean" and not isinstance(value, bool):
            problems.append(f"{field}: expected true or false, got {value!r}")
        if (rule.get("minLength") and isinstance(value, str)
                and len(value) < rule["minLength"]):
            problems.append(f"{field}: shorter than {rule['minLength']} characters")
    return problems


def answer_problems(answer, *, annotator_id: str, schema: dict | None = None) -> list[str]:
    """Every problem with one transport answer, before it is allowed near the sheet.

    The API parser normalizes an out-of-range value to blank, which is the right behavior for
    text a remote model wrote. An answer emitted by a transport this repository controls is
    held to the schema instead: a typo is a refusal, not a silently blanked column.
    """
    if not isinstance(answer, dict):
        return ["not a JSON object"]
    problems = [f"unexpected key {key}" for key in sorted(set(answer) - set(ANSWER_KEYS))]
    problems += [f"missing key {key}" for key in ANSWER_KEYS if key not in answer]
    for field in OPTIONAL_ANSWER_FIELDS:
        value = answer.get(field)
        if value is None:
            continue
        if field == "stance":
            if value not in STANCES:
                problems.append(f"stance: {value!r} is not one of {list(STANCES)}")
        elif not isinstance(value, bool):
            problems.append(f"{field}: expected true, false, or null, got {value!r}")
    if answer.get("notes") is not None and not isinstance(answer.get("notes"), str):
        problems.append("notes: expected a string or null")
    problems += schema_problems(annotation_record(answer, annotator_id=annotator_id), schema)
    return problems


# --- transports --------------------------------------------------------------

def session_rater_id(reader_model: str) -> str:
    """The annotator id a session-transport sheet carries: frozen prompt plus actual reader."""
    return f"{rater_id()}-{reader_model}"


def session_worksheet(requests: list[dict]) -> list[dict]:
    """The groups a session reader works through, in the order the API would have called them.

    The system prompt is the frozen instrument and is identical for every group, so it is
    addressed by hash here and written once beside the worksheet rather than 148 times.
    """
    return [{
        "index": index,
        "group_day": request["group_day"],
        "group_party": request["group_party"],
        "candidate_ids": list(request["candidate_ids"]),
        "item_request_sha256": request_hashes(request),
        "system_sha256": util.sha256_hex(request["system"]),
        "user": request["user"],
    } for index, request in enumerate(requests)]


def run_session(requests: list[dict], answers: list[dict], *, reader_model: str,
                registered_model: str = MODEL, wall_seconds: float | None = None) -> dict:
    """Assemble a run record from answers a session produced against the frozen requests.

    The answers travel through the same parser the API responses travel through, so the sheet
    is produced by one code path whatever read the items. What differs is stated, not implied:
    the reader, the absent token accounting, and the zero bill.
    """
    annotator = session_rater_id(reader_model)
    schema = annotation_schema()
    index = {cid: position for position, request in enumerate(requests)
             for cid in request["candidate_ids"]}
    lines: dict[int, list[str]] = defaultdict(list)
    errors: list[str] = []
    for order, answer in enumerate(answers):
        cid = ""
        if isinstance(answer, dict):
            cid = str(answer.get("candidate_id") or "").strip()
        problems = answer_problems(answer, annotator_id=annotator, schema=schema)
        if cid not in index:
            errors.append(f"answer {order}: candidate_id {cid!r} belongs to no request")
            continue
        if problems:
            errors.extend(f"{cid}: {problem}" for problem in problems)
            continue
        lines[index[cid]].append(json.dumps(answer, ensure_ascii=False, sort_keys=True))

    rows: list[dict] = []
    calls: list[dict] = []
    for position, request in enumerate(requests):
        parsed, problems = parse_response("\n".join(lines[position]), request["candidate_ids"])
        rows.extend(parsed)
        errors.extend(f"[{request['group_day']} {request['group_party']}] {problem}"
                      for problem in problems)
        calls.append({
            "group_day": request["group_day"],
            "group_party": request["group_party"],
            "items": len(request["candidate_ids"]),
            "labels_returned": len(parsed),
            "item_request_sha256": request_hashes(request),
        })
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "transport": "session",
        "transport_deviation": SESSION_DEVIATION,
        "registered_model": registered_model,
        "reader_model": reader_model,
        "model": reader_model,
        "registration": registration(),
        "rater_id": annotator,
        "frozen_prompt_rater_id": rater_id(),
        "calls": calls,
        "labels": len(rows),
        "errors": errors,
        "token_accounting": "not applicable: the session transport makes no API call",
        "cost_usd": 0.0,
        "wall_seconds": wall_seconds,
        "rows": rows,
    }


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
