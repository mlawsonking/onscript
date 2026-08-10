"""Ops: dead-man ntfy, budget governor, and the nightly public symmetry audit (§5.2, §6.4).

The symmetry report is the product's armor: it proves, every day, that both parties ran
through an identical instrument (same prompts_sha, same thresholds_sha, same pipeline), so an
asymmetric finding is reality's, not the instrument's.
"""
from __future__ import annotations

import os
import statistics
from collections import Counter

from datetime import date

from . import (config, denominators, instrument_fingerprint, llm, public_strings, readiness,
               roster, util)


def collection_maturity(statements, focus_day, *, reference_day: str | None = None) -> dict:
    """Has `focus_day` finished landing, so its volume can be compared with prior days?

    A morning collect run sees the focus day hours before upstream finishes delivering it.
    On 2026-08-08 the run counted 2 statements against a trailing median of 138.5 and paged,
    and the same day later assembled 192. Comparing a partial day with complete ones measures
    the clock, not the corpus.

    Maturity has two arms, both taken from the readiness gate so this and the publication
    path agree on when a day has stopped filling:
      ready       - the day holds at least READY_RATIO of its trailing same-weekday median,
                    which is the same test that lets the day be assembled at all.
      waited out  - the day is at least MAX_WAIT_DAYS old, which is the point at which the
                    readiness gate stops waiting and force-finalizes. Whatever is there is
                    what upstream is going to deliver.

    `reference_day` is the clock, injected rather than read, so the manifest a run writes is
    reproducible (docs/37 rule 5). Without one only the ready arm can be evaluated.
    """
    by_day = Counter(s["published_at"] for s in statements if s.get("lane") == 1)
    row = readiness.day_readiness(by_day, focus_day)
    age_days = None
    if reference_day:
        try:
            age_days = (date.fromisoformat(reference_day) - date.fromisoformat(focus_day)).days
        except (TypeError, ValueError):
            age_days = None
    waited_out = age_days is not None and age_days >= readiness.MAX_WAIT_DAYS
    mature = bool(row["ready"] or waited_out)
    if row["ready"]:
        reason = "the focus day cleared the readiness gate"
    elif waited_out:
        reason = (f"the focus day is {age_days} days old, past the {readiness.MAX_WAIT_DAYS}-day "
                  f"readiness wait, so upstream is not still landing it")
    else:
        reason = (f"upstream is still landing the focus day ({row['reason']})"
                  if age_days is None else
                  f"upstream is still landing the focus day, {age_days} days old ({row['reason']})")
    return {"mature": mature, "ready": bool(row["ready"]), "age_days": age_days,
            "same_weekday_baseline": row["baseline"], "share": row["share"], "reason": reason}


def volume_anomaly(statements, focus_day, *, maturity: dict | None = None) -> dict:
    """Lane-1 daily volume against the trailing-14-day median for one focus day.

    Single definition shared by collect (the run's newest day) and assemble (the target
    day), so the two callers cannot compute the anomaly two different ways (docs/37 rule 12).

    `maturity` is a collection_maturity row. When it reports an immature focus day the
    comparison is withheld and `anomalously_low` is False, because a partial count is not
    evidence of a thin day. The count and the median are published either way, so a withheld
    comparison never reads as a healthy one. Omitting `maturity` judges the day, which is
    what the assemble caller wants: a day it is publishing has already cleared the readiness
    gate or been force-finalized past it. The default is the arm that alerts.
    """
    by_day = Counter(s["published_at"] for s in statements if s.get("lane") == 1)
    days = sorted(by_day)
    prior = [by_day[d] for d in days if d < focus_day][-14:]
    today = by_day.get(focus_day, 0)
    med = statistics.median(prior) if prior else 0
    mature = True if maturity is None else bool(maturity.get("mature"))
    low = mature and bool(med) and today < config.NULL_SERVICE_VOLUME_RATIO * med
    out = {"today": today, "trailing_median": med, "anomalously_low": low}
    if maturity is not None:
        out["collection_mature"] = mature
        out["comparison"] = "judged" if mature else "withheld"
        out["maturity_reason"] = maturity.get("reason")
    return out


def thresholds_sha() -> str:
    """Hash of every comparative threshold, so the site can prove both parties used the same ones."""
    return instrument_fingerprint.legacy_thresholds_sha()


