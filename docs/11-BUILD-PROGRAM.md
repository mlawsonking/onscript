# 11-BUILD-PROGRAM — build dark, release by gate (v1, 2026-07-14)

> **What this is.** The standing work order that converts the gameplanned backlog (§10 v2 + v3 +
> the 09-DESIGN-REVIEW adoptions) into a **shelf of finished, verified, unreleased features**, built
> while the streak runs. The ladder (07-OPERATIONS §1) gates the system's *public posture*; it does
> not gate build sessions. Every feature here is built to completion — code, tests, verified on real
> data, rendered dark — and waits behind an explicit release switch. **Releasing is Michael's act:
> one commit (or one variable), on a morning he chooses.** Fable owns this doc; Opus executes it;
> the BUILDLOG records it.

## §0 Program invariants (checked every session)

1. **The streak is never destabilized.** The nightly cloud run staying green *is* the regression
   suite. Dark features are additive: new modules, new pages, new JSON — never breaking changes to
   the daily path. Schema changes are versioned and additive (Constitution VI).
2. **Build ≠ release.** No feature renders publicly, posts, or alters public numbers until its
   release flag flips. Flag flips are dated public commits — the release *is* the changelog.
3. **Every feature lands in a fixed final state:** code + tests + **verified against real data** +
   registered in the FEATURES registry as `built / verified / UNRELEASED`, with its gate evidence
   linked (backtest, neutrality note, acceptance run). "Should work" is not built.
4. **$0-LLM by default.** Deterministic first; one-time generation via subscription `claude -p`
   (§1.3 generator policy); the metered key exists only in GitHub Actions for the daily voice.
   `ANTHROPIC_API_KEY` is never set locally.
5. **Symmetry by construction** in every feature (identical thresholds both parties), and the
   **member-naming resolution** from 09: raw counts + receipts, never composite member scores;
   both-party lists ship together; ≥3 dated citations per named member.
6. **Publication-language gates:** the trend-language gate (08 §gates) and citation-or-silence
   apply to every rendered claim, dark or released.

## §1 The release-switch architecture (Opus builds this in the hardening session)

- **`FEATURES` registry** — a single committed, code-owned dict (in `pipeline/config.py`):
  `FEATURES = {"archive": False, "silence_board": False, ...}`. The site renderer and RUN B consult
  it; anything `False` builds its artifacts but does not render/link publicly. Flipping one value
  to `True` in a commit = the release act (dated, public, diffable — Constitution VIII spirit).
- **`POSTING_ENABLED`** — GitHub Actions **repo variable** (not a commit): gates the outbound
  Bluesky leg at runtime. Michael flips it in the UI at S3 launch. Kill-tested: no path posts when
  off, regardless of creds.
- **Registry discipline:** each feature's row in this doc gets three checkmarks over its life —
  ☐ built → ☐ verified → ☐ RELEASED (+date). BUILDLOG session entries update them.

## §2 The build queue

**Wave 0 — hardening (BUILDLOG Session-4 item 2, a–g).** Launch-blocking; do first. Includes the
FEATURES/`POSTING_ENABLED` architecture above, the posting day fix, receipts rendering, banner.

**Wave 1 — v2, "the insight release" (§10; build order = dependency order):**
| # | Feature | Spec | Depends on | Release gate |
|---|---------|------|-----------|--------------|
| 1.1 | **The Archive ("Library of Alexandria")** — 25-yr curves on every phrase page, Archive Coverage page, 327 chapters + era essays rendered, era-fingerprints front page | §10 v2 + 08/10 | chapter corpus (done), `passed==true` filter, citations_era wiring | §10 acceptance: coverage tables published; cross-era claims coverage-gated; chapters verifier-clean, zero uncited fragments |
| 1.2 | **Silence Detector** (GDELT DOC 2.0 + committed theme→taxonomy map) + mirror twin **"Shouting Into the Void"** | §10 v2 + 09 #5 | GDELT ingest (public, no key); rule-generated ex-ante event list (09 sharpening: floor-voted bills + FEMA declarations via `DATA_GOV_API_KEY`) | silence claims machine-gated + reproducible from published data; both directions ship together |
| 1.3 | **Authors-vs-Vessels member pages** (the amended S4) + pages-lite | 01-VISION S4 amendment; 09 #8 resolution | citation back-join wiring (scripts/analysis, promoted) | §10 acceptance kept: survives a hostile spot-check — every number expandable to its receipts; both-party lists simultaneous; no composite score |
| 1.4 | **The Script** — daily reconstructed-memo artifact | §10 v2 | Memo-Detector archetypes (10-FINDINGS methods) | verifier-clean; election-cycle claims carry the density caveat |
| 1.5 | **Weekly Awards** (Ventriloquism et al.) | §10 v2 + vision §4 amended | 1.3 | awards fire symmetrically by construction; brand-account copy deadpan; releases only post-S3 |
| 1.6 | **Floor leg** (GovInfo H/S/E granules + name→bioguide resolver + coverage metric) | §10 v2 | `DATA_GOV_API_KEY` (set) | ≥95% attribution resolved or the gap published; Lane-2 machine-block tests |
| 1.7 | **The Duet** + **phrase search** | §10 v2 | — | standard verifier + neutrality |
| 1.8 | **Owner's Brief** (Monday ntfy digest: five health numbers + shelf report) | 07-OPS §3 | ntfy topic (set) | fires Mondays; numbers match manifests |
| 1.9 | **Credit-claim ledger** (touts joined to roll-call votes — raw, two receipts, no verdict) | 09 adopt-later, now unblocked | congress.gov roll-calls via `DATA_GOV_API_KEY`; bill-reference extractor | member-naming gate (§0.5); alphabetical default order; no colors |
| 1.10 | **Memo-cadence evasion flag** (4th burst archetype: STAGGERED/SMOOTHED) | 09 add | Memo-Detector code | instrumented as signal, not accusation; density-controlled |

