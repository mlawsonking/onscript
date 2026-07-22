# 24 — Public-Surface Stabilization Brief (BINDING)

**Authority:** Fable, Session 43, 2026-07-22. Adjudicates the external ("Codex") request
"authorize the OnScript public-surface stabilization packet." Every packet premise was
independently re-verified against the repo before ruling (Art. XVI); the defect register below
is the evidence, with anchors. Michael holds the standing veto; **release (push/deploy) is his
act, never the implementer's.** The implementer executes this brief exactly and does not
re-litigate rulings (Constitution; docs/21 §2 posture applies to any non-Fable worker,
including external ones).

**Decisions: P0-A APPROVE (modified) · P0-B APPROVE (modified) · P1 APPROVE (modified) ·
P2 APPROVE, STAGED · P3 DEFER.**

---

## 0. Verified defect register (do not re-derive; reproduce each as a failing test first)

- **D1 — stale public posture.** About says "The accounts are live but have not begun posting"
  (`pipeline/site.py:1910`, rendered in `site/public/about.html`) and "At public launch, each
  will post…"; the posts-empty branch repeats it (`site.py:1968`). Accounts are plain text, not
  links (`site.py:1904-1906`); the house account is absent from About entirely. Zero links to
  the public GitHub repo or `data-latest` anywhere in `site.py`. `README.md:71` says "no remote
  exists yet" under a live "Launch blockers" section. `docs/07-OPERATIONS.md:20` marks S2
  "(← current, 2026-07-14)".
- **D2 — the signed post archive lags its own posting run and has no partial handling.**
  `assemble.yml` order: render (step 5, `:97-98`) → redact (`:109-110`) → post (`:112-113`) →
  persist (`:115-118`) → one commit of `data/derived` + `site/public` (`:120-134`). `site.py`
  snapshots manifests at import (`_POSTED_THREADS`, `site.py:1985`), so the committed
  `posts.html` structurally excludes the thread posted in the same run — proven on HEAD
  `265e576`: `post-2026-07-21.json` (`posted:true`, real `root_uri`) landed in the same commit
  as a `posts.html` whose newest entry is 07-20 — under the copy "Any post attributed to these
  accounts that does not appear here is not ours" (`site.py:1962-1965`). Separately,
  `posted_threads()` filters only on `posted`+`thread` (`site.py:1942-1945`): a
  `partial:True` manifest (whose `thread` is the full *intended* text) would render as a
  complete authenticated thread, replies included, that never went live.
- **D3 — pre-epoch observations on public Stage-1 surfaces.** `STAGE1_EPOCH = "2025-01-03"`
  (`config.py:58`). 51 of 277 public phrase pages carry 2013–2024 observations (first-seen
  lines, curve axes, peaks); the embedded search index (`phrase_search_index()`,
  `site.py:1049-1078`) ships rows like `{"q":"the supreme court","p":79,"f":"2013-01-04"}`.
  Mechanism: `alexandria.merge()` writes the merged 25-year ledger into the state ledger and
  passes it to `build_derived` (`alexandria.py:191,195`), and neither `build.phrase_page`
  (`build.py:202-214`) nor the site applies any epoch filter. The same pages print "Our corpus
  begins 2025-01" (`site.py:1480-1483`) directly beneath 2013 receipts. This is also a live
  R6/seam exposure: pre-2021 legacy-lane observations mixed into public curves with no lane
  disclosure, while `FEATURES["archive"]` is dark.
- **D4 — bare Bioguide IDs rendered as names.** 20 phrase pages render e.g. "2013-04-17 by
  S001168" — `member_name()` falls through to `esc(bioguide)` (`site.py:108-124`);
  `data/reference/roster.json` is tracked but current-Congress-only (538 entries; none of the
  leaked historical IDs resolve). Every leak has a pre-epoch first-sayer; P1's window gate
  removes the entire live class.
