# 34: Alexandria Stage 2 embedding runbook (the 4080 layer)

Author: Opus, Session 53, 2026-07-27. This is a runbook, not a redesign. The design it operationalizes
is docs/03 section 1.4 (the Alexandria math on the 4080) and docs/02 R10 (local embeddings). docs/05
lists the Archive exhibits these inputs feed. Constitution Articles III (two lanes) and the docs/03
temporal honesty layer govern any exhibit derived from them.

## 0. What this is, and what it is not

Alexandria Stage 2's deterministic pass is already complete (docs/04 Session 3: the 25-year ledger,
adoption curves, discipline index, coverage tables, and the era and monthly chapters). This runbook
covers the one remaining, optional layer: a one-time pass on Michael's RTX 4080 that produces

1. sentence embeddings for every statement in the corpus (paraphrase-tolerant vectors), and
2. a topic tag per statement from a local 8-14B model.

These feed Archive exhibits only: the de-facto caucus map, 25-year topic ownership, and the frame-war
maps in docs/05. They are dark until Michael flips their surfaces, exactly like the archive and
silence surfaces.

What this is not:

- It is not the daily pipeline. The charter keeps nothing recurring on a personal machine; the daily
  run stays cloud and API-keyed. This is one-time capital work, disclosed on the methodology page.
- It does not write chapter prose. Local models are weak at the register; Claude writes the chapters
  (docs/03 section 1.4). The GPU does math only.
- It is $0 marginal. Local GPU compute, no API calls.

## 1. Precondition gate (verified 2026-07-27)

Run the input check before the GPU job. It is read-only, CPU-only, $0, and deterministic:

```bash
python scripts/deep/alexandria_stage2_verify.py
```

It confirms the embedding inputs match the shard inventory the deterministic pass built. As of
2026-07-27 it reports READY:

- Press mirror (Lane-1 congress-press, `data/raw/congress-press/*.jsonl`): 688,820 records across
  congresses 107-119 (2001-2026), delta 0 against every alexandria shard's `records` count. The
  embeddable unit count is the normalized statement total, 684,853. Provenance lane split of the raw
  records: legacy 485,948, scraper 200,033, page_html 2,839.
- CREC Extensions lane (`crec/state/E/statements-{year}.jsonl` on X:): 152,187 E-statements across
  2001-2026, with all 13 ledger shards (107-119) present. 15 rows date to congress 106 (a pre-2001
  boundary sliver, ignore). This lane is the pre-2013 corpus: congresses 107-112 carry ~83,671 CREC
  E-statements while the press mirror carries only ~2,389 there, so almost all pre-2013 embedding
  coverage is CREC-borne.

Total embeddable vectors: about 837,040 (684,853 press plus 152,187 CREC). A non-zero delta or a
missing ledger is a stop-and-diagnose: the shards and the embedding inputs must agree before embedding,
or the vector store and the ledger describe different corpora.

## 2. Inputs and the lane contract

Each vector is keyed by the statement's stable id and carries its provenance lane (`date_source` for
press, `source=crec` plus `crec_section` for CREC) and its congress. The lane rides with every vector
because the comparison an exhibit later runs is only valid within one lane:

- The press lane is the symmetric cross-party corpus (Lane 1). Any exhibit that compares the parties
  (de-facto caucuses, polarization-over-time) draws Lane-1 vectors only. The scraper/legacy seam
  (2021-01-03) still applies: a cross-seam comparison is a cross-instrument comparison (docs/12 L1),
  so an exhibit that spans it must isolate by instrument or declare the seam.
- The CREC Extensions lane is a separate instrument. It enriches (it is the deep-history spine) and it
  can carry within-CREC exhibits, but it never enters a cross-party denominator with the press lane.
  This is the same rule the deep archive already enforces (SD.8, docs/13): a CREC-only pre-2013 claim
  needs its own within-lane design, not a borrow from press credibility.
- Temporal honesty (docs/03): historical coverage is uneven. Every exhibit carries per-year by
  per-party coverage and gates cross-era claims on coverage parity; pre-2011 strata are labelled
  partial. Embeddings do not change this; they ride on top of it.

## 3. The embedding pass

Model: `sentence-transformers/all-MiniLM-L6-v2`, 384-dimensional, the model named in docs/02 R10. It
runs in minutes on the 4080 for the whole corpus.

Committed as `scripts/deep/alexandria_embed.py` (Opus, Session 59, 2026-07-28). The torch and
sentence-transformers stack it needs lives in a dedicated virtual environment OUTSIDE this repository,
so `requirements.lock` stays empty of third-party runtime dependencies and the daily pipeline never
inherits a GPU dependency. The script imports that stack lazily and prints where it lives if it is
missing, which is why the repository suite imports the module on a box with no GPU stack at all.

Create the environment once:

```bash
C:\ProgramData\miniconda3\python.exe -m venv --system-site-packages C:/Users/bobdo/venvs/onscript-embed
C:/Users/bobdo/venvs/onscript-embed/Scripts/python.exe -m pip install sentence-transformers==3.4.1
```

`--system-site-packages` is deliberate: the box's conda base already carries a working
`torch 2.6.0+cu124` against the installed driver, so the environment adds only the encoder layer
instead of downloading a second multi-gigabyte CUDA build. Nothing in it is ever imported by
`pipeline/`.

