# Pass 2 quick reference

For Michael, beside the open app. This restates `evaluation/ANNOTATION-GUIDE.md` and expands
its worked examples. **It adds no rule.** If anything here looks like a rule the guide does not
contain, the guide wins and the difference is a defect in this file.

Every phrase used as an example below is absent from the pilot and the full sample, checked
before it was written. None of them decides an item you are about to label.

## 1. The one question

For every item, cover the sentence with your hand and read only the candidate phrase.

**If a reader who saw nothing else could not tell what position is being taken, it is not a
message.**

That is the whole correction. The sentence is there to tell you what the phrase *means*. It is
not there to lend the phrase meaning it does not have. Most candidates are short windows cut
out of longer sentences, so a political sentence wrapped around an empty fragment is the common
case, not the rare one.

Expect to use `unknown` often. A pass that never reaches for it has been reading sentences.

## 2. Order of operations, per item

1. Read the phrase. Cover the sentence. Decide if it says anything on its own.
2. **Answer B (phrase complete) first.** It is a gate, not a footnote.
3. Then choose the class, walking the ladder in order and stopping at the first fit.
4. Assign the family ID.
5. Fill C, D, F if the item shows a support set.
6. Use `notes` on any call you would want a second opinion on.

The app enforces step 2. Clicking **message** while B is unanswered is refused and records
nothing. Clicking **message** when B says no is refused. Answering B **no** after you already
chose message withdraws the message label and tells you why. Nothing else is blocked.

## 3. The class ladder

Walk in order. Stop at the first class that fits. Message is only reached after the four above
it have been ruled out.

| | Class | Test |
|---|---|---|
| 1 | **private** | Names or describes a private individual, or the item shows a `<private-individual-…>` label |
| 2 | **nomenclature** | An official name or title: committee, caucus, bill, act, office, agency, place-as-proper-name |
| 3 | **procedural** | Legislative, publication, or office process rather than a position |
| 4 | **biographical** | A person's life or career history |
| 5 | **message** | Carries substantive political meaning on its own. All three conditions below must hold |
| 6 | **unknown** | Anything else, and the safe default when you are unsure |

Message requires **all three**:

- a substantive content word, not only scaffolding, filler, or a reference,
- completeness (task B), and
- the four classes above it ruled out.

## 4. One class per example

**private.** Phrase: `a constituent from springfield` where the item shows
`<private-individual-a1b2>` in place of a name. The label is a real part of the item and is the
evidence a name was suppressed. Do not try to recover it. Choose private and stop.

**nomenclature.** Phrase: `the senate armed services`. Sentence: "She was appointed to the
Senate Armed Services Committee for the 119th Congress." Part of a committee name. A name is
not a message even when the statement around it is political.

Also nomenclature: `the affordable care act`, `on energy and commerce`,
`chairman of the subcommittee`. All are names and titles.

**procedural.** Phrase: `voted against the resolution`. Sentence: "He voted against the
resolution when it came to the floor on Tuesday." This is the process register: introducing,
cosponsoring, voting, marking up, holding a hearing, joining a letter, pointing at a document.

Also procedural: `held a markup on`, `cosponsored the bipartisan bill`, `roll call vote`,
`is available here`.

**biographical.** Phrase: `served in the navy`. Sentence: "Before his election to Congress he
served in the Navy for twelve years." Career history.

Also biographical: `born and raised in`, `graduated from the university`,
`a small business owner`, `before his election to`.

**message.** Phrase: `puts patients over profits`. Sentence: "This bill puts patients over
profits, and I will fight for it." Cover the sentence: the phrase alone states a value and a
position. It survives on its own.

Also message: `gutting medicaid to fund`, `an attack on our seniors`,
`the largest tax increase`. Each carries a claim or a characterization without help.

**unknown.** Phrase: `claim they are for`. Sentence: "Republicans claim they are for working
families, but it is Democrats who support an increase in the minimum wage." The sentence is
plainly political. The phrase is scaffolding and could sit in a sentence about anything.

Note that `working families`, from **the same sentence**, is a message. One political sentence,
one message phrase, one unknown phrase. That pair is the whole lesson.

## 5. The shapes that will actually give you trouble

**Dangling fragments.** `lower costs for` stops on a preposition that needs an object.
`introduced legislation to` ends on a "to" that needs a verb. These fail task B, so they cannot
be message whatever the sentence is about. Expect a lot of these: the candidates are n-gram
windows and many stop mid-construction.

