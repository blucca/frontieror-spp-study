# Isolated dynamic-scarcity probe — separate from Main scores

Only the value-order scarcity term changes from initial row degree to current
compatible row degree. Candidate pool, coverage reward, RNG, MRV, propagation,
memo and cutoff remain fixed. The minimal ranking function is
[`dynamic_order.py`](dynamic_order.py); integration source and diff are retained.

Original hard3, unchanged 1706-column pool, theta5.333333, six-second probes,
seeds104729*[1,2,3], one serial batch; no LP/MIP calls in the algorithm:

| Seed | Frozen static probe, retained | Dynamic probe | Dynamic cost |
|---|---|---|---:|
| 1 | cover252, 4.932 s | TIME_LIMIT, 5.999 s | — |
| 2 | TIME_LIMIT, 6 s | cover, 2.189 s | 328 |
| 3 | TIME_LIMIT, 6 s | cover, 4.197 s | 328 |

Both dynamic covers select22 original columns, provide all15000 binary values
and pass independent exact and original NumPy2.5.3 checkers. Seed1 has no
witness; its process/resource gate passes. This probe-only result gives up
the original seed1 cover and gains covers on seeds2/3. It has no new full
Main-pipeline score in this replay. Frozen `main/solve.py` stays unchanged.

Complete original raw/run/witness/checker records:
[`results/2026-11-21/dynamic-probe/`](../../results/2026-11-21/dynamic-probe/).
Recorded worker/queue are audit sources with historical paths, not Main entries.