The procedure the script implements:

1. Stream the statement text and its (stable_id, congress, lane) for each lane. Press text is the
   normalized statement text (the same unit the ledger counts); CREC text is the E-statement `text`.
2. Encode in batches (batch 256-512 on 12 GB VRAM), `normalize_embeddings=True`, fp16 on GPU.
3. Write one shard per (lane, congress) to X: as `alexandria/embeddings/{lane}/emb-{congress}.f16.npy`
   plus a parallel `ids-{congress}.jsonl` (stable_id order matches the matrix rows). Append-only; a
   completed (lane, congress) is skipped on resume.
4. Record a manifest per shard: model id, model revision sha, dimension, dtype, row count, and the
   sha256 of the id list, so a reader can prove which model produced which vectors (the same
   generator-provenance discipline the chapters use).

Storage: 837,040 vectors at 384 dims is about 1.29 GB in fp32 or 0.64 GB in fp16, trivial on X:
(about 1.8 TB free). Determinism: pin the model revision and the dtype; the same corpus and model
reproduce the same vectors within fp tolerance, which is why the manifest records the model sha.

## 4. The topic-tag pass

Model: a local 8-14B instruct model (docs/03 section 1.4), temperature 0, one topic per statement from
the committed `taxonomy_v1.json` label set (the same 25 topics the silence board and the daily pipeline
use, so the historical layer and the live layer share one vocabulary). $0, local.

Committed as `scripts/deep/alexandria_topic_tag.py` with its frozen instrument at
`data/reference/alexandria-topic-tag.json` (Opus, Session 59, 2026-07-28). The script is PREPARED and
NOT RUN; section 6a states the run command and what an operator must do first. The procedure it
implements:

1. For each statement, prompt the model with the text and the fixed taxonomy label list; require a
   single label from that list (or `other`), parsed deterministically.
2. Write `alexandria/topics/{lane}/topics-{congress}.jsonl` (stable_id, topic, model_conf) to X:,
   append-only, resumable per (lane, congress).
3. Manifest per shard: model id, revision sha, prompt sha, taxonomy version, row count. The tag is a
   deterministic-parse over a temperature-0 generation; the manifest lets a reader reproduce it.

The tags are a computation, not prose. They never touch the chapter voice and never bypass the
verifier for anything published.

## 4a. The topic-tag run command (prepared, not run)

The script and its frozen instrument are committed. The pass has not been started and starting it is
a separate operator act. Two prerequisites, neither of which this session performed:

1. A local 8-14B instruct model must be served on an OpenAI-compatible endpoint. The frozen config
   names `qwen2.5-14b-instruct` at `http://localhost:1234/v1/chat/completions`, which is LM Studio's
   default server. LM Studio is installed at `X:\LLAMA\LM Studio`; as of 2026-07-28 no model is
   present in its library, so the model must be pulled before the endpoint answers.
2. If the model id or the endpoint changes, re-freeze the config. The script fails closed against
   `data/reference/alexandria-topic-tag.json` and refuses to generate on drift, so an edited prompt
   or a swapped model cannot silently produce tags that a manifest then attributes to the frozen
   instrument.

Inspect the frozen instrument without generating anything (this is what the script does by default):

```bash
python scripts/deep/alexandria_topic_tag.py
```

Run the pass, once both prerequisites hold:

```bash
python scripts/deep/alexandria_topic_tag.py --allow-local-generation --report topic-tag-report.json
```

`--allow-local-generation` is required and has no default. Resume is per (lane, congress) exactly as
the embedding pass: a shard whose manifest reports complete is skipped, so an interrupted run is
restarted with the same command.

Why it stops here rather than running with the embeddings: the constitutional line in docs/03
section 1.4 is that a local model may compute but never write voice, and the distance between a
classification and a generation is a matter of how the output is used. Vectors cannot be mistaken
for prose. A 14B model's free text can. Leaving the tagger prepared and unrun keeps that boundary an
operator decision with a named owner rather than a side effect of an embedding session.

## 5. Non-interference and safety

- Read-only on `data/raw/congress-press` and the CREC state; writes go only to X:
  (`alexandria/embeddings`, `alexandria/topics`), the append-only state store, never the repo working
  tree and never `site/public` or `data/derived`.
- No FEATURES flag flips, no POSTING_ENABLED change, no workflow dispatch, no site render. The exhibits
  that consume these vectors stay dark behind their own flags until Michael releases them.
- Starting the GPU job is Michael's machine time and his call. This runbook and the verify gate are the
  dry preparation; nothing here has run a GPU or produced a vector.

## 6. Order of operations for the run day

1. `python scripts/deep/alexandria_stage2_verify.py` and confirm READY (delta 0, ledgers present).
2. Build and run `scripts/deep/alexandria_embed.py` (section 3). Verify: every (lane, congress) shard's
   row count equals its id-list length and equals the input statement count; spot-check determinism by
   re-encoding one batch and comparing within fp tolerance.
3. Build and run `scripts/deep/alexandria_topic_tag.py` (section 4). Verify: tag count equals statement
   count per shard; every tag is in the taxonomy label set.
4. Leave the exhibits dark. Record the run in docs/04 (generator, model shas, counts, elapsed) exactly
   as the chapters and CREC builds are recorded.
