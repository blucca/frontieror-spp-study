# Fixed-pool OSS probe negatives — separate from Main

Original hard3, seed1, the same1706-column /100-row density pool, six-second
first-stage budgets, exact matched solver versions:

| Probe | Solver outcome | Search s | Whole algorithm s | Whole feasible witness |
|---|---|---:|---:|---|
| Restricted objective HiGHS1.15.1 | TimeLimit, bound56 | 5.680 | 5.885 | none |
| Cost-free feasibility CP-SAT9.15.6755 | UNKNOWN | 4.927 | 6.031 | none |

Both exit2 after recording NO_COVER; no solution/checker artifacts exist.
The CP-SAT constant-objective response contains objective0 as a solver statistic;
the explicitly reported solution objective is null because no witness exists.
These are probe-only diagnostics, not full Main scores. `algorithm=main` in
raw run records is the shared harness selector, not the frozen Main source.

Original minimal sources are under `restricted-highs/` and `cost-free-cpsat/`.
They retain historical helper imports for audit; the imported seeded helper is
published under `experiments/paired-seeds/`. Full original raw stdout/stderr/run
receipts: [`results/2026-11-21/restricted-pool/`](../../results/2026-11-21/restricted-pool/).
Detailed solver metrics are in `algorithm.stdout.log`; the shared worker exits
on the failed algorithm before populating its run-record `metrics` field.