def prompts_sha() -> dict:
    out = {pid: llm.load_prompt(pid)["sha"] for pid in ("P1", "P2", "P3")}
    # docs/19 §2c — the live voice appends a nomenclature-handling clause to the P2/P3 system prompt at
    # runtime WHEN the tagger is live. Baking it into the committed prompt files would change prompts_sha
    # while the feature is dark (a public-bytes change, docs/19 §3.4); instead it is runtime-appended and
    # its hash is disclosed HERE only when the flag is on, so the published fingerprint reflects what
    # actually shaped the output without churning the dark state. Lazy import: cycle-proof.
    if config.feature_on("nomenclature_tags"):
        from . import distill
        out["P2P3_nomenclature_clause"] = util.sha256_hex(distill.NOMENCLATURE_VOICE_CLAUSE)[:12]
    return out


def caucus_sizes(statements: list[dict]) -> dict:
    """Distinct members per party observed in the whole corpus — a self-contained caucus proxy
    (the corpus covers all current members with official sites, R2). No external roster needed."""
    seen = {p: set() for p in config.ALL_PARTIES}
    for s in statements:
        m = s.get("member") or {}
        p, bio = m.get("party"), m.get("bioguide")
        if p in seen and bio:
            seen[p].add(bio)
    return {p: len(v) for p, v in seen.items()}


def budget_governor(month_to_date_usd: float) -> str:
    """§6.4: >$8 warn, >$9.50 degrade (Sonnet->Haiku + trim), $10 Console hard cap is the backstop."""
    if month_to_date_usd > 9.5:
        return "degrade"
    if month_to_date_usd > 8.0:
        return "warn"
    return "nominal"


# ---------------------------------------------------------------------------
# Real LLM-spend ledger (strict budget). Per-month file, keyed by day so a re-run OVERWRITES that
# day's cost instead of double-counting. This is the code-side source of truth for month-to-date
# spend; the Anthropic Console is the authoritative backstop. Committed under data/derived/cost/.
# ---------------------------------------------------------------------------
def _cost_ledger_path(day: str):
    return config.DERIVED / "cost" / f"{day[:7]}.json"


def record_cost(day: str, usd: float, *, tokens_in: int = 0, tokens_out: int = 0, model: str = "") -> dict:
    """ACCUMULATE this run's real LLM spend into the day. Real re-runs (a manual re-dispatch, an
    overlapping cron) each bill fresh Anthropic money, so they ADD — overwriting would let the ledger
    keep only the last run and the $9 ceiling would under-count. A $0 deterministic re-run adds
    nothing and never clobbers a prior real cost. The Console cap is the hard backstop; a concurrent
    read-modify-write is still possible (documented) but the daily cadence makes it rare. Returns
    the updated month ledger. §voice-wiring (MEDIUM-4)."""
    path = _cost_ledger_path(day)
    ledger = util.read_json(path, {"month": day[:7], "days": {}})
    prev = ledger.setdefault("days", {}).get(day, {})
    ledger["days"][day] = {
        "usd": round(prev.get("usd", 0) + usd, 6),
        "tokens_in": prev.get("tokens_in", 0) + tokens_in,
        "tokens_out": prev.get("tokens_out", 0) + tokens_out,
        "calls": prev.get("calls", 0) + (1 if usd > 0 else 0),
        "model": model or prev.get("model", ""), "updated_at": util.now_utc_iso(),
    }
    ledger["total_usd"] = round(sum(d.get("usd", 0) for d in ledger["days"].values()), 6)
    util.write_json(path, ledger)
    return ledger


def month_to_date_usd(day: str, *, include_day: bool = False) -> float:
    """Total real LLM spend for day's month. Pre-flight checks exclude `day` (the run not yet made);
    displays/governor after record_cost pass include_day=True."""
    ledger = util.read_json(_cost_ledger_path(day), {})
    days = ledger.get("days") or {}
    return round(sum(v.get("usd", 0) for k, v in days.items() if include_day or k != day), 6)


