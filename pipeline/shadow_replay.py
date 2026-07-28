"""Shadow replay for the P2/P3 prompt activation gate (R-33.6).

The comparison this harness runs has an asymmetry that is the whole point of it: the live side
is not generated, it is READ. P2 v1.3 and P3 v1.1 already ran in production on real days and
their outputs are committed in ``data/derived/days``. Regenerating them would compare the
candidate against a fresh sample of the live prompt rather than against what the project
actually published, and it would pay for a side we already own. So the live side of every
party-day is the committed production record, and only the v1.4/v1.2 side is generated.

That choice makes the population honest, and much smaller than a file count suggests. A
committed day only carries evidence about the live prompt when the record was produced BY the
live prompt: same prompt sha, a real model generator, and a stats block of the schema the
candidate prompt consumes. ``classify_record`` states that ladder per party-day with a reason
for every exclusion, and only the surviving rows count toward the R-33.6 minimums. Days written
under P2 v1.0/v1.1/v1.2, under the dry-run or deterministic voice, or before the docs/28 claim
binding carry a different instrument, and putting them in one comparison without stating the
seam is exactly what docs/37 rule 13 forbids.

Every artifact this module emits carries gate progress against the R-33.6 minimums (60 complete
days, 200 party-days) as an explicit fraction. The flip stays blocked until the gate fills. This
harness makes the distance measurable; it never shortens it.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from . import config, contracts, distill, llm, ops, site, util, verify


METHOD_VERSION = "shadow-replay-v2"
MIN_COMPLETE_DAYS = 60
MIN_PARTY_DAYS = 200
PROMPT_PAIRS = {
    "P2": ("P2_daily_line.v1.3.txt", "P2_daily_line.v1.4.txt"),
    "P3": ("P3_quiet_day.v1.1.txt", "P3_quiet_day.v1.2.txt"),
}
GUARD_NAMES = ("unit_mixing", "quote_extension", "topic_label_assertion",
               "multi_claim_sentence", "sentence_mapping_mismatch")
_VERSION = re.compile(r"\.v(\d+\.\d+)\.txt$")
_QUOTE = re.compile(r'"([^"]+)"|“([^”]+)”')

# The prompt texts are module state, not a per-call disk read, so the Y9 registry mutation
# harness can bump one and watch the registration follow it (docs/37 rules 1, 6 and 7). A
# registration that reads its own copy is the defect that harness exists to catch.
_P2_LIVE_TEXT = (llm.PROMPTS_DIR / PROMPT_PAIRS["P2"][0]).read_text(encoding="utf-8").strip()
_P2_CANDIDATE_TEXT = (llm.PROMPTS_DIR / PROMPT_PAIRS["P2"][1]).read_text(encoding="utf-8").strip()
_P3_LIVE_TEXT = (llm.PROMPTS_DIR / PROMPT_PAIRS["P3"][0]).read_text(encoding="utf-8").strip()
_P3_CANDIDATE_TEXT = (llm.PROMPTS_DIR / PROMPT_PAIRS["P3"][1]).read_text(encoding="utf-8").strip()


def prompt_text(prompt_id: str, side: str) -> str:
    """The live text of one prompt in the pair, read from its owning module attribute."""
    return {
        ("P2", "live"): lambda: _P2_LIVE_TEXT,
        ("P2", "candidate"): lambda: _P2_CANDIDATE_TEXT,
        ("P3", "live"): lambda: _P3_LIVE_TEXT,
        ("P3", "candidate"): lambda: _P3_CANDIDATE_TEXT,
    }[(prompt_id, side)]()


def _prompt(prompt_id: str, side: str) -> dict:
    raw = prompt_text(prompt_id, side)
    filename = PROMPT_PAIRS[prompt_id][0 if side == "live" else 1]
    system, marker, user = raw.partition("\n---USER---\n")
    if not marker:
        raise ValueError(f"prompt has no user separator: {filename}")
    return {
        "id": prompt_id,
        "side": side,
        "file": filename,
        "version": (_VERSION.search(filename) or [None, "0.0"])[1],
        "sha256": util.sha256_hex(raw),
        "system": system.split("SYSTEM:", 1)[-1].strip(),
        "user_template": user.strip(),
    }


def prompt_inventory() -> dict:
    return {
        prompt_id: {
            side: {key: value for key, value in _prompt(prompt_id, side).items()
                   if key in {"file", "version", "sha256"}}
            for side in ("live", "candidate")
        }
        for prompt_id in PROMPT_PAIRS
    }


# --- the frozen replay instrument ---------------------------------------------------

REGISTRATION_PATH = config.REPO_ROOT / "data" / "reference" / "replay-registration.json"


class RegistrationError(RuntimeError):
    """The live replay instrument does not match the frozen registration."""


def replay_prompt_sha256() -> str:
    """Content address of the whole replay instrument: all four prompts in the two pairs."""
    parts = [METHOD_VERSION]
    for prompt_id in sorted(PROMPT_PAIRS):
        for side in ("live", "candidate"):
            parts.append(f"{prompt_id}:{side}:{prompt_text(prompt_id, side)}")
    return util.sha256_hex("\n".join(parts))


def registration() -> dict:
    """The live identity of the replay instrument, read from its owners, never copied."""
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "prompt_inventory": prompt_inventory(),
        "replay_prompt_sha256": replay_prompt_sha256(),
        "model": llm.VOICE_MODEL,
        "fallback_rate_ceiling": config.SHADOW_FALLBACK_RATE_CEILING,
        "minimums": {"complete_days": MIN_COMPLETE_DAYS, "party_days": MIN_PARTY_DAYS},
    }


def load_registration() -> dict:
    if not REGISTRATION_PATH.is_file():
        raise RegistrationError(
            f"no frozen registration at {REGISTRATION_PATH}; freeze the replay prompts before "
            "spending (scripts/shadow_replay.py --freeze)")
    return json.loads(REGISTRATION_PATH.read_text(encoding="utf-8"))


def registration_drift(frozen: dict | None = None) -> list[str]:
    """Fields where the live replay instrument differs from the frozen registration."""
    frozen = frozen if frozen is not None else load_registration()
    live = registration()
    drift = [key for key in ("method_version", "replay_prompt_sha256", "model",
                             "fallback_rate_ceiling", "minimums")
             if frozen.get(key) != live.get(key)]
    for prompt_id in sorted(PROMPT_PAIRS):
        for side in ("live", "candidate"):
            frozen_side = ((frozen.get("prompt_inventory") or {}).get(prompt_id) or {}).get(side)
            if frozen_side != live["prompt_inventory"][prompt_id][side]:
                drift.append(f"prompt_inventory.{prompt_id}.{side}")
    return sorted(drift)


def assert_registered(frozen: dict | None = None) -> dict:
    """Fail closed before any spend: the live prompts must be the registered prompts."""
    frozen = frozen if frozen is not None else load_registration()
    drift = registration_drift(frozen)
    if drift:
        raise RegistrationError(
            "the replay prompts are not the frozen ones; re-freeze the registration before a live "
            f"run. Drifted: {', '.join(drift)}")
    return frozen


# --- prompt rendering ---------------------------------------------------------------

def _render_prompt(prompt: dict, stats: dict, party: str, day: str) -> tuple[str, str]:
    selected = stats.get("selected_claims") or []
    allowed_counts = {
        "publications": stats.get("statements"),
        "claims": [row.get("counts") or {} for row in selected],
        "top_phrase": stats.get("top_phrase"),
    }
    fills = {
        "{day}": day,
        "{party}": {"D": "Democratic", "R": "Republican"}.get(party, party),
        "{code_computed_stats_json}": json.dumps(stats, ensure_ascii=False),
        "{talking_points_json}": json.dumps(selected, ensure_ascii=False),
        "{selected_claims_json}": json.dumps(selected, ensure_ascii=False),
        "{shared_nomenclature_json}": json.dumps(stats.get("shared_nomenclature") or [],
                                                 ensure_ascii=False),
        "{allowed_counts_json}": json.dumps(allowed_counts, ensure_ascii=False),
        "{publication_count_json}": json.dumps(stats.get("statements"), ensure_ascii=False),
    }
    system, user = prompt["system"], prompt["user_template"]
    for key, value in fills.items():
        system = system.replace(key, value)
        user = user.replace(key, value)
    return system, user


def request_sha256(system: str, user: str) -> str:
    """Content address of one rendered request, so a stored response can be audited to its input."""
    return util.sha256_hex(f"{system}\n---USER---\n{user}")


def _structured(text: str, stats: dict, *, expects_json: bool) -> tuple[dict, bool]:
    fallback = False
    if expects_json:
        try:
            value = json.loads(text)
            if not isinstance(value, dict) or not isinstance(value.get("composite"), str):
                raise ValueError("candidate response has no composite string")
            supplied = value.get("sentence_claims")
            if not isinstance(supplied, list):
                raise ValueError("candidate response has no sentence_claims list")
            return {"composite": value["composite"].strip(), "sentence_claims": supplied}, fallback
        except (json.JSONDecodeError, ValueError, TypeError):
            fallback = True
    composite = text.strip()
    return {
        "composite": composite,
        "sentence_claims": contracts.sentence_claims(composite, stats),
    }, fallback


def _guard_results(output: dict, stats: dict) -> dict:
    composite = output.get("composite") or ""
    selected = stats.get("selected_claims") or []
    allowed_quotes = {
        verify._norm(row.get("quote") or "")
        for row in selected if row.get("quote")
    }
    rendered_quotes = {
        verify._norm(match.group(1) or match.group(2) or "")
        for match in _QUOTE.finditer(composite)
    }
    quote_extension = sorted(rendered_quotes - allowed_quotes)

    outside_quotes = _QUOTE.sub(" ", composite).casefold()
    topic_assertions = sorted({
        topic for row in selected for topic in (row.get("topics") or [])
        if topic and any(
            re.search(rf"\b{re.escape(label)}\b", outside_quotes)
            for label in {str(topic).casefold(), str(topic).casefold().replace("_", " ")}
        )
    })

    computed = contracts.sentence_claims(composite, stats)
    multi_claim = [
        row["sentence_idx"] for row in computed if len(row.get("claim_ids") or []) > 1
    ]
    supplied = output.get("sentence_claims") or []
    mapping_mismatch = supplied != computed

    unit_mixing = []
    sentences = contracts.sentence_parts(composite)
    by_claim = {row.get("claim_id"): row for row in selected if row.get("claim_id")}
    for row in computed:
        ids = row.get("claim_ids") or []
        if len(ids) != 1 or row["sentence_idx"] >= len(sentences):
            continue
        counts = (by_claim.get(ids[0]) or {}).get("counts") or {}
        if (by_claim.get(ids[0]) or {}).get("object_type") != contracts.CLAIM_TYPE:
            continue
        if not all(isinstance(counts.get(unit), int) for unit in ("offices", "publications", "families")):
            continue
        sentence = sentences[row["sentence_idx"]].casefold()
        mentioned = any(str(counts[unit]) in sentence for unit in ("offices", "publications", "families"))
        if mentioned and not all(
            f"{counts[unit]} {unit}" in sentence for unit in ("offices", "publications", "families")
        ):
            unit_mixing.append(row["sentence_idx"])

    return {
        "unit_mixing": unit_mixing,
        "quote_extension": quote_extension,
        "topic_label_assertion": topic_assertions,
        "multi_claim_sentence": multi_claim,
        "sentence_mapping_mismatch": mapping_mismatch,
    }


def _scored(output: dict, stats: dict, *, fallback: bool) -> dict:
    """The full verifier plus the four R-33.6 zero-tolerance checks over one composite."""
    ok, reasons = verify.verify_daily_line(
        {"composite": output["composite"]}, json.dumps(stats, ensure_ascii=False), stats=stats,
    )
    guards = _guard_results(output, stats)
    return {
        "output_sha256": distill._record_hash(output),
        "verifier_passed": ok,
        "verifier_reasons": reasons,
        "guards": guards,
        "fallback": bool(fallback or not ok or any(bool(value) for value in guards.values())),
        "composite": output["composite"],
    }


# --- the record side: read, never generated -----------------------------------------

def _live_sha(prompt_id: str) -> str:
    return _prompt(prompt_id, "live")["sha256"]


def prompt_id_for(line: dict) -> str:
    return "P3" if line.get("quiet") else "P2"


def classify_record(line: dict) -> dict:
    """State whether one committed party-day is evidence about the live prompt, and why not.

    A day file is not automatically a sample of P2 v1.3 or P3 v1.1. The ladder here is the
    docs/37 rule 13 seam made explicit: same prompt lineage, a real model generator, and the
    stats schema the candidate prompt consumes.
    """
    prompt_id = prompt_id_for(line)
    stats = line.get("stats") or {}
    request = line.get("structured_request") or {}
    reasons = []

    if not line.get("composite"):
        reasons.append("no_composite")
    recorded_sha = ((request.get("prompt") or {}).get("sha256")) or line.get("prompt_sha")
    if recorded_sha != _live_sha(prompt_id):
        reasons.append("prompt_lineage_mismatch")
    generator = line.get("generator")
    if generator not in site.PRODUCTION_GENERATORS:
        reasons.append("not_model_generated")
    if stats.get("schema_version") != contracts.SCHEMA_VERSION:
        reasons.append("stats_schema_mismatch")
    recorded_digest = request.get("stats_sha256")
    if recorded_digest and recorded_digest != util.sha256_hex(
            json.dumps(stats, ensure_ascii=False)):
        reasons.append("stats_digest_mismatch")

    return {
        "prompt_id": prompt_id,
        "eligible": not reasons,
        "exclusion_reasons": reasons,
        "record_prompt_version": line.get("prompt_version"),
        "record_prompt_sha256": recorded_sha,
        "record_generator": generator,
        "record_stats_schema_version": stats.get("schema_version"),
    }


def record_side(line: dict) -> dict:
    """Score the committed production composite. Nothing here calls a model or spends."""
    stats = line.get("stats") or {}
    output = {
        "composite": line.get("composite") or "",
        "sentence_claims": line.get("sentence_claims")
        if isinstance(line.get("sentence_claims"), list)
        else contracts.sentence_claims(line.get("composite") or "", stats),
    }
    scored = _scored(output, stats, fallback=bool(line.get("fallback")))
    recorded = line.get("verifier") or {}
    return {
        **scored,
        "source": "committed_production_record",
        "generator": line.get("generator"),
        "composite_state": line.get("composite_state"),
        "prompt": {
            "file": PROMPT_PAIRS[prompt_id_for(line)][0],
            "version": line.get("prompt_version"),
            "sha256": line.get("prompt_sha"),
        },
        "recorded_verifier_passed": recorded.get("passed"),
        "recorded_fallback": bool(line.get("fallback")),
        # Re-running today's verifier over a committed composite can disagree with the verdict
        # stored on the day. That is a verifier-version finding, reported rather than smoothed.
        "verifier_verdict_moved": (recorded.get("passed") is not None
                                   and bool(recorded.get("passed")) != scored["verifier_passed"]),
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
    }


# --- the candidate side: the only thing that is generated ---------------------------

def candidate_request(line: dict, day: str, party: str) -> dict:
    """Render the candidate prompt against the stats production actually used."""
    prompt = _prompt(prompt_id_for(line), "candidate")
    stats = line.get("stats") or {}
    system, user = _render_prompt(prompt, stats, party, day)
    return {
        "day": day,
        "party": party,
        "prompt_id": prompt["id"],
        "prompt": {key: prompt[key] for key in ("file", "version", "sha256")},
        "system": system,
        "user": user,
        "request_sha256": request_sha256(system, user),
        "max_tokens": 400,
    }


def candidate_side(request: dict, line: dict, *, live: bool, call=None) -> dict:
    """Score the candidate output. Dry mode uses the deterministic voice and spends nothing."""
    stats = line.get("stats") or {}
    if live:
        caller = call or llm.direct_call
        response = caller(llm.VOICE_MODEL, request["system"], request["user"],
                          max_tokens=request["max_tokens"])
        raw = (response.get("text") or "").strip()
        tokens_in = int(response.get("tokens_in") or 0)
        tokens_out = int(response.get("tokens_out") or 0)
        output, fallback = _structured(raw, stats, expects_json=True)
    else:
        raw = distill._quiet_dry(stats) if line.get("quiet") else distill._compose_dry(stats)
        tokens_in = tokens_out = 0
        output, fallback = _structured(raw, stats, expects_json=False)
    return {
        **_scored(output, stats, fallback=fallback),
        "source": "generated_live" if live else "generated_dry",
        "prompt": request["prompt"],
        "request_sha256": request["request_sha256"],
        "response_sha256": util.sha256_hex(raw),
        "response_text": raw,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": llm.estimate_cost(llm.VOICE_MODEL, tokens_in, tokens_out,
                                      batched=False) if live else 0.0,
    }


# --- the run plan -------------------------------------------------------------------

def _complete_days(days_dir: Path) -> list[tuple[str, dict]]:
    """Every committed day carrying a composite for both composite parties."""
    rows = []
    for path in sorted(Path(days_dir).glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        day = payload.get("day") or path.stem
        lines = payload.get("daily_lines") or {}
        if all(isinstance(lines.get(party), dict) and lines[party].get("composite")
               for party in config.COMPOSITE_PARTIES):
            rows.append((day, payload))
    return rows


def gate_progress(complete_days: int, party_days: int) -> dict:
    """R-33.6 progress as a fraction, carried by every artifact this module writes."""
    return {
        "requirement": "R-33.6",
        "complete_days": {
            "observed": complete_days,
            "required": MIN_COMPLETE_DAYS,
            "fraction": round(complete_days / MIN_COMPLETE_DAYS, 6),
            "remaining": max(0, MIN_COMPLETE_DAYS - complete_days),
        },
        "party_days": {
            "observed": party_days,
            "required": MIN_PARTY_DAYS,
            "fraction": round(party_days / MIN_PARTY_DAYS, 6),
            "remaining": max(0, MIN_PARTY_DAYS - party_days),
        },
        "estimator": "committed party-days whose production record was written by the live prompt "
                     "of its pair, over the R-33.6 minimums",
        "unit": "party-day (one party lane on one measured day)",
        "denominator": "60 complete days and 200 party-days, both required",
        "passed": complete_days >= MIN_COMPLETE_DAYS and party_days >= MIN_PARTY_DAYS,
    }


def plan(days_dir: Path) -> dict:
    """The free, deterministic run plan: what exists, what is eligible, and what it would cost."""
    days = _complete_days(days_dir)
    rows, exclusions = [], {}
    eligible_days = 0
    for day, payload in days:
        lines = payload.get("daily_lines") or {}
        day_rows = []
        for party in config.COMPOSITE_PARTIES:
            line = lines.get(party) or {}
            verdict = classify_record(line)
            request = candidate_request(line, day, party)
            day_rows.append({
                "day": day,
                "party": party,
                **verdict,
                "candidate_prompt": request["prompt"],
                "request_sha256": request["request_sha256"],
                "approx_tokens_in": llm.approx_tokens(request["system"] + request["user"]),
                "max_tokens_out": request["max_tokens"],
            })
            for reason in verdict["exclusion_reasons"]:
                exclusions[reason] = exclusions.get(reason, 0) + 1
        rows.extend(day_rows)
        if all(row["eligible"] for row in day_rows):
            eligible_days += 1

    eligible_rows = [row for row in rows if row["eligible"]]
    tokens_in = sum(row["approx_tokens_in"] for row in eligible_rows)
    tokens_out = sum(row["max_tokens_out"] for row in eligible_rows)
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "source": str(days_dir),
        "ladder": {
            "committed_day_files": len(list(Path(days_dir).glob("*.json"))),
            "days_with_both_composites": len(days),
            "party_days_with_composites": len(rows),
            "gate_eligible_days": eligible_days,
            "gate_eligible_party_days": len(eligible_rows),
            "exclusion_reasons": dict(sorted(exclusions.items())),
        },
        "window": {
            "start": days[0][0] if days else None,
            "end": days[-1][0] if days else None,
        },
        "gate_progress": gate_progress(eligible_days, len(eligible_rows)),
        "prompt_inventory": prompt_inventory(),
        "replay_prompt_sha256": replay_prompt_sha256(),
        "cost_projection": {
            "model": llm.VOICE_MODEL,
            "calls": len(eligible_rows),
            "calls_basis": "one call per gate-eligible party-day; the live side is read from the "
                           "committed record and costs nothing",
            "approx_tokens_in": tokens_in,
            "max_tokens_out": tokens_out,
            "estimated_cost_usd": llm.estimate_cost(llm.VOICE_MODEL, tokens_in, tokens_out,
                                                    batched=False),
            "estimate_basis": "approx 4 characters per token; output priced at the ceiling, so the "
                              "estimate is an upper bound",
        },
        "party_day_plan": rows,
    }


# --- the spend gate -----------------------------------------------------------------

def budget_preflight(projected_usd: float, *, bound_usd: float, day: str) -> dict:
    """Read the month-to-date ledger and the code ceiling before any live replay call.

    Two independent conditions, both of which must hold. The run must fit under the authorized
    hard bound, and the remaining headroom under the monthly code ceiling must be at least twice
    that bound, so a replay can never be the spend that leaves the daily voice with no room. The
    daily pipeline is the thing that must not starve; this harness is optional.
    """
    mtd = ops.month_to_date_usd(day, include_day=True)
    headroom = round(config.LLM_MONTHLY_CEILING_USD - mtd, 6)
    reasons = []
    if projected_usd > bound_usd:
        reasons.append("projection_exceeds_authorized_bound")
    if headroom < 2 * bound_usd:
        reasons.append("headroom_below_twice_the_bound")
    if ops.voice_budget_state(day, projected_usd) == "halt":
        reasons.append("budget_governor_halt")
    if llm.dry_run():
        # The charter keeps ANTHROPIC_API_KEY in Actions secrets only, so an operator box has no
        # key by design. Say that here rather than letting _headers raise a KeyError mid-run,
        # after the registration has been asserted and the operator believes a run started.
        reasons.append("no_api_key")
    return {
        "day": day,
        "api_key_available": not llm.dry_run(),
        "month_to_date_usd": mtd,
        "monthly_code_ceiling_usd": config.LLM_MONTHLY_CEILING_USD,
        "warn_threshold_usd": config.LLM_MONTHLY_WARN_USD,
        "headroom_usd": headroom,
        "authorized_bound_usd": bound_usd,
        "required_headroom_usd": round(2 * bound_usd, 6),
        "projected_usd": projected_usd,
        "governor_state": ops.voice_budget_state(day, projected_usd),
        "blocking_reasons": reasons,
        "cleared": not reasons,
    }


class BudgetPreflightError(RuntimeError):
    """The live replay was refused before any call, by the budget preflight."""


# --- the append-only evidence file --------------------------------------------------

EVIDENCE_NAME = "evidence.jsonl"


def evidence_path(root: Path | None = None) -> Path:
    return (Path(root) if root else config.DERIVED / "replay") / EVIDENCE_NAME


def load_evidence(root: Path | None = None) -> list[dict]:
    path = evidence_path(root)
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def evidence_key(row: dict) -> tuple:
    """One party-day under one candidate prompt. A new candidate prompt replays the day again."""
    return (row["day"], row["party"], row["candidate_prompt"]["sha256"])


def replayed_keys(root: Path | None = None) -> set:
    return {evidence_key(row) for row in load_evidence(root)}


def pending(days_dir: Path, root: Path | None = None) -> list[tuple]:
    """Gate-eligible party-days with no evidence yet under the current candidate prompt."""
    done = replayed_keys(root)
    out = []
    for row in plan(days_dir)["party_day_plan"]:
        if not row["eligible"]:
            continue
        if (row["day"], row["party"], row["candidate_prompt"]["sha256"]) not in done:
            out.append((row["day"], row["party"]))
    return out


def evidence_rows(report: dict) -> list[dict]:
    """Turn one run's scored party-days into evidence rows. Deterministic given the responses."""
    rows = []
    for row in report["party_day_results"]:
        candidate = row["candidate"]
        rows.append({
            "schema_version": 1,
            "method_version": report["method_version"],
            "mode": report["mode"],
            "day": row["day"],
            "party": row["party"],
            "prompt_id": row["prompt_id"],
            "replay_prompt_sha256": report["replay_prompt_sha256"],
            "candidate_prompt": candidate["prompt"],
            "request_sha256": candidate["request_sha256"],
            "response_sha256": candidate["response_sha256"],
            "response_text": candidate["response_text"],
            "tokens_in": candidate["tokens_in"],
            "tokens_out": candidate["tokens_out"],
            "cost_usd": candidate["cost_usd"],
            "record": {key: row["live"][key] for key in
                       ("composite", "output_sha256", "verifier_passed", "verifier_reasons",
                        "guards", "fallback", "generator", "composite_state", "prompt",
                        "recorded_verifier_passed", "verifier_verdict_moved")},
            "candidate": {key: candidate[key] for key in
                          ("composite", "output_sha256", "verifier_passed", "verifier_reasons",
                           "guards", "fallback")},
            "changed": row["changed"],
        })
    return rows