- **D5 — the receipts promise gap.** Search copy promises "the members who carried it"
  (`site.py:1094-1095`); `phrase_page_body()` (`site.py:1433-1486`) renders curve + first-sayer
  (+ tie) + bare peak count — no roster, no citations, no sources. Data reality: per-phrase
  JSONs carry **no per-day member identities beyond day 1** (series are counts only); day
  JSONs carry citations only for the LLM-selected talking points, joined by fuzzy label. A
  receipts feature therefore requires a new deterministically built evidence slice.
  `_wayback_url()` (`site.py:737-743`) is already a pure function of url+date — no stored
  archive data or network needed. Unit/joint machinery exists: `_unit_key`
  (`pipeline/phrases.py:44-46`) counts a joint family once by construction.
- **P3 facts.** `site/brand/brand.py` requires Pillow; **no workflow installs any pip package**
  (stdlib-only CI); `site/public` is 296 files / ~5.5 MB committed. Per-page PNGs mean a new
  dependency on the live daily path plus committed-binary churn → DEFER per the requester's own
  rule.

---

## 1. P0-A — public truth (APPROVE, modified)

Scope: `pipeline/site.py` copy, `README.md`, `docs/07-OPERATIONS.md` status marker,
`docs/20-DRIP-CALENDAR.md` supersession notice, focused tests.

1. About: accounts post daily (three accounts including the house account
   `@onscript.news`, each a clickable `https://bsky.app/profile/<handle>` link); remove
   "have not begun posting" / "At public launch" framing; fix the `site.py:1968` empty-branch
   copy to something that is true in any environment (e.g. "No posts recorded in this build").
2. About + Methodology: link the public GitHub repository and the `data-latest` release assets.
   Derive the repo URL once — add a single constant (e.g. `config.REPO_URL`) rather than
   hardcoding it at call sites; take the value from the actual `origin` remote.
3. Degraded-voice copy: describe it as a **deterministic fallback, plainly labeled** — but do
   **NOT** rename generator/provenance values (`dry_run`, `P3:dry_run`) in manifests or
   historical data; those are frozen provenance labels. Copy only.
4. `README.md`: rewrite as the post-launch operator/reproduction runbook (what runs when, where
   state lives, how to reproduce a day, `pipeline.redact --check` verification, kill switches).
   Remove the completed "Launch blockers" section. Never name the ntfy topic or any secret value.
5. `docs/07-OPERATIONS.md`: move the "current" marker to S3 with date 2026-07-22 — additive;
   do not rewrite ladder history. `docs/20`: short supersession notice at top (docs/23 §7.3 +
   Session 42 govern current dates); do not rewrite historical decisions.