**Substantive words inside an incomplete window.** This is the trap that costs you. A fragment
can be full of strong political vocabulary and still fail B. Strong words are not the test.
Completeness is a separate condition and it is a gate.

**Name-bearing fragments.** `of speaker johnson's`, `with secretary kennedy's`. These are built
around an official's name but carry scaffolding around it. The guide's ladder puts nomenclature
above message, so if the phrase is built around the name, nomenclature. If it is mostly
scaffolding and the name is incidental, B usually fails it into unknown anyway. This boundary
is genuinely ambiguous, it is the one the model reader answered inconsistently across two items
in its own pass, and it is worth a `notes` entry when you hit it. Decide it once and hold to it.

**Bare scaffolding and boilerplate.** `said in a statement`, `released the following statement`,
`in the coming weeks`, `i am proud to`. No position, no subject. Unknown.

**Chamber and body references.** `the house of representatives` used only to say where
something happened is a location, not a position. Unknown, not nomenclature, when it is
functioning as a pointer rather than as a name being invoked.

**Quoted speech.** If the sentence quotes someone, read who is asserting the phrase. That
matters more for task D (stance) than for the class, but a phrase that only exists inside
someone else's quoted words is still judged as the phrase, on its own.

**Redaction labels.** `<private-individual-…>` in an item is expected and is the evidence the
privacy floor worked. Class private, stop.

## 6. Tasks B through F

**B, phrase complete. Required.** Is the phrase a coherent noun phrase, verb phrase, or clause
a reader could take as a unit?

- yes: `working families`, `puts patients over profits`, `roll call vote`
- no: `lower costs for`, `introduced legislation to`, `claim they are for`

Completeness is about the phrase as shown, never the sentence. A phrase can sit inside a
perfectly good sentence and still be a fragment.

**C, proposition consistent.** Only for items showing a support set. Are the other statements
using this phrase to assert the same underlying point, or does the string just happen to
recur across unrelated subjects? Judge the proposition, not the wording. Same point in
different words is still consistent.

**D, stance.**

- **affirmative**: the member asserts it as their own position.
- **negated**: the member states it to reject it ("this is *not* a stock trading ban").
- **mixed**: the same sentence both asserts and denies, or quotes an opponent's use and rejects
  it in the same breath.

Watch the contrastive frame. In "Republicans claim they are for working families, but it is
Democrats who...", the member is reporting an opponent's use of `working families` in order to
dispute it. That is **mixed**, not affirmative.

**E, family ID. Required.** Two items share a family when their releases are the same document
reused, or one document many offices published together.

- One joint or cosigned release published by twenty offices: **one** family, same ID on all
  twenty.
- A template reused with a name and district swapped: **one** family.
- Two members writing their own statements about the same event: **different** families, even
  when they share a phrase and a day.
- Do not chain. A resembles B and B resembles C does not put A and C together.

Any short stable label works, for example `fam-medicaid-cuts-01`. Consistency of reuse is what
matters, not the text. The app offers your existing labels as you type, so reuse from that list
rather than retyping.

**F, claim supported.** At least three *distinct offices* genuinely asserting the same point
with this phrase.

The trap is counting carriers instead of documents. Ten offices publishing the same cosigned
letter is **one** supporting document, not ten. Set aside copies of one joint document,
off-topic uses, and negated uses, then count what is left. Below three is no.

## 7. Finishing

The header counts items with a class and a family. When it reads **200 / 200**, click
**Export answer CSV** and save it as:

```
evaluation\goldset\bundles\pilot\michael-pass2.answersheet.csv
```

Your browser will put it in Downloads first. Move it to that path, or say where you dropped it.

While the pass is open: do not look at the live site, the classifier source, or the model
rater's sheet. The app autosaves in the browser as you go, so you can close the tab and reopen
the same file to resume, but do not move or delete the folder it lives in until you have
exported.

## 8. What you already know, and what it does to this pass

Recorded so it is weighed rather than discovered, per the Session 57 transparency rule and
`PILOT-RECORD.md` section 4.2.

Before this pass you have been told the model reader's aggregate distribution, that the largest
disagreement with pass 1 was message against unknown on 121 items, and that pass 1 never used
unknown. That is one-directional information: it tells you which way to move.

The honest use of it is to apply the cover-the-sentence test to each item on its own merits and
let the distribution land wherever it lands. Do not aim for a target. If an item is a message
under the test, label it message; the fact that pass 1 over-used message is not a reason to
under-use it now.

This is why pass 2 is recorded as a corrected pass and not an independent one, and why Gate B
still waits on labels from someone who is not you.