def append_evidence(rows: list[dict], root: Path | None = None) -> dict:
    """Append rows never seen before. Existing lines are never rewritten or reordered.

    Only live rows are admitted. A dry row is a deterministic-voice composite, not an answer
    from the candidate prompt, and a gate that counted them would be counting the harness's own
    template as evidence about a model.
    """
    dry = [row for row in rows if row.get("mode") != "live"]
    if dry:
        raise ValueError(
            f"{len(dry)} non-live rows offered to the replay evidence file; only real model "
            "responses are evidence for the R-33.6 gate")
    path = evidence_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    known = replayed_keys(root)
    fresh = [row for row in rows if evidence_key(row) not in known]
    if fresh:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            for row in sorted(fresh, key=evidence_key):
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "path": str(path),
        "appended": len(fresh),
        "already_present": len(rows) - len(fresh),
        "total_rows": len(known) + len(fresh),
    }


# --- the comparison -----------------------------------------------------------------

def _summary(rows: list[dict], side: str) -> dict:
    offered = len(rows)
    fallback_count = sum(1 for row in rows if row[side]["fallback"])
    return {
        "offered_party_days": offered,
        "verifier_passed": sum(1 for row in rows if row[side]["verifier_passed"]),
        "verifier_failed": sum(1 for row in rows if not row[side]["verifier_passed"]),
        "fallback_count": fallback_count,
        "fallback_rate": round(fallback_count / offered, 6) if offered else None,
        "fallback_rate_estimator": "fallback party-days / offered party-days",
        "fallback_rate_unit": "party-day share",
        "fallback_rate_denominator": offered,
        "guard_violation_party_days": {
            guard: sum(1 for row in rows if row[side]["guards"][guard]) for guard in GUARD_NAMES
        },
        "tokens_in": sum(row[side].get("tokens_in") or 0 for row in rows),
        "tokens_out": sum(row[side].get("tokens_out") or 0 for row in rows),
        "cost_usd": round(sum(row[side].get("cost_usd") or 0.0 for row in rows), 6),
    }


