"""Dry-first shadow replay for prompt activation decisions."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from . import config, contracts, distill, eligibility, llm, ops, util, verify


METHOD_VERSION = "shadow-replay-v1"
MIN_COMPLETE_DAYS = 60
MIN_PARTY_DAYS = 200
PROMPT_PAIRS = {
    "P2": ("P2_daily_line.v1.3.txt", "P2_daily_line.v1.4.txt"),
    "P3": ("P3_quiet_day.v1.1.txt", "P3_quiet_day.v1.2.txt"),
}
_VERSION = re.compile(r"\.v(\d+\.\d+)\.txt$")
_QUOTE = re.compile(r'"([^"]+)"|“([^”]+)”')


def _prompt(filename: str, prompt_id: str) -> dict:
    raw = (llm.PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()
    system, marker, user = raw.partition("\n---USER---\n")
    if not marker:
        raise ValueError(f"prompt has no user separator: {filename}")
    return {
        "id": prompt_id,
        "file": filename,
        "version": (_VERSION.search(filename) or [None, "0.0"])[1],
        "sha256": util.sha256_hex(raw),
        "system": system.split("SYSTEM:", 1)[-1].strip(),
        "user_template": user.strip(),
    }


def prompt_inventory() -> dict:
    return {
        prompt_id: {
            "live": {key: value for key, value in _prompt(pair[0], prompt_id).items()
                     if key in {"file", "version", "sha256"}},
            "candidate": {key: value for key, value in _prompt(pair[1], prompt_id).items()
                          if key in {"file", "version", "sha256"}},
        }
        for prompt_id, pair in PROMPT_PAIRS.items()
    }


def _top_phrase(payload: dict, party: str, day: str) -> dict | None:
    for row in payload.get("top_synchronized") or []:
        if not isinstance(row, dict) or row.get("party") != party:
            continue
        classified = eligibility.classify_phrase(
            row.get("ngram") or "", day=day, family_count=row.get("family_count"),
        )
        if eligibility.eligible_for_surface(classified, "daily_line"):
            return {
                "text": row.get("ngram"), "members": row.get("day_peak"),
                "family_count": row.get("family_count"),
            }
    return None


def _stats(payload: dict, party: str, day: str) -> tuple[dict, bool]:
    line = ((payload.get("daily_lines") or {}).get(party) or {})
    source_stats = line.get("stats") or {}
    count = source_stats.get("statements")
    if not isinstance(count, int):
        count = 0
    claims = ((payload.get("talking_points") or {}).get(party) or [])
    stats = distill.build_stats(party, day, count, claims, _top_phrase(payload, party, day))
    return stats, bool(line.get("quiet"))


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
        "{shared_nomenclature_json}": json.dumps(stats.get("shared_nomenclature") or [], ensure_ascii=False),
        "{allowed_counts_json}": json.dumps(allowed_counts, ensure_ascii=False),
        "{publication_count_json}": json.dumps(stats.get("statements"), ensure_ascii=False),
    }
    system, user = prompt["system"], prompt["user_template"]
    for key, value in fills.items():
        system = system.replace(key, value)
        user = user.replace(key, value)
    return system, user


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


def _one(prompt: dict, stats: dict, party: str, day: str, quiet: bool, *,
         live: bool, candidate: bool) -> dict:
    if live:
        system, user = _render_prompt(prompt, stats, party, day)
        response = llm.direct_call(llm.VOICE_MODEL, system, user, max_tokens=400)
        raw = (response.get("text") or "").strip()
        output, fallback = _structured(raw, stats, expects_json=candidate)
        tokens_in = int(response.get("tokens_in") or llm.approx_tokens(system + user))
        tokens_out = int(response.get("tokens_out") or llm.approx_tokens(raw))
    else:
        raw = distill._quiet_dry(stats) if quiet else distill._compose_dry(stats)
        output, fallback = _structured(raw, stats, expects_json=False)
        tokens_in = tokens_out = 0
    ok, reasons = verify.verify_daily_line(
        {"composite": output["composite"]}, json.dumps(stats, ensure_ascii=False), stats=stats,
    )
    guards = _guard_results(output, stats)
    if not ok or any(bool(value) for value in guards.values()):
        fallback = True
    return {
        "prompt": {key: prompt[key] for key in ("file", "version", "sha256")},
        "output_sha256": distill._record_hash(output),
        "verifier_passed": ok,
        "verifier_reasons": reasons,
        "guards": guards,
        "fallback": fallback,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "composite": output["composite"],
    }


def _complete_days(days_dir: Path) -> list[tuple[str, dict]]:
    rows = []
    for path in sorted(days_dir.glob("*.json")):
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


def _summary(rows: list[dict], side: str) -> dict:
    offered = len(rows)
    fallback_count = sum(1 for row in rows if row[side]["fallback"])
    guard_counts = {
        guard: sum(1 for row in rows if row[side]["guards"][guard])
        for guard in ("unit_mixing", "quote_extension", "topic_label_assertion",
                      "multi_claim_sentence", "sentence_mapping_mismatch")
    }
    return {
        "offered_party_days": offered,
        "verifier_passed": sum(1 for row in rows if row[side]["verifier_passed"]),
        "verifier_failed": sum(1 for row in rows if not row[side]["verifier_passed"]),
        "fallback_count": fallback_count,
        "fallback_rate": round(fallback_count / offered, 6) if offered else None,
        "fallback_rate_estimator": "fallback party-days / offered party-days",
        "fallback_rate_unit": "party-day share",
        "fallback_rate_denominator": offered,
        "guard_violation_party_days": guard_counts,
    }


def run(days_dir: Path, *, live: bool = False, allow_api_spend: bool = False,
        limit: int | None = None) -> dict:
    """Compare live and candidate prompt lineages. Dry-run is the default and spends nothing."""
    if live and not allow_api_spend:
        raise PermissionError("live shadow replay requires allow_api_spend=True")
    days = _complete_days(days_dir)
    if limit is not None:
        days = days[:max(0, limit)]
    projected = 0.0
    if live:
        projected = llm.estimate_cost(
            llm.VOICE_MODEL, len(days) * 4 * 3000, len(days) * 4 * 400,
            batched=False, on_date=date.today().isoformat(),
        )
        if ops.voice_budget_state(date.today().isoformat(), projected) == "halt":
            raise RuntimeError("budget governor halted live shadow replay")

    prompts = {
        prompt_id: {
            "live": _prompt(pair[0], prompt_id),
            "candidate": _prompt(pair[1], prompt_id),
        }
        for prompt_id, pair in PROMPT_PAIRS.items()
    }
    rows = []
    for day, payload in days:
        for party in config.COMPOSITE_PARTIES:
            stats, quiet = _stats(payload, party, day)
            prompt_id = "P3" if quiet else "P2"
            live_row = _one(
                prompts[prompt_id]["live"], stats, party, day, quiet,
                live=live, candidate=False,
            )
            candidate_row = _one(
                prompts[prompt_id]["candidate"], stats, party, day, quiet,
                live=live, candidate=True,
            )
            rows.append({
                "day": day, "party": party, "prompt_id": prompt_id,
                "live": live_row, "candidate": candidate_row,
                "changed": live_row["output_sha256"] != candidate_row["output_sha256"],
            })

    live_summary = _summary(rows, "live")
    candidate_summary = _summary(rows, "candidate")
    complete_days = len(days)
    party_days = len(rows)
    enough = complete_days >= MIN_COMPLETE_DAYS and party_days >= MIN_PARTY_DAYS
    zero_tolerance = (
        candidate_summary["verifier_failed"] == 0
        and all(value == 0 for value in candidate_summary["guard_violation_party_days"].values())
    )
    rate = candidate_summary["fallback_rate"]
    fallback_pass = rate is not None and rate <= config.SHADOW_FALLBACK_RATE_CEILING
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "mode": "live" if live else "dry_run",
        "source": str(days_dir),
        "window": {
            "start": days[0][0] if days else None,
            "end": days[-1][0] if days else None,
            "complete_days": complete_days,
            "party_days": party_days,
        },
        "minimums": {"complete_days": MIN_COMPLETE_DAYS, "party_days": MIN_PARTY_DAYS},
        "prompt_inventory": prompt_inventory(),
        "fallback_rate_ceiling": config.SHADOW_FALLBACK_RATE_CEILING,
        "projected_live_cost_usd": projected,
        "live": live_summary,
        "candidate": candidate_summary,
        "comparison": {
            "changed_party_days": sum(1 for row in rows if row["changed"]),
            "unchanged_party_days": sum(1 for row in rows if not row["changed"]),
        },
        "activation_gate": {
            "minimum_sample_passed": enough,
            "zero_tolerance_checks_passed": zero_tolerance,
            "fallback_rate_passed": fallback_pass,
            "ready": live and enough and zero_tolerance and fallback_pass,
            "dry_run_cannot_activate": not live,
        },
        "party_day_results": rows,
    }
