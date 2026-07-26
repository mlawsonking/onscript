# Gold-set harness

W10 provides tools only. It performs no real annotation.

Run the synthetic end-to-end acceptance sample from the repository root:

```text
python scripts/goldset.py metrics tests/fixtures/w10_synthetic_annotations.json
```

The command applies date splits, merges two independent annotation batches, applies the explicit
adjudication records, and emits precision by class, the confusion matrix, document-family pairwise
precision and recall, and the party error gap.

Create a deterministic stratified sample with:

```text
python scripts/goldset.py sample tests/fixtures/w10_synthetic_annotations.json --per-stratum 2
```

Sampling strata are party, predicted class, lane, and year. Candidate IDs are hash-ranked within
each stratum. The same input produces the same sample.