def voice_budget_state(day: str, projected_usd: float = 0.0) -> str:
    """Pre-flight budget decision for the real LLM voice. 'halt' => use the deterministic voice
    (this run would cross the code ceiling); 'warn' => call but alert; 'nominal' => call. The $10
    Console cap is the last-line backstop below this. Includes today's ALREADY-recorded spend so a
    same-day re-dispatch still counts toward the ceiling. §voice-wiring (MEDIUM-4)."""
    mtd = month_to_date_usd(day, include_day=True)
    if mtd + max(0.0, projected_usd) >= config.LLM_MONTHLY_CEILING_USD:
        return "halt"
    if mtd >= config.LLM_MONTHLY_WARN_USD:
        return "warn"
    return "nominal"


# A NOTIFICATION MAY NOT DIE OF ITS OWN SUBJECT LINE. An ntfy title rides in an HTTP HEADER, and
# http.client encodes header values as latin-1, so one typographic dash in a title raises
# UnicodeEncodeError inside urlopen, the except below swallows it, and the page is silently not
# sent. That is not hypothetical. The Monday Owner's Brief titled itself with U+2014, so every
# Monday send since FEATURES["owners_brief"] flipped died on "'latin-1' codec can't encode
# character U+2014 in position 15" and logged one line nobody was reading. Observed in run
# 31386662898 at 12:19:29.08Z on 2026-08-10; the defect is deterministic, so it had been eating the
# digest every week. A fail-closed encoder that closes against the exact message the mechanism
# exists to carry is an authored outage, not safety (docs/37 rule 4). §S68-5.
#
# ASCII, not latin-1, and the narrowing is the header's alone. The body already goes out as UTF-8
# bytes and keeps every character it had. The header is narrowed one step further than the
# transport requires because ntfy decodes header bytes as UTF-8: a latin-1 "e-acute" would satisfy
# http.client and arrive as mojibake, which is a quieter failure than the one being fixed.
# Characters with a readable ASCII spelling get it; anything else becomes "?" and costs a glyph
# rather than the notification.
HEADER_TRANSLITERATIONS = {
    0x2014: " - ", 0x2013: "-", 0x2212: "-", 0x2010: "-", 0x2011: "-",
    0x2018: "'", 0x2019: "'", 0x201A: "'", 0x201C: '"', 0x201D: '"', 0x201E: '"',
    0x2026: "...", 0x00A0: " ", 0x2022: "*", 0x00B7: "*", 0x2192: "->", 0x2190: "<-",
    0x00A7: "S", 0x00B1: "+/-", 0x00D7: "x", 0x2264: "<=", 0x2265: ">=",
}


def header_safe(value) -> str:
    """An HTTP-header-safe spelling of `value`: ASCII by construction, and it never raises.

    Total by construction rather than by enumeration. The transliteration table is a readability
    courtesy for the characters this project actually writes; the `encode("ascii", "replace")` is
    the guarantee, and it holds for any input including one nobody predicted.
    """
    return str(value).translate(HEADER_TRANSLITERATIONS).encode("ascii", "replace").decode("ascii")


def ntfy(title: str, message: str, *, priority: str = "default") -> dict:
    """Dead-man switch. Posts to ntfy.sh/<NTFY_TOPIC> if the secret is set; else logs (the topic
    is a secret and NEVER lives in the repo — CLAUDE.md constraint)."""
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print(f"[ntfy:{priority}] {title} — {message}")
        return {"sent": False, "reason": "no NTFY_TOPIC set (dev)"}
    try:  # pragma: no cover - the network leg; the header construction above it is covered
        import urllib.request
        # header_safe on BOTH values: priority is a caller-supplied string too, and a header that
        # cannot encode is a dropped page whichever field carries the character.
        req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=message.encode(),
                                     headers={"Title": header_safe(title),
                                              "Priority": header_safe(priority)}, method="POST")
        urllib.request.urlopen(req, timeout=15)
        return {"sent": True}
    except Exception as e:
        print(f"[ntfy-failed] {title}: {e}")
        return {"sent": False, "reason": str(e)}


