# 25: Documentation voice brief (binding)

Authority: Fable, Session 44, 2026-07-23. Requested by Michael after a read-only prose audit
of the tracked Markdown corpus. The audit's headline numbers were independently reproduced
before this ruling: 29 tracked files, 2,617 U+2014 characters, per-file counts matching.

Purpose: the documentation reads like model output. Michael has rejected that voice. This
brief authorizes an external worker (Codex) to rewrite the prose of every tracked Markdown
file into plain, natural project writing. The rewrite changes how things are said. It must
not change what is true, decided, required, or recorded. Michael retains review and release
authority. The audit counts are baseline measurements, not replacement instructions.

## 1. Rulings

### R-V1. Historical and append-only records: in-place normalization, approved once

Applies to docs/03-GAMEPLAN.md, docs/04-BUILDLOG.md, docs/13-SEARCH-LEDGER.md, and the
session history currently inside CLAUDE.md.

1. Git retains every original. The pre-rewrite text stays recoverable at the commit each
   normalization note cites.
2. Immutable content inside these records: verdict words and their qualifiers (CONFIRM,
   REFUTE, ARTIFACT, HELD, and similar), dates, quantities, thresholds, costs, commit SHAs,
   file paths, registration references, supersession chains, and the order of entries.
   The prose around them may be rewritten.
3. Each normalized historical record receives a short dated note at the top: prose
   normalized on this date under docs/25; findings, decisions, and chronology unchanged;
   original wording at commit `<pre-rewrite SHA>`. The note names the real SHA so a reader
   can diff rather than trust.
4. This ruling supersedes the docs/24 §1.6 exclusion of docs/03 and docs/04 for style only.
   It grants no authority to revise history, change a verdict, soften or harden an old
   claim, or update a stale statement to present knowledge. A passage that reads as wrong
   today keeps its recorded meaning; flag it in the evidence table instead of correcting it.
5. The registration files under data/reference/search/ are data, not documentation. They
   are untouched, as is every other non-Markdown file.
6. Phase-document ownership: docs/01, docs/03, and docs/05 are Fable phase documents, and
   the standing rule forbids other models from rewriting them. This brief is the Fable
   authorization for style-only editing of those files. Content ownership is unchanged.

### R-V2. The constitution (docs/06) gets the strictest treatment

Its wording is operative. Past rulings have turned on precise phrases in it.

1. Allowed: punctuation, sentence structure, removal of theatrics, sentence-case headings.
2. Required: article numbers and titles stay stable. Every invariant keeps its full
   operative content. Where a metaphor is a defined term of art, keep the term and state
   its meaning in plain language next to it.
3. Evidence: a per-article before-and-after table. Michael spot-checks this file directly.

### R-V3. CLAUDE.md restructure, approved

1. Split CLAUDE.md into: a project summary with constraints; the model-split workflow
   table; a consolidated standing-rules-and-traps section; a short current-status section;
   and a pointer to a new docs/26-SESSION-HISTORY.md that holds the dated session entries.
2. Before any session entry moves to the history file, extract every rule, trap, or lesson
   still in force and place it in the standing-rules section or in the canonical document
   it belongs to. The evidence must include a ledger mapping each extracted item from its
   old entry to its new home. Losing an operative fact is the failure mode of this stage.
   When in doubt, keep the fact.
3. Going forward, sessions append dated entries to docs/26 and keep the CLAUDE.md
   current-status section short. Both files record this contract. New entries follow the
   house style in section 3 of this brief.
4. docs/26 may be split into numbered parts if it grows too large for one file.

### R-V4. Vocabulary versus rhetoric

1. Terms anchored in code, configuration, schemas, tests, or product surfaces are project
   vocabulary. Examples: lane, seam, dead-man, skip-and-log, dark, flip, the streak,
   FEATURES flag names, Alexandria, Unison, Void, Concordance, Duet, Daily Lines, the
   graveyard shelf. Keep these terms. Define each one plainly at its first use in the
   document where it matters. Stop using them as decoration.