6. **Forbidden:** edits to `docs/03-GAMEPLAN.md` / `docs/04-BUILDLOG.md` (the "public at
   launch" hits there are historical record, not stale copy).
7. Validation: scan all regenerated `site/public` HTML for the retired phrases; zero hits.

## 2. P0-B — signed archive truthful in the same run (APPROVE, modified)

Scope: `.github/workflows/assemble.yml`, `pipeline/site.py`, one focused workflow-order test +
site tests. **Never execute `pipeline/post_bluesky.py`** — not even "safely"; a gated local run
rewrites tracked manifests (S40 finding 9). It may be read and imported by tests with stubs.

1. Keep the pre-post render exactly where it is — it is the preflight that stops a run from
   posting a thread whose receipts page cannot build. Add a **second render step after the post
   step and before the commit step.** A fresh `python pipeline/site.py` process re-globs the
   manifests (the import-time snapshot makes an in-process re-render insufficient — this is why
   it must be a new invocation).
2. Ordering invariants (assert in a test that parses the workflow YAML): exactly two site-render
   invocations; render₁ before post; render₂ after post and before commit; the redact step stays
   before the state-persist/upload step; commit still stages `data/derived` + `site/public`
   together. No new network use in render₂.
3. Failure semantics for render₂ — all-or-nothing and non-blocking: snapshot `site/public`
   before render₂; on nonzero exit, restore the snapshot, emit a loud log marker, and let the
   job continue to commit (a failed render₂ degrades to today's status quo — one-run lag that
   self-heals — which must never cost the day's data commit). Render₁'s failure semantics are
   untouched (job dies before posting; dead-man fires).
4. `posts.html` truth rules in `site.py`:
   - Only `posted=True` with a non-empty `root_uri` renders as an authenticated thread.
   - `partial=True`: render the entry explicitly marked partial with the root link only —
     **never print reply text the manifest cannot prove went live.**
   - A `posted=True` entry missing `root_uri` renders as unverifiable, not as authenticated.
   - Reword the absolute claim so it is literally true under (i) normal same-run inclusion,
     (ii) a failed render₂ (one-run lag), (iii) partials — e.g. scope it with a time bound.
     Symmetric wording, both parties.
5. Do not touch: posting logic, manifest schema, redact, dead-man, `POSTING_ENABLED` handling.

## 3. P1 — temporal honesty while Archive is dark (APPROVE, modified)

Ruled implementation: **render-time public-window gate only.** Do not modify
`alexandria.py`, the state ledger, `build_derived`'s ledger handling, or any committed
`data/derived/phrases/*.json` (they are data, not claims; Archive will need them; most are
never rewritten by daily runs, so a build-time-only fix would strand the 51 stale pages).

1. One pure helper (site-side, or in `build.py` if shared): filter a phrase series to days
   `>= config.STAGE1_EPOCH`. Apply to: phrase-page curve, "First recorded" line, peak,
   distinctiveness display context, data-points/active-day counts, and every
   `phrase_search_index()` row (`p`/`f` recomputed from the gated series).
2. **The epoch has exactly one source: `config.STAGE1_EPOCH`.** No new hardcoded "2025"
   prose; the existing footnote renders its date from config.
3. First-sayer rules: if the true `first_seen.date >= epoch`, render as today (roster name).
   If pre-epoch, the derived file cannot name the in-window first carrier — render an honest
   line: first in-window active day, **no member attribution, no bioguide**, plus the existing
   pointer that pre-window history awaits the Archive release. Additionally harden
   `member_name()` so no caller can ever emit a raw ID styled as a name ("member name
   unavailable" instead). Do **not** add a historical roster in this packet — that is
   Archive-flip work.
4. A phrase with zero in-window observations: its page remains (public pages are permanent)
   with an honest empty-window state; it is dropped from the search index (the index promises
   a curve and carriers; an empty page is not a result).
5. Methodology's coverage description and the phrase-page disclosure must describe the same
   window as the statistics.
6. **Kill test (required, as requested):** fixture whose largest peak and earliest sayer are
   pre-epoch → Archive-off output uses the post-epoch peak and post-epoch first-seen handling;
   the pre-epoch record remains intact in the fixture/derived input. Plus: index rows agree
   with page stats; zero-in-window phrases are unlisted but their pages render.

## 4. P2 — receipts promise (APPROVE, STAGED — Stage A mandatory, Stage B gated)

**Stage A (mandatory): copy–delivery alignment.** Reword the search subhead and any phrase-page
promise so they promise exactly what renders after this packet — no more. If Stage B ships,
the copy may promise receipts in the "where at least three distinct offices can be cited"
form; the test "search copy and phrase-page behavior agree" locks it either way.

**Stage B (approved with gates): "Peak-day evidence" section on each public phrase page.**
1. Peak = the **post-epoch** peak (P1 lands first; sequencing is P0-A → P0-B → P1 → P2).
2. A new small derived evidence slice, built deterministically during the derived build (never
   at render): for each phrase in the public index, on its peak day, from normalized **Lane-1**
   statements: member name, party-state, date, source URL. **No statement or quote text in the
   slice** — receipts are identity+source only, which keeps the speaker-attribution and
   copyright surface at zero. Wayback links synthesized at render via the existing
   `_wayback_url()` — no stored archive URLs, no network at build or render.
3. Counting: units via the existing `_unit_key` machinery — a joint family is one unit;
   grounding via the same verbatim containment the verifier uses (the receipt's statement must
   contain the exact phrase). Numerator and caucus denominator use the same denominator source
   the party-columns view uses; identical rules both parties.
4. Quorum-or-silence: fewer than 3 groundable distinct units → **no evidentiary section for
   that phrase, log the omission**; never borrow from another day/phrase, never infer.
   Bounded visible sample with an honest "showing N of M".
5. Privacy: `privacy.is_suppressed` runs before the slice is written and before render;
   a suppressed phrase gets no slice entry and no page (existing behavior preserved).
6. **Cost gate (measured, not guessed):** incremental on-disk cache keyed by
   (slug, peak-day, source fingerprint). Steady-state added time per cron ≤ 60 s; one-time
   bootstrap ≤ ~15 min on the long RUN A path. Measure and report both. **If any Stage B gate
   (cost, grounding, complexity) cannot be met, ship Stage A alone and return DEFER for
   Stage B with the measurements** — do not improvise.
7. Tests: the six enumerated in the request (quorum + exact grounding; joint=one unit; valid
   HTTP(S) URLs; suppressed phrase → no page/slice; removed source → removed receipt;
   copy/behavior agreement).

## 5. P3 — page-specific share cards: DEFER

Grounds, from evidence: Pillow is absent from the stdlib-only CI (a new dependency on the live
daily path), and per-page PNGs multiply the committed `site/public` (~5.5 MB today) with
re-churning binaries on a public repo. The requester's own rule ("material dependency or
reliability expansion → DEFER") applies. The generic `og.png` stands. Revisit as a designed
feature after the 08-03 window, possibly with the Archive flip.

---

## 6. Standing constraints (all of the requester's, plus)

- Interpreter: `C:\ProgramData\miniconda3\python.exe` (bare `python` is a 0-byte stub on this
  box). Test floor: all 435 existing + new, zero failures.
- Start: `git fetch origin && git rebase origin/main` (this tree is post-rewrite; safe).
  **Never touch, rebase, or push branch `wip/nomenclature`** (contaminated pre-rewrite local
  history). Never `git add -A`.
- **Commit code, tests, and the docs in scope ONLY.** After local validation builds, revert
  generated trees: `git checkout -- site/public data/derived` (wherever dirtied). The cloud
  cron is the sole author of generated public surfaces; a locally rebuilt site commits stale
  state under false provenance. Local `data/state` ends ~2026-07-09 — expect stale local data;
  tests use fixtures.
- Four separate commits, in order: P0-A, P0-B, P1, P2. Evidence table maps each defect →
  failing-then-passing test → files → observed result. Working tree at end: only the commits
  plus the pre-existing untracked `AGENTS.md`.
- Never run `pipeline/post_bluesky.py`; never dispatch workflows; never push; never flip
  FEATURES or `POSTING_ENABLED`; no prompt/threshold/schema changes; no new LLM calls or
  recurring costs; no weakening of privacy, citation, immutability, atomicity, or
  failure-visibility machinery.

## 7. Release protocol (Michael)

1. Review the evidence table; spot-check the P0-B and P1 kill tests.
2. Push only in a clean cron window: `gh run list` shows nothing queued or in flight, and not
   within ~30 min before 09:30/11:30/19:30/21:30Z (scheduler drift runs late, so check the
   list, not the clock). **Never dispatch a run to "test" the change** — a dispatched run can
   displace a pending scheduled one (S40).
3. The next scheduled assemble is the live exercise of P0-B. Read its log (Art. XVI): green,
   two renders, and the committed `posts.html` carrying that same run's thread.
4. Post-push, read-only live verification is authorized: fetch the live pages, re-run the
   stale-phrase scan against production HTML, confirm search-index rows are all post-epoch.
   Nothing else (no dispatch, no posting, no flips).
