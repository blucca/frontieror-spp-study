# Originally held-out public cases: large1 / large4 / large5

These were the remaining three exact official `hoffman1993` instance links,
downloaded at pinned revision `ef42a2eac13595453f986d9df0b62e86e75ab596`
without reference solutions. All nine planned runs completed, using frozen
Main v1 and the original matched-version cold baselines, default seed1.

| Case | Main v1 | HiGHS1.15.1 cold | CP-SAT9.15.6755 cold |
|---|---:|---:|---:|
| large1 | 2833 | 3541 | **1832** |
| large4 | **331** | no feasible witness | no feasible witness |
| large5 | **180 optimal** | **180 optimal** | no feasible witness |

The three missing baseline witnesses are actual `FAILED` full-entry outcomes:
exit2 after the fixed cold search budget, with resource bounds passing. Costs
are absent, not zero. Successful solutions pass both complete checkers.
Full raw files: [`results/2026-11-21/holdouts/`](../../results/2026-11-21/holdouts/).

After the root README's pinned environment setup:

```sh
python3 -B experiments/holdouts/queue.py
```

This repeats the original nine-run serial queue and preserves negative runs.
New results stay in `temp/holdouts/`; the one-shot queue stops when that output
state already exists. The portable queue adapts root/source/output paths and
selects the first two allowed CPUs on the replay host. `recorded_queue.py`
retains original measured paths and exact CPU IDs0/1. Frozen solver, adapters,
shared checker and original NumPy checker are unchanged.
