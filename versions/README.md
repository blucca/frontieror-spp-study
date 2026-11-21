# Version source ledger

- `v1/main/solve.py`: original complete six-case entry, unchanged14,659B.
- `v2/main/solve.py`: large-hole LNS candidate; full large4 external60s STOP.
- `v2_1/main/solve.py`: presolve-off candidate; full large4 external60s STOP.
- `v3/main/solve.py`: deadline-bounded daemon API candidate, awaiting complete
  nine-run release gate in the local preparation checkpoint.

At this preparation checkpoint, public Main remains v1. Historical source and
failed-candidate results are independent from promoted Main scores. Baseline
scripts copied under v1 preserve their original helper import layout.
