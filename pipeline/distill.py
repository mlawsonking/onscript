"""B3/B4 — the Daily Line: P2 composite per party per day, then the blocking verifier (§6.2/§6.3).

Real mode calls Sonnet (batch, direct-call fallback for the timeout kill-test). Dry-run
composes a deterministic first-person-plural composite using ONLY the code-computed STATS
numbers and verbatim fragment quotes (<=10 words) — so it passes the digit-whitelist and
quote-grounding checks by construction. Either way the composite is run through the verifier;
any violation drops the line to the honest fallback (§7.2), never silence.
"""
from __future__ import annotations

import json
import re

from . import boilerplate, config, contracts, eligibility, llm, nomenclature, util, verify

# Owning constant for the structured-composite method. The instrument fingerprint
# imports this so its attestation cannot drift from the running method (docs/36 Y1).
STRUCTURED_COMPOSITE_VERSION = "structured-composite-v1"

_QUOTE_MAX_WORDS = 10

COMPOSITE_STATES = (
    "generated_verified",
    "deterministic_fallback",
    "withheld_no_eligible_claim",
    "withheld_verifier_failure",
    "corrected",
)

# docs/19 §2c — appended to the live-voice system prompt (runtime, flag-gated) when any talking point
# carries a nomenclature annotation. Runtime-appended rather than baked into the committed P2/P3 files
# so the prompts (and prompts_sha over them) are byte-stable while the tagger is dark; ops.prompts_sha
# folds a marker of this clause when the flag is on, so the published fingerprint stays honest.
NOMENCLATURE_VOICE_CLAUSE = (
    "\n\nSome talking points include a \"nomenclature\" field. That phrase is the OFFICIAL NAME of a "
    "bill or committee, cited to an external record — it is not a coordinated message. Do not present "
    "it as evidence that members share a talking point; if you refer to it at all, name it plainly as "
    "legislation. Members typing a bill's own name is not message coordination."
)

# Register guard (§Session-8): mechanical checks that a composite has not drifted out of the deadpan-
# clinical voice — no fourth-wall/schema words, no enthusiasm/irony markers, no hashtags/emoji. Runs
# on the golden set on every prompt/model change, and could gate live output. Tone that survives all
# of these (snark by word choice) is caught by the frozen golden snapshot diff, not this.
_REGISTER_BANS = ("cluster", "talking point", "stats block", "sync_min", "sync minimum",
                  "the top phrase", "provided fragment", " null", "json")


def register_violations(text: str) -> list[str]:
    t = text or ""
    low = t.lower()
    out = [f"schema word: {w.strip()!r}" for w in _REGISTER_BANS if w in low]
    if "!" in t:
        out.append("exclamation (enthusiasm/irony marker)")
    if re.search(r"#\w", t):
        out.append("hashtag")
    if any(ord(c) >= 0x1F000 or 0x2190 <= ord(c) <= 0x2BFF for c in t):
        out.append("emoji/pictograph")
    if len(t.split()) > 120:
        out.append("over 120 words")
    return out


def _quote(fragment_text: str, label: str = "") -> str:
    """Return a verbatim quote window of at most ten words that still contains P.

    A label-blind prefix can cut off a late support phrase and make the deterministic composite fail
    its own binding verifier. For a long fragment, slide the ten-word window until it contains the
    label. The first valid window keeps the most preceding context and is deterministic.
    """
    words = (fragment_text or "").split()
    if len(words) <= _QUOTE_MAX_WORDS or not label:
        return " ".join(words[:_QUOTE_MAX_WORDS])
    for start in range(len(words) - _QUOTE_MAX_WORDS + 1):
        window = " ".join(words[start:start + _QUOTE_MAX_WORDS])
        if boilerplate.contains_gram(window, label):
            return window
    return " ".join(words[:_QUOTE_MAX_WORDS])


