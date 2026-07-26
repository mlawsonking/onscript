"""RUN B "assemble" (§2): extractions -> clusters -> Daily Lines -> VERIFY -> derived + symmetry.

Self-sufficient given the state RUN A leaves (statements + ledger): it extracts the focus
day's statements on demand (idempotent via the extraction cache), clusters per party, distills
+ verifies the two Daily Lines, merges them into the day's derived JSON, and publishes the
nightly symmetry audit. $0 in dry-run.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import (boilerplate, brief, build, cluster, config, contracts, corrections, distill,
                      duet, eligibility, extract, llm, nomenclature, ops, privacy, readiness, roster, util,
                      verify)  # noqa: E402


def _load_taxonomy() -> list[dict]:
    return util.read_json(config.TAXONOMY_FILE, {"topics": []})["topics"]


def _name(bio: str, rmap: dict) -> str:
    return (rmap.get(bio, {}) or {}).get("name") or bio


def _attributable(frag: str, stmt: dict, rmap: dict) -> bool:
    """Did the CITED MEMBER actually say this fragment, or is it a colleague's quote that merely
    sits inside their release?

    A congressional press release is a MULTI-SPEAKER document: a release from Castro's office
    carries quotes from Castro, Houlahan AND Cisneros. `verify.is_verbatim` cannot tell these apart
    BY DESIGN — it asks only whether the string occurs in the cited statement, and a colleague's
    quote genuinely does. **Verbatim is not attributable**, and the gap is exactly where a receipt
    would put another member's words next to this member's name and their .gov link (Art. XII).
    Real shape, on real data: Rep. Cisneros's "I'm proud to support my colleagues, Congressman Castro
    and Congresswoman Houlahan..." appears verbatim inside BOTH Castro's and Houlahan's releases.

    So we re-ask the question the verifier structurally cannot, using the 1.7a Duet's gate: is the
    nearest attribution marker this member's? ANY self-attributed occurrence is enough — a fragment
    that appears once in a colleague's block and once in the member's own words is the member's.

    Two deliberate fail-OPEN cases, both preserving today's behavior rather than inventing silence:
    unresolvable speaker (no roster name to compare against), and a fragment that no single sentence
    carries (extraction windows are built per-sentence, so this is rare — 0 of 103 live quotes).
    Fail-open is safe HERE only because the caller demotes rather than drops: the worst case is the
    status quo, never a fabricated receipt."""
    text = stmt.get("text") or ""
    speaker = duet._surname(_name((stmt.get("member") or {}).get("bioguide"), rmap))
    if not speaker or not text:
        return True
    target = verify._norm(frag or "")
    if not target:
        return True
    # Locate via the same sentence-span + normalize path the Duet matches on, never str.find: an
    # identical string can occur in several blocks and the FIRST one may be a different speaker's.
    hits = [(s, at) for s, at in duet._sentence_spans(text) if target in verify._norm(s)]
    if not hits:
        return True
    return any(not duet.attributed_to_other(text, at, at + len(s), speaker) for s, at in hits)


def _citations(tp: dict, stmt_by_id: dict, rmap: dict, k: int = 3) -> list[dict]:
    """Resolve a verified talking point to >=k real (member, date, URL) citations — one per
    distinct unit (joint/delegation collapses to one, §11 trap 2). This is the citation-or-silence
    receipt the public pages render (Art. XII). Persisted into the day JSON so the site is
    self-contained (no roster re-resolution at render time)."""
    # C-ii: bind each citation to the specific fragment THAT member's statement contributed, so a
    # displayed quote sits next to the member who said it and their .gov link — a reader can click and
    # verify that exact quote, instead of a decoupled quote/citation pair that points at unrelated
    # topics. §Session-7.
    #
    # An unattributable fragment cannot serve as evidence for P. It therefore costs the unit its
    # receipt, and the assembly gate suppresses the talking point unless three bound receipts remain.
    #
    # docs/19 §4b — a receipt must support its LINE's meaning: only cite families whose source actually
    # carries the cluster key. A member chained into the cluster by a DIFFERENT shared gram (Booker's
    # flood bill under "into the trump administration's"; Krishnamoorthi's Blanche release under
    # "democratic colleagues in demanding the") is not a receipt for THIS phrase. This is the SAME
    # key-carrying set the quorum counts, so the receipts show exactly the families that passed quorum —
    # a published cluster has >=3 of them, so this never thins receipts below the floor.
    label = tp.get("label", "")
    frag_by_stmt: dict = {}
    for f in tp.get("fragments", []):
        if f.get("statement") and f.get("text"):
            frag_by_stmt.setdefault(f["statement"], []).append(f["text"])
    occurrence_by_statement: dict[str, dict] = {}
    for occurrence in tp.get("occurrences") or []:
        sid = occurrence.get("statement_id")
        if sid and sid not in occurrence_by_statement:
            occurrence_by_statement[sid] = occurrence
    cites, seen = [], set()
    for sid in tp.get("statements", []):
        s = stmt_by_id.get(sid)
        if not s:
            continue
        if label and not boilerplate.contains_gram(s.get("text", ""), label):
            continue
        m = s.get("member") or {}
        unit = s.get("joint_group") or m.get("bioguide")
        if not unit or unit in seen:
            continue
        seen.add(unit)
        # Each displayed receipt must visibly carry the same support phrase as its header. A
        # P-carrying, self-attributable fragment is evidence; an unrelated fragment from the same
        # transitive component is not. Units without such a fragment remain in the support count but
        # are skipped for the three displayed receipts.
        quote = next((q for q in frag_by_stmt.get(sid, [])
                      if boilerplate.contains_gram(q, label) and _attributable(q, s, rmap)), None)
        if not quote:
            continue
        occurrence = occurrence_by_statement.get(sid) or {}
        cites.append({"member": _name(m.get("bioguide"), rmap), "party": m.get("party"),
                      "state": m.get("state"), "date": s.get("published_at"), "url": s.get("url"),
                      "quote": quote,
                      "occurrence_id": occurrence.get("occurrence_id"),
                      "office_id": occurrence.get("office_id") or m.get("bioguide"),
                      "publication_id": occurrence.get("publication_id") or sid,
                      "family_id": occurrence.get("family_id") or s.get("joint_group") or sid})
        if len(cites) >= k:
            break
    return cites


def _reject_reason(label: str, ok_verify: bool, vreasons: list) -> str | None:
    """docs/19 §4b — the stable reason code for dropping a talking point at the MESSAGE gates, or None
    if it clears them all. Order mirrors assemble()'s gate order: quorum/verbatim (verify), then the
    scaffold-key admission gate (a frame that terminates before its object, or an attribution frame),
    then weak-label (low information). Privacy (Art. XIII) is a SEPARATE gate the caller applies and
    never records with the label. Pure + party-blind, so it is unit-testable without a full assemble."""
    if not ok_verify:
        return (boilerplate.REJECT_FAMILY_QUORUM if any("key-quorum" in r for r in (vreasons or []))
                else "REJECT_NON_VERBATIM")
    if boilerplate.is_scaffold_key(label):
        return boilerplate.scaffold_reason(label)          # ATTRIBUTION_FRAME / INCOMPLETE_SYNTACTIC_SPAN
    if boilerplate.is_weak_label(label):
        return boilerplate.REJECT_LOW_INFORMATION_CONTENT
    return None


REJECT_RECEIPT_BINDING = "REJECT_RECEIPT_BINDING"
REJECT_CLAIM_CONTRACT = "REJECT_CLAIM_CONTRACT"


def _screen_talking_points(tps: list[dict], stmt_by_id: dict, rmap: dict) \
        -> tuple[list[dict], int, list[dict]]:
    """Apply every publication gate to already P-bound talking points.

    This helper keeps the production path and the P0 fixtures on the same code. A rejected claim is
    logged with its corrected support count. Privacy remains the one label-free omission.
    """
    published: list[dict] = []
    dropped = 0
    rejected: list[dict] = []
    for original_tp in tps:
        try:
            tp = contracts.canonical_claim(original_tp, stmt_by_id)
        except (TypeError, ValueError):
            tp = original_tp
            ok, vreasons = False, ["claim-invariant:canonicalization"]
            reason = REJECT_CLAIM_CONTRACT
        else:
            ok, vreasons = verify.verify_talking_point(tp, stmt_by_id, require_contract=True)
            reason = _reject_reason(tp.get("label", ""), ok, vreasons)
            if any(str(row).startswith("claim-invariant:") for row in vreasons):
                reason = REJECT_CLAIM_CONTRACT
        label = tp.get("label", "")
        if reason:
            ok = False
        elif privacy.filter_talking_points([tp])[1]:
            ok = False
        if ok:
            citations = _citations(tp, stmt_by_id, rmap)
            if len(citations) < config.SYNC_MIN_MEMBERS:
                ok = False
                reason = REJECT_RECEIPT_BINDING
            else:
                tp["citations"] = citations
                tp["citation_occurrence_ids"] = [row.get("occurrence_id") for row in citations]
                final_ok, _final_reasons = verify.verify_talking_point(
                    tp, stmt_by_id, require_contract=True, require_citations=True
                )
                if final_ok:
                    published.append(eligibility.classify_claim(tp, day=tp.get("day")))
                else:
                    ok = False
                    reason = REJECT_CLAIM_CONTRACT
        if not ok:
            dropped += 1
            if reason and not privacy.is_suppressed(label):
                rejected.append({"label": label, "reason": reason,
                                 "member_count": tp.get("member_count")})
    return published, dropped, rejected


def _is_final(day: str) -> bool:
    """Was this day already published? A final day is never re-assembled (and never skipped). The
    readiness gate uses this to walk the backlog oldest-first. §deploy-hardening.

    ONE DEFINITION OF "PUBLISHED". This delegates to `util.day_is_final`, which is also what makes a
    published day immutable to RUN A (docs/23 §7.5 R-C). The readiness gate and the write guard must
    never be able to disagree about which days are published — that disagreement is precisely how a
    day gets clobbered."""
    return util.day_is_final(day)


# TRIGGER-PROVENANCE: facts about how the ORIGINAL run was launched and what the readiness gate saw.
# A repair restores CONTENT; it does not restage history, so these carry over from the published
# manifest untouched. `forced_finalize` belongs here and not with content: it records that the gate
# waited out MAX_WAIT_DAYS and published anyway — and since the `--day` repair path hard-codes
# forced=False, recomputing it would LAUNDER a force-finalized day into a streak-eligible one
# (`ops.unattended_streak` breaks on `forced_finalize`) and silently drop its alert.
REPAIR_PRESERVED_KEYS = ("event", "unattended", "run_id", "forced_finalize", "readiness")


def repair_safe_manifest(manifest: dict, prior: dict, *, now: str, repair_run_id: str,
                         repair_event: str) -> tuple[dict, bool]:
    """Merge trigger-provenance from a prior PUBLISHED manifest into this run's manifest.

    WHY THIS EXISTS (docs/23 §7.5 R-C amendment). `run_assemble --day` is the sanctioned repair path
    for a published day, but the manifest write is unconditional and `event`/`unattended` are
    recomputed from GITHUB_EVENT_NAME every run. A repair is NEVER a `schedule` event, and
    `ops.unattended_streak` breaks on the first falsy `unattended` — so repairing the NEWEST published
    day flips the head of the §1.4.1 streak and fails the launch gate. Measured on the real manifests:
    repairing 2026-07-18 takes the gate from `passes: True` to `passes: False`.

    What is NOT preserved: `degraded`. That describes what is published NOW, not how the run was
    triggered — if a repair degrades a day, the streak SHOULD notice.

    A field the prior manifest never carried is DROPPED rather than invented: the 2026-07-14 and
    2026-07-15 manifests pre-date the instrumentation, and an uninstrumented run must stay
    uninstrumented so `unattended_streak` correctly refuses to count it.

    Pure so it is testable without a full assemble — the regression this guards against is invisible
    to a source-inspection test."""
    is_repair = bool(prior) and bool(prior.get("final", True))
    if not is_repair:
        return manifest, False
    out = dict(manifest)
    for k in REPAIR_PRESERVED_KEYS:
        if k in prior:
            out[k] = prior[k]
        else:
            out.pop(k, None)
    out["repaired_at"] = now
    out["repair_run_id"] = repair_run_id
    out["repair_event"] = repair_event
    return out, True


def _counts_by_day(statements) -> dict:
    from collections import Counter
    return dict(Counter(s["published_at"] for s in statements if s.get("lane") == 1))


def assemble(day: str, statements=None, *, readiness_info=None, forced=False) -> dict:
    statements = statements if statements is not None else list(util.iter_jsonl(config.STATE / "statements.jsonl.gz"))
    ledger = util.read_json(config.STATE / "ledger.json", {})
    if not statements or not ledger:
        raise SystemExit("no state — run RUN A (scripts/backfill_stage1.py or run_collect) first")
    taxonomy = _load_taxonomy()
    rmap = roster.load()
    sync = set(ledger)

    focus = [s for s in statements if s["published_at"] == day and s.get("lane") == 1]
    extractions, extract_cost = extract.extract(focus, sync, taxonomy)

    stmt_by_id = {s["id"]: s for s in statements}
    per_party_llm: dict[str, dict] = {}
    day_payload: dict[str, dict] = {}

    # Real Sonnet voice gate + STRICT pre-flight budget check (voice-wiring). The voice fires only
    # when a key is present (not dry_run), the LLM_VOICE_ENABLED switch is on, AND month-to-date spend
    # leaves room under the code ceiling (config.LLM_MONTHLY_CEILING_USD). Otherwise: deterministic, $0.
    projected = 2 * llm.estimate_cost(llm.VOICE_MODEL, 3000, 400, batched=False)  # ~2 voice calls, generous
    voice_state = ops.voice_budget_state(day, projected)
    allow_llm_voice = config.llm_voice_enabled() and voice_state != "halt"

    for party in config.COMPOSITE_PARTIES:
        party_stmts = [s for s in focus if (s.get("member") or {}).get("party") == party]
        annotated = []
        for s in party_stmts:
            for f in extractions.get(s["id"], {}).get("fragments", []):
                annotated.append({**f, "statement": s["id"], "joint_group": s.get("joint_group"),
                                  "bioguide": (s.get("member") or {}).get("bioguide"),
                                  "source_text": s.get("text", "")})
        tps = cluster.cluster_day(party, day, annotated, statements_by_id=stmt_by_id)

        # Verify and cite the corrected support set. Privacy drops remain label-free; every other
        # omission is logged with a stable reason and the support-unit count.
        published, dropped, rejected = _screen_talking_points(tps, stmt_by_id, rmap)

        # top synchronized phrase for the party that day (with first-sayer name)
        top_rows = [r for r in build.top_synchronized(ledger, day, k=5) if r["party"] == party]
        top_phrase = None
        if top_rows:
            r = top_rows[0]
            fsb = (r.get("first_seen") or {}).get("bioguide")
            fsm = rmap.get(fsb) or {}
            top_phrase = {"text": r["ngram"], "members": r["day_peak"]}
            # Expose a first-sayer ONLY when the roster fully resolves it (name + party + state).
            # first_seen is corpus-wide, so the bioguide is often a former member absent from the
            # current roster — in that case omit it entirely, so the voice has nothing to fabricate
            # (the verifier does not ground names/party/state). §Session-7 (#4). Present => the voice
            # tags it "Name (R-SC)"; may be the OTHER party (real cross-party origination).
            if fsm.get("party") and fsm.get("state") and fsm.get("name"):
                top_phrase.update({"first_sayer": _name(fsb, rmap),
                                   "first_sayer_party": fsm["party"], "first_sayer_state": fsm["state"]})

        distillation = distill.daily_line(party, day, party_stmts, published, top_phrase, stmt_by_id,
                                          allow_llm_voice=allow_llm_voice)

        # REAL token usage from the voice call (0 when the deterministic voice was used) — the
        # symmetry audit + cost ledger report actual spend, never an estimate. §voice-wiring.
        usage = distillation.get("usage") or {}
        per_party_llm[party] = {
            "tokens_in": int(usage.get("tokens_in", 0)), "tokens_out": int(usage.get("tokens_out", 0)),
            "claims_published": len(published), "claims_dropped": dropped,
        }
        day_payload[party] = {"daily_line": distillation, "talking_points": published,
                              "rejected_keys": rejected}   # docs/19 §4b forward dark-shelf (reason-coded)

    # STRICT budget accounting FIRST — persist the real spend to the month ledger BEFORE any risky
    # day-JSON write, so a write failure can never lose a billed call. Cost each run at its OWN day's
    # Sonnet rate (date-aware). The governor reads true month-to-date; the $10 Console cap is the
    # last-line backstop. §voice-wiring (LOW-7b, MEDIUM-5).
    day_cost = round(sum(llm.estimate_cost(llm.VOICE_MODEL, per_party_llm[p]["tokens_in"],
                                           per_party_llm[p]["tokens_out"], batched=False, on_date=day)
                         for p in config.COMPOSITE_PARTIES), 6)
    if not llm.dry_run():
        ops.record_cost(day, day_cost, model=llm.VOICE_MODEL,
                        tokens_in=sum(per_party_llm[p]["tokens_in"] for p in config.COMPOSITE_PARTIES),
                        tokens_out=sum(per_party_llm[p]["tokens_out"] for p in config.COMPOSITE_PARTIES))
    month_to_date = ops.month_to_date_usd(day, include_day=True)
    governor = ops.budget_governor(month_to_date)

    # merge Daily Lines into the day's derived JSON (deterministic top phrases already there)
    day_file = config.DERIVED / "days" / f"{day}.json"
    day_json = util.read_json(day_file, {"day": day})
    day_json["schema_version"] = contracts.SCHEMA_VERSION
    day_json["daily_lines"] = {p: day_payload[p]["daily_line"] for p in config.COMPOSITE_PARTIES}
    day_json["talking_points"] = {p: day_payload[p]["talking_points"] for p in config.COMPOSITE_PARTIES}
    # docs/19 §4b — the reason-coded rejected candidates for THIS day (the forward dark-shelf view of
    # what the conservative admission gate + quorum dropped, so false negatives are auditable before
    # anyone tunes the gate). Additive; never rendered; carries no private-name label (Art. XIII guard
    # above). schema_version stays 1.
    day_json["rejected_keys"] = {p: day_payload[p]["rejected_keys"] for p in config.COMPOSITE_PARTIES}
    day_json["top_synchronized"] = build.top_synchronized(ledger, day, k=20)
    # R3 / #146 — each party's OWN top-k, so the per-party columns give both parties equal slots (the
    # pooled top-20 is 88% D by caucus size, not coordination). Computed EVERY day (build-dark); the
    # render is gated on FEATURES["party_columns"], so the flip is a pure release act. Additive.
    day_json["sync_by_party"] = build.top_synchronized_by_party(ledger, day, k_per_party=10)
    # 1.7a The Duet — the same phrase, both parties, the same day. Computed EVERY day so the archive
    # keeps it and the flag flip is a pure release act (no backfill needed); RENDERING is gated on
    # FEATURES["duet"] (BUILD-PROGRAM §1, build dark / release by gate). Deterministic and $0 — it
    # reads the ledger and the day's statements, and calls no model.
    day_json["duets"] = duet.find_duets(day, ledger, focus, rmap, k=duet.DUET_MAX_PER_DAY)
    util.write_json(day_file, day_json)

    freshness = {"note": "assemble stage; freshness measured in RUN A"}
    # `forced` = the readiness gate waited out MAX_WAIT_DAYS and upstream never filled: we publish what
    # we have rather than leave a hole in the series, but it is honestly degraded. §deploy-hardening.
    degraded = forced or any(day_payload[p]["daily_line"]["fallback"] for p in config.COMPOSITE_PARTIES)
    # docs/19 §2a MEASURE — UNCONDITIONAL (does not read FEATURES["nomenclature_tags"]): of this day's
    # FULL synchronized set per party, what share is an official name (bill title / committee name)?
    # Tagged on a COPY so nothing here touches the published rows or the day JSON. An asymmetric tagger
    # would otherwise be invisible to the nightly audit (docs/16 §6).
    nomen_measure = {}
    all_sync = build.top_synchronized(ledger, day, k=10_000)
    cong = util.congress_for_date(day)
    for p in config.COMPOSITE_PARTIES:
        prows = [dict(r) for r in all_sync if r.get("party") == p]
        nomenclature.tag(prows, congress=cong)
        tagged = sum(1 for r in prows if r.get("nomenclature"))
        nomen_measure[p] = {"tagged": tagged, "total": len(prows),
                            "rate": round(tagged / len(prows), 4) if prows else None}
    report = ops.symmetry_report(day, statements, per_party_llm, freshness=freshness, degraded=degraded,
                                 nomen_measure=nomen_measure)

    correction_rows = corrections.load()
    manifest = {
        "schema_version": contracts.SCHEMA_VERSION,
        "run_id": f"assemble-{date.today().isoformat()}", "kind": "assemble",
        "generated_at": util.now_utc_iso(), "day": day,
        "dry_run": llm.dry_run(), "extract_cost": extract_cost,
        "per_party_llm": per_party_llm, "daily_voice_cost_usd": day_cost,
        "llm_voice_enabled": config.llm_voice_enabled(),
        "voice_used": bool(allow_llm_voice and not llm.dry_run()),
        "voice_budget_state": voice_state, "month_to_date_usd": month_to_date,
        "governor_state": governor, "degraded": degraded,
        "corrections_count": len(correction_rows),
        # WHO TRIGGERED THIS RUN. §1.4.1 acceptance is "three consecutive UNATTENDED real runs", and
        # until now nothing recorded whether a run was a cron or a human dispatch — so the gate could
        # only be tracked by hand in prose, and on 2026-07-16 it was tracked WRONG ("2/3, the 07-16
        # cron completes it"; that cron actually published the fallback and reset the streak to 0).
        # A gate the code cannot count is a gate that gets counted by wishful thinking (Constitution:
        # numbers come from code). GITHUB_EVENT_NAME is 'schedule' for cron, 'workflow_dispatch' for a
        # human, and absent locally.
        "event": os.environ.get("GITHUB_EVENT_NAME") or "local",
        "unattended": os.environ.get("GITHUB_EVENT_NAME") == "schedule",
        # §deploy-hardening: this day cleared the readiness gate (or waited out MAX_WAIT and was
        # finalized degraded). final=True means PUBLISHED — never re-assembled, and never skipped.
        "final": True, "forced_finalize": forced, "readiness": readiness_info,
        "symmetry": {"prompts_sha": report["prompts_sha"], "thresholds_sha": report["thresholds_sha"]},
        "alerts": (["degraded"] if degraded else []) + (["forced-finalize: upstream never filled"] if forced else []),
    }
    # REPAIR-SAFE PROVENANCE (docs/23 §7.5 R-C, amendment) — see `repair_safe_manifest` for why the
    # obvious unconditional write would have failed the §1.4.1 launch gate.
    man_path = config.DERIVED / "manifest" / f"assemble-{day}.json"
    prior_manifest = util.read_json(man_path, {}) or {}
    manifest.update(corrections.publication_fields(
        day_json, prior_manifest, corrections.for_day(day, correction_rows)
    ))
    manifest, is_repair = repair_safe_manifest(
        manifest, prior_manifest,
        now=util.now_utc_iso(), repair_run_id=f"assemble-{date.today().isoformat()}",
        repair_event=os.environ.get("GITHUB_EVENT_NAME") or "local")
    util.write_json(man_path, manifest)
    # Pointer to the day THIS run built — post_bluesky reads it (not collect's focus_day), which
    # fixes the Session-4 day-selection no-op. Posting targets exactly what assemble published.
    #
    # A REPAIR MUST NOT REPOINT IT. Repairing an old day would otherwise aim the next post at that
    # day: repairing 2026-07-12 on launch eve would make the first live Daily Line thread a
    # nine-day-stale day. A repair fixes the record; it never changes what posts next.
    if not is_repair:
        util.write_json(config.DERIVED / "manifest" / "assemble-latest.json",
                        {"day": day, "generated_at": util.now_utc_iso(), "run_id": manifest["run_id"]})
    else:
        print(f"[repair] {day}: provenance preserved (event={manifest.get('event')!r} "
              f"unattended={manifest.get('unattended')!r}); assemble-latest NOT repointed")
    if degraded or governor != "nominal" or voice_state in ("warn", "halt"):
        ops.ntfy("OnScript assemble",
                 f"day={day} governor={governor} voice={voice_state} "
                 f"mtd=${month_to_date:.2f} degraded={degraded}",
                 priority="high" if (degraded or voice_state == "halt") else "default")
    return {"manifest": manifest, "day_json": day_json, "report": report}


def _owners_brief() -> None:
    """07-OPS §3: "RUN B appends a Monday ntfy". Dark until FEATURES["owners_brief"] flips.

    Two deliberate placements:
      * **skip-and-log** — the workflow runs this step WITHOUT `|| true` (unlike the posting leg), so
        an exception here would fail RUN B and break the streak. The brief is a report ABOUT the
        machine; it must never be able to take the machine down (CLAUDE.md: never crash the run).
      * **called from main(), not assemble()** — main() returns early when no day is ready, and a
        Monday where nothing assembled is precisely the Monday the owner needs a brief (streak would
        be RED). Wiring it inside assemble() would silence it exactly when it matters most.

    The brief's day (`brief.brief_day()`) is the day it RUNS, not the day being assembled.
    """
    try:
        day = brief.brief_day()
        r = brief.send_brief(day)
        print(f"[brief] {day}: {r['brief']['headline']} — {r.get('reason') or ('sent' if r['sent'] else 'not sent')}")
    except Exception as e:  # pragma: no cover - the whole point is that nothing escapes
        print(f"[brief] skipped (skip-and-log): {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=None,
                    help="explicit day (manual/backfill) — bypasses the readiness gate")
    args = ap.parse_args()

    # §deploy-hardening (2026-07-16): do NOT blindly assemble product_day(). If the mirror is still
    # landing, publishing a thin day and then advancing product_day() would SKIP that day forever —
    # a permanent hole in the time-series. Instead: assemble the oldest not-yet-final day that is
    # READY (oldest-first, so the series fills chronologically); if none is ready, NO-OP at $0 and let
    # a later retry cron pick it up the moment upstream fills. A day that never fills is force-
    # finalized after MAX_WAIT_DAYS so a quiet holiday can never livelock the streak.
    statements = list(util.iter_jsonl(config.STATE / "statements.jsonl.gz"))
    if args.day:
        day, forced, sel = args.day, False, {"reason": "explicit --day override", "readiness": None}
    else:
        sel = readiness.select_target_day(_counts_by_day(statements), _is_final, util.product_day())
        if sel["day"] is None:
            print(f"===== RUN B assemble — NO-OP (no cluster, no distill, no API spend) =====")
            print(sel["reason"])
            _owners_brief()      # a Monday with nothing to assemble is a Monday that needs a brief
            return 0
        day, forced = sel["day"], sel["forced"]
        print(f"[readiness] target={day} forced={forced} :: {sel['reason']}")

    res = assemble(day, statements, readiness_info=sel.get("readiness"), forced=forced)
    dj = res["day_json"]
    print(f"===== RUN B assemble — {day} (dry_run={llm.dry_run()}) =====")
    for p in config.COMPOSITE_PARTIES:
        dl = dj["daily_lines"][p]
        tps = dj["talking_points"][p]
        print(f"\n[{p}] talking points published: {len(tps)}  verifier_passed={dl['verifier']['passed']}  fallback={dl['fallback']}")
        print(f"[{p}] DAILY LINE: {dl['composite']}")
        if tps:
            receipts = " | ".join('"' + f["text"] + '"' for f in tps[0]["fragments"][:3])
            print(f"[{p}] top cluster: {tps[0]['member_count']} members — receipts: {receipts}")
    r = res["report"]
    print("\n----- symmetry audit -----")
    for p in config.COMPOSITE_PARTIES:
        pp = r["parties"][p]
        print(f"  {p}: {pp['statements_ingested']} statements, {pp['members_covered']}/{pp['caucus_size']} members "
              f"({pp['coverage_pct']}%), claims {pp['claims_published']} published / {pp['claims_dropped']} dropped")
    print(f"  prompts_sha={list(r['prompts_sha'].values())[0][:12]}…  thresholds_sha={r['thresholds_sha'][:12]}… (identical both parties)")
    _owners_brief()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
