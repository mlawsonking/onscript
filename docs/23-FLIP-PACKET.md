# 23 — THE FLIP PACKET

## DRAFT — Michael to ratify

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
| **#160** | Rule on `data/derived` git history before S3 (does the rewritten history + purge satisfy Art. XIII for a public repo?) | The literal-name purge is **DONE** (Session 17 `git filter-repo`, 0 occurrences remain, HEAD tree byte-identical). What remains is your *ruling* that this is sufficient, plus residual #166 below. | Rule. See §1.0-detail. |
| **#166** | GitHub server-side purge of unreachable pre-rewrite objects | Open. Old SHAs cited in the public BUILDLOG would be fetchable pointers to name-bearing pre-rewrite blobs until GitHub GCs them. | Before public: either a GitHub-support purge request **or** delete-and-recreate the repo. |

**#1.0-detail — the privacy-history situation, stated honestly (evidence: `pipeline/privacy.py`,
BUILDLOG Sessions 12/17 lines 1584–1599, docs/16 §9 ruling 1):**

- **Display suppression is LIVE.** The Article XIII gate (`privacy.py`, HMAC-salted, fail-closed
  canary) runs on every build/assemble/post/chapter/duet path. The two apparent private-citizen names
  (#145) no longer render on the site. **This is done; the #145 bus task is stale-open** (see §5).
- **The salt is set** (#159, Session 17, canary-verified). **#159 is done; stale-open** (see §5).
- **Git history is rewritten** — the two literal name forms are gone from all 164 commits' blobs.
- **What is genuinely still open and gates public:** (a) #166's server-side object purge; (b) #160's
  formal ruling that the above is enough. These are real pre-public acts, not paperwork.
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
  work is tracked by #160/#166 (Tier 1). #145 as titled is done.
- **#159** ("Set `PRIVACY_SALT` before the gate commit is pushed") — **the salt is set**, canary-verified
  (Session 17). Done.

Leave #160, #166, #110, #105, #131, #132, #133, #158 open — those are real.

---

## §6 · THE RECOMMENDATION, IN ONE BREATH

Close #129 and #110. Clear #160/#166. Set real passwords, flip `POSTING_ENABLED`, take the repo public,
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
