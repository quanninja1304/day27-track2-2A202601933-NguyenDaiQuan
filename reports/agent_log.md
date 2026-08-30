# AI Agent Decision Log

## Decision 1 — Contract clock and type drift

- Hypothesis: coercion-only range checks hide strings in numeric columns, while
  an implicit wall clock makes historical unit fixtures nondeterministic.
- Agent proposal: explicit type masks plus an injectable/reference clock for
  live freshness; map severity to `block`, `warn`, or `observe`.
- Evidence/test: type-drift and two-hour freshness tests pass; healthy public
  fixture remains deterministic.
- Decision: accept.

## Decision 2 — Robust anomaly baseline

- Hypothesis: naive z-score and mismatched weekend segmentation generate false
  positives and are fragile to outliers.
- Agent proposal: preserve explicit z-score, use MAD in `auto`, consume
  `same_segment_history`, and support known-event suppression.
- Evidence/test: 70% volume drop is detected, a valid weekend segment is not,
  and zero-MAD changes are detected.
- Decision: accept after revising baseline to compare like-for-like batch counts.

## Decision 3 — Distribution and RAG drift

- Hypothesis: mean ratio misses shape drift and embedding-norm collapse.
- Agent proposal: dependency-free two-sample KS plus a small-sample mean guard;
  reuse both signals for embedding norms.
- Evidence/test: equal-mean/different-shape and large norm-shift tests pass.
- Decision: accept.

## Decision 4 — dbt SCD join correctness

- Hypothesis: two active customer versions multiply order facts and revenue.
- Agent proposal: rank active versions before the join and add the smallest
  native dbt unit test containing two active rows for one customer.
- Evidence/test: `dbt build` completed `PASS=19`; the native unit test expects
  revenue 170 rather than 340.
- Decision: accept.

## Decision 5 — Actionable validation

- Hypothesis: printing individual GX Expectations is not an operational gate.
- Agent proposal: Suite → ValidationDefinition → Checkpoint with a local
  severity Action, plus critical-batch quarantine.
- Evidence/test: healthy Checkpoint succeeds; duplicate-key Checkpoint fails and
  maps to `block_and_quarantine`.
- Decision: accept; replaced the slower Data Docs Action with a deterministic
  local action suitable for the lab.

## Decision 6 — Paging and blast radius

- Hypothesis: a single fast window pages on transient spikes, and direct-only
  column lineage understates impact.
- Agent proposal: require short/long burn agreement and use cycle-safe BFS for
  both dataset and column lineage.
- Evidence/test: `(15x, 7x)` pages, `(15x, 1x)` does not; cyclic transitive
  column traversal terminates with the complete blast radius.
- Decision: accept.
