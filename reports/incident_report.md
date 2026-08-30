# Incident Report — Duplicate order replay

## Severity

P1 data incident. The revenue mart and CEO dashboard are in the blast radius;
the critical contract correctly blocks publication.

## Summary

The incoming orders batch contained repeated `order_id` values consistent with
a partial upstream replay. The pipeline process itself could still finish, but
the data was not safe to publish because duplicate facts can inflate completed
order counts and revenue.

## Detection

- Signal: critical `unique(order_id)` contract and GX Expectation failure.
- First observed: during the duplicate-key game-day validation run.
- Corroboration: 603 input rows after three records were repeated; six rows were
  marked as members of duplicate groups.

## Root Cause

Most likely an ingestion replay without idempotent deduplication. This ranking
comes from the unchanged schema/value domains plus repeated primary keys; it
does not depend on reading the injection implementation.

## Evidence

1. Custom contract: `unique/order_id`, severity `critical`, action `block`.
2. GX Checkpoint: `success=False`, action `block_and_quarantine`.
3. Contract SLO for that run: 1 bad critical check out of 1, burn rate about
   1000x for a 99.9% target.
4. Dataset lineage: `stg_orders → fct_daily_revenue → ceo_revenue_dashboard`.
5. dbt also has a unique test on `stg_orders.order_id`, providing a second
   deterministic protection layer.

## Blast Radius

```text
raw_orders
→ stg_orders
→ fct_daily_revenue
→ ceo_revenue_dashboard
```

The KB/RAG branch is independent and was not affected.

## Mitigation

- Block the orders batch before dbt publication.
- Quarantine the rejected batch at the GX action boundary.
- Re-run the upstream extraction with an idempotency key or deduplicate by
  `order_id` only after confirming the authoritative replay semantics.

## Recovery

Restore the last known-good incoming batch, rerun contract/GX checks, then run
`dbt build`. Publish only after the anomaly and SLO evidence are healthy.

## Verification

- [x] Contract healthy after reset
- [x] dbt build healthy (`PASS=19`, including one unit test and 13 data tests)
- [x] Healthy row count returns inside the robust expected range
- [x] SLO calculation and sustained-burn policy covered by tests
- [x] Downstream blast radius verified by transitive lineage

## Prevention / Action Items

| Action | Owner | Deadline | Why |
|---|---|---|---|
| Add producer-side idempotency key | commerce-data | Next sprint | Prevent replayed facts |
| Keep critical uniqueness as a release gate | commerce-data | Done | Deterministic containment |
| Alert only on paired burn windows | reliability | Done | Avoid transient-noise pages |
| Attach owner/runbook metadata to dashboard | reliability | Done | Faster triage |