def build_stats(party: str, day: str, party_statement_count: int, talking_points: list[dict],
                top_phrase: dict | None) -> dict:
    """Code-computed STATS block — the ONLY source of numbers the composite may use (§6.2 P2 rule 3)."""
    tps = []
    selected, shared_nomenclature = eligibility.select_claims(talking_points, day=day, limit=2)
    surface_counts = {name: 0 for name in eligibility.SURFACE_CLASSES}
    for candidate in talking_points:
        classified = eligibility.classify_claim(candidate, day=day)
        surface_counts[classified["surface_class"]] += 1

    rendered_top = top_phrase
    top_classification = None
    if isinstance(top_phrase, dict) and top_phrase.get("text"):
        top_classification = eligibility.classify_phrase(
            top_phrase["text"], day=day, family_count=top_phrase.get("family_count")
        )
        if top_classification["surface_class"] == "nomenclature":
            shared_nomenclature.append({
                "label": top_phrase["text"],
                "member_count": top_phrase.get("members"),
                "counts": top_phrase.get("counts") or {},
                **top_classification,
            })
        if top_classification["surface_class"] != "message":
            rendered_top = None
    # docs/19 §2c — congress for the pre-distill nomenclature annotation, resolved ONLY when the tagger
    # is live so the flag-off STATS block is byte-identical (docs/19 §3.4). Annotation, not deletion.
    cong = util.congress_for_date(day) if config.feature_on("nomenclature_tags") else None
    selected_entries = []
    for claim_index, tp in enumerate(selected):
        # The quote MUST be verbatim member speech: the blocking verifier grounds it against real
        # fragment text, NEVER against the code-computed label (a punctuation-stripped n-gram that is
        # often not a raw substring of any statement — quoting it would violate citation integrity).
        # Pick the SHORTEST fragment in the cluster: on-topic (all fragments share the label phrase),
        # complete, and clean — not a mid-truncated long one that dangles. The label rides along as
        # the UNQUOTED talking-point name. §Session-5 (HIGH-1 fix).
        label = tp.get("label", "")
        quote_candidates = []
        for fragment in (tp.get("fragments") or []):
            text = fragment.get("text") or ""
            if not text or not boilerplate.contains_gram(text, label):
                continue
            quote = _quote(text, label)
            if boilerplate.contains_gram(quote, label):
                quote_candidates.append((len(text.split()), text, quote))
        quote = min(quote_candidates, key=lambda row: (row[0], row[1]))[2] if quote_candidates else ""
        if tp.get("schema_version") == contracts.SCHEMA_VERSION:
            quote = tp.get("display_quote") or ""
        claim_id = tp.get("claim_id") or tp.get("id") or f"{day}-{party}-legacy-{claim_index:02d}"
        entry = {"label": tp["label"], "members": tp["member_count"], "quote": quote,
                 "topics": tp.get("topics", []),
                 "claim_id": claim_id,
                 "claim_type": contracts.CLAIM_TYPE,
                 "object_type": tp.get("object_type"),
                 "surface_class": tp.get("surface_class"),
                 "surface_eligible": tp.get("surface_eligible"),
                 "surface_classifier": tp.get("classifier"),
                 "topic_provenance": tp.get("topic_provenance") or [],
                 "counts": tp.get("counts") or {
                     "offices": tp.get("member_count"),
                     "publications": len(tp.get("statements") or []),
                     "families": tp.get("member_count"),
                     "support_units": tp.get("member_count"),
                 }}
        # docs/19 §2c — annotate a talking point whose KEY is an official name (bill title / committee
        # name) so the live voice cannot launder it into message-coordination prose and have the
        # verifier pass it (the members really did type the name). ANNOTATION ONLY: the quote, the
        # citation path, and verify.is_verbatim are untouched; _compose_llm reads this field to instruct
        # the model. DARK until FEATURES["nomenclature_tags"] (cong is None when off -> no field added).
        if cong is not None:
            v = nomenclature.is_nomenclature(tp["label"], cong)
            if v:
                entry["nomenclature"] = {"lane": v["lane"], "cite": v["cite"], "class": v["class"]}
        tps.append(entry)
        if tp.get("surface_class") == "message":
            selected_entries.append(entry)
    return {"schema_version": contracts.SCHEMA_VERSION,
            "party": party, "day": day, "statements": party_statement_count,
            "talking_points": tps, "top_phrase": rendered_top,
            "selected_claims": selected_entries,
            "shared_nomenclature": [
                {
                    "claim_id": row.get("claim_id") or row.get("id"),
                    "label": row.get("label"),
                    "counts": row.get("counts") or {"support_units": row.get("member_count")},
                    "surface_class": "nomenclature",
                    "classifier": row.get("classifier"),
                }
                for row in {row.get("label"): row for row in shared_nomenclature}.values()
            ],
            "surface_class_counts": surface_counts,
            "eligibility_withheld_count": surface_counts.get("unknown", 0),
            "top_phrase_classification": top_classification,
            "claim_ids": [row["claim_id"] for row in selected_entries if row.get("claim_id")],
            "sync_min": config.SYNC_MIN_MEMBERS}  # the coordination threshold (for the no-coordination line)


