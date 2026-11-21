# Historical v1 snapshot — superseded live entry

# Main v1 mechanism

The frozen entry is [`main/solve.py`](main/solve.py), 14,659 bytes,
SHA-256 `262cc89ce7daf833bf168bf5db4dafc3d46ae88e182ef5feaf2fe558890dd58b`.
It uses Python only: standard-library bitsets and a Python `highspy` call.
The entry has no subprocess, compiler, network call or auxiliary input.
Historical C++ programs live exclusively under `controls/`.
The same frozen entry has now been tested on all six official public cases.

## Cold basin, then full optimization

1. Read every original column and cost; validate sorted unique in-range row
   coverage and the full dimensions. Build all `M` binary output entries.
2. For `K=0`, `N<=256`, and strictly positive costs, keep the cheapest index per
   identical coverage. Empty columns are excluded from the exploratory pool.
   Use a cheapest singleton cover when available; otherwise a bounded full-pool
   Algorithm-X-style bitset DFS finds a first exact cover.
3. Sort by cost per covered row. Find a support prefix attaining
   `ceil(2*log(N))` degree per row when available. Thicken that prefix by a
   factor of four, within an input-derived 10%–20% column quantile, including
   ties at its density threshold. If an exact partition uses only columns with
   density `cost/coverage <= theta`, its cost is at most `theta*N`.
4. Probe this pool for up to six seconds using fewest-compatible-row branching;
   branch ranking combines an independent fixed RNG, coverage and scarcity.
   Branch ranking is cost-free; the incumbent cost supplies a pruning cutoff.
   A pool timeout keeps the existing incumbent.
5. Feed the legal cover to `highspy.setSolution`, then solve the **full original
   model**, with all `M` columns and all `N+K` rows, for the remaining time.
   Deduplication/pool restrictions affect only the probe, not this model.
   Preserve the best independently feasible incumbent and write full JSON.

The supplied CLI uses `min(55, time_limit-5)` seconds from process startup.
HiGHS gets two threads and seed 1; cold and pool DFS RNG seeds are 1 and
104729. Fixed seeds and wall-based cutoffs describe this v1 observation.

## Constraints and checkers

Every coverage row enforces `sum(x_j for j covering row)=1`, each `x_j` is
binary, and the objective is `sum(cost_j*x_j)`. Active Base constraints use
`K=base_constraints.num_constraints`, with all K lower/upper ranges from D.
`num_bases` is a separate schema quantity. With Base constraints, larger N or
costs outside the positive probe scope, the full sparse HiGHS path is used.

The independent exact checker recomputes every row, all M binary values,
selected/vector consistency, objective and K Base rows using rational arithmetic.
The original FrontierOR checker is an unchanged, separate NumPy process.
The synthetic Base fixture has `num_bases=1`, `num_constraints=2`, N=1, M=2;
its second Base row forces column 1, objective 2, and three native model rows.
That fixture tests the fallback contract; it is separate from benchmark scores.

## Observed seed-1 hard-instance path

Full cold cover 2138 → thickness pool 1,706 columns, theta=5.333333, minimum
row degree 64 → legal pool cover 252 after 572,584 DFS nodes / 4.932 s →
full 15,000-column HiGHS cost 240 after 49.727 s search, final bound 56.
The three improvement timestamps and complete metrics are in
[`results/2026-11-21/main/large3/algorithm.stdout.log`](../../results/2026-11-21/main/large3/algorithm.stdout.log).

The exploratory entropy script models independent uniform hyperedges conditioned
on size. It supplies a heuristic expectation, not the actual cover count of
these structured airline instances; measured pool outcomes drive the replay.

## Seed exposure and stability observation

The separate [`experiments/paired-seeds/main/solve.py`](../../experiments/paired-seeds/main/solve.py)
exposes `--seed` and passes it to cold DFS, HiGHS and pool DFS (104729*seed).
The full [source diff](../../experiments/paired-seeds/source-change.diff) records this
parameterization; the frozen entry above stays byte-identical. Extra hard costs
411/510 versus paired cold HiGHS440/337 demonstrate sensitivity to seed and
bounded pool-search outcomes. The publication retains the losing seed3.
