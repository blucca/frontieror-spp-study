# Main v3 mechanism and exact deadline contract

Frozen source: `main/solve.py`,19474B, SHA-256
`eb3f39141b36c7768961f707c464ab1a481e0fe14f69ddca9580f41d972a9ea9`. Python-only, no subprocess solver/compiler/network or auxiliary
algorithm input. Historical C++ is confined to independent controls.

1. Validate the full instance and all M original columns/costs. For K=0,
   N<=256 and positive costs, cheapest identical-cover deduplication supports
   a bounded first cold exact cover; a complete singleton cover is used when
   available. This cover is validated before it can become an output.
2. Preserve v1's input-derived density pool: row-degree goal ceil(2logN),
   support-prefix x4 within10%-20% of canonical columns, density ties included.
   An exact partition of density<=theta columns costs at most theta*N.
   A cost-free-ranking bitset probe gets at most6s; seed is104729*CLI seed.
3. When that pool gives no new cover and an incumbent exists, use at most6s
   of strict, incumbent-preserving large-hole LNS. Alternate all incumbent
   columns with random75%-100% column unions. Only candidate columns wholly
   within the removed row union enter repair. Each hole gets at most0.6s,
   including graph rebuild. Price-prioritized ordering and the removed true
   cost cutoff guide repair; accept only a strictly cheaper whole exact cover.
   Untouched rows retain the incumbent. Failed/timed-out repair keeps it.
4. Warm-start the full original HiGHS model: all M columns, all N+K rows,
   K=base.num_constraints ranges, two threads, matching seed. On the Main
   path use the package's existing daemon `startSolve()` API and wait only
   until the absolute process deadline. Baseline `bounded=False` remains
   synchronous. The v1 measured helper and adapters remain archived.
5. A completed native task may supply a better independently feasible cover.
   A still-pending task raises the deadline condition without reading live
   native solution/info. Main validates its prior cover, writes all M values,
   closes JSON, flushes stdout/stderr, then exits the whole process with
   `os._exit(0)`. Pending-native metrics carry no optimum, gap or bound.
   With no prior whole cover, it emits a bounded failure and exits2.

The entry deadline is min(55,time_limit-5) from startup. Cold/pool ranking
preserves v1's RNG+coverage+scarcity rule. Large-hole repair uses true costs;
its generic bitset log's historical “cost-free” label is not its value-order
definition. Source `price_order=True` and the LNS function specify that order.

## Observed progression and boundaries

Small-hole large1 probe:2833→2833,6259 holes,12625 nodes, no improvement.
The separate global/large-hole first-stage probe improved2833→1334; v3 keeps
1334 in the full pipeline. Hard3 seed1 still uses the successful original
density basin252 then full refinement240. Seeds2/3 finish350/416; seed3 remains
worse than cold HiGHS337. Neither a timed-out pool nor a partial hole supplies
an output witness. Historical and probe-only experiments stay separately scored.

The large4 full native task is pending at Main's deadline. Cost331 is the
earlier exact cover, not a live backend result or an optimality claim.
An independent12s diagnostic measured12.060s algorithm /12.408s including
both checkers, with the same prior-cover deadline fallback. The local delayed-
backend tiny simulation passed objective16/all25 variables/exit0.

Original NumPy2.5.3 and independent rational whole-witness checkers validate
coverage, exact objective, selected/vector consistency, all M binary values
and all K Base rows. The separate K2 fixture has num_bases1, num_constraints2,
three native rows, selected column1/objective2; it passes the v3 native gate.
