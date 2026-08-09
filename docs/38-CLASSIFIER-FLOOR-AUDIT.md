# 38: Classifier floor audit against the published surface

Authority: Opus, Session 64, 2026-08-01. Evidence for the docs/33 R-33.2 ruling on fail-closed
classification. This document reports what the deterministic classifier did to phrases that
actually published, measured on committed day artifacts. It proposes options and changes
nothing. The rulings it serves belong to Fable, and every release act belongs to Michael.

The gold-set pilot is the designed instrument for this question and its labels do not exist
yet. This audit is not a substitute for them. It exists because the same defect the gold set
was built to measure is visible on the live surface now, at a size worth ruling on early.

## 1. What was measured

Population: every talking-point claim and every top-synchronized n-gram in the 20 committed day
artifacts under `data/derived/days`, covering 2026-06-30 through 2026-07-29.

- 79 published talking-point claims
- 311 top-synchronized n-grams
- 455 member-mentions across the published claims

Instrument: `pipeline.eligibility.classify_phrase`, the live deterministic classifier, called
with each phrase and its day. No threshold, prompt, or configuration was changed.

The sealed pilot sample is deliberately excluded. Its shape distribution is a prior that would
contaminate the in-flight pass-2 annotation (docs/35 §10.2, and the disclosure discipline in
`evaluation/goldset/PILOT-RECORD.md` §4.2).

Reproduction: `scripts/audit_classifier_floor.py`, deterministic, no network, no API budget.

## 2. Finding 1: the message class carries most of the published surface

| Surface | message | procedural | nomenclature | unknown | biographical |
|---|---|---|---|---|---|
| Published claims (79) | **47 (59.5%)** | 16 | 11 | 5 | 0 |
| Top-synchronized (311) | **212 (68.2%)** | 54 | 37 | 6 | 2 |

R-33.2 defines message as an affirmative standard that unmatched phrases fail into unknown.
A standard that admits 59.5% of published claims and 68.2% of the synchronization table is not
behaving as a floor. The unknown class, which is the rule's stated safe default, takes 6.3% and
1.9% respectively.

## 3. Finding 2: the admissions include names, dates, and procedure

The twelve most-shared published claims, with the class the live classifier assigned:

| Members | Classified | Phrase | Reading under the docs/35 ladder |
|---|---|---|---|
| 53 | message | `after the supreme court` | temporal connector, states no position |
| 47 | message | `national defense authorization act` | an act title, nomenclature stops above message |
| 24 | message | `national defense authorization act` | as above |
| 15 | message | `dependent children from purchasing` | fragment of a bill provision |
| 12 | message | `after the supreme court` | as above |
| 10 | nomenclature | `21st century road to` | correct class, incomplete phrase |
| 10 | nomenclature | `house transportation and infrastructure` | correct |
| 9 | nomenclature | `road to housing act` | correct |
| 8 | procedural | `the senate environment and` | correct class, incomplete phrase |
| 8 | message | `house by a vote` | procedure |
| 6 | message | `court of the united states` | part of a proper name |
| 6 | nomenclature | `and related programs appropriations` | correct |

Six of the seven message admissions in this table are, by the guide's own class ladder, either
nomenclature or procedural. The ladder places both above message precisely so that a bill title
is not counted as a talking point.

This is the shape the Session 57 memory prior described (the classifier over-labels message and
procedural). It is recorded here as a measurement, not as a confirmation of that prior: the
prior concerned a different comparison and is disclosed in `PILOT-RECORD.md` §4.1.

## 4. Finding 3: a fifth of published claims are broken fragments

17 of 79 published claims (21.5%) end on a preposition, conjunction, article, or auxiliary,
which is a word requiring a completion the phrase does not contain. They reached 69 of 455
member-mentions. Sixteen are distinct.

```
war powers resolution to          the senate version of
21st century road to              acting director of the
a letter to secretary of          letter to acting director of
companion legislation in the      the high cost of
i voted yes on                    the senate environment and
the southern district of          the 21st century road to
the trump administration to       democratic colleagues in demanding the
senate homeland security and      senior member of the
```

Phrase completeness is already a stated condition of the message standard in R-33.2 and a
required task in the annotation guide. It is not enforced on the publication path. Applying the
completeness condition alone would have withheld all 17.

The count is measured on the tail only. An earlier pass also flagged phrases beginning with a
preposition and was discarded as wrong: `on the house floor` and `in the united states` are
complete prepositional phrases that read correctly.

## 5. Finding 4: synchronization selects against message content

Mean number of members converging on a phrase, by class, across the 311 top-synchronized
n-grams:

