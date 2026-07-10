# 04-BUILDLOG — OnScript, Phase 4 (Implementation, Opus)

Running log of the multi-session build. Convention (per CLAUDE.md / gameplan §13): each
session records **progress against the §1.4 acceptance criteria** and any **sanctioned §13
deviations with rationale**, so a fresh session resumes without re-deriving state. The phase
is done when **§1.4 passes in full**, not when code exists.

> **RESUME POINTER (read first).** The deterministic core (ingest → normalize → phrase
> engine → ledger → derived JSON) and the citation verifier are **built and verified on real
> `congress-press` data** (session 1). Not yet built: the LLM layer (P1/P2/P3 wiring to the
> Anthropic Batch API), the two GitHub Actions workflows (RUN A / RUN B), the Astro site, and
> Bluesky posting. Those are session-2+ and need two things this dev box lacks: the
> `ANTHROPIC_API_KEY` secret and a GitHub remote (Actions is the true runtime). Michael's
> launch errands (domains/handles/repo/secrets, §7.3/§9) are the human gate.

## Environment (this dev box)

- **Python:** `C:\ProgramData\miniconda3\python.exe` (3.13). The deterministic core is
  **stdlib-only** on purpose so it runs identically here and on `ubuntu-latest` (Python 3.12).
- **No Node / no npm** locally → the Astro site can't be previewed here; Vercel builds it in
  the cloud (charter: no local Node dependency for deploys). Site work is written, not locally run.
- **No git remote yet** → Actions can't be exercised until Michael creates the public repo and
  pushes. Workflow YAML will be written and cloud-verified after that (recorded honestly, not
  claimed as passing before it runs).
- Network egress works from Python (used for the real-data backfill below).

## §1.4 acceptance-criteria status

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | 3 consecutive unattended real runs publish site + both Bluesky threads by 09:00 ET | ⛔ not started | needs LLM layer + Actions + site + Bluesky (session 2+) |
| 2 | Citation integrity: every claim ≥3 members; every fragment a verbatim substring; 0 published failures | 🟡 verifier built + unit-tested | `pipeline/verify.py`; `tests/test_verify.py` (5 tests). Not yet exercised on live LLM output |
| 3 | Kill-test A (source death) + Kill-test B (batch timeout) | 🟡 partial | A1 degraded-mode + `--offline` mirror rebuild exist; ntfy + batch-fallback are session-2 |
| 4 | Backfill proof: ledger loaded to epoch; a known 2026 phrase's curve spot-checked | 🟡 engine proven on a real slice | 2-month slice verified (below); **full 2025-epoch backfill running** — result appended when complete |
| 5 | Boilerplate proof: top-20 synchronized phrases contain zero template artifacts | ✅ **passing** | see session-1 proof below |
| 6 | Symmetry report published from real run data | ⛔ not started | needs the site (session 2+); coverage tables already computed (`data/derived/coverage.json`) |
| 7 | Budget telemetry in manifest; projected month ≤ $10; Console cap set | 🟡 manifest scaffolded | `spend_estimate_usd` in manifest (0 for the deterministic core); governor is session-2 |
| 8 | Hygiene: repo public; secrets scanned; raw→Release assets; `rebuild.py` reproduces a day from raw | 🟡 partial | `rebuild.py` determinism check built; `.gitignore` keeps raw/state out of git; repo-public + Release upload are session-2/Michael |

Legend: ✅ passing · 🟡 built, not fully proven end-to-end · ⛔ not started.

## Session 1 (2026-07-10) — the deterministic moat, verified on real data

**Built:** the full deterministic core (table in the README), the three versioned prompts
(`pipeline/prompts/*.v1.0.txt`, §6.2 verbatim), `taxonomy_v1.json` (24 topics), the verifier,
`rebuild.py`, and the test suite (`tests/`, 17 tests, all passing).

**Verified against real `congress-press` data** (June–July 2026 slice, 5,560 records):