def symmetry_report(day: str, statements: list[dict], per_party_llm: dict, *, freshness: dict,
                    degraded: bool, nomen_measure: dict | None = None,
                    roster_table: dict | None = None, source_registry: dict | None = None,
                    fingerprint: dict | None = None) -> dict:
    """The §5.2 audit, per party, published on the Methodology page every day.

    `nomen_measure` (docs/19 §2a) is the per-party {tagged,total,rate} share of this day's synchronized
    phrases that are official names (bill titles / committee names). MEASUREMENT-ONLY and UNCONDITIONAL
    (it does not read FEATURES["nomenclature_tags"]) so an asymmetric tagger can never be invisible to
    the instrument that exists to catch asymmetry (docs/16 §6). It changes the audit JSON, not the
    marketed phrase surfaces the release flag gates."""
    caucus = caucus_sizes(statements)  # full corpus caucus proxy (all members with official sites)
    nomen = nomen_measure or {}
    source_health = "not_attested"
    if isinstance(freshness, dict) and freshness.get("status") in {"healthy", "degraded", "unknown"}:
        source_health = freshness["status"]
    parties: dict[str, dict] = {}
    for p in config.COMPOSITE_PARTIES:
        # DAY-SCOPED: every per-party row is THIS DAY's Lane-1 ingestion, consistent with the per-day
        # token/claim rows below — never the cumulative corpus total mislabeled under the day
        # (which read as "44,767 statements ingested today / 100% coverage"). §Session-5 fix.
        stmts = [s for s in statements
                 if (s.get("member") or {}).get("party") == p and s.get("lane") == 1
                 and s.get("published_at") == day]
        members = {(s.get("member") or {}).get("bioguide") for s in stmts if (s.get("member") or {}).get("bioguide")}
        llm_p = per_party_llm.get(p, {})
        nm = nomen.get(p) or {}
        dated = denominators.daily_measures(
            day, p, statements, roster_table=roster_table, source_registry=source_registry
        )
        parties[p] = {
            "statements_ingested": len(stmts),
            "members_covered": len(members),
            "caucus_size": caucus.get(p),
            "coverage_pct": round(100 * len(members) / caucus[p], 1) if caucus.get(p) else None,
            # W1 adds explicit units without changing the legacy fields above. The observed count is
            # evidence from this day. The eligible count is the corpus caucus proxy. Source health is
            # separate because the mirror cannot attest to every office endpoint.
            "observed_publishing_offices": len(members),
            # Transition compatibility: this flat key keeps its W1 corpus-proxy meaning for one
            # schema cycle. Public surfaces use the date-effective field below.
            "eligible_caucus_offices": caucus.get(p),
            "date_effective_eligible_caucus_offices": dated["eligible_caucus_offices"],
            "source_supported_offices": dated["source_supported_offices"],
            "publications": dated["publications"],
            "document_families": dated["document_families"],
            "office_source_states": dated["office_source_states"],
            "denominator_method_version": dated["method_version"],
            "denominator_window": dated["window"],
            "date_effective_denominators": dated,
            "source_collection_health": source_health,
            "tokens_in": llm_p.get("tokens_in", 0),
            "tokens_out": llm_p.get("tokens_out", 0),
            "claims_published": llm_p.get("claims_published", 0),
            "claims_dropped": llm_p.get("claims_dropped", 0),
            # docs/19 §2a — share of this day's synchronized phrases that are official names. The
            # denominator is the FULL synchronized set (not the truncated top-20 table), so a 103-D/15-R
            # display skew can't masquerade as an asymmetric tag rate (docs/16 §8.4). None when no
            # nomenclature tables are present (dark box).
            "nomenclature_tagged": nm.get("tagged"),
            "nomenclature_total": nm.get("total"),
            "nomenclature_rate": nm.get("rate"),
        }
    report = {
        # `day_scoped` marks `statements_ingested` as THIS DAY's ingest. It changed meaning once
        # (Session 5: it used to be the cumulative corpus total under a per-day label), and a reader
        # medianing across that boundary reads a healthy day as a 99.6% collapse. Reports now say
        # which semantics they carry instead of leaving readers to infer it from a date.
        "schema_version": 1, "day": day, "day_scoped": True,
        "statement": public_strings.SYMMETRY_PROMISE,
        "prompts_sha": prompts_sha(),
        "thresholds_sha": thresholds_sha(),
        "instrument_fingerprint": fingerprint or instrument_fingerprint.build(),
        "lane1_only": True,
        "degraded": degraded,
        "source_freshness": freshness,
        "source_collection_health_detail": public_strings.SOURCE_HEALTH_LIMIT,
        "deprecated_fields": {
            "parties.*.coverage_pct": public_strings.COVERAGE_DEPRECATION_NOTE,
        },
        "parties": parties,
    }
    util.write_json(config.DERIVED / "symmetry" / f"{day}.json", report)
    util.write_json(config.DERIVED / "symmetry" / "latest.json", report)
    return report


