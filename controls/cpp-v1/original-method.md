# Native exact-cover repair for FrontierOR hoffman1993

AI workflow authored the design, C++ implementation and tests; human code edits: 0.
Dataset attribution: FrontierOR authors, audited derivative of
[SmartOR/FrontierOR](https://huggingface.co/datasets/SmartOR/FrontierOR),
CC BY 4.0. Source license is retained in ../../frontier-benchmark-source/source-receipts/LICENSE.md.

## Mechanism

1. Two 64-bit row masks represent columns. With K=0, equal-coverage columns are
   interchangeable, so retain the cheapest original index.
2. Cold randomized Algorithm X (dancing links) chooses the uncovered row with
   the fewest compatible columns. Branches prefer low cost per covered row,
   with one small random perturbation per search. Bounded restarts find an
   initial partition; they read only the supplied transport.
3. Remove incumbent columns to produce randomized 30/40/50/60-row holes,
   starting with the costliest of three random columns. Keep the remaining
   partition fixed. Restrict repair to columns completely contained in the hole.
4. A 60 ms / 30,000-node weighted exact-cover B&B repairs each hole. The strict
   upper bound is the removed cost. The admissible lower bound is
   sum_r min_active_column(cost(column)/coverage_count(column)).
   Each replacement edge distributes its cost equally over its covered rows;
   every row's price is at most that edge's share, proving the bound.
   DLX keeps active incidence lists sorted by true cost/coverage, so these
   minima cost O(number of uncovered rows) at a search node.
5. Accept only strictly cheaper completed exact covers, then independently
   verify disjointness, full coverage and recomputed cost inside C++.
   Preserve the incumbent on search timeout. A completed full-row B&B certifies
   the optimum; smaller completed holes certify that neighborhood only.

## Contract and scope

    c++ -std=c++17 -O3 -DNDEBUG solver.cpp -o solver
    ./solver INPUT.dat LIMIT_SECONDS SEED > RAW.json
    ./self_check.sh

Transport: N M K; then M lines cost count row0 row1 ...; K lines
lower upper coeff0 ... coeffM-1. This method supports 1 <= N <= 128, K=0,
finite nonnegative costs and nonempty columns with unique in-range rows.
All three supplied instances satisfy this scope. Input outside this scope
returns status: no_feasible and a specific metrics.termination reason.
Supporting base constraints requires a side-resource-aware repair and a revised
duplicate-column test; larger N requires multiword masks and dynamic headers.

The steady-clock deadline starts before parsing. Search reserves 4 ms for final
JSON and checks time every 128 search nodes; neighborhood construction also
consumes the same overall budget. Final JSON includes original column indices.
The shared normalizer supplies all M binary variable values and runs the
independent/original checker. no_feasible with termination: deadline reports
a search timeout; exact_cover_infeasible comes from exhaustive Algorithm X.

The executable uses one CPU and standard C++17 only. No Python optimization,
solver library, reference-solution input, cached answer, or case-specific answer
is involved.
