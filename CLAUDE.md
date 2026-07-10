# PoliSpeak (working name — see docs/01-VISION.md §8 for naming candidates)

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
| 2 | **Opus** | Validation research — verify every load-bearing assumption against reality (APIs, ToS, costs, prior art). Mark every feature VIABLE / VIABLE-WITH-CHANGES / DEAD, with evidence + links. Kill without sentiment. | `docs/02-RESEARCH.md` | ⬅️ NEXT |
| 3 | **Fable** | Gameplan — final v1 scope (must ship in one weekend), architecture, schemas, pipeline stages, distillation prompts, voice guide, launch sequence, phased roadmap with acceptance criteria. | `docs/03-GAMEPLAN.md` | — |
| 4 | **Opus** | Implementation — build exactly what the gameplan specifies, end-to-end with real data on first run, tests where failure is expensive, README runbook. Verify against live sources. "Should work" is not done. | working pipeline + site | — |

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

- **Phase 1 complete** (Fable, 2026-07-10): `docs/01-VISION.md` written — end goals, five-family insight taxonomy (Coordination / Absence / Individuality / Framing / Lifecycle), 37-feature ranked universe (Tiers S/A/B/C), top-5 artifacts, virality theory, composite-voice guide, dashboard tour, naming candidates (front-runner: **Party Lines**), design tenets, and the §10 assumption register (R1–R11).
- **Next: Phase 2 (Opus).** Read the handoff note at the top of `docs/01-VISION.md`, validate the §10 assumption register against reality (priority order: R1–R3 corpus existence, R5 news baseline, R4 X rules, R6–R7 cost fit), and produce `docs/02-RESEARCH.md` with every feature marked VIABLE / VIABLE-WITH-CHANGES / DEAD, with evidence and links.