# ---------------------------------------------------------------------------
# §1.4.1 acceptance gate — "three consecutive unattended real runs (>=1 weekend day)"
#
# This exists because the gate was tracked in PROSE and the prose was wrong. On 2026-07-16 the canon
# read "the 3-consecutive gate is at 2/3 — the 07-16 cron completes it". That cron published the
# apology stub for both parties and reset the streak to zero. The claim survived because `gh run list`
# said `success` for all three runs: an Actions success means the workflow exited 0, which it does
# just as happily when the Daily Line falls back. A launch gate counted by reading run status is a
# launch gate counted by wishful thinking (Constitution: numbers come from code).
#
# FAILS CLOSED, in both directions that matter:
#   * a manifest with no `event` field predates this instrumentation -> NOT counted as unattended.
#     The streak therefore reads 0 until three genuinely-instrumented clean crons accumulate, which
#     is honest: we cannot retroactively prove a run was unattended, so we do not claim it.
#   * `degraded` covers BOTH the voice falling back and a forced-finalize, so a day that published an
#     apology can never be counted as a real run.
# ---------------------------------------------------------------------------
GATE_RUNS_REQUIRED = 3


def unattended_streak(today: str, manifest_dir=None) -> dict:
    """Consecutive clean UNATTENDED assemble runs ending at the most recent one.

    Returns {"value", "days", "weekend_day", "passes", "note"}. `passes` is the §1.4.1 gate itself:
    GATE_RUNS_REQUIRED consecutive clean unattended runs INCLUDING at least one weekend day.
    `manifest_dir` is injectable so tests never write into the real derived data."""
    from datetime import date as _date

    rows = []
    for p in sorted((manifest_dir or (config.DERIVED / "manifest")).glob("assemble-*.json")):
        day = p.stem.replace("assemble-", "")
        if day == "latest":
            continue
        m = util.read_json(p, {}) or {}
        rows.append((day, m))
    rows.sort(key=lambda r: r[0])

    streak: list[str] = []
    prev_day = None
    for day, m in reversed(rows):                 # walk backwards from the newest
        if not m.get("unattended"):               # absent (pre-instrumentation) or dispatched
            break
        if m.get("degraded") or m.get("forced_finalize"):
            break                                 # published, but not a REAL run
        # ADJACENCY. Manifests are keyed by TARGET day and a day that never assembled leaves no
        # manifest at all — the readiness gate's NO-OP is a legitimate $0 outcome, not a failure.
        # Without this check the walk would hop the gap and read 07-13/07-15/07-16 as "three
        # consecutive", quietly passing a launch gate on a machine that skipped a day. "Consecutive"
        # has to mean consecutive.
        try:
            d = _date.fromisoformat(day)
        except ValueError:
            break
        if prev_day is not None and (prev_day - d).days != 1:
            break
        prev_day = d
        streak.append(day)
        if len(streak) >= GATE_RUNS_REQUIRED * 3:  # bounded; we only need the head of the streak
            break
    streak.reverse()

    weekend = False
    for d in streak:
        try:
            if _date.fromisoformat(d).weekday() >= 5:
                weekend = True
        except ValueError:
            continue
    n = len(streak)
    passes = n >= GATE_RUNS_REQUIRED and weekend
    if n == 0:
        note = "no clean unattended run at the head — the streak is broken or uninstrumented"
    elif passes:
        note = f"{n} consecutive clean unattended runs incl. a weekend day — §1.4.1 PASSES"
    else:
        missing = []
        if n < GATE_RUNS_REQUIRED:
            missing.append(f"{GATE_RUNS_REQUIRED - n} more clean unattended run(s)")
        if not weekend:
            missing.append("a weekend day")
        note = f"{n}/{GATE_RUNS_REQUIRED} — still needs " + " and ".join(missing)
    return {"value": n, "days": streak, "weekend_day": weekend, "passes": passes, "note": note}