**Wave 2 — v3, "the coordination release" (§10, by Oct 5):**
| # | Feature | Notes / gates |
|---|---------|---------------|
| 2.1 | **The Memory Hole** (re-poll mirrored URLs; deletion/stealth-edit detection by hash diff) | §10 acceptance: injected test edit caught ≤48h. Deleted statements = highest-signal artifacts (09) |
| 2.2 | **Off-Script alerts feed** — *descriptive* anomalies only (spike-sans-news, sudden silence, deviation) | The *predictive* breakout alert stays **retired** (backtest, 10-FINDINGS). Member-deviation items obey §0.5. Gate: 14-day zero-false-positive soak |
| 2.3 | **Upstream Graph** + leadership-origin tags | "memo probability" language needs the neutrality review; correlation-not-cause labels |
| 2.4 | **Bill-brand tracker** · **phrase lifecycle cards + obituaries** (curation documented as selection-not-computation) · **response-latency clocks** · **frame-pair tracker** · **Time Machine** | per §10 |
| 2.5 | **Public API / bulk downloads + embeds** | serves the full derived corpus; the ecosystem leg (deadpan core, narratives downstream) |
| 2.6 | **Precision/recall eval table** (frozen hand-labeled holdout, rendered on Methodology) | **Human dependency: Michael labels the holdout** (tasked). The auditor publishes its own error rate |

**Not in this program (deliberately):** the HORIZON reservoir (quarterly-pick doctrine, 05 §3 —
bulk-building it would repeal the doctrine); Season-2 items (scheduled, Jan 2027); the parking lot;
retired items (naive S4 %-match; predictive breakout alerts).

## §3 Cadence & reporting

Each Opus session: pick the next unbuilt row → build → verify → register → BUILDLOG entry +
"You are here" update. The Monday ritual gains one line: **the shelf report** (features
built-verified-unreleased, and which release gates are cleared). Release decisions happen at the
ritual or whenever Michael chooses — never inside a build session.

*Fable, 2026-07-14. The shelf fills while the streak runs; every launch after the first is one
commit long.*

## §4 Named follow-ups queued by the nomenclature wiring (docs/19, Session 21 Opus)

- **Support-graph validity — a pre-v2-Concordance requirement (docs/19 §4c, 2nd pass).** The binding
  law is *no rendered proposition may outlive its evidence*: every factual rendered clause carries a
  non-empty machine-readable `support_cluster_ids`, and removing a cluster from the render input must
  remove every clause it exclusively supports (or leave it supported by another mapped cluster); no
  factual clause may survive with zero valid supports. The invariant is the support GRAPH, not textual
  difference (a prose-diff would fail on harmless rewording and pass a renderer that kept an unsupported
  claim in other words). **Not landed now: the current render path (deterministic/LLM voice) emits
  free-text prose that does not bind clauses to cluster ids** — building that binding is the Concordance
  (1.4) work, so this rides with it. Until then the Session-21 render-time re-composition is the
  interim guarantee (drop the scaffold cluster AND re-derive the prose from the surviving stats, so a
  dropped cluster cannot leave a claim behind — verified on 07-17 D).
- **Scaffold-aware key SELECTION** — the P2 breadth mitigation. Today a real cluster whose most-common
  4/5-gram happens to be a fragment (ends in a function word) is DROPPED whole by the admission gate
  (`is_scaffold_key`); the refinement is to pick the cluster's best NON-scaffold gram as its key instead
  of killing the cluster. Recovers legitimate coordination the conservative gate currently over-drops
  (measured: e.g. a committee-markup cluster keyed "…markup of the"). Lands with 1.3/1.5 (SPAN-gated).
- **Per-member ingest-health flags** in the nightly audit (docs/19 §2a) and the **phrase-page /
  archive-fingerprint** nomenclature tag surfaces beyond the day table — minor completions of the §2
  wiring (the day table, where the defect lives, is done).
- **The §4c definitions:** the "observed publishing member" R3 denominator ("source successfully checked
  AND ≥1 eligible document in the window", not merely a reachable site) and the
  first/observed/earliest-in-lane **timestamp distinction** wherever "first" renders — both pre-v2
  requirements, land with the origination pages (1.3) and the denominator work (R3).
