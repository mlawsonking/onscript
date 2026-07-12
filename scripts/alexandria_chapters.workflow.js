export const meta = {
  name: 'alexandria-chapters',
  description: 'Generate era-granular composite-voice chapters over the 25-year ledger (subscription agents, <=12 concurrent, grounded + verified downstream)',
  phases: [{ title: 'Generate', detail: 'one grounded era chapter per (Congress, party), 12 at a time' }],
}

// P4 verbatim (pipeline/prompts/P4_era_chapter.v1.0.txt) — the instrument, embedded so agents
// need no filesystem. Voice + hard grounding rules; Python re-verifies every chapter after.
const P4_SYSTEM = `You are the composite voice of the {party} members of the U.S. Congress during the {label}, speaking as one "we," in retrospect. You are deadpan, sincere, and clinically self-observant: you report your own coordination the way an instrument reviews its own record. HARD RULES: (1) Build ONLY from the provided STATS; never introduce a topic, claim, event, person, or fact not present in them. (2) Any quoted words must be copied exactly from the provided PHRASES, <=10 words per quote. (3) Use ONLY the numbers in STATS, verbatim; never compute, estimate, or invent a number. (4) Note the era's most-repeated phrases and how many of us said each; you may name the first-sayer only if given in STATS. (5) <=150 words, first-person plural, retrospective tense, no adjectives that don't appear in the phrases, no irony markers, no hashtags, no emoji. (6) If STATS.statements is low or PHRASES is empty, say plainly that the record from this era is too thin to characterize — do not fill the gap. You are analysis of the record, not a substitute for it.`

const BATCH = 12   // hard concurrency cap — each batch of <=12 completes before the next starts

function chapterPrompt(inp) {
  const sys = P4_SYSTEM.replaceAll('{party}', inp.party).replaceAll('{label}', inp.label)
  return `${sys}

ERA: ${inp.label} · PARTY: ${inp.party}
STATS (the ONLY numbers you may use, verbatim): ${JSON.stringify(inp.stats)}
PHRASES (the ONLY words you may quote, <=10 words each, copied exactly): ${JSON.stringify(inp.fragments)}

Write the era chapter now. Output ONLY the chapter text — no preamble, no title, no markdown.`
}

// args = the chapter inputs (from pipeline/chapters.build_era_inputs). Only "sufficient" eras
// are generated; thin eras get a deterministic code stub in Python (never fabricated prose).
const inputs = Array.isArray(args) ? args : (args && args.inputs) || []
const todo = inputs.filter(i => i && i.sufficient)
log(`generating ${todo.length} chapters (of ${inputs.length} eras; thin eras get code stubs), ${BATCH} at a time`)

phase('Generate')
const chapters = {}
for (let i = 0; i < todo.length; i += BATCH) {
  const batch = todo.slice(i, i + BATCH)
  const texts = await parallel(batch.map(inp => () =>
    agent(chapterPrompt(inp), { label: `chapter:${inp.id}`, phase: 'Generate' })
  ))
  batch.forEach((inp, j) => { if (texts[j]) chapters[inp.id] = texts[j] })
  log(`batch ${Math.floor(i / BATCH) + 1}: ${Object.keys(chapters).length}/${todo.length} generated`)
}

return { chapters, count: Object.keys(chapters).length, eras: inputs.length }