def _compose_dry(stats: dict, allow_absence_claim: bool = True) -> str:
    """Deterministic composite: numbers from STATS, quotes from fragments only, first-person plural.

    allow_absence_claim=False when STATS were emptied by the Art. XIII privacy filter rather than by
    the corpus. The "no phrase cleared the bar" line below is a FINDING (the silence story), and a
    silence manufactured by our own suppression is a fabricated finding — the privacy fix inventing
    a claim would be a second integrity failure on top of the one it is fixing (Art. II)."""
    parts = [f"Today {stats['statements']} of us released statements."]
    quoted = 0
    rendered_claims = (stats.get("selected_claims") if "selected_claims" in stats
                       else stats.get("talking_points") or [])
    # Classified STATS carry the review selection explicitly and are capped upstream. Legacy
    # fixtures have no selection field, so retain their frozen rendering contract.
    claims_to_render = rendered_claims[:2] if "selected_claims" in stats else rendered_claims
    for tp in claims_to_render:
        if tp["quote"]:
            # "carried", not "said": the phrase appeared in these members' statements — which may quote
            # third parties. "N of us" (member count), not "N statements" — members is the unit. §S8.
            counts = tp.get("counts") or {}
            if tp.get("object_type") == contracts.CLAIM_TYPE:
                parts.append(
                    f'{counts.get("offices", 0)} offices across '
                    f'{counts.get("publications", 0)} publications and '
                    f'{counts.get("families", 0)} families carried "{tp["quote"]}".'
                )
            else:
                parts.append(f'{tp["members"]} of us carried "{tp["quote"]}".')
            quoted += 1
    tp = stats.get("top_phrase")
    if quoted == 0 and not (tp and tp.get("text")) and allow_absence_claim:
        # Honest measured ABSENCE: statements went out, but no phrase cleared the coordination bar.
        # This turns an empty column into a finding (the silence story), not a missing feature.
        # Gated: an absence produced by privacy suppression is not a measurement (see docstring).
        if stats.get("eligibility_withheld_count"):
            parts.append("No measured phrase met the message-eligibility standard today.")
        else:
            parts.append(f"No phrase was shared by {stats.get('sync_min', config.SYNC_MIN_MEMBERS)} "
                         f"or more of us today.")
    if tp and tp.get("text"):
        # No quotation marks: the top synchronized phrase is a code-computed ledger n-gram, not a
        # verbatim member quote — render it as the measured phrase it is (§Session-5 HIGH-1 fix).
        parts.append(f'Our most synchronized phrase, used by {tp["members"]} of us: {tp["text"]}.')
    text = " ".join(parts)
    words = text.split()
    if len(words) > 120:
        text = " ".join(words[:120])
    return text


def _quiet_dry(stats: dict) -> str:
    # Thin/quiet days still carry the one code-computed fact worth stating: the day's top
    # synchronized phrase + how many converged on it (§Session-4(g)). No LLM claim needed — the
    # phrase is a real ledger fact and renders unquoted, outside the talking-point quote binding.
    parts = [f"We released {stats['statements']} statements today."]
    tp = stats.get("top_phrase")
    if tp and tp.get("text"):
        # No quotation marks — a code-computed ledger phrase, not a verbatim quote (§Session-5 HIGH-1).
        parts.append(f'Even so, {tp["members"]} of us converged on the same phrase: {tp["text"]}.')
    elif stats.get("eligibility_withheld_count"):
        parts.append("No measured phrase met the message-eligibility standard today.")
    return " ".join(parts)


_PARTY_FULL = {"D": "Democratic", "R": "Republican"}


def measurement_lead(party: str, day: str, publications: int | None) -> str:
    """Return the neutral code-owned sentence that precedes composite prose."""
    label = _PARTY_FULL.get(party, party)
    if isinstance(publications, int):
        return f"Measurement: {publications} publications were observed for the {label} party on {day}."
    return f"Measurement: the publication count is unavailable for the {label} party on {day}."


def state_for_line(line: dict | None, *, corrected: bool = False) -> str:
    """Resolve an explicit state for new and legacy Daily Line records."""
    if corrected:
        return "corrected"
    if not isinstance(line, dict):
        return "withheld_no_eligible_claim"
    stored = line.get("composite_state")
    if stored in COMPOSITE_STATES:
        return stored
    verifier = line.get("verifier") or {}
    if verifier.get("checked") and verifier.get("passed") is False:
        return "withheld_verifier_failure"
    stats = line.get("stats") or {}
    selected = (stats.get("selected_claims") if "selected_claims" in stats
                else stats.get("talking_points") or [])
    top = stats.get("top_phrase")
    if stats and not selected and not (isinstance(top, dict) and top.get("text")):
        return "withheld_no_eligible_claim"
    if line.get("generator") == "sonnet_direct":
        return "generated_verified"
    return "deterministic_fallback"


