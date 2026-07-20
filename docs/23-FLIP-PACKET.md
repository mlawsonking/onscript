# 23 — THE FLIP PACKET

## RATIFIED 2026-07-19 (Michael in-session; remaining decisions delegated to and made by Fable — see §7, which supersedes the recommendations above where they differ)

**What this is.** Every reserved decision that has piled up across Sessions 12–24, in one place, so you
can launch without spelunking canon. Opus drafted it; **you rule** (docs/21 §2 — the drafter changed,
the seat didn't). Each item gives: what it is · current state · where the evidence lives · the options
with their costs · a recommendation. The recommendation is a draft, not a decision — nothing here is
self-authorized. Grouped into exactly three tiers so you can act on Tier 1 alone and ignore the rest
until you feel like it.

**The one fact that changed everything:** **§1.4.1 has PASSED.** `ops.unattended_streak('2026-07-19')`
returns `passes=True` — 3 consecutive clean **unattended** real runs (2026-07-16 / 07-17 / 07-18),
including a weekend day, each `degraded=False final=True`, read from the record per Art. XVI (never run
status). This is the S2→S3 readiness gate the entire streak machine existed to clear. The instrument is
proven. The constraint is no longer build — it is this list.

---

## The 60-second version

- **Launching needs only Tier 1.** Tier 1 is: close your two dark-week gates (#129 receipts audit,
  #110 attorney), clear the pre-public privacy-history residuals (#160 / #166), then the four
  mechanical acts — **real Bluesky passwords → flip `POSTING_ENABLED` → repo public → announce.**
- **What Tier 1 alone ships:** the site exactly as it looks today at
  [onscript.news](https://onscript.news) (live, auto-deploying, real Sonnet voice at ~$0.006/day),
  plus the two composite accounts beginning to post. Nothing about the site's *content* changes at
  launch. That is deliberate.
- **Nothing in Tier 2 or Tier 3 needs deciding on launch day.** Every feature flip is an independent
  one-commit release you can schedule as a content moment (docs/20); every publication act is
  calendar-paced. My standing recommendation (Fable's steer, yours to override): **launch MINIMAL** —
  Tier 1 plus at most `party_columns` (an Article IV correctness fix) and, if you resolve its three
  riders, `nomenclature_tags`. Hold the other seven flags for the drip calendar.
- **One tiny thing needs a one-line answer before I can run a finding:** S5.2's floor (§4). It is the
  only measurement blocked on you.

---

## §1 · TIER 1 — LAUNCH ACTS (blocking, ordered)

These gate the launch. They are ordered; the pre-flip gates (§1.0) clear before the mechanical
sequence (§1.1) reaches "repo public."

### 1.0 Pre-flip gates — clear these before the repo goes public

| # | Item | State | Your act |
|---|---|---|---|
| **#129** | Hand-audit 5 receipts/day during the dark week (ends **2026-07-20**) | In progress — dark week nearly over; the site has run the live Sonnet voice since 07-13, verifier-clean | Finish the audit; it's your go/no-go on the voice. **Status report, not my decision.** |
| **#110 / #105** | Attorney review of the neutrality design + operator-protection bundle | Open on the bus; not yet reported done | Complete or explicitly waive before public. **Status report.** |
| **#160 + #161** | Rule on git history before S3 — the two private-citizen names were in tracked `data/derived/*.json` history. **#161 explicitly BLOCKS the public flip** (Art. XIII, unamendable). Near-duplicate tasks; same concern. | The literal-name purge is **DONE** (Session 17 `git filter-repo` over all 164 commits, 0 occurrences remain incl. the derived JSON these tasks name, HEAD tree byte-identical). What remains is your *ruling* that this is sufficient. | Verify + rule (and consolidate #160/#161). See §1.0-detail. |
| GitHub server-side purge (BUILDLOG "#166" residual — **not a numbered bus task**) | Unreachable pre-rewrite objects stay fetchable by old SHA until GitHub GCs; old SHAs are cited in the public BUILDLOG. | Before public: either a GitHub-support purge request **or** delete-and-recreate the repo. |

**#1.0-detail — the privacy-history situation, stated honestly (evidence: `pipeline/privacy.py`,
BUILDLOG Sessions 12/17 lines 1584–1599, docs/16 §9 ruling 1):**

- **Display suppression is LIVE.** The Article XIII gate (`privacy.py`, HMAC-salted, fail-closed
  canary) runs on every build/assemble/post/chapter/duet path. The two apparent private-citizen names
  (#145) no longer render on the site. **This is done; the #145 bus task is stale-open** (see §5).
- **The salt is set** (#159, Session 17, canary-verified). **#159 is done; stale-open** (see §5).
- **Git history is rewritten** — the Session-17 `git filter-repo --replace-text` purged **both literal
  name forms from ALL blob history** (the 52 name-bearing blobs incl. the `data/derived/days/*.json` +
  16 `phrases/*.json` that **#160 and #161** name; 0 occurrences verified post-rewrite, HEAD tree
  byte-identical). So the literal concern behind #160/#161 is **addressed**, and both are open pending
  only your confirmation it is sufficient. **(#160 and #161 are near-duplicate tasks — same derived-history
  concern; #161 is the one that explicitly BLOCKS the public flip. Consolidate at will.)**
- **What is genuinely still open and gates public:** (a) the **GitHub server-side object purge** — old
  SHAs cited in the public BUILDLOG stay fetchable pointers to pre-rewrite name-bearing blobs until
  GitHub GCs (a support-purge request **or** delete-and-recreate the repo); this is the BUILDLOG "#166"
  residual, **not a numbered bus task**. (b) your **formal ruling** (#160/#161) that the rewrite + purge
  is enough. Real pre-public acts, not paperwork.
- **The raw-mirror tension (attorney track):** the release-asset raw mirror contains 11 member
  statements that *mention* the names — the members' own published `.gov` speech. Article XIII
  (privacy floor) and Article VI (raw is immutable/rebuildable) pull opposite ways. Queued for the
  attorney hour (#110); leave raw untouched until ruled.

### 1.1 The mechanical launch sequence (gameplan §9)

Ordered; do them in this order.

1. **#131 — Replace the placeholder AT-Proto app passwords with real ones.** State: the
   `BSKY_*_PASSWORD` secrets are single-space placeholders (a truthy "belt"; the real gate is
   `POSTING_ENABLED`). The live-primitive smoke test already ran green (Session 8d, 13/13). Your act:
   set real app passwords for `blue.onscript.news` and `red.onscript.news` in Actions secrets.
2. **Flip `POSTING_ENABLED`** (Actions repo *variable*, not a secret — you flip it in the UI). This is
   the switch that turns the first brand post from a cron accident into a deliberate act. Kill-tested:
   no path posts while it is off, regardless of creds. Once on, the composites begin posting the daily
   line. The repo can still be private at this step.
3. **Make the repo public** — only after §1.0's #160/#166 clear. Unlocks free unlimited Actions +
   the transparency posture (public prompts, public code, symmetric instrument on display).
4. **#132 — Announce.** The origin-story teaser post from the `@onscript.news` house account (docs/20
   Aug row). This is the launch.

### 1.2 The five docs/16 §9 rulings — disposition (which gate LAUNCH vs a FEATURE flip)

The brief asked me to mark each. **Verdict: four of five gate a feature flip, not the launch.** Only
the first has a live instance, and that instance is already handled by §1.0.

| §9 | Ruling | Gates | Disposition |
|---|---|---|---|
| **1** | Article XIII / private-citizen names render as top phrases | **LAUNCH** (live) | Already handled: display-suppression is live (§1.0). The residual is #160/#166, in Tier 1 above. No new decision. |
| **2** | The ACA decision — `the affordable care act` scores TAG under the cumulative index, 0.000 under 119-only | `nomenclature_tags` flip | **Tier 2.** Only bites when tagging is live. Must be resolved *visibly in `verdicts-119.json`* before that flip. |
| **3** | The rank-and-truncate skew (#146) — pooled table is 87–100% D | `party_columns` flip | **Tier 2.** The fix IS the `party_columns` feature, built dark. Flipping it is the ruling. |
| **4** | The quiet-day floor — after tagging, quiet days lead with generic fragments | `nomenclature_tags` flip (editorial) | **Tier 2.** An editorial rider on the nomenclature flip; interacts with the daily-always cadence (§13). |
| **5** | Scope honesty — the defensible claim is "the top stops being bill titles on 4/7 days," not "the table is good" | `nomenclature_tags` flip (framing) | **Tier 2.** Sets the framing bar for the nomenclature release, not the launch. |

### 1.3 Not decisions — status reports you owe yourself

- **#129** closes the dark week 2026-07-20; it is your evidence the voice is trustworthy.
- **#110** is your legal comfort before going public.
Neither is something I can or should decide. I'm surfacing them so they don't get lost behind the
mechanical steps.

---

## §2 · TIER 2 — FEATURE FLIPS (each an independent one-commit release; NONE launch-blocking)

Every flag below is **built, verified, and dark** — `flag OFF ⇒ zero public bytes change`, enforced by
locked tests. Flipping any one is a single commit (Vercel auto-deploys). None of them needs to happen
at launch, and a dozen simultaneous flips would waste a dozen release posts and multiply your day-one
review surface. **Standing recommendation: launch MINIMAL** — flip `party_columns` (correctness), flip
`owners_brief` whenever (it's private), and schedule the rest as docs/20 content moments.

| Flag | Feature | What flipping does | Public? | Reserved knobs / riders | Rec |
|---|---|---|---|---|---|
| `party_columns` | R3 / #146 | Day table → per-party columns, each party its own top-k with N-of-caucus denominators. Kills the 87–100% D pooled skew (an Article IV artifact). | Yes | None. `SYNC_MIN` untouched; the fix is in the VIEW, not the threshold. | **FLIP at launch** |
| `owners_brief` | 1.8 / #158 | Monday health digest (5 numbers) to your ntfy topic. | **No** — private ops only | None | **FLIP anytime** (private; ~zero risk) |
| `nomenclature_tags` | docs/16 / 19 | Tags bill-title spans at display + pre-distill (so the Sonnet voice can't launder a bill title). `nomenclature_rate` is *already* measured in the nightly audit (unconditional). | Yes | **Carries §9-2 (ACA), §9-4 (quiet-day floor), §9-5 (framing).** Resolve those three to flip. | FLIP at/near launch **iff** the 3 riders are resolved; else schedule (Sep) |
| `authors_vessels` | 1.3 origination | SPAN-gated "first said by" origination claims on the phrase page (a bill title gets no authorship claim — kills the "Chip Roy authored the SAVE Act" defect). | Yes | The flip; the origination-page framing. | Schedule (docs/20 Sep) |
| `concordance` | 1.4 The Concordance | Per-member on-script index — a within-party-ranked reference table with denominators + heavy no-motive caveats. | Yes | Flip; `CONCORDANCE_PEAK_FLOOR`=15; `CONCORDANCE_MIN_STATEMENTS`=10; 2 flagged metric defs (either-party sync; any-day count); **leaderboard-vs-reference framing** (a "most on-script member" headline is a publication act). | Schedule (docs/20 Sep) |
| `awards` | 1.5 The Unison + The Void | Weekly symmetric awards — The Unison (each party's largest single-day office-share phrase over 7d) + The Void (loudest silence, from the absence map). Both phrase/topic-level, never member-level. | Yes | Flip; `UNISON_MIN_ACTIVE`=20; `UNISON_WINDOW_DAYS`=7; `UNISON_TOP_N`=5; `VOID_TOP_N`=3; **the thin-day framing question**; **Void-before-absence-map** (The Void degrades to UNAVAILABLE until `silence_board` is live). | Schedule (docs/20; after `silence_board` for the Void) |
| `archive` | 1.1 The Archive | Era/month chapter pages over the 25-year corpus (verifier-gated). | Yes | Flip. | Schedule (docs/20 Aug/Sep) |
| `silence_board` | 1.2 Silence Detector | The absence map + "Shouting Into the Void" (GDELT baseline; a gap is never a silence). Also the data source The Void (`awards`) needs. | Yes | Flip. | Schedule (docs/20 Aug/Sep); precedes `awards`' Void |
| `duet` + `phrase_search` | 1.7 | The Duet side-by-side view + client-side phrase search. | Yes | Flip. | Schedule (docs/20) |

**Not in this table (nothing to decide yet):** `floor` (1.6 — needs render + coverage metric, not built
for release), `credit_claim`, `memo_cadence_flag` (1.10), and every v3 flag (`memory_hole`,
`off_script_alerts`, `upstream_graph`, `bill_brand`, `public_api`, `eval_table`). These are future
build work, not reserved flips.

---

## §3 · TIER 3 — PUBLICATION ACTS (post-launch, calendar-paced per docs/20)

These are editorial acts — drafting and publishing finding cards/essays under your byline
(operator-is-not-the-instrument: the voice is yours). None is a launch-day act; all are paced by the
drip calendar and locked before the mid-October freeze.

| Piece | Card | When (docs/20) | State / rider |
|---|---|---|---|
| **P1 — The Self-Audit** | S1.9 (twice-validated) | Aug (launch essay) | CONFIRMED; rider passed (survives tag-stripping). The origin-story replication. |
| **P2 — The Boogeyman** | S2.9 (twice-confirmed) | Aug | CONFIRMED; symmetric, timeless, safe. |
| **P4 — The Great Intensification** | S1.1′ / S1.3′ | Sep | **#174 conditions all met** (two-panel per-lane framing; density caveat; docs/19 rider passed and *sharpened*; correlation labels). **Precondition: the fold-vs-isolate lane ruling (§3.1).** This is a REFUTED→CONFIRMED movement — your editorial/neutrality act, using the Intensification template. |
| **P3, P5, P6 …** | S4.4, S1.10, S1.6 nulls/artifacts | Sep–Oct | Publish as-is; adjudicated nulls need no re-registration. |

Drafts of P1 (S1.9) and P2 (S2.9) are being prepared **to `X:\onscript-data\drafts\`, never in-repo**
(the repo goes public; a pre-publication draft in git history could be quoted as "OnScript said" before
you ever edited it). They arrive as raw material for your editing, not as anything published.

### 3.1 A methodology ruling that gates any published lane number (fold-vs-isolate `page_html`)

Open ruling, flagged by the Session-16 L1 build, **never self-authorized** (BUILDLOG:1512):
`page_html` (2,839 records, the most party-skewed lane) can be **folded** into `scraped` (same
instrument; the build's default — moves the same-era lane gap +5.67pt → +4.71pt) or **isolated** as a
third lane (makes the post-2021 corpus permanently "mixed"). The code supports both
(`provenance.lane_of(by="instrument"|"source")`); the ruling picks *which number publishes*, not the
architecture. **This must be ruled before P4 (or any lane number) is published — a Tier-3
precondition, not a launch blocker.** My recommendation: **fold** (it is the same collection instrument,
merely date-parsed from the page body; isolating it publishes a permanent "mixed" asterisk on every
post-2021 comparison for a 2,839-record lane).

---

## §4 · A MEASUREMENT PRE-REGISTRATION AWAITING YOUR ONE-LINE CONFIRM — S5.2's floor

This is the only measurement blocked on you. S5.2 (The Concern Conversion Rate — "X% of congressional
concern is never followed by a bill within 180 days") has BILLSTATUS sponsorship data local and keyless,
but **its floor was never pre-registered** (docs/13's acknowledged p-hacking hole; docs/12:457 — "`≥Floor
per cell` is not a registration"). Per docs/12's discipline, floors are fixed as numerals **before**
touching confirmatory data. I did not measure and will not until you confirm.

**Draft pre-registration (confirm, amend, or reject):**

1. **Minimum cell size = 300 expressed-concern statements per reported cell** (a cell = party, or
   party × era-half). *Power justification:* the headline is a binomial proportion; at the
   least-favorable rate p=0.5, n=300 gives a 95% CI half-width of ±5.7pp, and at the folk-theory-likely
   p≈0.25, ±4.9pp. Cells below 300 are pooled or reported "insufficient," never as a headline.
2. **Comparative-claim gate:** a party-difference claim requires **both** party cells ≥300 **and** the
   gap to exceed the summed CI half-widths (≈8pp at p=0.5). Otherwise only the pooled rate publishes.
3. **Companion registrations that must also freeze before measuring** (flagging, not deciding — these
   are the real p-hacking surface, not just the cell size): the concern-detector lexicon; the
   180-day window (already in the hypothesis — keep); the on-topic match rule (token/topic overlap
   between the concern statement and the sponsored bill). I will draft these as a numeral/lexicon
   registration in the ledger for your confirm in the same pass — S5.2 does not run until all four are
   frozen.

*One line from you — "confirm 300 / amend to N / reject" — unblocks it. It is docs/20 Q1-2027 upside,
not launch-load.*

---

## §5 · STALE-BUS CLEANUP (candidates for you to close — I did not touch them)

The bus carries tasks whose underlying work is verifiably complete (the NOW.md notes the bus has drifted
noisy). I'm surfacing them for you to close; I did not close them myself because they sit on the
privacy floor and closing is your call:

- **#145** ("URGENT: private-citizen names render on the LIVE site") — **the display suppression is
  live** (`privacy.py`, deployed Session 12/17). The names no longer render. The *remaining* privacy
  work is tracked by #160/#161 (Tier 1). #145 as titled is done.
- **#159** ("Set `PRIVACY_SALT` before the gate commit is pushed") — **the salt is set**, canary-verified
  (Session 17). Done.

Leave #160, #161, #110, #105, #131, #132, #133, #158 open — those are real.

**⚠ A tooling discrepancy found while filing this packet (worth a fix):** `vtask list` and the
`vtask add` fuzzy-dedupe both call `GET /projects/11/tasks?per_page=200`, but Vikunja caps `per_page`
at **50** and vtask requests no explicit sort — so on a project with >50 total tasks (polispeak has 55),
both see only page 1 (the *oldest* 50) and silently miss the newest tasks. Consequences this session:
(a) the session-start `vtask list` showed **10 open tasks when there are 13** — it hid **#161** (a
launch-blocking privacy task) and #176/#177; (b) the dedupe couldn't see #176 and so did **not** refuse
a re-file, creating a true duplicate #178 (I closed it). The bus's whole anti-duplicate guarantee is
defeated by this. Fix is small (paginate the read / add `sort_by=id&order_by=desc`) in
`~/.claude/vtask/vtask.py:116`.

---

## §6 · THE RECOMMENDATION, IN ONE BREATH

Close #129 and #110. Clear #160/#161 + the GitHub server-side purge. Set real passwords, flip `POSTING_ENABLED`, take the repo public,
announce. Flip `party_columns` (it's a correctness fix) and `owners_brief` (it's private) in the same
window if you like — but you don't have to. Everything else waits for the calendar. Resolve
`nomenclature_tags`' three riders when you want that release; rule fold-vs-isolate before the September
Intensification card; confirm S5.2's floor whenever. **Nothing on this page except Tier 1 stands
between the instrument and November.**

---

*Filed by Opus (Session 26), 2026-07-19. Evidence pointers: `ops.unattended_streak`; `pipeline/config.py`
FEATURES (l.183–204) + `posting_enabled` (l.219); `pipeline/privacy.py`; docs/16 §9; docs/19; docs/20;
docs/21 §2; BUILDLOG Sessions 12/16/17/21/22/23/24. This document decides nothing — it presents the
reserved list for your ruling.*

---

## §7 · RATIFICATION + THE RELEASE SCHEDULE (2026-07-19; binding)

### 7.1 Michael's gate rulings (in-session, recorded verbatim in effect)

1. **#129 receipts hand-audit — DONE.** (Task closed.)
2. **#110/#105 attorney review — EXPLICITLY WAIVED for launch.** Stays open on the bus as a
   post-launch act at Michael's leisure; no longer gates anything.
3. **#160/#161 privacy-history ruling — the rewrite IS SUFFICIENT.** (Both tasks closed.)
4. **GitHub server-side purge — WAIVED pre-public.** Michael will contact GitHub support later;
   the residual risk (a referenced name in a verbatim member quote, reachable only by pre-rewrite
   SHA until GC) is accepted with eyes open. Not a launch gate.

**All Tier-1 gates are therefore CLEAR. The only remaining human act before launch is #131.**

### 7.2 Delegated decisions (Fable, under Michael's in-session delegation; revocable by Michael at any time)

1. **`nomenclature_tags` riders — all three resolved; the flag is schedulable.**
   §9-2 (ACA): **tag by the CUMULATIVE index.** A tag is annotation, never deletion — "the
   affordable care act" IS an official short title and the chip cites the official record. The rule
   is party-blind (span containment against BILLSTATUS); that D-vocabulary tags where R's
   "obamacare" does not is an asymmetric *finding* from a symmetric *instrument*, which is exactly
   the distinction the constitution protects. Recorded visibly in `verdicts-119.json` before the flip.
   §9-4 (quiet days): **no new floor.** Daily-always is a §13 locked decision; a quiet day rendering
   generic overlap under the existing descriptive banner is honest. Any future floor must be
   measured in (the UNISON_MIN_ACTIVE pattern), never guessed in.
   §9-5 (framing): the release copy claims exactly what was measured — "the top phrases stop being
   bill titles on 4 of 7 days" — and nothing broader.
2. **Concordance:** `PEAK_FLOOR=15` and `MIN_STATEMENTS=10` ratified (both measured, not guessed).
   Both flagged metric definitions stay **as built, disclosed in Methodology** (either-party sync;
   any-day counting); own-party-only is a possible future refinement that must be measured and
   disclosed, never silently changed. **Permanent framing: a reference table.** Any "most on-script
   member" headline is a Tier-3 publication act, forever.
3. **Awards:** `UNISON_MIN_ACTIVE=20`, `WINDOW_DAYS=7`, `TOP_N=5`, `VOID_TOP_N=3` ratified as
   measured. Thin/quiet-week handling as built (floor + banner, no content blocklist — the docs/16
   anti-pattern stays dead). **The Void ships only after `silence_board` is live** (sequenced below).
4. **Fold-vs-isolate (§3.1): FOLD ratified.** `page_html` is the same collection instrument, merely
   date-parsed from the body. The docs/17 §1 rule stands: where folded-vs-strict moves a published
   headline by >0.5pt of D-share, report both. **P4 (the Intensification) is now fully unblocked.**
5. **S5.2: floor CONFIRMED at 300/cell with the comparative-claim gate as drafted (§4).** The three
   companion registrations (concern lexicon · 180-day window · on-topic match rule) freeze as a
   committed ledger registration BEFORE any measurement run; the lexicon is committed to the repo;
   no post-hoc edits. S5.2 may then run in any worker session.
6. **Stale bus:** #129/#145/#159/#160/#161 closed. The `vtask` pagination bug (§5 ⚠) is queued as a
   worker fix (paginate + sort in `~/.claude/vtask/vtask.py`) — it defeats the dedupe guarantee and
   hid a launch-blocking task; fix before relying on the bus again.

### 7.3 THE RELEASE SCHEDULE (standing authorization — bounded, conditional, revocable)

**The health gate (every scheduled flip is conditional on ALL of):** the Monday owners-brief digest
green · no open P0 · the prior week's nightly symmetry audits clean · site current (yesterday's day
published, `degraded=False`). **Any failure pauses the whole schedule and escalates to Michael via
ntfy — a paused schedule is the system working.** Michael retains a standing veto ("pause the
schedule" in any session stops everything). Flips execute Monday afternoons, AFTER the digest.

| Date | Act | Owner |
|---|---|---|
| **Mon 07-20** | **LAUNCH.** Michael: set the two app passwords (#131) + one reply approving/editing the announce text (drafted to `X:\onscript-data\drafts\`). Worker then executes, in order: `POSTING_ENABLED` on → repo public → announce (#132). Same window: flip `party_columns` (correctness) + `owners_brief` (private). | Michael (2 acts) → worker |
| Mon 07-27 | Flip `nomenclature_tags` (riders resolved §7.2.1; ACA visible in verdicts; release copy per §9-5 bar) | Worker |
| Mon 08-03 | Flip `archive` (1.1) — the 25-year chapters, the biggest single content moment on the shelf | Worker |
| ~Wed 08-05 | **P1: the Self-Audit essay** (S1.9) publishes | Michael (editorial) |
| Mon 08-10 | Flip `silence_board` (1.2) — landing on the original v2 target date | Worker |
| Mon 08-17 | Flip `duet` + `phrase_search` (1.7) | Worker |
| ~Wed 08-19 | **P2: the Boogeyman** (S2.9) publishes | Michael (editorial) |
| Mon 08-24 | Flip `awards` (1.5) — The Void now live-fed by the absence map | Worker |
| Mon 08-31 | Flip `authors_vessels` (1.3). **All Sep–Oct pieces locked today** (docs/20 freeze discipline) | Worker + Michael (lock) |
| Mon 09-07 | Flip `concordance` (1.4) — deliberately last: member-level, now with 7 weeks of public audit history behind it | Worker |
| Sep–Oct | P3/P4/P5/P6 per docs/20 (P4 unblocked by §7.2.4) | Michael (editorial) |
| **~Mon 10-12** | **FREEZE** — no flips, no new backward-looking claims until post-midterms (docs/20 §1) | — |
| Dec | Resume: cycle retrospective, the Seam methods essay, graveyard annual | Michael (editorial) |

**Worker-session immediate duties (before Mon):** draft the announce text + P1/P2 raw drafts to
`X:\onscript-data\drafts\` (never in-repo) · fix the vtask pagination bug · prepare each scheduled
flip as a ready one-commit change · verify the launch sequence end-to-end in dry-run one final time ·
**(added 07-19) the day-navigation fix**: the day pages are permanent but UNREACHABLE — index.html
links to zero of them; add a "← Yesterday" link on the homepage day panel + a `/day/` date-archive
index in the nav (navigation to already-public pages: launch polish, not a flagged feature; locked
test that every published day JSON has a listed page) · **(added 07-19) the announce path**: Michael
has set `BSKY_BRAND_HANDLE` (`onscript.news`) + `BSKY_BRAND_PASSWORD` — wire the house-account
announce as a **manual-dispatch one-off** using the Session-8d smoke-tested AT-Proto primitives,
gated on the approved text verbatim (fallback stays: Michael pastes it in the app; either path is
fine, neither is a cron).

### 7.4 Michael's complete remaining list

1. ~~**#131** — create the two real app passwords, set the Actions secrets.~~ **DONE 2026-07-19**
   (`BSKY_BLUE_PASSWORD`, `BSKY_RED_PASSWORD` set; plus `BSKY_BRAND_HANDLE`/`BSKY_BRAND_PASSWORD`
   for the house account — announce wiring added to the worker duties above). `POSTING_ENABLED`
   remains OFF, which is the designed pre-go state: real creds, kill-tested gate holding.
2. **One reply** — "go" (approving or editing the announce text once it lands in
   `X:\onscript-data\drafts\`). This is now the ONLY remaining human act before launch.

Then: the 2-minute Monday digest glance, editorial acts per docs/20 at your leisure, and the standing
veto. Everything else is scheduled, gated, and executed by the worker under this authorization.

### 7.5 · The Session-28 findings adjudicated (Fable, 2026-07-20, under the §7.2 delegation as re-affirmed in-session; revocable)

Three rulings on the pre-launch audit's findings (BUILDLOG Session 28). The delegation covers these
rulings; it does **NOT** consume §7.4.2 — the announce "go" stays Michael's one reply, because the
first public words get a human eye **by design, not by oversight**.

**R-A · The ACA rider (#179): the operative rule STANDS, on corrected facts; the 07-27 flip is
re-authorized.** §7.2.1's factual prediction was inverted by measurement: at the committed
cumulative index and the disclosed 0.8 threshold, **neither party's ordinary framing tags**
(`affordable care act` 0.0049 over 1,820 docs · `the affordable care act` 0.0008 · `obamacare` no
row), and the only ACA-family phrase that tags is **`the unaffordable care act`** (ratio 1.0, cite
hr6300 — an actual introduced bill bearing that title). RULED: **this is the instrument working,
not a defect.** docs/16's law is that nomenclature is a property of the OCCURRENCE; the corpus
says members use "the affordable care act" as *message* 99.5% of the time, so it must not tag —
and every measured use of "the unaffordable care act" references an official title, so it must.
The output asymmetry traces to an asymmetry in the parties' own conduct: one caucus wrote its
counter-brand into a bill title; the other's counter-brand ("the big ugly bill", 0.000) never
became one. One rule, both parties → an asymmetric **finding** from a symmetric **instrument** —
the exact category Art. IV protects, and honestly a nicer demonstration of the principle than the
imaginary asymmetry the original rationale accepted. Riders: (1) **chip copy is
descriptive-citational only** — bill, congress, record link; never an evaluative label; (2) the
gated Methodology section explains **occurrence-not-phrase with the ACA family as the worked
example** — it is the best pedagogy on the shelf and the pre-answer to the first accusation
("why does the pun tag and 'obamacare' doesn't?"); (3) the §9-5 bar extends here: release copy
claims what was measured, never "D vocabulary tags." **#179 CLOSED by this ruling.**

**R-B · `silence_board` / the awards cascade: dates HOLD, behind a wiring deadline.** The board is
built and kill-tested but has no production caller; `derived/silence/` has never accumulated. A
build session wires it (skip-and-log; boards accumulate **DARK**) with a landing deadline of
**Mon 08-03** — one week of boards before the 08-10 flip, three before The Void. **Auto-slip
rule:** if boards are not accumulating in production by the 08-03 digest, the 08-10 flip slips
week-by-week until they are, and `awards` (08-24) **ships whole or slips with it** — The Void must
be live-fed at flip; honest-UNAVAILABLE is a *degradation* state, not a *launch* state (consistent
with §7.2.3). Opus work; no human errand.

**R-C · The `daily_lines` nulling is a P0 — the §7.3 health gate's first catch is us, before the
first flip. Launch proceeds Mon 07-20 BEHIND the repair, same day if it lands.** RUN A rewrote a
`final: True` day's JSON to `daily_lines: null` (0a66cea → day 07-18, −85 lines; likewise
`collect 07-14` → day 07-12, proven from file history: af36b2a carried 2 composites, 6459640
carries 0). **Evidence correction to the S28 table:** 07-09 was **never damaged** — no committed
version of its file ever carried `daily_lines` (verified across its entire history); it is an
honest phrases-only backfill day and gets **no repair** (Art. II: never fabricate a composite for
a day the voice never ran). INVARIANT to implement, with a locked test: **a day whose assemble
manifest is `final: True` is immutable to RUN A** — collect never rewrites a published day JSON;
the only write path to a final day is the documented `run_assemble --day` repair. Repairs =
exactly **{07-12, 07-18}**, via that path. **Never unlink a public day page** — the pages are the
permanent record; the guard prevents new orphans and the 07-18 repair restores that page's
coherence. Streak evidence unaffected (manifests untouched; `passes: True` re-verified at S28
close). A paused-then-cleared launch morning is the gate **working** — it goes in the methods
story (docs/20's December flagship can cite it: the health gate's first catch was ourselves).

**The corrected launch-morning order (one worker session, Mon 07-20):**
1. R-C guard + the two repairs; full suite green; site regenerated; `day/2026-07-18.html`
   coherent; homepage on the newest lined day.
2. Verify from the record (Art. XVI): the morning cloud commits are clean, and whether
   `concordance.json`/`awards.json` landed in production output (the S28 open check gating
   08-24/09-07 confidence).
3. Monday digest green (the first 15-min ritual).
4. On Michael's "go": `POSTING_ENABLED` on → repo public → announce (dispatch workflow, the
   RECOMMENDED 4-post text **verbatim**, confirm=POST) → flip `party_columns` + `owners_brief`.
5. Any failure at any step: ntfy, and launch slips to the next clean day. The gate working, not a
   crisis.

**The announce text: the RECOMMENDED 4-post thread is AFFIRMED as drafted** (every count measured
through the real builder; the 36 figure matches the page it links). Michael's entire remaining act
is one reply: **"go"** — or edits, which re-enter at step 4.

**AMENDMENT (Michael, in-session, 2026-07-20): LAUNCH DAY = TUESDAY 07-21.** An editorial timing
choice, not a gate pause: the announce lands on the **Monday 07-20 reading** (a full weekday page,
assembled Tue ~11:30Z) instead of Sunday's quiet one. Consequences:

- **Monday (worker session 1) = the repair day.** §7.5 steps 1–3 only: the R-C guard + repairs
  {07-12, 07-18} + suite + coherent site + the Art.-XVI record checks. **No launch acts.** The
  guard landing Monday now matters doubly: without it, a post-assemble collect could null the very
  Monday reading the launch is waiting for.
- **Tuesday (worker session 2) = the launch morning.** After the ~11:30Z assemble lands day 07-20
  and the homepage shows Monday's reading, verify it looks right — then, **on Michael's "go"**:
  `POSTING_ENABLED` on → repo public → announce (verbatim, confirm=POST) → flip `party_columns` +
  `owners_brief`. Failure handling unchanged: ntfy, slip day-by-day.
- The rest of the schedule is unmoved (07-27 `nomenclature_tags` onward; the Monday-flip rhythm
  resumes next week).
- **The "go" stays pending until Tuesday** — the point of waiting is that Michael sees the Monday
  page before the announce points the world at it. The RECOMMENDED text stands affirmed; edits
  re-enter at the announce step.

**AMENDMENT 2 (Fable, 2026-07-20, on Michael's launch-eve scope question): three additions, chosen
to fit "properly test and vet in one day" — and an explicit list of what stays dark.**

1. **`phrase_search` joins the launch window** (Tuesday, with `party_columns`/`owners_brief`). It is
   the direct answer to "not much navigability": 276 phrase pages exist and only the top-40 tables
   reach them. Built + locked-tested since S13; it is a UTILITY, not a content moment, so pulling it
   forward costs the drip almost nothing — **`duet` keeps 08-17 as that day's moment.** Monday duty:
   flip locally, render, click through, full suite, stage the one-commit flip.
2. **Link cards (og: meta) — the real "prep for Bluesky" item.** The site shell emits **zero**
   Open Graph tags (verified: no `og:` anywhere in `site.py` or the rendered pages), so the
   announce, every daily receipts link in every composite thread, and every share forever would
   unfurl as a bare imageless card. Monday duty: add `og:title`/`og:description`/`og:url` + a
   static `og:image` (the committed brand card, copied to `site/public/` so it actually serves;
   verify the deploy path), locked test that every page carries them. Site chrome, not a feature —
   ungated, same category as the day-nav fix.
3. **First-post mechanics (Tuesday brief fix).** As sequenced, Michael's "go" happens AFTER the
   ~11:30Z assemble — so with the flag flipping mid-morning, the composites' first threads would not
   post until the **21:30Z run (5:30pm ET)**: the announce would point at two composite accounts
   that stay silent all day. Fix, added to the Tuesday order: after go + flips, **re-dispatch
   `assemble.yml` with `day=2026-07-20`** (the documented repair path; posting is idempotent by
   manifest + deterministic rkey) so the first composite threads land in the same morning window as
   the announce. The 11:30Z run's dry-run log **is** the final preview of exactly those threads —
   the worker eyeballs it before the flip.

**Stays dark, deliberately:** `archive` holds for 08-03 — it is the biggest single content moment
on the shelf (the second attention spike, two weeks after launch-week decay) and the
deepest-scrutiny surface (25 years of historical claims) should not debut on the loudest day before
the daily instrument has public track record. `duet` 08-17 · `awards` 08-24 (silence-fed, R-B) ·
`authors_vessels` 08-31 · `concordance` 09-07 (member-level, wants audit history) ·
`nomenclature_tags` 07-27 (R-A) — all per schedule and riders. **No new code surfaces on launch
eve beyond the three above**; specifically, NO Bluesky embed/quote-post wiring — if the house
account should quote-post the composites' first threads, Michael does it **in the app** (a human
act, zero new code). If "bluesky quotes" meant verbatim member quotes inside the post threads:
post-launch enhancement — a new public surface needs its own verifier/privacy gating; the receipts
link carries the quotes today.

Monday worker prompt: **"read CLAUDE.md and docs/23 §7.5, run the Monday repair + launch-eve polish."**
Tuesday worker prompt: **"read CLAUDE.md and docs/23 §7.5, run the launch morning."**

**AMENDMENT 3 (Fable, 2026-07-20 afternoon — Sessions 30/30b adjudicated; THE FINAL TUESDAY ORDER).**
Both Monday worker sessions ran and their open points are ruled:

- **R-D · S30's repair deviation is RATIFIED.** Restoring {07-12, 07-18} from the exact published
  bytes instead of the §7.5-named `--day` re-assembly was correct three independent ways: the
  literal mechanism would have broken the streak evidence through launch morning (07-18 is the
  streak head), written "0 statements" fabrications from stale local state (Art. II), and
  restamped false provenance (`dry_run` → `sonnet_direct`). A repair that would have failed the
  launch gate it was sequenced in front of is not a repair. `repair_safe_manifest` is now the
  **standing repair semantics** (trigger-provenance preserved; `degraded` recomputed; a field the
  original never carried is dropped, never invented). **Never `--day` 07-12/07-18 — already
  repaired; it would regenerate, not restore.** S30b's corrections-log clobber fix (the tar
  extract was silently resetting the public error record 3→0 — on announce eve the site was
  denying its own corrections), the `DELIBERATELY_RELEASED` test mechanism (a release is a named
  reviewable act; an accidental flip still reddens), and the privacy-ruled og implementation are
  all ratified as built.
- **R-E · The 07-19 (Sunday) publishing policy.** S30b proved the natural cron cannot reach day
  07-20 while 07-19 sits non-final (oldest-first, returns on first non-final). Ruling:
  **daily-always is a §13 locked decision — a thin, honest Sunday page ("We released N statements
  today") beats a Wednesday force-finalize marked degraded.** So: if the 11:30Z scheduled pass has
  not already resolved 07-19, dispatch `assemble.yml -f day=2026-07-19` **iff its real count ≥ 1**
  (at 0 there is nothing to publish and the costless skip is honest), and **always dispatch
  `-f day=2026-07-20` LAST** so `assemble-latest` points the posting leg at the Monday reading.
- **R-F · The `phrase_search_index` non-dict guard is Tuesday's step 0, pre-authorized.** A known
  whole-build crash surface must not go live with its flag. Two lines mirroring the page loop's
  existing isinstance guard, plus a test — done and committed BEFORE the flip commit.
- **R-G · The posting path stays FROZEN through launch.** The S30b follow-ups
  (collision-recovery returns before replies → a truncated 1-post thread; `SITE`/`config.SITE_URL`
  dedup) are the **first post-launch fixes (Wed 07-22)**, not launch-eve edits to smoke-tested
  code. If the rare truncation fires on launch day, the remedy is manual: reply with the receipts
  link from the app.

**THE FINAL TUESDAY ORDER (one worker session, new chat, model = Opus):**
0. `gh run list` — never push while a cron is in flight (S30 standing rule). Then R-F (the
   search-index guard + test, committed).
1. Art. XVI record check: overnight commits clean · corrections count still 3 (the S30b fix held)
   · the immutability guard held (no day nulled) · 07-19's real count from the morning collect ·
   suite green.
2. Day publishing per R-E: 07-19 iff count ≥1, then **07-20 LAST**. Verify from the record that
   `assemble-latest` = 2026-07-20 and the homepage shows the Monday reading. Eyeball the dry-run
   thread print in the log — it is the final preview of the first real posts.
3. Health: digest green · no open P0 · site current.
4. **→ Michael's "go" ←** (the §7.4.2 reply, given to the worker session; standing veto intact).
5. Execute, in order: `POSTING_ENABLED` on → repo public → announce (`announce.yml` dispatch,
   approved text verbatim, `confirm=POST`) → the flip commit (`party_columns` + `owners_brief` +
   `phrase_search` = True, all three added to `DELIBERATELY_RELEASED` — per S30b this is exactly
   two lines) → push (step-0 check again) → re-dispatch `assemble.yml -f day=2026-07-20` so the
   composites' first threads post in the same morning window, linking a site with columns, search,
   and og cards live.
6. **Expected artifact, do not "fix":** the dispatch writes `unattended:False`, so
   `ops.unattended_streak` reads `passes:False` afterward. §1.4.1 already PASSED on the historical
   record (07-16/17/18, Art. XVI) — it gates on evidence already collected.
7. Verify live: both composite threads up · og cards unfurl on the real posts · phrase search
   works on the live site · corrections page still says 3. Michael's optional in-app acts: pin the
   announce; quote-post the composites' first threads from the house account.
8. Any failure at any step: ntfy, hold, slip to the next clean day.
