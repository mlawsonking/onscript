# OnScript

*Repo codename: `polispeak`. Product name: **OnScript** (`onscript.news`).*

Every morning, unattended: ingest what U.S. members of Congress publicly said, distill each
party into one cited composite "Daily Line," verify every receipt mechanically, publish to
the dashboard, post to both Bluesky accounts, audit our own symmetry in public — and never
miss. The compounding time-series is the moat; the receipts discipline is the armor.

- **What / why / product thesis:** [`CLAUDE.md`](CLAUDE.md)
- **Phase docs:** [`docs/01-VISION.md`](docs/01-VISION.md) · [`docs/02-RESEARCH.md`](docs/02-RESEARCH.md) · [`docs/03-GAMEPLAN.md`](docs/03-GAMEPLAN.md) (the build spec)
- **Build log (Phase 4, multi-session):** [`docs/04-BUILDLOG.md`](docs/04-BUILDLOG.md)
- Predecessor (2022): [PoliticianTweeting](https://github.com/mlawsonking/PoliticianTweeting)

## Architecture (gameplan §2)

```
GitHub Actions (public repo, free tier)
  RUN A collect  (05:30 ET): pull+mirror congress-press · Bluesky (Lane 2) · normalize
                              · phrase engine (local) · submit Anthropic extraction batch
  RUN B assemble (07:30 ET): retrieve batch · cluster · 2 Daily-Line calls · VERIFY (blocking)
                              · render JSON/SVG/og-card · commit · post Bluesky · symmetry audit
raw (immutable)  -> GitHub Release assets      ledger/state -> Release asset
derived (small)  -> committed in data/derived/ -> the site reads it
```

Two-lane data model (§5): **Lane 1 = press releases only**, the sole input to any cross-party
number; **Lane 2 = Bluesky/floor**, enrichment + citations, machine-blocked from comparative
metrics. Identical instrument for both parties, audited nightly in public.

## The deterministic core (built, verified — Phase 4 session 1)

Stdlib-only Python (runs identically on the Ubuntu runner and a dev box), `$0` LLM:

| module | stage | does |
|---|---|---|
| `pipeline/fetch.py` | A1 | pull `dwillis/congress-press`, mirror raw immutably, dead-man freshness |
| `pipeline/normalize.py` | A3 | statement schema · dedupe · syndication filter · exact + **near-identical** joint-collapse (§11 trap 2) |
| `pipeline/boilerplate.py` | A4 | structural strip + n-gram template/date suppression |
| `pipeline/phrases.py` | A4 | content n-grams · per-(congress,party) DF suppression · first-appearance ledger · discipline index |
| `pipeline/build.py` | — | top synchronized phrases · adoption curves · coverage tables (derived JSON) |
| `pipeline/verify.py` | B4 | **deterministic citation verifier** (substring · ≥3 members · digit-whitelist) — the product |
| `pipeline/deterministic.py` | — | the pure run: normalize → engine → ledger → derived |

## Run it locally

Requires only Python 3.11+ (stdlib). No third-party deps for the deterministic core.

```powershell
# Stage-1 backfill: pull the 119th-Congress epoch (2025-01-03 -> today), build the ledger, prove it
python scripts/backfill_stage1.py                 # full epoch
python scripts/backfill_stage1.py --start 2026-06-01   # fast slice for a smoke test
python scripts/backfill_stage1.py --offline        # rebuild from the existing raw mirror, no network

# Reproducibility check (§1.4.8): rebuild twice from raw, assert byte-identical derived JSON
python pipeline/rebuild.py

# Tests (no pytest needed)
python tests/run_tests.py
```

## Secrets (GitHub Actions — never in the repo)

`ANTHROPIC_API_KEY` · `NTFY_TOPIC` · `BSKY_BLUE_HANDLE`/`BSKY_BLUE_PASSWORD` ·
`BSKY_RED_HANDLE`/`BSKY_RED_PASSWORD` · `DATA_GOV_API_KEY` (v2 floor leg).

## Launch blockers (human-only, gameplan §7.3, §9)

- Michael registers `onscript.news` + `theonscript.com` (~$30), creates `blue.onscript.news` /
  `red.onscript.news` Bluesky accounts (spec-labeled), sets Actions secrets.
- Create the public GitHub repo + push (Actions is the true runtime; no remote exists yet).
- One-hour media-attorney review of composite framing + methodology page (R9 prudence).