def _record_hash(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return util.sha256_hex(raw)


def _compose_llm(prompt: dict, stats: dict, party: str, day: str) -> tuple[str, int, int]:
    """Call the real Sonnet voice (synchronous direct call — 2/day, pennies). Returns
    (composite_text, tokens_in, tokens_out) from the API's own usage. Raises on transport error;
    the caller falls back to the deterministic voice, and the blocking verifier still gates whatever
    text is ultimately used, so an ungrounded LLM claim can never publish. §voice-wiring."""
    fills = {"{day}": day, "{party}": _PARTY_FULL.get(party, party),
             "{code_computed_stats_json}": json.dumps(stats, ensure_ascii=False),
             "{talking_points_json}": json.dumps(
                 stats.get("selected_claims") if "selected_claims" in stats
                 else stats.get("talking_points", []), ensure_ascii=False
             )}
    system, user = prompt["system"], prompt["user_template"]
    for k, v in fills.items():
        system = system.replace(k, v)
        user = user.replace(k, v)
    # docs/19 §2c — when the tagger is live AND a talking point is an official name, append the
    # handling clause so the voice cannot present a bill title as a coordinated message. Flag-gated,
    # so dark => committed prompt unchanged => the live call is byte-identical to today's.
    if config.feature_on("nomenclature_tags") and stats.get("shared_nomenclature"):
        system += NOMENCLATURE_VOICE_CLAUSE
    res = llm.direct_call(llm.VOICE_MODEL, system, user, max_tokens=400)
    text = (res.get("text") or "").strip()
    # If the API omits usage, ESTIMATE (never record a billed call as free) — over-count is the safe
    # direction for a spend ledger. §voice-wiring (LOW-7a).
    tin = int(res.get("tokens_in") or 0) or (llm.approx_tokens(system) + llm.approx_tokens(user))
    tout = int(res.get("tokens_out") or 0) or max(1, llm.approx_tokens(text))
    return text, tin, tout


def _has_voiceable_content(stats: dict) -> bool:
    """True when a code-selected claim or a top phrase exists to voice.

    A day with neither renders a deterministic null (R-36.5): the model is not called,
    because a template already produces the null text. This is the single predicate the
    model-call gate and the withheld_no_eligible_claim state both read, so they cannot
    diverge.
    """
    top = stats.get("top_phrase")
    return bool(stats.get("selected_claims")) or bool(isinstance(top, dict) and top.get("text"))


def daily_line(party: str, day: str, party_statements: list[dict], talking_points: list[dict],
               top_phrase: dict | None, statements_by_id: dict, allow_llm_voice: bool = False) -> dict:
    """Produce + verify one party-day Daily Line. Returns the daily_distillation record (§3).

    Voice selection: the real Sonnet voice fires ONLY when allow_llm_voice (run_assemble computes it
    from config.llm_voice_enabled() AND the budget governor) AND a key is present. Otherwise — gate
    off, budget halt, no key, or an API error — it is the honest deterministic voice. Either way the
    blocking verifier gates the output; a failure drops to the honest fallback, never silence."""
    n = len(party_statements)
    quiet = n < config.QUIET_DAY_MAX_STATEMENTS
    prompt = llm.load_prompt("P3" if quiet else "P2")

    stats = build_stats(party, day, n, talking_points, top_phrase)
    stats_blob = json.dumps(stats, ensure_ascii=False)
    generation_request = {
        "method": STRUCTURED_COMPOSITE_VERSION,
        "party": party,
        "day": day,
        "prompt": {"id": prompt["id"], "version": prompt["version"], "sha256": prompt["sha"]},
        "stats_sha256": util.sha256_hex(stats_blob),
        "claim_ids": list(stats.get("claim_ids") or []),
    }
    request_sha256 = _record_hash(generation_request)
    model_response_sha256 = None

    tokens_in = tokens_out = 0
    # R-36.5: a day with zero code-selected claims and no top phrase renders a deterministic
    # null. The model is never called to produce what a template already says.
    if allow_llm_voice and not llm.dry_run() and _has_voiceable_content(stats):
        try:  # pragma: no cover - requires ANTHROPIC_API_KEY + LLM_VOICE_ENABLED
            composite, tokens_in, tokens_out = _compose_llm(prompt, stats, party, day)
            model_response_sha256 = util.sha256_hex(composite)
            if not composite.strip():
                raise ValueError("empty composite from voice")   # never publish a blank line (HIGH-2)
            generator = "sonnet_direct"     # a real production voice (site.PRODUCTION_GENERATORS)
            model = llm.VOICE_MODEL
        except Exception as e:  # transport/API error/empty -> deterministic; a voice failure never crashes
            print(f"[voice:{party}] LLM voice failed ({e}); deterministic fallback")
            composite = _quiet_dry(stats) if quiet else _compose_dry(stats)
            generator = "deterministic"
            model = prompt["id"] + ":deterministic"
    elif llm.dry_run():
        composite = _quiet_dry(stats) if quiet else _compose_dry(stats)
        generator = "dry_run"
        model = prompt["id"] + ":dry_run"
    else:
        # Key present but the voice is gated OFF (LLM_VOICE_ENABLED) or the budget halted it:
        # the honest deterministic voice, $0. §voice-wiring.
        composite = _quiet_dry(stats) if quiet else _compose_dry(stats)
        generator = "deterministic"
        model = prompt["id"] + ":deterministic"

    # B4 verifier (blocking): every UNQUOTED number must be a code-computed count (the strict `stats`
    # whitelist — a digit inside a member quote can never become a fabricated aggregate), and every
    # quoted span must be verbatim, in-context member text. Failure -> honest fallback, never silence.
    ok, reasons = verify.verify_daily_line({"composite": composite}, stats_blob, stats=stats)
    fallback = False
    if not ok and generator == "sonnet_direct":
        # HARDENING (deploy-breakdown 2026-07-16): the Sonnet drifted a quote — LLM verbatim-grounding is
        # inherently brittle (07-15 shipped un-grounded quotes 'national security department' /
        # "applauded today's house passage…"). Do NOT drop straight to the apologetic stub: fall back to
        # the RICH deterministic composite, which is verifier-clean BY CONSTRUCTION (code numbers +
        # verbatim fragments only), then re-verify. The site keeps a real, informative Daily Line.
        print(f"[voice:{party}] Sonnet failed verify ({reasons}); deterministic-composite fallback")
        composite = _quiet_dry(stats) if quiet else _compose_dry(stats)
        generator = "deterministic"
        model = prompt["id"] + ":deterministic"
        ok, reasons = verify.verify_daily_line({"composite": composite}, stats_blob, stats=stats)
    if not ok:
        # Last resort: even the deterministic composite failed to verify (should be impossible — it uses
        # only code numbers + verbatim fragments). The honest stub, never silence. §7.2.
        composite = "Composite withheld because its claims could not be verified."
        fallback = True
        # The published text is the deterministic fallback — attribute it honestly, never as the
        # model (the honesty banner + _voice_flags must not claim Sonnet wrote this). §LOW-6.
        generator = "deterministic"
        model = prompt["id"] + ":fallback"

    # sentence -> talking-point receipts mapping (which clusters back each sentence)
    sentence_claims = contracts.sentence_claims(composite, stats)
    receipts = [{"sentence_idx": row["sentence_idx"], "talking_points": row["claim_ids"],
                 "claim_ids": row["claim_ids"]} for row in sentence_claims]
    structured_output = {"composite": composite, "sentence_claims": sentence_claims}
    response_sha256 = _record_hash(structured_output)
    if not ok:
        composite_state = "withheld_verifier_failure"
    elif not _has_voiceable_content(stats):
        composite_state = "withheld_no_eligible_claim"
    elif generator == "sonnet_direct":
        composite_state = "generated_verified"
    else:
        composite_state = "deterministic_fallback"

    return {
        "schema_version": contracts.SCHEMA_VERSION, "day": day, "party": party,
        "composite": composite,
        "measurement_lead": measurement_lead(party, day, n),
        "composite_state": composite_state,
        "structured_request": generation_request,
        "structured_output": structured_output,
        "generation_hashes": {
            "method": STRUCTURED_COMPOSITE_VERSION,
            "request_sha256": request_sha256,
            "response_sha256": response_sha256,
            "model_response_sha256": model_response_sha256,
        },
        "quiet": quiet, "fallback": fallback,
        "sentence_receipts": receipts,
        "sentence_claims": sentence_claims,
        "model": model, "generator": generator,
        "prompt_version": prompt["version"], "prompt_sha": prompt["sha"],
        "stats": stats,
        "verifier": {"checked": True, "passed": ok, "reasons": reasons,
                     "talking_points_published": len(talking_points)},
        # Real token usage for the spend ledger (0 unless the Sonnet voice actually fired). Tokens
        # are charged even if the verifier later dropped the line to fallback — record them honestly.
        "usage": {"tokens_in": tokens_in, "tokens_out": tokens_out, "model": model},
    }