- ingest+mirror works; upstream freshness read live (pushed 9.8h ago → fresh).
- normalize: 5,559 kept / 1 reject; **12 exact joint-collapses + 157 near-identical
  (delegation) collapses**; 6 syndicated flagged.
- phrase engine: 6.4M n-grams tracked → 36,200 DF-boilerplate suppressed → **30,290-entry
  ledger** with first-sayer + adoption curves + per-party discipline index.
- bipartisan coverage: D 3,383 statements / 249 members; R 2,134 / 243 members.
- **Real coordination signal confirmed:** e.g. **8 Democrats on 2026-06-30** independently
  converged on "if you are born in the united states" / "birthright citizenship" / "by
  executive order" (first-sayer A000380); **8 Democrats on 2026-06-25** on "to end temporary
  protected status" for "haitians and syrians." First-sayer, roster, and curve all captured.

**Two data-quality traps surfaced by real data and fixed (this is why we run against reality):**

1. **§11.1 boilerplate / dates.** First pass surfaced `"tuesday july 7"`, `"july 9 2026"` and
   template soup in the top phrases. Fixed with temporal-suppression regexes (weekdays, years,
   month+day) + the existing template list. §1.4.5 now passes.
2. **§11 trap 2 — joint releases masquerading as coordination.** A Houston-delegation letter
   (near-identical text, not byte-identical) inflated one event into ~18 "coordinated" phrases.
   Fixed by adding **near-identical (shingle-Jaccard) collapse** on top of exact collapse; the
   ledger shrank 99,883 → 30,290 (≈70% was near-dup inflation), and the flagship chart is no
   longer debunkable on day one.

## §13 deviations / knob settings recorded (all within "Open knobs" — no locked decision touched)

- **Boilerplate regex list (open knob):** extended with temporal patterns (weekdays, 4-digit
  years, month-adjacent-to-day, am/pm/tz). Rationale: dates are scheduling, not political
  messages; §1.4.5 required it. `"may"` as a modal deliberately survives (only `month + day`
  is flagged).
- **Near-identical joint-collapse (implements §11 trap 2, not a knob relitigation):** added
  `NEAR_JOINT_JACCARD=0.70`, `NEAR_JOINT_SHINGLE_K=8`, `NEAR_JOINT_MIN_TOKENS=40`,
  `NEAR_JOINT_WINDOW=80` (length-sorted windowed comparison bounds cost). crc32 shingles (not
  builtin `hash()`) so clustering is deterministic across runs → `rebuild.py` reproducibility holds.
- **Independents (I):** kept as their own bucket; they enter the ledger but are **not** folded
  into either composite in v1, and comparative metrics are D/R only. Caucus-aware bucketing is a
  v2 refinement (logged here so it isn't silently lost).
- **DF boilerplate threshold:** default top 0.5% per-(congress,party), min 40 docs/stratum
  before DF-suppression engages (avoids nuking small strata). Unchanged from §13 default.

## Next session (2+) — planned order

1. **LLM layer** (`pipeline/extract.py`, `pipeline/cluster.py`, `pipeline/distill.py`): P1
   extraction (Haiku batch, keyed by statement hash so nothing is distilled twice), local
   clustering into talking points, P2 Daily Line (Sonnet batch → direct fallback), run the
   blocking verifier over the output, merge Daily Lines into the per-day derived JSON. Needs
   `ANTHROPIC_API_KEY`; build an offline dry-run mode so it's testable without spend.
2. **RUN A / RUN B GitHub Actions workflows** + ops (manifest, budget governor, ntfy dead-man,
   symmetry report, Release-asset upload). Cloud-verified only after the repo is pushed.
3. **Astro site** (Today / day archive / phrases / methodology / about) reading `data/derived/`;
   og-card via headless Chrome in RUN B.
4. **Kill-tests A & B**, then the three-consecutive-unattended-runs acceptance gate.
5. **Stage 2 "Alexandria"** (2001 full-history, dark-week, non-blocking) once schemas are frozen.
