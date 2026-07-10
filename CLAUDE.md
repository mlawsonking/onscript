# OnScript (repo codename: polispeak — name locked in Phase 3, see docs/03-GAMEPLAN.md §0)

A daily, automated system that ingests what elected U.S. officials publicly say, distills each party's real talking points into one composite cited voice, and surfaces the coordination machinery of American political speech: who's reading from the same script, what nobody will say, and which members are just vessels. Two composite party accounts are the marketing; the public dashboard and the compounding time-series are the product. Midterms November 2026 are the attention window.

## Product thesis (condensed)

**Compression, not parody.** "This is literally what each party said today, compressed to one voice, with receipts." The comedy is emergent because the source material is real. Three insight engines ride on the corpus:

1. **Talking-point propagation detection** — first-appearance tracking + adoption curves across members over 24–72h. A phrase going from 2 accounts to 90 in a day detects the private memo from its public output.
2. **The silence detector** — topics dominating national news that neither party's members will touch, diffed against a daily news baseline. The absence map.
3. **The on-script index** — per-member score of verbatim party language vs. own language. "Most on-script member of Congress" leaderboard.

Every claim is citation-backed (≥3 real source statements: member, date, URL). This is load-bearing armor against bias accusations, not decoration.

Predecessor: github.com/mlawsonking/PoliticianTweeting (2022, twint + trigrams + Flourish). It proved the signal exists (Dems tweet with higher phrase alignment; national moments ignite as phrase spikes) and died when twint/the Twitter API died. This project is the 2026 rebuild with LLM distillation and open data sources.

## Model-split workflow — STRICT, check which model you are before doing anything

| Phase | Model | Job | Output | Status |
|-------|-------|-----|--------|--------|
| 1 | **Fable** | Expansive ideation — feature universe, virality theory, top artifacts. No code, no feasibility research. | `docs/01-VISION.md` | ✅ done 2026-07-10 |
| 2 | **Opus** | Validation research — verify every load-bearing assumption against reality (APIs, ToS, costs, prior art). Mark every feature VIABLE / VIABLE-WITH-CHANGES / DEAD, with evidence + links. Kill without sentiment. | `docs/02-RESEARCH.md` | ✅ done 2026-07-10 |
| 3 | **Fable** | Gameplan — final v1 scope (must ship in one weekend), architecture, schemas, pipeline stages, distillation prompts, voice guide, launch sequence, phased roadmap with acceptance criteria. | `docs/03-GAMEPLAN.md` | ✅ done 2026-07-10 |
| 4 | **Opus** | Implementation — build exactly what the gameplan specifies, end-to-end with real data on first run, tests where failure is expensive, README runbook. Verify against live sources. "Should work" is not done. | working pipeline + site | ⬅️ NEXT |

**Phase gates:**
- Which docs exist in `docs/` determines the phase. Do not do another model's phase.
- Each phase ends with: its doc committed, a one-paragraph handoff note at the top of that doc for the next model, and the Status column + Current Status section here updated.
- If you are Opus and `01-VISION.md` doesn't exist → stop and say so.
- If you are Fable and `02-RESEARCH.md` exists and is complete → you are in Phase 3, not Phase 1.

## Hard constraints

- **Stack:** GitHub Actions (cron + compute, free tier) → Anthropic API (Haiku-class for the daily pipeline; **cost ceiling $10/month at v1**) → JSON → static site on Vercel. No servers to babysit. No local Node dependency for deploys (GitHub → Vercel auto-deploy, same as PlainSpeak).
- **Data sources:** official/open first (congress.gov API, member press releases, Bluesky). X ingestion only if research shows a sane path; X *posting* for composite accounts is a research question (pricing + automation labeling rules), not an assumption.
- **Citation integrity is non-negotiable:** every distilled talking point links to ≥3 real source statements with member, date, URL. If it can't be cited, it doesn't ship.
- **Robustness:** daily pipeline survives source outages (skip-and-log, never crash the run); dead-man switch (ntfy notification to Michael's existing topic — topic name lives in GitHub Actions secrets, NEVER in this repo — on failed runs or anomalously small output); raw ingested data stored immutably so the time-series is rebuildable.
- **Neutrality by construction:** identical pipeline, prompts, and thresholds for both parties, documented visibly on the site. Symmetric instrument; asymmetric findings allowed — that distinction is the answer to the first accusation.
- **Compounding asset, not launch pop:** the time-series is the moat. Design storage/schemas so month-6 me thanks weekend-1 me. Never break schema compatibility; raw data is append-only and date-stamped.

## Current status

- **Phase 1 complete** (Fable, 2026-07-10): `docs/01-VISION.md` — end goals, five-family insight taxonomy, 37-feature ranked universe, top-5 artifacts, virality theory, voice guide, naming candidates, design tenets, assumption register R1–R11.
- **Phase 2 complete** (Opus, 2026-07-10): `docs/02-RESEARCH.md` — all R1–R11 validated against live primary sources, adversarially re-checked; every feature marked. Headlines: spine flips to press releases (`dwillis/congress-press`) + Bluesky; X DEAD as automated channel; "Party Lines" DEAD → **OnScript**; GDELT 2.0 news baseline; $10/mo fits only batched+cached+routed; press releases are the only symmetric two-party source (mirror the scraper). No feature dead.
- **Phase 3 complete** (Fable, 2026-07-10): `docs/03-GAMEPLAN.md` — the build spec. Five governing decisions (daily-always cadence with budget governor; **two-lane neutrality architecture** with nightly public symmetry audit; mirror+cold-standby-fork+dead-man for the scraper dependency; batch/cache/route ≈ $6–9/mo; transformative self-surveillance voice). Weekend v1 = the streak machine (ingest→distill→verify→publish→post→audit) + **backfilled ledger to 2025-01-03** so the time-series moat exists at launch. Schemas (schema_version 1), pipeline stages A1–B9 with failure semantics, verbatim prompts P1–P3 (public + versioned), voice/account specs (`blue.onscript.news`/`red.onscript.news`), launch sequence, roadmap v2 (silence detector + on-script leaderboard + floor leg, by Aug 10) / v3 (alerts + Memory Hole + upstream graph, by Oct 5) / season 2 (assimilation curves, Jan 2027), risk register, locked decision log (§13).
- **Phase 3 amendment (same day, after review with Michael):** backfill staged to the **full 2001 corpus** ("Library of Alexandria," gameplan §1.3) — deterministic 25-year ledger during dark week ($0 LLM), era-granular LLM chapters in v2 (≤$30 one-time, before Sep 1, on Michael's explicit go), temporal coverage gates on all cross-era claims, `congress`-keyed schemas in v1.
- **Next: Phase 4 (Opus).** Read the handoff note at the top of `docs/03-GAMEPLAN.md`; build §1 exactly (v1 acceptance criteria §1.4 including both kill-tests); locked decisions in §13 are not to be relitigated. One human errand gates launch: Michael buys domains/handles (§7.3, ~$30 one-time).