| Class | Count | Share | Mean peak members |
|---|---|---|---|
| biographical | 2 | 0.6% | 24.0 |
| nomenclature | 37 | 11.9% | **10.3** |
| message | 212 | 68.2% | 7.9 |
| procedural | 54 | 17.4% | 6.7 |
| unknown | 6 | 1.9% | 6.3 |

Biographical has the highest mean on two n-grams and is too small to carry weight; it is shown
because a table ranked by mean that omitted its top row would mislead. The load-bearing
comparison is nomenclature at 10.3 against message at 7.9, on 37 and 212 n-grams.

The most-shared phrases are names. The single most-synchronized n-gram on six of the eight
busiest days is nomenclature or biographical, not message.

This is a structural property rather than a bug. Offices converge exactly on the strings they
cannot vary: bill titles, committee names, statutory language. They diverge on argument,
because each office writes its own. A ranking that sorts by raw convergence will therefore
surface the legislative calendar most days, which is a true statement about language and a weak
statement about message discipline.

It bears on the headline. "Our most synchronized phrase" is a real measurement, but it is not a
measurement of coordinated messaging, and on most days it will name a bill.

## 6. Finding 5: an unquoted phrase in the composite reads as a system failure

The deterministic fallback template renders the top synchronized phrase without a delimiter
(`pipeline/distill.py`, the `top_phrase` clause). On 2026-07-29 the Republican composite
published:

> Our most synchronized phrase, used by 5 of us: refused to answer.

The phrase is `refused to answer`, used by five members. The sentence reads as the instrument
reporting an error. Every other claim in the same template is delimited; this clause is the
outlier.

The absence of quotation marks is deliberate and its reason is sound. The comment records it: a
ledger n-gram is not a verbatim member quote, and quoting it would assert that a member said
those exact words. The defect is that the cure removed the delimiter without replacing it, so a
measured string is run into prose.

Any fix has to keep the non-assertion and restore the boundary, and it has to survive plain
text because this composite is posted.

## 7. Options

Each option states its blast radius. None is applied. R-29.5 governs: public-string and prompt
changes land dark and activate on Michael's push.

**O1. Delimit the top-synchronized phrase in the composite.** Restore a boundary that does not
assert verbatim speech. Touches one clause in `distill.py`. Changes published prose and the
posted thread text, so it is a public-string change under R-29.5. Smallest change with the
largest visible effect. Does not touch classification.

**O2. Enforce the completeness condition on the publication path.** The message standard already
requires completeness; apply it where claims are selected. Withholds the 17 fragments in §4.
Cost: quiet days get quieter, and the withheld share is not yet measured against a gold
standard. This is a threshold change and, under R-33.2, the gold-set classifier threshold is
supposed to join the standard when the W10 metrics exist. Ruling it early trades evidence for
speed.

**O3. Raise the ladder above message for names and procedure.** Address the §3 admissions
directly by tightening the nomenclature and procedural tests so bill titles and vote language
stop reaching message. Largest correctness gain and the largest risk: it moves the instrument
fingerprint and changes what every past day would have published, so the existing time series
and the comparison it supports are affected. Constitution Article xiii and docs/37 rule 13
apply. Should wait for the gold-set metrics that were built to size exactly this.

**O4. Separate the headline from raw convergence.** Rank the daily headline on a message-class
subset rather than on all phrases, so the front page stops leading with a bill title. Product
decision before a code decision. No classification change; a display and selection change.

**O5. Change candidate generation to prefer complete constituents.** The root cause of §4:
fixed-width sliding windows cut phrases mid-constituent. This is the largest piece of work,
invalidates comparability with the current series, and belongs to a versioned method change
rather than to this audit.

## 8. Recommendation

O1 now, as a single reviewable dark commit. It is the one finding here that requires no gold
standard to adjudicate, and it is the one a reader sees first.

O2 and O3 wait for the pass-2 gold-set metrics. This audit sizes the problem; it does not
license a threshold move, and moving thresholds on the strength of author judgment is what the
gold set exists to replace.

O4 is Michael's product call and can be taken at any time.

O5 is a v2 method change and should be scoped separately.

## 9. What this audit does not establish

- It is not a precision measurement. The right column of §3 is the author's reading of the class
  ladder, not an adjudicated label. Two readers could differ on some rows.
- It is not the gold set. The instrument that measures classifier precision is the pilot, and
  its labels do not exist yet.
- It says nothing about party symmetry. Both parties were measured through the same classifier,
  and no per-party error rate is reported here.
- The 2026-07-29 composite quoted in §6 is a single published example, not a rate. How often the
  clause reads badly was not measured.
