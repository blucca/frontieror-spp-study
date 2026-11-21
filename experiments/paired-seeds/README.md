# v1-family paired seed replay

Original hard seed1 was retained, not rerun. The measured extension ran Main
seed2 tiny/easy/hard, cold HiGHS seed2 hard, then Main/cold HiGHS seed3 hard,
serially, in the original version-gated environment and same resource envelope.

Hard costs by paired seed: **240/453, 411/440, 510/337** for Python v1/cold
HiGHS1.15.1. The losing seed3 and all original run/checker files are retained.
See [RESULTS.md](../../RESULTS.md) and [raw evidence](../../results/2026-11-21/paired-seeds/).

`main/solve.py` only exposes seeds relative to frozen `../../main/solve.py`:
[`source-change.diff`](source-change.diff). Cold DFS uses seed, pool DFS uses
104729*seed, and HiGHS uses the same seed. The cold baseline is correspondingly
parameterized. Seed1 source/score remains the original frozen record.

After the root README's version-gated environment setup:

```sh
python3 -B experiments/paired-seeds/queue.py
```

This reproduces the recorded six-run extension; it writes new output under
`temp/paired-seeds/` and leaves archived evidence unchanged. `controller.py`
is the unchanged measured seed-capable controller. `queue.py` changes only
clone-local root/output paths; `recorded_queue.py` retains the historical path.
The single-file seeded algorithm also accepts the original four arguments plus
`--seed 2` or `--seed 3`, using the existing pinned environment.