2. Rhetoric with no such anchor (armor, spine, sacred, doctrine, moat as flourish, war
   metaphors) is rewritten into specific language that says what the sentence means.
3. In prose, "kill test" becomes failure test, regression test, or mutation test, matching
   what the test does. Code identifiers and test function names are out of scope.

## 2. Scope

In scope, every tracked Markdown file: README.md; CLAUDE.md; every file matching
docs/*.md; pipeline/prompts/README.md; scripts/ops/history-rewrite/README.md;
site/brand/README.md. One new file is authorized: docs/26-SESSION-HISTORY.md (with
numbered splits if needed). Every tracked Markdown file must be examined; the evidence
includes a coverage checklist listing each file and its disposition.

Out of scope, protected:

1. AGENTS.md (untracked; Michael's local instruction file).
2. Every file under pipeline/prompts/ except its README.md. Prompt bytes are versioned
   runtime behavior; a style edit there is a product change and is refused.
3. Source code, workflows, tests (narrow carve-out below), data/, site/public/, and
   anything generated.

Test carve-out: where an existing test asserts specific prose wording inside an authorized
Markdown file, that test may be updated to assert the rewritten wording. Every such test
edit is listed in the evidence table with before and after assertions. No other test
changes.

## 3. House style (binding, including for this brief and all future documentation)

1. No em dashes (U+2014) in authored prose. U+2014 survives only inside protected verbatim
   quotations, code fences, and inline code, and each survivor is listed in the exception
   list with file, line, and reason.
2. Prefer periods and short declarative sentences. One main thought per sentence.
3. Use commas, colons, semicolons, and parentheses sparingly.
4. En dashes stay for numeric and date ranges.
5. Sentence case for headings.
6. All caps only for real acronyms, enum values, and literal status tokens.
7. Remove decorative emoji. A small legend of operational status markers may remain where
   a table or log genuinely uses them as tokens; define the legend once.
8. Bold marks short labels and scannable terms. Do not bold whole arguments or verdict
   sentences.
9. Replace dramatic metaphor with specific language (see R-V4).
10. Reduce "honest," "exactly," "literally," "structurally," "the real," "by construction,"
    and "load-bearing." Each remaining use must be doing work a plain word cannot.
11. Replace "kill test" per R-V4.3.
12. Avoid rhetorical contrasts ("X, not Y") and three-part crescendos as templates.
13. State facts without announcing their importance first.
14. No fake dialogue, anticipated objections, or defensive asides unless they document a
    real dispute that happened.
15. Use direct project language: requirement, evidence, decision, risk, core path,
    failure mode.
16. Keep paragraphs focused. Split long status entries into fields: outcome, evidence,
    decision, next action.
17. State each rationale once in its canonical document and link to it elsewhere. Remove
    duplicate explanations.
18. Keep model names where they record real phase ownership or history. Remove casual
    model self-reference that adds nothing operational.
19. Second person only in genuine runbooks. Role names elsewhere.
20. No slogan is protected by repetition. Preserve the meaning; rewrite the phrasing if it
    carries the cadence this brief removes.
21. Do not churn line endings or trailing whitespace beyond what the rewrite requires.

The target voice: a technically competent founder maintaining a serious project. It can
have personality. It does not perform.

## 4. Stages and commits

One commit per stage, four commits total. Each stage leaves every cross-reference
resolving and the test suite green. Any tracked Markdown file not named below lands in the
most similar stage; nothing is skipped.

1. Stage V1, operating surface: README.md; CLAUDE.md plus the docs/26 split (R-V3);
   docs/07; docs/20; docs/21; docs/23; docs/24.
2. Stage V2, canonical and governance: docs/01; docs/02; docs/03; docs/05; docs/06
   (R-V2); docs/11; docs/16.
3. Stage V3, research and history: docs/04; docs/08; docs/09; docs/10; docs/12; docs/13
   (R-V1); docs/14; docs/15; docs/17; docs/18; docs/19; docs/22.
4. Stage V4, subsystem files and consistency: pipeline/prompts/README.md;
   scripts/ops/history-rewrite/README.md; site/brand/README.md; a self-check of this
   brief; the corpus-wide final counts and consistency pass.

Sequencing: these commits sit on top of the current local stack (through `166b4de`). Do
not interleave them between existing commits. Push rules stay governed by docs/24 §7 and
§10: the stabilization pushes land first, and the voice commits push only after Michael
has reviewed the stages.

## 5. Validation gates (all required, per stage where applicable)

1. Before-and-after counts per file: U+2014, multiword all-caps runs, emoji, bold spans,
   lines over 240 characters, and the recurring lexicon from the audit ("this is,"
   "honest," "exactly," "the real," "spine," "by construction," "load-bearing," "the
   instrument," "kill test," "armor," "doctrine").
2. Zero U+2014 outside the exception list. The exception list enumerates every survivor.
3. Mechanical fact-preservation diff per file: extract dates, hex SHAs, numbers,
   percentages, dollar amounts, file paths, URLs, environment variables, flag names, and
   commands from the before and after text. The multisets must match. Any intentional
   difference is listed with a reason; the expected count of such differences is zero.
4. Every relative Markdown link and heading anchor resolves after each stage.
   Cross-document references to renamed headings update in the same commit.
5. Semantic evidence table per file: the decisions, requirements, and facts it carries,
   confirmed present after the rewrite. For docs/06, the R-V2 per-article table. For
   docs/13, a per-entry table of verdict, date, and supersession preservation. For
   CLAUDE.md, the R-V3 operative-facts ledger.
6. At least six representative before-and-after passages, drawn from the audit's named
   examples, demonstrating sentence-level rewriting rather than punctuation swaps.
7. Suite green at every stage via the house runner:
   `C:\ProgramData\miniconda3\python.exe tests\run_tests.py`. Floor: the suite count at
   execution time (477 at ruling time) plus any carve-out updates, zero failures.
8. `git diff --check` clean. No changes outside authorized files. No regenerated
   site/public or data/derived content. Tree clean except the untracked AGENTS.md.
   No push, no deployment, no workflow dispatch.

## 6. Release

Michael reviews stage by stage and holds release authority. Pushes follow the docs/24 §7
window rules. Nothing in this brief changes any runtime behavior, schedule, flag, or
public data path.

## Appendix A: U+2014 exceptions

The tracked Markdown corpus contains eleven U+2014 characters. Each one is protected by
section 3.1 because it appears in a code fence or inline code.

| File | Line | Occurrence | Reason |
|---|---:|---:|---|
| docs/03-GAMEPLAN.md | 211 | 1 | Code-fenced JSON schema comment. |
| docs/03-GAMEPLAN.md | 242 | 1 | Code-fenced manifest schema comment. |
| docs/04-BUILDLOG.md | 2498 | 1 | Code-fenced captured pipeline output. |
| docs/04-BUILDLOG.md | 2500 | 1 | First U+2014 in code-fenced captured pipeline output. |
| docs/04-BUILDLOG.md | 2500 | 2 | Second U+2014 in code-fenced captured pipeline output. |
| docs/16-NOMENCLATURE-SPEC.md | 124 | 1 | Code-fenced Python source comment. |
| docs/16-NOMENCLATURE-SPEC.md | 142 | 1 | Code-fenced Python docstring. |
| docs/16-NOMENCLATURE-SPEC.md | 152 | 1 | Code-fenced Python docstring. |
| docs/16-NOMENCLATURE-SPEC.md | 196 | 1 | Code-fenced Python source comment. |
| docs/16-NOMENCLATURE-SPEC.md | 292 | 1 | Code-fenced test assertion comment. |
| docs/26-SESSION-HISTORY.md | 942 | 1 | Inline code preserving captured pipeline output. |