SPEND_BOUND_USD = 3.0  # the hard bound Michael authorized for the R-33.6 live replay


def run(days_dir: Path, *, live: bool = False, allow_api_spend: bool = False,
        limit: int | None = None, call=None, only: set | None = None,
        bound_usd: float = SPEND_BOUND_USD, day: str | None = None) -> dict:
    """Compare the committed live record against a generated candidate. Dry is free and default.

    ``only`` restricts the run to a set of (day, party) pairs, which is how the incremental
    accumulator replays days not yet in the evidence file.
    """
    if live and not allow_api_spend:
        raise PermissionError("live shadow replay requires allow_api_spend=True")
    run_plan = plan(days_dir)
    preflight = None
    if live:
        # Freeze the instrument before the money, in this order: an edited prompt must not be
        # able to quietly become the thing a published sheet was produced by (docs/35 §10.2).
        assert_registered()
        preflight = budget_preflight(
            run_plan["cost_projection"]["estimated_cost_usd"],
            bound_usd=bound_usd, day=day or date.today().isoformat(),
        )
        if not preflight["cleared"]:
            raise BudgetPreflightError(
                "live shadow replay refused by the budget preflight: "
                f"{', '.join(preflight['blocking_reasons'])}. "
                f"month-to-date {preflight['month_to_date_usd']} USD, headroom "
                f"{preflight['headroom_usd']} USD, bound {bound_usd} USD.")

    days = _complete_days(days_dir)
    if limit is not None:
        days = days[:max(0, limit)]

    rows, skipped = [], []
    eligible_days = 0
    for day, payload in days:
        lines = payload.get("daily_lines") or {}
        day_eligible = True
        for party in config.COMPOSITE_PARTIES:
            line = lines.get(party) or {}
            verdict = classify_record(line)
            if not verdict["eligible"]:
                day_eligible = False
                skipped.append({"day": day, "party": party,
                                "exclusion_reasons": verdict["exclusion_reasons"]})
                continue
            if only is not None and (day, party) not in only:
                continue
            request = candidate_request(line, day, party)
            record = record_side(line)
            candidate = candidate_side(request, line, live=live, call=call)
            rows.append({
                "day": day, "party": party, "prompt_id": verdict["prompt_id"],
                "classification": verdict,
                "live": record, "candidate": candidate,
                "changed": record["output_sha256"] != candidate["output_sha256"],
            })
        if day_eligible:
            eligible_days += 1

    # A day counts toward the complete-days minimum only when BOTH party lanes were actually
    # scored in this run. Counting eligible days against scored party-days would let a run
    # restricted with `only` to a single lane report a whole day of gate progress.
    scored_by_day: dict[str, set] = {}
    for row in rows:
        scored_by_day.setdefault(row["day"], set()).add(row["party"])
    scored_days = len(scored_by_day)
    complete_scored_days = sum(1 for parties in scored_by_day.values()
                               if parties >= set(config.COMPOSITE_PARTIES))
    live_summary = _summary(rows, "live")
    candidate_summary = _summary(rows, "candidate")
    zero_tolerance = (
        bool(rows)
        and candidate_summary["verifier_failed"] == 0
        and all(value == 0 for value in candidate_summary["guard_violation_party_days"].values())
    )
    rate = candidate_summary["fallback_rate"]
    fallback_pass = rate is not None and rate <= config.SHADOW_FALLBACK_RATE_CEILING
    progress = gate_progress(complete_scored_days, len(rows))
    return {
        "schema_version": 2,
        "method_version": METHOD_VERSION,
        "mode": "live" if live else "dry_run",
        "source": str(days_dir),
        "comparison_design": "the live side is the committed production record; only the "
                             "candidate side is generated",
        "window": {
            "start": rows[0]["day"] if rows else None,
            "end": rows[-1]["day"] if rows else None,
            "scored_days": scored_days,
            "scored_party_days": len(rows),
            "gate_eligible_days": eligible_days,
        },
        "ladder": run_plan["ladder"],
        "minimums": {"complete_days": MIN_COMPLETE_DAYS, "party_days": MIN_PARTY_DAYS},
        "gate_progress": progress,
        "prompt_inventory": prompt_inventory(),
        "replay_prompt_sha256": replay_prompt_sha256(),
        "fallback_rate_ceiling": config.SHADOW_FALLBACK_RATE_CEILING,
        "projected_live_cost_usd": run_plan["cost_projection"]["estimated_cost_usd"],
        "actual_cost_usd": candidate_summary["cost_usd"],
        "budget_preflight": preflight,
        "live": live_summary,
        "candidate": candidate_summary,
        "excluded_party_days": skipped,
        "comparison": {
            "changed_party_days": sum(1 for row in rows if row["changed"]),
            "unchanged_party_days": sum(1 for row in rows if not row["changed"]),
            "record_verifier_verdict_moved": sum(
                1 for row in rows if row["live"]["verifier_verdict_moved"]),
        },
        "activation_gate": {
            "minimum_sample_passed": progress["passed"],
            "zero_tolerance_checks_passed": zero_tolerance,
            "fallback_rate_passed": fallback_pass,
            "ready": bool(live and progress["passed"] and zero_tolerance and fallback_pass),
            "dry_run_cannot_activate": not live,
        },
        "party_day_results": rows,
    }
